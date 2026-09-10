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


def historial_escasez(dias: list[dict], bins_spread: dict[str, list[float]]) -> dict:
    """Frecuencia histórica de contextos de spread y de días de escasez.

    Responde '¿qué tan probable es la escasez?': con todo el histórico de la BD
    cuenta días por bin de spread, días con bolsa > precio de escasez (señal de
    escasez real) y percentiles del spread. La política de clonación suele no
    tener datos en el bin 'escasez': esta medida cuantifica ese vacío.
    """
    n = 0
    n_escasez = 0
    bins: dict[str, int] = {label: 0 for label in bins_spread}
    spreads: list[float] = []
    por_anio: dict[int, list[float]] = {}
    for d in dias:
        bolsa = float(d["prec_bolsa"] or 0.0)
        cont = float(d["prec_cont"] or 0.0)
        esc = float(d["prec_escasez"] or 0.0)
        spread = bolsa - cont
        n += 1
        spreads.append(spread)
        label, _, _ = binificar_spread(spread, bins_spread)
        bins[label] += 1
        if esc > 0 and bolsa > esc:
            n_escasez += 1
        por_anio.setdefault(d["fecha"].year if hasattr(d["fecha"], "year") else int(str(d["fecha"])[:4]), []).append(spread)

    if not n:
        return {"n_dias": 0, "frecuencia_bins": {}, "n_dias_escasez": 0, "pct_dias_escasez": 0.0,
                "spread_p50": 0.0, "spread_p95": 0.0, "spread_p99": 0.0, "spread_max": 0.0, "por_anio": {}}

    def _p(orden: list[float], q: float) -> float:
        return orden[min(int(round(q * (n - 1))), n - 1)]

    orden = sorted(spreads)
    anios = {}
    for anio, vals in por_anio.items():
        esc_anio = sum(1 for i, d in enumerate(dias) if int(str(d["fecha"])[:4]) == anio and float(d["prec_escasez"] or 0) > 0 and float(d["prec_bolsa"] or 0) > float(d["prec_escasez"] or 0))
        anios[anio] = {"n_dias": len(vals), "n_escasez": esc_anio,
                       "pct_escasez": round(esc_anio / len(vals) * 100.0, 1)}

    return {
        "n_dias": n,
        "frecuencia_bins": {k: {"n": v, "pct": round(v / n * 100.0, 2)} for k, v in bins.items()},
        "n_dias_escasez": n_escasez,
        "pct_dias_escasez": round(n_escasez / n * 100.0, 2),
        "spread_p50": round(orden[n // 2], 1),
        "spread_p95": round(_p(orden, 0.95), 1),
        "spread_p99": round(_p(orden, 0.99), 1),
        "spread_max": round(max(orden), 1),
        "por_anio": anios,
    }