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

SOLID: es el único componente que habla con el repo y los controladores del
estudio; los services son lógica pura inyectada con datos y parámetros.
"""
from __future__ import annotations

import copy
from datetime import date, timedelta

from sfeia.app.controllers.fase_diaria import FaseDiaria
from sfeia.app.controllers.fase_segmentacion import FaseSegmentacion
from sfeia.app.services import diario

from asistente.app.models.entities import (
    ParametrosAsistente,
    PerfilAccion,
    SimulacionDia,
    VentanasResueltas,
)
from asistente.app.services import clonacion, contexto, maestros, simulacion


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
        foco_fin = _parse(v["foco_fin"])

        estudio_ini = _parse(p.estudio_ini) if p.estudio_ini else _parse(v["foco_ini"])
        estudio_fin = _parse(p.estudio_fin) if p.estudio_fin else foco_fin - timedelta(days=n_impacto)
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

        # ---- 1. ventana de estudio: F-1 + FaseDiaria (config sobreescrita) ----
        cfg_estudio = copy.deepcopy(self.cfg)
        cv = cfg_estudio["ventana"]
        cv["foco_ini"] = w.estudio_ini
        cv["foco_fin"] = w.estudio_fin
        cv["fin_c_familia"] = _iso(_parse(w.estudio_fin) + timedelta(days=1))
        cv["fin_c15"] = w.estudio_fin

        datos: dict = {}
        FaseSegmentacion(self.repo, cfg_estudio).ejecutar(datos)
        FaseDiaria(self.repo, cfg_estudio).ejecutar(datos)

        d = datos["diario"]
        if d["n_agentes"] == 0:
            raise ValueError(
                f"No hay comercializadores con demanda en la ventana de estudio {w.estudio_ini}..{w.estudio_fin}."
            )
        segmento_por_codigo = {c: a.segmento.value for c, a in datos["f-1"]["por_codigo"].items()}

        # ---- 2. maestros (top-N del segmento+estrategia) ----
        maestros_lista = maestros.seleccionar_maestros(
            d["agentes"], segmento, estrategia, top, d["n_dias"], p.min_dias_pct
        )
        if not maestros_lista:
            disponibles = sorted({perf.arquetipo for perf in d["perfiles"].values()})
            raise ValueError(
                f"No hay agentes del segmento **{segmento}** jugando la estrategia **{estrategia}** en la "
                f"ventana de estudio {w.estudio_ini}..{w.estudio_fin}. Estrategias presentes: "
                + ", ".join(disponibles)
                + ". Ajusta el segmento, la estrategia o la ventana de estudio."
            )
        codigos_maestros = {m.codigo for m in maestros_lista}

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

        sims: list[SimulacionDia] = []
        vistos: set[str] = set()
        for ad in agentedia_impacto.values():
            dia = str(ad["dia"])
            if dia in vistos:
                continue
            vistos.add(dia)
            spread = ad["prec_bolsa"] - ad["prec_cont"]
            perfil = clonacion.aplicar_politica(politica, spread)
            ad_xxxc = simulacion.construir_ad_xxxc(
                dema_kwh, perfil, ad["prec_cont"], ad["prec_bolsa"], ad["prec_escasez"]
            )
            margen_im = diario.desempeno_diario(ad_xxxc, params)["margen_por_kwh_cop"]
            bin_label, _, _ = contexto.binificar_spread(spread, a_cfg["bins_spread"])
            sims.append(SimulacionDia(
                fecha=dia,
                bin_spread=bin_label,
                es_escasez=contexto.es_escasez(ad["prec_bolsa"], ad["prec_escasez"]),
                perfil=perfil,
                margen_imitacion=round(margen_im, 2),
                margen_maestros=simulacion.mediana_margen_dia(
                    agentedia_impacto, dia, codigos=codigos_maestros
                ),
                margen_segmento=simulacion.mediana_margen_dia(
                    agentedia_impacto, dia, segmento=segmento, segmento_por_codigo=segmento_por_codigo
                ),
            ))
        sims.sort(key=lambda s: s.fecha)
        resumen = simulacion.resumen_impacto(sims, dema_kwh)

        advertencias = [
            "El margen es un artefacto de modelado (Pv=350 COP/kWh fijo, precios de sistema): sirve para "
            "comparar estrategias, no como margen real del negocio.",
            "Behavioral Cloning no generaliza fuera de la distribución de spread del estudio; los bins sin "
            "entrenamiento se resuelven con el bin más cercano o el fallback.",
            "La ventana de impacto usa datos ya cargados en elecdb; es retrospectiva, no predicción en vivo.",
            "Los maestros se eligen dentro de su segmento: el asistente no compite contra GRANDE por diseño.",
        ]
        if len(maestros_lista) < top:
            advertencias.append(
                f"Solo se encontraron {len(maestros_lista)} agentes en el (segmento, estrategia) de la ventana "
                f"de estudio; el top pedido era {top}."
            )

        resultado = {
            "parametros": {
                "segmento": segmento,
                "estrategia": estrategia,
                "top": top,
                "demanda_dia_gwh": round(dema_kwh / 1e6, 4),
                "min_dias_pct": p.min_dias_pct,
                "ventanas": {
                    "estudio": {"ini": w.estudio_ini, "fin": w.estudio_fin},
                    "impacto": {"ini": w.impacto_ini, "fin": w.impacto_fin},
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
            "resumen": resumen,
            "advertencias": advertencias,
        }
        return resultado