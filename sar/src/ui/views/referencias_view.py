"""Referencias View."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt
from sar.src.ui.design_system.components import CustomCard, CustomButton, StyledDataTable, FilterBar
from sar.src.storage.repositories import ProduccionRepository

class ReferenciasView(QWidget):
    """View to consult the final generated Referencias."""
    
    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        
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
            action_icon_name="refresh",
            action_tooltip="Actualizar Referencias",
            parent=self
        )
        self.layout.addWidget(self.filter_bar)
        
        # Main Card for the Data Table
        self.card = CustomCard(title="Producción de Referencias", parent=self)
        
        # Table Organism
        headers = ["✔", "ID", "Consecutivo", "Referencia", "Importe", "Folio Orden", "Grupo", "Empresa", "Concepto", "Delegación", "Estado", "Procesado Por", "Fecha Gen.", "Vigencia"]
        self.table = StyledDataTable(headers, parent=self)
        self.table.setMinimumHeight(400)
        self.table.setColumnHidden(1, True) # Ocultamos el ID Interno
        
        self.card.add_widget(self.table)
        
        # Action Buttons Layout
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        
        self.btn_marcar_visibles = CustomButton("Marcar Visibles", is_secondary=True)
        self.btn_marcar_visibles.clicked.connect(self._on_marcar_visibles)
        
        self.btn_estado = CustomButton("Cambiar Estado")
        self.btn_estado.clicked.connect(self._on_cambiar_estado)
        
        self.btn_asignar = CustomButton("Asignar Usuario")
        self.btn_asignar.clicked.connect(self._on_asignar)
        
        self.btn_detalle = CustomButton("Ver Detalle", is_secondary=True)
        self.btn_detalle.clicked.connect(self._on_ver_detalle)
        
        self.btn_pdf = CustomButton("Ver PDF", is_secondary=True)
        self.btn_pdf.clicked.connect(self._on_ver_pdf)
        
        actions_layout.addWidget(self.btn_marcar_visibles)
        actions_layout.addWidget(self.btn_estado)
        actions_layout.addWidget(self.btn_asignar)
        actions_layout.addWidget(self.btn_detalle)
        actions_layout.addWidget(self.btn_pdf)
        
        self.card.layout.addLayout(actions_layout)
        self.layout.addWidget(self.card)
        
        self._current_search_text = ""
        self._current_estado_filter = "Todos"
        
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

    def _on_asignar(self):
        ref_ids = self._get_selected_referencia_ids()
        if not ref_ids:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona al menos una referencia usando las casillas (✔) o haciendo clic en una fila.")
            return
            
        try:
            with self.db_connector.get_session() as session:
                from sar.src.storage.repositories import UsuarioRepository
                u_repo = UsuarioRepository(session)
                usuarios = u_repo.get_all_usuarios()
                
                if not usuarios:
                    QMessageBox.warning(self, "Sin Usuarios", "No hay usuarios disponibles.")
                    return
                    
                items = [f"{u.usuario_id} - {u.nombre} ({u.username})" for u in usuarios]
                from PySide6.QtWidgets import QInputDialog
                item, ok = QInputDialog.getItem(self, "Asignar Referencias", f"Selecciona el usuario para {len(ref_ids)} referencias:", items, 0, False)
                
            if ok and item:
                u_id = int(item.split(" - ")[0])
                with self.db_connector.get_session() as session:
                    repo = ProduccionRepository(session)
                    repo.asignar_referencias(ref_ids, u_id)
                QMessageBox.information(self, "Éxito", f"{len(ref_ids)} referencias asignadas correctamente.")
                self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al asignar: {str(e)}")

    def _on_marcar_visibles(self):
        """Marca las casillas de todas las filas que actualmente son visibles en la tabla."""
        from PySide6.QtCore import Qt
        count = 0
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                item_check = self.table.item(row, 0)
                if item_check:
                    item_check.setCheckState(Qt.CheckState.Checked)
                    count += 1
        QMessageBox.information(self, "Selección", f"Se han marcado {count} referencias visibles.")

    def _on_cambiar_estado(self):
        ref_ids = self._get_selected_referencia_ids()
        if not ref_ids:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona al menos una referencia.")
            return
            
        from PySide6.QtWidgets import QInputDialog
        opciones = ["AUTORIZADA", "RECHAZADA"]
        item, ok = QInputDialog.getItem(self, "Cambiar Estado", f"Selecciona el nuevo estado para {len(ref_ids)} referencias:", opciones, 0, False)
        
        if ok and item:
            try:
                with self.db_connector.get_session() as session:
                    repo = ProduccionRepository(session)
                    repo.update_referencias_estado_masivo(ref_ids, item)
                QMessageBox.information(self, "Éxito", f"{len(ref_ids)} referencias cambiadas a {item}.")
                self.refresh_data()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al cambiar estado: {str(e)}")

    def _on_ver_detalle(self):
        ref_ids = self._get_selected_referencia_ids()
        if not ref_ids: return
        QMessageBox.information(self, "Detalle", f"Detalles de la referencia ID: {ref_ids[0]}\\n(Funcionalidad en desarrollo)")
        
    def _on_ver_pdf(self):
        ref_ids = self._get_selected_referencia_ids()
        if not ref_ids: return
        QMessageBox.information(self, "PDF", f"Abriendo visor PDF para la referencia ID: {ref_ids[0]}\\n(Funcionalidad en desarrollo)")
        
    def refresh_data(self):
        """Fetches the latest Referencias from the database."""
        try:
            with self.db_connector.get_session() as session:
                repo = ProduccionRepository(session)
                referencias = repo.get_referencias(limit=500)
                
                data_rows = []
                for r in referencias:
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
                    
                self.table.populate_rows(data_rows, checkable_first_col=True)
                self._apply_filters()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar la producción de referencias:\\n{str(e)}")

    def _filter_table_by_text(self, text: str):
        self._current_search_text = text.lower()
        self._apply_filters()
        
    def _filter_table_by_state(self, state: str):
        self._current_estado_filter = state
        self._apply_filters()

    def _apply_filters(self):
        search_text = getattr(self, '_current_search_text', "")
        estado_filter = getattr(self, '_current_estado_filter', "Todos")
        
        for row in range(self.table.rowCount()):
            estado = self.table.item(row, 10).text() if self.table.item(row, 10) else ""
            
            # 1. State Filter Logic
            state_match = True
            if estado_filter != "Todos":
                state_match = estado == estado_filter
            
            # 2. Search Text Logic (search across all columns)
            text_match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and search_text in item.text().lower():
                    text_match = True
                    break
                    
            if state_match and text_match:
                self.table.setRowHidden(row, False)
            else:
                self.table.setRowHidden(row, True)
