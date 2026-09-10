"""Simulación del agente XXXC en la ventana de impacto (lógica pura).

Construye el agente-día de XXXC a partir del perfil recomendado por la política
de clonación y de la demanda de referencia, calcula su margen con la **misma
lógica** del estudio (`sfeia.app.services.diario.desempeno_diario`) y lo
compara contra el margen real de los maestros y del segmento ese día.

Adiciones del plan de investigación:
- `simular_dias` (P1.1): decide con **spread previo** (ex-ante, sin look-ahead)
  y, si el día está fuera de la zona de confianza (P1.3), aplica un perfil
  defensivo que reduce la exposición a bolsa.
- `replicacion_is_oos` (P0.5): ratio IS→OOS de la imitación (estándar de los
  quants: un sistema sano conserva ≥ 50–70 % del desempeño IS).
- `dsr_aprox` (P0.5): Deflated Sharpe aproximado, corrige por múltiples
  pruebas (López de Prado).
- `capacidad` (P2.1) y `decision_negocio` con kill-switch (P2.2).

SOLID: responsabilidad única — simular y comparar la imitación en el impacto.
"""
from __future__ import annotations

import math
from statistics import median

import numpy as np

from sfeia.app.models.entities import (
    EscenarioEstres,
    MetricasDistribucion,
    PerfilAccion,
    ResumenImpacto,
    SimulacionDia,
)
from sfeia.app.services import clonacion, contexto, diario


def construir_ad_xxxc(
    dema_kwh: float,
    perfil: PerfilAccion,
    prec_cont: float,
    prec_bolsa: float,
    prec_escasez: float,
) -> dict:
    """Agente-día de XXXC coherente con el modelo del estudio (ventas = 0).

    La composición reg/no-reg del perfil reparte la demanda; los contratos
    hacia regulado y las compras SICEP se derivan de forma consistente con
    `features_diarias` del estudio.
    """
    pct_noreg = perfil.pct_noreg
    dema_reg_kwh = dema_kwh * (1.0 - pct_noreg / 100.0)
    dema_noreg_kwh = dema_kwh * (pct_noreg / 100.0)
    comp_cont_kwh = dema_kwh * (perfil.pct_cobertura / 100.0)
    comp_bolsa_kwh = dema_kwh * (perfil.pct_exposicion / 100.0)
    comp_cont_reg_kwh = comp_cont_kwh * (dema_reg_kwh / dema_kwh) if dema_kwh else 0.0
    comp_sicep_kwh = comp_cont_reg_kwh * (perfil.pct_sicep / 100.0)
    return {
        "dema_kwh": dema_kwh,
        "dema_reg_kwh": dema_reg_kwh,
        "dema_noreg_kwh": dema_noreg_kwh,
        "comp_cont_kwh": comp_cont_kwh,
        "comp_cont_reg_kwh": comp_cont_reg_kwh,
        "vent_cont_kwh": 0.0,
        "comp_bolsa_kwh": comp_bolsa_kwh,
        "vent_bolsa_kwh": 0.0,
        "comp_sicep_kwh": comp_sicep_kwh,
        "prec_cont": prec_cont,
        "prec_bolsa": prec_bolsa,
        "prec_escasez": prec_escasez,
    }


def _perfil_defensivo(perfil: PerfilAccion, factor_exposicion: float) -> PerfilAccion:
    """Reduce exposición a bolsa trasladando a contratos (P1.3).

    Fuera de la distribución de entrenamiento, clonar a ciegas es el modo de
    fallo del BC. Se conserva el abastecimiento total (cobertura + exposición ≈
    igual) moviendo volumen de bolsa a contratos, cuyo precio es conocido.
    """
    expo = round(perfil.pct_exposicion * factor_exposicion, 1)
    cob = round(perfil.pct_cobertura + (perfil.pct_exposicion - expo), 1)
    return PerfilAccion(
        pct_cobertura=cob,
        pct_exposicion=expo,
        pct_noreg=perfil.pct_noreg,
        pct_sicep=perfil.pct_sicep,
        tiene_sicep=perfil.tiene_sicep,
        n_dias=perfil.n_dias,
    )


