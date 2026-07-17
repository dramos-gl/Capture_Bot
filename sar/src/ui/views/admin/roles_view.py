"""Roles Administration Sub-view."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QMessageBox
from sar.src.ui.design_system.components.atoms.gl_checkbox import CustomCheckBox
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.molecules.gl_labeled_input import LabeledInput
from sar.src.ui.design_system.components.organisms.gl_crud_table import CrudTablePanel
from sar.src.ui.design_system.components.organisms.gl_dialog import CustomDialog
from sar.src.storage.repositories import UsuarioRepository
from sar.src.services.admin_service import AdminService

class RolesView(QWidget):
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
        
        self.modulos = []
        self.acciones = []
        self.app_modulos = []
        
        self._build_ui()
        self.refresh_data()
        
    def _build_ui(self):
        self.tbl_roles = CrudTablePanel("Roles del Sistema")
        self.tbl_roles.setup_table(["ID", "Código", "Nombre", "Estado"], ["rol_id", "codigo", "nombre", "activo"])
        self.tbl_roles.add_requested.connect(self._on_new_rol)
        self.tbl_roles.edit_requested.connect(self._on_edit_rol)
        self.layout.addWidget(self.tbl_roles)
        
        self.current_rol_id = None
        self.tbl_roles.btn_add.setVisible(self.can_edit)
        
    def _create_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        
        self.inp_r_codigo = LabeledInput("Código del Rol")
        self.inp_r_nombre = LabeledInput("Nombre")
        self.chk_r_activo = CustomCheckBox("Rol Activo")
        self.chk_r_activo.setChecked(True)
        
        dialog.add_widget(self.inp_r_codigo)
        dialog.add_widget(self.inp_r_nombre)
        dialog.add_widget(self.chk_r_activo)
        
        from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QGridLayout
        from PySide6.QtCore import Qt
        
        self.group_permisos = QGroupBox("Matriz de Permisos")
        self.group_permisos.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #e2e8f0; border-radius: 8px; margin-top: 10px; padding-top: 24px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        self.permisos_layout = QVBoxLayout()
        
        self.matrix_table = QTableWidget()
        self.matrix_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.matrix_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.matrix_table.setColumnCount(len(self.acciones))
        self.matrix_table.setRowCount(len(self.modulos))
        self.matrix_table.setHorizontalHeaderLabels([a["nombre"] for a in self.acciones])
        self.matrix_table.setVerticalHeaderLabels([m["nombre"] for m in self.modulos])
        self.matrix_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.matrix_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.matrix_table.setMinimumHeight(220)
        
        self.checkboxes_matrix = {}  # (mod_id, acc_id): chk
        
        for r_idx, mod in enumerate(self.modulos):
            for c_idx, acc in enumerate(self.acciones):
                chk = CustomCheckBox()
                if not self.can_edit:
                    chk.setEnabled(False)
                # Centering checkbox in cell
                widget = QWidget()
                widget.setStyleSheet("background-color: transparent;")
                l = QHBoxLayout(widget)
                l.addWidget(chk)
                l.setAlignment(Qt.AlignCenter)
                l.setContentsMargins(0,0,0,0)
                self.matrix_table.setCellWidget(r_idx, c_idx, widget)
                self.checkboxes_matrix[(mod["id"], acc["id"])] = chk
                
        self.permisos_layout.addWidget(self.matrix_table)
        self.group_permisos.setLayout(self.permisos_layout)
        dialog.add_widget(self.group_permisos)
        
        # Módulos de Aplicación (Nivel 1)
        self.group_apps = QGroupBox("Módulos de Aplicación Autorizados (Acceso Nivel 1)")
        self.group_apps.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #e2e8f0; border-radius: 8px; margin-top: 10px; padding-top: 24px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        self.apps_layout = QGridLayout()
        self.apps_layout.setContentsMargins(15, 10, 15, 10)
        self.apps_layout.setHorizontalSpacing(20)
        self.apps_layout.setVerticalSpacing(10)
        self.checkboxes_apps = {}  # app_modulo_id: chk
        
        for idx, app in enumerate(self.app_modulos):
            chk = CustomCheckBox(app["nombre"])
            if not self.can_edit:
                chk.setEnabled(False)
            row = idx // 2
            col = idx % 2
            self.apps_layout.addWidget(chk, row, col)
            self.checkboxes_apps[app["id"]] = chk
            
        self.group_apps.setLayout(self.apps_layout)
        dialog.add_widget(self.group_apps)
        
        # Make dialog wider and taller for the matrix and proper spacing
        dialog.setMinimumSize(780, 640)
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_r_codigo.input.setReadOnly(True)
            self.inp_r_nombre.input.setReadOnly(True)
            self.chk_r_activo.setEnabled(False)
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_rol(dialog))
        
        return dialog

    def _on_new_rol(self):
        self.current_rol_id = None
        dialog = self._create_dialog("Nuevo Rol")
        self.inp_r_codigo.set_focus()
        dialog.exec()
        
    def _on_edit_rol(self, data: dict):
        self.current_rol_id = data.get("rol_id")
        dialog = self._create_dialog(f"Editar Rol: {data.get('nombre')}")
        
        self.inp_r_codigo.set_text(data.get("codigo", ""))
        self.inp_r_nombre.set_text(data.get("nombre", ""))
        self.chk_r_activo.setChecked(bool(data.get("activo", False)))
        
        # Load permissions
        try:
            if self.api_client.connect_via_api:
                permisos = self.api_client.request("GET", f"/api/admin/permisos-for-rol/{self.current_rol_id}")
                permisos_set = {(p[0], p[1]) for p in permisos}
                for (m_id, a_id), chk in self.checkboxes_matrix.items():
                    chk.setChecked((m_id, a_id) in permisos_set)
                    
                app_mods = self.api_client.request("GET", f"/api/admin/app-modulos-for-rol/{self.current_rol_id}")
                app_mods_set = set(app_mods)
                for am_id, chk in self.checkboxes_apps.items():
                    chk.setChecked(am_id in app_mods_set)
            else:
                with self.db_connector.get_session() as session:
                    repo = UsuarioRepository(session)
                    permisos = repo.get_permisos_for_rol(self.current_rol_id)
                    permisos_set = set(permisos)
                    for (m_id, a_id), chk in self.checkboxes_matrix.items():
                        chk.setChecked((m_id, a_id) in permisos_set)
                        
                    # Cargar módulos de aplicación autorizados
                    app_mods = repo.get_app_modulos_for_rol(self.current_rol_id)
                    app_mods_set = set(app_mods)
                    for am_id, chk in self.checkboxes_apps.items():
                        chk.setChecked(am_id in app_mods_set)
        except Exception as e:
            print("Error loading permissions:", e)
        
        self.inp_r_codigo.set_focus()
        dialog.exec()

    def _save_rol(self, dialog: CustomDialog):
        
        permisos_matrix = [(m_id, a_id) for (m_id, a_id), chk in self.checkboxes_matrix.items() if chk.isChecked()]
        app_modulo_ids = [am_id for am_id, chk in self.checkboxes_apps.items() if chk.isChecked()]
        
        data = {
            "rol_id": self.current_rol_id,
            "codigo": self.inp_r_codigo.text().strip(),
            "nombre": self.inp_r_nombre.text().strip(),
            "activo": self.chk_r_activo.isChecked(),
            "permisos_matrix": permisos_matrix,
            "app_modulo_ids": app_modulo_ids
        }
        
        try:
            if self.api_client.connect_via_api:
                payload = {
                    "usuario_id": self.current_user_id,
                    "sesion_id": self.current_sesion_id,
                    "data": data
                }
                self.api_client.request("POST", "/api/admin/save/roles", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    service = AdminService(session)
                    service.save_rol(self.current_user_id, self.current_sesion_id, data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Rol guardado correctamente.")
            dialog.accept()
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def refresh_data(self):
        try:
            if self.api_client.connect_via_api:
                self.modulos = self.api_client.request("GET", "/api/admin/data/modulos")
                self.acciones = self.api_client.request("GET", "/api/admin/data/acciones")
                self.app_modulos = self.api_client.request("GET", "/api/admin/data/app_modulos")
                
                roles = self.api_client.request("GET", "/api/admin/data/roles")
                self.tbl_roles.populate(roles)
            else:
                with self.db_connector.get_session() as session:
                    repo = UsuarioRepository(session)
                    
                    # Load matrix headers
                    self.modulos = [{"id": m.modulo_id, "nombre": m.nombre} for m in repo.get_all_modulos()]
                    self.acciones = [{"id": a.accion_id, "nombre": a.nombre} for a in repo.get_all_acciones()]
                    self.app_modulos = [{"id": am.app_modulo_id, "nombre": am.nombre} for am in repo.get_all_app_modulos()]
                    
                    items = repo.get_all_roles()
                    data = [{"rol_id": i.rol_id, "codigo": i.codigo, "nombre": i.nombre, "activo": i.activo} for i in items]
                    self.tbl_roles.populate(data)
        except Exception as e:
            print("Error refreshing roles:", e)
