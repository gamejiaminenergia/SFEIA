"""VIEW: renderizado del informe de estrategias diarias en Markdown.

Recibe los resultados del estudio híbrido (datos["diario"]) y la config, y
produce sfeia/docs/informe_estrategias_diarias.md. Jamás consulta la BD.
"""
from __future__ import annotations

from pathlib import Path

from sfeia.app.models.entities import BalanceEstrategia, PerfilEstrategia
from sfeia.app.services.diario import matriz_puestos

BASE_DIR = Path(__file__).resolve().parent.parent.parent

_FEATURES_DESCRIPCION = {
    "log_dema": "Tamaño (log1p demanda diaria, GWh)",
    "pct_noreg": "Mercado objetivo (D2): % demanda no regulada del día",
    "pct_cobertura": "Abastecimiento (D1): % cobertura con contratos (log1p, clip 300 %)",
    "pct_exposicion": "Riesgo spot (D4): % exposición a bolsa (log1p)",
    "pct_sicep": "Convocatoria (D2): % compras reguladas con registro SICEP",
    "tiene_sicep": "1 si compra regulado, 0 si puro no regulado",
}


def _tabla(encabezados: list[str], filas: list[list]) -> str:
    if not filas:
        return "_Sin datos._"
    ancho = len(encabezados)
    salida = ["| " + " | ".join(encabezados) + " |",
              "|" + "|".join("---" for _ in encabezados) + "|"]
    for fila in filas:
        celdas = [str(fila[i]) if i < len(fila) else "" for i in range(ancho)]
        salida.append("| " + " | ".join(celdas) + " |")
    return "\n".join(salida)


def _fmt(v, sufijo: str = "") -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:,.1f}{sufijo}".replace(",", " ")
    return f"{v}{sufijo}"


def _fmt_feature(feature: str, valor: float) -> str:
    if feature.startswith("pct_") or feature == "tiene_sicep":
        return f"{valor:,.0f}".replace(",", " ")
    return f"{valor:,.2f}".replace(",", " ")


_EXPLICACION_ESTRATEGIA = {
    "Comercializador regulado": (
        "Base de clientes regulados (residencial y pequeños negocios) atendidos con tarifa CREG. Compra la mayor "
        "parte de su energía con contratos, preferiblemente vía convocatoria pública (SICEP alto) y suele cubrir "
        "más de lo que demanda.",
        "Le va bien cuando el precio de bolsa sube: sus contratos lo protegen y no paga el sobrecosto del spot.",
        "Margen regulado fijo (CV) con poco margen de maniobra; gana por volumen, no por spread.",
    ),
    "Integrado/regional regulado": (
        "Grandes grupos con red de distribución (ENDC, EPMC, CELSIA…): base regulada servida por convocatoria "
        "pública, cobertura de contratos amplia y exposición a bolsa muy baja. Llevan años de mercado y fuertes "
        "garantías.",
        "El más estable: rinde bien casi todos los días y domina cuando la bolsa está cara (tiene contratos que "
        "valen menos que el spot).",
        "Poco margen por kWh (modelo regulado); su resultado depende del enorme volumen y de renovar su cartera "
        "por convocatoria.",
    ),
    "Trader no regulado": (
        "Intermediario del mercado no regulado (industria y comercio): compra y vende energía en contratos y bolsa "
        "en volúmenes muy superiores a su propia demanda (rol de trading). Sin base regulada.",
        "Le va bien cuando la bolsa es barata (spread contratos–bolsa favorable) y puede revender con margen.",
        "Exposición al spot y necesidad de garantías por el alto volumen transado frente a su demanda.",
    ),
    "Trader expuesto a bolsa (sin cobertura)": (
        "Compra casi toda su energía en la bolsa, sin contratos de cobertura; mezcla clientes regulados y no "
        "regulados y es de menor tamaño. Acepta el precio spot a cambio de no pagar la prima de los contratos.",
        "El que mejor rinde cuando la bolsa está barata (Ene–Jun): compra al costo spot y no asume sobrecosto de "
        "contratos.",
        "Máxima exposición: en días de escasez (Jul) el precio de bolsa se dispara y es el que más pierde.",
    ),
    "Trader con sobrecobertura de contratos": (
        "Comercializador no regulado que compra contratos muy por encima de su demanda y revende el excedente; "
        "casi no usa bolsa. Actúa como arbitrajista de contratos.",
        "Domina los días de escasez (bolsa cara): su energía comprada por contrato a precio fijo se vuelve muy "
        "valiosa frente al spot.",
        "Descalce de cobertura y garantías por volumen; si el contrato se vuelve más caro que la bolsa, pierde.",
    ),
}


