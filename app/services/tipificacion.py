"""Tipificación de arquetipos por segmento (F6).

Reglas derivadas del plan (sección 6): discriminadores normativos →
empíricos. Entrada: un dict de métricas por agente; salida: nombre del arquetipo.
"""
from __future__ import annotations


def tipificar(codigo: str, segmento: str, m: dict) -> str:
    """Asigna arquetipo a un agente según segmento y métricas."""
    pct_reg = m.get("pct_reg", 0.0)
    noreg = 100.0 - pct_reg
    pct_sicep = m.get("pct_sicep", 0.0)
    pct_expo = m.get("pct_exposicion", 0.0)

    # Caso señal: intervenido
    if codigo == "CSIC":
        return "Distribuidor en intervención"

    # Generador+comercializador solo no regulado (GRANDE/MEDIANO)
    if segmento in ("GRANDE", "MEDIANO") and noreg >= 95:
        return "Generador+comercializador solo no regulado"

    if segmento == "GRANDE":
        if pct_sicep >= 80:
            return "Integrado de red"
        return "Comercializador conservador"

    if segmento == "MEDIANO":
        if pct_reg >= 80 and pct_expo < 15:
            return "Regional regulado"
        return "Trader mixto"

    # PEQUEÑO
    if noreg >= 60:
        return "Trader no regulado especializado"
    return "Frontera regulada"