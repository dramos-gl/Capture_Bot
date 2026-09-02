import re
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QFrame, QLabel, 
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QGridLayout
)
from PySide6.QtCore import Qt
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.atoms.gl_input import CustomInput
from sar.src.ui.design_system.components.atoms.gl_checkbox import CustomCheckBox
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
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
        dialog.setMinimumSize(780, 640)
        
        # -------------------------------------------------------------
        # 1. TARJETA: IDENTIFICACIÓN Y CONFIGURACIÓN DEL ROL
        # -------------------------------------------------------------
        card_rol = QFrame(dialog)
        card_rol.setObjectName("card_rol")
        card_rol.setStyleSheet(f"""
            QFrame#card_rol {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay_rol = QVBoxLayout(card_rol)
        lay_rol.setContentsMargins(0, 0, 0, 0)
        lay_rol.setSpacing(8)
        
        lbl_rol = CustomLabel("🛡️ IDENTIFICACIÓN Y CONFIGURACIÓN DEL ROL", variant="subheader")
        lbl_rol.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay_rol.addWidget(lbl_rol)
        
        form_rol = QFormLayout()
        form_rol.setSpacing(8)
        form_rol.setContentsMargins(0, 0, 0, 0)
        
        rol_lay = QHBoxLayout()
        rol_lay.setSpacing(10)
        
        self.inp_r_codigo = CustomInput("Ej. OPERADOR", parent=card_rol)
        self.inp_r_codigo.setMaxLength(30)
        self.inp_r_codigo.textEdited.connect(lambda t: self.inp_r_codigo.setText(t.upper()))
        
        # Compatibility wrappers
        self.inp_r_codigo.text = self.inp_r_codigo.text
        self.inp_r_codigo.set_text = self.inp_r_codigo.setText
        self.inp_r_codigo.set_focus = self.inp_r_codigo.setFocus
        
        lbl_nom = QLabel("Nombre *:")
        lbl_nom.setStyleSheet(f"color: {Colors.TEXT_LIGHT_SECONDARY}; font-size: 12px; font-weight: 500;")
        
        self.inp_r_nombre = CustomInput("Nombre descriptivo del rol", parent=card_rol)
        self.inp_r_nombre.setMaxLength(100)
        self.inp_r_nombre.text = self.inp_r_nombre.text
        self.inp_r_nombre.set_text = self.inp_r_nombre.setText
        
        rol_lay.addWidget(self.inp_r_codigo, 1)
        rol_lay.addWidget(lbl_nom)
        rol_lay.addWidget(self.inp_r_nombre, 2)
        
        form_rol.addRow("Código del Rol *:", rol_lay)
        lay_rol.addLayout(form_rol)
        dialog.add_widget(card_rol)
        
        # -------------------------------------------------------------
        # 2. MATRIZ DE PERMISOS CRUZADOS (Módulos vs Acciones)
        # -------------------------------------------------------------
        card_matrix = QFrame(dialog)
        card_matrix.setObjectName("card_matrix")
        card_matrix.setStyleSheet(f"""
            QFrame#card_matrix {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay_matrix = QVBoxLayout(card_matrix)
        lay_matrix.setContentsMargins(0, 0, 0, 0)
        lay_matrix.setSpacing(8)
        
        lbl_matrix = CustomLabel("⚙️ MATRIZ DE PERMISOS CRUZADOS (MÓDULOS VS ACCIONES)", variant="subheader")
        lbl_matrix.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay_matrix.addWidget(lbl_matrix)
        
        self.matrix_table = QTableWidget(card_matrix)
        self.matrix_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.matrix_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.matrix_table.setColumnCount(len(self.acciones))
        self.matrix_table.setRowCount(len(self.modulos))
        self.matrix_table.setHorizontalHeaderLabels([a["nombre"] for a in self.acciones])
        self.matrix_table.setVerticalHeaderLabels([m["nombre"] for m in self.modulos])
        self.matrix_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.matrix_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.matrix_table.setMinimumHeight(200)
        
        self.checkboxes_matrix = {}
        for r_idx, mod in enumerate(self.modulos):
            for c_idx, acc in enumerate(self.acciones):
                chk = CustomCheckBox()
                if not self.can_edit:
                    chk.setEnabled(False)
                widget = QWidget()
                widget.setStyleSheet("background-color: transparent;")
                l = QHBoxLayout(widget)
                l.addWidget(chk)
                l.setAlignment(Qt.AlignCenter)
                l.setContentsMargins(0, 0, 0, 0)
                self.matrix_table.setCellWidget(r_idx, c_idx, widget)
                self.checkboxes_matrix[(mod["id"], acc["id"])] = chk
                
        lay_matrix.addWidget(self.matrix_table)
        dialog.add_widget(card_matrix)
        
        # -------------------------------------------------------------
        # 3. MÓDULOS DE APLICACIÓN AUTORIZADOS (Acceso Nivel 1)
        # -------------------------------------------------------------
        card_apps = QFrame(dialog)
        card_apps.setObjectName("card_apps")
        card_apps.setStyleSheet(f"""
            QFrame#card_apps {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay_apps = QVBoxLayout(card_apps)
        lay_apps.setContentsMargins(0, 0, 0, 0)
        lay_apps.setSpacing(8)
        
        lbl_apps = CustomLabel("📱 MÓDULOS DE APLICACIÓN AUTORIZADOS (ACCESO NIVEL 1)", variant="subheader")
        lbl_apps.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay_apps.addWidget(lbl_apps)
        
        grid_apps = QGridLayout()
        grid_apps.setContentsMargins(0, 4, 0, 0)
        grid_apps.setHorizontalSpacing(20)
        grid_apps.setVerticalSpacing(8)
        
        self.checkboxes_apps = {}
        for idx, app in enumerate(self.app_modulos):
            chk = CustomCheckBox(app["nombre"])
            if not self.can_edit:
                chk.setEnabled(False)
            row = idx // 2
            col = idx % 2
            grid_apps.addWidget(chk, row, col)
            self.checkboxes_apps[app["id"]] = chk
            
        lay_apps.addLayout(grid_apps)
        dialog.add_widget(card_apps)
        
        # -------------------------------------------------------------
        # 4. ESTADO OPERATIVO (CustomCheckBox)
        # -------------------------------------------------------------
        self.chk_r_activo = CustomCheckBox("Rol de sistema activo para asignación de usuarios", dialog)
        self.chk_r_activo.setChecked(True)
        self.chk_r_activo.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {Colors.TEXT_LIGHT_PRIMARY}; margin: 4px 2px;")
        dialog.add_widget(self.chk_r_activo)
        
        # Validación en tiempo real
        def _validate_rol():
            c_val = self.inp_r_codigo.text().strip()
            n_val = self.inp_r_nombre.text().strip()
            dialog.btn_save.setEnabled(bool(c_val and n_val))
            
        self.inp_r_codigo.textChanged.connect(_validate_rol)
        self.inp_r_nombre.textChanged.connect(_validate_rol)
        _validate_rol()
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_r_codigo.setReadOnly(True)
            self.inp_r_nombre.setReadOnly(True)
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
            "codigo": self.inp_r_codigo.text().strip().upper(),
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
                    
                    self.modulos = [{"id": m.modulo_id, "nombre": m.nombre} for m in repo.get_all_modulos()]
                    self.acciones = [{"id": a.accion_id, "nombre": a.nombre} for a in repo.get_all_acciones()]
                    self.app_modulos = [{"id": am.app_modulo_id, "nombre": am.nombre} for am in repo.get_all_app_modulos()]
                    
                    items = repo.get_all_roles()
                    data = [{"rol_id": i.rol_id, "codigo": i.codigo, "nombre": i.nombre, "activo": i.activo} for i in items]
                    self.tbl_roles.populate(data)
        except Exception as e:
            print("Error refreshing roles:", e)

