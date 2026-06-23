"""System Administration View."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel, QMainWindow, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Signal
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.storage.repositories import UsuarioRepository
from sar.src.ui.design_system.components.organisms.gl_admin_menubar import AdminMenuBar
from sar.src.ui.design_system.utils.icons import Icons

from sar.src.ui.views.admin.users_view import UsersView
from sar.src.ui.views.admin.roles_view import RolesView
from sar.src.ui.views.admin.modules_view import ModulesView
from sar.src.ui.views.admin.actions_view import ActionsView
from sar.src.ui.views.admin.permissions_view import PermissionsView
from sar.src.ui.views.admin.catalogs_view import CatalogsView
from sar.src.ui.views.admin.geography_view import GeographyView
from sar.src.ui.views.admin.rfcs_view import RfcsView
from sar.src.ui.views.admin.status_view import StatusView
from sar.src.ui.views.admin.parameters_view import ParametersView
from sar.src.ui.views.admin.localizers_view import LocalizersView


class AdminWindow(QMainWindow):
    """Refactored View to manage system administration using a Standalone Window and Native Menu Bar."""
    
    logout_requested = Signal()
    
    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self._logging_out = False
        
        # Window setup
        self.setWindowTitle("Configuración del Sistema")
        self.resize(1000, 700)
        
        # RBAC permissions
        self.user_permissions = set()
        self._load_permissions()
        
        # Top Menu Bar
        self.menu_bar = AdminMenuBar()
        self.menu_bar.view_requested.connect(self._change_view)
        self.menu_bar.logout_clicked.connect(self._handle_logout_action)
        self.menu_bar.exit_clicked.connect(self._handle_exit_action)
        
        # User Info Widget (Set as corner widget in menu bar)
        self.user_info_widget = QWidget()
        self.user_info_widget.setObjectName("menuUserWidget")
        self.user_info_layout = QHBoxLayout(self.user_info_widget)
        self.user_info_layout.setContentsMargins(10, 6, 10, 6)
        self.user_info_layout.setSpacing(6)
        
        self.lbl_user_icon = QLabel()
        self.lbl_user_icon.setPixmap(Icons.user().pixmap(14, 14))
        self.lbl_user_icon.setStyleSheet("background: transparent;")
        
        self.lbl_username = CustomLabel(self._get_username_string(), variant="body")
        self.lbl_username.setStyleSheet("font-weight: bold; color: #4a5568; font-size: 12px; background: transparent;")
        
        self.user_info_layout.addWidget(self.lbl_user_icon)
        self.user_info_layout.addWidget(self.lbl_username)
        
        self.menu_bar.setCornerWidget(self.user_info_widget, Qt.TopRightCorner)
        self.setMenuBar(self.menu_bar)
        
        # Central Content Setup
        self.central_widget = QWidget()
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(24)
        
        # Title
        self.lbl_title = CustomLabel("Administración del Sistema", variant="header")
        self.layout.addWidget(self.lbl_title)
        
        # Stacked Widget for sub-views
        self.stacked_widget = QStackedWidget()
        self.layout.addWidget(self.stacked_widget)
        
        self.setCentralWidget(self.central_widget)
        
        self._setup_views()
        
    def _get_current_session(self):
        main_window = self.window()
        return getattr(main_window, 'current_sesion_id', None)
        
    def _get_current_user(self):
        try:
            with self.db_connector.get_session() as session:
                from sar.src.storage.models import Sesion
                sesion_id = self._get_current_session()
                if sesion_id:
                    db_sesion = session.get(Sesion, sesion_id)
                    if db_sesion:
                        return db_sesion.usuario_id
        except Exception:
            pass
        return 1
        
    def _get_username_string(self):
        uid = self._get_current_user()
        try:
            with self.db_connector.get_session() as session:
                from sar.src.storage.models import Usuario
                user_obj = session.get(Usuario, uid)
                if user_obj:
                    return f"Usuario: {user_obj.username}"
        except Exception:
            pass
        return "Usuario: admin"

    def _load_permissions(self):
        uid = self._get_current_user()
        try:
            with self.db_connector.get_session() as session:
                repo = UsuarioRepository(session)
                perms = repo.get_user_permissions(uid)
                self.user_permissions = set(perms)
        except Exception:
            pass
            
    def _can_edit(self, modulo: str) -> bool:
        # Dev fallback: If no permissions are loaded for the user or the module is missing, assume True.
        if not self.user_permissions or not any(m == modulo for m, a in self.user_permissions):
            return True
        # Check if CREAR or EDITAR is present for this modulo
        return (modulo, "CREAR") in self.user_permissions or (modulo, "EDITAR") in self.user_permissions

    def _setup_views(self):
        current_user = self._get_current_user()
        current_session = self._get_current_session()
        
        self.views = {
            "usuarios": UsersView(self.db_connector, current_user, current_session, self._can_edit("ADMIN_SEGURIDAD")),
            "roles": RolesView(self.db_connector, current_user, current_session, self._can_edit("ADMIN_SEGURIDAD")),
            "permisos": PermissionsView(self.db_connector, current_user, current_session, self._can_edit("ADMIN_SEGURIDAD")),
            "app_modulos": ModulesView(self.db_connector, current_user, current_session, self._can_edit("ADMIN_SEGURIDAD")),
            "acciones": ActionsView(self.db_connector, current_user, current_session, self._can_edit("ADMIN_SEGURIDAD")),
            "conceptos": CatalogsView(self.db_connector, current_user, current_session, self._can_edit("ADMIN_CATALOGOS")),
            "geografia": GeographyView(self.db_connector, current_user, current_session, self._can_edit("ADMIN_CATALOGOS")),
            "rfcs": RfcsView(self.db_connector, current_user, current_session, self._can_edit("ADMIN_CATALOGOS")),
            "estados": StatusView(self.db_connector, current_user, current_session, self._can_edit("ADMIN_CATALOGOS")),
            "parametros": ParametersView(self.db_connector, current_user, current_session, self._can_edit("ADMIN_CONFIG")),
            "localizadores": LocalizersView(self.db_connector, current_user, current_session, self._can_edit("ADMIN_CONFIG"))
        }
        
        # Add a default placeholder view
        self.default_view = QWidget()
        l = QVBoxLayout(self.default_view)
        lbl = CustomLabel("Seleccione una opción del menú superior.", variant="body")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(lbl)
        self.stacked_widget.addWidget(self.default_view)
        
        for view in self.views.values():
            self.stacked_widget.addWidget(view)
            
        self.stacked_widget.setCurrentWidget(self.default_view)
        
    def _change_view(self, view_name: str):
        if view_name in self.views:
            view = self.views[view_name]
            view.refresh_data()
            self.stacked_widget.setCurrentWidget(view)

    def _handle_logout_action(self):
        self._logging_out = True
        self.logout_requested.emit()

    def _handle_exit_action(self):
        self.close()

    def closeEvent(self, event):
        if getattr(self, "_logging_out", False):
            event.accept()
            return
            
        reply = QMessageBox.question(
            self,
            "Confirmar Salida",
            "¿Está seguro de que desea salir del sistema?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
            QApplication.quit()
        else:
            event.ignore()
