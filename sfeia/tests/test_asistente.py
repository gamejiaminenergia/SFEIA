"""Pruebas unitarias del asistente imitador (lógica pura, sin BD)."""
from __future__ import annotations

from datetime import date

import numpy as np

from sfeia.app.models.entities import AgenteDia, PerfilEstrategia
from sfeia.app.services import diario

from sfeia.app.models.entities import (
    PerfilAccion,
    PoliticaClonacion,
    ReglaPolitica,
    SimulacionDia,
)
from sfeia.app.services import clonacion, contexto, maestros, simulacion

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
        SimulacionDia("2026-07-01", "barata", False, PerfilAccion(0.0, 100.0, 100.0, 0.0, 0.0), 10.0, 8.0, 6.0, 1_000.0),
        SimulacionDia("2026-07-02", "barata", False, PerfilAccion(0.0, 100.0, 100.0, 0.0, 0.0), 12.0, 9.0, 7.0, 1_500.0),
    ]
    r = simulacion.resumen_impacto(sims, demanda_kwh_dia=100_000.0)
    assert r.dias == 2
    assert r.mediana_imitacion == 11.0
    assert r.mediana_maestros == 8.5
    assert r.pct_dias_gana_segmento == 100.0
    assert r.pct_dias_gana_maestros == 100.0
    assert r.garantia_mediana_cop == 1_250.0
    assert r.garantia_max_cop == 1_500.0


def test_distribucion():
    m = simulacion.distribucion([-10.0, -5.0, 5.0, 10.0, 20.0])
    assert m.n == 5
    assert m.mediana == 5.0
    assert m.pct_dias_perdida == 40.0
    assert m.peor_dia == -10.0
    assert m.mejor_dia == 20.0
    # drawdown de la serie acumulada: -10,-15,-10,0,20 -> caída pico-valle = 15
    assert m.drawdown_max == 15.0


def test_distribucion_vacia():
    m = simulacion.distribucion([])
    assert m.n == 0 and m.mediana == 0.0


def test_escenario_escasez():
    agentedia = _agentedia_toy()
    etiquetas = sorted(agentedia)
    labels = np.array([0 if agentedia[k]["codigo"] == "EXP" else 1 for k in etiquetas])
    perfiles = {
        0: PerfilEstrategia(cluster_id=0, arquetipo=ESTRATEGIA, n=3, n_agentes=1,
                            medias={}, composicion_segmento={"PEQUEÑO": 3}),
    }
    politica = clonacion.construir_politica(
        agentedia, etiquetas, labels, perfiles, {"EXP"}, "PEQUEÑO", ESTRATEGIA, {"EXP": "PEQUEÑO"}, BINS
    )
    dias = [ad for ad in agentedia.values()]
    esc = simulacion.escenario_escasez(100_000.0, politica, dias, PARAMS)
    assert len(esc) == 2
    assert esc[0].nombre == "escasez_umbral"
    assert esc[1].nombre == "escasez_extrema"
    assert esc[1].spread > esc[0].spread
    assert all(e.garantia_cop >= 0 for e in esc)


def test_sensibilidad_maestros():
    agentes = []
    for dia in ("2026-01-01", "2026-01-02", "2026-01-03"):
        agentes.append(AgenteDia(
            codigo="EXP", nombre="EXP S.A.", dia=dia, segmento="PEQUEÑO",
            cluster_id=0, arquetipo=ESTRATEGIA, features={}, margen_kwh=10.0, costo_kwh=300.0,
        ))
    sens = maestros.sensibilidad(agentes, "PEQUEÑO", ESTRATEGIA, n_dias_estudio=3,
                                 tops=(1, 3), min_dias_pcts=(0.0, 50.0))
    assert sens[(1, 0.0)] == ["EXP"]
    assert sens[(3, 50.0)] == ["EXP"]


