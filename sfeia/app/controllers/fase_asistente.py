"""CONTROLLER del asistente imitador (agente XXXC).

Orquesta todo el flujo:
1. Resuelve y valida las ventanas de estudio e impacto (contra el límite de
   datos de elecdb).
2. Corre F-1 (segmentación) + FaseDiaria (estrategias diarias) sobre la
   **ventana de estudio** (config con ventana sobreescrita).
3. Selecciona a los **top-N** maestros del (segmento, estrategia).
4. Construye la **política de clonación** (BC por bin de spread).
5. Lee la ventana de impacto, simula a XXXC con la política y compara su
   margen contra el real de maestros y segmento.

Adiciones del plan de investigación (`docs/investigacion_imitacion_traders_profesionales.md`):
- P0.1 Holdout de selección: la ventana de estudio se parte en sub-estudio
  (elegir maestros) + sub-validación (medir si la selección generaliza).
- P0.2 Bootstrap skill-vs-luck (¿el top-N supera al azar?).
- P0.3 Deduplicación de maestros correlacionados (N efectivo).
- P0.4 Métricas de riesgo en la selección (en `AgenteMaestro`).
- P0.5 DSR aproximado + ratio de replicación IS→OOS.
- P1.1 Contexto ex-ante: la decisión usa el spread del día anterior.
- P1.2 Agregación ponderada de los perfiles de los maestros (pesos tipo EWA).
- P1.3 Zona de confianza: fuera de la distribución se reduce la exposición.
- P1.4 Régimen hidrológico (nivel agregado de embalses) por día.
- P2.1 Capacidad, P2.2 kill-switch, P2.3 walk-forward.

SOLID: es el único componente que habla con el repo y los controladores del
estudio; los services son lógica pura inyectada con datos y parámetros.
"""
from __future__ import annotations

import copy
from datetime import date, timedelta
from statistics import median

from sfeia.app.controllers.fase_diaria import FaseDiaria
from sfeia.app.controllers.fase_segmentacion import FaseSegmentacion
from sfeia.app.services import diario

from sfeia.app.models.entities import (
    ParametrosAsistente,
    PerfilAccion,
    SimulacionDia,
    VentanasResueltas,
)
from sfeia.app.services import clonacion, contexto, maestros, scorecard, simulacion


def _parse(s: str) -> date:
    return date.fromisoformat(s)


def _iso(d: date) -> str:
    return d.isoformat()


