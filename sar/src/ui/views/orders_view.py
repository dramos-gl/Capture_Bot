"""Orders Management View."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QStackedWidget, QCheckBox, QFrame, QPushButton
)
from PySide6.QtCore import Qt
from sar.src.ui.design_system.components import (
    CustomCard, CustomLabel, CustomButton, CustomCheckBox, InteractiveGrid, CustomInput, CustomComboBox, FilterBar,
    GLInfoBanner, GLMessageBox as QMessageBox
)
from sar.src.ui.design_system.utils.icons import Icons
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
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QWidget#ordersScrollContent {
                background-color: transparent;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setObjectName("ordersScrollContent")
        self.layout = QVBoxLayout(scroll_content)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(24)
        
        self.tabs = QStackedWidget()
        
        self.tab_nueva = QWidget()
        self.tab_historial = QWidget()
        
        self.tabs.addWidget(self.tab_nueva) # Index 0: Capturar Nueva Orden
        self.tabs.addWidget(self.tab_historial) # Index 1: Órdenes Capturadas
        
        self.layout.addWidget(self.tabs)
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        self._setup_historial_tab()
        self._setup_nueva_orden_tab()
        
        # Pre-load catalogs and data
        self._current_search_text = ""
        self._current_estado_filter = "Todas"
        
        # Pagination state
        self.current_page = 1
        self.page_size = 50
        self._all_ordenes_data = []
        self._filtered_ordenes_data = []

        # Edit mode state variables
        self._edit_mode = False
        self._editing_order_id = None
        self._editing_folio = None

        self._load_catalogs()
        self.refresh_historial()
        
        # Agregamos el primer renglón por defecto en la nueva orden
        self.grid.add_row()
        
    def _check_permission(self, modulo_codigo: str, accion_codigo: str) -> bool:
        """Helper to verify if current session/user holds permission for modulo + accion."""
        parent_window = self.window()
        usuario_id = getattr(parent_window, 'current_usuario_id', None)
        if not usuario_id:
            return True # Fallback if standalone/testing without active user session context
        
        try:
            if getattr(self.api_client, 'connect_via_api', False):
                perms = self.api_client.request("GET", f"/api/auth/permissions/{usuario_id}")
                return perms.get(modulo_codigo, {}).get(accion_codigo, False)
            else:
                with self.db_connector.get_session() as session:
                    from sar.src.services.security_service import SecurityService
                    sec_service = SecurityService(session)
                    return sec_service.has_permission(usuario_id, modulo_codigo, accion_codigo)
        except Exception as e:
            print(f"Error checking permission {modulo_codigo}:{accion_codigo}: {e}")
            return False

    def _on_abrir_validador_fiscal(self):
        """Opens the read-only fiscal domicile validation dialog for companies/RFC."""
        if not self._check_permission("ORDENES", "LEER"):
            QMessageBox.warning(
                self,
                "Acceso Denegado",
                "No tiene permisos para consultar datos de empresas (ORDENES:LEER)."
            )
            return

        from sar.src.ui.views.company_fiscal_dialog import CompanyFiscalValidationDialog
        dialog = CompanyFiscalValidationDialog(self.ordenes_ui_service, parent=self)
        dialog.exec()

    def _on_guardar_orden(self):
        # RBAC Check: CREAR for new order, EDITAR for edit mode
        required_action = "EDITAR" if self._edit_mode else "CREAR"
        if not self._check_permission("ORDENES", required_action):
            action_desc = "modificar órdenes de generación" if self._edit_mode else "crear nuevas órdenes de generación"
            QMessageBox.warning(
                self,
                "Acceso Denegado",
                f"No tiene permisos para {action_desc} (ORDENES:{required_action})."
            )
            return

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
            es_cancelacion = getattr(self, "chk_cancelaciones", None) and self.chk_cancelaciones.isChecked()
            es_fojas = getattr(self, "chk_fojas", None) and self.chk_fojas.isChecked()
            es_testimonios = getattr(self, "chk_testimonios", None) and self.chk_testimonios.isChecked()
            
            # Construcción de los detalles de las solicitudes a incluir
            item_details = []
            for row in data:
                rfc_txt = self.grid.get_rfc_text(row["rfc_id"]) or str(row["rfc_id"])
                concept_txt = self.grid.get_concepto_text(row["concepto_id"]) or str(row["concepto_id"])
                del_txt = self.grid.get_delegacion_text(row["delegacion_id"]) or str(row["delegacion_id"])
                cant_str = f"Cantidad = {row['cantidad']}"
                if row.get("concepto_id") == 5 and row.get("cantidad_actos", 1) > 1:
                    cant_str += f" (Fojas/Actos = {row['cantidad_actos']})"
                item_details.append(f"• {rfc_txt} - {concept_txt} ({del_txt}): {cant_str}")
            
            details_str = "\n".join(item_details)

            from datetime import datetime
            current_year = datetime.utcnow().year
            all_ordenes = getattr(self, "_all_ordenes_data", [])

            if es_cancelacion:
                folio_cancel = f"ORD-CANCEL-{current_year}"
                orden_existente = next((o for o in all_ordenes if o.get("folio") == folio_cancel), None)
                action_title = "Confirmar Orden de Cancelación"
                action_msg = (
                    f"¿Estás seguro de que deseas actualizar la orden de cancelación de aviso con las siguientes partidas?\n\n{details_str}\n\nDescripción: {desc}"
                    if orden_existente else
                    f"¿Estás seguro de que deseas guardar la orden Anual de cancelación de aviso con las siguientes partidas?\n\n{details_str}\n\nDescripción: {desc}"
                )
            elif es_fojas:
                folio_fojas = f"ORD-FOJAS-{current_year}"
                orden_existente = next((o for o in all_ordenes if o.get("folio") == folio_fojas), None)
                action_title = "Confirmar Orden de Fojas"
                action_msg = (
                    f"¿Estás seguro de que deseas actualizar la orden de fojas ({folio_fojas}) con las siguientes partidas?\n\n{details_str}\n\nDescripción: {desc}"
                    if orden_existente else
                    f"¿Estás seguro de que deseas guardar la orden Anual de fojas con las siguientes partidas?\n\n{details_str}\n\nDescripción: {desc}"
                )
            elif es_testimonios:
                folio_testimonio = f"ORD-TESTIMONIO-{current_year}"
                orden_existente = next((o for o in all_ordenes if o.get("folio") == folio_testimonio), None)
                action_title = "Confirmar Orden de Testimonios"
                action_msg = (
                    f"¿Estás seguro de que deseas actualizar la orden de testimonios ({folio_testimonio}) con las siguientes partidas?\n\n{details_str}\n\nDescripción: {desc}"
                    if orden_existente else
                    f"¿Estás seguro de que deseas guardar la orden Anual de testimonios con las siguientes partidas?\n\n{details_str}\n\nDescripción: {desc}"
                )
            else:
                action_title = "Confirmar Guardar Orden"
                action_msg = (
                    f"¿Estás seguro de que deseas guardar esta orden con las siguientes partidas?\n\n"
                    f"{details_str}\n\n"
                    f"Descripción: {desc}"
                )
                
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
                if self.chk_cancelaciones.isChecked():
                    tipo_ord = "CANCELACION"
                elif self.chk_fojas.isChecked():
                    tipo_ord = "FOJAS"
                elif self.chk_testimonios.isChecked():
                    tipo_ord = "TESTIMONIO"
                else:
                    tipo_ord = "ESTANDAR"

                folio = self.ordenes_ui_service.crear_orden_manual(
                    usuario_id=current_usuario_id,
                    sesion_id=current_sesion_id,
                    descripcion=desc,
                    municipio_id=municipio_id,
                    renglones=data,
                    tipo_orden=tipo_ord
                )
                QMessageBox.information(
                    self, "Éxito", 
                    f"Orden {folio} registrada correctamente con {len(data)} partidas."
                )
                # Reset Form
                if self.chk_cancelaciones.isChecked():
                    self.chk_cancelaciones.setChecked(False)
                elif self.chk_fojas.isChecked():
                    self.chk_fojas.setChecked(False)
                elif self.chk_testimonios.isChecked():
                    self.chk_testimonios.setChecked(False)
                else:
                    self.desc_input.setText("")
                self.grid.clear()
                self.grid.add_row()
                
        except Exception as e:
            QMessageBox.critical(self, "Error al Guardar", f"Hubo un problema al crear la orden:\n{str(e)}")

    def _setup_historial_tab(self):
        from sar.src.ui.design_system.components import StyledDataTable, CustomCard
        layout = QVBoxLayout(self.tab_historial)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)
        
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
        self.historial_card = CustomCard(title="Órdenes de Generación Capturadas", parent=self)
        
        headers = ["ID", "Folio", "Descripción", "Estado", "Creador", "Fecha Creación", "Total Solicitadas", "Total Generadas"]
        self.table_historial = StyledDataTable(headers, parent=self)
        self.table_historial.setColumnHidden(0, True) # Ocultar ID interno
        self.table_historial.setMinimumHeight(200)
        self.table_historial.setMinimumWidth(200)
        self.table_historial.cellDoubleClicked.connect(self._on_row_double_clicked)
        self.table_historial.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_historial.customContextMenuRequested.connect(self._show_context_menu)
        
        self.historial_card.add_widget(self.table_historial)
        
        # Table Footer Pagination Layout (Golden Standard)
        self.footer_layout = QHBoxLayout()
        self.footer_layout.setContentsMargins(0, 8, 0, 0)
        
        self.lbl_pagination_info = CustomLabel("Mostrando 0 a 0 de 0 órdenes", variant="muted")
        self.lbl_pagination_info.setObjectName("ordersPaginationInfo")
        self.footer_layout.addWidget(self.lbl_pagination_info)
        
        self.footer_layout.addStretch()
        
        # Page size combobox (activación dinámica si total > 50)
        self.cb_page_size = CustomComboBox(self)
        self.cb_page_size.addItems(["50 por página", "100 por página", "200 por página"])
        self.cb_page_size.setCurrentIndex(0) # Default 50 por página
        self.cb_page_size.currentTextChanged.connect(self._on_page_size_changed)
        self.cb_page_size.setVisible(False)
        self.footer_layout.addWidget(self.cb_page_size)
        
        # Pagination buttons wrapper
        self.pagination_widget = QWidget(self)
        self.pag_btn_layout = QHBoxLayout(self.pagination_widget)
        self.pag_btn_layout.setContentsMargins(0, 0, 0, 0)
        self.pag_btn_layout.setSpacing(4)
        self.footer_layout.addWidget(self.pagination_widget)
        
        self.historial_card.layout.addLayout(self.footer_layout)
        
        actions_layout = QHBoxLayout()
        self.lbl_table_hint = CustomLabel(
            "💡 Doble clic sobre cualquier orden para ver solicitudes, generar lotes Excel/PDF o Autorizar/Rechazar",
            variant="muted"
        )
        self.lbl_table_hint.setWordWrap(True)
        actions_layout.addWidget(self.lbl_table_hint, stretch=1)
        actions_layout.addSpacing(12)
        
        self.btn_editar_orden = CustomButton.action_editar(parent=self)
        self.btn_editar_orden.setToolTip("Editar orden seleccionada")
        self.btn_editar_orden.clicked.connect(self._on_editar_orden_clicked)

        self.btn_autorizar_orden = CustomButton.action_autorizar(parent=self)
        self.btn_autorizar_orden.setToolTip("Autorizar orden seleccionada")
        self.btn_autorizar_orden.clicked.connect(self._on_autorizar_orden)
        
        self.btn_rechazar_orden = CustomButton.action_rechazar(parent=self)
        self.btn_rechazar_orden.setToolTip("Rechazar orden seleccionada")
        self.btn_rechazar_orden.clicked.connect(self._on_rechazar_orden)
        
        self.btn_cancelar_orden = CustomButton.action_cancelar(parent=self)
        self.btn_cancelar_orden.setToolTip("Cancelar orden seleccionada")
        self.btn_cancelar_orden.clicked.connect(self._on_cancelar_orden)
        
        actions_layout.addWidget(self.btn_editar_orden)
        actions_layout.addWidget(self.btn_autorizar_orden)
        actions_layout.addWidget(self.btn_rechazar_orden)
        actions_layout.addWidget(self.btn_cancelar_orden)
        
        self.historial_card.layout.addLayout(actions_layout)
        
        layout.addWidget(self.historial_card)

    def _setup_nueva_orden_tab(self):
        layout = QVBoxLayout(self.tab_nueva)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)
        
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

        # Botón de Validación Fiscal de Empresas (Regla de Oro)
        self.btn_validar_fiscal = CustomButton("Validar Domicilio Fiscal", is_secondary=True, parent=self)
        self.btn_validar_fiscal.setIcon(Icons.advertencia("#D97706"))
        self.btn_validar_fiscal.setObjectName("btnValidarDomicilioFiscal")
        self.btn_validar_fiscal.setToolTip(
            "REGLA DE ORO: Validar visualmente el domicilio fiscal registrado de las empresas (RFC) "
            "antes de generar la orden y procesar derechos con los BOTs."
        )
        self.btn_validar_fiscal.setStyleSheet("""
            QPushButton#btnValidarDomicilioFiscal {
                background-color: rgba(217, 119, 6, 0.15);
                color: #D97706;
                border: 1px solid rgba(217, 119, 6, 0.40);
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 6px;
            }
            QPushButton#btnValidarDomicilioFiscal:hover {
                background-color: rgba(217, 119, 6, 0.25);
                border: 1px solid #D97706;
            }
        """)
        self.btn_validar_fiscal.clicked.connect(self._on_abrir_validador_fiscal)
        card_header_layout.addWidget(self.btn_validar_fiscal)
        
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
        
        # Checkbox Modos Anuales (Design System Atom)
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(16)
        self.chk_cancelaciones = CustomCheckBox("Derechos Cancelación de Avisos")
        self.chk_fojas = CustomCheckBox("Derechos de Fojas")
        self.chk_testimonios = CustomCheckBox("Expedición de Testimonios")
        
        self.chk_cancelaciones.toggled.connect(self._on_toggle_cancelaciones)
        self.chk_fojas.toggled.connect(self._on_toggle_fojas)
        self.chk_testimonios.toggled.connect(self._on_toggle_testimonios)
        
        mode_layout.addWidget(self.chk_cancelaciones)
        mode_layout.addWidget(self.chk_fojas)
        mode_layout.addWidget(self.chk_testimonios)
        mode_layout.addStretch()

        card_layout.addLayout(inputs_layout)
        card_layout.addLayout(mode_layout)
        
        # Divider line
        divider = QFrame()
        divider.setObjectName("dividerLine")
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        card_layout.addWidget(divider)
        
        # Interactive Grid
        self.grid = InteractiveGrid(self)
        self.grid.set_has_disponibles(False)
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
            
    def _on_toggle_cancelaciones(self, checked: bool):
        from datetime import datetime
        current_year = datetime.utcnow().year
        if checked:
            self.chk_fojas.blockSignals(True)
            self.chk_testimonios.blockSignals(True)
            self.chk_fojas.setChecked(False)
            self.chk_testimonios.setChecked(False)
            self.chk_fojas.blockSignals(False)
            self.chk_testimonios.blockSignals(False)

            self._load_catalogs(tipo_modulo="CANCELACION")
            self.desc_input.setText(f"Cancelación de Avisos {current_year}")
            self.desc_input.setReadOnly(True)
        else:
            self._load_catalogs(tipo_modulo="ESTANDAR")
            self.desc_input.setText("")
            self.desc_input.setReadOnly(False)

    def _on_toggle_fojas(self, checked: bool):
        from datetime import datetime
        current_year = datetime.utcnow().year
        if checked:
            self.chk_cancelaciones.blockSignals(True)
            self.chk_testimonios.blockSignals(True)
            self.chk_cancelaciones.setChecked(False)
            self.chk_testimonios.setChecked(False)
            self.chk_cancelaciones.blockSignals(False)
            self.chk_testimonios.blockSignals(False)

            self._load_catalogs(tipo_modulo="FOJAS")
            self.desc_input.setText(f"Derechos de Fojas {current_year}")
            self.desc_input.setReadOnly(True)
        else:
            self._load_catalogs(tipo_modulo="ESTANDAR")
            self.desc_input.setText("")
            self.desc_input.setReadOnly(False)

    def _on_toggle_testimonios(self, checked: bool):
        from datetime import datetime
        current_year = datetime.utcnow().year
        if checked:
            self.chk_cancelaciones.blockSignals(True)
            self.chk_fojas.blockSignals(True)
            self.chk_cancelaciones.setChecked(False)
            self.chk_fojas.setChecked(False)
            self.chk_cancelaciones.blockSignals(False)
            self.chk_fojas.blockSignals(False)

            self._load_catalogs(tipo_modulo="TESTIMONIO")
            self.desc_input.setText(f"Derechos de Testimonios {current_year}")
            self.desc_input.setReadOnly(True)
        else:
            self._load_catalogs(tipo_modulo="ESTANDAR")
            self.desc_input.setText("")
            self.desc_input.setReadOnly(False)

    def _load_catalogs(self, es_cancelacion: bool = False, tipo_modulo: Optional[str] = None):
        try:
            data = self.ordenes_ui_service.get_catalogos(es_cancelacion=es_cancelacion, tipo_modulo=tipo_modulo)
            rfcs = [
                (
                    r["rfc_id"],
                    f"{r['alias'].strip()} | {r['rfc']}" if r.get("alias") and r.get("alias").strip() else r["rfc"]
                )
                for r in data["rfcs"]
            ]
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
        self._all_ordenes_data = data or []
        self._apply_historial_filters(reset_page=True)

    def _on_historial_error(self, err_msg):
        QMessageBox.critical(self, "Error", f"No se pudo cargar el historial de órdenes:\n{err_msg}")
    
    def _on_historial_search(self, text: str):
        self._current_search_text = text.strip().lower()
        self._apply_historial_filters(reset_page=True)
    
    def _on_historial_state_change(self, state: str):
        self._current_estado_filter = state
        self._apply_historial_filters(reset_page=True)

    def _on_page_size_changed(self, text: str):
        if "50" in text:
            self.page_size = 50
        elif "100" in text:
            self.page_size = 100
        elif "200" in text:
            self.page_size = 200
        self.current_page = 1
        self._apply_historial_filters(reset_page=True)

    def _set_page(self, page_num: int):
        self.current_page = page_num
        self._apply_historial_filters(reset_page=False)

    def _apply_historial_filters(self, reset_page: bool = False):
        if reset_page:
            self.current_page = 1

        search_text = getattr(self, '_current_search_text', "").strip().lower()
        estado_filter = getattr(self, '_current_estado_filter', "Todas")

        # 1. Filter in-memory data
        filtered = []
        for o in getattr(self, '_all_ordenes_data', []):
            if estado_filter != "Todas" and o.get("estado") != estado_filter:
                continue

            if search_text:
                matched = (
                    search_text in str(o.get("folio", "")).lower()
                    or search_text in str(o.get("descripcion", "")).lower()
                    or search_text in str(o.get("estado", "")).lower()
                    or search_text in str(o.get("creador", "")).lower()
                    or search_text in str(o.get("fecha_creacion", "")).lower()
                )
                if not matched:
                    continue

            filtered.append(o)

        self._filtered_ordenes_data = filtered
        total_items = len(self._filtered_ordenes_data)
        total_pages = max(1, (total_items + self.page_size - 1) // self.page_size)

        if self.current_page > total_pages:
            self.current_page = total_pages
        if self.current_page < 1:
            self.current_page = 1

        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, total_items)
        page_slice = self._filtered_ordenes_data[start_idx:end_idx]

        # 2. Populate table with page slice
        data_rows = []
        for o in page_slice:
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

        self.table_historial.blockSignals(True)
        self.table_historial.populate_rows(data_rows, checkable_first_col=False)
        self.table_historial.blockSignals(False)

        # 3. Update footer info
        if total_items == 0:
            self.lbl_pagination_info.setText("Mostrando 0 a 0 de 0 órdenes")
        else:
            self.lbl_pagination_info.setText(f"Mostrando {start_idx + 1} a {end_idx} de {total_items} órdenes")

        # 4. Redraw pagination buttons (Golden Standard)
        while self.pag_btn_layout.count():
            item = self.pag_btn_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Activar dinámicamente el selector de densidad solo si el total supera el mínimo (50)
        self.cb_page_size.setVisible(total_items > 50)

        # Activar dinámicamente los botones de navegación solo si hay 2 o más páginas
        if total_pages <= 1:
            self.pagination_widget.setVisible(False)
            return

        self.pagination_widget.setVisible(True)

        def add_page_btn(text: str, target: int, enabled: bool, is_active: bool = False):
            btn = QPushButton(text)
            btn.setEnabled(enabled)
            if is_active:
                btn.setObjectName("paginationActivePageBtn")
            elif text in ("<<", "<", ">", ">>"):
                btn.setObjectName("paginationNavBtn")
            else:
                btn.setObjectName("paginationPageBtn")
            btn.clicked.connect(lambda _checked=False, t=target: self._set_page(t))
            self.pag_btn_layout.addWidget(btn)

        add_page_btn("<<", 1, self.current_page > 1)
        add_page_btn("<", self.current_page - 1, self.current_page > 1)
        add_page_btn(str(self.current_page), self.current_page, True, is_active=True)
        add_page_btn(">", self.current_page + 1, self.current_page < total_pages)
        add_page_btn(">>", total_pages, self.current_page < total_pages)

    def _on_row_double_clicked(self, row: int, column: int):
        if not (self._check_permission("ORDENES", "LEER") or self._check_permission("DERECHOS", "LEER")):
            QMessageBox.warning(
                self,
                "Acceso Denegado",
                "No tiene permisos suficientes para consultar el detalle de procesamiento de órdenes (ORDENES:LEER)."
            )
            return
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

        accion_nombre = "Rechazar" if estado_codigo == "RECHAZADA" else "Autorizar"
        total_referencias_acumuladas = 0
        folios_procesados = []
        
        try:
            for oid in orden_ids:
                res = self.ordenes_ui_service.check_orden_ready_for_masivo(oid, accion=estado_codigo)
                folio = res.get("folio", f"ID {oid}")
                folios_procesados.append(folio)
                
                if not res["ready"]:
                    msg = res.get("reason", "La orden no cumple con las condiciones para ser procesada.")
                    if res.get("suggestion"):
                        msg += f"\n\nSugerencia: {res['suggestion']}"
                    QMessageBox.warning(
                        self, 
                        f"No se puede {accion_nombre} la orden", 
                        msg
                    )
                    return
                total_referencias_acumuladas += res.get("total_referencias", 0)
        except Exception as e:
            QMessageBox.critical(self, "Error de Validación", f"No se pudo validar el estado de las órdenes:\n{str(e)}")
            return

        folios_str = ", ".join([f"'{f}'" for f in folios_procesados])

        if estado_codigo == "RECHAZADA":
            confirm_title = "Confirmar Rechazo de Orden"
            confirm_msg = (
                f"¿Estás seguro de que deseas rechazar la orden {folios_str}?\n\n"
                f"⚠️ Advertencia de Rechazo:\n"
                f"• Se rechazarán permanentemente todos los derechos ({total_referencias_acumuladas} referencias).\n"
                f"• Las solicitudes y grupos asociados quedarán cancelados.\n"
                f"• Esta orden quedará registrada como RECHAZADA en la auditoría y sus derechos no ingresarán al inventario."
            )
        else:
            confirm_title = "Confirmar Autorización de Orden"
            confirm_msg = (
                f"¿Estás seguro de que deseas autorizar la orden {folios_str}?\n\n"
                f"✔️ Resultado de Autorización:\n"
                f"• Se autorizarán formalmente {total_referencias_acumuladas} referencias en estado PENDIENTE_AUTORIZACION.\n"
                f"• Los derechos pasarán a estar disponibles en el Inventario para asignación o reserva."
            )

        reply = QMessageBox.question(
            self, 
            confirm_title, 
            confirm_msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
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
        if not self._check_permission("ORDENES", "EJECUTAR"):
            QMessageBox.warning(
                self,
                "Acceso Denegado",
                "No tiene permisos para autorizar órdenes completas (ORDENES:EJECUTAR)."
            )
            return
        self._change_orden_estado("AUTORIZADA")
        
    def _on_rechazar_orden(self):
        if not self._check_permission("ORDENES", "EJECUTAR"):
            QMessageBox.warning(
                self,
                "Acceso Denegado",
                "No tiene permisos para rechazar órdenes completas (ORDENES:EJECUTAR)."
            )
            return
        self._change_orden_estado("RECHAZADA")

    def _on_cancelar_orden(self):
        if not self._check_permission("ORDENES", "ELIMINAR"):
            QMessageBox.warning(
                self,
                "Acceso Denegado",
                "No tiene permisos para cancelar órdenes (ORDENES:ELIMINAR)."
            )
            return
            
        selected_items = self.table_historial.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona al menos una orden para cancelar.")
            return

        selected_rows = sorted(set(item.row() for item in selected_items))
        orden_ids = []
        
        # Pre-validaciones de estado y referencias generadas
        for row in selected_rows:
            id_item = self.table_historial.item(row, 0)
            folio_item = self.table_historial.item(row, 1)
            estado_item = self.table_historial.item(row, 3)
            generadas_item = self.table_historial.item(row, 7)
            
            if not id_item:
                continue
                
            oid = int(id_item.text())
            folio = folio_item.text().strip() if folio_item else f"ID {oid}"
            estado = estado_item.text().strip().upper() if estado_item else ""
            
            generadas_str = generadas_item.text().strip() if generadas_item else "0"
            generadas = int(generadas_str) if generadas_str.isdigit() else 0

            if estado == "CANCELADA":
                QMessageBox.information(
                    self,
                    "Cancelación No Permitida",
                    f"La orden '{folio}' ya fue cancelada previamente."
                )
                return

            if estado == "AUTORIZADA":
                QMessageBox.information(
                    self,
                    "Cancelación No Permitida",
                    f"La orden '{folio}' se encuentra en estado 'AUTORIZADA' y no puede ser cancelada."
                )
                return

            if estado == "RECHAZADA":
                QMessageBox.information(
                    self,
                    "Cancelación No Permitida",
                    f"La orden '{folio}' se encuentra en estado 'RECHAZADA' y no puede ser cancelada."
                )
                return

            if generadas > 0:
                QMessageBox.information(
                    self,
                    "Cancelación No Permitida",
                    f"No se puede cancelar la orden '{folio}' porque ya cuenta con {generadas} referencia(s) generada(s).\n\n"
                    f"Las órdenes con derechos generados no pueden eliminarse para garantizar la trazabilidad."
                )
                return

            if estado in ["COMPLETADA", "EN_PROCESO"]:
                QMessageBox.information(
                    self,
                    "Cancelación No Permitida",
                    f"La orden '{folio}' se encuentra en estado '{estado}' y no puede ser cancelada."
                )
                return

            orden_ids.append(oid)

        if not orden_ids:
            return
            
        reply = QMessageBox.question(
            self,
            "Confirmar Cancelación", 
            f"¿Estás seguro de que deseas cancelar {len(orden_ids)} orden(es)?\n\n"
            "Esto cancelará de forma permanente la orden y todas sus solicitudes asociadas.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
            
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
        action_procesar = menu.addAction("Procesar derechos (Doble clic)")
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
        if not self._check_permission("ORDENES", "EDITAR"):
            QMessageBox.warning(
                self,
                "Acceso Denegado",
                "No tiene permisos para modificar órdenes existentes (ORDENES:EDITAR)."
            )
            return
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
        if not self._check_permission("ORDENES", "EDITAR"):
            QMessageBox.warning(
                self,
                "Acceso Denegado",
                "No tiene permisos para modificar órdenes existentes (ORDENES:EDITAR)."
            )
            return
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
            self.grid.btn_save.setText("Guardar")
            self.grid.btn_save.setToolTip("Actualizar orden con los cambios realizados")
            self.grid.btn_cancel.setVisible(True)
            self.grid.btn_cancel.setToolTip("Cancelar edición y descartar cambios")
            
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
                
            # Set tipo_orden and catalog
            self.chk_cancelaciones.blockSignals(True)
            self.chk_fojas.blockSignals(True)
            self.chk_testimonios.blockSignals(True)
            self.chk_cancelaciones.setChecked(False)
            self.chk_fojas.setChecked(False)
            self.chk_testimonios.setChecked(False)
            self.chk_cancelaciones.blockSignals(False)
            self.chk_fojas.blockSignals(False)
            self.chk_testimonios.blockSignals(False)
            
            tipo_orden = data.get("tipo_orden", "ESTANDAR")
            if tipo_orden == "CANCELACION":
                self.chk_cancelaciones.setChecked(True)
                self.chk_cancelaciones.setEnabled(False)
                self.chk_cancelaciones.setVisible(True)
                self.chk_fojas.setVisible(False)
                self.chk_testimonios.setVisible(False)
            elif tipo_orden == "FOJAS":
                self.chk_fojas.setChecked(True)
                self.chk_fojas.setEnabled(False)
                self.chk_fojas.setVisible(True)
                self.chk_cancelaciones.setVisible(False)
                self.chk_testimonios.setVisible(False)
            elif tipo_orden == "TESTIMONIO":
                self.chk_testimonios.setChecked(True)
                self.chk_testimonios.setEnabled(False)
                self.chk_testimonios.setVisible(True)
                self.chk_cancelaciones.setVisible(False)
                self.chk_fojas.setVisible(False)
            else:
                self._load_catalogs(tipo_modulo="ESTANDAR")
                self.desc_input.setReadOnly(False)
                self.chk_cancelaciones.setVisible(False)
                self.chk_fojas.setVisible(False)
                self.chk_testimonios.setVisible(False)
                
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
            main_window = self.window()
            if hasattr(main_window, 'sidebar'):
                main_window.sidebar.blockSignals(True)
                main_window.sidebar.select_item("capturar_orden")
                main_window.sidebar.blockSignals(False)
            
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
        self.grid.btn_save.setText("Guardar")
        self.grid.btn_save.setToolTip("Guardar orden")
        self.grid.btn_cancel.setVisible(False)
        self.total_anterior_frame.setVisible(False)
        self.lbl_tot_ant_val.setText("0")
        
        self.desc_input.setText("")
        
        # Reset checkboxes
        self.chk_cancelaciones.setVisible(True)
        self.chk_cancelaciones.setEnabled(True)
        self.chk_cancelaciones.setChecked(False)
        self.chk_fojas.setVisible(True)
        self.chk_fojas.setEnabled(True)
        self.chk_fojas.setChecked(False)
        self.chk_testimonios.setVisible(True)
        self.chk_testimonios.setEnabled(True)
        self.chk_testimonios.setChecked(False)
        
        self._load_catalogs() # Re-selects default municipio
        
        self.grid.clear()
        self.grid.add_row()
        
        # Refresh history
        self.refresh_historial()
        
        # Switch to history tab (1)
        self.tabs.setCurrentIndex(1)
        main_window = self.window()
        if hasattr(main_window, 'sidebar'):
            main_window.sidebar.blockSignals(True)
            main_window.sidebar.select_item("ordenes_capturadas")
            main_window.sidebar.blockSignals(False)