def test_historial_escasez():
    from datetime import date

    dias = [
        {"fecha": date(2025, 1, 1), "prec_bolsa": 300.0, "prec_cont": 330.0, "prec_escasez": 800.0},  # spread -30
        {"fecha": date(2025, 1, 2), "prec_bolsa": 500.0, "prec_cont": 330.0, "prec_escasez": 800.0},  # spread 170
        {"fecha": date(2025, 1, 3), "prec_bolsa": 950.0, "prec_cont": 330.0, "prec_escasez": 800.0},  # spread 620
        {"fecha": date(2025, 1, 4), "prec_bolsa": 700.0, "prec_cont": 330.0, "prec_escasez": 800.0},  # spread 370
    ]
    h = contexto.historial_escasez(dias, BINS)
    assert h["n_dias"] == 4
    assert h["n_dias_escasez"] == 1  # solo 950 > 800
    assert h["pct_dias_escasez"] == 25.0
    assert h["frecuencia_bins"]["muy_barata"]["n"] == 1
    assert h["frecuencia_bins"]["barata"]["n"] == 1
    assert h["frecuencia_bins"]["neutral"]["n"] == 1
    assert h["frecuencia_bins"]["cara"]["n"] == 1  # 620 cae en 'cara' (test BINS sin bin escasez)
    assert h["spread_max"] == 620.0
    assert h["spread_p50"] == 370.0
    assert h["por_anio"][2025]["n_escasez"] == 1


def test_config_split_estudio_vs_simulador():
    """config.yaml (estudio) y asistente.yaml (simulador) son independientes."""
    from sfeia.config.settings import load_asistente_config, load_config, load_merged

    estudio = load_config()
    simulador = load_asistente_config()
    # el estudio NO conoce la clave `asistente`; el simulador solo trae la suya
    assert "asistente" not in estudio
    assert set(simulador) == {"asistente"}
    # la fusión conserva lo del estudio + lo del simulador
    merged = load_merged()
    assert merged["database"]["dsn_env"] == "DB_DSN"
    assert merged["diario"]["k"] == 5
    assert merged["asistente"]["segmento_por_defecto"] == "PEQUEÑO"


def test_decision_negocio():
    d = simulacion.decision_negocio(
        dema_kwh=100_000.0, mediana_benigna=86.2,
        margen_escasez=-520.36, margen_escasez_extrema=-715.6,
        pct_escasez=10.64, pct_escasez_nino=25.0,
    )
    assert d["perdida_dia_escasez_cop"] == -52_036_000.0
    assert d["perdida_dia_escasez_extrema_cop"] == -71_560_000.0
    # E = (1-p)*86.2 + p*(-520.36)
    assert d["e_margen_dia_historico"] == round(0.8936 * 86.2 + 0.1064 * -520.36, 2)
    assert d["e_margen_dia_anio_nino"] < 0  # en año Niño pierde en expectativa
    assert "PIERDE" in d["veredicto"]


def test_decision_negocio_benigna():
    d = simulacion.decision_negocio(
        dema_kwh=100_000.0, mediana_benigna=86.2,
        margen_escasez=5.0, margen_escasez_extrema=-15.0,
        pct_escasez=10.64, pct_escasez_nino=25.0,
    )
    assert "Sin pérdida relevante" in d["veredicto"]


def test_detectar_duplicados():
    from sfeia.app.models.entities import AgenteMaestro

    ms = [
        AgenteMaestro("A", "A", 10, 62.48, -10.29),
        AgenteMaestro("B", "B", 10, 62.48, -10.29),
        AgenteMaestro("C", "C", 10, -28.59, -132.91),
    ]
    dups = maestros.detectar_duplicados(ms)
    assert ["A", "B"] in dups
    assert len(dups) == 1


# --------------------------------------------------------- P0: validez ---------
def test_detectar_duplicados_correlacion():
    from sfeia.app.models.entities import AgenteMaestro

    agentes = []
    for i, dia in enumerate(("2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04")):
        agentes.append(AgenteDia("A", "A", dia, "PEQUEÑO", 0, ESTRATEGIA, {}, float(i), 300.0))
        agentes.append(AgenteDia("B", "B", dia, "PEQUEÑO", 0, ESTRATEGIA, {}, float(i) + 0.1, 300.0))
        agentes.append(AgenteDia("C", "C", dia, "PEQUEÑO", 0, ESTRATEGIA, {}, 100.0 - float(i), 300.0))
    ms = [
        AgenteMaestro("A", "A", 4, 1.5, 1.5),
        AgenteMaestro("B", "B", 4, 1.6, 1.6),
        AgenteMaestro("C", "C", 4, 98.5, 98.5),
    ]
    dups = maestros.detectar_duplicados(ms, agentes, umbral_corr=0.9)
    assert any("A" in g and "B" in g for g in dups)
    assert all("C" not in g for g in dups)
    assert maestros.n_efectivo(ms, agentes, umbral_corr=0.9) == 2


