"""R2F Cancun Recibos y Facturas Admin control panel."""

import os
import subprocess
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QButtonGroup, QLabel, QScrollArea
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QDateTime, QSize
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl

from sar.src.ui.design_system.components import (
    CustomCard, CustomButton, StyledDataTable, FilterBar, CustomComboBox, CustomLabel, NavigationSidebar,
    GLMessageBox as QMessageBox
)
from sar.src.ui.design_system.components.molecules.gl_stat_card import StatCard
from sar.src.ui.design_system.utils.icons import Icons
from sar.src.ui.design_system.tokens.colors import Colors
from cancunbot.src.storage.cancunbot_repos import ReciboCancunRepository

class R2FLoadWorker(QThread):
    """Background worker thread to load R2F Receipts from the DB dynamically with pagination."""
    result_ready = Signal(list, int) # data, total_count
    error_occurred = Signal(str)
    
    def __init__(self, db_connector, limit: int, offset: int, search_text: str, estado_filter: str):
        super().__init__()
        self.db_connector = db_connector
        self.limit = limit
        self.offset = offset
        self.search_text = search_text
        self.estado_filter = estado_filter
        self._is_cancelled = False
        
    def cancel(self):
        self._is_cancelled = True
        
    def run(self):
        try:
            if self._is_cancelled:
                return
            with self.db_connector.get_session() as session:
                repo = ReciboCancunRepository(session)
                res, total_count = repo.get_recibos_paginated(
                    limit=self.limit,
                    offset=self.offset,
                    search_text=self.search_text,
                    estado_filter=self.estado_filter
                )
                
                # Detach entities to dictionary representation to avoid session boundary issues in QThread
                data_list = []
                for r in res:
                    # Resolve status label safely
                    status_lbl = "DESCONOCIDO"
                    if r.estado:
                        status_lbl = r.estado.codigo
                        
                    data_list.append({
                        "recibo_id": r.recibo_id,
                        "folio_electronico": r.folio_electronico or r.folio_pase_caja or "--",
                        "rfc": r.rfc or "--",
                        "contribuyente": r.nombre_contribuyente or "--",
                        "concepto": r.concepto or "--",
                        "total": float(r.total) if r.total else 0.0,
                        "pdf_ruta": r.pdf_ruta,
                        "sm": r.sm or "--",
                        "mz": r.mz or "--",
                        "l": r.l or "--",
                        "estado": status_lbl,
                        "fecha": r.fecha_expedicion.strftime("%Y-%m-%d") if r.fecha_expedicion else "--"
                    })
                
            if not self._is_cancelled:
                self.result_ready.emit(data_list, total_count)
        except Exception as e:
            if not self._is_cancelled:
                self.error_occurred.emit(str(e))


