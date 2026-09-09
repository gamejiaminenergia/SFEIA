"""CONTROLLER F-1: segmentación de la población por tamaño."""
from __future__ import annotations

from app.services.segmentacion import resumen_por_segmento, segmentar_poblacion


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
        muestra = self.cfg["muestra"]

        por_codigo = {a.codigo: a for a in poblacion}
        codigo_por_nombre = {a.nombre: a.codigo for a in poblacion}

        resultado = {
            "poblacion": poblacion,
            "resumen": resumen,
            "muestra": muestra,
            "muestra_total": sum(len(v) for v in muestra.values()),
            "total_agentes": len(poblacion),
            "por_codigo": por_codigo,
            "codigo_por_nombre": codigo_por_nombre,
        }
        datos["f-1"] = resultado
        return resultado