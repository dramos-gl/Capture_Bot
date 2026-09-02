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
        dialog.setMinimumWidth(560)
        
        card_ac = QFrame(dialog)
        card_ac.setObjectName("card_ac")
        card_ac.setStyleSheet(f"""
            QFrame#card_ac {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay_ac = QVBoxLayout(card_ac)
        lay_ac.setContentsMargins(0, 0, 0, 0)
        lay_ac.setSpacing(8)
        
        lbl_ac = CustomLabel("🔐 DEFINICIÓN DE ACCIÓN / PERMISO RBAC", variant="subheader")
        lbl_ac.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay_ac.addWidget(lbl_ac)
        
        form_ac = QFormLayout()
        form_ac.setSpacing(8)
        form_ac.setContentsMargins(0, 0, 0, 0)
        
        self.inp_codigo = CustomInput("Ej. EDITAR_RFC", parent=card_ac)
        self.inp_codigo.setMaxLength(30)
        self.inp_codigo.textEdited.connect(lambda t: self.inp_codigo.setText(t.upper()))
        self.inp_codigo.text = self.inp_codigo.text
        self.inp_codigo.set_text = self.inp_codigo.setText
        self.inp_codigo.set_focus = self.inp_codigo.setFocus
        
        self.inp_nombre = CustomInput("Nombre descriptivo de la acción", parent=card_ac)
        self.inp_nombre.setMaxLength(100)
        self.inp_nombre.text = self.inp_nombre.text
        self.inp_nombre.set_text = self.inp_nombre.setText
        
        self.inp_desc = CustomInput("Descripción técnica de los privilegios otorgados", parent=card_ac)
        self.inp_desc.setMaxLength(255)
        self.inp_desc.text = self.inp_desc.text
        self.inp_desc.set_text = self.inp_desc.setText
        
        form_ac.addRow("Código *:", self.inp_codigo)
        form_ac.addRow("Nombre *:", self.inp_nombre)
        form_ac.addRow("Descripción:", self.inp_desc)
        lay_ac.addLayout(form_ac)
        dialog.add_widget(card_ac)
        
        self.chk_activo = CustomCheckBox("Acción activa para evaluación de permisos", dialog)
        self.chk_activo.setChecked(True)
        self.chk_activo.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {Colors.TEXT_LIGHT_PRIMARY}; margin: 4px 2px;")
        dialog.add_widget(self.chk_activo)
        
        def _validate_ac():
            c_val = self.inp_codigo.text().strip()
            n_val = self.inp_nombre.text().strip()
            dialog.btn_save.setEnabled(bool(c_val and n_val))
            
        self.inp_codigo.textChanged.connect(_validate_ac)
        self.inp_nombre.textChanged.connect(_validate_ac)
        _validate_ac()
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_codigo.setReadOnly(True)
            self.inp_nombre.setReadOnly(True)
            self.inp_desc.setReadOnly(True)
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
            "codigo": self.inp_codigo.text().strip().upper(),
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
                data = [{"accion_id": i.get("accion_id", i.get("id")), "codigo": i.get("codigo", ""), "nombre": i.get("nombre", ""), "descripcion": i.get("descripcion", ""), "activo": i.get("activo", True)} for i in acciones]
                self.tbl_acciones.populate(data)
            else:
                with self.db_connector.get_session() as session:
                    repo = UsuarioRepository(session)
                    items = repo.get_all_acciones()
                    data = [{"accion_id": i.accion_id, "codigo": i.codigo, "nombre": i.nombre, "descripcion": i.descripcion, "activo": i.activo} for i in items]
                    self.tbl_acciones.populate(data)
        except Exception as e:
            print("Error refreshing acciones:", e)
