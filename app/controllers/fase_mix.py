"""CONTROLLER F4: mix de mercado objetivo — % reg/no-reg y pérdidas (C08 + contexto CIIU C06)."""
from __future__ import annotations

from collections import defaultdict


class FaseMix:
    def __init__(self, repo, cfg):
        self.repo = repo
        self.cfg = cfg

    def ejecutar(self, datos: dict) -> dict:
        v = self.cfg["ventana"]
        perdidas_rows, ciiu_rows = self.repo.mix(v["foco_ini"], v["fin_c_familia"])

        perd = defaultdict(lambda: {"dema": 0.0, "real": 0.0})
        for r in perdidas_rows:
            d = perd[r["agente"]]
            d["dema"] += float(r["dema_come_gwh"] or 0.0)
            d["real"] += float(r["dema_real_gwh"] or 0.0)

        ciiu_agg: dict[str, float] = defaultdict(float)
        for r in ciiu_rows:
            ciiu_agg[r["sector_ciiu"]] += float(r["dema_noreg_gwh"] or 0.0)
        top_ciiu = sorted(ciiu_agg.items(), key=lambda kv: kv[1], reverse=True)[:10]

        codigo_por_nombre = datos["f-1"]["codigo_por_nombre"]
        por_codigo = datos["f-1"]["por_codigo"]
        sample = {c for codes in datos["f-1"]["muestra"].values() for c in codes}

        tabla = []
        for nombre, codigo in codigo_por_nombre.items():
            if codigo not in sample or nombre not in perd:
                continue
            d = perd[nombre]
            pct_perd = (d["dema"] - d["real"]) / d["dema"] * 100 if d["dema"] else 0.0
            pct_reg = _pct_reg(datos, codigo)
            tabla.append({
                "codigo": codigo,
                "nombre": nombre,
                "segmento": por_codigo[codigo].segmento.value,
                "pct_reg": pct_reg,
                "pct_noreg": round(100.0 - pct_reg, 1),
                "pct_perdidas": round(pct_perd, 2),
            })
        resultado = {"tabla": tabla, "top_ciiu": top_ciiu}
        datos["f4"] = resultado
        return resultado


def _pct_reg(datos: dict, codigo: str) -> float:
    """% regulado por agente desde los datos de F1 (C01)."""
    for fila in datos["f1"]["tabla"]:
        if fila["codigo"] == codigo:
            return fila["pct_reg"]
    return 0.0