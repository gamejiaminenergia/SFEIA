"""CONTROLLER: experimento de poder estadístico (Ruta C del plan).

Responde: '¿la señal operable que encontró el harness es un artefacto de bajo
poder estadístico o de selección?'. Variantes (todas con el mismo premio
C16-C18 relativo):

- C1 Bootstrap con más simulaciones (n_boot=2000): el p-valor operable se
  mantiene ≤ 0.05 → no es un artefacto de pocas simulaciones.
- C2 Ventana larga (365 d): la selección y el bootstrap sobre un año completo
  (más días por agente, mediana más precisa) mantienen la señal.
- C3 Pool entre segmentos: la nula se construye sobre TODA la estrategia (no
  solo el segmento objetivo); si el mejor agente del segmento sigue superando
  esa nula más amplia, la señal no depende del pool.

Salida: `docs/experimento_poder_estadistico.md` + `data/experimento_poder.csv`.
"""
from __future__ import annotations

import copy
from datetime import date, timedelta

from sfeia.app.controllers.fase_asistente import FaseAsistente
from sfeia.app.services import maestros


def _iso(d: date) -> str:
    return d.isoformat()


def _fecha(d: str) -> date:
    return date.fromisoformat(d)


class EstudioPoder:
    def __init__(self, repo, cfg: dict):
        self.repo = repo
        self.cfg = cfg

    def ejecutar(self) -> dict:
        a_cfg = self.cfg["asistente"]
        params = self.cfg["modelo_financiero"]
        clip = self.cfg["diario"].get("clip_margen_cop_kwh")
        semilla = int(self.cfg["diario"].get("random_state", 42))
        relativo = bool(a_cfg.get("seleccion_por_relativo", True))
        top = int(a_cfg.get("top_por_defecto", 10))
        min_dias = float(a_cfg["min_dias_pct"])
        fa = FaseAsistente(self.repo, self.cfg)

        # Combinaciones ejemplo (regímenes Niño 2015-16 y benigno 2019)
        ejemplos = [
            {"ini": "2015-01-01", "fin": "2015-03-31", "segmento": "PEQUEÑO",
             "estrategia": "Comercializador regulado", "nota": "Niño 2015 (escasez)"},
            {"ini": "2016-04-25", "fin": "2016-07-23", "segmento": "PEQUEÑO",
             "estrategia": "Trader expuesto a bolsa (sin cobertura)", "nota": "Niño 2016"},
            {"ini": "2019-03-11", "fin": "2019-06-08", "segmento": "PEQUEÑO",
             "estrategia": "Comercializador regulado", "nota": "benigno 2019"},
        ]

        filas: list[dict] = []
        for e in ejemplos:
            w = {"estudio_ini": e["ini"], "estudio_fin": e["fin"],
                 "impacto_ini": _iso(_fecha(e["fin"]) + timedelta(days=1)),
                 "impacto_fin": _iso(_fecha(e["fin"]) + timedelta(days=7))}
            datos = fa._correr_estudio(w["estudio_ini"], w["estudio_fin"])
            d = datos["diario"]
            # C1: bootstrap fino (n_boot alto) sobre la ventana estándar
            b_fino = maestros.bootstrap_skill_luck(
                d["agentes"], e["segmento"], e["estrategia"], top, d["n_dias"],
                n_boot=2000, semilla=semilla, min_dias_pct=min_dias, relativo=relativo,
            )
            # C3: pool entre segmentos (nula sobre toda la estrategia)
            b_cross = _bootstrap_cross_segmento(
                d["agentes"], e["segmento"], e["estrategia"], top, 1000, semilla, min_dias, relativo
            )
            filas.append({
                "ventana": f"{e['ini']}..{e['fin']}", "nota": e["nota"],
                "segmento": e["segmento"], "estrategia": e["estrategia"],
                "n_agentes": b_fino["n_agentes_candidatos"] if b_fino else None,
                "p_n_boot2000": b_fino["p_valor"] if b_fino else None,
                "p_pool_entre_segmentos": b_cross["p_valor"] if b_cross else None,
            })

        # C2: ventana larga (365 d) sobre el combo más recurrente
        d365 = fa._correr_estudio("2015-01-01", "2015-12-31")["diario"]
        b_365 = maestros.bootstrap_skill_luck(
            d365["agentes"], "PEQUEÑO", "Comercializador regulado", top, d365["n_dias"],
            n_boot=1000, semilla=semilla, min_dias_pct=min_dias, relativo=relativo,
        )
        largo = {
            "ventana": "2015-01-01..2015-12-31", "nota": "ventana larga (365 d) · Comercializador regulado PEQUEÑO",
            "n_agentes": b_365["n_agentes_candidatos"] if b_365 else None,
            "p_n_boot2000": b_365["p_valor"] if b_365 else None,
            "p_pool_entre_segmentos": None,
        }
        return {"filas": filas, "largo": largo}


def _bootstrap_cross_segmento(
    agentes, segmento_objetivo, estrategia, top, n_boot, semilla, min_dias_pct, relativo,
) -> dict | None:
    """Nula construida sobre TODOS los agentes de la estrategia (todos los
    segmentos): si el mejor agente del segmento objetivo supera esa nula más
    amplia, la señal no depende del pool restringido al segmento."""
    import numpy as np

    def _mediana(vals):
        return sorted(vals)[len(vals) // 2]

    seg_dia: dict[tuple[str, str], list[float]] = {}
    for a in agentes:
        seg_dia.setdefault((a.segmento, a.dia), []).append(a.margen_kwh)
    seg_dia = {k: _mediana(v) for k, v in seg_dia.items()}

    series_obj: dict[str, list[float]] = {}
    pool: list[float] = []
    for a in agentes:
        if a.arquetipo != estrategia:
            continue
        rel = a.margen_kwh - seg_dia.get((a.segmento, a.dia), a.margen_kwh) if relativo else a.margen_kwh
        if a.segmento == segmento_objetivo:
            series_obj.setdefault(a.codigo, []).append(rel)
        pool.append(rel)
    if not series_obj or not pool:
        return None
    counts = [len(v) for v in series_obj.values()]
    real = max(_mediana(v) for v in series_obj.values())
    rng = np.random.default_rng(semilla)
    nulos = []
    for _ in range(n_boot):
        ag = []
        for c in counts:
            s = sorted(rng.choice(pool, size=c, replace=True).tolist())
            ag.append(s[len(s) // 2])
        ag.sort(reverse=True)
        nulos.append(ag[0])
    p = (sum(1 for x in nulos if x >= real) + 1) / (n_boot + 1)
    return {"p_valor": round(p, 4), "n_agentes_candidatos": len(series_obj), "n_pool": len(pool)}