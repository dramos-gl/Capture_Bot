import re
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QFrame, QLabel
from PySide6.QtCore import Qt
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.atoms.gl_input import CustomInput
from sar.src.ui.design_system.components.atoms.gl_checkbox import CustomCheckBox
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
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
        headers = ["ID", "RFC", "Razón Social", "Alias", "Calle", "No. Ext.", "No. Int.", "Colonia", "CP", "Localidad", "Municipio", "Estado", "Activo"]
        keys = ["rfc_id", "rfc", "razon_social", "alias", "calle", "no_exterior", "no_interior", "colonia", "codigo_postal", "localidad", "municipio", "estado", "activo"]
        self.tbl_rfcs.setup_table(headers, keys)
        self.tbl_rfcs.add_requested.connect(self._on_new)
        self.tbl_rfcs.edit_requested.connect(self._on_edit)
        self.layout.addWidget(self.tbl_rfcs)
        
        self.current_rfc_id = None
        self.tbl_rfcs.btn_add.setVisible(self.can_edit)
        
    def _create_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        dialog.setMinimumWidth(660)
        
        # -------------------------------------------------------------
        # 1. TARJETA: IDENTIFICACIÓN FISCAL (QFormLayout estático como Asignar Derecho)
        # -------------------------------------------------------------
        card_fiscal = QFrame(dialog)
        card_fiscal.setObjectName("card_fiscal")
        card_fiscal.setStyleSheet(f"""
            QFrame#card_fiscal {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay_fiscal = QVBoxLayout(card_fiscal)
        lay_fiscal.setContentsMargins(0, 0, 0, 0)
        lay_fiscal.setSpacing(8)
        
        lbl_fiscal = CustomLabel("🏢 DATOS DE IDENTIFICACIÓN FISCAL", variant="subheader")
        lbl_fiscal.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay_fiscal.addWidget(lbl_fiscal)
        
        form_fiscal = QFormLayout()
        form_fiscal.setSpacing(8)
        form_fiscal.setContentsMargins(0, 0, 0, 0)
        
        # Fila 1: RFC y Alias en horizontal
        rfc_lay = QHBoxLayout()
        rfc_lay.setSpacing(10)
        
        self.txt_rfc = CustomInput("Ej. XAXX010101000", parent=card_fiscal)
        self.txt_rfc.setMaxLength(13)
        self.txt_rfc.textEdited.connect(lambda t: self.txt_rfc.setText(t.upper()))
        
        lbl_alias = QLabel("Alias / Comercial:")
        lbl_alias.setStyleSheet(f"color: {Colors.TEXT_LIGHT_SECONDARY}; font-size: 12px; font-weight: 500;")
        self.txt_alias = CustomInput("Nombre comercial o sucursal (Opcional)", parent=card_fiscal)
        self.txt_alias.setMaxLength(100)
        
        rfc_lay.addWidget(self.txt_rfc, 2)
        rfc_lay.addWidget(lbl_alias)
        rfc_lay.addWidget(self.txt_alias, 3)
        form_fiscal.addRow("RFC *:", rfc_lay)
        
        # Error label sutil para RFC
        self.lbl_rfc_err = QLabel("", card_fiscal)
        self.lbl_rfc_err.setStyleSheet(f"color: {Colors.ERROR}; font-size: 11px; font-weight: bold;")
        self.lbl_rfc_err.setVisible(False)
        form_fiscal.addRow("", self.lbl_rfc_err)
        
        # Fila 2: Razón Social Completa
        self.txt_rs = CustomInput("Razón social completa o denominación social", parent=card_fiscal)
        self.txt_rs.setMaxLength(500)
        form_fiscal.addRow("Razón Social *:", self.txt_rs)
        
        lay_fiscal.addLayout(form_fiscal)
        dialog.add_widget(card_fiscal)
        
        # -------------------------------------------------------------
        # 2. TARJETA: DOMICILIO FISCAL Y LOCALIZACIÓN
        # -------------------------------------------------------------
        card_domicilio = QFrame(dialog)
        card_domicilio.setObjectName("card_domicilio")
        card_domicilio.setStyleSheet(f"""
            QFrame#card_domicilio {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay_domicilio = QVBoxLayout(card_domicilio)
        lay_domicilio.setContentsMargins(0, 0, 0, 0)
        lay_domicilio.setSpacing(8)
        
        lbl_domicilio = CustomLabel("📍 DOMICILIO FISCAL Y LOCALIZACIÓN", variant="subheader")
        lbl_domicilio.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay_domicilio.addWidget(lbl_domicilio)
        
        form_dom = QFormLayout()
        form_dom.setSpacing(8)
        form_dom.setContentsMargins(0, 0, 0, 0)
        
        # Fila 1: Calle
        self.txt_calle = CustomInput("Nombre de la calle o avenida", parent=card_domicilio)
        form_dom.addRow("Calle / Avenida:", self.txt_calle)
        
        # Fila 2: Números Ext / Int
        num_lay = QHBoxLayout()
        num_lay.setSpacing(10)
        self.txt_ext = CustomInput("No. Ext / SM / Mz", parent=card_domicilio)
        lbl_int = QLabel("No. Int:")
        lbl_int.setStyleSheet(f"color: {Colors.TEXT_LIGHT_SECONDARY}; font-size: 12px; font-weight: 500;")
        self.txt_int = CustomInput("Piso / Depto (Opcional)", parent=card_domicilio)
        num_lay.addWidget(self.txt_ext, 1)
        num_lay.addWidget(lbl_int)
        num_lay.addWidget(self.txt_int, 1)
        form_dom.addRow("Números Ext/Int:", num_lay)
        
        # Fila 3: Colonia y Código Postal
        col_lay = QHBoxLayout()
        col_lay.setSpacing(10)
        self.txt_col = CustomInput("Colonia o fraccionamiento", parent=card_domicilio)
        lbl_cp = QLabel("C.P.:")
        lbl_cp.setStyleSheet(f"color: {Colors.TEXT_LIGHT_SECONDARY}; font-size: 12px; font-weight: 500;")
        self.txt_cp = CustomInput("77500", parent=card_domicilio)
        self.txt_cp.setMaxLength(10)
        col_lay.addWidget(self.txt_col, 3)
        col_lay.addWidget(lbl_cp)
        col_lay.addWidget(self.txt_cp, 1)
        form_dom.addRow("Colonia / C.P.:", col_lay)
        
        # Fila 4: Localidad, Municipio y Estado
        geo_lay = QHBoxLayout()
        geo_lay.setSpacing(8)
        self.txt_loc = CustomInput("Localidad / Ciudad", parent=card_domicilio)
        self.txt_mun = CustomInput("Municipio", parent=card_domicilio)
        self.txt_est = CustomInput("Estado", parent=card_domicilio)
        geo_lay.addWidget(self.txt_loc, 1)
        geo_lay.addWidget(self.txt_mun, 1)
        geo_lay.addWidget(self.txt_est, 1)
        form_dom.addRow("Ubicación Geo:", geo_lay)
        
        lay_domicilio.addLayout(form_dom)
        dialog.add_widget(card_domicilio)
        
        # -------------------------------------------------------------
        # 3. ESTADO OPERATIVO (CustomCheckBox)
        # -------------------------------------------------------------
        self.chk_activo = CustomCheckBox("Contribuyente activo para facturación y generación de referencias", dialog)
        self.chk_activo.setChecked(True)
        self.chk_activo.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {Colors.TEXT_LIGHT_PRIMARY}; margin: 4px 2px;")
        dialog.add_widget(self.chk_activo)
        
        # Validación en tiempo real
        def _validate_fields():
            rfc_val = self.txt_rfc.text().strip().upper()
            rs_val = self.txt_rs.text().strip()
            
            is_rfc_valid = True
            if rfc_val:
                if not re.match(r"^[A-ZÑ&]{3,4}\d{6}[A-Z\d]{3}$", rfc_val):
                    self.lbl_rfc_err.setText("Formato de RFC inválido (12 caracteres P. Moral o 13 P. Física).")
                    self.lbl_rfc_err.setVisible(True)
                    self.txt_rfc.setStyleSheet(f"border: 1px solid {Colors.ERROR};")
                    is_rfc_valid = False
                else:
                    self.lbl_rfc_err.setVisible(False)
                    self.txt_rfc.setStyleSheet("")
            else:
                self.lbl_rfc_err.setVisible(False)
                self.txt_rfc.setStyleSheet("")
                
            can_save = bool(rfc_val and rs_val and is_rfc_valid)
            dialog.btn_save.setEnabled(can_save)
            
        self.txt_rfc.textChanged.connect(_validate_fields)
        self.txt_rs.textChanged.connect(_validate_fields)
        _validate_fields()
        
        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.txt_rfc.setReadOnly(True)
            self.txt_rs.setReadOnly(True)
            self.txt_alias.setReadOnly(True)
            self.txt_calle.setReadOnly(True)
            self.txt_ext.setReadOnly(True)
            self.txt_int.setReadOnly(True)
            self.txt_col.setReadOnly(True)
            self.txt_cp.setReadOnly(True)
            self.txt_loc.setReadOnly(True)
            self.txt_mun.setReadOnly(True)
            self.txt_est.setReadOnly(True)
            self.chk_activo.setEnabled(False)
            
        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save(dialog))
        return dialog
 
    def _on_new(self):
        self.current_rfc_id = None
        dialog = self._create_dialog("Nuevo Contribuyente (RFC)")
        self.txt_rfc.setFocus()
        dialog.exec()
        
    def _on_edit(self, data: dict):
        self.current_rfc_id = data.get("rfc_id")
        dialog = self._create_dialog(f"Editar Contribuyente: {data.get('rfc')}")
        
        self.txt_rfc.setText(data.get("rfc", "") or "")
        self.txt_rs.setText(data.get("razon_social", "") or "")
        self.txt_alias.setText(data.get("alias", "") or "")
        self.txt_calle.setText(data.get("calle", "") or "")
        self.txt_ext.setText(data.get("no_exterior", "") or "")
        self.txt_int.setText(data.get("no_interior", "") or "")
        self.txt_col.setText(data.get("colonia", "") or "")
        self.txt_cp.setText(data.get("codigo_postal", "") or "")
        self.txt_loc.setText(data.get("localidad", "") or "")
        self.txt_mun.setText(data.get("municipio", "") or "")
        self.txt_est.setText(data.get("estado", "") or "")
        self.chk_activo.setChecked(bool(data.get("activo", False)))
        
        self.txt_rfc.setFocus()
        dialog.exec()
 
    def _save(self, dialog: CustomDialog):
        data = {
            "rfc_id": self.current_rfc_id,
            "rfc": self.txt_rfc.text().strip().upper(),
            "razon_social": self.txt_rs.text().strip(),
            "alias": self.txt_alias.text().strip() or None,
            "calle": self.txt_calle.text().strip(),
            "no_exterior": self.txt_ext.text().strip(),
            "no_interior": self.txt_int.text().strip(),
            "colonia": self.txt_col.text().strip(),
            "codigo_postal": self.txt_cp.text().strip(),
            "localidad": self.txt_loc.text().strip(),
            "municipio": self.txt_mun.text().strip(),
            "estado": self.txt_est.text().strip(),
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
                        "alias": i.alias,
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

