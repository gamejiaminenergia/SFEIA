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
    filas = [[i + 1, m.codigo, m.nombre, m.n_dias, m.mediana_margen, m.media_margen]
             for i, m in enumerate(resultado["maestros"])]
    p = directorio / "maestros_topN.csv"
    _escribir(p, [
        "posicion", "codigo_agente", "nombre_agente", "dias_en_estrategia",
        "mediana_margen_cop_kwh", "media_margen_cop_kwh",
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
            s.perfil.pct_cobertura, s.perfil.pct_exposicion, s.perfil.pct_noreg, s.perfil.pct_sicep,
            s.margen_imitacion,
            "" if s.margen_maestros is None else s.margen_maestros,
            "" if s.margen_segmento is None else s.margen_segmento,
        ])
    p = directorio / "simulacion_impacto.csv"
    _escribir(p, [
        "fecha", "contexto_spread", "dia_escasez_1_0",
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

    return generados


def guardar(resultado: dict, cfg: dict) -> list[Path]:
    """Alias de exportar() para mantener la interfaz de las vistas."""
    return exportar(resultado, cfg)