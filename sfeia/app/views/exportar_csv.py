"""VIEW: exportación de los resultados del asistente imitador a CSV.

Genera en `data/` (raíz) archivos UTF-8 con BOM para Excel y cabeceras en
español. Jamás consulta la BD: solo serializa el resultado de FaseAsistente.
"""
from __future__ import annotations

import csv
from pathlib import Path

from sfeia.app.services.contexto import ordenar_bins

BASE_DIR = Path(__file__).resolve().parents[3]


def _escribir(path: Path, encabezados: list[str], filas: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(encabezados)
        w.writerows(filas)


def exportar(resultado: dict, cfg: dict) -> list[Path]:
    directorio = BASE_DIR / cfg["asistente"]["data_dir"]
    generados: list[Path] = []

    # ---- 1. maestros_topN.csv ----
    filas = [[i + 1, m.codigo, m.nombre, m.n_dias, m.mediana_margen, m.media_margen,
              m.mediana_relativa, m.pct_dias_supera_segmento,
              m.pct_dias_perdida, m.drawdown_max, m.downside_mediana]
             for i, m in enumerate(resultado["maestros"])]
    p = directorio / "maestros_topN.csv"
    _escribir(p, [
        "posicion", "codigo_agente", "nombre_agente", "dias_en_estrategia",
        "mediana_margen_cop_kwh", "media_margen_cop_kwh",
        "mediana_relativa_cop_kwh", "pct_dias_supera_segmento",
        "pct_dias_perdida", "drawdown_max_cop_kwh_acum", "mediana_dias_malos_cop_kwh",
    ], filas)
    generados.append(p)

    # ---- 2. politica_clonacion.csv ----
    politica = resultado["politica"]
    filas = []
    for label, lo, hi in ordenar_bins(politica.bins_spread):
        regla = politica.reglas.get(label)
        if not regla:
            filas.append([label, lo, hi, 0, "", "", "", ""])
            continue
        per = regla.perfil
        filas.append([
            label, lo, hi, regla.n_dias,
            per.pct_cobertura, per.pct_exposicion, per.pct_noreg, per.pct_sicep,
        ])
    fb = politica.fallback
    if fb:
        filas.append([
            "FALLBACK", "", "", fb.n_dias,
            fb.pct_cobertura, fb.pct_exposicion, fb.pct_noreg, fb.pct_sicep,
        ])
    p = directorio / "politica_clonacion.csv"
    _escribir(p, [
        "contexto_spread", "spread_min_cop_kwh", "spread_max_cop_kwh", "dias_entrenamiento",
        "pct_cobertura_contratos", "pct_exposicion_bolsa", "pct_no_regulado", "pct_sicep",
    ], filas)
    generados.append(p)

    # ---- 3. simulacion_impacto.csv ----
    filas = []
    for s in resultado["simulacion"]:
        filas.append([
            s.fecha, s.bin_spread, 1 if s.es_escasez else 0,
            1 if s.en_distribucion else 0,
            "" if s.nivel_embalses_pct is None else s.nivel_embalses_pct,
            s.perfil.pct_cobertura, s.perfil.pct_exposicion, s.perfil.pct_noreg, s.perfil.pct_sicep,
            s.margen_imitacion,
            "" if s.margen_maestros is None else s.margen_maestros,
            "" if s.margen_segmento is None else s.margen_segmento,
        ])
    p = directorio / "simulacion_impacto.csv"
    _escribir(p, [
        "fecha", "contexto_spread", "dia_escasez_1_0", "en_distribucion_1_0", "nivel_embalses_pct",
        "pct_cobertura_contratos", "pct_exposicion_bolsa", "pct_no_regulado", "pct_sicep",
        "margen_imitacion_cop_kwh", "mediana_margen_maestros_cop_kwh", "mediana_margen_segmento_cop_kwh",
    ], filas)
    generados.append(p)

    # ---- 4. resumen_impacto.csv ----
    res = resultado["resumen"]
    p = directorio / "resumen_impacto.csv"
    _escribir(p, [
        "metrica", "valor",
    ], [
        ["dias_impacto", res.dias],
        ["demanda_dia_kwh", res.demanda_kwh_dia],
        ["mediana_margen_imitacion_cop_kwh", res.mediana_imitacion],
        ["media_margen_imitacion_cop_kwh", res.media_imitacion],
        ["mediana_margen_maestros_cop_kwh", "" if res.mediana_maestros is None else res.mediana_maestros],
        ["mediana_margen_segmento_cop_kwh", "" if res.mediana_segmento is None else res.mediana_segmento],
        ["pct_dias_gana_a_maestros", "" if res.pct_dias_gana_maestros is None else res.pct_dias_gana_maestros],
        ["pct_dias_gana_a_segmento", "" if res.pct_dias_gana_segmento is None else res.pct_dias_gana_segmento],
        ["garantia_mediana_cop", res.garantia_mediana_cop],
        ["garantia_max_cop", res.garantia_max_cop],
    ])
    generados.append(p)

    # ---- 5. distribucion_margenes.csv (riesgo del impacto) ----
    d = resultado["distribuciones"]
    filas = []
    for metrica, campo in [
        ("n_dias", "n"), ("mediana_cop_kwh", "mediana"), ("media_cop_kwh", "media"),
        ("p5_cop_kwh", "p5"), ("p95_cop_kwh", "p95"),
        ("pct_dias_perdida", "pct_dias_perdida"), ("peor_dia_cop_kwh", "peor_dia"),
        ("mejor_dia_cop_kwh", "mejor_dia"), ("drawdown_max_cop_kwh_acum", "drawdown_max"),
    ]:
        filas.append([metrica,
                      getattr(d["imitacion"], campo),
                      getattr(d["maestros"], campo),
                      getattr(d["segmento"], campo)])
    p = directorio / "distribucion_margenes.csv"
    _escribir(p, ["metrica", "imitacion", "maestros_real", "segmento_real"], filas)
    generados.append(p)

    # ---- 6. escenario_escasez.csv (estrés sintético) ----
    filas = [[e.nombre, e.descripcion, e.prec_bolsa, e.prec_cont, e.spread, e.bin_spread,
              e.margen_cop_kwh, e.garantia_cop] for e in resultado["escenarios"]]
    p = directorio / "escenario_escasez.csv"
    _escribir(p, [
        "escenario", "descripcion", "precio_bolsa_cop_kwh", "precio_contratos_cop_kwh",
        "spread_cop_kwh", "bin_spread", "margen_cop_kwh", "garantia_cop",
    ], filas)
    generados.append(p)

    # ---- 7. historial_escasez.csv (frecuencia histórica de contextos) ----
    h = resultado["historial_escasez"]
    filas = []
    for label, f in h["frecuencia_bins"].items():
        filas.append(["frecuencia_bin", label, "", f["n"], f["pct"], "", "", ""])
    filas += [
        ["dias_escasez_real", "", h["n_dias_escasez"], h["n_dias"], h["pct_dias_escasez"], "", "", ""],
        ["spread_p50_cop_kwh", "", "", "", "", h["spread_p50"], "", ""],
        ["spread_p95_cop_kwh", "", "", "", "", h["spread_p95"], "", ""],
        ["spread_p99_cop_kwh", "", "", "", "", h["spread_p99"], "", ""],
        ["spread_max_cop_kwh", "", "", "", "", h["spread_max"], "", ""],
    ]
    for anio, a in sorted(h["por_anio"].items()):
        filas.append(["por_anio", anio, "", a["n_dias"], a["pct_escasez"], "", a["n_escasez"], ""])
    p = directorio / "historial_escasez.csv"
    _escribir(p, [
        "tipo", "año", "n_dias_escasez", "n_dias", "pct", "spread_cop_kwh", "n_escasez", "contexto",
    ], filas)
    generados.append(p)

    # ---- 8. validacion_seleccion.csv (P0: bootstrap, holdout, DSR, replicación) ----
    v = resultado.get("validez", {})
    filas = []
    boot = v.get("bootstrap")
    if boot:
        filas.append(["bootstrap_p_valor", boot["p_valor"]])
        filas.append(["bootstrap_mejor_maestro_real_cop_kwh", boot["mejor_maestro_real"]])
        filas.append(["bootstrap_nulo_p50_cop_kwh", boot["nulo_p50"]])
        filas.append(["bootstrap_nulo_p95_cop_kwh", boot["nulo_p95"]])
        filas.append(["bootstrap_candidatos_trials", boot["n_agentes_candidatos"]])
    h_ = v.get("holdout")
    if h_:
        filas.append(["holdout_pct_persistencia",
                      "" if h_.get("pct_persistencia") is None else h_["pct_persistencia"]])
        filas.append(["holdout_mediana_percentil",
                      "" if h_.get("mediana_percentil") is None else h_["mediana_percentil"]])
    rep = v.get("replicacion_is_oos")
    if rep:
        filas.append(["replicacion_is_cop_kwh", rep["mediana_imitacion_is"]])
        filas.append(["replicacion_oos_cop_kwh", rep["mediana_imitacion_oos"]])
        filas.append(["replicacion_ratio", rep["ratio_replicacion"]])
    dsr = v.get("dsr")
    if dsr:
        filas.append(["dsr_sharpe_diario", dsr["sharpe_diario"]])
        filas.append(["dsr_skew", dsr["skew"]])
        filas.append(["dsr_kurt", dsr["kurt"]])
        filas.append(["dsr_n_trials", dsr["n_trials"]])
        filas.append(["dsr_valor", dsr["dsr"]])
        filas.append(["dsr_significativo", 1 if dsr["significativo"] else 0])
    if v.get("n_efectivo_maestros") is not None:
        filas.append(["n_efectivo_maestros", v["n_efectivo_maestros"]])
    p = directorio / "validacion_seleccion.csv"
    _escribir(p, ["metrica", "valor"], filas)
    generados.append(p)

    return generados


def exportar_barrido(barrido: dict, cfg: dict) -> Path:
    """CSV del barrido de combinaciones (S2)."""
    directorio = BASE_DIR / cfg["asistente"]["data_dir"]
    filas = []
    for c in barrido["combinaciones"]:
        filas.append([
            c["segmento"], c["estrategia"], c["n_maestros"], c["n_efectivo"],
            ",".join(c["codigos"]),
            c["mediana_relativa_top"], c["mediana_margen_absoluto"],
            c["p_valor"], c["ratio_replicacion"], c["drawdown_max"],
            1 if c["kill_switch"] else 0, 1 if c["valida"] else 0,
        ])
    p = directorio / "barrido_combinaciones.csv"
    _escribir(p, [
        "segmento", "estrategia", "n_maestros", "n_efectivo", "codigos",
        "mediana_relativa_top_cop_kwh", "mediana_margen_absoluto_cop_kwh",
        "p_valor_bootstrap", "ratio_replicacion", "drawdown_max_cop_kwh",
        "kill_switch_1_0", "valida_1_0",
    ], filas)
    return p


def exportar_walk_forward(resultados: list[dict], cfg: dict) -> Path:
    """CSV de la serie walk-forward (P2.3): un paso = una ventana estudio→impacto.

    Cada fila reporta el desempeño OOS (impacto) de ese paso y el resultado de
    las pruebas de validez (replicación, DSR).
    """
    directorio = BASE_DIR / cfg["asistente"]["data_dir"]
    filas = []
    for r in resultados:
        p = r["parametros"]
        v = r["parametros"]["ventanas"]
        res = r["resumen"]
        val = r.get("validez", {})
        rep = val.get("replicacion_is_oos", {})
        dsr = val.get("dsr", {})
        filas.append([
            v["estudio"]["ini"], v["estudio"]["fin"],
            v["impacto"]["ini"], v["impacto"]["fin"],
            len(r["maestros"]),
            res.mediana_imitacion,
            "" if res.mediana_maestros is None else res.mediana_maestros,
            "" if res.mediana_segmento is None else res.mediana_segmento,
            "" if rep.get("ratio_replicacion") is None else rep["ratio_replicacion"],
            "" if not dsr else dsr["dsr"],
            r["decision"]["kill_switch_activado"],
        ])
    p = directorio / "walk_forward.csv"
    _escribir(p, [
        "estudio_ini", "estudio_fin", "impacto_ini", "impacto_fin",
        "n_maestros", "mediana_margen_imitacion_cop_kwh",
        "mediana_margen_maestros_cop_kwh", "mediana_margen_segmento_cop_kwh",
        "replicacion_ratio", "dsr", "kill_switch_activado",
    ], filas)
    return p


def guardar(resultado: dict, cfg: dict) -> list[Path]:
    """Alias de exportar() para mantener la interfaz de las vistas."""
    return exportar(resultado, cfg)