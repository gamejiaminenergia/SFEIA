"""Carga de configuración del proyecto SFEIA.

Hay DOS archivos independientes:
- `config/config.yaml`     -> configuración del ESTUDIO (motor): database,
  ventana, segmentación, modelo financiero y clustering diario.
- `config/asistente.yaml`  -> configuración del SIMULADOR (asistente imitador).

El asistente (punto de entrada `python -m sfeia.main`) carga el estudio y le
suma su propia configuración (`load_merged`). Cada archivo se entiende solo.
No contiene credenciales en código (DB_DSN vía variable de entorno).
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "config.yaml"
ASISTENTE_CONFIG_PATH = BASE_DIR / "config" / "asistente.yaml"


def load_config(path: str | Path | None = None) -> dict:
    """Lee config/config.yaml (ESTUDIO) y devuelve su diccionario."""
    cfg_path = Path(path) if path else CONFIG_PATH
    with open(cfg_path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_asistente_config(path: str | Path | None = None) -> dict:
    """Lee config/asistente.yaml (SIMULADOR) y devuelve su diccionario."""
    cfg_path = Path(path) if path else ASISTENTE_CONFIG_PATH
    with open(cfg_path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_merged(path: str | Path | None = None, asistente_path: str | Path | None = None) -> dict:
    """Configuración completa: estudio + asistente fusionadas.

    Las claves del estudio vienen de config.yaml; la clave `asistente` se
    sobreescribe con config/asistente.yaml (independiente).
    """
    cfg = load_config(path)
    cfg.update(load_asistente_config(asistente_path))
    return cfg


def db_dsn(cfg: dict) -> str:
    """DSN de la BD elecdb: variable de entorno DB_DSN o default del config."""
    d = cfg["database"]
    return os.getenv(d["dsn_env"], d["default"])