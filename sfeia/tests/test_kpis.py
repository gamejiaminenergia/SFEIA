"""Pruebas del modelo financiero y KPIs (lógica pura, sin BD)."""
from sfeia.app.services.kpi_cartera import agregar_enriquecido, modelo_financiero
from sfeia.app.services.kpi_cobertura import resumen_cobertura


def test_agregar_enriquecido():
    rows = [
        {"dema_come": 1000.0, "comp_bolsa_naci_ener": 600.0, "vent_bolsa_naci_ener": 100.0,
         "comp_cont_ener": 400.0, "vent_cont_ener": 0.0, "perdidas_ener": 50.0,
         "val_comp_bolsa_naci": 210000.0, "val_vent_bolsa_naci": 35000.0,
         "val_comp_cont": 120000.0, "val_vent_cont": 0.0},
        {"dema_come": 1000.0, "comp_bolsa_naci_ener": 600.0, "vent_bolsa_naci_ener": 100.0,
         "comp_cont_ener": 400.0, "vent_cont_ener": 0.0, "perdidas_ener": 50.0,
         "val_comp_bolsa_naci": 210000.0, "val_vent_bolsa_naci": 35000.0,
         "val_comp_cont": 120000.0, "val_vent_cont": 0.0},
    ]
    ag = agregar_enriquecido(rows)
    assert ag["dema_kwh"] == 2000.0
    assert ag["pos_net_bolsa_kwh"] == 1000.0
    assert ag["exposicion_neta_cop"] == (210000 + 120000 - 35000) * 2

    fin = modelo_financiero(ag, {
        "pv_tarifa_cop_kwh": 350.0, "cargo_regulado_cop_kwh": 76.1,
        "factor_cobertura": 0.25, "tasa_costo_anual": 0.02,
        "incobrables_pct": 0.02, "impuesto_pct": 0.33,
    })
    # Costo energía = egreso / compras = 660000 / 2000 = 330 COP/kWh
    assert fin["costo_energia_cop_kwh"] == 330.0
    # Pv=350 < costo 330 + cargos 76 → margen negativo (artefacto del modelo C18)
    assert fin["margen_por_kwh_cop"] < 0


def test_resumen_cobertura():
    rows = [
        {"agente": "A", "dema_gwh": 100.0, "cont_gwh": 80.0, "bolsa_gwh": 20.0},
        {"agente": "A", "dema_gwh": 100.0, "cont_gwh": 70.0, "bolsa_gwh": 30.0},
    ]
    out = resumen_cobertura(rows)
    assert out["A"]["pct_cobertura"] == 75.0
    assert out["A"]["pct_exposicion"] == 25.0