def simular_dias(
    agentedia: dict[str, dict],
    politica,
    dema_kwh: float,
    params: dict,
    segmento_por_codigo: dict[str, str],
    segmento: str,
    codigos_maestros: set[str],
    bins_spread: dict[str, list[float]],
    usar_spread_previo: bool = True,
    factor_exposicion_fuera: float = 0.5,
    nivel_embalses_por_dia: dict[str, float] | None = None,
) -> list[SimulacionDia]:
    """Simula la política día a día sobre `agentedia` y compara contra maestros/segmento.

    Contexto ex-ante (P1.1): la decisión usa el spread con la bolsa del **día
    anterior** (conocida al decidir) y el contrato del día (conocido). El
    primer día cae al spread del mismo día (sin referencia previa). `es_escasez`
    se reporta con la bolsa realizada del día (informativo, no es la decisión).
    """
    precios_dia: dict[str, tuple[float, float, float]] = {}
    for ad in agentedia.values():
        d = str(ad["dia"])
        if d not in precios_dia:
            precios_dia[d] = (ad["prec_cont"], ad["prec_bolsa"], ad["prec_escasez"])
    fechas = sorted(precios_dia)
    bolsa_prev: dict[str, float] = {
        fechas[i]: precios_dia[fechas[i - 1]][1] for i in range(1, len(fechas))
    }

    sims: list[SimulacionDia] = []
    vistos: set[str] = set()
    for ad in agentedia.values():
        dia = str(ad["dia"])
        if dia in vistos:
            continue
        vistos.add(dia)
        prec_cont, prec_bolsa, prec_escasez = precios_dia[dia]
        if usar_spread_previo and dia in bolsa_prev:
            spread_ctx = bolsa_prev[dia] - prec_cont
        else:
            spread_ctx = prec_bolsa - prec_cont
        perfil, en_dist = clonacion.aplicar_politica_con_banda(politica, spread_ctx)
        if not en_dist and factor_exposicion_fuera < 1.0:
            perfil = _perfil_defensivo(perfil, factor_exposicion_fuera)
        ad_xxxc = construir_ad_xxxc(dema_kwh, perfil, prec_cont, prec_bolsa, prec_escasez)
        res = diario.desempeno_diario(ad_xxxc, params)
        bin_label, _, _ = contexto.binificar_spread(spread_ctx, bins_spread)
        nivel = None
        if nivel_embalses_por_dia:
            nivel = nivel_embalses_por_dia.get(dia)
            nivel = round(nivel, 1) if nivel is not None else None
        sims.append(SimulacionDia(
            fecha=dia,
            bin_spread=bin_label,
            es_escasez=contexto.es_escasez(prec_bolsa, prec_escasez),
            perfil=perfil,
            margen_imitacion=round(res["margen_por_kwh_cop"], 2),
            margen_maestros=mediana_margen_dia(agentedia, dia, codigos=codigos_maestros),
            margen_segmento=mediana_margen_dia(
                agentedia, dia, segmento=segmento, segmento_por_codigo=segmento_por_codigo
            ),
            garantia_exigida_cop=round(res["garantia_exigida_cop"], 0),
            en_distribucion=en_dist,
            nivel_embalses_pct=nivel,
        ))
    sims.sort(key=lambda s: s.fecha)
    return sims


