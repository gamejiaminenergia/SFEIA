"""CONTROLLER F2: cobertura/exposición por agente (C04)."""
from __future__ import annotations

from sfeia.app.services.kpi_cobertura import resumen_cobertura


class FaseCobertura:
    def __init__(self, repo, cfg):
        self.repo = repo
        self.cfg = cfg

    def ejecutar(self, datos: dict) -> dict:
        v = self.cfg["ventana"]
        rows = self.repo.cobertura(v["foco_ini"], v["fin_c_familia"])
        por_nombre = resumen_cobertura(rows)
        codigo_por_nombre = datos["f-1"]["codigo_por_nombre"]
        por_codigo = datos["f-1"]["por_codigo"]
        sample = {c for codes in datos["f-1"]["muestra"].values() for c in codes}

        tabla = []
        for nombre, codigo in codigo_por_nombre.items():
            if codigo not in sample or nombre not in por_nombre:
                continue
            m = por_nombre[nombre]
            tabla.append({
                "codigo": codigo,
                "nombre": nombre,
                "segmento": por_codigo[codigo].segmento.value,
                "pct_cobertura": m["pct_cobertura"],
                "pct_exposicion": m["pct_exposicion"],
            })
        resultado = {"tabla": tabla}
        datos["f2"] = resultado
        return resultado