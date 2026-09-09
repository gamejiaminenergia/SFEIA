"""Entidades del dominio (MODEL). Dataclasses puras, sin acceso a datos."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Segmento(str, Enum):
    GRANDE = "GRANDE"
    MEDIANO = "MEDIANO"
    PEQUEÑO = "PEQUEÑO"


@dataclass(frozen=True)
class Agente:
    codigo: str
    nombre: str
    actividad: str = "COMERCIALIZACIÓN"


@dataclass
class AgenteSegmentado:
    codigo: str
    nombre: str
    dema_come_gwh: float
    pct_reg: float
    pct_noreg: float
    segmento: Segmento


@dataclass
class MatrizFila:
    segmento: str
    agente: str
    codigo: str
    dema_gwh: float
    pct_reg: float
    pct_cobertura: float
    pct_exposicion: float
    pct_sicep: float
    pct_perdidas: float
    costo_energia_cop_kwh: float
    garantia_est_cop: float
    provision_cartera_cop: float
    arquetipo: str