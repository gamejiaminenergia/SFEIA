"""CONTROLLER de selección de muestra no supervisada.

Solo se ejecuta en el pipeline benchmark cuando `seleccion_muestra.metodo ==
kmeans`: reutiliza FaseClustering (clústeres sobre los 65, sin tocar sus
salidas) y deriva los representantes por clúster (medoide + extremos) que
alimentan la narrativa del informe. No modifica el estudio `--estudio kmeans`.
"""
from __future__ import annotations

from sfeia.app.controllers.fase_clustering import FaseClustering
from sfeia.app.services.clustering import seleccionar_representantes


class FaseMuestra:
    def __init__(self, repo, cfg):
        self.repo = repo
        self.cfg = cfg

    def ejecutar(self, datos: dict) -> dict:
        if "clustering" not in datos:
            FaseClustering(self.repo, self.cfg).ejecutar(datos)
        cl = datos["clustering"]
        sel = self.cfg.get("seleccion_muestra", {})
        representantes = seleccionar_representantes(
            etiquetas=cl["etiquetas"],
            labels=cl["labels"],
            X_scaled=cl["X_scaled"],
            modelo=cl["modelo"],
            agregados=cl["agregados"],
            features=cl["features"],
            representantes_por_cluster=int(sel.get("representantes_por_cluster", 3)),
            extremos_por_feature=int(sel.get("extremos_por_feature", 1)),
        )
        datos["f-1"]["representantes"] = representantes
        return representantes