"""CONTROLLER del estudio híbrido diario (F-1 + D1).

Ejecuta después de FaseSegmentacion: agrega los datos diarios de los 65
comercializadores (sql/d1_diario.sql), construye la matriz pooled de agentes-día,
corre el k-means, perfila los arquetipos, rankea las estrategias por día y
calcula el balance del período. Solo LEE datos["f-1"] (población, segmento,
nombres); guarda el resultado en datos["diario"].
"""
from __future__ import annotations

import math

from app.services import clustering, diario


class FaseDiaria:
    def __init__(self, repo, cfg):
        self.repo = repo
        self.cfg = cfg

    def ejecutar(self, datos: dict) -> dict:
        v = self.cfg["ventana"]
        d = self.cfg["diario"]

        por_codigo = datos["f-1"]["por_codigo"]
        codigo_a_nombre = {c: a.nombre for c, a in por_codigo.items()}
        segmento_por_codigo = {c: a.segmento.value for c, a in por_codigo.items()}
        poblacion = set(por_codigo)

        rows = self.repo.diario(v["foco_ini"], v["fin_c_familia"])
        agentedia = diario.construir_agente_dia(rows)
        agentedia = {k: ad for k, ad in agentedia.items() if ad["codigo"] in poblacion}

        params = self.cfg["modelo_financiero"]
        clip_sicep = d.get("clip_pct_sicep", 100.0)
        for k, ad in agentedia.items():
            ad["features"] = diario.features_diarias(ad, clip_sicep)
            ad["desempeno"] = diario.desempeno_diario(ad, params)
        diario.aplicar_clip_margen(agentedia, d.get("clip_margen_cop_kwh"))

        features = list(d["features"])
        transformes = {
            k: (v, lambda x: math.log1p(x))
            for k, v in (d.get("transformes") or {}).items()
        }
        X, etiquetas, nombres_features = diario.construir_matriz_diaria(
            agentedia,
            features,
            clip_sobrecobertura=d.get("clip_sobrecobertura"),
            transformes=transformes,
        )
        X_scaled, scaler = clustering.escalar(X, d.get("scaler", "standard"))

        resultados_k = diario.elegir_k_diario(
            X_scaled, d["k_min"], d["k_max"], d["random_state"], d.get("submuestra_k")
        )
        k = d.get("k") or clustering.mejor_k(resultados_k)
        labels, modelo = clustering.aplicar_kmeans(X_scaled, k, d["random_state"], d.get("n_init", 10))

        perfiles = diario.perfilar_estrategias(agentedia, etiquetas, labels, features, segmento_por_codigo)
        filas = diario.construir_agente_dia_filas(
            agentedia, etiquetas, labels, perfiles, codigo_a_nombre, segmento_por_codigo
        )
        ranking = diario.ranking_diario(agentedia, etiquetas, labels)
        balance = diario.balance_periodo(ranking, perfiles)
        balance, atipicos = diario.separar_atipicos(
            balance, len(ranking), d.get("min_dias_pct", 0.0)
        )

        ranking_por_segmento = diario.ranking_diario_por_segmento(
            agentedia, etiquetas, labels, segmento_por_codigo
        )
        balance_por_segmento = diario.balance_por_segmento(
            ranking_por_segmento, perfiles, len(ranking), d.get("min_dias_pct", 0.0)
        )
        estrategia_x_segmento = diario.matriz_estrategia_x_segmento(
            ranking_por_segmento, perfiles
        )

        resultado = {
            "agentedia": agentedia,
            "features": nombres_features,
            "etiquetas": etiquetas,
            "labels": labels,
            "modelo": modelo,
            "k_seleccionado": k,
            "resultados_k": resultados_k,
            "perfiles": perfiles,
            "agentes": filas,
            "ranking": ranking,
            "balance": balance,
            "atipicos": atipicos,
            "ranking_por_segmento": ranking_por_segmento,
            "balance_por_segmento": balance_por_segmento,
            "estrategia_x_segmento": estrategia_x_segmento,
            "segmentos": sorted(segmento_por_codigo.values()),
            "n_agentes_dia": len(filas),
            "n_dias": len(ranking),
            "n_agentes": len(poblacion),
        }
        datos["diario"] = resultado
        return resultado