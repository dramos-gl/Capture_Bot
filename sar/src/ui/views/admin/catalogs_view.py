"""Catalogs Administration Sub-view."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QMessageBox, QCheckBox, QTabWidget
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.molecules.gl_labeled_input import LabeledInput
from sar.src.ui.design_system.components.molecules.gl_labeled_combo import LabeledComboBox
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
        
        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.delegaciones_list = []
        self.delegaciones_map = {}
        
        self._build_ui()
        self.refresh_data()
        
    def _build_ui(self):
        self.tabs = QTabWidget(self)
        self.layout.addWidget(self.tabs)
        
        # 1. Conceptos Tab
        self.tab_conceptos = QWidget()
        lay_concepts = QHBoxLayout(self.tab_conceptos)
        lay_concepts.setContentsMargins(0, 0, 0, 0)
        self.tbl_conceptos = CrudTablePanel("Catálogo de Conceptos")
        self.tbl_conceptos.setup_table(["ID", "Código Portal", "Nombre", "Alias", "Estado"], ["concepto_id", "codigo_portal", "nombre", "alias", "activo"])
        self.tbl_conceptos.add_requested.connect(self._on_new_concepto)
        self.tbl_conceptos.edit_requested.connect(self._on_edit_concepto)
        self.tbl_conceptos.btn_add.setVisible(self.can_edit)
        self.tbl_conceptos.btn_edit.setVisible(self.can_edit)
        lay_concepts.addWidget(self.tbl_conceptos)
        self.tabs.addTab(self.tab_conceptos, "Conceptos")
        
        # 2. Notarías Tab
        self.tab_notarias = QWidget()
        lay_notarias = QHBoxLayout(self.tab_notarias)
        lay_notarias.setContentsMargins(0, 0, 0, 0)
        self.tbl_notarias = CrudTablePanel("Catálogo de Notarías")
        self.tbl_notarias.setup_table(["ID", "Nombre", "Estado"], ["notaria_id", "nombre", "activo"])
        self.tbl_notarias.add_requested.connect(self._on_new_notaria)
        self.tbl_notarias.edit_requested.connect(self._on_edit_notaria)
        self.tbl_notarias.btn_add.setVisible(self.can_edit)
        self.tbl_notarias.btn_edit.setVisible(self.can_edit)
        lay_notarias.addWidget(self.tbl_notarias)
        self.tabs.addTab(self.tab_notarias, "Notarías")
        
        # 3. Colaboradores Tab
        self.tab_colaboradores = QWidget()
        lay_colaboradores = QHBoxLayout(self.tab_colaboradores)
        lay_colaboradores.setContentsMargins(0, 0, 0, 0)
        self.tbl_colaboradores = CrudTablePanel("Catálogo de Colaboradores")
        self.tbl_colaboradores.setup_table(["ID", "Nombre", "Estado"], ["colaborador_id", "nombre", "activo"])
        self.tbl_colaboradores.add_requested.connect(self._on_new_colaborador)
        self.tbl_colaboradores.edit_requested.connect(self._on_edit_colaborador)
        self.tbl_colaboradores.btn_add.setVisible(self.can_edit)
        self.tbl_colaboradores.btn_edit.setVisible(self.can_edit)
        lay_colaboradores.addWidget(self.tbl_colaboradores)
        self.tabs.addTab(self.tab_colaboradores, "Colaboradores")
        
        # 4. Desarrollos Tab
        self.tab_desarrollos = QWidget()
        lay_desarrollos = QHBoxLayout(self.tab_desarrollos)
        lay_desarrollos.setContentsMargins(0, 0, 0, 0)
        self.tbl_desarrollos = CrudTablePanel("Catálogo de Desarrollos")
        self.tbl_desarrollos.setup_table(["ID", "Nombre", "Delegación", "Estado"], ["desarrollo_id", "nombre", "delegacion_nombre", "activo"])
        self.tbl_desarrollos.add_requested.connect(self._on_new_desarrollo)
        self.tbl_desarrollos.edit_requested.connect(self._on_edit_desarrollo)
        self.tbl_desarrollos.btn_add.setVisible(self.can_edit)
        self.tbl_desarrollos.btn_edit.setVisible(self.can_edit)
        lay_desarrollos.addWidget(self.tbl_desarrollos)
        self.tabs.addTab(self.tab_desarrollos, "Desarrollos")

    # --- CONCEPTOS ---
    def _create_concepto_dialog(self, title: str) -> CustomDialog:
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
        dialog = self._create_concepto_dialog("Nuevo Concepto")
        self.inp_c_nombre.set_focus()
        dialog.exec()
        
    def _on_edit_concepto(self, data: dict):
        self.current_concepto_id = data.get("concepto_id")
        dialog = self._create_concepto_dialog(f"Editar Concepto: {data.get('nombre')}")
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
            if self.api_client.connect_via_api:
                payload = {"usuario_id": self.current_user_id, "sesion_id": self.current_sesion_id, "data": data}
                self.api_client.request("POST", "/api/admin/save/conceptos", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    service = AdminService(session)
                    service.save_concepto(self.current_user_id, self.current_sesion_id, data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Concepto guardado correctamente.")
            dialog.accept()
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # --- NOTARIAS ---
    def _create_notaria_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        
        self.inp_n_nombre = LabeledInput("Nombre de la Notaría")
        self.chk_n_activo = QCheckBox("Notaría Activa")
        self.chk_n_activo.setChecked(True)
        
        dialog.add_widget(self.inp_n_nombre)
        dialog.add_widget(self.chk_n_activo)
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_n_nombre.input.setReadOnly(True)
            self.chk_n_activo.setEnabled(False)
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_notaria(dialog))
        return dialog

    def _on_new_notaria(self):
        self.current_notaria_id = None
        dialog = self._create_notaria_dialog("Nueva Notaría")
        self.inp_n_nombre.set_focus()
        dialog.exec()

    def _on_edit_notaria(self, data: dict):
        self.current_notaria_id = data.get("notaria_id")
        dialog = self._create_notaria_dialog(f"Editar Notaría: {data.get('nombre')}")
        self.inp_n_nombre.set_text(data.get("nombre", ""))
        self.chk_n_activo.setChecked(bool(data.get("activo", False)))
        self.inp_n_nombre.set_focus()
        dialog.exec()

    def _save_notaria(self, dialog: CustomDialog):
        data = {
            "notaria_id": self.current_notaria_id,
            "nombre": self.inp_n_nombre.text().strip().upper(),
            "activo": self.chk_n_activo.isChecked()
        }
        if not data["nombre"]:
            QMessageBox.warning(self, "Validación", "El Nombre de la Notaría es obligatorio.")
            return
        try:
            if self.api_client.connect_via_api:
                payload = {"usuario_id": self.current_user_id, "sesion_id": self.current_sesion_id, "data": data}
                self.api_client.request("POST", "/api/admin/save/notarias", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    service = AdminService(session)
                    service.save_notaria(self.current_user_id, self.current_sesion_id, data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Notaría guardada correctamente.")
            dialog.accept()
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # --- COLABORADORES ---
    def _create_colaborador_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        
        self.inp_col_nombre = LabeledInput("Nombre del Colaborador")
        self.chk_col_activo = QCheckBox("Colaborador Activo")
        self.chk_col_activo.setChecked(True)
        
        dialog.add_widget(self.inp_col_nombre)
        dialog.add_widget(self.chk_col_activo)
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_col_nombre.input.setReadOnly(True)
            self.chk_col_activo.setEnabled(False)
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_colaborador(dialog))
        return dialog

    def _on_new_colaborador(self):
        self.current_colaborador_id = None
        dialog = self._create_colaborador_dialog("Nuevo Colaborador")
        self.inp_col_nombre.set_focus()
        dialog.exec()

    def _on_edit_colaborador(self, data: dict):
        self.current_colaborador_id = data.get("colaborador_id")
        dialog = self._create_colaborador_dialog(f"Editar Colaborador: {data.get('nombre')}")
        self.inp_col_nombre.set_text(data.get("nombre", ""))
        self.chk_col_activo.setChecked(bool(data.get("activo", False)))
        self.inp_col_nombre.set_focus()
        dialog.exec()

    def _save_colaborador(self, dialog: CustomDialog):
        data = {
            "colaborador_id": self.current_colaborador_id,
            "nombre": self.inp_col_nombre.text().strip().upper(),
            "activo": self.chk_col_activo.isChecked()
        }
        if not data["nombre"]:
            QMessageBox.warning(self, "Validación", "El Nombre del Colaborador es obligatorio.")
            return
        try:
            if self.api_client.connect_via_api:
                payload = {"usuario_id": self.current_user_id, "sesion_id": self.current_sesion_id, "data": data}
                self.api_client.request("POST", "/api/admin/save/colaboradores", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    service = AdminService(session)
                    service.save_colaborador(self.current_user_id, self.current_sesion_id, data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Colaborador guardado correctamente.")
            dialog.accept()
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # --- DESARROLLOS ---
    def _create_desarrollo_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        
        self.inp_d_nombre = LabeledInput("Nombre del Desarrollo")
        
        delegacion_names = [d["nombre"] for d in self.delegaciones_list]
        self.cmb_d_delegacion = LabeledComboBox("Delegación", delegacion_names)
        
        self.chk_d_activo = QCheckBox("Desarrollo Activo")
        self.chk_d_activo.setChecked(True)
        
        dialog.add_widget(self.inp_d_nombre)
        dialog.add_widget(self.cmb_d_delegacion)
        dialog.add_widget(self.chk_d_activo)
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_d_nombre.input.setReadOnly(True)
            self.cmb_d_delegacion.combo.setEnabled(False)
            self.chk_d_activo.setEnabled(False)
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_desarrollo(dialog))
        return dialog

    def _on_new_desarrollo(self):
        self.current_desarrollo_id = None
        dialog = self._create_desarrollo_dialog("Nuevo Desarrollo")
        self.inp_d_nombre.set_focus()
        dialog.exec()

    def _on_edit_desarrollo(self, data: dict):
        self.current_desarrollo_id = data.get("desarrollo_id")
        dialog = self._create_desarrollo_dialog(f"Editar Desarrollo: {data.get('nombre')}")
        self.inp_d_nombre.set_text(data.get("nombre", ""))
        self.chk_d_activo.setChecked(bool(data.get("activo", False)))
        
        # Set selected delegacion
        del_id = data.get("delegacion_id")
        del_name = self.delegaciones_map.get(del_id, "")
        idx = self.cmb_d_delegacion.combo.findText(del_name)
        if idx >= 0:
            self.cmb_d_delegacion.combo.setCurrentIndex(idx)
            
        self.inp_d_nombre.set_focus()
        dialog.exec()

    def _save_desarrollo(self, dialog: CustomDialog):
        del_name = self.cmb_d_delegacion.combo.currentText()
        # Find delegacion_id from name
        del_id = None
        for d in self.delegaciones_list:
            if d["nombre"] == del_name:
                del_id = d["delegacion_id"]
                break
                
        data = {
            "desarrollo_id": self.current_desarrollo_id,
            "nombre": self.inp_d_nombre.text().strip().upper(),
            "delegacion_id": del_id,
            "activo": self.chk_d_activo.isChecked()
        }
        if not data["nombre"]:
            QMessageBox.warning(self, "Validación", "El Nombre del Desarrollo es obligatorio.")
            return
        if not data["delegacion_id"]:
            QMessageBox.warning(self, "Validación", "La Delegación es obligatoria.")
            return
        try:
            if self.api_client.connect_via_api:
                payload = {"usuario_id": self.current_user_id, "sesion_id": self.current_sesion_id, "data": data}
                self.api_client.request("POST", "/api/admin/save/desarrollos", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    service = AdminService(session)
                    service.save_desarrollo(self.current_user_id, self.current_sesion_id, data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Desarrollo guardado correctamente.")
            dialog.accept()
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # --- GENERAL ---
    def refresh_data(self):
        try:
            # First, fetch delegaciones
            if self.api_client.connect_via_api:
                self.delegaciones_list = self.api_client.request("GET", "/api/admin/data/delegaciones")
                concepts_data = self.api_client.request("GET", "/api/admin/data/conceptos")
                notarias_data = self.api_client.request("GET", "/api/admin/data/notarias")
                colaboradores_data = self.api_client.request("GET", "/api/admin/data/colaboradores")
                desarrollos_data = self.api_client.request("GET", "/api/admin/data/desarrollos")
            else:
                with self.db_connector.get_session() as session:
                    repo = CatalogoRepository(session)
                    
                    dels = repo.get_all_delegaciones_list()
                    self.delegaciones_list = [{"delegacion_id": d.delegacion_id, "nombre": d.nombre} for d in dels]
                    
                    concepts = repo.get_all_conceptos()
                    concepts_data = [{"concepto_id": c.concepto_id, "codigo_portal": c.codigo_portal, "nombre": c.nombre, "alias": c.alias, "activo": c.activo} for c in concepts]
                    
                    notarias = repo.get_all_notarias()
                    notarias_data = [{"notaria_id": n.notaria_id, "nombre": n.nombre, "activo": n.activo} for n in notarias]
                    
                    colabs = repo.get_all_colaboradores()
                    colaboradores_data = [{"colaborador_id": c.colaborador_id, "nombre": c.nombre, "activo": c.activo} for c in colabs]
                    
                    desas = repo.get_all_desarrollos()
                    desarrollos_data = [
                        {"desarrollo_id": d.desarrollo_id, "nombre": d.nombre, "delegacion_id": d.delegacion_id, "delegacion_nombre": d.delegacion.nombre if d.delegacion else "", "activo": d.activo}
                        for d in desas
                    ]
            
            self.delegaciones_map = {d["delegacion_id"]: d["nombre"] for d in self.delegaciones_list}
            
            # Populate tables
            self.tbl_conceptos.populate(concepts_data)
            self.tbl_notarias.populate(notarias_data)
            self.tbl_colaboradores.populate(colaboradores_data)
            self.tbl_desarrollos.populate(desarrollos_data)
            
        except Exception as e:
            print("Error refreshing catalogos:", e)
