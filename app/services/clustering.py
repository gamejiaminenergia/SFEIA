"""Clustering no supervisado de comercializadores (K-Means, scikit-learn).

Lógica pura (sin acceso a BD): recibe agregados por agente + config y produce
matriz de features, elección de k (silhouette/inercia), k-means, perfiles de
clúster, arquetipos emergentes y contrapunto con la segmentación/tipificación
del estudio actual. El controlador (fase_clustering) es quien consulta la BD.
"""
from __future__ import annotations

import math

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import RobustScaler, StandardScaler

from app.models.entities import AgenteClusterizado, PerfilCluster
from app.services.tipificacion import tipificar

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
    """Arma la matriz X (n×p) a partir de los agregados por agente.

    Devuelve (X float64, etiquetas= códigos ordenados, nombres de features).
    `transformes` mapea feature -> (clave raw, callable) para aplicar log1p u
    otras transformaciones sobre el valor crudo (los perfiles siguen usando la
    clave raw en escala original). `clip_*` winsoriza valores extremos.
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


def _promedios(agregados: dict[str, dict], miembros: list[str], features: list[str], fun) -> dict:
    out: dict[str, float] = {}
    for f in features:
        vals = [float(agregados[c].get(f, 0.0) or 0.0) for c in miembros]
        out[f] = round(fun(vals), 2) if vals else 0.0
    return out


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


def perfilar_clusters(
    agregados: dict[str, dict],
    etiquetas: list[str],
    labels: np.ndarray,
    features: list[str],
    segmento_por_codigo: dict[str, str],
) -> dict[int, PerfilCluster]:
    """Perfiles de cada clúster en escala original + composición por segmento."""
    perfiles: dict[int, PerfilCluster] = {}
    for cid in sorted(set(int(x) for x in labels)):
        miembros = [etiquetas[i] for i in range(len(labels)) if int(labels[i]) == cid]
        medias = _promedios(agregados, miembros, features, lambda v: sum(v) / len(v))
        medianas = _promedios(agregados, miembros, features, lambda v: sorted(v)[len(v) // 2])
        composicion: dict[str, int] = {}
        for c in miembros:
            seg = segmento_por_codigo.get(c, "?")
            composicion[seg] = composicion.get(seg, 0) + 1
        perfiles[cid] = PerfilCluster(
            cluster_id=cid,
            n=len(miembros),
            miembros=sorted(miembros),
            medias=medias,
            medianas=medianas,
            composicion_segmento=composicion,
            arquetipo=nombrar_arquetipo(medias),
        )
    return perfiles


def construir_agente_clusterizado(
    agregados: dict[str, dict],
    etiquetas: list[str],
    labels: np.ndarray,
    segmento_por_codigo: dict[str, str],
    perfiles: dict[int, PerfilCluster],
    nombres: dict[str, str],
) -> list[AgenteClusterizado]:
    """Una fila por agente con su clúster, arquetipo y features en escala original."""
    filas: list[AgenteClusterizado] = []
    for i, cod in enumerate(etiquetas):
        cid = int(labels[i])
        filas.append(AgenteClusterizado(
            codigo=cod,
            nombre=nombres.get(cod, cod),
            segmento=segmento_por_codigo.get(cod, "?"),
            cluster_id=cid,
            arquetipo=perfiles[cid].arquetipo,
            features=dict(agregados[cod]),
        ))
    filas.sort(key=lambda f: (f.cluster_id, -f.features.get("dema_gwh", 0.0)))
    return filas


def comparar_con_segmento(
    etiquetas: list[str],
    labels: np.ndarray,
    segmento_por_codigo: dict[str, str],
) -> dict:
    """Tabla cruzada clúster×segmento + ARI (contrapunto con F-1)."""
    contigencia: dict[tuple[int, str], int] = {}
    for i, cod in enumerate(etiquetas):
        key = (int(labels[i]), segmento_por_codigo.get(cod, "?"))
        contigencia[key] = contigencia.get(key, 0) + 1
    segmentos = sorted(set(segmento_por_codigo.values()))
    clus = sorted({int(x) for x in labels})
    tabla = [[contigencia.get((c, s), 0) for s in segmentos] for c in clus]
    ari = adjusted_rand_score([int(x) for x in labels], [segmento_por_codigo.get(c, "?") for c in etiquetas])
    return {"tabla": tabla, "clusters": clus, "segmentos": segmentos, "ari": round(ari, 4)}


def comparar_con_tipificacion(
    etiquetas: list[str],
    labels: np.ndarray,
    agregados: dict[str, dict],
    segmento_por_codigo: dict[str, str],
    muestra_codes: set[str],
) -> dict:
    """Contrapunto contra la tipificación por reglas (tipificacion.tipificar) en la muestra 25."""
    arquetipo_regla: dict[str, str] = {}
    for cod in etiquetas:
        if cod not in muestra_codes:
            continue
        r = agregados[cod]
        m = {
            "pct_reg": round(100.0 - float(r.get("pct_noreg", 0.0) or 0.0), 1),
            "pct_sicep": float(r.get("pct_sicep", 0.0) or 0.0),
            "pct_exposicion": float(r.get("pct_exposicion", 0.0) or 0.0),
        }
        arquetipo_regla[cod] = tipificar(cod, segmento_por_codigo.get(cod, "?"), m)

    pares = [(int(labels[i]), arquetipo_regla[etiquetas[i]]) for i in range(len(labels)) if etiquetas[i] in arquetipo_regla]
    if not pares:
        return {"n": 0, "ari": None, "tabla": [], "desacuerdos": []}

    reglas = sorted({p[1] for p in pares})
    clus = sorted({p[0] for p in pares})
    contigencia: dict[tuple[int, str], int] = {}
    for p in pares:
        contigencia[(p[0], p[1])] = contigencia.get((p[0], p[1]), 0) + 1
    tabla = [[contigencia.get((c, r), 0) for r in reglas] for c in clus]
    ari = adjusted_rand_score([p[0] for p in pares], [p[1] for p in pares])
    # Coincidencia agente a agente: se listan los de la muestra cuyo arquetipo-regla
    # no es el mayoritario dentro de su clúster.
    desacuerdos = []
    for i in range(len(labels)):
        cod = etiquetas[i]
        if cod not in arquetipo_regla:
            continue
        cid = int(labels[i])
        miembros = [etiquetas[j] for j in range(len(labels)) if int(labels[j]) == cid and etiquetas[j] in arquetipo_regla]
        if not miembros:
            continue
        mayoritario = max(set(arquetipo_regla[m] for m in miembros), key=lambda r: sum(1 for m in miembros if arquetipo_regla[m] == r))
        if arquetipo_regla[cod] != mayoritario:
            desacuerdos.append({"codigo": cod, "arquetipo_regla": arquetipo_regla[cod], "arquetipo_cluster": nombrar_cluster_desde(contigencia, cid, reglas)})
    return {"n": len(pares), "ari": round(ari, 4), "tabla": tabla, "clusters": clus, "reglas": reglas, "desacuerdos": desacuerdos}


def nombrar_cluster_desde(contigencia: dict, cid: int, reglas: list[str]) -> str:
    """Etiqueta-regla mayoritaria en un clúster (para el contrapunto)."""
    totales = {r: contigencia.get((cid, r), 0) for r in reglas}
    return max(totales, key=totales.get) if totales else "—"


def seleccionar_representantes(
    etiquetas: list[str],
    labels: np.ndarray,
    X_scaled: np.ndarray,
    modelo: KMeans,
    agregados: dict[str, dict],
    features: list[str],
    representantes_por_cluster: int = 3,
    extremos_por_feature: int = 1,
) -> dict[int, dict]:
    """Selecciona representantes por clúster para la narrativa del informe.

    Por clúster: **medoide** (agente más cercano al centroide) + **extremos**,
    tomados de (a) los miembros más lejanos al centroide (borde) y (b) los
    valores extremos (máx/mín) por feature discriminante. Devolver dict
    {clúster: {n, medoide, extremos}}.
    """
    rep: dict[int, dict] = {}
    for cid in sorted({int(x) for x in labels}):
        idx = [i for i in range(len(labels)) if int(labels[i]) == cid]
        centro = modelo.cluster_centers_[cid]
        dist = [float(np.linalg.norm(X_scaled[i] - centro)) for i in idx]
        order = sorted(range(len(idx)), key=lambda k: dist[k])
        candidatos: list[int] = [order[0]]  # medoide
        for k in reversed(order):  # borde: más lejanos al centroide
            if len(candidatos) >= representantes_por_cluster:
                break
            if k not in candidatos:
                candidatos.append(k)
        if len(candidatos) < representantes_por_cluster:
            extra: list[int] = []
            for f in features:
                vals = sorted(
                    (float(agregados[etiquetas[i]].get(f, 0.0) or 0.0), i) for i in idx
                )
                for e in vals[:extremos_por_feature] + vals[-extremos_por_feature:]:
                    if e[1] not in extra:
                        extra.append(e[1])
            for e in extra:
                if len(candidatos) >= representantes_por_cluster:
                    break
                if e not in candidatos:
                    candidatos.append(e)
        medoide = etiquetas[idx[order[0]]]
        extremos = [etiquetas[idx[k]] for k in candidatos[1:]]
        rep[cid] = {"n": len(idx), "medoide": medoide, "extremos": extremos}
    return rep