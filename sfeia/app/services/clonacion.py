"""Clonación conductual (Behavioral Cloning) por tabla contexto → acción.

Aprende, de los agentes-día de los maestros (top-N) cuando jugaron la
estrategia objetivo en la ventana de estudio, la **mediana del perfil de
abastecimiento** por bin de spread. La política es determinista e
interpretable: dado el spread de un día → perfil recomendado.

SOLID: responsabilidad única — construir y consultar la política de clonación.
"""
from __future__ import annotations

from statistics import median

from sfeia.app.models.entities import PerfilAccion, PoliticaClonacion, ReglaPolitica
from sfeia.app.services.contexto import binificar_spread

FEATURES_ACCION = ["pct_cobertura", "pct_exposicion", "pct_noreg", "pct_sicep", "tiene_sicep"]


def _coincide(arquetipo: str, estrategia: str) -> bool:
    return arquetipo.strip().lower() == estrategia.strip().lower()


def _mediana_perfil(dias: list[dict]) -> PerfilAccion:
    """Mediana de cada feature de acción sobre los agentes-día de entrenamiento."""
    return PerfilAccion(
        pct_cobertura=round(median([d["pct_cobertura"] for d in dias]), 1),
        pct_exposicion=round(median([d["pct_exposicion"] for d in dias]), 1),
        pct_noreg=round(median([d["pct_noreg"] for d in dias]), 1),
        pct_sicep=round(median([d["pct_sicep"] for d in dias]), 1),
        tiene_sicep=round(median([d["tiene_sicep"] for d in dias]), 2),
        n_dias=len(dias),
    )


def construir_politica(
    agentedia: dict[str, dict],
    etiquetas: list[str],
    labels,
    perfiles: dict,
    codigos_maestros: set[str],
    segmento: str,
    estrategia: str,
    segmento_por_codigo: dict[str, str],
    bins_spread: dict[str, list[float]],
) -> PoliticaClonacion:
    """Política BC a partir de los agentes-día de los maestros.

    Solo entrena con los días en que un maestro jugó la **estrategia objetivo**
    (clúster del estudio que coincide con `estrategia`). Por bin de spread se
    agrupan esos agentes-día y se toma la mediana del perfil de abastecimiento.
    """
    cids_objetivo = {cid for cid, p in perfiles.items() if _coincide(p.arquetipo, estrategia)}
    por_bin: dict[str, list[dict]] = {}
    metadatos: dict[str, tuple[float, float]] = {}
    todos: list[dict] = []

    for i, clave in enumerate(etiquetas):
        ad = agentedia[clave]
        if ad["codigo"] not in codigos_maestros:
            continue
        if segmento_por_codigo.get(ad["codigo"]) != segmento:
            continue
        if int(labels[i]) not in cids_objetivo:
            continue
        f = ad["features"]
        spread = ad["prec_bolsa"] - ad["prec_cont"]
        bin_label, lo, hi = binificar_spread(spread, bins_spread)
        por_bin.setdefault(bin_label, []).append(f)
        metadatos[bin_label] = (lo, hi)
        todos.append(f)

    reglas: dict[str, ReglaPolitica] = {}
    for label, dias in por_bin.items():
        lo, hi = metadatos[label]
        reglas[label] = ReglaPolitica(
            bin_spread=label,
            spread_min=lo,
            spread_max=hi,
            perfil=_mediana_perfil(dias),
            n_dias=len(dias),
        )

    fallback = _mediana_perfil(todos) if todos else None
    return PoliticaClonacion(reglas=reglas, fallback=fallback, bins_spread=bins_spread)


def _distancia_a_bin(spread: float, lo: float, hi: float) -> float:
    if lo <= spread <= hi:
        return 0.0
    return min(abs(spread - lo), abs(spread - hi))


def aplicar_politica(politica: PoliticaClonacion, spread: float) -> PerfilAccion:
    """Perfil recomendado para un día dado su spread (con fallback).

    Si el bin del día no tiene entrenamiento (contexto fuera de distribución),
    se usa el bin **con datos** más cercano; si no hay ninguna regla, el
    fallback (mediana global de la ventana de estudio).
    """
    label, lo, hi = binificar_spread(spread, politica.bins_spread)
    regla = politica.reglas.get(label)
    if regla:
        return regla.perfil

    candidatos = [
        (r, _distancia_a_bin(spread, r.spread_min, r.spread_max))
        for r in politica.reglas.values()
    ]
    if candidatos:
        mejor = min(candidatos, key=lambda x: (x[1], x[0].bin_spread))[0]
        return mejor.perfil
    if politica.fallback:
        return politica.fallback
    raise ValueError("Política de clonación vacía: no hay reglas ni fallback para entrenar")