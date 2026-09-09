"""Pruebas unitarias de la segmentación (F-1)."""
from sfeia.app.models.entities import Segmento
from sfeia.app.services.segmentacion import asignar_segmento, resumen_por_segmento, segmentar_poblacion


def test_asignar_segmento_umbrales():
    assert asignar_segmento(7403.4) == Segmento.GRANDE
    assert asignar_segmento(2000.0) == Segmento.GRANDE
    assert asignar_segmento(1999.9) == Segmento.MEDIANO
    assert asignar_segmento(1645.2) == Segmento.MEDIANO
    assert asignar_segmento(100.0) == Segmento.MEDIANO
    assert asignar_segmento(99.9) == Segmento.PEQUEÑO
    assert asignar_segmento(0.1) == Segmento.PEQUEÑO


def test_asignar_segmento_umbrales_personalizados():
    assert asignar_segmento(1500.0, grande_min=3000.0) == Segmento.MEDIANO
    assert asignar_segmento(50.0, mediano_min=10.0) == Segmento.MEDIANO


def test_segmentar_poblacion_y_resumen():
    rows = [
        {"agente_code": "AAA", "name": "A", "dema_come_gwh": 5000.0, "reg_gwh": 3000.0, "noreg_gwh": 2000.0},
        {"agente_code": "BBB", "name": "B", "dema_come_gwh": 500.0, "reg_gwh": 500.0, "noreg_gwh": 0.0},
        {"agente_code": "CCC", "name": "C", "dema_come_gwh": 50.0, "reg_gwh": 0.0, "noreg_gwh": 50.0},
    ]
    poblacion = segmentar_poblacion(rows)
    assert [p.segmento for p in poblacion] == [Segmento.GRANDE, Segmento.MEDIANO, Segmento.PEQUEÑO]
    assert poblacion[0].pct_noreg == 40.0
    assert poblacion[2].pct_reg == 0.0

    resumen = resumen_por_segmento(poblacion)
    assert resumen["GRANDE"]["n"] == 1
    assert resumen["MEDIANO"]["n"] == 1
    assert resumen["PEQUEÑO"]["n"] == 1
    assert resumen["GRANDE"]["pct_mercado"] == 90.1
    assert resumen["PEQUEÑO"]["pct_mercado"] == 0.9