def _tabla_explicacion_estrategias(diario: dict) -> str:
    """Tabla de negocio por estrategia (qué hace, cuándo le va bien, riesgo)."""
    filas = []
    for cid in sorted(diario["perfiles"]):
        p = diario["perfiles"][cid]
        explicacion = _EXPLICACION_ESTRATEGIA.get(p.arquetipo)
        if explicacion:
            filas.append([f"**{p.arquetipo}** (E{cid})", explicacion[0], explicacion[1], explicacion[2]])
        else:
            filas.append([f"**{p.arquetipo}** (E{cid})", "Sin descripción disponible.", "—", "—"])
    return _tabla(["Estrategia", "Qué hace", "Cuándo le va mejor", "Riesgo principal"], filas)


def _composicion(p: PerfilEstrategia) -> str:
    partes = [f"{seg}: {n}" for seg, n in sorted(p.composicion_segmento.items())]
    return "; ".join(partes) if partes else "—"


def _representativos(diario: dict, cid: int) -> list[str]:
    """Agentes únicos del clúster ordenados por máxima demanda diaria (top 5)."""
    max_dema: dict[str, float] = {}
    for a in diario["agentes"]:
        if a.cluster_id != cid:
            continue
        dema = float(a.features.get("dema_gwh", 0.0))
        if dema > max_dema.get(a.codigo, 0.0):
            max_dema[a.codigo] = dema
    return sorted(max_dema, key=max_dema.get, reverse=True)[:5]


def _dias_precio(agentedia: dict) -> dict:
    """Precios de sistema por día (una vez por día; son comunes a todos)."""
    out: dict[str, dict] = {}
    for ad in agentedia.values():
        dia = str(ad["dia"])
        if dia not in out:
            out[dia] = {
                "prec_bolsa": ad["prec_bolsa"],
                "prec_cont": ad["prec_cont"],
                "prec_escasez": ad["prec_escasez"],
                "spread": ad["prec_bolsa"] - ad["prec_cont"],
            }
    return out


def _ganador(ranking: dict, dia: str) -> tuple[int, float]:
    for cid, res in ranking.get(dia, {}).items():
        if res["rango"] == 1:
            return cid, res["mediana"]
    return -1, 0.0


def _nombre_arquetipo(perfiles: dict, cid: int, atipico_ids: set | None = None) -> str:
    p = perfiles.get(cid)
    nombre = p.arquetipo if p else "—"
    if atipico_ids and cid in atipico_ids:
        nombre += " (atípico)"
    return nombre


def _segmentos(diario: dict) -> list[str]:
    """Orden GRANDE → MEDIANO → PEQUEÑO (solo los presentes en el estudio)."""
    orden = ["GRANDE", "MEDIANO", "PEQUEÑO"]
    presentes = diario.get("ranking_por_segmento", {})
    return [s for s in orden if s in presentes]


