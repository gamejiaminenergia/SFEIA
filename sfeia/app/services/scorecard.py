"""Scorecard de aceptación del asistente imitador (lógica pura).

Define los gates del plan de aceptación (`docs/plan_aceptacion_imitador.md`):

- N0 integridad (tests/determinismo/sin look-ahead) se verifican fuera.
- N1 validez de la selección: V1 bootstrap p-valor · V2 N efectivo · V3 holdout ·
  V4 replicación IS→OOS · V5 DSR.
- N2 económico/riesgo: E1 % días gana al segmento · E2 sin kill-switch ·
  E3 EV histórico ≥ 0 · E4 capacidad.
- N3 robustez (walk-forward) se mide sobre la combinación confirmada.
- N4 fidelidad del clon (F1): MAE del perfil clonado vs. perfil realizado de los
  maestros en OOS (independiente del margen-artefacto).

SOLID: responsabilidad única — evaluar y medir la aceptación.
"""
from __future__ import annotations

from datetime import date, timedelta

FEATURES_FIDELIDAD = ["pct_cobertura", "pct_exposicion", "pct_noreg", "pct_sicep"]


def generar_grid(
    dias_estudio: int,
    dias_impacto: int,
    paso_dias: int,
    ini_min: date,
    fin_max: date,
) -> list[dict]:
    """Grid de ventanas rodantes estudio→impacto entre `ini_min` y `fin_max`.

    Cada ventana: estudio de `dias_estudio` terminando en t, impacto de
    `dias_impacto` contiguo y posterior. Avanza de `paso_dias` en `paso_dias`.
    """
    ventanas: list[dict] = []
    t = ini_min + timedelta(days=dias_estudio - 1)
    while True:
        estudio_fin = t
        estudio_ini = t - timedelta(days=dias_estudio - 1)
        impacto_ini = t + timedelta(days=1)
        impacto_fin = t + timedelta(days=dias_impacto)
        if impacto_fin > fin_max:
            break
        if estudio_ini >= ini_min:
            ventanas.append({
                "estudio_ini": estudio_ini.isoformat(),
                "estudio_fin": estudio_fin.isoformat(),
                "impacto_ini": impacto_ini.isoformat(),
                "impacto_fin": impacto_fin.isoformat(),
            })
        t += timedelta(days=paso_dias)
    return ventanas


def evaluar_gates(fila: dict, g: dict) -> dict:
    """Evalúa los gates N1/N2 de una fila de combinación (coarse o confirmada).

    `fila` trae: p_valor, n_efectivo, persistencia (None si no evaluada),
    ratio_replicacion, dsr, pct_gana_segmento, kill_switch, ev_historico,
    supera_capacidad. `g` trae los umbrales (`alpha`, `min_n_efectivo`, ...).
    Devuelve el detalle de cada gate y los veredictos parciales.
    """
    gates = {
        "V1_bootstrap": fila.get("p_valor") is not None and fila["p_valor"] <= g["alpha"],
        "V2_n_efectivo": (fila.get("n_efectivo") or 0) >= g["min_n_efectivo"],
        # V3 no evaluada (None) NO bloquea: se confirma en las candidatas.
        "V3_holdout": fila.get("persistencia") is None or fila["persistencia"] >= g["min_persistencia"],
        "V4_replicacion": fila.get("ratio_replicacion") is not None and fila["ratio_replicacion"] >= g["min_replicacion"],
        "V5_dsr": fila.get("dsr") is not None and fila["dsr"] >= g["min_dsr"],
        "E1_gana_segmento": fila.get("pct_gana_segmento") is not None and fila["pct_gana_segmento"] >= g["min_pct_gana_segmento"],
        "E2_sin_kill_switch": not bool(fila.get("kill_switch", False)),
        "E3_ev_historico": fila.get("ev_historico") is not None and fila["ev_historico"] >= g["min_ev_historico"],
        "E4_capacidad": not bool(fila.get("supera_capacidad", True)),
    }
    n1_cheap = all(gates[k] for k in ("V1_bootstrap", "V2_n_efectivo", "V4_replicacion", "V5_dsr"))
    n2 = all(gates[k] for k in ("E1_gana_segmento", "E2_sin_kill_switch", "E3_ev_historico", "E4_capacidad"))
    return {
        "gates": gates,
        "n1_cheap": n1_cheap,
        "n1_completo": n1_cheap and gates["V3_holdout"],
        "n2": n2,
        "valida_cheap": bool(n1_cheap and n2),
        "valida_final": bool(n1_cheap and gates["V3_holdout"] and n2),
    }


def fidelidad_mae(
    agentedia: dict[str, dict],
    politica,
    codigos_maestros: set[str],
    segmento_por_codigo: dict[str, str] | None = None,
    segmento: str | None = None,
    usar_spread_previo: bool = True,
    features: tuple[str, ...] = tuple(FEATURES_FIDELIDAD),
) -> dict:
    """N4/F1: MAE del perfil clonado vs. perfil realizado de los maestros (OOS).

    Por día de `agentedia` (impacto) se compara el perfil que la política
    recomienda (con el contexto ex-ante del día) contra la **mediana** del
    perfil realizado por los maestros ese mismo día. Independiente del margen:
    mide fidelidad conductual, no recompensa.

    Devuelve {feature: MAE, promedio: media de features}. Si `segmento` o
    `segmento_por_codigo` no se pasan, se usa solo la membresía de maestros.
    """
    from sfeia.app.services import clonacion

    precios: dict[str, tuple[float, float]] = {}
    for ad in agentedia.values():
        d = str(ad["dia"])
        if d not in precios:
            precios[d] = (ad["prec_cont"], ad["prec_bolsa"])
    fechas = sorted(precios)
    bolsa_prev = {fechas[i]: precios[fechas[i - 1]][1] for i in range(1, len(fechas))}

    por_dia: dict[str, list[dict]] = {}
    for ad in agentedia.values():
        if ad["codigo"] not in codigos_maestros:
            continue
        if segmento_por_codigo and segmento_por_codigo.get(ad["codigo"]) != segmento:
            continue
        por_dia.setdefault(str(ad["dia"]), []).append(ad["features"])

    recs: dict[str, object] = {}
    for d in fechas:
        spread = (bolsa_prev[d] - precios[d][0]) if (usar_spread_previo and d in bolsa_prev) \
            else (precios[d][1] - precios[d][0])
        recs[d] = clonacion.aplicar_politica(politica, spread)

    errs: dict[str, list[float]] = {f: [] for f in features}
    for d, filas in por_dia.items():
        if d not in recs:
            continue
        n = len(filas)
        med = {f: sorted(r[f] for r in filas)[n // 2] for f in features}
        for f in features:
            errs[f].append(abs(getattr(recs[d], f) - med[f]))

    out: dict[str, float | None] = {}
    for f in features:
        out[f] = round(sum(errs[f]) / len(errs[f]), 2) if errs[f] else None
    vals = [v for v in out.values() if v is not None]
    out["promedio"] = round(sum(vals) / len(vals), 2) if vals else None
    return out