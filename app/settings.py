import json
import os
import sys
from pathlib import Path
from app.paths import CONFIG_FILE

DEFAULT_CONFIG = {
    "excel_path": "",
    "download_dir": "",
    "last_used": None,
    "satq_url": "https://satq.qroo.gob.mx/paperless/timbrador.html",
    "max_timbrado_retries": 2,
    "reintento_automatico": True,
    "modo_timbrado": "asistido"
}

def _load_config() -> dict:
    """Carga el JSON de configuración. Si el archivo falta o está corrupto, devuelve los valores por defecto."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # combinar con defaults para asegurar claves
                return {**DEFAULT_CONFIG, **data}
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def _save_config(config: dict) -> None:
    """Guarda de forma segura el diccionario de configuración en JSON."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def get_config() -> dict:
    """Devuelve la configuración completa como diccionario."""
    return _load_config()

def set_excel_path(path: str) -> None:
    cfg = _load_config()
    cfg["excel_path"] = os.path.abspath(path)
    cfg["last_used"] = "excel"
    _save_config(cfg)

def set_satq_url(url: str) -> None:
    cfg = _load_config()
    cfg["satq_url"] = url.strip()
    cfg["last_used"] = "satq_url"
    _save_config(cfg)

def set_download_dir(path: str) -> None:
    cfg = _load_config()
    cfg["download_dir"] = os.path.abspath(path)
    cfg["last_used"] = "download"
    _save_config(cfg)

def get_excel_path() -> str:
    return _load_config().get("excel_path", "")

def get_download_dir() -> str:
    val = _load_config().get("download_dir", "")
    if not val:
        from app.paths import DOWNLOADS_DIR
        return str(DOWNLOADS_DIR)
    return val

def get_satq_url() -> str:
    return _load_config().get("satq_url", "https://satq.qroo.gob.mx/paperless/timbrador.html")

def get_max_timbrado_retries() -> int:
    """Devuelve el número máximo de reintentos automáticos al timbrar cuando se detecta fallo del portal."""
    return _load_config().get("max_timbrado_retries", 2)

def get_reintento_automatico() -> bool:
    """Indica si el bot debe intentar automáticamente volver a cargar la página en caso de error."""
    return _load_config().get("reintento_automatico", True)

def get_modo_timbrado() -> str:
    """Obtiene el modo de timbrado configurado ('asistido' o 'autonomo')."""
    return _load_config().get("modo_timbrado", "asistido")

def set_modo_timbrado(modo: str) -> None:
    """Persiste el modo de timbrado en settings.json. Valores: 'asistido' | 'autonomo'."""
    if modo not in ("asistido", "autonomo"):
        raise ValueError(f"Modo inválido: '{modo}'. Use 'asistido' o 'autonomo'.")
    cfg = _load_config()
    cfg["modo_timbrado"] = modo
    _save_config(cfg)
