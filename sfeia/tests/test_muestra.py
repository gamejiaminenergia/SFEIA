"""Pruebas unitarias de la selección de muestra no supervisada (sin BD)."""
from __future__ import annotations

import numpy as np

from sfeia.app.controllers.fase_segmentacion import _poblacion_completa
from sfeia.app.models.entities import AgenteSegmentado, Segmento
from sfeia.app.services import clustering


def _poblacion() -> list[AgenteSegmentado]:
    return [
        AgenteSegmentado("AAA", "A", 5000.0, 70.0, 30.0, Segmento.GRANDE),
        AgenteSegmentado("BBB", "B", 800.0, 90.0, 10.0, Segmento.MEDIANO),
        AgenteSegmentado("CCC", "C", 30.0, 0.0, 100.0, Segmento.PEQUEÑO),
        AgenteSegmentado("DDD", "D", 2000.0, 60.0, 40.0, Segmento.GRANDE),
    ]


def test_poblacion_completa_agrupa_todos():
    out = _poblacion_completa(_poblacion())
    assert sum(len(v) for v in out.values()) == 4
    assert set(out["GRANDE"]) == {"AAA", "DDD"}
    assert out["MEDIANO"] == ["BBB"]
    assert out["PEQUEÑO"] == ["CCC"]


def _toy_clusters():
    """6 agentes en 2 blobs bien separados por pct_noreg."""
    agregados = {
        "R1": {"dema_gwh": 1000.0, "pct_noreg": 5.0, "pct_cobertura": 90.0, "pct_exposicion": 8.0,
               "pct_sicep": 85.0, "tiene_sicep": 1.0},
        "R2": {"dema_gwh": 500.0, "pct_noreg": 8.0, "pct_cobertura": 88.0, "pct_exposicion": 10.0,
               "pct_sicep": 90.0, "tiene_sicep": 1.0},
        "R3": {"dema_gwh": 300.0, "pct_noreg": 12.0, "pct_cobertura": 92.0, "pct_exposicion": 6.0,
               "pct_sicep": 80.0, "tiene_sicep": 1.0},
        "T1": {"dema_gwh": 80.0, "pct_noreg": 95.0, "pct_cobertura": 40.0, "pct_exposicion": 45.0,
               "pct_sicep": 0.0, "tiene_sicep": 0.0},
        "T2": {"dema_gwh": 40.0, "pct_noreg": 100.0, "pct_cobertura": 30.0, "pct_exposicion": 55.0,
               "pct_sicep": 0.0, "tiene_sicep": 0.0},
        "T3": {"dema_gwh": 15.0, "pct_noreg": 90.0, "pct_cobertura": 50.0, "pct_exposicion": 40.0,
               "pct_sicep": 0.0, "tiene_sicep": 0.0},
    }
    features = ["log_dema", "pct_noreg", "pct_cobertura", "pct_exposicion", "pct_sicep", "tiene_sicep"]
    X, etiquetas, _ = clustering.construir_matriz(agregados, features)
    Xs, _ = clustering.escalar(X, "standard")
    labels, modelo = clustering.aplicar_kmeans(Xs, 2, semilla=42)
    return etiquetas, labels, Xs, modelo, agregados, features


def test_seleccionar_representantes_medoide_y_extremos():
    etiquetas, labels, Xs, modelo, agregados, features = _toy_clusters()
    reps = clustering.seleccionar_representantes(
        etiquetas, labels, Xs, modelo, agregados, features,
        representantes_por_cluster=3, extremos_por_feature=1,
    )
    assert set(reps) == {0, 1}
    for cid, r in reps.items():
        miembros = [etiquetas[i] for i in range(len(labels)) if int(labels[i]) == cid]
        assert r["medoide"] in miembros
        assert all(e in miembros for e in r["extremos"])
        assert 1 + len(r["extremos"]) <= 3
    # Los dos blobs separados: el medoide de un clúster es un "R" y del otro un "T"
    medoides = {r["medoide"] for r in reps.values()}
    assert any(m.startswith("R") for m in medoides)
    assert any(m.startswith("T") for m in medoides)


def test_seleccionar_representantes_respeta_tope():
    etiquetas, labels, Xs, modelo, agregados, features = _toy_clusters()
    reps = clustering.seleccionar_representantes(
        etiquetas, labels, Xs, modelo, agregados, features,
        representantes_por_cluster=2, extremos_por_feature=1,
    )
    for cid, r in reps.items():
        assert 1 + len(r["extremos"]) <= 2