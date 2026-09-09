"""Estudio híbrido diario: estrategias por agente-día (K-Means pooled) + ranking.

Lógica pura (sin acceso a BD): recibe las filas diarias del repositorio y la
config, y produce la matriz de agentes-día, el desempeño diario (margen estimado
por kWh, lógica C16–C18 sobre C15 diario), el clustering k-means pooled sobre
los ~65×212 agentes-día, el ranking diario de estrategias y el balance del
período. El controlador (fase_diaria) es quien consulta la BD.

Lo mejor de cada estudio anterior:
- k-means (estudio no supervisado): agrupación sin umbrales/reglas manuales,
  elección de k por silhouette, seed fija reproducible.
- benchmark F1–F6: modelo financiero (margen por kWh) como métrica de desempeño
  y segmentación por tamaño como contexto.
Nuevo: granularidad diaria y ranking temporal de estrategias.
"""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from app.models.entities import AgenteDia, BalanceEstrategia, PerfilEstrategia
from app.services import clustering
from app.services.kpi_cartera import modelo_financiero


def clave(codigo: str, dia: object) -> str:
    return f"{codigo}|{dia}"


def construir_agente_dia(rows: list[dict]) -> dict[str, dict]:
    """Convierte las filas diarias del repo en un dict keyed por 'codigo|dia'."""
    out: dict[str, dict] = {}
    for r in rows:
        k = clave(r["agente"], r["dia"])
        out[k] = {
            "codigo": r["agente"],
            "dia": r["dia"],
            "dema_kwh": float(r["dema_kwh"] or 0.0),
            "dema_reg_kwh": float(r["dema_reg_kwh"] or 0.0),
            "dema_noreg_kwh": float(r["dema_noreg_kwh"] or 0.0),
            "comp_cont_kwh": float(r["comp_cont_kwh"] or 0.0),
            "comp_cont_reg_kwh": float(r["comp_cont_reg_kwh"] or 0.0),
            "vent_cont_kwh": float(r["vent_cont_kwh"] or 0.0),
            "comp_bolsa_kwh": float(r["comp_bolsa_kwh"] or 0.0),
            "vent_bolsa_kwh": float(r["vent_bolsa_kwh"] or 0.0),
            "comp_sicep_kwh": float(r["comp_sicep_kwh"] or 0.0),
            "prec_cont": float(r["prec_cont_cop_kwh"] or 0.0),
            "prec_bolsa": float(r["prec_bolsa_cop_kwh"] or 0.0),
            "prec_escasez": float(r["prec_escasez_cop_kwh"] or 0.0),
        }
    return out


def features_diarias(ad: dict, clip_pct_sicep: float = 100.0) -> dict:
    """Features del agente-día en escala original (las 6 del estudio k-means)."""
    dema_kwh = ad["dema_kwh"]
    dema_gwh = dema_kwh / 1e6
    total = ad["dema_reg_kwh"] + ad["dema_noreg_kwh"]
    pct_noreg = ad["dema_noreg_kwh"] / total * 100 if total else 0.0
    pct_cobertura = ad["comp_cont_kwh"] / dema_kwh * 100 if dema_kwh else 0.0
    pct_exposicion = ad["comp_bolsa_kwh"] / dema_kwh * 100 if dema_kwh else 0.0
    reg_comp = ad["comp_cont_reg_kwh"]
    pct_sicep = ad["comp_sicep_kwh"] / reg_comp * 100 if reg_comp else 0.0
    # CompContEnerSICEP puede incluir compras no reguladas y exceder el 100 %:
    # se techa en clip_pct_sicep para no producir valores espurios (anomalías diarias).
    pct_sicep = min(pct_sicep, clip_pct_sicep)
    tiene_sicep = 1.0 if reg_comp > 0 else 0.0
    return {
        "dema_gwh": round(dema_gwh, 4),
        "log_dema": round(math.log1p(dema_gwh), 4),
        "pct_noreg": round(pct_noreg, 2),
        "pct_cobertura": round(pct_cobertura, 2),
        "pct_exposicion": round(pct_exposicion, 2),
        "pct_sicep": round(pct_sicep, 2),
        "tiene_sicep": tiene_sicep,
    }


