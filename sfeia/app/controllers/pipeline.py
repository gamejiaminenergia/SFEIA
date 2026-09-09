"""CONTROLLER: pipeline de ejecución de las fases F-1, F0–F6 en orden."""
from __future__ import annotations

from sfeia.app.controllers.fase_cartera import FaseCartera
from sfeia.app.controllers.fase_cobertura import FaseCobertura
from sfeia.app.controllers.fase_contexto import FaseContexto
from sfeia.app.controllers.fase_financiera import FaseFinanciera
from sfeia.app.controllers.fase_mix import FaseMix
from sfeia.app.controllers.fase_muestra import FaseMuestra
from sfeia.app.controllers.fase_picovalle import FasePicoValle
from sfeia.app.controllers.fase_segmentacion import FaseSegmentacion
from sfeia.app.controllers.fase_sintesis import FaseSintesis


class Pipeline:
    """Orquesta F-1 y F0–F6. Nuevas fases se registran por extensión (OCP)."""

    def __init__(self, repo, cfg):
        self.repo = repo
        self.cfg = cfg

    def ejecutar(self) -> dict:
        datos: dict = {}

        FaseSegmentacion(self.repo, self.cfg).ejecutar(datos)   # F-1
        if self.cfg.get("seleccion_muestra", {}).get("metodo") == "kmeans":
            # Muestra no supervisada: representa a los 65 vía k-means.
            FaseMuestra(self.repo, self.cfg).ejecutar(datos)
        FaseContexto(self.repo, self.cfg).ejecutar(datos)       # F0
        FaseCartera(self.repo, self.cfg).ejecutar(datos)        # F1
        FaseCobertura(self.repo, self.cfg).ejecutar(datos)      # F2
        FasePicoValle(self.repo, self.cfg).ejecutar(datos)      # F3
        FaseMix(self.repo, self.cfg).ejecutar(datos)            # F4
        FaseFinanciera(self.repo, self.cfg).ejecutar(datos)     # F5
        FaseSintesis(self.repo, self.cfg).ejecutar(datos)       # F6

        return datos