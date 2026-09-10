"""Clustering no supervisado de agentes-día (K-Means, scikit-learn).

Lógica pura (sin acceso a BD): matriz de features, elección de k (silhouette),
k-means y etiquetado interpretativo de arquetipos. Es el núcleo del estudio
híbrido diario: `diario.construir_matriz_diaria` delega aquí la construcción
de la matriz pooled y el clustering.
"""
from __future__ import annotations

import math

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import RobustScaler, StandardScaler

TRANSFORMACIONES = {
    "log_dema": ("dema_gwh", lambda v: math.log1p(float(v or 0.0))),
}


def construir_matriz(
    agregados: dict[str, dict],
    features: list[str],
    clip_sobrecobertura: float | None = None,
    transformes: dict[str, tuple[str, object]] | None = None,
    clip_intensidad_pico: float | None = None,
) -> tuple[np.ndarray, list[str], list[str]]:
    """Arma la matriz X (n×p) a partir de los agregados por agente-día.

    Devuelve (X float64, etiquetas= claves 'codigo|dia' ordenadas, nombres de
    features). `transformes` mapea feature -> (clave raw, callable) para
    aplicar log1p u otras transformaciones sobre el valor crudo (los perfiles
    siguen usando la clave raw en escala original). `clip_*` winsoriza extremos.
    """
    codigos = sorted(agregados)
    etiquetas = list(codigos)
    nombres = list(features)
    transformes = transformes or {}
    filas: list[list[float]] = []
    for cod in codigos:
        r = agregados[cod]
        fila: list[float] = []
        for f in features:
            if f in TRANSFORMACIONES:
                clave, fun = TRANSFORMACIONES[f]
                val = fun(r.get(clave, 0.0))
            elif f in transformes:
                clave, fun = transformes[f]
                val = float(fun(float(r.get(clave, 0.0) or 0.0)))
            else:
                val = float(r.get(f, 0.0) or 0.0)
            if f == "pct_cobertura" and clip_sobrecobertura is not None:
                val = min(val, clip_sobrecobertura)
            if f == "intensidad_pico" and clip_intensidad_pico is not None:
                val = max(-clip_intensidad_pico, min(clip_intensidad_pico, val))
            fila.append(val)
        filas.append(fila)
    X = np.asarray(filas, dtype=np.float64)
    return X, etiquetas, nombres


def escalar(X: np.ndarray, metodo: str = "standard") -> tuple[np.ndarray, object]:
    """Estandariza X para k-means. Devuelve (X_scaled, scaler ajustado)."""
    scaler = StandardScaler() if metodo == "standard" else RobustScaler()
    return scaler.fit_transform(X), scaler


def elegir_k(
    X: np.ndarray,
    k_min: int = 2,
    k_max: int = 10,
    semilla: int = 42,
) -> list[dict]:
    """Silhouette medio e inercia para cada k en [k_min, k_max]."""
    resultados: list[dict] = []
    for k in range(k_min, k_max + 1):
        if k >= X.shape[0]:
            break
        model = KMeans(n_clusters=k, n_init=10, random_state=semilla, max_iter=300)
        labels = model.fit_predict(X)
        sil = silhouette_score(X, labels) if k >= 2 and k < X.shape[0] else float("nan")
        resultados.append({"k": k, "silhouette": round(float(sil), 4), "inercia": round(float(model.inertia_), 1)})
    return resultados


def mejor_k(resultados: list[dict]) -> int:
    """k con mayor silhouette medio; si no hay, el mayor k reportado."""
    if not resultados:
        raise ValueError("Sin resultados de elección de k")
    return max(resultados, key=lambda r: (r["silhouette"] if not math.isnan(r["silhouette"]) else -1.0))["k"]


def aplicar_kmeans(
    X: np.ndarray,
    k: int,
    semilla: int = 42,
    n_init: int = 10,
) -> tuple[np.ndarray, KMeans]:
    """Ajusta KMeans sobre X (escalada). Devuelve (labels, modelo)."""
    model = KMeans(n_clusters=k, n_init=n_init, random_state=semilla, max_iter=300)
    labels = model.fit_predict(X)
    return labels, model


def nombrar_arquetipo(medias: dict) -> str:
    """Etiqueta interpretativa (post-hoc) de un clúster a partir de sus medias.

    El nombre emerge de los datos (no de reglas previas por agente); se revisa
    y ajusta en el informe según los perfiles.
    """
    noreg = medias.get("pct_noreg", 0.0)
    cob = medias.get("pct_cobertura", 0.0)
    expo = medias.get("pct_exposicion", 0.0)
    sicep = medias.get("pct_sicep", 0.0)
    perd = medias.get("pct_perdidas", 0.0)
    if noreg >= 85:
        return "Trader no regulado"
    if cob >= 120 and noreg >= 40:
        return "Trader con sobrecobertura de contratos"
    if expo >= 60 and cob < 50:
        return "Trader expuesto a bolsa (sin cobertura)"
    if noreg <= 30 and expo < 15 and sicep >= 50:
        return "Integrado/regional regulado"
    if noreg <= 30:
        return "Comercializador regulado"
    if perd >= 5:
        return "Comercializador mixto con red"
    if sicep >= 50:
        return "Comercializador mixto con convocatoria"
    return "Comercializador mixto"