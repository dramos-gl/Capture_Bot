"""Admin Menu Bar Organism."""

from PySide6.QtWidgets import QMenuBar
from PySide6.QtCore import Signal, Qt
from sar.src.ui.design_system.tokens.colors import Colors

class AdminMenuBar(QMenuBar):
    """Traditional QMenuBar tailored for the Administration Module."""
    
    view_requested = Signal(str)
    logout_clicked = Signal()
    exit_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_menus()
        
    def _build_menus(self):
        # Sistema
        menu_sistema = self.addMenu("Sistema")
        menu_sistema.setWindowFlag(Qt.FramelessWindowHint, True)
        act_logout = menu_sistema.addAction("Cerrar sesión")
        act_exit = menu_sistema.addAction("Salir")
        
        act_logout.triggered.connect(self.logout_clicked.emit)
        act_exit.triggered.connect(self.exit_clicked.emit)
        
        # Seguridad y Accesos
        menu_seguridad = self.addMenu("Seguridad y Accesos")
        menu_seguridad.setWindowFlag(Qt.FramelessWindowHint, True)
        act_users = menu_seguridad.addAction("Gestión de Usuarios")
        act_roles = menu_seguridad.addAction("Roles y Permisos")
        menu_seguridad.addSeparator()
        act_modulos = menu_seguridad.addAction("Módulos del Sistema")
        act_acciones = menu_seguridad.addAction("Catálogo de Acciones")
        
        act_users.triggered.connect(lambda: self.view_requested.emit("usuarios"))
        act_roles.triggered.connect(lambda: self.view_requested.emit("roles"))
        
        seg_permisos = menu_seguridad.addAction("Matriz de Permisos")
        seg_permisos.triggered.connect(lambda: self.view_requested.emit("permisos"))
        
        act_modulos.triggered.connect(lambda: self.view_requested.emit("app_modulos"))
        act_acciones.triggered.connect(lambda: self.view_requested.emit("acciones"))
        
        # Catálogos Base
        menu_catalogos = self.addMenu("Catálogos Base")
        menu_catalogos.setWindowFlag(Qt.FramelessWindowHint, True)
        act_conceptos = menu_catalogos.addAction("Conceptos de Referencia")
        act_geografia = menu_catalogos.addAction("Geografía (Municipios y Delegaciones)")
        act_rfcs = menu_catalogos.addAction("Registro Federal de Contribuyentes (RFC)")
        act_estados = menu_catalogos.addAction("Estados del Sistema")
        
        act_conceptos.triggered.connect(lambda: self.view_requested.emit("conceptos"))
        act_geografia.triggered.connect(lambda: self.view_requested.emit("geografia"))
        act_rfcs.triggered.connect(lambda: self.view_requested.emit("rfcs"))
        act_estados.triggered.connect(lambda: self.view_requested.emit("estados"))
        
        # Configuración Core
        menu_config = self.addMenu("Configuración Core")
        menu_config.setWindowFlag(Qt.FramelessWindowHint, True)
        act_parametros = menu_config.addAction("Parámetros del Sistema")
        act_locs = menu_config.addAction("Localizadores (Motor Bot)")
        
        act_parametros.triggered.connect(lambda: self.view_requested.emit("parametros"))
        act_locs.triggered.connect(lambda: self.view_requested.emit("localizadores"))
        
        # Procesos Especiales
        menu_procesos = self.addMenu("Procesos Especiales")
        menu_procesos.setWindowFlag(Qt.FramelessWindowHint, True)
        act_migracion = menu_procesos.addAction("Migración de Referencias")
        act_carga = menu_procesos.addAction("Carga Masiva de Referencias")
        act_update = menu_procesos.addAction("Escanear Delegaciones en PDFs")
        act_reserva_masiva = menu_procesos.addAction("Reserva Masiva de Referencias")
        
        act_migracion.triggered.connect(lambda: self.view_requested.emit("migracion"))
        act_carga.triggered.connect(lambda: self.view_requested.emit("carga_masiva"))
        act_update.triggered.connect(lambda: self.view_requested.emit("update_facturas"))
        act_reserva_masiva.triggered.connect(lambda: self.view_requested.emit("reserva_masiva"))
