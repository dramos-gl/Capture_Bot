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
        dialog.setMinimumWidth(580)
        
        card_l = QFrame(dialog)
        card_l.setObjectName("card_l")
        card_l.setStyleSheet(f"""
            QFrame#card_l {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay_l = QVBoxLayout(card_l)
        lay_l.setContentsMargins(0, 0, 0, 0)
        lay_l.setSpacing(8)
        
        lbl_l = CustomLabel("🤖 LOCALIZADOR WEB DE CAPTURA (BOT)", variant="subheader")
        lbl_l.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay_l.addWidget(lbl_l)
        
        form_l = QFormLayout()
        form_l.setSpacing(8)
        form_l.setContentsMargins(0, 0, 0, 0)
        
        self.inp_l_clave = CustomInput("Ej. BTN_GUARDAR_SOLICITUD", parent=card_l)
        self.inp_l_clave.setMaxLength(50)
        self.inp_l_clave.textEdited.connect(lambda t: self.inp_l_clave.setText(t.upper()))
        self.inp_l_clave.text = self.inp_l_clave.text
        self.inp_l_clave.set_text = self.inp_l_clave.setText
        self.inp_l_clave.set_focus = self.inp_l_clave.setFocus
        
        self.inp_l_label = CustomInput("Etiqueta visible en portal bancario/SAT", parent=card_l)
        self.inp_l_label.setMaxLength(100)
        self.inp_l_label.text = self.inp_l_label.text
        self.inp_l_label.set_text = self.inp_l_label.setText
        
        self.cmb_l_estrategia = CustomComboBox(card_l)
        self.cmb_l_estrategia.addItems(["css", "xpath", "id", "name"])
        
        self.inp_l_selector = CustomInput("Ej. #btn-submit o //button[@id='save']", parent=card_l)
        self.inp_l_selector.setMaxLength(255)
        self.inp_l_selector.text = self.inp_l_selector.text
        self.inp_l_selector.set_text = self.inp_l_selector.setText
        
        form_l.addRow("Nombre Clave *:", self.inp_l_clave)
        form_l.addRow("Label Visible:", self.inp_l_label)
        form_l.addRow("Estrategia *:", self.cmb_l_estrategia)
        form_l.addRow("Valor Selector *:", self.inp_l_selector)
        lay_l.addLayout(form_l)
        dialog.add_widget(card_l)
        
        self.chk_l_activo = CustomCheckBox("Localizador activo para automatización", dialog)
        self.chk_l_activo.setChecked(True)
        self.chk_l_activo.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {Colors.TEXT_LIGHT_PRIMARY}; margin: 4px 2px;")
        dialog.add_widget(self.chk_l_activo)
        
        def _validate_l():
            c_val = self.inp_l_clave.text().strip()
            s_val = self.inp_l_selector.text().strip()
            dialog.btn_save.setEnabled(bool(c_val and s_val))
            
        self.inp_l_clave.textChanged.connect(_validate_l)
        self.inp_l_selector.textChanged.connect(_validate_l)
        _validate_l()
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_l_clave.setReadOnly(True)
            self.inp_l_label.setReadOnly(True)
            self.cmb_l_estrategia.setEnabled(False)
            self.inp_l_selector.setReadOnly(True)
            self.chk_l_activo.setEnabled(False)
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_loc(dialog))
        return dialog

    def _on_new_loc(self):
        self.current_loc_id = None
        dialog = self._create_dialog("Nuevo Localizador")
        self.inp_l_clave.set_focus()
        dialog.exec()
        
    def _on_edit_loc(self, data: dict):
        self.current_loc_id = data.get("localizador_id")
        dialog = self._create_dialog(f"Editar Localizador: {data.get('nombre_clave')}")
        self.inp_l_clave.set_text(data.get("nombre_clave", ""))
        self.inp_l_label.set_text(data.get("label_visible", "") or "")
        
        est = data.get("estrategia_selector", "css")
        idx = self.cmb_l_estrategia.findText(est)
        if idx >= 0:
            self.cmb_l_estrategia.setCurrentIndex(idx)
            
        self.inp_l_selector.set_text(data.get("valor_selector", ""))
        self.chk_l_activo.setChecked(bool(data.get("activo", False)))
        self.inp_l_clave.set_focus()
        dialog.exec()

    def _save_loc(self, dialog: CustomDialog):
        data = {
            "localizador_id": self.current_loc_id,
            "nombre_clave": self.inp_l_clave.text().strip().upper(),
            "label_visible": self.inp_l_label.text().strip(),
            "estrategia_selector": self.cmb_l_estrategia.currentText(),
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
