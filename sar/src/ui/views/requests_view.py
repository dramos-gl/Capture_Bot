"""Requests (Bandeja de Trabajo) View."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QDialog, QScrollArea
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIntValidator
from sar.src.ui.design_system.components import (
    CustomCard, CustomLabel, CustomInput, CustomButton, StyledDataTable, KeepOpenMenu,
    GLInfoBanner, GLMessageBox as QMessageBox
)
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.services.solicitudes_ui_service import SolicitudesUIService
from sar.src.services.fase_b_service import FaseBService, FaseBWorker


class RequestsLoadWorker(QThread):
    """Background worker thread to load solicitudes dynamically."""
    result_ready = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, solicitudes_ui_service, orden_ids: list = None):
        super().__init__()
        self.solicitudes_ui_service = solicitudes_ui_service
        self.orden_ids = orden_ids
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            if self._is_cancelled:
                return
            res = self.solicitudes_ui_service.get_solicitudes(self.orden_ids)
            if not self._is_cancelled:
                self.result_ready.emit(res)
        except Exception as e:
            if not self._is_cancelled:
                self.error_occurred.emit(str(e))

class EditQuantityDialog(QDialog):
    """Dialog to edit request quantity with a fixed current field and new field."""
    def __init__(self, cant_actual: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar Cantidad")
        self.resize(360, 310)
        self.setMinimumSize(340, 300)
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.SURFACE_LIGHT};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        
        self.lbl_title = CustomLabel("Actualizar Cantidad", variant="subheader")
        layout.addWidget(self.lbl_title)
        
        # Field 1: Cantidad Actual (read-only)
        layout.addWidget(CustomLabel("Cantidad Actual:", variant="body"))
        self.txt_actual = CustomInput(str(cant_actual))
        self.txt_actual.setReadOnly(True)
        self.txt_actual.setFixedHeight(36)
        layout.addWidget(self.txt_actual)
        
        # Field 2: Nueva Cantidad
        layout.addWidget(CustomLabel("Nueva Cantidad:", variant="body"))
        self.txt_nueva = CustomInput("Ingresa la nueva cantidad")
        self.txt_nueva.setValidator(QIntValidator(1, 999999, self))
        self.txt_nueva.setFixedHeight(36)
        layout.addWidget(self.txt_nueva)
        
        layout.addStretch()

        # Buttons (Design System Action Factories)
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 8, 0, 0)
        btn_layout.setSpacing(12)
        btn_layout.addStretch()
        
        self.btn_cancel = CustomButton.action_cancelar(parent=self)
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_save = CustomButton.action_guardar(parent=self)
        self.btn_save.setFixedHeight(36)
        self.btn_save.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)
        
    def get_new_quantity(self) -> int:
        try:
            return int(self.txt_nueva.text().strip())
        except ValueError:
            return -1

class RequestsView(QWidget):
    """View to manage and execute Solicitudes (Work Queue)."""
    
    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.solicitudes_ui_service = SolicitudesUIService(self.db_connector)
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
            QWidget#requestsScrollContent {
                background-color: transparent;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setObjectName("requestsScrollContent")
        self.layout = QVBoxLayout(scroll_content)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(24)
        
        from sar.src.ui.design_system.components import FilterBar
        
        self.filter_bar = FilterBar(
            search_placeholder="Buscar solicitud",
            state_options=["Todas", "ASIGNADA", "AUTORIZADA", "CANCELADA", "COMPLETADA", "ERROR", "FACTURADA", "FACTURADA_PARCIAL", "PENDIENTE", "PROCESANDO"],
            on_search=self._filter_table_by_text,
            on_state_change=self._filter_table_by_state,
            on_action=self.refresh_data,
            action_icon_name="actualizar",
            action_tooltip="Actualizar Bandeja",
            parent=self
        )
        self.layout.addWidget(self.filter_bar)
        
        # Main Card for the Data Table
        self.card = CustomCard(title="Solicitudes Pendientes y en Proceso", parent=self)
        
        # Table Organism
        headers = ["ID Solicitud", "Grupo", "Folio Orden", "Empresa (RFC)", "Concepto", "Delegación", "Solicitadas", "Generadas", "Facturadas", "Estado", "Asignado a"]
        self.table = StyledDataTable(headers, parent=self)
        from PySide6.QtWidgets import QAbstractItemView
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setMinimumHeight(200)
        self.table.setMinimumWidth(200)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        
        self.card.add_widget(self.table)
        
        # Action Buttons & Footer Hint Layout
        actions_layout = QHBoxLayout()
        self.lbl_table_hint = CustomLabel("💡 Doble clic en 'Folio Orden' para ver detalle / lotes • Doble clic en 'Asignado a' para asignar usuario", variant="muted")
        self.lbl_table_hint.setWordWrap(True)
        actions_layout.addWidget(self.lbl_table_hint, stretch=1)
        actions_layout.addSpacing(12)
        
        self.btn_editar = CustomButton.action_editar(parent=self)
        self.btn_editar.setToolTip("Editar cantidad de la solicitud seleccionada")
        self.btn_editar.clicked.connect(self._on_editar)

        self.btn_asignar = CustomButton.action_asignar(parent=self)
        self.btn_asignar.setToolTip("Asignar usuario a solicitudes seleccionadas")
        self.btn_asignar.clicked.connect(self._on_asignar)
        
        self.btn_cancelar = CustomButton.action_cancelar(parent=self)
        self.btn_cancelar.setToolTip("Cancelar solicitud seleccionada")
        self.btn_cancelar.clicked.connect(self._on_cancelar)
        
        actions_layout.addWidget(self.btn_editar)
        actions_layout.addWidget(self.btn_asignar)
        actions_layout.addWidget(self.btn_cancelar)
        
        self.card.layout.addLayout(actions_layout)
        self.layout.addWidget(self.card)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        self.selected_orden_ids = []
        self.todas_las_ordenes = []
        self.is_custom_filter = False
        
        # Add order filter button to FilterBar layout
        from sar.src.ui.design_system.utils.icons import Icons
        self.btn_filter_orden = CustomButton("", is_secondary=True)
        self.btn_filter_orden.setIcon(Icons.filter_icon("#475569"))
        self.btn_filter_orden.setFixedSize(36, 36)
        self.btn_filter_orden.setToolTip("Filtrar solicitudes por órdenes específicas (selección múltiple)")
        self.btn_filter_orden.clicked.connect(self._show_order_filter_menu)
        
        self.filter_bar.layout().insertWidget(self.filter_bar.layout().count() - 1, self.btn_filter_orden, alignment=Qt.AlignmentFlag.AlignBottom)
        
        self._load_available_orders()
        self._update_order_filter_title()
        
    def _get_selected_solicitud_id(self) -> int:
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona una solicitud de la tabla primero.")
            return -1
        row = selected[0].row()
        item = self.table.item(row, 0)
        return int(item.text())

    def _get_selected_solicitud_ids(self) -> list[int]:
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona al menos una solicitud de la tabla primero.")
            return []
        
        # Use set to ensure unique rows are captured
        selected_rows = set(item.row() for item in selected_items)
        ids = []
        for row in sorted(selected_rows):
            item = self.table.item(row, 0)
            if item:
                ids.append(int(item.text()))
        return ids

    def _check_permission(self, modulo_codigo: str, accion_codigo: str) -> bool:
        """Helper to verify if current session/user holds permission for modulo + accion."""
        parent_window = self.window()
        usuario_id = getattr(parent_window, 'current_usuario_id', None)
        if not usuario_id:
            return True # Fallback if standalone/testing without active user session context
        
        try:
            from sar.src.storage.api_client import APIClient
            api_client = APIClient()
            if getattr(api_client, 'connect_via_api', False):
                perms = api_client.request("GET", f"/api/auth/permissions/{usuario_id}")
                return perms.get(modulo_codigo, {}).get(accion_codigo, False)
            else:
                with self.db_connector.get_session() as session:
                    from sar.src.services.security_service import SecurityService
                    sec_service = SecurityService(session)
                    return sec_service.has_permission(usuario_id, modulo_codigo, accion_codigo)
        except Exception as e:
            print(f"Error checking permission {modulo_codigo}:{accion_codigo}: {e}")
            return False

    def _on_cell_double_clicked(self, row, column):
        item = self.table.item(row, 0)
        if not item: return
        sol_id = int(item.text())

        # Column 2 corresponds to "Folio Orden"
        if column == 2:
            if not (self._check_permission("SOLICITUDES", "LEER") or self._check_permission("ORDENES", "LEER")):
                QMessageBox.warning(
                    self,
                    "Acceso Denegado",
                    "No tiene permisos suficientes para consultar el detalle de procesamiento de la orden (ORDENES:LEER)."
                )
                return
            
            try:
                orden_id = self.solicitudes_ui_service.get_orden_id_by_solicitud(sol_id)
                    
                from sar.src.ui.views.order_processing_dialog import OrderProcessingDialog
                dialog = OrderProcessingDialog(self.db_connector, orden_id, self)
                dialog.exec()
                self.refresh_data()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo abrir el detalle de la orden:\n{str(e)}")

        # Column 10 corresponds to "Asignado a"
        elif column == 10:
            self._on_asignar(target_sol_id=sol_id)

    def _get_default_directory(self) -> str:
        """Helper to get the default directory configured in parametro_sistema, pointing to 'boletas'."""
        import os
        try:
            base_path = self.solicitudes_ui_service.get_ruta_derechos()
            
            if base_path:
                # Look for boletas/BOLETAS subfolder
                for sub in ["boletas", "BOLETAS"]:
                    sub_path = os.path.join(base_path, sub)
                    if os.path.exists(sub_path):
                        return os.path.abspath(sub_path)
                if os.path.exists(base_path):
                    return os.path.abspath(base_path)
        except Exception:
            pass
        return ""

    def _on_generar_excel_lotes(self):
        sol_ids = self._get_selected_solicitud_ids()
        if not sol_ids: return
        
        confirm = QMessageBox.question(
            self,
            "Confirmar Generación - Excel",
            f"¿Está seguro de que desea generar los archivos Excel en lotes para las {len(sol_ids)} solicitudes seleccionadas?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return
            
        try:
            from PySide6.QtWidgets import QFileDialog
            default_dir = self._get_default_directory()
            dest_dir = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta para Guardar Excel Lotes", default_dir)
            if not dest_dir:
                return
                
            from sar.src.services.fase_b_service import FaseBService
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
                        f"Total de derechos: {result['total_referencias']}\n"
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
        if not sol_ids: return
        
        confirm = QMessageBox.question(
            self,
            "Confirmar Generación - PDF",
            f"¿Está seguro de que desea generar los PDFs unificados en lotes para las {len(sol_ids)} solicitudes seleccionadas?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return
            
        try:
            from PySide6.QtWidgets import QFileDialog
            default_dir = self._get_default_directory()
            dest_dir = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta para Guardar PDF Unificado", default_dir)
            if not dest_dir:
                return
                
            from sar.src.services.fase_b_service import FaseBService
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
                        f"Total de derechos: {result['total_referencias']}\n"
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

    def _on_asignar(self, target_sol_id: int = None):
        if not self._check_permission("SOLICITUDES", "ASIGNAR"):
            QMessageBox.warning(
                self,
                "Acceso Denegado",
                "No tiene permisos para asignar usuarios a solicitudes (SOLICITUDES:ASIGNAR)."
            )
            return
        sol_id = target_sol_id if target_sol_id is not None else self._get_selected_solicitud_id()
        if sol_id == -1: return
        
        try:
            data = self.solicitudes_ui_service.get_all_usuarios()
            if not data:
                QMessageBox.warning(self, "Sin Usuarios", "No hay usuarios disponibles.")
                return
            items = [f"{u['usuario_id']} - {u['nombre']} ({u['username']})" for u in data]
                    
            from PySide6.QtWidgets import QInputDialog
            item, ok = QInputDialog.getItem(self, "Asignar Solicitud", "Selecciona el usuario:", items, 0, False)
                 
            if ok and item:
                u_id = int(item.split(" - ")[0])
                u_nombre = item.split(" - ")[1]
                
                # Diálogo de confirmación para la asignación
                confirm = QMessageBox.question(
                    self,
                    "Confirmar Asignación",
                    f"¿Estás seguro de que deseas asignar la solicitud ID: {sol_id} al usuario '{u_nombre}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if confirm == QMessageBox.Yes:
                    self.solicitudes_ui_service.asignar_solicitud(sol_id, u_id)
                    QMessageBox.information(self, "Éxito", "Solicitud asignada correctamente.")
                    self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al asignar: {str(e)}")
            
    def _on_editar(self):
        if not self._check_permission("SOLICITUDES", "EDITAR"):
            QMessageBox.warning(
                self,
                "Acceso Denegado",
                "No tiene permisos para editar la cantidad de solicitudes (SOLICITUDES:EDITAR)."
            )
            return
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona una solicitud de la tabla primero.")
            return
        row = selected[0].row()
        sol_id = int(self.table.item(row, 0).text())
        cant_actual = int(self.table.item(row, 6).text())
        estado_item = self.table.item(row, 9)
        estado_actual = estado_item.text().strip() if estado_item else ""

        # Pre-validación UX: Únicamente permitir editar solicitudes en estado PENDIENTE
        if estado_actual.upper() != "PENDIENTE":
            QMessageBox.information(
                self,
                "Edición No Permitida",
                f"Únicamente se pueden editar solicitudes en estado 'Pendiente'.\n\n"
                f"La solicitud seleccionada (ID: {sol_id}) se encuentra en estado '{estado_actual}'."
            )
            return

        dialog = EditQuantityDialog(cant_actual, self)
        if dialog.exec() == QDialog.Accepted:
            qty = dialog.get_new_quantity()
            if qty <= 0:
                QMessageBox.warning(self, "Cantidad Inválida", "La nueva cantidad debe ser un número entero mayor a 0.")
                return
                
            # Diálogo de confirmación mostrando la cantidad actual y la nueva
            confirm = QMessageBox.question(
                self,
                "Confirmar Actualización de Cantidad",
                f"¿Estás seguro de que deseas actualizar la cantidad de la solicitud {sol_id}?\n\n"
                f"• Cantidad actual: {cant_actual}\n"
                f"• Nueva cantidad: {qty}",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                try:
                    self.solicitudes_ui_service.editar_cantidad_solicitud(sol_id, qty)
                    QMessageBox.information(self, "Éxito", "Cantidad actualizada correctamente.")
                    self.refresh_data()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Error al editar: {str(e)}")
                
    def _on_cancelar(self):
        if not self._check_permission("SOLICITUDES", "ELIMINAR"):
            QMessageBox.warning(
                self,
                "Acceso Denegado",
                "No tiene permisos para cancelar solicitudes (SOLICITUDES:ELIMINAR)."
            )
            return
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona una solicitud de la tabla primero.")
            return
        row = selected[0].row()
        sol_id = int(self.table.item(row, 0).text())
        estado_item = self.table.item(row, 9)
        estado_actual = estado_item.text().strip() if estado_item else ""

        # Pre-validación UX: Únicamente permitir cancelar solicitudes en estado PENDIENTE
        if estado_actual.upper() != "PENDIENTE":
            QMessageBox.information(
                self,
                "Cancelación No Permitida",
                f"Únicamente se pueden cancelar solicitudes en estado 'Pendiente'.\n\n"
                f"La solicitud seleccionada (ID: {sol_id}) se encuentra en estado '{estado_actual}' y no puede ser cancelada."
            )
            return
        
        reply = QMessageBox.question(
            self,
            "Confirmar Cancelación",
            f"¿Estás seguro de que deseas cancelar la solicitud ID: {sol_id}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.solicitudes_ui_service.cancelar_solicitud(sol_id)
                QMessageBox.information(self, "Éxito", "Solicitud cancelada correctamente.")
                self.refresh_data()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al cancelar: {str(e)}")
        
    def refresh_data(self):
        """Fetches the latest Solicitudes."""
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

        orden_ids = getattr(self, 'selected_orden_ids', [])
        
        self.active_worker = RequestsLoadWorker(self.solicitudes_ui_service, orden_ids)
        self.active_worker.result_ready.connect(self._on_data_loaded)
        self.active_worker.error_occurred.connect(self._on_load_error)
        self.active_worker.start()

    def _on_data_loaded(self, solicitudes):
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
                str(s.get("cantidad_facturada", 0)),
                s["estado"],
                s["usuario_asignado"]
            ])
            
        self.table.populate_rows(data_rows)
        self._apply_filters()

    def _on_load_error(self, err_msg):
        QMessageBox.critical(self, "Error", f"No se pudo cargar la bandeja de trabajo:\n{err_msg}")

    def _filter_table_by_text(self, text: str):
        self._current_search_text = text.lower()
        self._apply_filters()
        
    def _filter_table_by_state(self, state: str):
        self._current_estado_filter = state
        self._apply_filters()

    def _apply_filters(self):
        search_text = getattr(self, '_current_search_text', "")
        estado_filter = getattr(self, '_current_estado_filter', "Todas")
        
        for row in range(self.table.rowCount()):
            estado = self.table.item(row, 9).text() if self.table.item(row, 9) else ""
            
            # 1. State Filter Logic
            state_match = True
            if estado_filter != "Todas":
                if estado_filter == "ASIGNADA":
                    state_match = estado in ["ASIGNADA", "ASIGNADO"]
                elif estado_filter == "CANCELADA":
                    state_match = estado in ["CANCELADA", "CANCELADO"]
                elif estado_filter == "COMPLETADA":
                    state_match = estado in ["COMPLETADA", "COMPLETADO"]
                else:
                    state_match = (estado == estado_filter)
            
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

    def _load_available_orders(self, preserve_selection=False):
        try:
            raw_ordenes = self.solicitudes_ui_service.get_ordenes(include_rejected=False)
            self.todas_las_ordenes = [
                ord for ord in raw_ordenes
                if str(ord.get("estado", "") or ord.get("estado_codigo", "")).upper() not in ("RECHAZADA", "RECHAZADO", "CANCELADA", "CANCELADO")
            ]
            if self.todas_las_ordenes:
                valid_ids = {ord["orden_id"] for ord in self.todas_las_ordenes}
                if preserve_selection and self.is_custom_filter:
                    self.selected_orden_ids = [oid for oid in self.selected_orden_ids if oid in valid_ids]
                elif not self.is_custom_filter:
                    self.selected_orden_ids = [self.todas_las_ordenes[0]["orden_id"]]
            else:
                self.selected_orden_ids = []
        except Exception as e:
            print("Error loading available orders for requests:", e)
            self.todas_las_ordenes = []
            self.selected_orden_ids = []
        self._update_order_filter_title()

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
                
            self._update_order_filter_title()
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
                    self._update_order_filter_title()
                    self.refresh_data()
                return handler
                
            action.triggered.connect(make_toggle_handler(oid))
            menu.addAction(action)
            
        # Display the menu directly under the filter button
        menu.exec(self.btn_filter_orden.mapToGlobal(self.btn_filter_orden.rect().bottomLeft()))

    def _get_active_orders_formatted_text(self) -> str:
        """Genera el texto HTML formateado de las órdenes activas en el filtro."""
        total_orders = len(getattr(self, "todas_las_ordenes", []))
        selected_ids = getattr(self, "selected_orden_ids", [])
        num_selected = len(selected_ids)

        if total_orders == 0 or num_selected == 0:
            return '<span style="color: #EF4444; font-weight: bold;">(Ninguna orden seleccionada)</span>'
        elif num_selected == total_orders:
            return '<span style="color: #10B981; font-weight: bold;">Todas las órdenes</span>'
        else:
            from sar.src.ui.design_system.utils.formatters import format_orden_filter_label
            selected_objs = [
                ord for ord in self.todas_las_ordenes
                if ord.get("orden_id") in selected_ids
            ]
            if len(selected_objs) <= 3:
                names = []
                for o in selected_objs:
                    label = format_orden_filter_label(o.get("folio", ""), o.get("descripcion", ""), max_desc_len=25)
                    parts = label.split(" - ", 1)
                    if len(parts) == 2:
                        names.append(f"<b>{parts[0]}</b> ({parts[1]})")
                    else:
                        names.append(f"<b>{label}</b>")
                return ", ".join(names)
            else:
                names = []
                for o in selected_objs[:2]:
                    label = format_orden_filter_label(o.get("folio", ""), o.get("descripcion", ""), max_desc_len=20)
                    parts = label.split(" - ", 1)
                    if len(parts) == 2:
                        names.append(f"<b>{parts[0]}</b> ({parts[1]})")
                    else:
                        names.append(f"<b>{label}</b>")
                remaining = len(selected_objs) - 2
                names_str = ", ".join(names)
                return f'{names_str} y <span style="color: #2563EB; font-weight: bold;">+{remaining} órdenes más</span>'

    def _update_order_filter_title(self):
        """Actualiza el título de la tarjeta principal con el estado de las órdenes activas."""
        if hasattr(self, "card") and hasattr(self.card, "header"):
            order_text = self._get_active_orders_formatted_text()
            self.card.header.setText(
                f"Solicitudes Pendientes y en Proceso &nbsp;|&nbsp; <span style='font-size: 13px; font-weight: normal;'>Órdenes activas en filtro: <b>{order_text}</b></span>"
            )
