"""VIEW: informe del barrido de combinaciones (S2) en Markdown.

Recibe el resultado de `FaseAsistente.ejecutar_barrido` y produce
`docs/informe_barrido_combinaciones.md` (raíz del repo). Jamás consulta la BD.
"""
from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]

ADVERTENCIA = (
    "> **Advertencia (léela antes que nada):** este es un **ejercicio descriptivo sobre comportamiento pasado** con un "
    "margen de **modelado** (Pv=350 COP/kWh fijo, precios promedio de sistema). Los márgenes aquí son artefactos "
    "matemáticos para comparar estrategias entre sí, **no dinero real ni una recomendación de inversión**. La "
    "selección usa el **margen relativo al segmento** (cancela el artefacto); la mediana absoluta se reporta como "
    "contexto."
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


def renderizar(barrido: dict) -> str:
    v = barrido["ventanas"]
    f = barrido["filtros"]
    combos = barrido["combinaciones"]
    validas = [c for c in combos if c["valida"]]
    L: list[str] = []

    L.append("# Barrido de combinaciones (segmento × estrategia) — ¿dónde hay señal?")
    L.append("")
    L.append(ADVERTENCIA)
    L.append("")
    L.append(f"Ventana de estudio: **{v['estudio']['ini']} → {v['estudio']['fin']}** · "
             f"Ventana de impacto: **{v['impacto']['ini']} → {v['impacto']['fin']}**.")
    L.append("")
    L.append(f"Filtros de validez (S2): bootstrap p-valor ≤ {f['min_p_valor']} · replicación IS→OOS ≥ "
             f"{f['min_replicacion']} · N efectivo de maestros ≥ {f['min_n_efectivo']}.")
    L.append("")

    if validas:
        L.append(f"## Resultado: {len(validas)} combinaciones VÁLIDAS")
        L.append("")
        L.append("Las siguientes combinaciones pasaron el filtro de validez. Se pueden imitar con respaldo estadístico.")
        L.append("")
    else:
        L.append("## Resultado: ninguna combinación pasó la validez")
        L.append("")
        L.append("Con este margen de modelado y estas ventanas, **ninguna** (segmento × estrategia) supera el filtro. "
                 "Esto es información útil: el mercado no es imitable de forma estadísticamente robusta con los datos "
                 "actuales. Las mejores candidatas (más abajo) son las menos malas, pero NO pasan la barrera.")
        L.append("")

    L.append("## Ranking de combinaciones (válidas primero)")
    L.append("")
    filas = [[
        c["segmento"], c["estrategia"], c["n_maestros"], c["n_efectivo"],
        ", ".join(c["codigos"]), _fmt(c["mediana_relativa_top"]),
        _fmt(c["mediana_margen_absoluto"]), _fmt(c["p_valor"], 4),
        "—" if c["ratio_replicacion"] is None else _fmt(c["ratio_replicacion"], 2),
        "sí" if c["valida"] else "no",
        "sí" if c["kill_switch"] else "no",
    ] for c in combos]
    L.append(_tabla(["Segmento", "Estrategia", "N maestros", "N efectivo", "Códigos",
                     "Relativo top (COP/kWh)", "Margen abs. mediana (COP/kWh)",
                     "p-valor", "Replicación IS→OOS", "Válida", "Kill-switch"], filas))
    L.append("")
    L.append("**Lectura:** *Relativo top* es la mediana del margen relativo al segmento del top-N (positivo = los "
             "maestros superaron a su segmento). *Válida* combina p-valor, replicación y N efectivo. *Kill-switch* "
             "indica si el drawdown del período superó el umbral de protección.")
    return "\n".join(L)


def guardar(barrido: dict, cfg: dict) -> Path:
    md = renderizar(barrido)
    destino = BASE_DIR / cfg["asistente"]["salida_barrido"]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(md, encoding="utf-8")
    return destino