#!/usr/bin/env python3
"""CLI del asistente imitador del agente XXXC (simulador en la raíz).

Behavioral Cloning del top-N de un (segmento, estrategia): aprende de la
ventana de estudio el perfil de abastecimiento que usaron los maestros por
bin de spread y lo replica en la ventana de impacto.

Uso:
    python -m asistente [--segmento PEQUEÑO] [--estrategia "Trader expuesto a bolsa (sin cobertura)"]
                        [--top 5]
                        [--estudio-ini 2026-06-01] [--estudio-fin 2026-06-30]
                        [--impacto-ini 2026-07-01] [--impacto-fin 2026-07-08]
                        [--demanda-dia-gwh 0.12] [--config path/to/config.yaml]

Sin fechas: el estudio usa la ventana principal menos los últimos N días
(`asistente.dias_impacto_por_defecto`) y el impacto los últimos N días.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sfeia.app.models.repositories import RepoElecdb
from sfeia.config.settings import db_dsn, load_config

from asistente.app.controllers.fase_asistente import FaseAsistente
from asistente.app.models.entities import ParametrosAsistente
from asistente.app.views.exportar_csv import exportar as exportar_csv
from asistente.app.views.informe_asistente_md import guardar as guardar_informe

CONFIG_DEFECTO = Path(__file__).resolve().parent.parent / "sfeia" / "config" / "config.yaml"


def _parsear(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Asistente imitador del agente XXXC (Behavioral Cloning del top-N)")
    parser.add_argument("--config", default=str(CONFIG_DEFECTO))
    parser.add_argument("--segmento", default=None, help="GRANDE | MEDIANO | PEQUEÑO")
    parser.add_argument("--estrategia", default=None, help="Arquetipo del estudio a imitar")
    parser.add_argument("--top", type=int, default=None, help="N de maestros a imitar")
    parser.add_argument("--estudio-ini", default=None)
    parser.add_argument("--estudio-fin", default=None)
    parser.add_argument("--impacto-ini", default=None)
    parser.add_argument("--impacto-fin", default=None)
    parser.add_argument("--demanda-dia-gwh", type=float, default=None,
                        help="Demanda diaria de XXXC; si se omite, mediana del segmento")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parsear(argv)
    cfg = load_config(args.config)
    repo = RepoElecdb(db_dsn(cfg))

    a_cfg = cfg["asistente"]
    params = ParametrosAsistente(
        segmento=args.segmento or a_cfg["segmento_por_defecto"],
        estrategia=args.estrategia or a_cfg["estrategia_por_defecto"],
        top=args.top or a_cfg["top_por_defecto"],
        estudio_ini=args.estudio_ini,
        estudio_fin=args.estudio_fin,
        impacto_ini=args.impacto_ini,
        impacto_fin=args.impacto_fin,
        demanda_dia_gwh=args.demanda_dia_gwh if args.demanda_dia_gwh is not None else a_cfg.get("dema_dia_gwh"),
        min_dias_pct=float(a_cfg["min_dias_pct"]),
        dias_impacto_por_defecto=int(a_cfg["dias_impacto_por_defecto"]),
    )

    print(f"Asistente imitador: {params.segmento} · {params.estrategia} · top-{params.top}")
    try:
        resultado = FaseAsistente(repo, cfg).ejecutar(params)
    except ValueError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1

    destino = guardar_informe(resultado, cfg)
    print(f"Informe generado: {destino.relative_to(Path.cwd())}")

    csvs = exportar_csv(resultado, cfg)
    print("CSV generados:")
    for c in csvs:
        print(f"  - {c.relative_to(Path.cwd())}")

    p = resultado["parametros"]
    res = resultado["resumen"]
    print()
    print(f"Maestros ({len(resultado['maestros'])}): "
          + ", ".join(m.codigo for m in resultado["maestros"]))
    print(f"Política: {len(resultado['politica'].reglas)} bins con datos"
          + (f" (fallback: {resultado['politica'].fallback.n_dias} días)" if resultado["politica"].fallback else ""))
    print(f"Impacto ({p['ventanas']['impacto']['ini']} → {p['ventanas']['impacto']['fin']}):")
    print(f"  mediana imitación  = {res.mediana_imitacion:.2f} COP/kWh")
    print(f"  mediana maestros   = {res.mediana_maestros if res.mediana_maestros is not None else '—'}")
    print(f"  mediana segmento   = {res.mediana_segmento if res.mediana_segmento is not None else '—'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())