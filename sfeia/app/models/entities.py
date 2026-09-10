"""Entidades del dominio (MODEL). Dataclasses puras, sin acceso a datos.

Cubre el estudio híbrido diario (segmentación, estrategias, desempeño) y el
asistente imitador (Behavioral Cloning del top-N): maestros, política de
clonación, simulación en la ventana de impacto.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Segmento(str, Enum):
    GRANDE = "GRANDE"
    MEDIANO = "MEDIANO"
    PEQUEÑO = "PEQUEÑO"


@dataclass
class AgenteSegmentado:
    codigo: str
    nombre: str
    dema_come_gwh: float
    pct_reg: float
    pct_noreg: float
    segmento: Segmento


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


# ---------------------------------------------------------------- asistente --
@dataclass(frozen=True)
class ParametrosAsistente:
    """Parámetros de una ejecución del asistente imitador.

    Las fechas pueden venir `None` desde el CLI; el controlador las resuelve con
    la config y el límite de datos de la BD antes de ejecutar.
    """
    segmento: str = "PEQUEÑO"
    estrategia: str = "Trader expuesto a bolsa (sin cobertura)"
    top: int = 5
    estudio_ini: str | None = None
    estudio_fin: str | None = None
    impacto_ini: str | None = None
    impacto_fin: str | None = None
    demanda_dia_gwh: float | None = None
    min_dias_pct: float = 20.0
    dias_impacto_por_defecto: int = 7


@dataclass(frozen=True)
class VentanasResueltas:
    """Ventanas de estudio e impacto ya resueltas y validadas."""
    estudio_ini: str
    estudio_fin: str
    impacto_ini: str
    impacto_fin: str


@dataclass
class AgenteMaestro:
    """Un agente del top-N del (segmento, estrategia) en la ventana de estudio."""
    codigo: str
    nombre: str
    n_dias: int
    mediana_margen: float
    media_margen: float


@dataclass
class PerfilAccion:
    """Perfil de abastecimiento diario (la 'acción' que se clona).

    Mismas variables del estudio k-means en escala original.
    """
    pct_cobertura: float
    pct_exposicion: float
    pct_noreg: float
    pct_sicep: float
    tiene_sicep: float
    n_dias: int = 0

    def a_dict(self) -> dict:
        return {
            "pct_cobertura": self.pct_cobertura,
            "pct_exposicion": self.pct_exposicion,
            "pct_noreg": self.pct_noreg,
            "pct_sicep": self.pct_sicep,
            "tiene_sicep": self.tiene_sicep,
            "n_dias": self.n_dias,
        }


@dataclass
class ReglaPolitica:
    """Regla de la política de clonación: en un bin de spread, esta es la acción."""
    bin_spread: str
    spread_min: float
    spread_max: float
    perfil: PerfilAccion
    n_dias: int = 0


@dataclass
class PoliticaClonacion:
    """Política completa: reglas por bin + perfil fallback (mediana global).

    `reglas` solo contiene bins con datos; los bins sin entrenamiento se
    resuelven con el bin más cercano con datos, o con `fallback` si ninguno.
    """
    reglas: dict[str, ReglaPolitica] = field(default_factory=dict)
    fallback: PerfilAccion | None = None
    bins_spread: dict[str, list[float]] = field(default_factory=dict)


@dataclass
class SimulacionDia:
    """Resultado de un día de la ventana de impacto."""
    fecha: str
    bin_spread: str
    es_escasez: bool
    perfil: PerfilAccion
    margen_imitacion: float
    margen_maestros: float | None
    margen_segmento: float | None
    garantia_exigida_cop: float = 0.0


@dataclass
class MetricasDistribucion:
    """Distribución de márgenes de una serie (imitación / maestros / segmento)."""
    n: int
    mediana: float
    media: float
    p5: float
    p95: float
    pct_dias_perdida: float
    peor_dia: float
    mejor_dia: float
    drawdown_max: float


@dataclass
class EscenarioEstres:
    """Escenario sintético de estrés (p. ej. bolsa en/precio de escasez)."""
    nombre: str
    descripcion: str
    prec_bolsa: float
    prec_cont: float
    spread: float
    bin_spread: str
    margen_cop_kwh: float
    garantia_cop: float


@dataclass
class ResumenImpacto:
    """Balance de la ventana de impacto (imitación vs maestros vs segmento)."""
    dias: int
    demanda_kwh_dia: float
    mediana_imitacion: float
    media_imitacion: float
    mediana_maestros: float | None
    mediana_segmento: float | None
    pct_dias_gana_segmento: float | None
    pct_dias_gana_maestros: float | None
    garantia_mediana_cop: float = 0.0
    garantia_max_cop: float = 0.0