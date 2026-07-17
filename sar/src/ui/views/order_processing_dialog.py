"""Interactive Dialog to process individual or multiple Solicitudes within an Order."""

from typing import List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QMessageBox, QFrame, QLineEdit, QComboBox, QCheckBox, QTableWidgetItem, QLabel, QWidget
)
from PySide6.QtCore import Qt
from sar.src.ui.design_system.components import CustomLabel, CustomButton, StyledDataTable, CustomComboBox
from sar.src.ui.design_system.utils.icons import Icons
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.storage.repositories import ProduccionRepository
from sar.src.storage.api_client import APIClient

class OrderProcessingDialog(QDialog):
    """Modal dialog to authorize or reject granular Solicitudes and references under an Order."""

    def __init__(self, db_connector, orden_id: int, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.orden_id = orden_id
        self.solicitudes_data = []
        self.orden_estado = ""
        self.api_client = APIClient()
        
        self.setWindowTitle("Procesar Referencias por Solicitud")
        self.resize(1000, 680)
        self.setMinimumSize(900, 600)
        self.setObjectName("orderProcessingDialog")

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)

        # 1. Header Section
        self.header_layout = QHBoxLayout()
        self.lbl_title = CustomLabel("Procesar Referencias por Solicitud", variant="header")
        self.lbl_subtitle = CustomLabel("Orden: ... | Total de solicitudes: 0 | Referencias pendientes por autorización: 0", variant="body")
        self.lbl_subtitle.setObjectName("orderProcessingSubtitle")
        
        title_block = QVBoxLayout()
        title_block.addWidget(self.lbl_title)
        title_block.addWidget(self.lbl_subtitle)
        self.header_layout.addLayout(title_block)
        
        self.main_layout.addLayout(self.header_layout)

        # 2. Information Row (Metrics Card stretching full-width)
        self.banner_row = QWidget()
        self.banner_row.setStyleSheet("background: transparent;")
        banner_row_layout = QHBoxLayout(self.banner_row)
        banner_row_layout.setContentsMargins(0, 0, 0, 0)
        banner_row_layout.setSpacing(0)
        
        # Metrics block
        self.metric_frame = QFrame()
        self.metric_frame.setObjectName("orderProcessingMetricBar")
        metric_layout = QHBoxLayout(self.metric_frame)
        metric_layout.setContentsMargins(16, 6, 16, 6)
        metric_layout.setSpacing(16)
        metric_layout.setAlignment(Qt.AlignCenter)
        
        # Color dots indicators using design system Colors
        self.dot_solicitadas = QLabel()
        self.dot_solicitadas.setFixedSize(10, 10)
        self.dot_solicitadas.setStyleSheet(f"background-color: #64748B; border-radius: 5px; border: none;")
        
        self.lbl_metric_solicitadas = CustomLabel("Solicitadas: 0", variant="body")
        self.lbl_metric_solicitadas.setObjectName("orderProcessingMetricSolicitadas")
        
        self.dot_generadas = QLabel()
        self.dot_generadas.setFixedSize(10, 10)
        self.dot_generadas.setStyleSheet(f"background-color: {Colors.PRIMARY}; border-radius: 5px; border: none;")
        
        self.lbl_metric_generadas = CustomLabel("Generadas: 0", variant="body")
        self.lbl_metric_generadas.setObjectName("orderProcessingMetricGeneradas")
        
        self.dot_auth = QLabel()
        self.dot_auth.setFixedSize(10, 10)
        self.dot_auth.setStyleSheet(f"background-color: {Colors.SUCCESS}; border-radius: 5px; border: none;")
        
        self.lbl_metric_auth = CustomLabel("Autorizadas: 0", variant="body")
        self.lbl_metric_auth.setObjectName("orderProcessingMetricAuth")
        
        self.dot_rej = QLabel()
        self.dot_rej.setFixedSize(10, 10)
        self.dot_rej.setStyleSheet(f"background-color: {Colors.ERROR}; border-radius: 5px; border: none;")
        
        self.lbl_metric_rej = CustomLabel("Rechazadas: 0", variant="body")
        self.lbl_metric_rej.setObjectName("orderProcessingMetricRej")
        
        self.dot_facturadas = QLabel()
        self.dot_facturadas.setFixedSize(10, 10)
        self.dot_facturadas.setStyleSheet(f"background-color: {Colors.ACCENT_VIOLET}; border-radius: 5px; border: none;")
        
        self.lbl_metric_facturadas = CustomLabel("Facturadas: 0", variant="body")
        self.lbl_metric_facturadas.setObjectName("orderProcessingMetricFacturadas")
        
        metric_layout.addWidget(self.dot_solicitadas)
        metric_layout.addWidget(self.lbl_metric_solicitadas)
        metric_layout.addSpacing(24)
        metric_layout.addWidget(self.dot_generadas)
        metric_layout.addWidget(self.lbl_metric_generadas)
        metric_layout.addSpacing(24)
        metric_layout.addWidget(self.dot_auth)
        metric_layout.addWidget(self.lbl_metric_auth)
        metric_layout.addSpacing(24)
        metric_layout.addWidget(self.dot_rej)
        metric_layout.addWidget(self.lbl_metric_rej)
        metric_layout.addSpacing(24)
        metric_layout.addWidget(self.dot_facturadas)
        metric_layout.addWidget(self.lbl_metric_facturadas)
        
        banner_row_layout.addWidget(self.metric_frame)
        self.main_layout.addWidget(self.banner_row)
        
        # Cancelled Warning Banner (Hidden by default, shown only if order is CANCELADA)
        self.cancelled_banner = QFrame()
        self.cancelled_banner.setObjectName("orderProcessingBanner")
        self.cancelled_banner.setStyleSheet("""
            QFrame#orderProcessingBanner {
                background-color: #FEF2F2;
                border: 1px solid #FCA5A5;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        cb_layout = QHBoxLayout(self.cancelled_banner)
        cb_layout.setContentsMargins(12, 12, 12, 12)
        cb_layout.setSpacing(10)
        
        self.lbl_cb_icon = QLabel()
        self.lbl_cb_icon.setPixmap(Icons.alert_triangle("#EF4444").pixmap(18, 18))
        cb_layout.addWidget(self.lbl_cb_icon)
        
        self.lbl_cb_text = CustomLabel(
            "Esta orden se encuentra CANCELADA. Solo se permite la visualización de sus solicitudes.",
            variant="body"
        )
        self.lbl_cb_text.setStyleSheet("color: #991B1B; font-weight: bold;")
        cb_layout.addWidget(self.lbl_cb_text, stretch=1)
        
        self.cancelled_banner.setVisible(False)
        self.main_layout.addWidget(self.cancelled_banner)
 
        # 3. Filter and Selection Bar
        self.filter_layout = QHBoxLayout()
        
        self.chk_select_all = QCheckBox("Seleccionar todas (0)")
        self.chk_select_all.clicked.connect(self._on_select_all_clicked)
        self.filter_layout.addWidget(self.chk_select_all)
        self.filter_layout.addStretch()
        
        # Search Box
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar solicitud...")
        self.txt_search.setFixedWidth(220)
        self.txt_search.textChanged.connect(self._filter_table_rows)
        self.filter_layout.addWidget(self.txt_search)
        
        # Status Filter Combo
        self.lbl_filter = CustomLabel("Filtrar por estado", variant="body")
        self.lbl_filter.setStyleSheet("font-weight: bold; margin-left: 10px; background: transparent;")
        self.filter_layout.addWidget(self.lbl_filter)
        
        self.cmb_filter = CustomComboBox()
        self.cmb_filter.addItems(["Todos", "Pendientes", "Autorizadas", "Rechazadas"])
        self.cmb_filter.currentTextChanged.connect(self._filter_table_rows)
        self.filter_layout.addWidget(self.cmb_filter)
        
        self.main_layout.addLayout(self.filter_layout)

        # 4. Solicitudes Table
        headers = ["✔", "ID", "Folio Orden", "Empresa (RFC)", "Concepto", "Delegación", "Solicitadas", "Generadas", "Estado"]
        self.table = StyledDataTable(headers, parent=self)
        self.table.setColumnHidden(1, True) # Hide ID
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemChanged.connect(self._on_item_changed)
        self.main_layout.addWidget(self.table)

        # 5. Bottom Action Buttons Layout
        self.bottom_layout = QHBoxLayout()
        
        # Action Buttons
        self.btn_fase_b_excel = CustomButton("Generar Excel", is_secondary=True)
        self.btn_fase_b_excel.setIcon(Icons.file_excel("#16A34A")) # Excel green
        self.btn_fase_b_excel.setToolTip("Generar Archivos Excel Lotes")
        self.btn_fase_b_excel.clicked.connect(self._on_generar_excel_lotes)
        
        self.btn_fase_b_pdf = CustomButton("Generar PDF", is_secondary=True)
        self.btn_fase_b_pdf.setIcon(Icons.file_pdf("#DC2626")) # PDF red
        self.btn_fase_b_pdf.setToolTip("Generar Archivos PDF Unificado")
        self.btn_fase_b_pdf.clicked.connect(self._on_generar_pdf_unificado)

        self.btn_cancel = CustomButton("Cancelar", is_secondary=False)
        self.btn_cancel.setObjectName("dangerBtn")
        self.btn_cancel.setIcon(Icons.cancelar("#FFFFFF"))
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_reject = CustomButton("Rechazar seleccionadas", is_secondary=False)
        self.btn_reject.setObjectName("orderProcessingRejectBtn")
        self.btn_reject.setIcon(Icons.cancelar(Colors.ERROR))
        self.btn_reject.clicked.connect(self._on_reject_selected)
        
        self.btn_authorize = CustomButton("Autorizar seleccionadas", is_secondary=False)
        self.btn_authorize.setObjectName("orderProcessingAuthBtn")
        self.btn_authorize.setIcon(Icons.aceptar("#FFFFFF"))
        self.btn_authorize.clicked.connect(self._on_authorize_selected)
        
        self.bottom_layout.addWidget(self.btn_fase_b_excel)
        self.bottom_layout.addWidget(self.btn_fase_b_pdf)
        self.bottom_layout.addWidget(self.btn_authorize)
        self.bottom_layout.addWidget(self.btn_reject)
        self.bottom_layout.addWidget(self.btn_cancel)
        self.bottom_layout.addStretch()
        
        self.main_layout.addLayout(self.bottom_layout)
        
        self._load_data()

    def _load_data(self):
        """Loads or refreshes solicitudes data for the order. Uses API or direct DB based on CONNECT_VIA_API."""
        try:
            if self.api_client.connect_via_api:
                # Use dedicated API endpoints
                self.solicitudes_data = self.api_client.request(
                    "GET", f"/api/docs/ordenes/{self.orden_id}/solicitudes-detalle"
                )
                estado_resp = self.api_client.request(
                    "GET", f"/api/docs/ordenes/{self.orden_id}/estado"
                )
                self.orden_estado = estado_resp.get("estado", "")
            else:
                with self.db_connector.get_session() as session:
                    repo = ProduccionRepository(session)
                    self.solicitudes_data = repo.get_solicitudes_detalle_by_orden(self.orden_id)
                    self.orden_estado = repo.get_orden_estado(self.orden_id)
                
            self._populate_table()
            self._update_metrics_and_summary()
            self._apply_readonly_if_cancelled()
        except Exception as e:
            QMessageBox.critical(self, "Error al cargar datos", f"No se pudo obtener el detalle de las solicitudes:\n{str(e)}")

    def _populate_table(self):
        """Populates the StyledDataTable and sets checkboxes for PENDIENTE_AUTORIZACION states only."""
        # Block signals to prevent itemChanged loop
        self.table.blockSignals(True)
        
        is_cancelled = (self.orden_estado == "CANCELADA")
        data_rows = []
        for data in self.solicitudes_data:
            data_rows.append([
                "", # Checkbox column
                str(data["solicitud_id"]),
                data["folio_orden"],
                data["empresa"],
                data["concepto"],
                data["delegacion"],
                str(data["cantidad_solicitada"]),
                str(data["cantidad_generada"]),
                data["estado"]
            ])
            
        self.table.populate_rows(data_rows, checkable_first_col=True)
        
        # Post-customize row elements (IDs, state, checkbox permissions)
        for row_idx, data in enumerate(self.solicitudes_data):
            # Put database ID in column 1 (hidden)
            id_item = QTableWidgetItem(str(data["solicitud_id"]))
            self.table.setItem(row_idx, 1, id_item)
            
            # Retrieve generated checkbox item
            tbl_chk_item = self.table.item(row_idx, 0)
            if tbl_chk_item:
                # Allow selecting all rows for Fase B generation
                tbl_chk_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable)
                tbl_chk_item.setCheckState(Qt.CheckState.Unchecked)
                    
        self.table.blockSignals(False)
        self._filter_table_rows()

    def _filter_table_rows(self):
        """Hides or shows rows based on search filter and status filter."""
        search_text = self.txt_search.text().lower().strip()
        status_filter = self.cmb_filter.currentText()
        
        for row in range(self.table.rowCount()):
            solicitud_id_item = self.table.item(row, 1)
            empresa_item = self.table.item(row, 3)
            concepto_item = self.table.item(row, 4)
            delegacion_item = self.table.item(row, 5)
            estado_item = self.table.item(row, 8)
            
            if not all([solicitud_id_item, empresa_item, concepto_item, delegacion_item, estado_item]):
                continue
                
            # Check search match
            match_search = (
                search_text in empresa_item.text().lower() or
                search_text in concepto_item.text().lower() or
                search_text in delegacion_item.text().lower() or
                search_text in solicitud_id_item.text()
            )
            
            # Check status match
            estado_val = estado_item.text()
            match_status = True
            if status_filter == "Pendientes":
                match_status = (estado_val == "PENDIENTE_AUTORIZACION")
            elif status_filter == "Autorizadas":
                match_status = (estado_val == "AUTORIZADA")
            elif status_filter == "Rechazadas":
                match_status = (estado_val == "RECHAZADA")
                
            self.table.setRowHidden(row, not (match_search and match_status))

    def _update_metrics_and_summary(self):
        """Recalculates counts and updates the subtitles and metrics block in real time."""
        total_sols = len(self.solicitudes_data)
        
        total_solicitadas = sum(d["cantidad_solicitada"] for d in self.solicitudes_data)
        total_generadas = sum(d["cantidad_generada"] for d in self.solicitudes_data)
        total_autorizadas = sum(d["count_autorizada"] for d in self.solicitudes_data)
        total_rechazadas = sum(d["count_rechazada"] for d in self.solicitudes_data)
        total_facturadas = sum(d.get("count_facturada", 0) for d in self.solicitudes_data)
        total_pendientes = sum(d["count_pendiente"] for d in self.solicitudes_data)
        
        folio = self.solicitudes_data[0]["folio_orden"] if self.solicitudes_data else "N/A"
        
        self.lbl_subtitle.setText(
            f"Orden: {folio} | Total de solicitudes: {total_sols} | Referencias pendientes por autorización: {total_pendientes}"
        )
        
        self.lbl_metric_solicitadas.setText(f"Solicitadas: {total_solicitadas}")
        self.lbl_metric_generadas.setText(f"Generadas: {total_generadas}")
        self.lbl_metric_auth.setText(f"Autorizadas: {total_autorizadas}")
        self.lbl_metric_rej.setText(f"Rechazadas: {total_rechazadas}")
        self.lbl_metric_facturadas.setText(f"Facturadas: {total_facturadas}")
        
        # Update check all label
        self.chk_select_all.setText(f"Seleccionar todas ({total_sols})")
        self.chk_select_all.setEnabled(total_sols > 0)
        
        # Uncheck check-all if no items
        if total_sols == 0:
            self.chk_select_all.setChecked(False)

    def _on_select_all_clicked(self):
        """Handles checking or unchecking all checkable row checkboxes based on the master checkbox."""
        check_state = Qt.CheckState.Checked if self.chk_select_all.isChecked() else Qt.CheckState.Unchecked
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            # Only change if the row is not hidden and is checkable
            if not self.table.isRowHidden(row):
                chk_item = self.table.item(row, 0)
                if chk_item and (chk_item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
                    chk_item.setCheckState(check_state)
        self.table.blockSignals(False)

    def _on_item_changed(self, item):
        """Detects row checkState changes to update selection states."""
        if item.column() == 0:
            # Sync main select all checkbox
            self._sync_select_all_checkbox()

    def _sync_select_all_checkbox(self):
        """Syncs the top selection checkbox state with table row selection states."""
        any_unchecked = False
        any_checked = False
        
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                chk_item = self.table.item(row, 0)
                if chk_item and (chk_item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
                    if chk_item.checkState() == Qt.CheckState.Unchecked:
                        any_unchecked = True
                    else:
                        any_checked = True
                        
        self.chk_select_all.blockSignals(True)
        if any_checked and not any_unchecked:
            self.chk_select_all.setChecked(True)
        else:
            self.chk_select_all.setChecked(False)
        self.chk_select_all.blockSignals(False)

    def _get_selected_solicitud_ids(self) -> List[int]:
        """Returns the list of database IDs for checked rows."""
        ids = []
        for row in range(self.table.rowCount()):
            chk_item = self.table.item(row, 0)
            if chk_item and chk_item.checkState() == Qt.CheckState.Checked:
                id_item = self.table.item(row, 1)
                if id_item:
                    ids.append(int(id_item.text()))
        return ids

    def _get_selected_solicitud_ids_for_authorization(self) -> List[int]:
        """Returns database IDs only for checked rows that are in PENDIENTE_AUTORIZACION state."""
        ids = []
        for row in range(self.table.rowCount()):
            chk_item = self.table.item(row, 0)
            if chk_item and chk_item.checkState() == Qt.CheckState.Checked:
                estado_item = self.table.item(row, 8)
                if estado_item and estado_item.text() == "PENDIENTE_AUTORIZACION":
                    id_item = self.table.item(row, 1)
                    if id_item:
                        ids.append(int(id_item.text()))
        return ids

    def _process_selected_with_state(self, nuevo_estado: str, label_action: str):
        """Performs transactional update in database and provides success/error notifications."""
        selected_ids = self._get_selected_solicitud_ids()
        if not selected_ids:
            QMessageBox.warning(self, "Selección Requerida", "Seleccione al menos una solicitud de la tabla primero.")
            return

        invalid_sols = []
        valid_ids = []
        for sol_id in selected_ids:
            data = next((d for d in self.solicitudes_data if d["solicitud_id"] == sol_id), None)
            if data:
                is_pending_state = (data["estado"] == "PENDIENTE_AUTORIZACION")
                all_refs_pending = (
                    data["count_pendiente"] == data["cantidad_generada"] and 
                    data["count_autorizada"] == 0 and 
                    data["count_rechazada"] == 0
                )
                
                if not (is_pending_state and all_refs_pending):
                    invalid_sols.append(
                        f"- Solicitud ID {sol_id} (Estado: {data['estado']}, "
                        f"Pendientes: {data['count_pendiente']}/{data['cantidad_generada']})"
                    )
                else:
                    valid_ids.append(sol_id)

        if invalid_sols:
            invalid_list = "\n".join(invalid_sols)
            QMessageBox.warning(
                self, 
                "Acción Bloqueada", 
                f"No se pueden procesar las siguientes solicitudes porque no se encuentran en estado PENDIENTE_AUTORIZACION "
                f"o tienen referencias ya autorizadas/rechazadas:\n\n"
                f"{invalid_list}\n\n"
                f"Por favor, desmarque estas solicitudes antes de proceder."
            )
            return

        if not valid_ids:
            QMessageBox.warning(self, "Selección Requerida", "Seleccione al menos una solicitud válida pendiente de autorización.")
            return
            
        reply = QMessageBox.question(
            self, "Confirmar Procesamiento",
            f"¿Estás seguro de que deseas marcar las {len(valid_ids)} solicitudes seleccionadas como {label_action}?\n"
            "Esto actualizará todas sus referencias hijas pendientes.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.api_client.connect_via_api:
                    res = self.api_client.request(
                        "POST",
                        f"/api/docs/ordenes/{self.orden_id}/procesar-solicitudes",
                        json={"solicitud_ids": valid_ids, "nuevo_estado": nuevo_estado}
                    )
                    rows_updated = res.get("rows_updated", len(valid_ids))
                else:
                    with self.db_connector.get_session() as session:
                        repo = ProduccionRepository(session)
                        res = repo.procesar_estado_solicitudes_seleccionadas(valid_ids, nuevo_estado)
                        session.commit()
                    rows_updated = res["rows_updated"]
                    
                QMessageBox.information(
                    self, "Éxito", 
                    f"Se procesaron con éxito {len(valid_ids)} solicitudes ({rows_updated} referencias actualizadas)."
                )
                self._load_data()
                if self.parent() and hasattr(self.parent(), 'refresh_historial'):
                    self.parent().refresh_historial()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Ocurrió un error al procesar las solicitudes:\n{str(e)}")

    def _on_authorize_selected(self):
        self._process_selected_with_state("AUTORIZADA", "AUTORIZADAS")

    def _on_reject_selected(self):
        self._process_selected_with_state("RECHAZADA", "RECHAZADAS")

    def _get_default_directory(self) -> str:
        """Helper to get the default directory configured in parametro_sistema, pointing to 'boletas' and order subfolder."""
        import os
        try:
            if self.api_client.connect_via_api:
                data = self.api_client.request("GET", "/api/docs/config/ruta-derechos")
                base_path = data.get("ruta_derechos")
            else:
                from sar.src.storage.repositories import ConfigRepository
                with self.db_connector.get_session() as session:
                    config_repo = ConfigRepository(session)
                    base_path = config_repo.get_parametro("RUTA_DERECHOS")
            
            if base_path:
                # Obtener folio de la orden de los datos de solicitudes
                folio = self.solicitudes_data[0]["folio_orden"] if self.solicitudes_data else ""
                folio_clean = "".join(c for c in folio if c.isalnum() or c in ("-", "_")).strip()
                
                for sub in ["boletas", "BOLETAS"]:
                    sub_path = os.path.join(base_path, sub)
                    if os.path.exists(sub_path):
                        if folio_clean:
                            order_path = os.path.join(sub_path, folio_clean)
                            os.makedirs(order_path, exist_ok=True)
                            return os.path.abspath(order_path)
                        return os.path.abspath(sub_path)
                if os.path.exists(base_path):
                    if folio_clean:
                        order_path = os.path.join(base_path, folio_clean)
                        os.makedirs(order_path, exist_ok=True)
                        return os.path.abspath(order_path)
                    return os.path.abspath(base_path)
        except Exception:
            pass
        return ""

    def _confirm_generation_with_counts(self, sol_ids: List[int], file_type: str) -> bool:
        """Validates and prompts the user confirming the reference count requested vs generated."""
        selected_data = [d for d in self.solicitudes_data if d["solicitud_id"] in sol_ids]
        
        sum_solicitadas = sum(d["cantidad_solicitada"] for d in selected_data)
        sum_generadas = sum(d["cantidad_generada"] for d in selected_data)
        
        has_mismatch = any(d["cantidad_solicitada"] != d["cantidad_generada"] for d in selected_data)
        
        if has_mismatch:
            msg = (
                f"Advertencia: Existe una discrepancia en la cantidad de referencias para las solicitudes seleccionadas.\n\n"
                f"• Referencias Solicitadas: {sum_solicitadas}\n"
                f"• Referencias Generadas: {sum_generadas}\n\n"
                f"Esto significa que una o varias solicitudes seleccionadas aún no han sido completamente procesadas por el Bot A.\n\n"
                f"¿Está seguro de que desea proceder con la generación de archivos de todos modos?"
            )
            confirm = QMessageBox.warning(
                self,
                f"Confirmar Generación - Discrepancia {file_type}",
                msg,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
        else:
            msg = (
                f"Se procederá a generar los archivos {file_type} para las solicitudes seleccionadas.\n\n"
                f"• Referencias Solicitadas: {sum_solicitadas}\n"
                f"• Referencias Generadas: {sum_generadas}\n\n"
                f"¿Está seguro de que desea continuar?"
            )
            confirm = QMessageBox.question(
                self,
                f"Confirmar Generación - {file_type}",
                msg,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            
        return confirm == QMessageBox.Yes

    def _on_generar_excel_lotes(self):
        sol_ids = self._get_selected_solicitud_ids()
        if not sol_ids:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona al menos una solicitud de la tabla primero.")
            return
        
        if not self._confirm_generation_with_counts(sol_ids, "Excel"):
            return
            
        try:
            from PySide6.QtWidgets import QFileDialog
            default_dir = self._get_default_directory()
            dest_dir = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta para Guardar Excel Lotes", default_dir)
            if not dest_dir:
                return
                
            from sar.src.services.fase_b_service import FaseBService, FaseBWorker
            from sar.src.ui.design_system.components import GLLoadingDialog
            
            service = FaseBService(self.db_connector)
            
            # Check for existing file conflicts
            conflicts = service.check_conflicting_files(sol_ids, dest_dir, action_type="excel")
            if conflicts:
                conflicts_str = "\n".join([f"- {name}" for name in conflicts])
                replace_confirm = QMessageBox.warning(
                    self,
                    "Archivos Existentes - Reemplazar",
                    f"Los siguientes archivos ya existen en la carpeta de destino:\n\n{conflicts_str}\n\n¿Desea reemplazarlos?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if replace_confirm != QMessageBox.Yes:
                    return
            
            # Show Loading dialog
            self.loading_dialog = GLLoadingDialog("Generando archivos Excel...", self)
            self.loading_dialog.show()
            
            # Start background worker
            self.excel_worker = FaseBWorker(service, sol_ids, dest_dir, action_type="excel")
            
            def on_finished(result):
                self.loading_dialog.close()
                if result["success"]:
                    archivos_str = "\n".join([f"- {name}" for name in result["archivos"]])
                    msg = (
                        f"¡Archivos Excel generados con éxito!\n\n"
                        f"Total de referencias: {result['total_referencias']}\n"
                        f"Total de lotes: {result['lotes_generados']}\n\n"
                        f"Archivos:\n{archivos_str}\n\n"
                        f"Guardados en:\n{dest_dir}"
                    )
                    QMessageBox.information(self, "Éxito - Generar Excel", msg)
                else:
                    QMessageBox.warning(self, "Advertencia - Generar Excel", result["message"])
                    
            def on_error(err):
                self.loading_dialog.close()
                QMessageBox.critical(self, "Error - Generar Excel", f"Ocurrió un error al generar los archivos Excel:\n{str(err)}")
                
            self.excel_worker.finished.connect(on_finished)
            self.excel_worker.error.connect(on_error)
            self.excel_worker.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error - Generar Excel", f"Ocurrió un error al iniciar la generación de Excel:\n{str(e)}")

    def _on_generar_pdf_unificado(self):
        sol_ids = self._get_selected_solicitud_ids()
        if not sol_ids:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona al menos una solicitud de la tabla primero.")
            return
        
        if not self._confirm_generation_with_counts(sol_ids, "PDF"):
            return
            
        try:
            from PySide6.QtWidgets import QFileDialog
            default_dir = self._get_default_directory()
            dest_dir = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta para Guardar PDF Unificado", default_dir)
            if not dest_dir:
                return
                
            from sar.src.services.fase_b_service import FaseBService, FaseBWorker
            from sar.src.ui.design_system.components import GLLoadingDialog
            
            service = FaseBService(self.db_connector)
            
            # Check for existing file conflicts
            conflicts = service.check_conflicting_files(sol_ids, dest_dir, action_type="pdf")
            if conflicts:
                conflicts_str = "\n".join([f"- {name}" for name in conflicts])
                replace_confirm = QMessageBox.warning(
                    self,
                    "Archivos Existentes - Reemplazar",
                    f"Los siguientes archivos ya existen en la carpeta de destino:\n\n{conflicts_str}\n\n¿Desea reemplazarlos?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if replace_confirm != QMessageBox.Yes:
                    return
            
            # Show Loading dialog
            self.loading_dialog = GLLoadingDialog("Generando PDFs unificados...", self)
            self.loading_dialog.show()
            
            # Start background worker
            self.pdf_worker = FaseBWorker(service, sol_ids, dest_dir, action_type="pdf")
            
            def on_finished(result):
                self.loading_dialog.close()
                if result["success"]:
                    archivos_str = "\n".join([f"- {name}" for name in result["archivos"]])
                    msg = (
                        f"¡PDFs unificados generados con éxito!\n\n"
                        f"Total de referencias: {result['total_referencias']}\n"
                        f"Total de lotes: {result['lotes_generados']}\n\n"
                        f"Archivos:\n{archivos_str}\n\n"
                        f"Guardados en:\n{dest_dir}"
                    )
                    QMessageBox.information(self, "Éxito - Generar PDF Unificado", msg)
                else:
                    QMessageBox.warning(self, "Advertencia - Generar PDF Unificado", result["message"])
                    
            def on_error(err):
                self.loading_dialog.close()
                QMessageBox.critical(self, "Error - Generar PDF Unificado", f"Ocurrió un error al generar los PDFs unificados:\n{str(err)}")
                
            self.pdf_worker.finished.connect(on_finished)
            self.pdf_worker.error.connect(on_error)
            self.pdf_worker.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error - Generar PDF Unificado", f"Ocurrió un error al iniciar la generación de PDFs:\n{str(e)}")

    def _apply_readonly_if_cancelled(self):
        """Disables controls and displays a warning banner if the order is cancelled."""
        if self.orden_estado == "CANCELADA":
            self.btn_reject.setEnabled(False)
            self.btn_authorize.setEnabled(False)
            self.chk_select_all.setEnabled(False)
            self.chk_select_all.setChecked(False)
            self.cancelled_banner.setVisible(True)
        else:
            self.btn_reject.setEnabled(True)
            self.btn_authorize.setEnabled(True)
            self.cancelled_banner.setVisible(False)
