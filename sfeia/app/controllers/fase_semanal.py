"""CONTROLLER: recomendación semanal "lo actual y el futuro" (canal cliente).

Ancla la ventana al borde de datos (o a `--fecha`), corre el flujo completo
topN (`FaseAsistente.ejecutar`) y el modo arquetipo como control, aplica los
gates N1+N2 del scorecard y arma el veredicto OPERAR/NO OPERAR con criterio
estricto ("solo operar si gana", ver `docs/plan_recomendacion_semanal.md`).

El armado del payload (veredicto, KPIs, series para el dashboard, régimen) es
lógica pura testeable (funciones de módulo); la clase `FaseSemanal` solo
consulta el repo y orquesta. Las vistas (dashboard HTML / Markdown / CSV)
serializan el payload sin tocar BD.

SOLID: único componente que orquesta la recomendación semanal.
"""
from __future__ import annotations

import copy
from datetime import date, timedelta
from statistics import median

from sfeia.app.controllers.fase_asistente import FaseAsistente
from sfeia.app.models.entities import ParametrosAsistente
from sfeia.app.services import diario, scorecard
from sfeia.app.services.contexto import binificar_spread, historial_escasez, ordenar_bins

# Fallback de gates N1+N2 si `asistente.aceptacion.gates` no existe (los
# mismos valores por defecto del scorecard).
GATES_DEFAULT = {
    "alpha": 0.05,
    "min_n_efectivo": 3,
    "min_persistencia": 50.0,
    "min_replicacion": 0.5,
    "min_dsr": 0.95,
    "min_pct_gana_segmento": 60.0,
    "min_ev_historico": 0.0,
}

NOMBRES_GATES = {
    "V1_bootstrap": "su resultado no se distingue del azar",
    "V2_n_efectivo": "pocos agentes de referencia independientes",
    "V3_holdout": "no se sostiene en el período de comprobación",
    "V4_replicacion": "pierde fuerza al pasar a la semana real",
    "V5_dsr": "no resiste la corrección por el número de opciones evaluadas",
    "E1_gana_segmento": "gana pocos días frente al promedio del mercado",
    "E2_sin_kill_switch": "activa el freno de seguridad por pérdida acumulada",
    "E3_ev_historico": "pierde dinero en expectativa (histórico)",
    "E4_capacidad": "excede el tamaño operable en el mercado",
}


def resolver_ancla(ventana_cfg: dict, fecha_max: str) -> dict:
    """Resuelve el ancla del motor contra el borde de datos (4.1 del plan).

    Si `foco_fin` es None, usa `fecha_max` (fecha_max_sistema de elecdb) y
    `foco_ini = foco_fin − 180 días`; rellena `fin_c_familia` (exclusivo,
    fin+1) y `fin_c15` (inclusivo). Devuelve una copia de `ventana_cfg`.
    """
    v = copy.deepcopy(ventana_cfg)
    f_fin = date.fromisoformat(fecha_max)
    v["foco_fin"] = v.get("foco_fin") or fecha_max
    v["foco_ini"] = v.get("foco_ini") or (f_fin - timedelta(days=180)).isoformat()
    v["fin_c_familia"] = (date.fromisoformat(v["foco_fin"]) + timedelta(days=1)).isoformat()
    v["fin_c15"] = v["foco_fin"]
    return v


