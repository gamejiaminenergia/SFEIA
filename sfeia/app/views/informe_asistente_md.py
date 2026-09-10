"""VIEW: informe del asistente imitador en Markdown.

Recibe el resultado de `FaseAsistente` y la config, y produce
`docs/informe_asistente_imitador.md` (raíz del repo). Jamás consulta la BD.
Incluye medidas de riesgo (distribución de márgenes, drawdown, garantías),
escenarios de estrés sintéticos y robustez de la selección de maestros.
"""
from __future__ import annotations

from pathlib import Path

from sfeia.app.services.contexto import ordenar_bins

BASE_DIR = Path(__file__).resolve().parents[3]

ADVERTENCIA = (
    "> **Advertencia (léela antes que nada):** esto es un **ejercicio descriptivo sobre comportamiento pasado** con un "
    "margen de **modelado** (Pv=350 COP/kWh fijo, precios promedio de sistema). Los márgenes aquí son artefactos "
    "matemáticos para comparar estrategias entre sí, **no dinero real ni una recomendación de inversión**. No sustituye "
    "análisis financiero, regulatorio ni legal."
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


def _fmt_cop(v) -> str:
    if v is None:
        return "—"
    return f"{v:,.0f}".replace(",", " ")


def _tabla_maestros(r: dict) -> str:
    relativo = r["validez"].get("seleccion_por_relativo", True)
    filas = [[i + 1, m.codigo, m.nombre, m.n_dias, _fmt(m.mediana_margen), _fmt(m.media_margen),
              _fmt(m.mediana_relativa), _fmt(m.pct_dias_supera_segmento),
              _fmt(m.pct_dias_perdida), _fmt(m.drawdown_max), _fmt(m.downside_mediana)]
             for i, m in enumerate(r["maestros"])]
    encabezados = ["Pos.", "Código", "Comercializador", "Días en la estrategia",
                   "Mediana margen (COP/kWh)", "Media margen",
                   "Mediana relativa (COP/kWh)", "% días > segmento",
                   "% días pérdida", "Drawdown máx. (COP/kWh acum.)", "Mediana días malos (COP/kWh)"]
    return _tabla(encabezados, filas) + (
        "\n\n> **Selección por margen relativo al segmento** (S1): el ranking usa la *mediana relativa*"
        " (margen del agente − mediana del segmento el mismo día), que cancela el artefacto Pv=350. La mediana"
        " absoluta se reporta como contexto."
        if relativo else ""
    )


def _tabla_validez(r: dict) -> str:
    """Validez de la selección (P0): holdout, bootstrap, DSR, replicación."""
    v = r["validez"]
    L: list[str] = []
    filas: list[list] = []

    boot = v.get("bootstrap")
    if boot:
        sig = boot["p_valor"] <= v.get("alpha_significancia", 0.05)
        filas.append(["Bootstrap skill-vs-luck", "p-valor", _fmt(boot["p_valor"], 4),
                      "sí" if sig else "no"])
        filas.append(["", "Mejor maestro real (COP/kWh)", _fmt(boot["mejor_maestro_real"]), ""])
        filas.append(["", "Nulo p50 / p95 (COP/kWh)",
                      f"{_fmt(boot['nulo_p50'])} / {_fmt(boot['nulo_p95'])}", ""])
        filas.append(["", "Candidatos rankeados (trials)", str(boot["n_agentes_candidatos"]), ""])

    h = v.get("holdout")
    if h:
        pct = h.get("pct_persistencia")
        filas.append(["Holdout (sub-estudio → sub-validación)",
                      "% de maestros que siguen en la mitad superior",
                      "—" if pct is None else _fmt(pct),
                      "≥50 %" if (pct is not None and pct >= 50.0) else "<50 % (azar)"])
        filas.append(["", "Mediana del percentil de los maestros",
                      "—" if h.get("mediana_percentil") is None else _fmt(h["mediana_percentil"]), ""])

    rep = v.get("replicacion_is_oos")
    if rep:
        ratio = rep.get("ratio_replicacion")
        filas.append(["Replicación IS→OOS",
                      "mediana imitación estudio / impacto (COP/kWh)",
                      f"{_fmt(rep['mediana_imitacion_is'])} / {_fmt(rep['mediana_imitacion_oos'])}",
                      "—" if ratio is None else _fmt(ratio, 2)])
        filas.append(["", "Criterio de sistema sano", "≥ 50–70 %", ""])

    dsr = v.get("dsr")
    if dsr:
        filas.append(["DSR (corrige múltiples pruebas)",
                      f"Sharpe diario {_fmt(dsr['sharpe_diario'], 3)} · skew {_fmt(dsr['skew'])} · kurt {_fmt(dsr['kurt'])}",
                      _fmt(dsr["dsr"], 3), "sí" if dsr["significativo"] else "no"])

    if filas:
        L.append(_tabla(["Prueba", "Métrica", "Valor", "Pasa"], filas))
    if v.get("n_efectivo_maestros") is not None:
        L.append("")
        L.append(f"N efectivo de maestros (tras deduplicar correlacionados): **{v['n_efectivo_maestros']}** de "
                 f"{len(r['maestros'])}.")
    return "\n".join(L)


def _tabla_robustez(r: dict) -> str:
    sens = r["robustez"]["sensibilidad"]
    filas = []
    tops = sorted({k[0] for k in sens})
    mps = sorted({k[1] for k in sens})
    for mp in mps:
        fila = [f"{mp:.0f} %"]
        for top in tops:
            fila.append(", ".join(sens[(top, mp)]) if sens[(top, mp)] else "—")
        filas.append(fila)
    texto = _tabla(["min. días en estrategia"] + [f"top-{t}" for t in tops], filas)
    dups = r["robustez"].get("duplicados", [])
    if dups:
        texto += "\n\n> ⚠️ **Maestros con comportamiento idéntico o correlacionado**: "
        texto += "; ".join(" y ".join(d) for d in dups)
        texto += ". Contarlos como 'independientes' infla el top-N (ver N efectivo en la sección de validez)."
    return texto


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
    modo = politica.modo
    if modo == "ponderado":
        pesos = ", ".join(f"{c}: {w:.2f}" for c, w in (politica.pesos or {}).items())
        tabla += (f"\n\n> **Agregación ponderada** (P1.2): el perfil por bin combina a los maestros con pesos "
                  f"({pesos}) en vez de elegir un top-N duro. Los pesos premian superar la mediana del segmento.")
    rango = politica.rango_spread
    if rango:
        tabla += (f"\n\n> **Zona de confianza** (P1.3): la política fue entrenada con spreads en "
                  f"[{rango[0]:,.0f}, {rango[1]:,.0f}] COP/kWh. Un día fuera de ese rango reduce su exposición "
                  "a bolsa (trasladándola a contratos) en vez de clonar a ciegas.")
    fb = politica.fallback
    if fb:
        tabla += ("\n\n> **Fallback** (mediana global del estudio, para contextos sin datos):"
                  f" cobertura {fb.pct_cobertura:.0f} %, exposición {fb.pct_exposicion:.0f} %,"
                  f" no regulado {fb.pct_noreg:.0f} %, SICEP {fb.pct_sicep:.0f} %.")
    return tabla


def _tabla_escenarios(r: dict) -> str:
    if not r["escenarios"]:
        return "_Sin escenarios._"
    filas = [[e.nombre, e.descripcion, _fmt(e.prec_bolsa, 1), _fmt(e.prec_cont, 1), _fmt(e.spread, 1),
              e.bin_spread, _fmt(e.margen_cop_kwh), _fmt_cop(e.garantia_cop)] for e in r["escenarios"]]
    return _tabla(["Escenario", "Descripción", "Bolsa (COP/kWh)", "Contratos (COP/kWh)", "Spread",
                   "Bin", "Margen (COP/kWh)", "Garantía (COP)"], filas)


def _tabla_historial(r: dict) -> str:
    h = r["historial_escasez"]
    if not h.get("n_dias"):
        return "_Sin datos históricos._"
    filas_bins = [[label, f["n"], _fmt(f["pct"])] for label, f in h["frecuencia_bins"].items()]
    tabla = _tabla(["Contexto (spread)", "Días históricos", "% del histórico"], filas_bins)
    tabla += "\n\n" + _tabla(
        ["Métrica", "Valor"],
        [
            ["Días con escasez real (bolsa > precio de escasez)",
             f"{h['n_dias_escasez']} de {h['n_dias']} ({_fmt(h['pct_dias_escasez'])} %)"],
            ["Spread p50 (COP/kWh)", _fmt(h["spread_p50"])],
            ["Spread p95 (COP/kWh)", _fmt(h["spread_p95"])],
            ["Spread p99 (COP/kWh)", _fmt(h["spread_p99"])],
            ["Spread máximo (COP/kWh)", _fmt(h["spread_max"])],
        ],
    )
    filas_anio = [[anio, a["n_dias"], a["n_escasez"], _fmt(a["pct_escasez"])]
                  for anio, a in sorted(h["por_anio"].items())]
    tabla += "\n\n**Por año:**\n\n" + _tabla(["Año", "Días", "Días de escasez", "% del año"], filas_anio)
    return tabla


def _tabla_distribucion(r: dict) -> str:
    d = r["distribuciones"]
    filas = [
        ["Días", _fmt(d["imitacion"].n, 0), _fmt(d["maestros"].n, 0), _fmt(d["segmento"].n, 0)],
        ["Mediana (COP/kWh)", _fmt(d["imitacion"].mediana), _fmt(d["maestros"].mediana), _fmt(d["segmento"].mediana)],
        ["Media (COP/kWh)", _fmt(d["imitacion"].media), _fmt(d["maestros"].media), _fmt(d["segmento"].media)],
        ["p5 (COP/kWh)", _fmt(d["imitacion"].p5), _fmt(d["maestros"].p5), _fmt(d["segmento"].p5)],
        ["p95 (COP/kWh)", _fmt(d["imitacion"].p95), _fmt(d["maestros"].p95), _fmt(d["segmento"].p95)],
        ["% días con pérdida", _fmt(d["imitacion"].pct_dias_perdida), _fmt(d["maestros"].pct_dias_perdida), _fmt(d["segmento"].pct_dias_perdida)],
        ["Peor día (COP/kWh)", _fmt(d["imitacion"].peor_dia), _fmt(d["maestros"].peor_dia), _fmt(d["segmento"].peor_dia)],
        ["Mejor día (COP/kWh)", _fmt(d["imitacion"].mejor_dia), _fmt(d["maestros"].mejor_dia), _fmt(d["segmento"].mejor_dia)],
        ["Drawdown máximo (COP/kWh acum.)", _fmt(d["imitacion"].drawdown_max), _fmt(d["maestros"].drawdown_max), _fmt(d["segmento"].drawdown_max)],
    ]
    return _tabla(["Métrica", "Imitación (XXXC)", "Maestros (real)", "Segmento (real)"], filas)


def _tabla_simulacion(r: dict) -> str:
    filas = []
    for s in r["simulacion"]:
        esc = "sí" if s.es_escasez else "no"
        distr = "sí" if s.en_distribucion else "**no**"
        emb = "—" if s.nivel_embalses_pct is None else _fmt(s.nivel_embalses_pct)
        filas.append([
            s.fecha, s.bin_spread, esc, distr, emb,
            f"{s.perfil.pct_cobertura:.0f}%", f"{s.perfil.pct_exposicion:.0f}%",
            _fmt(s.margen_imitacion), _fmt(s.margen_maestros), _fmt(s.margen_segmento),
            _fmt_cop(s.garantia_exigida_cop),
        ])
    return _tabla(["Fecha", "Contexto", "Escasez", "En distribución", "Embalses (%)",
                   "Cobertura", "Exposición",
                   "Margen imitación", "Mediana maestros", "Mediana segmento", "Garantía (COP)"], filas)


def _seccion_alternativa(r: dict) -> str:
    """S3: alternativa recomendada cuando la combinación pedida no validó."""
    alt = r.get("alternativa")
    if not alt:
        return ""
    L: list[str] = []
    L.append("## 11. Alternativa recomendada (la combinación pedida no validó)")
    L.append("")
    L.append(f"El objetivo **{r['parametros']['segmento']} · {r['parametros']['estrategia']}** no superó las pruebas "
             f"de validez. La mejor alternativa del mismo estudio es **{alt['segmento']} · {alt['estrategia']}** "
             f"(maestros: {', '.join(alt['codigos'])}), con mediana relativa de **{_fmt(alt['mediana_relativa_top'])} "
             "COP/kWh** por encima de su segmento.")
    L.append("")
    res = alt["resumen"]
    rep = alt["replicacion"]
    ratio = rep.get("ratio_replicacion")
    L.append(_tabla(["Métrica", "Valor"], [
        ["Mediana margen imitación (COP/kWh)", _fmt(res.mediana_imitacion)],
        ["Mediana maestros (COP/kWh)", _fmt(res.mediana_maestros)],
        ["Mediana segmento (COP/kWh)", _fmt(res.mediana_segmento)],
        ["% días que la imitación gana al segmento", _fmt(res.pct_dias_gana_segmento)],
        ["Replicación IS→OOS", "—" if ratio is None else _fmt(ratio, 2)],
        ["Garantía mediana (COP)", _fmt_cop(res.garantia_mediana_cop)],
    ]))
    L.append("")
    fb = alt["politica"].fallback
    if fb:
        L.append(f"Perfil alternativo (fallback): cobertura **{fb.pct_cobertura:.0f} %**, exposición bolsa "
                 f"**{fb.pct_exposicion:.0f} %**, no regulado **{fb.pct_noreg:.0f} %**, SICEP **{fb.pct_sicep:.0f} %**.")
        L.append("")
    return "\n".join(L)


def _seccion_decision(r: dict, res) -> str:
    """Decisiones de negocio explícitas para el agente XXXC."""
    d = r["decision"]
    p = r["parametros"]
    fb = r["politica"].fallback
    L: list[str] = []
    L.append("## 12. Decisiones de negocio para el agente XXXC")
    L.append("")
    L.append(f"Resumen ejecutivo para **{p['segmento']} · {p['estrategia']}** en el período planteado"
             f" (estudio {p['ventanas']['estudio']['ini']} → {p['ventanas']['estudio']['fin']};"
             f" impacto {p['ventanas']['impacto']['ini']} → {p['ventanas']['impacto']['fin']}):")
    L.append("")

    bullets: list[str] = []
    if fb:
        bullets.append(
            f"**Perfil a replicar:** compra **{fb.pct_exposicion:.0f} % de tu demanda en bolsa** y"
            f" **{fb.pct_cobertura:.0f} % en contratos**, con mix **{fb.pct_noreg:.0f} % no regulado** y"
            f" **{fb.pct_sicep:.0f} % SICEP** (perfil mediano de los maestros)."
        )
    bullets.append(
        f"**Capital para operar:** constituye garantías por al menos **{_fmt_cop(res.garantia_max_cop)} COP/día**"
        f" (mediana **{_fmt_cop(res.garantia_mediana_cop)} COP**)."
    )
    bullets.append(
        f"**Pérdida en un día de escasez:** si la bolsa toca el precio de escasez pierdes"
        f" **{_fmt_cop(abs(d['perdida_dia_escasez_cop']))} COP** en un día"
        f" ({_fmt_cop(abs(d['perdida_dia_escasez_extrema_cop']))} COP si la supera 25 %), sobre tu demanda simulada"
        f" de {res.demanda_kwh_dia / 1e6:.3f} GWh/día."
    )
    bullets.append(
        f"**Expectativa de negocio:** con la frecuencia histórica de escasez ({_fmt(d['pct_escasez_historico'])} %"
        f" de los días) tu beneficio esperado es **{_fmt(d['e_margen_dia_historico'])} COP/kWh/día**;"
        f" en un año Niño ({_fmt(d['pct_escasez_anio_nino'], 0)} % de escasez) baja a"
        f" **{_fmt(d['e_margen_dia_anio_nino'])} COP/kWh/día**."
    )
    if d.get("kill_switch_activado"):
        bullets.append(
            f"**Kill-switch (activado):** el drawdown acumulado del período "
            f"**{_fmt(d['drawdown_max_cop_kwh'])} COP/kWh** supera el umbral: **no operar** la estrategia "
            "imitada sin rediseño."
        )
    else:
        bullets.append(
            f"**Kill-switch:** drawdown acumulado del período **{_fmt(d['drawdown_max_cop_kwh'])} COP/kWh**; "
            f"el umbral de protección está en {d.get('kill_switch_drawdown_cop_kwh', 0):.0f} COP/kWh."
        )
    cap = d.get("capacidad")
    if cap:
        estado = "supera" if cap["supera_capacidad"] else "dentro del"
        bullets.append(
            f"**Capacidad:** la demanda simulada de XXXC ({cap['dema_imitar_kwh']:,.0f} kWh/día) es el "
            f"**{cap['pct_del_segmento']:.1f} %** de la demanda mediana del segmento "
            f"({cap['umbral_pct']:.0f} % = umbral): {estado} límite."
        )
    bullets.append(
        "**Regla de protección:** define un límite/cobertura cuando el spread bolsa−contrato se acerque a 600"
        " COP/kWh (contexto 'escasez'): ahí la política no tiene datos de entrenamiento y el perfil imitado"
        " (sin cobertura) es el que más pierde."
    )
    bullets.append(
        "**Re-evaluación:** el top de maestros es pequeño y con comportamientos duplicados; no operes con datos"
        " de un solo período. Revisa esta decisión cada ventana (modo `--walk-forward`)."
    )
    for b in bullets:
        L.append(f"- {b}")
    L.append("")
    L.append(f"**Veredicto:** {d['veredicto']}")
    L.append("")
    return "\n".join(L)


def renderizar(resultado: dict, cfg: dict) -> str:
    p = resultado["parametros"]
    res = resultado["resumen"]
    v = p["ventanas"]
    d = resultado["distribuciones"]
    L: list[str] = []

    L.append("# Asistente imitador del agente XXXC — Behavioral Cloning del top-N")
    L.append("")
    L.append(f"> Clona el comportamiento del top-{p['top']} de **{p['segmento']} · {p['estrategia']}** en la ventana"
             f" de estudio y lo replica en la ventana de impacto. Metodología: `docs/plan_agente_xxxc_asistente.md`.")
    L.append("")
    L.append(ADVERTENCIA)
    L.append("")

    # ---- 1. Parámetros ----
    L.append("## 1. Parámetros")
    L.append("")
    params_filas = [
        ["Segmento", p["segmento"]],
        ["Estrategia a imitar", p["estrategia"]],
        ["Top de maestros", str(p["top"])],
        ["Demanda diaria de XXXC (GWh)", _fmt(p["demanda_dia_gwh"])],
        ["Presencia mínima en la estrategia", f"{p['min_dias_pct']:.0f} % de los días"],
        ["Ventana de estudio (define maestros)", f"{v['estudio']['ini']} → {v['estudio']['fin']}"],
    ]
    if v.get("validacion"):
        params_filas.append(["Sub-validación (holdout)", f"{v['validacion']['ini']} → {v['validacion']['fin']}"])
    params_filas.append(["Ventana de impacto (evalúa imitación)", f"{v['impacto']['ini']} → {v['impacto']['fin']}"])
    if p.get("contexto"):
        ctx = p["contexto"]
        L.append(f"**Contexto de decisión (P1):** spread del día anterior = "
                 f"{'sí' if ctx['usar_spread_previo'] else 'no'} (sin look-ahead) · "
                 f"factor de exposición fuera de distribución = {_fmt(ctx['factor_exposicion_fuera'])} · "
                 f"régimen hidrológico = {'sí' if ctx['regimen_hidrologico'] else 'no'}.")
        L.append("")
    L.append(_tabla(["Parámetro", "Valor"], params_filas))
    L.append("")

    # ---- 2. Maestros y robustez ----
    L.append(f"## 2. Maestros — top {p['top']} del segmento en la ventana de estudio")
    L.append("")
    e = resultado["estudio"]
    L.append(f"Ranking de agentes por mediana del margen diario dentro de **{p['segmento']} · {p['estrategia']}**"
             f" en {v['estudio']['ini']} → {v['estudio']['fin']}"
             f" (estudio de {e['n_agentes']} agentes, {e['n_dias']} días, k={e['k']}).")
    L.append("")
    L.append(_tabla_maestros(resultado))
    L.append("")
    L.append("**Robustez de la selección** (misma ventana de estudio, otras configuraciones de top y presencia):")
    L.append("")
    L.append(_tabla_robustez(resultado))
    L.append("")

    # ---- 2bis. Validez de la selección ----
    L.append("## 3. Validez de la selección (¿los maestros son hábiles o suertudos?)")
    L.append("")
    L.append("Tres pruebas separan la selección del ruido: **bootstrap skill-vs-luck** (¿el mejor maestro supera al "
             "azar?), **holdout** (¿la selección hecha en sub-estudio se sostiene en la sub-validación?) y "
             "**DSR** (¿el resultado de la imitación resiste la corrección por múltiples pruebas?). La "
             "**replicación IS→OOS** mide cuánto del desempeño del estudio se conserva en el impacto.")
    L.append("")
    L.append(_tabla_validez(resultado))
    L.append("")

    # ---- 3. Política ----
    L.append("## 4. Política de clonación (contexto → perfil de abastecimiento)")
    L.append("")
    L.append("Por bin de spread (bolsa − contrato) se aprende la **mediana** del perfil que usaron los maestros"
             " cuando jugaron la estrategia objetivo. Un día con ese contexto recibe ese perfil.")
    L.append("")
    L.append(_tabla_politica(resultado))
    L.append("")

    # ---- 4. Escenarios de estrés ----
    L.append("## 5. Escenarios de estrés (sintéticos — la ventana no tuvo estos días)")
    L.append("")
    L.append("La ventana de impacto puede no contener días de bolsa cara/escasez. Estos escenarios **sintéticos**"
             " responden: ¿qué pasa con la imitación si mañana la bolsa se dispara? Se construyen con el perfil"
             " que la política asignaría en ese contexto.")
    L.append("")
    L.append(_tabla_escenarios(resultado))
    L.append("")

    # ---- 5. Frecuencia histórica de escasez ----
    L.append("## 6. Frecuencia histórica de escasez (todo el histórico de la BD)")
    L.append("")
    h = resultado["historial_escasez"]
    L.append(f"Con {h['n_dias']} días de histórico (2015 → límite de datos), la escasez real"
             f" (bolsa > precio de escasez) ocurre el **{_fmt(h['pct_dias_escasez'])} %** de los días, y el contexto"
             " en que la política de clonación **no tiene datos** (spread > 600, bin 'escasez') es raro pero existe."
             " Cuando ocurre, la sección 4 muestra pérdidas de **−520 a −715 COP/kWh/día**.")
    anio_impacto = v["impacto"]["fin"][:4]
    esc_impacto = h["por_anio"].get(int(anio_impacto), {})
    if esc_impacto and esc_impacto["n_escasez"] == 0:
        L.append("")
        L.append(f"> ⚠️ **La ventana de impacto ({anio_impacto}) es un año sin días de escasez.** La distribución"
                 " 'ideal' de la sección 6 refleja ese clima benigno; en un año con escasez (2015–16, 2023–24:"
                 " 21–30 % de los días) la misma estrategia produce las pérdidas de la sección 4.")
    L.append("")
    L.append(_tabla_historial(resultado))
    L.append("")

    # ---- 6. Distribución de márgenes (riesgo) ----
    L.append("## 7. Distribución de márgenes en el impacto (riesgo)")
    L.append("")
    L.append("Medidas de la serie diaria de márgenes. **p5** es un día malo, **% días con pérdida** la frecuencia de"
             " pérdidas, **drawdown máximo** la peor caída pico→valle acumulada del período.")
    L.append("")
    L.append(_tabla_distribucion(resultado))
    L.append("")
    if res.mediana_maestros is not None:
        L.append(f"> **Lectura:** la imitación logra una mediana de **{res.mediana_imitacion:.1f} COP/kWh/día**"
                 f" frente a **{res.mediana_maestros:.1f}** de sus maestros reales y **{res.mediana_segmento:.1f}** del"
                 " segmento, con **" + _fmt(d["imitacion"].pct_dias_perdida) + " % de días en pérdida** y un drawdown"
                 f" de **{d['imitacion'].drawdown_max:.1f} COP/kWh** acumulados en el período. El margen es un"
                 " artefacto de modelado; solo sirve para comparar entre sí.")
        L.append("")

    # ---- 7. Simulación diaria ----
    L.append(f"## 8. Simulación día a día ({v['impacto']['ini']} → {v['impacto']['fin']})")
    L.append("")
    L.append("XXXC replica cada día el perfil recomendado y se calcula su margen y garantía estimada con la misma"
             " lógica del estudio (C16–C18 sobre precios de sistema). Se compara contra la mediana real de los"
             " maestros y del segmento ese día. **En distribución** indica si el spread del día cae dentro del"
             " rango entrenado (si no, la exposición a bolsa se redujo — P1.3); **Embalses** es el nivel agregado"
             " del SIN (P1.4).")
    L.append("")
    L.append(_tabla_simulacion(resultado))
    L.append("")

    # ---- 9. Balance del impacto ----
    L.append("## 9. Balance del impacto")
    L.append("")
    filas_balance = [
        ["Mediana margen (COP/kWh)", _fmt(res.mediana_imitacion),
         _fmt(res.mediana_maestros), _fmt(res.mediana_segmento)],
        ["Media margen (COP/kWh)", _fmt(res.media_imitacion), "—", "—"],
        ["% días que la imitación gana", "—",
         _fmt(res.pct_dias_gana_maestros), _fmt(res.pct_dias_gana_segmento)],
    ]
    val = resultado.get("validez", {})
    rep = val.get("replicacion_is_oos")
    if rep:
        ratio = rep.get("ratio_replicacion")
        filas_balance.append([
            "Replicación IS→OOS (ratio estudio→impacto)",
            "—" if ratio is None else _fmt(ratio, 2), "—", "—",
        ])
    dsr = val.get("dsr")
    if dsr:
        filas_balance.append([
            "DSR (corregido por múltiples pruebas)",
            _fmt(dsr["dsr"], 3) + (" (sí)" if dsr["significativo"] else " (no)"), "—", "—",
        ])
    L.append(_tabla(["Métrica", "Imitación (XXXC)", "Maestros (real)", "Segmento (real)"], filas_balance))
    L.append("")
    L.append(f"Garantía estimada por día (COP): mediana **{_fmt_cop(res.garantia_mediana_cop)}**, máximo"
             f" **{_fmt_cop(res.garantia_max_cop)}**. Demanda simulada: **{res.demanda_kwh_dia:,.0f} kWh"
             f"** ({res.demanda_kwh_dia / 1e6:.3f} GWh).".replace(",", " "))
    L.append("")

    # ---- 9. Advertencias ----
    L.append("## 10. Advertencias y limitaciones")
    L.append("")
    for i, adv in enumerate(resultado["advertencias"], start=1):
        L.append(f"{i}. {adv}")
    L.append("")

    # ---- Alternativa recomendada (S3) ----
    L.append(_seccion_alternativa(resultado))

    # ---- Decisiones de negocio (cierre) ----
    L.append(_seccion_decision(resultado, res))

    return "\n".join(L)


def guardar(resultado: dict, cfg: dict) -> Path:
    md = renderizar(resultado, cfg)
    destino = BASE_DIR / cfg["asistente"]["salida"]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(md, encoding="utf-8")
    return destino