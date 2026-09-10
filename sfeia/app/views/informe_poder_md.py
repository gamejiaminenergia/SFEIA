"""VIEW: informe del experimento de poder estadístico (Ruta C).

Recibe el resultado de `EstudioPoder.ejecutar` y produce
`docs/experimento_poder_estadistico.md` (raíz). Jamás consulta la BD.
"""
from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]

ADVERTENCIA = (
    "> El margen es un artefacto de modelado (Pv=350 COP/kWh fijo). La selección usa el margen relativo al "
    "segmento. Ningún valor es dinero real."
)


def _tabla(encabezados: list[str], filas: list[list]) -> str:
    salida = ["| " + " | ".join(encabezados) + " |", "|" + "|".join("---" for _ in encabezados) + "|"]
    for fila in filas:
        salida.append("| " + " | ".join(str(c) for c in fila) + " |")
    return "\n".join(salida)


def renderizar(res: dict) -> str:
    L = ["# Experimento de poder estadístico (Ruta C)", "", ADVERTENCIA, "",
         "Pregunta: ¿la señal operable que encontró el harness es un artefacto de bajo poder estadístico o de "
         "selección del pool? Las variantes usan el mismo premio C16-C18 relativo:",
         "",
         "- **C1** bootstrap con n_boot=2000 (más simulaciones).",
         "- **C2** ventana larga (365 d): más días por agente, mediana más precisa.",
         "- **C3** pool entre segmentos: la nula se construye sobre TODA la estrategia, no solo el segmento.",
         "",
         "## Combinaciones de ejemplo",
         "",
         "| Ventana | Nota | Segmento · Estrategia | N agentes | p (n_boot=2000) | p (pool entre segmentos) |",
         "|---|---|---|---|---|---|"]
    for f in res["filas"]:
        L.append(f"| {f['ventana']} | {f['nota']} | {f['segmento']} · {f['estrategia']} | "
                 f"{f['n_agentes']} | {f['p_n_boot2000']} | {f['p_pool_entre_segmentos']} |")
    L += ["", "## Ventana larga (C2)", "", "| Ventana | Nota | N agentes | p (n_boot=2000) |",
          "|---|---|---|---|"]
    lo = res["largo"]
    L.append(f"| {lo['ventana']} | {lo['nota']} | {lo['n_agentes']} | {lo['p_n_boot2000']} |")
    L += ["", "**Lectura:** si el p-valor operable se mantiene ≤ 0.05 con más simulaciones, en ventana larga y con "
          "una nula más amplia (pool entre segmentos), la señal NO es un artefacto de poder ni de selección del pool.",
          "", "---", "_Generado por `python -m sfeia.main --poder`. No editar a mano._"]
    return "\n".join(L)


def guardar(res: dict, cfg: dict) -> Path:
    destino = BASE_DIR / cfg["asistente"]["poder"]["salida"]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(renderizar(res), encoding="utf-8")
    return destino