"""Segmentación de la población por tamaño (F-1).

Lógica pura: dado el DemaCome semestral asigna GRANDE/MEDIANO/PEQUEÑO.
Umbrales parametrizados (config/config.yaml) para reproducibilidad.
"""
from __future__ import annotations

from sfeia.app.models.entities import AgenteSegmentado, Segmento


def asignar_segmento(dema_gwh: float, grande_min: float = 2000.0, mediano_min: float = 100.0) -> Segmento:
    """Asigna segmento por demanda semestral (GWh)."""
    if dema_gwh >= grande_min:
        return Segmento.GRANDE
    if dema_gwh >= mediano_min:
        return Segmento.MEDIANO
    return Segmento.PEQUEÑO


def segmentar_poblacion(rows: list[dict], grande_min: float = 2000.0, mediano_min: float = 100.0) -> list[AgenteSegmentado]:
    """Convierte las filas de sql/f-1_segmentacion.sql en entidades segmentadas."""
    poblacion: list[AgenteSegmentado] = []
    for r in rows:
        gwh = float(r["dema_come_gwh"] or 0.0)
        reg = float(r["reg_gwh"]) if r.get("reg_gwh") is not None else 0.0
        noreg = float(r["noreg_gwh"]) if r.get("noreg_gwh") is not None else 0.0
        poblacion.append(
            AgenteSegmentado(
                codigo=r["agente_code"],
                nombre=r["name"],
                dema_come_gwh=round(gwh, 1),
                pct_reg=round(reg / gwh * 100, 1) if gwh else 0.0,
                pct_noreg=round(noreg / gwh * 100, 1) if gwh else 0.0,
                segmento=asignar_segmento(gwh, grande_min, mediano_min),
            )
        )
    return poblacion


def resumen_por_segmento(poblacion: list[AgenteSegmentado]) -> dict[str, dict]:
    """Agrega conteo, GWh y mix reg/no-reg por segmento."""
    resumen: dict[str, dict] = {
        s.value: {"n": 0, "gwh": 0.0, "reg_gwh": 0.0, "noreg_gwh": 0.0}
        for s in Segmento
    }
    total_gwh = sum(a.dema_come_gwh for a in poblacion)
    for a in poblacion:
        r = resumen[a.segmento.value]
        r["n"] += 1
        r["gwh"] += a.dema_come_gwh
        r["reg_gwh"] += a.dema_come_gwh * a.pct_reg / 100.0
        r["noreg_gwh"] += a.dema_come_gwh * a.pct_noreg / 100.0
    for r in resumen.values():
        r["pct_mercado"] = round(r["gwh"] / total_gwh * 100, 1) if total_gwh else 0.0
        r["pct_reg"] = round(r["reg_gwh"] / r["gwh"] * 100, 1) if r["gwh"] else 0.0
        r["pct_noreg"] = round(r["noreg_gwh"] / r["gwh"] * 100, 1) if r["gwh"] else 0.0
        r["gwh"] = round(r["gwh"], 1)
    return resumen