def _tabla_segmentacion(f_1: dict, seg: dict) -> str:
    """Resumen de la segmentación F-1 (criterios, conteo y mercado por segmento)."""
    resumen = f_1["resumen"]
    orden = ["GRANDE", "MEDIANO", "PEQUEÑO"]
    filas = []
    for s in orden:
        r = resumen[s]
        filas.append([
            s,
            f"≥ {seg['grande_min_gwh']:,.0f}".replace(",", " ") if s == "GRANDE"
            else (f"{seg['mediano_min_gwh']:,.0f} – <{seg['grande_min_gwh']:,.0f}".replace(",", " ") if s == "MEDIANO" else f"< {seg['mediano_min_gwh']:,.0f}".replace(",", " ")),
            r["n"], f"{r['gwh']:,.1f}".replace(",", " "), r["pct_mercado"], r["pct_reg"],
        ])
    return _tabla(
        ["Segmento", "Criterio (DemaCome GWh/semestre)", "Agentes", "Demanda (GWh)", "% mercado", "% regulado"],
        filas,
    )


def _tabla_agentes_segmento(f_1: dict) -> str:
    """Todos los comercializadores con su segmento (ordenado por demanda)."""
    orden = {"GRANDE": 0, "MEDIANO": 1, "PEQUEÑO": 2}
    poblacion = sorted(
        f_1["poblacion"],
        key=lambda a: (orden.get(a.segmento.value, 9), -a.dema_come_gwh),
    )
    filas = [[
        a.segmento.value, a.codigo, a.nombre,
        f"{a.dema_come_gwh:,.1f}".replace(",", " "), a.pct_reg, a.pct_noreg,
    ] for a in poblacion]
    return _tabla(
        ["Segmento", "Código", "Comercializador", "Demanda (GWh)", "% Regulado", "% No regulado"],
        filas,
    )


def _resumen_segmento(diario: dict, seg: str) -> str:
    """n de agentes y estrategias del segmento para el encabezado de su matriz."""
    codigos = {a.codigo for a in diario["agentes"] if a.segmento == seg}
    n_estrategias = len(diario["balance_por_segmento"].get(seg, {}).get("balance", []))
    return f"{len(codigos)} agentes · {n_estrategias} estrategias en el ranking"


def _matriz_estrategia_x_segmento(diario: dict) -> str:
    """Tabla estrategia × segmento con la mejor de cada columna en negrita.

    Celdas = mediana del margen diario (la misma del ranking por segmento,
    coherente con el balance). Las estrategias atípicas del segmento se marcan
    y NO se resaltan como la mejor.
    """
    segs = _segmentos(diario)
    xs = diario["estrategia_x_segmento"]
    atipico = {
        (b.cluster_id, seg)
        for seg, bl in diario["balance_por_segmento"].items()
        for b in bl.get("atipicos", [])
    }
    filas: list[list] = []
    for cid in sorted(xs):
        nom = diario["perfiles"][cid].arquetipo if cid in diario["perfiles"] else f"E{cid}"
        fila = [f"**{nom}**"]
        for seg in segs:
            celda = xs[cid].get(seg)
            if not celda:
                fila.append("—")
                continue
            txt = f"{celda['mediana']:.1f} ({celda['dias']} días)"
            if (cid, seg) in atipico:
                txt += " (atípico)"
            fila.append(txt)
        filas.append(fila)
    # resaltar la mejor de cada columna (sin contar atípicos ni "—")
    for j, seg in enumerate(segs, start=1):
        candidatas = [f for f in filas if f[j] != "—" and "(atípico)" not in f[j]]
        if not candidatas:
            continue
        mejor_fila = max(candidatas, key=lambda f: float(f[j].split(" ")[0]))
        mejor_fila[j] = f"**{mejor_fila[j]}**"
    return _tabla(["Estrategia"] + segs, filas)


def _lectura_por_segmento(diario: dict) -> str:
    """Nota de lectura: qué mirar en cada segmento y el porqué."""
    lines: list[str] = [
        "> **Cómo leerlo:** el ranking pooled (sección 6) lo encabezan estrategias que funcionan bien"
        " combinando todos los tamaños. Para el análisis de negocio importa la **columna de cada segmento**:"
        " en GRANDE suele dominar la cobertura de contratos (integrados con red, años de mercado y garantías),"
        " mientras que en MEDIANO y PEQUEÑO compiten traders y regulados con estructuras distintas. Si un"
        " segmento tiene **0 días** en una estrategia, esa estrategia no aparece en su balance.",
    ]
    return "\n".join(lines)


