"""VIEW: informe del asistente imitador en Markdown.

Recibe el resultado de `FaseAsistente` y la config, y produce
`docs/informe_asistente_imitador.md` (raíz del repo). Jamás consulta la BD.
"""
from __future__ import annotations

from pathlib import Path

from asistente.app.services.contexto import ordenar_bins

BASE_DIR = Path(__file__).resolve().parents[3]


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


def _fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:,.2f}".replace(",", " ")
    return str(v)


def _tabla_maestros(r: dict) -> str:
    filas = [[i + 1, m.codigo, m.nombre, m.n_dias, _fmt(m.mediana_margen), _fmt(m.media_margen)]
             for i, m in enumerate(r["maestros"])]
    return _tabla(["Pos.", "Código", "Comercializador", "Días en la estrategia",
                   "Mediana margen (COP/kWh)", "Media margen"], filas)


def _tabla_politica(r: dict) -> str:
    politica = r["politica"]
    filas = []
    for label, lo, hi in ordenar_bins(politica.bins_spread):
        regla = politica.reglas.get(label)
        if not regla:
            filas.append([label, f"{lo:,.0f}–{hi:,.0f}".replace(",", " "), "—", "—", "—", "—", "—"])
            continue
        p = regla.perfil
        filas.append([
            label, f"{lo:,.0f}–{hi:,.0f}".replace(",", " "), regla.n_dias,
            f"{p.pct_cobertura:.0f}%", f"{p.pct_exposicion:.0f}%",
            f"{p.pct_noreg:.0f}%", f"{p.pct_sicep:.0f}%",
        ])
    tabla = _tabla(["Contexto (spread bolsa−contrato)", "Rango (COP/kWh)", "Días de entrenamiento",
                    "Cobertura contratos", "Exposición bolsa", "No regulado", "SICEP"], filas)
    fb = politica.fallback
    if fb:
        tabla += ("\n\n> **Fallback** (mediana global del estudio, para contextos sin datos):"
                  f" cobertura {fb.pct_cobertura:.0f} %, exposición {fb.pct_exposicion:.0f} %,"
                  f" no regulado {fb.pct_noreg:.0f} %, SICEP {fb.pct_sicep:.0f} %.")
    return tabla


def _tabla_simulacion(r: dict) -> str:
    filas = []
    for s in r["simulacion"]:
        esc = "sí" if s.es_escasez else "no"
        filas.append([
            s.fecha, s.bin_spread, esc,
            f"{s.perfil.pct_cobertura:.0f}%", f"{s.perfil.pct_exposicion:.0f}%",
            _fmt(s.margen_imitacion), _fmt(s.margen_maestros), _fmt(s.margen_segmento),
        ])
    return _tabla(["Fecha", "Contexto", "Escasez", "Cobertura", "Exposición",
                   "Margen imitación", "Mediana maestros", "Mediana segmento"], filas)


