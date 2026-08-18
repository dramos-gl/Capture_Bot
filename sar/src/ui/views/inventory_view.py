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
from sar.src.ui.design_system.utils.icons import Icons

class InventoryLoadWorker(QThread):
    """Background worker thread to load references from the DB dynamically with pagination."""
    result_ready = Signal(list, int, dict) # data, total_count, summary
    error_occurred = Signal(str)
    
    def __init__(self, inventario_ui_service, limit: int, offset: int, search_text: str, concepto_id: int, rfc_id: int, filter_assigned: str, start_date: str = None, end_date: str = None, orden_ids: list = None):
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
        self.orden_ids = orden_ids
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
                end_date=self.end_date,
                orden_ids=self.orden_ids
            )
            if self._is_cancelled:
                return
            summary = self.inventario_ui_service.get_inventario_summary(
                search_text=self.search_text,
                concepto_id=self.concepto_id,
                rfc_id=self.rfc_id,
                start_date=self.start_date,
                end_date=self.end_date,
                orden_ids=self.orden_ids
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

    def __init__(self, service, row_widget, rfc_id: int, concepto_id: int, delegacion_id: int, orden_ids: list = None):
        super().__init__()
        self.service = service
        self.row_widget = row_widget
        self.rfc_id = rfc_id
        self.concepto_id = concepto_id
        self.delegacion_id = delegacion_id
        self.orden_ids = orden_ids

    def run(self):
        try:
            count = self.service.get_disponibles_count(self.rfc_id, self.concepto_id, self.delegacion_id, orden_ids=self.orden_ids)
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
        from sar.src.services.referencias_service import ReferenciasService
        self.referencias_service = ReferenciasService(self.db_connector)
        self.selected_orden_ids = []
        self.todas_las_ordenes = []
        self.is_custom_filter = False
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
        self.tabs.addTab(self.tab_visor, "📋 Inventario")

        # 2. Tab: Asignación Masiva
        self.tab_masivo = QWidget()
        self._setup_tab_masivo()
        self.tabs.addTab(self.tab_masivo, "⚡ Asignar & Validar por lotes")

        # 3. Tab: Apartar Referencia
        self.tab_apartar = QWidget()
        self._setup_tab_apartar()
        self.tabs.addTab(self.tab_apartar, "🔑 Reserva de Derechos")

        # 4. Tab: Asignación Individual
        self.tab_individual = QWidget()
        self._setup_tab_individual()
        self.tabs.addTab(self.tab_individual, "👤 Asignar Derechos")

        # 5. Tab: Gestión de Asignaciones
        self.tab_lotes = QWidget()
        self._setup_tab_lotes()
        self.tabs.addTab(self.tab_lotes, "📋 Gestión de Asignaciones")

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
        elif tab_key in ("inventario_catalogos", "inventario_individual"):
            self.tabs.setCurrentWidget(self.tab_individual)
        elif tab_key == "inventario_lotes":
            self.tabs.setCurrentWidget(self.tab_lotes)


    def refresh_all(self, load_catalogs=True):
        if load_catalogs:
            self._load_catalogs_data()
        else:
            self._load_filters_data()
        self.refresh_visor_data()
        self.refresh_lotes_data()


    # =========================================================================
    # TAB 1: VISOR DE INVENTARIO
    # =========================================================================
    def _setup_tab_visor(self):
        layout = QVBoxLayout(self.tab_visor)
        layout.setSpacing(16)

        # Filter bar
        self.filter_bar = FilterBar(
            search_placeholder="",
            state_options=["Todos", "Disponible", "Asignada", "Reservadas"],
            on_search=None,
            on_state_change=self._on_state_filter_visor,
            on_action=self.refresh_visor_data,
            action_icon_name="actualizar",
            action_tooltip="Actualizar Vista",
            parent=self
        )
        self.filter_bar.inp_search.setVisible(False)
        
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
            "Total de Derechos",
            "0",
            icon_name="file_text",
            color_hex=Colors.ACCENT,
            show_sparkline=False,
            parent=kpi_widget
        )
        self.card_total.lbl_sub.setText("Disponibles + Asignados + Reservados")
        self.kpi_layout.addWidget(self.card_total, stretch=1)
        
        self.card_disponibles = StatCard(
            "Derechos Disponibles",
            "0",
            icon_name="clock",
            color_hex=Colors.PRIMARY,
            show_sparkline=False,
            parent=kpi_widget
        )
        self.card_disponibles.lbl_sub.setText("Total sin asignar")
        self.kpi_layout.addWidget(self.card_disponibles, stretch=1)
        
        self.card_asignadas = StatCard(
            "Derechos Asignados",
            "0",
            icon_name="shield_check",
            color_hex=Colors.SUCCESS,
            show_sparkline=False,
            parent=kpi_widget
        )
        self.card_asignadas.lbl_sub.setText("Total asignados")
        self.kpi_layout.addWidget(self.card_asignadas, stretch=1)

        self.card_reservadas = StatCard(
            "Derechos Reservados",
            "0",
            icon_name="archive",
            color_hex="#F59E0B",
            show_sparkline=False,
            parent=kpi_widget
        )
        self.card_reservadas.lbl_sub.setText("Total reservados")
        self.kpi_layout.addWidget(self.card_reservadas, stretch=1)
        self.kpi_layout.addStretch()
        
        layout.addWidget(kpi_widget)

        # Main Card & Table
        self.card = CustomCard(title="", parent=self)
        
        # Table Header Layout (Title + Search + Filter)
        self.table_header_layout = QHBoxLayout()
        self.table_header_layout.setContentsMargins(0, 0, 0, 0)
        self.table_header_layout.setSpacing(12)
        
        # Section icon & label
        self.lbl_table_icon = QLabel()
        self.lbl_table_icon.setPixmap(Icons.file_text("#2563EB").pixmap(18, 18))
        self.lbl_table_icon.setStyleSheet("background: transparent;")
        
        self.lbl_table_title = CustomLabel("Referencias en Estado FACTURADA", variant="subheader")
        
        self.table_header_layout.addWidget(self.lbl_table_icon)
        self.table_header_layout.addWidget(self.lbl_table_title)
        self.table_header_layout.addStretch()
        
        # Search Box inside Table Header
        self.search_input_visor = QLineEdit(self)
        self.search_input_visor.setPlaceholderText("Buscar referencia...")
        self.search_input_visor.setFixedWidth(240)
        self.search_input_visor.addAction(Icons.search("#64748B"), QLineEdit.LeadingPosition)
        self.search_input_visor.textChanged.connect(self._on_search_visor)
        self.table_header_layout.addWidget(self.search_input_visor)
        
        # Filter Button (Funnel) inside Table Header
        self.btn_filter_orden = QPushButton()
        self.btn_filter_orden.setObjectName("secondaryBtn")
        self.btn_filter_orden.setIcon(Icons.filter_icon("#475569"))
        self.btn_filter_orden.setFixedSize(36, 36)
        self.btn_filter_orden.setToolTip("Filtrar por Órdenes")
        self.btn_filter_orden.clicked.connect(self._show_order_filter_menu)
        self.table_header_layout.addWidget(self.btn_filter_orden)
        
        self.card.layout.addLayout(self.table_header_layout)
        
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

        actions_layout.addWidget(self.btn_marcar_visibles)
        actions_layout.addStretch()
        
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

        self._load_available_orders(preserve_selection=True)
        
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
            end_date=None,
            orden_ids=list(self.selected_orden_ids) if self.selected_orden_ids else None
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
        reservadas = summary.get("reservadas", 0)
        total = disponibles + asignadas + reservadas
        
        self.card_total.set_value(f"{total:,}")
        self.card_disponibles.set_value(f"{disponibles:,}")
        self.card_asignadas.set_value(f"{asignadas:,}")
        self.card_reservadas.set_value(f"{reservadas:,}")
        
        self._populate_visor_table()

    def _on_visor_load_error(self, err):
        self.pagination_widget.setEnabled(True)
        self.lbl_pagination_info.setText("Error al cargar inventario.")
        QMessageBox.critical(self, "Error de Datos", f"Fallo al conectar con el servidor:\n{err}")

    def _populate_visor_table(self):
        rows_data = []
        for r in self.all_data:
            if r.get("estado_codigo") == "RESERVADA":
                state_desc = "Reservada"
            else:
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
        if text == "Reservadas":
            self._current_estado_filter = "Reservada"
        else:
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

    def _load_available_orders(self, preserve_selection=False):
        try:
            self.todas_las_ordenes = self.referencias_service.get_ordenes()
            if self.todas_las_ordenes:
                valid_ids = {ord["orden_id"] for ord in self.todas_las_ordenes}
                if preserve_selection and self.is_custom_filter and self.selected_orden_ids:
                    self.selected_orden_ids = [oid for oid in self.selected_orden_ids if oid in valid_ids]
                
                if not self.selected_orden_ids or (preserve_selection and not self.is_custom_filter):
                    self.selected_orden_ids = [self.todas_las_ordenes[0]["orden_id"]]
            else:
                self.selected_orden_ids = []
        except Exception as e:
            print("Error loading available orders for inventory:", e)
            self.todas_las_ordenes = []
            self.selected_orden_ids = []

    def _show_order_filter_menu(self):
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction
        
        sender_btn = self.sender()
        if not sender_btn:
            sender_btn = self.btn_filter_orden
            
        if not hasattr(self, 'todas_las_ordenes') or not self.todas_las_ordenes:
            self._load_available_orders()
            
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 8px;
                border-radius: 4px;
                color: #1E293B;
            }
            QMenu::item:selected {
                background-color: #F1F5F9;
                color: #0F172A;
            }
        """)
        
        action_all = QAction("Todas las órdenes", menu, checkable=True)
        is_all_selected = len(self.selected_orden_ids) == len(self.todas_las_ordenes) and len(self.todas_las_ordenes) > 0
        action_all.setChecked(is_all_selected)
        
        def toggle_all(checked):
            self.is_custom_filter = True
            if checked:
                self.selected_orden_ids = [ord["orden_id"] for ord in self.todas_las_ordenes]
            else:
                self.selected_orden_ids = []
            self.current_page = 1
            self.current_page_lotes = 1
            self._refresh_active_tab_data()
            
        action_all.triggered.connect(toggle_all)
        menu.addAction(action_all)
        menu.addSeparator()
        
        for ord in self.todas_las_ordenes:
            label = f"{ord['folio']} ({ord['fecha_creacion'].split()[0] if isinstance(ord['fecha_creacion'], str) else ord['fecha_creacion'].strftime('%Y-%m-%d')})"
            action = QAction(label, menu, checkable=True)
            action.setChecked(ord["orden_id"] in self.selected_orden_ids)
            
            def make_toggle_handler(oid):
                def handler(checked):
                    self.is_custom_filter = True
                    if checked:
                        if oid not in self.selected_orden_ids:
                            self.selected_orden_ids.append(oid)
                    else:
                        if oid in self.selected_orden_ids:
                            self.selected_orden_ids.remove(oid)
                    self.current_page = 1
                    self.current_page_lotes = 1
                    self._refresh_active_tab_data()
                return handler
                
            action.triggered.connect(make_toggle_handler(ord["orden_id"]))
            menu.addAction(action)
            
        menu.exec(sender_btn.mapToGlobal(sender_btn.rect().bottomLeft()))

    def _refresh_active_tab_data(self):
        active = self.tabs.currentWidget()
        if active == self.tab_visor:
            self.refresh_visor_data()
        elif active == self.tab_individual:
            self._update_all_grids_availability()
            if self._pending_ind_refs:
                self._on_buscar_referencias_ind()
        elif active == self.tab_apartar:
            self._update_all_grids_availability()
        elif active == self.tab_lotes:
            self.refresh_lotes_data()

    def _update_all_grids_availability(self):
        active = self.tabs.currentWidget()
        if active == self.tab_individual:
            for row in self.grid_individual.rows:
                self.grid_individual.availability_requested.emit(row)
        elif active == self.tab_apartar:
            for row in self.grid_apartar.rows:
                self.grid_apartar.availability_requested.emit(row)

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
        if not state_item or state_item.text() not in ("Asignada", "Reservada"):
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

        card_form = CustomCard(title="", parent=self)
        
        # Header Layout with Filter Button
        header_layout_masivo = QHBoxLayout()
        lbl_title_masivo = CustomLabel("Asignación Masiva por Lotes", variant="subheader")
        header_layout_masivo.addWidget(lbl_title_masivo)
        header_layout_masivo.addStretch()
        
        self.btn_filter_orden_masivo = QPushButton()
        self.btn_filter_orden_masivo.setObjectName("secondaryBtn")
        self.btn_filter_orden_masivo.setIcon(Icons.filter_icon("#475569"))
        self.btn_filter_orden_masivo.setFixedSize(36, 36)
        self.btn_filter_orden_masivo.setToolTip("Filtrar por Órdenes")
        self.btn_filter_orden_masivo.clicked.connect(self._show_order_filter_menu)
        header_layout_masivo.addWidget(self.btn_filter_orden_masivo)
        
        self.form_layout_masivo = QFormLayout()
        card_form.layout.addLayout(header_layout_masivo)
        card_form.layout.addLayout(self.form_layout_masivo)
        
        self.chk_completar_reserva = CustomCheckBox("Completar Lote Apartado (Reserva)", self)
        self.chk_completar_reserva.stateChanged.connect(self._on_completar_reserva_changed)
        self.form_layout_masivo.addRow("", self.chk_completar_reserva)

        self.cb_destino_masivo = CustomComboBox(self)
        self.cb_destino_masivo.addItems(["-- Seleccione un tipo de destino --", "NOTARIA", "COLABORADOR"])
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

        self.cb_notarias_masivo.hide()
        self.lbl_notaria_row = self.form_layout_masivo.labelForField(self.cb_notarias_masivo)
        if self.lbl_notaria_row: self.lbl_notaria_row.hide()

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
        elif text == "COLABORADOR":
            self.cb_notarias_masivo.hide()
            lbl = self.form_layout_masivo.labelForField(self.cb_notarias_masivo)
            if lbl: lbl.hide()
            
            self.cb_colaboradores_masivo.show()
            lbl_c = self.form_layout_masivo.labelForField(self.cb_colaboradores_masivo)
            if lbl_c: lbl_c.show()
            
            self.txt_solicitante_masivo.setEnabled(False)
            self.txt_solicitante_masivo.clear()
        else:
            # Hide both if '-- Seleccione un tipo de destino --' is selected
            self.cb_notarias_masivo.hide()
            lbl = self.form_layout_masivo.labelForField(self.cb_notarias_masivo)
            if lbl: lbl.hide()
            
            self.cb_colaboradores_masivo.hide()
            lbl_c = self.form_layout_masivo.labelForField(self.cb_colaboradores_masivo)
            if lbl_c: lbl_c.hide()
            
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
                # Group error types to show a clear diagnostic report to the QA Auditor
                error_types = set()
                for r in self.validated_records:
                    if r["status"] == "ERROR":
                        if "no existe" in r["error_message"].lower():
                            error_types.add("Referencias inexistentes en la base de datos")
                        elif "ya está asignada" in r["error_message"].lower():
                            error_types.add("Referencias ya asignadas/confirmadas previamente")
                        else:
                            error_types.add(r["error_message"])
                
                err_summary = "\n- ".join(error_types)
                QMessageBox.warning(
                    self, 
                    "Inconsistencias y Errores Detectados", 
                    f"Se identificaron los siguientes problemas en el archivo Excel:\n\n- {err_summary}\n\n"
                    "Por seguridad, estos registros marcados en ROJO se omitirán durante la importación. Puede corregirlos en el Excel y volver a validar."
                )

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
        if tipo_destino == "NOTARIA" and not self.chk_completar_reserva.isChecked() and not solicitante_externo:
            QMessageBox.warning(self, "Falta Acreditación", "Ingresa el nombre del Solicitante Externo (ej. Pedro Gómez) para la Notaría.")
            return

        observaciones = self.txt_obs_masivo.toPlainText().strip()

        # Filter only correct or warned records
        valid_details = []
        warnings_count = 0
        errors_count = 0
        warning_messages = set()
        
        for r in self.validated_records:
            if r["status"] == "ERROR":
                errors_count += 1
                continue
            if r["status"] == "WARNING":
                warnings_count += 1
                if "ya tiene una asignación" in r["error_message"].lower():
                    warning_messages.add("Duplicación de ubicación (se incrementará el número de 'Intento' consecutivamente)")
                else:
                    warning_messages.add(r["error_message"])
            valid_details.append(r)

        if not valid_details:
            QMessageBox.critical(self, "Guardado Fallido", "No hay registros válidos para importar en el lote de asignación.")
            return

        # Prepare a highly detailed and professional QA confirmation prompt
        prompt_msg = (
            f"¿Estás seguro de que deseas guardar y confirmar este lote de asignación?\n\n"
            f"📊 Resumen de registros:\n"
            f"  • Listos para procesar (Reservadas/Asignadas): {len(valid_details) - warnings_count}\n"
            f"  • Registros con advertencias (Ubicación duplicada): {warnings_count}\n"
            f"  • Registros con error crítico (Omitidos): {errors_count}\n\n"
        )
        if warning_messages:
            prompt_msg += "⚠️ ADVERTENCIAS IMPORTANTES:\n- " + "\n- ".join(warning_messages) + "\n\n"
        
        if errors_count > 0:
            prompt_msg += "Nota: Los registros marcados con error crítico no se guardarán en la base de datos.\n\n"

        reply = QMessageBox.question(
            self, "Confirmar Importación de Lote",
            prompt_msg,
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
                    payload = {
                        "detalles": detalles_payload,
                        "usuario_id": usuario_id
                    }
                    self.api_client.request("POST", "/api/docs/inventario/lotes/completar", data=payload)
                else:
                    with self.db_connector.get_session() as session:
                        from sar.src.storage.repositories import InventarioRepository
                        repo = InventarioRepository(session)
                        repo.completar_reservaciones(valid_details, usuario_id=usuario_id)
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
    def _setup_tab_individual(self):
        layout = QVBoxLayout(self.tab_individual)
        layout.setSpacing(16)

        card_ind = CustomCard(parent=self)
        form_layout = QVBoxLayout()
        form_layout.setSpacing(16)

        # Header with Filter Button
        card_header_layout = QHBoxLayout()
        card_title_vbox = QVBoxLayout()
        lbl_card_title = CustomLabel("Asignación de Derechos Directa", variant="subheader")
        card_title_vbox.addWidget(lbl_card_title)
        card_header_layout.addLayout(card_title_vbox)
        card_header_layout.addStretch()
        
        self.btn_filter_orden_ind = QPushButton()
        self.btn_filter_orden_ind.setObjectName("secondaryBtn")
        self.btn_filter_orden_ind.setIcon(Icons.filter_icon("#475569"))
        self.btn_filter_orden_ind.setFixedSize(36, 36)
        self.btn_filter_orden_ind.setToolTip("Filtrar por Órdenes")
        self.btn_filter_orden_ind.clicked.connect(self._show_order_filter_menu)
        card_header_layout.addWidget(self.btn_filter_orden_ind)
        
        form_layout.addLayout(card_header_layout)


        # Destino Selectors
        dest_layout = QHBoxLayout()
        dest_layout.setSpacing(16)

        vbox_tipo = QVBoxLayout()
        lbl_tipo = CustomLabel("Tipo de Destino", variant="body")
        lbl_tipo.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        self.cb_tipo_destino_ind = CustomComboBox(self)
        self.cb_tipo_destino_ind.addItem("-- Seleccione Destino --", None)
        self.cb_tipo_destino_ind.addItems(["NOTARIA", "COLABORADOR"])
        self.cb_tipo_destino_ind.setCurrentIndex(0)
        self.cb_tipo_destino_ind.currentTextChanged.connect(self._on_tipo_destino_ind_changed)
        vbox_tipo.addWidget(lbl_tipo)
        vbox_tipo.addWidget(self.cb_tipo_destino_ind)


        vbox_dest = QVBoxLayout()
        lbl_dest = CustomLabel("Destinatario", variant="body")
        lbl_dest.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        self.cb_destinatario_ind = CustomComboBox(self)
        vbox_dest.addWidget(lbl_dest)
        vbox_dest.addWidget(self.cb_destinatario_ind)

        dest_layout.addLayout(vbox_tipo, stretch=1)
        dest_layout.addLayout(vbox_dest, stretch=1)
        form_layout.addLayout(dest_layout)
        
        # Interactive Grid for filters and counts
        self.grid_individual = InteractiveGrid(self)
        self.grid_individual.setMinimumHeight(180)
        self.grid_individual.set_third_column_label("Delegación")
        self.grid_individual.btn_save.setVisible(False)
        self.grid_individual.btn_cancel.setVisible(False)
        
        # Connect availability and cascade signals for individual grid
        self.grid_individual.availability_requested.connect(self._on_availability_requested_ind)
        self.grid_individual.cascade_rfcs_needed.connect(self._on_cascade_rfcs_needed)
        self.grid_individual.cascade_delegaciones_needed.connect(self._on_cascade_delegaciones_needed)
        self.grid_individual.cascade_conceptos_needed.connect(self._on_cascade_conceptos_needed)

        # Create aligned action buttons to go in the header alongside + Agregar Renglón

        self.btn_buscar_ind = QPushButton("Buscar Referencias")
        self.btn_buscar_ind.setObjectName("primaryBtn")
        self.btn_buscar_ind.setMinimumHeight(35)
        self.btn_buscar_ind.setIcon(Icons.get_icon("buscar", color="#FFFFFF"))
        self.btn_buscar_ind.clicked.connect(self._on_buscar_referencias_ind)

        self.btn_confirmar_ind = QPushButton("Continuar Asignación")
        self.btn_confirmar_ind.setObjectName("primaryBtn")
        self.btn_confirmar_ind.setMinimumHeight(35)
        self.btn_confirmar_ind.setIcon(Icons.get_icon("siguiente", color="#FFFFFF"))
        self.btn_confirmar_ind.setEnabled(False)
        self.btn_confirmar_ind.clicked.connect(self._on_confirmar_asignacion_ind)

        self.btn_limpiar_ind = QPushButton("Limpiar")
        self.btn_limpiar_ind.setObjectName("secondaryBtn")
        self.btn_limpiar_ind.setMinimumHeight(35)
        self.btn_limpiar_ind.setIcon(Icons.get_icon("limpiar", color="#475569"))
        self.btn_limpiar_ind.clicked.connect(self._on_limpiar_ind)


        # Inject into the InteractiveGrid header layout (before stretch, so they align right next to btn_add)
        self.grid_individual.header_layout.addWidget(self.btn_buscar_ind)
        self.grid_individual.header_layout.addWidget(self.btn_confirmar_ind)
        self.grid_individual.header_layout.addWidget(self.btn_limpiar_ind)

        form_layout.addWidget(self.grid_individual)

        card_ind.layout.addLayout(form_layout)
        layout.addWidget(card_ind)

        # Preview list table
        self.card_preview_ind = CustomCard(title="Referencias Disponibles a Asignar", parent=self)
        self.table_preview_ind = StyledDataTable(["✔", "ID", "Referencia (Portal)", "Concepto", "Empresa", "Importe", "Delegación"], parent=self)
        self.table_preview_ind.setMinimumHeight(240)
        self.table_preview_ind.setColumnHidden(1, True) # Hide internal ID
        self.card_preview_ind.add_widget(self.table_preview_ind)
        layout.addWidget(self.card_preview_ind)

        self._pending_ind_refs = []

    def _on_limpiar_ind(self):
        """Clears individual grid rows, destination selections and preview list data."""
        self.grid_individual.clear()
        self.grid_individual.add_row()
        self.table_preview_ind.clearContents()
        self.table_preview_ind.setRowCount(0)
        self._pending_ind_refs = []
        self.btn_confirmar_ind.setEnabled(False)
        self.cb_tipo_destino_ind.setCurrentIndex(0)
        self.cb_destinatario_ind.clear()

    def _on_tipo_destino_ind_changed(self, text):

        self.cb_destinatario_ind.clear()
        if not text or text == "-- Seleccione Destino --":
            self.grid_individual.clear()
            self.grid_individual.set_cascade_mode(False)
            return

        if text == "NOTARIA" and hasattr(self, "_notarias_map"):
            self.cb_destinatario_ind.addItem("-- Seleccione Destinatario --", None)
            self.cb_destinatario_ind.addItems(list(self._notarias_map.keys()))
            self.cb_destinatario_ind.setCurrentIndex(0)
            # NOTARIA: Enable cascade mode (Desarrollo -> RFC -> Delegación -> Concepto)
            if hasattr(self, "_cascade_desarrollos_entries"):
                self.grid_individual.set_cascade_mode(True, self._cascade_desarrollos_entries)
        else:
            if hasattr(self, "_colaboradores_map"):
                self.cb_destinatario_ind.addItem("-- Seleccione Destinatario --", None)
                self.cb_destinatario_ind.addItems(list(self._colaboradores_map.keys()))
                self.cb_destinatario_ind.setCurrentIndex(0)

            # COLABORADOR: Disable cascade mode (independent combos, but Desarrollo remains visible and optional)
            self.grid_individual.set_cascade_mode(False)
            self.grid_individual.set_has_desarrollo(True)
            # Pre-load only RFCs that actually have 'FACTURADA' stock
            try:
                rfcs_con_stock = self.inventario_ui_service.get_rfcs_con_stock_facturadas()
                rfcs_tuples = [(r["rfc_id"], r["razon_social"]) for r in rfcs_con_stock]
                
                concepts_all_tuples = sorted(
                    [(c_id, c_name) for c_name, c_id in self._concepts_map.items()],
                    key=lambda x: x[0]
                )
                delegations_list_tuples = [
                    (dg_id, dg_name) for dg_name, dg_id in self._delegations_map.items()
                ]
                
                # Fetch desarrollos catalog for the optional combo
                desarrollos_tuples = sorted(
                    [
                        (
                            d["desarrollo_id"],
                            d["nombre"],
                            d.get("delegacion_id"),
                            d.get("es_default", False),
                        )
                        for d in self.inventario_ui_service.get_desarrollos()
                    ],
                    key=lambda x: (not x[3], x[1])
                )
                
                self.grid_individual.set_catalogs(rfcs_tuples, concepts_all_tuples, delegations_list_tuples, desarrollos_tuples)
            except Exception as e:
                print("Error loading active stock RFCs for individual grid:", e)


        # Clear and add a clean row to match the new mode
        self.grid_individual.clear()
        self.grid_individual.add_row()



    def _on_availability_requested_ind(self, row_widget):
        self._avail_pending_row = row_widget
        self._avail_timer.start()

    def _on_buscar_referencias_ind(self):
        tipo_destino = self.cb_tipo_destino_ind.currentText()
        if not tipo_destino or tipo_destino == "-- Seleccione Destino --":
            QMessageBox.warning(self, "Destino Requerido", "Debe seleccionar primero un Tipo de Destino válido.")
            return

        grid_data = self.grid_individual.get_all_data()

        if not grid_data:
            QMessageBox.warning(self, "Grilla Vacía", "Por favor, agregue al menos una partida para buscar.")
            return

        for i, row in enumerate(grid_data):
            # If in cascade mode (NOTARIA), rfc, concepto, and delegacion are required.
            # In non-cascade mode (COLABORADOR), desarrollo is hidden but rfc, concepto and delegacion are still required.
            if not row.get("rfc_id") or not row.get("concepto_id") or not row.get("delegacion_id"):
                QMessageBox.warning(self, "Validación", f"El renglón {i+1} debe tener Empresa, Concepto y Delegación seleccionados.")
                return


        self._pending_ind_refs = []
        try:
            for row in grid_data:
                refs = self.inventario_ui_service.get_referencias_disponibles_filtro(
                    row["rfc_id"], row["concepto_id"], row["delegacion_id"], row["cantidad"],
                    orden_ids=list(self.selected_orden_ids) if self.selected_orden_ids else None
                )
                for r in refs:
                    r["desarrollo_id"] = None
                    r["delegacion_id"] = row["delegacion_id"]
                    r["delegacion_nombre"] = self.grid_individual.get_delegacion_text(row["delegacion_id"]) or "Delegación"
                    self._pending_ind_refs.append(r)
            
            table_rows = []
            for item in self._pending_ind_refs:
                table_rows.append([
                    "",  # checked column
                    str(item["referencia_id"]),
                    item["referencia_portal"],
                    item.get("concepto_nombre", ""),
                    item.get("empresa_nombre", ""),
                    f"${float(item['importe']):,.2f}" if item.get("importe") else "$0.00",
                    item["delegacion_nombre"]
                ])
            
            self.table_preview_ind.blockSignals(True)
            self.table_preview_ind.populate_rows(table_rows, checkable_first_col=True)
            for r in range(self.table_preview_ind.rowCount()):
                self.table_preview_ind.item(r, 0).setCheckState(Qt.CheckState.Checked)
            self.table_preview_ind.blockSignals(False)

            self.btn_confirmar_ind.setEnabled(len(self._pending_ind_refs) > 0)
            if not self._pending_ind_refs:
                QMessageBox.information(self, "Sin Coincidencias", "No se encontraron referencias físicas FACTURADAS disponibles con los filtros especificados.")
        except Exception as e:
            QMessageBox.critical(self, "Error al Consultar", f"Ocurrió un error al buscar referencias en la BD:\n{str(e)}")

    def _on_confirmar_asignacion_ind(self):
        selected_refs = []
        for r in range(self.table_preview_ind.rowCount()):
            if self.table_preview_ind.item(r, 0).checkState() == Qt.CheckState.Checked:
                ref_id = int(self.table_preview_ind.item(r, 1).text())
                for item in self._pending_ind_refs:
                    if item["referencia_id"] == ref_id:
                        selected_refs.append(item)
                        break

        if not selected_refs:
            QMessageBox.warning(self, "Selección Vacía", "Por favor, seleccione al menos una referencia de la lista para asignar.")
            return

        tipo_destino = self.cb_tipo_destino_ind.currentText()
        if not tipo_destino or tipo_destino == "-- Seleccione Destino --":
            QMessageBox.warning(self, "Destino Requerido", "Por favor, seleccione un tipo de destino válido.")
            return

        dest_name = self.cb_destinatario_ind.currentText()
        if not dest_name or dest_name == "-- Seleccione Destinatario --":
            QMessageBox.warning(self, "Destinatario Requerido", "Por favor, seleccione un destinatario de la lista.")
            return

        if tipo_destino == "NOTARIA":
            destino_id = self._notarias_map.get(dest_name)
        elif tipo_destino == "COLABORADOR":
            destino_id = self._colaboradores_map.get(dest_name)
        else:
            destino_id = None


        if not destino_id:
            QMessageBox.warning(self, "Destino Inválido", "Por favor, seleccione un destinatario válido.")
            return

        ref_ids = [r["referencia_id"] for r in selected_refs]
        ref_portals = [r["referencia_portal"] for r in selected_refs]
        
        # Instantiate ManualAssignmentDialog to capture all details, passing selected_refs to maintain referential integrity of developments
        dialog = ManualAssignmentDialog(self.db_connector, ref_ids, ref_portals, parent=self, selected_refs=selected_refs)

        
        # Prepopulate the selected destination type and value in the dialog
        idx_dest_type = dialog.cb_destino.findText(tipo_destino)
        if idx_dest_type >= 0:
            dialog.cb_destino.setCurrentIndex(idx_dest_type)
        dialog._on_destino_changed(tipo_destino)
        
        if tipo_destino == "NOTARIA":
            idx_not = dialog.cb_notarias.findText(dest_name)
            if idx_not >= 0:
                dialog.cb_notarias.setCurrentIndex(idx_not)
        else:
            idx_col = dialog.cb_colaboradores.findText(dest_name)
            if idx_col >= 0:
                dialog.cb_colaboradores.setCurrentIndex(idx_col)

        # Execute Dialog
        if dialog.exec() == QDialog.Accepted:
            self.table_preview_ind.clearContents()
            self.table_preview_ind.setRowCount(0)
            self.grid_individual.clear()
            self.grid_individual.add_row()
            self.btn_confirmar_ind.setEnabled(False)
            self.refresh_all()

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

            # Populate Notaría combos — insert explicit placeholder so no record is auto-selected
            self.cb_notarias_masivo.clear()
            self.cb_notarias_masivo.addItem("-- Seleccione una notaría --")
            self.cb_notarias_masivo.addItems(list(self._notarias_map.keys()))
            self.cb_notarias_masivo.setCurrentIndex(0)

            self.cb_notarias_apartar.clear()
            self.cb_notarias_apartar.addItem("-- Seleccione una notaría --")
            for nombre in self._notarias_map:
                self.cb_notarias_apartar.addItem(nombre)
            self.cb_notarias_apartar.setCurrentIndex(0)  # keep placeholder selected

            self.cb_colaboradores_masivo.clear()
            self.cb_colaboradores_masivo.addItem("-- Seleccione un colaborador --")
            self.cb_colaboradores_masivo.addItems(list(self._colaboradores_map.keys()))
            self.cb_colaboradores_masivo.setCurrentIndex(0)

            self.cb_empresa_masivo.clear()
            self.cb_empresa_masivo.addItem("-- Seleccione empresa --")
            self.cb_empresa_masivo.addItems(list(self._rfcs_map.keys()))
            self.cb_empresa_masivo.setCurrentIndex(0)

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





            # Populate tables in Tab 3 — only ACTIVE delegations
            delegations_list_tuples = [
                (
                    d["delegacion_id"] if isinstance(d, dict) else d.delegacion_id,
                    d["nombre"] if isinstance(d, dict) else d.nombre
                )
                for d in delegations_list
                if (d.get("activo", True) if isinstance(d, dict) else getattr(d, "activo", True))
            ]

            # Populate grid_apartar in CASCADE MODE using desarrollos_empresa data
            desarrollos_activos_para_apartar = self.inventario_ui_service.get_desarrollos_activos_para_apartar()
            self._cascade_desarrollos_entries = desarrollos_activos_para_apartar  # cache for new rows
            self.grid_apartar.set_has_desarrollo(True)
            self.grid_apartar.set_cascade_mode(True, desarrollos_activos_para_apartar)
            if not self.grid_apartar.rows:
                self.grid_apartar.add_row()

            # Populate grid_individual by default in CASCADE MODE to match Apartar
            self.grid_individual.set_has_desarrollo(True)
            self.grid_individual.set_cascade_mode(True, desarrollos_activos_para_apartar)
            if not self.grid_individual.rows:
                self.grid_individual.add_row()


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

        # Build custom header for the card with Filter Button
        card_header_layout = QHBoxLayout()
        card_title_vbox = QVBoxLayout()
        lbl_card_title = CustomLabel("Reserva de Derechos (Apartados)", variant="subheader")
        lbl_card_subtitle = CustomLabel("Completa los datos para reservar derechos para una notaría", variant="muted")
        card_title_vbox.addWidget(lbl_card_title)
        card_title_vbox.addWidget(lbl_card_subtitle)
        card_header_layout.addLayout(card_title_vbox)
        card_header_layout.addStretch()
        
        self.btn_filter_orden_apartar = QPushButton()
        self.btn_filter_orden_apartar.setObjectName("secondaryBtn")
        self.btn_filter_orden_apartar.setIcon(Icons.filter_icon("#475569"))
        self.btn_filter_orden_apartar.setFixedSize(36, 36)
        self.btn_filter_orden_apartar.setToolTip("Filtrar por Órdenes")
        self.btn_filter_orden_apartar.clicked.connect(self._show_order_filter_menu)
        card_header_layout.addWidget(self.btn_filter_orden_apartar)
        
        form_layout.addLayout(card_header_layout)

        # Two-column input layout: Notaria on the left, Observaciones on the right
        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(16)

        # Left side: Notaria — with explicit placeholder so no item is pre-selected
        not_layout = QVBoxLayout()
        lbl_notaria = CustomLabel("Notaría de Destino *", variant="body")
        lbl_notaria.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        self.cb_notarias_apartar = CustomComboBox(self)
        self.cb_notarias_apartar.setMinimumHeight(35)
        self.cb_notarias_apartar.setPlaceholderText("-- Seleccione una notaría --")
        not_layout.addWidget(lbl_notaria)
        not_layout.addWidget(self.cb_notarias_apartar)

        # Right side: Observaciones (obligatorio)
        obs_layout = QVBoxLayout()
        lbl_obs = CustomLabel("Observaciones del Lote *", variant="body")
        lbl_obs.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        self.txt_obs_apartar = CustomInput("Observaciones obligatorias para el apartado...")
        self.txt_obs_apartar.setMinimumHeight(35)
        obs_layout.addWidget(lbl_obs)
        obs_layout.addWidget(self.txt_obs_apartar)

        inputs_layout.addLayout(not_layout, stretch=1)
        inputs_layout.addLayout(obs_layout, stretch=1)
        form_layout.addLayout(inputs_layout)

        # Interactive Grid (cascade mode: Desarrollo → RFC → Delegación → Concepto)
        self.grid_apartar = InteractiveGrid(self)
        self.grid_apartar.set_has_desarrollo(True)
        self.grid_apartar.btn_save.setVisible(False)
        self.grid_apartar.btn_cancel.setVisible(False)
        self.grid_apartar.availability_requested.connect(self._on_availability_requested)
        # Connect cascade signals to the view's handler methods
        self.grid_apartar.cascade_rfcs_needed.connect(self._on_cascade_rfcs_needed)
        self.grid_apartar.cascade_delegaciones_needed.connect(self._on_cascade_delegaciones_needed)
        self.grid_apartar.cascade_conceptos_needed.connect(self._on_cascade_conceptos_needed)
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
        delegacion_id = data.get("delegacion_id")
        if not rfc_id or not concepto_id or not delegacion_id:
            return

        worker = AvailabilityWorker(
            self.inventario_ui_service, row, rfc_id, concepto_id, delegacion_id,
            orden_ids=list(self.selected_orden_ids) if self.selected_orden_ids else None
        )
        worker.result_ready.connect(self._on_availability_result)
        worker.finished.connect(lambda: self._active_avail_workers.remove(worker) if worker in self._active_avail_workers else None)
        self._active_avail_workers.append(worker)
        worker.start()

    def _on_availability_result(self, row_widget, count: int):
        """Called on the main thread when the worker returns a count.
        Dynamically updates whichever grid contains the row.
        """
        if row_widget in self.grid_apartar.rows:
            self.grid_apartar.update_row_availability(row_widget, count)
        elif row_widget in self.grid_individual.rows:
            self.grid_individual.update_row_availability(row_widget, count)


    # ── Cascade handlers ─────────────────────────────────────────────────────

    def _on_cascade_rfcs_needed(self, row_widget, desarrollo_id: int):
        """Load RFCs for the selected Desarrollo and feed them into the row."""
        try:
            rfcs = self.inventario_ui_service.get_rfcs_por_desarrollo(desarrollo_id)
            row_widget.populate_rfcs(rfcs)
        except Exception as e:
            print(f"Error cargando RFCs para desarrollo {desarrollo_id}: {e}")

    def _on_cascade_delegaciones_needed(self, row_widget, desarrollo_id: int, rfc_id: int):
        """Load Delegaciones for the selected Desarrollo+RFC and feed them into the row."""
        try:
            delegaciones = self.inventario_ui_service.get_delegaciones_por_desarrollo_rfc(desarrollo_id, rfc_id)
            row_widget.populate_delegaciones(delegaciones)
        except Exception as e:
            print(f"Error cargando Delegaciones para desarrollo {desarrollo_id}, rfc {rfc_id}: {e}")

    def _on_cascade_conceptos_needed(self, row_widget, rfc_id: int, delegacion_id: int):
        """Load Conceptos for the selected RFC+Delegación and feed them into the row."""
        try:
            if row_widget in self.grid_individual.rows:
                # No restriction on concepts for Asignación Individual Directa: Load all active concepts
                conceptos_all_tuples = sorted(
                    [{"concepto_id": c_id, "nombre": c_name} for c_name, c_id in self._concepts_map.items()],
                    key=lambda x: x["concepto_id"]
                )
                row_widget.populate_conceptos(conceptos_all_tuples)
            else:
                # Keep stock restriction for Apartar tab
                conceptos = self.inventario_ui_service.get_conceptos_con_stock(rfc_id, delegacion_id)
                row_widget.populate_conceptos(conceptos)
        except Exception as e:
            print(f"Error cargando Conceptos para rfc {rfc_id}, delegacion {delegacion_id}: {e}")


    def _on_save_apartar(self):
        # --- Validación 1: Notaría seleccionada ---
        not_name = self.cb_notarias_apartar.currentText()
        notaria_id = self._notarias_map.get(not_name)
        if not notaria_id:
            QMessageBox.warning(self, "Notaría Faltante", "Por favor, seleccione una Notaría de destino válida.")
            return

        # --- Validación 2: Observaciones obligatorias ---
        obs_text = self.txt_obs_apartar.text().strip()
        if not obs_text:
            QMessageBox.warning(self, "Observaciones Requeridas",
                                "Las observaciones del lote son obligatorias.\n"
                                "Por favor describe el motivo o referencia del apartado.")
            self.txt_obs_apartar.setFocus()
            return
            
        data = self.grid_apartar.get_all_data()
        if not data:
            QMessageBox.warning(self, "Validación", "Debes agregar al menos un renglón para realizar un apartado.")
            return

        # --- Validaciones por renglón ---
        CONCEPTO_AVISO_ID = 2
        CONCEPTO_CLG_ID = 3
        seen_combinations = set()
        rows_data = []
        for i, row in enumerate(data):
            n = i + 1
            if not row["rfc_id"] or not row["concepto_id"] or not row["delegacion_id"]:
                QMessageBox.warning(self, "Validación", f"El renglón {n} debe tener Empresa, Concepto y Delegación seleccionados.")
                return
            if row["concepto_id"] not in (CONCEPTO_AVISO_ID, CONCEPTO_CLG_ID):
                QMessageBox.warning(self, "Validación",
                                    f"El renglón {n} tiene un concepto no permitido.\n"
                                    f"Solo se permiten: Aviso Preventivo (2) y CLG (3).")
                return

            # --- Validación 3: No duplicados ---
            key = (row["rfc_id"], row["concepto_id"], row["delegacion_id"], row.get("desarrollo_id"))
            if key in seen_combinations:
                QMessageBox.warning(self, "Renglón Duplicado",
                                    f"El renglón {n} es duplicado.\n"
                                    f"Ya existe un renglón con la misma Empresa, Concepto, Delegación y Desarrollo.")
                return
            seen_combinations.add(key)

            # --- Validación 4: Cantidad no puede superar disponibles ---
            disp_count = row.get("_disponibles", None)
            # Fetch from the row widget directly for precision
            for row_widget in self.grid_apartar.rows:
                wd = row_widget.get_data()
                if (wd["rfc_id"] == row["rfc_id"] and
                        wd["concepto_id"] == row["concepto_id"] and
                        wd["delegacion_id"] == row["delegacion_id"]):
                    disp_text = row_widget.lbl_disponibles.text()
                    # Parse count from label (e.g. "✓ 15", "⚠ 3", "✗ 0")
                    try:
                        disp_count = int(disp_text.split()[-1])
                    except (ValueError, IndexError):
                        disp_count = None
                    break

            if disp_count is not None and row["cantidad"] > disp_count:
                rfc_name = self.grid_apartar.get_rfc_text(row["rfc_id"]) or f"RFC {row['rfc_id']}"
                concepto_name = self.grid_apartar.get_concepto_text(row["concepto_id"]) or f"Concepto {row['concepto_id']}"
                QMessageBox.warning(
                    self, "Cantidad Excede Disponibles",
                    f"Renglón {n} — {rfc_name} / {concepto_name}:\n"
                    f"La cantidad solicitada ({row['cantidad']}) supera las referencias disponibles ({disp_count}).\n"
                    f"Reduzca la cantidad o verifique los filtros."
                )
                return

            rows_data.append({
                "rfc_id": row["rfc_id"],
                "concepto_id": row["concepto_id"],
                "delegacion_id": row["delegacion_id"],
                "desarrollo_id": row.get("desarrollo_id"),
                "cantidad": row["cantidad"]
            })

        # --- Regla de negocio: cada (empresa, delegación/desarrollo) debe tener AVISO y CLG ---
        pair_concepts: dict = {}  # (rfc_id, desarrollo_id or delegacion_id) -> set of concepto_ids
        for r in rows_data:
            pair_key = (r["rfc_id"], r["desarrollo_id"] if r["desarrollo_id"] else r["delegacion_id"])
            pair_concepts.setdefault(pair_key, set()).add(r["concepto_id"])

        missing_pairs = []
        for (rfc_id, target_id), concepts_set in pair_concepts.items():
            missing = []
            if CONCEPTO_AVISO_ID not in concepts_set:
                missing.append("Aviso Preventivo")
            if CONCEPTO_CLG_ID not in concepts_set:
                missing.append("CLG")
            if missing:
                rfc_name = self.grid_apartar.get_rfc_text(rfc_id) or f"RFC {rfc_id}"
                des_name = None
                has_desarrollo_id = any(
                    r["rfc_id"] == rfc_id and r["desarrollo_id"] == target_id
                    for r in rows_data
                )
                if has_desarrollo_id:
                    des_name = self.grid_apartar.get_desarrollo_text(target_id)
                if not des_name:
                    des_name = self.grid_apartar.get_delegacion_text(target_id) or f"Delegación/Desarrollo {target_id}"
                missing_pairs.append(f"• {rfc_name} / {des_name}: falta(n) {', '.join(missing)}")

        if missing_pairs:
            detail = "\n".join(missing_pairs)
            QMessageBox.warning(
                self, "Regla de Negocio",
                f"Cada combinación de Empresa + Delegación/Desarrollo debe tener un renglón de "
                f"Aviso Preventivo y uno de CLG.\n\nFaltan:\n{detail}"
            )
            return

        # --- Diálogo de confirmación con resumen detallado ---
        total_refs = sum(r["cantidad"] for r in rows_data)
        resumen_lineas = []
        for r in rows_data:
            rfc_name = self.grid_apartar.get_rfc_text(r["rfc_id"]) or f"RFC {r['rfc_id']}"
            concepto_name = self.grid_apartar.get_concepto_text(r["concepto_id"]) or f"Concepto {r['concepto_id']}"
            deleg_name = self.grid_apartar.get_delegacion_text(r["delegacion_id"]) or f"Deleg. {r['delegacion_id']}"
            des_name = ""
            if r["desarrollo_id"]:
                des_name = self.grid_apartar.get_desarrollo_text(r["desarrollo_id"]) or ""
                des_name = f" / {des_name}" if des_name else ""
            resumen_lineas.append(
                f"  • {rfc_name} | {concepto_name} | {deleg_name}{des_name} → {r['cantidad']} ref(s)"
            )
        resumen_texto = "\n".join(resumen_lineas)

        confirm_msg = (
            f"¿Confirmar el apartado de {total_refs} referencias para la notaría '{not_name}'?\n\n"
            f"Resumen de partidas:\n{resumen_texto}\n\n"
            f"Observaciones: {obs_text}\n\n"
            f"Esta operación reservará las referencias en estado RESERVADA y no podrá deshacerse fácilmente."
        )
        reply = QMessageBox.question(
            self, "Confirmar Apartado",
            confirm_msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # --- Ejecución del apartado ---
        try:
            parent_window = self.window()
            usuario_id = getattr(parent_window, "current_usuario_id", 1)
            
            if self.api_client.connect_via_api:
                for row_d in rows_data:
                    payload = {
                        "notaria_id": notaria_id,
                        "rfc_id": row_d["rfc_id"],
                        "concepto_id": row_d["concepto_id"],
                        "delegacion_id": row_d["delegacion_id"],
                        "desarrollo_id": row_d["desarrollo_id"],
                        "cantidad": row_d["cantidad"],
                        "usuario_creacion": usuario_id,
                        "observaciones": obs_text
                    }
                    self.api_client.request("POST", "/api/docs/inventario/lotes/apartar", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    from sar.src.storage.repositories import InventarioRepository
                    repo = InventarioRepository(session)
                    repo.apartar_referencias_lote(
                        notaria_id=notaria_id,
                        usuario_id=usuario_id,
                        partidas=rows_data,
                        observaciones=obs_text
                    )
                    session.commit()
                    
            QMessageBox.information(
                self, "Apartado Exitoso",
                f"Se han reservado exitosamente {total_refs} referencias en total en estado RESERVADA."
            )
            
            # Reset tabla, observaciones y recargar visor
            self.txt_obs_apartar.clear()
            self.grid_apartar.clear()
            self.grid_apartar.add_row()
            self.cb_notarias_apartar.setCurrentIndex(0)  # Restablecer placeholder
            self.refresh_visor_data()
        except Exception as e:
            QMessageBox.critical(self, "Error al Reservar", f"No se pudo completar el apartado de referencias:\n{str(e)}")

    def _on_apartar_referencias(self):
        # We also want to adapt ApartarReferenciasDialog to use InteractiveGrid
        dialog = ApartarReferenciasDialog(self.db_connector, self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_visor_data()

    # =========================================================================
    # TAB 5: GESTIÓN DE ASIGNACIONES
    # =========================================================================
    def _setup_tab_lotes(self):
        """Sets up the Gestión de Asignaciones tab — shows assignment summary rows."""
        layout = QVBoxLayout(self.tab_lotes)
        layout.setSpacing(16)

        # --- Header area ---
        header_layout = QHBoxLayout()
        title_lbl = CustomLabel("📋 Gestión de Asignaciones", variant="subheader")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # --- Filter bar ---
        from sar.src.ui.design_system.components.molecules.gl_labeled_combo import LabeledComboBox
        from sar.src.ui.design_system.components.molecules.gl_labeled_input import LabeledInput
        from PySide6.QtWidgets import QGroupBox

        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        # Search using QLineEdit matching the design/style of filterBarSearch in FilterBar
        self.search_lotes = QLineEdit()
        self.search_lotes.setObjectName("filterBarSearch")
        self.search_lotes.setPlaceholderText("🔍 Buscar por ID, notaria, colaborador, solicitante...")
        self.search_lotes.setStyleSheet("""
            QLineEdit#filterBarSearch {
                background-color: white;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 13px;
                color: #1e293b;
            }
            QLineEdit#filterBarSearch:focus {
                border: 1px solid #2563eb;
            }
        """)
        self.search_lotes.textChanged.connect(self._on_search_lotes)
        
        # Wrap in layout with margin-top: 14px to align perfectly with groupboxes
        search_wrap = QWidget()
        search_wrap.setStyleSheet("background: transparent;")
        search_wrap_layout = QVBoxLayout(search_wrap)
        search_wrap_layout.setContentsMargins(0, 14, 0, 0)
        search_wrap_layout.addWidget(self.search_lotes)
        filter_row.addWidget(search_wrap, stretch=3)

        # Tipo Destino
        self.labeled_destino_lotes = LabeledComboBox("Tipo Destino", ["Todos", "NOTARIA", "COLABORADOR"])
        self.cb_destino_filter_lotes = self.labeled_destino_lotes.combo
        self.cb_destino_filter_lotes.currentTextChanged.connect(self._on_destino_filter_lotes)
        filter_row.addWidget(self.labeled_destino_lotes)

        # Date Filters wrapped in matching style groupbox to homologate height
        self.group_start_date = QGroupBox("Desde", self)
        self.group_start_date.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                margin-top: 14px;
                font-weight: bold;
                color: #2563EB;
                font-size: 11px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 4px;
            }
        """)
        start_date_layout = QVBoxLayout(self.group_start_date)
        start_date_layout.setContentsMargins(4, 4, 4, 4)
        self.start_date_filter = QDateEdit()
        self.start_date_filter.setCalendarPopup(True)
        self.start_date_filter.setDate(QDate.currentDate().addMonths(-3))
        self.start_date_filter.setStyleSheet("border: none; background-color: white; min-width: 110px;")
        self.start_date_filter.dateChanged.connect(self._on_date_changed_lotes)
        start_date_layout.addWidget(self.start_date_filter)
        filter_row.addWidget(self.group_start_date)

        self.group_end_date = QGroupBox("Hasta", self)
        self.group_end_date.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                margin-top: 14px;
                font-weight: bold;
                color: #2563EB;
                font-size: 11px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 4px;
            }
        """)
        end_date_layout = QVBoxLayout(self.group_end_date)
        end_date_layout.setContentsMargins(4, 4, 4, 4)
        self.end_date_filter = QDateEdit()
        self.end_date_filter.setCalendarPopup(True)
        self.end_date_filter.setDate(QDate.currentDate())
        self.end_date_filter.setStyleSheet("border: none; background-color: white; min-width: 110px;")
        self.end_date_filter.dateChanged.connect(self._on_date_changed_lotes)
        end_date_layout.addWidget(self.end_date_filter)
        filter_row.addWidget(self.group_end_date)

        # Refresh button
        btn_refresh = CustomButton("↻ Actualizar", is_secondary=True)
        # Shift layout margin slightly to align with the margin-top offset of inputs
        btn_refresh.setStyleSheet("margin-top: 14px;")
        btn_refresh.clicked.connect(self.refresh_lotes_data)
        filter_row.addWidget(btn_refresh)

        # Filter Button (Funnel) for Lotes
        self.btn_filter_orden_lotes = QPushButton()
        self.btn_filter_orden_lotes.setObjectName("secondaryBtn")
        self.btn_filter_orden_lotes.setIcon(Icons.filter_icon("#475569"))
        self.btn_filter_orden_lotes.setFixedSize(36, 36)
        self.btn_filter_orden_lotes.setToolTip("Filtrar por Órdenes")
        self.btn_filter_orden_lotes.setStyleSheet("margin-top: 14px;")
        self.btn_filter_orden_lotes.clicked.connect(self._show_order_filter_menu)
        filter_row.addWidget(self.btn_filter_orden_lotes)

        layout.addLayout(filter_row)

        # --- Main Card & Table ---
        self.card_lotes = CustomCard(title="Registro de Asignaciones", parent=self)

        headers = ["ID", "Tipo Destino", "Asignado A", "Solicitante", "Fecha", "Total Refs", "Creado Por", "Observaciones"]
        self.table_lotes = StyledDataTable(headers, parent=self)
        self.table_lotes.setMinimumHeight(350)
        self.table_lotes.setMinimumWidth(200)
        self.card_lotes.add_widget(self.table_lotes)

        # Pagination footer
        footer_layout = QHBoxLayout()
        self.lbl_pagination_info_lotes = CustomLabel("0 asignaciones encontradas", variant="muted")
        footer_layout.addWidget(self.lbl_pagination_info_lotes)
        footer_layout.addStretch()

        self.cb_page_size_lotes = CustomComboBox(self)
        self.cb_page_size_lotes.addItems(["50 por página", "100 por página", "200 por página"])
        self.cb_page_size_lotes.setCurrentIndex(0)
        self.cb_page_size_lotes.currentTextChanged.connect(self._on_page_size_changed_lotes)
        footer_layout.addWidget(self.cb_page_size_lotes)

        self.pagination_widget_lotes = QWidget(self)
        self.pag_btn_layout_lotes = QHBoxLayout(self.pagination_widget_lotes)
        self.pag_btn_layout_lotes.setContentsMargins(0, 0, 0, 0)
        footer_layout.addWidget(self.pagination_widget_lotes)
        self.card_lotes.layout.addLayout(footer_layout)

        # Action buttons
        actions_layout = QHBoxLayout()
        self.btn_exportar_reporte_lotes = CustomButton("📊 Exportar Asignación Seleccionada", is_secondary=True)
        self.btn_exportar_reporte_lotes.clicked.connect(self._on_exportar_lote_seleccionado)
        self.btn_ver_detalles_lote = CustomButton("🔍 Ver Detalle", is_secondary=True)
        self.btn_ver_detalles_lote.clicked.connect(self._on_ver_detalle_lote)
        actions_layout.addStretch()
        actions_layout.addWidget(self.btn_exportar_reporte_lotes)
        actions_layout.addWidget(self.btn_ver_detalles_lote)
        self.card_lotes.layout.addLayout(actions_layout)
        layout.addWidget(self.card_lotes)

        # Hint label
        hint = CustomLabel("💡 Doble clic sobre una asignación para ver sus referencias.", variant="muted")
        layout.addWidget(hint)


        # State
        self.current_page_lotes = 1
        self.page_size_lotes = 50
        self.all_lotes_data = []  # List of dicts from get_lotes_asignacion_filtered
        self.total_lotes = 0
        self._current_search_text_lotes = ""
        self._current_tipo_destino_lotes = "Todos"
        self._current_rfc_id_lotes = None

        self.table_lotes.cellDoubleClicked.connect(self._on_table_cell_double_clicked_lotes)


    def refresh_lotes_data(self):
        """Loads assignments from service with active filters and populates the table."""
        if not hasattr(self, 'table_lotes'):
            return
        self.lbl_pagination_info_lotes.setText("Cargando asignaciones...")
        self.pagination_widget_lotes.setEnabled(False)

        tipo_destino = self._current_tipo_destino_lotes if self._current_tipo_destino_lotes != "Todos" else None
        search = self._current_search_text_lotes or None
        
        start_date = self.start_date_filter.date().toString("yyyy-MM-dd")
        end_date = self.end_date_filter.date().toString("yyyy-MM-dd")
        
        offset = (self.current_page_lotes - 1) * self.page_size_lotes

        try:
            lotes, total = self.inventario_ui_service.get_lotes_asignacion_filtered(
                search=search,
                tipo_destino=tipo_destino,
                limit=self.page_size_lotes,
                offset=offset,
                start_date=start_date,
                end_date=end_date,
                orden_ids=list(self.selected_orden_ids) if self.selected_orden_ids else None
            )
            self.all_lotes_data = lotes
            self.total_lotes = total
            self._populate_lotes_table()
        except Exception as e:
            self.lbl_pagination_info_lotes.setText(f"Error al cargar asignaciones: {e}")
            print("[GestionAsignaciones] Error:", e)


    def _populate_lotes_table(self):
        """Populates the lotes table from self.all_lotes_data without the Empresa column."""
        self.table_lotes.setRowCount(0)
        rows = []
        for l in self.all_lotes_data:
            rows.append([
                str(l["lote_asignacion_id"]),
                l["tipo_destino"],
                l["asignado_a"],
                l.get("solicitante_externo", ""),
                l["fecha"],
                str(l["total_referencias"]),
                l.get("creador", ""),
                l.get("observaciones", "")
            ])
        self.table_lotes.populate_rows(rows)

        total_pages = max(1, -(-self.total_lotes // self.page_size_lotes))
        start = (self.current_page_lotes - 1) * self.page_size_lotes + 1 if self.total_lotes > 0 else 0
        end = min(self.current_page_lotes * self.page_size_lotes, self.total_lotes)
        self.lbl_pagination_info_lotes.setText(
            f"Mostrando {start}–{end} de {self.total_lotes} asignaciones"
        )
        self.pagination_widget_lotes.setEnabled(True)

        # Rebuild pagination buttons
        while self.pag_btn_layout_lotes.count():
            item = self.pag_btn_layout_lotes.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        def add_page_btn(text, target, enabled):
            btn = QPushButton(text)
            btn.setEnabled(enabled)
            btn.clicked.connect(lambda: self._set_page_lotes(target))
            self.pag_btn_layout_lotes.addWidget(btn)

        add_page_btn("<<", 1, self.current_page_lotes > 1)
        add_page_btn("<", self.current_page_lotes - 1, self.current_page_lotes > 1)
        add_page_btn(str(self.current_page_lotes), self.current_page_lotes, False)
        add_page_btn(">", self.current_page_lotes + 1, self.current_page_lotes < total_pages)
        add_page_btn(">>", total_pages, self.current_page_lotes < total_pages)


    def _set_page_lotes(self, page):
        self.current_page_lotes = page
        self.refresh_lotes_data()

    def _on_search_lotes(self, text):
        self._current_search_text_lotes = text
        self.current_page_lotes = 1
        self.refresh_lotes_data()

    def _on_destino_filter_lotes(self, text):
        self._current_tipo_destino_lotes = text
        self.current_page_lotes = 1
        self.refresh_lotes_data()

    def _on_date_changed_lotes(self, qdate):
        self.current_page_lotes = 1
        self.refresh_lotes_data()

    def _on_page_size_changed_lotes(self, text):
        if "50" in text: self.page_size_lotes = 50
        elif "100" in text: self.page_size_lotes = 100
        else: self.page_size_lotes = 200
        self.current_page_lotes = 1
        self.refresh_lotes_data()

    def _on_table_cell_double_clicked_lotes(self, row, column):
        """Open LoteProcessingDialog on double-click."""
        if not self.all_lotes_data or row >= len(self.all_lotes_data):
            return
        lote = self.all_lotes_data[row]
        lote_id = lote.get("lote_asignacion_id")
        if lote_id:
            dialog = LoteProcessingDialog(self.db_connector, lote_id, self)
            dialog.exec()

    def _on_ver_detalle_lote(self):
        """Open detail dialog for the currently selected lote row."""
        selected = self.table_lotes.selectedItems()
        if not selected:
            QMessageBox.information(self, "Selección", "Selecciona una asignación de la tabla primero.")
            return
        row = selected[0].row()
        self._on_table_cell_double_clicked_lotes(row, 0)

    def _on_exportar_lote_seleccionado(self):
        """Export the selected lote to Excel via ExportLotesDialog pre-filtered."""
        selected = self.table_lotes.selectedItems()
        if not selected:
            QMessageBox.information(self, "Selección", "Selecciona una asignación de la tabla primero.")
            return
        row = selected[0].row()
        if not self.all_lotes_data or row >= len(self.all_lotes_data):
            return
        lote = self.all_lotes_data[row]
        lote_id = lote.get("lote_asignacion_id")
        dest_name = lote.get("asignado_a", "")
        req_name = lote.get("solicitante_externo", "")
        date_str = lote.get("fecha", "")

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Reporte de Asignación",
            f"Control_Inventario_Lote_{lote_id}.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return
        try:
            details = self.inventario_ui_service.get_lote_detalles(lote_id)
            title = "ENTREGA DE DERECHOS"
            subtitle = f"DESTINO: {dest_name.upper()} {f'({req_name.upper()})' if req_name else ''}"
            date_range = date_str.split()[0] if date_str else ""
            ExcelInventoryHandler.generate_excel_inventory_file(
                dest_path=file_path,
                title=title,
                subtitle=subtitle,
                date_range=date_range,
                data_rows=details
            )
            QMessageBox.information(self, "Exportación Completada", f"Archivo generado en:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error de Exportación", f"No se pudo generar el archivo:\n{str(e)}")


# =============================================================================
# DIALOGS
# =============================================================================
class ManualAssignmentDialog(QDialog):
    """Dialog to perform individual or bulk manual reference assignments."""
    
    def __init__(self, db_connector, ref_ids, ref_portals, parent=None, selected_refs=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.ref_ids = ref_ids
        self.selected_refs = selected_refs or []
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
            # Notaria requires client and address details
            self.txt_cliente.setEnabled(True)
            self.cb_desarrollo.setEnabled(True)
            self.txt_mz.setEnabled(True)
            self.txt_lote.setEnabled(True)
            self.txt_edif.setEnabled(True)
            self.txt_viv.setEnabled(True)
            self.txt_folio.setEnabled(True)
            self.txt_estatus_aviso.setEnabled(True)
        else:
            self.cb_notarias.hide()
            self.cb_colaboradores.show()
            self.txt_solicitante.setEnabled(False)
            self.txt_solicitante.clear()
            # For COLABORADOR, customer and address inputs are optional or bypassed.
            # We keep them enabled so they can be captured optionally, but they won't be validated as mandatory.
            pass


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
            
            # Filter developments to ensure referential integrity
            # Extract unique (rfc_id, delegacion_id) pairs from the references being assigned
            rfc_delegacion_pairs = set()
            for ref in self.selected_refs:
                rfc_id = ref.get("rfc_id")
                delegacion_id = ref.get("delegacion_id")
                # Look up mapping from grid_individual rows if not directly present in ref dict
                if not rfc_id or not delegacion_id:
                    for row in self.parent().grid_individual.get_all_data():
                        rfc_id = rfc_id or row.get("rfc_id")
                        delegacion_id = delegacion_id or row.get("delegacion_id")
                if rfc_id and delegacion_id:
                    rfc_delegacion_pairs.add((rfc_id, delegacion_id))

            # Fetch active triadic relationships from the catalog
            try:
                desarrollo_empresas = self.inventario_ui_service.get_desarrollos_activos_para_apartar()
            except Exception:
                desarrollo_empresas = []

            # Determine valid developments matching referential integrity filters
            valid_desarrollo_ids = set()
            for de in desarrollo_empresas:
                for rfc_id, del_id in rfc_delegacion_pairs:
                    if de.get("rfc_id") == rfc_id and de.get("delegacion_id") == del_id:
                        valid_desarrollo_ids.add(de.get("desarrollo_id"))

            # Populate developments combo with placeholder
            self.cb_desarrollo.addItem("-- Seleccione Desarrollo (Opcional) --", None)
            
            # Load only valid filtered developments (or all if no filters resolved)
            for d in desarrollos:
                if not rfc_delegacion_pairs or d["desarrollo_id"] in valid_desarrollo_ids:
                    self.cb_desarrollo.addItem(d["nombre"], d["desarrollo_id"])
            
            self.cb_desarrollo.setCurrentIndex(0)


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
        if des_name == "-- Seleccione Desarrollo (Opcional) --":
            des_name = None
        des_id = self._desarrollos_map.get(des_name) if des_name else None

        
        # Validation checks
        if tipo_destino == "NOTARIA":
            if not cliente:
                QMessageBox.warning(self, "Falta Información", "Por favor ingresa el nombre del cliente.")
                return
            if not des_id:
                QMessageBox.warning(self, "Falta Información", "Selecciona un desarrollo válido.")
                return
        else:
            # For COLABORADOR, observations field is mandatory if no client data is provided.
            if not self.txt_obs.toPlainText().strip():
                QMessageBox.warning(self, "Falta Información", "Debe capturar observaciones en la asignación del colaborador.")
                return
            if not cliente:
                cliente = "ASIGNACIÓN INTERNA"  # Default fallback if empty

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
    """Dialog to list historical assignments and export any to Control_Inventario.xlsx format."""
    
    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.inventario_ui_service = InventarioUIService(self.db_connector)
        
        self.setWindowTitle("Exportar Reporte de Asignación")
        self.setMinimumSize(600, 400)
        self.layout = QVBoxLayout(self)
        
        self.layout.addWidget(CustomLabel("Historial de Asignaciones", variant="subheader"))
        
        self.table_lotes = StyledDataTable(["ID Asignación", "Destino", "Asignado A", "Solicitante Externo", "Fecha Creación", "Refs", "Observaciones"], parent=self)
        self.layout.addWidget(self.table_lotes)

        # Buttons
        btns = QHBoxLayout()
        btn_close = CustomButton("Cerrar", is_secondary=True)
        btn_close.clicked.connect(self.reject)
        
        btn_export = CustomButton("Exportar Asignación")
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
            QMessageBox.warning(self, "Selección Requerida", "Por favor selecciona una asignación en la lista para exportarla.")
            return

        row = selected[0].row()
        lote_id = int(self.table_lotes.item(row, 0).text())
        dest_name = self.table_lotes.item(row, 2).text()
        req_name = self.table_lotes.item(row, 3).text()
        date_str = self.table_lotes.item(row, 4).text()

        # Ask where to save
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Reporte de Asignación",
            f"Asignacion_{lote_id}.xlsx",
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
    """Dialog to show details of an assignment with rich header, enhanced table,
    Generar Excel and Generar PDF actions."""

    def __init__(self, db_connector, lote_id: int, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.lote_id = lote_id
        self.inventario_ui_service = InventarioUIService(self.db_connector)
        self.header_data: dict = {}
        self.detalles: list = []

        self.setWindowTitle(f"Detalle de Asignación #{lote_id}")
        self.resize(1100, 680)
        self.setMinimumSize(950, 600)
        
        # Main Layout following design_system spacing
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # ── Header Section using CustomLabel ─────────────────────────────────
        self.header_layout = QHBoxLayout()
        self.lbl_title = CustomLabel(f"Detalle de Asignación #{lote_id}", variant="header")
        self.lbl_subtitle = CustomLabel("Cargando información del lote...", variant="body")
        self.lbl_subtitle.setObjectName("assignmentProcessingSubtitle")
        
        title_block = QVBoxLayout()
        title_block.addWidget(self.lbl_title)
        title_block.addWidget(self.lbl_subtitle)
        self.header_layout.addLayout(title_block)
        root.addLayout(self.header_layout)

        # ── Metrics Bar using design system components ───────────────────────
        self.banner_row = QWidget()
        self.banner_row.setStyleSheet("background: transparent;")
        banner_row_layout = QHBoxLayout(self.banner_row)
        banner_row_layout.setContentsMargins(0, 0, 0, 0)
        banner_row_layout.setSpacing(0)
        
        self.metric_frame = QFrame()
        self.metric_frame.setObjectName("assignmentMetricBar")
        # Reuse style pattern of orderProcessingMetricBar
        self.metric_frame.setStyleSheet("""
            QFrame#assignmentMetricBar {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        metric_layout = QHBoxLayout(self.metric_frame)
        metric_layout.setContentsMargins(16, 8, 16, 8)
        metric_layout.setSpacing(20)
        metric_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.lbl_metric_solicitante = CustomLabel("Solicitante: —", variant="body")
        self.lbl_metric_solicitante.setStyleSheet("font-weight: bold;")
        
        self.lbl_metric_fecha = CustomLabel("Fecha: —", variant="body")
        
        self.lbl_metric_estado = CustomLabel("Estado: —", variant="body")
        self.lbl_metric_estado.setStyleSheet("font-weight: bold;")

        metric_layout.addWidget(self.lbl_metric_solicitante)
        metric_layout.addWidget(self.lbl_metric_fecha)
        metric_layout.addWidget(self.lbl_metric_estado)
        
        banner_row_layout.addWidget(self.metric_frame)
        root.addWidget(self.banner_row)

        # ── References table ─────────────────────────────────────────────────

        headers = [
            "✔", "ID", "Ref ID",
            "Estado", "Empresa", "Concepto",
            "Referencia", "Cliente", "Desarrollo",
            "MZA", "Lote", "Ext", "Int",
            "No.Oficial", "P.A.", "Fecha Solicitud",
        ]
        self.table_detalles = StyledDataTable(headers, parent=self)
        self.table_detalles.setColumnHidden(1, True)  # ID interno
        self.table_detalles.setColumnHidden(2, True)  # Ref ID
        self.table_detalles.setMinimumHeight(300)
        root.addWidget(self.table_detalles)

        # ── Buttons ──────────────────────────────────────────────────────────
        btns = QHBoxLayout()
        
        btn_excel = CustomButton("Generar Excel", is_secondary=True)
        btn_excel.setIcon(Icons.file_excel("#16A34A")) # Excel green
        btn_excel.setToolTip("Generar Archivos Excel Lotes")
        btn_excel.clicked.connect(self._on_generate_excel)
        
        btn_pdf = CustomButton("Generar PDF", is_secondary=True)
        btn_pdf.setIcon(Icons.file_pdf("#DC2626")) # PDF red
        btn_pdf.setToolTip("Generar Archivos PDF Unificado")
        btn_pdf.clicked.connect(self._on_generate_pdf)

        btn_close = CustomButton("Cerrar", is_secondary=True)
        btn_close.clicked.connect(self.reject)

        btns.addStretch()
        btns.addWidget(btn_excel)
        btns.addWidget(btn_pdf)
        btns.addWidget(btn_close)
        root.addLayout(btns)

        self._load_all()

    # ── Data loading ─────────────────────────────────────────────────────────
    def _load_all(self):
        """Load header and detail rows."""
        try:
            self.header_data = self.inventario_ui_service.get_lote_asignacion_header(self.lote_id)
            self._apply_header(self.header_data)
        except Exception as e:
            print("[LoteProcessingDialog] Header error:", e)

        try:
            self.detalles = self.inventario_ui_service.get_lote_detalles(self.lote_id)
            self._populate_table()
        except Exception as e:
            QMessageBox.critical(self, "Error al Cargar",
                                 f"No se pudieron cargar los detalles de la asignación:\n{str(e)}")

    def _apply_header(self, h: dict):
        tipo       = h.get("tipo_destino", "")
        asignado   = h.get("asignado_a", "—")
        fecha      = h.get("fecha", "—")
        estado     = h.get("estado_refs", "—")
        solicitante = h.get("solicitante_externo", "")
        icon = "🏛" if tipo == "NOTARIA" else "🤝"

        self.lbl_title.setText(f"Detalle de Asignación #{self.lote_id}")
        self.lbl_subtitle.setText(f"{icon} {tipo}: {asignado}")
        
        self.lbl_metric_solicitante.setText(f"Solicitante: {solicitante}" if solicitante else f"Asignado a: {asignado}")
        self.lbl_metric_fecha.setText(f"Fecha: {fecha}")
        self.lbl_metric_estado.setText(f"Estado: {estado}")
        
        # Color metrics conditionally
        estado_color = "#16A34A" if estado == "ASIGNADA" else "#D97706"
        self.lbl_metric_estado.setStyleSheet(f"font-weight: bold; color: {estado_color};")

    def _populate_table(self):
        rows = []
        for d in self.detalles:
            rows.append([
                "",
                str(d.get("lote_detalle_id", "")),
                str(d.get("referencia_id", "") or ""),
                d.get("estado", ""),
                d.get("empresa", ""),
                d.get("concepto", ""),
                d.get("referencia", ""),
                d.get("cliente", ""),
                d.get("desarrollo", ""),
                d.get("mz", ""),
                d.get("lote", ""),
                d.get("edif", ""),
                d.get("viv", ""),
                d.get("folio_electronico", ""),
                d.get("pa", ""),
                d.get("fecha_solicitud", ""),
            ])
        self.table_detalles.populate_rows(rows, checkable_first_col=True)
        for r in range(self.table_detalles.rowCount()):
            chk = self.table_detalles.item(r, 0)
            if chk:
                chk.setCheckState(Qt.CheckState.Checked)

    def _get_selected_details(self) -> list:
        """Returns detalles list filtered to checked rows."""
        selected = []
        for r in range(self.table_detalles.rowCount()):
            if self.table_detalles.item(r, 0).checkState() == Qt.CheckState.Checked:
                if r < len(self.detalles):
                    selected.append(self.detalles[r])
        return selected

    # ── Excel generation ─────────────────────────────────────────────────────
    def _on_generate_excel(self):
        selected = self._get_selected_details()
        if not selected:
            QMessageBox.warning(self, "Selección Vacía",
                                "Por favor selecciona al menos una referencia.")
            return

        import re
        def _clean(s: str) -> str:
            return re.sub(r'[\\/:*?"<>|]', '_', s or "").strip()

        asignado  = _clean(self.header_data.get("asignado_a", "Asignacion"))
        # fecha raw: "14/08/2026 09:30" → "20260814"
        fecha_raw = self.header_data.get("fecha", "")
        try:
            from datetime import datetime
            fecha_str = datetime.strptime(fecha_raw.split()[0], "%d/%m/%Y").strftime("%Y%m%d")
        except Exception:
            from datetime import date
            fecha_str = date.today().strftime("%Y%m%d")
        total_refs   = len(selected)
        default_name = f"{asignado}_{fecha_str}_{total_refs}refs.xlsx"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Excel de Asignación", default_name, "Excel Files (*.xlsx)"
        )
        if not file_path:
            return
        try:
            ExcelInventoryHandler.generate_assignment_excel(
                dest_path=file_path,
                header=self.header_data,
                data_rows=selected,
            )
            QMessageBox.information(self, "Excel Generado",
                                    f"Archivo guardado exitosamente:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error al Generar Excel", str(e))

    # ── PDF generation ───────────────────────────────────────────────────────
    def _on_generate_pdf(self):
        selected = self._get_selected_details()
        if not selected:
            QMessageBox.warning(self, "Selección Vacía",
                                "Por favor selecciona al menos una referencia.")
            return

        dest_dir = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Destino")
        if not dest_dir:
            return

        import re
        import shutil
        from pypdf import PdfWriter, PdfReader

        def sanitize(name: str) -> str:
            return re.sub(r'[^\w\-.]', '_', name or "").strip("_") or "sin_nombre"

        asignado_a   = sanitize(self.header_data.get("asignado_a", ""))
        estado_lote  = self.header_data.get("estado_refs", "ASIGNADA")
        success = error = missing = 0
        consecutivo = 1

        def merge_or_copy_pdfs(pdf_paths: list, dest_path: str):
            """Merge multiple PDFs into one; if only one, just copy it."""
            valid = [p for p in pdf_paths if p and os.path.exists(p)]
            if not valid:
                return False
            if len(valid) == 1:
                shutil.copy2(valid[0], dest_path)
            else:
                writer = PdfWriter()
                for pp in valid:
                    try:
                        reader = PdfReader(pp)
                        for page in reader.pages:
                            writer.add_page(page)
                    except Exception:
                        pass
                with open(dest_path, "wb") as f:
                    writer.write(f)
            return True

        for d in selected:
            ref_id     = d.get("referencia_id")
            concepto   = sanitize(d.get("concepto", "CONCEPTO"))
            cliente    = sanitize(d.get("cliente", ""))
            referencia = sanitize(d.get("referencia", ""))
            estado_ref = d.get("estado", estado_lote)

            if not ref_id:
                missing += 1
                continue
            try:
                facturas = self.inventario_ui_service.get_facturas_by_referencia_id(ref_id)
                if not facturas:
                    missing += 1
                    continue

                # Collect all PDF paths for this reference
                pdf_paths = []
                for f in facturas:
                    if f.get("pdf_path"):
                        pdf_paths.append(f["pdf_path"])
                    if f.get("pdf2_path") and f["pdf2_path"].lower().endswith(".pdf"):
                        pdf_paths.append(f["pdf2_path"])

                if not any(os.path.exists(p) for p in pdf_paths if p):
                    missing += 1
                    continue

                # Build output filename per state
                consec = f"{consecutivo:03d}"
                if estado_ref == "ASIGNADA":
                    # nombre_cliente_Concepto_consecutivo.pdf
                    out_name = f"{cliente}_{concepto}_{consec}.pdf"
                else:
                    # referencia_notaria_Concepto_consecutivo.pdf  (RESERVADA)
                    out_name = f"{referencia}_{asignado_a}_{concepto}_{consec}.pdf"

                out_path = os.path.join(dest_dir, out_name)
                if merge_or_copy_pdfs(pdf_paths, out_path):
                    success += 1
                    consecutivo += 1
                else:
                    error += 1
            except Exception as e:
                print(f"[PDF] Error ref {ref_id}:", e)
                error += 1

        msg = f"PDFs generados exitosamente: {success}\n"
        if missing: msg += f"Referencias sin archivos: {missing}\n"
        if error:   msg += f"Errores al procesar: {error}\n"
        QMessageBox.information(self, "Generación de PDFs Finalizada", msg)


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
        
        self.setWindowTitle("Reserva de Derechos (Apartados)")
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
            CONCEPTOS_APARTADO = {2, 3}
            concepts_list_tuples = sorted(
                [
                    (c_id, c_name)
                    for c_name, c_id in self._concepts_map.items()
                    if c_id in CONCEPTOS_APARTADO
                ],
                key=lambda x: x[0]
            )
            delegations_list_tuples = [(d["delegacion_id"] if isinstance(d, dict) else d.delegacion_id, d["nombre"] if isinstance(d, dict) else d.nombre) for d in self._catalogs_data["delegaciones"]]
            
            desarrollos_tuples = []
            for d in self._catalogs_data["desarrollos"]:
                desarrollos_tuples.append((d["desarrollo_id"], d["nombre"], d.get("delegacion_id")))
                
            self.grid.set_has_desarrollo(True)
            self.grid.set_catalogs(rfcs_list_tuples, concepts_list_tuples, delegations_list_tuples, desarrollos_tuples)
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
                QMessageBox.warning(self, "Validación", f"El renglón {i+1} debe tener todos los campos seleccionados (Empresa, Concepto y Delegación).")
                return
                
            key = (row["rfc_id"], row["concepto_id"], row["delegacion_id"], row.get("desarrollo_id"))
            if key in seen_combinations:
                QMessageBox.warning(self, "Validación", f"El renglón {i+1} tiene una combinación duplicada de Empresa, Concepto, Delegación y Desarrollo.")
                return
            seen_combinations.add(key)
            
            # Si el desarrollo_id no fue seleccionado (es None o "Cualquier Desarrollo"), pasamos el delegacion_id como desarrollo_id a la consulta / repo
            final_desarrollo_id = row.get("desarrollo_id") if row.get("desarrollo_id") else row["delegacion_id"]
            
            rows_data.append({
                "rfc_id": row["rfc_id"],
                "concepto_id": row["concepto_id"],
                "desarrollo_id": final_desarrollo_id,
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

