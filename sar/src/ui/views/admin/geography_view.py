"""Geography Administration Sub-view."""

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
from sar.src.storage.repositories import CatalogoRepository
from sar.src.services.admin_service import AdminService

class GeographyView(QWidget):
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
        self.tbl_muns = CrudTablePanel("Municipios")
        self.tbl_muns.setup_table(["ID", "Código Portal", "Nombre", "Estado"], ["municipio_id", "codigo_portal", "nombre", "activo"])
        self.tbl_muns.add_requested.connect(self._on_new_mun)
        self.tbl_muns.edit_requested.connect(self._on_edit_mun)
        self.tbl_muns.item_selected.connect(self._on_mun_selected)
        self.layout.addWidget(self.tbl_muns)
        
        self.tbl_dels = CrudTablePanel("Delegaciones")
        self.tbl_dels.setup_table(["ID", "Código Portal", "Nombre", "Estado"], ["delegacion_id", "codigo_portal", "nombre", "activo"])
        self.tbl_dels.add_requested.connect(self._on_new_del)
        self.tbl_dels.edit_requested.connect(self._on_edit_del)
        self.layout.addWidget(self.tbl_dels)
        self.tbl_dels.setEnabled(False)
        
        self.current_mun_id = None
        self.current_del_id = None
        self.tbl_muns.btn_add.setVisible(self.can_edit)
        self.tbl_dels.btn_add.setVisible(self.can_edit)
        
    def _create_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        dialog.setMinimumWidth(540)
        
        card_m = QFrame(dialog)
        card_m.setObjectName("card_m")
        card_m.setStyleSheet(f"""
            QFrame#card_m {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay_m = QVBoxLayout(card_m)
        lay_m.setContentsMargins(0, 0, 0, 0)
        lay_m.setSpacing(8)
        
        lbl_m = CustomLabel("🗺️ DATOS DEL MUNICIPIO", variant="subheader")
        lbl_m.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay_m.addWidget(lbl_m)
        
        form_m = QFormLayout()
        form_m.setSpacing(8)
        form_m.setContentsMargins(0, 0, 0, 0)
        
        self.inp_m_codigo_portal = CustomInput("Ej. MUN_001 (Opcional)", parent=card_m)
        self.inp_m_codigo_portal.setMaxLength(30)
        self.inp_m_codigo_portal.text = self.inp_m_codigo_portal.text
        self.inp_m_codigo_portal.set_text = self.inp_m_codigo_portal.setText
        
        self.inp_m_nombre = CustomInput("Nombre del municipio (ej. BENITO JUÁREZ)", parent=card_m)
        self.inp_m_nombre.setMaxLength(100)
        self.inp_m_nombre.textEdited.connect(lambda t: self.inp_m_nombre.setText(t.upper()))
        self.inp_m_nombre.text = self.inp_m_nombre.text
        self.inp_m_nombre.set_text = self.inp_m_nombre.setText
        self.inp_m_nombre.set_focus = self.inp_m_nombre.setFocus
        
        form_m.addRow("Código Portal:", self.inp_m_codigo_portal)
        form_m.addRow("Nombre Municipio *:", self.inp_m_nombre)
        lay_m.addLayout(form_m)
        dialog.add_widget(card_m)
        
        self.chk_m_activo = CustomCheckBox("Municipio activo en catálogo", dialog)
        self.chk_m_activo.setChecked(True)
        self.chk_m_activo.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {Colors.TEXT_LIGHT_PRIMARY}; margin: 4px 2px;")
        dialog.add_widget(self.chk_m_activo)
        
        def _validate_m():
            dialog.btn_save.setEnabled(bool(self.inp_m_nombre.text().strip()))
        self.inp_m_nombre.textChanged.connect(_validate_m)
        _validate_m()
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_m_codigo_portal.setReadOnly(True)
            self.inp_m_nombre.setReadOnly(True)
            self.chk_m_activo.setEnabled(False)
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_mun(dialog))
        return dialog
 
    def _on_new_mun(self):
        self.current_mun_id_edit = None
        dialog = self._create_dialog("Nuevo Municipio")
        self.inp_m_nombre.set_focus()
        dialog.exec()
        
    def _on_mun_selected(self, data: dict):
        self.current_mun_id = data.get("municipio_id")
        self.tbl_dels.setEnabled(True)
        self.tbl_dels.lbl_title.setText(f"Delegaciones de {data.get('nombre')}")
        self.refresh_delegaciones()
        
    def _on_edit_mun(self, data: dict):
        self.current_mun_id_edit = data.get("municipio_id")
        dialog = self._create_dialog(f"Editar Municipio: {data.get('nombre')}")
        self.inp_m_codigo_portal.set_text(data.get("codigo_portal", "") or "")
        self.inp_m_nombre.set_text(data.get("nombre", ""))
        self.chk_m_activo.setChecked(bool(data.get("activo", False)))
        self.inp_m_nombre.set_focus()
        dialog.exec()
 
    def _save_mun(self, dialog: CustomDialog):
        data = {
            "municipio_id": self.current_mun_id_edit,
            "codigo_portal": self.inp_m_codigo_portal.text().strip(),
            "nombre": self.inp_m_nombre.text().strip().upper(),
            "activo": self.chk_m_activo.isChecked()
        }
        try:
            if self.api_client.connect_via_api:
                payload = {
                    "usuario_id": self.current_user_id,
                    "sesion_id": self.current_sesion_id,
                    "data": data
                }
                self.api_client.request("POST", "/api/admin/save/municipios", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    service = AdminService(session)
                    service.save_municipio(self.current_user_id, self.current_sesion_id, data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Municipio guardado correctamente.")
            dialog.accept()
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def _create_del_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        dialog.setMinimumWidth(540)
        
        card_d = QFrame(dialog)
        card_d.setObjectName("card_d")
        card_d.setStyleSheet(f"""
            QFrame#card_d {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay_d = QVBoxLayout(card_d)
        lay_d.setContentsMargins(0, 0, 0, 0)
        lay_d.setSpacing(8)
        
        lbl_d = CustomLabel("📍 DATOS DE LA DELEGACIÓN", variant="subheader")
        lbl_d.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay_d.addWidget(lbl_d)
        
        form_d = QFormLayout()
        form_d.setSpacing(8)
        form_d.setContentsMargins(0, 0, 0, 0)
        
        self.inp_d_codigo_portal = CustomInput("Ej. DEL_001 (Opcional)", parent=card_d)
        self.inp_d_codigo_portal.setMaxLength(30)
        self.inp_d_codigo_portal.text = self.inp_d_codigo_portal.text
        self.inp_d_codigo_portal.set_text = self.inp_d_codigo_portal.setText
        
        self.inp_d_nombre = CustomInput("Nombre de la delegación (ej. CANCÚN CENTRO)", parent=card_d)
        self.inp_d_nombre.setMaxLength(100)
        self.inp_d_nombre.textEdited.connect(lambda t: self.inp_d_nombre.setText(t.upper()))
        self.inp_d_nombre.text = self.inp_d_nombre.text
        self.inp_d_nombre.set_text = self.inp_d_nombre.setText
        self.inp_d_nombre.set_focus = self.inp_d_nombre.setFocus
        
        form_d.addRow("Código Portal:", self.inp_d_codigo_portal)
        form_d.addRow("Nombre Delegación *:", self.inp_d_nombre)
        lay_d.addLayout(form_d)
        dialog.add_widget(card_d)
        
        self.chk_d_activo = CustomCheckBox("Delegación activa en catálogo", dialog)
        self.chk_d_activo.setChecked(True)
        self.chk_d_activo.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {Colors.TEXT_LIGHT_PRIMARY}; margin: 4px 2px;")
        dialog.add_widget(self.chk_d_activo)
        
        def _validate_d():
            dialog.btn_save.setEnabled(bool(self.inp_d_nombre.text().strip()))
        self.inp_d_nombre.textChanged.connect(_validate_d)
        _validate_d()
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_d_codigo_portal.setReadOnly(True)
            self.inp_d_nombre.setReadOnly(True)
            self.chk_d_activo.setEnabled(False)
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_del(dialog))
        return dialog
 
    def _on_new_del(self):
        self.current_del_id = None
        dialog = self._create_del_dialog("Nueva Delegación")
        self.inp_d_nombre.set_focus()
        dialog.exec()
        
    def _on_edit_del(self, data: dict):
        self.current_del_id = data.get("delegacion_id")
        dialog = self._create_del_dialog(f"Editar Delegación: {data.get('nombre')}")
        self.inp_d_codigo_portal.set_text(data.get("codigo_portal", "") or "")
        self.inp_d_nombre.set_text(data.get("nombre", ""))
        self.chk_d_activo.setChecked(bool(data.get("activo", False)))
        self.inp_d_nombre.set_focus()
        dialog.exec()
 
    def _save_del(self, dialog: CustomDialog):
        data = {
            "delegacion_id": self.current_del_id,
            "municipio_id": self.current_mun_id,
            "codigo_portal": self.inp_d_codigo_portal.text().strip(),
            "nombre": self.inp_d_nombre.text().strip().upper(),
            "activo": self.chk_d_activo.isChecked()
        }
        try:
            if self.api_client.connect_via_api:
                payload = {
                    "usuario_id": self.current_user_id,
                    "sesion_id": self.current_sesion_id,
                    "data": data
                }
                self.api_client.request("POST", "/api/admin/save/delegaciones", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    service = AdminService(session)
                    service.save_delegacion(self.current_user_id, self.current_sesion_id, data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Delegación guardada correctamente.")
            dialog.accept()
            self.refresh_delegaciones()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def refresh_data(self):
        try:
            if self.api_client.connect_via_api:
                muns = self.api_client.request("GET", "/api/admin/data/municipios")
                self.tbl_muns.populate(muns)
            else:
                with self.db_connector.get_session() as session:
                    repo = CatalogoRepository(session)
                    items = repo.get_all_municipios()
                    data = [{"municipio_id": i.municipio_id, "codigo_portal": i.codigo_portal, "nombre": i.nombre, "activo": i.activo} for i in items]
                    self.tbl_muns.populate(data)
            
            if self.current_mun_id:
                self.refresh_delegaciones()
            else:
                self.tbl_dels.populate([])
                self.tbl_dels.setEnabled(False)
        except Exception as e:
            print("Error refreshing geography:", e)
 
    def refresh_delegaciones(self):
        if not self.current_mun_id:
            return
        try:
            if self.api_client.connect_via_api:
                all_dels = self.api_client.request("GET", "/api/admin/data/delegaciones")
                filtered = [d for d in all_dels if d.get("municipio_id") == self.current_mun_id]
                self.tbl_dels.populate(filtered)
            else:
                with self.db_connector.get_session() as session:
                    repo = CatalogoRepository(session)
                    items = repo.get_delegaciones_by_municipio(self.current_mun_id)
                    data = [{"delegacion_id": i.delegacion_id, "codigo_portal": i.codigo_portal, "nombre": i.nombre, "activo": i.activo} for i in items]
                    self.tbl_dels.populate(data)
        except Exception as e:
            print("Error refreshing delegaciones:", e)
