"""Modules Administration Sub-view (AppModulo and Modulo)."""

import re
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QFrame, QLabel
from PySide6.QtCore import Qt
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.atoms.gl_input import CustomInput
from sar.src.ui.design_system.components.atoms.gl_checkbox import CustomCheckBox
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
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
        self.tbl_app = CrudTablePanel("App Módulos (Macro)")
        self.tbl_app.setup_table(["ID", "Código", "Nombre", "Estado"], ["app_modulo_id", "codigo", "nombre", "activo"])
        self.tbl_app.add_requested.connect(self._on_new_app)
        self.tbl_app.edit_requested.connect(self._on_edit_app)
        self.layout.addWidget(self.tbl_app)
        
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
        dialog.setMinimumWidth(540)
        
        card_app = QFrame(dialog)
        card_app.setObjectName("card_app")
        card_app.setStyleSheet(f"""
            QFrame#card_app {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay_app = QVBoxLayout(card_app)
        lay_app.setContentsMargins(0, 0, 0, 0)
        lay_app.setSpacing(8)
        
        lbl_app = CustomLabel("📱 IDENTIFICACIÓN DE APP MÓDULO (NIVEL 1)", variant="subheader")
        lbl_app.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay_app.addWidget(lbl_app)
        
        form_app = QFormLayout()
        form_app.setSpacing(8)
        form_app.setContentsMargins(0, 0, 0, 0)
        
        self.inp_a_cod = CustomInput("Ej. R2F_CONTROL", parent=card_app)
        self.inp_a_cod.setMaxLength(30)
        self.inp_a_cod.textEdited.connect(lambda t: self.inp_a_cod.setText(t.upper()))
        self.inp_a_cod.text = self.inp_a_cod.text
        self.inp_a_cod.set_text = self.inp_a_cod.setText
        self.inp_a_cod.set_focus = self.inp_a_cod.setFocus
        
        form_app.addRow("Código *:", self.inp_a_cod)
        
        self.inp_a_nom = CustomInput("Nombre descriptivo de la app", parent=card_app)
        self.inp_a_nom.setMaxLength(100)
        self.inp_a_nom.text = self.inp_a_nom.text
        self.inp_a_nom.set_text = self.inp_a_nom.setText
        
        form_app.addRow("Nombre *:", self.inp_a_nom)
        lay_app.addLayout(form_app)
        dialog.add_widget(card_app)
        
        self.chk_a_act = CustomCheckBox("App módulo activo en menú de navegación", dialog)
        self.chk_a_act.setChecked(True)
        self.chk_a_act.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {Colors.TEXT_LIGHT_PRIMARY}; margin: 4px 2px;")
        dialog.add_widget(self.chk_a_act)
        
        def _validate_app():
            c_val = self.inp_a_cod.text().strip()
            n_val = self.inp_a_nom.text().strip()
            dialog.btn_save.setEnabled(bool(c_val and n_val))
            
        self.inp_a_cod.textChanged.connect(_validate_app)
        self.inp_a_nom.textChanged.connect(_validate_app)
        _validate_app()
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_a_cod.setReadOnly(True)
            self.inp_a_nom.setReadOnly(True)
            self.chk_a_act.setEnabled(False)
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_app(dialog))
        return dialog

    def _create_mod_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        dialog.setMinimumWidth(580)
        
        card_mod = QFrame(dialog)
        card_mod.setObjectName("card_mod")
        card_mod.setStyleSheet(f"""
            QFrame#card_mod {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay_mod = QVBoxLayout(card_mod)
        lay_mod.setContentsMargins(0, 0, 0, 0)
        lay_mod.setSpacing(8)
        
        lbl_mod = CustomLabel("🧩 CONFIGURACIÓN DE MÓDULO INTERNO (NIVEL 2)", variant="subheader")
        lbl_mod.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay_mod.addWidget(lbl_mod)
        
        form_mod = QFormLayout()
        form_mod.setSpacing(8)
        form_mod.setContentsMargins(0, 0, 0, 0)
        
        self.inp_m_cod = CustomInput("Ej. REFERENCIAS", parent=card_mod)
        self.inp_m_cod.setMaxLength(30)
        self.inp_m_cod.textEdited.connect(lambda t: self.inp_m_cod.setText(t.upper()))
        self.inp_m_cod.text = self.inp_m_cod.text
        self.inp_m_cod.set_text = self.inp_m_cod.setText
        self.inp_m_cod.set_focus = self.inp_m_cod.setFocus
        form_mod.addRow("Código *:", self.inp_m_cod)
        
        self.inp_m_nom = CustomInput("Nombre del módulo de funcionalidad", parent=card_mod)
        self.inp_m_nom.setMaxLength(100)
        self.inp_m_nom.text = self.inp_m_nom.text
        self.inp_m_nom.set_text = self.inp_m_nom.setText
        form_mod.addRow("Nombre *:", self.inp_m_nom)
        
        self.inp_m_desc = CustomInput("Descripción técnica del alcance del módulo", parent=card_mod)
        self.inp_m_desc.setMaxLength(255)
        self.inp_m_desc.text = self.inp_m_desc.text
        self.inp_m_desc.set_text = self.inp_m_desc.setText
        form_mod.addRow("Descripción:", self.inp_m_desc)
        
        lay_mod.addLayout(form_mod)
        dialog.add_widget(card_mod)
        
        self.chk_m_act = CustomCheckBox("Módulo activo para evaluación RBAC", dialog)
        self.chk_m_act.setChecked(True)
        self.chk_m_act.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {Colors.TEXT_LIGHT_PRIMARY}; margin: 4px 2px;")
        dialog.add_widget(self.chk_m_act)
        
        def _validate_mod():
            c_val = self.inp_m_cod.text().strip()
            n_val = self.inp_m_nom.text().strip()
            dialog.btn_save.setEnabled(bool(c_val and n_val))
            
        self.inp_m_cod.textChanged.connect(_validate_mod)
        self.inp_m_nom.textChanged.connect(_validate_mod)
        _validate_mod()
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_m_cod.setReadOnly(True)
            self.inp_m_nom.setReadOnly(True)
            self.inp_m_desc.setReadOnly(True)
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
            "codigo": self.inp_a_cod.text().strip().upper(),
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
            "codigo": self.inp_m_cod.text().strip().upper(),
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
                apps = self.api_client.request("GET", "/api/admin/data/app_modulos")
                self.tbl_app.populate(apps)
                
                mods = self.api_client.request("GET", "/api/admin/data/modulos")
                self.tbl_mod.populate(mods)
            else:
                with self.db_connector.get_session() as session:
                    repo = UsuarioRepository(session)
                    apps = repo.get_all_app_modulos()
                    self.tbl_app.populate([{"app_modulo_id": a.app_modulo_id, "codigo": a.codigo, "nombre": a.nombre, "activo": a.activo} for a in apps])
                    
                    mods = repo.get_all_modulos()
                    self.tbl_mod.populate([{"modulo_id": m.modulo_id, "codigo": m.codigo, "nombre": m.nombre, "descripcion": m.descripcion, "activo": m.activo} for m in mods])
        except Exception as e:
            print("Error refreshing modules:", e)