def fila_topn_desde_resultado(resultado: dict) -> dict:
    """Convierte el resultado del flujo completo en la fila de gates N1+N2
    (mismo formato que las filas del scorecard) + claves de despliegue."""
    v = resultado["validez"]
    res = resultado["resumen"]
    dec = resultado["decision"]
    dist = resultado["distribuciones"]["imitacion"]
    boot = v.get("bootstrap") or {}
    hold = v.get("holdout") or {}
    rep = v.get("replicacion_is_oos") or {}
    dsr = v.get("dsr") or {}
    cap = dec.get("capacidad") or {}
    maestros = resultado["maestros"]
    rels = [m.mediana_relativa for m in maestros]
    return {
        "modo": "topN",
        "segmento": resultado["parametros"]["segmento"],
        "estrategia": resultado["parametros"]["estrategia"],
        "n_maestros": len(maestros),
        "n_efectivo": v.get("n_efectivo_maestros"),
        "codigos": [m.codigo for m in maestros],
        "mediana_relativa_top": round(sum(rels) / len(rels), 2) if rels else None,
        "mediana_margen_absoluto": res.mediana_imitacion,
        "p_valor": boot.get("p_valor"),
        "ratio_replicacion": rep.get("ratio_replicacion"),
        "dsr": dsr.get("dsr"),
        "persistencia": hold.get("pct_persistencia"),
        "pct_gana_segmento": res.pct_dias_gana_segmento,
        "kill_switch": bool(dec.get("kill_switch_activado", False)),
        "drawdown_max": dist.drawdown_max,
        "p5": dist.p5,
        "p95": dist.p95,
        "peor_dia": dist.peor_dia,
        "mejor_dia": dist.mejor_dia,
        "ev_historico": dec.get("e_margen_dia_historico"),
        "ev_anio_nino": dec.get("e_margen_dia_anio_nino"),
        "supera_capacidad": bool(cap.get("supera_capacidad")) if cap else False,
        "capacidad_pct": cap.get("pct_del_segmento") if cap else None,
    }


def _gates_fallidos(ev: dict | None) -> list[str]:
    if not ev:
        return []
    return [NOMBRES_GATES[k] for k, pasa in ev["gates"].items() if not pasa]


def veredicto_semanal(fila_topn: dict | None, fila_arq: dict | None, gates: dict) -> dict:
    """Veredicto OPERAR/NO OPERAR (criterio estricto, §3 del plan).

    OPERAR si AL MENOS una combinación (topN o arquetipo) pasa N1+N2 completos
    (`valida_final` de `scorecard.evaluar_gates`); en caso contrario NO OPERAR
    prominente. La razón se redacta en lenguaje de negocio (sin jerga interna).
    """
    ev_topn = scorecard.evaluar_gates(fila_topn, gates) if fila_topn else None
    ev_arq = scorecard.evaluar_gates(fila_arq, gates) if fila_arq else None
    por_topn = bool(ev_topn and ev_topn["valida_final"])
    por_arq = bool(ev_arq and ev_arq["valida_final"])
    if por_topn or por_arq:
        if por_topn and fila_topn:
            razon = (
                f"La estrategia «{fila_topn['estrategia']}» del segmento {fila_topn['segmento']} muestra una "
                "ventaja comprobada sobre el promedio del mercado: se mantiene en la semana de comprobación y "
                "no es atribuible al azar."
            )
        else:
            razon = (
                f"La estrategia «{fila_arq['estrategia']}» del segmento {fila_arq['segmento']} (la mejor según "
                "el nivel de precios de cada día) muestra una ventaja comprobada sobre el promedio del mercado."
            )
        razon += " Opere con el perfil de la sección «Cómo operar» y revise esta recomendación cada semana."
        return {
            "operar": True,
            "veredicto": "OPERAR",
            "razon": razon,
            "por_topn": por_topn,
            "por_arquetipo": por_arq,
            "gates_topn": ev_topn,
            "gates_arq": ev_arq,
        }
    fallos = sorted(set(_gates_fallidos(ev_topn) + _gates_fallidos(ev_arq)))
    base = ("Ninguna de las estrategias analizadas muestra una ventaja comprobada sobre el promedio del "
            "mercado en la ventana vigente")
    razon = (base + ": " + "; ".join(fallos) + "." if fallos else base + ".")
    razon += " Sin ventaja comprobada, la regla es NO OPERAR."
    return {
        "operar": False,
        "veredicto": "NO OPERAR",
        "razon": razon,
        "por_topn": False,
        "por_arquetipo": False,
        "gates_topn": ev_topn,
        "gates_arq": ev_arq,
    }


