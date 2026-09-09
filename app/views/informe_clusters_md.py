"""VIEW: renderizado del informe k-means en Markdown (docs/informe_arquetipos_kmeans.md).

Recibe los resultados del estudio de clustering (datos["clustering"]) y produce
Markdown. Jamás consulta la BD. Independiente de informe_md.py.
"""
from __future__ import annotations

from pathlib import Path

from app.models.entities import PerfilCluster

BASE_DIR = Path(__file__).resolve().parent.parent.parent


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


def _med(feature: str, p: PerfilCluster, agrega_extra: bool = True) -> tuple[str, str]:
    """(media, mediana) formateadas de una feature del perfil."""
    med = p.medias.get(feature, 0.0)
    medn = p.medianas.get(feature, 0.0)
    suf = ""
    if feature in ("pct_noreg", "pct_cobertura", "pct_exposicion", "pct_sicep", "pct_perdidas"):
        suf = "%"
    elif feature == "intensidad_pico":
        suf = "%"
    elif feature == "dema_gwh":
        suf = " GWh"
    return _fmt(med, suf), _fmt(medn, suf)


def renderizar(datos: dict, cfg: dict) -> str:
    cl = datos["clustering"]
    f_1 = datos["f-1"]
    L: list[str] = []

    # ---------- Encabezado ----------
    L.append(f"# {cfg['informe_kmeans']['titulo']}")
    L.append("")
    L.append(f"> Proyecto SFEIA · Generado {cfg['ventana']['foco_ini']} → {cfg['ventana']['foco_fin']} (H1-2026)"
             f" · Población: **{cl['muestra_total']} comercializadores** · K-Means de scikit-learn"
             f" (k={cl['k_seleccionado']}, semilla={cfg['clustering']['random_state']}).")
    L.append("")
    L.append("> Estudio **complementario e independiente** del benchmark por segmento"
             " (docs/informe_estrategias_comercializacion.md). No modifica la segmentación F-1 ni la tipificación F6.")
    L.append("")

    # ---------- Resumen ejecutivo ----------
    L.append("## Resumen ejecutivo")
    L.append("")
    perfiles = cl["perfiles"]
    for cid in sorted(perfiles):
        p = perfiles[cid]
        L.append(f"- **Clúster {cid} · {p.arquetipo}** ({p.n} agentes): composición {_composicion(p)}.")
    L.append(f"- Silhouette medio (k={cl['k_seleccionado']}): **{_mejor_silhouette(cl)}**."
             f" ARI vs segmento F-1: **{cl['vs_segmento']['ari']}**;"
             f" ARI vs arquetipo por reglas (muestra 25): **{cl['vs_tipificacion']['ari']}**.")
    L.append("")

    # ---------- Metodología ----------
    L.append("## 1. Metodología")
    L.append("")
    L.append("Features por agente (perfil reportado en escala original; la matriz de clustering usa"
             " transformaciones documentadas):")
    L.append("")
    _DESCRIPCION_FEATURE = {
        "log_dema": ("Tamaño", "log1p(DemaCome semestral, GWh)"),
        "pct_noreg": ("Mercado objetivo (D2)", "% de demanda no regulada"),
        "pct_cobertura": ("Abastecimiento (D1)", "% cobertura con contratos — log1p en la matriz (clip 300 %)"),
        "pct_exposicion": ("Riesgo spot (D4)", "% exposición a bolsa — log1p en la matriz"),
        "pct_sicep": ("Convocatoria (D2)", "% compras reguladas con registro SICEP (NaN → 0)"),
        "tiene_sicep": ("Convocatoria (D2)", "1 si compra regulado, 0 si puro no regulado"),
        "pct_perdidas": ("Red (D4)", "% pérdidas (DemaCome − DemaReal)/DemaCome"),
        "intensidad_pico": ("Flexibilidad (D5)", "posición neta bolsa PICO / demanda (%)"),
    }
    L.append(_tabla(
        ["Feature", "Dimensión", "Descripción"],
        [[f] + list(_DESCRIPCION_FEATURE[f]) for f in cl["features"]],
    ))
    L.append("")
    L.append(f"Escalado: **{cfg['clustering']['scaler']}**; elección de k por **{cfg['clustering']['metodo_k']}**"
             f" sobre k∈[{cfg['clustering']['k_min']},{cfg['clustering']['k_max']}];"
             f" `random_state={cfg['clustering']['random_state']}`, `n_init={cfg['clustering']['n_init']}`.")
    if "pct_perdidas" not in cl["features"] or "intensidad_pico" not in cl["features"]:
        L.append("")
        L.append("**Features evaluadas y excluidas:** `pct_perdidas` e `intensidad_pico` se probaron y se"
                 " descartaron por silhouette inferior y ruido extremo en agentes diminutos (posición neta/venta"
                 " desproporcionada a su demanda). Todo el conjunto es reproducible desde `config/config.yaml`.")
    L.append("")
    L.append("> **Matiz de transparencia:** el k-means no está *libre de sesgo*: la selección de features,"
             " el escalado, la imputación de SICEP y el número de clústeres siguen siendo decisiones del analista."
             " Lo que elimina es el etiquetado/umbralización manual de arquetipos. Todo es reproducible desde"
             " `config/config.yaml`.")
    L.append("")

    # ---------- Elección de k ----------
    L.append("## 2. Elección de k")
    L.append("")
    L.append(_tabla(
        ["k", "Silhouette medio", "Inercia"],
        [[r["k"], _fmt(r["silhouette"]), _fmt(r["inercia"])] for r in cl["resultados_k"]],
    ))
    L.append("")
    L.append(f"Se selecciona **k={cl['k_seleccionado']}** (máximo silhouette medio; los demás k se reportan"
             " para sensibilidad).")
    L.append("")

    # ---------- Perfiles por clúster ----------
    L.append("## 3. Perfiles por clúster")
    L.append("")
    for cid in sorted(perfiles):
        p = perfiles[cid]
        L.append(f"### Clúster {cid} — {p.arquetipo} ({p.n} agentes)")
        L.append("")
        L.append("Miembros: " + ", ".join(p.miembros))
        L.append("")
        L.append("Composición por segmento F-1: " + _composicion(p) + ".")
        L.append("")
        L.append(_tabla(
            ["Feature", "Media", "Mediana"],
            [[f, _med(f, p)[0], _med(f, p)[1]] for f in cl["features"]],
        ))
        L.append("")
        L.append("Agentes representativos (mayor demanda): **"
                 + ", ".join(_representativos(cl, cid)) + "**.")
        L.append("")

    # ---------- Arquetipos emergentes ----------
    L.append("## 4. Arquetipos emergentes (interpretación)")
    L.append("")
    for cid in sorted(perfiles):
        p = perfiles[cid]
        L.append(f"**{p.arquetipo}** (Clúster {cid}): " + _descripcion(p) + f" — {_fmt_medias_clave(p)}")
    L.append("")

    # ---------- Contrapunto y validación ----------
    L.append("## 5. Contrapunto y validación")
    L.append("")
    vs = cl["vs_segmento"]
    L.append("### 5.1 Clúster × segmento F-1")
    L.append("")
    L.append(_tabla(
        ["Clúster"] + vs["segmentos"],
        [[f"C{cid}"] + vs["tabla"][i] for i, cid in enumerate(vs["clusters"])],
    ))
    L.append("")
    L.append(f"**ARI (clúster vs segmento por tamaño): {vs['ari']}.** Un valor bajo indica que el tamaño"
             " no es la única dimensión que separa a los agentes (hipótesis M0).")
    L.append("")
    vt = cl["vs_tipificacion"]
    L.append("### 5.2 Clúster × arquetipo por reglas (muestra 25)")
    L.append("")
    if vt.get("tabla"):
        L.append(_tabla(
            ["Clúster"] + vt["reglas"],
            [[f"C{cid}"] + vt["tabla"][i] for i, cid in enumerate(vt["clusters"])],
        ))
    else:
        L.append("_Sin datos._")
    L.append("")
    L.append(f"**ARI (clúster vs tipificación por reglas, n={vt.get('n', 0)}): {vt.get('ari')}.**")
    if vt.get("desacuerdos"):
        L.append("")
        L.append("Casos donde el arquetipo por reglas no coincide con el mayoritario del clúster:")
        L.append("")
        L.append(_tabla(
            ["Agente", "Arquetipo por reglas", "Arquetipo del clúster"],
            [[d["codigo"], d["arquetipo_regla"], d["arquetipo_cluster"]] for d in vt["desacuerdos"]],
        ))
    L.append("")

    # ---------- Estrategias por arquetipo ----------
    L.append("## 6. Estrategias por arquetipo")
    L.append("")
    L.append(_estrategias(cl))
    L.append("")

    # ---------- Limitaciones ----------
    L.append("## 7. Limitaciones")
    L.append("")
    L.append("1. **K-means asume esfericidad y varianza similar** por clúster; el resultado depende del"
             " escalado (standard/robust) y de transformaciones (log/clip).")
    L.append("2. **n=65 es pequeño**: los clústeres son frágiles ante cambios de features o de un agente;"
             " k se elige por silhouette pero no existe un 'k verdadero'.")
    L.append("3. **El 'sin sesgo' es parcial**: features, escalado, imputación y k son decisiones del analista;"
             " nombrar arquetipos es una interpretación humana (sección 1).")
    L.append("4. **SICEP es 0 imputado** en puros no regulados (no compran regulado); `tiene_sicep` distingue"
             " '0% convocatoria' de 'no aplica'.")
    L.append("5. **pct_perdidas e intensidad_pico se excluyeron** por silhouette inferior y ruido extremo en"
             " agentes diminutos; `pct_cobertura` > 100 % (sobrecobertura por trading) se mitiga con clip (300 %)"
             " y log1p en la matriz.")
    L.append("6. **No hay precio ni margen por agente** (D3 no entra): los arquetipos describen estructura de"
             " compra/venta, no desempeño financiero real.")
    L.append("7. Resultados describen **comportamiento pasado** (H1-2026), no predicción.")
    L.append("")

    return "\n".join(L)


