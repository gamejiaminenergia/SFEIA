"""Pruebas unitarias del scorecard de aceptación (lógica pura, sin BD)."""
from __future__ import annotations

from datetime import date

import numpy as np

from sfeia.app.models.entities import PerfilEstrategia
from sfeia.app.services import clonacion, diario, maestros, scorecard

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


# --------------------------------------------------------- Ruta A: arquetipo
def _agentedia_dos_arquetipos() -> tuple[dict[str, dict], list[str], np.ndarray, dict]:
    """Dos arquetipos en PEQUEÑO: 'REG' (margen alto, ganador) y 'TRAD' (margen bajo)."""
    agentedia = {}
    for dia, bolsa in [(date(2026, 1, 1), 300.0), (date(2026, 1, 2), 310.0)]:
        for codigo, margen in [("REG", 100.0), ("TRAD", 0.0)]:
            if codigo == "REG":
                ad = {
                    "codigo": "REG", "dia": dia,
                    "dema_kwh": 100_000.0, "dema_reg_kwh": 100_000.0, "dema_noreg_kwh": 0.0,
                    "comp_cont_kwh": 90_000.0, "comp_cont_reg_kwh": 90_000.0, "vent_cont_kwh": 0.0,
                    "comp_bolsa_kwh": 10_000.0, "vent_bolsa_kwh": 0.0, "comp_sicep_kwh": 50_000.0,
                    "prec_cont": 350.0, "prec_bolsa": bolsa, "prec_escasez": 700.0,
                }
            else:
                ad = {
                    "codigo": "TRAD", "dia": dia,
                    "dema_kwh": 100_000.0, "dema_reg_kwh": 0.0, "dema_noreg_kwh": 100_000.0,
                    "comp_cont_kwh": 0.0, "comp_cont_reg_kwh": 0.0, "vent_cont_kwh": 0.0,
                    "comp_bolsa_kwh": 100_000.0, "vent_bolsa_kwh": 0.0, "comp_sicep_kwh": 0.0,
                    "prec_cont": 350.0, "prec_bolsa": bolsa, "prec_escasez": 700.0,
                }
            ad["features"] = diario.features_diarias(ad)
            r = diario.desempeno_diario(ad, {k: v for k, v in [
                ("pv_tarifa_cop_kwh", 350.0), ("cargo_regulado_cop_kwh", 76.1),
                ("factor_cobertura", 0.25), ("tasa_costo_anual", 0.02),
                ("incobrables_pct", 0.02), ("impuesto_pct", 0.33)]})
            ad["desempeno"] = {"margen_por_kwh_cop": margen}
            agentedia[diario.clave(codigo, dia)] = ad
    etiquetas = sorted(agentedia)
    labels = np.array([0 if agentedia[k]["codigo"] == "REG" else 1 for k in etiquetas])
    perfiles = {
        0: PerfilEstrategia(0, "Comercializador regulado", 2, 1, {}, {"PEQUEÑO": 2}),
        1: PerfilEstrategia(1, "Trader expuesto a bolsa (sin cobertura)", 2, 1, {}, {"PEQUEÑO": 2}),
    }
    return agentedia, etiquetas, labels, perfiles


def test_arquetipos_ganadores_por_bin():
    agentedia, etiquetas, labels, perfiles = _agentedia_dos_arquetipos()
    seg = {"REG": "PEQUEÑO", "TRAD": "PEQUEÑO"}
    ganadores, fallback = maestros.arquetipos_ganadores_por_bin(
        agentedia, etiquetas, labels, perfiles, "PEQUEÑO", seg, BINS
    )
    # spread = bolsa - contrato ≈ 300-350 = -50 → 'muy_barata'
    assert ganadores["muy_barata"] == 0  # REG (margen 100) gana el bin
    assert fallback == 0
    assert perfiles[ganadores["muy_barata"]].arquetipo == "Comercializador regulado"