class FaseAsistente:
    def __init__(self, repo, cfg: dict):
        self.repo = repo
        self.cfg = cfg

    # ------------------------------------------------------------------ fechas
    def _resolver_fechas(self, p: ParametrosAsistente) -> VentanasResueltas:
        v = self.cfg["ventana"]
        n_impacto = p.dias_impacto_por_defecto
        n_estudio = int(self.cfg["asistente"].get("dias_estudio_por_defecto", 30))
        foco_fin = _parse(v["foco_fin"])

        estudio_fin = _parse(p.estudio_fin) if p.estudio_fin else foco_fin - timedelta(days=n_impacto)
        estudio_ini = _parse(p.estudio_ini) if p.estudio_ini else estudio_fin - timedelta(days=n_estudio - 1)
        impacto_ini = _parse(p.impacto_ini) if p.impacto_ini else estudio_fin + timedelta(days=1)
        impacto_fin = _parse(p.impacto_fin) if p.impacto_fin else foco_fin

        return VentanasResueltas(
            estudio_ini=_iso(estudio_ini),
            estudio_fin=_iso(estudio_fin),
            impacto_ini=_iso(impacto_ini),
            impacto_fin=_iso(impacto_fin),
        )

    def _validar_fechas(self, w: VentanasResueltas, max_sistema: date) -> None:
        estudio_ini, estudio_fin = _parse(w.estudio_ini), _parse(w.estudio_fin)
        impacto_ini, impacto_fin = _parse(w.impacto_ini), _parse(w.impacto_fin)

        if not (estudio_ini <= estudio_fin < impacto_ini <= impacto_fin):
            raise ValueError(
                "Ventanas inválidas: debe cumplirse estudio_ini ≤ estudio_fin < impacto_ini ≤ impacto_fin "
                f"(recibido estudio {w.estudio_ini}..{w.estudio_fin}, impacto {w.impacto_ini}..{w.impacto_fin})."
            )
        if estudio_ini > max_sistema:
            raise ValueError(
                f"La ventana de estudio inicia el {w.estudio_ini}, después de la última fecha con datos "
                f"({max_sistema.isoformat()})."
            )
        if estudio_fin > max_sistema:
            raise ValueError(
                f"La ventana de estudio termina el {w.estudio_fin}, pero elecdb solo tiene datos de precios "
                f"de sistema hasta {max_sistema.isoformat()}."
            )
        if impacto_ini > max_sistema:
            raise ValueError(
                f"La ventana de impacto inicia el {w.impacto_ini}, después de la última fecha con datos "
                f"({max_sistema.isoformat()})."
            )
        if impacto_fin > max_sistema:
            raise ValueError(
                f"La ventana de impacto termina el {w.impacto_fin}, pero elecdb solo tiene datos de precios "
                f"de sistema hasta {max_sistema.isoformat()}. Reduce la ventana o pasa fechas explícitas "
                "dentro del rango disponible."
            )

    # ----------------------------------------------------------- estudio auxiliar
    def _correr_estudio(self, ini: str, fin: str) -> dict:
        """F-1 + FaseDiaria sobre una ventana dada (config con ventana sobreescrita)."""
        cfg_e = copy.deepcopy(self.cfg)
        cv = cfg_e["ventana"]
        cv["foco_ini"] = ini
        cv["foco_fin"] = fin
        cv["fin_c_familia"] = _iso(_parse(fin) + timedelta(days=1))
        cv["fin_c15"] = fin
        datos: dict = {}
        FaseSegmentacion(self.repo, cfg_e).ejecutar(datos)
        FaseDiaria(self.repo, cfg_e).ejecutar(datos)
        return datos

    # --------------------------------------------------------------- ejecución
    def ejecutar(self, p: ParametrosAsistente) -> dict:
        a_cfg = self.cfg["asistente"]
        segmento = p.segmento
        estrategia = p.estrategia
        top = p.top
        params = self.cfg["modelo_financiero"]
        clip = self.cfg["diario"].get("clip_margen_cop_kwh")

        w = self._resolver_fechas(p)
        max_sistema = _parse(self.repo.fecha_max_sistema())
        self._validar_fechas(w, max_sistema)

        # ---- 1. ventana de estudio: F-1 + FaseDiaria ----
        dias_holdout = int(a_cfg.get("dias_holdout", 0) or 0)
        datos_val = None
        if dias_holdout > 0:
            sub_fin = _parse(w.estudio_fin) - timedelta(days=dias_holdout)
            if sub_fin < _parse(w.estudio_ini):
                raise ValueError(
                    "`dias_holdout` deja la sub-validación vacía: reduce el holdout o alarga la ventana de estudio "
                    f"(estudio {w.estudio_ini}..{w.estudio_fin})."
                )
            datos_sel = self._correr_estudio(w.estudio_ini, _iso(sub_fin))
            datos_val = self._correr_estudio(_iso(sub_fin + timedelta(days=1)), w.estudio_fin)
            ventana_estudio = {"ini": w.estudio_ini, "fin": _iso(sub_fin)}
            ventana_validacion = {"ini": _iso(sub_fin + timedelta(days=1)), "fin": w.estudio_fin}
        else:
            datos_sel = self._correr_estudio(w.estudio_ini, w.estudio_fin)
            ventana_estudio = {"ini": w.estudio_ini, "fin": w.estudio_fin}
            ventana_validacion = None

        d = datos_sel["diario"]
        if d["n_agentes"] == 0:
            raise ValueError(
                f"No hay comercializadores con demanda en la ventana de estudio {w.estudio_ini}..{w.estudio_fin}."
            )
        segmento_por_codigo = {c: a.segmento.value for c, a in datos_sel["f-1"]["por_codigo"].items()}

        # ---- 2. maestros (top-N del segmento+estrategia) ----
        relativo = bool(a_cfg.get("seleccion_por_relativo", True))
        maestros_lista = maestros.seleccionar_maestros(
            d["agentes"], segmento, estrategia, top, d["n_dias"], p.min_dias_pct, relativo=relativo
        )
        if not maestros_lista:
            disponibles = sorted({perf.arquetipo for perf in d["perfiles"].values()})
            raise ValueError(
                f"No hay agentes del segmento **{segmento}** jugando la estrategia **{estrategia}** en la "
                f"ventana de estudio {ventana_estudio['ini']}..{ventana_estudio['fin']}. Estrategias presentes: "
                + ", ".join(disponibles)
                + ". Ajusta el segmento, la estrategia o la ventana de estudio."
            )
        codigos_maestros = {m.codigo for m in maestros_lista}

        # ---- P0.1: ¿la selección generaliza? (holdout) ----
        holdout = None
        if datos_val is not None:
            holdout = maestros.persistencia_seleccion(
                datos_val["diario"]["agentes"], segmento, estrategia, codigos_maestros,
                datos_val["diario"]["n_dias"], p.min_dias_pct,
            )

        # ---- P0.2: bootstrap skill-vs-luck ----
        bootstrap = maestros.bootstrap_skill_luck(
            d["agentes"], segmento, estrategia, top, d["n_dias"],
            n_boot=int(a_cfg.get("n_boot", 1000)),
            semilla=int(self.cfg["diario"].get("random_state", 42)),
            min_dias_pct=p.min_dias_pct,
            relativo=relativo,
        )

        # ---- P1.2: pesos de agregación (en vez del top-N duro) ----
        if relativo:
            # con selección relativa la referencia es "superar al segmento" (relativo = 0)
            mediana_segmento_estudio = 0.0
        else:
            seg_marg = [a.margen_kwh for a in d["agentes"] if a.segmento == segmento]
            mediana_segmento_estudio = sorted(seg_marg)[len(seg_marg) // 2] if seg_marg else None
        pesos = None
        if a_cfg.get("ponderar_politica", False):
            pesos = maestros.pesos_maestros(
                maestros_lista, mediana_segmento=mediana_segmento_estudio,
                eta=float(a_cfg.get("pesos_eta", 1.0)),
            )

        # ---- 3. política de clonación (BC) ----
        politica = clonacion.construir_politica(
            d["agentedia"],
            d["etiquetas"],
            d["labels"],
            d["perfiles"],
            codigos_maestros,
            segmento,
            estrategia,
            segmento_por_codigo,
            a_cfg["bins_spread"],
            pesos=pesos,
        )

        # ---- 4. ventana de impacto: datos reales + simulación de XXXC ----
        rows_impacto = self.repo.diario(w.impacto_ini, _iso(_parse(w.impacto_fin) + timedelta(days=1)))
        if not rows_impacto:
            raise ValueError(
                f"No hay datos de mercado para la ventana de impacto {w.impacto_ini}..{w.impacto_fin} "
                f"(última fecha con datos: {max_sistema.isoformat()})."
            )
        agentedia_impacto = diario.construir_agente_dia(rows_impacto)
        for ad in agentedia_impacto.values():
            ad["desempeno"] = diario.desempeno_diario(ad, params)
        diario.aplicar_clip_margen(agentedia_impacto, clip)

        dema_kwh = (
            p.demanda_dia_gwh * 1e6
            if p.demanda_dia_gwh
            else contexto.demanda_referencia(d["agentedia"], segmento_por_codigo, segmento)
        )
        if dema_kwh <= 0:
            raise ValueError(
                f"No se pudo determinar la demanda de referencia del segmento **{segmento}** en el estudio y no "
                "se pasó `--demanda-dia-gwh`."
            )

        # ---- P1.4: régimen hidrológico (nivel agregado de embalses por día) ----
        usar_hidro = bool(a_cfg.get("usar_regimen_hidrologico", True))

        def _nivel_por_dia(ini: str, fin: str) -> dict[str, float]:
            if not usar_hidro:
                return {}
            filas = self.repo.contexto_hidrologia(ini, _iso(_parse(fin) + timedelta(days=1)))
            return {str(r["fecha"])[:10]: float(r["nivel_agregado_pct"]) for r in filas}

        nivel_por_dia_sel = _nivel_por_dia(ventana_estudio["ini"], ventana_estudio["fin"])
        nivel_por_dia_imp = _nivel_por_dia(w.impacto_ini, w.impacto_fin)

        # ---- P1.1/P1.3: simulación con contexto ex-ante y zona de confianza ----
        usar_previo = bool(a_cfg.get("usar_spread_previo", True))
        factor_expo = float(a_cfg.get("factor_exposicion_fuera_distribucion", 0.5))

        sims_estudio = simulacion.simular_dias(
            d["agentedia"], politica, dema_kwh, params, segmento_por_codigo, segmento,
            codigos_maestros, a_cfg["bins_spread"],
            usar_spread_previo=usar_previo, factor_exposicion_fuera=factor_expo,
            nivel_embalses_por_dia=nivel_por_dia_sel,
        )
        sims = simulacion.simular_dias(
            agentedia_impacto, politica, dema_kwh, params, segmento_por_codigo, segmento,
            codigos_maestros, a_cfg["bins_spread"],
            usar_spread_previo=usar_previo, factor_exposicion_fuera=factor_expo,
            nivel_embalses_por_dia=nivel_por_dia_imp,
        )
        resumen = simulacion.resumen_impacto(sims, dema_kwh)

        # ---- P0.5: replicación IS→OOS y DSR ----
        replicacion = simulacion.replicacion_is_oos(sims_estudio, sims)
        n_trials = bootstrap["n_agentes_candidatos"] if bootstrap else top
        dsr = simulacion.dsr_aprox([s.margen_imitacion for s in sims], n_trials=n_trials)

        distribuciones = {
            "imitacion": simulacion.distribucion([s.margen_imitacion for s in sims]),
            "maestros": simulacion.distribucion(
                [s.margen_maestros for s in sims if s.margen_maestros is not None]
            ),
            "segmento": simulacion.distribucion(
                [s.margen_segmento for s in sims if s.margen_segmento is not None]
            ),
        }
        escenarios = simulacion.escenario_escasez(
            dema_kwh, politica, list(d["agentedia"].values()), params
        )
        historial_escasez = contexto.historial_escasez(
            self.repo.historial_precios(), a_cfg["bins_spread"]
        )
        esc_by_name = {e.nombre: e for e in escenarios}
        cap = simulacion.capacidad(
            dema_kwh, d["agentedia"], segmento, segmento_por_codigo,
            float(a_cfg.get("capacidad_max_pct_segmento", 5.0)),
        )
        decision = simulacion.decision_negocio(
            dema_kwh=dema_kwh,
            mediana_benigna=resumen.mediana_imitacion,
            margen_escasez=esc_by_name["escasez_umbral"].margen_cop_kwh if "escasez_umbral" in esc_by_name else 0.0,
            margen_escasez_extrema=esc_by_name["escasez_extrema"].margen_cop_kwh if "escasez_extrema" in esc_by_name else 0.0,
            pct_escasez=historial_escasez["pct_dias_escasez"],
            pct_escasez_nino=float(a_cfg.get("pct_escasez_anio_nino", 25.0)),
            drawdown_max=distribuciones["imitacion"].drawdown_max,
            kill_switch_drawdown=float(a_cfg.get("kill_switch_drawdown_cop_kwh", 500.0)),
            capacidad=cap,
        )
        robustez = {
            "sensibilidad": maestros.sensibilidad(
                d["agentes"], segmento, estrategia, d["n_dias"],
                tops=(max(1, p.top - 2), p.top, p.top + 2),
                min_dias_pcts=(10.0, p.min_dias_pct, 30.0),
            ),
            "duplicados": maestros.detectar_duplicados(
                maestros_lista, d["agentes"], float(a_cfg.get("umbral_corr_duplicados", 0.9))
            ),
            "n_efectivo": maestros.n_efectivo(
                maestros_lista, d["agentes"], float(a_cfg.get("umbral_corr_duplicados", 0.9))
            ),
        }

        validez = {
            "holdout": holdout,
            "bootstrap": bootstrap,
            "replicacion_is_oos": replicacion,
            "dsr": dsr,
            "n_efectivo_maestros": robustez["n_efectivo"],
            "alpha_significancia": float(a_cfg.get("alpha_significancia", 0.05)),
            "seleccion_por_relativo": relativo,
        }
        alpha = validez["alpha_significancia"]
        persistencia_ok = (
            holdout is None
            or (holdout.get("pct_persistencia") is not None and holdout["pct_persistencia"] >= 50.0)
        )
        replicacion_ok = (
            replicacion.get("ratio_replicacion") is not None
            and replicacion["ratio_replicacion"] >= float(a_cfg.get("barrido", {}).get("min_replicacion", 0.5))
        )
        objetivo_valido = bool(
            bootstrap is not None
            and bootstrap["p_valor"] <= alpha
            and persistencia_ok
            and replicacion_ok
            and robustez["n_efectivo"] >= int(a_cfg.get("barrido", {}).get("min_n_efectivo", 3))
        )
        validez["objetivo_es_valido"] = objetivo_valido

        # ---- S3: alternativa recomendada si el objetivo no valida ----
        alternativa = None
        if not objetivo_valido:
            alt_info = maestros.alternativa_recomendada(
                d["agentes"], segmento, estrategia, d["n_dias"],
                min_dias_pct=p.min_dias_pct, top=max(3, min(top, 5)),
            )
            if alt_info:
                alt_seg, alt_est = alt_info["segmento"], alt_info["estrategia"]
                alt_codigos = set(alt_info["codigos"])
                alt_politica = clonacion.construir_politica(
                    d["agentedia"], d["etiquetas"], d["labels"], d["perfiles"],
                    alt_codigos, alt_seg, alt_est, segmento_por_codigo, a_cfg["bins_spread"],
                )
                alt_sims = simulacion.simular_dias(
                    agentedia_impacto, alt_politica, dema_kwh, params, segmento_por_codigo,
                    alt_seg, alt_codigos, a_cfg["bins_spread"],
                    usar_spread_previo=usar_previo, factor_exposicion_fuera=factor_expo,
                    nivel_embalses_por_dia=nivel_por_dia_imp,
                )
                alt_sims_is = simulacion.simular_dias(
                    d["agentedia"], alt_politica, dema_kwh, params, segmento_por_codigo,
                    alt_seg, alt_codigos, a_cfg["bins_spread"],
                    usar_spread_previo=usar_previo, factor_exposicion_fuera=factor_expo,
                    nivel_embalses_por_dia=nivel_por_dia_sel,
                )
                alternativa = {
                    "segmento": alt_seg,
                    "estrategia": alt_est,
                    "codigos": alt_info["codigos"],
                    "n_maestros": len(alt_info["codigos"]),
                    "mediana_relativa_top": alt_info["mediana_relativa_top"],
                    "mediana_margen_absoluto_top": alt_info["mediana_margen_absoluto_top"],
                    "politica": alt_politica,
                    "resumen": simulacion.resumen_impacto(alt_sims, dema_kwh),
                    "replicacion": simulacion.replicacion_is_oos(alt_sims_is, alt_sims),
                    "simulacion": alt_sims,
                }

        advertencias = [
            "El margen es un artefacto de modelado (Pv=350 COP/kWh fijo, precios de sistema): sirve para "
            "comparar estrategias, no como margen real del negocio.",
            "Behavioral Cloning no generaliza fuera de la distribución de spread del estudio; los bins sin "
            "entrenamiento se resuelven con el bin más cercano y los días fuera del rango entrenado reducen "
            "su exposición a bolsa (zona de confianza).",
            "La ventana de impacto usa datos ya cargados en elecdb; es retrospectiva, no predicción en vivo.",
            "Los maestros se eligen dentro de su segmento: el asistente no compite contra GRANDE por diseño.",
            "No existe ground truth real (liquidaciones XM) para validar el margen: la validación externa queda "
            "pendiente (P2.4 del plan de investigación).",
        ]
        if len(maestros_lista) < top:
            advertencias.append(
                f"Solo se encontraron {len(maestros_lista)} agentes en el (segmento, estrategia) de la ventana "
                f"de estudio; el top pedido era {top}."
            )
        if robustez["n_efectivo"] < len(maestros_lista):
            advertencias.append(
                f"N efectivo de maestros: {robustez['n_efectivo']} de {len(maestros_lista)} (hay maestros con "
                "comportamiento correlacionado/duplicado que no suman información independiente)."
            )
        if bootstrap and bootstrap["p_valor"] > validez["alpha_significancia"]:
            advertencias.append(
                f"La selección del top-{top} NO supera el bootstrap skill-vs-luck (p={bootstrap['p_valor']} > "
                f"{validez['alpha_significancia']}): el 'mejor maestro' es indistinguible del azar. "
                "No operar sin más evidencia."
            )
        if holdout and holdout.get("pct_persistencia") is not None and holdout["pct_persistencia"] < 50.0:
            advertencias.append(
                f"La selección NO se sostiene fuera de la ventana de estudio: solo "
                f"{holdout['pct_persistencia']} % de los maestros siguen en la mitad superior en la "
                f"sub-validación ({ventana_validacion['ini']}..{ventana_validacion['fin']})."
            )
        if replicacion.get("ratio_replicacion") is not None and replicacion["ratio_replicacion"] < 0.5:
            advertencias.append(
                f"La replicación IS→OOS es baja ({replicacion['ratio_replicacion']:.2f}): la política pierde "
                "más de la mitad de su desempeño del estudio al pasar al impacto."
            )
        if dsr and not dsr["significativo"]:
            advertencias.append(
                f"DSR ≈ {dsr['dsr']:.2f} (< 0.95) con {dsr['n_trials']} trials: el resultado de la imitación "
                "puede ser producto de la selección por azar."
            )
        if decision["kill_switch_activado"]:
            advertencias.append(
                f"KILL-SWITCH activado: el drawdown acumulado ({decision['drawdown_max_cop_kwh']:.0f} COP/kWh) "
                f"supera el umbral ({a_cfg.get('kill_switch_drawdown_cop_kwh', 500.0):.0f} COP/kWh)."
            )
        if cap and cap["supera_capacidad"]:
            advertencias.append(
                f"Capacidad: la demanda simulada supera el {cap['umbral_pct']:.0f} % de la demanda del segmento "
                f"({cap['pct_del_segmento']:.1f} %); la imitación no es replicable a esa escala."
            )
        if not objetivo_valido and alternativa:
            advertencias.append(
                f"La combinación objetivo NO pasó la validez (bootstrap/holdout/replicación/N efectivo). "
                f"Alternativa recomendada: **{alternativa['segmento']} · {alternativa['estrategia']}** "
                f"(relativo {alternativa['mediana_relativa_top']:.1f} COP/kWh)."
            )

        resultado = {
            "parametros": {
                "segmento": segmento,
                "estrategia": estrategia,
                "top": top,
                "demanda_dia_gwh": round(dema_kwh / 1e6, 4),
                "min_dias_pct": p.min_dias_pct,
                "ventanas": {
                    "estudio": ventana_estudio,
                    "validacion": ventana_validacion,
                    "impacto": {"ini": w.impacto_ini, "fin": w.impacto_fin},
                },
                "contexto": {
                    "usar_spread_previo": usar_previo,
                    "factor_exposicion_fuera": factor_expo,
                    "regimen_hidrologico": usar_hidro,
                },
            },
            "estudio": {
                "n_agentes": d["n_agentes"],
                "n_dias": d["n_dias"],
                "n_agentes_dia": d["n_agentes_dia"],
                "k": d["k_seleccionado"],
                "arquetipos": {cid: perf.arquetipo for cid, perf in d["perfiles"].items()},
            },
            "maestros": maestros_lista,
            "politica": politica,
            "simulacion": sims,
            "simulacion_estudio": sims_estudio,
            "resumen": resumen,
            "distribuciones": distribuciones,
            "escenarios": escenarios,
            "historial_escasez": historial_escasez,
            "decision": decision,
            "validez": validez,
            "robustez": robustez,
            "alternativa": alternativa,
            "advertencias": advertencias,
        }
        return resultado

    # ------------------------------------------------------------ walk-forward
    def ejecutar_walk_forward(self, p: ParametrosAsistente, wf_cfg: dict) -> list[dict]:
        """P2.3: serie de ventanas rodantes (estudio → impacto) hacia atrás.

        Parte de la última fecha con datos y recorre hacia atrás: en cada paso
        entrena sobre [estudio] y evalúa en [impacto] contiguo y posterior. Solo
        se reportan los resultados OOS (estándar de los quants). Devuelve la
        lista de resultados de cada paso.
        """
        max_sistema = _parse(self.repo.fecha_max_sistema())
        dias_estudio = int(wf_cfg.get("dias_estudio", 30))
        dias_impacto = int(wf_cfg.get("dias_impacto", 7))
        pasos_max = int(wf_cfg.get("pasos_max", 6))
        fin_impacto = max_sistema
        resultados: list[dict] = []
        for _ in range(pasos_max):
            impacto_fin = fin_impacto
            impacto_ini = impacto_fin - timedelta(days=dias_impacto - 1)
            estudio_fin = impacto_ini - timedelta(days=1)
            estudio_ini = estudio_fin - timedelta(days=dias_estudio - 1)
            if estudio_ini < date(2015, 1, 1):
                break
            pp = ParametrosAsistente(
                segmento=p.segmento, estrategia=p.estrategia, top=p.top,
                estudio_ini=_iso(estudio_ini), estudio_fin=_iso(estudio_fin),
                impacto_ini=_iso(impacto_ini), impacto_fin=_iso(impacto_fin),
                demanda_dia_gwh=p.demanda_dia_gwh, min_dias_pct=p.min_dias_pct,
                dias_impacto_por_defecto=dias_impacto,
            )
            try:
                resultados.append(self.ejecutar(pp))
            except ValueError:
                break
            fin_impacto = impacto_ini - timedelta(days=1)
        return resultados

    # ---------------------------------------------------------------- barrido
    def ejecutar_scan_ventana(self, w: dict, scan_cfg: dict, historial: dict | None = None) -> dict:
        """Scan de TODAS las (segmento × estrategia) en una ventana con scorecard.

        Versión ligera para el grid de búsqueda del harness de aceptación
        (`--aceptacion`): un solo estudio + impacto por ventana, bootstrap
        grueso (n_boot bajo) y sin holdout (V3 se confirma luego en las
        candidatas con el flujo completo). Devuelve por combinación las
        métricas de los gates N1 (cheap) / N2 / N4 (fidelidad del clon).
        `historial` pre-calculado evita releer el histórico por ventana.
        """
        a_cfg = self.cfg["asistente"]
        params = self.cfg["modelo_financiero"]
        clip = self.cfg["diario"].get("clip_margen_cop_kwh")
        bins = a_cfg["bins_spread"]
        usar_previo = bool(a_cfg.get("usar_spread_previo", True))
        factor_expo = float(a_cfg.get("factor_exposicion_fuera_distribucion", 0.5))
        relativo = bool(a_cfg.get("seleccion_por_relativo", True))
        semilla = int(self.cfg["diario"].get("random_state", 42))
        umbral_corr = float(a_cfg.get("umbral_corr_duplicados", 0.9))
        umbral_kill = float(a_cfg.get("kill_switch_drawdown_cop_kwh", 500.0))
        n_boot = int(scan_cfg.get("n_boot_scan", 200))
        top = int(scan_cfg.get("top", a_cfg["top_por_defecto"]))
        min_dias = float(scan_cfg.get("min_dias_pct", a_cfg["min_dias_pct"]))

        datos = self._correr_estudio(w["estudio_ini"], w["estudio_fin"])
        d = datos["diario"]
        if d["n_agentes"] == 0:
            return {"ventana": w, "combinaciones": [], "error": "sin agentes"}
        seg_cod = {c: a.segmento.value for c, a in datos["f-1"]["por_codigo"].items()}

        rows_imp = self.repo.diario(w["impacto_ini"], _iso(_parse(w["impacto_fin"]) + timedelta(days=1)))
        if not rows_imp:
            return {"ventana": w, "combinaciones": [], "error": "sin datos impacto"}
        ad_imp = diario.construir_agente_dia(rows_imp)
        for ad in ad_imp.values():
            ad["features"] = diario.features_diarias(ad)
            ad["desempeno"] = diario.desempeno_diario(ad, params)
        diario.aplicar_clip_margen(ad_imp, clip)

        nivel_sel: dict[str, float] = {}
        nivel_imp: dict[str, float] = {}
        if bool(a_cfg.get("usar_regimen_hidrologico", True)):
            nivel_sel = {str(r["fecha"])[:10]: float(r["nivel_agregado_pct"])
                         for r in self.repo.contexto_hidrologia(w["estudio_ini"], _iso(_parse(w["estudio_fin"]) + timedelta(days=1)))}
            nivel_imp = {str(r["fecha"])[:10]: float(r["nivel_agregado_pct"])
                         for r in self.repo.contexto_hidrologia(w["impacto_ini"], _iso(_parse(w["impacto_fin"]) + timedelta(days=1)))}

        hist = historial if historial is not None else contexto.historial_escasez(self.repo.historial_precios(), bins)

        combinaciones: list[dict] = []
        for seg in sorted({a.segmento for a in d["agentes"]}):
            dema = contexto.demanda_referencia(d["agentedia"], seg_cod, seg)
            if dema <= 0:
                continue
            for est in sorted({pf.arquetipo for pf in d["perfiles"].values()}):
                ms = maestros.seleccionar_maestros(
                    d["agentes"], seg, est, top, d["n_dias"], min_dias, relativo=relativo
                )
                if not ms:
                    continue
                codigos = {m.codigo for m in ms}
                politica = clonacion.construir_politica(
                    d["agentedia"], d["etiquetas"], d["labels"], d["perfiles"],
                    codigos, seg, est, seg_cod, bins,
                )
                sims_is = simulacion.simular_dias(
                    d["agentedia"], politica, dema, params, seg_cod, seg, codigos, bins,
                    usar_spread_previo=usar_previo, factor_exposicion_fuera=factor_expo,
                    nivel_embalses_por_dia=nivel_sel,
                )
                sims = simulacion.simular_dias(
                    ad_imp, politica, dema, params, seg_cod, seg, codigos, bins,
                    usar_spread_previo=usar_previo, factor_exposicion_fuera=factor_expo,
                    nivel_embalses_por_dia=nivel_imp,
                )
                res = simulacion.resumen_impacto(sims, dema)
                rep = simulacion.replicacion_is_oos(sims_is, sims)
                boot = maestros.bootstrap_skill_luck(
                    d["agentes"], seg, est, top, d["n_dias"],
                    n_boot=n_boot, semilla=semilla, min_dias_pct=min_dias, relativo=relativo,
                )
                neff = maestros.n_efectivo(ms, d["agentes"], umbral_corr)
                dist = simulacion.distribucion([s.margen_imitacion for s in sims])
                n_trials = boot["n_agentes_candidatos"] if boot else top
                dsr = simulacion.dsr_aprox([s.margen_imitacion for s in sims], n_trials=n_trials)
                esc = simulacion.escenario_escasez(dema, politica, list(d["agentedia"].values()), params)
                margen_esc = next((e.margen_cop_kwh for e in esc if e.nombre == "escasez_umbral"), None)
                decision = simulacion.decision_negocio(
                    dema_kwh=dema, mediana_benigna=res.mediana_imitacion,
                    margen_escasez=float(margen_esc) if margen_esc is not None else 0.0,
                    margen_escasez_extrema=0.0,
                    pct_escasez=hist["pct_dias_escasez"], pct_escasez_nino=25.0,
                    drawdown_max=dist.drawdown_max, kill_switch_drawdown=umbral_kill,
                )
                cap = simulacion.capacidad(
                    dema, d["agentedia"], seg, seg_cod,
                    float(a_cfg.get("capacidad_max_pct_segmento", 5.0)),
                )
                f1 = scorecard.fidelidad_mae(ad_imp, politica, codigos, seg_cod, seg, usar_previo)
                combinaciones.append({
                    "segmento": seg, "estrategia": est,
                    "n_maestros": len(ms), "n_efectivo": neff,
                    "codigos": [m.codigo for m in ms],
                    "mediana_relativa_top": round(median([m.mediana_relativa for m in ms]), 2),
                    "mediana_margen_absoluto": res.mediana_imitacion,
                    "p_valor": boot["p_valor"] if boot else 1.0,
                    "ratio_replicacion": rep.get("ratio_replicacion"),
                    "dsr": dsr["dsr"] if dsr else None,
                    "persistencia": None,
                    "pct_gana_segmento": res.pct_dias_gana_segmento,
                    "kill_switch": bool(dist.drawdown_max > umbral_kill),
                    "drawdown_max": dist.drawdown_max,
                    "ev_historico": decision["e_margen_dia_historico"],
                    "ev_anio_nino": decision["e_margen_dia_anio_nino"],
                    "supera_capacidad": bool(cap["supera_capacidad"]) if cap else False,
                    "capacidad_pct": cap["pct_del_segmento"] if cap else None,
                    "mae_f1": f1["promedio"],
                    "mae_f1_detalle": f1,
                })
        combinaciones.sort(key=lambda c: (c["p_valor"], -c["mediana_relativa_top"]))
        return {"ventana": w, "combinaciones": combinaciones, "error": None}

    def ejecutar_scan_ventana_arquetipo(self, w: dict, scan_cfg: dict, historial: dict | None = None) -> dict:
        """Ruta A: scan de arquetipo ganador por régimen en una ventana.

        Por segmento construye la política 'arquetipo' (mezcla arquetipos por
        bin de spread), valida con bootstrap a nivel de arquetipo y mide la
        imitación en el impacto. Devuelve una fila por segmento.
        """
        a_cfg = self.cfg["asistente"]
        params = self.cfg["modelo_financiero"]
        clip = self.cfg["diario"].get("clip_margen_cop_kwh")
        bins = a_cfg["bins_spread"]
        usar_previo = bool(a_cfg.get("usar_spread_previo", True))
        factor_expo = float(a_cfg.get("factor_exposicion_fuera_distribucion", 0.5))
        relativo = bool(a_cfg.get("seleccion_por_relativo", True))
        semilla = int(self.cfg["diario"].get("random_state", 42))
        umbral_kill = float(a_cfg.get("kill_switch_drawdown_cop_kwh", 500.0))
        n_boot = int(scan_cfg.get("n_boot_scan", 200))
        min_dias = float(scan_cfg.get("min_dias_pct", a_cfg["min_dias_pct"]))

        datos = self._correr_estudio(w["estudio_ini"], w["estudio_fin"])
        d = datos["diario"]
        if d["n_agentes"] == 0:
            return {"ventana": w, "combinaciones": [], "error": "sin agentes"}
        seg_cod = {c: a.segmento.value for c, a in datos["f-1"]["por_codigo"].items()}

        rows_imp = self.repo.diario(w["impacto_ini"], _iso(_parse(w["impacto_fin"]) + timedelta(days=1)))
        if not rows_imp:
            return {"ventana": w, "combinaciones": [], "error": "sin datos impacto"}
        ad_imp = diario.construir_agente_dia(rows_imp)
        for ad in ad_imp.values():
            ad["features"] = diario.features_diarias(ad)
            ad["desempeno"] = diario.desempeno_diario(ad, params)
        diario.aplicar_clip_margen(ad_imp, clip)

        nivel_sel: dict[str, float] = {}
        nivel_imp: dict[str, float] = {}
        if bool(a_cfg.get("usar_regimen_hidrologico", True)):
            nivel_sel = {str(r["fecha"])[:10]: float(r["nivel_agregado_pct"])
                         for r in self.repo.contexto_hidrologia(w["estudio_ini"], _iso(_parse(w["estudio_fin"]) + timedelta(days=1)))}
            nivel_imp = {str(r["fecha"])[:10]: float(r["nivel_agregado_pct"])
                         for r in self.repo.contexto_hidrologia(w["impacto_ini"], _iso(_parse(w["impacto_fin"]) + timedelta(days=1)))}

        hist = historial if historial is not None else contexto.historial_escasez(self.repo.historial_precios(), bins)

        combinaciones: list[dict] = []
        for seg in sorted({a.segmento for a in d["agentes"]}):
            dema = contexto.demanda_referencia(d["agentedia"], seg_cod, seg)
            if dema <= 0:
                continue
            politica = clonacion.construir_politica(
                d["agentedia"], d["etiquetas"], d["labels"], d["perfiles"],
                set(), seg, "", seg_cod, bins, modo="arquetipo",
            )
            if not politica.reglas and not politica.fallback:
                continue
            boot = maestros.bootstrap_skill_luck(
                d["agentes"], seg, "", 1, d["n_dias"],
                n_boot=n_boot, semilla=semilla, min_dias_pct=min_dias, relativo=relativo, nivel="arquetipo",
            )
            sims_is = simulacion.simular_dias(
                d["agentedia"], politica, dema, params, seg_cod, seg, set(), bins,
                usar_spread_previo=usar_previo, factor_exposicion_fuera=factor_expo,
                nivel_embalses_por_dia=nivel_sel,
            )
            sims = simulacion.simular_dias(
                ad_imp, politica, dema, params, seg_cod, seg, set(), bins,
                usar_spread_previo=usar_previo, factor_exposicion_fuera=factor_expo,
                nivel_embalses_por_dia=nivel_imp,
            )
            res = simulacion.resumen_impacto(sims, dema)
            rep = simulacion.replicacion_is_oos(sims_is, sims)
            dist = simulacion.distribucion([s.margen_imitacion for s in sims])
            n_trials = boot["n_arquetipos"] if boot else 1
            dsr = simulacion.dsr_aprox([s.margen_imitacion for s in sims], n_trials=n_trials)
            esc = simulacion.escenario_escasez(dema, politica, list(d["agentedia"].values()), params)
            margen_esc = next((e.margen_cop_kwh for e in esc if e.nombre == "escasez_umbral"), None)
            decision = simulacion.decision_negocio(
                dema_kwh=dema, mediana_benigna=res.mediana_imitacion,
                margen_escasez=float(margen_esc) if margen_esc is not None else 0.0,
                margen_escasez_extrema=0.0,
                pct_escasez=hist["pct_dias_escasez"], pct_escasez_nino=25.0,
                drawdown_max=dist.drawdown_max, kill_switch_drawdown=umbral_kill,
            )
            cap = simulacion.capacidad(
                dema, d["agentedia"], seg, seg_cod,
                float(a_cfg.get("capacidad_max_pct_segmento", 5.0)),
            )
            f1 = scorecard.fidelidad_mae(ad_imp, politica, set(), seg_cod, seg, usar_previo)
            combinaciones.append({
                "segmento": seg,
                "estrategia": boot["mejor_arquetipo"] if boot else "arquetipo",
                "modo_arquetipo": True,
                "n_maestros": boot["n_arquetipos"] if boot else 0,
                "n_efectivo": boot["n_arquetipos"] if boot else 0,
                "codigos": sorted((politica.ganadores_arquetipo or {}).values()),
                "mediana_relativa_top": 0.0,
                "mediana_margen_absoluto": res.mediana_imitacion,
                "p_valor": boot["p_valor"] if boot else 1.0,
                "ratio_replicacion": rep.get("ratio_replicacion"),
                "dsr": dsr["dsr"] if dsr else None,
                "persistencia": None,
                "pct_gana_segmento": res.pct_dias_gana_segmento,
                "kill_switch": bool(dist.drawdown_max > umbral_kill),
                "drawdown_max": dist.drawdown_max,
                "ev_historico": decision["e_margen_dia_historico"],
                "ev_anio_nino": decision["e_margen_dia_anio_nino"],
                "supera_capacidad": bool(cap["supera_capacidad"]) if cap else False,
                "capacidad_pct": cap["pct_del_segmento"] if cap else None,
                "mae_f1": f1["promedio"],
                "mae_f1_detalle": f1,
                "ganadores_arquetipo": politica.ganadores_arquetipo,
            })
        combinaciones.sort(key=lambda c: (c["p_valor"], -c["mediana_margen_absoluto"]))
        return {"ventana": w, "combinaciones": combinaciones, "error": None}

    # ---------------------------------------------------------------- barrido
    def ejecutar_barrido(self, p: ParametrosAsistente, b_cfg: dict) -> dict:
        """S2: evalúa TODAS las (segmento × estrategia) y reporta las validas.

        Reusa el estudio del motor (una sola corrida F-1 + FaseDiaria) y, por
        cada combinación presente: selecciona maestros (margen relativo),
        construye la política, simula estudio e impacto, y le aplica el filtro
        de validez (bootstrap p-valor, replicación IS→OOS, N efectivo). Devuelve
        las combinaciones ordenadas (validas primero) para `--barrido`.
        """
        a_cfg = self.cfg["asistente"]
        params = self.cfg["modelo_financiero"]
        clip = self.cfg["diario"].get("clip_margen_cop_kwh")

        w = self._resolver_fechas(p)
        max_sistema = _parse(self.repo.fecha_max_sistema())
        self._validar_fechas(w, max_sistema)

        datos = self._correr_estudio(w.estudio_ini, w.estudio_fin)
        d = datos["diario"]
        if d["n_agentes"] == 0:
            raise ValueError(
                f"No hay comercializadores con demanda en la ventana de estudio {w.estudio_ini}..{w.estudio_fin}."
            )
        segmento_por_codigo = {c: a.segmento.value for c, a in datos["f-1"]["por_codigo"].items()}

        rows_impacto = self.repo.diario(w.impacto_ini, _iso(_parse(w.impacto_fin) + timedelta(days=1)))
        if not rows_impacto:
            raise ValueError(
                f"No hay datos de mercado para la ventana de impacto {w.impacto_ini}..{w.impacto_fin} "
                f"(última fecha con datos: {max_sistema.isoformat()})."
            )
        agentedia_impacto = diario.construir_agente_dia(rows_impacto)
        for ad in agentedia_impacto.values():
            ad["desempeno"] = diario.desempeno_diario(ad, params)
        diario.aplicar_clip_margen(agentedia_impacto, clip)

        usar_hidro = bool(a_cfg.get("usar_regimen_hidrologico", True))
        nivel_por_dia_imp: dict[str, float] = {}
        if usar_hidro:
            nivel_por_dia_imp = {
                str(r["fecha"])[:10]: float(r["nivel_agregado_pct"])
                for r in self.repo.contexto_hidrologia(
                    w.impacto_ini, _iso(_parse(w.impacto_fin) + timedelta(days=1))
                )
            }

        usar_previo = bool(a_cfg.get("usar_spread_previo", True))
        factor_expo = float(a_cfg.get("factor_exposicion_fuera_distribucion", 0.5))
        relativo = bool(a_cfg.get("seleccion_por_relativo", True))
        n_boot = int(b_cfg.get("n_boot_rapido", 200))
        min_p = float(b_cfg.get("min_p_valor", 0.05))
        min_rep = float(b_cfg.get("min_replicacion", 0.5))
        min_nef = int(b_cfg.get("min_n_efectivo", 3))
        semilla = int(self.cfg["diario"].get("random_state", 42))
        umbral_corr = float(a_cfg.get("umbral_corr_duplicados", 0.9))
        umbral_kill = float(a_cfg.get("kill_switch_drawdown_cop_kwh", 500.0))

        segmentos = sorted({a.segmento for a in d["agentes"]})
        estrategias = sorted({pf.arquetipo for pf in d["perfiles"].values()})
        filas: list[dict] = []
        for seg in segmentos:
            dema_seg = contexto.demanda_referencia(d["agentedia"], segmento_por_codigo, seg)
            if dema_seg <= 0:
                continue
            for est in estrategias:
                ms = maestros.seleccionar_maestros(
                    d["agentes"], seg, est, p.top, d["n_dias"], p.min_dias_pct, relativo=relativo
                )
                if not ms:
                    continue
                codigos = {m.codigo for m in ms}
                politica = clonacion.construir_politica(
                    d["agentedia"], d["etiquetas"], d["labels"], d["perfiles"],
                    codigos, seg, est, segmento_por_codigo, a_cfg["bins_spread"],
                )
                sims_is = simulacion.simular_dias(
                    d["agentedia"], politica, dema_seg, params, segmento_por_codigo, seg,
                    codigos, a_cfg["bins_spread"],
                    usar_spread_previo=usar_previo, factor_exposicion_fuera=factor_expo,
                )
                sims = simulacion.simular_dias(
                    agentedia_impacto, politica, dema_seg, params, segmento_por_codigo, seg,
                    codigos, a_cfg["bins_spread"],
                    usar_spread_previo=usar_previo, factor_exposicion_fuera=factor_expo,
                    nivel_embalses_por_dia=nivel_por_dia_imp,
                )
                res = simulacion.resumen_impacto(sims, dema_seg)
                rep = simulacion.replicacion_is_oos(sims_is, sims)
                boot = maestros.bootstrap_skill_luck(
                    d["agentes"], seg, est, p.top, d["n_dias"],
                    n_boot=n_boot, semilla=semilla, min_dias_pct=p.min_dias_pct, relativo=relativo,
                )
                neff = maestros.n_efectivo(ms, d["agentes"], umbral_corr)
                dist = simulacion.distribucion([s.margen_imitacion for s in sims])
                p_valor = boot["p_valor"] if boot else 1.0
                ratio = rep.get("ratio_replicacion")
                valida = bool(
                    boot is not None and p_valor <= min_p
                    and ratio is not None and ratio >= min_rep
                    and neff >= min_nef
                )
                filas.append({
                    "segmento": seg,
                    "estrategia": est,
                    "n_maestros": len(ms),
                    "n_efectivo": neff,
                    "codigos": [m.codigo for m in ms],
                    "mediana_relativa_top": round(median([m.mediana_relativa for m in ms]), 2),
                    "mediana_margen_absoluto": res.mediana_imitacion,
                    "p_valor": p_valor,
                    "ratio_replicacion": ratio,
                    "drawdown_max": dist.drawdown_max,
                    "kill_switch": dist.drawdown_max > umbral_kill,
                    "valida": valida,
                })

        filas.sort(key=lambda r: (r["valida"], r["mediana_relativa_top"]), reverse=True)
        filas = filas[: int(b_cfg.get("max_combinaciones", 20))]
        return {
            "combinaciones": filas,
            "ventanas": {
                "estudio": {"ini": w.estudio_ini, "fin": w.estudio_fin},
                "impacto": {"ini": w.impacto_ini, "fin": w.impacto_fin},
            },
            "filtros": {"min_p_valor": min_p, "min_replicacion": min_rep, "min_n_efectivo": min_nef},
        }