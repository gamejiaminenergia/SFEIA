"""Modelo financiero por kWh (equivalente a C16–C18) sobre agregados diarios.

Estimaciones con precio promedio de sistema (ver plan): no hay precio horario
ni precio por agente en elecdb. No sustituyen liquidaciones XM. Es la métrica
de desempeño del estudio híbrido diario y del asistente imitador.
"""
from __future__ import annotations


def modelo_financiero(ag: dict, params: dict) -> dict:
    """Aplica la lógica documentada de C16–C18 sobre los totales del agente-día.

    `ag` debe traer: dema_kwh, compra_bolsa_kwh, venta_bolsa_kwh,
    compra_cont_kwh, venta_cont_kwh, exposicion_neta_cop, egreso_energia_cop.
    Devuelve el margen estimado por kWh (artefacto: Pv fijo de config).
    """
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