def renderizar(resultado: dict, cfg: dict) -> str:
    a_cfg = cfg["asistente"]
    p = resultado["parametros"]
    res = resultado["resumen"]
    v = p["ventanas"]
    L: list[str] = []

    L.append("# Asistente imitador del agente XXXC — Behavioral Cloning del top-N")
    L.append("")
    L.append(f"> Proyecto SFEIA (simulador) · Clona el comportamiento del top-{p['top']} de"
             f" **{p['segmento']} · {p['estrategia']}** y lo replica en una ventana de impacto."
             " Documentado en `docs/plan_agente_xxxc_asistente.md`.")
    L.append("")

    # ---- Parámetros ----
    L.append("## 1. Parámetros")
    L.append("")
    L.append(_tabla(
        ["Parámetro", "Valor"],
        [
            ["Segmento", p["segmento"]],
            ["Estrategia a imitar", p["estrategia"]],
            ["Top de maestros", str(p["top"])],
            ["Demanda diaria de XXXC (GWh)", _fmt(p["demanda_dia_gwh"])],
            ["Presencia mínima en la estrategia", f"{p['min_dias_pct']:.0f} % de los días"],
            ["Ventana de estudio (define maestros)", f"{v['estudio']['ini']} → {v['estudio']['fin']}"],
            ["Ventana de impacto (evalúa imitación)", f"{v['impacto']['ini']} → {v['impacto']['fin']}"],
        ],
    ))
    L.append("")

    # ---- Maestros ----
    L.append(f"## 2. Maestros — top {p['top']} del segmento en la ventana de estudio")
    L.append("")
    e = resultado["estudio"]
    L.append(f"Ranking de agentes por mediana del margen diario dentro de"
             f" **{p['segmento']} · {p['estrategia']}** en {v['estudio']['ini']} → {v['estudio']['fin']}"
             f" (estudio de {e['n_agentes']} agentes, {e['n_dias']} días, k={e['k']})."
             " Los maestros son quienes se imitan: su perfil de abastecimiento por contexto se clona.")
    L.append("")
    L.append(_tabla_maestros(resultado))
    L.append("")

    # ---- Política ----
    L.append("## 3. Política de clonación (contexto → perfil de abastecimiento)")
    L.append("")
    L.append("Por bin de spread (bolsa − contrato) se aprende la **mediana** del perfil que usaron los"
             " maestros cuando jugaron la estrategia objetivo. Un día con ese contexto recibe ese perfil.")
    L.append("")
    L.append(_tabla_politica(resultado))
    L.append("")

    # ---- Simulación ----
    L.append(f"## 4. Simulación en la ventana de impacto ({v['impacto']['ini']} → {v['impacto']['fin']})")
    L.append("")
    L.append("XXXC replica cada día el perfil recomendado y se calcula su margen con la misma lógica del"
             " estudio (C16–C18 sobre precios de sistema). Se compara contra la **mediana real** de los"
             " maestros y del segmento ese día en los datos cargados.")
    L.append("")
    L.append(_tabla_simulacion(resultado))
    L.append("")

    # ---- Balance ----
    L.append("## 5. Balance del impacto")
    L.append("")
    L.append(_tabla(
        ["Métrica", "Imitación (XXXC)", "Maestros (real)", "Segmento (real)"],
        [
            ["Mediana margen (COP/kWh)", _fmt(res.mediana_imitacion),
             _fmt(res.mediana_maestros), _fmt(res.mediana_segmento)],
            ["Media margen (COP/kWh)", _fmt(res.media_imitacion), "—", "—"],
            ["% días que la imitación gana", "—",
             _fmt(res.pct_dias_gana_maestros), _fmt(res.pct_dias_gana_segmento)],
        ],
    ))
    L.append("")
    if res.mediana_maestros is not None:
        dif = res.mediana_imitacion - res.mediana_maestros
        L.append(f"La imitación logra una mediana de **{res.mediana_imitacion:.1f} COP/kWh/día** frente a"
                 f" **{res.mediana_maestros:.1f}** de sus maestros reales (delta **{dif:+.1f}**) y"
                 f" **{res.mediana_segmento:.1f}** del segmento. Recuerda: el margen es un artefacto de"
                 " modelado, válido para comparar entre sí.")
        L.append("")
    L.append(f"Demanda diaria simulada: **{res.demanda_kwh_dia:,.0f} kWh**"
             f" ({res.demanda_kwh_dia / 1e6:.3f} GWh).".replace(",", " "))
    L.append("")

    # ---- Advertencias / limitaciones ----
    L.append("## 6. Advertencias y limitaciones")
    L.append("")
    for i, adv in enumerate(resultado["advertencias"], start=1):
        L.append(f"{i}. {adv}")
    L.append("")

    return "\n".join(L)


def guardar(resultado: dict, cfg: dict) -> Path:
    md = renderizar(resultado, cfg)
    destino = BASE_DIR / cfg["asistente"]["salida"]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(md, encoding="utf-8")
    return destino