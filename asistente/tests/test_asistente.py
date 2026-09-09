"""Pruebas unitarias del asistente imitador (lógica pura, sin BD)."""
from __future__ import annotations

from datetime import date

import numpy as np

from sfeia.app.models.entities import AgenteDia, PerfilEstrategia
from sfeia.app.services import diario

from asistente.app.models.entities import (
    PerfilAccion,
    PoliticaClonacion,
    ReglaPolitica,
    SimulacionDia,
)
from asistente.app.services import clonacion, contexto, maestros, simulacion

PARAMS = {
    "pv_tarifa_cop_kwh": 350.0,
    "cargo_regulado_cop_kwh": 76.1,
    "factor_cobertura": 0.25,
    "tasa_costo_anual": 0.02,
    "incobrables_pct": 0.02,
    "impuesto_pct": 0.33,
}

BINS = {
    "muy_barata": [-999999, 0],
    "barata": [0, 200],
    "neutral": [200, 400],
    "cara": [400, 999999],
}

ESTRATEGIA = "Trader expuesto a bolsa (sin cobertura)"


def _filas_toy() -> list[dict]:
    filas = []
    for dia in (date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)):
        filas.append({
            "agente": "EXP", "dia": dia,
            "dema_kwh": 100_000.0, "dema_reg_kwh": 0.0, "dema_noreg_kwh": 100_000.0,
            "comp_cont_kwh": 0.0, "comp_cont_reg_kwh": 0.0,
            "vent_cont_kwh": 0.0, "comp_bolsa_kwh": 100_000.0, "vent_bolsa_kwh": 0.0,
            "comp_sicep_kwh": 0.0,
            "prec_cont_cop_kwh": 300.0, "prec_bolsa_cop_kwh": 350.0, "prec_escasez_cop_kwh": 400.0,
        })
    return filas


def _agentedia_toy() -> dict[str, dict]:
    agentedia = diario.construir_agente_dia(_filas_toy())
    for ad in agentedia.values():
        ad["features"] = diario.features_diarias(ad)
        ad["desempeno"] = diario.desempeno_diario(ad, PARAMS)
    return agentedia


def test_binificar_spread():
    assert contexto.binificar_spread(-10.0, BINS)[0] == "muy_barata"
    assert contexto.binificar_spread(0.0, BINS)[0] == "barata"
    assert contexto.binificar_spread(199.0, BINS)[0] == "barata"
    assert contexto.binificar_spread(250.0, BINS)[0] == "neutral"
    assert contexto.binificar_spread(500.0, BINS)[0] == "cara"
    assert contexto.binificar_spread(999_999.0, BINS)[0] == "cara"
    # fuera de rango -> bin extremo más cercano (nunca se queda sin bin)
    assert contexto.binificar_spread(-10_000_000.0, BINS)[0] == "muy_barata"
    assert contexto.binificar_spread(10_000_000.0, BINS)[0] == "cara"


def test_es_escasez():
    assert contexto.es_escasez(500.0, 400.0) is True
    assert contexto.es_escasez(300.0, 400.0) is False


def test_demanda_referencia():
    agentedia = _agentedia_toy()
    seg = {"EXP": "PEQUEÑO"}
    assert contexto.demanda_referencia(agentedia, seg, "PEQUEÑO") == 100_000.0
    assert contexto.demanda_referencia(agentedia, seg, "GRANDE") == 0.0


def test_seleccionar_maestros():
    agentes = []
    for i, dia in enumerate(("2026-01-01", "2026-01-02", "2026-01-03")):
        agentes.append(AgenteDia(
            codigo="EXP", nombre="EXP S.A.", dia=dia, segmento="PEQUEÑO",
            cluster_id=0, arquetipo=ESTRATEGIA, features={}, margen_kwh=10.0 + i, costo_kwh=300.0,
        ))
    for dia in ("2026-01-01", "2026-01-02"):
        agentes.append(AgenteDia(
            codigo="OTRO", nombre="OTRO", dia=dia, segmento="PEQUEÑO",
            cluster_id=0, arquetipo=ESTRATEGIA, features={}, margen_kwh=5.0, costo_kwh=300.0,
        ))
    top = maestros.seleccionar_maestros(agentes, "PEQUEÑO", ESTRATEGIA, top=1, n_dias_estudio=3, min_dias_pct=50)
    assert [m.codigo for m in top] == ["EXP"]
    assert top[0].mediana_margen == 11.0
    # con presencia mínima alta, OTRO (2/3 días < 50% + redondeo) queda fuera
    top2 = maestros.seleccionar_maestros(agentes, "PEQUEÑO", ESTRATEGIA, top=5, n_dias_estudio=3, min_dias_pct=100)
    assert [m.codigo for m in top2] == ["EXP"]
    # segmento/estrategia distintos no califican
    assert maestros.seleccionar_maestros(agentes, "GRANDE", ESTRATEGIA, top=5, n_dias_estudio=3, min_dias_pct=0) == []


