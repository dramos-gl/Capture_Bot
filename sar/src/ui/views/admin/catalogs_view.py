"""Catalogs Administration Sub-view."""

import re
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QFrame, QLabel, QTabWidget
from PySide6.QtCore import Qt
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.atoms.gl_input import CustomInput
from sar.src.ui.design_system.components.atoms.gl_checkbox import CustomCheckBox
from sar.src.ui.design_system.components.molecules.gl_combo_box import CustomComboBox
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
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
        dialog.setMinimumWidth(560)
        
        card_c = QFrame(dialog)
        card_c.setObjectName("card_c")
        card_c.setStyleSheet(f"""
            QFrame#card_c {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay_c = QVBoxLayout(card_c)
        lay_c.setContentsMargins(0, 0, 0, 0)
        lay_c.setSpacing(8)
        
        lbl_c = CustomLabel("📋 CONFIGURACIÓN DE CONCEPTO", variant="subheader")
        lbl_c.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay_c.addWidget(lbl_c)
        
        form_c = QFormLayout()
        form_c.setSpacing(8)
        form_c.setContentsMargins(0, 0, 0, 0)
        
        self.inp_c_codigo_portal = CustomInput("Ej. CONC_001 (Opcional)", parent=card_c)
        self.inp_c_codigo_portal.setMaxLength(30)
        self.inp_c_codigo_portal.text = self.inp_c_codigo_portal.text
        self.inp_c_codigo_portal.set_text = self.inp_c_codigo_portal.setText
        
        self.inp_c_nombre = CustomInput("Nombre descriptivo del concepto", parent=card_c)
        self.inp_c_nombre.setMaxLength(100)
        self.inp_c_nombre.text = self.inp_c_nombre.text
        self.inp_c_nombre.set_text = self.inp_c_nombre.setText
        self.inp_c_nombre.set_focus = self.inp_c_nombre.setFocus
        
        self.inp_c_alias = CustomInput("Alias para búsquedas (Opcional)", parent=card_c)
        self.inp_c_alias.setMaxLength(20)
        self.inp_c_alias.text = self.inp_c_alias.text
        self.inp_c_alias.set_text = self.inp_c_alias.setText
        
        form_c.addRow("Código Portal:", self.inp_c_codigo_portal)
        form_c.addRow("Nombre Concepto *:", self.inp_c_nombre)
        form_c.addRow("Alias / Corto:", self.inp_c_alias)
        lay_c.addLayout(form_c)
        dialog.add_widget(card_c)
        
        self.chk_c_activo = CustomCheckBox("Concepto activo para solicitudes", dialog)
        self.chk_c_activo.setChecked(True)
        self.chk_c_activo.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {Colors.TEXT_LIGHT_PRIMARY}; margin: 4px 2px;")
        dialog.add_widget(self.chk_c_activo)
        
        def _validate_c():
            dialog.btn_save.setEnabled(bool(self.inp_c_nombre.text().strip()))
        self.inp_c_nombre.textChanged.connect(_validate_c)
        _validate_c()
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_c_codigo_portal.setReadOnly(True)
            self.inp_c_nombre.setReadOnly(True)
            self.inp_c_alias.setReadOnly(True)
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
        dialog.setMinimumWidth(560)
        
        card_n = QFrame(dialog)
        card_n.setObjectName("card_n")
        card_n.setStyleSheet(f"""
            QFrame#card_n {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay_n = QVBoxLayout(card_n)
        lay_n.setContentsMargins(0, 0, 0, 0)
        lay_n.setSpacing(8)
        
        lbl_n = CustomLabel("🏛️ DATOS DE LA NOTARÍA", variant="subheader")
        lbl_n.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay_n.addWidget(lbl_n)
        
        form_n = QFormLayout()
        form_n.setSpacing(8)
        form_n.setContentsMargins(0, 0, 0, 0)
        
        self.inp_n_nombre = CustomInput("Nombre de la notaría (ej. NOTARÍA 12 CANCÚN)", parent=card_n)
        self.inp_n_nombre.setMaxLength(100)
        self.inp_n_nombre.textEdited.connect(lambda t: self.inp_n_nombre.setText(t.upper()))
        self.inp_n_nombre.text = self.inp_n_nombre.text
        self.inp_n_nombre.set_text = self.inp_n_nombre.setText
        self.inp_n_nombre.set_focus = self.inp_n_nombre.setFocus
        
        self.inp_n_alias = CustomInput("Alias corto para reportes (Opcional)", parent=card_n)
        self.inp_n_alias.setMaxLength(50)
        self.inp_n_alias.text = self.inp_n_alias.text
        self.inp_n_alias.set_text = self.inp_n_alias.setText
        
        form_n.addRow("Nombre Notaría *:", self.inp_n_nombre)
        form_n.addRow("Alias / Notario:", self.inp_n_alias)
        lay_n.addLayout(form_n)
        dialog.add_widget(card_n)
        
        self.chk_n_activo = CustomCheckBox("Notaría activa para asignación de referencias", dialog)
        self.chk_n_activo.setChecked(True)
        self.chk_n_activo.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {Colors.TEXT_LIGHT_PRIMARY}; margin: 4px 2px;")
        dialog.add_widget(self.chk_n_activo)
        
        def _validate_n():
            dialog.btn_save.setEnabled(bool(self.inp_n_nombre.text().strip()))
        self.inp_n_nombre.textChanged.connect(_validate_n)
        _validate_n()
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_n_nombre.setReadOnly(True)
            self.inp_n_alias.setReadOnly(True)
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
        dialog.setMinimumWidth(540)
        
        card_col = QFrame(dialog)
        card_col.setObjectName("card_col")
        card_col.setStyleSheet(f"""
            QFrame#card_col {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay_col = QVBoxLayout(card_col)
        lay_col.setContentsMargins(0, 0, 0, 0)
        lay_col.setSpacing(8)
        
        lbl_col = CustomLabel("👥 DATOS DE COLABORADOR / SOLICITANTE", variant="subheader")
        lbl_col.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay_col.addWidget(lbl_col)
        
        form_col = QFormLayout()
        form_col.setSpacing(8)
        form_col.setContentsMargins(0, 0, 0, 0)
        
        self.inp_col_nombre = CustomInput("Nombre completo del colaborador", parent=card_col)
        self.inp_col_nombre.setMaxLength(100)
        self.inp_col_nombre.textEdited.connect(lambda t: self.inp_col_nombre.setText(t.upper()))
        self.inp_col_nombre.text = self.inp_col_nombre.text
        self.inp_col_nombre.set_text = self.inp_col_nombre.setText
        self.inp_col_nombre.set_focus = self.inp_col_nombre.setFocus
        
        form_col.addRow("Nombre Completo *:", self.inp_col_nombre)
        lay_col.addLayout(form_col)
        dialog.add_widget(card_col)
        
        self.chk_col_activo = CustomCheckBox("Colaborador activo para asignaciones", dialog)
        self.chk_col_activo.setChecked(True)
        self.chk_col_activo.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {Colors.TEXT_LIGHT_PRIMARY}; margin: 4px 2px;")
        dialog.add_widget(self.chk_col_activo)
        
        def _validate_col():
            dialog.btn_save.setEnabled(bool(self.inp_col_nombre.text().strip()))
        self.inp_col_nombre.textChanged.connect(_validate_col)
        _validate_col()
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_col_nombre.setReadOnly(True)
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
        dialog.setMinimumWidth(540)
        
        card_d = QFrame(dialog)
        card_d.setObjectName("card_d")
        card_d.setStyleSheet(f"""
            QFrame#card_d {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay_d = QVBoxLayout(card_d)
        lay_d.setContentsMargins(0, 0, 0, 0)
        lay_d.setSpacing(8)
        
        lbl_d = CustomLabel("🏗️ DATOS DEL DESARROLLO / PROYECTO", variant="subheader")
        lbl_d.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay_d.addWidget(lbl_d)
        
        form_d = QFormLayout()
        form_d.setSpacing(8)
        form_d.setContentsMargins(0, 0, 0, 0)
        
        self.inp_d_nombre = CustomInput("Nombre del desarrollo o proyecto inmobiliario", parent=card_d)
        self.inp_d_nombre.setMaxLength(100)
        self.inp_d_nombre.textEdited.connect(lambda t: self.inp_d_nombre.setText(t.upper()))
        self.inp_d_nombre.text = self.inp_d_nombre.text
        self.inp_d_nombre.set_text = self.inp_d_nombre.setText
        self.inp_d_nombre.set_focus = self.inp_d_nombre.setFocus
        
        form_d.addRow("Nombre Desarrollo *:", self.inp_d_nombre)
        lay_d.addLayout(form_d)
        dialog.add_widget(card_d)
        
        self.chk_d_activo = CustomCheckBox("Desarrollo activo en inventario", dialog)
        self.chk_d_activo.setChecked(True)
        self.chk_d_activo.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {Colors.TEXT_LIGHT_PRIMARY}; margin: 4px 2px;")
        dialog.add_widget(self.chk_d_activo)
        
        def _validate_d():
            dialog.btn_save.setEnabled(bool(self.inp_d_nombre.text().strip()))
        self.inp_d_nombre.textChanged.connect(_validate_d)
        _validate_d()
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_d_nombre.setReadOnly(True)
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
        dialog.setMinimumWidth(580)
        
        card_de = QFrame(dialog)
        card_de.setObjectName("card_de")
        card_de.setStyleSheet(f"""
            QFrame#card_de {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay_de = QVBoxLayout(card_de)
        lay_de.setContentsMargins(0, 0, 0, 0)
        lay_de.setSpacing(8)
        
        lbl_de = CustomLabel("🏢 ASOCIACIÓN EMPRESA (RFC) Y DELEGACIÓN", variant="subheader")
        lbl_de.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay_de.addWidget(lbl_de)
        
        form_de = QFormLayout()
        form_de.setSpacing(8)
        form_de.setContentsMargins(0, 0, 0, 0)
        
        rfc_names = [f"{r['rfc']} - {r['razon_social']}" for r in self.rfcs_list]
        self.cmb_de_rfc = CustomComboBox(card_de)
        self.cmb_de_rfc.addItems(rfc_names)
        
        del_names = [d["nombre"] for d in getattr(self, 'delegaciones_activas_list', self.delegaciones_list)]
        self.cmb_de_delegacion = CustomComboBox(card_de)
        self.cmb_de_delegacion.addItems(del_names)
        
        # Compatibility wrappers
        self.cmb_de_rfc.combo = self.cmb_de_rfc
        self.cmb_de_delegacion.combo = self.cmb_de_delegacion
        
        form_de.addRow("Empresa (RFC) *:", self.cmb_de_rfc)
        form_de.addRow("Delegación *:", self.cmb_de_delegacion)
        lay_de.addLayout(form_de)
        dialog.add_widget(card_de)
        
        self.chk_de_default = CustomCheckBox("Empresa predeterminada para este desarrollo (es_default)", dialog)
        self.chk_de_activo = CustomCheckBox("Asociación empresa-desarrollo activa", dialog)
        self.chk_de_activo.setChecked(True)
        
        dialog.add_widget(self.chk_de_default)
        dialog.add_widget(self.chk_de_activo)
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.cmb_de_rfc.setEnabled(False)
            self.cmb_de_delegacion.setEnabled(False)
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
        
        rfc_display = f"{data.get('rfc_nombre', '')} - {data.get('rfc_razon_social', '')}"
        idx = self.cmb_de_rfc.findText(rfc_display)
        if idx >= 0:
            self.cmb_de_rfc.setCurrentIndex(idx)
            
        del_name = data.get("delegacion_nombre")
        idx2 = self.cmb_de_delegacion.findText(del_name)
        if idx2 < 0 and del_name:
            self.cmb_de_delegacion.addItem(del_name)
            idx2 = self.cmb_de_delegacion.findText(del_name)
        if idx2 >= 0:
            self.cmb_de_delegacion.setCurrentIndex(idx2)
            
        self.chk_de_default.setChecked(bool(data.get("es_default", False)))
        self.chk_de_activo.setChecked(bool(data.get("activo", False)))
        dialog.exec()

    def _save_desarrollo_empresa(self, dialog: CustomDialog):
        rfc_text = self.cmb_de_rfc.currentText()
        rfc_id = None
        for r in self.rfcs_list:
            display = f"{r['rfc']} - {r['razon_social']}"
            if display == rfc_text:
                rfc_id = r["rfc_id"]
                break
                
        del_name = self.cmb_de_delegacion.currentText()
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
                        } for de in items
                    ]
            self.tbl_desarrollo_empresas.populate(data)
        except Exception as e:
            print("Error refreshing desarrollo_empresas:", e)

    def refresh_data(self):
        try:
            if self.api_client.connect_via_api:
                self.delegaciones_list = self.api_client.request("GET", "/api/admin/data/delegaciones")
                self.rfcs_list = self.api_client.request("GET", "/api/admin/data/rfcs")
                
                concepts_data = self.api_client.request("GET", "/api/admin/data/conceptos")
                notarias_data = self.api_client.request("GET", "/api/admin/data/notarias")
                colaboradores_data = self.api_client.request("GET", "/api/admin/data/colaboradores")
                desarrollos_data = self.api_client.request("GET", "/api/admin/data/desarrollos")
            else:
                with self.db_connector.get_session() as session:
                    repo = CatalogoRepository(session)
                    items_del = repo.get_all_delegaciones_list()
                    self.delegaciones_list = [{"delegacion_id": d.delegacion_id, "nombre": d.nombre, "activo": d.activo} for d in items_del]
                    
                    items_rfc = repo.get_all_rfcs()
                    self.rfcs_list = [{"rfc_id": r.rfc_id, "rfc": r.rfc, "razon_social": r.razon_social, "activo": r.activo} for r in items_rfc]
                    
                    items_c = repo.get_all_conceptos()
                    concepts_data = [{"concepto_id": i.concepto_id, "codigo_portal": i.codigo_portal, "nombre": i.nombre, "alias": i.alias, "activo": i.activo} for i in items_c]
                    
                    items_n = repo.get_all_notarias()
                    notarias_data = [{"notaria_id": i.notaria_id, "nombre": i.nombre, "alias": i.alias, "activo": i.activo} for i in items_n]
                    
                    items_col = repo.get_all_colaboradores()
                    colaboradores_data = [{"colaborador_id": i.colaborador_id, "nombre": i.nombre, "activo": i.activo} for i in items_col]
                    
                    items_d = repo.get_all_desarrollos()
                    desarrollos_data = [{"desarrollo_id": i.desarrollo_id, "nombre": i.nombre, "activo": i.activo} for i in items_d]
                    
            self.delegaciones_activas_list = [d for d in self.delegaciones_list if d.get("activo", True)]
            self.delegaciones_map = {d["delegacion_id"]: d["nombre"] for d in self.delegaciones_list}
            
            self.tbl_conceptos.populate(concepts_data)
            self.tbl_notarias.populate(notarias_data)
            self.tbl_colaboradores.populate(colaboradores_data)
            self.tbl_desarrollos.populate(desarrollos_data)
            
            self.refresh_desarrollo_empresas()
        except Exception as e:
            print("Error refreshing catalogos:", e)
