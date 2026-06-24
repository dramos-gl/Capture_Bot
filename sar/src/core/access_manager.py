"""Manager for robust destination path validation, error handling, local contingency fallback and background synchronization."""

import os
import uuid
import shutil
import logging
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from sqlalchemy import text

logger = logging.getLogger("OptimaCaptureBot.AccessManager")

def check_write_access(path_str: str) -> tuple[bool, str]:
    """
    Checks if a path is fully accessible and has read/write permissions.
    Tries to create a directory structure, write an atomic temp file, and delete it.
    Returns (has_access: bool, error_message: str)
    """
    try:
        path = Path(path_str).resolve()
        
        # 1. Attempt to create directory if not exists
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return False, f"La ruta no existe y no pudo ser creada: {str(e)}"
                
        # 2. Perform atomic write test
        test_file = path / f".ocb_write_test_{uuid.uuid4().hex}.tmp"
        try:
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("test_access")
            test_file.unlink() # Delete test file
            return True, ""
        except (PermissionError, OSError) as e:
            return False, f"Sin permisos de escritura: {str(e)}"
            
    except Exception as e:
        return False, f"Fallo al intentar acceder: {str(e)}"


class PathVerifyThread(QThread):
    """Asynchronous thread to check path connectivity without locking PySide6 GUI."""
    result_ready = Signal(str, bool, str) # path_str, has_access, error_message

    def __init__(self, path_str: str, parent=None):
        super().__init__(parent)
        self.path_str = path_str

    def run(self):
        has_access, err_msg = check_write_access(self.path_str)
        self.result_ready.emit(self.path_str, has_access, err_msg)


class SyncContingencyThread(QThread):
    """Background thread to safely migrate files from local contingency to remote default output dir."""
    progress_msg = Signal(str)
    finished_sync = Signal(bool, int, str) # success, files_migrated, message

    def __init__(self, db_connector, default_output_dir: str, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.default_output_dir = default_output_dir

    def run(self):
        self.progress_msg.emit("Iniciando sincronización de contingencia local...")
        contingency_dir = os.path.abspath(os.path.join("storage", "contingencia"))
        if not os.path.exists(contingency_dir):
            self.finished_sync.emit(True, 0, "No existe carpeta de contingencia local. Nada que sincronizar.")
            return

        # Check default path availability
        ok, err = check_write_access(self.default_output_dir)
        if not ok:
            self.finished_sync.emit(False, 0, f"Ruta por defecto '{self.default_output_dir}' no es accesible: {err}")
            return

        migrated_count = 0
        try:
            # 1. Traverse all files in contingency folder
            for root, _, files in os.walk(contingency_dir):
                for file in files:
                    if not file.lower().endswith(".pdf"):
                        continue
                    
                    local_filepath = os.path.join(root, file)
                    
                    rel_path = os.path.relpath(local_filepath, contingency_dir)
                    # rel_path format: [boletas|facturas]/[orden|año]/[RFC]/[concepto]/[file]
                    parts = rel_path.split(os.sep)
                    
                    if len(parts) < 2:
                        dest_subdir = os.path.abspath(self.default_output_dir)
                    else:
                        # Rebuild identical nested tree in network drive: [default_output_dir]/[boletas|facturas]/[orden|año]/[RFC]/[concepto]/
                        dest_subdir = os.path.abspath(os.path.join(self.default_output_dir, *parts[:-1]))
                        
                    os.makedirs(dest_subdir, exist_ok=True)
                    dest_filepath = os.path.join(dest_subdir, file)
                    
                    self.progress_msg.emit(f"Migrando {file} a ruta por defecto...")
                    
                    # Move physical file
                    shutil.move(local_filepath, dest_filepath)
                    migrated_count += 1
                    
                    # 2. Update physical path in database
                    # Database holds either:
                    # - sar_archivo.archivo_pdf (boletas): where nombre_archivo = file
                    # - sar_archivo.factura (facturas): where pdf_path contains file name
                    with self.db_connector.get_session() as session:
                        # Try update boleta path
                        upd_pdf = text("""
                            UPDATE sar_archivo.archivo_pdf
                            SET ruta_archivo = :new_path
                            WHERE nombre_archivo = :filename
                        """)
                        session.execute(upd_pdf, {"new_path": dest_filepath, "filename": file})
                        
                        # Try update factura path
                        upd_fact = text("""
                            UPDATE sar_archivo.factura
                            SET pdf_path = :new_path
                            WHERE pdf_path LIKE :pattern
                        """)
                        session.execute(upd_fact, {"new_path": dest_filepath, "pattern": f"%{file}"})
                        session.commit()
            
            # Clean up empty subdirs in contingency
            try:
                for root, dirs, _ in os.walk(contingency_dir, topdown=False):
                    for d in dirs:
                        dir_to_remove = os.path.join(root, d)
                        if not os.listdir(dir_to_remove):
                            os.rmdir(dir_to_remove)
            except:
                pass
                
            self.finished_sync.emit(True, migrated_count, f"Sincronización completada. Se migraron {migrated_count} archivos.")
            
        except Exception as e:
            logger.exception("Error during contingency sync:")
            self.finished_sync.emit(False, migrated_count, f"Error durante sincronización: {str(e)}")
