"""Pruebas unitarias de la recomendación semanal (lógica pura, sin BD).

Cubren: resolución del ancla (4.1), veredicto OPERAR/NO OPERAR (criterio
estricto), fila de gates desde el resultado del flujo, series del dashboard y
render determinista del HTML autocontenido (JSON embebido válido + escape).
"""
from __future__ import annotations

import json
from datetime import date, timedelta

from sfeia.app.controllers.fase_semanal import (
    GATES_DEFAULT,
    construir_series,
    fila_topn_desde_resultado,
    resolver_ancla,
    veredicto_semanal,
)
from sfeia.app.models.entities import MetricasDistribucion, PerfilAccion, ResumenImpacto, SimulacionDia
from sfeia.app.views.dashboard_semanal_html import render as render_html


def _gates_todos(ok: bool = True):
    g = {k: ok for k in GATE_INFO_KEYS}
    return {
        "gates": g,
        "n1_cheap": ok, "n1_completo": ok, "n2": ok,
        "valida_cheap": ok, "valida_final": ok,
    }


GATE_INFO_KEYS = [
    "V1_bootstrap", "V2_n_efectivo", "V3_holdout", "V4_replicacion", "V5_dsr",
    "E1_gana_segmento", "E2_sin_kill_switch", "E3_ev_historico", "E4_capacidad",
]


def _fila_pasa() -> dict:
    return {
        "segmento": "PEQUEÑO", "estrategia": "Comercializador regulado",
        "p_valor": 0.01, "n_efectivo": 4, "persistencia": 80.0,
        "ratio_replicacion": 0.8, "dsr": 0.97, "pct_gana_segmento": 70.0,
        "kill_switch": False, "ev_historico": 1.5, "supera_capacidad": False,
        "mediana_margen_absoluto": 12.3, "drawdown_max": 20.0,
    }


# ---------------------------------------------------------------- ancla (4.1)
def test_resolver_ancla_con_nulos():
    v = resolver_ancla({"foco_ini": None, "foco_fin": None,
                        "fin_c_familia": None, "fin_c15": None}, "2026-07-31")
    assert v["foco_fin"] == "2026-07-31"
    assert v["foco_ini"] == (date(2026, 7, 31) - timedelta(days=180)).isoformat()
    assert v["fin_c_familia"] == "2026-08-01"
    assert v["fin_c15"] == "2026-07-31"


def test_resolver_ancla_con_foco_ya_puesto():
    v = resolver_ancla({"foco_ini": "2025-01-01", "foco_fin": "2025-07-31",
                        "fin_c_familia": None, "fin_c15": None}, "2026-07-31")
    assert v["foco_fin"] == "2025-07-31"
    assert v["foco_ini"] == "2025-01-01"
    assert v["fin_c_familia"] == "2025-08-01"
    assert v["fin_c15"] == "2025-07-31"


# ---------------------------------------------------------------- veredicto
def test_veredicto_operar_topn():
    v = veredicto_semanal(_fila_pasa(), None, GATES_DEFAULT)
    assert v["operar"] is True
    assert v["veredicto"] == "OPERAR"
    assert v["por_topn"] is True
    assert "ventaja comprobada" in v["razon"]
    assert "Cómo operar" in v["razon"]


def test_veredicto_operar_arquetipo():
    fila_arq = {**_fila_pasa(), "estrategia": "Trader no regulado", "persistencia": None}
    v = veredicto_semanal(None, fila_arq, GATES_DEFAULT)
    assert v["operar"] is True
    assert v["por_arquetipo"] is True


def test_veredicto_no_operar():
    fila = _fila_pasa()
    fila.update({"p_valor": 0.6, "dsr": 0.5, "pct_gana_segmento": 20.0, "ev_historico": -1.0})
    v = veredicto_semanal(fila, None, GATES_DEFAULT)
    assert v["operar"] is False
    assert v["veredicto"] == "NO OPERAR"
    assert "azar" in v["razon"]
    assert "pierde dinero en expectativa" in v["razon"]
    assert "no operar" in v["razon"].lower()