def mediana_margen_dia(
    agentedia: dict[str, dict],
    dia: str,
    codigos: set[str] | None = None,
    segmento: str | None = None,
    segmento_por_codigo: dict[str, str] | None = None,
) -> float | None:
    """Mediana del margen por kWh de un subgrupo de agentes en un día (impacto)."""
    valores: list[float] = []
    for ad in agentedia.values():
        if str(ad["dia"]) != dia:
            continue
        if codigos is not None and ad["codigo"] not in codigos:
            continue
        if segmento is not None and segmento_por_codigo.get(ad["codigo"]) != segmento:
            continue
        valores.append(ad["desempeno"]["margen_por_kwh_cop"])
    if not valores:
        return None
    orden = sorted(valores)
    return round(orden[len(orden) // 2], 2)


def replicacion_is_oos(
    sims_estudio: list[SimulacionDia],
    sims_impacto: list[SimulacionDia],
) -> dict:
    """Ratio de replicación IS→OOS de la imitación (P0.5).

    Mediana del margen de la imitación en la ventana de estudio (IS) vs. en la
    de impacto (OOS). Un ratio ≥ 0.5–0.7 es el estándar de un sistema sano;
    cerca de 0 significa que la política no generaliza.
    """
    def _med(sims: list[SimulacionDia]) -> float | None:
        vals = [s.margen_imitacion for s in sims if s.margen_imitacion is not None]
        return round(median(vals), 2) if vals else None

    m_is = _med(sims_estudio)
    m_oos = _med(sims_impacto)
    ratio = (round(m_oos / m_is, 3) if m_is else None)
    return {"mediana_imitacion_is": m_is, "mediana_imitacion_oos": m_oos, "ratio_replicacion": ratio}


def dsr_aprox(margenes: list[float], n_trials: int) -> dict | None:
    """Deflated Sharpe Ratio aproximado (P0.5, Bailey–López de Prado).

    Corrige el Sharpe de la serie de la imitación por el número de trials
    independientes de la selección (≈ agentes candidatos rankeados). `dsr >=
    0.95` indica que el resultado difícilmente es producto de la selección por
    azar. Devuelve None si la serie es demasiado corta o sin varianza.
    """
    from scipy import stats

    arr = np.asarray([float(x) for x in margenes if x is not None])
    n = arr.size
    if n < 3 or not n_trials or n_trials < 1:
        return None
    std = arr.std(ddof=1)
    if std == 0:
        return None
    sr = float(arr.mean() / std)
    skew = float(stats.skew(arr))
    kurt = float(stats.kurtosis(arr, fisher=False))
    var_sr = max((1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr ** 2) / (n - 1), 1e-12)
    gamma = 0.5772156649015329  # constante de Euler–Mascheroni
    emax = math.sqrt(var_sr) * (
        (1 - gamma) * stats.norm.ppf(1 - 1.0 / n_trials)
        + gamma * stats.norm.ppf(1 - 1.0 / (n_trials * math.e))
    )
    den = math.sqrt(max(1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr ** 2, 1e-12))
    z = (sr - emax) * math.sqrt(n - 1) / den
    dsr = float(stats.norm.cdf(z))
    return {
        "sharpe_diario": round(sr, 3),
        "skew": round(skew, 2),
        "kurt": round(kurt, 2),
        "n_trials": int(n_trials),
        "dsr": round(dsr, 3),
        "significativo": bool(dsr >= 0.95),
    }


def capacidad(
    dema_kwh: float,
    agentedia: dict[str, dict],
    segmento: str,
    segmento_por_codigo: dict[str, str],
    umbral_pct: float = 5.0,
) -> dict | None:
    """Límite de capacidad (P2.1): la imitación no puede absorber más que una
    fracción de la demanda total del segmento (proxy de profundidad del mercado).
    """
    por_dia: dict[str, list[float]] = {}
    for ad in agentedia.values():
        if segmento_por_codigo.get(ad["codigo"]) != segmento:
            continue
        por_dia.setdefault(str(ad["dia"]), []).append(ad["dema_kwh"])
    demas = [sum(v) for v in por_dia.values() if v]
    if not demas:
        return None
    dema_seg = median(demas)
    if dema_seg <= 0:
        return None
    pct = dema_kwh / dema_seg * 100.0
    return {
        "dema_imitar_kwh": round(dema_kwh, 0),
        "dema_total_segmento_mediana_kwh": round(dema_seg, 0),
        "pct_del_segmento": round(pct, 1),
        "umbral_pct": umbral_pct,
        "supera_capacidad": bool(pct > umbral_pct),
    }


def resumen_impacto(sims: list[SimulacionDia], demanda_kwh_dia: float) -> ResumenImpacto:
    """Balance de la ventana de impacto: imitación vs maestros vs segmento."""
    imit = [s.margen_imitacion for s in sims if s.margen_imitacion is not None]
    maest = [s.margen_maestros for s in sims if s.margen_maestros is not None]
    seg = [s.margen_segmento for s in sims if s.margen_segmento is not None]
    garantias = [s.garantia_exigida_cop for s in sims]

    def _mediana(vals: list[float]) -> float | None:
        return round(median(vals), 2) if vals else None

    def _pct(condiciones: list[bool]) -> float | None:
        if not condiciones:
            return None
        return round(sum(1 for c in condiciones if c) / len(condiciones) * 100.0, 1)

    return ResumenImpacto(
        dias=len(sims),
        demanda_kwh_dia=round(demanda_kwh_dia, 0),
        mediana_imitacion=_mediana(imit) or 0.0,
        media_imitacion=round(sum(imit) / len(imit), 2) if imit else 0.0,
        mediana_maestros=_mediana(maest),
        mediana_segmento=_mediana(seg),
        pct_dias_gana_segmento=_pct([s.margen_imitacion > s.margen_segmento for s in sims if s.margen_segmento is not None]),
        pct_dias_gana_maestros=_pct([s.margen_imitacion > s.margen_maestros for s in sims if s.margen_maestros is not None]),
        garantia_mediana_cop=round(median(garantias), 0) if garantias else 0.0,
        garantia_max_cop=round(max(garantias), 0) if garantias else 0.0,
    )


def _percentil(orden: list[float], q: float) -> float:
    n = len(orden)
    return orden[min(int(round(q * (n - 1))), n - 1)]


def _drawdown_max(vals: list[float]) -> float:
    """Peor caída pico→valle de la serie acumulada de márgenes (COP/kWh)."""
    acum = 0.0
    pico = 0.0
    dd = 0.0
    for v in vals:
        acum += v
        pico = max(pico, acum)
        dd = max(dd, pico - acum)
    return dd


def distribucion(vals: list[float]) -> MetricasDistribucion:
    """Distribución de una serie de márgenes (medida de riesgo del período)."""
    if not vals:
        return MetricasDistribucion(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    n = len(vals)
    orden = sorted(vals)
    return MetricasDistribucion(
        n=n,
        mediana=round(orden[n // 2], 2),
        media=round(sum(vals) / n, 2),
        p5=round(_percentil(orden, 0.05), 2),
        p95=round(_percentil(orden, 0.95), 2),
        pct_dias_perdida=round(sum(1 for v in vals if v < 0) / n * 100.0, 1),
        peor_dia=round(min(vals), 2),
        mejor_dia=round(max(vals), 2),
        drawdown_max=round(_drawdown_max(vals), 2),
    )


def escenario_escasez(
    dema_kwh: float,
    politica,
    dias_referencia: list[dict],
    params: dict,
) -> list[EscenarioEstres]:
    """Estrés sintético si la bolsa toca (o supera) el precio de escasez.

    Usa el día del estudio con el mayor precio de escasez como referencia y
    construye dos niveles: bolsa = precio de escasez (se activa la señal) y
    bolsa = 1.25 × precio de escasez (spread > 600, bin 'escasez', donde la
    política normalmente no tiene datos y cae al fallback).
    """
    if not dias_referencia:
        return []
    dia = max(dias_referencia, key=lambda ad: ad["prec_escasez"])
    prec_cont = dia["prec_cont"]
    prec_escasez = dia["prec_escasez"]
    niveles = [
        ("escasez_umbral", "Bolsa en el precio de escasez", prec_escasez),
        ("escasez_extrema", "Bolsa 25 % sobre el precio de escasez", prec_escasez * 1.25),
    ]
    out: list[EscenarioEstres] = []
    for nombre, descripcion, prec_bolsa in niveles:
        spread = prec_bolsa - prec_cont
        perfil = clonacion.aplicar_politica(politica, spread)
        ad = construir_ad_xxxc(dema_kwh, perfil, prec_cont, prec_bolsa, prec_escasez)
        res = diario.desempeno_diario(ad, params)
        bin_label, _, _ = contexto.binificar_spread(spread, politica.bins_spread)
        out.append(EscenarioEstres(
            nombre=nombre,
            descripcion=descripcion,
            prec_bolsa=round(prec_bolsa, 1),
            prec_cont=round(prec_cont, 1),
            spread=round(spread, 1),
            bin_spread=bin_label,
            margen_cop_kwh=round(res["margen_por_kwh_cop"], 2),
            garantia_cop=round(res["garantia_exigida_cop"], 0),
        ))
    return out

def decision_negocio(
    dema_kwh: float,
    mediana_benigna: float,
    margen_escasez: float,
    margen_escasez_extrema: float,
    pct_escasez: float,
    pct_escasez_nino: float = 25.0,
    drawdown_max: float = 0.0,
    kill_switch_drawdown: float = 0.0,
    capacidad: dict | None = None,
) -> dict:
    """Traduce el análisis a decisiones de negocio para XXXC.

    Calcula la pérdida diaria si la bolsa toca el precio de escasez, el
    beneficio esperado por kWh bajo la frecuencia histórica y bajo un año
    Niño, y el veredicto de conveniencia de la estrategia imitada.

    Adiciones del plan: kill-switch por drawdown (P2.2) y límite de capacidad
    (P2.1). Si el drawdown acumulado del período simulado supera el umbral, el
    veredicto ordena NO operar la estrategia imitada sin rediseño.
    """
    def _e(p: float, margen: float) -> float:
        return (1.0 - p) * mediana_benigna + p * margen

    p_hist = pct_escasez / 100.0
    p_nino = pct_escasez_nino / 100.0
    perdida_escasez_cop = round(margen_escasez * dema_kwh, 0)
    perdida_extrema_cop = round(margen_escasez_extrema * dema_kwh, 0)
    e_historico = round(_e(p_hist, margen_escasez), 2)
    e_nino = round(_e(p_nino, margen_escasez), 2)

    kill_sw = bool(kill_switch_drawdown and drawdown_max > kill_switch_drawdown)

    if kill_sw:
        veredicto = (
            f"KILL-SWITCH: el drawdown acumulado del período simulado ({drawdown_max:,.0f} COP/kWh) supera el "
            f"umbral ({kill_switch_drawdown:,.0f} COP/kWh). NO operar la estrategia imitada sin rediseñar el perfil "
            "o reducir la exposición."
        )
    elif capacidad and capacidad["supera_capacidad"]:
        veredicto = (
            f"CAPACIDAD: la demanda simulada de XXXC ({capacidad['dema_imitar_kwh']:,.0f} kWh/día) supera el "
            f"umbral de {capacidad['umbral_pct']:.0f} % de la demanda del segmento "
            f"({capacidad['pct_del_segmento']:.1f} %): no replicable sin afectar el mercado."
        )
    elif margen_escasez >= 0:
        veredicto = "Sin pérdida relevante en escasez: la estrategia no expone a XXXC al riesgo de bolsa."
    elif e_nino < 0:
        veredicto = (
            f"En un año Niño (escasez ~{pct_escasez_nino:.0f} % de los días) la estrategia PIERDE en expectativa. "
            "Es viable solo en años benignos; exige cobertura o reducción de exposición si el clima se torna seco."
        )
    elif e_historico < 0:
        veredicto = (
            f"Incluso con la frecuencia histórica de escasez (~{pct_escasez:.2f} %) la estrategia pierde en "
            "expectativa: no se recomienda sin cambiar el perfil."
        )
    else:
        veredicto = (
            f"Con la frecuencia histórica de escasez (~{pct_escasez:.2f} %) la estrategia es positiva en "
            "expectativa, pero con una cola de pérdidas (pierde COP en un día de escasez). Solo operarla si se "
            "acepta ese riesgo y hay garantías/capital para sostener al menos los días malos."
        )

    return {
        "perdida_dia_escasez_cop": perdida_escasez_cop,
        "perdida_dia_escasez_extrema_cop": perdida_extrema_cop,
        "e_margen_dia_historico": e_historico,
        "e_margen_dia_anio_nino": e_nino,
        "pct_escasez_historico": pct_escasez,
        "pct_escasez_anio_nino": pct_escasez_nino,
        "drawdown_max_cop_kwh": round(drawdown_max, 2),
        "kill_switch_activado": kill_sw,
        "kill_switch_drawdown_cop_kwh": kill_switch_drawdown,
        "capacidad": capacidad,
        "veredicto": veredicto,
    }