def _mejor_silhouette(cl: dict) -> float:
    for r in cl["resultados_k"]:
        if r["k"] == cl["k_seleccionado"]:
            return r["silhouette"]
    return float("nan")


def _composicion(p: PerfilCluster) -> str:
    partes = [f"{seg}: {n}" for seg, n in sorted(p.composicion_segmento.items())]
    return "; ".join(partes) if partes else "—"


def _representativos(cl: dict, cid: int) -> list[str]:
    return [a.codigo for a in cl["agentes"] if a.cluster_id == cid][:5]


def _fmt_medias_clave(p: PerfilCluster) -> str:
    return (f"no regulado {p.medias.get('pct_noreg', 0.0):.0f}% · cobertura {p.medias.get('pct_cobertura', 0.0):.0f}%"
            f" · exposición {p.medias.get('pct_exposicion', 0.0):.0f}% · SICEP {p.medias.get('pct_sicep', 0.0):.0f}%")


def _descripcion(p: PerfilCluster) -> str:
    noreg = p.medias.get("pct_noreg", 0.0)
    cob = p.medias.get("pct_cobertura", 0.0)
    expo = p.medias.get("pct_exposicion", 0.0)
    sicep = p.medias.get("pct_sicep", 0.0)
    if noreg >= 85:
        return "concentra la demanda no regulada y compite por spread spot–contrato; riesgo de capital de trabajo en escasez."
    if cob >= 120 and noreg >= 40:
        return "sobrecobertura de contratos (trading): compra y vende contratos por encima de su demanda; rol vendedor."
    if expo >= 60 and cob < 50:
        return "compra la mayor parte de su energía en bolsa (sin cobertura de contratos); máxima exposición al precio spot."
    if noreg <= 30 and expo < 15 and sicep >= 50:
        return "base regulada servida vía convocatoria pública (SICEP alto), baja exposición y cobertura de contratos amplia."
    if noreg <= 30:
        return "base regulada con tarifa CREG y exposición contenida."
    if sicep >= 50:
        return "mezcla regulado/no regulado con compras reguladas por convocatoria."
    return "mezcla regulado/no regulado sin señal clara de convocatoria; exposición y cobertura intermedias."


