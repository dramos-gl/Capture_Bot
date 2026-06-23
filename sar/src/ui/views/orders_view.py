"""Orders Management View."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMessageBox
)
from sar.src.ui.design_system.components import (
    CustomCard, CustomLabel, CustomButton, InteractiveGrid, CustomInput, CustomComboBox
)
from sar.src.storage.repositories import CatalogoRepository
from sar.src.services.ordenes_service import OrdenesService
from sar.src.ui.design_system.components.molecules.gl_labeled_input import LabeledInput

class OrdersView(QWidget):
    """View to manage and create Orders."""
    
    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        
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
        
        self.tabs.addTab(self.tab_historial, "Órdenes Capturadas")
        self.tabs.addTab(self.tab_nueva, "Capturar Nueva Orden")
        
        self.layout.addWidget(self.tabs)
        
        self._setup_historial_tab()
        self._setup_nueva_orden_tab()
        
        # Pre-load catalogs and data
        self._load_catalogs()
        self.refresh_historial()
        
        # Agregamos el primer renglón por defecto en la nueva orden
        self.grid.add_row()
        
    def _setup_historial_tab(self):
        from sar.src.ui.design_system.components import StyledDataTable, CustomCard
        layout = QVBoxLayout(self.tab_historial)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Main Card for the Data Table
        self.historial_card = CustomCard(parent=self)
        
        headers = ["✔", "ID", "Folio", "Descripción", "Estado", "Creador", "Fecha Creación", "Total Solicitadas", "Total Generadas"]
        self.table_historial = StyledDataTable(headers, parent=self)
        self.table_historial.setColumnHidden(1, True) # Ocultar ID interno
        self.table_historial.cellDoubleClicked.connect(self._on_row_double_clicked)
        
        self.historial_card.add_widget(self.table_historial)
        
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        
        self.btn_autorizar_orden = CustomButton("Autorizar Orden Completa")
        self.btn_autorizar_orden.clicked.connect(self._on_autorizar_orden)
        
        self.btn_rechazar_orden = CustomButton("Rechazar Orden Completa", is_secondary=True)
        self.btn_rechazar_orden.clicked.connect(self._on_rechazar_orden)
        
        actions_layout.addWidget(self.btn_autorizar_orden)
        actions_layout.addWidget(self.btn_rechazar_orden)
        
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
            with self.db_connector.get_session() as session:
                repo = CatalogoRepository(session)
                rfcs = [(r.rfc_id, r.rfc) for r in repo.get_rfcs_activos()]
                conceptos = [(c.concepto_id, c.nombre) for c in repo.get_conceptos_activos()]
                delegaciones = [(d.delegacion_id, d.nombre) for d in repo.get_delegaciones_activas()]
                
                self.grid.set_catalogs(rfcs, conceptos, delegaciones)
                
                # Load municipios to combo_municipio
                municipios = [m for m in repo.get_all_municipios() if m.activo]
                self.combo_municipio.clear()
                default_index = 0
                for idx, m in enumerate(municipios):
                    self.combo_municipio.addItem(m.nombre, m.municipio_id)
                    # Benito Juárez is typically ID 2 or has 'BENITO' in the name
                    if m.municipio_id == 2 or "BENITO" in m.nombre.upper():
                        default_index = idx
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
        reply = QMessageBox.question(
            self, "Confirmar Guardar",
            "¿Estás seguro de que deseas guardar esta orden?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
                
        # Main Window should have the current session id and user id, but we might only have session id.
        # We can extract the user_id by querying the session in the DB, or just pass it down.
        # For this desktop app, we fetch user_id from the current session.
        main_window = self.window()
        current_sesion_id = getattr(main_window, 'current_sesion_id', None)
        
        try:
            with self.db_connector.get_session() as session:
                # Get current user
                from sar.src.storage.models import Sesion
                db_sesion = session.get(Sesion, current_sesion_id) if current_sesion_id else None
                usuario_id = db_sesion.usuario_id if db_sesion else 1 # Fallback to 1 for dev if no session
                
                service = OrdenesService(session)
                nueva_orden = service.crear_orden_manual(
                    usuario_id=usuario_id,
                    sesion_id=current_sesion_id,
                    descripcion=desc,
                    municipio_id=municipio_id,
                    renglones=data
                )
                
                QMessageBox.information(
                    self, "Éxito", 
                    f"Orden {nueva_orden.folio} creada correctamente con {len(data)} grupos."
                )
                
                # Reset Form
                self.desc_input.setText("")
                self.grid.clear()
                self.grid.add_row()
                
        except Exception as e:
            QMessageBox.critical(self, "Error al Guardar", f"Hubo un problema al crear la orden:\n{str(e)}")

    def refresh_historial(self):
        try:
            from sar.src.storage.repositories import ProduccionRepository
            with self.db_connector.get_session() as session:
                repo = ProduccionRepository(session)
                ordenes = repo.get_ordenes()
                
                data_rows = []
                for o in ordenes:
                    data_rows.append([
                        "", # Checkbox vacio inicial
                        str(o["orden_id"]),
                        o["folio"],
                        o["descripcion"],
                        o["estado"],
                        o["creador"],
                        o["fecha_creacion"],
                        str(o["total_solicitadas"]),
                        str(o["total_generadas"])
                    ])
                    
                self.table_historial.populate_rows(data_rows, checkable_first_col=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el historial de órdenes:\n{str(e)}")

    def _on_row_double_clicked(self, row: int, column: int):
        id_item = self.table_historial.item(row, 1)
        if id_item:
            orden_id = int(id_item.text())
            from sar.src.ui.views.order_processing_dialog import OrderProcessingDialog
            dialog = OrderProcessingDialog(self.db_connector, orden_id, self)
            dialog.exec()

    def _get_selected_ordenes(self) -> list[int]:
        from PySide6.QtCore import Qt
        ids = []
        for row in range(self.table_historial.rowCount()):
            item_check = self.table_historial.item(row, 0)
            if item_check and item_check.checkState() == Qt.CheckState.Checked:
                ids.append(int(self.table_historial.item(row, 1).text()))
                
        if not ids:
            selected = self.table_historial.selectedItems()
            if selected:
                row = selected[0].row()
                ids.append(int(self.table_historial.item(row, 1).text()))
        return ids

    def _change_orden_estado(self, estado_codigo: str):
        orden_ids = self._get_selected_ordenes()
        if not orden_ids:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona al menos una orden para procesar.")
            return
            
        reply = QMessageBox.question(self, "Confirmar Acción", 
            f"¿Estás seguro de que deseas marcar {len(orden_ids)} orden(es) como {estado_codigo}? Esto actualizará todas sus referencias.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
        if reply == QMessageBox.Yes:
            try:
                from sar.src.storage.repositories import ProduccionRepository
                with self.db_connector.get_session() as session:
                    repo = ProduccionRepository(session)
                    for oid in orden_ids:
                        repo.update_orden_estado_masivo(oid, estado_codigo)
                QMessageBox.information(self, "Éxito", f"Las órdenes fueron procesadas como {estado_codigo}.")
                self.refresh_historial()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Ocurrió un error: {str(e)}")

    def _on_autorizar_orden(self):
        self._change_orden_estado("AUTORIZADA")
        
    def _on_rechazar_orden(self):
        self._change_orden_estado("RECHAZADA")
