"""CONTROLLER del estudio k-means: agrega F1–F4 a los 65 y ejecuta el clustering.

Independencia: no modifica ningún controlador del estudio actual (F-1, F0–F6).
Agrega por su cuenta los repos (las queries sql/f1…f4 devuelven todos los
agentes) y solo LEE datos["f-1"] (población, segmento de referencia, nombres).
"""
from __future__ import annotations

import math
from collections import defaultdict

from sfeia.app.services import clustering


def _codigo_a_nombre(datos: dict) -> dict[str, str]:
    return {c: a.nombre for c, a in datos["f-1"]["por_codigo"].items()}


def _segmento_por_codigo(datos: dict) -> dict[str, str]:
    return {c: a.segmento.value for c, a in datos["f-1"]["por_codigo"].items()}


def _sumar(rows: list[dict], clave: str, key: str = "agente") -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    for r in rows:
        out[r[key]] += float(r[clave] or 0.0)
    return dict(out)


class FaseClustering:
    def __init__(self, repo, cfg):
        self.repo = repo
        self.cfg = cfg

    def ejecutar(self, datos: dict) -> dict:
        v = self.cfg["ventana"]
        cl = self.cfg["clustering"]
        codigo_a_nombre = _codigo_a_nombre(datos)
        segmento_por_codigo = _segmento_por_codigo(datos)

        # ---- Agregación propia de F1–F4 para TODOS los agentes ----
        c01, c02, c03, sicep_rows = self.repo.cartera(v["foco_ini"], v["fin_c_familia"])
        cobertura_rows = self.repo.cobertura(v["foco_ini"], v["fin_c_familia"])
        pico_rows = self.repo.pico_valle(v["foco_ini"], v["fin_c_familia"])
        perdidas_rows, _ = self.repo.mix(v["foco_ini"], v["fin_c_familia"])

        dema_reg = _sumar(c01, "dema_reg_gwh")
        dema_noreg = _sumar(c01, "dema_noreg_gwh")
        cont_reg = _sumar(sicep_rows, "cont_reg_gwh")
        cont_sicep = _sumar(sicep_rows, "cont_sicep_gwh")

        cob = defaultdict(lambda: {"dema": 0.0, "cont": 0.0, "bolsa": 0.0})
        for r in cobertura_rows:
            d = cob[r["agente"]]
            d["dema"] += float(r["dema_gwh"] or 0.0)
            d["cont"] += float(r["cont_gwh"] or 0.0)
            d["bolsa"] += float(r["bolsa_gwh"] or 0.0)

        pico_pos = defaultdict(float)
        for r in pico_rows:
            if r["bloque_horario"].startswith("PICO"):
                pico_pos[r["agente"]] += float(r["posicion_neta_bolsa_gwh"] or 0.0)

        perd = defaultdict(lambda: {"dema": 0.0, "real": 0.0})
        for r in perdidas_rows:
            d = perd[r["agente"]]
            d["dema"] += float(r["dema_come_gwh"] or 0.0)
            d["real"] += float(r["dema_real_gwh"] or 0.0)

        # ---- Matriz de features (escala original) por código ----
        agregados: dict[str, dict] = {}
        for cod, seg in segmento_por_codigo.items():
            nombre = codigo_a_nombre[cod]
            # Tamaño y mix desde la población F-1 (DemaCome semestral, C01)
            dema_gwh = float(datos["f-1"]["por_codigo"][cod].dema_come_gwh)
            reg = dema_reg.get(nombre, 0.0)
            noreg = dema_noreg.get(nombre, 0.0)
            total = reg + noreg
            pct_noreg = round(noreg / total * 100, 2) if total else 0.0
            c = cob.get(nombre, {})
            cob_dema = c["dema"]
            pct_cobertura = round(c["cont"] / cob_dema * 100, 2) if cob_dema else 0.0
            pct_exposicion = round(c["bolsa"] / cob_dema * 100, 2) if cob_dema else 0.0
            reg_comp = cont_reg.get(nombre, 0.0)
            pct_sicep = round(cont_sicep.get(nombre, 0.0) / reg_comp * 100, 2) if reg_comp else 0.0
            tiene_sicep = 1.0 if reg_comp > 0 else 0.0
            perd_dema = perd.get(nombre, {}).get("dema", 0.0)
            perd_real = perd.get(nombre, {}).get("real", 0.0)
            pct_perdidas = round((perd_dema - perd_real) / perd_dema * 100, 2) if perd_dema else 0.0
            intensidad_pico = round(pico_pos.get(nombre, 0.0) / dema_gwh * 100, 2) if dema_gwh else 0.0
            agregados[cod] = {
                "dema_gwh": dema_gwh,
                "log_dema": round(math.log1p(dema_gwh), 4),
                "pct_noreg": pct_noreg,
                "pct_cobertura": pct_cobertura,
                "pct_exposicion": pct_exposicion,
                "pct_sicep": pct_sicep,
                "tiene_sicep": tiene_sicep,
                "pct_perdidas": pct_perdidas,
                "intensidad_pico": intensidad_pico,
            }

        # ---- Pipeline de clustering ----
        features = list(cl["features"])
        transformes = {
            k: (v, lambda x: math.log1p(x))
            for k, v in (cl.get("transformes") or {}).items()
        }
        X, etiquetas, nombres = clustering.construir_matriz(
            agregados,
            features,
            clip_sobrecobertura=cl.get("clip_sobrecobertura"),
            transformes=transformes,
            clip_intensidad_pico=cl.get("clip_intensidad_pico"),
        )
        X_scaled, scaler = clustering.escalar(X, cl.get("scaler", "standard"))

        resultados_k = clustering.elegir_k(X_scaled, cl["k_min"], cl["k_max"], cl["random_state"])
        k = cl.get("k") or clustering.mejor_k(resultados_k)
        labels, modelo = clustering.aplicar_kmeans(X_scaled, k, cl["random_state"], cl.get("n_init", 10))

        perfiles = clustering.perfilar_clusters(agregados, etiquetas, labels, features, segmento_por_codigo)
        filas = clustering.construir_agente_clusterizado(
            agregados, etiquetas, labels, segmento_por_codigo, perfiles, codigo_a_nombre
        )

        vs_segmento = clustering.comparar_con_segmento(etiquetas, labels, segmento_por_codigo)
        muestra = {c for codes in datos["f-1"]["muestra"].values() for c in codes}
        vs_tipificacion = clustering.comparar_con_tipificacion(
            etiquetas, labels, agregados, segmento_por_codigo, muestra
        )

        resultado = {
            "agregados": agregados,
            "features": nombres,
            "etiquetas": etiquetas,
            "X_scaled": X_scaled,
            "scaler": scaler,
            "labels": labels,
            "modelo": modelo,
            "k_seleccionado": k,
            "resultados_k": resultados_k,
            "perfiles": perfiles,
            "agentes": filas,
            "vs_segmento": vs_segmento,
            "vs_tipificacion": vs_tipificacion,
            "muestra_total": len(filas),
        }
        datos["clustering"] = resultado
        return resultado