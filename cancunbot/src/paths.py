"""
CancunBot — Rutas del Proyecto
Centraliza todas las rutas de archivos y directorios relevantes.
"""
from pathlib import Path

# Raíz del proyecto CancunBot
ROOT_DIR: Path = Path(__file__).parent.parent

# Fuentes de configuración
SETTINGS_FILE: Path = ROOT_DIR / "settings.json"
ENV_FILE: Path = ROOT_DIR / ".env"

# Directorios temporales
TEMP_DIR: Path = ROOT_DIR / "temp"
DOWNLOAD_TEMP_DIR: Path = TEMP_DIR / "downloads"
SESSION_STATE_DIR: Path = TEMP_DIR / "sessions"

# Logs
LOGS_DIR: Path = ROOT_DIR / "logs"

# Migraciones SQL
MIGRATIONS_DIR: Path = ROOT_DIR / "src" / "storage" / "migrations"

def ensure_dirs() -> None:
    """Crea los directorios necesarios si no existen."""
    for directory in [TEMP_DIR, DOWNLOAD_TEMP_DIR, SESSION_STATE_DIR, LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
