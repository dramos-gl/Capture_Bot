"""Catalogs Administration Sub-view."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QMessageBox, QCheckBox
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.molecules.gl_labeled_input import LabeledInput
from sar.src.ui.design_system.components.organisms.gl_crud_table import CrudTablePanel
from sar.src.ui.design_system.components.organisms.gl_dialog import CustomDialog
from sar.src.storage.repositories import CatalogoRepository
from sar.src.services.admin_service import AdminService

class CatalogsView(QWidget):
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
        self.tbl_conceptos = CrudTablePanel("Catálogo de Conceptos")
        self.tbl_conceptos.setup_table(["ID", "Código Portal", "Nombre", "Alias", "Estado"], ["concepto_id", "codigo_portal", "nombre", "alias", "activo"])
        self.tbl_conceptos.add_requested.connect(self._on_new_concepto)
        self.tbl_conceptos.edit_requested.connect(self._on_edit_concepto)
        self.layout.addWidget(self.tbl_conceptos)
        
        self.current_concepto_id = None
        self.tbl_conceptos.btn_add.setVisible(self.can_edit)
        
    def _create_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        
        self.inp_c_codigo_portal = LabeledInput("Código Portal (Opcional)")
        self.inp_c_nombre = LabeledInput("Nombre del Concepto")
        self.inp_c_alias = LabeledInput("Alias (Opcional)")
        self.inp_c_alias.input.setMaxLength(20)
        self.chk_c_activo = QCheckBox("Concepto Activo")
        self.chk_c_activo.setChecked(True)
        
        dialog.add_widget(self.inp_c_codigo_portal)
        dialog.add_widget(self.inp_c_nombre)
        dialog.add_widget(self.inp_c_alias)
        dialog.add_widget(self.chk_c_activo)
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_c_codigo_portal.input.setReadOnly(True)
            self.inp_c_nombre.input.setReadOnly(True)
            self.inp_c_alias.input.setReadOnly(True)
            self.chk_c_activo.setEnabled(False)
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_concepto(dialog))
        
        return dialog

    def _on_new_concepto(self):
        self.current_concepto_id = None
        dialog = self._create_dialog("Nuevo Concepto")
        self.inp_c_nombre.set_focus()
        dialog.exec()
        
    def _on_edit_concepto(self, data: dict):
        self.current_concepto_id = data.get("concepto_id")
        dialog = self._create_dialog(f"Editar Concepto: {data.get('nombre')}")
        
        self.inp_c_codigo_portal.set_text(data.get("codigo_portal", "") or "")
        self.inp_c_nombre.set_text(data.get("nombre", ""))
        self.inp_c_alias.set_text(data.get("alias", "") or "")
        self.chk_c_activo.setChecked(bool(data.get("activo", False)))
        
        self.inp_c_nombre.set_focus()
        dialog.exec()

    def _save_concepto(self, dialog: CustomDialog):
        data = {
            "concepto_id": self.current_concepto_id,
            "codigo_portal": self.inp_c_codigo_portal.text().strip(),
            "nombre": self.inp_c_nombre.text().strip(),
            "alias": self.inp_c_alias.text().strip(),
            "activo": self.chk_c_activo.isChecked()
        }
        
        if not data["nombre"]:
            QMessageBox.warning(self, "Validación", "El Nombre del Concepto es obligatorio.")
            return
            
        try:
            with self.db_connector.get_session() as session:
                service = AdminService(session)
                service.save_concepto(self.current_user_id, self.current_sesion_id, data)
                session.commit()
            QMessageBox.information(self, "Éxito", "Concepto guardado correctamente.")
            dialog.accept()
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def refresh_data(self):
        try:
            with self.db_connector.get_session() as session:
                repo = CatalogoRepository(session)
                items = repo.get_all_conceptos()
                data = [{"concepto_id": c.concepto_id, "codigo_portal": c.codigo_portal, "nombre": c.nombre, "alias": c.alias, "activo": c.activo} for c in items]
                self.tbl_conceptos.populate(data)
        except Exception as e:
            print("Error refreshing conceptos:", e)
