import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QPushButton, QTabWidget,
    QFileDialog, QDialog, QFormLayout, QLineEdit, QTextEdit, QLabel, QComboBox,
    QDateEdit, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QDate
from sar.src.ui.design_system.components import (
    CustomCard, CustomButton, StyledDataTable, FilterBar, CustomComboBox,
    LabeledComboBox, CustomLabel, CustomInput, CustomCheckBox, InteractiveGrid
)
from sar.src.ui.design_system.components.molecules.gl_stat_card import StatCard
from sar.src.ui.design_system.theme_manager import Colors
from sar.src.services.inventario_ui_service import InventarioUIService
from sar.src.services.excel_inventory_handler import ExcelInventoryHandler

class InventoryLoadWorker(QThread):
    """Background worker thread to load references from the DB dynamically with pagination."""
    result_ready = Signal(list, int, dict) # data, total_count, summary
    error_occurred = Signal(str)
    
    def __init__(self, inventario_ui_service, limit: int, offset: int, search_text: str, concepto_id: int, rfc_id: int, filter_assigned: str, start_date: str = None, end_date: str = None):
        super().__init__()
        self.inventario_ui_service = inventario_ui_service
        self.limit = limit
        self.offset = offset
        self.search_text = search_text
        self.concepto_id = concepto_id
        self.rfc_id = rfc_id
        self.filter_assigned = filter_assigned
        self.start_date = start_date
        self.end_date = end_date
        self._is_cancelled = False
        
    def cancel(self):
        self._is_cancelled = True
        
    def run(self):
        try:
            if self._is_cancelled:
                return
            res = self.inventario_ui_service.get_referencias_facturadas_paginated(
                limit=self.limit,
                offset=self.offset,
                search_text=self.search_text,
                concepto_id=self.concepto_id,
                rfc_id=self.rfc_id,
                filter_assigned=self.filter_assigned,
                start_date=self.start_date,
                end_date=self.end_date
            )
            if self._is_cancelled:
                return
            summary = self.inventario_ui_service.get_inventario_summary(
                search_text=self.search_text,
                concepto_id=self.concepto_id,
                rfc_id=self.rfc_id,
                start_date=self.start_date,
                end_date=self.end_date
            )
            if not self._is_cancelled:
                self.result_ready.emit(res["records"], res["total_count"], summary)
        except Exception as e:
            if not self._is_cancelled:
                import traceback
                traceback.print_exc()
                self.error_occurred.emit(str(e))


class AvailabilityWorker(QThread):
    """Lightweight worker to fetch disponibles count for a single grid row without blocking UI."""
    result_ready = Signal(object, int)  # row_widget, count

    def __init__(self, service, row_widget, rfc_id: int, concepto_id: int, desarrollo_id: int):
        super().__init__()
        self.service = service
        self.row_widget = row_widget
        self.rfc_id = rfc_id
        self.concepto_id = concepto_id
        self.desarrollo_id = desarrollo_id

    def run(self):
        try:
            count = self.service.get_disponibles_count(self.rfc_id, self.concepto_id, self.desarrollo_id)
            self.result_ready.emit(self.row_widget, count)
        except Exception:
            self.result_ready.emit(self.row_widget, 0)


