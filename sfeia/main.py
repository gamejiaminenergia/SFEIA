#!/usr/bin/env python3
"""Punto de entrada del análisis SFEIA (estudio híbrido diario).

Uso: python main.py [--config config/config.yaml]
Ejecuta F-1 (segmentación) + FaseDiaria (estrategias diarias, k-means pooled,
ranking de desempeño y balance del período) sobre elecdb y genera el informe
Markdown único del proyecto (docs/informe_estrategias_diarias.md).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sfeia.app.controllers.fase_diaria import FaseDiaria
from sfeia.app.controllers.fase_segmentacion import FaseSegmentacion
from sfeia.app.models.repositories import RepoElecdb
from sfeia.app.views.exportar_csv import exportar as exportar_csv
from sfeia.app.views.informe_diario_md import guardar
from sfeia.config.settings import db_dsn, load_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Análisis de estrategias de comercialización en el MEM")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent / "config" / "config.yaml"))
    args = parser.parse_args()

    cfg = load_config(args.config)
    repo = RepoElecdb(db_dsn(cfg))

    print("Ejecutando F-1 (segmentación) + FaseDiaria (estrategias diarias) ...")
    datos: dict = {}
    FaseSegmentacion(repo, cfg).ejecutar(datos)   # F-1 (población de 65)
    FaseDiaria(repo, cfg).ejecutar(datos)         # estudio híbrido diario

    destino = guardar(datos, cfg)
    print(f"Informe generado: {destino}")

    csvs = exportar_csv(datos, cfg)
    print("CSV generados (data/):")
    for c in csvs:
        print(f"  - {c.relative_to(Path.cwd())}")

    d = datos["diario"]
    resumen = datos["f-1"]["resumen"]
    print("Segmentos:", {k: f"{v['n']} agentes / {v['pct_mercado']}% del mercado" for k, v in resumen.items()})
    print(f"Agentes-día: {d['n_agentes_dia']} ({d['n_agentes']} agentes × {d['n_dias']} días) · k={d['k_seleccionado']}")
    print("Ranking de estrategias del período (mediana margen COP/kWh/día):")
    for i, b in enumerate(d["balance"], start=1):
        print(f"  {i}. {b.arquetipo} · {b.mediana_margen} · {b.dias_puesto1} días 1.º")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())