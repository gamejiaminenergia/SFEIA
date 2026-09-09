"""CONTROLLER F-1: segmentación de la población completa por tamaño.

El estudio híbrido diario analiza TODOS los comercializadores con demanda en la
ventana (65): no existe muestra. `muestra` se mantiene como la población
completa agrupada por segmento para compatibilidad con módulos heredados.
"""
from __future__ import annotations

from app.models.entities import Segmento
from app.services.segmentacion import resumen_por_segmento, segmentar_poblacion


def _poblacion_completa(poblacion) -> dict[str, list[str]]:
    """Todos los agentes agrupados por segmento de tamaño."""
    out: dict[str, list[str]] = {s.value: [] for s in Segmento}
    for a in poblacion:
        out[a.segmento.value].append(a.codigo)
    return out


class FaseSegmentacion:
    def __init__(self, repo, cfg):
        self.repo = repo
        self.cfg = cfg

    def ejecutar(self, datos: dict) -> dict:
        v = self.cfg["ventana"]
        seg = self.cfg["segmentacion"]
        rows = self.repo.segmentacion_poblacion(v["foco_ini"], v["fin_c_familia"])
        poblacion = segmentar_poblacion(rows, seg["grande_min_gwh"], seg["mediano_min_gwh"])
        resumen = resumen_por_segmento(poblacion)

        muestra = _poblacion_completa(poblacion)

        por_codigo = {a.codigo: a for a in poblacion}
        codigo_por_nombre = {a.nombre: a.codigo for a in poblacion}

        resultado = {
            "poblacion": poblacion,
            "resumen": resumen,
            "muestra": muestra,
            "muestra_metodo": "poblacion_completa",
            "muestra_total": sum(len(v) for v in muestra.values()),
            "total_agentes": len(poblacion),
            "por_codigo": por_codigo,
            "codigo_por_nombre": codigo_por_nombre,
        }
        datos["f-1"] = resultado
        return resultado