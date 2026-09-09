"""CONTROLLER F1: perfil de cartera por agente (C01, C02, C03, SICEP)."""
from __future__ import annotations

from collections import defaultdict


class FaseCartera:
    def __init__(self, repo, cfg):
        self.repo = repo
        self.cfg = cfg

    def ejecutar(self, datos: dict) -> dict:
        v = self.cfg["ventana"]
        c01, c02, c03, sicep = self.repo.cartera(v["foco_ini"], v["fin_c_familia"])

        dema = defaultdict(lambda: {"dema": 0.0, "reg": 0.0, "noreg": 0.0})
        for r in c01:
            d = dema[r["agente"]]
            d["dema"] += float(r["dema_gwh"] or 0.0)
            d["reg"] += float(r["dema_reg_gwh"] or 0.0)
            d["noreg"] += float(r["dema_noreg_gwh"] or 0.0)

        bolsa = defaultdict(lambda: {"comp": 0.0, "vent": 0.0})
        for r in c02:
            b = bolsa[r["agente"]]
            b["comp"] += float(r["comp_bolsa_gwh"] or 0.0)
            b["vent"] += float(r["vent_bolsa_gwh"] or 0.0)

        cont = defaultdict(lambda: {"comp": 0.0, "vent": 0.0})
        for r in c03:
            c = cont[r["agente"]]
            c["comp"] += float(r["comp_contratos_gwh"] or 0.0)
            c["vent"] += float(r["vent_contratos_gwh"] or 0.0)

        sic = defaultdict(lambda: {"reg": 0.0, "sicep": 0.0})
        for r in sicep:
            s = sic[r["agente"]]
            s["reg"] += float(r["cont_reg_gwh"] or 0.0)
            s["sicep"] += float(r["cont_sicep_gwh"] or 0.0)

        codigo_por_nombre = datos["f-1"]["codigo_por_nombre"]
        por_codigo = datos["f-1"]["por_codigo"]

        tabla = []
        for nombre, codigo in codigo_por_nombre.items():
            if codigo not in _sample_codes(datos):
                continue
            d, b, c, s = dema[nombre], bolsa[nombre], cont[nombre], sic[nombre]
            pct_reg = round(d["reg"] / d["dema"] * 100, 1) if d["dema"] else 0.0
            tabla.append({
                "codigo": codigo,
                "nombre": nombre,
                "segmento": por_codigo[codigo].segmento.value,
                "dema_gwh": round(d["dema"], 1),
                "pct_reg": pct_reg,
                "pct_noreg": round(100.0 - pct_reg, 1),
                "comp_bolsa_gwh": round(b["comp"], 1),
                "vent_bolsa_gwh": round(b["vent"], 1),
                "comp_cont_gwh": round(c["comp"], 1),
                "vent_cont_gwh": round(c["vent"], 1),
                "pos_net_bolsa_gwh": round(b["comp"] - b["vent"], 1),
                "pos_net_cont_gwh": round(c["comp"] - c["vent"], 1),
                "pct_sicep": round(s["sicep"] / s["reg"] * 100, 1) if s["reg"] else None,
            })

        resultado = {"tabla": tabla}
        datos["f1"] = resultado
        return resultado


def _sample_codes(datos: dict) -> set[str]:
    return {c for codes in datos["f-1"]["muestra"].values() for c in codes}