def test_veredicto_sin_filas():
    v = veredicto_semanal(None, None, GATES_DEFAULT)
    assert v["operar"] is False


# ------------------------------------------------- fila de gates desde el flujo
def test_fila_topn_desde_resultado():
    res = ResumenImpacto(
        dias=7, demanda_kwh_dia=1e6, mediana_imitacion=8.5, media_imitacion=9.0,
        mediana_maestros=8.0, mediana_segmento=6.0,
        pct_dias_gana_segmento=71.4, pct_dias_gana_maestros=57.1,
        garantia_mediana_cop=5e6, garantia_max_cop=9e6,
    )
    dist = MetricasDistribucion(7, 8.5, 9.0, 2.0, 15.0, 14.3, 1.0, 16.0, 3.0)
    resultado = {
        "parametros": {"segmento": "PEQUEÑO", "estrategia": "Comercializador regulado"},
        "resumen": res,
        "distribuciones": {"imitacion": dist},
        "decision": {
            "kill_switch_activado": False,
            "e_margen_dia_historico": 1.2,
            "e_margen_dia_anio_nino": -0.3,
            "capacidad": {"supera_capacidad": False, "pct_del_segmento": 2.0},
        },
        "validez": {
            "n_efectivo_maestros": 3,
            "bootstrap": {"p_valor": 0.02},
            "holdout": {"pct_persistencia": 75.0},
            "replicacion_is_oos": {"ratio_replicacion": 0.9},
            "dsr": {"dsr": 0.98},
        },
        "maestros": [],
    }
    f = fila_topn_desde_resultado(resultado)
    assert f["p_valor"] == 0.02
    assert f["n_efectivo"] == 3
    assert f["persistencia"] == 75.0
    assert f["ratio_replicacion"] == 0.9
    assert f["dsr"] == 0.98
    assert f["pct_gana_segmento"] == 71.4
    assert f["kill_switch"] is False
    assert f["ev_historico"] == 1.2
    assert f["supera_capacidad"] is False
    assert f["mediana_margen_absoluto"] == 8.5
    assert f["p5"] == 2.0 and f["p95"] == 15.0


# ------------------------------------------------------------------ series
def _sim(dia: str, m: float, emb=None) -> SimulacionDia:
    perfil = PerfilAccion(60.0, 40.0, 30.0, 50.0, 1.0, 3)
    return SimulacionDia(
        fecha=dia, bin_spread="neutral", es_escasez=False, perfil=perfil,
        margen_imitacion=m, margen_maestros=m + 1.0, margen_segmento=m - 1.0,
        garantia_exigida_cop=1000.0, en_distribucion=True, nivel_embalses_pct=emb,
    )


def test_construir_series_con_sims():
    sims = [_sim("2026-07-25", 5.0, 55.0), _sim("2026-07-26", -3.0, 54.5), _sim("2026-07-27", 4.0, None)]
    s = construir_series(sims, {"2026-07-25": 100.0, "2026-07-26": 120.0, "2026-07-27": 90.0},
                         {"2026-07-25": 55.0, "2026-07-26": 54.5}, BINS_T, (0.0, 200.0))
    assert s["dias"] == ["2026-07-25", "2026-07-26", "2026-07-27"]
    assert s["margen_imitacion"] == [5.0, -3.0, 4.0]
    assert s["drawdown"] == [0.0, 3.0, 0.0]
    assert s["spread"] == [100.0, 120.0, 90.0]
    assert s["embalses"] == [55.0, 54.5, None]
    assert s["rango_spread"] == [0.0, 200.0]
    assert s["bins_spread"][0][0] == "muy_barata"


BINS_T = {"muy_barata": [-999999, 0], "barata": [0, 200], "neutral": [200, 999999]}


def test_construir_series_sin_sims():
    s = construir_series(None, {"2026-07-25": 10.0}, {"2026-07-25": 60.0}, BINS_T, None)
    assert s["dias"] == ["2026-07-25"]
    assert s["margen_imitacion"] == []
    assert s["spread"] == [10.0]
    assert s["embalses"] == [60.0]


