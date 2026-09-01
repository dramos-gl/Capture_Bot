"""Bulk Upload references view."""

import os
import csv
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QComboBox
)
from PySide6.QtCore import Qt
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sqlalchemy import text

class BulkLoadView(QWidget):
    """View to download the bulk load template and trigger the references load process for a selected Order."""
    
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
        self.refresh_data()
        
    def _build_ui(self):
        # Label de descripción completa de la funcionalidad
        self.lbl_desc = CustomLabel(
            "<b>Descripción del Proceso:</b><br/>"
            "Esta herramienta permite insertar masivamente un gran volumen de referencias autorizadas externamente de forma manual a una Orden de Generación.<br/>"
            "1. <b>Selecciona</b> la orden destino sobre la cual deseas importar las referencias.<br/>"
            "2. Presiona <b>Generar Plantilla CSV</b> para descargar el formato adecuado con los RFCs y conceptos vigentes de la orden.<br/>"
            "3. Abre el archivo en Excel e introduce la información solicitada sin duplicar números de referencia.<br/>"
            "4. Presiona <b>Ejecutar Carga Masiva</b> para validar e insertar transaccionalmente todas las referencias y actualizar los acumuladores del sistema.",
            variant="body"
        )
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 12px; border-radius: 6px; color: #475569;")
        self.layout.addWidget(self.lbl_desc)

        # Top Controls Layout
        self.controls_layout = QHBoxLayout()
        
        # Selector de orden destino
        self.controls_layout.addWidget(CustomLabel("Orden Destino:", variant="body"))
        self.combo_orden = QComboBox()
        self.combo_orden.setFixedWidth(250)
        self.controls_layout.addWidget(self.combo_orden)
        
        # Botón Generar Plantilla CSV de Carga
        self.btn_generar = CustomButton("Generar Plantilla CSV", is_secondary=True, icon_name="document")
        self.btn_generar.clicked.connect(self._on_generar_plantilla)
        self.controls_layout.addWidget(self.btn_generar)
        
        self.controls_layout.addStretch()
        
        # Botón Ejecutar Carga Masiva
        self.btn_ejecutar = CustomButton("Ejecutar Carga Masiva", icon_name="settings")
        self.btn_ejecutar.clicked.connect(self._on_ejecutar_carga)
        self.btn_ejecutar.setEnabled(self.can_edit)
        self.controls_layout.addWidget(self.btn_ejecutar)
        
        self.layout.addLayout(self.controls_layout)
        
        # Tabla resumen de la orden seleccionada
        self.lbl_table_title = CustomLabel("Resumen de Cuotas/Límites de la Orden Seleccionada", variant="subheader")
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
        """Refreshes the summary table showing requested vs generated references for the selected order."""
        orden_id = self.combo_orden.currentData()
        if not orden_id:
            self.table.setRowCount(0)
            return
            
        try:
            with self.db_connector.get_session() as session:
                resumen = session.execute(text("""
                    SELECT gr.grupo_id, r.rfc, c.alias AS concepto_alias,
                           gr.cantidad_solicitada, gr.cantidad_generada, gr.cantidad_autorizada
                    FROM sar_produccion.grupo_referencia gr
                    JOIN sar_catalogo.rfc r ON gr.rfc_id = r.rfc_id
                    JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
                    WHERE gr.orden_id = :oid
                    ORDER BY gr.grupo_id
                """), {"oid": orden_id}).mappings().all()
                
                self.table.setColumnCount(5)
                self.table.setHorizontalHeaderLabels(["Grupo ID", "RFC Emisor", "Concepto", "Cantidad Solicitada", "Cantidad Cargada"])
                self.table.setRowCount(len(resumen))
                
                for idx, row in enumerate(resumen):
                    self.table.setItem(idx, 0, QTableWidgetItem(str(row['grupo_id'])))
                    self.table.setItem(idx, 1, QTableWidgetItem(row['rfc']))
                    self.table.setItem(idx, 2, QTableWidgetItem(row['concepto_alias']))
                    self.table.setItem(idx, 3, QTableWidgetItem(str(row['cantidad_solicitada'])))
                    self.table.setItem(idx, 4, QTableWidgetItem(str(row['cantidad_generada'])))
                    
                self.table.resizeColumnsToContents()
                self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        except Exception as e:
            print("Error loading order summary:", e)

    def _on_generar_plantilla(self):
        orden_id = self.combo_orden.currentData()
        if not orden_id:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Plantilla de Carga Masiva", 
            f"plantilla_carga_referencias_orden_{orden_id}.csv", 
            "Archivos CSV (*.csv)"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'rfc',
                    'concepto_alias',
                    'delegacion',
                    'referencia_portal',
                    'importe',
                    'fecha_generacion',
                    'fecha_vigencia'
                ])
                # Escribir filas de muestra basadas en los grupos existentes en la BD
                with self.db_connector.get_session() as session:
                    grupos = session.execute(text("""
                        SELECT r.rfc, c.alias AS concepto_alias, d.nombre AS delegacion
                        FROM sar_produccion.grupo_referencia gr
                        JOIN sar_catalogo.rfc r ON gr.rfc_id = r.rfc_id
                        JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
                        LEFT JOIN sar_produccion.solicitud s ON s.grupo_id = gr.grupo_id
                        LEFT JOIN sar_catalogo.delegacion d ON s.delegacion_id = d.delegacion_id
                        WHERE gr.orden_id = :oid
                    """), {"oid": orden_id}).mappings().all()
                    
                    for g in grupos:
                        writer.writerow([
                            g['rfc'],
                            g['concepto_alias'],
                            g['delegacion'] or 'CANCUN',
                            'EJEMPLO123456789',
                            '0.00',
                            datetime.now().strftime('%Y-%m-%d'),
                            ''
                        ])
            
            QMessageBox.information(
                self, "Éxito", 
                f"Plantilla generada exitosamente.\n\n"
                "Edita el archivo CSV agregando las referencias y respetando los RFCs, Conceptos y Delegaciones de la Orden."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar la plantilla: {e}")

    def _on_ejecutar_carga(self):
        orden_id = self.combo_orden.currentData()
        if not orden_id:
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar CSV de Referencias", "", "Archivos CSV (*.csv)"
        )
        
        if not file_path:
            return
            
        # Confirmar acción
        reply = QMessageBox.question(
            self, "Confirmar Carga Masiva",
            f"¿Está seguro de que desea importar las referencias a la Orden seleccionada utilizando el archivo CSV?\n\n"
            "Esta operación insertará los registros de forma transaccional y recalculará cuotas y consecutivos del sistema.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
            
        try:
            # Reutilizar el script de carga masiva en runtime
            import importlib.util
            spec = importlib.util.spec_from_file_location("cargar_script", "sar/scripts/core/cargar_referencias_masivas.py")
            cargar_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cargar_module)
            
            # Sobrescribir constantes del script
            cargar_module.ORDEN_ID = orden_id
            cargar_module.CSV_PATH = os.path.abspath(file_path)
            
            # Ejecutar main
            cargar_module.main()
            
            QMessageBox.information(self, "Éxito", "La carga masiva se completó con éxito.")
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error de Carga", f"Error durante la carga masiva:\n\n{e}")
