"""Pruebas unitarias del scorecard de aceptación (lógica pura, sin BD)."""
from __future__ import annotations

from datetime import date

import numpy as np

from sfeia.app.models.entities import PerfilEstrategia
from sfeia.app.services import clonacion, diario, scorecard

BINS = {
    "muy_barata": [-999999, 0],
    "barata": [0, 200],
    "neutral": [200, 400],
    "cara": [400, 999999],
}

ESTRATEGIA = "Trader expuesto a bolsa (sin cobertura)"


def test_generar_grid():
    g = scorecard.generar_grid(30, 7, 10, date(2025, 1, 1), date(2025, 3, 15))
    assert g, "debe generar ventanas"
    w0 = g[0]
    assert w0["estudio_ini"] == "2025-01-01"
    assert w0["estudio_fin"] == "2025-01-30"
    assert w0["impacto_ini"] == "2025-01-31"
    assert w0["impacto_fin"] == "2025-02-06"
    for a, b in zip(g, g[1:]):
        assert b["estudio_ini"] > a["estudio_ini"]  # avanza
        assert b["impacto_fin"] <= "2025-03-15"
    # ventana con impacto después del límite se descarta
    assert g[-1]["impacto_fin"] <= "2025-03-15"


def test_generar_grid_sin_ventanas():
    g = scorecard.generar_grid(30, 7, 10, date(2025, 3, 1), date(2025, 3, 15))
    assert g == []


def test_evaluar_gates_todo_verde():
    fila = {
        "p_valor": 0.01, "n_efectivo": 5, "persistencia": 66.7,
        "ratio_replicacion": 0.8, "dsr": 0.97,
        "pct_gana_segmento": 85.0, "kill_switch": False,
        "ev_historico": 12.0, "supera_capacidad": False,
    }
    g = {
        "alpha": 0.05, "min_n_efectivo": 3, "min_persistencia": 50.0,
        "min_replicacion": 0.5, "min_dsr": 0.95,
        "min_pct_gana_segmento": 60.0, "min_ev_historico": 0.0,
    }
    ev = scorecard.evaluar_gates(fila, g)
    assert ev["valida_final"] is True
    assert ev["n1_completo"] is True and ev["n2"] is True


def test_evaluar_gates_p_valor_alto():
    fila = {
        "p_valor": 0.9, "n_efectivo": 5, "persistencia": None,
        "ratio_replicacion": 0.8, "dsr": 0.97,
        "pct_gana_segmento": 85.0, "kill_switch": False,
        "ev_historico": 12.0, "supera_capacidad": False,
    }
    g = {
        "alpha": 0.05, "min_n_efectivo": 3, "min_persistencia": 50.0,
        "min_replicacion": 0.5, "min_dsr": 0.95,
        "min_pct_gana_segmento": 60.0, "min_ev_historico": 0.0,
    }
    ev = scorecard.evaluar_gates(fila, g)
    assert ev["gates"]["V1_bootstrap"] is False
    assert ev["valida_cheap"] is False and ev["valida_final"] is False


def test_evaluar_gates_holdout_none_no_bloquea_cheap():
    fila = {
        "p_valor": 0.01, "n_efectivo": 5, "persistencia": None,
        "ratio_replicacion": 0.8, "dsr": 0.97,
        "pct_gana_segmento": 85.0, "kill_switch": False,
        "ev_historico": 12.0, "supera_capacidad": False,
    }
    g = {
        "alpha": 0.05, "min_n_efectivo": 3, "min_persistencia": 50.0,
        "min_replicacion": 0.5, "min_dsr": 0.95,
        "min_pct_gana_segmento": 60.0, "min_ev_historico": 0.0,
    }
    ev = scorecard.evaluar_gates(fila, g)
    assert ev["valida_cheap"] is True   # V3 no evaluada no bloquea el scan
    assert ev["gates"]["V3_holdout"] is True


def test_evaluar_gates_ev_negativo():
    fila = {
        "p_valor": 0.01, "n_efectivo": 5, "persistencia": 60.0,
        "ratio_replicacion": 0.8, "dsr": 0.97,
        "pct_gana_segmento": 85.0, "kill_switch": False,
        "ev_historico": -5.0, "supera_capacidad": False,
    }
    g = {
        "alpha": 0.05, "min_n_efectivo": 3, "min_persistencia": 50.0,
        "min_replicacion": 0.5, "min_dsr": 0.95,
        "min_pct_gana_segmento": 60.0, "min_ev_historico": 0.0,
    }
    ev = scorecard.evaluar_gates(fila, g)
    assert ev["gates"]["E3_ev_historico"] is False
    assert ev["valida_final"] is False


def _agentedia_maestro_perfecto() -> dict[str, dict]:
    """Dos maestros idénticos con cobertura 0 / exposición 100 (perfil clonable)."""
    agentedia = {}
    for dia, bolsa in [(date(2026, 1, 1), 300.0), (date(2026, 1, 2), 300.0)]:
        ad = {
            "codigo": "EXP", "dia": dia,
            "dema_kwh": 100_000.0, "dema_reg_kwh": 0.0, "dema_noreg_kwh": 100_000.0,
            "comp_cont_kwh": 0.0, "comp_cont_reg_kwh": 0.0, "vent_cont_kwh": 0.0,
            "comp_bolsa_kwh": 100_000.0, "vent_bolsa_kwh": 0.0, "comp_sicep_kwh": 0.0,
            "prec_cont": 300.0, "prec_bolsa": bolsa, "prec_escasez": 400.0,
        }
        ad["features"] = diario.features_diarias(ad)
        agentedia[diario.clave("EXP", dia)] = ad
    return agentedia


def test_fidelidad_mae_clon_perfecto():
    ad = _agentedia_maestro_perfecto()
    etiquetas = sorted(ad)
    labels = np.array([0] * len(etiquetas))
    perfiles = {0: PerfilEstrategia(0, ESTRATEGIA, 2, 1, {}, {"PEQUEÑO": 2})}
    politica = clonacion.construir_politica(
        ad, etiquetas, labels, perfiles, {"EXP"}, "PEQUEÑO", ESTRATEGIA, {"EXP": "PEQUEÑO"}, BINS
    )
    # el maestro juega exactamente el perfil que la política clona → MAE ≈ 0
    f = scorecard.fidelidad_mae(ad, politica, {"EXP"}, {"EXP": "PEQUEÑO"}, "PEQUEÑO")
    assert f["promedio"] == 0.0
    assert f["pct_cobertura"] == 0.0
    assert f["pct_exposicion"] == 0.0


def test_fidelidad_mae_sin_maestros():
    ad = _agentedia_maestro_perfecto()
    etiquetas = sorted(ad)
    labels = np.array([0] * len(etiquetas))
    perfiles = {0: PerfilEstrategia(0, ESTRATEGIA, 2, 1, {}, {"PEQUEÑO": 2})}
    politica = clonacion.construir_politica(
        ad, etiquetas, labels, perfiles, {"EXP"}, "PEQUEÑO", ESTRATEGIA, {"EXP": "PEQUEÑO"}, BINS
    )
    f = scorecard.fidelidad_mae(ad, politica, {"OTRO"})
    assert f["promedio"] is None