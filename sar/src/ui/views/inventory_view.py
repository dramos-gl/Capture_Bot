import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QPushButton, QTabWidget,
    QFileDialog, QDialog, QFormLayout, QLineEdit, QTextEdit, QLabel, QComboBox
)
from PySide6.QtCore import Qt, QThread, Signal
from sar.src.ui.design_system.components import (
    CustomCard, CustomButton, StyledDataTable, FilterBar, CustomComboBox,
    LabeledComboBox, CustomLabel, CustomInput, CustomCheckBox
)
from sar.src.storage.repositories import InventarioRepository
from sar.src.services.excel_inventory_handler import ExcelInventoryHandler

class InventoryLoadWorker(QThread):
    """Background worker thread to load references from the DB dynamically with pagination."""
    result_ready = Signal(list, int) # data, total_count
    error_occurred = Signal(str)
    
    def __init__(self, db_connector, limit: int, offset: int, search_text: str, concepto_id: int, filter_assigned: str):
        super().__init__()
        self.db_connector = db_connector
        self.limit = limit
        self.offset = offset
        self.search_text = search_text
        self.concepto_id = concepto_id
        self.filter_assigned = filter_assigned
        
    def run(self):
        try:
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                res, total_count = repo.get_referencias_facturadas_paginated(
                    limit=self.limit,
                    offset=self.offset,
                    search_text=self.search_text,
                    concepto_id=self.concepto_id,
                    filter_assigned=self.filter_assigned
                )
                self.result_ready.emit(res, total_count)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(str(e))


