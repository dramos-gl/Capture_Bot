"""Requests (Bandeja de Trabajo) View."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt
from sar.src.ui.design_system.components import CustomCard, CustomLabel, CustomButton, StyledDataTable
from sar.src.storage.repositories import OperacionRepository

class RequestsView(QWidget):
    """View to manage and execute Solicitudes (Work Queue)."""
    
    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(24)
        
        from sar.src.ui.design_system.components import FilterBar
        
        self.filter_bar = FilterBar(
            search_placeholder="Buscar solicitud",
            state_options=["Activas", "Todas", "Pendientes", "Asignadas", "Canceladas"],
            on_search=self._filter_table_by_text,
            on_state_change=self._filter_table_by_state,
            on_action=self.refresh_data,
            action_icon_name="refresh",
            action_tooltip="Actualizar Bandeja",
            parent=self
        )
        self.layout.addWidget(self.filter_bar)
        
        # Main Card for the Data Table
        self.card = CustomCard(title="Solicitudes Pendientes y en Proceso", parent=self)
        
        # Table Organism
        headers = ["ID Solicitud", "Grupo", "Folio Orden", "Empresa (RFC)", "Concepto", "Delegación", "Solicitadas", "Generadas", "Estado", "Asignado a"]
        self.table = StyledDataTable(headers, parent=self)
        self.table.setMinimumHeight(400)
        
        self.card.add_widget(self.table)
        
        # Action Buttons Layout
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        
        self.btn_asignar = CustomButton("Asignar Usuario")
        self.btn_asignar.clicked.connect(self._on_asignar)
        
        self.btn_editar = CustomButton("Editar Cantidad", is_secondary=True)
        self.btn_editar.clicked.connect(self._on_editar)
        
        self.btn_cancelar = CustomButton("Cancelar Solicitud", is_secondary=True)
        self.btn_cancelar.setObjectName("dangerBtn")
        self.btn_cancelar.clicked.connect(self._on_cancelar)
        
        actions_layout.addWidget(self.btn_asignar)
        actions_layout.addWidget(self.btn_editar)
        actions_layout.addWidget(self.btn_cancelar)
        
        self.card.layout.addLayout(actions_layout)
        self.layout.addWidget(self.card)
        
        self.refresh_data()
        
    def _get_selected_solicitud_id(self) -> int:
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona una solicitud de la tabla primero.")
            return -1
        row = selected[0].row()
        item = self.table.item(row, 0)
        return int(item.text())

    def _on_asignar(self):
        sol_id = self._get_selected_solicitud_id()
        if sol_id == -1: return
        
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
                item, ok = QInputDialog.getItem(self, "Asignar Solicitud", "Selecciona el usuario:", items, 0, False)
                
            if ok and item:
                u_id = int(item.split(" - ")[0])
                with self.db_connector.get_session() as session:
                    repo = OperacionRepository(session)
                    repo.asignar_solicitud(sol_id, u_id)
                QMessageBox.information(self, "Éxito", "Solicitud asignada correctamente.")
                self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al asignar: {str(e)}")
            
    def _on_editar(self):
        sol_id = self._get_selected_solicitud_id()
        if sol_id == -1: return
        
        from PySide6.QtWidgets import QInputDialog
        qty, ok = QInputDialog.getInt(self, "Editar Cantidad", "Ingresa la nueva cantidad:", 1, minValue=1, maxValue=1000000)
        
        if ok:
            try:
                with self.db_connector.get_session() as session:
                    repo = OperacionRepository(session)
                    repo.editar_cantidad_solicitud(sol_id, qty)
                QMessageBox.information(self, "Éxito", "Cantidad actualizada correctamente.")
                self.refresh_data()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al editar: {str(e)}")
                
    def _on_cancelar(self):
        sol_id = self._get_selected_solicitud_id()
        if sol_id == -1: return
        
        reply = QMessageBox.question(self, "Confirmar Cancelación", f"¿Estás seguro que deseas cancelar la solicitud {sol_id}?", QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                with self.db_connector.get_session() as session:
                    repo = OperacionRepository(session)
                    repo.cancelar_solicitud(sol_id)
                QMessageBox.information(self, "Éxito", "Solicitud cancelada correctamente.")
                self.refresh_data()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al cancelar: {str(e)}")
        
    def refresh_data(self):
        """Fetches the latest Solicitudes from the database."""
        try:
            with self.db_connector.get_session() as session:
                repo = OperacionRepository(session)
                solicitudes = repo.get_solicitudes()
                
                data_rows = []
                for s in solicitudes:
                    data_rows.append([
                        str(s["solicitud_id"]),
                        str(s["grupo_id"]),
                        s["folio"],
                        s["rfc"],
                        s["concepto"],
                        s["delegacion"],
                        str(s["cantidad_solicitada"]),
                        str(s["cantidad_generada"]),
                        s["estado"],
                        s["usuario_asignado"]
                    ])
                    
                self.table.populate_rows(data_rows)
                self._apply_filters()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar la bandeja de trabajo:\n{str(e)}")

    def _filter_table_by_text(self, text: str):
        self._current_search_text = text.lower()
        self._apply_filters()
        
    def _filter_table_by_state(self, state: str):
        self._current_estado_filter = state
        self._apply_filters()

    def _apply_filters(self):
        search_text = getattr(self, '_current_search_text', "")
        estado_filter = getattr(self, '_current_estado_filter', "Activas")
        
        for row in range(self.table.rowCount()):
            estado = self.table.item(row, 8).text() if self.table.item(row, 8) else ""
            
            # 1. State Filter Logic
            state_match = True
            if estado_filter == "Activas":
                state_match = estado in ["PENDIENTE", "ASIGNADO", "PROCESANDO", "BORRADOR"]
            elif estado_filter == "Pendientes":
                state_match = estado == "PENDIENTE"
            elif estado_filter == "Asignadas":
                state_match = estado == "ASIGNADO"
            elif estado_filter == "Canceladas":
                state_match = estado in ["CANCELADO", "CANCELADA"]
            # "Todas" matches everything
            
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
