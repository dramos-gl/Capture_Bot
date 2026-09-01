"""Login Screen View."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QApplication, QPushButton
from PySide6.QtCore import Signal, Qt, QSize
from sar.src.ui.design_system.components import CustomLabel, LabeledInput, CustomButton, CustomComboBox
from sar.src.ui.design_system.utils.icons import Icons
from sar.src.storage.repositories import UsuarioRepository

class LoginView(QWidget):
    """Modern Login View matching the requested mockup."""
    
    # Emits username, password, app_modulo_code on successful validation
    login_requested = Signal(str, str, str)
    
    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        
        # Outer layout to center everything
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.center_layout = QVBoxLayout()
        self.center_layout.setContentsMargins(0, 0, 0, 0)
        self.center_layout.setSpacing(16)
        self.center_layout.setAlignment(Qt.AlignCenter)
        
        # Shield Icon
        self.icon_lbl = QLabel(self)
        self.icon_lbl.setPixmap(Icons.shield_lock().pixmap(48, 48))
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.center_layout.addWidget(self.icon_lbl)
        
        # Header title
        self.title_lbl = CustomLabel("SAR Login", variant="header")
        self.title_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #1e3a5f;")
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.center_layout.addWidget(self.title_lbl)
        
        # Subtitle
        mod_lbl = CustomLabel("Módulo de Acceso", variant="body")
        mod_lbl.setStyleSheet("font-size: 14px; color: #4a5568;")
        mod_lbl.setAlignment(Qt.AlignCenter)
        self.center_layout.addWidget(mod_lbl)
        
        self.center_layout.addSpacing(6)
        
        # Module Selection
        self.cb_modulo = CustomComboBox(self)
        self.cb_modulo.setPlaceholderText("Seleccionar un módulo")
        self.cb_modulo_original_stylesheet = self.cb_modulo.styleSheet()
        self._load_modules()
        self.center_layout.addWidget(self.cb_modulo)
        
        # Module Error Label
        self.modulo_error_lbl = CustomLabel("", variant="muted", parent=self)
        self.modulo_error_lbl.setVisible(False)
        self.center_layout.addWidget(self.modulo_error_lbl)
        
        # Clear module error when selection changes
        self.cb_modulo.currentIndexChanged.connect(self._clear_modulo_error)
        
        # Labeled inputs
        self.user_input = LabeledInput(label_text="Usuario", icon_name="user", parent=self)
        self.pass_input = LabeledInput(label_text="Contraseña", is_password=True, icon_name="lock", parent=self)
        
        self.center_layout.addWidget(self.user_input)
        self.center_layout.addWidget(self.pass_input)
        
        self.center_layout.addSpacing(8)
        
        # Buttons Layout
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setSpacing(12)
        
        # Login button
        self.login_btn = CustomButton("Iniciar Sesión", is_secondary=False, parent=self)
        self.login_btn.clicked.connect(self._on_login_clicked)
        self.btn_layout.addWidget(self.login_btn)
        
        # Cancel button
        self.cancel_btn = CustomButton("Cancelar", is_secondary=False, parent=self)
        self.cancel_btn.setObjectName("dangerBtn") # Override to use danger color
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        self.btn_layout.addWidget(self.cancel_btn)
        
        self.center_layout.addLayout(self.btn_layout)
        
        # Keyboard Navigation & Focus Flow
        self.user_input.input.returnPressed.connect(self.pass_input.set_focus)
        self.pass_input.input.returnPressed.connect(self._on_login_clicked)
        
        self.login_btn.setAutoDefault(True)
        self.cancel_btn.setAutoDefault(True)
        
        # Explicit Tab Order
        QWidget.setTabOrder(self.cb_modulo, self.user_input.input)
        QWidget.setTabOrder(self.user_input.input, self.pass_input.input)
        QWidget.setTabOrder(self.pass_input.input, self.login_btn)
        QWidget.setTabOrder(self.login_btn, self.cancel_btn)
        
        # We put center_layout inside a container widget to control width
        self.form_container = QWidget(self)
        self.form_container.setFixedWidth(340)
        self.form_container.setLayout(self.center_layout)
        
        self.main_layout.addStretch()
        self.main_layout.addWidget(self.form_container)
        self.main_layout.addStretch()
        
    def _load_modules(self):
        try:
            from sar.src.storage.api_client import APIClient
            api_client = APIClient()
            if api_client.connect_via_api:
                # Load modules via API
                modulos = api_client.request("GET", "/api/auth/modules")
                for mod in modulos:
                    self.cb_modulo.addItem(mod["nombre"], userData=mod["codigo"])
            else:
                # Load modules via database
                with self.db_connector.get_session() as session:
                    repo = UsuarioRepository(session)
                    modulos = repo.get_all_app_modulos()
                    for mod in modulos:
                        self.cb_modulo.addItem(mod.nombre, userData=mod.codigo)
        except Exception as e:
            import traceback
            import sys
            import os
            import datetime
            try:
                if getattr(sys, 'frozen', False):
                    log_dir = os.path.dirname(sys.executable)
                else:
                    log_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
                log_path = os.path.join(log_dir, "sar_error.log")
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"\n[{datetime.datetime.now()}] Error loading modules: {str(e)}\n")
                    traceback.print_exc(file=f)
            except Exception:
                pass
            print("Error loading modules:", e)
        
    def _clear_modulo_error(self):
        self.modulo_error_lbl.setText("")
        self.modulo_error_lbl.setVisible(False)
        self.cb_modulo.setStyleSheet(self.cb_modulo_original_stylesheet)
        
    def _on_login_clicked(self):
        """Validates simple layout fields and emits request."""
        username = self.user_input.text().strip()
        password = self.pass_input.text().strip()
        selected_mod_code = self.cb_modulo.currentData()
        
        has_error = False
        
        if not selected_mod_code:
            self.modulo_error_lbl.setText("Debe seleccionar un módulo")
            self.modulo_error_lbl.set_error_style(True)
            self.modulo_error_lbl.setVisible(True)
            self.cb_modulo.setStyleSheet(self.cb_modulo_original_stylesheet + "\nQComboBox { border: 1px solid #DC2626; }")
            has_error = True
        else:
            self._clear_modulo_error()
            
        if not username:
            self.user_input.show_error("El usuario es requerido")
            has_error = True
        else:
            self.user_input.clear_error()
            
        if not password:
            self.pass_input.show_error("La contraseña es requerida")
            has_error = True
        else:
            self.pass_input.clear_error()
            
        if not has_error:
            self.login_requested.emit(username, password, selected_mod_code)
            
    def _on_cancel_clicked(self):
        """Exits application directly on cancel without prompt."""
        QApplication.quit()

    def set_login_error(self, message: str):
        """Shows login general error on password field."""
        self.pass_input.show_error(message)
