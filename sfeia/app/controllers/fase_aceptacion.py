"""CONTROLLER: harness de aceptación del asistente (Fase 0 del plan).

Corre el grid de ventanas (2015 → límite de datos), hace el **scan grueso**
(`FaseAsistente.ejecutar_scan_ventana`, n_boot bajo, sin holdout) sobre todas
las (segmento × estrategia) de cada ventana y **confirma** las candidatas (y
las mejores casi-candidatas) con el flujo completo `FaseAsistente.ejecutar`
(bootstrap fino + holdout + DSR + riesgo). Produce el scorecard N0–N4.

SOLID: es el único componente que orquesta el grid y consulta el repo; la
lógica de evaluación vive en `sfeia.app.services.scorecard`.
"""
from __future__ import annotations

import copy
from datetime import date, timedelta

from sfeia.app.controllers.fase_asistente import FaseAsistente
from sfeia.app.models.entities import ParametrosAsistente
from sfeia.app.services import diario, scorecard
from sfeia.app.services.contexto import historial_escasez


def _fecha(d: str) -> date:
    return date.fromisoformat(d)


def _iso(d: date) -> str:
    return d.isoformat()


class FaseAceptacion:
    def __init__(self, repo, cfg: dict):
        self.repo = repo
        self.cfg = cfg

    # ------------------------------------------------------------- grid
    def generar_grid(self, a_cfg: dict, fin_max: date) -> list[dict]:
        g = a_cfg["aceptacion"]["grid"]
        return scorecard.generar_grid(
            int(g["dias_estudio"]), int(g["dias_impacto"]), int(g["paso_dias"]),
            date(2015, 1, 1), fin_max,
        )

    # ----------------------------------------------------- flujo completo
    def ejecutar(self) -> dict:
        a_cfg = self.cfg["asistente"]
        acc = a_cfg["aceptacion"]
        scan_cfg = {**acc["scan"], **acc["gates"]}
        fin_max = _fecha(self.repo.fecha_max_sistema())
        ventanas = self.generar_grid(a_cfg, fin_max)
        hist = historial_escasez(self.repo.historial_precios(), a_cfg["bins_spread"])
        fa = FaseAsistente(self.repo, self.cfg)

        filas, candidatas, errores = self._scan_modo(ventanas, scan_cfg, hist, fa, modo="topN")
        filas_arq, candidatas_arq, errores_arq = self._scan_modo(ventanas, scan_cfg, hist, fa, modo="arquetipo")
        errores += errores_arq

        confirmadas = self._confirmar_modo(candidatas, filas, scan_cfg, fa, modo="topN")
        confirmadas_arq = self._confirmar_modo(candidatas_arq, filas_arq, scan_cfg, fa, modo="arquetipo")

        confirmadas.sort(key=lambda c: (0 if c["valida_final"] else 1, c["p_valor"]))
        confirmadas_arq.sort(key=lambda c: (0 if c["valida_final"] else 1, c["p_valor"]))
        return {
            "ventanas": ventanas,
            "n_ventanas_ok": len(ventanas) - errores,
            "n_ventanas_error": errores,
            "filas": filas,
            "n_combinaciones": len(filas),
            "candidatas": candidatas,
            "confirmadas": confirmadas,
            "filas_arquetipo": filas_arq,
            "n_combinaciones_arquetipo": len(filas_arq),
            "candidatas_arquetipo": candidatas_arq,
            "confirmadas_arquetipo": confirmadas_arq,
            "historial": hist,
            "filtros": acc["gates"],
            "grid": acc["grid"],
        }

    def _scan_modo(self, ventanas: list[dict], scan_cfg: dict, hist: dict,
                   fa: FaseAsistente, modo: str) -> tuple[list[dict], list[dict], int]:
        """Scan grueso de un modo (topN o arquetipo) sobre el grid."""
        filas: list[dict] = []
        errores = 0
        for w in ventanas:
            scan = fa.ejecutar_scan_ventana(w, scan_cfg, historial=hist) if modo == "topN" \
                else fa.ejecutar_scan_ventana_arquetipo(w, scan_cfg, historial=hist)
            if scan.get("error"):
                errores += 1
                continue
            for c in scan["combinaciones"]:
                fila = {
                    "estudio_ini": w["estudio_ini"], "estudio_fin": w["estudio_fin"],
                    "impacto_ini": w["impacto_ini"], "impacto_fin": w["impacto_fin"],
                    "modo": modo, **c,
                }
                ev = scorecard.evaluar_gates(fila, scan_cfg)
                fila["candidata"] = ev["valida_cheap"]
                fila["valida_cheap"] = ev["valida_cheap"]
                filas.append(fila)
        candidatas = [f for f in filas if f["candidata"]]
        return filas, candidatas, errores

    def _confirmar_modo(self, candidatas: list[dict], filas: list[dict], scan_cfg: dict,
                        fa: FaseAsistente, modo: str) -> list[dict]:
        """Confirmación fina de candidatas (y mejores casi-candidatas)."""
        max_confirmar = int(scan_cfg.get("max_confirmar", 25))
        candidatas.sort(key=lambda f: (f["p_valor"], -f["mediana_margen_absoluto"], f["estudio_ini"]))
        candidatas = candidatas[:max_confirmar]
        orden = sorted(filas, key=lambda f: (f["p_valor"], -f["mediana_margen_absoluto"]))
        confirmar_top = int(scan_cfg.get("confirmar_top", 8))
        a_confirmar = candidatas + [f for f in orden if not f["candidata"]][:confirmar_top]
        vistos: set[str] = set()
        confirmadas: list[dict] = []
        for f in a_confirmar:
            k = (f["modo"], f["estudio_ini"], f["estudio_fin"], f["segmento"], f["estrategia"])
            if k in vistos:
                continue
            vistos.add(k)
            conf = self._confirmar(f, scan_cfg, modo)
            if conf:
                confirmadas.append(conf)
        return confirmadas

    # ------------------------------------------------------- confirmación
    def _confirmar(self, f: dict, scan_cfg: dict, modo: str = "topN") -> dict | None:
        """Confirmación fina: flujo completo del asistente sobre la ventana.

        n_boot=1000, holdout activo, DSR con trials reales, riesgo y fidelidad.
        Con `modo="arquetipo"` usa la política de arquetipo ganador por régimen
        y valida a nivel de arquetipo (bootstrap + persistencia del ganador).
        """
        cfg_e = copy.deepcopy(self.cfg)
        cfg_e["asistente"]["n_boot"] = int(scan_cfg.get("n_boot_confirma", 1000))
        cfg_e["asistente"]["dias_holdout"] = int(scan_cfg.get("dias_holdout", 2))
        cfg_e["asistente"]["top_por_defecto"] = int(scan_cfg["top"])
        fa = FaseAsistente(self.repo, cfg_e)
        if modo == "arquetipo":
            return self._confirmar_arquetipo(f, scan_cfg, fa)
        p = ParametrosAsistente(
            segmento=f["segmento"], estrategia=f["estrategia"], top=int(scan_cfg["top"]),
            estudio_ini=f["estudio_ini"], estudio_fin=f["estudio_fin"],
            impacto_ini=f["impacto_ini"], impacto_fin=f["impacto_fin"],
            min_dias_pct=float(scan_cfg["min_dias_pct"]),
            dias_impacto_por_defecto=7,
        )
        try:
            r = fa.ejecutar(p)
        except ValueError:
            return None
        val = r["validez"]
        boot = val.get("bootstrap")
        holdout = val.get("holdout")
        rep = val.get("replicacion_is_oos", {})
        dsr = val.get("dsr")
        res = r["resumen"]
        dist = r["distribuciones"]["imitacion"]
        dec = r["decision"]
        cap = dec.get("capacidad")
        f1 = self._f1_confirmado(fa, r)
        fila = {
            "modo": "topN",
            "estudio_ini": f["estudio_ini"], "estudio_fin": f["estudio_fin"],
            "impacto_ini": f["impacto_ini"], "impacto_fin": f["impacto_fin"],
            "segmento": f["segmento"], "estrategia": f["estrategia"],
            "n_maestros": len(r["maestros"]),
            "n_efectivo": val.get("n_efectivo_maestros"),
            "codigos": [m.codigo for m in r["maestros"]],
            "mediana_relativa_top": round(
                sum(m.mediana_relativa for m in r["maestros"]) / len(r["maestros"]), 2
            ) if r["maestros"] else None,
            "mediana_margen_absoluto": res.mediana_imitacion,
            "p_valor": boot["p_valor"] if boot else 1.0,
            "ratio_replicacion": rep.get("ratio_replicacion"),
            "dsr": dsr["dsr"] if dsr else None,
            "persistencia": holdout.get("pct_persistencia") if holdout else None,
            "pct_gana_segmento": res.pct_dias_gana_segmento,
            "kill_switch": bool(dec["kill_switch_activado"]),
            "drawdown_max": dist.drawdown_max,
            "ev_historico": dec["e_margen_dia_historico"],
            "ev_anio_nino": dec["e_margen_dia_anio_nino"],
            "supera_capacidad": bool(cap["supera_capacidad"]) if cap else False,
            "capacidad_pct": cap["pct_del_segmento"] if cap else None,
            "mae_f1": f1["promedio"],
            "mae_f1_detalle": f1,
        }
        ev = scorecard.evaluar_gates(fila, scan_cfg)
        fila["gates"] = ev["gates"]
        fila["valida_final"] = ev["valida_final"]
        fila["n1_completo"] = ev["n1_completo"]
        fila["n2"] = ev["n2"]
        return fila

    def _confirmar_arquetipo(self, f: dict, scan_cfg: dict, fa: FaseAsistente) -> dict | None:
        """Confirmación fina en modo arquetipo: bootstrap fino + holdout V3'."""
        w = {"estudio_ini": f["estudio_ini"], "estudio_fin": f["estudio_fin"],
             "impacto_ini": f["impacto_ini"], "impacto_fin": f["impacto_fin"]}
        scan_fino = dict(scan_cfg)
        scan_fino["n_boot_scan"] = int(scan_cfg.get("n_boot_confirma", 1000))
        r = fa.ejecutar_scan_ventana_arquetipo(w, scan_fino, historial=None)
        if r.get("error"):
            return None
        c = next((x for x in r["combinaciones"] if x["segmento"] == f["segmento"]), None)
        if not c:
            return None
        # holdout V3': seleccionar ganador en sub-estudio y validar en sub-validación
        persistencia = self._holdout_arquetipo(fa, w, f["segmento"], scan_cfg)
        fila = {**c,
                "modo": "arquetipo",
                "estudio_ini": w["estudio_ini"], "estudio_fin": w["estudio_fin"],
                "impacto_ini": w["impacto_ini"], "impacto_fin": w["impacto_fin"],
                "persistencia": persistencia.get("persistencia") if persistencia else None,
                }
        fila["codigos"] = sorted((c.get("ganadores_arquetipo") or {}).values())
        ev = scorecard.evaluar_gates(fila, scan_cfg)
        fila["gates"] = ev["gates"]
        fila["valida_final"] = ev["valida_final"]
        fila["n1_completo"] = ev["n1_completo"]
        fila["n2"] = ev["n2"]
        return fila

    def _holdout_arquetipo(self, fa: FaseAsistente, w: dict, segmento: str, scan_cfg: dict) -> dict | None:
        """V3': el arquetipo ganador del sub-estudio se sostiene en sub-validación."""
        from sfeia.app.services import maestros as msvc

        dias_holdout = int(scan_cfg.get("dias_holdout", 2))
        sub_fin = _fecha(w["estudio_fin"]) - timedelta(days=dias_holdout)
        if sub_fin < _fecha(w["estudio_ini"]):
            return None
        min_dias = float(scan_cfg["min_dias_pct"])
        try:
            full_sel = fa._correr_estudio(w["estudio_ini"], _iso(sub_fin))
            full_val = fa._correr_estudio(_iso(sub_fin + timedelta(days=1)), w["estudio_fin"])
        except ValueError:
            return None
        d_sel, d_val = full_sel["diario"], full_val["diario"]
        seg_cod_sel = {x: a.segmento.value for x, a in full_sel["f-1"]["por_codigo"].items()}
        bins = fa.cfg["asistente"]["bins_spread"]
        ganadores, fallback = msvc.arquetipos_ganadores_por_bin(
            d_sel["agentedia"], d_sel["etiquetas"], d_sel["labels"], d_sel["perfiles"],
            segmento, seg_cod_sel, bins,
        )
        if fallback is None:
            return None
        arq = d_sel["perfiles"][fallback].arquetipo
        return msvc.persistencia_arquetipo(d_val["agentes"], segmento, arq, d_val["n_dias"], min_dias)

    def _f1_confirmado(self, fa: FaseAsistente, r: dict) -> dict:
        """F1 (fidelidad) sobre la ventana de impacto del flujo confirmado."""
        p = r["parametros"]
        w_imp = p["ventanas"]["impacto"]
        rows = fa.repo.diario(w_imp["ini"], _iso(_fecha(w_imp["fin"]) + timedelta(days=1)))
        ad_imp = diario.construir_agente_dia(rows)
        for ad in ad_imp.values():
            ad["features"] = diario.features_diarias(ad)
        codigos = {m.codigo for m in r["maestros"]}
        usar_previo = bool(fa.cfg["asistente"].get("usar_spread_previo", True))
        return scorecard.fidelidad_mae(ad_imp, r["politica"], codigos, usar_spread_previo=usar_previo)