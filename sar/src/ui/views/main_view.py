"""Main shell coordinator view."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QLabel
from PySide6.QtCore import Signal, Qt
from sar.src.ui.design_system.components import NavigationSidebar, CustomLabel

class MainView(QWidget):
    """Main Application Window layout binding Sidebar navigation and stack views."""
    
    # Signal emitted when logout is requested from sidebar
    logout_requested = Signal()
    
    def __init__(self, theme_manager, db_connector, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.db_connector = db_connector
        self.is_dark_theme = self.theme_manager.is_dark_active()
        self.admin_window = None
        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = NavigationSidebar(self)
        self.sidebar.set_username(self._get_username_string())
        self.layout.addWidget(self.sidebar)
        
        # Main content area container (Stacked widget + Bottom right footer)
        self.content_area = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        # Stacked layout for main views
        self.stacked_widget = QStackedWidget(self.content_area)
        self.content_layout.addWidget(self.stacked_widget, stretch=1)
        
        # Discreet right-aligned footer bar
        self.footer_bar = QWidget(self.content_area)
        self.footer_bar_layout = QHBoxLayout(self.footer_bar)
        self.footer_bar_layout.setContentsMargins(16, 2, 20, 6)
        self.footer_bar_layout.setSpacing(0)
        
        self.lbl_global_footer = QLabel("Sistema de Administración de Derechos | DRR | v1.0.0", self.footer_bar)
        self.lbl_global_footer.setObjectName("globalAppFooter")
        self.lbl_global_footer.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_global_footer.setStyleSheet("color: #94A3B8; font-size: 10px; background: transparent;")
        
        self.footer_bar_layout.addStretch()
        self.footer_bar_layout.addWidget(self.lbl_global_footer)
        self.content_layout.addWidget(self.footer_bar)
        
        self.layout.addWidget(self.content_area, stretch=1)
        
        # Setup child views lazily
        self.dashboard_view = None
        self.orders_view = None
        self.requests_view = None
        self.refs_view = None
        self.inventory_view = None
        
        self.placeholder_lbl = QLabel("Cargando...", self)
        self.placeholder_lbl.setAlignment(Qt.AlignCenter)
        self.stacked_widget.addWidget(self.placeholder_lbl)
        
        # Connect sidebar navigation selection
        self.sidebar.nav_selected.connect(self._on_navigation)
        
        # Connect theme toggle action
        self.sidebar.theme_toggled.connect(self._toggle_theme)

        # Connect logout action
        self.sidebar.logout_requested.connect(self.logout_requested.emit)
        
        # Apply RBAC permissions (Nivel 2)
        self._apply_permissions()
        
    def _apply_permissions(self):
        """Loads user permissions and shows authorized sidebar navigation items (Fail-Closed)."""
        try:
            parent_window = self.window()
            usuario_id = getattr(parent_window, 'current_usuario_id', None)
            if not usuario_id:
                return

            if self.api_client.connect_via_api:
                perms = self.api_client.request("GET", f"/api/auth/permissions/{usuario_id}")
                self.user_permissions_cache = perms
                has_dashboard = perms.get("DASHBOARD", {}).get("LEER", False)
                has_ordenes = perms.get("ORDENES", {}).get("LEER", False)
                has_solicitudes = perms.get("SOLICITUDES", {}).get("LEER", False)
                has_derechos = perms.get("DERECHOS", {}).get("LEER", False) or perms.get("REFERENCIAS", {}).get("LEER", False)
                has_ctrl_inv = perms.get("CTRL:INVENTARIO", {}).get("LEER", False) or perms.get("REFERENCIAS", {}).get("LEER", False)
                has_ctrl_asignar = perms.get("CTRL:ASIGNAR_DERECHO", {}).get("LEER", False) or perms.get("REFERENCIAS", {}).get("LEER", False)
                has_ctrl_validar = perms.get("CTRL:ASIGNAR_VALIDAR", {}).get("LEER", False) or perms.get("REFERENCIAS", {}).get("LEER", False)
                has_ctrl_reserva = perms.get("CTRL:RESERVA_DERECHO", {}).get("LEER", False) or perms.get("REFERENCIAS", {}).get("LEER", False)
                has_ctrl_lotes = perms.get("CTRL:GESTION_LOTES", {}).get("LEER", False) or perms.get("REFERENCIAS", {}).get("LEER", False)
                has_seguridad = perms.get("SEGURIDAD", {}).get("LEER", False)
                has_cancun = (
                    perms.get("FOLIOS_CANCUN", {}).get("LEER", False) or
                    perms.get("RECIBOS_CANCUN", {}).get("LEER", False) or
                    perms.get("FACTURAS_CANCUN", {}).get("LEER", False)
                )
            else:
                with self.db_connector.get_session() as session:
                    from sar.src.services.security_service import SecurityService
                    sec_service = SecurityService(session)
                    has_dashboard = sec_service.has_permission(usuario_id, "DASHBOARD", "LEER")
                    has_ordenes = sec_service.has_permission(usuario_id, "ORDENES", "LEER")
                    has_solicitudes = sec_service.has_permission(usuario_id, "SOLICITUDES", "LEER")
                    has_derechos = sec_service.has_permission(usuario_id, "DERECHOS", "LEER") or sec_service.has_permission(usuario_id, "REFERENCIAS", "LEER")
                    has_ctrl_inv = sec_service.has_permission(usuario_id, "CTRL:INVENTARIO", "LEER") or sec_service.has_permission(usuario_id, "REFERENCIAS", "LEER")
                    has_ctrl_asignar = sec_service.has_permission(usuario_id, "CTRL:ASIGNAR_DERECHO", "LEER") or sec_service.has_permission(usuario_id, "REFERENCIAS", "LEER")
                    has_ctrl_validar = sec_service.has_permission(usuario_id, "CTRL:ASIGNAR_VALIDAR", "LEER") or sec_service.has_permission(usuario_id, "REFERENCIAS", "LEER")
                    has_ctrl_reserva = sec_service.has_permission(usuario_id, "CTRL:RESERVA_DERECHO", "LEER") or sec_service.has_permission(usuario_id, "REFERENCIAS", "LEER")
                    has_ctrl_lotes = sec_service.has_permission(usuario_id, "CTRL:GESTION_LOTES", "LEER") or sec_service.has_permission(usuario_id, "REFERENCIAS", "LEER")
                    has_seguridad = sec_service.has_permission(usuario_id, "SEGURIDAD", "LEER")
                    has_cancun = (
                        sec_service.has_permission(usuario_id, "FOLIOS_CANCUN", "LEER") or
                        sec_service.has_permission(usuario_id, "RECIBOS_CANCUN", "LEER") or
                        sec_service.has_permission(usuario_id, "FACTURAS_CANCUN", "LEER")
                    )
                
            default_item = None

            if has_dashboard:
                self.sidebar.show_item("dashboard")
                if not default_item: default_item = "dashboard"
            if has_ordenes:
                self.sidebar.show_item("ordenes")
                self.sidebar.show_item("ordenes_capturadas")
                self.sidebar.show_item("capturar_orden")
                if not default_item: default_item = "ordenes"
            if has_solicitudes:
                self.sidebar.show_item("solicitudes")
                if not default_item: default_item = "solicitudes"
            
            if has_derechos:
                self.sidebar.show_item("referencias")
                if not default_item: default_item = "referencias"

            has_any_ctrl = any([has_ctrl_inv, has_ctrl_asignar, has_ctrl_validar, has_ctrl_reserva, has_ctrl_lotes])
            if has_any_ctrl:
                self.sidebar.show_item("inventario")
                if not default_item: default_item = "inventario"

            if has_ctrl_inv:     self.sidebar.show_item("inventario_facturas")
            if has_ctrl_validar: self.sidebar.show_item("inventario_masivo")
            if has_ctrl_reserva: self.sidebar.show_item("inventario_apartar")
            if has_ctrl_asignar: self.sidebar.show_item("inventario_catalogos")
            if has_ctrl_lotes:   self.sidebar.show_item("inventario_lotes")

            if has_cancun:
                self.sidebar.show_item("r2f_control")
                if not default_item: default_item = "r2f_control"

            if has_seguridad:
                self.sidebar.show_item("configuracion")
                if not default_item: default_item = "configuracion"

            if default_item:
                self.sidebar.select_item(default_item)
        except Exception as e:
            print(f"Error applying permissions in MainView: {e}")

    def _create_placeholder_view(self, title_text: str) -> QWidget:
        """Helper to create simple layout placeholders for views."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        
        lbl = CustomLabel(title_text, variant="header")
        layout.addWidget(lbl)
        return widget
        
    def _load_metrics_view(self, orden_ids: list, return_widget: QWidget = None):
        """Handler to load and switch to metrics view inside QStackedWidget remembering previous view."""
        if not hasattr(self, "metrics_view") or not self.metrics_view:
            from sar.src.ui.views.metrics_dashboard_dialog import MetricsDashboardDialog
            self.metrics_view = MetricsDashboardDialog(self.db_connector, initial_orden_ids=orden_ids, parent=self)
            self.metrics_view._previous_view = return_widget or self.dashboard_view
            
            def _on_back():
                prev = getattr(self.metrics_view, '_previous_view', None) or self.dashboard_view
                self.stacked_widget.setCurrentWidget(prev)
                
            self.metrics_view.back_requested.connect(_on_back)
            self.stacked_widget.addWidget(self.metrics_view)
        else:
            self.metrics_view._previous_view = return_widget or self.stacked_widget.currentWidget() or self.dashboard_view
            self.metrics_view.selected_orden_ids = list(orden_ids)
            self.metrics_view._update_orden_filter_label()
            self.metrics_view.refresh_metrics()
        
        self.stacked_widget.setCurrentWidget(self.metrics_view)

    def _on_navigation(self, view_key: str):
        """Switches the stacked widget active view or opens independent windows with routing permissions check."""
        try:
            parent_window = self.window()
            usuario_id = getattr(parent_window, 'current_usuario_id', None)
            if not usuario_id:
                return

            if view_key == "r2f_control":
                if self.api_client.connect_via_api:
                    perms = getattr(self, 'user_permissions_cache', None)
                    if perms is None:
                        perms = self.api_client.request("GET", f"/api/auth/permissions/{usuario_id}")
                        self.user_permissions_cache = perms
                    has_permission = (
                        perms.get("FOLIOS_CANCUN", {}).get("LEER", False) or
                        perms.get("RECIBOS_CANCUN", {}).get("LEER", False) or
                        perms.get("FACTURAS_CANCUN", {}).get("LEER", False)
                    )
                else:
                    with self.db_connector.get_session() as session:
                        from sar.src.services.security_service import SecurityService
                        sec_service = SecurityService(session)
                        has_permission = (
                            sec_service.has_permission(usuario_id, "FOLIOS_CANCUN", "LEER") or
                            sec_service.has_permission(usuario_id, "RECIBOS_CANCUN", "LEER") or
                            sec_service.has_permission(usuario_id, "FACTURAS_CANCUN", "LEER")
                        )
                if not has_permission:
                    from sar.src.ui.design_system.components import GLMessageBox as QMessageBox
                    QMessageBox.warning(self, "Acceso Denegado", "No tiene permisos para acceder al módulo Cancún (R2F).")
                    return
            else:
                mod_mapping = {
                    "dashboard": "DASHBOARD",
                    "ordenes": "ORDENES",
                    "ordenes_capturadas": "ORDENES",
                    "capturar_orden": "ORDENES",
                    "solicitudes": "SOLICITUDES",
                    "referencias": "DERECHOS",
                    "inventario": "CONTROL_DERECHOS",
                    "inventario_facturas": "CTRL:INVENTARIO",
                    "inventario_masivo": "CTRL:ASIGNAR_VALIDAR",
                    "inventario_apartar": "CTRL:RESERVA_DERECHO",
                    "inventario_catalogos": "CTRL:ASIGNAR_DERECHO",
                    "inventario_lotes": "CTRL:GESTION_LOTES",
                    "configuracion": "SEGURIDAD"
                }
                
                req_mod = mod_mapping.get(view_key)
                if req_mod:
                    if self.api_client.connect_via_api:
                        perms = getattr(self, 'user_permissions_cache', None)
                        if perms is None:
                            perms = self.api_client.request("GET", f"/api/auth/permissions/{usuario_id}")
                            self.user_permissions_cache = perms
                        has_permission = perms.get(req_mod, {}).get("LEER", False) or perms.get("REFERENCIAS", {}).get("LEER", False)
                    else:
                        with self.db_connector.get_session() as session:
                            from sar.src.services.security_service import SecurityService
                            sec_service = SecurityService(session)
                            has_permission = (
                                sec_service.has_permission(usuario_id, req_mod, "LEER") or
                                sec_service.has_permission(usuario_id, "REFERENCIAS", "LEER")
                            )
                    
                    if not has_permission:
                        from sar.src.ui.design_system.components import GLMessageBox as QMessageBox
                        QMessageBox.warning(self, "Acceso Denegado", f"No tiene permisos para acceder al módulo {req_mod}.")
                        return
        except Exception as e:
            print(f"Routing security error in MainView: {e}")
            return

        if view_key == "dashboard":
            if not self.dashboard_view:
                from sar.src.ui.views.dashboard_view import DashboardView
                self.dashboard_view = DashboardView(self.db_connector, self)
                self.dashboard_view.show_metrics_requested.connect(
                    lambda oids: self._load_metrics_view(oids, return_widget=self.dashboard_view)
                )
                self.stacked_widget.addWidget(self.dashboard_view)
            self.stacked_widget.setCurrentWidget(self.dashboard_view)
            self.dashboard_view.refresh_data()
        elif view_key in ["ordenes", "ordenes_capturadas", "capturar_orden"]:
            if not self.orders_view:
                from sar.src.ui.views.orders_view import OrdersView
                self.orders_view = OrdersView(self.db_connector, self)
                self.stacked_widget.addWidget(self.orders_view)
            self.stacked_widget.setCurrentWidget(self.orders_view)
            self.orders_view.refresh_historial()
            if view_key == "ordenes_capturadas":
                self.orders_view.tabs.setCurrentIndex(1)
            elif view_key == "capturar_orden":
                self.orders_view.tabs.setCurrentIndex(0)
        elif view_key == "solicitudes":
            if not self.requests_view:
                from sar.src.ui.views.requests_view import RequestsView
                self.requests_view = RequestsView(self.db_connector, self)
                self.stacked_widget.addWidget(self.requests_view)
            self.stacked_widget.setCurrentWidget(self.requests_view)
            self.requests_view.refresh_data()
        elif view_key == "referencias":
            if not self.refs_view:
                from sar.src.ui.views.referencias_view import ReferenciasView
                self.refs_view = ReferenciasView(self.db_connector, self)
                self.stacked_widget.addWidget(self.refs_view)
            self.stacked_widget.setCurrentWidget(self.refs_view)
            self.refs_view.refresh_data()
        elif view_key == "r2f_control":
            if not hasattr(self, "r2f_control_view") or not self.r2f_control_view:
                from sar.src.ui.views.r2f_control_view import R2FControlView
                self.r2f_control_view = R2FControlView(self.db_connector, self)
                self.stacked_widget.addWidget(self.r2f_control_view)
            self.stacked_widget.setCurrentWidget(self.r2f_control_view)
            self.r2f_control_view.refresh_data()
        elif view_key in ["inventario", "inventario_facturas", "inventario_masivo", "inventario_apartar", "inventario_catalogos", "inventario_lotes"]:
            is_new = False
            if not self.inventory_view:
                from sar.src.ui.views.inventory_view import InventoryView
                self.inventory_view = InventoryView(self.db_connector, self)
                self.inventory_view.show_metrics_requested.connect(
                    lambda oids: self._load_metrics_view(oids, return_widget=self.inventory_view)
                )
                self.stacked_widget.addWidget(self.inventory_view)
                is_new = True
            self.stacked_widget.setCurrentWidget(self.inventory_view)
            
            target_tab = "inventario_facturas" if view_key == "inventario" else view_key
            self.inventory_view.set_active_tab(target_tab)
            
            # Carga inteligente por pestaña: si ya fue instanciada o el destino no es el visor por defecto
            if not is_new or target_tab != "inventario_facturas":
                load_cats = view_key in ["inventario_masivo", "inventario_apartar", "inventario_catalogos"]
                self.inventory_view.refresh_all(load_catalogs=load_cats, active_tab=target_tab)
        elif view_key == "configuracion":

            if not self.admin_window:
                from sar.src.ui.views.admin_view import AdminWindow
                parent_window = self.window()
                uid = getattr(parent_window, 'current_usuario_id', None)
                sid = getattr(parent_window, 'current_sesion_id', None)
                on_logout_fn = getattr(parent_window, '_on_logout', None)
                self.admin_window = AdminWindow(
                    self.db_connector,
                    self,
                    current_usuario_id=uid,
                    current_sesion_id=sid
                )
                if on_logout_fn:
                    self.admin_window._on_logout = on_logout_fn
                    self.admin_window.logout_requested.connect(self.logout_requested.emit)
            self.admin_window.show()
            self.admin_window.raise_()
            self.admin_window.activateWindow()
            
    def _toggle_theme(self):
        """Toggles theme state between Light and Dark modes."""
        self.is_dark_theme = not self.is_dark_theme
        # Apply theme globally to the top-level window/app
        window = self.window()
        self.theme_manager.apply_theme(window, self.is_dark_theme)
        
    def hide_admin_menu(self):
        """Hides the administration menu button from the sidebar."""
        self.sidebar.hide_item("configuracion")

    def _get_username_string(self) -> str:
        """Helper to fetch the current user's username."""
        try:
            parent_window = self.window()
            username = getattr(parent_window, 'current_username', None)
            if username:
                return username
                
            if self.api_client.connect_via_api:
                return "Usuario API"

            with self.db_connector.get_session() as session:
                from sar.src.storage.models import Sesion, Usuario
                sesion_id = getattr(parent_window, 'current_sesion_id', None)
                if sesion_id:
                    db_sesion = session.get(Sesion, sesion_id)
                    if db_sesion and db_sesion.usuario:
                        return db_sesion.usuario.username
        except Exception:
            pass
        return "Administrador"
