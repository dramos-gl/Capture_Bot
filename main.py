import os
import sys

from app.paths import BASE_DIR, LOGS_DIR, inicializar_directorios
# --- SOLUCIÓN DE COMPATIBILIDAD TCL/TK EN ENTORNOS VIRTUALES (EXTRA CAUTELA) ---
# Evita el error '_tkinter.TclError: Can't find a usable init.tcl' inyectando
# dinámicamente las rutas desde sys.base_prefix si no están en el entorno.
base_tcl = os.path.join(sys.base_prefix, 'tcl')
if os.path.exists(base_tcl):
    for folder in os.listdir(base_tcl):
        if folder.startswith('tcl'):
            os.environ['TCL_LIBRARY'] = os.path.join(base_tcl, folder)
        elif folder.startswith('tk'):
            os.environ['TK_LIBRARY'] = os.path.join(base_tcl, folder)

import queue
import logging
from logging.handlers import RotatingFileHandler

from app.orchestrator import BotOrchestrator
from app.gui import OptimaCaptureApp

# Ruta predeterminada del libro Excel en el workspace
DEFAULT_EXCEL_NAME = "Optima_Capture_Bot.xlsx"

def inicializar_entorno():
    """
    Crea las carpetas de la arquitectura modular si no existen en la raíz.
    """
    inicializar_directorios()

def configurar_logging():
    """
    Configura el sistema de logs tanto para consola como para archivo rotativo diario.
    """
    log_format = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
    
    # Manejador de archivo rotativo en la carpeta logs/
    log_file = str(LOGS_DIR / "optima_capture_bot.log")
    file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.INFO)
    
    # Manejador de consola estándar
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    console_handler.setLevel(logging.INFO)
    
    # Configurar Logger Raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    logging.info("Sistema de logging inicializado exitosamente.")

def main():
    # 1. Crear directorios base
    inicializar_entorno()
    
    # 2. Configurar logs del sistema
    configurar_logging()
    # 3. Localizar archivo Excel usando settings/fallback
    from app import settings
    excel_path = settings.get_excel_path()
    if not excel_path or not os.path.exists(excel_path):
        default_path = str(BASE_DIR / DEFAULT_EXCEL_NAME)
        if os.path.exists(default_path):
            excel_path = default_path
            settings.set_excel_path(excel_path)
            logging.info(f"Archivo Excel predeterminado encontrado y configurado: {excel_path}")
        else:
            excel_path = ""
            logging.warning("Advertencia: No se encontró ningún archivo Excel válido al iniciar. Se solicitará al usuario seleccionarlo desde la interfaz gráfica.")
    else:
        logging.info(f"Archivo Excel cargado desde configuración: {excel_path}")
    
    # 4. Crear la cola thread-safe de eventos
    event_queue = queue.Queue()
    
    # 5. Instanciar el Orquestador del Bot
    orchestrator = BotOrchestrator(excel_path=excel_path, event_queue=event_queue)
    
    # 6. Lanzar la Interfaz Gráfica CustomTkinter en el hilo principal
    logging.info("Lanzando interfaz gráfica en CustomTkinter...")
    app = OptimaCaptureApp(
        excel_path=excel_path, 
        event_queue=event_queue, 
        orchestrator=orchestrator
    )
    
    # Registrar el app en el orquestador si hiciera falta para alguna referencia rápida
    # pero el flujo principal ya está desacoplado mediante la cola de eventos.
    
    try:
        app.mainloop()
    except KeyboardInterrupt:
        logging.warning("Interrupción de teclado detectada. Cerrando bot...")
    finally:
        # Cerrar de forma segura cualquier recurso abierto en caso de cierres bruscos
        if orchestrator.scraper:
            orchestrator.scraper.cerrar()
        logging.info("Aplicación cerrada de forma limpia.")

if __name__ == "__main__":
    main()
