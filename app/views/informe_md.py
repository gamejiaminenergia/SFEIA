"""VIEW: renderizado del informe en Markdown (docs/informe_estrategias_comercializacion.md).

Recibe los resultados del pipeline (datos) y produce Markdown. Jamás consulta la BD.
"""
from __future__ import annotations

from pathlib import Path

from app.models.entities import MatrizFila

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _tabla(encabezados: list[str], filas: list[list]) -> str:
    """Genera una tabla Markdown."""
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


def _fmt_cop(v: float) -> str:
    if v is None:
        return "—"
    return f"$ {v/1e9:,.1f} MM".replace(",", " ") if abs(v) >= 1e9 else f"$ {v/1e6:,.0f} M".replace(",", " ")


def renderizar(datos: dict, cfg: dict) -> str:
    f1, f2, f3 = datos["f1"]["tabla"], datos["f2"]["tabla"], datos["f3"]["tabla"]
    f4, f5 = datos["f4"]["tabla"], datos["f5"]["tabla"]
    f0 = datos["f0"]["contexto"]
    f_1 = datos["f-1"]
    f6 = datos["f6"]

    L: list[str] = []

    # ---------- Encabezado ----------
    L.append(f"# {cfg['informe']['titulo']}")
    L.append("")
    L.append(f"> Proyecto SFEIA · Generado {cfg['ventana']['foco_ini']} → {cfg['ventana']['foco_fin']} (H1-2026)"
             f" · Población: **{f_1['total_agentes']} comercializadores** · Muestra estratificada: **{f_1['muestra_total']}**.")
    L.append("")

    # ---------- Resumen ejecutivo ----------
    L.append("## Resumen ejecutivo")
    L.append("")
    r0 = f6["r0"]
    rseg = f_1["resumen"]
    L.append(f"- La población tiene **{f_1['total_agentes']} comercializadores**: los **{rseg['GRANDE']['n']} GRANDE** "
             f"concentran {_fmt(rseg['GRANDE']['pct_mercado'], '%')} de la demanda; los **{rseg['MEDIANO']['n']} MEDIANO** "
             f"el {_fmt(rseg['MEDIANO']['pct_mercado'], '%')}; los **{rseg['PEQUEÑO']['n']} PEQUEÑO** solo el "
             f"{_fmt(rseg['PEQUEÑO']['pct_mercado'], '%')} pero con {_fmt(rseg['PEQUEÑO']['pct_noreg'], '%')} de demanda no regulada (mix invertido).")
    L.append(f"- La **muestra estratificada** ({f_1['muestra_total']} agentes) tipifica los arquetipos por segmento; ver secciones 2 y 8.")
    L.append("")

    # ---------- F0 Contexto ----------
    L.append("## 1. Contexto de mercado (F0 · C13)")
    L.append("")
    L.append(_tabla(
        ["Mes", "PBM prom (COP/kWh)", "PBM máx", "PBM mín", "Precio escasez", "Precio contratos", "DemSIN (GWh)", "¿PBM > escasez?", "Spread cont–bolsa"],
        [[r["mes"], _fmt(r["pbm_prom_cop"]), _fmt(r["pbm_max_cop"]), _fmt(r["pbm_min_cop"]),
          _fmt(r["prec_escasez_prom_cop"]), _fmt(r["prec_contratos_prom_cop"]),
          _fmt(r["dema_sin_total_gwh"]), "SÍ" if r["pbm_sobre_escasez"] else "no",
          _fmt(r["spread_contrato_bolsa"])] for r in f0],
    ))
    L.append("")
    meses_esc = [r["mes"] for r in f0 if r["pbm_sobre_escasez"]]
    L.append(f"Meses con PBM promedio sobre el precio de escasez: **{', '.join(meses_esc) if meses_esc else 'ninguno'}** "
             f"(el precio de escasez es el techo del riesgo spot, H4).")
    L.append("")

    # ---------- F-1 Segmentación ----------
    L.append("## 2. Segmentación por tamaño (F-1)")
    L.append("")
    L.append("| Segmento | Criterio (GWh/sem) | Agentes | Demanda (GWh) | % mercado | % reg | % no-reg |")
    L.append("|----------|--------------------|--------:|--------------:|----------:|------:|---------:|")
    for seg, r in f_1["resumen"].items():
        L.append(f"| **{seg}** | — | {r['n']} | {_fmt(r['gwh'])} | {_fmt(r['pct_mercado'], '%')} | "
                 f"{_fmt(r['pct_reg'], '%')} | {_fmt(r['pct_noreg'], '%')} |")
    L.append("")
    L.append("Muestra estratificada por segmento y arquetipo:")
    L.append("")
    for seg, codes in f_1["muestra"].items():
        L.append(f"- **{seg}** ({len(codes)}): " + ", ".join(codes))
    L.append("")

    # ---------- F1 Cartera ----------
    L.append("## 3. Perfil de cartera (F1 · C01–C03 + SICEP)")
    L.append("")
    L.append(_tabla(
        ["Segmento", "Agente", "Demanda GWh", "% reg", "Compra bolsa GWh", "Venta bolsa GWh", "Pos neta bolsa",
         "Compra contratos GWh", "Venta contratos GWh", "Pos neta contratos", "% SICEP (reg)"],
        [[f["segmento"], f["codigo"], _fmt(f["dema_gwh"]), _fmt(f["pct_reg"], "%"),
          _fmt(f["comp_bolsa_gwh"]), _fmt(f["vent_bolsa_gwh"]), _fmt(f["pos_net_bolsa_gwh"]),
          _fmt(f["comp_cont_gwh"]), _fmt(f["vent_cont_gwh"]), _fmt(f["pos_net_cont_gwh"]),
          _fmt(f["pct_sicep"], "%")] for f in f1],
    ))
    L.append("")

    # ---------- F2 Cobertura ----------
    L.append("## 4. Cobertura y exposición a bolsa (F2 · C04)")
    L.append("")
    L.append(_tabla(
        ["Segmento", "Agente", "% Cobertura contratos", "% Exposición bolsa"],
        [[f["segmento"], f["codigo"], _fmt(f["pct_cobertura"], "%"), _fmt(f["pct_exposicion"], "%")] for f in f2],
    ))
    L.append("")

    # ---------- F3 Pico/valle ----------
    L.append("## 5. Posición neta por bloque horario (F3 · C05)")
    L.append("")
    L.append(_tabla(
        ["Segmento", "Agente", "Compra PICO (GWh)", "Posición neta PICO", "Rol PICO", "Compra fuera pico (GWh)", "Posición neta fuera", "Rol fuera"],
        [[f["segmento"], f["codigo"], _fmt(f["comp_pico_gwh"]), _fmt(f["pos_pico_gwh"]), f["rol_pico"],
          _fmt(f["comp_fuera_gwh"]), _fmt(f["pos_fuera_gwh"]), f["rol_fuera"]] for f in f3],
    ))
    L.append("")

    # ---------- F4 Mix ----------
    L.append("## 6. Mix de mercado objetivo (F4 · C01/C08, contexto CIIU)")
    L.append("")
    L.append(_tabla(
        ["Segmento", "Agente", "% Regulado", "% No regulado", "% Pérdidas"],
        [[f["segmento"], f["codigo"], _fmt(f["pct_reg"], "%"), _fmt(f["pct_noreg"], "%"), _fmt(f["pct_perdidas"], "%")] for f in f4],
    ))
    L.append("")
    L.append("Top 10 sectores CIIU de demanda no regulada del SIN (contexto, C06):")
    L.append("")
    L.append(_tabla(["Sector CIIU", "GWh no-reg"],
                    [[s, _fmt(g)] for s, g in datos["f4"]["top_ciiu"]]))
    L.append("")

    # ---------- F5 Financiero ----------
    L.append("## 7. Precio y riesgo financiero (F5 · C15 + modelo C16–C18)")
    L.append("")
    L.append("> Valores COP = **estimaciones** (volumen × precio promedio de sistema). El margen es el **modelo C18** "
             "con parámetros fijos (Pv=350, cargo=76,1): NO es el margen real del agente.")
    L.append("")
    L.append(_tabla(
        ["Segmento", "Agente", "Costo energía est. (COP/kWh)", "Garantía est.", "Costo garantía", "Provisión cartera", "Margen modelo (COP/kWh)"],
        [[f["segmento"], f["codigo"], _fmt(f["costo_energia_cop_kwh"]), _fmt_cop(f["garantia_exigida_cop"]),
          _fmt_cop(f["costo_garantia_cop"]), _fmt_cop(f["provision_cartera_cop"]), _fmt(f["margen_modelo_cop_kwh"])] for f in f5],
    ))
    L.append("")
    L.append("Spread contratos–bolsa de mercado (C10, nivel sistema):")
    L.append("")
    L.append(_tabla(
        ["Mes", "Precio contratos", "Precio bolsa", "Spread"],
        [[r["mes"], _fmt(r["prec_contratos_prom_cop"]), _fmt(r["prec_bolsa_prom_cop"]), _fmt(r["spread_contratos_vs_bolsa"])] for r in datos["f5"]["spread_mercado"]],
    ))
    L.append("")

    # ---------- F6 Matriz ----------
    L.append("## 8. Matriz por segmento y arquetipos (F6)")
    L.append("")
    L.append(_tabla(
        ["Segmento", "Agente", "Dema GWh", "% Reg", "% Cobertura", "% Exposición", "% SICEP", "% Pérdidas", "Costo energía", "Garantía est.", "Arquetipo"],
        [[f.segmento, f.codigo, _fmt(f.dema_gwh), _fmt(f.pct_reg, "%"), _fmt(f.pct_cobertura, "%"),
          _fmt(f.pct_exposicion, "%"), _fmt(f.pct_sicep, "%"), _fmt(f.pct_perdidas, "%"),
          _fmt(f.costo_energia_cop_kwh), _fmt_cop(f.garantia_est_cop), f.arquetipo] for f in f6["matriz"]],
    ))
    L.append("")

    # ---------- R0–R5 ----------
    L.append("## 9. Contraste de hipótesis R0–R5")
    L.append("")
    L.append(f"**R0 — el tamaño condiciona la estrategia.** Por segmento: % no regulado prom "
             f"{r0['GRANDE']['pct_noreg_prom']}% (GRANDE) · {r0['MEDIANO']['pct_noreg_prom']}% (MEDIANO) · "
             f"{r0['PEQUEÑO']['pct_noreg_prom']}% (PEQUEÑO); cobertura de contratos prom "
             f"{r0['GRANDE']['cobertura_prom']}% / {r0['MEDIANO']['cobertura_prom']}% / {r0['PEQUEÑO']['cobertura_prom']}%; "
             f"exposición a bolsa prom {r0['GRANDE']['exposicion_prom']}% / {r0['MEDIANO']['exposicion_prom']}% / {r0['PEQUEÑO']['exposicion_prom']}%.")
    L.append(f"**R1 — no regulado = mayor apetito de riesgo spot.** Correlación % no regulado vs % exposición: "
             f"**{f6['r1']['corr_pct_noreg_vs_exposicion']}** (n={f6['r1']['n']}).")
    L.append(f"**R2 — mayor exposición → mayor garantía estimada.** Correlación % exposición vs log(garantía): "
             f"**{f6['r2']['corr_pct_exposicion_vs_log_garantia']}** (estructural: garantía = 25% × exposición valorada a precio de sistema).")
    L.append(f"**R3 — SICEP (proxy convocatoria).** Promedio % compras reguladas con registro SICEP: "
             f"GRANDE {f6['r3']['por_segmento']['GRANDE']['prom']}%, MEDIANO {f6['r3']['por_segmento']['MEDIANO']['prom']}%, "
             f"PEQUEÑO {f6['r3']['por_segmento']['PEQUEÑO']['prom']}%; **CSIC {f6['r3']['csic_pct_sicep']}%** (señal: cartera antigua fuera de convocatoria).")
    expuestos = ", ".join(f"{a['codigo']} ({a['pct_exposicion']}%)" for a in f6["r4"]["agentes_alta_exposicion"]) or "ninguno"
    L.append(f"**R4 — escasez y descalce.** Meses con PBM > precio de escasez (ventana amplia 2024-2026): "
             f"**{', '.join(f6['r4']['meses_pbm_sobre_escasez']) if f6['r4']['meses_pbm_sobre_escasez'] else 'ninguno'}**. "
             f"Agentes de la muestra con exposición ≥30% en H1-2026: {expuestos}.")
    L.append(f"**R5 — pérdidas vs regulado.** Correlación % regulado vs % pérdidas: **{f6['r5']['corr_pct_reg_vs_perdidas']}** "
             f"(la eficiencia en pérdidas es palanca de margen del segmento regulado).")
    L.append("")

    # ---------- Estrategias ----------
    L.append("## 10. Estrategias recomendadas por segmento")
    L.append("")
    L.append("**GRANDE (integrados de red):** apalancarse en escala y cobertura de contratos vía convocatoria (SICEP ≥80%); "
             "el margen se juega en eficiencia de pérdidas y costo G, no en exposición spot.")
    L.append("**MEDIANO (regionales y traders mixtos):** los regionales protegen el regulado con convocatorias y baja exposición; "
             "los traders mixtos deben dimensionar garantías (R2) antes de crecer en no regulado.")
    L.append("**PEQUEÑO (traders no regulado / frontera):** apuesta de spread spot–contrato con exposición estructural alta (R1); "
             "su riesgo es el capital de trabajo y la liquidez de garantías en eventos de escasez (R4).")
    L.append("")

    # ---------- Limitaciones ----------
    L.append("## 11. Limitaciones")
    L.append("")
    L.append("1. Valores COP son estimaciones (precio promedio de sistema); no hay precio ni contraparte por agente en elecdb.")
    L.append("2. El margen por kWh es el modelo C18 (parámetros fijos), no el margen real; CSIC y los puros salen con margen negativo artificial.")
    L.append("3. R0–R5 son contrastaciones descriptivas sobre H1-2026, no relaciones causales.")
    L.append("4. TIE y AGPE salieron NULL en la muestra; la autocontratación (tope 10%) no es medible.")
    L.append("")

    return "\n".join(L)


def guardar(datos: dict, cfg: dict) -> Path:
    md = renderizar(datos, cfg)
    destino = BASE_DIR / cfg["informe"]["salida"]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(md, encoding="utf-8")
    return destino