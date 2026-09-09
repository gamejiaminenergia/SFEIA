"""Contexto de mercado (lógica pura): bins de spread, escasez y demanda de referencia.

SOLID: responsabilidad única — describir el 'estado del mercado' con el que el
asistente binifica y consulta su política de clonación.
"""
from __future__ import annotations

from statistics import median


def ordenar_bins(bins_spread: dict[str, list[float]]) -> list[tuple[str, float, float]]:
    """Devuelve [(label, min, max)] ordenado por min (bins contiguos)."""
    items = [(label, float(lo), float(hi)) for label, (lo, hi) in bins_spread.items()]
    items.sort(key=lambda x: x[1])
    return items


def binificar_spread(spread: float, bins_spread: dict[str, list[float]]) -> tuple[str, float, float]:
    """Bin al que pertenece el spread (bolsa − contrato, COP/kWh).

    Los bins de config son [min, max) contiguos. Si el spread queda fuera del
    rango configurado (dato fuera de distribución), se asigna al bin extremo
    más cercano (nunca se queda sin bin).
    """
    orden = ordenar_bins(bins_spread)
    for label, lo, hi in orden:
        if lo <= spread < hi:
            return label, lo, hi
    if spread < orden[0][1]:
        label, lo, hi = orden[0]
    else:
        label, lo, hi = orden[-1]
    return label, lo, hi


def es_escasez(prec_bolsa: float, prec_escasez: float) -> bool:
    """True si el precio de bolsa del día supera el precio de escasez."""
    return prec_bolsa > prec_escasez


def demanda_referencia(agentedia: dict[str, dict], segmento_por_codigo: dict[str, str], segmento: str) -> float:
    """Mediana de la demanda diaria (kWh) de los agentes del segmento en la ventana.

    Es la demanda representativa que se le asigna a XXXC cuando el usuario no
    la pasa explícitamente (`--demanda-dia-gwh`).
    """
    valores = [
        ad["dema_kwh"]
        for ad in agentedia.values()
        if segmento_por_codigo.get(ad["codigo"]) == segmento and ad["dema_kwh"] > 0
    ]
    if not valores:
        return 0.0
    return float(median(valores))