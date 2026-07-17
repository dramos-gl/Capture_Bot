"""RFCs Administration Sub-view."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QMessageBox, QCheckBox, QGridLayout
from sar.src.ui.design_system.components.molecules.gl_labeled_input import LabeledInput
from sar.src.ui.design_system.components.organisms.gl_crud_table import CrudTablePanel
from sar.src.ui.design_system.components.organisms.gl_dialog import CustomDialog
from sar.src.storage.repositories import CatalogoRepository
from sar.src.services.admin_service import AdminService

class RfcsView(QWidget):
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
        self.tbl_rfcs = CrudTablePanel("Registro Federal de Contribuyentes (RFC)")
        headers = ["ID", "RFC", "Razón Social", "Calle", "No. Ext.", "No. Int.", "Colonia", "CP", "Localidad", "Municipio", "Estado", "Activo"]
        keys = ["rfc_id", "rfc", "razon_social", "calle", "no_exterior", "no_interior", "colonia", "codigo_postal", "localidad", "municipio", "estado", "activo"]
        self.tbl_rfcs.setup_table(headers, keys)
        self.tbl_rfcs.add_requested.connect(self._on_new)
        self.tbl_rfcs.edit_requested.connect(self._on_edit)
        self.layout.addWidget(self.tbl_rfcs)
        
        self.current_rfc_id = None
        self.tbl_rfcs.btn_add.setVisible(self.can_edit)
        
    def _create_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        
        self.inp_rfc = LabeledInput("RFC")
        self.inp_rfc.set_validator(r"^[A-ZÑ&]{3,4}\d{6}(?:[A-Z\d]{3})?$", "Debe tener formato de RFC válido (12 o 13 caracteres mayúsculas/números).")
        self.inp_rs = LabeledInput("Razón Social")
        self.inp_calle = LabeledInput("Calle (Opcional)")
        self.inp_ext = LabeledInput("No. Exterior (Opcional)")
        self.inp_int = LabeledInput("No. Interior (Opcional)")
        self.inp_col = LabeledInput("Colonia (Opcional)")
        self.inp_cp = LabeledInput("Código Postal (Opcional)")
        self.inp_loc = LabeledInput("Localidad (Opcional)")
        self.inp_mun = LabeledInput("Municipio (Opcional)")
        self.inp_est = LabeledInput("Estado (Opcional)")
        self.chk_activo = QCheckBox("Activo")
        self.chk_activo.setChecked(True)
        
        # Create a container for the grid layout
        grid_container = QWidget()
        grid = QGridLayout(grid_container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(16)
        
        grid.addWidget(self.inp_rfc, 0, 0)
        grid.addWidget(self.inp_rs, 0, 1)
        grid.addWidget(self.inp_calle, 1, 0)
        grid.addWidget(self.inp_ext, 1, 1)
        grid.addWidget(self.inp_int, 2, 0)
        grid.addWidget(self.inp_col, 2, 1)
        grid.addWidget(self.inp_cp, 3, 0)
        grid.addWidget(self.inp_loc, 3, 1)
        grid.addWidget(self.inp_mun, 4, 0)
        grid.addWidget(self.inp_est, 4, 1)
        grid.addWidget(self.chk_activo, 5, 0, 1, 2)
        
        dialog.add_widget(grid_container)
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_rfc.input.setReadOnly(True)
            self.inp_rs.input.setReadOnly(True)
            self.inp_calle.input.setReadOnly(True)
            self.inp_ext.input.setReadOnly(True)
            self.inp_int.input.setReadOnly(True)
            self.inp_col.input.setReadOnly(True)
            self.inp_cp.input.setReadOnly(True)
            self.inp_loc.input.setReadOnly(True)
            self.inp_mun.input.setReadOnly(True)
            self.inp_est.input.setReadOnly(True)
            self.chk_activo.setEnabled(False)
            
        # Bind validation states to the save button
        self._valid_states = {"rfc": True}
        
        def _on_validity_changed(field: str, is_valid: bool):
            self._valid_states[field] = is_valid
            dialog.btn_save.setEnabled(all(self._valid_states.values()))
            
        self.inp_rfc.validity_changed.connect(lambda v: _on_validity_changed("rfc", v))
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save(dialog))
        return dialog
 
    def _on_new(self):
        self.current_rfc_id = None
        dialog = self._create_dialog("Nuevo RFC")
        self.inp_rfc.set_focus()
        dialog.exec()
        
    def _on_edit(self, data: dict):
        self.current_rfc_id = data.get("rfc_id")
        dialog = self._create_dialog(f"Editar RFC: {data.get('rfc')}")
        
        self.inp_rfc.set_text(data.get("rfc", ""))
        self.inp_rs.set_text(data.get("razon_social", ""))
        self.inp_calle.set_text(data.get("calle", "") or "")
        self.inp_ext.set_text(data.get("no_exterior", "") or "")
        self.inp_int.set_text(data.get("no_interior", "") or "")
        self.inp_col.set_text(data.get("colonia", "") or "")
        self.inp_cp.set_text(data.get("codigo_postal", "") or "")
        self.inp_loc.set_text(data.get("localidad", "") or "")
        self.inp_mun.set_text(data.get("municipio", "") or "")
        self.inp_est.set_text(data.get("estado", "") or "")
        self.chk_activo.setChecked(bool(data.get("activo", False)))
        
        self.inp_rfc.set_focus()
        dialog.exec()
 
    def _save(self, dialog: CustomDialog):
        data = {
            "rfc_id": self.current_rfc_id,
            "rfc": self.inp_rfc.text().strip().upper(),
            "razon_social": self.inp_rs.text().strip(),
            "calle": self.inp_calle.text().strip(),
            "no_exterior": self.inp_ext.text().strip(),
            "no_interior": self.inp_int.text().strip(),
            "colonia": self.inp_col.text().strip(),
            "codigo_postal": self.inp_cp.text().strip(),
            "localidad": self.inp_loc.text().strip(),
            "municipio": self.inp_mun.text().strip(),
            "estado": self.inp_est.text().strip(),
            "activo": self.chk_activo.isChecked()
        }
        
        try:
            if self.api_client.connect_via_api:
                payload = {
                    "usuario_id": self.current_user_id,
                    "sesion_id": self.current_sesion_id,
                    "data": data
                }
                self.api_client.request("POST", "/api/admin/save/rfcs", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    service = AdminService(session)
                    service.save_rfc(self.current_user_id, self.current_sesion_id, data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "RFC guardado correctamente.")
            dialog.accept()
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def refresh_data(self):
        try:
            if self.api_client.connect_via_api:
                data = self.api_client.request("GET", "/api/admin/data/rfcs")
                self.tbl_rfcs.populate(data)
            else:
                with self.db_connector.get_session() as session:
                    repo = CatalogoRepository(session)
                    items = repo.get_all_rfcs()
                    data = [{
                        "rfc_id": i.rfc_id, 
                        "rfc": i.rfc, 
                        "razon_social": i.razon_social, 
                        "calle": i.calle,
                        "no_exterior": i.no_exterior,
                        "no_interior": i.no_interior,
                        "colonia": i.colonia,
                        "codigo_postal": i.codigo_postal,
                        "localidad": i.localidad,
                        "municipio": i.municipio,
                        "estado": i.estado,
                        "activo": i.activo
                    } for i in items]
                    self.tbl_rfcs.populate(data)
        except Exception as e:
            print("Error refreshing RFCs:", e)
