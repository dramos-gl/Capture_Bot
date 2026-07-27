"""
CancunBot — Servicio de Configuración
Carga settings.json y variables de entorno (.env).
"""
import json
import os
import logging
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Carga .env si existe
_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

_settings_path = Path(__file__).parent.parent.parent / "settings.json"
_settings_cache: dict | None = None


def cargar_settings() -> dict:
    """Carga y cachea el archivo settings.json."""
    global _settings_cache
    if _settings_cache is None:
        if not _settings_path.exists():
            raise FileNotFoundError(f"No se encontró settings.json en: {_settings_path}")
        with open(_settings_path, encoding="utf-8") as f:
            _settings_cache = json.load(f)
        logger.info("settings.json cargado correctamente.")
    return _settings_cache


def obtener(clave: str, default: Any = None) -> Any:
    """Obtiene un valor de settings.json o variable de entorno.
    Las variables de entorno tienen prioridad sobre settings.json.
    """
    # Primero busca en variables de entorno
    env_value = os.getenv(clave)
    if env_value is not None:
        return env_value
    # Luego en settings.json
    settings = cargar_settings()
    return settings.get(clave, default)


def get_db_url() -> str:
    """Construye la URL de conexión a PostgreSQL para SQLAlchemy."""
    host = obtener("DB_HOST", "127.0.0.1")
    port = obtener("DB_PORT", "5432")
    name = obtener("DB_NAME", "db_cancunbot")
    user = obtener("DB_USER", "postgres")
    password = obtener("DB_PASSWORD", "")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
