"""Roles Administration Sub-view."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QMessageBox, QCheckBox
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
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.modulos = []
        self.acciones = []
        
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
        self.chk_r_activo = QCheckBox("Rol Activo")
        self.chk_r_activo.setChecked(True)
        
        dialog.add_widget(self.inp_r_codigo)
        dialog.add_widget(self.inp_r_nombre)
        dialog.add_widget(self.chk_r_activo)
        
        from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
        from PySide6.QtCore import Qt
        
        self.group_permisos = QGroupBox("Matriz de Permisos")
        self.group_permisos.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 10px; }")
        self.permisos_layout = QVBoxLayout()
        
        self.matrix_table = QTableWidget()
        self.matrix_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.matrix_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.matrix_table.setColumnCount(len(self.acciones))
        self.matrix_table.setRowCount(len(self.modulos))
        self.matrix_table.setHorizontalHeaderLabels([a["nombre"] for a in self.acciones])
        self.matrix_table.setVerticalHeaderLabels([m["nombre"] for m in self.modulos])
        self.matrix_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        self.checkboxes_matrix = {}  # (mod_id, acc_id): chk
        
        for r_idx, mod in enumerate(self.modulos):
            for c_idx, acc in enumerate(self.acciones):
                chk = QCheckBox()
                if not self.can_edit:
                    chk.setEnabled(False)
                # Centering checkbox in cell
                widget = QWidget()
                l = QHBoxLayout(widget)
                l.addWidget(chk)
                l.setAlignment(Qt.AlignCenter)
                l.setContentsMargins(0,0,0,0)
                self.matrix_table.setCellWidget(r_idx, c_idx, widget)
                self.checkboxes_matrix[(mod["id"], acc["id"])] = chk
                
        self.permisos_layout.addWidget(self.matrix_table)
        self.group_permisos.setLayout(self.permisos_layout)
        dialog.add_widget(self.group_permisos)
        
        # Make dialog wider for the matrix
        dialog.setMinimumWidth(700)
        
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
            with self.db_connector.get_session() as session:
                repo = UsuarioRepository(session)
                permisos = repo.get_permisos_for_rol(self.current_rol_id)
                permisos_set = set(permisos)
                for (m_id, a_id), chk in self.checkboxes_matrix.items():
                    chk.setChecked((m_id, a_id) in permisos_set)
        except Exception as e:
            print("Error loading permissions:", e)
        
        self.inp_r_codigo.set_focus()
        dialog.exec()

    def _save_rol(self, dialog: CustomDialog):
        
        permisos_matrix = [(m_id, a_id) for (m_id, a_id), chk in self.checkboxes_matrix.items() if chk.isChecked()]
        
        data = {
            "rol_id": self.current_rol_id,
            "codigo": self.inp_r_codigo.text().strip(),
            "nombre": self.inp_r_nombre.text().strip(),
            "activo": self.chk_r_activo.isChecked(),
            "permisos_matrix": permisos_matrix
        }
        
        try:
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
            with self.db_connector.get_session() as session:
                repo = UsuarioRepository(session)
                
                # Load matrix headers
                self.modulos = [{"id": m.modulo_id, "nombre": m.nombre} for m in repo.get_all_modulos()]
                self.acciones = [{"id": a.accion_id, "nombre": a.nombre} for a in repo.get_all_acciones()]
                
                items = repo.get_all_roles()
                data = [{"rol_id": i.rol_id, "codigo": i.codigo, "nombre": i.nombre, "activo": i.activo} for i in items]
                self.tbl_roles.populate(data)
        except Exception as e:
            print("Error refreshing roles:", e)
