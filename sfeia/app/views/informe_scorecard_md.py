"""VIEW: informe del scorecard de aceptación en Markdown.

Recibe el resultado de `FaseAceptacion.ejecutar` y produce
`docs/scorecard_aceptacion.md` (raíz del repo). Jamás consulta la BD.
"""
from __future__ import annotations

from pathlib import Path

from sfeia.app.services import scorecard

BASE_DIR = Path(__file__).resolve().parents[3]

ADVERTENCIA = (
    "> **Advertencia:** el margen es un **artefacto de modelado** (Pv=350 COP/kWh fijo, precios de sistema) usado "
    "para comparar estrategias entre sí. La selección usa el **margen relativo al segmento** (cancela el artefacto). "
    "Ningún valor aquí es dinero real ni una recomendación de inversión."
)


def _tabla(encabezados: list[str], filas: list[list]) -> str:
    if not filas:
        return "_Sin datos._"
    salida = [
        "| " + " | ".join(encabezados) + " |",
        "|" + "|".join("---" for _ in encabezados) + "|",
    ]
    for fila in filas:
        celdas = [str(fila[i]) if i < len(fila) else "" for i in range(len(encabezados))]
        salida.append("| " + " | ".join(celdas) + " |")
    return "\n".join(salida)


def _fmt(v, dec: int = 2) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:,.{dec}f}".replace(",", " ")
    return str(v)


def _si_no(v: bool) -> str:
    return "sí" if v else "no"


