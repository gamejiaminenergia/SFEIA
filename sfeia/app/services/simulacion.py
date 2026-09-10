"""Simulación del agente XXXC en la ventana de impacto (lógica pura).

Construye el agente-día de XXXC a partir del perfil recomendado por la política
de clonación y de la demanda de referencia, calcula su margen con la **misma
lógica** del estudio (`sfeia.app.services.diario.desempeno_diario`) y lo
compara contra el margen real de los maestros y del segmento ese día.

SOLID: responsabilidad única — simular y comparar la imitación en el impacto.
"""
from __future__ import annotations

from statistics import median

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
) -> dict:
    """Traduce el análisis a decisiones de negocio para XXXC.

    Calcula la pérdida diaria si la bolsa toca el precio de escasez, el
    beneficio esperado por kWh bajo la frecuencia histórica y bajo un año
    Niño, y el veredicto de conveniencia de la estrategia imitada.
    """
    def _e(p: float, margen: float) -> float:
        return (1.0 - p) * mediana_benigna + p * margen

    p_hist = pct_escasez / 100.0
    p_nino = pct_escasez_nino / 100.0
    perdida_escasez_cop = round(margen_escasez * dema_kwh, 0)
    perdida_extrema_cop = round(margen_escasez_extrema * dema_kwh, 0)
    e_historico = round(_e(p_hist, margen_escasez), 2)
    e_nino = round(_e(p_nino, margen_escasez), 2)

    if margen_escasez >= 0:
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
        "veredicto": veredicto,
    }
