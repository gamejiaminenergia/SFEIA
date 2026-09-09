#!/usr/bin/env python3
"""Punto de entrada del análisis SFEIA.

Uso: python main.py [--config config/config.yaml]
Ejecuta el pipeline F-1, F0–F6 sobre elecdb y genera el informe Markdown.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.controllers.pipeline import Pipeline
from app.models.repositories import RepoElecdb
from app.views.informe_md import guardar
from config.settings import db_dsn, load_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Análisis de estrategias de comercialización en el MEM")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent / "config" / "config.yaml"))
    args = parser.parse_args()

    cfg = load_config(args.config)
    repo = RepoElecdb(db_dsn(cfg))

    print("Ejecutando fases F-1, F0–F6 ...")
    datos = Pipeline(repo, cfg).ejecutar()

    destino = guardar(datos, cfg)
    print(f"Informe generado: {destino}")

    resumen = datos["f-1"]["resumen"]
    print("Segmentos:", {k: f"{v['n']} agentes / {v['pct_mercado']}% del mercado" for k, v in resumen.items()})
    print(f"Matriz F6: {len(datos['f6']['matriz'])} agentes tipificados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())