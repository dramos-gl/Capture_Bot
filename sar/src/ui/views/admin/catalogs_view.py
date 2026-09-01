"""Catalogs Administration Sub-view."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QCheckBox, QTabWidget
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
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
        self.rfcs_list = []
        
        self.current_desarrollo_id = None
        self.current_desarrollo_empresa_id = None
        
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
        self.tbl_notarias.setup_table(["ID", "Nombre", "Alias", "Estado"], ["notaria_id", "nombre", "alias", "activo"])
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
        
        # 4. Desarrollos Tab (horizontal split layout)
        self.tab_desarrollos = QWidget()
        lay_desarrollos = QHBoxLayout(self.tab_desarrollos)
        lay_desarrollos.setContentsMargins(0, 0, 0, 0)
        lay_desarrollos.setSpacing(16)
        
        # Left Table: Developments
        self.tbl_desarrollos = CrudTablePanel("Catálogo de Desarrollos")
        self.tbl_desarrollos.setup_table(["ID", "Nombre", "Estado"], ["desarrollo_id", "nombre", "activo"])
        self.tbl_desarrollos.add_requested.connect(self._on_new_desarrollo)
        self.tbl_desarrollos.edit_requested.connect(self._on_edit_desarrollo)
        self.tbl_desarrollos.item_selected.connect(self._on_desarrollo_selected)
        self.tbl_desarrollos.btn_add.setVisible(self.can_edit)
        self.tbl_desarrollos.btn_edit.setVisible(self.can_edit)
        lay_desarrollos.addWidget(self.tbl_desarrollos, stretch=6)
        
        # Right Table: Development-Companies Mapping
        self.tbl_desarrollo_empresas = CrudTablePanel("Empresas Asociadas")
        self.tbl_desarrollo_empresas.setup_table(["ID", "Empresa (RFC)", "Delegación", "Default", "Estado"], ["desarrollo_empresa_id", "rfc_nombre", "delegacion_nombre", "es_default", "activo"])
        self.tbl_desarrollo_empresas.add_requested.connect(self._on_new_desarrollo_empresa)
        self.tbl_desarrollo_empresas.edit_requested.connect(self._on_edit_desarrollo_empresa)
        self.tbl_desarrollo_empresas.btn_add.setVisible(self.can_edit)
        self.tbl_desarrollo_empresas.btn_edit.setVisible(self.can_edit)
        self.tbl_desarrollo_empresas.setEnabled(False)
        lay_desarrollos.addWidget(self.tbl_desarrollo_empresas, stretch=4)
        
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
        self.inp_n_alias = LabeledInput("Alias (Opcional)")
        self.chk_n_activo = QCheckBox("Notaría Activa")
        self.chk_n_activo.setChecked(True)
        
        dialog.add_widget(self.inp_n_nombre)
        dialog.add_widget(self.inp_n_alias)
        dialog.add_widget(self.chk_n_activo)
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_n_nombre.input.setReadOnly(True)
            self.inp_n_alias.input.setReadOnly(True)
            self.chk_n_activo.setEnabled(False)
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_notaria(dialog))
        return dialog

    def _on_new_notaria(self):
        self.current_notaria_id = None
        dialog = self._create_notaria_dialog("Nueva Notaría")
        self.inp_n_nombre.set_text("")
        self.inp_n_alias.set_text("")
        self.inp_n_nombre.set_focus()
        dialog.exec()

    def _on_edit_notaria(self, data: dict):
        self.current_notaria_id = data.get("notaria_id")
        dialog = self._create_notaria_dialog(f"Editar Notaría: {data.get('nombre')}")
        self.inp_n_nombre.set_text(data.get("nombre", ""))
        self.inp_n_alias.set_text(data.get("alias", ""))
        self.chk_n_activo.setChecked(bool(data.get("activo", False)))
        self.inp_n_nombre.set_focus()
        dialog.exec()

    def _save_notaria(self, dialog: CustomDialog):
        data = {
            "notaria_id": self.current_notaria_id,
            "nombre": self.inp_n_nombre.text().strip().upper(),
            "alias": self.inp_n_alias.text().strip(),
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
        self.chk_col_activo = QCheckBox("Colaborador Activa")
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
        
        self.chk_d_activo = QCheckBox("Desarrollo Activo")
        self.chk_d_activo.setChecked(True)
        
        dialog.add_widget(self.inp_d_nombre)
        dialog.add_widget(self.chk_d_activo)
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_d_nombre.input.setReadOnly(True)
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
        self.inp_d_nombre.set_focus()
        dialog.exec()

    def _save_desarrollo(self, dialog: CustomDialog):
        data = {
            "desarrollo_id": self.current_desarrollo_id,
            "nombre": self.inp_d_nombre.text().strip().upper(),
            "activo": self.chk_d_activo.isChecked()
        }
        if not data["nombre"]:
            QMessageBox.warning(self, "Validación", "El Nombre del Desarrollo es obligatorio.")
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

    def _on_desarrollo_selected(self, data: dict):
        self.current_desarrollo_id = data.get("desarrollo_id")
        self.tbl_desarrollo_empresas.setEnabled(True)
        self.tbl_desarrollo_empresas.lbl_title.setText(f"Empresas: {data.get('nombre')}")
        self.refresh_desarrollo_empresas()

    # --- DESARROLLO EMPRESAS ---
    def _create_desarrollo_empresa_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        
        rfc_names = [f"{r['rfc']} - {r['razon_social']}" for r in self.rfcs_list]
        self.cmb_de_rfc = LabeledComboBox("Empresa", rfc_names)
        
        del_names = [d["nombre"] for d in self.delegaciones_activas_list]
        self.cmb_de_delegacion = LabeledComboBox("Delegación", del_names)
        
        self.chk_de_default = QCheckBox("Empresa Predeterminada (es_default)")
        self.chk_de_activo = QCheckBox("Asociación Activa")
        self.chk_de_activo.setChecked(True)
        
        dialog.add_widget(self.cmb_de_rfc)
        dialog.add_widget(self.cmb_de_delegacion)
        dialog.add_widget(self.chk_de_default)
        dialog.add_widget(self.chk_de_activo)
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.cmb_de_rfc.combo.setEnabled(False)
            self.cmb_de_delegacion.combo.setEnabled(False)
            self.chk_de_default.setEnabled(False)
            self.chk_de_activo.setEnabled(False)
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_desarrollo_empresa(dialog))
        return dialog

    def _on_new_desarrollo_empresa(self):
        self.current_desarrollo_empresa_id = None
        dialog = self._create_desarrollo_empresa_dialog("Asociar Nueva Empresa")
        dialog.exec()

    def _on_edit_desarrollo_empresa(self, data: dict):
        self.current_desarrollo_empresa_id = data.get("desarrollo_empresa_id")
        dialog = self._create_desarrollo_empresa_dialog("Editar Asociación")
        
        # Set current RFC
        rfc_display = f"{data.get('rfc_nombre', '')} - {data.get('rfc_razon_social', '')}"
        idx = self.cmb_de_rfc.combo.findText(rfc_display)
        if idx >= 0:
            self.cmb_de_rfc.combo.setCurrentIndex(idx)
            
        # Set current Delegación
        del_name = data.get("delegacion_nombre")
        idx2 = self.cmb_de_delegacion.combo.findText(del_name)
        if idx2 < 0 and del_name:
            self.cmb_de_delegacion.combo.addItem(del_name)
            idx2 = self.cmb_de_delegacion.combo.findText(del_name)
        if idx2 >= 0:
            self.cmb_de_delegacion.combo.setCurrentIndex(idx2)
            
        self.chk_de_default.setChecked(bool(data.get("es_default", False)))
        self.chk_de_activo.setChecked(bool(data.get("activo", False)))
        dialog.exec()

    def _save_desarrollo_empresa(self, dialog: CustomDialog):
        rfc_text = self.cmb_de_rfc.combo.currentText()
        rfc_id = None
        for r in self.rfcs_list:
            display = f"{r['rfc']} - {r['razon_social']}"
            if display == rfc_text:
                rfc_id = r["rfc_id"]
                break
                
        del_name = self.cmb_de_delegacion.combo.currentText()
        del_id = None
        for d in self.delegaciones_list:
            if d["nombre"] == del_name:
                del_id = d["delegacion_id"]
                break
                
        data = {
            "desarrollo_empresa_id": self.current_desarrollo_empresa_id,
            "desarrollo_id": self.current_desarrollo_id,
            "rfc_id": rfc_id,
            "delegacion_id": del_id,
            "es_default": self.chk_de_default.isChecked(),
            "activo": self.chk_de_activo.isChecked()
        }
        if not data["rfc_id"]:
            QMessageBox.warning(self, "Validación", "La Empresa es obligatoria.")
            return
        if not data["delegacion_id"]:
            QMessageBox.warning(self, "Validación", "La Delegación es obligatoria.")
            return
        try:
            if self.api_client.connect_via_api:
                payload = {"usuario_id": self.current_user_id, "sesion_id": self.current_sesion_id, "data": data}
                self.api_client.request("POST", "/api/admin/save/desarrollo_empresas", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    service = AdminService(session)
                    service.save_desarrollo_empresa(self.current_user_id, self.current_sesion_id, data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Asociación de empresa guardada correctamente.")
            dialog.accept()
            self.refresh_desarrollo_empresas()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def refresh_desarrollo_empresas(self):
        if not self.current_desarrollo_id:
            self.tbl_desarrollo_empresas.populate([])
            return
        try:
            if self.api_client.connect_via_api:
                data = self.api_client.request("GET", "/api/admin/data/desarrollo_empresas", data={"desarrollo_id": self.current_desarrollo_id})
            else:
                with self.db_connector.get_session() as session:
                    repo = CatalogoRepository(session)
                    items = repo.get_desarrollo_empresas(self.current_desarrollo_id)
                    data = [
                        {
                            "desarrollo_empresa_id": de.desarrollo_empresa_id,
                            "desarrollo_id": de.desarrollo_id,
                            "rfc_id": de.rfc_id,
                            "rfc_nombre": de.rfc.rfc if de.rfc else "",
                            "rfc_razon_social": de.rfc.razon_social if de.rfc else "",
                            "delegacion_id": de.delegacion_id,
                            "delegacion_nombre": de.delegacion.nombre if de.delegacion else "",
                            "es_default": de.es_default,
                            "activo": de.activo
                        }
                        for de in items
                    ]
            self.tbl_desarrollo_empresas.populate(data)
        except Exception as e:
            print("Error refreshing desarrollo empresas:", e)

    # --- GENERAL ---
    def refresh_data(self):
        try:
            if self.api_client.connect_via_api:
                self.delegaciones_list = self.api_client.request("GET", "/api/admin/data/delegaciones")
                self.delegaciones_activas_list = [d for d in self.delegaciones_list if d.get("activo", True)]
                self.rfcs_list = self.api_client.request("GET", "/api/admin/data/rfcs")
                concepts_data = self.api_client.request("GET", "/api/admin/data/conceptos")
                notarias_data = self.api_client.request("GET", "/api/admin/data/notarias")
                colaboradores_data = self.api_client.request("GET", "/api/admin/data/colaboradores")
                desarrollos_data = self.api_client.request("GET", "/api/admin/data/desarrollos")
            else:
                with self.db_connector.get_session() as session:
                    repo = CatalogoRepository(session)
                    
                    dels = repo.get_all_delegaciones_list()
                    self.delegaciones_list = [{"delegacion_id": d.delegacion_id, "nombre": d.nombre, "activo": d.activo} for d in dels]
                    self.delegaciones_activas_list = [d for d in self.delegaciones_list if d.get("activo", True)]
                    
                    rfcs = repo.get_all_rfcs()
                    self.rfcs_list = [{"rfc_id": r.rfc_id, "rfc": r.rfc, "razon_social": r.razon_social} for r in rfcs]
                    
                    concepts = repo.get_all_conceptos()
                    concepts_data = [{"concepto_id": c.concepto_id, "codigo_portal": c.codigo_portal, "nombre": c.nombre, "alias": c.alias, "activo": c.activo} for c in concepts]
                    
                    notarias = repo.get_all_notarias()
                    notarias_data = [{"notaria_id": n.notaria_id, "nombre": n.nombre, "alias": n.alias, "activo": n.activo} for n in notarias]
                    
                    colabs = repo.get_all_colaboradores()
                    colaboradores_data = [{"colaborador_id": c.colaborador_id, "nombre": c.nombre, "activo": c.activo} for c in colabs]
                    
                    desas = repo.get_all_desarrollos()
                    desarrollos_data = [
                        {"desarrollo_id": d.desarrollo_id, "nombre": d.nombre, "activo": d.activo}
                        for d in desas
                    ]
            
            self.delegaciones_map = {d["delegacion_id"]: d["nombre"] for d in self.delegaciones_list}
            
            # Populate tables
            self.tbl_conceptos.populate(concepts_data)
            self.tbl_notarias.populate(notarias_data)
            self.tbl_colaboradores.populate(colaboradores_data)
            self.tbl_desarrollos.populate(desarrollos_data)
            
            # Refresh details table if there's any active development selected
            self.refresh_desarrollo_empresas()
            
        except Exception as e:
            print("Error refreshing catalogos:", e)
