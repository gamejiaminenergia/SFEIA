"""Modelo financiero por agente (equivalente a C16–C18) desde C15.

Estimaciones con precio promedio de sistema (ver plan sección 3.2):
no hay precio horario ni precio por agente en elecdb. No sustituyen
liquidaciones XM.
"""
from __future__ import annotations


def agregar_enriquecido(rows: list[dict]) -> dict:
    """Agrega filas horarias de C15 a totales por agente."""
    def f(key):
        return sum(float(r[key] or 0.0) for r in rows)

    dema = f("dema_come")
    compra_bolsa = f("comp_bolsa_naci_ener")
    venta_bolsa = f("vent_bolsa_naci_ener")
    compra_cont = f("comp_cont_ener")
    venta_cont = f("vent_cont_ener")
    perdidas = f("perdidas_ener")
    val_comp = f("val_comp_cont") + f("val_comp_bolsa_naci")
    val_vent = f("val_vent_cont") + f("val_vent_bolsa_naci")
    val_comp_bolsa = f("val_comp_bolsa_naci")
    val_vent_bolsa = f("val_vent_bolsa_naci")

    return {
        "dema_kwh": dema,
        "compra_bolsa_kwh": compra_bolsa,
        "venta_bolsa_kwh": venta_bolsa,
        "compra_cont_kwh": compra_cont,
        "venta_cont_kwh": venta_cont,
        "perdidas_kwh": perdidas,
        "val_comp_cop": val_comp,
        "val_vent_cop": val_vent,
        "pos_net_bolsa_kwh": compra_bolsa - venta_bolsa,
        "pos_net_cont_kwh": compra_cont - venta_cont,
        "exposicion_neta_cop": val_comp - val_vent,
        "egreso_energia_cop": val_comp,
    }


def modelo_financiero(ag: dict, params: dict) -> dict:
    """Aplica la lógica documentada de C16–C18 sobre los totales de C15."""
    pv = float(params["pv_tarifa_cop_kwh"])
    cargo = float(params["cargo_regulado_cop_kwh"])
    factor = float(params["factor_cobertura"])
    tasa = float(params["tasa_costo_anual"])
    incobrables = float(params["incobrables_pct"])
    impuesto = float(params["impuesto_pct"])

    demanda = ag["dema_kwh"]
    compra_kwh = ag["compra_bolsa_kwh"] + ag["compra_cont_kwh"]
    expo = ag["exposicion_neta_cop"]

    ingreso = demanda * pv
    egreso = ag["egreso_energia_cop"]
    cargos = compra_kwh * cargo
    bruta = ingreso - egreso - cargos

    garantia = max(0.0, expo * factor)
    costo_garantia = garantia * (tasa / 12.0)
    provision = ingreso * incobrables
    imp = max(0.0, bruta * impuesto)
    utilidad_neta = bruta - imp - costo_garantia - provision
    margen_kwh = utilidad_neta / demanda if demanda else 0.0
    costo_energia_kwh = egreso / compra_kwh if compra_kwh else 0.0

    return {
        "garantia_exigida_cop": round(garantia),
        "costo_garantia_cop": round(costo_garantia),
        "provision_cartera_cop": round(provision),
        "impuesto_cop": round(imp),
        "utilidad_neta_cop": round(utilidad_neta),
        "margen_por_kwh_cop": round(margen_kwh, 2),
        "costo_energia_cop_kwh": round(costo_energia_kwh, 1),
        "ingreso_clientes_cop": round(ingreso),
    }