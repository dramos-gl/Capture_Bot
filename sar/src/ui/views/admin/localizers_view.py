"""Localizers Administration Sub-view."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QCheckBox
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.molecules.gl_labeled_input import LabeledInput
from sar.src.ui.design_system.components.organisms.gl_crud_table import CrudTablePanel
from sar.src.ui.design_system.components.organisms.gl_dialog import CustomDialog
from sar.src.storage.repositories import ConfigRepository
from sar.src.services.admin_service import AdminService

class LocalizersView(QWidget):
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
        self.tbl_locs = CrudTablePanel("Localizadores UI (Bot)")
        self.tbl_locs.setup_table(["ID", "Nombre Clave", "Label", "Selector", "Estado"], ["localizador_id", "nombre_clave", "label_visible", "valor_selector", "activo"])
        self.tbl_locs.add_requested.connect(self._on_new_loc)
        self.tbl_locs.edit_requested.connect(self._on_edit_loc)
        self.layout.addWidget(self.tbl_locs)
        
        self.current_loc_id = None
        self.tbl_locs.btn_add.setVisible(self.can_edit)
        
    def _create_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        
        self.inp_l_clave = LabeledInput("Nombre Clave", "Ej. LOGIN_BTN")
        self.inp_l_label = LabeledInput("Etiqueta Visible", "Nombre en UI")
        self.inp_l_estrategia = LabeledInput("Estrategia", "css o xpath")
        self.inp_l_selector = LabeledInput("Valor del Selector")
        self.chk_l_activo = QCheckBox("Activo")
        self.chk_l_activo.setChecked(True)
        
        dialog.add_widget(self.inp_l_clave)
        dialog.add_widget(self.inp_l_label)
        dialog.add_widget(self.inp_l_estrategia)
        dialog.add_widget(self.inp_l_selector)
        dialog.add_widget(self.chk_l_activo)
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_l_clave.input.setReadOnly(True)
            self.inp_l_label.input.setReadOnly(True)
            self.inp_l_estrategia.input.setReadOnly(True)
            self.inp_l_selector.input.setReadOnly(True)
            self.chk_l_activo.setEnabled(False)
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_loc(dialog))
        
        return dialog
 
    def _on_new_loc(self):
        self.current_loc_id = None
        dialog = self._create_dialog("Nuevo Localizador")
        self.inp_l_estrategia.set_text("css")
        self.inp_l_clave.set_focus()
        dialog.exec()
        
    def _on_edit_loc(self, data: dict):
        self.current_loc_id = data.get("localizador_id")
        dialog = self._create_dialog(f"Editar Localizador: {data.get('nombre_clave')}")
        
        self.inp_l_clave.set_text(data.get("nombre_clave", ""))
        self.inp_l_label.set_text(data.get("label_visible", ""))
        self.inp_l_estrategia.set_text(data.get("estrategia_selector", "css"))
        self.inp_l_selector.set_text(data.get("valor_selector", ""))
        self.chk_l_activo.setChecked(bool(data.get("activo", False)))
        
        self.inp_l_clave.set_focus()
        dialog.exec()
 
    def _save_loc(self, dialog: CustomDialog):
        data = {
            "localizador_id": self.current_loc_id,
            "nombre_clave": self.inp_l_clave.text().strip(),
            "label_visible": self.inp_l_label.text().strip(),
            "estrategia_selector": self.inp_l_estrategia.text().strip(),
            "valor_selector": self.inp_l_selector.text().strip(),
            "activo": self.chk_l_activo.isChecked()
        }
        
        try:
            if self.api_client.connect_via_api:
                payload = {
                    "usuario_id": self.current_user_id,
                    "sesion_id": self.current_sesion_id,
                    "data": data
                }
                self.api_client.request("POST", "/api/admin/save/localizadores", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    service = AdminService(session)
                    service.save_localizador(self.current_user_id, self.current_sesion_id, data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Localizador guardado correctamente.")
            dialog.accept()
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def refresh_data(self):
        try:
            if self.api_client.connect_via_api:
                data = self.api_client.request("GET", "/api/admin/data/localizadores")
                self.tbl_locs.populate(data)
            else:
                with self.db_connector.get_session() as session:
                    repo = ConfigRepository(session)
                    items = repo.get_all_localizadores_list()
                    data = [{"localizador_id": i.localizador_id, "nombre_clave": i.nombre_clave, "label_visible": i.label_visible, "estrategia_selector": i.estrategia_selector, "valor_selector": i.valor_selector, "activo": i.activo} for i in items]
                    self.tbl_locs.populate(data)
        except Exception as e:
            print("Error refreshing localizadores:", e)
