"""Referencias View."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QPushButton
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from sar.src.services.referencias_service import ReferenciasService
from sar.src.ui.design_system.components import CustomCard, CustomButton, StyledDataTable, FilterBar, CustomComboBox, CustomLabel, KeepOpenMenu

class ReferencesLoadWorker(QThread):
    """Background worker thread to load references from the DB dynamically with pagination."""
    result_ready = Signal(list, int) # data, total_count
    error_occurred = Signal(str)
    
    def __init__(self, referencias_service, limit: int, offset: int, search_text: str, estado_filter: str, orden_ids: list = None):
        super().__init__()
        self.referencias_service = referencias_service
        self.limit = limit
        self.offset = offset
        self.search_text = search_text
        self.estado_filter = estado_filter
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
                estado_filter=self.estado_filter,
                orden_ids=self.orden_ids
            )
            if not self._is_cancelled:
                self.result_ready.emit(res, total_count)
        except Exception as e:
            if not self._is_cancelled:
                import traceback
                traceback.print_exc()
                self.error_occurred.emit(str(e))

class ReferenciasView(QWidget):
    """View to consult the final generated Referencias."""
    
    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.referencias_service = ReferenciasService(self.db_connector)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(24)
        
        # Filtros
        self.filter_bar = FilterBar(
            search_placeholder="Buscar por referencia, consecutivo...",
            state_options=["Todos", "GENERADA", "AUTORIZADA", "RECHAZADA", "EXPIRADA"],
            on_search=self._filter_table_by_text,
            on_state_change=self._filter_table_by_state,
            on_action=self.refresh_data,
            action_icon_name="actualizar",
            action_tooltip="Actualizar Referencias",
            parent=self
        )
        self.layout.addWidget(self.filter_bar)
        
        # Main Card for the Data Table
        self.card = CustomCard(title="Producción de Referencias", parent=self)
        
        # Table Organism
        headers = ["✔", "ID", "Consecutivo", "Referencia", "Importe", "Folio Orden", "Grupo", "Empresa", "Concepto", "Delegación", "Estado", "Procesado Por", "Fecha Gen.", "Vigencia"]
        self.table = StyledDataTable(headers, parent=self)
        self.table.setMinimumHeight(200)
        self.table.setMinimumWidth(200)
        self.table.setColumnHidden(1, True) # Ocultamos el ID Interno
        
        self.card.add_widget(self.table)
        
        # Pagination state
        self.current_page = 1
        self.page_size = 200
        self.all_data = []
        self.total_items = 0
        self.active_worker = None
        
        # Table Footer Pagination Layout
        self.footer_layout = QHBoxLayout()
        self.footer_layout.setContentsMargins(0, 8, 0, 0)
        
        self.lbl_pagination_info = CustomLabel("Mostrando 0 a 0 de 0 referencias", variant="muted")
        self.lbl_pagination_info.setObjectName("referenciasPaginationInfo")
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
        self.card.layout.addLayout(self.footer_layout)
        
        # Action Buttons Layout
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        
        self.btn_marcar_visibles = CustomButton("Marcar Visibles", is_secondary=True)
        self.btn_marcar_visibles.clicked.connect(self._on_marcar_visibles)
        
        self.btn_estado = CustomButton("Cambiar Estado")
        self.btn_estado.clicked.connect(self._on_cambiar_estado)
        
        self.btn_detalle = CustomButton("Ver Detalle", is_secondary=True)
        self.btn_detalle.clicked.connect(self._on_ver_detalle)
        
        self.btn_pdf = CustomButton("Ver PDF", is_secondary=True)
        self.btn_pdf.clicked.connect(self._on_ver_pdf)
        
        actions_layout.addWidget(self.btn_marcar_visibles)
        actions_layout.addWidget(self.btn_estado)
        actions_layout.addWidget(self.btn_detalle)
        actions_layout.addWidget(self.btn_pdf)
        
        self.card.layout.addLayout(actions_layout)
        self.layout.addWidget(self.card)
        
        self._current_search_text = ""
        self._current_estado_filter = "Todos"
        self.selected_orden_ids = []
        self.todas_las_ordenes = []
        self.is_custom_filter = False
        
        # Add order filter button to FilterBar layout
        from sar.src.ui.design_system.utils.icons import Icons
        self.btn_filter_orden = CustomButton("", is_secondary=True)
        self.btn_filter_orden.setIcon(Icons.filter_icon("#475569"))
        self.btn_filter_orden.setFixedSize(36, 36)
        self.btn_filter_orden.setToolTip("Filtrar por Orden")
        self.btn_filter_orden.clicked.connect(self._show_order_filter_menu)
        
        self.filter_bar.layout().insertWidget(self.filter_bar.layout().count() - 1, self.btn_filter_orden, alignment=Qt.AlignmentFlag.AlignBottom)
        
        # Debounce timer for text search (350ms delay) to prevent database flooding while typing
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._on_search_timer_timeout)
        
        self.table.itemChanged.connect(self._on_table_item_changed)
        
        self._load_available_orders()
        self.refresh_data()
        
    def _get_selected_referencia_ids(self) -> list[int]:
        """Obtiene las referencias marcadas por checkbox, o la seleccionada si no hay checkboxes marcados."""
        from PySide6.QtCore import Qt
        ids = []
        for row in range(self.table.rowCount()):
            item_check = self.table.item(row, 0)
            if item_check and item_check.checkState() == Qt.CheckState.Checked:
                ids.append(int(self.table.item(row, 1).text()))
                
        if not ids:
            # Fallback a selección de fila única
            selected = self.table.selectedItems()
            if selected:
                row = selected[0].row()
                ids.append(int(self.table.item(row, 1).text()))
                
        return ids

    def _on_marcar_visibles(self):
        """Marca o desmarca las casillas de todas las filas que actualmente son visibles en la tabla."""
        from PySide6.QtCore import Qt
        
        # Determinar si hay alguna fila visible marcada
        any_checked = False
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                item_check = self.table.item(row, 0)
                if item_check and item_check.checkState() == Qt.CheckState.Checked:
                    any_checked = True
                    break
                    
        target_state = Qt.CheckState.Unchecked if any_checked else Qt.CheckState.Checked
        action_name = "desmarcado" if any_checked else "marcado"
        
        self.table.blockSignals(True)
        count = 0
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                item_check = self.table.item(row, 0)
                if item_check:
                    item_check.setCheckState(target_state)
                    count += 1
        self.table.blockSignals(False)
        
        self.update_marcar_button_text()
        QMessageBox.information(self, "Selección", f"Se han {action_name} {count} referencias visibles.")

    def _on_table_item_changed(self, item):
        if item.column() == 0:
            self.update_marcar_button_text()

    def update_marcar_button_text(self):
        from PySide6.QtCore import Qt
        any_checked = False
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                item_check = self.table.item(row, 0)
                if item_check and item_check.checkState() == Qt.CheckState.Checked:
                    any_checked = True
                    break
        if any_checked:
            self.btn_marcar_visibles.setText("Desmarcar Visibles")
        else:
            self.btn_marcar_visibles.setText("Marcar Visibles")

    def _on_cambiar_estado(self):
        # 1. Obtener referencias seleccionadas y validar que estén en PENDIENTE_AUTORIZACION
        selected_ids = []
        for row in range(self.table.rowCount()):
            item_check = self.table.item(row, 0)
            if item_check and item_check.checkState() == Qt.CheckState.Checked:
                state_text = self.table.item(row, 10).text() if self.table.item(row, 10) else ""
                if state_text != "PENDIENTE_AUTORIZACION":
                    QMessageBox.warning(self, "Acción Inválida", "Solo se pueden autorizar o rechazar referencias en estado PENDIENTE_AUTORIZACION.")
                    return
                selected_ids.append(int(self.table.item(row, 1).text()))
                
        if not selected_ids:
            # Fallback a selección de fila única
            selected = self.table.selectedItems()
            if selected:
                row = selected[0].row()
                state_text = self.table.item(row, 10).text() if self.table.item(row, 10) else ""
                if state_text != "PENDIENTE_AUTORIZACION":
                    QMessageBox.warning(self, "Acción Inválida", "Solo se pueden autorizar o rechazar referencias en estado PENDIENTE_AUTORIZACION.")
                    return
                selected_ids.append(int(self.table.item(row, 1).text()))
                
        if not selected_ids:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona al menos una referencia pendiente.")
            return
            
        from PySide6.QtWidgets import QInputDialog
        opciones = ["AUTORIZADA", "RECHAZADA"]
        item, ok = QInputDialog.getItem(self, "Cambiar Estado", f"Selecciona el nuevo estado para {len(selected_ids)} referencias:", opciones, 0, False)
        
        if ok and item:
            try:
                rechazar_restantes = False
                stats = self.referencias_service.get_pending_authorization_stats(selected_ids)
                total_pendientes = stats.get("total_pendientes", 0)
                
                if total_pendientes > 0:
                    remaining_pending = total_pendientes - len(selected_ids)
                    
                    if remaining_pending > 0:
                        # Mostrar diálogo de confirmación personalizado
                        msg_box = QMessageBox(self)
                        msg_box.setWindowTitle("Confirmar Acción Parcial")
                        msg_box.setIcon(QMessageBox.Question)
                        msg_box.setText(
                            f"Ha seleccionado {len(selected_ids)} referencias de un total de {total_pendientes} pendientes en la(s) solicitud(es) vinculada(s).\n\n"
                            f"¿Desea cambiar el estado de las {len(selected_ids)} seleccionadas a {item} y RECHAZAR automáticamente las {remaining_pending} restantes?"
                        )
                        btn_yes = msg_box.addButton("Sí (Procesar y Rechazar Restantes)", QMessageBox.YesRole)
                        btn_no = msg_box.addButton("No (Solo Procesar Seleccionadas)", QMessageBox.NoRole)
                        btn_cancel = msg_box.addButton("Cancelar", QMessageBox.RejectRole)
                        msg_box.setDefaultButton(btn_no)
                        
                        msg_box.exec()
                        clicked = msg_box.clickedButton()
                        
                        if clicked == btn_cancel:
                            return
                        rechazar_restantes = (clicked == btn_yes)
                    else:
                        # Confirmación simple
                        reply = QMessageBox.question(
                            self, "Confirmar Cambio",
                            f"¿Estás seguro de que deseas marcar las {len(selected_ids)} referencias seleccionadas como {item}?",
                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                        )
                        if reply == QMessageBox.No:
                            return

                # Ejecutar actualización transaccional a través del servicio
                self.referencias_service.update_referencias_estado_masivo(selected_ids, item, rechazar_restantes)
                    
                QMessageBox.information(self, "Éxito", f"{len(selected_ids)} referencias cambiadas a {item}.")
                self.refresh_data()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al cambiar estado: {str(e)}")

    def _on_ver_detalle(self):
        ref_ids = self._get_selected_referencia_ids()
        if not ref_ids: return
        QMessageBox.information(self, "Detalle", f"Detalles de la referencia ID: {ref_ids[0]}\n(Funcionalidad en desarrollo)")
        
    def _on_ver_pdf(self):
        ref_ids = self._get_selected_referencia_ids()
        if not ref_ids: return
        QMessageBox.information(self, "PDF", f"Abriendo visor PDF para la referencia ID: {ref_ids[0]}\n(Funcionalidad en desarrollo)")
        
    def refresh_data(self):
        """Starts background thread to fetch data matching filters and current offset."""
        self._load_available_orders(preserve_selection=True)
        # Cancel active thread if running safely
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.cancel()
            try:
                self.active_worker.result_ready.disconnect()
                self.active_worker.error_occurred.disconnect()
            except RuntimeError:
                pass
            self.active_worker.wait()

        # Visual feedback: set pagination info label to loading state
        self.lbl_pagination_info.setText("Cargando referencias desde el servidor...")
        self.pagination_widget.setEnabled(False) # Disable navigation buttons
        self.cb_page_size.setEnabled(False)

        search_text = getattr(self, '_current_search_text', "").strip()
        estado_filter = getattr(self, '_current_estado_filter', "Todos")
        offset = (self.current_page - 1) * self.page_size
        orden_ids = getattr(self, 'selected_orden_ids', [])

        self.active_worker = ReferencesLoadWorker(
            referencias_service=self.referencias_service,
            limit=self.page_size,
            offset=offset,
            search_text=search_text,
            estado_filter=estado_filter,
            orden_ids=orden_ids
        )
        self.active_worker.result_ready.connect(self._on_data_loaded)
        self.active_worker.error_occurred.connect(self._on_load_error)
        self.active_worker.start()

    def _on_data_loaded(self, data, total_count):
        self.all_data = data
        self.filtered_data = data
        self.total_items = total_count
        
        # Restore control states
        self.pagination_widget.setEnabled(True)
        self.cb_page_size.setEnabled(True)

        self._populate_table_and_pagination()

    def _on_load_error(self, err_msg):
        self.pagination_widget.setEnabled(True)
        self.cb_page_size.setEnabled(True)
        self.lbl_pagination_info.setText("Error al cargar datos de referencias.")
        QMessageBox.critical(self, "Error de Conexión", f"No se pudo consultar el servidor de base de datos:\n{err_msg}")

    def _populate_table_and_pagination(self):
        # 1. Populate Table with current page data (which is what we got from the DB query)
        data_rows = []
        for r in self.all_data:
            data_rows.append([
                "", # Checkbox vacio inicial
                str(r["referencia_id"]),
                str(r["consecutivo_grupo"]),
                r["referencia_portal"],
                r["importe"],
                r["folio_orden"],
                str(r["grupo_id"]),
                r["empresa"],
                r["concepto"],
                r["delegacion"],
                r["estado"],
                r["procesado_por"],
                r["fecha_generacion"],
                r["fecha_vigencia"]
            ])
            
        self.table.blockSignals(True)
        self.table.populate_rows(data_rows, checkable_first_col=True)
        self.table.blockSignals(False)
        
        # 2. Calculate indices for info display
        total_items = self.total_items
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + len(self.all_data), total_items)
        
        # Update Footer Info
        if total_items == 0:
            self.lbl_pagination_info.setText("Mostrando 0 a 0 de 0 referencias")
        else:
            self.lbl_pagination_info.setText(f"Mostrando {start_idx + 1} a {end_idx} de {total_items} referencias")
            
        # 3. Redraw Pagination Buttons
        # Clear layout
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
        
        self.update_marcar_button_text()

    def _filter_table_by_text(self, text: str):
        self._current_search_text = text.strip()
        self.current_page = 1
        # Start or reset the single-shot debounce timer
        self.search_timer.start(350)

    def _on_search_timer_timeout(self):
        self.refresh_data()
        
    def _filter_table_by_state(self, state: str):
        self._current_estado_filter = state
        self.current_page = 1
        self.refresh_data()

    def _on_page_size_changed(self, text: str):
        if "50" in text:
            self.page_size = 50
        elif "100" in text:
            self.page_size = 100
        elif "200" in text:
            self.page_size = 200
        self.current_page = 1
        self.refresh_data()

    def _set_page(self, page_num: int):
        self.current_page = page_num
        self.refresh_data()

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
            print("Error loading available orders for references:", e)
            self.todas_las_ordenes = []
            self.selected_orden_ids = []

    def _show_order_filter_menu(self):
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
                
            self.current_page = 1
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
                    self.current_page = 1
                    self.refresh_data()
                return handler
                
            action.triggered.connect(make_toggle_handler(oid))
            menu.addAction(action)
            
        # Display the menu directly under the filter button
        menu.exec(self.btn_filter_orden.mapToGlobal(self.btn_filter_orden.rect().bottomLeft()))