def renderizar(datos: dict, cfg: dict) -> str:
    diario = datos["diario"]
    f_1 = datos["f-1"]
    v = cfg["ventana"]
    atipico_ids = {b.cluster_id for b in diario.get("atipicos", [])}
    L: list[str] = []

    # ---------- Encabezado ----------
    L.append(f"# {cfg['informe_diario']['titulo']}")
    L.append("")
    L.append(f"> Proyecto SFEIA · Ventana **{v['foco_ini']} → {v['foco_fin']}** ·"
             f" Población: **{diario['n_agentes']} comercializadores** ·"
             f" **{diario['n_agentes_dia']} agentes-día** en **{diario['n_dias']} días** ·"
             f" K-Means pooled (k={diario['k_seleccionado']}, semilla={cfg['diario']['random_state']}).")
    L.append("")
    L.append("> Estudio **híbrido**: reemplaza al benchmark por segmento y al k-means de H1-2026. Toma del"
             " no supervisado la agrupación en arquetipos (sin umbrales ni reglas manuales) y del benchmark"
             " el modelo financiero (margen estimado por kWh) como métrica de desempeño, todo a granularidad"
             " **diaria**. Archivo único de salida del proyecto.")
    L.append("")

    # ---------- Resumen ejecutivo ----------
    L.append("## Resumen ejecutivo")
    L.append("")
    L.append("Ranking final de estrategias del período (mediana del margen estimado diario por kWh, en COP):")
    L.append("")
    L.append(_tabla(
        ["Pos.", "Estrategia", "Clúster", "Días", "Mediana margen (COP/kWh)", "Días 1.º", "% top-3", "Rango prom."],
        [[i + 1, b.arquetipo, b.cluster_id, b.dias, _fmt(b.mediana_margen), b.dias_puesto1, _fmt(b.pct_top3, "%"), _fmt(b.rango_promedio)]
         for i, b in enumerate(diario["balance"])],
    ))
    L.append("")
    if diario["balance"]:
        mejor = diario["balance"][0]
        peor = diario["balance"][-1]
        L.append(f"La estrategia que mejor funcionó en el período fue **{mejor.arquetipo}**"
                 f" (mediana de {mejor.mediana_margen} COP/kWh/día, {mejor.dias_puesto1} días en el 1.er puesto)."
                 f" La de peor desempeño fue **{peor.arquetipo}** ({peor.mediana_margen} COP/kWh/día)."
                 " El margen es un **artefacto de modelado** (Pv=350 COP/kWh fijo); sirve para comparar estrategias,"
                 " no como margen real del negocio.")
    if diario.get("atipicos"):
        L.append("")
        L.append("_Casos atípicos (excluidos del ranking por presencia marginal):_ "
                 + "; ".join(f"{b.arquetipo} (E{b.cluster_id}, {b.dias} días)" for b in diario["atipicos"]) + ".")
    L.append("")

    # ---------- Metodología ----------
    L.append("## 1. Metodología")
    L.append("")
    L.append("**Población y granularidad.** Todos los comercializadores con demanda en la ventana (65) se"
             " observan **por día** (~212 días → ~13 800 agentes-día). Cada agente puede cambiar de estrategia"
             " de un día a otro; la agrupación sale de los datos, no de reglas a priori.")
    L.append("")
    L.append("**Segmentación de la población (F-1).** Cada comercializador se clasifica en"
             " GRANDE/MEDIANO/PEQUEÑO por su **demanda comercial total (DemaCome) de la ventana**, con los"
             " umbrales de `config/config.yaml` (`segmentacion:`). Es una clasificación por **volumen**, no por"
             " número de clientes ni por estrategia; el segmento se usa como **variable de análisis** (no entra"
             " al k-means), para que los tamaños no compitan entre sí en el ranking.")
    L.append("")
    L.append(_tabla_segmentacion(f_1, cfg["segmentacion"]))
    L.append("")
    L.append("#### 1.1 Comercializadores por segmento")
    L.append("")
    L.append(_tabla_agentes_segmento(f_1))
    L.append("")
    L.append("")
    L.append("**Features diarias** (mismas 6 del estudio k-means, calculadas por agente y día;"
             " cobertura/exposición entran log1p a la matriz, cobertura clip 300 %):")
    L.append("")
    L.append(_tabla(
        ["Feature", "Descripción"],
        [[f, _FEATURES_DESCRIPCION.get(f, "")] for f in diario["features"]],
    ))
    L.append("")
    L.append(f"**Clustering.** K-Means (scikit-learn) sobre la matriz pooled escalada con"
             f" **{cfg['diario']['scaler']}**; elección de k por **{cfg['diario']['metodo_k']}** en"
             f" k∈[{cfg['diario']['k_min']},{cfg['diario']['k_max']}] sobre una submuestra determinista de"
             f" {cfg['diario'].get('submuestra_k', 'todos')} filas (silhouette es O(n²)); el k elegido se aplica"
             f" a toda la matriz. `random_state={cfg['diario']['random_state']}`, `n_init={cfg['diario']['n_init']}`."
             " Los nombres de arquetipo son etiquetas interpretativas post-hoc sobre los centroides.")
    L.append("")
    L.append("**Desempeño diario.** Por agente y día se estima el **margen por kWh** con la lógica del modelo"
             " financiero (C16–C18) sobre los agregados diarios de C15: compras/ventas valoradas con el precio"
             " promedio **de sistema** del día (contratos `PrecPromCont` y bolsa `PPPrecBolsNaci`). No existe"
             " precio ni margen real por agente en elecdb: el margen diferencia a los agentes por su **mix diario**"
             " contratos/bolsa y reg/no-reg. Cada día se agrupa a los agentes por estrategia y se ordenan las"
             " estrategias por la **mediana** de su margen diario (empates por media).")
    L.append("")
    L.append("**Guardas de robustez (config `diario:`).** "
             f"(a) El margen se **winsoriza** a ±{cfg['diario'].get('clip_margen_cop_kwh', '—')} COP/kWh: los traders"
             " con volumen transado muy superior a su demanda producen márgenes por kWh desproporcionados"
             " (artefacto del denominador). (b) Las estrategias presentes en menos del "
             f"**{cfg['diario'].get('min_dias_pct', 0)} %** de los días se reportan como **casos atípicos** y se"
             " excluyen del ranking (no son representativas del período). (c) `pct_sicep` se techa en "
             f"{cfg['diario'].get('clip_pct_sicep', 100)} % (SICEP puede incluir compras no reguladas).")
    L.append("")
    L.append(f"**Ranking y balance.** Se construye el ranking de estrategias para cada uno de los {diario['n_dias']}"
             " días y se consolida: mediana/media del margen diario, días en 1.er puesto, % de días top-3, rango"
             " promedio y tendencia (diferencia 2.ª mitad − 1.ª mitad del período).")
    L.append("")
    L.append("> **Matiz de transparencia:** features, escalado, k y la métrica de desempeño siguen siendo"
             " decisiones del analista (todo reproducible desde `config/config.yaml`). El k-means describe"
             " comportamiento **pasado**; no es causal ni predictivo.")
    L.append("")

    # ---------- Elección de k ----------
    L.append("## 2. Elección de k")
    L.append("")
    L.append(_tabla(
        ["k", "Silhouette medio", "Inercia"],
        [[r["k"], _fmt(r["silhouette"]), _fmt(r["inercia"])] for r in diario["resultados_k"]],
    ))
    L.append("")
    L.append(f"Se selecciona **k={diario['k_seleccionado']}** (máximo silhouette medio sobre la submuestra;"
             " los demás k se reportan para sensibilidad).")
    L.append("")

    # ---------- Arquetipos diarios ----------
    L.append("## 3. Arquetipos diarios")
    L.append("")
    L.append("Cada estrategia (arquetipo) es un grupo de agentes que el día a día se comporta igual en su"
             " abastecimiento (contratos vs bolsa), su mercado objetivo (regulado vs no regulado) y su exposición"
             " al precio spot. A continuación, qué significa cada una en lenguaje de negocio:")
    L.append("")
    L.append(_tabla_explicacion_estrategias(diario))
    L.append("")
    for cid in sorted(diario["perfiles"]):
        p = diario["perfiles"][cid]
        L.append(f"### E{cid} — {p.arquetipo} ({p.n} agentes-día, {p.n_agentes} agentes únicos)")
        L.append("")
        L.append(f"Composición por segmento F-1: {_composicion(p)}.")
        L.append("")
        L.append(_tabla(
            ["Feature", "Media diaria"],
            [[f, _fmt_feature(f, p.medias.get(f, 0.0))] for f in diario["features"]],
        ))
        L.append("")
        L.append("Agentes representativos: **" + ", ".join(_representativos(diario, cid)) + "**.")
        L.append("")

    # ---------- Ranking diario ----------
    L.append("## 4. Ranking diario")
    L.append("")
    L.append("Número de días que cada estrategia ocupó cada puesto (1.º = mejor margen del día):")
    L.append("")
    k = diario["k_seleccionado"]
    mp = matriz_puestos(diario["ranking"], k)
    L.append(_tabla(
        ["Estrategia"] + [f"{i + 1}.º" for i in range(k)] + ["Total días"],
        [[diario["perfiles"][cid].arquetipo] + mp[cid] + [sum(mp[cid])] for cid in range(k)],
    ))
    L.append("")
    L.append("### 4.1 Matriz de puestos por segmento")
    L.append("")
    L.append("La misma distribución pero **por segmento** (GRANDE/MEDIANO/PEQUEÑO): cada segmento compite"
             " dentro de sí mismo, no contra los demás.")
    L.append("")
    for seg in _segmentos(diario):
        L.append(f"**{seg}** — {_resumen_segmento(diario, seg)}")
        L.append("")
        mps = matriz_puestos(diario["ranking_por_segmento"].get(seg, {}), k)
        filas_mp = [[diario["perfiles"][cid].arquetipo] + mps[cid] + [sum(mps[cid])]
                    for cid in range(k) if sum(mps[cid]) > 0]
        L.append(_tabla(
            ["Estrategia"] + [f"{i + 1}.º" for i in range(k)] + ["Total días"],
            filas_mp,
        ))
        L.append("")
    dias_precio = _dias_precio(diario["agentedia"])
    L.append("### 4.2 Días destacados (bolsa cara)")
    L.append("")
    L.append("Días con mayor precio de bolsa (señal de escasez; el spread bolsa−contrato define quién gana):")
    L.append("")
    top_dias = sorted(dias_precio.items(), key=lambda kv: kv[1]["spread"], reverse=True)[:8]
    if top_dias:
        L.append(_tabla(
            ["Fecha", "Bolsa (COP/kWh)", "Contratos (COP/kWh)", "Spread", "Estrategia ganadora"],
            [[dia, _fmt(d["prec_bolsa"]), _fmt(d["prec_cont"]), _fmt(d["spread"]),
              _nombre_arquetipo(diario["perfiles"], _ganador(diario["ranking"], dia)[0], atipico_ids)]
             for dia, d in top_dias],
        ))
        L.append("")
    L.append("Días de escasez (bolsa > precio de escasez):"
             f" **{sum(1 for d in dias_precio.values() if d['prec_bolsa'] > d['prec_escasez'])}** de"
             f" {len(dias_precio)} días. En esos días la estrategia ganadora fue, por frecuencia:")
    L.append("")
    escasez_dias = [dia for dia, d in dias_precio.items() if d["prec_bolsa"] > d["prec_escasez"]]
    if escasez_dias:
        conteo: dict[str, int] = {}
        for dia in escasez_dias:
            cid, _ = _ganador(diario["ranking"], dia)
            nom = _nombre_arquetipo(diario["perfiles"], cid, atipico_ids)
            conteo[nom] = conteo.get(nom, 0) + 1
        L.append(_tabla(["Estrategia", "Días ganados"],
                        [[nom, n] for nom, n in sorted(conteo.items(), key=lambda kv: -kv[1])]))
    else:
        L.append("_Sin días de escasez en la ventana._")
    L.append("")

    # ---------- Ranking y balance por segmento ----------
    L.append("## 5. Ranking y balance por segmento")
    L.append("")
    L.append("El ranking pooled mezcla segmentos de tamaños muy distintos. Aquí cada segmento se analiza"
             " **por separado** (los GRANDE no compiten contra los PEQUEÑO), para ver qué estrategia funciona"
             " mejor dentro de cada uno — especialmente en MEDIANO y PEQUEÑO, donde la estructura es menos"
             " homogénea que en GRANDE.")
    L.append("")
    for seg in _segmentos(diario):
        bl = diario["balance_por_segmento"].get(seg, {})
        balance_seg = bl.get("balance", [])
        atipicos_seg = bl.get("atipicos", [])
        if not balance_seg:
            continue
        mejor_seg = balance_seg[0]
        L.append(f"### 5.{_segmentos(diario).index(seg) + 1} — {seg}")
        L.append("")
        L.append(_tabla(
            ["Pos.", "Estrategia", "Clúster", "Días", "Mediana margen (COP/kWh)", "Días 1.º", "% top-3", "Rango prom."],
            [[i + 1, b.arquetipo, b.cluster_id, b.dias, _fmt(b.mediana_margen), b.dias_puesto1,
              _fmt(b.pct_top3, "%"), _fmt(b.rango_promedio)]
             for i, b in enumerate(balance_seg)],
        ))
        L.append("")
        L.append(f"La mejor estrategia del segmento **{seg}** fue **{mejor_seg.arquetipo}**"
                 f" (mediana {mejor_seg.mediana_margen} COP/kWh/día, {mejor_seg.dias_puesto1} días en 1.º).")
        if atipicos_seg:
            L.append(" Casos atípicos del segmento: "
                     + "; ".join(f"{b.arquetipo} (E{b.cluster_id}, {b.dias} días)" for b in atipicos_seg) + ".")
        L.append("")
    L.append("### 5.4 Matriz estrategia × segmento (mediana del margen, COP/kWh)")
    L.append("")
    L.append("Cada celda es la mediana del **margen diario** de esa estrategia dentro de ese segmento (días ="
             " días presentes), la misma métrica del ranking por segmento. En **negrita**, la mejor estrategia"
             " de cada columna (segmento); las estrategias atípicas del segmento se marcan y no se cuentan:")
    L.append("")
    L.append(_matriz_estrategia_x_segmento(diario))
    L.append("")
    L.append(_lectura_por_segmento(diario))
    L.append("")

    # ---------- Balance del período ----------
    L.append("## 6. Balance del período")
    L.append("")
    L.append(_tabla(
        ["Pos.", "Estrategia", "Clúster", "Días", "Mediana margen (COP/kWh)", "Media margen",
         "Días 1.º", "% top-3", "Rango prom.", "Tendencia 2.ª−1.ª mitad"],
        [[i + 1, b.arquetipo, b.cluster_id, b.dias, _fmt(b.mediana_margen), _fmt(b.media_margen),
          b.dias_puesto1, _fmt(b.pct_top3, "%"), _fmt(b.rango_promedio), _fmt(b.tendencia)]
         for i, b in enumerate(diario["balance"])],
    ))
    L.append("")
    L.append(_narrativa_balance(diario))
    L.append("")
    if diario.get("atipicos"):
        L.append("**Casos atípicos** (presentes en pocos días; fuera del ranking):")
        L.append("")
        L.append(_tabla(
            ["Estrategia", "Clúster", "Días", "Mediana margen (COP/kWh)", "Días 1.º"],
            [[b.arquetipo, b.cluster_id, b.dias, _fmt(b.mediana_margen), b.dias_puesto1]
             for b in diario["atipicos"]],
        ))
        L.append("")

    # ---------- Limitaciones ----------
    L.append("## 7. Limitaciones")
    L.append("")
    L.append("1. **No hay precio ni margen real por agente** en elecdb: todo valor COP es volumen × precio"
             " promedio de sistema del día; el margen es un artefacto de modelado (Pv=350 COP/kWh fijo).")
    L.append("2. **K-Means es descriptivo**: asume esfericidad/varianza similar; k, features y escalado son"
             " decisiones del analista; resultados dependen de la ventana.")
    L.append("3. **Agentes diminutos** (volúmenes < 0,01 GWh/día) producen features ruidosas y márgenes extremos;"
             " se mitigan con log1p y clip, pero distorsionan las medianas de su estrategia.")
    L.append("4. **SICEP diario** es 0 imputado en puros no regulados (no compran regulado); `tiene_sicep`"
             " distingue '0 % convocatoria' de 'no aplica'.")
    L.append("5. **Sin precios de contrato por agente**: el margen solo capta el mix y el nivel de precio de"
             " sistema; no hay señal de negociación individual ni de contraparte.")
    L.append("6. Resultados describen **comportamiento pasado** (Ene–Jul 2026), no predicción.")
    L.append("")

    return "\n".join(L)


