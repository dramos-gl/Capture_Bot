"""Modules Administration Sub-view (AppModulo and Modulo)."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QMessageBox, QCheckBox
from sar.src.ui.design_system.components.molecules.gl_labeled_input import LabeledInput
from sar.src.ui.design_system.components.organisms.gl_crud_table import CrudTablePanel
from sar.src.ui.design_system.components.organisms.gl_dialog import CustomDialog
from sar.src.storage.repositories import UsuarioRepository
from sar.src.services.admin_service import AdminService

class ModulesView(QWidget):
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
        # Table AppModulo
        self.tbl_app = CrudTablePanel("App Módulos (Macro)")
        self.tbl_app.setup_table(["ID", "Código", "Nombre", "Estado"], ["app_modulo_id", "codigo", "nombre", "activo"])
        self.tbl_app.add_requested.connect(self._on_new_app)
        self.tbl_app.edit_requested.connect(self._on_edit_app)
        self.layout.addWidget(self.tbl_app)
        
        # Table Modulo Interno
        self.tbl_mod = CrudTablePanel("Módulos Internos")
        self.tbl_mod.setup_table(["ID", "Código", "Nombre", "Descripción", "Estado"], ["modulo_id", "codigo", "nombre", "descripcion", "activo"])
        self.tbl_mod.add_requested.connect(self._on_new_mod)
        self.tbl_mod.edit_requested.connect(self._on_edit_mod)
        self.layout.addWidget(self.tbl_mod)
        
        self.current_app_id = None
        self.current_mod_id = None
        self.tbl_app.btn_add.setVisible(self.can_edit)
        self.tbl_mod.btn_add.setVisible(self.can_edit)
        
    def _create_app_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        self.inp_a_cod = LabeledInput("Código")
        self.inp_a_nom = LabeledInput("Nombre")
        self.chk_a_act = QCheckBox("Activo")
        self.chk_a_act.setChecked(True)
        dialog.add_widget(self.inp_a_cod)
        dialog.add_widget(self.inp_a_nom)
        dialog.add_widget(self.chk_a_act)
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_a_cod.input.setReadOnly(True)
            self.inp_a_nom.input.setReadOnly(True)
            self.chk_a_act.setEnabled(False)
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_app(dialog))
        return dialog

    def _create_mod_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        self.inp_m_cod = LabeledInput("Código")
        self.inp_m_nom = LabeledInput("Nombre")
        self.inp_m_desc = LabeledInput("Descripción")
        self.chk_m_act = QCheckBox("Activo")
        self.chk_m_act.setChecked(True)
        dialog.add_widget(self.inp_m_cod)
        dialog.add_widget(self.inp_m_nom)
        dialog.add_widget(self.inp_m_desc)
        dialog.add_widget(self.chk_m_act)
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_m_cod.input.setReadOnly(True)
            self.inp_m_nom.input.setReadOnly(True)
            self.inp_m_desc.input.setReadOnly(True)
            self.chk_m_act.setEnabled(False)
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_mod(dialog))
        return dialog

    def _on_new_app(self):
        self.current_app_id = None
        d = self._create_app_dialog("Nuevo App Módulo")
        self.inp_a_cod.set_focus()
        d.exec()

    def _on_edit_app(self, data: dict):
        self.current_app_id = data.get("app_modulo_id")
        d = self._create_app_dialog(f"Editar App Módulo: {data.get('nombre')}")
        self.inp_a_cod.set_text(data.get("codigo", ""))
        self.inp_a_nom.set_text(data.get("nombre", ""))
        self.chk_a_act.setChecked(bool(data.get("activo", False)))
        self.inp_a_cod.set_focus()
        d.exec()

    def _save_app(self, dialog):
        data = {
            "app_modulo_id": self.current_app_id,
            "codigo": self.inp_a_cod.text().strip(),
            "nombre": self.inp_a_nom.text().strip(),
            "activo": self.chk_a_act.isChecked()
        }
        try:
            if self.api_client.connect_via_api:
                payload = {
                    "usuario_id": self.current_user_id,
                    "sesion_id": self.current_sesion_id,
                    "data": data
                }
                self.api_client.request("POST", "/api/admin/save/app_modulos", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    service = AdminService(session)
                    service.save_app_modulo(self.current_user_id, self.current_sesion_id, data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Guardado correctamente.")
            dialog.accept()
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_new_mod(self):
        self.current_mod_id = None
        d = self._create_mod_dialog("Nuevo Módulo Interno")
        self.inp_m_cod.set_focus()
        d.exec()

    def _on_edit_mod(self, data: dict):
        self.current_mod_id = data.get("modulo_id")
        d = self._create_mod_dialog(f"Editar Módulo: {data.get('nombre')}")
        self.inp_m_cod.set_text(data.get("codigo", ""))
        self.inp_m_nom.set_text(data.get("nombre", ""))
        self.inp_m_desc.set_text(data.get("descripcion", "") or "")
        self.chk_m_act.setChecked(bool(data.get("activo", False)))
        self.inp_m_cod.set_focus()
        d.exec()

    def _save_mod(self, dialog):
        data = {
            "modulo_id": self.current_mod_id,
            "codigo": self.inp_m_cod.text().strip(),
            "nombre": self.inp_m_nom.text().strip(),
            "descripcion": self.inp_m_desc.text().strip(),
            "activo": self.chk_m_act.isChecked()
        }
        try:
            if self.api_client.connect_via_api:
                payload = {
                    "usuario_id": self.current_user_id,
                    "sesion_id": self.current_sesion_id,
                    "data": data
                }
                self.api_client.request("POST", "/api/admin/save/modulos", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    service = AdminService(session)
                    service.save_modulo(self.current_user_id, self.current_sesion_id, data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Guardado correctamente.")
            dialog.accept()
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def refresh_data(self):
        try:
            if self.api_client.connect_via_api:
                app_mods = self.api_client.request("GET", "/api/admin/data/app_modulos")
                data_app = [{"app_modulo_id": i["id"], "codigo": i.get("codigo", ""), "nombre": i["nombre"], "activo": i.get("activo", True)} for i in app_mods]
                self.tbl_app.populate(data_app)
                
                mods = self.api_client.request("GET", "/api/admin/data/modulos")
                data_mod = [{"modulo_id": i["id"], "codigo": i.get("codigo", ""), "nombre": i["nombre"], "descripcion": i.get("descripcion", ""), "activo": i.get("activo", True)} for i in mods]
                self.tbl_mod.populate(data_mod)
            else:
                with self.db_connector.get_session() as session:
                    repo = UsuarioRepository(session)
                    app_mods = repo.get_all_app_modulos()
                    data_app = [{"app_modulo_id": i.app_modulo_id, "codigo": i.codigo, "nombre": i.nombre, "activo": i.activo} for i in app_mods]
                    self.tbl_app.populate(data_app)
                    
                    mods = repo.get_all_modulos()
                    data_mod = [{"modulo_id": i.modulo_id, "codigo": i.codigo, "nombre": i.nombre, "descripcion": i.descripcion, "activo": i.activo} for i in mods]
                    self.tbl_mod.populate(data_mod)
        except Exception as e:
            print("Error refreshing modules:", e)
