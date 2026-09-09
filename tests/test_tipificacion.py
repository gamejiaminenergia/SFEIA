"""Pruebas unitarias de la tipificación de arquetipos (F6)."""
from app.services.tipificacion import tipificar


def test_integrado_de_red():
    assert tipificar("ENDC", "GRANDE", {"pct_reg": 75, "pct_sicep": 90}) == "Integrado de red"


def test_intervenido():
    assert tipificar("CSIC", "GRANDE", {"pct_reg": 92, "pct_sicep": 30}) == "Distribuidor en intervención"


def test_generador_solo_no_regulado():
    assert tipificar("GECC", "GRANDE", {"pct_reg": 0, "pct_sicep": 0}) == "Generador+comercializador solo no regulado"
    assert tipificar("ISGC", "MEDIANO", {"pct_reg": 5, "pct_sicep": 0}) == "Generador+comercializador solo no regulado"


def test_regional_regulado():
    assert tipificar("CNSC", "MEDIANO", {"pct_reg": 100, "pct_exposicion": 5}) == "Regional regulado"


def test_trader_mixto_mediano():
    assert tipificar("NEUC", "MEDIANO", {"pct_reg": 47, "pct_exposicion": 30}) == "Trader mixto"


def test_trader_no_regulado_pequeno():
    assert tipificar("FERC", "PEQUEÑO", {"pct_reg": 0, "pct_exposicion": 40}) == "Trader no regulado especializado"


def test_frontera_regulada():
    assert tipificar("EBPC", "PEQUEÑO", {"pct_reg": 100, "pct_exposicion": 2}) == "Frontera regulada"