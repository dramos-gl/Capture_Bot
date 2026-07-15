"""Point of entry for the new SAR application GUI."""

import sys
import os

# Ensure the root dir is in Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from sar.src.ui.design_system.theme_manager import ThemeManager
from sar.src.ui.views.login_view import LoginView
from sar.src.ui.views.main_view import MainView
from sar.src.storage.db_connector import DatabaseConnector
from sar.src.services.security_service import SecurityService
from sqlalchemy.exc import OperationalError

class MainWindow(QMainWindow):
    """Standalone Login Window acting as the main entry point and router."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SAR - Iniciar Sesión")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.resize(400, 520)
        
        # Initialize Database Connector and API Client wrapper
        self.db_connector = DatabaseConnector()
        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()
        self.current_sesion_id = None
        self._drag_pos = None
        
        # Initialize Login View as the only widget
        self.login_view = LoginView(self.db_connector, self)
        self.setCentralWidget(self.login_view)
        
        # Connect login signal
        self.login_view.login_requested.connect(self._handle_login)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_pos') and self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            diff = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + diff)
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()
        
    def _handle_login(self, username, password, selected_mod_code):
        """Validates credentials using the API switch or direct database connection."""
        try:
            if self.api_client.connect_via_api:
                # ===================================================================
                # RUTA A: Conexión mediante API REST (FastAPI)
                # ===================================================================
                payload = {
                    "username": username,
                    "password": password,
                    "ip_equipo": "127.0.0.1",
                    "equipo_nombre": "Cliente LAN"
                }
                res = self.api_client.request("POST", "/api/auth/login", data=payload)
                
                # Verificar acceso al módulo seleccionado (Nivel 1)
                access_res = self.api_client.request("GET", f"/api/auth/module-access/{res['usuario_id']}/{selected_mod_code}")
                if not access_res.get("has_access", False):
                    self.api_client.request("POST", "/api/auth/logout", data={"sesion_id": res["sesion_id"]})
                    self.login_view.set_login_error("Acceso no autorizado para este módulo.")
                    return
                
                # Almacenar token de sesión de forma segura
                self.api_client.save_token(username, res["access_token"])
                
                self.current_sesion_id = res["sesion_id"]
                self.current_usuario_id = res["usuario_id"]
                self.current_username = username
            else:
                # ===================================================================
                # RUTA B: Conexión Directa a PostgreSQL (Código Original)
                # ===================================================================
                with self.db_connector.get_session() as db_session:
                    security_service = SecurityService(db_session)
                    sesion_obj = security_service.login(username, password)
                    
                    if not sesion_obj:
                        self.login_view.set_login_error("Credenciales inválidas o usuario inactivo")
                        return
                        
                    if not security_service.has_app_module_access(sesion_obj.usuario_id, selected_mod_code):
                        security_service.logout(sesion_obj.sesion_id)
                        self.login_view.set_login_error("Acceso no autorizado para este módulo.")
                        return

                    self.current_sesion_id = sesion_obj.sesion_id
                    self.current_usuario_id = sesion_obj.usuario_id

            # Clear login form
            self.login_view.user_input.set_text("")
            self.login_view.pass_input.set_text("")
            self.login_view.user_input.clear_error()
            self.login_view.pass_input.clear_error()
            
            # Hide login window
            self.hide()
                    
            if selected_mod_code == "ADMIN":
                from sar.src.ui.views.admin_view import AdminWindow
                self.active_module = AdminWindow(
                    self.db_connector,
                    current_usuario_id=self.current_usuario_id,
                    current_sesion_id=self.current_sesion_id
                )
                self.active_module.logout_requested.connect(self._handle_logout)
            elif selected_mod_code == "CTRL_REF":
                from sar.src.ui.views.main_view import MainView
                self.active_module = QMainWindow()
                self.active_module.current_sesion_id = self.current_sesion_id
                self.active_module.current_usuario_id = self.current_usuario_id
                self.active_module.setWindowTitle("SAR - Control de Referencias")
                self.active_module.resize(1100, 750)
                
                # Use the existing MainView (which has the sidebar and dashboard)
                main_view_widget = MainView(ThemeManager, self.db_connector, self.active_module)
                main_view_widget.hide_admin_menu()
                self.active_module.setCentralWidget(main_view_widget)
                
                # Hook up logout for MainView
                main_view_widget.logout_requested.connect(self._handle_logout)
            elif selected_mod_code == "BOT_FACE_A":
                from sar.src.ui.views.bot_view import BotView
                self.active_module = QMainWindow()
                self.active_module.current_sesion_id = self.current_sesion_id
                self.active_module.setWindowTitle("SAR - Bot Face A (Automático)")
                self.active_module.resize(1100, 750)
                
                bot_view_widget = BotView(self.db_connector, self.current_sesion_id, self.current_usuario_id, self.active_module)
                self.active_module.setCentralWidget(bot_view_widget)
                
                # Hook up logout for BotView
                bot_view_widget.logout_requested.connect(self._handle_logout)
            elif selected_mod_code == "BOT_C":
                from sar.src.ui.views.billing_bot_view import BillingBotWindow
                self.active_module = BillingBotWindow(self.db_connector, self.current_sesion_id, self.current_usuario_id)
                self.active_module.current_sesion_id = self.current_sesion_id
                
                # Hook up logout for BillingBotWindow
                self.active_module.logout_requested.connect(self._handle_logout)
            else:
                # Placeholder for other modules
                from PySide6.QtWidgets import QLabel
                self.active_module = QMainWindow()
                self.active_module.setWindowTitle(f"Módulo: {selected_mod_code}")
                self.active_module.resize(800, 600)
                lbl = QLabel(f"Bienvenido al módulo {selected_mod_code}", self.active_module)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.active_module.setCentralWidget(lbl)
                
            if selected_mod_code in ("BOT_FACE_A", "BOT_C"):
                self.active_module.show()
            else:
                self.active_module.showMaximized()
        except OperationalError:
            self.login_view.set_login_error("Error: No se pudo conectar a la base de datos física.")
        except Exception as e:
            self.login_view.set_login_error(f"Error inesperado: {str(e)}")

    def _handle_logout(self):
        """Logs out the user, closes the session and returns to the login screen."""
        if self.current_sesion_id is not None:
            try:
                if self.api_client.connect_via_api:
                    self.api_client.request(
                        "POST", 
                        "/api/auth/logout", 
                        data={"sesion_id": self.current_sesion_id},
                        username=getattr(self, 'current_username', None)
                    )
                    self.api_client.delete_token(getattr(self, 'current_username', ""))
                else:
                    with self.db_connector.get_session() as db_session:
                        security_service = SecurityService(db_session)
                        security_service.logout(self.current_sesion_id)
            except Exception as e:
                print(f"Error al registrar logout: {e}")
            finally:
                self.current_sesion_id = None
                
        # Close the active module and show login
        if hasattr(self, 'active_module'):
            self.active_module.close()
        self.show()


def main():
    # Register explicit AppUserModelID for Windows Taskbar grouping/icon representation
    if sys.platform == "win32":
        try:
            import ctypes
            myappid = "dramos.gl.sar.system.v2"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            print("Error setting AppUserModelID:", e)

    app = QApplication(sys.argv)
    
    # Apply global window icon
    icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "src", "ui", "assets", "sar_logo.png"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Apply theme
    ThemeManager.apply_theme(app, is_dark=False)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
