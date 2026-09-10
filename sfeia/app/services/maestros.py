"""Selección de los maestros del asistente (lógica pura).

Dado el resultado del estudio híbrido diario sobre la ventana de estudio,
elige a los **top-N** agentes del (segmento, estrategia) objetivo por mediana
del margen por kWh, con guarda de presencia mínima en la estrategia.

SOLID: responsabilidad única — quiénes son los maestros a imitar.
"""
from __future__ import annotations

from statistics import median

from sfeia.app.models.entities import AgenteMaestro


def _coincide(arquetipo: str, estrategia: str) -> bool:
    return arquetipo.strip().lower() == estrategia.strip().lower()


def seleccionar_maestros(
    agentes: list,
    segmento: str,
    estrategia: str,
    top: int,
    n_dias_estudio: int,
    min_dias_pct: float = 0.0,
) -> list[AgenteMaestro]:
    """Top-N agentes del (segmento, estrategia) por mediana del margen diario.

    `agentes` son los `AgenteDia` del estudio (tienen segmento, arquetipo y
    margen_kwh). Se agrupa por código y se ordena por mediana del margen;
    los agentes con presencia marginal en la estrategia quedan fuera.
    """
    margenes: dict[str, list[float]] = {}
    nombres: dict[str, str] = {}
    for a in agentes:
        if a.segmento != segmento or not _coincide(a.arquetipo, estrategia):
            continue
        margenes.setdefault(a.codigo, []).append(a.margen_kwh)
        nombres[a.codigo] = a.nombre

    umbral = max(1, round(n_dias_estudio * min_dias_pct / 100)) if min_dias_pct and n_dias_estudio else 0

    candidatos: list[AgenteMaestro] = []
    for codigo, vals in margenes.items():
        n = len(vals)
        if n < umbral:
            continue
        orden = sorted(vals)
        candidatos.append(AgenteMaestro(
            codigo=codigo,
            nombre=nombres.get(codigo, codigo),
            n_dias=n,
            mediana_margen=round(orden[len(orden) // 2], 2),
            media_margen=round(sum(vals) / n, 2),
        ))

    candidatos.sort(key=lambda m: (-m.mediana_margen, -m.n_dias, m.codigo))
    return candidatos[:top]


def sensibilidad(
    agentes: list,
    segmento: str,
    estrategia: str,
    n_dias_estudio: int,
    tops: tuple[int, ...] = (3, 5, 7),
    min_dias_pcts: tuple[float, ...] = (10.0, 20.0, 30.0),
) -> dict[tuple[int, float], list[str]]:
    """Estabilidad del top-N frente a (top, min_dias_pct).

    Re-selecciona maestros con otras configuraciones sobre la **misma** ventana
    de estudio y devuelve { (top, min_dias_pct): [códigos] } para ver si los
    maestros cambian mucho (robustez de la selección).
    """
    out: dict[tuple[int, float], list[str]] = {}
    for top in tops:
        for mp in min_dias_pcts:
            ms = seleccionar_maestros(agentes, segmento, estrategia, top, n_dias_estudio, mp)
            out[(top, mp)] = [m.codigo for m in ms]
    return out


def detectar_duplicados(maestros: list[AgenteMaestro]) -> list[list[str]]:
    """Agrupa maestros con idéntico (mediana, media) de margen.

    Un margen idéntico redondeado suele indicar el mismo comportamiento (o
    datos espejo); contar cada uno como 'maestro' independiente infla el top-N.
    """
    grupos: dict[tuple[float, float], list[str]] = {}
    for m in maestros:
        grupos.setdefault((m.mediana_margen, m.media_margen), []).append(m.codigo)
    return [codes for codes in grupos.values() if len(codes) > 1]