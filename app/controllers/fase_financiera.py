"""CONTROLLER F5: precio/margen — modelo financiero por agente desde C15 + spread de mercado (C10)."""
from __future__ import annotations

from app.services.kpi_cartera import agregar_enriquecido, modelo_financiero

_ORDEN = {"GRANDE": 0, "MEDIANO": 1, "PEQUEÑO": 2}


class FaseFinanciera:
    def __init__(self, repo, cfg):
        self.repo = repo
        self.cfg = cfg

    def ejecutar(self, datos: dict) -> dict:
        v = self.cfg["ventana"]
        mp = self.cfg["modelo_financiero"]
        por_codigo = datos["f-1"]["por_codigo"]
        sample = {c for codes in datos["f-1"]["muestra"].values() for c in codes}

        tabla = []
        for codigo in sorted(sample):
            rows = self.repo.agente_enriquecido(v["foco_ini"], v["fin_c15"], codigo)
            ag = agregar_enriquecido(rows)
            fin = modelo_financiero(ag, mp)
            dema_gwh = ag["dema_kwh"] / 1e6
            tabla.append({
                "codigo": codigo,
                "nombre": por_codigo[codigo].nombre,
                "segmento": por_codigo[codigo].segmento.value,
                "dema_gwh": round(dema_gwh, 1),
                "costo_energia_cop_kwh": fin["costo_energia_cop_kwh"],
                "garantia_exigida_cop": fin["garantia_exigida_cop"],
                "costo_garantia_cop": fin["costo_garantia_cop"],
                "provision_cartera_cop": fin["provision_cartera_cop"],
                "ingreso_clientes_cop": fin["ingreso_clientes_cop"],
                "utilidad_neta_cop": fin["utilidad_neta_cop"],
                "margen_modelo_cop_kwh": fin["margen_por_kwh_cop"],
            })
        tabla.sort(key=lambda t: (_ORDEN.get(t["segmento"], 9), -t["dema_gwh"]))

        spread = self.repo.precio_contratos(v["foco_ini"], v["fin_c_familia"])
        for r in spread:
            for k in r:
                if k != "mes":
                    r[k] = float(r[k] or 0.0)

        resultado = {"tabla": tabla, "spread_mercado": spread}
        datos["f5"] = resultado
        return resultado