def construir_series(sims: list | None, spread_por_dia: dict[str, float],
                     embalses_por_dia: dict[str, float], bins_spread: dict,
                     rango_spread: tuple | None) -> dict:
    """Series alineadas por día para las gráficas del dashboard.

    Si `sims` es None (flujo topN falló), las series de margen quedan vacías y
    solo se reportan spread/embalses (independientes del flujo).
    """
    out: dict = {
        "dias": [], "margen_imitacion": [], "margen_maestros": [], "margen_segmento": [],
        "drawdown": [], "spread": [], "embalses": [], "bin_spread": [],
        "en_distribucion": [], "es_escasez": [],
        "rango_spread": [float(rango_spread[0]), float(rango_spread[1])] if rango_spread else None,
        "bins_spread": [[label, float(lo), float(hi)] for label, lo, hi in ordenar_bins(bins_spread)],
    }
    if not sims:
        fechas = sorted(spread_por_dia)
        out["dias"] = fechas
        out["spread"] = [spread_por_dia[d] for d in fechas]
        out["embalses"] = [embalses_por_dia.get(d) for d in fechas]
        return out
    acum = 0.0
    pico = 0.0
    for s in sims:
        out["dias"].append(s.fecha)
        out["margen_imitacion"].append(s.margen_imitacion)
        out["margen_maestros"].append(None if s.margen_maestros is None else s.margen_maestros)
        out["margen_segmento"].append(None if s.margen_segmento is None else s.margen_segmento)
        acum += s.margen_imitacion
        pico = max(pico, acum)
        out["drawdown"].append(round(pico - acum, 2))
        out["spread"].append(spread_por_dia.get(s.fecha))
        out["embalses"].append(embalses_por_dia.get(s.fecha))
        out["bin_spread"].append(s.bin_spread)
        out["en_distribucion"].append(1 if s.en_distribucion else 0)
        out["es_escasez"].append(1 if s.es_escasez else 0)
    return out


