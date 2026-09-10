"""Clonación conductual (Behavioral Cloning) por tabla contexto → acción.

Aprende, de los agentes-día de los maestros (top-N) cuando jugaron la
estrategia objetivo en la ventana de estudio, la **mediana del perfil de
abastecimiento** por bin de spread. La política es determinista e
interpretable: dado el spread de un día → perfil recomendado.

Adiciones del plan de investigación:
- `pesos` (P1.2): si se pasan, el perfil por bin es el **promedio ponderado**
  de los perfiles de cada maestro (agregación) en vez de la mediana pooled del
  top-N discreto (que era Follow-the-Leader).
- `rango_spread` (P1.3): rango de spreads observado en el entrenamiento.
  `aplicar_politica_con_banda` indica si un día está dentro/fuera de la
  distribución; el simulador reduce exposición fuera de ella.

SOLID: responsabilidad única — construir y consultar la política de clonación.
"""
from __future__ import annotations

from statistics import median

from sfeia.app.models.entities import PerfilAccion, PoliticaClonacion, ReglaPolitica
from sfeia.app.services import maestros
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


def _perfil_ponderado(por_maestro: dict[str, list[dict]], pesos: dict[str, float]) -> PerfilAccion:
    """Perfil por bin = mediana de cada maestro en ese bin, combinada con pesos.

    Los maestros sin presencia en el bin no aportan; los pesos se re-normalizan
    sobre los presentes. Si ningún maestro con peso tiene datos, cae a la
    mediana pooled (comportamiento original).
    """
    med_por_maestro = {c: _mediana_perfil(dias) for c, dias in por_maestro.items()}
    n_dias = sum(len(dias) for dias in por_maestro.values())
    presentes = [c for c in med_por_maestro if c in pesos]
    if not presentes:
        return _mediana_perfil([d for dias in por_maestro.values() for d in dias])
    w = {c: pesos[c] for c in presentes}
    tot = sum(w.values()) or 1.0

    def _mezcla(atr: str, redondeo: int) -> float:
        return round(sum(w[c] / tot * getattr(med_por_maestro[c], atr) for c in presentes), redondeo)

    return PerfilAccion(
        pct_cobertura=_mezcla("pct_cobertura", 1),
        pct_exposicion=_mezcla("pct_exposicion", 1),
        pct_noreg=_mezcla("pct_noreg", 1),
        pct_sicep=_mezcla("pct_sicep", 1),
        tiene_sicep=_mezcla("tiene_sicep", 2),
        n_dias=n_dias,
    )


def _construir_politica_arquetipo(
    agentedia: dict[str, dict],
    etiquetas: list[str],
    labels,
    perfiles: dict,
    segmento: str,
    segmento_por_codigo: dict[str, str],
    bins_spread: dict[str, list[float]],
) -> PoliticaClonacion:
    """Ruta A: política que mezcla arquetipos por régimen (bin de spread).

    El 'experto' no es el top-N de agentes (indistinguibles dentro de una
    estrategia) sino el **arquetipo ganador por bin**: se clona el perfil
    mediano de TODOS los agentes del segmento que juegan el arquetipo que mejor
    superó al segmento en ese bin. El fallback es el perfil del arquetipo
    ganador global (sin condicionar por bin).
    """
    ganadores, fallback = maestros.arquetipos_ganadores_por_bin(
        agentedia, etiquetas, labels, perfiles, segmento, segmento_por_codigo, bins_spread
    )
    por_bin: dict[str, list[dict]] = {}
    por_fallback: list[dict] = []
    spread_min: float | None = None
    spread_max: float | None = None
    for i, k in enumerate(etiquetas):
        ad = agentedia[k]
        if segmento_por_codigo.get(ad["codigo"]) != segmento:
            continue
        cid = int(labels[i])
        spread = ad["prec_bolsa"] - ad["prec_cont"]
        spread_min = spread if spread_min is None else min(spread_min, spread)
        spread_max = spread if spread_max is None else max(spread_max, spread)
        if cid == fallback:
            por_fallback.append(ad["features"])
        bin_label, _, _ = binificar_spread(spread, bins_spread)
        if cid == ganadores.get(bin_label):
            por_bin.setdefault(bin_label, []).append(ad["features"])

    reglas: dict[str, ReglaPolitica] = {}
    for bin_label, dias in por_bin.items():
        lo, hi = _limites_bin(bin_label, bins_spread)
        reglas[bin_label] = ReglaPolitica(
            bin_spread=bin_label, spread_min=lo, spread_max=hi,
            perfil=_mediana_perfil(dias), n_dias=len(dias),
        )
    fallback_perfil = _mediana_perfil(por_fallback) if por_fallback else None
    rango = (round(spread_min, 2), round(spread_max, 2)) if spread_min is not None else None
    return PoliticaClonacion(
        reglas=reglas,
        fallback=fallback_perfil,
        bins_spread=bins_spread,
        rango_spread=rango,
        modo="arquetipo",
        ganadores_arquetipo={b: perfiles[cid].arquetipo for b, cid in ganadores.items()},
    )