class R2FControlView(QWidget):
    """View to consult and administer the downloaded R2F-Cancún receipts & billing metadata."""
    logout_requested = Signal()
    
    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.setStyleSheet(f"background-color: {Colors.BG_LIGHT}; color: {Colors.TEXT_LIGHT_PRIMARY};")

        # Layout exterior (Sidebar + Área de Contenido + Footer)
        self.main_h_layout = QHBoxLayout(self)
        self.main_h_layout.setContentsMargins(0, 0, 0, 0)
        self.main_h_layout.setSpacing(0)
        
        # 1. SIDEBAR DE NAVEGACIÓN COMPLETO CON HAMBURGUESA ☰
        self.sidebar = NavigationSidebar(self)
        self.sidebar.brand_title.setText("R2F")
        self.sidebar.brand_subtitle.setText("Control de Recibos")
        
        # Omitir explícitamente el botón "Cambiar Tema"
        if hasattr(self.sidebar, "theme_btn") and self.sidebar.theme_btn:
            self.sidebar.theme_btn.hide()
            
        # Conectar señal de logout
        self.sidebar.logout_requested.connect(self.logout_requested.emit)
        
        # Mostrar menú de Cancun / R2F Control
        self.sidebar.show_item("dashboard")
        self.sidebar.show_item("r2f_control")
        self.sidebar.select_item("r2f_control")
        self.sidebar.nav_selected.connect(self._on_sidebar_item_selected)
        
        self.main_h_layout.addWidget(self.sidebar)
        
        # 2. ÁREA PRINCIPAL DE CONTENIDO
        self.content_area = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        # ScrollArea principal para el contenido
        scroll_area = QScrollArea(self.content_area)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QWidget#r2fScrollContent {
                background-color: transparent;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setObjectName("r2fScrollContent")
        self.layout = QVBoxLayout(scroll_content)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(20)
        
        # --- HEADER DE BIENVENIDA / ENCABEZADO SAR ---
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(12)
        
        self.indicator_bar = QFrame(self)
        self.indicator_bar.setFixedWidth(4)
        self.indicator_bar.setFixedHeight(28)
        self.indicator_bar.setObjectName("dashboardIndicatorBar")
        self.header_layout.addWidget(self.indicator_bar)
        
        self.title_text_layout = QVBoxLayout()
        self.title_text_layout.setContentsMargins(0, 0, 0, 0)
        self.title_text_layout.setSpacing(2)
        
        self.lbl_title = CustomLabel("Tablero de Control Operativo R2F", variant="header")
        self.lbl_subtitle = CustomLabel("Resumen general del estado de recibos y facturación", variant="muted")
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
        self.time_layout.addWidget(self.lbl_calendar_icon)
        self.time_layout.addWidget(self.lbl_datetime)
        self.header_layout.addWidget(self.time_widget)
        
        self.btn_update = QPushButton(self)
        self.btn_update.setObjectName("filterBarActionBtn")
        self.btn_update.setIcon(Icons.actualizar("#FFFFFF"))
        self.btn_update.setIconSize(QSize(20, 20))
        self.btn_update.setFixedSize(35, 35)
        self.btn_update.setToolTip("Actualizar Tablero R2F")
        self.btn_update.clicked.connect(self.refresh_data)
        self.header_layout.addWidget(self.btn_update)
        
        self.layout.addLayout(self.header_layout)
        
        # --- FILA DE TARJETAS KPI (StatCards) ---
        self.kpi_widget = QWidget(self)
        self.kpi_widget.setStyleSheet("background: transparent;")
        self.kpi_layout = QHBoxLayout(self.kpi_widget)
        self.kpi_layout.setContentsMargins(0, 0, 0, 0)
        self.kpi_layout.setSpacing(10)
        
        self.card_total = StatCard("Total Descargados", "0", "file_text", color_hex=Colors.CHART_EMERALD_DARK, parent=self.kpi_widget)
        self.card_pendientes = StatCard("Pendientes Facturar", "0", "clock", color_hex=Colors.CHART_AMBER, parent=self.kpi_widget)
        self.card_facturados = StatCard("Facturados", "0", "shield_check", color_hex=Colors.CHART_TEAL, parent=self.kpi_widget)
        self.card_errores = StatCard("Errores Factura", "0", "x_circle", color_hex=Colors.CHART_CORAL, parent=self.kpi_widget)
        self.card_invalidos = StatCard("Invalidos", "0", "alert_triangle", color_hex=Colors.ERROR, parent=self.kpi_widget)
        self.card_lotes = StatCard("Lotes Activos", "0", "list_icon", color_hex=Colors.CHART_BLUE, parent=self.kpi_widget)
        
        self.kpi_layout.addWidget(self.card_total, stretch=1)
        self.kpi_layout.addWidget(self.card_pendientes, stretch=1)
        self.kpi_layout.addWidget(self.card_facturados, stretch=1)
        self.kpi_layout.addWidget(self.card_errores, stretch=1)
        self.kpi_layout.addWidget(self.card_invalidos, stretch=1)
        self.kpi_layout.addWidget(self.card_lotes, stretch=1)
        
        self.layout.addWidget(self.kpi_widget)
        
        # --- BANDEJA PRINCIPAL DE REGISTROS ---
        self.filter_bar = FilterBar(
            search_placeholder="Buscar por folio, RFC, contribuyente...",
            state_options=["Todos", "CAPTURADO", "PENDIENTE_FACTURAR", "FACTURANDO", "FACTURADO", "ERROR_FACTURA"],
            on_search=self._filter_table_by_text,
            on_state_change=self._filter_table_by_state,
            on_action=self.refresh_data,
            action_icon_name="actualizar",
            action_tooltip="Actualizar Registros",
            parent=self
        )
        self.layout.addWidget(self.filter_bar)
        
        # Main Card
        self.card = CustomCard(title="Bandeja de Control de Recibos & Facturas", parent=self)
        
        headers = ["✔", "ID", "Folio/Referencia", "RFC", "Contribuyente", "Concepto de Cobro", "SM", "MZ", "L", "Total", "Fecha", "Estado"]
        self.table = StyledDataTable(headers, parent=self)
        self.table.setMinimumHeight(200)
        self.table.setMinimumWidth(200)
        self.table.setColumnHidden(1, True) # Ocultar ID
        
        self.card.add_widget(self.table)
        
        # Pagination
        self.current_page = 1
        self.page_size = 200
        self.all_data = []
        self.total_items = 0
        self.active_worker = None
        
        self.footer_layout = QHBoxLayout()
        self.footer_layout.setContentsMargins(0, 8, 0, 0)
        
        self.lbl_pagination_info = CustomLabel("Mostrando 0 a 0 de 0 registros", variant="muted")
        self.footer_layout.addWidget(self.lbl_pagination_info)
        self.footer_layout.addStretch()
        
        self.cb_page_size = CustomComboBox(self)
        self.cb_page_size.addItems(["50 por página", "100 por página", "200 por página"])
        self.cb_page_size.setFixedWidth(120)
        self.cb_page_size.setCurrentIndex(2) # Default 200
        self.cb_page_size.currentTextChanged.connect(self._on_page_size_changed)
        self.footer_layout.addWidget(self.cb_page_size)
        
        self.pagination_widget = QWidget(self)
        self.pagination_widget.setStyleSheet("background: transparent;")
        self.pag_btn_layout = QHBoxLayout(self.pagination_widget)
        self.pag_btn_layout.setContentsMargins(0, 0, 0, 0)
        self.pag_btn_layout.setSpacing(4)
        
        self.footer_layout.addWidget(self.pagination_widget)
        self.card.layout.addLayout(self.footer_layout)
        
        # Control Action buttons
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        
        self.btn_marcar_visibles = CustomButton("Marcar Visibles", is_secondary=True)
        self.btn_marcar_visibles.clicked.connect(self._on_marcar_visibles)
        
        self.btn_estado = CustomButton("Liberar para Factura")
        self.btn_estado.clicked.connect(self._on_liberar_factura)
        
        self.btn_pdf = CustomButton("Ver PDF Recibo", is_secondary=True)
        self.btn_pdf.clicked.connect(self._on_ver_pdf)
        
        actions_layout.addWidget(self.btn_marcar_visibles)
        actions_layout.addWidget(self.btn_estado)
        actions_layout.addWidget(self.btn_pdf)
        
        self.card.layout.addLayout(actions_layout)
        self.layout.addWidget(self.card)
        
        scroll_area.setWidget(scroll_content)
        self.content_layout.addWidget(scroll_area, stretch=1)
        
        # Discreet right-aligned footer bar (Pie de página global SAR)
        self.global_footer_bar = QWidget(self.content_area)
        self.global_footer_layout = QHBoxLayout(self.global_footer_bar)
        self.global_footer_layout.setContentsMargins(16, 2, 20, 6)
        self.global_footer_layout.setSpacing(0)
        
        self.lbl_global_footer = QLabel("Sistema de Administración de Recibos & Facturas | R2F | v1.0.0", self.global_footer_bar)
        self.lbl_global_footer.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_global_footer.setStyleSheet("color: #94A3B8; font-size: 10px; background: transparent;")
        
        self.global_footer_layout.addStretch()
        self.global_footer_layout.addWidget(self.lbl_global_footer)
        self.content_layout.addWidget(self.global_footer_bar)
        
        self.main_h_layout.addWidget(self.content_area, stretch=1)
        
        self._current_search_text = ""
        self._current_estado_filter = "Todos"
        
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._on_search_timer_timeout)
        
        self.table.itemChanged.connect(self._on_table_item_changed)
        self.refresh_data()
        
    def _on_sidebar_item_selected(self, key: str):
        """Maneja la selección de ítems en el sidebar principal."""
        pass
        
    def _on_sidebar_nav_changed(self, state_code: str):
        """Callback to handle clicks on the local sidebar items."""
        self._current_estado_filter = state_code
        self.current_page = 1
        self.refresh_data()
        
    def refresh_data(self):
        """Launches pagination worker to load matching receipt items."""
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.cancel()
            try:
                self.active_worker.result_ready.disconnect()
                self.active_worker.error_occurred.disconnect()
            except RuntimeError:
                pass
            self.active_worker.wait()
            
        offset = (self.current_page - 1) * self.page_size
        
        self.active_worker = R2FLoadWorker(
            self.db_connector,
            limit=self.page_size,
            offset=offset,
            search_text=self._current_search_text,
            estado_filter=self._current_estado_filter
        )
        self.active_worker.result_ready.connect(self._on_data_loaded)
        self.active_worker.error_occurred.connect(self._on_load_error)
        self.active_worker.start()
        
    def _on_data_loaded(self, data, total_count):
        self.all_data = data
        self.total_items = total_count
        self._update_table_content()
        
    def _on_load_error(self, err_msg):
        QMessageBox.critical(self, "Error al Cargar", f"Ocurrió un error al cargar los recibos de la base de datos:\n{err_msg}")
        
    def _update_table_content(self):
        data_rows = []
        for item in self.all_data:
            data_rows.append([
                "",  # Primer columna para checkbox
                str(item["recibo_id"]),
                item["folio_electronico"],
                item["rfc"],
                item["contribuyente"],
                item["concepto"],
                item["sm"],
                item["mz"],
                item["l"],
                f"${item['total']:,.2f}",
                item["fecha"],
                item["estado"]
            ])
            
        self.table.blockSignals(True)
        self.table.populate_rows(data_rows, checkable_first_col=True)
        self.table.blockSignals(False)
        self._update_pagination_footer()
        self.update_marcar_button_text()
        
    def _update_pagination_footer(self):
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + len(self.all_data), self.total_items)
        
        if self.total_items == 0:
            self.lbl_pagination_info.setText("Mostrando 0 a 0 de 0 registros")
        else:
            self.lbl_pagination_info.setText(f"Mostrando {start_idx + 1} a {end_idx} de {self.total_items} registros")
            
        # Redraw
        while self.pag_btn_layout.count():
            it = self.pag_btn_layout.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()
                
        total_pages = max(1, (self.total_items + self.page_size - 1) // self.page_size)
        
        def add_nav_btn(text, target, enabled):
            btn = QPushButton(text)
            btn.setObjectName("paginationNavBtn")
            btn.setEnabled(enabled)
            btn.clicked.connect(lambda: self._set_page(target))
            self.pag_btn_layout.addWidget(btn)
            
        def add_page_btn(num, active):
            btn = QPushButton(str(num))
            btn.setObjectName("paginationActivePageBtn" if active else "paginationPageBtn")
            btn.clicked.connect(lambda: self._set_page(num))
            self.pag_btn_layout.addWidget(btn)
            
        start_p = max(1, self.current_page - 2)
        end_p = min(total_pages, start_p + 4)
        if end_p - start_p < 4:
            start_p = max(1, end_p - 4)
            
        add_nav_btn("<<", 1, self.current_page > 1)
        add_nav_btn("<", self.current_page - 1, self.current_page > 1)
        for p in range(start_p, end_p + 1):
            add_page_btn(p, p == self.current_page)
        add_nav_btn(">", self.current_page + 1, self.current_page < total_pages)
        add_nav_btn(">>", total_pages, self.current_page < total_pages)
        
    def _set_page(self, num):
        self.current_page = num
        self.refresh_data()
        
    def _filter_table_by_text(self, text_val: str):
        self._current_search_text = text_val
        self.search_timer.start(350)
        
    def _on_search_timer_timeout(self):
        self.current_page = 1
        self.refresh_data()
        
    def _filter_table_by_state(self, text_val: str, index: int = 0):
        self._current_estado_filter = text_val
        self.current_page = 1
        self.refresh_data()
        
    def _on_page_size_changed(self, text_val: str):
        try:
            self.page_size = int(text_val.split()[0])
            self.current_page = 1
            self.refresh_data()
        except ValueError:
            pass
            
    def _on_table_item_changed(self, item):
        if item.column() == 0:
            self.update_marcar_button_text()
            
    def update_marcar_button_text(self):
        any_checked = False
        for row in range(self.table.rowCount()):
            item_check = self.table.item(row, 0)
            if item_check and item_check.checkState() == Qt.CheckState.Checked:
                any_checked = True
                break
        self.btn_marcar_visibles.setText("Desmarcar Visibles" if any_checked else "Marcar Visibles")
        
    def _on_marcar_visibles(self):
        any_checked = False
        for row in range(self.table.rowCount()):
            item_check = self.table.item(row, 0)
            if item_check and item_check.checkState() == Qt.CheckState.Checked:
                any_checked = True
                break
                
        target_state = Qt.CheckState.Unchecked if any_checked else Qt.CheckState.Checked
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            item_check = self.table.item(row, 0)
            if item_check:
                item_check.setCheckState(target_state)
        self.table.blockSignals(False)
        self.update_marcar_button_text()
        
    def _get_selected_ids(self) -> list[int]:
        ids = []
        for row in range(self.table.rowCount()):
            item_check = self.table.item(row, 0)
            if item_check and item_check.checkState() == Qt.CheckState.Checked:
                ids.append(int(self.table.item(row, 1).text()))
        if not ids:
            selected = self.table.selectedItems()
            if selected:
                row = selected[0].row()
                ids.append(int(self.table.item(row, 1).text()))
        return ids
        
    def _on_liberar_factura(self):
        """Forces updating selected receipts status back to PENDIENTE_FACTURAR to re-enqueue for billing."""
        selected_ids = self._get_selected_ids()
        if not selected_ids:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona al menos un recibo para liberar.")
            return
            
        reply = QMessageBox.question(
            self, "Liberar para Factura",
            f"¿Estás seguro de que deseas liberar {len(selected_ids)} recibos seleccionados?\n"
            "Esto colocará su estado como PENDIENTE_FACTURAR para que sean tomados por el Bot de Facturas.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
            
        try:
            with self.db_connector.get_session() as session:
                repo = ReciboCancunRepository(session)
                for rid in selected_ids:
                    repo.update_status(rid, "PENDIENTE_FACTURAR")
                session.commit()
            QMessageBox.information(self, "Proceso Completado", f"Se han liberado {len(selected_ids)} recibos con éxito.")
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron liberar los registros:\n{e}")
            
    def _on_ver_pdf(self):
        """Opens the physical PDF receipt file in the OS default viewer."""
        selected_ids = self._get_selected_ids()
        if not selected_ids or len(selected_ids) > 1:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona un único registro para visualizar su archivo PDF.")
            return
            
        recibo_id = selected_ids[0]
        pdf_path_str = None
        
        # Encontrar ruta
        for item in self.all_data:
            if item["recibo_id"] == recibo_id:
                pdf_path_str = item["pdf_ruta"]
                break
                
        if not pdf_path_str or not os.path.exists(pdf_path_str):
            QMessageBox.critical(self, "Archivo No Encontrado", f"El archivo PDF del recibo no existe o la ruta es inválida:\n{pdf_path_str}")
            return
            
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path_str))
        except Exception as e:
            QMessageBox.critical(self, "Error al Abrir", f"No se pudo abrir el archivo PDF:\n{e}")
