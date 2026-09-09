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


@dataclass
class AgenteClusterizado:
    codigo: str
    nombre: str
    segmento: str
    cluster_id: int
    arquetipo: str
    features: dict


@dataclass
class PerfilCluster:
    cluster_id: int
    n: int
    miembros: list[str]
    medias: dict
    medianas: dict
    composicion_segmento: dict
    arquetipo: str


@dataclass
class AgenteDia:
    """Una fila por (agente, día) del estudio híbrido diario."""
    codigo: str
    nombre: str
    dia: str
    segmento: str
    cluster_id: int
    arquetipo: str
    features: dict
    margen_kwh: float
    costo_kwh: float


@dataclass
class PerfilEstrategia:
    """Perfil de un arquetipo (clúster) en la población de agentes-día."""
    cluster_id: int
    arquetipo: str
    n: int
    n_agentes: int
    medias: dict
    composicion_segmento: dict


@dataclass
class BalanceEstrategia:
    """Balance del período por estrategia (ranking final)."""
    cluster_id: int
    arquetipo: str
    dias: int
    mediana_margen: float
    media_margen: float
    dias_puesto1: int
    pct_top3: float
    rango_promedio: float
    tendencia: float