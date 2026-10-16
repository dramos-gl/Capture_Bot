"""System Administration View."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel, QMainWindow, QApplication
)
from PySide6.QtCore import Qt, Signal
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
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
from sar.src.ui.views.admin.migration_view import MigrationView
from sar.src.ui.views.admin.bulk_load_view import BulkLoadView
from sar.src.ui.views.admin.update_facturas_view import UpdateFacturasView
from sar.src.ui.views.admin.reservas_proceso_view import ReservasProcesoView
from sar.src.ui.views.admin.regularizar_colaborador_view import RegularizarColaboradorView
from sar.src.ui.views.admin.fusion_lotes_view import FusionLotesView
from sar.src.ui.views.admin.ubicaciones_view import UbicacionesView
try:
    from satc.src.ui.views.satc_catalogs_view import SatcCatalogsView
except ImportError:
    SatcCatalogsView = None
from sar.src.ui.views.admin.help_dialogs import (
    AboutDialog, ShortcutsDialog, SystemDiagnosticsDialog, SupportDialog, UserManualDialog
)


class AdminWindow(QMainWindow):
    """Refactored View to manage system administration using a Standalone Window and Native Menu Bar."""
    
    logout_requested = Signal()
    
    def __init__(self, db_connector, parent=None, current_usuario_id=None, current_sesion_id=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self._logging_out = False
        self.current_usuario_id = current_usuario_id
        self.current_sesion_id = current_sesion_id
        
        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()
        
        # Window setup: Habilitar maximizar, minimizar y dimensionado responsivo
        self.setWindowTitle("SAR - Administración")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            w = min(1080, int(avail.width() * 0.90))
            h = min(720, int(avail.height() * 0.88))
            self.setMinimumSize(880, 540)
            self.resize(w, h)
            x = avail.left() + (avail.width() - w) // 2
            y = avail.top() + (avail.height() - h) // 2
            self.move(x, y)
        else:
            self.setMinimumSize(880, 540)
            self.resize(1000, 680)
        
        # RBAC permissions
        self.user_permissions = set()
        self._load_permissions()
        
        # Top Menu Bar
        self.menu_bar = AdminMenuBar()
        self.menu_bar.view_requested.connect(self._change_view)
        self.menu_bar.logout_clicked.connect(self._handle_logout_action)
        self.menu_bar.exit_clicked.connect(self._handle_exit_action)
        
        # Connect Help Menu Actions
        self.menu_bar.help_manual_requested.connect(self._show_help_manual)
        self.menu_bar.help_shortcuts_requested.connect(self._show_help_shortcuts)
        self.menu_bar.help_diagnostics_requested.connect(self._show_help_diagnostics)
        self.menu_bar.help_support_requested.connect(self._show_help_support)
        self.menu_bar.help_about_requested.connect(self._show_help_about)
        
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
        if self.current_sesion_id:
            return self.current_sesion_id
        main_window = self.window()
        return getattr(main_window, 'current_sesion_id', None)
        
    def _get_current_user(self):
        if self.current_usuario_id:
            return self.current_usuario_id
        try:
            if self.api_client.connect_via_api:
                return 1
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
        main_win = self.window()
        username = getattr(main_win, 'current_username', None) or getattr(self, 'current_username', None)
        if username:
            return f"Usuario: {username}"
        try:
            if self.api_client.connect_via_api:
                users = self.api_client.request("GET", "/api/auth/users")
                for u in users:
                    if u["usuario_id"] == uid:
                        return f"Usuario: {u['username']}"
            else:
                with self.db_connector.get_session() as session:
                    from sar.src.storage.models import Usuario
                    user_obj = session.get(Usuario, uid)
                    if user_obj:
                        return f"Usuario: {user_obj.username}"
        except Exception:
            pass
        return "Usuario: Admin"

    def _load_permissions(self):
        uid = self._get_current_user()
        try:
            if self.api_client.connect_via_api:
                perms_list = self.api_client.request("GET", f"/api/admin/permissions-for-user/{uid}")
                self.user_permissions = {(p[0], p[1]) for p in perms_list}
            else:
                with self.db_connector.get_session() as session:
                    repo = UsuarioRepository(session)
                    perms = repo.get_user_permissions(uid)
                    self.user_permissions = set(perms)
        except Exception:
            pass
            
    def _can_edit(self, modulo: str, submodulo: str = None) -> bool:
        # Verifica CREAR o EDITAR en el submódulo atómico o fallback al módulo macro
        if submodulo:
            if (submodulo, "CREAR") in self.user_permissions or (submodulo, "EDITAR") in self.user_permissions:
                return True
        return (modulo, "CREAR") in self.user_permissions or (modulo, "EDITAR") in self.user_permissions

    def _has_view_access(self, modulo: str, submodulo: str = None) -> bool:
        """Verifica si el usuario cuenta con algún permiso sobre el submódulo o módulo macro (Fail-Closed)."""
        if not self.user_permissions:
            return False
        for (m, a) in self.user_permissions:
            if submodulo and m == submodulo:
                return True
            if m == modulo:
                return True
        return False

    def _setup_views(self):
        """Prepares lazy factories for on-demand view instantiation to optimize startup time and memory."""
        self.instantiated_views = {}
        self.views = self.instantiated_views  # Backward compatibility reference
        
        # Mapping of view keys to factory functions (instantiated only when clicked)
        self.view_factories = {
            "usuarios": lambda: UsersView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("SEGURIDAD", "ADM:USUARIOS")),
            "roles": lambda: RolesView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("SEGURIDAD", "ADM:ROLES")),
            "permisos": lambda: PermissionsView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("SEGURIDAD", "ADM:PERMISOS")),
            "app_modulos": lambda: ModulesView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("SEGURIDAD", "ADM:MODULOS")),
            "acciones": lambda: ActionsView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("SEGURIDAD", "ADM:ACCIONES")),
            "conceptos": lambda: CatalogsView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("CATALOGOS", "ADM:CAT_NEGOCIO")),
            "geografia": lambda: GeographyView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("CATALOGOS", "ADM:GEOGRAFIA")),
            "rfcs": lambda: RfcsView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("CATALOGOS", "ADM:RFCS")),
            "estados": lambda: StatusView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("CATALOGOS", "ADM:ESTADOS")),
            "parametros": lambda: ParametersView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("CONFIGURACION", "ADM:PARAMETROS")),
            "localizadores": lambda: LocalizersView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("CONFIGURACION", "ADM:LOCALIZADORES")),
            "carga_masiva": lambda: BulkLoadView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("PROCESOS_ESPECIALES", "ADM:CARGA_MASIVA")),
            "ubicaciones": lambda: UbicacionesView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("PROCESOS_ESPECIALES", "ADM:UBICACIONES") or self._can_edit("CATALOGOS", "ADM:GEOGRAFIA")),
            "migracion": lambda: MigrationView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("PROCESOS_ESPECIALES", "ADM:MIGRACION")),
            "reserva_masiva": lambda: ReservasProcesoView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("PROCESOS_ESPECIALES", "ADM:RESERVA_MASIVA")),
            "regularizar_colaborador": lambda: RegularizarColaboradorView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("PROCESOS_ESPECIALES", "ADM:RESERVA_MASIVA")),
            "fusion_lotes": lambda: FusionLotesView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("PROCESOS_ESPECIALES", "ADM:FUSION_LOTES") or self._can_edit("PROCESOS_ESPECIALES", "ADM:RESERVA_MASIVA")),
            "update_facturas": lambda: UpdateFacturasView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("PROCESOS_ESPECIALES", "ADM:UPDATE_FACTURAS")),
        }
        
        # Registrar factorías para SATC solo si el subsistema está disponible
        if SatcCatalogsView is not None:
            satc_factory = lambda: SatcCatalogsView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("TRAMITES_VIVIENDA", "CATALOGOS_SATC"))
            for key in ["satc_catalogos", "satc_tipos_tramite", "satc_estados_tramite", "satc_estados_vivienda", "satc_regimenes", "satc_viviendas"]:
                self.view_factories[key] = satc_factory
        
        # Add a lightweight default placeholder view
        self.default_view = QWidget()
        l = QVBoxLayout(self.default_view)
        lbl = CustomLabel("Seleccione una opción del menú superior para comenzar.", variant="body")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(lbl)
        self.stacked_widget.addWidget(self.default_view)
        self.stacked_widget.setCurrentWidget(self.default_view)
        
    def _change_view(self, view_name: str):
        """Loads and switches to the requested view lazily on-demand."""
        view_module_map = {
            "usuarios": ("SEGURIDAD", "ADM:USUARIOS"),
            "roles": ("SEGURIDAD", "ADM:ROLES"),
            "permisos": ("SEGURIDAD", "ADM:PERMISOS"),
            "app_modulos": ("SEGURIDAD", "ADM:MODULOS"),
            "acciones": ("SEGURIDAD", "ADM:ACCIONES"),
            "conceptos": ("CATALOGOS", "ADM:CAT_NEGOCIO"),
            "geografia": ("CATALOGOS", "ADM:GEOGRAFIA"),
            "rfcs": ("CATALOGOS", "ADM:RFCS"),
            "estados": ("CATALOGOS", "ADM:ESTADOS"),
            "parametros": ("CONFIGURACION", "ADM:PARAMETROS"),
            "localizadores": ("CONFIGURACION", "ADM:LOCALIZADORES"),
            "carga_masiva": ("PROCESOS_ESPECIALES", "ADM:CARGA_MASIVA"),
            "ubicaciones": ("PROCESOS_ESPECIALES", "ADM:UBICACIONES"),
            "migracion": ("PROCESOS_ESPECIALES", "ADM:MIGRACION"),
            "reserva_masiva": ("PROCESOS_ESPECIALES", "ADM:RESERVA_MASIVA"),
            "regularizar_colaborador": ("PROCESOS_ESPECIALES", "ADM:RESERVA_MASIVA"),
            "update_facturas": ("PROCESOS_ESPECIALES", "ADM:UPDATE_FACTURAS"),
            "satc_catalogos": ("TRAMITES_VIVIENDA", "CATALOGOS_SATC"),
            "satc_tipos_tramite": ("TRAMITES_VIVIENDA", "CATALOGOS_SATC"),
            "satc_estados_tramite": ("TRAMITES_VIVIENDA", "CATALOGOS_SATC"),
            "satc_estados_vivienda": ("TRAMITES_VIVIENDA", "CATALOGOS_SATC"),
            "satc_regimenes": ("TRAMITES_VIVIENDA", "CATALOGOS_SATC"),
            "satc_viviendas": ("TRAMITES_VIVIENDA", "CATALOGOS_SATC"),
        }
        
        if view_name in view_module_map:
            mod, submod = view_module_map[view_name]
            # Si el usuario es admin o tiene permisos de trámites / catálogos
            if not self._has_view_access(mod, submod) and not self._has_view_access("CATALOGOS") and not self._has_view_access("SEGURIDAD"):
                QMessageBox.warning(
                    self,
                    "Acceso Denegado",
                    f"No cuenta con permisos autorizados para acceder al submódulo '{submod}'."
                )
                return

        # Para los submódulos de satc que comparten la misma vista por pestañas:
        target_tab_idx = None
        target_view_key = view_name
        if view_name in ["satc_tipos_tramite", "satc_estados_tramite", "satc_estados_vivienda", "satc_regimenes", "satc_viviendas"]:
            target_view_key = "satc_catalogos"
            tab_map = {
                "satc_tipos_tramite": 0,
                "satc_estados_tramite": 1,
                "satc_estados_vivienda": 2,
                "satc_regimenes": 3,
                "satc_viviendas": 4
            }
            target_tab_idx = tab_map.get(view_name)

        if target_view_key not in self.instantiated_views and target_view_key in self.view_factories:
            # Instantiate view on-demand for the first time
            view_instance = self.view_factories[target_view_key]()
            self.stacked_widget.addWidget(view_instance)
            self.instantiated_views[target_view_key] = view_instance
            
        if target_view_key in self.instantiated_views:
            view = self.instantiated_views[target_view_key]
            if target_tab_idx is not None and hasattr(view, "tabs"):
                view.tabs.setCurrentIndex(target_tab_idx)
            if hasattr(view, "refresh_data"):
                view.refresh_data()
            self.stacked_widget.setCurrentWidget(view)

    def _handle_logout_action(self):
        reply = QMessageBox.question(
            self,
            "Cerrar Sesión",
            "¿Estás seguro de que deseas cerrar sesión?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._logging_out = True
            self._is_logging_out = True
            self.logout_requested.emit()

    def _handle_exit_action(self):
        self.close()

    def _show_help_manual(self):
        dialog = UserManualDialog(self)
        dialog.exec()

    def _show_help_shortcuts(self):
        dialog = ShortcutsDialog(self)
        dialog.exec()

    def _show_help_diagnostics(self):
        dialog = SystemDiagnosticsDialog(self.db_connector, self)
        dialog.exec()

    def _show_help_support(self):
        dialog = SupportDialog(self)
        dialog.exec()

    def _show_help_about(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def closeEvent(self, event):
        if getattr(self, "_logging_out", False) or getattr(self, "_is_logging_out", False):
            event.accept()
            return
            
        # Verificar si hay procesos en segundo plano activos en las sub-vistas instanciadas
        active_processes = []
        for view_key, view_inst in getattr(self, "instantiated_views", {}).items():
            worker = getattr(view_inst, "worker", None)
            if worker and hasattr(worker, "isRunning") and worker.isRunning():
                active_processes.append(view_key)

        if active_processes:
            warning_reply = QMessageBox.question(
                self,
                "Proceso en Ejecución",
                f"Hay procesos en segundo plano activos en: {', '.join(active_processes)}.\n\n"
                "¿Está seguro de que desea salir? Los procesos incompletos podrían interrumpirse.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if warning_reply != QMessageBox.Yes:
                event.ignore()
                return

        reply = QMessageBox.question(
            self,
            "Confirmar Salida",
            "¿Está seguro de que desea salir del sistema?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._logging_out = True
            self._is_logging_out = True
            if hasattr(self, '_on_logout') and callable(self._on_logout):
                self._on_logout(exit_app=True)
            event.accept()
            QApplication.quit()
        else:
            event.ignore()
