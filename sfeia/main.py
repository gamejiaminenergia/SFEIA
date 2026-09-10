#!/usr/bin/env python3
"""Punto de entrada único del proyecto SFEIA: asistente imitador del agente XXXC.

Behavioral Cloning del top-N de un (segmento, estrategia): aprende de la
ventana de estudio el perfil de abastecimiento que usaron los maestros por
bin de spread y lo replica en la ventana de impacto.

Uso:
    python -m sfeia.main [--segmento PEQUEÑO] [--estrategia "Trader expuesto a bolsa (sin cobertura)"]
                         [--top 5]
                         [--estudio-ini 2025-07-01] [--estudio-fin 2025-07-31]
                         [--impacto-ini 2025-08-01] [--impacto-fin 2025-08-08]
                         [--demanda-dia-gwh 0.12] [--config path/to/config.yaml]
                         [--walk-forward] [--barrido] [--semanal [--fecha AAAA-MM-DD]]

Sin fechas: el estudio usa los últimos `dias_estudio_por_defecto` días antes de
la ventana de impacto y el impacto los últimos `dias_impacto_por_defecto` días
de la ventana principal (ancla = borde de datos de elecdb). `--barrido` evalúa
todas las (segmento × estrategia) y filtra por validez; `--walk-forward` corre
la serie de ventanas rodantes; `--semanal` entrega la recomendación semanal
(veredicto OPERAR/NO OPERAR + dashboard HTML autocontenido) anclada a
`--fecha` o al borde de datos.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sfeia.app.controllers.fase_asistente import FaseAsistente
from sfeia.app.models.entities import ParametrosAsistente
from sfeia.app.models.repositories import RepoElecdb
from sfeia.app.views.exportar_csv import exportar as exportar_csv
from sfeia.app.views.exportar_csv import exportar_barrido, exportar_walk_forward
from sfeia.app.views.informe_asistente_md import guardar as guardar_informe
from sfeia.app.views.informe_barrido_md import guardar as guardar_informe_barrido
from sfeia.config.settings import CONFIG_PATH, db_dsn, load_merged


def _parsear(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Asistente imitador del agente XXXC (Behavioral Cloning del top-N)"
    )
    parser.add_argument("--config", default=str(CONFIG_PATH),
                        help="Config única (estudio + simulador) en sfeia/config/config.yaml")
    parser.add_argument("--segmento", default=None, help="GRANDE | MEDIANO | PEQUEÑO")
    parser.add_argument("--estrategia", default=None, help="Arquetipo del estudio a imitar")
    parser.add_argument("--top", type=int, default=None, help="N de maestros a imitar")
    parser.add_argument("--estudio-ini", default=None)
    parser.add_argument("--estudio-fin", default=None)
    parser.add_argument("--impacto-ini", default=None)
    parser.add_argument("--impacto-fin", default=None)
    parser.add_argument("--demanda-dia-gwh", type=float, default=None,
                        help="Demanda diaria de XXXC; si se omite, mediana del segmento")
    parser.add_argument("--walk-forward", action="store_true",
                        help="Corre la serie de ventanas rodantes (P2.3) y exporta data/walk_forward.csv")
    parser.add_argument("--barrido", action="store_true",
                        help="Evalúa todas las (segmento × estrategia), filtra por validez (S2) y exporta "
                             "data/barrido_combinaciones.csv + docs/informe_barrido_combinaciones.md")
    parser.add_argument("--aceptacion", action="store_true",
                        help="Harness de aceptación: grid 2015→hoy, scan grueso + confirmación de candidatas, "
                             "scorecard N0–N4 en docs/scorecard_aceptacion.md + data/scorecard*.csv")
    parser.add_argument("--poder", action="store_true",
                        help="Experimento de poder estadístico (Ruta C): ¿la señal operable resiste más "
                             "simulaciones, ventanas largas y pool entre segmentos? docs/experimento_poder_estadistico.md")
    parser.add_argument("--semanal", action="store_true",
                        help="Recomendación semanal 'lo actual y el futuro': re-entrena con los últimos 90 días, "
                             "valida contra la última semana CERRADA y entrega el dashboard HTML autocontenido "
                             "docs/recomendacion_semanal.html (+ .md y CSV) con veredicto OPERAR/NO OPERAR")
    parser.add_argument("--fecha", default=None, metavar="AAAA-MM-DD",
                        help="Ancla de la ventana para --semanal (o el flujo por defecto): la ventana termina en "
                             "esa fecha; si se omite, en el borde de datos de elecdb")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parsear(argv)
    cfg = load_merged(args.config)
    repo = RepoElecdb(db_dsn(cfg))

    # Ancla dinámica (plan_recomendacion_semanal §4.1): si el foco es null (o
    # se pasa --fecha), se resuelve contra el borde de datos de elecdb.
    from sfeia.app.controllers.fase_semanal import resolver_ancla
    if args.fecha:
        cfg["ventana"]["foco_fin"] = args.fecha
        cfg["ventana"]["foco_ini"] = None
    cfg["ventana"] = resolver_ancla(cfg["ventana"], repo.fecha_max_sistema())

    a_cfg = cfg["asistente"]
    params = ParametrosAsistente(
        segmento=args.segmento or a_cfg["segmento_por_defecto"],
        estrategia=args.estrategia or a_cfg["estrategia_por_defecto"],
        top=args.top or a_cfg["top_por_defecto"],
        estudio_ini=args.estudio_ini or a_cfg.get("estudio_ini"),
        estudio_fin=args.estudio_fin or a_cfg.get("estudio_fin"),
        impacto_ini=args.impacto_ini or a_cfg.get("impacto_ini"),
        impacto_fin=args.impacto_fin or a_cfg.get("impacto_fin"),
        demanda_dia_gwh=args.demanda_dia_gwh if args.demanda_dia_gwh is not None else a_cfg.get("dema_dia_gwh"),
        min_dias_pct=float(a_cfg["min_dias_pct"]),
        dias_impacto_por_defecto=int(a_cfg["dias_impacto_por_defecto"]),
    )

    print(f"Asistente imitador: {params.segmento} · {params.estrategia} · top-{params.top}")
    try:
        if args.semanal:
            from sfeia.app.controllers.fase_semanal import FaseSemanal
            from sfeia.app.views.dashboard_semanal_html import guardar as guardar_dashboard
            from sfeia.app.views.exportar_csv import exportar_semanal
            sem_cfg = a_cfg.get("semanal", {})
            a_cfg["dias_estudio_por_defecto"] = int(sem_cfg.get("dias_estudio", 90))
            a_cfg["dias_impacto_por_defecto"] = int(sem_cfg.get("dias_impacto", 7))
            payload = FaseSemanal(repo, cfg).ejecutar(params)
            html_d = guardar_dashboard(payload, cfg)
            csv_d = exportar_semanal(payload, cfg)
            print(f"Recomendación semanal → {html_d.relative_to(Path.cwd())}")
            print(f"  - {csv_d.relative_to(Path.cwd())}")
            print(f"VEREDICTO: {payload['veredicto']}")
            print(f"  {payload['razon']}")
            return 0
        if args.poder:
            from sfeia.app.controllers.estudio_poder import EstudioPoder
            from sfeia.app.views.informe_poder_md import guardar as guardar_poder
            res = EstudioPoder(repo, cfg).ejecutar()
            destino = guardar_poder(res, cfg)
            print(f"Experimento de poder (Ruta C) → {destino.relative_to(Path.cwd())}")
            for f in res["filas"]:
                print(f"  {f['ventana']} {f['segmento']}·{f['estrategia'][:30]:32s} "
                      f"p(n_boot2000)={f['p_n_boot2000']}  p(pool entre seg)={f['p_pool_entre_segmentos']}")
            print(f"  [ventana larga] {res['largo']['nota']}  p={res['largo']['p_n_boot2000']}")
            return 0
        if args.aceptacion:
            from sfeia.app.controllers.fase_aceptacion import FaseAceptacion
            from sfeia.app.views.exportar_csv import exportar_scorecard
            from sfeia.app.views.informe_scorecard_md import guardar as guardar_scorecard
            res = FaseAceptacion(repo, cfg).ejecutar()
            csvs = exportar_scorecard(res, cfg)
            destino = guardar_scorecard(res, cfg)
            print(f"Scorecard: {res['n_ventanas_ok']} ventanas · {res['n_combinaciones']} combinaciones (topN) · "
                  f"{res['n_combinaciones_arquetipo']} (arquetipo) → {destino.relative_to(Path.cwd())}")
            for c in csvs:
                print(f"  - {c.relative_to(Path.cwd())}")
            operables = [c for c in res["confirmadas"] if c["valida_final"]]
            operables_arq = [c for c in res["confirmadas_arquetipo"] if c["valida_final"]]
            if operables or operables_arq:
                print(f"VEREDICTO: COMBINACIÓN OPERABLE ENCONTRADA ({len(operables) + len(operables_arq)}):")
                for c in operables[:15]:
                    print(f"  - {c['segmento']} · {c['estrategia']}  p={c['p_valor']:.4f}  réplica {c['ratio_replicacion']:.2f}"
                          f"  DSR {c['dsr']:.2f}  holdout {c['persistencia']}%  estudio {c['estudio_ini']}..{c['estudio_fin']}")
                for c in operables_arq[:15]:
                    print(f"  - {c['segmento']} · {c['estrategia']} (arquetipo)  p={c['p_valor']:.4f}  réplica {c['ratio_replicacion']:.2f}"
                          f"  DSR {c['dsr']:.2f}  estudio {c['estudio_ini']}..{c['estudio_fin']}")
            else:
                print(f"VEREDICTO: NO-OPERABLE. Confirmadas: {len(res['confirmadas'])} topN + "
                      f"{len(res['confirmadas_arquetipo'])} arquetipo (ninguna pasa N1+N2).")
            return 0
        if args.barrido:
            b_cfg = a_cfg.get("barrido", {})
            barrido = FaseAsistente(repo, cfg).ejecutar_barrido(params, b_cfg)
            destino = exportar_barrido(barrido, cfg)
            guardar_informe_barrido(barrido, cfg)
            validas = [c for c in barrido["combinaciones"] if c["valida"]]
            print(f"Barrido: {len(barrido['combinaciones'])} combinaciones evaluadas → {destino.relative_to(Path.cwd())}")
            if validas:
                print(f"  {len(validas)} combinaciones VÁLIDAS:")
                for c in validas:
                    print(f"    - {c['segmento']} · {c['estrategia']}  relativo {c['mediana_relativa_top']:.2f}"
                          f"  p={c['p_valor']:.3f}  réplica {c['ratio_replicacion']:.2f}")
            else:
                print("  Ninguna combinación pasó el filtro de validez. Ver informe del barrido.")
            return 0
        if args.walk_forward:
            wf_cfg = a_cfg.get("walk_forward", {"dias_estudio": 30, "dias_impacto": 7, "pasos_max": 6})
            resultados = FaseAsistente(repo, cfg).ejecutar_walk_forward(params, wf_cfg)
            if not resultados:
                print("ERROR: walk-forward no produjo ninguna ventana válida.", file=sys.stderr)
                return 1
            destino = exportar_walk_forward(resultados, cfg)
            print(f"Walk-forward: {len(resultados)} pasos → {destino.relative_to(Path.cwd())}")
            ratios = [r["validez"]["replicacion_is_oos"]["ratio_replicacion"]
                      for r in resultados if r["validez"]["replicacion_is_oos"]["ratio_replicacion"] is not None]
            dsrs = [r["validez"]["dsr"]["dsr"] for r in resultados if r["validez"].get("dsr")]
            print(f"  Ratio de replicación IS→OOS (mediana): "
                  + (f"{sorted(ratios)[len(ratios)//2]:.2f}" if ratios else "—"))
            print(f"  DSR (mediana): " + (f"{sorted(dsrs)[len(dsrs)//2]:.2f}" if dsrs else "—"))
            return 0

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
    val = resultado.get("validez", {})
    print()
    print(f"Maestros ({len(resultado['maestros'])}): "
          + ", ".join(m.codigo for m in resultado["maestros"]))
    print(f"Política: {len(resultado['politica'].reglas)} bins con datos"
          + (f" (fallback: {resultado['politica'].fallback.n_dias} días)" if resultado["politica"].fallback else ""))
    if val.get("bootstrap"):
        b = val["bootstrap"]
        print(f"Skill-vs-luck: p={b['p_valor']:.3f}"
              + (" (sí supera al azar)" if b["p_valor"] <= val.get("alpha_significancia", 0.05) else " (NO supera al azar)"))
    if val.get("holdout") and val["holdout"].get("pct_persistencia") is not None:
        print(f"Holdout: {val['holdout']['pct_persistencia']:.1f} % de maestros persisten en sub-validación")
    if val.get("dsr"):
        print(f"DSR: {val['dsr']['dsr']:.2f} ({val['dsr']['n_trials']} trials)")
    print(f"Impacto ({p['ventanas']['impacto']['ini']} → {p['ventanas']['impacto']['fin']}):")
    print(f"  mediana imitación  = {res.mediana_imitacion:.2f} COP/kWh")
    print(f"  mediana maestros   = {res.mediana_maestros if res.mediana_maestros is not None else '—'}")
    print(f"  mediana segmento   = {res.mediana_segmento if res.mediana_segmento is not None else '—'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())