"""Pruebas unitarias del estudio híbrido diario (lógica pura, sin BD)."""
from __future__ import annotations

from datetime import date

import numpy as np

from app.services import clustering, diario

PARAMS = {
    "pv_tarifa_cop_kwh": 350.0,
    "cargo_regulado_cop_kwh": 76.1,
    "factor_cobertura": 0.25,
    "tasa_costo_anual": 0.02,
    "incobrables_pct": 0.02,
    "impuesto_pct": 0.33,
}

FEATURES = ["log_dema", "pct_noreg", "pct_cobertura", "pct_exposicion", "pct_sicep", "tiene_sicep"]


def _filas_toy() -> list[dict]:
    """Dos agentes: REG (contratista regulado) y EXP (expuesto a bolsa), 3 días."""
    filas = []
    for dia in (date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)):
        filas.append({
            "agente": "REG", "dia": dia,
            "dema_kwh": 1_000_000.0, "dema_reg_kwh": 1_000_000.0, "dema_noreg_kwh": 0.0,
            "comp_cont_kwh": 900_000.0, "comp_cont_reg_kwh": 900_000.0,
            "vent_cont_kwh": 0.0, "comp_bolsa_kwh": 100_000.0, "vent_bolsa_kwh": 0.0,
            "comp_sicep_kwh": 810_000.0,
            "prec_cont_cop_kwh": 300.0, "prec_bolsa_cop_kwh": 350.0, "prec_escasez_cop_kwh": 400.0,
        })
        filas.append({
            "agente": "EXP", "dia": dia,
            "dema_kwh": 100_000.0, "dema_reg_kwh": 0.0, "dema_noreg_kwh": 100_000.0,
            "comp_cont_kwh": 0.0, "comp_cont_reg_kwh": 0.0,
            "vent_cont_kwh": 0.0, "comp_bolsa_kwh": 100_000.0, "vent_bolsa_kwh": 0.0,
            "comp_sicep_kwh": 0.0,
            "prec_cont_cop_kwh": 300.0, "prec_bolsa_cop_kwh": 350.0, "prec_escasez_cop_kwh": 400.0,
        })
    return filas


def _agentedia_toy() -> dict[str, dict]:
    agentedia = diario.construir_agente_dia(_filas_toy())
    for ad in agentedia.values():
        ad["features"] = diario.features_diarias(ad)
        ad["desempeno"] = diario.desempeno_diario(ad, PARAMS)
    return agentedia


def test_construir_agente_dia():
    agentedia = diario.construir_agente_dia(_filas_toy())
    assert len(agentedia) == 6
    k = diario.clave("REG", date(2026, 1, 1))
    assert agentedia[k]["comp_cont_kwh"] == 900_000.0
    assert agentedia[k]["prec_cont"] == 300.0


def test_features_diarias():
    ad = {
        "dema_kwh": 1_000_000.0, "dema_reg_kwh": 600_000.0, "dema_noreg_kwh": 400_000.0,
        "comp_cont_kwh": 900_000.0, "comp_cont_reg_kwh": 500_000.0,
        "comp_bolsa_kwh": 100_000.0, "comp_sicep_kwh": 250_000.0,
    }
    f = diario.features_diarias(ad)
    assert f["pct_noreg"] == 40.0
    assert f["pct_cobertura"] == 90.0
    assert f["pct_exposicion"] == 10.0
    assert f["pct_sicep"] == 50.0
    assert f["tiene_sicep"] == 1.0
    assert abs(f["log_dema"] - np.log1p(1.0)) < 1e-4


def test_features_diarias_sin_regulado():
    f = diario.features_diarias({"dema_kwh": 100.0, "dema_reg_kwh": 0.0, "dema_noreg_kwh": 100.0,
                                 "comp_cont_kwh": 0.0, "comp_cont_reg_kwh": 0.0,
                                 "comp_bolsa_kwh": 100.0, "comp_sicep_kwh": 0.0})
    assert f["pct_sicep"] == 0.0 and f["tiene_sicep"] == 0.0 and f["pct_noreg"] == 100.0


