"""Orders Management View."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout
)
from PySide6.QtCore import Qt
from sar.src.ui.design_system.components import (
    CustomCard, CustomLabel, CustomButton, InteractiveGrid, CustomInput, CustomComboBox, FilterBar,
    GLMessageBox as QMessageBox
)
from PySide6.QtCore import QThread, Signal
from sar.src.services.ordenes_ui_service import OrdenesUIService
from sar.src.ui.design_system.components.molecules.gl_labeled_input import LabeledInput

class OrdersLoadWorker(QThread):
    """Background worker thread to load orders from the DB/API dynamically."""
    result_ready = Signal(list)
    error_occurred = Signal(str)
    
    def __init__(self, ordenes_ui_service):
        super().__init__()
        self.ordenes_ui_service = ordenes_ui_service
        self._is_cancelled = False
        
    def cancel(self):
        self._is_cancelled = True
        
    def run(self):
        try:
            if self._is_cancelled:
                return
            res = self.ordenes_ui_service.get_ordenes()
            if not self._is_cancelled:
                self.result_ready.emit(res)
        except Exception as e:
            if not self._is_cancelled:
                self.error_occurred.emit(str(e))

class OrdersView(QWidget):
    """View to manage and create Orders."""
    
    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()
        self.ordenes_ui_service = OrdenesUIService(self.db_connector)
        self.active_worker = None
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(24)
        
        # Header layout with Title (NO Subtitle, NO Help button)
        header_text_layout = QVBoxLayout()
        self.lbl_title = CustomLabel("Gestión de Órdenes", variant="header")
        self.lbl_title.setObjectName("orderViewTitle")
        header_text_layout.addWidget(self.lbl_title)
        self.layout.addLayout(header_text_layout)
        
        from PySide6.QtWidgets import QTabWidget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: transparent; }
        """)
        
        # Hide physical tab bar
        self.tabs.tabBar().hide()
        
        self.tab_historial = QWidget()
        self.tab_nueva = QWidget()
        
        self.tabs.addTab(self.tab_nueva, "Capturar Nueva Orden")
        self.tabs.addTab(self.tab_historial, "Órdenes Capturadas")
        
        self.layout.addWidget(self.tabs)
        
        self._setup_historial_tab()
        self._setup_nueva_orden_tab()
        
        # Pre-load catalogs and data
        self._current_search_text = ""
        self._current_estado_filter = "Todas"
        
        # Edit mode state variables
        self._edit_mode = False
        self._editing_order_id = None
        self._editing_folio = None

        self._load_catalogs()
        self.refresh_historial()
        
        # Agregamos el primer renglón por defecto en la nueva orden
        self.grid.add_row()
        
    def _setup_historial_tab(self):
        from sar.src.ui.design_system.components import StyledDataTable, CustomCard
        layout = QVBoxLayout(self.tab_historial)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Filter Bar
        self.filter_bar_historial = FilterBar(
            search_placeholder="Buscar por folio, descripción, estado...",
            state_options=["Todas", "BORRADOR", "PENDIENTE", "EN_PROCESO", "PENDIENTE_AUTORIZACION", "COMPLETADA", "AUTORIZADA", "RECHAZADA", "CANCELADA"],
            on_search=self._on_historial_search,
            on_state_change=self._on_historial_state_change,
            on_action=self.refresh_historial,
            action_icon_name="actualizar",
            action_tooltip="Actualizar Historial",
            parent=self
        )
        layout.addWidget(self.filter_bar_historial)
        
        # Main Card for the Data Table
        self.historial_card = CustomCard(parent=self)
        
        headers = ["ID", "Folio", "Descripción", "Estado", "Creador", "Fecha Creación", "Total Solicitadas", "Total Generadas"]
        self.table_historial = StyledDataTable(headers, parent=self)
        self.table_historial.setColumnHidden(0, True) # Ocultar ID interno
        self.table_historial.cellDoubleClicked.connect(self._on_row_double_clicked)
        self.table_historial.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_historial.customContextMenuRequested.connect(self._show_context_menu)
        
        self.historial_card.add_widget(self.table_historial)
        
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        
        self.btn_autorizar_orden = CustomButton("Autorizar Orden Completa")
        self.btn_autorizar_orden.clicked.connect(self._on_autorizar_orden)
        
        self.btn_rechazar_orden = CustomButton("Rechazar Orden Completa", is_secondary=True)
        self.btn_rechazar_orden.clicked.connect(self._on_rechazar_orden)
        
        self.btn_cancelar_orden = CustomButton("Cancelar Orden", is_secondary=True)
        self.btn_cancelar_orden.clicked.connect(self._on_cancelar_orden)
        
        self.btn_editar_orden = CustomButton("Editar Orden", is_secondary=True)
        self.btn_editar_orden.clicked.connect(self._on_editar_orden_clicked)
        
        actions_layout.addWidget(self.btn_autorizar_orden)
        actions_layout.addWidget(self.btn_rechazar_orden)
        actions_layout.addWidget(self.btn_cancelar_orden)
        actions_layout.addWidget(self.btn_editar_orden)
        
        self.historial_card.layout.addLayout(actions_layout)
        
        layout.addWidget(self.historial_card)

    def _setup_nueva_orden_tab(self):
        layout = QVBoxLayout(self.tab_nueva)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # New Order Card initialized without title so we can construct a custom header
        from PySide6.QtWidgets import QFrame
        self.card = CustomCard(parent=self)
        card_layout = self.card.layout
        card_layout.setSpacing(16)
        
        # Build custom header for the card
        card_header_layout = QHBoxLayout()
        
        card_title_vbox = QVBoxLayout()
        self.lbl_card_title = CustomLabel("Configuración de la Orden", variant="subheader")
        self.lbl_card_title.setObjectName("cardHeaderTitle")
        self.lbl_card_subtitle = CustomLabel("Completa los datos para crear una nueva orden", variant="muted")
        self.lbl_card_subtitle.setObjectName("cardHeaderSubtitle")
        card_title_vbox.addWidget(self.lbl_card_title)
        card_title_vbox.addWidget(self.lbl_card_subtitle)
        card_header_layout.addLayout(card_title_vbox)
        card_header_layout.addStretch()
        
        # Previous total box (only shown in edit mode)
        self.total_anterior_frame = QFrame()
        self.total_anterior_frame.setObjectName("totalAnteriorFrame")
        total_anterior_layout = QHBoxLayout(self.total_anterior_frame)
        total_anterior_layout.setContentsMargins(6, 6, 6, 6)
        total_anterior_layout.setSpacing(12)
        
        lbl_tot_ant_text = CustomLabel("Total Anterior:", variant="body")
        lbl_tot_ant_text.setObjectName("totalAnteriorTitle")
        self.lbl_tot_ant_val = CustomLabel("0", variant="header")
        self.lbl_tot_ant_val.setObjectName("totalAnteriorValue")
        
        total_anterior_layout.addWidget(lbl_tot_ant_text)
        total_anterior_layout.addWidget(self.lbl_tot_ant_val)
        card_header_layout.addWidget(self.total_anterior_frame)
        self.total_anterior_frame.setVisible(False)

        # General total box
        self.total_general_frame = QFrame()
        self.total_general_frame.setObjectName("totalGeneralFrame")
        total_general_layout = QHBoxLayout(self.total_general_frame)
        total_general_layout.setContentsMargins(6, 6, 6, 6)
        total_general_layout.setSpacing(12)
        
        lbl_tot_text = CustomLabel("Total General:", variant="body")
        lbl_tot_text.setObjectName("totalGeneralTitle")
        self.lbl_tot_val = CustomLabel("1", variant="header")
        self.lbl_tot_val.setObjectName("totalGeneralValue")
        
        total_general_layout.addWidget(lbl_tot_text)
        total_general_layout.addWidget(self.lbl_tot_val)
        card_header_layout.addWidget(self.total_general_frame)
        
        card_layout.addLayout(card_header_layout)
        
        # Two-column input layout: Municipio on the left, Descripción on the right
        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(16)
        
        # Left side: Municipio
        mun_layout = QVBoxLayout()
        lbl_mun_title = CustomLabel("Municipio de Acceso (Tributanet)", variant="body")
        lbl_mun_title.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        self.combo_municipio = CustomComboBox()
        self.combo_municipio.setMinimumHeight(35)
        mun_layout.addWidget(lbl_mun_title)
        mun_layout.addWidget(self.combo_municipio)
        
        # Right side: Descripción
        desc_layout = QVBoxLayout()
        lbl_desc_title = CustomLabel("Descripción de la Orden", variant="body")
        lbl_desc_title.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        self.desc_input = CustomInput("Ingresa una descripción...")
        self.desc_input.setMinimumHeight(35)
        desc_layout.addWidget(lbl_desc_title)
        desc_layout.addWidget(self.desc_input)
        
        inputs_layout.addLayout(mun_layout, stretch=1)
        inputs_layout.addLayout(desc_layout, stretch=1)
        
        card_layout.addLayout(inputs_layout)
        
        # Divider line
        divider = QFrame()
        divider.setObjectName("dividerLine")
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        card_layout.addWidget(divider)
        
        # Interactive Grid
        self.grid = InteractiveGrid(self)
        self.grid.data_changed.connect(self._update_summary)
        self.grid.save_triggered.connect(self._on_guardar_orden)
        self.grid.cancel_triggered.connect(self._on_cancelar_edicion)
        card_layout.addWidget(self.grid)
        
        layout.addWidget(self.card)
        
    def _update_summary(self):
        data = self.grid.get_all_data()
        
        # Update badge count in grid header
        self.grid.lbl_badge.setText(str(len(data)))
        
        # Update total general value
        total_general = 0
        for row in data:
            if row.get("rfc_id") and row.get("concepto_id"):
                total_general += row.get("cantidad", 0)
        self.lbl_tot_val.setText(str(total_general))
            
    def _load_catalogs(self):
        try:
            data = self.ordenes_ui_service.get_catalogos()
            rfcs = [(r["rfc_id"], r["rfc"]) for r in data["rfcs"]]
            conceptos = [(c["concepto_id"], c["nombre"]) for c in data["conceptos"]]
            delegaciones = [(d["delegacion_id"], d["nombre"]) for d in data["delegaciones"]]
            
            self.grid.set_catalogs(rfcs, conceptos, delegaciones)
            
            municipios = data["municipios"]
            self.combo_municipio.clear()
            default_index = 0
            for idx, m in enumerate(municipios):
                if m["activo"]:
                    self.combo_municipio.addItem(m["nombre"], m["municipio_id"])
                    if m["municipio_id"] == 2 or "BENITO" in m["nombre"].upper():
                        default_index = self.combo_municipio.count() - 1
            self.combo_municipio.setCurrentIndex(default_index)
        except Exception as e:
            QMessageBox.critical(self, "Error de Catálogos", f"No se pudieron cargar los catálogos.\n{str(e)}")
            
    def _on_guardar_orden(self):
        desc = self.desc_input.text().strip()
        data = self.grid.get_all_data()
        municipio_id = self.combo_municipio.currentData()
        
        if not desc:
            QMessageBox.warning(self, "Validación", "Debes ingresar una descripción para la orden.")
            return
            
        if not municipio_id:
            QMessageBox.warning(self, "Validación", "Debes seleccionar un municipio de acceso.")
            return
            
        if not data:
            QMessageBox.warning(self, "Validación", "Debes agregar al menos un renglón a la orden.")
            return
            
        # Validate that all rows have selected elements and no duplicates
        seen_combinations = set()
        for i, row in enumerate(data):
            if not row["rfc_id"] or not row["concepto_id"] or not row["delegacion_id"]:
                QMessageBox.warning(self, "Validación", f"El renglón {i+1} debe tener todos los campos seleccionados (RFC, Concepto y Delegación).")
                return
                
            key = (row["rfc_id"], row["concepto_id"], row.get("delegacion_id"))
            if key in seen_combinations:
                QMessageBox.warning(self, "Validación", f"El renglón {i+1} tiene una combinación duplicada de RFC, Concepto y Delegación. No se puede solicitar dos veces el mismo RFC y Concepto para la misma delegación.")
                return
            seen_combinations.add(key)
            
        # Confirmation Dialog
        if self._edit_mode:
            changes_summary = []
            original_map = {}
            for r in getattr(self, "_original_renglones", []):
                key = (r["rfc_id"], r["concepto_id"], r["delegacion_id"])
                original_map[key] = r
                
            current_keys = set()
            has_increased_completed = False
            
            for row in data:
                key = (row["rfc_id"], row["concepto_id"], row["delegacion_id"])
                current_keys.add(key)
                
                rfc_txt = self.grid.get_rfc_text(row["rfc_id"]) or str(row["rfc_id"])
                concept_txt = self.grid.get_concepto_text(row["concepto_id"]) or str(row["concepto_id"])
                del_txt = self.grid.get_delegacion_text(row["delegacion_id"]) or str(row["delegacion_id"])
                
                if key in original_map:
                    orig_row = original_map[key]
                    orig_cant = orig_row["cantidad"]
                    curr_cant = row["cantidad"]
                    
                    if orig_row.get("cantidad_generada", 0) > 0 and curr_cant > orig_row.get("cantidad_generada", 0):
                        has_increased_completed = True
                    
                    if curr_cant != orig_cant:
                        changes_summary.append(
                            f"• {rfc_txt} - {concept_txt} ({del_txt}):\n"
                            f"  Cant. Anterior: {orig_cant} → Cant. Actual: {curr_cant}"
                        )
                else:
                    curr_cant = row["cantidad"]
                    changes_summary.append(
                        f"• [NUEVA] {rfc_txt} - {concept_txt} ({del_txt}):\n"
                        f"  Cant. Anterior: 0 → Cant. Actual: {curr_cant}"
                    )
            
            # Check deleted rows
            for key, orig_row in original_map.items():
                if key not in current_keys:
                    rfc_txt = self.grid.get_rfc_text(orig_row["rfc_id"]) or str(orig_row["rfc_id"])
                    concept_txt = self.grid.get_concepto_text(orig_row["concepto_id"]) or str(orig_row["concepto_id"])
                    del_txt = self.grid.get_delegacion_text(orig_row["delegacion_id"]) or str(orig_row["delegacion_id"])
                    orig_cant = orig_row["cantidad"]
                    changes_summary.append(
                        f"• [ELIMINADA] {rfc_txt} - {concept_txt} ({del_txt}):\n"
                        f"  Cant. Anterior: {orig_cant} → Cant. Actual: 0 (Eliminada)"
                    )
                    
            if changes_summary:
                summary_text = "\n".join(changes_summary)
                completed_warning = ""
                if has_increased_completed:
                    completed_warning = (
                        "⚠️ IMPORTANTE: Has incrementado la cantidad en partidas que ya fueron procesadas por el bot.\n"
                        "Se generará una nueva solicitud pendiente por la cantidad adicional.\n\n"
                    )
                    
                reply = QMessageBox.question(
                    self, "Resumen de Cambios a la Orden",
                    f"{completed_warning}"
                    f"Se realizarán los siguientes cambios en las partidas:\n\n"
                    f"{summary_text}\n\n"
                    f"¿Deseas continuar con la actualización?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
            else:
                # No changes in rows, just confirm update header
                reply = QMessageBox.question(
                    self, "Confirmar Actualizar",
                    "¿Estás seguro de que deseas actualizar esta orden (encabezado)?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
        else:
            action_title = "Confirmar Guardar"
            action_msg = "¿Estás seguro de que deseas guardar esta orden?"
            reply = QMessageBox.question(
                self, action_title, action_msg,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
                
        # Main Window should have the current session id and user id, but we might only have session id.
        # We can extract the user_id by querying the session in the DB, or just pass it down.
        # For this desktop app, we fetch user_id from the current session.
        main_window = self.window()
        current_sesion_id = getattr(main_window, 'current_sesion_id', None)
        current_usuario_id = getattr(main_window, 'current_usuario_id', 1)
        
        try:
            if self._edit_mode:
                folio = self.ordenes_ui_service.actualizar_orden_manual(
                    orden_id=self._editing_order_id,
                    usuario_id=current_usuario_id,
                    sesion_id=current_sesion_id,
                    descripcion=desc,
                    municipio_id=municipio_id,
                    renglones=data
                )
                QMessageBox.information(
                    self, "Éxito", 
                    f"Orden {folio} actualizada correctamente."
                )
                self._on_cancelar_edicion()
            else:
                folio = self.ordenes_ui_service.crear_orden_manual(
                    usuario_id=current_usuario_id,
                    sesion_id=current_sesion_id,
                    descripcion=desc,
                    municipio_id=municipio_id,
                    renglones=data
                )
                QMessageBox.information(
                    self, "Éxito", 
                    f"Orden {folio} creada correctamente con {len(data)} grupos."
                )
                # Reset Form
                self.desc_input.setText("")
                self.grid.clear()
                self.grid.add_row()
                
        except Exception as e:
            QMessageBox.critical(self, "Error al Guardar", f"Hubo un problema al crear la orden:\n{str(e)}")

    def refresh_historial(self):
        # Cancel active thread if running safely
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.cancel()
            try:
                self.active_worker.result_ready.disconnect()
                self.active_worker.error_occurred.disconnect()
            except RuntimeError:
                pass
            self.active_worker.wait()

        self.active_worker = OrdersLoadWorker(self.ordenes_ui_service)
        self.active_worker.result_ready.connect(self._on_historial_loaded)
        self.active_worker.error_occurred.connect(self._on_historial_error)
        self.active_worker.start()

    def _on_historial_loaded(self, data):
        self._all_ordenes_data = data
        data_rows = []
        for o in self._all_ordenes_data:
            data_rows.append([
                str(o["orden_id"]),
                o["folio"],
                o["descripcion"],
                o["estado"],
                o["creador"],
                o["fecha_creacion"],
                str(o["total_solicitadas"]),
                str(o["total_generadas"])
            ])
            
        self.table_historial.populate_rows(data_rows, checkable_first_col=False)
        self._apply_historial_filters()

    def _on_historial_error(self, err_msg):
        QMessageBox.critical(self, "Error", f"No se pudo cargar el historial de órdenes:\n{err_msg}")
    
    def _on_historial_search(self, text: str):
        self._current_search_text = text.strip().lower()
        self._apply_historial_filters()
    
    def _on_historial_state_change(self, state: str):
        self._current_estado_filter = state
        self._apply_historial_filters()
    
    def _apply_historial_filters(self):
        search_text = getattr(self, '_current_search_text', "")
        estado_filter = getattr(self, '_current_estado_filter', "Todas")
        
        for row in range(self.table_historial.rowCount()):
            # Estado is in column 3
            estado_item = self.table_historial.item(row, 3)
            estado = estado_item.text() if estado_item else ""
            
            # 1. State Filter
            state_match = True
            if estado_filter != "Todas":
                state_match = (estado == estado_filter)
            
            # 2. Text search across visible columns
            text_match = True
            if search_text:
                text_match = False
                for col in range(self.table_historial.columnCount()):
                    item = self.table_historial.item(row, col)
                    if item and search_text in item.text().lower():
                        text_match = True
                        break
            
            self.table_historial.setRowHidden(row, not (state_match and text_match))

    def _on_row_double_clicked(self, row: int, column: int):
        id_item = self.table_historial.item(row, 0)
        if id_item:
            orden_id = int(id_item.text())
            from sar.src.ui.views.order_processing_dialog import OrderProcessingDialog
            dialog = OrderProcessingDialog(self.db_connector, orden_id, self)
            dialog.exec()

    def _get_selected_ordenes(self) -> list[int]:
        ids = []
        selected = self.table_historial.selectedItems()
        if selected:
            rows = set()
            for item in selected:
                rows.add(item.row())
            for row in rows:
                id_item = self.table_historial.item(row, 0)
                if id_item:
                    ids.append(int(id_item.text()))
        return ids

    def _change_orden_estado(self, estado_codigo: str):
        orden_ids = self._get_selected_ordenes()
        if not orden_ids:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona al menos una orden para procesar.")
            return

        total_referencias_acumuladas = 0
        try:
            for oid in orden_ids:
                res = self.ordenes_ui_service.check_orden_ready_for_masivo(oid)
                if not res["ready"]:
                    QMessageBox.warning(
                        self, 
                        "Acción Inválida", 
                        f"No se puede aplicar la acción masiva sobre la orden ID {oid}:\n\n"
                        f"{res['reason']}\n\n"
                        f"Sugerencia: Vaya al módulo 'Procesar Solicitud de la Orden' "
                        f"haciendo doble clic sobre la orden para realizar un procesamiento parcial."
                    )
                    return
                total_referencias_acumuladas += res.get("total_referencias", 0)
        except Exception as e:
            QMessageBox.critical(self, "Error de Validación", f"No se pudo validar el estado de las órdenes:\n{str(e)}")
            return
            
        reply = QMessageBox.question(
            self, 
            "Confirmar Acción", 
            f"¿Estás seguro de que deseas marcar {len(orden_ids)} orden(es) como {estado_codigo}?\n\n"
            f"Se procesará un total de {total_referencias_acumuladas} referencias en estado PENDIENTE_AUTORIZACION.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
            
        if reply == QMessageBox.Yes:
            try:
                main_window = self.window()
                current_sesion_id = getattr(main_window, 'current_sesion_id', None)
                current_usuario_id = getattr(main_window, 'current_usuario_id', 1)
                
                for oid in orden_ids:
                    self.ordenes_ui_service.update_orden_estado_masivo(
                        oid, estado_codigo, usuario_id=current_usuario_id, sesion_id=current_sesion_id
                    )
                QMessageBox.information(self, "Éxito", f"Las órdenes fueron procesadas como {estado_codigo} con éxito.")
                self.refresh_historial()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Ocurrió un error al procesar las órdenes:\n{str(e)}")

    def _on_autorizar_orden(self):
        self._change_orden_estado("AUTORIZADA")
        
    def _on_rechazar_orden(self):
        self._change_orden_estado("RECHAZADA")

    def _on_cancelar_orden(self):
        orden_ids = self._get_selected_ordenes()
        if not orden_ids:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona al menos una orden para cancelar.")
            return
            
        reply = QMessageBox.question(self, "Confirmar Cancelación", 
            f"¿Estás seguro de que deseas cancelar {len(orden_ids)} orden(es)? "
            "Esto cancelará de forma permanente la orden y todas sus solicitudes asociadas.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
        if reply == QMessageBox.Yes:
            try:
                main_window = self.window()
                current_sesion_id = getattr(main_window, 'current_sesion_id', None)
                current_usuario_id = getattr(main_window, 'current_usuario_id', 1)
                
                for oid in orden_ids:
                    self.ordenes_ui_service.cancelar_orden_transaccional(
                        oid, usuario_id=current_usuario_id, sesion_id=current_sesion_id
                    )
                QMessageBox.information(self, "Éxito", f"Las órdenes fueron canceladas con éxito.")
                self.refresh_historial()
            except Exception as e:
                QMessageBox.critical(self, "Error al Cancelar", f"No se pudo cancelar la orden:\n{str(e)}")

    def _show_context_menu(self, position):
        from PySide6.QtWidgets import QMenu
        row = self.table_historial.rowAt(position.y())
        if row < 0:
            return
            
        menu = QMenu(self)
        action_procesar = menu.addAction("Procesar referencias (Doble clic)")
        action_editar = menu.addAction("Editar orden")
        
        id_item = self.table_historial.item(row, 0)
        
        action = menu.exec(self.table_historial.viewport().mapToGlobal(position))
        if action == action_procesar:
            self._on_row_double_clicked(row, 0)
        elif action == action_editar:
            if id_item:
                orden_id = int(id_item.text())
                self.load_order_for_editing(orden_id)

    def _on_editar_orden_clicked(self):
        selected_ids = self._get_selected_ordenes()
        if not selected_ids:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona una orden para editar.")
            return
        if len(selected_ids) > 1:
            QMessageBox.warning(self, "Selección Inválida", "Solo puedes editar una orden a la vez.")
            return
            
        orden_id = selected_ids[0]
        self.load_order_for_editing(orden_id)

    def load_order_for_editing(self, orden_id: int):
        try:
            if self.api_client.connect_via_api:
                data = self.api_client.request("GET", f"/api/ops/ordenes/{orden_id}")
            else:
                with self.db_connector.get_session() as session:
                    from sar.src.storage.repositories import ProduccionRepository
                    repo = ProduccionRepository(session)
                    data = repo.get_orden_detalle_edicion(orden_id)
            
            if not data["editable"]:
                QMessageBox.warning(
                    self, 
                    "No Editable", 
                    f"No se puede editar la orden {data['folio']}.\n\n"
                    f"Razón: Solo se pueden editar órdenes en estado PENDIENTE o BORRADOR "
                    f"donde todas sus solicitudes estén en estado PENDIENTE, ASIGNADA o COMPLETADA, "
                    f"y que la orden no esté cancelada."
                )
                return
                
            # Set edit mode
            self._edit_mode = True
            self._editing_order_id = data["orden_id"]
            self._editing_folio = data["folio"]
            
            # Update UI header
            self.lbl_card_title.setText(f"Editar Orden: {data['folio']}")
            self.lbl_card_subtitle.setText("Modifica los datos y partidas de la orden")
            self.grid.btn_save.setText("Actualizar Orden")
            self.grid.btn_cancel.setVisible(True)
            
            # Calculate total anterior and display it
            total_anterior = sum(r["cantidad"] for r in data["renglones"])
            self.lbl_tot_ant_val.setText(str(total_anterior))
            self.total_anterior_frame.setVisible(True)
            
            # Fill inputs
            self.desc_input.setText(data["descripcion"] or "")
            
            # Find and set municipio
            idx_mun = self.combo_municipio.findData(data["municipio_id"])
            if idx_mun >= 0:
                self.combo_municipio.setCurrentIndex(idx_mun)
                
            # Clear and populate grid
            self.grid.clear()
            self._original_renglones = [dict(r) for r in data["renglones"]]
            for r in data["renglones"]:
                self.grid.add_row_with_data(
                    rfc_id=r["rfc_id"],
                    concepto_id=r["concepto_id"],
                    delegacion_id=r["delegacion_id"],
                    cantidad=r["cantidad"],
                    cantidad_generada=r.get("cantidad_generada", 0)
                )
                
            # Switch to Capture tab (0)
            self.tabs.setCurrentIndex(0)
            
        except Exception as e:
            QMessageBox.critical(self, "Error al Cargar", f"No se pudieron obtener los detalles de la orden:\n{str(e)}")

    def _on_cancelar_edicion(self):
        # Reset mode
        self._edit_mode = False
        self._editing_order_id = None
        self._editing_folio = None
        
        # Reset UI
        self.lbl_card_title.setText("Configuración de la Orden")
        self.lbl_card_subtitle.setText("Completa los datos para crear una nueva orden")
        self.grid.btn_save.setText("Guardar Orden")
        self.grid.btn_cancel.setVisible(False)
        self.total_anterior_frame.setVisible(False)
        self.lbl_tot_ant_val.setText("0")
        
        self.desc_input.setText("")
        self._load_catalogs() # Re-selects default municipio
        
        self.grid.clear()
        self.grid.add_row()
        
        # Refresh history
        self.refresh_historial()
        
        # Switch to history tab (1)
        self.tabs.setCurrentIndex(1)
