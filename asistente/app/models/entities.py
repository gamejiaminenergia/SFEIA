"""Entidades del dominio del asistente imitador (MODEL).

Dataclasses puras, sin acceso a datos. El asistente clona el comportamiento
(top-N) de un (segmento, estrategia) en una ventana de estudio y lo replica en
una ventana de impacto (Behavioral Cloning por tabla contexto → acción).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParametrosAsistente:
    """Parámetros de una ejecución del asistente.

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