def test_desempeno_diario_formula():
    ad = {
        "dema_kwh": 1_000.0, "comp_cont_kwh": 1_000.0, "vent_cont_kwh": 0.0,
        "comp_bolsa_kwh": 0.0, "vent_bolsa_kwh": 0.0,
        "prec_cont": 300.0, "prec_bolsa": 350.0,
    }
    d = diario.desempeno_diario(ad, PARAMS)
    # egreso = 1000*300; ingreso = 1000*350; cargos = 1000*76.1; bruta negativa
    egreso = 300_000.0
    ingreso = 350_000.0
    cargos = 76_100.0
    bruta = ingreso - egreso - cargos
    garantia = 300_000.0 * 0.25
    costo_garantia = garantia * (0.02 / 12)
    provision = ingreso * 0.02
    utilidad = bruta - max(0.0, bruta * 0.33) - costo_garantia - provision
    assert d["margen_por_kwh_cop"] == round(utilidad / 1000.0, 2)
    assert d["costo_energia_cop_kwh"] == 300.0


def test_matriz_diaria_forma_y_orden():
    agentedia = _agentedia_toy()
    X, etiquetas, nombres = diario.construir_matriz_diaria(agentedia, FEATURES)
    assert X.shape == (6, 6)
    assert etiquetas == sorted(etiquetas)
    assert nombres == FEATURES
    # el log_dema del agente EXP (0.1 GWh) es menor que el de REG (1 GWh)
    def _log(codigo, dia):
        return np.log1p(diario.construir_agente_dia(_filas_toy())[diario.clave(codigo, dia)]["dema_kwh"] / 1e6)
    idx_reg = etiquetas.index(diario.clave("REG", date(2026, 1, 1)))
    idx_exp = etiquetas.index(diario.clave("EXP", date(2026, 1, 1)))
    assert X[idx_reg, 0] == _log("REG", date(2026, 1, 1))
    assert X[idx_reg, 0] > X[idx_exp, 0]


def test_elegir_k_diario_submuestra():
    X, etiquetas, _ = diario.construir_matriz_diaria(_agentedia_toy(), FEATURES)
    Xs, _ = clustering.escalar(X, "standard")
    resultados = diario.elegir_k_diario(Xs, 2, 4, semilla=42, submuestra=5)
    # con submuestra de 5 filas, k solo llega a X.shape[0]-1 = 4
    assert [r["k"] for r in resultados] == [2, 3, 4]
    assert clustering.mejor_k(resultados) == 2


def test_kmeans_pooled_separa_y_reproducible():
    agentedia = _agentedia_toy()
    X, etiquetas, _ = diario.construir_matriz_diaria(agentedia, FEATURES)
    Xs, _ = clustering.escalar(X, "standard")
    labels, _ = clustering.aplicar_kmeans(Xs, 2, semilla=42)
    l2, _ = clustering.aplicar_kmeans(Xs, 2, semilla=42)
    assert list(labels) == list(l2)
    # REG y EXP caen en clústeres distintos
    reg_ids = {labels[etiquetas.index(diario.clave("REG", dia))] for dia in (date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3))}
    exp_ids = {labels[etiquetas.index(diario.clave("EXP", dia))] for dia in (date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3))}
    assert len(reg_ids) == 1 and len(exp_ids) == 1 and reg_ids != exp_ids


def test_ranking_diario_ordena_por_margen():
    agentedia = _agentedia_toy()
    etiquetas = sorted(agentedia)
    labels = np.array([0 if agentedia[k]["codigo"] == "REG" else 1 for k in etiquetas])
    ranking = diario.ranking_diario(agentedia, etiquetas, labels)
    assert len(ranking) == 3
    for res in ranking.values():
        # REG (contratista) debe tener mayor margen que EXP (expuesto) en bolsa cara
        assert res[0]["mediana"] > res[1]["mediana"]
        assert res[0]["rango"] == 1 and res[1]["rango"] == 2


def test_balance_periodo_elige_la_mejor():
    agentedia = _agentedia_toy()
    etiquetas = sorted(agentedia)
    labels = np.array([0 if agentedia[k]["codigo"] == "REG" else 1 for k in etiquetas])
    ranking = diario.ranking_diario(agentedia, etiquetas, labels)
    segmentos = {"REG": "GRANDE", "EXP": "PEQUEÑO"}
    perfiles = diario.perfilar_estrategias(agentedia, etiquetas, labels, FEATURES, segmentos)
    balance = diario.balance_periodo(ranking, perfiles)
    assert balance[0].cluster_id == 0  # REG gana el período
    assert balance[0].dias_puesto1 == 3
    assert balance[1].cluster_id == 1
    assert perfiles[0].composicion_segmento.get("GRANDE") == 3


