import os
import sys
from pathlib import Path

def get_base_dir() -> Path:
    """
    Retorna la ruta absoluta del directorio base de la aplicación.
    Si se ejecuta como un ejecutable compilado con PyInstaller (frozen),
    retorna el directorio que contiene al ejecutable.
    Si se ejecuta como script de Python, retorna el directorio raíz del proyecto (padre de 'app').
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent.resolve()
    
    current_dir = Path(__file__).resolve().parent
    if current_dir.name == "app":
        return current_dir.parent.resolve()
    return current_dir.resolve()

BASE_DIR = get_base_dir()

# Directorios de la aplicación (todos absolutos y basados en BASE_DIR)
LOGS_DIR = BASE_DIR / "logs"
DOWNLOADS_DIR = BASE_DIR / "downloads"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
TEMP_DIR = BASE_DIR / "temp"

# Archivos de configuración
CONFIG_FILE = BASE_DIR / "settings.json"

def inicializar_directorios():
    """
    Modo 'Primer Inicio': Crea automáticamente los directorios necesarios si no existen.
    """
    for folder in [LOGS_DIR, DOWNLOADS_DIR, SCREENSHOTS_DIR, TEMP_DIR]:
        folder.mkdir(parents=True, exist_ok=True)