def test_construir_politica_arquetipo():
    agentedia, etiquetas, labels, perfiles = _agentedia_dos_arquetipos()
    seg = {"REG": "PEQUEÑO", "TRAD": "PEQUEÑO"}
    pol = clonacion.construir_politica(
        agentedia, etiquetas, labels, perfiles, set(), "PEQUEÑO", "", seg, BINS, modo="arquetipo"
    )
    assert pol.modo == "arquetipo"
    assert "muy_barata" in pol.reglas
    assert pol.reglas["muy_barata"].perfil.pct_cobertura == 90.0  # perfil de REG
    assert pol.ganadores_arquetipo["muy_barata"] == "Comercializador regulado"
    assert pol.fallback is not None


def test_bootstrap_skill_luck_arquetipo():
    from sfeia.app.models.entities import AgenteDia

    # "Comercializador regulado" domina claramente al pool (mezcla de arquetipos)
    agentes = []
    for dia in ("2026-01-01", "2026-01-02", "2026-01-03"):
        agentes.append(AgenteDia("R1", "R1", dia, "PEQUEÑO", 0, "Comercializador regulado", {}, 100.0, 300.0))
        agentes.append(AgenteDia("R2", "R2", dia, "PEQUEÑO", 0, "Comercializador regulado", {}, 90.0, 300.0))
        for i in range(4):
            agentes.append(AgenteDia(f"T{i}", f"T{i}", dia, "PEQUEÑO", 1, "Trader expuesto a bolsa (sin cobertura)", {}, 0.0, 300.0))
    b = maestros.bootstrap_skill_luck(
        agentes, "PEQUEÑO", "x", top=1, n_dias_estudio=3, n_boot=300, semilla=7,
        min_dias_pct=0.0, relativo=False, nivel="arquetipo",
    )
    assert b["n_arquetipos"] == 2
    assert b["mejor_arquetipo"] == "Comercializador regulado"
    assert b["mejor_maestro_real"] == 100.0  # max del ranking, no el mínimo
    assert b["p_valor"] < 1.0  # hay ventaja real frente a la nula pooled


def test_bootstrap_skill_luck_arquetipo_sin_skill():
    from sfeia.app.models.entities import AgenteDia

    agentes = []
    for dia in ("2026-01-01", "2026-01-02", "2026-01-03"):
        for arq in ("Comercializador regulado", "Trader expuesto a bolsa (sin cobertura)"):
            agentes.append(AgenteDia("X", "X", dia, "PEQUEÑO", 0, arq, {}, 5.0, 300.0))
    b = maestros.bootstrap_skill_luck(
        agentes, "PEQUEÑO", "x", top=1, n_dias_estudio=3, n_boot=300, semilla=7,
        min_dias_pct=0.0, relativo=False, nivel="arquetipo",
    )
    assert b["mejor_maestro_real"] == 5.0
    assert b["p_valor"] == 1.0  # sin diferencia, indistinguible del azar


def test_persistencia_arquetipo():
    from sfeia.app.models.entities import AgenteDia

    agentes = []
    for dia in ("2026-02-01", "2026-02-02", "2026-02-03"):
        agentes.append(AgenteDia("R", "R", dia, "PEQUEÑO", 0, "Comercializador regulado", {}, 80.0, 300.0))
        agentes.append(AgenteDia("T", "T", dia, "PEQUEÑO", 1, "Trader expuesto a bolsa (sin cobertura)", {}, 10.0, 300.0))
    p = maestros.persistencia_arquetipo(agentes, "PEQUEÑO", "Comercializador regulado", 3, 0.0)
    assert p["n_arquetipos"] == 2
    assert p["persistencia"] == 100.0
    p2 = maestros.persistencia_arquetipo(agentes, "PEQUEÑO", "Trader expuesto a bolsa (sin cobertura)", 3, 0.0)
    assert p2["persistencia"] == 0.0