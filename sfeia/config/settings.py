"""Carga de configuración del proyecto SFEIA.

Un SOLO archivo: `config/config.yaml` contiene el motor (estudio híbrido
diario) y el simulador (asistente imitador). Antes eran dos archivos
(config.yaml + asistente.yaml); se fusionaron porque el asistente reutiliza el
motor (ventana, modelo financiero y guardas del diario) y tenerlos separados
duplicaba el foco. `load_config` es la única entrada; `load_merged` se conserva
como alias para no romper la interfaz. No contiene credenciales en código
(DB_DSN vía variable de entorno).
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "config.yaml"


def load_config(path: str | Path | None = None) -> dict:
    """Lee config/config.yaml (configuración única) y devuelve su diccionario."""
    cfg_path = Path(path) if path else CONFIG_PATH
    with open(cfg_path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_merged(path: str | Path | None = None) -> dict:
    """Configuración completa. Antes fusionaba estudio + simulador; ahora hay
    un solo archivo, así que es idéntica a `load_config` (se mantiene como
    alias para no romper la interfaz de los controladores)."""
    return load_config(path)


def db_dsn(cfg: dict) -> str:
    """DSN de la BD elecdb: variable de entorno DB_DSN o default del config."""
    d = cfg["database"]
    return os.getenv(d["dsn_env"], d["default"])