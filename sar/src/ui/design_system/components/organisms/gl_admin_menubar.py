"""Admin Menu Bar Organism with rich icons, shortcuts, and Help integration."""

from PySide6.QtWidgets import QMenuBar, QMenu
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction, QKeySequence
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.utils.icons import Icons


class AdminMenuBar(QMenuBar):
    """Traditional QMenuBar tailored for the Administration Module with icon support."""
    
    view_requested = Signal(str)
    logout_clicked = Signal()
    exit_clicked = Signal()
    
    # Help Signals
    help_manual_requested = Signal()
    help_shortcuts_requested = Signal()
    help_diagnostics_requested = Signal()
    help_support_requested = Signal()
    help_about_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QMenuBar {{
                background-color: {Colors.SLATE_50};
                color: {Colors.TEXT_LIGHT_PRIMARY};
                border-bottom: 1px solid {Colors.SLATE_200};
                font-size: 13px;
                font-weight: 500;
                padding: 2px 6px;
            }}
            QMenuBar::item {{
                background: transparent;
                padding: 6px 12px;
                border-radius: 6px;
                margin: 2px;
            }}
            QMenuBar::item:selected {{
                background-color: {Colors.SLATE_200};
                color: {Colors.SLATE_900};
            }}
            QMenuBar::item:pressed {{
                background-color: #CBD5E1;
            }}
            QMenu {{
                background-color: {Colors.SURFACE_LIGHT};
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 6px 28px 6px 10px;
                border-radius: 4px;
                color: {Colors.TEXT_LIGHT_PRIMARY};
                font-size: 12px;
            }}
            QMenu::item:selected {{
                background-color: {Colors.ACCENT_BG};
                color: {Colors.ACCENT};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {Colors.SLATE_200};
                margin: 4px 6px;
            }}
        """)
        self._build_menus()

    def _add_action(self, menu: QMenu, text: str, icon_name: str, shortcut: str = None, color: str = None) -> QAction:
        """Helper to create and add a styled QAction with colored icon and optional keyboard shortcut."""
        action = QAction(text, self)
        if icon_name:
            icon_color = color or Colors.TEXT_LIGHT_SECONDARY
            action.setIcon(Icons.get_icon(icon_name, size=16, color=icon_color))
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        menu.addAction(action)
        return action
        
    def _build_menus(self):
        # 1. 📁 Sistema
        menu_sistema = self.addMenu("&Sistema")
        menu_sistema.setWindowFlag(Qt.FramelessWindowHint, True)
        
        act_logout = self._add_action(menu_sistema, "Cerrar sesión", "salir", "Ctrl+L", color=Colors.ACCENT_AMBER)
        menu_sistema.addSeparator()
        act_exit = self._add_action(menu_sistema, "Salir del Sistema", "cerrar", "Ctrl+Q", color=Colors.ERROR)
        
        act_logout.triggered.connect(self.logout_clicked.emit)
        act_exit.triggered.connect(self.exit_clicked.emit)
        
        # 2. 🛡️ Seguridad y Accesos
        menu_seguridad = self.addMenu("&Seguridad y Accesos")
        menu_seguridad.setWindowFlag(Qt.FramelessWindowHint, True)
        
        act_users = self._add_action(menu_seguridad, "Gestión de Usuarios", "usuarios", "Ctrl+1", color=Colors.ACCENT_BLUE)
        act_roles = self._add_action(menu_seguridad, "Gestión de Roles", "roles", "Ctrl+2", color=Colors.ACCENT_VIOLET)
        act_permisos = self._add_action(menu_seguridad, "Matriz de Permisos", "permisos", "Ctrl+3", color=Colors.ACCENT_INDIGO)
        menu_seguridad.addSeparator()
        act_modulos = self._add_action(menu_seguridad, "Módulos de la Aplicación", "modulos", color=Colors.ACCENT_CYAN)
        act_acciones = self._add_action(menu_seguridad, "Catálogo de Acciones", "actividad", color=Colors.ACCENT_TEAL)
        
        act_users.triggered.connect(lambda: self.view_requested.emit("usuarios"))
        act_roles.triggered.connect(lambda: self.view_requested.emit("roles"))
        act_permisos.triggered.connect(lambda: self.view_requested.emit("permisos"))
        act_modulos.triggered.connect(lambda: self.view_requested.emit("app_modulos"))
        act_acciones.triggered.connect(lambda: self.view_requested.emit("acciones"))
        
        # 3. 📚 Catálogos Base
        menu_catalogos = self.addMenu("&Catálogos Base")
        menu_catalogos.setWindowFlag(Qt.FramelessWindowHint, True)
        
        act_conceptos = self._add_action(menu_catalogos, "Catálogos de Negocio (Conceptos, Notarías, Desarrollos)", "tabla", color=Colors.ACCENT_EMERALD)
        act_geografia = self._add_action(menu_catalogos, "Geografía Operativa (Municipios y Delegaciones)", "idioma", color=Colors.ACCENT_TEAL)
        act_rfcs = self._add_action(menu_catalogos, "Contribuyentes Base (RFC)", "documento_plantilla", color=Colors.ACCENT_AMBER)
        act_estados = self._add_action(menu_catalogos, "Estados y Transiciones del Sistema", "validar", color=Colors.SUCCESS)
        
        act_conceptos.triggered.connect(lambda: self.view_requested.emit("conceptos"))
        act_geografia.triggered.connect(lambda: self.view_requested.emit("geografia"))
        act_rfcs.triggered.connect(lambda: self.view_requested.emit("rfcs"))
        act_estados.triggered.connect(lambda: self.view_requested.emit("estados"))
        
        # 4. ⚙️ Configuración Core
        menu_config = self.addMenu("&Configuración Core")
        menu_config.setWindowFlag(Qt.FramelessWindowHint, True)
        
        act_parametros = self._add_action(menu_config, "Parámetros Globales del Sistema", "parametros", color=Colors.ACCENT_BLUE)
        act_locs = self._add_action(menu_config, "Localizadores y Selectores (Motor Bot)", "integraciones", color=Colors.ACCENT_VIOLET)
        
        act_parametros.triggered.connect(lambda: self.view_requested.emit("parametros"))
        act_locs.triggered.connect(lambda: self.view_requested.emit("localizadores"))
        
        # 5. 🛠️ Procesos Especiales
        menu_procesos = self.addMenu("&Procesos Especiales")
        menu_procesos.setWindowFlag(Qt.FramelessWindowHint, True)
        
        act_carga = self._add_action(menu_procesos, "Carga Masiva de Referencias", "documento_cargar", color=Colors.ACCENT_CYAN)
        act_migracion = self._add_action(menu_procesos, "Migración y Sincronización", "sincronizar", color=Colors.ACCENT_INDIGO)
        act_reserva_masiva = self._add_action(menu_procesos, "Reserva Masiva de Referencias", "bloquear", color=Colors.ACCENT_ROSE)
        act_update = self._add_action(menu_procesos, "Escanear Delegaciones en Facturas (PDF)", "documento_historial", color=Colors.ACCENT_EMERALD)
        
        act_carga.triggered.connect(lambda: self.view_requested.emit("carga_masiva"))
        act_migracion.triggered.connect(lambda: self.view_requested.emit("migracion"))
        act_reserva_masiva.triggered.connect(lambda: self.view_requested.emit("reserva_masiva"))
        act_update.triggered.connect(lambda: self.view_requested.emit("update_facturas"))

        # 6. ❓ Ayuda
        menu_ayuda = self.addMenu("&Ayuda")
        menu_ayuda.setWindowFlag(Qt.FramelessWindowHint, True)
        
        act_manual = self._add_action(menu_ayuda, "Manual de Administración y Guía", "documento_abrir", "F1", color=Colors.ACCENT)
        act_shortcuts = self._add_action(menu_ayuda, "Atajos de Teclado", "preferencias", "Ctrl+H", color=Colors.ACCENT_VIOLET)
        act_diagnostics = self._add_action(menu_ayuda, "Diagnóstico y Estado del Servidor", "actividad", color=Colors.SUCCESS)
        menu_ayuda.addSeparator()
        act_support = self._add_action(menu_ayuda, "Mesa de Ayuda y Soporte Técnico", "soporte", color=Colors.ACCENT_AMBER)
        act_about = self._add_action(menu_ayuda, "Acerca de SAR...", "informacion", color=Colors.ACCENT_CYAN)
        
        act_manual.triggered.connect(self.help_manual_requested.emit)
        act_shortcuts.triggered.connect(self.help_shortcuts_requested.emit)
        act_diagnostics.triggered.connect(self.help_diagnostics_requested.emit)
        act_support.triggered.connect(self.help_support_requested.emit)
        act_about.triggered.connect(self.help_about_requested.emit)