def test_matriz_puestos():
    ranking = {
        "2026-01-01": {0: {"rango": 1}, 1: {"rango": 2}},
        "2026-01-02": {0: {"rango": 1}, 1: {"rango": 2}},
    }
    mp = diario.matriz_puestos(ranking, 2)
    assert mp[0] == [2, 0] and mp[1] == [0, 2]


def test_features_diarias_techo_sicep():
    ad = {
        "dema_kwh": 1_000.0, "dema_reg_kwh": 1_000.0, "dema_noreg_kwh": 0.0,
        "comp_cont_kwh": 1_000.0, "comp_cont_reg_kwh": 10.0,
        "comp_bolsa_kwh": 0.0, "comp_sicep_kwh": 1_000.0,
    }
    f = diario.features_diarias(ad, clip_pct_sicep=100.0)
    assert f["pct_sicep"] == 100.0
    assert f["tiene_sicep"] == 1.0


def test_aplicar_clip_margen():
    agentedia = _agentedia_toy()
    margen_original = agentedia[diario.clave("REG", date(2026, 1, 1))]["desempeno"]["margen_por_kwh_cop"]
    diario.aplicar_clip_margen(agentedia, limite=10.0)
    assert agentedia[diario.clave("REG", date(2026, 1, 1))]["desempeno"]["margen_por_kwh_cop"] == -10.0
    assert agentedia[diario.clave("EXP", date(2026, 1, 1))]["desempeno"]["margen_por_kwh_cop"] == -10.0
    diario.aplicar_clip_margen(agentedia, limite=None)
    assert agentedia[diario.clave("REG", date(2026, 1, 1))]["desempeno"]["margen_por_kwh_cop"] == -10.0
    assert margen_original != -10.0


def test_separar_atipicos():
    from app.models.entities import BalanceEstrategia

    b1 = BalanceEstrategia(0, "A", dias=200, mediana_margen=-20.0, media_margen=-20.0,
                           dias_puesto1=50, pct_top3=90.0, rango_promedio=1.5, tendencia=0.0)
    b2 = BalanceEstrategia(1, "B", dias=2, mediana_margen=180.0, media_margen=180.0,
                           dias_puesto1=2, pct_top3=100.0, rango_promedio=1.0, tendencia=0.0)
    ranking, atipicos = diario.separar_atipicos([b1, b2], n_dias=212, min_dias_pct=20)
    assert ranking == [b1]
    assert atipicos == [b2]


def _filas_toy_segmentos() -> list[dict]:
    """3 agentes: REG y MID (GRANDE, margen distinto) + EXP (PEQUEÑO), 3 días."""
    filas = []
    for dia in (date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)):
        filas.append({
            "agente": "REG", "dia": dia,
            "dema_kwh": 1_000_000.0, "dema_reg_kwh": 1_000_000.0, "dema_noreg_kwh": 0.0,
            "comp_cont_kwh": 1_000_000.0, "comp_cont_reg_kwh": 1_000_000.0,
            "vent_cont_kwh": 0.0, "comp_bolsa_kwh": 0.0, "vent_bolsa_kwh": 0.0,
            "comp_sicep_kwh": 900_000.0,
            "prec_cont_cop_kwh": 300.0, "prec_bolsa_cop_kwh": 350.0, "prec_escasez_cop_kwh": 400.0,
        })
        filas.append({
            "agente": "MID", "dia": dia,
            "dema_kwh": 500_000.0, "dema_reg_kwh": 350_000.0, "dema_noreg_kwh": 150_000.0,
            "comp_cont_kwh": 350_000.0, "comp_cont_reg_kwh": 350_000.0,
            "vent_cont_kwh": 0.0, "comp_bolsa_kwh": 150_000.0, "vent_bolsa_kwh": 0.0,
            "comp_sicep_kwh": 315_000.0,
            "prec_cont_cop_kwh": 300.0, "prec_bolsa_cop_kwh": 350.0, "prec_escasez_cop_kwh": 400.0,
        })
        filas.append({
            "agente": "EXP", "dia": dia,
            "dema_kwh": 100_000.0, "dema_reg_kwh": 0.0, "dema_noreg_kwh": 100_000.0,
            "comp_cont_kwh": 0.0, "comp_cont_reg_kwh": 0.0,
            "vent_cont_kwh": 0.0, "comp_bolsa_kwh": 100_000.0, "vent_bolsa_kwh": 0.0,
            "comp_sicep_kwh": 0.0,
            "prec_cont_cop_kwh": 300.0, "prec_bolsa_cop_kwh": 350.0, "prec_escasez_cop_kwh": 400.0,
        })
    return filas