def _estrategias(cl: dict) -> str:
    perfiles = cl["perfiles"]
    out: list[str] = []
    for cid in sorted(perfiles):
        p = perfiles[cid]
        noreg = p.medias.get("pct_noreg", 0.0)
        cob = p.medias.get("pct_cobertura", 0.0)
        expo = p.medias.get("pct_exposicion", 0.0)
        if noreg >= 85:
            palanca = "dimensionar garantías y cobertura de contratos antes de crecer en no regulado; margen en spread spot."
        elif cob >= 120 and noreg >= 40:
            palanca = "arbitraje de contratos; vigilar descalce de cobertura y liquidez de garantías."
        elif expo >= 60 and cob < 50:
            palanca = "reducir exposición con contratos escalonados y dimensionar garantías (R2): es el arquetipo más vulnerable al spot."
        elif noreg <= 30 and expo < 15:
            palanca = "eficiencia de pérdidas y costo G; renovar cartera regulada por convocatoria (SICEP)."
        elif noreg <= 30:
            palanca = "disciplina de compras reguladas y gestión de exposición; monitorear señal SICEP."
        else:
            palanca = "balancear cartera regulada (convocatoria) y no regulada; controlar exposición spot y garantías."
        out.append(f"- **{p.arquetipo}** (Clúster {cid}): {palanca}")
    return "\n".join(out)


def guardar(datos: dict, cfg: dict) -> Path:
    md = renderizar(datos, cfg)
    destino = BASE_DIR / cfg["informe_kmeans"]["salida"]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(md, encoding="utf-8")
    return destino