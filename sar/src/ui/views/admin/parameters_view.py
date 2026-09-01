"""Parameters Administration Sub-view."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QCheckBox
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.molecules.gl_labeled_input import LabeledInput
from sar.src.ui.design_system.components.organisms.gl_crud_table import CrudTablePanel
from sar.src.ui.design_system.components.organisms.gl_dialog import CustomDialog
from sar.src.storage.repositories import ConfigRepository
from sar.src.services.admin_service import AdminService

class ParametersView(QWidget):
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
        self.tbl_parametros = CrudTablePanel("Parámetros del Sistema")
        self.tbl_parametros.setup_table(["ID", "Código", "Valor", "Estado"], ["parametro_id", "codigo", "valor", "activo"])
        self.tbl_parametros.add_requested.connect(self._on_new_param)
        self.tbl_parametros.edit_requested.connect(self._on_edit_param)
        self.layout.addWidget(self.tbl_parametros)
        
        self.current_param_id = None
        self.tbl_parametros.btn_add.setVisible(self.can_edit)
        
    def _create_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        
        self.inp_p_codigo = LabeledInput("Código del Parámetro", "Ej. TAMANO_LOTE")
        self.inp_p_valor = LabeledInput("Valor")
        self.chk_p_activo = QCheckBox("Parámetro Activo")
        self.chk_p_activo.setChecked(True)
        
        dialog.add_widget(self.inp_p_codigo)
        dialog.add_widget(self.inp_p_valor)
        dialog.add_widget(self.chk_p_activo)
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_p_codigo.input.setReadOnly(True)
            self.inp_p_valor.input.setReadOnly(True)
            self.chk_p_activo.setEnabled(False)
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_param(dialog))
        
        return dialog
 
    def _on_new_param(self):
        self.current_param_id = None
        dialog = self._create_dialog("Nuevo Parámetro")
        self.inp_p_codigo.set_focus()
        dialog.exec()
        
    def _on_edit_param(self, data: dict):
        self.current_param_id = data.get("parametro_id")
        dialog = self._create_dialog(f"Editar Parámetro: {data.get('codigo')}")
        
        self.inp_p_codigo.set_text(data.get("codigo", ""))
        self.inp_p_valor.set_text(data.get("valor", ""))
        self.chk_p_activo.setChecked(bool(data.get("activo", False)))
        
        self.inp_p_codigo.set_focus()
        dialog.exec()
 
    def _save_param(self, dialog: CustomDialog):
        data = {
            "parametro_id": self.current_param_id,
            "codigo": self.inp_p_codigo.text().strip(),
            "valor": self.inp_p_valor.text().strip(),
            "activo": self.chk_p_activo.isChecked()
        }
        
        if not data["codigo"] or not data["valor"]:
            QMessageBox.warning(self, "Validación", "Código y Valor son obligatorios.")
            return
            
        try:
            if self.api_client.connect_via_api:
                payload = {
                    "usuario_id": self.current_user_id,
                    "sesion_id": self.current_sesion_id,
                    "data": data
                }
                self.api_client.request("POST", "/api/admin/save/parametros", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    service = AdminService(session)
                    service.save_parametro(self.current_user_id, self.current_sesion_id, data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Parámetro guardado correctamente.")
            dialog.accept()
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def refresh_data(self):
        try:
            if self.api_client.connect_via_api:
                data = self.api_client.request("GET", "/api/admin/data/parametros")
                self.tbl_parametros.populate(data)
            else:
                with self.db_connector.get_session() as session:
                    repo = ConfigRepository(session)
                    items = repo.get_all_parametros()
                    data = [{"parametro_id": p.parametro_id, "codigo": p.codigo, "valor": p.valor, "activo": p.activo} for p in items]
                    self.tbl_parametros.populate(data)
        except Exception as e:
            print("Error refreshing parametros:", e)
