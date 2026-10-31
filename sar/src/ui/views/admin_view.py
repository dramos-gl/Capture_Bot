"""System Administration View."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel, QMainWindow, QApplication
)
from PySide6.QtCore import Qt, Signal
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.molecules.gl_card import CustomCard
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
from sar.src.storage.repositories import UsuarioRepository
from sar.src.ui.design_system.components.organisms.gl_admin_menubar import AdminMenuBar
from sar.src.ui.design_system.components.organisms.gl_action_toolbar import GLActionToolbar
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
        
        self.lbl_username = CustomLabel(self._get_username_string(), variant="caption")
        
        self.user_info_layout.addWidget(self.lbl_user_icon)
        self.user_info_layout.addWidget(self.lbl_username)
        
        self.menu_bar.setCornerWidget(self.user_info_widget, Qt.TopRightCorner)
        self.setMenuBar(self.menu_bar)
        
        # Action Toolbar Organism (Barra de herramientas fija superior)
        self.action_toolbar = GLActionToolbar(self)
        self.addToolBar(Qt.TopToolBarArea, self.action_toolbar)
        
        # Conexión de acciones globales de la Toolbar Dinámica
        self.action_toolbar.home_requested.connect(self._on_toolbar_home)
        self.action_toolbar.view_requested.connect(self._change_view)
        
        self.action_toolbar.new_requested.connect(self._on_toolbar_new)
        self.action_toolbar.edit_requested.connect(self._on_toolbar_edit)
        self.action_toolbar.refresh_requested.connect(self._on_toolbar_refresh)
        self.action_toolbar.export_requested.connect(self._on_toolbar_export)
        self.action_toolbar.help_requested.connect(self._on_toolbar_help)
        self.action_toolbar.exit_requested.connect(self._on_toolbar_exit)

        # Acciones operativas para el módulo Importación de Viviendas
        self.action_toolbar.template_requested.connect(self._on_toolbar_template)
        self.action_toolbar.import_file_requested.connect(self._on_toolbar_import_file)
        self.action_toolbar.clean_requested.connect(self._on_toolbar_clean)
        self.action_toolbar.apply_requested.connect(self._on_toolbar_apply)
        
        # Central Content Setup (Maximizando área de trabajo útil)
        self.central_widget = QWidget()
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(0)
        
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
            "notarias": lambda: CatalogsView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("CATALOGOS", "ADM:CAT_NEGOCIO")),
            "colaboradores": lambda: CatalogsView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("CATALOGOS", "ADM:CAT_NEGOCIO")),
            "desarrollos": lambda: CatalogsView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("CATALOGOS", "ADM:CAT_NEGOCIO")),
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
        
        if SatcCatalogsView is not None:
            satc_factory = lambda: SatcCatalogsView(self.db_connector, self._get_current_user(), self._get_current_session(), self._can_edit("TRAMITES_VIVIENDA", "CATALOGOS_SATC"))
            for key in ["satc_catalogos", "satc_tipos_tramite", "satc_estados_tramite", "satc_estados_vivienda", "satc_regimenes", "satc_formatos", "satc_viviendas", "satc_corte_erp"]:
                self.view_factories[key] = satc_factory
        
        # Vista de bienvenida no invasiva inicial
        self.welcome_widget = self._create_welcome_view()
        self.stacked_widget.addWidget(self.welcome_widget)
        self.stacked_widget.setCurrentWidget(self.welcome_widget)

    def _create_welcome_view(self) -> QWidget:
        """Creates an elegant, non-invasive corporate placeholder encouraging the user to select an option."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)
        layout.setContentsMargins(40, 40, 40, 40)

        # Icono corporativo sobrio
        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setPixmap(Icons.get_pixmap("seguridad", size=64, color=Colors.TEXT_LIGHT_MUTED))
        layout.addWidget(icon_lbl)

        # Título principal de bienvenida
        title_lbl = CustomLabel("Bienvenido al Módulo de Administración", variant="header")
        title_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_lbl)

        # Subtítulo explicativo no invasivo
        subtitle_lbl = CustomLabel(
            "Seleccione una opción del menú superior para comenzar a gestionar el sistema.",
            variant="muted"
        )
        subtitle_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle_lbl)

        return widget
        
    def _change_view(self, view_name: str):
        """Loads and switches to the requested view lazily on-demand."""
        view_module_map = {
            "usuarios": ("SEGURIDAD", "ADM:USUARIOS"),
            "roles": ("SEGURIDAD", "ADM:ROLES"),
            "permisos": ("SEGURIDAD", "ADM:PERMISOS"),
            "app_modulos": ("SEGURIDAD", "ADM:MODULOS"),
            "acciones": ("SEGURIDAD", "ADM:ACCIONES"),
            "conceptos": ("CATALOGOS", "ADM:CAT_NEGOCIO"),
            "notarias": ("CATALOGOS", "ADM:CAT_NEGOCIO"),
            "colaboradores": ("CATALOGOS", "ADM:CAT_NEGOCIO"),
            "desarrollos": ("CATALOGOS", "ADM:CAT_NEGOCIO"),
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
            "satc_formatos": ("TRAMITES_VIVIENDA", "CATALOGOS_SATC"),
            "satc_viviendas": ("TRAMITES_VIVIENDA", "CATALOGOS_SATC"),
            "satc_corte_erp": ("TRAMITES_VIVIENDA", "CATALOGOS_SATC"),
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

        # Manejo de pestañas para vistas compartidas (Catálogos de Negocio SAR y Catálogos SATC)
        target_tab_idx = None
        target_view_key = view_name

        if view_name in ["conceptos", "notarias", "colaboradores", "desarrollos"]:
            target_view_key = "conceptos"
            catalog_tab_map = {
                "conceptos": 0,
                "notarias": 1,
                "colaboradores": 2,
                "desarrollos": 3
            }
            target_tab_idx = catalog_tab_map.get(view_name)

        if view_name == "satc_catalogos":
            view_name = "satc_tipos_tramite"

        if view_name in ["satc_tipos_tramite", "satc_estados_tramite", "satc_estados_vivienda", "satc_regimenes", "satc_viviendas", "satc_formatos", "satc_corte_erp"]:
            target_view_key = "satc_catalogos"
            tab_map = {
                "satc_tipos_tramite": 0,
                "satc_estados_tramite": 1,
                "satc_estados_vivienda": 2,
                "satc_regimenes": 3,
                "satc_viviendas": 4,
                "satc_formatos": 5,
                "satc_corte_erp": 6
            }
            target_tab_idx = tab_map.get(view_name)

        # Feedback visual ágil y no intrusivo: cursor de espera durante la preparación de la vista
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if target_view_key not in self.instantiated_views and target_view_key in self.view_factories:
                # Instantiate view on-demand for the first time
                view_instance = self.view_factories[target_view_key]()
                self.stacked_widget.addWidget(view_instance)
                self.instantiated_views[target_view_key] = view_instance
                if hasattr(view_instance, "action_state_changed"):
                    view_instance.action_state_changed.connect(lambda: self._update_toolbar_state(view_instance))
                
            if target_view_key in self.instantiated_views:
                view = self.instantiated_views[target_view_key]
                if target_tab_idx is not None and hasattr(view, "tabs"):
                    view.tabs.setCurrentIndex(target_tab_idx)
                if hasattr(view, "refresh_data"):
                    view.refresh_data()
                self.stacked_widget.setCurrentWidget(view)
                # Mapeo de submódulos a categoría de herramientas en la toolbar
            category_map = {
                "usuarios": "SEGURIDAD",
                "roles": "SEGURIDAD",
                "permisos": "SEGURIDAD",
                "app_modulos": "SEGURIDAD",
                "acciones": "SEGURIDAD",
                "conceptos": "CATALOGOS",
                "notarias": "CATALOGOS",
                "colaboradores": "CATALOGOS",
                "desarrollos": "CATALOGOS",
                "geografia": "CATALOGOS",
                "rfcs": "CATALOGOS",
                "estados": "CATALOGOS",
                "carga_masiva": "PROCESOS",
                "ubicaciones": "PROCESOS",
                "migracion": "PROCESOS",
                "reserva_masiva": "PROCESOS",
                "regularizar_colaborador": "PROCESOS",
                "fusion_lotes": "PROCESOS",
                "update_facturas": "PROCESOS",
                "parametros": "CONFIGURACION",
                "localizadores": "CONFIGURACION",
                "satc_catalogos": "SATC",
                "satc_tipos_tramite": "SATC",
                "satc_estados_tramite": "SATC",
                "satc_estados_vivienda": "SATC",
                "satc_regimenes": "SATC",
                "satc_viviendas": "SATC",
                "satc_formatos": "SATC",
                "satc_corte_erp": "SATC",
            }
            category = category_map.get(view_name, "SATC" if "satc" in view_name else "CATALOGOS")
            self.action_toolbar.set_module_context(category, view_name)
            self._update_toolbar_state(view)
        finally:
            QApplication.restoreOverrideCursor()

    def _get_active_crud_panel(self, view):
        """Helper to find the active CrudTablePanel in single or tabbed views."""
        from sar.src.ui.design_system.components.organisms.gl_crud_table import CrudTablePanel
        
        # 1. Búsqueda directa por atributos conocidos
        candidate_attrs = [
            "tbl_usuarios", "tbl_users", "tbl_roles", "tbl_modulos", "tbl_mod", "tbl_app",
            "tbl_acciones", "tbl_status", "tbl_rfcs", "tbl_parametros", "tbl_params",
            "tbl_localizadores", "tbl_muns", "tbl_dels"
        ]
        for attr in candidate_attrs:
            val = getattr(view, attr, None)
            if isinstance(val, CrudTablePanel):
                return val

        # 2. Vistas con Pestañas (CatalogsView, SatcCatalogsView, etc.)
        if hasattr(view, "tabs"):
            idx = view.tabs.currentIndex()
            # Mapeo según la vista
            if hasattr(view, "tbl_conceptos"):
                panels = [
                    getattr(view, "tbl_conceptos", None),
                    getattr(view, "tbl_notarias", None),
                    getattr(view, "tbl_colaboradores", None),
                    getattr(view, "tbl_desarrollos", None)
                ]
                if 0 <= idx < len(panels) and isinstance(panels[idx], CrudTablePanel):
                    return panels[idx]
            elif hasattr(view, "tbl_tipos"):
                panels = [
                    getattr(view, "tbl_tipos", None),
                    getattr(view, "tbl_est_tramite", None),
                    getattr(view, "tbl_est_vivienda", None),
                    getattr(view, "tbl_regimenes", None),
                    getattr(view, "tbl_viviendas", None),
                    getattr(view, "tbl_formatos", None)
                ]
                if 0 <= idx < len(panels) and isinstance(panels[idx], CrudTablePanel):
                    return panels[idx]

        # 3. Búsqueda dinámica en hijos del widget actual
        if hasattr(view, "findChildren"):
            crud_children = [c for c in view.findChildren(CrudTablePanel) if c.isVisible()]
            if crud_children:
                return crud_children[0]

        return None

    def _update_toolbar_state(self, view=None):
        """Enables or disables toolbar CRUD buttons based on view capabilities and selection."""
        view = view or self.stacked_widget.currentWidget()
        if not view or view == self.welcome_widget:
            self.action_toolbar.set_actions_mode("default")
            self.action_toolbar.set_crud_enabled(False, False)
            self.action_toolbar.act_refresh.setEnabled(False)
            self.action_toolbar.act_export.setEnabled(False)
            return

        self.action_toolbar.act_refresh.setEnabled(True)
        self.action_toolbar.act_export.setEnabled(True)

        # Verificar si la vista activa es el submódulo de Importación de Viviendas o Carga Masiva
        is_viviendas = False
        if hasattr(view, "tabs") and hasattr(view, "tab_import_viviendas"):
            is_viviendas = (view.tabs.currentWidget() == view.tab_import_viviendas)

        from sar.src.ui.views.admin.bulk_load_view import BulkLoadView
        is_carga_masiva = isinstance(view, BulkLoadView)

        if is_viviendas:
            self.action_toolbar.set_actions_mode("viviendas")
            # En modo viviendas, la habilitación de guardar y exportar depende de los registros cargados
            can_apply = getattr(view.btn_v_ejecutar, "isEnabled", lambda: False)()
            can_export = getattr(view.btn_v_exportar_datos, "isEnabled", lambda: False)()
            self.action_toolbar.act_apply.setEnabled(can_apply)
            self.action_toolbar.act_export.setEnabled(can_export)
            return
        elif is_carga_masiva:
            self.action_toolbar.set_actions_mode("carga_masiva")
            can_apply = bool(view.precarga_data and view.precarga_data.get("es_valido") and getattr(view, "can_edit", False))
            can_export = bool(hasattr(view, "table_preview") and view.table_preview.rowCount() > 0)
            self.action_toolbar.act_apply.setEnabled(can_apply)
            self.action_toolbar.act_export.setEnabled(can_export)
            return
        else:
            self.action_toolbar.set_actions_mode("default")
        
        crud = self._get_active_crud_panel(view)
        if crud and hasattr(crud, "btn_add") and hasattr(crud, "btn_edit"):
            can_add = getattr(crud.btn_add, "isVisible", lambda: True)() and crud.btn_add.isEnabled()
            can_edit = bool(crud.table.selectedItems()) if hasattr(crud, "table") else False
            self.action_toolbar.set_crud_enabled(can_add, can_edit)
            
            # Sincronizar dinámicamente cuando cambie la selección en la grilla
            if hasattr(crud, "table"):
                def _sync_edit_state():
                    has_sel = bool(crud.table.selectedItems())
                    self.action_toolbar.act_edit.setEnabled(has_sel)
                crud.table.itemSelectionChanged.connect(_sync_edit_state)
        else:
            can_edit_view = getattr(view, "can_edit", False)
            self.action_toolbar.set_crud_enabled(can_edit_view, False)

    def _on_toolbar_home(self):
        """Navigates back to the welcome screen."""
        self.stacked_widget.setCurrentWidget(self.welcome_widget)
        self.action_toolbar.set_module_context("home")
        self._update_toolbar_state(self.welcome_widget)

    def _on_toolbar_new(self):
        """Triggers create action on the currently visible view/panel."""
        view = self.stacked_widget.currentWidget()
        crud = self._get_active_crud_panel(view)
        if crud:
            can_add = getattr(crud.btn_add, "isVisible", lambda: True)() and crud.btn_add.isEnabled()
            if can_add:
                crud.add_requested.emit()

    def _on_toolbar_edit(self):
        """Triggers edit action on the selected item in the active view/panel."""
        view = self.stacked_widget.currentWidget()
        crud = self._get_active_crud_panel(view)
        if crud and hasattr(crud, "table") and crud.table.selectedItems():
            crud._on_edit_button_clicked()

    def _on_toolbar_template(self):
        """Triggers official template download on the active import view."""
        view = self.stacked_widget.currentWidget()
        if hasattr(view, "_on_v_descargar_plantilla"):
            view._on_v_descargar_plantilla()
        elif hasattr(view, "_on_generar_plantilla"):
            view._on_generar_plantilla()

    def _on_toolbar_import_file(self):
        """Triggers file selection and parsing on the active import view."""
        view = self.stacked_widget.currentWidget()
        if hasattr(view, "_on_v_seleccionar_archivo"):
            view._on_v_seleccionar_archivo()
            self._update_toolbar_state(view)
        elif hasattr(view, "_on_seleccionar_archivo"):
            view._on_seleccionar_archivo()
            self._update_toolbar_state(view)

    def _on_toolbar_clean(self):
        """Cleans and resets filters and data on the active import view."""
        view = self.stacked_widget.currentWidget()
        if hasattr(view, "_on_v_limpiar"):
            view._on_v_limpiar()
            self._update_toolbar_state(view)
        elif hasattr(view, "_limpiar_precarga"):
            view._limpiar_precarga()
            self._update_toolbar_state(view)

    def _on_toolbar_apply(self):
        """Applies parsed records to the database on the active import view."""
        view = self.stacked_widget.currentWidget()
        if hasattr(view, "_on_v_ejecutar_importacion"):
            view._on_v_ejecutar_importacion()
            self._update_toolbar_state(view)
        elif hasattr(view, "_on_ejecutar_carga"):
            view._on_ejecutar_carga()
            self._update_toolbar_state(view)

    def _on_toolbar_refresh(self):
        """Refreshes the active view data."""
        view = self.stacked_widget.currentWidget()
        if hasattr(view, "tabs") and hasattr(view, "tab_import_viviendas") and view.tabs.currentWidget() == view.tab_import_viviendas:
            if hasattr(view, "_on_v_regimen_changed"):
                view._on_v_regimen_changed()
                self._update_toolbar_state(view)
                return
        if hasattr(view, "refresh_data"):
            view.refresh_data()
            self._update_toolbar_state(view)

    def _on_toolbar_export(self):
        """Exports visible table data to CSV or delegates to specialized export handler."""
        view = self.stacked_widget.currentWidget()
        if hasattr(view, "tabs") and hasattr(view, "tab_import_viviendas") and view.tabs.currentWidget() == view.tab_import_viviendas:
            if hasattr(view, "_on_v_exportar_datos"):
                view._on_v_exportar_datos()
                return
        elif hasattr(view, "_on_exportar_datos"):
            view._on_exportar_datos()
            return

        crud = self._get_active_crud_panel(view)
        table = getattr(crud, "table", None) or getattr(view, "table", None) or getattr(view, "table_res", None) or getattr(view, "tbl_viviendas", None)
        if not table or table.rowCount() == 0:
            QMessageBox.information(self, "Exportar", "No hay registros disponibles para exportar.")
            return

        from PySide6.QtWidgets import QFileDialog
        import csv
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Datos", "exportacion_administracion.csv", "CSV (*.csv)")
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                headers = [table.horizontalHeaderItem(c).text() if table.horizontalHeaderItem(c) else f"Col {c}" for c in range(table.columnCount())]
                writer.writerow(headers)
                for r in range(table.rowCount()):
                    row = [table.item(r, c).text() if table.item(r, c) else "" for c in range(table.columnCount())]
                    writer.writerow(row)
            QMessageBox.information(self, "Éxito", f"Datos exportados correctamente:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error al Exportar", f"No se pudo guardar el archivo: {e}")

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

    def _on_toolbar_exit(self):
        """Dispara el cierre de la ventana principal, activando la confirmación de salida de closeEvent."""
        self.close()

    def _on_toolbar_help(self):
        """Abre la guía de ayuda específica contextualizada al módulo activo de la barra de herramientas."""
        active_cat = getattr(self.action_toolbar, "current_category", "") or "SATC"
        self._show_help_manual(module_category=active_cat)

    def _show_help_manual(self, module_category: str = ""):
        dialog = UserManualDialog(self, initial_category=module_category)
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
