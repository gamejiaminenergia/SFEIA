"""VIEW: exportación de los resultados del asistente imitador a CSV.

Genera en `data/` (raíz) archivos UTF-8 con BOM para Excel y cabeceras en
español. Jamás consulta la BD: solo serializa el resultado de FaseAsistente.
"""
from __future__ import annotations

import csv
from pathlib import Path

from asistente.app.services.contexto import ordenar_bins

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
    ])
    generados.append(p)

    return generados


def guardar(resultado: dict, cfg: dict) -> list[Path]:
    """Alias de exportar() para mantener la interfaz de las vistas."""
    return exportar(resultado, cfg)