def perfil_realizado_maestros(agentedia: dict, codigos: set[str]) -> dict | None:
    """Mediana del perfil realizado por los maestros en la ventana (día a día)."""
    dias = [ad["features"] for ad in agentedia.values() if ad["codigo"] in codigos]
    if not dias:
        return None

    def _med(k: str) -> float:
        vals = sorted(d[k] for d in dias)
        return round(vals[len(vals) // 2], 1)

    return {
        "pct_cobertura": _med("pct_cobertura"),
        "pct_exposicion": _med("pct_exposicion"),
        "pct_noreg": _med("pct_noreg"),
        "pct_sicep": _med("pct_sicep"),
        "n_dias": len(dias),
    }


def construir_kpis(fuente: dict, regimen: dict, umbral_kill: float,
                   pct_escasez_historico: float | None) -> list[dict]:
    """Las 8 KPI cards del dashboard con estado de semáforo (ok/warn/bad).

    Etiquetas y notas en lenguaje de negocio: el dashboard es para el cliente,
    no para el analista. p-valor y DSR se muestran como porcentajes.
    """
    def _f(v, dec: int = 2):
        return None if v is None else round(float(v), dec)

    med = _f(fuente.get("mediana_margen_absoluto"))
    pct = _f(fuente.get("pct_gana_segmento"), 1)
    dsr_raw = fuente.get("dsr")
    dsr = round(dsr_raw * 100.0, 0) if dsr_raw is not None else None
    p_raw = fuente.get("p_valor")
    p_suerte = round(p_raw * 100.0, 1) if p_raw is not None else None
    neff = fuente.get("n_efectivo")
    dd = _f(fuente.get("drawdown_max"))
    ev = _f(fuente.get("ev_historico"), 2)
    emb = regimen.get("nivel_embalses_ultimo")

    def _estado_med(v):
        if v is None:
            return "warn"
        return "ok" if v > 0 else "bad"

    def _estado_pct(v):
        if v is None:
            return "warn"
        return "ok" if v >= 60 else ("warn" if v >= 50 else "bad")

    def _estado_dsr(v):
        if v is None:
            return "warn"
        return "ok" if v >= 0.95 else ("warn" if v >= 0.8 else "bad")

    def _estado_pval(v):
        if v is None:
            return "warn"
        return "ok" if v <= 0.05 else ("warn" if v <= 0.1 else "bad")

    def _estado_neff(v):
        if v is None:
            return "warn"
        return "ok" if v >= 3 else ("warn" if v >= 2 else "bad")

    def _estado_dd(v):
        if v is None:
            return "warn"
        if v <= 0:
            return "ok"
        return "bad" if v >= umbral_kill else "warn"

    def _estado_ev(v):
        if v is None:
            return "warn"
        return "ok" if v >= 0 else "bad"

    def _estado_emb(v):
        if v is None:
            return "warn"
        return "ok" if v >= 70 else ("warn" if v >= 30 else "bad")

    nota_escasez = (f"Considera la frecuencia histórica de escasez (~{pct_escasez_historico} % de los días)."
                    if pct_escasez_historico is not None
                    else "Considera la frecuencia histórica de escasez.")
    return [
        {"id": "mediana_margen", "etiqueta": "Resultado medio de la estrategia (semana)", "valor": med,
         "unidad": "COP/kWh", "estado": _estado_med(med),
         "nota": "Lo que habría ganado o perdido por cada kWh vendido, operando el perfil recomendado la última semana."},
        {"id": "pct_gana_segmento", "etiqueta": "Días que gana al promedio del mercado", "valor": pct,
         "unidad": "%", "estado": _estado_pct(pct),
         "nota": "Días de la semana en que la estrategia superó al promedio de empresas de su tamaño. Debajo de 60 % la ventaja es dudosa."},
        {"id": "dsr", "etiqueta": "Confianza de que la ventaja no es suerte", "valor": dsr,
         "unidad": "%", "estado": _estado_dsr(dsr_raw),
         "nota": "Corrige por el número de estrategias evaluadas. Arriba de 95 %: la ventaja difícilmente es azar."},
        {"id": "bootstrap_p", "etiqueta": "Probabilidad de que sea solo suerte", "valor": p_suerte,
         "unidad": "%", "estado": _estado_pval(p_raw),
         "nota": "Debajo de 5 %: el resultado es difícil de explicar por azar."},
        {"id": "n_efectivo", "etiqueta": "Agentes imitados (independientes)", "valor": neff,
         "unidad": "", "estado": _estado_neff(neff),
         "nota": "Con menos de 3, la imitación no tiene base sólida (varias empresas se comportan igual)."},
        {"id": "drawdown_max", "etiqueta": "Peor caída acumulada", "valor": dd,
         "unidad": "COP/kWh acum.", "estado": _estado_dd(dd),
         "nota": f"Freno de seguridad: se detiene todo si la pérdida acumulada supera {umbral_kill:,.0f} COP/kWh."},
        {"id": "ev_historico", "etiqueta": "Ganancia esperada por kWh·día", "valor": ev,
         "unidad": "COP/kWh·día", "estado": _estado_ev(ev),
         "nota": nota_escasez},
        {"id": "embalses", "etiqueta": "Nivel de embalses", "valor": emb,
         "unidad": "%", "estado": _estado_emb(emb),
         "nota": f"Tendencia en la semana: {regimen.get('tendencia_embalses', '—')}."},
    ]


def _fecha(s: str) -> date:
    return date.fromisoformat(s)


def _iso(d: date) -> str:
    return d.isoformat()


class FaseSemanal:
    """Orquesta la recomendación semanal y arma el payload para las vistas."""

    def __init__(self, repo, cfg: dict):
        self.repo = repo
        self.cfg = cfg

    def ejecutar(self, p: ParametrosAsistente) -> dict:
        a_cfg = self.cfg["asistente"]
        sem_cfg = a_cfg.get("semanal", {})
        gates = a_cfg.get("aceptacion", {}).get("gates", GATES_DEFAULT)
        bins = a_cfg["bins_spread"]
        umbral_kill = float(a_cfg.get("kill_switch_drawdown_cop_kwh", 500.0))
        fa = FaseAsistente(self.repo, self.cfg)

        max_sistema = _fecha(self.repo.fecha_max_sistema())
        w = fa._resolver_fechas(p)
        fa._validar_fechas(w, max_sistema)
        historial = historial_escasez(self.repo.historial_precios(), bins)

        # ---- 1. flujo completo topN ----
        fila_topn: dict | None = None
        error_topn: str | None = None
        resultado = None
        try:
            resultado = fa.ejecutar(p)
            fila_topn = fila_topn_desde_resultado(resultado)
        except ValueError as err:
            error_topn = str(err)

        # ---- 2. control: arquetipo ganador por régimen (Ruta A) ----
        fila_arq: dict | None = None
        scan_cfg = {
            "n_boot_scan": int(a_cfg.get("aceptacion", {}).get("scan", {}).get("n_boot_scan", 200)),
            "min_dias_pct": float(p.min_dias_pct),
        }
        wdict = {"estudio_ini": w.estudio_ini, "estudio_fin": w.estudio_fin,
                 "impacto_ini": w.impacto_ini, "impacto_fin": w.impacto_fin}
        try:
            scan = fa.ejecutar_scan_ventana_arquetipo(wdict, scan_cfg, historial=historial)
            if not scan.get("error") and scan["combinaciones"]:
                fila_arq = next((c for c in scan["combinaciones"] if c["segmento"] == p.segmento), None)
                fila_arq = fila_arq or scan["combinaciones"][0]
                fila_arq = dict(fila_arq)
                fila_arq["persistencia"] = None
        except ValueError:
            fila_arq = None

        # ---- 3. contexto del mercado (independiente del flujo) ----
        rows_imp = self.repo.diario(w.impacto_ini, _iso(_fecha(w.impacto_fin) + timedelta(days=1)))
        spread_por_dia: dict[str, float] = {}
        dias_escasez_set: set[str] = set()
        for r in rows_imp:
            d = str(r["dia"])[:10]
            bolsa = float(r["prec_bolsa_cop_kwh"] or 0.0)
            cont = float(r["prec_cont_cop_kwh"] or 0.0)
            esc = float(r["prec_escasez_cop_kwh"] or 0.0)
            spread_por_dia[d] = round(bolsa - cont, 1)
            if esc > 0 and bolsa > esc:
                dias_escasez_set.add(d)
        embalses_por_dia: dict[str, float] = {}
        if bool(a_cfg.get("usar_regimen_hidrologico", True)):
            embalses_por_dia = {
                str(r["fecha"])[:10]: float(r["nivel_agregado_pct"])
                for r in self.repo.contexto_hidrologia(w.impacto_ini, _iso(_fecha(w.impacto_fin) + timedelta(days=1)))
            }
        regimen = self._construir_regimen(spread_por_dia, embalses_por_dia, len(dias_escasez_set), historial)

        # ---- 4. veredicto ----
        verdict = veredicto_semanal(fila_topn, fila_arq, gates)

        # ---- 5. series para las gráficas ----
        sims = resultado["simulacion"] if resultado else None
        rango = resultado["politica"].rango_spread if resultado else None
        series = construir_series(sims, spread_por_dia, embalses_por_dia, bins, rango)

        # ---- 6. perfil recomendado y realizado ----
        perfil: dict = {"recomendado": None, "es_defensivo": False,
                        "maestros_realizado": None, "arquetipo_ganador": None}
        if resultado and sims:
            ultimo = sims[-1]
            perfil["recomendado"] = ultimo.perfil.a_dict()
            perfil["es_defensivo"] = not ultimo.en_distribucion
            codigos = {m.codigo for m in resultado["maestros"]}
            agentedia_imp = diario.construir_agente_dia(rows_imp)
            for ad in agentedia_imp.values():
                ad["features"] = diario.features_diarias(ad)
            perfil["maestros_realizado"] = perfil_realizado_maestros(agentedia_imp, codigos)
        if fila_arq and fila_arq.get("ganadores_arquetipo"):
            perfil["arquetipo_ganador"] = {b: n for b, n in fila_arq["ganadores_arquetipo"].items()}

        # ---- 7. KPIs ----
        fuente = fila_topn if fila_topn else (fila_arq or {})
        kpis = construir_kpis(fuente, regimen, umbral_kill, historial.get("pct_dias_escasez"))

        # ---- 8. advertencias y conclusiones (lenguaje de negocio) ----
        advertencias: list[str] = []
        if error_topn:
            advertencias.append(
                "El análisis completo no pudo ejecutarse en esta ventana (datos insuficientes o ventana "
                "inválida); la recomendación se basa solo en el análisis de control. Consulte a su analista.")
        if resultado:
            n_maestros = len(resultado["maestros"])
            if n_maestros < p.top:
                advertencias.append(
                    f"El grupo de referencia para esta estrategia es pequeño ({n_maestros} empresas de las "
                    f"{p.top} esperadas): la imitación se basa en menos evidencia de la deseable.")
            if resultado["robustez"]["n_efectivo"] < n_maestros:
                advertencias.append(
                    "Varias empresas de referencia compran y venden al unísono: en la práctica, es como imitar "
                    "a una sola empresa.")
            boot = resultado["validez"].get("bootstrap")
            if boot and boot["p_valor"] > resultado["validez"]["alpha_significancia"]:
                advertencias.append(
                    "El resultado del grupo de referencia no se distingue del azar en esta ventana: "
                    "es igual de probable que sea suerte que habilidad.")
            dsr_v = resultado["validez"].get("dsr")
            if dsr_v and not dsr_v["significativo"]:
                advertencias.append(
                    "La ventaja no resiste la corrección por el número de estrategias evaluadas: pudo aparecer "
                    "por haber revisado muchas opciones, no por ser real.")
            if resultado["decision"]["kill_switch_activado"]:
                advertencias.append(
                    "La pérdida acumulada simulada superó el freno de seguridad "
                    f"({resultado['decision']['kill_switch_drawdown_cop_kwh']:,.0f} COP/kWh acumulados): "
                    "operar esta estrategia esta semana no es prudente.")
            cap = resultado["decision"].get("capacidad")
            if cap and cap["supera_capacidad"]:
                advertencias.append(
                    "El tamaño de operación solicitado supera el 5 % del mercado de su segmento: "
                    "no es replicable sin mover los precios en su contra.")
        advertencias += [
            "Las cifras son estimaciones con precios de referencia del sistema (ventas reguladas valoradas a "
            "350 COP/kWh): no son las liquidaciones reales de cada empresa.",
            "La semana evaluada ya ocurrió: la recomendación asume que las condiciones de precios se mantienen, "
            "pero el mercado puede cambiar mañana.",
            "Cuando el precio de bolsa sale del rango histórico del modelo, el sistema reduce automáticamente la "
            "exposición a bolsa (perfil defensivo).",
        ]
        conclusiones = self._conclusiones(verdict, fila_topn, fila_arq, perfil, regimen)

        maestros_tabla = []
        if resultado:
            maestros_tabla = [{
                "posicion": i + 1, "codigo": m.codigo, "nombre": m.nombre, "n_dias": m.n_dias,
                "mediana_margen": m.mediana_margen, "mediana_relativa": m.mediana_relativa,
                "pct_dias_perdida": m.pct_dias_perdida, "drawdown_max": m.drawdown_max,
            } for i, m in enumerate(resultado["maestros"])]

        alternativa = None
        if resultado and resultado.get("alternativa"):
            alt = resultado["alternativa"]
            alternativa = {
                "segmento": alt["segmento"], "estrategia": alt["estrategia"],
                "codigos": alt["codigos"], "mediana_relativa_top": alt["mediana_relativa_top"],
                "mediana_imitacion": alt["resumen"].mediana_imitacion,
            }

        return {
            "tipo": "recomendacion_semanal",
            "generado": _iso(date.today()),
            "ancla": w.impacto_fin,
            "ventanas": {
                "estudio": {"ini": w.estudio_ini, "fin": w.estudio_fin},
                "impacto": {"ini": w.impacto_ini, "fin": w.impacto_fin},
            },
            "segmento": p.segmento,
            "estrategia": p.estrategia,
            "top": p.top,
            "veredicto": verdict["veredicto"],
            "razon": verdict["razon"],
            "operar": verdict["operar"],
            "error_topn": error_topn,
            "topn": fila_topn,
            "arquetipo": fila_arq,
            "gates": {"topn": verdict["gates_topn"], "arquetipo": verdict["gates_arq"]},
            "umbrales": gates,
            "kpis": kpis,
            "regimen": regimen,
            "series": series,
            "perfil": perfil,
            "maestros": maestros_tabla,
            "alternativa": alternativa,
            "historial_escasez": {
                "pct_dias_escasez": historial.get("pct_dias_escasez"),
                "frecuencia_bins": {k: v["pct"] for k, v in historial.get("frecuencia_bins", {}).items()},
                "spread_p50": historial.get("spread_p50"),
                "spread_p95": historial.get("spread_p95"),
                "spread_max": historial.get("spread_max"),
            },
            "advertencias": advertencias,
            "conclusiones": conclusiones,
        }

    # --------------------------------------------------------------- helpers
    def _construir_regimen(self, spread_por_dia: dict[str, float],
                           embalses_por_dia: dict[str, float],
                           dias_escasez: int, historial: dict) -> dict:
        fechas = sorted(spread_por_dia)
        spread_ultimo = spread_por_dia[fechas[-1]] if fechas else None
        bin_actual, _, _ = binificar_spread(spread_ultimo or 0.0, self.cfg["asistente"]["bins_spread"])
        emb_vals = [v for v in embalses_por_dia.values() if v is not None]
        emb_ultimo = emb_vals[-1] if emb_vals else None
        if len(emb_vals) >= 2:
            delta = emb_vals[-1] - emb_vals[0]
            tendencia = "subiendo" if delta > 1 else ("bajando" if delta < -1 else "estable")
        else:
            tendencia = "—"
        return {
            "bin_actual": bin_actual,
            "spread_ultimo": spread_ultimo,
            "dias_escasez_impacto": dias_escasez,
            "n_dias_impacto": len(fechas),
            "nivel_embalses_ultimo": round(emb_ultimo, 1) if emb_ultimo is not None else None,
            "tendencia_embalses": tendencia,
            "pct_escasez_historico": historial.get("pct_dias_escasez"),
        }

    def _conclusiones(self, verdict: dict, fila_topn: dict | None, fila_arq: dict | None,
                      perfil: dict, regimen: dict) -> list[str]:
        L: list[str] = []
        if verdict["operar"]:
            if verdict["por_topn"] and fila_topn:
                L.append(
                    f"Esta semana: OPERAR con la estrategia «{fila_topn['estrategia']}» del segmento "
                    f"{fila_topn['segmento']}, siguiendo el perfil de la sección «Cómo operar» (resultado medio "
                    f"de {fila_topn['mediana_margen_absoluto']:.1f} COP/kWh en la última semana)."
                )
            if verdict["por_arquetipo"] and fila_arq:
                L.append(
                    f"La estrategia ganadora por nivel de precios («{fila_arq['estrategia']}» del segmento "
                    f"{fila_arq['segmento']}») también muestra ventaja comprobada y sirve de control."
                )
            L.append("Revise cada semana esta recomendación: si cambian los precios o el nivel de embalses, "
                     "el veredicto se recalcula automáticamente.")
        else:
            L.append("Esta semana: NO OPERAR con la estrategia analizada. Ninguna estrategia muestra una "
                     "ventaja comprobada sobre el promedio del mercado, y la regla del sistema es "
                     "«solo operar si se gana».")
            L.append("Si debe operar por obligación comercial, hágalo cubierto: compre la mayor parte con "
                     "contratos y evite la bolsa (perfil defensivo de la sección «Cómo operar»).")
            L.append("Esta recomendación se actualiza cada semana: si las condiciones de precios mejoran "
                     "(embalses altos, bolsa barata), el veredicto puede pasar a OPERAR automáticamente.")
        return L
