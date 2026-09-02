import re
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QFrame, QLabel
from PySide6.QtCore import Qt
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.atoms.gl_input import CustomInput
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
from sar.src.ui.design_system.components.organisms.gl_crud_table import CrudTablePanel
from sar.src.ui.design_system.components.organisms.gl_dialog import CustomDialog
from sar.src.storage.repositories import CatalogoRepository
from sar.src.services.admin_service import AdminService

class StatusView(QWidget):
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
        self.tbl_status = CrudTablePanel("Estados del Sistema")
        self.tbl_status.setup_table(["ID", "Entidad", "Código", "Descripción"], ["estado_id", "entidad", "codigo", "descripcion"])
        self.tbl_status.add_requested.connect(self._on_new)
        self.tbl_status.edit_requested.connect(self._on_edit)
        self.layout.addWidget(self.tbl_status)
        
        self.current_estado_id = None
        self.tbl_status.btn_add.setVisible(self.can_edit)
        
    def _create_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        dialog.setMinimumWidth(540)
        
        card_st = QFrame(dialog)
        card_st.setObjectName("card_st")
        card_st.setStyleSheet(f"""
            QFrame#card_st {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay_st = QVBoxLayout(card_st)
        lay_st.setContentsMargins(0, 0, 0, 0)
        lay_st.setSpacing(8)
        
        lbl_st = CustomLabel("🚦 REGISTRO DE ESTADO DE FLUJO", variant="subheader")
        lbl_st.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay_st.addWidget(lbl_st)
        
        form_st = QFormLayout()
        form_st.setSpacing(8)
        form_st.setContentsMargins(0, 0, 0, 0)
        
        self.inp_entidad = CustomInput("Tabla o módulo (ej. ORDENES)", parent=card_st)
        self.inp_entidad.setMaxLength(50)
        self.inp_entidad.textEdited.connect(lambda t: self.inp_entidad.setText(t.upper()))
        self.inp_entidad.text = self.inp_entidad.text
        self.inp_entidad.set_text = self.inp_entidad.setText
        self.inp_entidad.set_focus = self.inp_entidad.setFocus
        
        self.inp_codigo = CustomInput("Código único de estado (ej. EN_PROCESO)", parent=card_st)
        self.inp_codigo.setMaxLength(50)
        self.inp_codigo.textEdited.connect(lambda t: self.inp_codigo.setText(t.upper()))
        self.inp_codigo.text = self.inp_codigo.text
        self.inp_codigo.set_text = self.inp_codigo.setText
        
        self.inp_desc = CustomInput("Descripción del estado en el workflow", parent=card_st)
        self.inp_desc.setMaxLength(255)
        self.inp_desc.text = self.inp_desc.text
        self.inp_desc.set_text = self.inp_desc.setText
        
        form_st.addRow("Entidad *:", self.inp_entidad)
        form_st.addRow("Código *:", self.inp_codigo)
        form_st.addRow("Descripción:", self.inp_desc)
        lay_st.addLayout(form_st)
        dialog.add_widget(card_st)
        
        def _validate_st():
            e_val = self.inp_entidad.text().strip()
            c_val = self.inp_codigo.text().strip()
            dialog.btn_save.setEnabled(bool(e_val and c_val))
            
        self.inp_entidad.textChanged.connect(_validate_st)
        self.inp_codigo.textChanged.connect(_validate_st)
        _validate_st()
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_entidad.setReadOnly(True)
            self.inp_codigo.setReadOnly(True)
            self.inp_desc.setReadOnly(True)
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save(dialog))
        return dialog

    def _on_new(self):
        self.current_estado_id = None
        dialog = self._create_dialog("Nuevo Estado de Sistema")
        self.inp_entidad.set_focus()
        dialog.exec()
        
    def _on_edit(self, data: dict):
        self.current_estado_id = data.get("estado_id")
        dialog = self._create_dialog(f"Editar Estado: {data.get('codigo')}")
        self.inp_entidad.set_text(data.get("entidad", ""))
        self.inp_codigo.set_text(data.get("codigo", ""))
        self.inp_desc.set_text(data.get("descripcion", "") or "")
        self.inp_entidad.set_focus()
        dialog.exec()

    def _save(self, dialog: CustomDialog):
        data = {
            "estado_id": self.current_estado_id,
            "entidad": self.inp_entidad.text().strip().upper(),
            "codigo": self.inp_codigo.text().strip().upper(),
            "descripcion": self.inp_desc.text().strip()
        }
        
        try:
            if self.api_client.connect_via_api:
                payload = {
                    "usuario_id": self.current_user_id,
                    "sesion_id": self.current_sesion_id,
                    "data": data
                }
                self.api_client.request("POST", "/api/admin/save/estados", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    service = AdminService(session)
                    service.save_estado_sistema(self.current_user_id, self.current_sesion_id, data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Estado guardado correctamente.")
            dialog.accept()
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def refresh_data(self):
        try:
            if self.api_client.connect_via_api:
                data = self.api_client.request("GET", "/api/admin/data/estados")
                self.tbl_status.populate(data)
            else:
                with self.db_connector.get_session() as session:
                    repo = CatalogoRepository(session)
                    items = repo.get_all_estados_sistema()
                    data = [{"estado_id": i.estado_id, "entidad": i.entidad, "codigo": i.codigo, "descripcion": i.descripcion} for i in items]
                    self.tbl_status.populate(data)
        except Exception as e:
            print("Error refreshing estados:", e)