def _narrativa_balance(diario: dict) -> str:
    if not diario["balance"]:
        return "_Sin datos._"
    mejor = diario["balance"][0]
    if len(diario["balance"]) > 1:
        segundo = diario["balance"][1]
        linea2 = (f"En segundo lugar, **{segundo.arquetipo}** ({segundo.mediana_margen} COP/kWh/día,"
                  f" {segundo.dias_puesto1} días en 1.º).")
    else:
        linea2 = ""
    p = diario["perfiles"].get(mejor.cluster_id)
    perfil = ""
    if p:
        perfil = (f" Perfil: {p.n} agentes-día de {p.n_agentes} agentes; "
                  f"no regulado {p.medias.get('pct_noreg', 0.0):.0f} %, cobertura"
                  f" {p.medias.get('pct_cobertura', 0.0):.0f} %, exposición"
                  f" {p.medias.get('pct_exposicion', 0.0):.0f} %.")
    tend = ""
    if mejor.tendencia > 0:
        tend = " Su tendencia fue **positiva** (mejoró en la 2.ª mitad del período)."
    elif mejor.tendencia < 0:
        tend = " Su tendencia fue **negativa** (empeoró en la 2.ª mitad del período)."
    else:
        tend = " Su tendencia fue estable en el período."
    return (f"La estrategia **{mejor.arquetipo}** dominó el período: mediana de {mejor.mediana_margen}"
            f" COP/kWh/día, {mejor.dias_puesto1} días en el 1.er puesto ({mejor.pct_top3} % de días top-3),"
            f" rango promedio {mejor.rango_promedio}.{perfil}{tend} {linea2}"
            " El resultado es un artefacto del modelo (Pv=350 fijo) y sirve para comparar estrategias, no como"
            " margen real del negocio.")


def guardar(datos: dict, cfg: dict) -> Path:
    md = renderizar(datos, cfg)
    destino = BASE_DIR / cfg["informe_diario"]["salida"]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(md, encoding="utf-8")
    return destino