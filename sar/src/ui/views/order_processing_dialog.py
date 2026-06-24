"""Interactive Dialog to process individual or multiple Solicitudes within an Order."""

from typing import List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QMessageBox, QFrame, QLineEdit, QComboBox, QCheckBox, QTableWidgetItem, QLabel
)
from PySide6.QtCore import Qt
from sar.src.ui.design_system.components import CustomLabel, CustomButton, StyledDataTable, CustomComboBox
from sar.src.ui.design_system.utils.icons import Icons
from sar.src.storage.repositories import ProduccionRepository

class OrderProcessingDialog(QDialog):
    """Modal dialog to authorize or reject granular Solicitudes and references under an Order."""

    def __init__(self, db_connector, orden_id: int, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.orden_id = orden_id
        self.solicitudes_data = []
        self.orden_estado = ""
        
        self.setWindowTitle("Procesar Solicitudes de la Orden")
        self.resize(1000, 680)
        self.setMinimumSize(900, 600)
        self.setObjectName("orderProcessingDialog")

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)

        # 1. Header Section
        self.header_layout = QHBoxLayout()
        self.lbl_title = CustomLabel("Procesar Solicitudes de la Orden", variant="header")
        self.lbl_subtitle = CustomLabel("Orden: ... | Total de solicitudes: 0 | Pendientes de autorización: 0", variant="body")
        self.lbl_subtitle.setObjectName("orderProcessingSubtitle")
        
        title_block = QVBoxLayout()
        title_block.addWidget(self.lbl_title)
        title_block.addWidget(self.lbl_subtitle)
        self.header_layout.addLayout(title_block)
        self.header_layout.addStretch()
        
        # Close button
        self.btn_close_top = CustomButton("✕", is_secondary=True)
        self.btn_close_top.setFixedSize(32, 32)
        self.btn_close_top.setObjectName("orderProcessingCloseBtn")
        self.btn_close_top.clicked.connect(self.reject)
        self.header_layout.addWidget(self.btn_close_top)
        
        self.main_layout.addLayout(self.header_layout)

        # 2. Information Banner
        self.banner = QFrame()
        self.banner.setObjectName("orderProcessingBanner")
        banner_layout = QHBoxLayout(self.banner)
        banner_layout.setContentsMargins(12, 12, 12, 12)
        banner_layout.setSpacing(10)
        
        self.lbl_banner_icon = QLabel()
        if hasattr(Icons, 'check'):
            self.lbl_banner_icon.setPixmap(Icons.check("#2563EB").pixmap(18, 18))
        banner_layout.addWidget(self.lbl_banner_icon)
        
        self.lbl_banner_text = CustomLabel(
            "Seleccione las solicitudes que desea procesar. Puede autorizar o rechazar individualmente o todas las pendientes.",
            variant="body"
        )
        self.lbl_banner_text.setObjectName("orderProcessingBannerText")
        banner_layout.addWidget(self.lbl_banner_text, stretch=1)
        
        self.main_layout.addWidget(self.banner)

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
        
        # Refresh Button
        self.btn_refresh = CustomButton("↻")
        self.btn_refresh.setFixedSize(35, 35)
        self.btn_refresh.clicked.connect(self._load_data)
        self.filter_layout.addWidget(self.btn_refresh)
        
        self.main_layout.addLayout(self.filter_layout)

        # 4. Solicitudes Table
        headers = ["✔", "ID", "Folio Orden", "Empresa (RFC)", "Concepto", "Delegación", "Solicitadas", "Generadas", "Estado"]
        self.table = StyledDataTable(headers, parent=self)
        self.table.setColumnHidden(1, True) # Hide ID
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemChanged.connect(self._on_item_changed)
        self.main_layout.addWidget(self.table)

        # 5. Bottom Metrics Bar and Action Buttons
        self.bottom_layout = QHBoxLayout()
        
        # Metrics block
        self.metric_frame = QFrame()
        self.metric_frame.setObjectName("orderProcessingMetricBar")
        metric_layout = QHBoxLayout(self.metric_frame)
        metric_layout.setContentsMargins(12, 6, 12, 6)
        metric_layout.setSpacing(16)
        
        self.lbl_metric_pending = CustomLabel("Pendientes: 0", variant="body")
        self.lbl_metric_pending.setObjectName("orderProcessingMetricPending")
        self.lbl_metric_auth = CustomLabel("Autorizadas: 0", variant="body")
        self.lbl_metric_auth.setObjectName("orderProcessingMetricAuth")
        self.lbl_metric_rej = CustomLabel("Rechazadas: 0", variant="body")
        self.lbl_metric_rej.setObjectName("orderProcessingMetricRej")
        
        metric_layout.addWidget(self.lbl_metric_pending)
        metric_layout.addWidget(self.lbl_metric_auth)
        metric_layout.addWidget(self.lbl_metric_rej)
        
        self.bottom_layout.addWidget(self.metric_frame)
        self.bottom_layout.addStretch()
        
        # Action Buttons
        self.btn_cancel = CustomButton("Cancelar", is_secondary=True)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_reject = CustomButton("Rechazar seleccionadas", is_secondary=False)
        self.btn_reject.setObjectName("orderProcessingRejectBtn")
        self.btn_reject.clicked.connect(self._on_reject_selected)
        
        self.btn_authorize = CustomButton("Autorizar seleccionadas", is_secondary=False)
        self.btn_authorize.setObjectName("orderProcessingAuthBtn")
        self.btn_authorize.clicked.connect(self._on_authorize_selected)
        
        self.bottom_layout.addWidget(self.btn_cancel)
        self.bottom_layout.addWidget(self.btn_reject)
        self.bottom_layout.addWidget(self.btn_authorize)
        
        self.main_layout.addLayout(self.bottom_layout)
        
        self._load_data()

    def _load_data(self):
        """Loads or refreshes solicitudes data for the order from the database."""
        try:
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
                if data["estado"] != "PENDIENTE_AUTORIZACION" or is_cancelled:
                    # Remove user checkability for other states or if cancelled
                    tbl_chk_item.setFlags(Qt.ItemFlag.ItemIsSelectable)
                    tbl_chk_item.setCheckState(Qt.CheckState.Unchecked)
                else:
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
        pendientes = sum(1 for d in self.solicitudes_data if d["estado"] == "PENDIENTE_AUTORIZACION")
        autorizadas = sum(1 for d in self.solicitudes_data if d["estado"] == "AUTORIZADA")
        rechazadas = sum(1 for d in self.solicitudes_data if d["estado"] == "RECHAZADA")
        
        folio = self.solicitudes_data[0]["folio_orden"] if self.solicitudes_data else "N/A"
        
        self.lbl_subtitle.setText(
            f"Orden: {folio} | Total de solicitudes: {total_sols} | Pendientes de autorización: {pendientes}"
        )
        
        self.lbl_metric_pending.setText(f"Pendientes: {pendientes}")
        self.lbl_metric_auth.setText(f"Autorizadas: {autorizadas}")
        self.lbl_metric_rej.setText(f"Rechazadas: {rechazadas}")
        
        # Update check all label
        self.chk_select_all.setText(f"Seleccionar todas ({pendientes})")
        self.chk_select_all.setEnabled(pendientes > 0)
        
        # Uncheck check-all if no pending
        if pendientes == 0:
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

    def _process_selected_with_state(self, nuevo_estado: str, label_action: str):
        """Performs transactional update in database and provides success/error notifications."""
        selected_ids = self._get_selected_solicitud_ids()
        if not selected_ids:
            QMessageBox.warning(self, "Selección Requerida", "Seleccione al menos una solicitud pendiente de autorización.")
            return
            
        reply = QMessageBox.question(
            self, "Confirmar Procesamiento",
            f"¿Estás seguro de que deseas marcar las {len(selected_ids)} solicitudes seleccionadas como {label_action}?\n"
            "Esto actualizará todas sus referencias hijas pendientes.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                with self.db_connector.get_session() as session:
                    repo = ProduccionRepository(session)
                    res = repo.procesar_estado_solicitudes_seleccionadas(selected_ids, nuevo_estado)
                    session.commit()
                    
                QMessageBox.information(
                    self, "Éxito", 
                    f"Se procesaron con éxito {len(selected_ids)} solicitudes ({res['rows_updated']} referencias actualizadas)."
                )
                self._load_data()
                self.parent().refresh_historial() # Update main view order list
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Ocurrió un error al procesar las solicitudes:\n{str(e)}")

    def _on_authorize_selected(self):
        self._process_selected_with_state("AUTORIZADA", "AUTORIZADAS")

    def _on_reject_selected(self):
        self._process_selected_with_state("RECHAZADA", "RECHAZADAS")

    def _apply_readonly_if_cancelled(self):
        """Disables controls and displays a warning banner if the order is cancelled."""
        if self.orden_estado == "CANCELADA":
            self.btn_reject.setEnabled(False)
            self.btn_authorize.setEnabled(False)
            self.chk_select_all.setEnabled(False)
            self.chk_select_all.setChecked(False)
            
            # Update banner for cancelled status
            self.lbl_banner_text.setText(
                "Esta orden se encuentra CANCELADA. Solo se permite la visualización de sus solicitudes."
            )
            # Use warning triangle icon
            self.lbl_banner_icon.setPixmap(Icons.alert_triangle("#EF4444").pixmap(18, 18))
            
            # Change banner background styling to a light red alert style
            self.banner.setStyleSheet("""
                QFrame#orderProcessingBanner {
                    background-color: #FEF2F2;
                    border: 1px solid #FCA5A5;
                    border-radius: 8px;
                    padding: 12px;
                }
            """)
            self.lbl_banner_text.setStyleSheet("color: #991B1B; font-weight: bold;")
        else:
            self.btn_reject.setEnabled(True)
            self.btn_authorize.setEnabled(True)
            # Default banner styling
            self.lbl_banner_text.setText(
                "Seleccione las solicitudes que desea procesar. Puede autorizar o rechazar individualmente o todas las pendientes."
            )
            self.lbl_banner_icon.setPixmap(Icons.check("#2563EB").pixmap(18, 18))
            self.banner.setStyleSheet("") # Revert to stylesheet from theme_manager
            self.lbl_banner_text.setStyleSheet("")