class InventoryView(QWidget):
    """View to manage Invoice/Reference Inventory Control (state: FACTURADA)."""

    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.inventario_ui_service = InventarioUIService(self.db_connector)
        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()
        self.active_worker = None
        
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

        # 3. Tab: Apartar Referencia
        self.tab_apartar = QWidget()
        self._setup_tab_apartar()
        self.tabs.addTab(self.tab_apartar, "🔑 Apartar Referencia")

        # 4. Tab: Catálogos
        self.tab_catalogos = QWidget()
        self._setup_tab_catalogos()
        self.tabs.addTab(self.tab_catalogos, "⚙ Gestión de Catálogos")

        # Hide tab bar headers to act as a QStackedWidget
        self.tabs.tabBar().hide()

        self.main_layout.addWidget(self.tabs)
        
        # Initial data loading (load only filters at start to make tab switching instant)
        self.refresh_all(load_catalogs=False)

    def set_active_tab(self, tab_key: str):
        """Switches active widget based on sidebar submenu navigation key."""
        if tab_key == "inventario_facturas":
            self.tabs.setCurrentWidget(self.tab_visor)
        elif tab_key == "inventario_masivo":
            self.tabs.setCurrentWidget(self.tab_masivo)
        elif tab_key == "inventario_apartar":
            self.tabs.setCurrentWidget(self.tab_apartar)
        elif tab_key == "inventario_catalogos":
            self.tabs.setCurrentWidget(self.tab_catalogos)

    def refresh_all(self, load_catalogs=True):
        if load_catalogs:
            self._load_catalogs_data()
        else:
            self._load_filters_data()
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
        
        # Add Labeled Concept combo filter to filter bar
        from sar.src.ui.design_system.components.molecules.gl_labeled_combo import LabeledComboBox
        self.labeled_concept = LabeledComboBox("Concepto", ["Todos los conceptos"])
        self.cb_concept_filter = self.labeled_concept.combo
        self.cb_concept_filter.currentTextChanged.connect(self._on_concept_filter_visor)
        self.filter_bar.layout().insertWidget(self.filter_bar.layout().count() - 1, self.labeled_concept)

        # Add Labeled Empresa combo filter to filter bar
        self.labeled_empresa = LabeledComboBox("Empresa", ["Todas las empresas"])
        self.cb_empresa_filter = self.labeled_empresa.combo
        self.cb_empresa_filter.currentTextChanged.connect(self._on_empresa_filter_visor)
        self.filter_bar.layout().insertWidget(self.filter_bar.layout().count() - 1, self.labeled_empresa)
        layout.addWidget(self.filter_bar)

        # KPI summary cards
        kpi_widget = QWidget(self)
        kpi_widget.setStyleSheet("background: transparent;")
        self.kpi_layout = QHBoxLayout(kpi_widget)
        self.kpi_layout.setContentsMargins(0, 0, 0, 0)
        self.kpi_layout.setSpacing(12)
        
        self.card_total = StatCard(
            "Total Referencias",
            "0",
            icon_name="file_text",
            color_hex=Colors.ACCENT,
            show_sparkline=False,
            parent=kpi_widget
        )
        self.card_total.lbl_sub.setText("Disponibles + Asignadas")
        self.kpi_layout.addWidget(self.card_total, stretch=1)
        
        self.card_disponibles = StatCard(
            "Referencias Disponibles",
            "0",
            icon_name="clock",
            color_hex=Colors.PRIMARY,
            show_sparkline=False,
            parent=kpi_widget
        )
        self.card_disponibles.lbl_sub.setText("Total sin asignar")
        self.kpi_layout.addWidget(self.card_disponibles, stretch=1)
        
        self.card_asignadas = StatCard(
            "Referencias Asignadas",
            "0",
            icon_name="shield_check",
            color_hex=Colors.SUCCESS,
            show_sparkline=False,
            parent=kpi_widget
        )
        self.card_asignadas.lbl_sub.setText("Total asignadas")
        self.kpi_layout.addWidget(self.card_asignadas, stretch=1)
        self.kpi_layout.addStretch()
        
        layout.addWidget(kpi_widget)

        # Main Card & Table
        self.card = CustomCard(title="Referencias en Estado FACTURADA", parent=self)
        
        headers = ["✔", "ID", "Referencia", "Concepto", "Empresa", "Importe", "Estado", "Asignado A", "Tipo", "Solicitante", "Desarrollo", "Cliente", "Mz", "Lt", "Edif", "Viv", "Folio Electrónico", "Fecha Asignación"]
        self.table = StyledDataTable(headers, parent=self)
        self.table.setMinimumHeight(200)
        self.table.setMinimumWidth(200)
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

        self.btn_apartar_referencias = CustomButton("Apartar Referencias", is_secondary=True)
        self.btn_apartar_referencias.clicked.connect(self._on_apartar_referencias)

        actions_layout.addWidget(self.btn_marcar_visibles)
        actions_layout.addStretch()
        actions_layout.addWidget(self.btn_apartar_referencias)
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
        self._current_rfc_id = None
        
        self.table.itemChanged.connect(self._on_table_item_changed)
        self.table.cellDoubleClicked.connect(self._on_table_cell_double_clicked)

    def refresh_visor_data(self):
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.cancel()
            try:
                self.active_worker.result_ready.disconnect(self._on_visor_data_loaded)
            except RuntimeError:
                pass
            try:
                self.active_worker.error_occurred.disconnect(self._on_visor_load_error)
            except RuntimeError:
                pass
            self.active_worker.wait()

        self.lbl_pagination_info.setText("Cargando inventario...")
        self.pagination_widget.setEnabled(False)

        offset = (self.current_page - 1) * self.page_size
        
        self.active_worker = InventoryLoadWorker(
            inventario_ui_service=self.inventario_ui_service,
            limit=self.page_size,
            offset=offset,
            search_text=self._current_search_text,
            concepto_id=self._current_concepto_id,
            rfc_id=self._current_rfc_id,
            filter_assigned=self._current_estado_filter,
            start_date=None,
            end_date=None
        )
        self.active_worker.result_ready.connect(self._on_visor_data_loaded)
        self.active_worker.error_occurred.connect(self._on_visor_load_error)
        self.active_worker.start()

    def _on_visor_data_loaded(self, data, total_count, summary):
        self.all_data = data
        self.total_items = total_count
        self.pagination_widget.setEnabled(True)
        
        # Update cards
        disponibles = summary.get("disponibles", 0)
        asignadas = summary.get("asignadas", 0)
        total = disponibles + asignadas
        
        self.card_total.set_value(f"{total:,}")
        self.card_disponibles.set_value(f"{disponibles:,}")
        self.card_asignadas.set_value(f"{asignadas:,}")
        
        self._populate_visor_table()

    def _on_visor_load_error(self, err):
        self.pagination_widget.setEnabled(True)
        self.lbl_pagination_info.setText("Error al cargar inventario.")
        QMessageBox.critical(self, "Error de Datos", f"Fallo al conectar con el servidor:\n{err}")

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

    def _on_empresa_filter_visor(self, text):
        if text == "Todas las empresas" or not hasattr(self, '_rfcs_map'):
            self._current_rfc_id = None
        else:
            self._current_rfc_id = self._rfcs_map.get(text)
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

    def _on_table_cell_double_clicked(self, row, column):
        state_item = self.table.item(row, 6)
        if not state_item or state_item.text() != "Asignada":
            return
            
        ref_id_str = self.table.item(row, 1).text()
        if not ref_id_str:
            return
            
        ref_id = int(ref_id_str)
        lote_id = None
        for r in self.all_data:
            if r.get("referencia_id") == ref_id:
                lote_id = r.get("lote_asignacion_id")
                break
                
        if lote_id:
            dialog = LoteProcessingDialog(self.db_connector, lote_id, self)
            dialog.exec()

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
        self.form_layout_masivo = QFormLayout()
        
        self.chk_completar_reserva = CustomCheckBox("Completar Lote Apartado (Reserva)", self)
        self.chk_completar_reserva.stateChanged.connect(self._on_completar_reserva_changed)
        self.form_layout_masivo.addRow("", self.chk_completar_reserva)

        self.cb_destino_masivo = CustomComboBox(self)
        self.cb_destino_masivo.addItems(["NOTARIA", "COLABORADOR"])
        self.cb_destino_masivo.currentTextChanged.connect(self._on_destino_masivo_changed)
        self.form_layout_masivo.addRow("Tipo Destino:", self.cb_destino_masivo)

        self.cb_notarias_masivo = CustomComboBox(self)
        self.form_layout_masivo.addRow("Notaría:", self.cb_notarias_masivo)

        self.cb_colaboradores_masivo = CustomComboBox(self)
        self.form_layout_masivo.addRow("Colaborador:", self.cb_colaboradores_masivo)

        self.cb_empresa_masivo = CustomComboBox(self)
        self.form_layout_masivo.addRow("Empresa por Defecto:", self.cb_empresa_masivo)

        self.txt_solicitante_masivo = QLineEdit(self)
        self.txt_solicitante_masivo.setPlaceholderText("Ej. Pedro Gómez")
        self.form_layout_masivo.addRow("Solicitante Externo (Persona):", self.txt_solicitante_masivo)

        self.txt_obs_masivo = QTextEdit(self)
        self.txt_obs_masivo.setMaximumHeight(80)
        self.form_layout_masivo.addRow("Observaciones:", self.txt_obs_masivo)

        # File picker row
        file_layout = QHBoxLayout()
        self.lbl_excel_path = QLabel("Ningún archivo seleccionado", self)
        self.lbl_excel_path.setStyleSheet("color: #64748B; font-style: italic;")
        
        btn_pick_excel = CustomButton("Seleccionar Excel de Control", is_secondary=True)
        btn_pick_excel.clicked.connect(self._on_pick_excel_masivo)
        
        btn_download_template = CustomButton("Descargar Plantilla", is_secondary=True)
        btn_download_template.clicked.connect(self._on_download_template)
        
        file_layout.addWidget(btn_pick_excel)
        file_layout.addWidget(btn_download_template)
        file_layout.addWidget(self.lbl_excel_path)
        file_layout.addStretch()
        self.form_layout_masivo.addRow("Archivo Excel:", file_layout)

        card_form.layout.addLayout(self.form_layout_masivo)
        layout.addWidget(card_form)

        # Preview list card
        self.card_preview = CustomCard(title="Previsualización de Coincidencias y Validaciones", parent=self)
        self.preview_table = StyledDataTable(["Fila Excel", "Cliente", "Desarrollo", "Delegación", "Concepto", "Referencia", "Ubicación", "Estatus Validation"], parent=self)
        self.preview_table.setMinimumHeight(150)
        self.preview_table.setMinimumWidth(200)
        self.card_preview.add_widget(self.preview_table)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_limpiar_preview = CustomButton("Limpiar Previsualización", is_secondary=True)
        self.btn_limpiar_preview.clicked.connect(self._on_limpiar_preview)
        btn_layout.addWidget(self.btn_limpiar_preview)
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
        self.lbl_colab_row = self.form_layout_masivo.labelForField(self.cb_colaboradores_masivo)
        if self.lbl_colab_row: self.lbl_colab_row.hide()

    def _on_completar_reserva_changed(self, state):
        is_checked = (state == 2 or state == Qt.CheckState.Checked)
        if is_checked:
            self.cb_destino_masivo.setCurrentText("NOTARIA")
            self.cb_destino_masivo.setEnabled(False)
            self._on_destino_masivo_changed("NOTARIA")
            self.cb_empresa_masivo.setEnabled(False)
            self.txt_solicitante_masivo.setEnabled(False)
            self.txt_obs_masivo.setEnabled(False)
        else:
            self.cb_destino_masivo.setEnabled(True)
            self.cb_empresa_masivo.setEnabled(True)
            self.txt_solicitante_masivo.setEnabled(True)
            self.txt_obs_masivo.setEnabled(True)

    def _on_destino_masivo_changed(self, text):
        if text == "NOTARIA":
            self.cb_notarias_masivo.show()
            lbl = self.form_layout_masivo.labelForField(self.cb_notarias_masivo)
            if lbl: lbl.show()
            
            self.cb_colaboradores_masivo.hide()
            lbl_c = self.form_layout_masivo.labelForField(self.cb_colaboradores_masivo)
            if lbl_c: lbl_c.hide()
            
            self.txt_solicitante_masivo.setEnabled(True)
        else:
            self.cb_notarias_masivo.hide()
            lbl = self.form_layout_masivo.labelForField(self.cb_notarias_masivo)
            if lbl: lbl.hide()
            
            self.cb_colaboradores_masivo.show()
            lbl_c = self.form_layout_masivo.labelForField(self.cb_colaboradores_masivo)
            if lbl_c: lbl_c.show()
            
            self.txt_solicitante_masivo.setEnabled(False)
            self.txt_solicitante_masivo.clear()

    def _on_download_template(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Plantilla de Importación",
            "Plantilla_Control_Inventario.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return
        try:
            ExcelInventoryHandler.generate_blank_template(file_path)
            QMessageBox.information(self, "Plantilla Descargada", f"Se ha generado la plantilla Excel con éxito en:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar la plantilla Excel:\n{str(e)}")

    def _on_limpiar_preview(self):
        self.parsed_records = []
        self.validated_records = []
        self.lbl_excel_path.setText("Ningún archivo seleccionado")
        self.preview_table.clearContents()
        self.preview_table.setRowCount(0)
        self.btn_confirmar_masivo.setEnabled(False)
        if hasattr(self, "_excel_file_path"):
            del self._excel_file_path

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

            # Get selected default RFC/Empresa from dropdown
            default_rfc_id = None
            default_empresa_txt = self.cb_empresa_masivo.currentText()
            if default_empresa_txt != "Seleccione empresa..." and hasattr(self, "_rfcs_map"):
                default_rfc_id = self._rfcs_map.get(default_empresa_txt)

            completar_notaria_id = None
            if self.chk_completar_reserva.isChecked():
                not_name = self.cb_notarias_masivo.currentText()
                completar_notaria_id = self._notarias_map.get(not_name)
                if not completar_notaria_id:
                    QMessageBox.warning(self, "Seleccionar Notaría", "Por favor, selecciona una Notaría válida para completar su apartado.")
                    return

            # Validate rows against database
            with self.db_connector.get_session() as session:
                self.validated_records = ExcelInventoryHandler.validate_parsed_rows(
                    session, self.parsed_records, default_rfc_id=default_rfc_id, completar_notaria_id=completar_notaria_id
                )

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
            import traceback
            traceback.print_exc()
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

            if self.chk_completar_reserva.isChecked():
                if self.api_client.connect_via_api:
                    detalles_payload = []
                    for det in valid_details:
                        det_dict = {
                            "lote_detalle_id": det["lote_detalle_id"],
                            "cliente": det["cliente"],
                            "desarrollo_id": det["desarrollo_id"],
                            "concepto_solicitado": det["concepto_solicitado"],
                            "referencia_asignada": det["referencia_asignada"],
                            "referencia_id": det.get("referencia_id"),
                            "mz": det.get("mz"),
                            "lote": det.get("lote"),
                            "edif": det.get("edif"),
                            "viv": det.get("viv"),
                            "folio_electronico": det.get("folio_electronico"),
                            "estatus_primer_aviso": det.get("estatus_primer_aviso"),
                            "ubicacion": det.get("ubicacion"),
                            "credito_titular": det.get("credito_titular"),
                            "pa": det.get("pa"),
                            "delegacion": det.get("delegacion"),
                            "fecha_solicitud": det["fecha_solicitud"].strftime("%Y-%m-%d") if det.get("fecha_solicitud") and not isinstance(det.get("fecha_solicitud"), str) else det.get("fecha_solicitud")
                        }
                        detalles_payload.append(det_dict)
                    payload = {"detalles": detalles_payload}
                    self.api_client.request("POST", "/api/docs/inventario/lotes/completar", data=payload)
                else:
                    with self.db_connector.get_session() as session:
                        from sar.src.storage.repositories import InventarioRepository
                        repo = InventarioRepository(session)
                        repo.completar_reservaciones(valid_details)
                        session.commit()
                QMessageBox.information(self, "Lote Completado", f"Se han completado exitosamente {len(valid_details)} asignaciones reservadas.")
            else:
                if self.api_client.connect_via_api:
                    detalles_payload = []
                    for det in valid_details:
                        det_dict = {
                            "cliente": det["cliente"],
                            "desarrollo_id": det["desarrollo_id"],
                            "concepto_solicitado": det["concepto_solicitado"],
                            "referencia_asignada": det["referencia_asignada"],
                            "referencia_id": det.get("referencia_id"),
                            "mz": det.get("mz"),
                            "lote": det.get("lote"),
                            "edif": det.get("edif"),
                            "viv": det.get("viv"),
                            "folio_electronico": det.get("folio_electronico"),
                            "estatus_primer_aviso": det.get("estatus_primer_aviso"),
                            "ubicacion": det.get("ubicacion"),
                            "credito_titular": det.get("credito_titular"),
                            "pa": det.get("pa"),
                            "delegacion": det.get("delegacion"),
                            "fecha_solicitud": det["fecha_solicitud"].strftime("%Y-%m-%d") if det.get("fecha_solicitud") and not isinstance(det.get("fecha_solicitud"), str) else det.get("fecha_solicitud")
                        }
                        detalles_payload.append(det_dict)

                    payload = {
                        "tipo_destino": tipo_destino,
                        "notaria_id": notaria_id,
                        "colaborador_id": colaborador_id,
                        "solicitante_externo": solicitante_externo,
                        "observaciones": observaciones,
                        "usuario_creacion": usuario_id,
                        "detalles": detalles_payload
                    }
                    res = self.api_client.request("POST", "/api/docs/inventario/lotes", data=payload)
                    lote_id = res["lote_id"]
                else:
                    with self.db_connector.get_session() as session:
                        from sar.src.storage.repositories import InventarioRepository
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
        from PySide6.QtWidgets import QGridLayout
        layout = QGridLayout(self.tab_catalogos)
        layout.setSpacing(24)

        # Left Column: Notarias Catalog
        card_notarias = CustomCard(title="Catálogo de Notarías", parent=self)
        col_not_layout = QVBoxLayout()
        self.table_notarias = StyledDataTable(["ID", "Nombre Notaría"], parent=self)
        self.table_notarias.setMinimumWidth(100)
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
        layout.addWidget(card_notarias, 0, 0)

        # Middle Column: Colaboradores Catalog
        card_colabs = CustomCard(title="Catálogo de Colaboradores", parent=self)
        col_col_layout = QVBoxLayout()
        self.table_colaboradores = StyledDataTable(["ID", "Nombre Colaborador"], parent=self)
        self.table_colaboradores.setMinimumWidth(100)
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
        layout.addWidget(card_colabs, 0, 1)

        # Right Column: Desarrollos Catalog
        card_des = CustomCard(title="Catálogo de Desarrollos", parent=self)
        col_des_layout = QVBoxLayout()
        self.table_desarrollos = StyledDataTable(["ID", "Desarrollo", "Delegación"], parent=self)
        self.table_desarrollos.setMinimumWidth(100)
        col_des_layout.addWidget(self.table_desarrollos)
        
        add_des_form = QFormLayout()
        self.txt_add_desarrollo = QLineEdit(self)
        self.txt_add_desarrollo.setPlaceholderText("Nombre del Desarrollo...")
        add_des_form.addRow("Desarrollo:", self.txt_add_desarrollo)
        
        self.cb_deleg_desarrollo = CustomComboBox(self)
        add_des_form.addRow("Delegación:", self.cb_deleg_desarrollo)
        
        btn_add_desarrollo = CustomButton("Agregar Desarrollo")
        btn_add_desarrollo.clicked.connect(self._on_add_desarrollo)
        
        col_des_layout.addLayout(add_des_form)
        col_des_layout.addWidget(btn_add_desarrollo)
        card_des.layout.addLayout(col_des_layout)
        layout.addWidget(card_des, 1, 0, 1, 2)

    def _load_catalogs_data(self):
        try:
            data = self.inventario_ui_service.get_catalogos_data()
            notarias = data["notarias"]
            colaboradores = data["colaboradores"]
            desarrollos = data["desarrollos"]
            concepts_list = data["conceptos"]
            delegations_list = data["delegaciones"]
            rfcs_list = data["rfcs"]
            
            self._notarias_map = {n["nombre"]: n["notaria_id"] for n in notarias}
            self._colaboradores_map = {c["nombre"]: c["colaborador_id"] for c in colaboradores}
            self._desarrollos_map = {d["nombre"]: d["desarrollo_id"] for d in desarrollos}
            self._delegations_map = {dg["nombre"] if isinstance(dg, dict) else dg.nombre: dg["delegacion_id"] if isinstance(dg, dict) else dg.delegacion_id for dg in delegations_list}
            self._concepts_map = {cp["nombre"] if isinstance(cp, dict) else cp.nombre: cp["concepto_id"] if isinstance(cp, dict) else cp.concepto_id for cp in concepts_list}
            self._rfcs_map = {r["razon_social"] if isinstance(r, dict) else r.razon_social: r["rfc_id"] if isinstance(r, dict) else r.rfc_id for r in rfcs_list}

            # Populate combo boxes
            self.cb_notarias_masivo.clear()
            self.cb_notarias_masivo.addItems(list(self._notarias_map.keys()))

            self.cb_notarias_apartar.clear()
            self.cb_notarias_apartar.addItems(list(self._notarias_map.keys()))

            self.cb_colaboradores_masivo.clear()
            self.cb_colaboradores_masivo.addItems(list(self._colaboradores_map.keys()))

            self.cb_empresa_masivo.clear()
            self.cb_empresa_masivo.addItem("Seleccione empresa...")
            self.cb_empresa_masivo.addItems(list(self._rfcs_map.keys()))

            self.cb_deleg_desarrollo.clear()
            self.cb_deleg_desarrollo.addItems(list(self._delegations_map.keys()))

            current_concept_txt = self.cb_concept_filter.currentText()
            self.cb_concept_filter.clear()
            self.cb_concept_filter.addItem("Todos los conceptos")
            self.cb_concept_filter.addItems(list(self._concepts_map.keys()))
            if current_concept_txt in self._concepts_map:
                self.cb_concept_filter.setCurrentText(current_concept_txt)

            current_empresa_txt = self.cb_empresa_filter.currentText()
            self.cb_empresa_filter.clear()
            self.cb_empresa_filter.addItem("Todas las empresas")
            self.cb_empresa_filter.addItems(list(self._rfcs_map.keys()))
            if current_empresa_txt in self._rfcs_map:
                self.cb_empresa_filter.setCurrentText(current_empresa_txt)

            # Populate tables in Tab 3
            self.table_notarias.populate_rows([[str(n["notaria_id"]), n["nombre"]] for n in notarias])
            self.table_colaboradores.populate_rows([[str(c["colaborador_id"]), c["nombre"]] for c in colaboradores])
            
            des_rows = []
            for d in desarrollos:
                des_rows.append([
                    str(d["desarrollo_id"]),
                    d["nombre"],
                    d.get("delegacion_nombre") or d.get("delegacion", "")
                ])
            self.table_desarrollos.populate_rows(des_rows)

            # Populate grid_apartar catalogs — only AVISO (2) and CLG (3) allowed, sorted by ID
            CONCEPTOS_APARTADO = {2, 3}
            rfcs_list_tuples = [(r_id, r_name) for r_name, r_id in self._rfcs_map.items()]
            concepts_list_tuples = sorted(
                [
                    (c_id, c_name)
                    for c_name, c_id in self._concepts_map.items()
                    if c_id in CONCEPTOS_APARTADO
                ],
                key=lambda x: x[0]  # 2 (AVISO) first, then 3 (CLG)
            )
            desarrollos_list_tuples = [(d_id, d_name) for d_name, d_id in self._desarrollos_map.items()]
            self.grid_apartar.set_catalogs(rfcs_list_tuples, concepts_list_tuples, desarrollos_list_tuples)

            if not self.grid_apartar.rows:
                self.grid_apartar.add_row()

        except Exception as e:
            print("Error loading catalog data for inventory view:", e)

    def _load_filters_data(self):
        try:
            data = self.inventario_ui_service.get_filtros_data()
            concepts_list = data["conceptos"]
            rfcs_list = data["rfcs"]
            
            self._concepts_map = {cp["nombre"] if isinstance(cp, dict) else cp.nombre: cp["concepto_id"] if isinstance(cp, dict) else cp.concepto_id for cp in concepts_list}
            self._rfcs_map = {r["razon_social"] if isinstance(r, dict) else r.razon_social: r["rfc_id"] if isinstance(r, dict) else r.rfc_id for r in rfcs_list}

            # Populate filter combos in visor
            current_concept_txt = self.cb_concept_filter.currentText()
            self.cb_concept_filter.clear()
            self.cb_concept_filter.addItem("Todos los conceptos")
            self.cb_concept_filter.addItems(list(self._concepts_map.keys()))
            if current_concept_txt in self._concepts_map:
                self.cb_concept_filter.setCurrentText(current_concept_txt)

            current_empresa_txt = self.cb_empresa_filter.currentText()
            self.cb_empresa_filter.clear()
            self.cb_empresa_filter.addItem("Todas las empresas")
            self.cb_empresa_filter.addItems(list(self._rfcs_map.keys()))
            if current_empresa_txt in self._rfcs_map:
                self.cb_empresa_filter.setCurrentText(current_empresa_txt)

        except Exception as e:
            print("Error loading filter data for inventory view:", e)

    def _on_add_notaria(self):
        name = self.txt_add_notaria.text().strip()
        if not name:
            return
        try:
            self.inventario_ui_service.save_notaria(name)
            self.txt_add_notaria.clear()
            self._load_catalogs_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la notaría (podría estar duplicada):\n{str(e)}")

    def _on_add_colaborador(self):
        name = self.txt_add_colaborador.text().strip()
        if not name:
            return
        try:
            self.inventario_ui_service.save_colaborador(name)
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
            self.inventario_ui_service.save_desarrollo(name, deleg_id)
            self.txt_add_desarrollo.clear()
            self._load_catalogs_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el desarrollo:\n{str(e)}")


    def _setup_tab_apartar(self):
        layout = QVBoxLayout(self.tab_apartar)
        layout.setSpacing(16)

        card_apartar = CustomCard(parent=self)
        form_layout = QVBoxLayout()
        form_layout.setSpacing(16)

        # Build custom header for the card
        card_header_layout = QHBoxLayout()
        card_title_vbox = QVBoxLayout()
        lbl_card_title = CustomLabel("Apartar Referencias (Reserva)", variant="subheader")
        lbl_card_subtitle = CustomLabel("Completa los datos para reservar referencias para una notaría", variant="muted")
        card_title_vbox.addWidget(lbl_card_title)
        card_title_vbox.addWidget(lbl_card_subtitle)
        card_header_layout.addLayout(card_title_vbox)
        card_header_layout.addStretch()
        form_layout.addLayout(card_header_layout)

        # Two-column input layout: Notaria on the left, Observaciones on the right
        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(16)

        # Left side: Notaria
        not_layout = QVBoxLayout()
        lbl_notaria = CustomLabel("Notaría de Destino", variant="body")
        lbl_notaria.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        self.cb_notarias_apartar = CustomComboBox(self)
        self.cb_notarias_apartar.setMinimumHeight(35)
        not_layout.addWidget(lbl_notaria)
        not_layout.addWidget(self.cb_notarias_apartar)

        # Right side: Observaciones
        obs_layout = QVBoxLayout()
        lbl_obs = CustomLabel("Observaciones del Lote", variant="body")
        lbl_obs.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        self.txt_obs_apartar = CustomInput("Ingresa observaciones o descripción para el apartado...")
        self.txt_obs_apartar.setMinimumHeight(35)
        obs_layout.addWidget(lbl_obs)
        obs_layout.addWidget(self.txt_obs_apartar)

        inputs_layout.addLayout(not_layout, stretch=1)
        inputs_layout.addLayout(obs_layout, stretch=1)
        form_layout.addLayout(inputs_layout)

        # Interactive Grid
        self.grid_apartar = InteractiveGrid(self)
        self.grid_apartar.set_third_column_label("Desarrollo")
        self.grid_apartar.btn_save.setVisible(False)
        self.grid_apartar.btn_cancel.setVisible(False)
        self.grid_apartar.availability_requested.connect(self._on_availability_requested)
        form_layout.addWidget(self.grid_apartar)

        # Debounce timer and pending availability worker tracking
        from PySide6.QtCore import QTimer
        self._avail_timer = QTimer(self)
        self._avail_timer.setSingleShot(True)
        self._avail_timer.setInterval(220)  # 220ms debounce
        self._avail_pending_row = None
        self._avail_timer.timeout.connect(self._launch_availability_worker)
        self._active_avail_workers = []  # track to avoid premature GC

        # Confirm Button at the bottom
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_save_apartar = CustomButton("Confirmar Apartados")
        self.btn_save_apartar.clicked.connect(self._on_save_apartar)
        btn_layout.addWidget(self.btn_save_apartar)
        form_layout.addLayout(btn_layout)

        card_apartar.layout.addLayout(form_layout)
        layout.addWidget(card_apartar)
        
        # Wait, since _setup_tab_apartar is called during __init__, self._rfcs_map might not exist yet.
        # So we trigger it dynamically when the catalogs are loaded.

    def _on_availability_requested(self, row_widget):
        """Debounce handler: stores the pending row and restarts the 220ms timer."""
        self._avail_pending_row = row_widget
        self._avail_timer.start()  # resets if already running

    def _launch_availability_worker(self):
        """Fires the background worker after the debounce window closes."""
        row = self._avail_pending_row
        if row is None:
            return
        data = row.get_data()
        rfc_id = data.get("rfc_id")
        concepto_id = data.get("concepto_id")
        desarrollo_id = data.get("delegacion_id")
        if not rfc_id or not concepto_id or not desarrollo_id:
            return

        worker = AvailabilityWorker(
            self.inventario_ui_service, row, rfc_id, concepto_id, desarrollo_id
        )
        worker.result_ready.connect(self._on_availability_result)
        worker.finished.connect(lambda: self._active_avail_workers.remove(worker) if worker in self._active_avail_workers else None)
        self._active_avail_workers.append(worker)
        worker.start()

    def _on_availability_result(self, row_widget, count: int):
        """Called on the main thread when the worker returns a count."""
        self.grid_apartar.update_row_availability(row_widget, count)

    def _on_save_apartar(self):
        not_name = self.cb_notarias_apartar.currentText()
        notaria_id = self._notarias_map.get(not_name)
        if not notaria_id:
            QMessageBox.warning(self, "Notaría Faltante", "Por favor, seleccione una Notaría de destino.")
            return
            
        data = self.grid_apartar.get_all_data()
        if not data:
            QMessageBox.warning(self, "Validación", "Debes agregar al menos un renglón para realizar un apartado.")
            return

        # Validate that all rows have selected elements and no duplicates
        CONCEPTO_AVISO_ID = 2
        CONCEPTO_CLG_ID = 3
        seen_combinations = set()
        rows_data = []
        for i, row in enumerate(data):
            if not row["rfc_id"] or not row["concepto_id"] or not row["delegacion_id"]:
                QMessageBox.warning(self, "Validación", f"El renglón {i+1} debe tener todos los campos seleccionados (Empresa, Concepto y Desarrollo).")
                return
            if row["concepto_id"] not in (CONCEPTO_AVISO_ID, CONCEPTO_CLG_ID):
                QMessageBox.warning(self, "Validación", f"El renglón {i+1} tiene un concepto no permitido. Solo se permiten: Aviso Preventivo (2) y CLG (3).")
                return

            key = (row["rfc_id"], row["concepto_id"], row["delegacion_id"])
            if key in seen_combinations:
                QMessageBox.warning(self, "Validación", f"El renglón {i+1} tiene una combinación duplicada de Empresa, Concepto y Desarrollo.")
                return
            seen_combinations.add(key)
            
            rows_data.append({
                "rfc_id": row["rfc_id"],
                "concepto_id": row["concepto_id"],
                "desarrollo_id": row["delegacion_id"],
                "cantidad": row["cantidad"]
            })

        # Business rule: each (empresa, desarrollo) pair must include both AVISO and CLG
        pair_concepts: dict = {}  # (rfc_id, desarrollo_id) -> set of concepto_ids
        for r in rows_data:
            pair_key = (r["rfc_id"], r["desarrollo_id"])
            pair_concepts.setdefault(pair_key, set()).add(r["concepto_id"])

        missing_pairs = []
        for (rfc_id, des_id), concepts_set in pair_concepts.items():
            missing = []
            if CONCEPTO_AVISO_ID not in concepts_set:
                missing.append("Aviso Preventivo")
            if CONCEPTO_CLG_ID not in concepts_set:
                missing.append("CLG")
            if missing:
                rfc_name = self.grid_apartar.get_rfc_text(rfc_id) or f"RFC {rfc_id}"
                des_name = self.grid_apartar.get_delegacion_text(des_id) or f"Desarrollo {des_id}"
                missing_pairs.append(f"• {rfc_name} / {des_name}: falta(n) {', '.join(missing)}")

        if missing_pairs:
            detail = "\n".join(missing_pairs)
            QMessageBox.warning(
                self, "Regla de Negocio",
                f"Cada combinación de Empresa + Desarrollo debe tener un renglón de "
                f"Aviso Preventivo y uno de CLG.\n\nFaltan:\n{detail}"
            )
            return

        # Confirmation Dialog
        reply = QMessageBox.question(
            self, "Confirmar Apartado",
            f"¿Estás seguro de que deseas apartar las referencias para esta notaría?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            parent_window = self.window()
            usuario_id = getattr(parent_window, "current_usuario_id", 1)
            obs_text = self.txt_obs_apartar.text().strip()
            obs_val = obs_text if obs_text else None
            
            if self.api_client.connect_via_api:
                # API sequentially
                for row_d in rows_data:
                    payload = {
                        "notaria_id": notaria_id,
                        "rfc_id": row_d["rfc_id"],
                        "concepto_id": row_d["concepto_id"],
                        "desarrollo_id": row_d["desarrollo_id"],
                        "cantidad": row_d["cantidad"],
                        "usuario_creacion": usuario_id,
                        "observaciones": obs_val
                    }
                    self.api_client.request("POST", "/api/docs/inventario/lotes/apartar", data=payload)
            else:
                # Single session transaction
                with self.db_connector.get_session() as session:
                    from sar.src.storage.repositories import InventarioRepository
                    repo = InventarioRepository(session)
                    for row_d in rows_data:
                        repo.apartar_referencias(
                            notaria_id=notaria_id,
                            rfc_id=row_d["rfc_id"],
                            concepto_id=row_d["concepto_id"],
                            desarrollo_id=row_d["desarrollo_id"],
                            cantidad=row_d["cantidad"],
                            usuario_id=usuario_id,
                            observaciones=obs_val
                        )
                    session.commit()
                    
            total_refs = sum(row_d["cantidad"] for row_d in rows_data)
            QMessageBox.information(self, "Apartado Exitoso", f"Se han reservado exitosamente {total_refs} referencias en total en estado RESERVADA.")
            
            # Reset table, observations and reload visor
            self.txt_obs_apartar.clear()
            self.grid_apartar.clear()
            self.grid_apartar.add_row()
            self.refresh_visor_data()
        except Exception as e:
            QMessageBox.critical(self, "Error al Reservar", f"No se pudo completar el apartado de referencias:\n{str(e)}")

    def _on_apartar_referencias(self):
        # We also want to adapt ApartarReferenciasDialog to use InteractiveGrid
        dialog = ApartarReferenciasDialog(self.db_connector, self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_visor_data()


# =============================================================================
# DIALOGS
# =============================================================================
class ManualAssignmentDialog(QDialog):
    """Dialog to perform individual or bulk manual reference assignments."""
    
    def __init__(self, db_connector, ref_ids, ref_portals, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.ref_ids = ref_ids
        self.inventario_ui_service = InventarioUIService(self.db_connector)
        
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
            notarias = self.inventario_ui_service.get_notarias()
            colaboradores = self.inventario_ui_service.get_colaboradores()
            desarrollos = self.inventario_ui_service.get_desarrollos()

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
        for r_id in self.ref_ids:
            # Find the actual portal code for references
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

            self.inventario_ui_service.crear_lote_asignacion(
                tipo_destino=tipo_destino,
                notaria_id=notaria_id,
                colaborador_id=colaborador_id,
                solicitante_externo=solicitante_externo,
                observaciones=self.txt_obs.toPlainText().strip(),
                usuario_creacion=usuario_id,
                detalles_list=detalles_list
            )

            QMessageBox.information(self, "Éxito", f"Se asignaron exitosamente {len(self.ref_ids)} facturas.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error al Guardar", f"No se pudo registrar la asignación en la base de datos:\n{str(e)}")


class ExportLotesDialog(QDialog):
    """Dialog to list historical lotes and export any to Control_Inventario.xlsx format."""
    
    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.inventario_ui_service = InventarioUIService(self.db_connector)
        
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
            self.lotes = self.inventario_ui_service.get_lotes_asignacion()
                
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
            details = self.inventario_ui_service.get_lote_detalles(lote_id)

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


class LoteProcessingDialog(QDialog):
    """Dialog to show details of a lote_asignacion and export renamed PDF invoices."""
    
    def __init__(self, db_connector, lote_id: int, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.lote_id = lote_id
        self.inventario_ui_service = InventarioUIService(self.db_connector)
        
        self.setWindowTitle(f"Procesar Lote de Asignación #{lote_id}")
        self.setMinimumSize(900, 500)
        self.layout = QVBoxLayout(self)
        
        self.layout.addWidget(CustomLabel(f"Detalle de Asignación - Lote #{lote_id}", variant="subheader"))
        
        headers = ["✔", "ID Detalle", "Referencia ID", "Cliente", "Referencia", "Desarrollo", "Ubicación", "Mz", "Lt", "Edif", "Viv", "Folio Electrónico"]
        self.table_detalles = StyledDataTable(headers, parent=self)
        self.table_detalles.setColumnHidden(1, True) # Hide ID Detalle
        self.table_detalles.setColumnHidden(2, True) # Hide Referencia ID
        self.layout.addWidget(self.table_detalles)
        
        # Action Buttons
        btns = QHBoxLayout()
        btn_close = CustomButton("Cerrar", is_secondary=True)
        btn_close.clicked.connect(self.reject)
        
        btn_export = CustomButton("Exportar Facturas Renombradas")
        btn_export.clicked.connect(self._on_export_facturas)
        
        btns.addStretch()
        btns.addWidget(btn_close)
        btns.addWidget(btn_export)
        self.layout.addLayout(btns)
        
        self._load_detalles()
        
    def _load_detalles(self):
        try:
            self.detalles = self.inventario_ui_service.get_lote_detalles(self.lote_id)
            rows = []
            for d in self.detalles:
                rows.append([
                    "",
                    str(d.get("lote_detalle_id", "")),
                    str(d.get("referencia_id", "") or ""),
                    d.get("cliente", ""),
                    d.get("referencia", ""),
                    d.get("desarrollo", ""),
                    d.get("ubicacion", ""),
                    d.get("mz", ""),
                    d.get("lote", ""),
                    d.get("edif", ""),
                    d.get("viv", ""),
                    d.get("folio_electronico", "")
                ])
            self.table_detalles.populate_rows(rows, checkable_first_col=True)
            
            # Select all by default
            for r in range(self.table_detalles.rowCount()):
                chk_item = self.table_detalles.item(r, 0)
                if chk_item:
                    chk_item.setCheckState(Qt.CheckState.Checked)
        except Exception as e:
            QMessageBox.critical(self, "Error al Cargar", f"No se pudieron cargar los detalles del lote:\n{str(e)}")
            
    def _on_export_facturas(self):
        # Find which rows are checked
        selected_rows = []
        for r in range(self.table_detalles.rowCount()):
            if self.table_detalles.item(r, 0).checkState() == Qt.CheckState.Checked:
                selected_rows.append(r)
                
        if not selected_rows:
            QMessageBox.warning(self, "Selección Vacía", "Por favor selecciona al menos una referencia para exportar.")
            return
            
        dest_dir = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Destino")
        if not dest_dir:
            return
            
        import shutil
        import re
        
        def sanitize_filename(name: str) -> str:
            return re.sub(r'[^\w\s\.-]', '', name).strip()
            
        success_count = 0
        error_count = 0
        missing_count = 0
        
        for r in selected_rows:
            ref_id_str = self.table_detalles.item(r, 2).text()
            cliente_raw = self.table_detalles.item(r, 3).text()
            ref_portal = self.table_detalles.item(r, 4).text()
            
            if not ref_id_str:
                continue
                
            ref_id = int(ref_id_str)
            cliente = sanitize_filename(cliente_raw) or f"Referencia_{ref_portal}"
            
            try:
                facturas = self.inventario_ui_service.get_facturas_by_referencia_id(ref_id)
                if not facturas:
                    missing_count += 1
                    continue
                    
                # A reference can have multiple invoice records or two files (pdf_path and xml_path) per invoice record
                idx = 1
                for f in facturas:
                    paths_to_copy = []
                    if f.get("pdf_path"):
                        paths_to_copy.append(f["pdf_path"])
                    if f.get("xml_path"):
                        paths_to_copy.append(f["xml_path"])
                        
                    for src_path in paths_to_copy:
                        if src_path and os.path.exists(src_path):
                            ext = os.path.splitext(src_path)[1]
                            dest_filename = f"{cliente}_{idx}{ext}"
                            dest_path = os.path.join(dest_dir, dest_filename)
                            shutil.copy2(src_path, dest_path)
                            idx += 1
                            success_count += 1
                        else:
                            error_count += 1
            except Exception as e:
                print(f"Error copying files for ref {ref_id}:", e)
                error_count += 1
                
        # Report results
        msg = f"Exportación finalizada:\n\n- Facturas exportadas con éxito: {success_count}\n"
        if missing_count > 0:
            msg += f"- Referencias sin facturas registradas: {missing_count}\n"
        if error_count > 0:
            msg += f"- Archivos no encontrados o con error: {error_count}\n"
            
        QMessageBox.information(self, "Resultado de Exportación", msg)


class ReservaGridRow(QFrame):
    """Dynamic row item inside ApartarReferenciasDialog."""
    deleted = Signal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("reservaGridRow")
        self.setStyleSheet("QFrame#reservaGridRow { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; }")
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(8)
        
        self.cb_empresa = CustomComboBox(self)
        self.cb_empresa.setMinimumWidth(120)
        self.cb_empresa.setPlaceholderText("Empresa...")
        
        self.cb_concepto = CustomComboBox(self)
        self.cb_concepto.setMinimumWidth(120)
        self.cb_concepto.setPlaceholderText("Concepto...")
        
        self.cb_desarrollo = CustomComboBox(self)
        self.cb_desarrollo.setMinimumWidth(140)
        self.cb_desarrollo.setPlaceholderText("Desarrollo...")
        
        from PySide6.QtWidgets import QSpinBox
        self.sb_cantidad = QSpinBox(self)
        self.sb_cantidad.setRange(1, 1000)
        self.sb_cantidad.setValue(10)
        self.sb_cantidad.setStyleSheet("""
            QSpinBox {
                padding: 6px;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                min-width: 80px;
                background-color: white;
            }
        """)
        
        from sar.src.ui.design_system.utils.icons import Icons
        self.btn_delete = CustomButton("", is_secondary=True)
        self.btn_delete.setIcon(Icons.trash())
        self.btn_delete.setFixedSize(30, 30)
        self.btn_delete.setStyleSheet("border: none;")
        self.btn_delete.clicked.connect(lambda: self.deleted.emit(self))
        
        self.layout.addWidget(self.cb_empresa)
        self.layout.addWidget(self.cb_concepto)
        self.layout.addWidget(self.cb_desarrollo)
        self.layout.addWidget(self.sb_cantidad)
        self.layout.addWidget(self.btn_delete)

    def populate(self, rfcs, conceptos, desarrollos):
        self.cb_empresa.clear()
        for name, r_id in rfcs.items():
            self.cb_empresa.addItem(name, r_id)
            
        self.cb_concepto.clear()
        for name, c_id in conceptos.items():
            self.cb_concepto.addItem(name, c_id)
            
        self.cb_desarrollo.clear()
        for name, d_id in desarrollos.items():
            self.cb_desarrollo.addItem(name, d_id)
            
    def get_data(self) -> dict:
        return {
            "rfc_id": self.cb_empresa.currentData(),
            "concepto_id": self.cb_concepto.currentData(),
            "desarrollo_id": self.cb_desarrollo.currentData(),
            "cantidad": self.sb_cantidad.value()
        }


class ApartarReferenciasDialog(QDialog):
    """Dialog to pre-reserve (apartar) references for a Notary in RESERVADA state with multi-row options."""
    
    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.inventario_ui_service = InventarioUIService(self.db_connector)
        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()
        
        self.setWindowTitle("Apartar Referencias (Reserva)")
        self.setMinimumWidth(750)
        self.setMinimumHeight(450)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(12)
        
        # Notaria Selector at the top
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Notaría de Destino:", self))
        self.cb_notarias = CustomComboBox(self)
        self.cb_notarias.setMinimumWidth(250)
        top_layout.addWidget(self.cb_notarias)
        top_layout.addStretch()
        self.layout.addLayout(top_layout)
        
        # Interactive Grid
        self.grid = InteractiveGrid(self)
        self.grid.set_third_column_label("Desarrollo")
        self.grid.btn_save.setVisible(False)
        self.grid.btn_cancel.setVisible(False)
        self.layout.addWidget(self.grid)
        
        # Dialog Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cancel = CustomButton("Cancelar", is_secondary=True)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_save = CustomButton("Confirmar Apartados")
        self.btn_save.clicked.connect(self._on_save)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        self.layout.addLayout(btn_layout)
        
        self._load_catalogs()
        
    def _load_catalogs(self):
        try:
            self._catalogs_data = self.inventario_ui_service.get_catalogos_data()
            self._notarias_map = {n["nombre"]: n["notaria_id"] for n in self._catalogs_data["notarias"]}
            self._rfcs_map = {r["razon_social"] if isinstance(r, dict) else r.razon_social: r["rfc_id"] if isinstance(r, dict) else r.rfc_id for r in self._catalogs_data["rfcs"]}
            self._concepts_map = {c["nombre"] if isinstance(c, dict) else c.nombre: c["concepto_id"] if isinstance(c, dict) else c.concepto_id for c in self._catalogs_data["conceptos"]}
            self._desarrollos_map = {d["nombre"]: d["desarrollo_id"] for d in self._catalogs_data["desarrollos"]}
            
            self.cb_notarias.addItems(list(self._notarias_map.keys()))
            
            rfcs_list_tuples = [(r_id, r_name) for r_name, r_id in self._rfcs_map.items()]
            concepts_list_tuples = [(c_id, c_name) for c_name, c_id in self._concepts_map.items()]
            desarrollos_list_tuples = [(d_id, d_name) for d_name, d_id in self._desarrollos_map.items()]
            self.grid.set_catalogs(rfcs_list_tuples, concepts_list_tuples, desarrollos_list_tuples)
            self.grid.add_row()
        except Exception as e:
            print("Error loading dialog catalog data:", e)
            
    def _on_save(self):
        not_name = self.cb_notarias.currentText()
        notaria_id = self._notarias_map.get(not_name)
        if not notaria_id:
            QMessageBox.warning(self, "Notaría Faltante", "Por favor, seleccione una Notaría de destino.")
            return
            
        data = self.grid.get_all_data()
        if not data:
            QMessageBox.warning(self, "Validación", "Debes agregar al menos un renglón para realizar un apartado.")
            return

        seen_combinations = set()
        rows_data = []
        for i, row in enumerate(data):
            if not row["rfc_id"] or not row["concepto_id"] or not row["delegacion_id"]:
                QMessageBox.warning(self, "Validación", f"El renglón {i+1} debe tener todos los campos seleccionados (Empresa, Concepto y Desarrollo).")
                return
                
            key = (row["rfc_id"], row["concepto_id"], row["delegacion_id"])
            if key in seen_combinations:
                QMessageBox.warning(self, "Validación", f"El renglón {i+1} tiene una combinación duplicada de Empresa, Concepto y Desarrollo.")
                return
            seen_combinations.add(key)
            
            rows_data.append({
                "rfc_id": row["rfc_id"],
                "concepto_id": row["concepto_id"],
                "desarrollo_id": row["delegacion_id"],
                "cantidad": row["cantidad"]
            })
            
        try:
            parent_window = self.window()
            usuario_id = getattr(parent_window, "current_usuario_id", 1)
            
            if self.api_client.connect_via_api:
                # API sequentially
                for row_d in rows_data:
                    payload = {
                        "notaria_id": notaria_id,
                        "rfc_id": row_d["rfc_id"],
                        "concepto_id": row_d["concepto_id"],
                        "desarrollo_id": row_d["desarrollo_id"],
                        "cantidad": row_d["cantidad"],
                        "usuario_creacion": usuario_id
                    }
                    self.api_client.request("POST", "/api/docs/inventario/lotes/apartar", data=payload)
            else:
                # Single session transaction
                with self.db_connector.get_session() as session:
                    from sar.src.storage.repositories import InventarioRepository
                    repo = InventarioRepository(session)
                    for row_d in rows_data:
                        repo.apartar_referencias(
                            notaria_id=notaria_id,
                            rfc_id=row_d["rfc_id"],
                            concepto_id=row_d["concepto_id"],
                            desarrollo_id=row_d["desarrollo_id"],
                            cantidad=row_d["cantidad"],
                            usuario_id=usuario_id
                        )
                    session.commit()
                    
            total_refs = sum(row_d["cantidad"] for row_d in rows_data)
            QMessageBox.information(self, "Apartado Exitoso", f"Se han reservado exitosamente {total_refs} referencias en total en estado RESERVADA.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error al Reservar", f"No se pudo completar el apartado de referencias:\n{str(e)}")
