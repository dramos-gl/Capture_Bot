"""Users Administration Sub-view."""

from PySide6.QtWidgets import QWidget, QHBoxLayout
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
from sar.src.ui.design_system.components.atoms.gl_checkbox import CustomCheckBox
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.molecules.gl_labeled_input import LabeledInput
from sar.src.ui.design_system.components.organisms.gl_crud_table import CrudTablePanel
from sar.src.ui.design_system.components.organisms.gl_dialog import CustomDialog
from sar.src.storage.repositories import UsuarioRepository
from sar.src.services.admin_service import AdminService

class UsersView(QWidget):
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
        
        self.all_roles = []
        
        self._build_ui()
        self.refresh_data()
        
    def _build_ui(self):
        # Full width Grid
        self.tbl_usuarios = CrudTablePanel("Usuarios del Sistema")
        self.tbl_usuarios.setup_table(["ID", "Usuario", "Nombre", "Estado"], ["usuario_id", "username", "nombre", "activo"])
        self.tbl_usuarios.add_requested.connect(self._on_new_usuario)
        self.tbl_usuarios.edit_requested.connect(self._on_edit_usuario)
        self.layout.addWidget(self.tbl_usuarios)
        
        # Enforce RBAC
        self.tbl_usuarios.btn_add.setVisible(self.can_edit)
        
        # Setup form dialog properties (not visible by default)
        self.current_usuario_id = None
        
    def _create_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        
        self.inp_u_username = LabeledInput("Username")
        self.inp_u_username.set_validator(r"^[a-zA-Z0-9_]{3,20}$", "Debe tener 3-20 caracteres (letras, números, _).")
        self.inp_u_nombre = LabeledInput("Nombre Completo")
        self.inp_u_correo = LabeledInput("Correo (Opcional)")
        self.inp_u_correo.set_validator(r"^(?:[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)?$", "Formato de correo inválido.")
        self.inp_u_pass = LabeledInput("Contraseña", "Dejar en blanco si no se cambia", is_password=True)
        self.chk_u_activo = CustomCheckBox("Usuario Activo")
        self.chk_u_activo.setChecked(True)
        
        dialog.add_widget(self.inp_u_username)
        dialog.add_widget(self.inp_u_pass)
        dialog.add_widget(self.inp_u_nombre)
        dialog.add_widget(self.inp_u_correo)
        dialog.add_widget(self.chk_u_activo)
        
        from sar.src.ui.design_system.components.molecules.gl_labeled_combo import LabeledComboBox
        
        self.labeled_roles = LabeledComboBox("Rol Asignado")
        self.cmb_roles = self.labeled_roles.combo
        self.cmb_roles.addItem("-- Selecciona un Rol --", None)
        for role in self.all_roles:
            self.cmb_roles.addItem(role["nombre"], role["id"])
            
        dialog.add_widget(self.labeled_roles)
            
        if not self.can_edit:
            self.cmb_roles.setEnabled(False)
            dialog.btn_save.setVisible(False)
            self.inp_u_username.input.setReadOnly(True)
            self.inp_u_nombre.input.setReadOnly(True)
            self.inp_u_correo.input.setReadOnly(True)
            self.inp_u_pass.input.setReadOnly(True)
            self.chk_u_activo.setEnabled(False)
            
        # Bind validation states to the save button
        self._valid_states = {"username": True, "correo": True}
        
        def _on_validity_changed(field: str, is_valid: bool):
            self._valid_states[field] = is_valid
            dialog.btn_save.setEnabled(all(self._valid_states.values()))
            
        self.inp_u_username.validity_changed.connect(lambda v: _on_validity_changed("username", v))
        self.inp_u_correo.validity_changed.connect(lambda v: _on_validity_changed("correo", v))
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_usuario(dialog))
        
        return dialog

    def _on_new_usuario(self):
        self.current_usuario_id = None
        dialog = self._create_dialog("Nuevo Usuario")
        self.inp_u_username.set_focus()
        dialog.exec()
        
    def _on_edit_usuario(self, data: dict):
        self.current_usuario_id = data.get("usuario_id")
        dialog = self._create_dialog(f"Editar Usuario: {data.get('username')}")
        
        self.inp_u_username.set_text(data.get("username", ""))
        self.inp_u_nombre.set_text(data.get("nombre", ""))
        self.inp_u_correo.set_text(data.get("correo", "") or "")
        self.chk_u_activo.setChecked(bool(data.get("activo", False)))
        
        try:
            if self.api_client.connect_via_api:
                user_roles = self.api_client.request("GET", f"/api/admin/roles-for-user/{self.current_usuario_id}")
                if user_roles:
                    first_role_id = user_roles[0]
                    index = self.cmb_roles.findData(first_role_id)
                    if index >= 0:
                        self.cmb_roles.setCurrentIndex(index)
            else:
                with self.db_connector.get_session() as session:
                    repo = UsuarioRepository(session)
                    user_roles = repo.get_roles_for_user(self.current_usuario_id)
                    if user_roles:
                        first_role_id = user_roles[0]
                        index = self.cmb_roles.findData(first_role_id)
                        if index >= 0:
                            self.cmb_roles.setCurrentIndex(index)
        except Exception as e:
            print("Error loading roles:", e)
        
        self.inp_u_username.set_focus()
        dialog.exec()

    def _save_usuario(self, dialog):
        data = {
            "usuario_id": self.current_usuario_id,
            "username": self.inp_u_username.text().strip(),
            "nombre": self.inp_u_nombre.text().strip(),
            "correo": self.inp_u_correo.text().strip(),
            "password_raw": self.inp_u_pass.text().strip(),
            "activo": self.chk_u_activo.isChecked(),
            "rol_ids": [self.cmb_roles.currentData()] if self.cmb_roles.currentData() else []
        }
        
        if not data["username"] or not data["nombre"]:
            QMessageBox.warning(self, "Validación", "Username y Nombre son obligatorios.")
            return
            
        try:
            if self.api_client.connect_via_api:
                # Check Uniqueness
                existing_users = self.api_client.request("GET", "/api/admin/data/usuarios")
                for u in existing_users:
                    if u["username"] == data["username"] and u["usuario_id"] != self.current_usuario_id:
                        self.inp_u_username.show_error("Este nombre de usuario ya está en uso.")
                        return
                self.inp_u_username.clear_error()
                
                payload = {
                    "usuario_id": self.current_user_id,
                    "sesion_id": self.current_sesion_id,
                    "data": data
                }
                self.api_client.request("POST", "/api/admin/save/usuarios", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    repo = UsuarioRepository(session)
                    existing = repo.get_by_username(data["username"])
                    if existing and existing.usuario_id != self.current_usuario_id:
                        self.inp_u_username.show_error("Este nombre de usuario ya está en uso.")
                        return
                    else:
                        self.inp_u_username.clear_error()
                        
                    service = AdminService(session)
                    service.save_usuario(self.current_user_id, self.current_sesion_id, data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Usuario guardado correctamente.")
            dialog.accept()
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def refresh_data(self):
        try:
            if self.api_client.connect_via_api:
                roles = self.api_client.request("GET", "/api/admin/data/roles")
                self.all_roles = [{"id": r["rol_id"], "nombre": r["nombre"]} for r in roles]
                
                users = self.api_client.request("GET", "/api/admin/data/usuarios")
                self.tbl_usuarios.populate(users)
            else:
                with self.db_connector.get_session() as session:
                    repo = UsuarioRepository(session)
                    roles = repo.get_all_roles()
                    self.all_roles = [{"id": r.rol_id, "nombre": r.nombre} for r in roles]
                    
                    users = repo.get_all_usuarios()
                    data = [{"usuario_id": u.usuario_id, "username": u.username, "nombre": u.nombre, "correo": u.correo, "activo": u.activo} for u in users]
                    self.tbl_usuarios.populate(data)
        except Exception as e:
            print("Error refreshing users:", e)
