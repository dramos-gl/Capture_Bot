"""Dashboard Main View matching the target design mockup."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLineEdit, QPushButton, QComboBox, QLabel, QDialog, QScrollArea
)
from PySide6.QtCore import Qt, QDateTime, QThread, Signal, QTimer, QSize
from sar.src.ui.design_system.components import CustomCard, CustomLabel, StyledDataTable, CustomButton, CustomComboBox, KeepOpenMenu
from sar.src.ui.design_system.components.molecules.gl_stat_card import StatCard
from sar.src.ui.design_system.utils.icons import Icons
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.services.referencias_service import ReferenciasService

class DashboardKPIsLoadWorker(QThread):
    """Background worker thread to load KPI counts for the dashboard."""
    result_ready = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, referencias_service, orden_ids: list = None):
        super().__init__()
        self.referencias_service = referencias_service
        self.orden_ids = orden_ids
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            if self._is_cancelled:
                return
            kpis = self.referencias_service.get_dashboard_kpis(self.orden_ids)
            if not self._is_cancelled:
                self.result_ready.emit(kpis)
        except Exception as e:
            if not self._is_cancelled:
                self.error_occurred.emit(str(e))

class DashboardReferencesLoadWorker(QThread):
    """Background worker thread to load dashboard references from the DB dynamically with pagination."""
    result_ready = Signal(list, int) # data, total_count
    error_occurred = Signal(str)
    
    def __init__(self, referencias_service, limit: int, offset: int, search_text: str, orden_ids: list = None):
        super().__init__()
        self.referencias_service = referencias_service
        self.limit = limit
        self.offset = offset
        self.search_text = search_text
        self.orden_ids = orden_ids
        self._is_cancelled = False
        
    def cancel(self):
        self._is_cancelled = True
        
    def run(self):
        try:
            if self._is_cancelled:
                return
            res, total_count = self.referencias_service.get_referencias_paginated(
                limit=self.limit,
                offset=self.offset,
                search_text=self.search_text,
                estado_filter="Todos",
                orden_ids=self.orden_ids
            )
            if not self._is_cancelled:
                self.result_ready.emit(res, total_count)
        except Exception as e:
            if not self._is_cancelled:
                import traceback
                traceback.print_exc()
                self.error_occurred.emit(str(e))

class DashboardView(QWidget):
    """Refactored Dashboard View reflecting the high-fidelity UI design mockup."""
    
    # Signal emitted when user double-clicks on the Total Generadas stat card
    show_metrics_requested = Signal(list)
    
    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.referencias_service = ReferenciasService(self.db_connector)
        self.active_kpis_worker = None
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QWidget#dashboardScrollContent {
                background-color: transparent;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setObjectName("dashboardScrollContent")
        self.layout = QVBoxLayout(scroll_content)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(20)
        
        # Pagination and data state variables
        self.all_data = []
        self.filtered_data = []
        self.current_page = 1
        self.page_size = 200
        self.total_items = 0
        self.active_worker = None
        self.selected_orden_ids = []
        self.todas_las_ordenes = []
        self.is_custom_filter = False
        
        # Debounce timer for text search (350ms delay) to prevent database flooding while typing
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._on_search_timer_timeout)
        
        # 1. Header Layout
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(12)
        
        # Left blue indicator bar
        self.indicator_bar = QFrame(self)
        self.indicator_bar.setFixedWidth(4)
        self.indicator_bar.setFixedHeight(28)
        self.indicator_bar.setObjectName("dashboardIndicatorBar")
        self.header_layout.addWidget(self.indicator_bar)
        
        # Header titles
        self.title_text_layout = QVBoxLayout()
        self.title_text_layout.setContentsMargins(0, 0, 0, 0)
        self.title_text_layout.setSpacing(2)
        
        self.lbl_title = CustomLabel("Tablero de Control Operativo", variant="header")
        self.lbl_title.setObjectName("dashboardTitle")
        
        self.lbl_subtitle = CustomLabel("Resumen general del estado de los derechos", variant="muted")
        self.lbl_subtitle.setObjectName("dashboardSubtitle")
        
        self.title_text_layout.addWidget(self.lbl_title)
        self.title_text_layout.addWidget(self.lbl_subtitle)
        self.header_layout.addLayout(self.title_text_layout)
        
        self.header_layout.addStretch()
        
        # Date & Time display widget
        self.time_widget = QWidget(self)
        self.time_widget.setStyleSheet("background: transparent;")
        self.time_layout = QHBoxLayout(self.time_widget)
        self.time_layout.setContentsMargins(0, 0, 0, 0)
        self.time_layout.setSpacing(6)
        
        self.lbl_calendar_icon = QLabel()
        self.lbl_calendar_icon.setPixmap(Icons.calendar().pixmap(16, 16))
        self.lbl_calendar_icon.setStyleSheet("background: transparent;")
        
        self.lbl_datetime = CustomLabel(QDateTime.currentDateTime().toString("dd/MM/yyyy  hh:mm AP"), variant="body")
        self.lbl_datetime.setObjectName("dashboardDatetime")
        
        self.time_layout.addWidget(self.lbl_calendar_icon)
        self.time_layout.addWidget(self.lbl_datetime)
        self.header_layout.addWidget(self.time_widget)
        
        # Actualizar Button
        self.btn_update = QPushButton(self)
        self.btn_update.setObjectName("filterBarActionBtn")
        self.btn_update.setIcon(Icons.actualizar("#FFFFFF"))
        self.btn_update.setIconSize(QSize(20, 20))
        self.btn_update.setFixedSize(35, 35)
        self.btn_update.setToolTip("Actualizar Tablero")
        self.btn_update.clicked.connect(self.refresh_data)
        self.header_layout.addWidget(self.btn_update)
        
        self.layout.addLayout(self.header_layout)
        
        # 2. KPI Cards Row (Single dynamic row with stretch=1 across all 6 cards)
        self.kpi_widget = QWidget(self)
        self.kpi_widget.setObjectName("kpiRowWidget")
        self.kpi_widget.setStyleSheet("QWidget#kpiRowWidget { background: transparent; }")
        self.kpi_layout = QHBoxLayout(self.kpi_widget)
        self.kpi_layout.setContentsMargins(0, 0, 0, 0)
        self.kpi_layout.setSpacing(10)
        
        self.card_generadas = StatCard("Total Generadas", "0", "file_text", color_hex=Colors.ACCENT, parent=self.kpi_widget)
        self.card_pendientes = StatCard("Pendientes Autorización", "0", "clock", color_hex=Colors.WARNING, parent=self.kpi_widget)
        self.card_autorizadas = StatCard("Autorizadas por Facturar", "0", "shield_check", color_hex=Colors.SUCCESS, parent=self.kpi_widget)
        self.card_rechazadas = StatCard("Rechazadas", "0", "x_circle", color_hex="#EA580C", parent=self.kpi_widget)
        self.card_error = StatCard("Con Error", "0", "alert_triangle", color_hex=Colors.ERROR, parent=self.kpi_widget)
        self.card_invalidas = StatCard("Derechos Invalidadas", "0", "alert_triangle", color_hex="#64748B", parent=self.kpi_widget)
        
        self.kpi_layout.addWidget(self.card_generadas, stretch=1)
        self.kpi_layout.addWidget(self.card_pendientes, stretch=1)
        self.kpi_layout.addWidget(self.card_autorizadas, stretch=1)
        self.kpi_layout.addWidget(self.card_rechazadas, stretch=1)
        self.kpi_layout.addWidget(self.card_error, stretch=1)
        self.kpi_layout.addWidget(self.card_invalidas, stretch=1)
        
        self.layout.addWidget(self.kpi_widget)
        
        # 3. Main Action Container (Recent Activity Card)
        self.activity_card = QFrame(self)
        self.activity_card.setObjectName("cardFrame")
        self.activity_layout = QVBoxLayout(self.activity_card)
        self.activity_layout.setContentsMargins(20, 20, 20, 20)
        self.activity_layout.setSpacing(16)
        
        # Table Header Layout (Title + Search + Filter + Actions)
        self.table_header_layout = QHBoxLayout()
        self.table_header_layout.setContentsMargins(0, 0, 0, 0)
        self.table_header_layout.setSpacing(12)
        
        # Section icon & label
        self.lbl_table_icon = QLabel()
        self.lbl_table_icon.setPixmap(Icons.file_text("#2563EB").pixmap(18, 18))
        self.lbl_table_icon.setStyleSheet("background: transparent;")
        
        self.lbl_table_title = CustomLabel("Últimos derechos generados", variant="subheader")
        self.lbl_table_title.setObjectName("dashboardTableTitle")
        
        self.table_header_layout.addWidget(self.lbl_table_icon)
        self.table_header_layout.addWidget(self.lbl_table_title)
        self.table_header_layout.addStretch()
        
        # Search Box
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Buscar derechos...")
        self.search_input.setFixedWidth(240)
        self.search_input.addAction(Icons.search("#64748B"), QLineEdit.LeadingPosition)
        self.search_input.textChanged.connect(self._on_search_changed)
        self.table_header_layout.addWidget(self.search_input)
        
        # Filter Button
        self.btn_filter = QPushButton()
        self.btn_filter.setObjectName("secondaryBtn")
        self.btn_filter.setIcon(Icons.filter_icon("#475569"))
        self.btn_filter.setFixedSize(36, 36)
        self.table_header_layout.addWidget(self.btn_filter)
        
        # More Options Button
        self.btn_more = QPushButton()
        self.btn_more.setObjectName("secondaryBtn")
        self.btn_more.setIcon(Icons.more_vertical("#475569"))
        self.btn_more.setFixedSize(36, 36)
        self.table_header_layout.addWidget(self.btn_more)
        
        self.activity_layout.addLayout(self.table_header_layout)
        
        # Data Table
        headers = ["ID", "Consecutivo", "Referencia Portal", "Importe", "Fecha Generación", "Estado"]
        self.table = StyledDataTable(headers, parent=self)
        self.table.setMinimumHeight(150)
        self.table.setMinimumWidth(200)
        self.activity_layout.addWidget(self.table)
        
        # Table Footer Pagination Layout
        self.footer_layout = QHBoxLayout()
        self.footer_layout.setContentsMargins(0, 8, 0, 0)
        
        self.lbl_pagination_info = CustomLabel("Mostrando 0 a 0 de 0 derechos", variant="muted")
        self.lbl_pagination_info.setObjectName("dashboardPaginationInfo")
        self.footer_layout.addWidget(self.lbl_pagination_info)
        
        self.footer_layout.addStretch()
        
        # Page size combobox
        self.cb_page_size = CustomComboBox(self)
        self.cb_page_size.addItems(["50 por página", "100 por página", "200 por página"])
        self.cb_page_size.setFixedWidth(120)
        self.cb_page_size.setCurrentIndex(2) # Default to 200 por página
        self.cb_page_size.currentTextChanged.connect(self._on_page_size_changed)
        self.footer_layout.addWidget(self.cb_page_size)
        
        # Pagination buttons wrapper
        self.pagination_widget = QWidget(self)
        self.pagination_widget.setStyleSheet("background: transparent;")
        self.pag_btn_layout = QHBoxLayout(self.pagination_widget)
        self.pag_btn_layout.setContentsMargins(0, 0, 0, 0)
        self.pag_btn_layout.setSpacing(4)
        
        self.footer_layout.addWidget(self.pagination_widget)
        self.activity_layout.addLayout(self.footer_layout)
        
        self.btn_filter.clicked.connect(self._show_filter_menu)
        
        self.card_generadas.mouseDoubleClickEvent = self._on_card_double_clicked
        self.card_pendientes.mouseDoubleClickEvent = self._on_card_double_clicked
        self.card_autorizadas.mouseDoubleClickEvent = self._on_card_double_clicked
        self.card_rechazadas.mouseDoubleClickEvent = self._on_card_double_clicked
        self.card_error.mouseDoubleClickEvent = self._on_error_card_double_clicked
        self.card_invalidas.mouseDoubleClickEvent = self._on_invalidas_card_double_clicked
        self.layout.addWidget(self.activity_card)
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        self._load_available_orders()
        self.refresh_data()
        
    def _on_card_double_clicked(self, event):
        self.show_metrics_requested.emit(list(self.selected_orden_ids))

    def _on_error_card_double_clicked(self, event):
        dialog = ErrorDetailDialog(
            db_connector=self.db_connector,
            title="Detalle de Derechos con Error",
            states=["ERROR", "FALLIDO"],
            orden_ids=list(self.selected_orden_ids),
            parent=self
        )
        dialog.exec()

    def _on_invalidas_card_double_clicked(self, event):
        dialog = ErrorDetailDialog(
            db_connector=self.db_connector,
            title="Detalle de Derechos Invalidados",
            states=["ERROR_VALIDACION"],
            orden_ids=list(self.selected_orden_ids),
            parent=self
        )
        dialog.exec()

    def refresh_data(self):
        """Fetches latest KPI metrics and launches background thread for paginated references."""
        # Update timestamp label
        self.lbl_datetime.setText(QDateTime.currentDateTime().toString("dd/MM/yyyy  hh:mm AP"))
        
        self._load_available_orders(preserve_selection=True)
        
        # Cancel active KPIs worker if running
        if self.active_kpis_worker and self.active_kpis_worker.isRunning():
            self.active_kpis_worker.cancel()
            try:
                self.active_kpis_worker.result_ready.disconnect()
                self.active_kpis_worker.error_occurred.disconnect()
            except RuntimeError:
                pass
            self.active_kpis_worker.wait()

        # Set visual feedback to loading state for KPIs
        self.card_generadas.set_value("...")
        self.card_pendientes.set_value("...")
        self.card_autorizadas.set_value("...")
        self.card_rechazadas.set_value("...")
        self.card_error.set_value("...")
        self.card_invalidas.set_value("...")

        # Start KPI background worker
        self.active_kpis_worker = DashboardKPIsLoadWorker(
            referencias_service=self.referencias_service,
            orden_ids=self.selected_orden_ids
        )
        self.active_kpis_worker.result_ready.connect(self._on_kpis_loaded)
        self.active_kpis_worker.error_occurred.connect(self._on_kpis_error)
        self.active_kpis_worker.start()
            
        self.refresh_data_references()

    def _on_kpis_loaded(self, kpis):
        self.card_generadas.set_value(str(kpis.get("total_generadas", 0)))
        self.card_pendientes.set_value(str(kpis.get("pendientes", 0)))
        self.card_autorizadas.set_value(str(kpis.get("autorizadas", 0)))
        self.card_rechazadas.set_value(str(kpis.get("rechazadas", 0)))
        self.card_error.set_value(str(kpis.get("con_error", 0)))
        self.card_invalidas.set_value(str(kpis.get("invalidas", 0)))

    def _on_kpis_error(self, err_msg):
        print("Error refreshing dashboard KPIs in background:", err_msg)
        self.card_generadas.set_value("0")
        self.card_pendientes.set_value("0")
        self.card_autorizadas.set_value("0")
        self.card_rechazadas.set_value("0")
        self.card_error.set_value("0")
        self.card_invalidas.set_value("0")

    def refresh_data_references(self):
        """Starts background thread to fetch dashboard references."""
        # Cancel active thread if running safely
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.cancel()
            try:
                self.active_worker.result_ready.disconnect()
                self.active_worker.error_occurred.disconnect()
            except RuntimeError:
                pass
            self.active_worker.wait()

        self.lbl_pagination_info.setText("Cargando derechos...")
        self.pagination_widget.setEnabled(False)
        self.cb_page_size.setEnabled(False)

        search_text = self.search_input.text().strip()
        offset = (self.current_page - 1) * self.page_size

        self.active_worker = DashboardReferencesLoadWorker(
            referencias_service=self.referencias_service,
            limit=self.page_size,
            offset=offset,
            search_text=search_text,
            orden_ids=self.selected_orden_ids
        )
        self.active_worker.result_ready.connect(self._on_data_loaded)
        self.active_worker.error_occurred.connect(self._on_load_error)
        self.active_worker.start()

    def _on_data_loaded(self, data, total_count):
        self.all_data = data
        self.filtered_data = data
        self.total_items = total_count
        
        self.pagination_widget.setEnabled(True)
        self.cb_page_size.setEnabled(True)
        
        self._populate_table_and_pagination()

    def _on_load_error(self, err_msg):
        self.pagination_widget.setEnabled(True)
        self.cb_page_size.setEnabled(True)
        self.lbl_pagination_info.setText("Error al cargar los derechos.")
        print("Dashboard references load error:", err_msg)

    def _on_search_changed(self, text):
        """Filters dashboard data using debounce timer to prevent SQL flood."""
        self.current_page = 1
        self.search_timer.start(350)

    def _on_search_timer_timeout(self):
        self.refresh_data_references()

    def _on_page_size_changed(self, text):
        """Handles page size combo selection changes."""
        if "50" in text:
            self.page_size = 50
        elif "100" in text:
            self.page_size = 100
        elif "200" in text:
            self.page_size = 200
        self.current_page = 1
        self.refresh_data_references()

    def _populate_table_and_pagination(self):
        # Populate Table
        data_rows = []
        for ref in self.all_data:
            data_rows.append([
                str(ref["referencia_id"]),
                str(ref["consecutivo_grupo"]),
                ref["referencia_portal"],
                f"${ref['importe']}" if ref['importe'] else "-",
                ref["fecha_generacion"],
                ref["estado"]
            ])
        self.table.populate_rows(data_rows)
        
        total_items = self.total_items
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + len(self.all_data), total_items)
        
        # Update Footer Info
        if total_items == 0:
            self.lbl_pagination_info.setText("Mostrando 0 a 0 de 0 derechos")
        else:
            self.lbl_pagination_info.setText(f"Mostrando {start_idx + 1} a {end_idx} de {total_items} derechos")
            
        # Redraw Pagination Buttons
        while self.pag_btn_layout.count():
            item = self.pag_btn_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        total_pages = max(1, (total_items + self.page_size - 1) // self.page_size)
        
        # Helper to add nav buttons
        def add_nav_btn(text, target_page, enabled):
            btn = QPushButton(text)
            btn.setObjectName("paginationNavBtn")
            btn.setEnabled(enabled)
            btn.clicked.connect(lambda: self._set_page(target_page))
            self.pag_btn_layout.addWidget(btn)
            
        # Helper to add numeric buttons
        def add_page_btn(page_num, active):
            btn = QPushButton(str(page_num))
            btn.setObjectName("paginationActivePageBtn" if active else "paginationPageBtn")
            btn.clicked.connect(lambda: self._set_page(page_num))
            self.pag_btn_layout.addWidget(btn)
            
        # Determine showing page range
        start_page = max(1, self.current_page - 2)
        end_page = min(total_pages, start_page + 4)
        if end_page - start_page < 4:
            start_page = max(1, end_page - 4)
            
        # Add << and <
        add_nav_btn("<<", 1, self.current_page > 1)
        add_nav_btn("<", self.current_page - 1, self.current_page > 1)
        
        for p in range(start_page, end_page + 1):
            add_page_btn(p, p == self.current_page)
            
        # Add > and >>
        add_nav_btn(">", self.current_page + 1, self.current_page < total_pages)
        add_nav_btn(">>", total_pages, self.current_page < total_pages)

    def _set_page(self, page_num):
        self.current_page = page_num
        self.refresh_data_references()

    def _load_available_orders(self, preserve_selection=False):
        try:
            raw_ordenes = self.referencias_service.get_ordenes(include_rejected=False)
            self.todas_las_ordenes = [
                ord for ord in raw_ordenes
                if str(ord.get("estado", "") or ord.get("estado_codigo", "")).upper() not in ("RECHAZADA", "RECHAZADO", "CANCELADA", "CANCELADO")
            ]
            if self.todas_las_ordenes:
                valid_ids = {ord["orden_id"] for ord in self.todas_las_ordenes}
                if preserve_selection and self.is_custom_filter and self.selected_orden_ids:
                    self.selected_orden_ids = [oid for oid in self.selected_orden_ids if oid in valid_ids]
                
                if not self.selected_orden_ids or (preserve_selection and not self.is_custom_filter):
                    self.selected_orden_ids = [ord["orden_id"] for ord in self.todas_las_ordenes if ord.get("total_pendiente_autorizacion", 0) > 0]
                    if not self.selected_orden_ids and self.todas_las_ordenes:
                        self.selected_orden_ids = [self.todas_las_ordenes[0]["orden_id"]]
            else:
                self.selected_orden_ids = []
        except Exception as e:
            print("Error loading available orders for dashboard:", e)
            self.todas_las_ordenes = []
            self.selected_orden_ids = []

    def _show_filter_menu(self):
        from PySide6.QtGui import QAction
        
        # Load orders if not loaded yet
        if not hasattr(self, 'todas_las_ordenes') or not self.todas_las_ordenes:
            self._load_available_orders()
            
        menu = KeepOpenMenu(self)
        order_actions = {}
        
        # "Todas" action
        action_all = QAction("Todas las órdenes", menu, checkable=True)
        is_all_selected = len(self.selected_orden_ids) == len(self.todas_las_ordenes) and len(self.todas_las_ordenes) > 0
        action_all.setChecked(is_all_selected)
        
        def update_all_action_state():
            is_all = len(self.selected_orden_ids) == len(self.todas_las_ordenes) and len(self.todas_las_ordenes) > 0
            action_all.blockSignals(True)
            action_all.setChecked(is_all)
            action_all.blockSignals(False)
        
        def toggle_all(checked):
            self.is_custom_filter = True
            if checked:
                self.selected_orden_ids = [ord["orden_id"] for ord in self.todas_las_ordenes]
            else:
                self.selected_orden_ids = []
                
            # Synchronize visual state of all order check items in menu
            for oid, act in order_actions.items():
                act.blockSignals(True)
                act.setChecked(checked)
                act.blockSignals(False)
                
            self.refresh_data()
            
        action_all.triggered.connect(toggle_all)
        menu.addAction(action_all)
        menu.addSeparator()
        
        # Actions for individual orders
        from sar.src.ui.design_system.utils.formatters import format_orden_filter_label
        for ord in self.todas_las_ordenes:
            oid = ord["orden_id"]
            label = format_orden_filter_label(ord.get("folio", ""), ord.get("descripcion", ""))
            action = QAction(label, menu, checkable=True)
            action.setChecked(oid in self.selected_orden_ids)
            order_actions[oid] = action
            
            def make_toggle_handler(target_oid):
                def handler(checked):
                    self.is_custom_filter = True
                    if checked:
                        if target_oid not in self.selected_orden_ids:
                            self.selected_orden_ids.append(target_oid)
                    else:
                        if target_oid in self.selected_orden_ids:
                            self.selected_orden_ids.remove(target_oid)
                    update_all_action_state()
                    self.refresh_data()
                return handler
                
            action.triggered.connect(make_toggle_handler(oid))
            menu.addAction(action)
            
        # Display the menu directly under the filter button
        menu.exec(self.btn_filter.mapToGlobal(self.btn_filter.rect().bottomLeft()))


class ErrorDetailDialog(QDialog):
    def __init__(self, db_connector, title: str, states: list, orden_ids: list = None, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.title_text = title
        self.states = states
        self.orden_ids = orden_ids
        self.raw_data = []
        self.setWindowTitle(title)
        self.resize(1000, 600)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Title Label
        lbl_title = CustomLabel(self.title_text, variant="subheader")
        layout.addWidget(lbl_title)

        # Header Row: Search and Export
        header_layout = QHBoxLayout()
        self.txt_search = QLineEdit(self)
        self.txt_search.setPlaceholderText("🔍 Buscar referencia, RFC o empresa...")
        self.txt_search.setStyleSheet("""
            QLineEdit {
                padding: 6px 12px;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                background-color: #FFFFFF;
                color: #1E293B;
            }
        """)
        self.txt_search.textChanged.connect(self._on_search_changed)
        header_layout.addWidget(self.txt_search)

        btn_export = CustomButton("Exportar Excel", is_secondary=True)
        btn_export.setIcon(Icons.file_excel("#16A34A"))
        btn_export.clicked.connect(self._export_to_excel)
        header_layout.addWidget(btn_export)

        layout.addLayout(header_layout)

        # Table
        headers = ["Folio Referencia", "RFC", "Razón Social", "Concepto", "Delegación", "Estado", "Importe", "Fecha Generación"]
        self.table = StyledDataTable(headers, parent=self)
        layout.addWidget(self.table)

    def _load_data(self):
        from sqlalchemy import select
        from sar.src.storage.models import Referencia, EstadoSistema, GrupoReferencia, Solicitud, Concepto, Rfc, Delegacion

        self.raw_data = []
        try:
            with self.db_connector.get_session() as session:
                stmt = (
                    select(
                        Referencia.referencia_portal,
                        Rfc.rfc,
                        Rfc.razon_social,
                        Concepto.nombre.label("concepto_nombre"),
                        Delegacion.nombre.label("delegacion_nombre"),
                        EstadoSistema.codigo.label("estado_codigo"),
                        Referencia.importe,
                        Referencia.fecha_generacion
                    )
                    .join(EstadoSistema, Referencia.estado_id == EstadoSistema.estado_id)
                    .join(GrupoReferencia, Referencia.grupo_id == GrupoReferencia.grupo_id)
                    .join(Rfc, GrupoReferencia.rfc_id == Rfc.rfc_id)
                    .join(Concepto, GrupoReferencia.concepto_id == Concepto.concepto_id)
                    .join(Solicitud, Referencia.solicitud_id == Solicitud.solicitud_id)
                    .join(Delegacion, Solicitud.delegacion_id == Delegacion.delegacion_id)
                    .where(EstadoSistema.codigo.in_(self.states))
                )
                if self.orden_ids:
                    stmt = stmt.where(GrupoReferencia.orden_id.in_(self.orden_ids))

                stmt = stmt.order_by(Referencia.fecha_generacion.desc())
                results = session.execute(stmt).all()

                for r in results:
                    self.raw_data.append({
                        "referencia_portal": r.referencia_portal,
                        "rfc": r.rfc,
                        "razon_social": r.razon_social,
                        "concepto_nombre": r.concepto_nombre,
                        "delegacion_nombre": r.delegacion_nombre,
                        "estado_codigo": r.estado_codigo,
                        "importe": r.importe,
                        "fecha_generacion": r.fecha_generacion
                    })
            self._populate_table(self.raw_data)
        except Exception as e:
            print("Error loading details for ErrorDetailDialog:", e)

    def _populate_table(self, data_list):
        table_rows = []
        for r in data_list:
            table_rows.append([
                r["referencia_portal"],
                r["rfc"],
                r["razon_social"],
                r["concepto_nombre"],
                r["delegacion_nombre"],
                r["estado_codigo"],
                f"${float(r['importe']):,.2f}" if r.get("importe") is not None else "$0.00",
                r["fecha_generacion"].strftime("%Y-%m-%d %H:%M:%S") if r.get("fecha_generacion") else ""
            ])
        self.table.populate_rows(table_rows)

    def _on_search_changed(self, text):
        query = text.strip().lower()
        if not query:
            self._populate_table(self.raw_data)
            return

        filtered = []
        for r in self.raw_data:
            if (query in r["referencia_portal"].lower() or 
                query in r["rfc"].lower() or 
                query in r["razon_social"].lower() or 
                query in r["concepto_nombre"].lower() or 
                query in r["delegacion_nombre"].lower()):
                filtered.append(r)
        self._populate_table(filtered)

    def _export_to_excel(self):
        from PySide6.QtWidgets import QFileDialog
        from sar.src.ui.design_system.components import GLMessageBox as QMessageBox
        import openpyxl

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exportar a Excel", f"{self.title_text}.xlsx", "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Detalle"

            headers = ["Folio Referencia", "RFC Empresa", "Razón Social", "Concepto", "Delegación", "Estado", "Importe", "Fecha Generación"]
            ws.append(headers)

            for r in self.raw_data:
                ws.append([
                    r["referencia_portal"],
                    r["rfc"],
                    r["razon_social"],
                    r["concepto_nombre"],
                    r["delegacion_nombre"],
                    r["estado_codigo"],
                    float(r["importe"]) if r["importe"] is not None else 0.0,
                    r["fecha_generacion"].strftime("%Y-%m-%d %H:%M:%S") if r["fecha_generacion"] else ""
                ])

            wb.save(file_path)
            QMessageBox.information(
                self, "Exportación Completada", f"Se ha exportado el reporte con éxito a:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"No se pudo exportar el archivo Excel:\n{str(e)}"
            )