def aplicar_clip_margen(agentedia: dict[str, dict], limite: float | None) -> None:
    """Winsoriza el margen por kWh de cada agente-día a [-limite, +limite].

    Los traders con volumen transado muy superior a su demanda (sobrecobertura)
    producen márgenes por kWh desproporcionados (artefacto del denominador
    `demanda`); se techan para que el ranking sea robusto y comparable.
    """
    if not limite:
        return
    for ad in agentedia.values():
        m = ad["desempeno"]["margen_por_kwh_cop"]
        ad["desempeno"]["margen_por_kwh_cop"] = max(-limite, min(limite, m))


def desempeno_diario(ad: dict, params: dict) -> dict:
    """Margen estimado por kWh del agente-día (lógica C16–C18 sobre C15 diario).

    Valora compras/ventas con los precios diarios de sistema (contratos y
    bolsa): no existe precio por agente en elecdb. Pv (tarifa de venta) es un
    parámetro fijo de modelado (artefacto, se reporta como tal).
    """
    prec_cont = ad["prec_cont"]
    prec_bolsa = ad["prec_bolsa"]
    val_comp_cont = ad["comp_cont_kwh"] * prec_cont
    val_comp_bolsa = ad["comp_bolsa_kwh"] * prec_bolsa
    val_vent_cont = ad["vent_cont_kwh"] * prec_cont
    val_vent_bolsa = ad["vent_bolsa_kwh"] * prec_bolsa
    ag = {
        "dema_kwh": ad["dema_kwh"],
        "compra_bolsa_kwh": ad["comp_bolsa_kwh"],
        "venta_bolsa_kwh": ad["vent_bolsa_kwh"],
        "compra_cont_kwh": ad["comp_cont_kwh"],
        "venta_cont_kwh": ad["vent_cont_kwh"],
        "exposicion_neta_cop": (val_comp_cont + val_comp_bolsa) - (val_vent_cont + val_vent_bolsa),
        "egreso_energia_cop": val_comp_cont + val_comp_bolsa,
    }
    return modelo_financiero(ag, params)


def construir_matriz_diaria(
    agentedia: dict[str, dict],
    features: list[str],
    transformes: dict[str, tuple[str, object]] | None = None,
    clip_sobrecobertura: float | None = None,
) -> tuple[np.ndarray, list[str], list[str]]:
    """Matriz X (n×p) sobre la población pooled de agentes-día.

    Devuelve (X float64, etiquetas= claves 'codigo|dia' ordenadas, nombres de
    features). Las transformaciones (log/clip) son las mismas del estudio k-means.
    """
    agregados = {k: ad["features"] for k, ad in agentedia.items()}
    return clustering.construir_matriz(
        agregados,
        features,
        clip_sobrecobertura=clip_sobrecobertura,
        transformes=transformes,
    )


def elegir_k_diario(
    X: np.ndarray,
    k_min: int,
    k_max: int,
    semilla: int,
    submuestra: int | None = None,
) -> list[dict]:
    """Silhouette/inercia por k sobre una submuestra determinista (n agentes-día grande).

    El O(n²) de silhouette sobre ~13 800 filas se evita muestreando con
    `random_state` fijo; el k resultante se aplica luego sobre la matriz completa.
    """
    n = X.shape[0]
    if submuestra and submuestra < n:
        rng = np.random.default_rng(semilla)
        idx = np.sort(rng.choice(n, size=int(submuestra), replace=False))
        Xk = X[idx]
    else:
        Xk = X
    return clustering.elegir_k(Xk, k_min, k_max, semilla)


def perfilar_estrategias(
    agentedia: dict[str, dict],
    etiquetas: list[str],
    labels: np.ndarray,
    features: list[str],
    segmento_por_codigo: dict[str, str],
) -> dict[int, PerfilEstrategia]:
    """Perfil por arquetipo en escala original + composición por segmento F-1."""
    perfiles: dict[int, PerfilEstrategia] = {}
    for cid in sorted({int(x) for x in labels}):
        idx = [i for i in range(len(labels)) if int(labels[i]) == cid]
        miembros = [etiquetas[i] for i in idx]
        medias: dict[str, float] = {}
        for f in features:
            vals = [agentedia[m]["features"][f] for m in miembros]
            medias[f] = round(sum(vals) / len(vals), 2) if vals else 0.0
        composicion: dict[str, int] = defaultdict(int)
        for m in miembros:
            seg = segmento_por_codigo.get(agentedia[m]["codigo"], "?")
            composicion[seg] += 1
        n_agentes = len({agentedia[m]["codigo"] for m in miembros})
        perfiles[cid] = PerfilEstrategia(
            cluster_id=cid,
            arquetipo=clustering.nombrar_arquetipo(medias),
            n=len(miembros),
            n_agentes=n_agentes,
            medias=medias,
            composicion_segmento=dict(composicion),
        )
    return perfiles


