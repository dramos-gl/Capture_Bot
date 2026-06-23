"""System Status Administration Sub-view."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QMessageBox
from sar.src.ui.design_system.components.molecules.gl_labeled_input import LabeledInput
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
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self._build_ui()
        self.refresh_data()
        
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
        
        self.inp_entidad = LabeledInput("Entidad (Tabla destino)")
        self.inp_codigo = LabeledInput("Código")
        self.inp_desc = LabeledInput("Descripción")
        
        dialog.add_widget(self.inp_entidad)
        dialog.add_widget(self.inp_codigo)
        dialog.add_widget(self.inp_desc)
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_entidad.input.setReadOnly(True)
            self.inp_codigo.input.setReadOnly(True)
            self.inp_desc.input.setReadOnly(True)
            
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
            "entidad": self.inp_entidad.text().strip(),
            "codigo": self.inp_codigo.text().strip(),
            "descripcion": self.inp_desc.text().strip()
        }
        
        try:
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
            with self.db_connector.get_session() as session:
                repo = CatalogoRepository(session)
                items = repo.get_all_estados_sistema()
                data = [{"estado_id": i.estado_id, "entidad": i.entidad, "codigo": i.codigo, "descripcion": i.descripcion} for i in items]
                self.tbl_status.populate(data)
        except Exception as e:
            print("Error refreshing estados:", e)
