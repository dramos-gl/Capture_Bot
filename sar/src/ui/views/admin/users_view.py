import re
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QFrame, QLabel
from PySide6.QtCore import Qt
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.atoms.gl_input import CustomInput
from sar.src.ui.design_system.components.atoms.gl_checkbox import CustomCheckBox
from sar.src.ui.design_system.components.molecules.gl_combo_box import CustomComboBox
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
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
        
    def _build_ui(self):
        self.tbl_usuarios = CrudTablePanel("Usuarios del Sistema")
        self.tbl_usuarios.setup_table(["ID", "Usuario", "Nombre", "Estado"], ["usuario_id", "username", "nombre", "activo"])
        self.tbl_usuarios.add_requested.connect(self._on_new_usuario)
        self.tbl_usuarios.edit_requested.connect(self._on_edit_usuario)
        self.layout.addWidget(self.tbl_usuarios)
        
        self.tbl_usuarios.btn_add.setVisible(self.can_edit)
        self.current_usuario_id = None
        
    def _create_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        dialog.setMinimumWidth(640)
        
        # -------------------------------------------------------------
        # 1. TARJETA: DATOS DE USUARIO Y CREDENCIALES
        # -------------------------------------------------------------
        card_user = QFrame(dialog)
        card_user.setObjectName("card_user")
        card_user.setStyleSheet(f"""
            QFrame#card_user {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay_user = QVBoxLayout(card_user)
        lay_user.setContentsMargins(0, 0, 0, 0)
        lay_user.setSpacing(8)
        
        lbl_user = CustomLabel("👤 DATOS DE USUARIO Y CREDENCIALES", variant="subheader")
        lbl_user.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay_user.addWidget(lbl_user)
        
        form_user = QFormLayout()
        form_user.setSpacing(8)
        form_user.setContentsMargins(0, 0, 0, 0)
        
        self.inp_u_username = CustomInput("Nombre de usuario único (ej. jgomez)", parent=card_user)
        self.inp_u_username.setMaxLength(20)
        
        # Wrapper object for validation compatibility
        self.inp_u_username.text = self.inp_u_username.text
        self.inp_u_username.set_text = self.inp_u_username.setText
        self.inp_u_username.set_focus = self.inp_u_username.setFocus
        self.inp_u_username.show_error = lambda msg: self.lbl_user_err.setText(msg) or self.lbl_user_err.setVisible(True)
        self.inp_u_username.clear_error = lambda: self.lbl_user_err.setVisible(False)
        
        form_user.addRow("Username *:", self.inp_u_username)
        
        self.lbl_user_err = QLabel("", card_user)
        self.lbl_user_err.setStyleSheet(f"color: {Colors.ERROR}; font-size: 11px; font-weight: bold;")
        self.lbl_user_err.setVisible(False)
        form_user.addRow("", self.lbl_user_err)
        
        self.inp_u_pass = CustomInput("Dejar en blanco si no se cambia", is_password=True, parent=card_user)
        self.inp_u_pass.text = self.inp_u_pass.text
        self.inp_u_pass.set_text = self.inp_u_pass.setText
        form_user.addRow("Contraseña:", self.inp_u_pass)
        
        self.inp_u_nombre = CustomInput("Nombre y apellidos del usuario", parent=card_user)
        self.inp_u_nombre.text = self.inp_u_nombre.text
        self.inp_u_nombre.set_text = self.inp_u_nombre.setText
        form_user.addRow("Nombre Completo *:", self.inp_u_nombre)
        
        self.inp_u_correo = CustomInput("usuario@dominio.com (Opcional)", parent=card_user)
        self.inp_u_correo.text = self.inp_u_correo.text
        self.inp_u_correo.set_text = self.inp_u_correo.setText
        form_user.addRow("Correo Electrónico:", self.inp_u_correo)
        
        lay_user.addLayout(form_user)
        dialog.add_widget(card_user)
        
        # -------------------------------------------------------------
        # 2. TARJETA: ROL Y PERMISOS DE ACCESO
        # -------------------------------------------------------------
        card_roles = QFrame(dialog)
        card_roles.setObjectName("card_roles")
        card_roles.setStyleSheet(f"""
            QFrame#card_roles {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay_roles = QVBoxLayout(card_roles)
        lay_roles.setContentsMargins(0, 0, 0, 0)
        lay_roles.setSpacing(8)
        
        lbl_roles = CustomLabel("🔐 ROL Y PERMISOS DE ACCESO", variant="subheader")
        lbl_roles.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay_roles.addWidget(lbl_roles)
        
        form_roles = QFormLayout()
        form_roles.setSpacing(8)
        form_roles.setContentsMargins(0, 0, 0, 0)
        
        self.cmb_roles = CustomComboBox(card_roles)
        self.cmb_roles.addItem("-- Selecciona un Rol --", None)
        for role in self.all_roles:
            self.cmb_roles.addItem(role["nombre"], role["id"])
            
        form_roles.addRow("Rol Asignado *:", self.cmb_roles)
        lay_roles.addLayout(form_roles)
        dialog.add_widget(card_roles)
        
        # -------------------------------------------------------------
        # 3. ESTADO OPERATIVO (CustomCheckBox)
        # -------------------------------------------------------------
        self.chk_u_activo = CustomCheckBox("Usuario activo para iniciar sesión en el sistema", dialog)
        self.chk_u_activo.setChecked(True)
        self.chk_u_activo.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {Colors.TEXT_LIGHT_PRIMARY}; margin: 4px 2px;")
        dialog.add_widget(self.chk_u_activo)
        
        # Validación en tiempo real
        def _validate_user():
            u_val = self.inp_u_username.text().strip()
            n_val = self.inp_u_nombre.text().strip()
            c_val = self.inp_u_correo.text().strip()
            
            is_valid = True
            if u_val and not re.match(r"^[a-zA-Z0-9_]{3,20}$", u_val):
                self.inp_u_username.show_error("Username debe tener 3-20 caracteres (letras, números, _).")
                is_valid = False
            elif c_val and not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", c_val):
                self.inp_u_username.show_error("Formato de correo electrónico inválido.")
                is_valid = False
            else:
                self.inp_u_username.clear_error()
                
            can_save = bool(u_val and n_val and is_valid)
            dialog.btn_save.setEnabled(can_save)
            
        self.inp_u_username.textChanged.connect(_validate_user)
        self.inp_u_nombre.textChanged.connect(_validate_user)
        self.inp_u_correo.textChanged.connect(_validate_user)
        _validate_user()
        
        if not self.can_edit:
            self.cmb_roles.setEnabled(False)
            dialog.btn_save.setVisible(False)
            self.inp_u_username.setReadOnly(True)
            self.inp_u_nombre.setReadOnly(True)
            self.inp_u_correo.setReadOnly(True)
            self.inp_u_pass.setReadOnly(True)
            self.chk_u_activo.setEnabled(False)
            
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