def _agentedia_toy_segmentos() -> dict[str, dict]:
    agentedia = diario.construir_agente_dia(_filas_toy_segmentos())
    for ad in agentedia.values():
        ad["features"] = diario.features_diarias(ad)
        ad["desempeno"] = diario.desempeno_diario(ad, PARAMS)
    return agentedia


def test_ranking_diario_por_segmento():
    agentedia = _agentedia_toy_segmentos()
    etiquetas = sorted(agentedia)
    labels = np.array([
        0 if agentedia[k]["codigo"] == "REG"
        else (2 if agentedia[k]["codigo"] == "MID" else 1)
        for k in etiquetas
    ])
    segmentos = {"REG": "GRANDE", "MID": "GRANDE", "EXP": "PEQUEÑO"}
    rps = diario.ranking_diario_por_segmento(agentedia, etiquetas, labels, segmentos)
    assert set(rps) == {"GRANDE", "PEQUEÑO"}
    for res in rps["GRANDE"].values():
        # REG (cobertura total) gana a MID (exposición parcial) en bolsa cara
        assert res[0]["rango"] == 1 and res[2]["rango"] == 2
        assert res[0]["mediana"] > res[2]["mediana"]
    for res in rps["PEQUEÑO"].values():
        assert res[1]["rango"] == 1


def test_balance_por_segmento():
    agentedia = _agentedia_toy_segmentos()
    etiquetas = sorted(agentedia)
    labels = np.array([
        0 if agentedia[k]["codigo"] == "REG"
        else (2 if agentedia[k]["codigo"] == "MID" else 1)
        for k in etiquetas
    ])
    segmentos = {"REG": "GRANDE", "MID": "GRANDE", "EXP": "PEQUEÑO"}
    rps = diario.ranking_diario_por_segmento(agentedia, etiquetas, labels, segmentos)
    perfiles = diario.perfilar_estrategias(agentedia, etiquetas, labels, FEATURES, segmentos)
    bps = diario.balance_por_segmento(rps, perfiles, n_dias=3, min_dias_pct=50)
    # min_dias_pct=50 sobre 3 días -> umbral 2; los clústeres con 3 días entran al ranking
    assert set(bps) == {"GRANDE", "PEQUEÑO"}
    assert bps["GRANDE"]["balance"][0].cluster_id == 0
    assert bps["GRANDE"]["atipicos"] == []
    assert bps["PEQUEÑO"]["balance"][0].cluster_id == 1


def test_estrategia_x_segmento():
    agentedia = _agentedia_toy_segmentos()
    etiquetas = sorted(agentedia)
    labels = np.array([
        0 if agentedia[k]["codigo"] == "REG"
        else (2 if agentedia[k]["codigo"] == "MID" else 1)
        for k in etiquetas
    ])
    segmentos = {"REG": "GRANDE", "MID": "GRANDE", "EXP": "PEQUEÑO"}
    rps = diario.ranking_diario_por_segmento(agentedia, etiquetas, labels, segmentos)
    perfiles = diario.perfilar_estrategias(agentedia, etiquetas, labels, FEATURES, segmentos)
    xs = diario.matriz_estrategia_x_segmento(rps, perfiles)
    assert xs[0]["GRANDE"]["dias"] == 3
    assert xs[2]["GRANDE"]["dias"] == 3
    assert xs[1]["PEQUEÑO"]["dias"] == 3
    # dentro de GRANDE, REG (clúster 0) tiene mayor margen que MID (clúster 2)
    assert xs[0]["GRANDE"]["mediana"] > xs[2]["GRANDE"]["mediana"]
    assert xs[1]["PEQUEÑO"]["mediana"] < xs[0]["GRANDE"]["mediana"]