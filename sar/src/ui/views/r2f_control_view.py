"""R2F Cancun Recibos y Facturas Admin control panel."""

import os
import subprocess
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QButtonGroup
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl

from sar.src.ui.design_system.components import (
    CustomCard, CustomButton, StyledDataTable, FilterBar, CustomComboBox, CustomLabel,
    GLMessageBox as QMessageBox
)
from sar.src.ui.design_system.utils.icons import Icons
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
    
    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        
        # Main layout is horizontal to accommodate the local Sidebar on the left
        self.main_h_layout = QHBoxLayout(self)
        self.main_h_layout.setContentsMargins(0, 0, 0, 0)
        self.main_h_layout.setSpacing(0)
        
        # 1. LOCAL SIDEBAR CONTAINER
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setFixedWidth(200)
        self.sidebar_frame.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border-right: 1px solid #334155;
            }
            QPushButton {
                background-color: transparent;
                color: #94A3B8;
                border: none;
                padding: 12px 16px;
                text-align: left;
                font-weight: bold;
                font-size: 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #F8FAFC;
            }
            QPushButton:checked {
                background-color: #2563EB;
                color: #FFFFFF;
            }
        """)
        self.sidebar_layout = QVBoxLayout(self.sidebar_frame)
        self.sidebar_layout.setContentsMargins(12, 24, 12, 12)
        self.sidebar_layout.setSpacing(8)
        
        # Sidebar Brand/Title Area
        brand_lbl = CustomLabel("R2F CONTROL", variant="header")
        brand_lbl.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: bold; margin-bottom: 20px; padding-left: 8px;")
        self.sidebar_layout.addWidget(brand_lbl)
        
        # Navigation buttons group (behaves like radio buttons)
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        
        self.btn_nav_todos = QPushButton("📋 Todos los Recibos")
        self.btn_nav_todos.setCheckable(True)
        self.btn_nav_todos.setChecked(True)
        self.btn_nav_todos.clicked.connect(lambda: self._on_sidebar_nav_changed("Todos"))
        self.button_group.addButton(self.btn_nav_todos)
        self.sidebar_layout.addWidget(self.btn_nav_todos)
        
        self.btn_nav_capturados = QPushButton("📥 Capturados / Descargados")
        self.btn_nav_capturados.setCheckable(True)
        self.btn_nav_capturados.clicked.connect(lambda: self._on_sidebar_nav_changed("CAPTURADO"))
        self.button_group.addButton(self.btn_nav_capturados)
        self.sidebar_layout.addWidget(self.btn_nav_capturados)
        
        self.btn_nav_pendientes = QPushButton("⏳ Pendientes Facturar")
        self.btn_nav_pendientes.setCheckable(True)
        self.btn_nav_pendientes.clicked.connect(lambda: self._on_sidebar_nav_changed("PENDIENTE_FACTURAR"))
        self.button_group.addButton(self.btn_nav_pendientes)
        self.sidebar_layout.addWidget(self.btn_nav_pendientes)
        
        self.btn_nav_facturados = QPushButton("🧾 Facturados")
        self.btn_nav_facturados.setCheckable(True)
        self.btn_nav_facturados.clicked.connect(lambda: self._on_sidebar_nav_changed("FACTURADO"))
        self.button_group.addButton(self.btn_nav_facturados)
        self.sidebar_layout.addWidget(self.btn_nav_facturados)
        
        self.btn_nav_errores = QPushButton("❌ Errores Facturación")
        self.btn_nav_errores.setCheckable(True)
        self.btn_nav_errores.clicked.connect(lambda: self._on_sidebar_nav_changed("ERROR_FACTURA"))
        self.button_group.addButton(self.btn_nav_errores)
        self.sidebar_layout.addWidget(self.btn_nav_errores)
        
        self.sidebar_layout.addStretch()
        self.main_h_layout.addWidget(self.sidebar_frame)
        
        # 2. MAIN CONTENT VIEW
        self.content_widget = QWidget()
        self.layout = QVBoxLayout(self.content_widget)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(24)
        
        # FilterBar search box
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
        # Hiding state combobox because we have it cleanly in the sidebar
        if hasattr(self.filter_bar, 'labeled_combo') and self.filter_bar.labeled_combo:
            self.filter_bar.labeled_combo.hide()
        self.layout.addWidget(self.filter_bar)
        
        # Main Card
        self.card = CustomCard(title="Bandeja de Control de Recibos & Facturas", parent=self)
        
        # Headers matching the Catastrales layout requested
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
        
        self.main_h_layout.addWidget(self.content_widget)
        
        self._current_search_text = ""
        self._current_estado_filter = "Todos"
        
        # Debounce timer for text search (350ms delay) to prevent database flooding while typing
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._on_search_timer_timeout)
        
        self.table.itemChanged.connect(self._on_table_item_changed)
        self.refresh_data()
        
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
        
    def _filter_table_by_state(self, index: int, text_val: str):
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