def _limites_bin(bin_label: str, bins_spread: dict[str, list[float]]) -> tuple[float, float]:
    lo, hi = bins_spread[bin_label]
    return float(lo), float(hi)


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
    pesos: dict[str, float] | None = None,
    modo: str = "topN",
) -> PoliticaClonacion:
    """Política BC a partir de los agentes-día de los maestros.

    Con `modo="topN"` (por defecto) solo entrena con los días en que un maestro
    del top-N jugó la **estrategia objetivo** y toma la mediana del perfil (o
    el promedio ponderado si `pesos`). Con `modo="arquetipo"` (Ruta A) clona el
    arquetipo ganador por bin de spread (ver `_construir_politica_arquetipo`).

    Registra el rango de spreads observado (P1.3): la zona de confianza
    dentro de la cual la política tiene respaldo empírico.
    """
    if modo == "arquetipo":
        return _construir_politica_arquetipo(
            agentedia, etiquetas, labels, perfiles, segmento, segmento_por_codigo, bins_spread
        )
    cids_objetivo = {cid for cid, p in perfiles.items() if _coincide(p.arquetipo, estrategia)}
    por_bin: dict[str, list[dict]] = {}
    por_bin_por_maestro: dict[str, dict[str, list[dict]]] = {}
    metadatos: dict[str, tuple[float, float]] = {}
    todos: list[dict] = []
    todos_por_maestro: dict[str, list[dict]] = {}
    spread_min: float | None = None
    spread_max: float | None = None

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
        spread_min = spread if spread_min is None else min(spread_min, spread)
        spread_max = spread if spread_max is None else max(spread_max, spread)
        bin_label, lo, hi = binificar_spread(spread, bins_spread)
        por_bin.setdefault(bin_label, []).append(f)
        por_bin_por_maestro.setdefault(bin_label, {}).setdefault(ad["codigo"], []).append(f)
        metadatos[bin_label] = (lo, hi)
        todos.append(f)
        todos_por_maestro.setdefault(ad["codigo"], []).append(f)

    reglas: dict[str, ReglaPolitica] = {}
    for label, dias in por_bin.items():
        lo, hi = metadatos[label]
        perfil = _perfil_ponderado(por_bin_por_maestro[label], pesos) if pesos else _mediana_perfil(dias)
        reglas[label] = ReglaPolitica(
            bin_spread=label,
            spread_min=lo,
            spread_max=hi,
            perfil=perfil,
            n_dias=len(dias),
        )

    if pesos:
        fallback = _perfil_ponderado(todos_por_maestro, pesos) if todos_por_maestro else None
    else:
        fallback = _mediana_perfil(todos) if todos else None
    rango = (round(spread_min, 2), round(spread_max, 2)) if todos else None
    return PoliticaClonacion(
        reglas=reglas,
        fallback=fallback,
        bins_spread=bins_spread,
        rango_spread=rango,
        modo="ponderado" if pesos else "mediana",
        pesos=dict(pesos) if pesos else None,
    )


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


def aplicar_politica_con_banda(
    politica: PoliticaClonacion, spread: float
) -> tuple[PerfilAccion, bool]:
    """Perfil + bandera de 'dentro de distribución' (P1.3).

    `en_distribucion=False` cuando el spread del día cae **fuera** del rango
    observado en el entrenamiento: la política aplica su regla más cercana pero
    el simulador debe **reducir exposición** (el clonado ciego fuera de la
    distribución es el modo de fallo clásico del Behavioral Cloning).
    """
    perfil = aplicar_politica(politica, spread)
    rango = politica.rango_spread
    if rango is None:
        return perfil, True
    return perfil, rango[0] <= spread <= rango[1]