def construir_agente_dia_filas(
    agentedia: dict[str, dict],
    etiquetas: list[str],
    labels: np.ndarray,
    perfiles: dict[int, PerfilEstrategia],
    nombres: dict[str, str],
    segmento_por_codigo: dict[str, str],
) -> list[AgenteDia]:
    """Una fila AgenteDia por (agente, día) con su clúster, arquetipo y desempeño."""
    filas: list[AgenteDia] = []
    for i, k in enumerate(etiquetas):
        ad = agentedia[k]
        cid = int(labels[i])
        filas.append(AgenteDia(
            codigo=ad["codigo"],
            nombre=nombres.get(ad["codigo"], ad["codigo"]),
            dia=str(ad["dia"]),
            segmento=segmento_por_codigo.get(ad["codigo"], "?"),
            cluster_id=cid,
            arquetipo=perfiles[cid].arquetipo,
            features=dict(ad["features"]),
            margen_kwh=ad["desempeno"]["margen_por_kwh_cop"],
            costo_kwh=ad["desempeno"]["costo_energia_cop_kwh"],
        ))
    return filas


def ranking_diario(
    agentedia: dict[str, dict],
    etiquetas: list[str],
    labels: np.ndarray,
) -> dict[str, dict]:
    """Por día: mediana/media del margen por kWh de cada estrategia + rango.

    Devuelve {día: {clúster: {mediana, media, n, rango}}}, días en orden cronológico.
    """
    por_dia: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for i, k in enumerate(etiquetas):
        ad = agentedia[k]
        dia = str(ad["dia"])
        por_dia[dia][int(labels[i])].append(ad["desempeno"]["margen_por_kwh_cop"])

    out: dict[str, dict] = {}
    for dia in sorted(por_dia):
        res: dict[int, dict] = {}
        for cid, vals in por_dia[dia].items():
            orden = sorted(vals)
            res[cid] = {
                "mediana": round(orden[len(orden) // 2], 2),
                "media": round(sum(vals) / len(vals), 2),
                "n": len(vals),
            }
        rank = sorted(res, key=lambda c: (-res[c]["mediana"], -res[c]["media"], c))
        for rango, cid in enumerate(rank, start=1):
            res[cid]["rango"] = rango
        out[dia] = res
    return out


def balance_periodo(
    ranking: dict[str, dict],
    perfiles: dict[int, PerfilEstrategia],
) -> list[BalanceEstrategia]:
    """Balance del período por estrategia, ordenado por desempeño (ranking final)."""
    balances: list[BalanceEstrategia] = []
    for cid, p in perfiles.items():
        dias = [res[cid] for res in ranking.values() if cid in res]
        if not dias:
            continue
        medianas = [d["mediana"] for d in dias]
        n = len(dias)
        h1 = medianas[: n // 2]
        h2 = medianas[n // 2:]
        tendencia = (sum(h2) / len(h2) - sum(h1) / len(h1)) if h1 and h2 else 0.0
        balances.append(BalanceEstrategia(
            cluster_id=cid,
            arquetipo=p.arquetipo,
            dias=n,
            mediana_margen=round(sorted(medianas)[n // 2], 2),
            media_margen=round(sum(medianas) / n, 2),
            dias_puesto1=sum(1 for d in dias if d["rango"] == 1),
            pct_top3=round(sum(1 for d in dias if d["rango"] <= 3) / n * 100, 1),
            rango_promedio=round(sum(d["rango"] for d in dias) / n, 2),
            tendencia=round(tendencia, 2),
        ))
    balances.sort(key=lambda b: (-b.mediana_margen, b.cluster_id))
    return balances


def separar_atipicos(
    balance: list[BalanceEstrategia],
    n_dias: int,
    min_dias_pct: float = 0.0,
) -> tuple[list[BalanceEstrategia], list[BalanceEstrategia]]:
    """Separa del ranking las estrategias con presencia marginal (< min_dias_pct % de días).

    Una estrategia que aparece pocos días (p. ej. un agente con un par de días
    de datos espurios) puede dominar la mediana sin ser representativa del
    período; se reporta aparte como "caso atípico".
    """
    if not min_dias_pct or n_dias <= 0:
        return balance, []
    umbral = max(1, round(n_dias * min_dias_pct / 100))
    atipicos = [b for b in balance if b.dias < umbral]
    ranking = [b for b in balance if b.dias >= umbral]
    return ranking, atipicos


def matriz_puestos(ranking: dict[str, dict], k: int) -> dict[int, list[int]]:
    """Por estrategia: n días en cada puesto (1..k)."""
    out: dict[int, list[int]] = {cid: [0] * k for cid in range(k)}
    for res in ranking.values():
        for cid, d in res.items():
            if 0 <= cid < k and 1 <= d["rango"] <= k:
                out[cid][d["rango"] - 1] += 1
    return out


def ranking_diario_por_segmento(
    agentedia: dict[str, dict],
    etiquetas: list[str],
    labels: np.ndarray,
    segmento_por_codigo: dict[str, str],
) -> dict[str, dict[str, dict]]:
    """Ranking diario de estrategias POR segmento (GRANDE/MEDIANO/PEQUEÑO).

    Para cada segmento y día se consideran solo los agentes-día de ese segmento:
    se agrupan por estrategia y se ordenan por la mediana del margen. Devuelve
    {segmento: {día: {clúster: {mediana, media, n, rango}}}}.
    """
    por_seg_dia: dict[str, dict[str, dict[int, list[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    for i, k in enumerate(etiquetas):
        ad = agentedia[k]
        seg = segmento_por_codigo.get(ad["codigo"], "?")
        dia = str(ad["dia"])
        por_seg_dia[seg][dia][int(labels[i])].append(ad["desempeno"]["margen_por_kwh_cop"])

    out: dict[str, dict[str, dict]] = {}
    for seg in sorted(por_seg_dia):
        por_dia: dict[str, dict] = {}
        for dia in sorted(por_seg_dia[seg]):
            res: dict[int, dict] = {}
            for cid, vals in por_seg_dia[seg][dia].items():
                orden = sorted(vals)
                res[cid] = {
                    "mediana": round(orden[len(orden) // 2], 2),
                    "media": round(sum(vals) / len(vals), 2),
                    "n": len(vals),
                }
            rank = sorted(res, key=lambda c: (-res[c]["mediana"], -res[c]["media"], c))
            for rango, cid in enumerate(rank, start=1):
                res[cid]["rango"] = rango
            por_dia[dia] = res
        out[seg] = por_dia
    return out


def balance_por_segmento(
    ranking_por_segmento: dict[str, dict[str, dict]],
    perfiles: dict[int, PerfilEstrategia],
    n_dias: int,
    min_dias_pct: float = 0.0,
) -> dict[str, dict]:
    """Balance del período por segmento.

    Devuelve {segmento: {"balance": [...], "atipicos": [...]}}; el guard de
    presencia mínima se aplica dentro de cada segmento.
    """
    out: dict[str, dict] = {}
    for seg, ranking in ranking_por_segmento.items():
        balance = balance_periodo(ranking, perfiles)
        ranking_b, atipicos = separar_atipicos(balance, n_dias, min_dias_pct)
        out[seg] = {"balance": ranking_b, "atipicos": atipicos}
    return out


def matriz_estrategia_x_segmento(
    ranking_por_segmento: dict[str, dict[str, dict]],
    perfiles: dict[int, PerfilEstrategia],
) -> dict[int, dict[str, dict]]:
    """Matriz estrategia × segmento: mediana/media del margen diario.

    Coherente con balance_por_segmento: para cada estrategia y segmento se toma
    la mediana del margen de cada día (la misma del ranking diario) y se
    consolida. Devuelve {clúster: {segmento: {mediana, media, dias}}}.
    """
    out: dict[int, dict[str, dict]] = {}
    for seg, por_dia in ranking_por_segmento.items():
        for cid in perfiles:
            vals = [res[cid]["mediana"] for res in por_dia.values() if cid in res]
            if not vals:
                continue
            out.setdefault(cid, {})[seg] = {
                "mediana": round(sorted(vals)[len(vals) // 2], 2),
                "media": round(sum(vals) / len(vals), 2),
                "dias": len(vals),
            }
    return out