"""CONTROLLER F0: contexto de mercado (C13)."""
from __future__ import annotations


class FaseContexto:
    def __init__(self, repo, cfg):
        self.repo = repo
        self.cfg = cfg

    def ejecutar(self, datos: dict) -> dict:
        v = self.cfg["ventana"]
        rows = self.repo.contexto_mercado(v["contexto_ini"], v["contexto_fin"])
        for r in rows:
            for k in ("pbm_prom_cop", "pbm_max_cop", "pbm_min_cop",
                      "prec_escasez_prom_cop", "prec_contratos_prom_cop"):
                r[k] = float(r[k] or 0.0)
            r["dema_sin_total_gwh"] = float(r["dema_sin_total_gwh"] or 0.0)
            r["pbm_sobre_escasez"] = r["pbm_prom_cop"] > r["prec_escasez_prom_cop"]
            r["spread_contrato_bolsa"] = round(r["prec_contratos_prom_cop"] - r["pbm_prom_cop"], 1)
        resultado = {"contexto": rows}
        datos["f0"] = resultado
        return resultado