# ------------------------------------------------------------------ payload
def _payload_minimo(veredicto: str = "OPERAR") -> dict:
    return {
        "tipo": "recomendacion_semanal",
        "generado": "2026-09-10",
        "ancla": "2026-07-31",
        "ventanas": {
            "estudio": {"ini": "2026-04-27", "fin": "2026-07-24"},
            "impacto": {"ini": "2026-07-25", "fin": "2026-07-31"},
        },
        "segmento": "PEQUEÑO",
        "estrategia": "Comercializador regulado",
        "top": 10,
        "veredicto": veredicto,
        "razon": "Razón de prueba.",
        "operar": veredicto == "OPERAR",
        "error_topn": None,
        "topn": _fila_pasa(),
        "arquetipo": None,
        "gates": {"topn": _gates_todos(True), "arquetipo": None},
        "umbrales": GATES_DEFAULT,
        "kpis": [
            {"id": "mediana_margen", "etiqueta": "Mediana margen imitación", "valor": 8.5,
             "unidad": "COP/kWh", "estado": "ok", "nota": "nota"},
            {"id": "dsr", "etiqueta": "DSR (corregido)", "valor": 0.97, "unidad": "",
             "estado": "ok", "nota": "nota"},
        ],
        "regimen": {
            "bin_actual": "neutral", "spread_ultimo": 150.0, "dias_escasez_impacto": 0,
            "n_dias_impacto": 7, "nivel_embalses_ultimo": 62.5, "tendencia_embalses": "estable",
            "pct_escasez_historico": 3.2,
        },
        "series": construir_series(
            [_sim("2026-07-25", 5.0, 62.0), _sim("2026-07-26", 4.0, 62.5)],
            {"2026-07-25": 150.0, "2026-07-26": 155.0},
            {"2026-07-25": 62.0, "2026-07-26": 62.5}, BINS_T, (100.0, 250.0),
        ),
        "perfil": {
            "recomendado": {"pct_cobertura": 60.0, "pct_exposicion": 40.0, "pct_noreg": 30.0,
                            "pct_sicep": 50.0, "tiene_sicep": 1.0, "n_dias": 2},
            "es_defensivo": False,
            "maestros_realizado": {"pct_cobertura": 65.0, "pct_exposicion": 35.0, "pct_noreg": 28.0,
                                   "pct_sicep": 55.0, "n_dias": 2},
            "arquetipo_ganador": None,
        },
        "maestros": [{
            "posicion": 1, "codigo": "EXP", "nombre": "<script>alert(1)</script> S.A.",
            "n_dias": 90, "mediana_margen": 10.0, "mediana_relativa": 4.0,
            "pct_dias_perdida": 5.0, "drawdown_max": 12.0,
        }],
        "alternativa": None,
        "historial_escasez": {
            "pct_dias_escasez": 3.2, "frecuencia_bins": {"neutral": 40.0},
            "spread_p50": 140.0, "spread_p95": 400.0, "spread_max": 700.0,
        },
        "advertencias": ["Advertencia 1"],
        "conclusiones": ["Conclusión 1"],
    }


# ----------------------------------------------------------- render del HTML
def test_render_html_estructura():
    html = render_html(_payload_minimo())
    assert html.startswith("<!DOCTYPE html>")
    assert "<html lang=\"es\">" in html
    assert "window.SEMANAL" in html
    assert "OPERAR" in html
    assert "g-margen" in html and "g-dist" in html
    assert "Recomendación semanal" in html


def test_render_html_escapa_nombres():
    html = render_html(_payload_minimo())
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_render_html_json_embebido_valido():
    html = render_html(_payload_minimo())
    marcador = "window.SEMANAL = "
    ini = html.index(marcador) + len(marcador)
    fin = html.index(";</script>", ini)
    datos = json.loads(html[ini:fin])
    assert datos["veredicto"] == "OPERAR"
    assert datos["series"]["dias"] == ["2026-07-25", "2026-07-26"]
    assert datos["series"]["rango_spread"] == [100.0, 250.0]


def test_render_html_determinista():
    p = _payload_minimo()
    assert render_html(p) == render_html(p)
