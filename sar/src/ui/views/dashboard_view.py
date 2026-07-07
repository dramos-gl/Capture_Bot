"""Dashboard Main View matching the target design mockup."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLineEdit, QPushButton, QComboBox, QLabel
)
from PySide6.QtCore import Qt, QDateTime, QThread, Signal, QTimer
from sar.src.ui.design_system.components import CustomCard, CustomLabel, StyledDataTable, CustomButton, CustomComboBox
from sar.src.ui.design_system.components.molecules.gl_stat_card import StatCard
from sar.src.ui.design_system.utils.icons import Icons
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.storage.repositories import ProduccionRepository

class DashboardReferencesLoadWorker(QThread):
    """Background worker thread to load dashboard references from the DB dynamically with pagination."""
    result_ready = Signal(list, int) # data, total_count
    error_occurred = Signal(str)
    
    def __init__(self, db_connector, limit: int, offset: int, search_text: str, orden_ids: list = None):
        super().__init__()
        self.db_connector = db_connector
        self.limit = limit
        self.offset = offset
        self.search_text = search_text
        self.orden_ids = orden_ids
        
    def run(self):
        try:
            with self.db_connector.get_session() as session:
                repo = ProduccionRepository(session)
                res, total_count = repo.get_referencias_paginated(
                    limit=self.limit,
                    offset=self.offset,
                    search_text=self.search_text,
                    estado_filter="Todos",
                    orden_ids=self.orden_ids
                )
                self.result_ready.emit(res, total_count)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(str(e))

class DashboardView(QWidget):
    """Refactored Dashboard View reflecting the high-fidelity UI design mockup."""
    
    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        
        self.layout = QVBoxLayout(self)
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
        
        self.lbl_subtitle = CustomLabel("Resumen general del estado de referencias", variant="muted")
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
        self.btn_update = QPushButton(" Actualizar")
        self.btn_update.setObjectName("primaryBtn")
        self.btn_update.setIcon(Icons.refresh())
        self.btn_update.setFixedHeight(36)
        self.btn_update.clicked.connect(self.refresh_data)
        self.header_layout.addWidget(self.btn_update)
        
        self.layout.addLayout(self.header_layout)
        
        # 2. KPI Cards Row (Grid)
        self.kpi_layout = QGridLayout()
        self.kpi_layout.setSpacing(16)
        
        self.card_generadas = StatCard("Total Generadas", "0", "file_text", color_hex=Colors.ACCENT, parent=self)
        self.card_pendientes = StatCard("Pendientes Autorización", "0", "clock", color_hex=Colors.WARNING, parent=self)
        self.card_autorizadas = StatCard("Autorizadas", "0", "shield_check", color_hex=Colors.SUCCESS, parent=self)
        self.card_error = StatCard("Con Error", "0", "alert_triangle", color_hex=Colors.ERROR, parent=self)
        
        self.kpi_layout.addWidget(self.card_generadas, 0, 0)
        self.kpi_layout.addWidget(self.card_pendientes, 0, 1)
        self.kpi_layout.addWidget(self.card_autorizadas, 0, 2)
        self.kpi_layout.addWidget(self.card_error, 0, 3)
        
        self.layout.addLayout(self.kpi_layout)
        
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
        
        self.lbl_table_title = CustomLabel("Últimas Referencias Generadas", variant="subheader")
        self.lbl_table_title.setObjectName("dashboardTableTitle")
        
        self.table_header_layout.addWidget(self.lbl_table_icon)
        self.table_header_layout.addWidget(self.lbl_table_title)
        self.table_header_layout.addStretch()
        
        # Search Box
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Buscar referencia...")
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
        self.table.setMinimumHeight(300)
        self.activity_layout.addWidget(self.table)
        
        # Table Footer Pagination Layout
        self.footer_layout = QHBoxLayout()
        self.footer_layout.setContentsMargins(0, 8, 0, 0)
        
        self.lbl_pagination_info = CustomLabel("Mostrando 0 a 0 de 0 referencias", variant="muted")
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
        
        self.layout.addWidget(self.activity_card)
        self._load_available_orders()
        self.refresh_data()
        
    def refresh_data(self):
        """Fetches latest KPI metrics and launches background thread for paginated references."""
        # Update timestamp label
        self.lbl_datetime.setText(QDateTime.currentDateTime().toString("dd/MM/yyyy  hh:mm AP"))
        
        self._load_available_orders(preserve_selection=True)
        
        try:
            with self.db_connector.get_session() as session:
                repo = ProduccionRepository(session)
                kpis = repo.get_dashboard_kpis(self.selected_orden_ids)
                
                self.card_generadas.set_value(str(kpis.get("total_generadas", 0)))
                self.card_pendientes.set_value(str(kpis.get("pendientes", 0)))
                self.card_autorizadas.set_value(str(kpis.get("autorizadas", 0)))
                self.card_error.set_value(str(kpis.get("con_error", 0)))
        except Exception as e:
            print("Error refreshing dashboard KPIs:", e)
            
        self.refresh_data_references()

    def refresh_data_references(self):
        """Starts background thread to fetch dashboard references."""
        # Cancel active thread if running
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.disconnect()
            self.active_worker.terminate()
            self.active_worker.wait()

        self.lbl_pagination_info.setText("Cargando referencias...")
        self.pagination_widget.setEnabled(False)
        self.cb_page_size.setEnabled(False)

        search_text = self.search_input.text().strip()
        offset = (self.current_page - 1) * self.page_size

        self.active_worker = DashboardReferencesLoadWorker(
            db_connector=self.db_connector,
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
        self.lbl_pagination_info.setText("Error al cargar referencias.")
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
            self.lbl_pagination_info.setText("Mostrando 0 a 0 de 0 referencias")
        else:
            self.lbl_pagination_info.setText(f"Mostrando {start_idx + 1} a {end_idx} de {total_items} referencias")
            
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
            with self.db_connector.get_session() as session:
                repo = ProduccionRepository(session)
                self.todas_las_ordenes = repo.get_ordenes()
                
            if self.todas_las_ordenes:
                valid_ids = {ord["orden_id"] for ord in self.todas_las_ordenes}
                if preserve_selection and self.is_custom_filter and self.selected_orden_ids:
                    self.selected_orden_ids = [oid for oid in self.selected_orden_ids if oid in valid_ids]
                
                if not self.selected_orden_ids or (preserve_selection and not self.is_custom_filter):
                    self.selected_orden_ids = [self.todas_las_ordenes[0]["orden_id"]]
            else:
                self.selected_orden_ids = []
        except Exception as e:
            print("Error loading available orders for dashboard:", e)
            self.todas_las_ordenes = []
            self.selected_orden_ids = []

    def _show_filter_menu(self):
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction
        
        # Load orders if not loaded yet
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
        
        # "Todas" action
        action_all = QAction("Todas las órdenes", menu, checkable=True)
        is_all_selected = len(self.selected_orden_ids) == len(self.todas_las_ordenes) and len(self.todas_las_ordenes) > 0
        action_all.setChecked(is_all_selected)
        
        def toggle_all(checked):
            self.is_custom_filter = True
            if checked:
                self.selected_orden_ids = [ord["orden_id"] for ord in self.todas_las_ordenes]
            else:
                self.selected_orden_ids = []
            self.refresh_data()
            
        action_all.triggered.connect(toggle_all)
        menu.addAction(action_all)
        menu.addSeparator()
        
        # Actions for individual orders
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
                    self.refresh_data()
                return handler
                
            action.triggered.connect(make_toggle_handler(ord["orden_id"]))
            menu.addAction(action)
            
        # Display the menu directly under the filter button
        menu.exec(self.btn_filter.mapToGlobal(self.btn_filter.rect().bottomLeft()))