class InventoryView(QWidget):
    """View to manage Invoice/Reference Inventory Control (state: FACTURADA)."""

    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)

        # Tab Widget
        self.tabs = QTabWidget(self)
        self.tabs.setStyleSheet("""
            QTabWidget::panel {
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                background-color: #FFFFFF;
                padding: 16px;
            }
            QTabBar::tab {
                background-color: #F1F5F9;
                color: #475569;
                padding: 8px 16px;
                border: 1px solid #E2E8F0;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #FFFFFF;
                color: #2C3E50;
                border-bottom: 2px solid #2563EB;
            }
        """)

        # 1. Tab: Visor de Inventario
        self.tab_visor = QWidget()
        self._setup_tab_visor()
        self.tabs.addTab(self.tab_visor, "📋 Inventario de Facturas")

        # 2. Tab: Asignación Masiva
        self.tab_masivo = QWidget()
        self._setup_tab_masivo()
        self.tabs.addTab(self.tab_masivo, "⚡ Asignación Masiva (Excel)")

        # 3. Tab: Catálogos
        self.tab_catalogos = QWidget()
        self._setup_tab_catalogos()
        self.tabs.addTab(self.tab_catalogos, "⚙ Gestión de Catálogos")

        self.main_layout.addWidget(self.tabs)
        
        # Initial data loading
        self.refresh_all()

    def refresh_all(self):
        if self.api_client.connect_via_api:
            return
        self._load_catalogs_data()
        self.refresh_visor_data()

    # =========================================================================
    # TAB 1: VISOR DE INVENTARIO
    # =========================================================================
    def _setup_tab_visor(self):
        layout = QVBoxLayout(self.tab_visor)
        layout.setSpacing(16)

        # Filter bar
        self.filter_bar = FilterBar(
            search_placeholder="Buscar por referencia, cliente, folio...",
            state_options=["Todos", "Disponible", "Asignada"],
            on_search=self._on_search_visor,
            on_state_change=self._on_state_filter_visor,
            on_action=self.refresh_visor_data,
            action_icon_name="actualizar",
            action_tooltip="Actualizar Vista",
            parent=self
        )
        
        # Add Concept combo filter to filter bar
        self.cb_concept_filter = CustomComboBox(self)
        self.cb_concept_filter.addItems(["Todos los conceptos"])
        self.cb_concept_filter.currentTextChanged.connect(self._on_concept_filter_visor)
        self.filter_bar.layout().insertWidget(self.filter_bar.layout().count() - 1, self.cb_concept_filter)
        
        layout.addWidget(self.filter_bar)

        # Main Card & Table
        self.card = CustomCard(title="Referencias en Estado FACTURADA", parent=self)
        
        headers = ["✔", "ID", "Referencia", "Concepto", "Empresa", "Importe", "Estado", "Asignado A", "Tipo", "Solicitante", "Desarrollo", "Cliente", "Mz", "Lt", "Edif", "Viv", "Folio Electrónico", "Fecha Asignación"]
        self.table = StyledDataTable(headers, parent=self)
        self.table.setMinimumHeight(350)
        self.table.setColumnHidden(1, True) # Hide internal ID
        self.card.add_widget(self.table)

        # Paging Info and Size
        footer_layout = QHBoxLayout()
        self.lbl_pagination_info = CustomLabel("Mostrando 0 a 0 de 0 referencias", variant="muted")
        footer_layout.addWidget(self.lbl_pagination_info)
        footer_layout.addStretch()

        self.cb_page_size = CustomComboBox(self)
        self.cb_page_size.addItems(["50 por página", "100 por página", "200 por página"])
        self.cb_page_size.setCurrentIndex(2) # Default 200
        self.cb_page_size.currentTextChanged.connect(self._on_page_size_changed)
        footer_layout.addWidget(self.cb_page_size)

        self.pagination_widget = QWidget(self)
        self.pag_btn_layout = QHBoxLayout(self.pagination_widget)
        self.pag_btn_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addWidget(self.pagination_widget)
        
        self.card.layout.addLayout(footer_layout)

        # Action Buttons
        actions_layout = QHBoxLayout()
        self.btn_marcar_visibles = CustomButton("Marcar Visibles", is_secondary=True)
        self.btn_marcar_visibles.clicked.connect(self._on_marcar_visibles)
        
        self.btn_asignar_manual = CustomButton("Asignar Selección")
        self.btn_asignar_manual.clicked.connect(self._on_asignar_manual)
        
        self.btn_exportar_lotes = CustomButton("Exportar Control Inventario", is_secondary=True)
        self.btn_exportar_lotes.clicked.connect(self._on_exportar_reporte)

        actions_layout.addWidget(self.btn_marcar_visibles)
        actions_layout.addStretch()
        actions_layout.addWidget(self.btn_exportar_lotes)
        actions_layout.addWidget(self.btn_asignar_manual)
        
        self.card.layout.addLayout(actions_layout)
        layout.addWidget(self.card)

        # Pagination state
        self.current_page = 1
        self.page_size = 200
        self.all_data = []
        self.total_items = 0
        self.active_worker = None
        self._current_search_text = ""
        self._current_estado_filter = "Todos"
        self._current_concepto_id = None
        
        self.table.itemChanged.connect(self._on_table_item_changed)

    def refresh_visor_data(self):
        if self.active_worker and self.active_worker.isRunning():
            try:
                self.active_worker.result_ready.disconnect()
                self.active_worker.error_occurred.disconnect()
            except RuntimeError:
                pass
            self.active_worker.terminate()
            self.active_worker.wait()

        self.lbl_pagination_info.setText("Cargando inventario...")
        self.pagination_widget.setEnabled(False)

        offset = (self.current_page - 1) * self.page_size
        
        self.active_worker = InventoryLoadWorker(
            db_connector=self.db_connector,
            limit=self.page_size,
            offset=offset,
            search_text=self._current_search_text,
            concepto_id=self._current_concepto_id,
            filter_assigned=self._current_estado_filter
        )
        self.active_worker.result_ready.connect(self._on_visor_data_loaded)
        self.active_worker.error_occurred.connect(self._on_visor_load_error)
        self.active_worker.start()

    def _on_visor_data_loaded(self, data, total_count):
        self.all_data = data
        self.total_items = total_count
        self.pagination_widget.setEnabled(True)
        self._populate_visor_table()

    def _on_visor_load_error(self, err):
        self.pagination_widget.setEnabled(True)
        self.lbl_pagination_info.setText("Error al cargar inventario.")
        QMessageBox.critical(self, "Error de Datos", f"Fallo al conectar base de datos:\n{err}")

    def _populate_visor_table(self):
        rows_data = []
        for r in self.all_data:
            state_desc = "Asignada" if r["asignada"] else "Disponible"
            rows_data.append([
                "",
                str(r["referencia_id"]),
                r["referencia_portal"],
                r["concepto"],
                r["empresa"],
                r["importe"],
                state_desc,
                r["asignado_a"],
                r["tipo_asignacion"],
                r["solicitante_externo"],
                r["desarrollo"],
                r["cliente"],
                r["mz"],
                r["lote"],
                r["edif"],
                r["viv"],
                r["folio_electronico"],
                r["fecha_asignacion"]
            ])

        self.table.blockSignals(True)
        self.table.populate_rows(rows_data, checkable_first_col=True)
        self.table.blockSignals(False)

        # Update labels & paging buttons
        total_pages = max(1, (self.total_items + self.page_size - 1) // self.page_size)
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + len(self.all_data), self.total_items)

        self.lbl_pagination_info.setText(f"Mostrando {start_idx + 1} a {end_idx} de {self.total_items} referencias")

        # Re-draw pagination buttons
        while self.pag_btn_layout.count():
            item = self.pag_btn_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        def add_page_btn(text, target, enabled):
            btn = QPushButton(text)
            btn.setEnabled(enabled)
            btn.clicked.connect(lambda: self._set_page(target))
            self.pag_btn_layout.addWidget(btn)

        add_page_btn("<<", 1, self.current_page > 1)
        add_page_btn("<", self.current_page - 1, self.current_page > 1)
        add_page_btn(str(self.current_page), self.current_page, False)
        add_page_btn(">", self.current_page + 1, self.current_page < total_pages)
        add_page_btn(">>", total_pages, self.current_page < total_pages)

    def _set_page(self, page):
        self.current_page = page
        self.refresh_visor_data()

    def _on_search_visor(self, text):
        self._current_search_text = text
        self.current_page = 1
        self.refresh_visor_data()

    def _on_state_filter_visor(self, text):
        self._current_estado_filter = text
        self.current_page = 1
        self.refresh_visor_data()

    def _on_concept_filter_visor(self, text):
        if text == "Todos los conceptos" or not hasattr(self, '_concepts_map'):
            self._current_concepto_id = None
        else:
            self._current_concepto_id = self._concepts_map.get(text)
        self.current_page = 1
        self.refresh_visor_data()

    def _on_page_size_changed(self, text):
        if "50" in text: self.page_size = 50
        elif "100" in text: self.page_size = 100
        else: self.page_size = 200
        self.current_page = 1
        self.refresh_visor_data()

    def _on_table_item_changed(self, item):
        if item.column() == 0:
            checked = any(self.table.item(r, 0).checkState() == Qt.CheckState.Checked for r in range(self.table.rowCount()))
            self.btn_marcar_visibles.setText("Desmarcar Visibles" if checked else "Marcar Visibles")

    def _on_marcar_visibles(self):
        any_checked = any(self.table.item(r, 0).checkState() == Qt.CheckState.Checked for r in range(self.table.rowCount()))
        target = Qt.CheckState.Unchecked if any_checked else Qt.CheckState.Checked
        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            self.table.item(r, 0).setCheckState(target)
        self.table.blockSignals(False)
        self.btn_marcar_visibles.setText("Marcar Visibles" if any_checked else "Desmarcar Visibles")

    def _on_asignar_manual(self):
        # Gather selected references
        ref_ids = []
        ref_portals = []
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0).checkState() == Qt.CheckState.Checked:
                ref_ids.append(int(self.table.item(r, 1).text()))
                ref_portals.append(self.table.item(r, 2).text())
                
        if not ref_ids:
            QMessageBox.warning(self, "Selección Vacía", "Por favor, selecciona al menos una factura en la tabla para asignarla.")
            return

        # Open Custom Manual Assignment Dialog
        dialog = ManualAssignmentDialog(self.db_connector, ref_ids, ref_portals, self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_visor_data()

    def _on_exportar_reporte(self):
        lotes_dialog = ExportLotesDialog(self.db_connector, self)
        lotes_dialog.exec()

    # =========================================================================
    # TAB 2: ASIGNACIÓN MASIVA (EXCEL)
    # =========================================================================
    def _setup_tab_masivo(self):
        layout = QVBoxLayout(self.tab_masivo)
        layout.setSpacing(16)

        card_form = CustomCard(title="Configuración de la Asignación", parent=self)
        form_layout = QFormLayout()
        
        self.cb_destino_masivo = CustomComboBox(self)
        self.cb_destino_masivo.addItems(["NOTARIA", "COLABORADOR"])
        self.cb_destino_masivo.currentTextChanged.connect(self._on_destino_masivo_changed)
        form_layout.addRow("Tipo Destino:", self.cb_destino_masivo)

        self.cb_notarias_masivo = CustomComboBox(self)
        form_layout.addRow("Notaría:", self.cb_notarias_masivo)

        self.cb_colaboradores_masivo = CustomComboBox(self)
        form_layout.addRow("Colaborador:", self.cb_colaboradores_masivo)

        self.txt_solicitante_masivo = QLineEdit(self)
        self.txt_solicitante_masivo.setPlaceholderText("Ej. Pedro Gómez")
        form_layout.addRow("Solicitante Externo (Persona):", self.txt_solicitante_masivo)

        self.txt_obs_masivo = QTextEdit(self)
        self.txt_obs_masivo.setMaximumHeight(80)
        form_layout.addRow("Observaciones:", self.txt_obs_masivo)

        # File picker row
        file_layout = QHBoxLayout()
        self.lbl_excel_path = QLabel("Ningún archivo seleccionado", self)
        self.lbl_excel_path.setStyleSheet("color: #64748B; font-style: italic;")
        btn_pick_excel = CustomButton("Seleccionar Excel de Control", is_secondary=True)
        btn_pick_excel.clicked.connect(self._on_pick_excel_masivo)
        file_layout.addWidget(btn_pick_excel)
        file_layout.addWidget(self.lbl_excel_path)
        file_layout.addStretch()
        form_layout.addRow("Archivo Excel:", file_layout)

        card_form.layout.addLayout(form_layout)
        layout.addWidget(card_form)

        # Preview list card
        self.card_preview = CustomCard(title="Previsualización de Coincidencias y Validaciones", parent=self)
        self.preview_table = StyledDataTable(["Fila Excel", "Cliente", "Desarrollo", "Delegación", "Concepto", "Referencia", "Ubicación", "Estatus Validation"], parent=self)
        self.preview_table.setMinimumHeight(250)
        self.card_preview.add_widget(self.preview_table)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_confirmar_masivo = CustomButton("Confirmar e Importar Lote de Asignación")
        self.btn_confirmar_masivo.setEnabled(False)
        self.btn_confirmar_masivo.clicked.connect(self._on_confirmar_masivo)
        btn_layout.addWidget(self.btn_confirmar_masivo)
        self.card_preview.layout.addLayout(btn_layout)

        layout.addWidget(self.card_preview)

        self.parsed_records = []
        self.validated_records = []
        
        # Hide internal widgets initially
        self.cb_colaboradores_masivo.hide()
        self.lbl_colab_row = form_layout.labelForField(self.cb_colaboradores_masivo)
        if self.lbl_colab_row: self.lbl_colab_row.hide()

    def _on_destino_masivo_changed(self, text):
        if text == "NOTARIA":
            self.cb_notarias_masivo.show()
            lbl = self.cb_notarias_masivo.parentWidget().layout().labelForField(self.cb_notarias_masivo)
            if lbl: lbl.show()
            
            self.cb_colaboradores_masivo.hide()
            lbl_c = self.cb_colaboradores_masivo.parentWidget().layout().labelForField(self.cb_colaboradores_masivo)
            if lbl_c: lbl_c.hide()
            
            self.txt_solicitante_masivo.setEnabled(True)
        else:
            self.cb_notarias_masivo.hide()
            lbl = self.cb_notarias_masivo.parentWidget().layout().labelForField(self.cb_notarias_masivo)
            if lbl: lbl.hide()
            
            self.cb_colaboradores_masivo.show()
            lbl_c = self.cb_colaboradores_masivo.parentWidget().layout().labelForField(self.cb_colaboradores_masivo)
            if lbl_c: lbl_c.show()
            
            self.txt_solicitante_masivo.setEnabled(False)
            self.txt_solicitante_masivo.clear()

    def _on_pick_excel_masivo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Excel de Control", "", "Excel Files (*.xlsx)")
        if not file_path:
            return
            
        self.lbl_excel_path.setText(os.path.basename(file_path))
        self._excel_file_path = file_path

        try:
            # Parse Excel
            self.parsed_records = ExcelInventoryHandler.parse_excel_inventory(file_path)
            if not self.parsed_records:
                QMessageBox.warning(self, "Excel Vacío", "No se encontraron filas con clientes o referencias válidas en el Excel.")
                return

            # Validate rows against database
            with self.db_connector.get_session() as session:
                self.validated_records = ExcelInventoryHandler.validate_parsed_rows(session, self.parsed_records)

            # Populate preview table
            preview_rows = []
            has_errors = False
            for r in self.validated_records:
                status_txt = r["status"]
                if r["status"] == "ERROR":
                    has_errors = True
                    status_txt = f"🔴 ERROR: {r['error_message']}"
                elif r["status"] == "WARNING":
                    status_txt = f"🟡 WARNING: {r['error_message']}"
                else:
                    status_txt = "🟢 CORRECTO"

                loc_str = f"Mz {r['mz']} Lt {r['lote']}"
                if r["edif"]: loc_str += f" Edif {r['edif']}"
                if r["viv"]: loc_str += f" Viv {r['viv']}"

                preview_rows.append([
                    str(r["excel_row"]),
                    r["cliente"],
                    r["desarrollo"],
                    r["delegacion_nombre"],
                    r["concepto_solicitado"],
                    r["referencia_asignada"],
                    loc_str,
                    status_txt
                ])

            self.preview_table.populate_rows(preview_rows)
            
            self.btn_confirmar_masivo.setEnabled(len(self.validated_records) > 0)
            
            if has_errors:
                QMessageBox.warning(self, "Errores Detectados", "El Excel contiene referencias con errores (delegación incorrecta, concepto cruzado o no facturada). Se omitirán o corregirán antes de continuar.")

        except Exception as e:
            QMessageBox.critical(self, "Error de Lectura", f"Fallo al abrir o leer el Excel:\n{str(e)}")

    def _on_confirmar_masivo(self):
        tipo_destino = self.cb_destino_masivo.currentText()
        notaria_id = None
        colaborador_id = None
        
        if tipo_destino == "NOTARIA":
            not_name = self.cb_notarias_masivo.currentText()
            notaria_id = self._notarias_map.get(not_name)
            if not notaria_id:
                QMessageBox.warning(self, "Falta Selección", "Selecciona una notaría válida.")
                return
        else:
            col_name = self.cb_colaboradores_masivo.currentText()
            colaborador_id = self._colaboradores_map.get(col_name)
            if not colaborador_id:
                QMessageBox.warning(self, "Falta Selección", "Selecciona un colaborador válido.")
                return

        solicitante_externo = self.txt_solicitante_masivo.text().strip()
        if tipo_destino == "NOTARIA" and not solicitante_externo:
            QMessageBox.warning(self, "Falta Acreditación", "Ingresa el nombre del Solicitante Externo (ej. Pedro Gómez) para la Notaría.")
            return

        observaciones = self.txt_obs_masivo.toPlainText().strip()

        # Filter only correct or warned records
        valid_details = []
        errors_count = 0
        for r in self.validated_records:
            if r["status"] == "ERROR":
                errors_count += 1
                continue
            valid_details.append(r)

        if not valid_details:
            QMessageBox.critical(self, "Guardado Fallido", "No hay registros válidos para importar en el lote de asignación.")
            return

        reply = QMessageBox.question(
            self, "Confirmar Asignación",
            f"¿Estás seguro de que deseas guardar el lote de asignación?\n\n"
            f"Registros correctos: {len(valid_details)}\n"
            f"Registros con error (excluidos): {errors_count}",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        try:
            parent_window = self.window()
            usuario_id = getattr(parent_window, "current_usuario_id", 1) # Default admin

            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                lote_id = repo.crear_lote_asignacion(
                    tipo_destino=tipo_destino,
                    notaria_id=notaria_id,
                    colaborador_id=colaborador_id,
                    solicitante_externo=solicitante_externo,
                    observaciones=observaciones,
                    usuario_creacion=usuario_id,
                    detalles_list=valid_details
                )
                session.commit()

            QMessageBox.information(self, "Lote Guardado", f"Se ha registrado exitosamente el lote ID {lote_id} con {len(valid_details)} asignaciones.")
            
            # Reset values
            self.lbl_excel_path.setText("Ningún archivo seleccionado")
            self.txt_obs_masivo.clear()
            self.txt_solicitante_masivo.clear()
            self.preview_table.clearContents()
            self.preview_table.setRowCount(0)
            self.btn_confirmar_masivo.setEnabled(False)
            
            self.refresh_all()

        except Exception as e:
            QMessageBox.critical(self, "Error de Escritura", f"Fallo al guardar en la base de datos:\n{str(e)}")

    # =========================================================================
    # TAB 3: GESTIÓN DE CATALOGOS
    # =========================================================================
    def _setup_tab_catalogos(self):
        layout = QHBoxLayout(self.tab_catalogos)
        layout.setSpacing(24)

        # Left Column: Notarias Catalog
        card_notarias = CustomCard(title="Catálogo de Notarías", parent=self)
        col_not_layout = QVBoxLayout()
        self.table_notarias = StyledDataTable(["ID", "Nombre Notaría"], parent=self)
        col_not_layout.addWidget(self.table_notarias)
        
        add_not_layout = QHBoxLayout()
        self.txt_add_notaria = QLineEdit(self)
        self.txt_add_notaria.setPlaceholderText("Nombre de la Notaría...")
        btn_add_notaria = CustomButton("Agregar")
        btn_add_notaria.clicked.connect(self._on_add_notaria)
        add_not_layout.addWidget(self.txt_add_notaria)
        add_not_layout.addWidget(btn_add_notaria)
        col_not_layout.addLayout(add_not_layout)
        card_notarias.layout.addLayout(col_not_layout)
        layout.addWidget(card_notarias)

        # Middle Column: Colaboradores Catalog
        card_colabs = CustomCard(title="Catálogo de Colaboradores", parent=self)
        col_col_layout = QVBoxLayout()
        self.table_colaboradores = StyledDataTable(["ID", "Nombre Colaborador"], parent=self)
        col_col_layout.addWidget(self.table_colaboradores)
        
        add_col_layout = QHBoxLayout()
        self.txt_add_colaborador = QLineEdit(self)
        self.txt_add_colaborador.setPlaceholderText("Nombre del Colaborador...")
        btn_add_colaborador = CustomButton("Agregar")
        btn_add_colaborador.clicked.connect(self._on_add_colaborador)
        add_col_layout.addWidget(self.txt_add_colaborador)
        add_col_layout.addWidget(btn_add_colaborador)
        col_col_layout.addLayout(add_col_layout)
        card_colabs.layout.addLayout(col_col_layout)
        layout.addWidget(card_colabs)

        # Right Column: Desarrollos Catalog
        card_des = CustomCard(title="Catálogo de Desarrollos", parent=self)
        col_des_layout = QVBoxLayout()
        self.table_desarrollos = StyledDataTable(["ID", "Desarrollo", "Delegación"], parent=self)
        col_des_layout.addWidget(self.table_desarrollos)
        
        add_des_form = QFormLayout()
        self.txt_add_desarrollo = QLineEdit(self)
        self.txt_add_desarrollo.setPlaceholderText("Nombre del Desarrollo...")
        add_des_form.addRow("Desarrollo:", self.txt_add_desarrollo)
        
        self.cb_deleg_desarrollo = CustomComboBox(self)
        add_des_form.addRow("Delegación:", self.cb_deleg_desarrollo)
        
        btn_add_desarrollo = CustomButton("Agregar Desarrollo")
        col_des_layout.addLayout(add_des_form)
        col_des_layout.addWidget(btn_add_desarrollo)
        card_des.layout.addLayout(col_des_layout)
        layout.addWidget(card_des)

    def _load_catalogs_data(self):
        try:
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                notarias = repo.get_notarias()
                colaboradores = repo.get_colaboradores()
                desarrollos = repo.get_desarrollos()
                
                # Load concepts for Tab 1 Filter combobox
                from sar.src.storage.models import Concepto
                from sqlalchemy import select
                concepts = session.execute(select(Concepto).where(Concepto.activo == True)).scalars().all()
                
                # Fetch delegaciones
                from sar.src.storage.models import Delegacion
                delegations = session.execute(select(Delegacion)).scalars().all()
                
                # Store mapping dictionaries INSIDE the session to prevent detached instance access
                self._notarias_map = {n["nombre"]: n["notaria_id"] for n in notarias}
                self._colaboradores_map = {c["nombre"]: c["colaborador_id"] for c in colaboradores}
                self._desarrollos_map = {d["nombre"]: d["desarrollo_id"] for d in desarrollos}
                self._delegations_map = {dg.nombre: dg.delegacion_id for dg in delegations}
                self._concepts_map = {cp.nombre: cp.concepto_id for cp in concepts}

            # Populate combo boxes
            self.cb_notarias_masivo.clear()
            self.cb_notarias_masivo.addItems(list(self._notarias_map.keys()))

            self.cb_colaboradores_masivo.clear()
            self.cb_colaboradores_masivo.addItems(list(self._colaboradores_map.keys()))

            self.cb_deleg_desarrollo.clear()
            self.cb_deleg_desarrollo.addItems(list(self._delegations_map.keys()))

            current_concept_txt = self.cb_concept_filter.currentText()
            self.cb_concept_filter.clear()
            self.cb_concept_filter.addItem("Todos los conceptos")
            self.cb_concept_filter.addItems(list(self._concepts_map.keys()))
            if current_concept_txt in self._concepts_map:
                self.cb_concept_filter.setCurrentText(current_concept_txt)

            # Populate tables in Tab 3
            self.table_notarias.populate_rows([[str(n["notaria_id"]), n["nombre"]] for n in notarias])
            self.table_colaboradores.populate_rows([[str(c["colaborador_id"]), c["nombre"]] for c in colaboradores])
            self.table_desarrollos.populate_rows([[str(d["desarrollo_id"]), d["nombre"], d["delegacion_nombre"]] for d in desarrollos])

        except Exception as e:
            print("Error loading catalog data for inventory view:", e)

    def _on_add_notaria(self):
        name = self.txt_add_notaria.text().strip()
        if not name:
            return
        try:
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                repo.save_notaria(name)
                session.commit()
            self.txt_add_notaria.clear()
            self._load_catalogs_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la notaría (podría estar duplicada):\n{str(e)}")

    def _on_add_colaborador(self):
        name = self.txt_add_colaborador.text().strip()
        if not name:
            return
        try:
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                repo.save_colaborador(name)
                session.commit()
            self.txt_add_colaborador.clear()
            self._load_catalogs_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el colaborador:\n{str(e)}")

    def _on_add_desarrollo(self):
        name = self.txt_add_desarrollo.text().strip()
        deleg_name = self.cb_deleg_desarrollo.currentText()
        deleg_id = self._delegations_map.get(deleg_name)
        
        if not name or not deleg_id:
            return
        try:
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                repo.save_desarrollo(name, deleg_id)
                session.commit()
            self.txt_add_desarrollo.clear()
            self._load_catalogs_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el desarrollo:\n{str(e)}")


# =============================================================================
# DIALOGS
# =============================================================================
class ManualAssignmentDialog(QDialog):
    """Dialog to perform individual or bulk manual reference assignments."""
    
    def __init__(self, db_connector, ref_ids, ref_portals, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.ref_ids = ref_ids
        
        self.setWindowTitle("Asignar Factura Manualmente")
        self.setMinimumWidth(400)
        self.layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        self.lbl_info = QLabel(f"Asignando {len(ref_ids)} referencias seleccionadas.", self)
        self.lbl_info.setStyleSheet("font-weight: bold; color: #2563EB;")
        form.addRow("Info:", self.lbl_info)

        self.cb_destino = CustomComboBox(self)
        self.cb_destino.addItems(["NOTARIA", "COLABORADOR"])
        self.cb_destino.currentTextChanged.connect(self._on_destino_changed)
        form.addRow("Tipo Destino:", self.cb_destino)

        self.cb_notarias = CustomComboBox(self)
        form.addRow("Notaría:", self.cb_notarias)

        self.cb_colaboradores = CustomComboBox(self)
        form.addRow("Colaborador:", self.cb_colaboradores)

        self.txt_solicitante = QLineEdit(self)
        self.txt_solicitante.setPlaceholderText("Nombre de la persona")
        form.addRow("Solicitante Externo:", self.txt_solicitante)

        # Fields from spreadsheet coordinates
        self.txt_cliente = QLineEdit(self)
        form.addRow("Nombre del Cliente:", self.txt_cliente)

        self.cb_desarrollo = CustomComboBox(self)
        form.addRow("Desarrollo:", self.cb_desarrollo)

        self.txt_fecha_sol = QLineEdit(self)
        self.txt_fecha_sol.setPlaceholderText("AAAA-MM-DD")
        self.txt_fecha_sol.setText(datetime.now().strftime("%Y-%m-%d"))
        form.addRow("Fecha Solicitud:", self.txt_fecha_sol)

        self.txt_mz = QLineEdit(self)
        self.txt_lote = QLineEdit(self)
        self.txt_edif = QLineEdit(self)
        self.txt_viv = QLineEdit(self)
        
        loc_lay = QHBoxLayout()
        loc_lay.addWidget(QLabel("Mz:"))
        loc_lay.addWidget(self.txt_mz)
        loc_lay.addWidget(QLabel("Lt:"))
        loc_lay.addWidget(self.txt_lote)
        form.addRow("Ubicación 1:", loc_lay)

        loc_lay2 = QHBoxLayout()
        loc_lay2.addWidget(QLabel("Edif:"))
        loc_lay2.addWidget(self.txt_edif)
        loc_lay2.addWidget(QLabel("Viv:"))
        loc_lay2.addWidget(self.txt_viv)
        form.addRow("Ubicación 2:", loc_lay2)

        self.txt_folio = QLineEdit(self)
        form.addRow("Folio Electrónico:", self.txt_folio)

        self.txt_estatus_aviso = QLineEdit(self)
        self.txt_estatus_aviso.setText("NUEVO INGRESO")
        form.addRow("Estatus RPP / Aviso:", self.txt_estatus_aviso)

        self.txt_obs = QTextEdit(self)
        self.txt_obs.setMaximumHeight(80)
        form.addRow("Observaciones:", self.txt_obs)

        self.layout.addLayout(form)

        # Buttons
        btns = QHBoxLayout()
        btn_cancel = CustomButton("Cancelar", is_secondary=True)
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = CustomButton("Guardar Asignación")
        btn_save.clicked.connect(self._on_save)
        
        btns.addStretch()
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        self.layout.addLayout(btns)

        # Hide internal widgets initially
        self.cb_colaboradores.hide()
        self._load_catalogs()

    def _on_destino_changed(self, text):
        if text == "NOTARIA":
            self.cb_notarias.show()
            self.cb_colaboradores.hide()
            self.txt_solicitante.setEnabled(True)
        else:
            self.cb_notarias.hide()
            self.cb_colaboradores.show()
            self.txt_solicitante.setEnabled(False)
            self.txt_solicitante.clear()

    def _load_catalogs(self):
        try:
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                notarias = repo.get_notarias()
                colaboradores = repo.get_colaboradores()
                desarrollos = repo.get_desarrollos()

            self._notarias_map = {n["nombre"]: n["notaria_id"] for n in notarias}
            self._colaboradores_map = {c["nombre"]: c["colaborador_id"] for c in colaboradores}
            self._desarrollos_map = {d["nombre"]: d["desarrollo_id"] for d in desarrollos}

            self.cb_notarias.addItems(list(self._notarias_map.keys()))
            self.cb_colaboradores.addItems(list(self._colaboradores_map.keys()))
            self.cb_desarrollo.addItems(list(self._desarrollos_map.keys()))

        except Exception as e:
            print("Error loading catalog data for ManualAssignmentDialog:", e)

    def _on_save(self):
        tipo_destino = self.cb_destino.currentText()
        notaria_id = None
        colaborador_id = None
        
        if tipo_destino == "NOTARIA":
            not_name = self.cb_notarias.currentText()
            notaria_id = self._notarias_map.get(not_name)
        else:
            col_name = self.cb_colaboradores.currentText()
            colaborador_id = self._colaboradores_map.get(col_name)

        solicitante_externo = self.txt_solicitante.text().strip()
        cliente = self.txt_cliente.text().strip()
        des_name = self.cb_desarrollo.currentText()
        des_id = self._desarrollos_map.get(des_name)
        
        if not cliente:
            QMessageBox.warning(self, "Falta Información", "Por favor ingresa el nombre del cliente.")
            return

        if not des_id:
            QMessageBox.warning(self, "Falta Información", "Selecciona un desarrollo válido.")
            return

        fecha_sol = None
        if self.txt_fecha_sol.text().strip():
            try:
                fecha_sol = datetime.strptime(self.txt_fecha_sol.text().strip(), "%Y-%m-%d").date()
            except ValueError:
                QMessageBox.warning(self, "Formato Incorrecto", "La fecha de solicitud debe tener formato AAAA-MM-DD")
                return

        # Prepare details (same values for all selected references)
        detalles_list = []
        for r_id, r_port in zip(self.ref_ids, self.ref_ids): # We pass list of ids
            # Find the actual portal code for references
            # Wait, let's load references from table
            portal_code = ""
            for r in range(self.parent().table.rowCount()):
                if int(self.parent().table.item(r, 1).text()) == r_id:
                    portal_code = self.parent().table.item(r, 2).text()
                    break

            detalles_list.append({
                "cliente": cliente,
                "desarrollo_id": des_id,
                "fecha_solicitud": fecha_sol,
                "mz": self.txt_mz.text().strip(),
                "lote": self.txt_lote.text().strip(),
                "edif": self.txt_edif.text().strip(),
                "viv": self.txt_viv.text().strip(),
                "folio_electronico": self.txt_folio.text().strip(),
                "estatus_primer_aviso": self.txt_estatus_aviso.text().strip(),
                "concepto_solicitado": "MANUAL",
                "referencia_id": r_id,
                "referencia_asignada": portal_code
            })

        try:
            parent_window = self.parent().window()
            usuario_id = getattr(parent_window, "current_usuario_id", 1)

            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                repo.crear_lote_asignacion(
                    tipo_destino=tipo_destino,
                    notaria_id=notaria_id,
                    colaborador_id=colaborador_id,
                    solicitante_externo=solicitante_externo,
                    observaciones=self.txt_obs.toPlainText().strip(),
                    usuario_creacion=usuario_id,
                    detalles_list=detalles_list
                )
                session.commit()

            QMessageBox.information(self, "Éxito", f"Se asignaron exitosamente {len(self.ref_ids)} facturas.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error al Guardar", f"No se pudo registrar la asignación en la base de datos:\n{str(e)}")


class ExportLotesDialog(QDialog):
    """Dialog to list historical lotes and export any to Control_Inventario.xlsx format."""
    
    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        
        self.setWindowTitle("Exportar Reporte de Asignación")
        self.setMinimumSize(600, 400)
        self.layout = QVBoxLayout(self)
        
        self.layout.addWidget(CustomLabel("Historial de Lotes de Asignación", variant="subheader"))
        
        self.table_lotes = StyledDataTable(["ID Lote", "Destino", "Asignado A", "Solicitante Externo", "Fecha Creación", "Refs", "Observaciones"], parent=self)
        self.layout.addWidget(self.table_lotes)

        # Buttons
        btns = QHBoxLayout()
        btn_close = CustomButton("Cerrar", is_secondary=True)
        btn_close.clicked.connect(self.reject)
        
        btn_export = CustomButton("Exportar Lote Seleccionado")
        btn_export.clicked.connect(self._on_export)
        
        btns.addStretch()
        btns.addWidget(btn_close)
        btns.addWidget(btn_export)
        self.layout.addLayout(btns)
        
        self._load_lotes()

    def _load_lotes(self):
        try:
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                self.lotes = repo.get_lotes_asignacion()
                
            rows = []
            for l in self.lotes:
                rows.append([
                    str(l["lote_asignacion_id"]),
                    l["tipo_destino"],
                    l["asignado_a"],
                    l["solicitante_externo"],
                    l["fecha"],
                    str(l["total_referencias"]),
                    l["observaciones"]
                ])
            self.table_lotes.populate_rows(rows)
        except Exception as e:
            print("Error loading lotes in dialog:", e)

    def _on_export(self):
        selected = self.table_lotes.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selección Requerida", "Por favor selecciona un lote en la lista para exportarlo.")
            return

        row = selected[0].row()
        lote_id = int(self.table_lotes.item(row, 0).text())
        dest_name = self.table_lotes.item(row, 2).text()
        req_name = self.table_lotes.item(row, 3).text()
        date_str = self.table_lotes.item(row, 4).text()

        # Ask where to save
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Reporte de Asignación",
            f"Control_Inventario_Lote_{lote_id}.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                details = repo.get_lote_detalles(lote_id)

            # Generate Styled Excel
            title = f"ENTREGA DE DERECHOS"
            subtitle = f"DESTINO: {dest_name.upper()} {f'({req_name.upper()})' if req_name else ''}"
            
            # Simple date range calculation from details
            date_range = date_str.split()[0]
            
            ExcelInventoryHandler.generate_excel_inventory_file(
                dest_path=file_path,
                title=title,
                subtitle=subtitle,
                date_range=date_range,
                data_rows=details
            )

            QMessageBox.information(self, "Exportación Completada", f"Se ha generado y guardado el archivo Excel con éxito en:\n{file_path}")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error de Exportación", f"No se pudo generar el archivo Excel:\n{str(e)}")
