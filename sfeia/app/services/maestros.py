"""Selección de los maestros del asistente (lógica pura).

Dado el resultado del estudio híbrido diario sobre la ventana de estudio,
elige a los **top-N** agentes del (segmento, estrategia) objetivo por mediana
del margen por kWh, con guarda de presencia mínima en la estrategia.

Incluye las adiciones del plan de investigación (P0):
- `bootstrap_skill_luck`: separa skill de luck (¿el top-N real supera al azar?).
- `persistencia_seleccion`: ¿la selección hecha en sub-estudio se sostiene en
  una sub-validación independiente (holdout)?
- `detectar_duplicados` / `n_efectivo`: deduplican maestros con series de
  margen correlacionadas (el N efectivo < N nominal).
- `pesos_maestros`: pesos para agregar perfiles (P1.2) en vez de elegir un
  top-N duro (Follow-the-Leader).

SOLID: responsabilidad única — quiénes son los maestros a imitar y con qué
confianza.
"""
from __future__ import annotations

import math
from statistics import median

from sfeia.app.models.entities import AgenteMaestro


def _coincide(arquetipo: str, estrategia: str) -> bool:
    return arquetipo.strip().lower() == estrategia.strip().lower()


def _mediana(vals: list[float]) -> float:
    orden = sorted(vals)
    return orden[len(orden) // 2]


def _drawdown_max(vals: list[float]) -> float:
    """Peor caída pico→valle de la serie acumulada de márgenes (COP/kWh)."""
    acum = 0.0
    pico = 0.0
    dd = 0.0
    for v in vals:
        acum += v
        pico = max(pico, acum)
        dd = max(dd, pico - acum)
    return dd


def _metricas_riesgo(vals: list[float]) -> tuple[float, float, float]:
    """(% días con pérdida, drawdown máximo, mediana del margen en días malos)."""
    if not vals:
        return 0.0, 0.0, 0.0
    perdidas = [v for v in vals if v < 0]
    pct = len(perdidas) / len(vals) * 100.0
    return (round(pct, 1), round(_drawdown_max(vals), 2),
            round(_mediana(perdidas), 2) if perdidas else 0.0)


def _mediana_segmento_por_dia(agentes: list, segmento: str) -> dict[str, float]:
    """Mediana del margen por día de TODOS los agentes del segmento (benchmark)."""
    por_dia: dict[str, list[float]] = {}
    for a in agentes:
        if a.segmento != segmento:
            continue
        por_dia.setdefault(a.dia, []).append(a.margen_kwh)
    return {dia: _mediana(vals) for dia, vals in por_dia.items() if vals}


def seleccionar_maestros(
    agentes: list,
    segmento: str,
    estrategia: str,
    top: int,
    n_dias_estudio: int,
    min_dias_pct: float = 0.0,
    relativo: bool = False,
) -> list[AgenteMaestro]:
    """Top-N agentes del (segmento, estrategia) por desempeño en la ventana.

    `agentes` son los `AgenteDia` del estudio (tienen segmento, arquetipo y
    margen_kwh). Se agrupa por código y se ordena por desempeño; los agentes
    con presencia marginal en la estrategia quedan fuera.

    Con `relativo=True` (S1) el ranking usa el **margen relativo al segmento**
    (margen del agente − mediana del segmento el mismo día): cancela el
    artefacto Pv=350 y el régimen de mercado. La mediana absoluta y las
    métricas de riesgo se siguen reportando para contexto.
    """
    series: dict[str, list[tuple[str, float]]] = {}
    nombres: dict[str, str] = {}
    for a in agentes:
        if a.segmento != segmento or not _coincide(a.arquetipo, estrategia):
            continue
        series.setdefault(a.codigo, []).append((a.dia, a.margen_kwh))
        nombres[a.codigo] = a.nombre

    umbral = max(1, round(n_dias_estudio * min_dias_pct / 100)) if min_dias_pct and n_dias_estudio else 0
    seg_dia = _mediana_segmento_por_dia(agentes, segmento) if relativo else {}

    candidatos: list[AgenteMaestro] = []
    for codigo, pares in series.items():
        n = len(pares)
        if n < umbral:
            continue
        vals = [m for _, m in pares]
        pct, dd, downside = _metricas_riesgo(vals)
        orden = sorted(vals)
        mediana_abs = round(orden[len(orden) // 2], 2)
        media_abs = round(sum(vals) / n, 2)
        if relativo:
            rels = [m - seg_dia.get(dia, m) for dia, m in pares]
            ro = sorted(rels)
            mediana_rel = round(ro[len(ro) // 2], 2)
            pct_supera = round(sum(1 for r in rels if r > 0) / n * 100.0, 1)
        else:
            mediana_rel, pct_supera = 0.0, 0.0
        candidatos.append(AgenteMaestro(
            codigo=codigo,
            nombre=nombres.get(codigo, codigo),
            n_dias=n,
            mediana_margen=mediana_abs,
            media_margen=media_abs,
            pct_dias_perdida=pct,
            drawdown_max=dd,
            downside_mediana=downside,
            mediana_relativa=mediana_rel,
            pct_dias_supera_segmento=pct_supera,
        ))

    if relativo:
        candidatos.sort(key=lambda m: (-m.mediana_relativa, -m.n_dias, m.codigo))
    else:
        candidatos.sort(key=lambda m: (-m.mediana_margen, -m.n_dias, m.codigo))
    return candidatos[:top]


def bootstrap_skill_luck(
    agentes: list,
    segmento: str,
    estrategia: str,
    top: int,
    n_dias_estudio: int,
    n_boot: int = 1000,
    semilla: int = 42,
    min_dias_pct: float = 0.0,
    relativo: bool = False,
) -> dict | None:
    """¿El top-N real supera lo que el azar produciría? (bootstrap).

    Hipótesis nula: no hay habilidad — dentro del (segmento, estrategia) el
    margen (o el margen relativo al segmento con `relativo=True`) de cualquier
    agente-día es intercambiable. Se re-muestrea el pool con reemplazo
    preservando el nº de días de cada agente, se recalcula el mejor agente
    (mediana) del top-N, y se compara con el mejor real. El percentil/p-valor
    responde: '¿qué tan probable es que el mejor maestro sea solo suerte?'.

    Devuelve None si no hay candidatos elegibles (sin comparación posible).
    """
    import numpy as np

    series: dict[str, list[tuple[str, float]]] = {}
    for a in agentes:
        if a.segmento != segmento or not _coincide(a.arquetipo, estrategia):
            continue
        series.setdefault(a.codigo, []).append((a.dia, a.margen_kwh))
    umbral = max(1, round(n_dias_estudio * min_dias_pct / 100)) if min_dias_pct and n_dias_estudio else 0
    series = {c: v for c, v in series.items() if len(v) >= umbral}
    if not series:
        return None

    seg_dia = _mediana_segmento_por_dia(agentes, segmento) if relativo else {}

    def _vals(pares: list[tuple[str, float]]) -> list[float]:
        if relativo:
            return [m - seg_dia.get(dia, m) for dia, m in pares]
        return [m for _, m in pares]

    medianas_reales = sorted(_mediana(_vals(v)) for v in series.values())
    real_stat = medianas_reales[-1]  # mejor maestro (mediana mayor)

    pool = [x for v in series.values() for x in _vals(v)]
    counts = [len(v) for v in series.values()]
    rng = np.random.default_rng(semilla)
    nulos: list[float] = []
    for _ in range(n_boot):
        ag = []
        for c in counts:
            s = sorted(rng.choice(pool, size=c, replace=True).tolist())
            ag.append(s[len(s) // 2])
        ag.sort(reverse=True)
        nulos.append(ag[0])

    p_valor = (sum(1 for x in nulos if x >= real_stat) + 1) / (n_boot + 1)
    percentil = sum(1 for x in nulos if x <= real_stat) / n_boot * 100.0
    return {
        "n_agentes_candidatos": len(series),
        "n_boot": n_boot,
        "mejor_maestro_real": round(real_stat, 2),
        "nulo_p50": round(float(np.median(nulos)), 2),
        "nulo_p95": round(float(np.percentile(nulos, 95)), 2),
        "p_valor": round(p_valor, 4),
        "percentil_real": round(percentil, 1),
    }


def alternativa_recomendada(
    agentes: list,
    objetivo_segmento: str,
    objetivo_estrategia: str,
    n_dias_estudio: int,
    min_dias_pct: float = 0.0,
    top: int = 5,
) -> dict | None:
    """S3: mejor combinación (segmento, estrategia) distinta de la objetivo.

    Barre todos los (segmento × estrategia) presentes en el estudio, los
    rankea por la mediana del margen **relativo** del top-N y devuelve la mejor
    combinación para proponerla como alternativa cuando la pedida no valida.
    """
    combos: dict[tuple[str, str], list] = {}
    for a in agentes:
        if a.segmento == objetivo_segmento and _coincide(a.arquetipo, objetivo_estrategia):
            continue
        combos.setdefault((a.segmento, a.arquetipo), []).append(a)

    mejores: list[dict] = []
    for (seg, est), _ in combos.items():
        ms = seleccionar_maestros(agentes, seg, est, top, n_dias_estudio, min_dias_pct, relativo=True)
        if not ms:
            continue
        mejores.append({
            "segmento": seg,
            "estrategia": est,
            "codigos": [m.codigo for m in ms],
            "n_maestros": len(ms),
            "mejor_mediana_relativa": ms[0].mediana_relativa,
            "mediana_relativa_top": round(_mediana([m.mediana_relativa for m in ms]), 2),
            "mediana_margen_absoluto_top": round(_mediana([m.mediana_margen for m in ms]), 2),
        })
    if not mejores:
        return None
    mejores.sort(key=lambda x: (-x["mediana_relativa_top"], -x["n_maestros"], x["segmento"], x["estrategia"]))
    return mejores[0]


def persistencia_seleccion(
    agentes_validacion: list,
    segmento: str,
    estrategia: str,
    codigos_maestros: set[str],
    n_dias_validacion: int,
    min_dias_pct: float = 0.0,
) -> dict:
    """¿La selección del sub-estudio se sostiene en la sub-validación? (holdout).

    Re-rankea los agentes del (segmento, estrategia) en la ventana de
    validación (independiente de la selección) y mide cuántos maestros siguen
    en la parte alta del ranking (percentil < 50) y cuántos superan la mediana
    del segmento. Un valor ≈ azar (50 %) indica que la selección no generaliza.
    """
    margenes: dict[str, list[float]] = {}
    for a in agentes_validacion:
        if a.segmento != segmento or not _coincide(a.arquetipo, estrategia):
            continue
        margenes.setdefault(a.codigo, []).append(a.margen_kwh)
    umbral = max(1, round(n_dias_validacion * min_dias_pct / 100)) if min_dias_pct and n_dias_validacion else 0
    margenes = {c: v for c, v in margenes.items() if len(v) >= umbral}
    if not margenes:
        return {"n_validacion": 0, "pct_persistencia": None, "mediana_persistencia": None}

    ranking = sorted(((c, _mediana(v)) for c, v in margenes.items()), key=lambda x: -x[1])
    n = len(ranking)
    pos: dict[str, int] = {c: i for i, (c, _) in enumerate(ranking)}
    persisten = [c for c in codigos_maestros if c in pos and pos[c] < n / 2]
    pct = len(persisten) / len(codigos_maestros) * 100.0 if codigos_maestros else 0.0
    med = median([pos[c] / max(n - 1, 1) for c in codigos_maestros if c in pos]) if any(
        c in pos for c in codigos_maestros) else None
    return {
        "n_validacion": n,
        "n_maestros_rankeados": sum(1 for c in codigos_maestros if c in pos),
        "pct_persistencia": round(pct, 1),
        "mediana_percentil": round(med * 100.0, 1) if med is not None else None,
    }


def pesos_maestros(
    maestros: list[AgenteMaestro],
    mediana_segmento: float | None = None,
    eta: float = 1.0,
) -> dict[str, float]:
    """Pesos para agregar los perfiles de los maestros (P1.2, tipo EWA).

    Premia superar la mediana del segmento (no el nivel absoluto del artefacto)
    y la presencia (n_días). `eta` controla cuán concentrada está la mezcla.
    Devuelve {código: peso} normalizado a 1.
    """
    if not maestros:
        return {}
    base = [m.mediana_margen for m in maestros]
    referencia = mediana_segmento if mediana_segmento is not None else median(base)
    dispersion = max(max(base) - min(base), 1.0)
    nmax = max(m.n_dias for m in maestros) or 1
    scores = [
        (m.mediana_margen - referencia) / dispersion + 0.5 * (m.n_dias / nmax)
        for m in maestros
    ]
    ws = [math.exp(eta * s) for s in scores]
    tot = sum(ws) or 1.0
    return {m.codigo: w / tot for m, w in zip(maestros, ws)}


def _serie_diaria(agentes: list, codigo: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for a in agentes:
        if a.codigo == codigo:
            out[a.dia] = a.margen_kwh
    return out


def _correlacion(x: dict[str, float], y: dict[str, float]) -> float | None:
    comunes = [d for d in x if d in y and x[d] is not None and y[d] is not None]
    if len(comunes) < 3:
        return None
    xs = [x[d] for d in comunes]
    ys = [y[d] for d in comunes]
    nx, ny = len(xs), len(ys)
    mx, my = sum(xs) / nx, sum(ys) / ny
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(nx))
    den = (sum((a - mx) ** 2 for a in xs) ** 0.5) * (sum((b - my) ** 2 for b in ys) ** 0.5)
    if den == 0:
        return None
    return num / den


def detectar_duplicados(
    maestros: list[AgenteMaestro],
    agentes: list | None = None,
    umbral_corr: float = 0.9,
) -> list[list[str]]:
    """Agrupa maestros con comportamiento idéntico o casi idéntico.

    Dos criterios: (1) igual (mediana, media) de margen — datos espejo; (2) si
    se pasan `agentes`, correlación de la serie diaria de márgenes > umbral
    (misma estrategia al unísono). Contar cada uno como 'maestro' independiente
    infla el top-N.
    """
    grupos: dict[tuple[float, float], list[str]] = {}
    for m in maestros:
        grupos.setdefault((m.mediana_margen, m.media_margen), []).append(m.codigo)
    unidos: list[list[str]] = [codes for codes in grupos.values() if len(codes) > 1]

    if not agentes:
        return unidos

    series = {m.codigo: _serie_diaria(agentes, m.codigo) for m in maestros}
    codes = [m.codigo for m in maestros]
    for i in range(len(codes)):
        for j in range(i + 1, len(codes)):
            corr = _correlacion(series[codes[i]], series[codes[j]])
            if corr is None or corr <= umbral_corr:
                continue
            for g in unidos:
                if codes[i] in g or codes[j] in g:
                    g.extend([codes[i], codes[j]])
                    break
            else:
                unidos.append([codes[i], codes[j]])
    # dedupe dentro de cada grupo
    return [sorted(set(g)) for g in unidos]


def n_efectivo(
    maestros: list[AgenteMaestro],
    agentes: list | None = None,
    umbral_corr: float = 0.9,
) -> int:
    """N de maestros independientes tras deduplicar (mínimo 1 si hay maestros)."""
    if not maestros:
        return 0
    dups = detectar_duplicados(maestros, agentes, umbral_corr)
    redundantes = sum(len(g) - 1 for g in dups)
    return max(1, len(maestros) - redundantes)


def sensibilidad(
    agentes: list,
    segmento: str,
    estrategia: str,
    n_dias_estudio: int,
    tops: tuple[int, ...] = (3, 5, 7),
    min_dias_pcts: tuple[float, ...] = (10.0, 20.0, 30.0),
) -> dict[tuple[int, float], list[str]]:
    """Estabilidad del top-N frente a (top, min_dias_pct).

    Re-selecciona maestros con otras configuraciones sobre la **misma** ventana
    de estudio y devuelve { (top, min_dias_pct): [códigos] } para ver si los
    maestros cambian mucho (robustez de la selección).
    """
    out: dict[tuple[int, float], list[str]] = {}
    for top in tops:
        for mp in min_dias_pcts:
            ms = seleccionar_maestros(agentes, segmento, estrategia, top, n_dias_estudio, mp)
            out[(top, mp)] = [m.codigo for m in ms]
    return out