"""Main shell coordinator view."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QStackedWidget
from PySide6.QtCore import Signal
from sar.src.ui.design_system.components import NavigationSidebar, CustomLabel
from sar.src.ui.views.dashboard_view import DashboardView
from sar.src.ui.views.orders_view import OrdersView
from sar.src.ui.views.requests_view import RequestsView
from sar.src.ui.views.referencias_view import ReferenciasView
from sar.src.ui.views.admin_view import AdminWindow

class MainView(QWidget):
    """Main Application Window layout binding Sidebar navigation and stack views."""
    
    # Signal emitted when logout is requested from sidebar
    logout_requested = Signal()
    
    def __init__(self, theme_manager, db_connector, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.db_connector = db_connector
        self.is_dark_theme = True
        self.admin_window = None
        
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
        
        # Setup child views
        self.dashboard_view = DashboardView(self.db_connector, self)
        self.stacked_widget.addWidget(self.dashboard_view)
        
        # Placeholder views for other sections
        self.orders_view = OrdersView(self.db_connector, self)
        self.requests_view = RequestsView(self.db_connector, self)
        self.refs_view = ReferenciasView(self.db_connector, self)
        
        self.stacked_widget.addWidget(self.orders_view)
        self.stacked_widget.addWidget(self.requests_view)
        self.stacked_widget.addWidget(self.refs_view)
        
        # Connect sidebar navigation selection
        self.sidebar.nav_selected.connect(self._on_navigation)
        
        # Connect theme toggle action
        self.sidebar.theme_toggled.connect(self._toggle_theme)

        # Connect logout action
        self.sidebar.logout_requested.connect(self.logout_requested.emit)
        
    def _create_placeholder_view(self, title_text: str) -> QWidget:
        """Helper to create simple layout placeholders for views."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        
        lbl = CustomLabel(title_text, variant="header")
        layout.addWidget(lbl)
        return widget
        
    def _on_navigation(self, view_key: str):
        """Switches the stacked widget active view or opens independent windows."""
        if view_key == "dashboard":
            self.stacked_widget.setCurrentWidget(self.dashboard_view)
            self.dashboard_view.refresh_data()
        elif view_key in ["ordenes", "ordenes_capturadas", "capturar_orden"]:
            self.stacked_widget.setCurrentWidget(self.orders_view)
            self.orders_view.refresh_historial()
            if view_key == "ordenes_capturadas":
                self.orders_view.tabs.setCurrentIndex(1)
            elif view_key == "capturar_orden":
                self.orders_view.tabs.setCurrentIndex(0)
        elif view_key == "solicitudes":
            self.stacked_widget.setCurrentWidget(self.requests_view)
            self.requests_view.refresh_data()
        elif view_key == "referencias":
            self.stacked_widget.setCurrentWidget(self.refs_view)
            self.refs_view.refresh_data()
        elif view_key == "configuracion":
            if not self.admin_window:
                self.admin_window = AdminWindow(self.db_connector, self)
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
        """Helper to fetch the current user's username from the physical database."""
        try:
            with self.db_connector.get_session() as session:
                from sar.src.storage.models import Sesion, Usuario
                parent_window = self.window()
                sesion_id = getattr(parent_window, 'current_sesion_id', None)
                if sesion_id:
                    db_sesion = session.get(Sesion, sesion_id)
                    if db_sesion and db_sesion.usuario:
                        return db_sesion.usuario.username
        except Exception:
            pass
        return "Administrador"