def test_bootstrap_skill_luck_sin_skill():
    agentes = []
    for dia in ("2026-01-01", "2026-01-02", "2026-01-03"):
        for codigo in ("A", "B"):
            agentes.append(AgenteDia(codigo, codigo, dia, "PEQUEÑO", 0, ESTRATEGIA, {}, 5.0, 300.0))
    b = maestros.bootstrap_skill_luck(
        agentes, "PEQUEÑO", ESTRATEGIA, top=1, n_dias_estudio=3, n_boot=100, semilla=7, min_dias_pct=0.0
    )
    assert b["mejor_maestro_real"] == 5.0
    assert b["p_valor"] == 1.0  # sin habilidad, el mejor es indistinguible del azar


def test_persistencia_seleccion():
    agentes = []
    for dia in ("2026-02-01", "2026-02-02", "2026-02-03"):
        agentes.append(AgenteDia("A", "A", dia, "PEQUEÑO", 0, ESTRATEGIA, {}, 50.0, 300.0))
        agentes.append(AgenteDia("B", "B", dia, "PEQUEÑO", 0, ESTRATEGIA, {}, -50.0, 300.0))
    h = maestros.persistencia_seleccion(
        agentes, "PEQUEÑO", ESTRATEGIA, {"A", "B"}, n_dias_validacion=3, min_dias_pct=0.0
    )
    assert h["pct_persistencia"] == 50.0  # solo A sigue en la mitad superior (1 de 2)
    h2 = maestros.persistencia_seleccion(
        agentes, "PEQUEÑO", ESTRATEGIA, {"B"}, n_dias_validacion=3, min_dias_pct=0.0
    )
    assert h2["pct_persistencia"] == 0.0


def test_metricas_riesgo_maestros():
    agentes = []
    for dia in ("2026-01-01", "2026-01-02", "2026-01-03"):
        agentes.append(AgenteDia("EXP", "EXP", dia, "PEQUEÑO", 0, ESTRATEGIA, {}, 10.0, 300.0))
        agentes.append(AgenteDia("MALO", "MALO", dia, "PEQUEÑO", 0, ESTRATEGIA, {}, -20.0, 300.0))
    top = maestros.seleccionar_maestros(agentes, "PEQUEÑO", ESTRATEGIA, top=5, n_dias_estudio=3, min_dias_pct=0.0)
    exp = next(m for m in top if m.codigo == "EXP")
    malo = next(m for m in top if m.codigo == "MALO")
    assert exp.pct_dias_perdida == 0.0
    assert malo.pct_dias_perdida == 100.0
    assert malo.downside_mediana == -20.0


def test_pesos_maestros():
    from sfeia.app.models.entities import AgenteMaestro

    ms = [AgenteMaestro("A", "A", 10, 50.0, -10.0), AgenteMaestro("B", "B", 10, -50.0, -10.0)]
    ws = maestros.pesos_maestros(ms, mediana_segmento=0.0, eta=1.0)
    assert abs(sum(ws.values()) - 1.0) < 1e-9
    assert ws["A"] > ws["B"]


def test_politica_ponderada():
    agentedia = _agentedia_toy()
    etiquetas = sorted(agentedia)
    labels = np.array([0 if agentedia[k]["codigo"] == "EXP" else 1 for k in etiquetas])
    perfiles = {
        0: PerfilEstrategia(cluster_id=0, arquetipo=ESTRATEGIA, n=3, n_agentes=1,
                            medias={}, composicion_segmento={"PEQUEÑO": 3}),
        1: PerfilEstrategia(cluster_id=1, arquetipo="Comercializador regulado", n=3, n_agentes=1,
                            medias={}, composicion_segmento={"GRANDE": 3}),
    }
    politica = clonacion.construir_politica(
        agentedia, etiquetas, labels, perfiles, {"EXP"}, "PEQUEÑO", ESTRATEGIA, {"EXP": "PEQUEÑO"}, BINS,
        pesos={"EXP": 1.0},
    )
    assert politica.modo == "ponderado"
    assert politica.rango_spread == (50.0, 50.0)
    assert politica.reglas["barata"].perfil.pct_exposicion == 100.0


