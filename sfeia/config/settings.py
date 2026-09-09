"""Carga de configuración del proyecto SFEIA.

Centraliza la lectura de config/config.yaml y de variables de entorno
(DB_DSN, CREG_URL). No contiene credenciales en código.
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "config.yaml"


def load_config(path: str | Path | None = None) -> dict:
    """Lee config/config.yaml y devuelve el diccionario de configuración."""
    cfg_path = Path(path) if path else CONFIG_PATH
    with open(cfg_path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def db_dsn(cfg: dict) -> str:
    """DSN de la BD elecdb: variable de entorno DB_DSN o default del config."""
    d = cfg["database"]
    return os.getenv(d["dsn_env"], d["default"])


def creg_url(cfg: dict) -> str:
    """URL del asistente normativo CREG: variable CREG_URL o default."""
    c = cfg["creg"]
    return os.getenv(c["url_env"], c["default"])