def test_construir_politica_y_aplicar():
    agentedia = _agentedia_toy()
    etiquetas = sorted(agentedia)
    labels = np.array([0 if agentedia[k]["codigo"] == "EXP" else 1 for k in etiquetas])
    perfiles = {
        0: PerfilEstrategia(cluster_id=0, arquetipo=ESTRATEGIA, n=3, n_agentes=1,
                            medias={}, composicion_segmento={"PEQUEÑO": 3}),
        1: PerfilEstrategia(cluster_id=1, arquetipo="Comercializador regulado", n=3, n_agentes=1,
                            medias={}, composicion_segmento={"GRANDE": 3}),
    }
    seg = {"EXP": "PEQUEÑO"}
    politica = clonacion.construir_politica(
        agentedia, etiquetas, labels, perfiles, {"EXP"}, "PEQUEÑO", ESTRATEGIA, seg, BINS
    )
    assert set(politica.reglas) == {"barata"}
    regla = politica.reglas["barata"]
    assert regla.n_dias == 3
    assert regla.perfil.pct_exposicion == 100.0
    assert regla.perfil.pct_cobertura == 0.0
    assert politica.fallback is not None
    assert politica.fallback.pct_exposicion == 100.0

    perfil = clonacion.aplicar_politica(politica, 50.0)
    assert perfil.pct_exposicion == 100.0
    # spread fuera de los bins con datos -> bin más cercano con datos
    perfil2 = clonacion.aplicar_politica(politica, 10_000_000.0)
    assert perfil2.pct_exposicion == 100.0


def test_aplicar_politica_fallback_vacio():
    politica = PoliticaClonacion(
        reglas={},
        fallback=PerfilAccion(pct_cobertura=50.0, pct_exposicion=50.0, pct_noreg=0.0, pct_sicep=0.0, tiene_sicep=1.0),
        bins_spread=BINS,
    )
    perfil = clonacion.aplicar_politica(politica, 123.0)
    assert perfil.pct_cobertura == 50.0 and perfil.pct_exposicion == 50.0


def test_aplicar_politica_sin_nada_levanta():
    import pytest

    politica = PoliticaClonacion(reglas={}, fallback=None, bins_spread=BINS)
    with pytest.raises(ValueError):
        clonacion.aplicar_politica(politica, 50.0)


def test_aplicar_politica_bin_mas_cercano():
    politica = PoliticaClonacion(
        reglas={
            "muy_barata": ReglaPolitica("muy_barata", -999999, 0, PerfilAccion(0.0, 100.0, 90.0, 0.0, 0.0, 2), 2),
            "cara": ReglaPolitica("cara", 400, 999999, PerfilAccion(120.0, 10.0, 5.0, 80.0, 1.0, 2), 2),
        },
        fallback=None,
        bins_spread=BINS,
    )
    # spread neutro (sin regla) -> el bin más cercano es el de 0-200? no: distancia a [400, inf) = 200,
    # distancia a (-inf,0) = 250 -> elige "cara"
    perfil = clonacion.aplicar_politica(politica, 200.0)
    assert perfil.pct_cobertura == 120.0


def test_construir_ad_xxxc_y_margen():
    perfil = PerfilAccion(pct_cobertura=80.0, pct_exposicion=20.0, pct_noreg=10.0, pct_sicep=50.0, tiene_sicep=1.0)
    ad = simulacion.construir_ad_xxxc(1_000_000.0, perfil, 300.0, 350.0, 400.0)
    assert ad["comp_cont_kwh"] == 800_000.0
    assert ad["comp_bolsa_kwh"] == 200_000.0
    assert ad["dema_reg_kwh"] == 900_000.0
    assert ad["comp_cont_reg_kwh"] == 720_000.0
    assert ad["comp_sicep_kwh"] == 360_000.0
    d = diario.desempeno_diario(ad, PARAMS)
    assert isinstance(d["margen_por_kwh_cop"], float)


def test_mediana_margen_dia():
    agentedia = _agentedia_toy()
    for ad in agentedia.values():
        ad["desempeno"] = diario.desempeno_diario(ad, PARAMS)
    dia = "2026-01-01"
    seg = {"EXP": "PEQUEÑO"}
    m = simulacion.mediana_margen_dia(agentedia, dia, codigos={"EXP"}, segmento="PEQUEÑO", segmento_por_codigo=seg)
    assert m == agentedia[diario.clave("EXP", date(2026, 1, 1))]["desempeno"]["margen_por_kwh_cop"]
    assert simulacion.mediana_margen_dia(agentedia, dia, codigos={"NO_EXISTE"}) is None


def test_resumen_impacto():
    sims = [
        SimulacionDia("2026-07-01", "barata", False, PerfilAccion(0.0, 100.0, 100.0, 0.0, 0.0), 10.0, 8.0, 6.0),
        SimulacionDia("2026-07-02", "barata", False, PerfilAccion(0.0, 100.0, 100.0, 0.0, 0.0), 12.0, 9.0, 7.0),
    ]
    r = simulacion.resumen_impacto(sims, demanda_kwh_dia=100_000.0)
    assert r.dias == 2
    assert r.mediana_imitacion == 11.0
    assert r.mediana_maestros == 8.5
    assert r.pct_dias_gana_segmento == 100.0
    assert r.pct_dias_gana_maestros == 100.0