def test_aplicar_politica_con_banda():
    politica = PoliticaClonacion(
        reglas={"barata": ReglaPolitica("barata", 0, 200, PerfilAccion(0.0, 100.0, 0.0, 0.0, 0.0), 2)},
        fallback=PerfilAccion(0.0, 100.0, 0.0, 0.0, 0.0),
        bins_spread=BINS, rango_spread=(0.0, 200.0),
    )
    _, en = clonacion.aplicar_politica_con_banda(politica, 50.0)
    assert en is True
    _, en2 = clonacion.aplicar_politica_con_banda(politica, 500.0)
    assert en2 is False


def test_simular_dias_fuera_de_distribucion():
    from datetime import date

    agentedia = {}
    for dia, bolsa in [(date(2026, 1, 1), 900.0), (date(2026, 1, 2), 350.0)]:
        ad = {
            "codigo": "EXP", "dia": dia,
            "dema_kwh": 100_000.0, "dema_reg_kwh": 100_000.0, "dema_noreg_kwh": 0.0,
            "comp_cont_kwh": 0.0, "comp_cont_reg_kwh": 0.0, "vent_cont_kwh": 0.0,
            "comp_bolsa_kwh": 100_000.0, "vent_bolsa_kwh": 0.0, "comp_sicep_kwh": 0.0,
            "prec_cont": 300.0, "prec_bolsa": bolsa, "prec_escasez": 400.0,
        }
        ad["features"] = diario.features_diarias(ad)
        ad["desempeno"] = diario.desempeno_diario(ad, PARAMS)
        agentedia[diario.clave("EXP", dia)] = ad
    politica = PoliticaClonacion(
        reglas={"barata": ReglaPolitica("barata", 0, 200, PerfilAccion(0.0, 100.0, 0.0, 0.0, 0.0), 2)},
        fallback=PerfilAccion(0.0, 100.0, 0.0, 0.0, 0.0),
        bins_spread=BINS, rango_spread=(0.0, 200.0), modo="mediana",
    )
    sims = simulacion.simular_dias(
        agentedia, politica, 100_000.0, PARAMS, {"EXP": "PEQUEÑO"}, "PEQUEÑO", {"EXP"}, BINS,
        usar_spread_previo=True, factor_exposicion_fuera=0.5,
    )
    assert len(sims) == 2
    # día 1: spread mismo día 600 (fuera de rango) -> perfil defensivo 50/50
    assert sims[0].en_distribucion is False
    assert sims[0].perfil.pct_exposicion == 50.0
    assert sims[0].perfil.pct_cobertura == 50.0
    # día 2: spread previo 600 (fuera de rango) -> defensivo también
    assert sims[1].en_distribucion is False
    assert sims[1].perfil.pct_exposicion == 50.0


def test_replicacion_is_oos():
    p = PerfilAccion(0.0, 100.0, 0.0, 0.0, 0.0)
    sims_e = [SimulacionDia("2026-01-01", "barata", False, p, -100.0, -90.0, -80.0)]
    sims_i = [SimulacionDia("2026-02-01", "barata", False, p, -50.0, -90.0, -80.0)]
    r = simulacion.replicacion_is_oos(sims_e, sims_i)
    assert r["ratio_replicacion"] == 0.5
    assert r["mediana_imitacion_is"] == -100.0


def test_dsr_aprox():
    rng = np.random.default_rng(0)
    margenes = rng.normal(5.0, 10.0, 40).tolist()
    d = simulacion.dsr_aprox(margenes, n_trials=10)
    assert d is not None
    assert 0.0 <= d["dsr"] <= 1.0
    assert d["n_trials"] == 10
    assert simulacion.dsr_aprox([], n_trials=10) is None


