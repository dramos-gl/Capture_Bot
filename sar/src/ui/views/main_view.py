"""Main shell coordinator view."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QStackedWidget
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
        
        # Stacked layout for main views
        self.stacked_widget = QStackedWidget(self)
        self.layout.addWidget(self.stacked_widget)
        
        # Setup child views lazily
        self.dashboard_view = None
        self.orders_view = None
        self.requests_view = None
        self.refs_view = None
        self.inventory_view = None
        
        from PySide6.QtWidgets import QLabel
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
                has_dashboard = perms.get("DASHBOARD", {}).get("LEER", False)
                has_ordenes = perms.get("ORDENES", {}).get("LEER", False)
                has_solicitudes = perms.get("SOLICITUDES", {}).get("LEER", False)
                has_referencias = perms.get("REFERENCIAS", {}).get("LEER", False)
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
                    has_referencias = sec_service.has_permission(usuario_id, "REFERENCIAS", "LEER")
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
            if has_referencias:
                self.sidebar.show_item("referencias")
                self.sidebar.show_item("inventario")
                self.sidebar.show_item("inventario_facturas")
                self.sidebar.show_item("inventario_masivo")
                self.sidebar.show_item("inventario_apartar")
                self.sidebar.show_item("inventario_catalogos")
                self.sidebar.show_item("inventario_lotes")
                if not default_item: default_item = "referencias"

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
        
    def _on_navigation(self, view_key: str):
        """Switches the stacked widget active view or opens independent windows with routing permissions check."""
        try:
            parent_window = self.window()
            usuario_id = getattr(parent_window, 'current_usuario_id', None)
            if not usuario_id:
                return

            if view_key == "r2f_control":
                if self.api_client.connect_via_api:
                    perms = self.api_client.request("GET", f"/api/auth/permissions/{usuario_id}")
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
                    "referencias": "REFERENCIAS",
                    "inventario": "REFERENCIAS",
                    "inventario_facturas": "REFERENCIAS",
                    "inventario_masivo": "REFERENCIAS",
                    "inventario_apartar": "REFERENCIAS",
                    "inventario_catalogos": "REFERENCIAS",
                    "inventario_lotes": "REFERENCIAS",
                    "configuracion": "SEGURIDAD"
                }
                
                req_mod = mod_mapping.get(view_key)
                if req_mod:
                    if self.api_client.connect_via_api:
                        perms = self.api_client.request("GET", f"/api/auth/permissions/{usuario_id}")
                        has_permission = perms.get(req_mod, {}).get("LEER", False)
                    else:
                        with self.db_connector.get_session() as session:
                            from sar.src.services.security_service import SecurityService
                            sec_service = SecurityService(session)
                            has_permission = sec_service.has_permission(usuario_id, req_mod, "LEER")
                    
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
                
                # Handler to load and switch to metrics view inside QStackedWidget
                def load_metrics_view(orden_ids):
                    if not hasattr(self, "metrics_view") or not self.metrics_view:
                        from sar.src.ui.views.metrics_dashboard_dialog import MetricsDashboardDialog
                        self.metrics_view = MetricsDashboardDialog(self.db_connector, initial_orden_ids=orden_ids, parent=self)
                        
                        # Return to dashboard when back button is pressed
                        self.metrics_view.back_requested.connect(lambda: self.stacked_widget.setCurrentWidget(self.dashboard_view))
                        self.stacked_widget.addWidget(self.metrics_view)
                    else:
                        self.metrics_view.selected_orden_ids = list(orden_ids)
                        self.metrics_view._update_orden_filter_label()
                        self.metrics_view.refresh_metrics()
                    
                    self.stacked_widget.setCurrentWidget(self.metrics_view)

                self.dashboard_view.show_metrics_requested.connect(load_metrics_view)
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
            if not self.inventory_view:
                from sar.src.ui.views.inventory_view import InventoryView
                self.inventory_view = InventoryView(self.db_connector, self)
                self.stacked_widget.addWidget(self.inventory_view)
            self.stacked_widget.setCurrentWidget(self.inventory_view)
            
            # Load catalogs only if entering mass assignment, reservation or catalog tabs
            load_cats = view_key in ["inventario_masivo", "inventario_apartar", "inventario_catalogos"]
            self.inventory_view.refresh_all(load_catalogs=load_cats)
            
            if view_key == "inventario":
                self.inventory_view.set_active_tab("inventario_facturas")
            else:
                self.inventory_view.set_active_tab(view_key)
        elif view_key == "configuracion":

            if not self.admin_window:
                from sar.src.ui.views.admin_view import AdminWindow
                parent_window = self.window()
                uid = getattr(parent_window, 'current_usuario_id', None)
                sid = getattr(parent_window, 'current_sesion_id', None)
                self.admin_window = AdminWindow(
                    self.db_connector,
                    self,
                    current_usuario_id=uid,
                    current_sesion_id=sid
                )
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
