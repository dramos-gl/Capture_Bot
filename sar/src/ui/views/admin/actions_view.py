"""Actions Administration Sub-view."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QMessageBox, QCheckBox
from sar.src.ui.design_system.components.molecules.gl_labeled_input import LabeledInput
from sar.src.ui.design_system.components.organisms.gl_crud_table import CrudTablePanel
from sar.src.ui.design_system.components.organisms.gl_dialog import CustomDialog
from sar.src.storage.repositories import UsuarioRepository
from sar.src.services.admin_service import AdminService

class ActionsView(QWidget):
    def __init__(self, db_connector, current_user_id, current_sesion_id, can_edit, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.current_user_id = current_user_id
        self.current_sesion_id = current_sesion_id
        self.can_edit = can_edit
        
        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self._build_ui()
        self.refresh_data()
        
    def _build_ui(self):
        self.tbl_acciones = CrudTablePanel("Acciones de Permisos")
        self.tbl_acciones.setup_table(["ID", "Código", "Nombre", "Descripción", "Estado"], ["accion_id", "codigo", "nombre", "descripcion", "activo"])
        self.tbl_acciones.add_requested.connect(self._on_new)
        self.tbl_acciones.edit_requested.connect(self._on_edit)
        self.layout.addWidget(self.tbl_acciones)
        
        self.current_accion_id = None
        self.tbl_acciones.btn_add.setVisible(self.can_edit)
        
    def _create_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        
        self.inp_codigo = LabeledInput("Código")
        self.inp_nombre = LabeledInput("Nombre")
        self.inp_desc = LabeledInput("Descripción")
        self.chk_activo = QCheckBox("Activo")
        self.chk_activo.setChecked(True)
        
        dialog.add_widget(self.inp_codigo)
        dialog.add_widget(self.inp_nombre)
        dialog.add_widget(self.inp_desc)
        dialog.add_widget(self.chk_activo)
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_codigo.input.setReadOnly(True)
            self.inp_nombre.input.setReadOnly(True)
            self.inp_desc.input.setReadOnly(True)
            self.chk_activo.setEnabled(False)
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save(dialog))
        return dialog
 
    def _on_new(self):
        self.current_accion_id = None
        dialog = self._create_dialog("Nueva Acción")
        self.inp_codigo.set_focus()
        dialog.exec()
        
    def _on_edit(self, data: dict):
        self.current_accion_id = data.get("accion_id")
        dialog = self._create_dialog(f"Editar Acción: {data.get('nombre')}")
        
        self.inp_codigo.set_text(data.get("codigo", ""))
        self.inp_nombre.set_text(data.get("nombre", ""))
        self.inp_desc.set_text(data.get("descripcion", "") or "")
        self.chk_activo.setChecked(bool(data.get("activo", False)))
        
        self.inp_codigo.set_focus()
        dialog.exec()
 
    def _save(self, dialog: CustomDialog):
        data = {
            "accion_id": self.current_accion_id,
            "codigo": self.inp_codigo.text().strip(),
            "nombre": self.inp_nombre.text().strip(),
            "descripcion": self.inp_desc.text().strip(),
            "activo": self.chk_activo.isChecked()
        }
        
        try:
            if self.api_client.connect_via_api:
                payload = {
                    "usuario_id": self.current_user_id,
                    "sesion_id": self.current_sesion_id,
                    "data": data
                }
                self.api_client.request("POST", "/api/admin/save/acciones", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    service = AdminService(session)
                    service.save_accion(self.current_user_id, self.current_sesion_id, data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Acción guardada correctamente.")
            dialog.accept()
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def refresh_data(self):
        try:
            if self.api_client.connect_via_api:
                acciones = self.api_client.request("GET", "/api/admin/data/acciones")
                # format for table expects accion_id
                data = [{"accion_id": i["id"], "codigo": i.get("codigo", ""), "nombre": i["nombre"], "descripcion": i.get("descripcion", ""), "activo": i.get("activo", True)} for i in acciones]
                self.tbl_acciones.populate(data)
            else:
                with self.db_connector.get_session() as session:
                    repo = UsuarioRepository(session)
                    items = repo.get_all_acciones()
                    data = [{"accion_id": i.accion_id, "codigo": i.codigo, "nombre": i.nombre, "descripcion": i.descripcion, "activo": i.activo} for i in items]
                    self.tbl_acciones.populate(data)
        except Exception as e:
            print("Error refreshing acciones:", e)
