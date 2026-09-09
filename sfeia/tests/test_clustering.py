"""Pruebas unitarias del clustering (lógica pura, sin BD)."""
from __future__ import annotations

import numpy as np

from sfeia.app.services import clustering


def _dos_blobs() -> tuple[np.ndarray, list[str]]:
    """6 agentes en 2 blobs bien separados por pct_noreg y tamaño."""
    agregados = {
        "AAA": {"dema_gwh": 3000.0, "pct_noreg": 5.0, "pct_cobertura": 90.0,
                "pct_exposicion": 8.0, "pct_sicep": 85.0, "tiene_sicep": 1.0,
                "pct_perdidas": 6.0, "intensidad_pico": 2.0},
        "BBB": {"dema_gwh": 1200.0, "pct_noreg": 8.0, "pct_cobertura": 88.0,
                "pct_exposicion": 10.0, "pct_sicep": 90.0, "tiene_sicep": 1.0,
                "pct_perdidas": 5.0, "intensidad_pico": 1.0},
        "CCC": {"dema_gwh": 600.0, "pct_noreg": 12.0, "pct_cobertura": 92.0,
                "pct_exposicion": 6.0, "pct_sicep": 80.0, "tiene_sicep": 1.0,
                "pct_perdidas": 7.0, "intensidad_pico": 3.0},
        "DDD": {"dema_gwh": 80.0, "pct_noreg": 95.0, "pct_cobertura": 40.0,
                "pct_exposicion": 45.0, "pct_sicep": 0.0, "tiene_sicep": 0.0,
                "pct_perdidas": 0.0, "intensidad_pico": -12.0},
        "EEE": {"dema_gwh": 40.0, "pct_noreg": 100.0, "pct_cobertura": 30.0,
                "pct_exposicion": 55.0, "pct_sicep": 0.0, "tiene_sicep": 0.0,
                "pct_perdidas": 0.0, "intensidad_pico": -15.0},
        "FFF": {"dema_gwh": 15.0, "pct_noreg": 90.0, "pct_cobertura": 50.0,
                "pct_exposicion": 40.0, "pct_sicep": 0.0, "tiene_sicep": 0.0,
                "pct_perdidas": 0.0, "intensidad_pico": -10.0},
    }
    features = ["log_dema", "pct_noreg", "pct_cobertura", "pct_exposicion",
                "pct_sicep", "tiene_sicep", "pct_perdidas", "intensidad_pico"]
    X, etiquetas, _ = clustering.construir_matriz(agregados, features)
    return X, etiquetas


def test_construir_matriz_forma_y_log():
    X, etiquetas = _dos_blobs()
    assert X.shape == (6, 8)
    assert etiquetas == sorted(etiquetas)
    # log_dema: log1p(3000) < log1p... valores positivos y crecientes con tamaño
    assert X[0, 0] == np.log1p(3000.0)


def test_construir_matriz_clip_sobrecobertura():
    agregados = {"A": {"pct_cobertura": 500.0, "pct_noreg": 0.0, "dema_gwh": 1.0}}
    X, _, _ = clustering.construir_matriz(agregados, ["log_dema", "pct_cobertura", "pct_noreg"], clip_sobrecobertura=300)
    assert X[0, 1] == 300.0


def test_elegir_k_y_mejor_k_separa_blobs():
    X, _ = _dos_blobs()
    Xs, _ = clustering.escalar(X, "standard")
    resultados = clustering.elegir_k(Xs, 2, 4, semilla=42)
    assert [r["k"] for r in resultados] == [2, 3, 4]
    assert clustering.mejor_k(resultados) == 2


def test_aplicar_kmeans_reproducible():
    X, _ = _dos_blobs()
    Xs, _ = clustering.escalar(X, "standard")
    l1, _ = clustering.aplicar_kmeans(Xs, 2, semilla=42)
    l2, _ = clustering.aplicar_kmeans(Xs, 2, semilla=42)
    assert list(l1) == list(l2)
    # Los blobs se separan: los 3 regulados en un clúster y los 3 traders en otro
    assert set(l1[:3]) == {l1[0]} and set(l1[3:]) == {l1[3]} and l1[0] != l1[3]


def test_perfilar_clusters_medias():
    X, etiquetas = _dos_blobs()
    Xs, _ = clustering.escalar(X, "standard")
    labels, _ = clustering.aplicar_kmeans(Xs, 2, semilla=42)
    segmentos = {"AAA": "GRANDE", "BBB": "MEDIANO", "CCC": "MEDIANO",
                 "DDD": "PEQUEÑO", "EEE": "PEQUEÑO", "FFF": "PEQUEÑO"}
    perfiles = clustering.perfilar_clusters(
        {c: {"dema_gwh": d} for c, d in zip(
            etiquetas, [3000.0, 1200.0, 600.0, 80.0, 40.0, 15.0])},
        etiquetas, labels, ["dema_gwh"], segmentos,
    )
    # El clúster de los traders (DDD/EEE/FFF) debe tener media de dema < clúster regulado
    medias = {cid: p.medias["dema_gwh"] for cid, p in perfiles.items()}
    trader = max(medias, key=medias.get)
    regulado = min(medias, key=medias.get)
    assert medias[trader] > medias[regulado]
    # composición: clúster con los 3 PEQUEÑO
    assert any(p.composicion_segmento.get("PEQUEÑO") == 3 for p in perfiles.values())


def test_ari_idéntico_es_1():
    from sklearn.metrics import adjusted_rand_score

    assert adjusted_rand_score([0, 0, 1, 1], [1, 1, 0, 0]) == 1.0


def test_ari_aleatorio_cercano_a_0():
    from sklearn.metrics import adjusted_rand_score

    rng = np.random.default_rng(7)
    a = [0] * 50 + [1] * 50
    b = list(rng.permutation(a))
    assert abs(adjusted_rand_score(a, b)) < 0.1


def test_nombrar_arquetipo():
    assert clustering.nombrar_arquetipo({"pct_noreg": 98.0, "pct_cobertura": 30.0,
                                         "pct_exposicion": 50.0, "pct_sicep": 0.0,
                                         "pct_perdidas": 0.0}) == "Trader no regulado"
    assert clustering.nombrar_arquetipo({"pct_noreg": 50.0, "pct_cobertura": 250.0,
                                         "pct_exposicion": 10.0, "pct_sicep": 0.0,
                                         "pct_perdidas": 0.0}) == "Trader con sobrecobertura de contratos"
    assert clustering.nombrar_arquetipo({"pct_noreg": 10.0, "pct_cobertura": 90.0,
                                         "pct_exposicion": 8.0, "pct_sicep": 90.0,
                                         "pct_perdidas": 6.0}) == "Integrado/regional regulado"
    assert clustering.nombrar_arquetipo({"pct_noreg": 0.0, "pct_cobertura": 0.0,
                                         "pct_exposicion": 95.0, "pct_sicep": 0.0,
                                         "pct_perdidas": 0.0}) == "Trader expuesto a bolsa (sin cobertura)"