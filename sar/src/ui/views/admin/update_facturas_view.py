"""View to trigger updating metadata on invoices by scanning PDF texts."""

import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QTextEdit,
    QProgressBar, QCheckBox, QComboBox
)
from PySide6.QtCore import Qt, QThread, Signal
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sqlalchemy import text

class UpdateWorker(QThread):
    """Worker thread to extract metadata from PDFs without blocking the UI."""
    progress_signal = Signal(str, int)  # message, progress_percentage
    finished_signal = Signal(dict)       # summary stats

    def __init__(self, db_connector, scan_delegation, scan_uuid, orden_id=None, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.scan_delegation = scan_delegation
        self.scan_uuid = scan_uuid
        self.orden_id = orden_id

    def extract_delegacion_from_pdf(self, pdf_path: str) -> str:
        if not pdf_path or not os.path.exists(pdf_path):
            return None
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                text_content = page.extract_text()
                if text_content:
                    text_lower = text_content.lower()
                    replacements = {
                        "\xf3": "o", "ó": "o",
                        "\xe1": "a", "á": "a",
                        "\xe9": "e", "é": "e",
                        "\xed": "i", "í": "i",
                        "\xfa": "u", "ú": "u",
                        "\xf1": "n", "ñ": "n",
                        "\ufffd": "o"
                    }
                    for old, new in replacements.items():
                        text_lower = text_lower.replace(old, new)

                    if "delegacion cancun" in text_lower:
                        return "Cancun"
                    elif "delegacion playa del carmen" in text_lower:
                        return "Playa del Carmen"
                    elif "delegacion chetumal" in text_lower:
                        return "Chetumal"
        except Exception as e:
            self.progress_signal.emit(f"  [Advertencia] Error al leer {os.path.basename(pdf_path)}: {e}", -1)
        return None

    def extract_uuid_from_pdf(self, pdf_path: str) -> str:
        """Example placeholder for scanning other fields like UUID from XML/PDF structure."""
        if not pdf_path or not os.path.exists(pdf_path):
            return None
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            import re
            uuid_regex = re.compile(r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}')
            for page in reader.pages:
                text_content = page.extract_text()
                if text_content:
                    match = uuid_regex.search(text_content)
                    if match:
                        return match.group(0)
        except Exception:
            pass
        return None

    def run(self):
        stats = {"total": 0, "delegaciones_ok": 0, "uuids_ok": 0, "sin_archivo": 0, "no_legibles": 0}
        
        try:
            with self.db_connector.get_session() as session:
                # Buscar facturas que necesiten actualización
                conditions = []
                if self.scan_delegation:
                    conditions.append("(delegacion IS NULL OR delegacion = '')")
                if self.scan_uuid:
                    conditions.append("(uuid IS NULL OR uuid = '')")
                    
                if not conditions:
                    self.progress_signal.emit("No se ha seleccionado ningún campo para escanear.", 100)
                    self.finished_signal.emit(stats)
                    return

                conditions_str = " OR ".join(conditions)
                params = {}
                if self.orden_id:
                    query_str = f"""
                        SELECT f.factura_id, f.pdf_path, f.pdf2_path, f.uuid, f.nombre_archivo, f.delegacion
                        FROM sar_archivo.factura f
                        JOIN sar_produccion.referencia r ON f.referencia_id = r.referencia_id
                        JOIN sar_produccion.grupo_referencia gr ON r.grupo_id = gr.grupo_id
                        WHERE ({conditions_str}) AND gr.orden_id = :orden_id
                    """
                    params["orden_id"] = self.orden_id
                else:
                    query_str = f"""
                        SELECT factura_id, pdf_path, pdf2_path, uuid, nombre_archivo, delegacion
                        FROM sar_archivo.factura
                        WHERE {conditions_str}
                    """
                facturas = session.execute(text(query_str), params).all()
                stats["total"] = len(facturas)
                
                if stats["total"] == 0:
                    self.progress_signal.emit("No hay facturas pendientes por actualizar para los criterios seleccionados.", 100)
                    self.finished_signal.emit(stats)
                    return
                
                self.progress_signal.emit(f"Se encontraron {stats['total']} facturas pendientes de escaneo.", 0)
                
                for idx, row in enumerate(facturas, 1):
                    pct = int((idx / stats["total"]) * 100)
                    factura_id = row.factura_id
                    pdf_path = row.pdf_path
                    pdf2_path = row.pdf2_path
                    folio_label = row.nombre_archivo or row.uuid or f"ID {factura_id}"
                    
                    self.progress_signal.emit(f"[{idx}/{stats['total']}] Analizando factura: {folio_label}", pct)
                    
                    updates = {}
                    
                    # 1. Escaneo de Delegación
                    if self.scan_delegation and (not row.delegacion): # Si el usuario eligió y la delegación está vacía
                        delegacion = None
                        if pdf_path:
                            delegacion = self.extract_delegacion_from_pdf(pdf_path)
                        if not delegacion and pdf2_path:
                            delegacion = self.extract_delegacion_from_pdf(pdf2_path)
                            
                        if delegacion:
                            updates["delegacion"] = delegacion
                            stats["delegaciones_ok"] += 1
                            self.progress_signal.emit(f"  -> Encontrada delegación: '{delegacion}'", pct)
                    
                    # 2. Escaneo de UUID
                    if self.scan_uuid and (not row.uuid):
                        uuid_val = None
                        if pdf_path:
                            uuid_val = self.extract_uuid_from_pdf(pdf_path)
                        if not uuid_val and pdf2_path:
                            uuid_val = self.extract_uuid_from_pdf(pdf2_path)
                            
                        if uuid_val:
                            updates["uuid"] = uuid_val
                            stats["uuids_ok"] += 1
                            self.progress_signal.emit(f"  -> Encontrado UUID: '{uuid_val}'", pct)
                    
                    # Aplicar actualizaciones a base de datos
                    if updates:
                        set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
                        updates["fid"] = factura_id
                        session.execute(text(f"""
                            UPDATE sar_archivo.factura
                            SET {set_clause}
                            WHERE factura_id = :fid
                        """), updates)
                    else:
                        # Verificar si existe el archivo
                        path_exists_1 = os.path.exists(pdf_path) if pdf_path else False
                        path_exists_2 = os.path.exists(pdf2_path) if pdf2_path else False
                        if not path_exists_1 and not path_exists_2:
                            stats["sin_archivo"] += 1
                        else:
                            stats["no_legibles"] += 1
                            
            self.progress_signal.emit("Escaneo completado. Guardando cambios...", 100)
            self.finished_signal.emit(stats)
            
        except Exception as e:
            self.progress_signal.emit(f"Error crítico durante el escaneo: {e}", 100)
            self.finished_signal.emit(stats)


class UpdateFacturasView(QWidget):
    """Sub-view to trigger metadata updates on invoices by scanning PDF files."""
    
    def __init__(self, db_connector, current_user_id, current_sesion_id, can_edit, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.current_user_id = current_user_id
        self.current_sesion_id = current_sesion_id
        self.can_edit = can_edit
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(16)
        
        self._build_ui()
        
    def _build_ui(self):
        # Label de descripción completa de la funcionalidad
        self.lbl_desc = CustomLabel(
            "<b>Descripción del Proceso:</b><br/>"
            "Este proceso automatizado escanea los archivos PDF de facturas físicas almacenados en el storage para recuperar información faltante de forma retrospectiva.<br/>"
            "1. Marca la opción <b>Escanear Delegación</b> para extraer del texto la delegación (Cancún, Playa del Carmen o Chetumal).<br/>"
            "2. Marca la opción <b>Escanear UUID</b> para recuperar de forma automática el folio fiscal (UUID de 36 caracteres).<br/>"
            "3. Presiona <b>Iniciar Escaneo e Importación</b> para procesar en segundo plano todas las facturas con metadatos vacíos sin congelar la aplicación.",
            variant="body"
        )
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 12px; border-radius: 6px; color: #475569;")
        self.layout.addWidget(self.lbl_desc)

        # Selector de orden
        self.order_layout = QHBoxLayout()
        self.order_layout.addWidget(CustomLabel("Filtrar por Orden:", variant="body"))
        self.combo_orden = QComboBox()
        self.combo_orden.setMinimumWidth(300)
        self.order_layout.addWidget(self.combo_orden)
        self.order_layout.addStretch()
        self.layout.addLayout(self.order_layout)

        # Checkboxes for fields to scan
        self.chk_layout = QHBoxLayout()
        self.chk_delegacion = QCheckBox("Escanear Delegación (Cancun, Playa, Chetumal)")
        self.chk_delegacion.setChecked(True)
        self.chk_uuid = QCheckBox("Escanear UUID (Formatos Regex)")
        
        self.chk_layout.addWidget(self.chk_delegacion)
        self.chk_layout.addWidget(self.chk_uuid)
        self.chk_layout.addStretch()
        
        # Action button
        self.btn_iniciar = CustomButton("Iniciar Escaneo e Importación", icon_name="settings")
        self.btn_iniciar.clicked.connect(self._on_start_scan)
        self.btn_iniciar.setEnabled(self.can_edit)
        self.chk_layout.addWidget(self.btn_iniciar)
        
        self.layout.addLayout(self.chk_layout)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.layout.addWidget(self.progress_bar)
        
        # Console output
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("font-family: Consolas, monospace; background-color: #f7fafc; color: #2d3748;")
        self.layout.addWidget(self.console)

    def refresh_data(self):
        """Clean UI state and populate orders."""
        self.console.clear()
        self.progress_bar.setValue(0)
        
        self.combo_orden.blockSignals(True)
        self.combo_orden.clear()
        self.combo_orden.addItem("Todas las Órdenes", None)
        
        try:
            with self.db_connector.get_session() as session:
                res = session.execute(text("""
                    SELECT orden_id, folio, descripcion, fecha_creacion 
                    FROM sar_produccion.orden_generacion 
                    ORDER BY orden_id DESC
                """)).mappings().all()
                
                from sar.src.ui.design_system.utils.formatters import format_orden_filter_label
                for r in res:
                    label = format_orden_filter_label(r["folio"], r.get("descripcion"))
                    self.combo_orden.addItem(label, r["orden_id"])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar las órdenes: {e}")
            
        self.combo_orden.blockSignals(False)

    def _on_start_scan(self):
        self.console.clear()
        self.btn_iniciar.setEnabled(False)
        
        # Obtener el orden_id seleccionado
        orden_id = self.combo_orden.currentData()
        
        # Iniciar thread worker
        self.worker = UpdateWorker(
            self.db_connector,
            scan_delegation=self.chk_delegacion.isChecked(),
            scan_uuid=self.chk_uuid.isChecked(),
            orden_id=orden_id
        )
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, msg: str, val: int):
        if val >= 0:
            self.progress_bar.setValue(val)
        self.console.append(msg)
        # Auto-scroll console
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

    def _on_finished(self, stats: dict):
        self.btn_iniciar.setEnabled(True)
        QMessageBox.information(
            self, "Proceso Completado",
            f"Escaneo finalizado.\n\n"
            f"Total procesados: {stats['total']}\n"
            f"Delegaciones importadas: {stats['delegaciones_ok']}\n"
            f"UUIDs importados: {stats['uuids_ok']}\n"
            f"Archivos no encontrados: {stats['sin_archivo']}\n"
            f"PDFs no legibles: {stats['no_legibles']}"
        )