def test_capacidad():
    agentedia = _agentedia_toy()
    seg = {"EXP": "PEQUEÑO"}
    cap = simulacion.capacidad(1_000_000.0, agentedia, "PEQUEÑO", seg, umbral_pct=5.0)
    assert cap["supera_capacidad"] is True
    cap2 = simulacion.capacidad(4_000.0, agentedia, "PEQUEÑO", seg, umbral_pct=5.0)
    assert cap2["supera_capacidad"] is False


def test_decision_negocio_kill_switch():
    d = simulacion.decision_negocio(
        dema_kwh=100_000.0, mediana_benigna=86.2,
        margen_escasez=-520.36, margen_escasez_extrema=-715.6,
        pct_escasez=10.64, pct_escasez_nino=25.0,
        drawdown_max=900.0, kill_switch_drawdown=500.0,
    )
    assert d["kill_switch_activado"] is True
    assert "KILL-SWITCH" in d["veredicto"]


# --------------------------------------------------------- S1: relativo -----
def test_seleccionar_maestros_relativo():
    agentes = []
    # C y D (otra estrategia) fijan la mediana del segmento por día
    agentes.append(AgenteDia("C", "C", "2026-01-01", "PEQUEÑO", 1, "Regulado", {}, 1100.0, 300.0))
    agentes.append(AgenteDia("C", "C", "2026-01-02", "PEQUEÑO", 1, "Regulado", {}, 80.0, 300.0))
    agentes.append(AgenteDia("C", "C", "2026-01-03", "PEQUEÑO", 1, "Regulado", {}, 80.0, 300.0))
    agentes.append(AgenteDia("D", "D", "2026-01-01", "PEQUEÑO", 1, "Regulado", {}, 10.0, 300.0))
    agentes.append(AgenteDia("D", "D", "2026-01-02", "PEQUEÑO", 1, "Regulado", {}, 10.0, 300.0))
    agentes.append(AgenteDia("D", "D", "2026-01-03", "PEQUEÑO", 1, "Regulado", {}, 10.0, 300.0))
    # A: solo el día de segmento alto (mediana absoluta enorme, relativa nula)
    agentes.append(AgenteDia("A", "A", "2026-01-01", "PEQUEÑO", 0, ESTRATEGIA, {}, 1000.0, 300.0))
    # B: días de segmento bajo (absoluta menor pero relativa claramente positiva)
    agentes.append(AgenteDia("B", "B", "2026-01-02", "PEQUEÑO", 0, ESTRATEGIA, {}, 150.0, 300.0))
    agentes.append(AgenteDia("B", "B", "2026-01-03", "PEQUEÑO", 0, ESTRATEGIA, {}, 150.0, 300.0))
    abs_top = maestros.seleccionar_maestros(agentes, "PEQUEÑO", ESTRATEGIA, top=2, n_dias_estudio=3,
                                            min_dias_pct=0.0, relativo=False)
    rel_top = maestros.seleccionar_maestros(agentes, "PEQUEÑO", ESTRATEGIA, top=2, n_dias_estudio=3,
                                            min_dias_pct=0.0, relativo=True)
    assert abs_top[0].codigo == "A"      # por absoluto gana A (1000)
    assert rel_top[0].codigo == "B"      # por relativo gana B (70 vs 0)
    assert rel_top[0].mediana_relativa == 70.0
    assert rel_top[0].pct_dias_supera_segmento == 100.0


def test_alternativa_recomendada():
    agentes = []
    for dia in ("2026-01-01", "2026-01-02", "2026-01-03"):
        agentes.append(AgenteDia("A", "A", dia, "PEQUEÑO", 0, ESTRATEGIA, {}, 50.0, 300.0))
        agentes.append(AgenteDia("B", "B", dia, "GRANDE", 1, "Regulado", {}, 30.0, 300.0))
    alt = maestros.alternativa_recomendada(agentes, "PEQUEÑO", ESTRATEGIA, n_dias_estudio=3,
                                           min_dias_pct=0.0, top=3)
    assert alt is not None
    assert alt["segmento"] == "GRANDE"
    assert alt["estrategia"] == "Regulado"
    assert alt["n_maestros"] == 1