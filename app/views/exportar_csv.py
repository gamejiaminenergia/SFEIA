"""VIEW: exportación de los resultados del estudio híbrido diario a CSV.

Genera en `data/` archivos CSV legibles por humanos (cabeceras en español,
unidades claras, codificación UTF-8 con BOM para que Excel muestre bien los
acentos). Jamás consulta la BD: solo serializa datos["diario"].
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _escribir(path: Path, encabezados: list[str], filas: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(encabezados)
        w.writerows(filas)


def _representativos(diario: dict, cid: int) -> list[str]:
    """Agentes únicos del clúster ordenados por máxima demanda diaria (top 5)."""
    max_dema: dict[str, float] = {}
    for a in diario["agentes"]:
        if a.cluster_id != cid:
            continue
        dema = float(a.features.get("dema_gwh", 0.0))
        if dema > max_dema.get(a.codigo, 0.0):
            max_dema[a.codigo] = dema
    return sorted(max_dema, key=max_dema.get, reverse=True)[:5]


def _ganador(ranking: dict, dia: str) -> int:
    for cid, res in ranking.get(dia, {}).items():
        if res["rango"] == 1:
            return cid
    return -1


def _dias_precio(agentedia: dict) -> dict:
    """Precios de sistema por día (comunes a todos los agentes)."""
    out: dict[str, dict] = {}
    for ad in agentedia.values():
        dia = str(ad["dia"])
        if dia not in out:
            out[dia] = {
                "prec_bolsa": ad["prec_bolsa"],
                "prec_cont": ad["prec_cont"],
                "prec_escasez": ad["prec_escasez"],
            }
    return out


def _segmentos(d: dict) -> list[str]:
    orden = ["GRANDE", "MEDIANO", "PEQUEÑO"]
    presentes = d.get("ranking_por_segmento", {})
    return [s for s in orden if s in presentes]


def exportar(datos: dict, cfg: dict, dirname: str = "data") -> list[Path]:
    d = datos["diario"]
    perfiles = d["perfiles"]
    atipico_ids = {b.cluster_id for b in d.get("atipicos", [])}
    directorio = BASE_DIR / dirname
    generados: list[Path] = []

    # ---- 1. agentes_dia.csv (detalle diario por agente) ----
    filas = []
    for a in d["agentes"]:
        f = a.features
        filas.append([
            a.dia, a.codigo, a.nombre, a.segmento, a.arquetipo, a.cluster_id,
            round(f.get("dema_gwh", 0.0), 4),
            f.get("pct_noreg", 0.0), f.get("pct_cobertura", 0.0),
            f.get("pct_exposicion", 0.0), f.get("pct_sicep", 0.0),
            f.get("tiene_sicep", 0), a.margen_kwh, a.costo_kwh,
        ])
    filas.sort(key=lambda r: (r[0], r[1]))
    p = directorio / "agentes_dia.csv"
    _escribir(p, [
        "fecha", "codigo_agente", "nombre_agente", "segmento", "estrategia",
        "cluster", "demanda_gwh_dia", "pct_no_regulado", "pct_cobertura_contratos",
        "pct_exposicion_bolsa", "pct_sicep", "compra_regulado_1_0",
        "margen_est_cop_kwh", "costo_energia_est_cop_kwh",
    ], filas)
    generados.append(p)

    # ---- 2. perfil_arquetipos.csv (perfil de cada estrategia) ----
    filas = []
    for cid in sorted(perfiles):
        pperf = perfiles[cid]
        m = pperf.medias
        comp = pperf.composicion_segmento
        filas.append([
            pperf.arquetipo, cid, pperf.n, pperf.n_agentes,
            m.get("log_dema", 0.0), m.get("pct_noreg", 0.0),
            m.get("pct_cobertura", 0.0), m.get("pct_exposicion", 0.0),
            m.get("pct_sicep", 0.0), m.get("tiene_sicep", 0),
            comp.get("GRANDE", 0), comp.get("MEDIANO", 0), comp.get("PEQUEÑO", 0),
            " ".join(_representativos(d, cid)),
        ])
    p = directorio / "perfil_arquetipos.csv"
    _escribir(p, [
        "estrategia", "cluster", "n_agentes_dia", "n_agentes_unicos",
        "media_log_demanda", "media_pct_no_regulado", "media_pct_cobertura",
        "media_pct_exposicion", "media_pct_sicep", "media_compra_regulado",
        "n_agentes_GRANDE", "n_agentes_MEDIANO", "n_agentes_PEQUENO",
        "agentes_representativos",
    ], filas)
    generados.append(p)

    # ---- 3. ranking_diario.csv (puesto por día y estrategia) ----
    filas = []
    for dia in sorted(d["ranking"]):
        for cid, res in d["ranking"][dia].items():
            nom = perfiles.get(cid).arquetipo if cid in perfiles else f"E{cid}"
            filas.append([
                dia, nom, cid, res["n"], res["mediana"], res["media"], res["rango"],
            ])
    p = directorio / "ranking_diario.csv"
    _escribir(p, [
        "fecha", "estrategia", "cluster", "n_agentes", "mediana_margen_cop_kwh",
        "media_margen_cop_kwh", "puesto_del_dia",
    ], filas)
    generados.append(p)

    # ---- 4. balance_periodo.csv (ranking final del período) ----
    filas = []
    todos = list(d["balance"]) + list(d.get("atipicos", []))
    for i, b in enumerate(todos, start=1):
        filas.append([
            i, b.arquetipo, b.cluster_id, b.dias, b.mediana_margen, b.media_margen,
            b.dias_puesto1, b.pct_top3, b.rango_promedio, b.tendencia,
            1 if b.cluster_id in atipico_ids else 0,
        ])
    p = directorio / "balance_periodo.csv"
    _escribir(p, [
        "posicion", "estrategia", "cluster", "dias_presente",
        "mediana_margen_cop_kwh", "media_margen_cop_kwh", "dias_puesto_1",
        "pct_dias_top3", "rango_promedio", "tendencia_2da_menos_1ra_mitad",
        "es_atipico",
    ], filas)
    generados.append(p)

    # ---- 5. dias_mercado.csv (contexto diario de mercado + ganador) ----
    filas = []
    dias_precio = _dias_precio(d["agentedia"])
    for dia in sorted(dias_precio):
        dp = dias_precio[dia]
        cid = _ganador(d["ranking"], dia)
        nom = perfiles[cid].arquetipo if cid in perfiles else "—"
        if cid in atipico_ids:
            nom += " (atipico)"
        filas.append([
            dia, round(dp["prec_bolsa"], 1), round(dp["prec_cont"], 1),
            round(dp["prec_bolsa"] - dp["prec_cont"], 1), round(dp["prec_escasez"], 1),
            1 if dp["prec_bolsa"] > dp["prec_escasez"] else 0, nom,
        ])
    p = directorio / "dias_mercado.csv"
    _escribir(p, [
        "fecha", "precio_bolsa_cop_kwh", "precio_contratos_cop_kwh",
        "spread_bolsa_menos_contratos", "precio_escasez_cop_kwh",
        "dia_escasez_1_0", "estrategia_ganadora",
    ], filas)
    generados.append(p)

    # ---- 6. matriz_puestos.csv (días en cada puesto por estrategia) ----
    k = d["k_seleccionado"]
    contador: dict[int, list[int]] = {cid: [0] * k for cid in range(k)}
    for res in d["ranking"].values():
        for cid, r in res.items():
            if 0 <= cid < k and 1 <= r["rango"] <= k:
                contador[cid][r["rango"] - 1] += 1
    filas = []
    for cid in range(k):
        nom = perfiles[cid].arquetipo if cid in perfiles else f"E{cid}"
        filas.append([nom, cid] + contador[cid] + [sum(contador[cid])])
    p = directorio / "matriz_puestos.csv"
    _escribir(p, (
        ["estrategia", "cluster"]
        + [f"dias_puesto_{i + 1}" for i in range(k)]
        + ["total_dias"]
    ), filas)
    generados.append(p)

    # ---- 7. balance_por_segmento.csv (ranking final por segmento) ----
    filas = []
    for seg in _segmentos(d):
        bl = d["balance_por_segmento"].get(seg, {})
        todos = list(bl.get("balance", [])) + list(bl.get("atipicos", []))
        for i, b in enumerate(todos, start=1):
            filas.append([
                seg, i, b.arquetipo, b.cluster_id, b.dias, b.mediana_margen, b.media_margen,
                b.dias_puesto1, b.pct_top3, b.rango_promedio, b.tendencia,
                1 if b.cluster_id in {x.cluster_id for x in bl.get("atipicos", [])} else 0,
            ])
    p = directorio / "balance_por_segmento.csv"
    _escribir(p, [
        "segmento", "posicion", "estrategia", "cluster", "dias_presente",
        "mediana_margen_cop_kwh", "media_margen_cop_kwh", "dias_puesto_1",
        "pct_dias_top3", "rango_promedio", "tendencia_2da_menos_1ra_mitad", "es_atipico",
    ], filas)
    generados.append(p)

    # ---- 8. ranking_por_segmento.csv (puesto por día y segmento) ----
    filas = []
    for seg in _segmentos(d):
        for dia in sorted(d["ranking_por_segmento"].get(seg, {})):
            for cid, res in d["ranking_por_segmento"][seg][dia].items():
                nom = perfiles.get(cid).arquetipo if cid in perfiles else f"E{cid}"
                filas.append([
                    seg, dia, nom, cid, res["n"], res["mediana"], res["media"], res["rango"],
                ])
    p = directorio / "ranking_por_segmento.csv"
    _escribir(p, [
        "segmento", "fecha", "estrategia", "cluster", "n_agentes",
        "mediana_margen_cop_kwh", "media_margen_cop_kwh", "puesto_del_dia",
    ], filas)
    generados.append(p)

    # ---- 9. estrategia_x_segmento.csv (matriz estrategia × segmento) ----
    filas = []
    for cid in sorted(d["estrategia_x_segmento"]):
        nom = perfiles.get(cid).arquetipo if cid in perfiles else f"E{cid}"
        for seg in sorted(d["estrategia_x_segmento"][cid]):
            celda = d["estrategia_x_segmento"][cid][seg]
            filas.append([nom, cid, seg, celda["dias"], celda["mediana"], celda["media"]])
    p = directorio / "estrategia_x_segmento.csv"
    _escribir(p, [
        "estrategia", "cluster", "segmento", "dias_presente",
        "mediana_margen_cop_kwh", "media_margen_cop_kwh",
    ], filas)
    generados.append(p)

    return generados


def guardar(datos: dict, cfg: dict) -> list[Path]:
    """Alias de exportar() para mantener la interfaz de las vistas."""
    return exportar(datos, cfg)