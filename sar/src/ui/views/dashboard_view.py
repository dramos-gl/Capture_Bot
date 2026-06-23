"""Dashboard Main View matching the target design mockup."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLineEdit, QPushButton, QComboBox, QLabel
)
from PySide6.QtCore import Qt, QDateTime
from sar.src.ui.design_system.components import CustomCard, CustomLabel, StyledDataTable, CustomButton, CustomComboBox
from sar.src.ui.design_system.components.molecules.gl_stat_card import StatCard
from sar.src.ui.design_system.utils.icons import Icons
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.storage.repositories import ProduccionRepository

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
        self.page_size = 50
        
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
        self.cb_page_size.addItems(["10 por página", "25 por página", "50 por página"])
        self.cb_page_size.setFixedWidth(120)
        self.cb_page_size.setCurrentIndex(2) # Default to 50 por página
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
        
        self.layout.addWidget(self.activity_card)
        self.refresh_data()
        
    def refresh_data(self):
        """Fetches latest KPI metrics and recent references from DB."""
        # Update timestamp label
        self.lbl_datetime.setText(QDateTime.currentDateTime().toString("dd/MM/yyyy  hh:mm AP"))
        
        try:
            with self.db_connector.get_session() as session:
                repo = ProduccionRepository(session)
                kpis = repo.get_dashboard_kpis()
                
                self.card_generadas.set_value(str(kpis.get("total_generadas", 0)))
                self.card_pendientes.set_value(str(kpis.get("pendientes", 0)))
                self.card_autorizadas.set_value(str(kpis.get("autorizadas", 0)))
                self.card_error.set_value(str(kpis.get("con_error", 0)))
                
                # Fetch up to 500 references for dynamic pagination
                self.all_data = repo.get_referencias(limit=500)
                self.current_page = 1
                self._apply_data_filters_and_pagination()
        except Exception as e:
            print("Error refreshing dashboard data:", e)
            
    def _on_search_changed(self, text):
        """Filters dashboard data and updates pagination."""
        self.current_page = 1
        self._apply_data_filters_and_pagination()
        
    def _on_page_size_changed(self, text):
        """Handles page size combo selection changes."""
        if "10" in text:
            self.page_size = 10
        elif "25" in text:
            self.page_size = 25
        elif "50" in text:
            self.page_size = 50
        self.current_page = 1
        self._apply_data_filters_and_pagination()
        
    def _apply_data_filters_and_pagination(self):
        """Applies real-time search queries and updates data model & views for the current page."""
        search_text = self.search_input.text().lower().strip()
        
        # 1. Filter data based on search text
        self.filtered_data = []
        for ref in self.all_data:
            match = False
            if not search_text:
                match = True
            else:
                if (search_text in str(ref["referencia_id"]).lower() or
                    search_text in str(ref["consecutivo_grupo"]).lower() or
                    search_text in ref["referencia_portal"].lower() or
                    search_text in f"${ref['importe']}".lower() or
                    search_text in ref["fecha_generacion"].lower() or
                    search_text in ref["estado"].lower()):
                    match = True
            if match:
                self.filtered_data.append(ref)
                
        # 2. Paginate filtered data
        total_items = len(self.filtered_data)
        total_pages = max(1, (total_items + self.page_size - 1) // self.page_size)
        
        if self.current_page > total_pages:
            self.current_page = total_pages
        if self.current_page < 1:
            self.current_page = 1
            
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, total_items)
        
        page_data = self.filtered_data[start_idx:end_idx]
        
        # 3. Populate Table
        data_rows = []
        for ref in page_data:
            data_rows.append([
                str(ref["referencia_id"]),
                str(ref["consecutivo_grupo"]),
                ref["referencia_portal"],
                f"${ref['importe']}" if ref['importe'] else "-",
                ref["fecha_generacion"],
                ref["estado"]
            ])
        self.table.populate_rows(data_rows)
        
        # 4. Update Footer Info
        if total_items == 0:
            self.lbl_pagination_info.setText("Mostrando 0 a 0 de 0 referencias")
        else:
            self.lbl_pagination_info.setText(f"Mostrando {start_idx + 1} a {end_idx} de {total_items} referencias")
            
        # 5. Redraw Pagination Buttons
        # Clear layout
        while self.pag_btn_layout.count():
            item = self.pag_btn_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
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
        self._apply_data_filters_and_pagination()
