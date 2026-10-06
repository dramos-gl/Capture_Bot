"""
SATC (Sistema de Automatización de Trámites Cancún) — Punto de Entrada Principal
Lanza la interfaz gráfica PySide6.
"""
import sys
import logging
from pathlib import Path

# Agrega la raíz del módulo satc al path de Python
sys.path.insert(0, str(Path(__file__).parent))

try:
    from satc.src.paths import ensure_dirs
except ImportError:
    from src.paths import ensure_dirs

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("satc.main")


def main() -> None:
    """Punto de entrada principal de SATC."""
    logger.info("Iniciando SATC (Sistema de Automatización de Trámites Cancún)...")
    ensure_dirs()

    try:
        from PySide6.QtWidgets import QApplication
        try:
            from satc.src.storage.db_connector import verificar_conexion
        except ImportError:
            from src.storage.db_connector import verificar_conexion

        # Verifica conexión a BD antes de iniciar UI
        if not verificar_conexion():
            logger.critical("No se pudo conectar a la base de datos de SATC. Verifica settings.json.")
            sys.exit(1)

        app = QApplication(sys.argv)
        app.setApplicationName("SATC")
        app.setApplicationVersion("2.0.0")

        # TODO: Importar y mostrar la vista principal cuando esté implementada
        # from src.ui.views.main_view import MainView
        # window = MainView()
        # window.show()

        logger.info("SATC listo.")
        sys.exit(app.exec())

    except ImportError as e:
        logger.critical(f"Dependencia faltante: {e}. Ejecuta: pip install -r requirements.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()

