"""Simulación del agente XXXC en la ventana de impacto (lógica pura).

Construye el agente-día de XXXC a partir del perfil recomendado por la política
de clonación y de la demanda de referencia, calcula su margen con la **misma
lógica** del estudio (`sfeia.app.services.diario.desempeno_diario`) y lo
compara contra el margen real de los maestros y del segmento ese día.

SOLID: responsabilidad única — simular y comparar la imitación en el impacto.
"""
from __future__ import annotations

from statistics import median

from asistente.app.models.entities import PerfilAccion, ResumenImpacto, SimulacionDia


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
    )