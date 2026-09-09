"""CONTROLLER F3: posición neta por bloque PICO (18–22h) vs fuera de pico (C05)."""
from __future__ import annotations

from collections import defaultdict


class FasePicoValle:
    def __init__(self, repo, cfg):
        self.repo = repo
        self.cfg = cfg

    def ejecutar(self, datos: dict) -> dict:
        v = self.cfg["ventana"]
        rows = self.repo.pico_valle(v["foco_ini"], v["fin_c_familia"])

        agg = defaultdict(lambda: {"pico": {}, "fuera": {}})
        for r in rows:
            bloque = "pico" if r["bloque_horario"].startswith("PICO") else "fuera"
            agg[r["agente"]][bloque] = {
                "comp": float(r["comp_bolsa_gwh"] or 0.0),
                "vent": float(r["vent_bolsa_gwh"] or 0.0),
                "pos": float(r["posicion_neta_bolsa_gwh"] or 0.0),
                "rol": r["rol_neto"],
            }

        codigo_por_nombre = datos["f-1"]["codigo_por_nombre"]
        por_codigo = datos["f-1"]["por_codigo"]
        sample = {c for codes in datos["f-1"]["muestra"].values() for c in codes}

        tabla = []
        for nombre, codigo in codigo_por_nombre.items():
            if codigo not in sample or nombre not in agg:
                continue
            p = agg[nombre]["pico"]
            f = agg[nombre]["fuera"]
            tabla.append({
                "codigo": codigo,
                "nombre": nombre,
                "segmento": por_codigo[codigo].segmento.value,
                "comp_pico_gwh": p.get("comp", 0.0),
                "pos_pico_gwh": p.get("pos", 0.0),
                "rol_pico": p.get("rol", "-"),
                "comp_fuera_gwh": f.get("comp", 0.0),
                "pos_fuera_gwh": f.get("pos", 0.0),
                "rol_fuera": f.get("rol", "-"),
            })
        resultado = {"tabla": tabla}
        datos["f3"] = resultado
        return resultado