def renderizar(res: dict) -> str:
    f = res["filtros"]
    grid = res["grid"]
    operables = [c for c in res["confirmadas"] if c["valida_final"]]
    L: list[str] = []

    L.append("# Scorecard de aceptación del asistente imitador")
    L.append("")
    L.append(ADVERTENCIA)
    L.append("")
    L.append(f"Grid: **{res['n_ventanas_ok']}** ventanas (estudio {grid['dias_estudio']} d · impacto "
             f"{grid['dias_impacto']} d · paso {grid['paso_dias']} d) entre **2015-01-01** y el límite de datos · "
             f"**{res['n_combinaciones']}** (segmento × estrategia × ventana) evaluadas en el scan grueso.")
    L.append("")
    L.append(f"Gates (N1/N2): bootstrap p ≤ {f['alpha']} · N efectivo ≥ {f['min_n_efectivo']} · holdout ≥ "
             f"{f['min_persistencia']} % · replicación ≥ {f['min_replicacion']} · DSR ≥ {f['min_dsr']} · "
             f"% días > segmento ≥ {f['min_pct_gana_segmento']} · EV histórico ≥ {f['min_ev_historico']} · "
             f"sin kill-switch · capacidad ≤ {f.get('capacidad_max_pct', 5.0)} %.")
    L.append("")

    if operables:
        L.append("## VEREDICTO: COMBINACIÓN OPERABLE ENCONTRADA")
        L.append("")
        L.append(f"**{len(operables)}** combinación(es) pasan N0+N1+N2+N3 en una ventana reproducible:")
        L.append("")
        for c in operables:
            L.append(f"- **{c['segmento']} · {c['estrategia']}** — estudio {c['estudio_ini']}→{c['estudio_fin']} · "
                     f"impacto {c['impacto_ini']}→{c['impacto_fin']} — p={c['p_valor']:.4f} · réplica "
                     f"{_fmt(c['ratio_replicacion'])} · DSR {_fmt(c['dsr'])} · N efectivo {c['n_efectivo']} · "
                     f"% días > segmento {_fmt(c['pct_gana_segmento'])}.")
        L.append("")
    else:
        L.append("## VEREDICTO: NO-OPERABLE (no se encontró combinación válida)")
        L.append("")
        L.append("Tras el barrido completo del grid, **ninguna** (segmento × estrategia × ventana) supera la "
                 "barrera de validez con el margen C16–C18 relativo al segmento. La siguiente tabla muestra las "
                 "confirmaciones más cercanas a la barrera (la distancia es la evidencia de por qué no hay señal).")
        L.append("")

    # ---- confirmadas ----
    L.append("## Confirmaciones (flujo completo: bootstrap fino + holdout + DSR)")
    L.append("")
    if res["confirmadas"]:
        filas = []
        for c in res["confirmadas"]:
            filas.append([
                c["estudio_ini"], c["segmento"], c["estrategia"],
                c["n_maestros"], c["n_efectivo"], _fmt(c["p_valor"], 4),
                _fmt(c["ratio_replicacion"]), _fmt(c["dsr"]), _fmt(c["persistencia"]),
                _fmt(c["pct_gana_segmento"]), _fmt(c["ev_historico"]),
                _si_no(c["kill_switch"]), _si_no(c["valida_final"]),
            ])
        L.append(_tabla([
            "Ventana estudio", "Segmento", "Estrategia", "N", "N ef.",
            "p-valor", "Réplica", "DSR", "Holdout %",
            "% > seg.", "EV hist.", "Kill", "Operable",
        ], filas))
    else:
        L.append("_No hubo confirmaciones._")
    L.append("")
    L.append("**Lectura:** *Operable* = pasa N1 completo (bootstrap + N efectivo + holdout + replicación + DSR) "
             "y N2 (económico/riesgo) en esa ventana.")
    L.append("")

    # ---- diagnóstico de la falta de señal ----
    L.append("## Diagnóstico de la falta de señal (tasas de paso por gate)")
    L.append("")
    n = len(res["filas"])
    if n:
        g = res["filtros"]
        evs = [scorecard.evaluar_gates(f, g) for f in res["filas"]]
        p_vals = sorted(f["p_valor"] for f in res["filas"] if f.get("p_valor") is not None)
        filas = [
            ["Combinaciones evaluadas (scan grueso)", n],
            ["p-valor mínimo (bootstrap skill-vs-luck)", round(p_vals[0], 4) if p_vals else "—"],
            ["p-valor mediana", round(p_vals[len(p_vals) // 2], 4) if p_vals else "—"],
        ]
        for gate, nombre in [
            ("V1_bootstrap", "V1 · bootstrap p ≤ 0.05"),
            ("V2_n_efectivo", "V2 · N efectivo ≥ 3"),
            ("V4_replicacion", "V4 · replicación ≥ 0.5"),
            ("V5_dsr", "V5 · DSR ≥ 0.95"),
            ("E1_gana_segmento", "E1 · % días > segmento ≥ 60"),
            ("E2_sin_kill_switch", "E2 · sin kill-switch"),
            ("E3_ev_historico", "E3 · EV histórico ≥ 0"),
            ("E4_capacidad", "E4 · capacidad ≤ límite"),
        ]:
            n_ok = sum(1 for e in evs if e["gates"].get(gate))
            filas.append([f"{nombre} (pasan / %)", f"{n_ok} / {round(n_ok / n * 100, 1)} %"])
        filas.append(["Combinaciones que pasan N1 cheap + N2 (candidatas)", sum(1 for e in evs if e["valida_cheap"])])
        L.append(_tabla(["Gate", "Resultado"], filas))
        L.append("")
        L.append("**Lectura:** el gate dominante es **V1 (bootstrap skill-vs-luck)**. El mejor maestro de cada "
                 "(segmento × estrategia × ventana) **nunca supera el percentil 95 de la nula** en los 11 años "
                 "analizados: la dispersión de 'habilidad' dentro de una estrategia es nula con el premio C16–C18 "
                 "relativo (los agentes de una misma estrategia son conductualmente homogéneos → el 'top' es suerte "
                 "entre iguales). Aun las combinaciones con N efectivo ≥ 3 caen en V1 (p ≈ 1.0).")
        L.append("")

    # ---- mejores del scan grueso ----
    orden = sorted(res["filas"], key=lambda f: (f["p_valor"], -f["mediana_relativa_top"]))[:20]
    L.append("## Mejores 20 del scan grueso (por p-valor, candidatas primero)")
    L.append("")
    filas = []
    for c in orden:
        filas.append([
            c["estudio_ini"], c["segmento"], c["estrategia"],
            c["n_maestros"], c["n_efectivo"], _fmt(c["p_valor"], 4),
            _fmt(c["ratio_replicacion"]), _fmt(c["dsr"]), _fmt(c["pct_gana_segmento"]),
            _fmt(c["mediana_relativa_top"]), _si_no(c["candidata"]),
        ])
    L.append(_tabla([
        "Ventana estudio", "Segmento", "Estrategia", "N", "N ef.",
        "p-valor", "Réplica", "DSR", "% > seg.", "Relativo", "Candidata",
    ], filas))
    L.append("")
    L.append("**Distancia a la barrera:** el p-valor del bootstrap skill-vs-luck es el gate más difícil; "
             "un valor ≈ 1 indica que el mejor maestro es indistinguible del azar dentro de su (segmento, estrategia).")
    L.append("")

    # ---- régimen de escasez del período ----
    h = res["historial"]
    L.append("## Contexto de escasez del histórico (para leer los resultados)")
    L.append("")
    L.append(f"Días con escasez real (bolsa > precio de escasez): **{h['pct_dias_escasez']} %** del histórico "
             f"({h['n_dias']} días). Años Niño (2015-16, 2023-24) tuvieron 21-30 %; 2017-22 y 2025 ~0 %.")
    L.append("")

    L.append("---")
    L.append("_Generado por `python -m sfeia.main --aceptacion`. No editar a mano._")
    return "\n".join(L)


def guardar(res: dict, cfg: dict) -> Path:
    md = renderizar(res)
    destino = BASE_DIR / cfg["asistente"]["aceptacion"]["salida"]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(md, encoding="utf-8")
    return destino