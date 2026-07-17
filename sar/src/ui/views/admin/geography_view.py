"""Geography Administration Sub-view."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QMessageBox, QCheckBox
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.molecules.gl_labeled_input import LabeledInput
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
        self.tbl_dels.setEnabled(False) # Disabled until a mun is selected
        
        self.current_mun_id = None
        self.current_del_id = None
        self.tbl_muns.btn_add.setVisible(self.can_edit)
        self.tbl_dels.btn_add.setVisible(self.can_edit)
        
    def _create_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        
        self.inp_m_codigo_portal = LabeledInput("Código Portal (Opcional)")
        self.inp_m_nombre = LabeledInput("Nombre")
        self.chk_m_activo = QCheckBox("Activo")
        self.chk_m_activo.setChecked(True)
        
        dialog.add_widget(self.inp_m_codigo_portal)
        dialog.add_widget(self.inp_m_nombre)
        dialog.add_widget(self.chk_m_activo)
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_m_codigo_portal.input.setReadOnly(True)
            self.inp_m_nombre.input.setReadOnly(True)
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
            "nombre": self.inp_m_nombre.text().strip(),
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
        self.inp_d_codigo_portal = LabeledInput("Código Portal (Opcional)")
        self.inp_d_nombre = LabeledInput("Nombre")
        self.chk_d_activo = QCheckBox("Activo")
        self.chk_d_activo.setChecked(True)
        dialog.add_widget(self.inp_d_codigo_portal)
        dialog.add_widget(self.inp_d_nombre)
        dialog.add_widget(self.chk_d_activo)
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_d_codigo_portal.input.setReadOnly(True)
            self.inp_d_nombre.input.setReadOnly(True)
            self.chk_d_activo.setEnabled(False)
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_del(dialog))
        return dialog
 
    def _on_new_del(self):
        if not self.current_mun_id: return
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
        if not self.current_mun_id: return
        data = {
            "delegacion_id": self.current_del_id,
            "municipio_id": self.current_mun_id,
            "codigo_portal": self.inp_d_codigo_portal.text().strip(),
            "nombre": self.inp_d_nombre.text().strip(),
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
            QMessageBox.information(self, "Éxito", "Delegación guardada.")
            dialog.accept()
            self.refresh_delegaciones()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def refresh_data(self):
        try:
            if self.api_client.connect_via_api:
                data = self.api_client.request("GET", "/api/admin/data/municipios")
                self.tbl_muns.populate(data)
            else:
                with self.db_connector.get_session() as session:
                    repo = CatalogoRepository(session)
                    items = repo.get_all_municipios()
                    data = [{"municipio_id": i.municipio_id, "codigo_portal": i.codigo_portal, "nombre": i.nombre, "activo": i.activo} for i in items]
                    self.tbl_muns.populate(data)
        except Exception as e:
            print("Error refreshing geografía:", e)
 
    def refresh_delegaciones(self):
        if not self.current_mun_id: return
        try:
            if self.api_client.connect_via_api:
                all_dels = self.api_client.request("GET", "/api/admin/data/delegaciones")
                # Filter delegaciones locally by current_mun_id
                filtered_dels = [d for d in all_dels if d["municipio_id"] == self.current_mun_id]
                self.tbl_dels.populate(filtered_dels)
            else:
                with self.db_connector.get_session() as session:
                    repo = CatalogoRepository(session)
                    items = repo.get_delegaciones_por_municipio(self.current_mun_id)
                    data = [{"delegacion_id": i.delegacion_id, "codigo_portal": i.codigo_portal, "nombre": i.nombre, "activo": i.activo} for i in items]
                    self.tbl_dels.populate(data)
        except Exception as e:
            print("Error refreshing delegaciones:", e)
