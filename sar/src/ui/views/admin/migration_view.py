"""Migration Administration Sub-view."""

import os
import csv
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QComboBox
)
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
from PySide6.QtCore import Qt, QThread, Signal
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.storage.repositories import ConfigRepository
from sar.src.services.admin_service import AdminService
from sqlalchemy import text

class MigrationWorker(QThread):
    finished_signal = Signal()
    error_signal = Signal(str)

    def __init__(self, orden_id, csv_path, parent=None):
        super().__init__(parent)
        self.orden_id = orden_id
        self.csv_path = csv_path

    def run(self):
        try:
            import importlib.util
            from datetime import datetime
            
            spec = importlib.util.spec_from_file_location("migrar_script", "sar/scripts/core/migrar_orden4_a_orden5.py")
            migrar_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migrar_module)
            
            # Sobrescribir constantes del script
            migrar_module.ORDEN_4_ID = self.orden_id
            migrar_module.CSV_PATH = self.csv_path
            migrar_module.DESCRIPCION_ORDEN_5 = f"Migración desde Orden {self.orden_id} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Ejecutar main del script
            migrar_module.main()
            self.finished_signal.emit()
        except Exception as e:
            self.error_signal.emit(str(e))

class MigrationView(QWidget):
    """View to download the migration template and trigger the Order migration process."""
    
    def __init__(self, db_connector, current_user_id, current_sesion_id, can_edit, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.current_user_id = current_user_id
        self.current_sesion_id = current_sesion_id
        self.can_edit = can_edit
        
        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(16)
        
        self._build_ui()
        
    def _build_ui(self):
        # Label de descripción completa de la funcionalidad
        self.lbl_desc = CustomLabel(
            "<b>Descripción del Proceso:</b><br/>"
            "Este proceso permite reubicar y transferir masivamente referencias mal clasificadas "
            "(ej. asignadas a una delegación incorrecta en la orden original) hacia una nueva Orden de Generación de corrección.<br/>"
            "1. <b>Selecciona</b> la orden de origen.<br/>"
            "2. Presiona <b>Generar Plantilla CSV</b> para descargar el mapeo actual.<br/>"
            "3. Edita el CSV en Excel cambiando únicamente los IDs en la columna <b>delegacion_id</b> (1: CHETUMAL, 2: CANCUN, 3: PLAYA DEL CARMEN, 4: COZUMEL).<br/>"
            "4. Presiona <b>Ejecutar Migración</b> y sube el archivo modificado para mover transaccionalmente las referencias en BD y reubicar/renombrar físicamente las facturas PDF en el storage.",
            variant="body"
        )
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 12px; border-radius: 6px; color: #475569;")
        self.layout.addWidget(self.lbl_desc)

        # Top Controls Layout
        self.controls_layout = QHBoxLayout()
        
        # Selector de orden de origen
        self.controls_layout.addWidget(CustomLabel("Orden de Origen:", variant="body"))
        self.combo_orden = QComboBox()
        self.combo_orden.setFixedWidth(250)
        self.controls_layout.addWidget(self.combo_orden)
        
        # Botón Generar Plantilla CSV
        self.btn_generar = CustomButton("Generar Plantilla CSV", is_secondary=True, icon_name="document")
        self.btn_generar.clicked.connect(self._on_generar_plantilla)
        self.controls_layout.addWidget(self.btn_generar)
        
        self.controls_layout.addStretch()
        
        # Botón Ejecutar Migración
        self.btn_ejecutar = CustomButton("Ejecutar Migración", icon_name="settings")
        self.btn_ejecutar.clicked.connect(self._on_ejecutar_migracion)
        self.btn_ejecutar.setEnabled(self.can_edit)
        self.controls_layout.addWidget(self.btn_ejecutar)
        
        self.layout.addLayout(self.controls_layout)
        
        # Tabla resumen de la orden seleccionada
        self.lbl_table_title = CustomLabel("Resumen de Referencias en la Orden Seleccionada", variant="subheader")
        self.layout.addWidget(self.lbl_table_title)
        
        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.layout.addWidget(self.table)
        
        # Connect change event
        self.combo_orden.currentIndexChanged.connect(self._on_orden_changed)

    def refresh_data(self):
        """Loads available orders into the combo box."""
        self.combo_orden.blockSignals(True)
        self.combo_orden.clear()
        
        try:
            if self.api_client.connect_via_api:
                res = self.api_client.request("GET", "/api/admin/data/ordenes")
            else:
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
        self._on_orden_changed()

    def _on_orden_changed(self):
        """Refreshes the summary table for the selected order."""
        orden_id = self.combo_orden.currentData()
        if not orden_id:
            self.table.setRowCount(0)
            return
            
        try:
            with self.db_connector.get_session() as session:
                resumen = session.execute(text("""
                    SELECT gr.grupo_id, r.rfc, c.alias AS concepto_alias,
                           d.nombre AS delegacion_actual, d.delegacion_id,
                           COUNT(ref.referencia_id) AS total_refs
                    FROM sar_produccion.grupo_referencia gr
                    JOIN sar_catalogo.rfc r ON gr.rfc_id = r.rfc_id
                    JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
                    JOIN sar_produccion.solicitud sol ON sol.grupo_id = gr.grupo_id
                    JOIN sar_catalogo.delegacion d ON sol.delegacion_id = d.delegacion_id
                    JOIN sar_produccion.referencia ref ON ref.grupo_id = gr.grupo_id
                    WHERE gr.orden_id = :oid
                    GROUP BY gr.grupo_id, r.rfc, c.alias, d.nombre, d.delegacion_id
                    ORDER BY gr.grupo_id, d.delegacion_id
                """), {"oid": orden_id}).mappings().all()
                
                self.table.setColumnCount(5)
                self.table.setHorizontalHeaderLabels(["Grupo ID", "RFC Emisor", "Concepto", "Delegación Actual", "Referencias"])
                self.table.setRowCount(len(resumen))
                
                for idx, row in enumerate(resumen):
                    self.table.setItem(idx, 0, QTableWidgetItem(str(row['grupo_id'])))
                    self.table.setItem(idx, 1, QTableWidgetItem(row['rfc']))
                    self.table.setItem(idx, 2, QTableWidgetItem(row['concepto_alias']))
                    self.table.setItem(idx, 3, QTableWidgetItem(f"{row['delegacion_actual']} (ID: {row['delegacion_id']})"))
                    self.table.setItem(idx, 4, QTableWidgetItem(str(row['total_refs'])))
                    
                self.table.resizeColumnsToContents()
                self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        except Exception as e:
            print("Error loading order summary:", e)

    def _on_generar_plantilla(self):
        orden_id = self.combo_orden.currentData()
        if not orden_id:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Plantilla de Migración", 
            f"plantilla_migracion_orden_{orden_id}.csv", 
            "Archivos CSV (*.csv)"
        )
        
        if not file_path:
            return
            
        try:
            with self.db_connector.get_session() as session:
                refs = session.execute(text("""
                    SELECT
                        ref.referencia_portal,
                        gr.rfc_id,
                        r.rfc,
                        gr.concepto_id,
                        c.alias          AS concepto_alias,
                        sol.delegacion_id,
                        d.nombre         AS delegacion_actual,
                        ref.grupo_id,
                        sol.solicitud_id,
                        ref.consecutivo_grupo
                    FROM sar_produccion.referencia ref
                    JOIN sar_produccion.grupo_referencia gr ON ref.grupo_id    = gr.grupo_id
                    JOIN sar_produccion.solicitud sol        ON ref.solicitud_id = sol.solicitud_id
                    JOIN sar_catalogo.rfc r                  ON gr.rfc_id        = r.rfc_id
                    JOIN sar_catalogo.concepto c             ON gr.concepto_id   = c.concepto_id
                    JOIN sar_catalogo.delegacion d           ON sol.delegacion_id = d.delegacion_id
                    WHERE gr.orden_id = :oid
                    ORDER BY gr.grupo_id, ref.consecutivo_grupo
                """), {"oid": orden_id}).mappings().all()

                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'referencia_portal',
                        'rfc_id',
                        'rfc',
                        'concepto_id',
                        'concepto_alias',
                        'delegacion_id',
                        'delegacion_actual',
                        'grupo_id_ord4',
                    ])
                    for r in refs:
                        writer.writerow([
                            r['referencia_portal'],
                            r['rfc_id'],
                            r['rfc'],
                            r['concepto_id'],
                            r['concepto_alias'],
                            r['delegacion_id'],
                            r['delegacion_actual'],
                            r['grupo_id'],
                        ])
            
            QMessageBox.information(
                self, "Éxito", 
                f"Plantilla generada exitosamente con {len(refs)} referencias.\n\n"
                "Edita la columna 'delegacion_id' con la delegación correcta y luego ejecuta la migración."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar la plantilla: {e}")

    def _on_ejecutar_migracion(self):
        orden_id = self.combo_orden.currentData()
        if not orden_id:
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar CSV de Migración Modificado", "", "Archivos CSV (*.csv)"
        )
        
        if not file_path:
            return
            
        # Confirmar acción
        reply = QMessageBox.question(
            self, "Confirmar Migración",
            f"¿Está seguro de que desea migrar las referencias de la Orden seleccionada utilizando el archivo CSV?\n\n"
            "Esta operación creará una nueva Orden, moverá las referencias e intentará organizar las facturas físicas en el storage.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
            
        try:
            from sar.src.ui.design_system.components.molecules.gl_loading_dialog import GLLoadingDialog
            self.loading_dialog = GLLoadingDialog("Ejecutando proceso de migración de orden...", self)
            self.loading_dialog.show()

            self.worker = MigrationWorker(orden_id, os.path.abspath(file_path))
            self.worker.finished_signal.connect(self._on_migration_success)
            self.worker.error_signal.connect(self._on_migration_error)
            self.worker.start()
        except Exception as e:
            QMessageBox.critical(self, "Error de Migración", f"Error al iniciar la migración:\n\n{e}")

    def _on_migration_success(self):
        if hasattr(self, "loading_dialog") and self.loading_dialog:
            self.loading_dialog.accept()
            self.loading_dialog = None
        QMessageBox.information(self, "Éxito", "La migración se completó con éxito.")
        self.refresh_data()

    def _on_migration_error(self, err_msg):
        if hasattr(self, "loading_dialog") and self.loading_dialog:
            self.loading_dialog.accept()
            self.loading_dialog = None
        QMessageBox.critical(self, "Error de Migración", f"Error durante la migración:\n\n{err_msg}")
