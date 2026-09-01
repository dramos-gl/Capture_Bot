"""Permissions Administration Sub-view."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
    QTableWidget, QHeaderView, QAbstractItemView, QLabel
)
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
from sar.src.ui.design_system.components.atoms.gl_checkbox import CustomCheckBox
from PySide6.QtCore import Qt
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.storage.repositories import UsuarioRepository
from sar.src.services.admin_service import AdminService

class PermissionsView(QWidget):
    def __init__(self, db_connector, current_user_id, current_sesion_id, can_edit, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.current_user_id = current_user_id
        self.current_sesion_id = current_sesion_id
        self.can_edit = can_edit
        
        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()
        
        self.roles = []
        self.modulos = []
        self.acciones = []
        self.checkboxes_matrix = {}  # (mod_id, acc_id): chk
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(16)
        
        self._build_ui()
        self.refresh_data()
        
    def _build_ui(self):
        # Top Bar
        top_bar = QHBoxLayout()
        
        lbl_rol = QLabel("Seleccionar Rol:")
        lbl_rol.setStyleSheet("font-weight: bold;")
        
        self.cmb_roles = QComboBox()
        self.cmb_roles.setFixedWidth(300)
        self.cmb_roles.currentIndexChanged.connect(self._on_rol_selected)
        
        self.btn_save = CustomButton("Guardar Cambios", icon_name="save")
        self.btn_save.clicked.connect(self._save_permissions)
        if not self.can_edit:
            self.btn_save.setEnabled(False)
            
        top_bar.addWidget(lbl_rol)
        top_bar.addWidget(self.cmb_roles)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_save)
        
        self.layout.addLayout(top_bar)
        
        # Matrix Table
        self.matrix_table = QTableWidget()
        self.matrix_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.matrix_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.matrix_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.matrix_table.horizontalHeader().setStretchLastSection(False)
        self.matrix_table.verticalHeader().setVisible(False)
        
        # Styling for table (to match Design System corporate navy header)
        self.matrix_table.setStyleSheet(f"""
            QHeaderView::section {{
                background-color: {Colors.PRIMARY};
                color: white;
                font-weight: bold;
                border: 1px solid {Colors.PRIMARY_LIGHT};
                padding: 8px;
            }}
        """)
        
        self.layout.addWidget(self.matrix_table)
        
    def refresh_data(self):
        try:
            if self.api_client.connect_via_api:
                roles_items = self.api_client.request("GET", "/api/admin/data/roles")
                self.roles = [{"id": r["rol_id"], "nombre": r["nombre"]} for r in roles_items if r.get("activo", True)]
                
                mod_items = self.api_client.request("GET", "/api/admin/data/modulos")
                self.modulos = [{"id": m["id"], "nombre": m["nombre"]} for m in mod_items]
                
                acc_items = self.api_client.request("GET", "/api/admin/data/acciones")
                self.acciones = [{"id": a["id"], "nombre": a["nombre"]} for a in acc_items]
            else:
                with self.db_connector.get_session() as session:
                    repo = UsuarioRepository(session)
                    
                    # Load roles
                    roles_items = repo.get_all_roles()
                    self.roles = [{"id": r.rol_id, "nombre": r.nombre} for r in roles_items if r.activo]
                    
                    # Load matrix headers
                    mod_items = repo.get_all_modulos()
                    self.modulos = [{"id": m.modulo_id, "nombre": m.nombre} for m in mod_items if m.activo]
                    
                    acc_items = repo.get_all_acciones()
                    self.acciones = [{"id": a.accion_id, "nombre": a.nombre} for a in acc_items if a.activo]
                
        except Exception as e:
            print("Error loading initial data:", e)
            return
            
        self._setup_matrix()
        
        # Populate combobox
        self.cmb_roles.blockSignals(True)
        self.cmb_roles.clear()
        for r in self.roles:
            self.cmb_roles.addItem(r["nombre"], r["id"])
        self.cmb_roles.blockSignals(False)
        
        if self.roles:
            self._on_rol_selected(0)
            
    def _setup_matrix(self):
        self.matrix_table.setColumnCount(len(self.acciones) + 1)
        self.matrix_table.setRowCount(len(self.modulos))
        
        headers = ["Módulo"] + [a["nombre"] for a in self.acciones]
        self.matrix_table.setHorizontalHeaderLabels(headers)
        
        # Adjust all columns width to contents to prevent label truncation
        for i in range(len(headers)):
            self.matrix_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        self.checkboxes_matrix.clear()
        
        for r_idx, mod in enumerate(self.modulos):
            # Módulo Name
            from PySide6.QtWidgets import QTableWidgetItem
            item = QTableWidgetItem(f" {mod['nombre']}")
            item.setFlags(Qt.ItemIsEnabled)
            self.matrix_table.setItem(r_idx, 0, item)
            
            # Action Checkboxes
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
                self.matrix_table.setCellWidget(r_idx, c_idx + 1, widget)
                self.checkboxes_matrix[(mod["id"], acc["id"])] = chk
                
    def _on_rol_selected(self, index: int):
        if index < 0: return
        rol_id = self.cmb_roles.itemData(index)
        
        # Uncheck all
        for chk in self.checkboxes_matrix.values():
            chk.setChecked(False)
            
        # Load permissions for this rol
        try:
            if self.api_client.connect_via_api:
                permisos = self.api_client.request("GET", f"/api/admin/permisos-for-rol/{rol_id}")
                permisos_set = {(p[0], p[1]) for p in permisos}
                for (m_id, a_id), chk in self.checkboxes_matrix.items():
                    if (m_id, a_id) in permisos_set:
                        chk.setChecked(True)
            else:
                with self.db_connector.get_session() as session:
                    repo = UsuarioRepository(session)
                    permisos = repo.get_permisos_for_rol(rol_id)
                    permisos_set = set(permisos)
                    for (m_id, a_id), chk in self.checkboxes_matrix.items():
                        if (m_id, a_id) in permisos_set:
                            chk.setChecked(True)
        except Exception as e:
            print("Error loading permissions for rol:", e)
 
    def _save_permissions(self):
        index = self.cmb_roles.currentIndex()
        if index < 0: return
        rol_id = self.cmb_roles.itemData(index)
        
        permisos_matrix = [(m_id, a_id) for (m_id, a_id), chk in self.checkboxes_matrix.items() if chk.isChecked()]
        
        try:
            if self.api_client.connect_via_api:
                # Fetch target rol details to preserve code/name/active fields
                all_roles = self.api_client.request("GET", "/api/admin/data/roles")
                target_rol = next((r for r in all_roles if r["rol_id"] == rol_id), None)
                if not target_rol:
                    raise Exception("Rol no encontrado")
                
                full_data = {
                    "rol_id": rol_id,
                    "codigo": target_rol["codigo"],
                    "nombre": target_rol["nombre"],
                    "activo": target_rol.get("activo", True),
                    "permisos_matrix": permisos_matrix
                }
                
                payload = {
                    "usuario_id": self.current_user_id,
                    "sesion_id": self.current_sesion_id,
                    "data": full_data
                }
                self.api_client.request("POST", "/api/admin/save/roles", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    service = AdminService(session)
                    repo = UsuarioRepository(session)
                    from sar.src.storage.models import Rol
                    rol = session.get(Rol, rol_id)
                    
                    full_data = {
                        "rol_id": rol.rol_id,
                        "codigo": rol.codigo,
                        "nombre": rol.nombre,
                        "activo": rol.activo,
                        "permisos_matrix": permisos_matrix
                    }
                    
                    service.save_rol(self.current_user_id, self.current_sesion_id, full_data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Permisos actualizados correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
