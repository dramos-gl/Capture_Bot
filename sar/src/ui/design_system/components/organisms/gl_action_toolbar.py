"""Dynamic Action Toolbar Organism for System Administration (Atomic Design)."""

from typing import Optional, Callable
from PySide6.QtWidgets import QToolBar, QToolButton, QWidget
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QAction
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.utils.icons import Icons


class GLActionToolbar(QToolBar):
    """Horizontal dynamic action bar providing contextual tools and CRUD operations per active module."""
    
    # Navegación general y de vista
    home_requested = Signal()
    view_requested = Signal(str)
    
    # Operaciones CRUD y Utilerías
    new_requested = Signal()
    edit_requested = Signal()
    refresh_requested = Signal()
    export_requested = Signal()
    help_requested = Signal()

    # Acciones operativas contextuales (Importación de Viviendas / Procesos)
    template_requested = Signal()
    import_file_requested = Signal()
    clean_requested = Signal()
    apply_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("adminActionToolbar")
        self.setMovable(False)
        self.setFloatable(False)
        self.setIconSize(QSize(24, 24))
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        
        self.current_category: Optional[str] = None
        self._module_actions = []
        self._actions_mode = "default"
        
        # Oculta inicialmente por defecto (hasta que se seleccione un módulo)
        self.setVisible(False)
        self._build_toolbar_skeleton()

    def _build_toolbar_skeleton(self):
        """Builds static navigation and CRUD tool controls."""
        # 1. Inicio / Home
        self.act_home = self._create_action(
            "Inicio", "inicio", "Volver a la pantalla de bienvenida", "#2563EB", self.home_requested.emit
        )
        self.act_home.setCheckable(True)
        self.addAction(self.act_home)
        
        # Separador inicial después de Inicio
        self.sep_home = self.addSeparator()

        # Marcador para inserción de herramientas dinámicas de módulo
        # 2. Separador entre herramientas dinámicas y CRUD
        self.sep_crud = self.addSeparator()

        # 3. Operaciones CRUD (Nuevo y Editar)
        self.act_new = self._create_action(
            "Nuevo", "nuevo_doc", "Crear nuevo registro (Ctrl+N)", "#10B981", self.new_requested.emit
        )
        self.addAction(self.act_new)

        self.act_edit = self._create_action(
            "Editar", "editar", "Editar registro seleccionado", "#3B82F6", self.edit_requested.emit
        )
        self.act_edit.setEnabled(False)
        self.addAction(self.act_edit)

        # 3.1 Acciones Especiales para Importación de Viviendas (Modo dinámico)
        self.act_template = self._create_action(
            "Plantilla\nExcel", "documento_descargar", "Descargar plantilla oficial en Excel", "#2563EB", self.template_requested.emit
        )
        self.act_template.setVisible(False)
        self.addAction(self.act_template)

        self.act_import_file = self._create_action(
            "Cargar\nArchivo", "importar", "Cargar archivo Excel o Constancia PDF", "#06B6D4", self.import_file_requested.emit
        )
        self.act_import_file.setVisible(False)
        self.addAction(self.act_import_file)

        # 4. Operaciones de Datos (Exportar y Refrescar)
        self.act_export = self._create_action(
            "Exportar", "exportar", "Exportar datos a archivo", "#475569", self.export_requested.emit
        )
        self.addAction(self.act_export)

        self.act_clean = self._create_action(
            "Limpiar", "limpiar", "Limpiar datos y filtros de la vista", "#64748B", self.clean_requested.emit
        )
        self.act_clean.setVisible(False)
        self.addAction(self.act_clean)

        self.act_apply = self._create_action(
            "Aplicar\nCambios", "guardar", "Aplicar e importar cambios a la base de datos", "#10B981", self.apply_requested.emit
        )
        self.act_apply.setVisible(False)
        self.act_apply.setEnabled(False)
        self.addAction(self.act_apply)

        self.act_refresh = self._create_action(
            "Refrescar", "actualizar", "Recargar datos de la tabla (F5)", "#14B8A6", self.refresh_requested.emit
        )
        self.addAction(self.act_refresh)

        # 5. Ayuda y Diagnóstico
        self.act_help = self._create_action(
            "Ayuda", "ayuda", "Abrir guía de ayuda (F1)", "#2563EB", self.help_requested.emit
        )
        self.addAction(self.act_help)

    def set_actions_mode(self, mode: str = "default"):
        """Switches the toolbar action block between standard CRUD and specialized module workflows."""
        self._actions_mode = mode
        if mode == "viviendas":
            # Ocultar botones estándar Nuevo y Editar
            self.act_new.setVisible(False)
            self.act_edit.setVisible(False)
            self.act_new.setEnabled(False)
            self.act_edit.setEnabled(False)
            
            # Mostrar botones de importación
            self.act_template.setVisible(True)
            self.act_import_file.setVisible(True)
            self.act_clean.setVisible(True)
            self.act_apply.setVisible(True)
            self.act_export.setVisible(True)
            self.act_refresh.setVisible(True)
            self.act_help.setVisible(True)
        else:
            # Restaurar botones estándar
            self.act_new.setVisible(True)
            self.act_edit.setVisible(True)
            
            # Ocultar botones de importación
            self.act_template.setVisible(False)
            self.act_import_file.setVisible(False)
            self.act_clean.setVisible(False)
            self.act_apply.setVisible(False)
            self.act_export.setVisible(True)
            self.act_refresh.setVisible(True)
            self.act_help.setVisible(True)

    def _create_action(self, text: str, icon_name: str, tooltip: str, color: str, callback: Optional[Callable] = None) -> QAction:
        action = QAction(self)
        action.setText(text)
        action.setToolTip(tooltip)
        icon = Icons.get_icon(icon_name, size=24, color=color)
        if not icon.isNull():
            action.setIcon(icon)
        if callback:
            action.triggered.connect(lambda checked=False, cb=callback: cb())
        return action

    def _clear_module_actions(self):
        """Removes contextual module actions from the toolbar."""
        for act in self._module_actions:
            self.removeAction(act)
        self._module_actions.clear()

    def set_module_context(self, category: str, active_view_key: str = ""):
        """Dynamically populates the toolbar with actions specific to the active main module."""
        if category == "home" or not category:
            self.current_category = None
            self._clear_module_actions()
            self.act_home.setChecked(True)
            self.setVisible(False)
            return

        # Si el módulo cambia, reconstruir los botones contextuales
        if self.current_category != category:
            self._clear_module_actions()
            self.current_category = category

            # Definición contextual por categoría macro del menú
            module_items = self._get_category_items(category)

            # Insertar los botones de módulo antes del separador CRUD
            for label, icon_name, tooltip, color, view_key in module_items:
                act = self._create_action(
                    label, icon_name, tooltip, color,
                    lambda vk=view_key: self.view_requested.emit(vk)
                )
                act.setCheckable(True)
                act.setData(view_key)
                self.insertAction(self.sep_crud, act)
                self._module_actions.append(act)

        # Sincronizar resaltado de la acción activa
        self.act_home.setChecked(False)
        for act in self._module_actions:
            act.setChecked(act.data() == active_view_key)
        self.setVisible(True)

    def _get_category_items(self, category: str) -> list:
        """Returns standard metadata for the dynamic tools of each module."""
        if category == "SATC":
            return [
                ("Tipos de\nTrámite", "satc_tipos_tramite", "Catálogo de Tipos de Trámite SATC", "#3B82F6", "satc_tipos_tramite"),
                ("Estados de\nTrámite", "satc_estados_tramite", "Catálogo de Estados de Trámite SATC", "#10B981", "satc_estados_tramite"),
                ("Estados de\nVivienda", "satc_estados_vivienda", "Estados de Ciclo de Vivienda / UPE", "#F59E0B", "satc_estados_vivienda"),
                ("Regímenes\nmz", "satc_regimenes", "Regímenes en Condominio (SM, MZ, LT)", "#8B5CF6", "satc_regimenes"),
                ("Importación de\nViviendas", "satc_viviendas", "Padrón Maestro e Importación de Viviendas", "#06B6D4", "satc_viviendas"),
            ]
        elif category == "SEGURIDAD":
            return [
                ("Gestión de\nUsuarios", "usuarios", "Usuarios del Sistema", "#3B82F6", "usuarios"),
                ("Gestión de\nRoles", "roles", "Roles y Perfiles", "#8B5CF6", "roles"),
                ("Matriz de\nPermisos", "permisos", "Permisos de Acceso", "#6366F1", "permisos"),
                ("Módulos\nSistema", "modulos", "Módulos de la Aplicación", "#06B6D4", "app_modulos"),
                ("Catálogo de\nAcciones", "actividad", "Acciones del Sistema", "#2DD4BF", "acciones"),
            ]
        elif category == "CATALOGOS":
            return [
                ("Catálogos\nNegocio", "tabla", "Conceptos, Notarías y Desarrollos", "#10B981", "conceptos"),
                ("Geografía\nOperativa", "idioma", "Municipios y Delegaciones", "#2DD4BF", "geografia"),
                ("Padrón\nRFC", "documento_plantilla", "Contribuyentes Base", "#F59E0B", "rfcs"),
                ("Estados\nSistema", "validar", "Estados y Transiciones SAR", "#16A34A", "estados"),
            ]
        elif category == "PROCESOS":
            return [
                ("Carga Masiva\nReferencias", "documento_cargar", "Cargar Referencias Masivas", "#06B6D4", "carga_masiva"),
                ("Catálogo de\nUbicaciones", "tabla", "Cargar Ubicaciones", "#2DD4BF", "ubicaciones"),
                ("Migración y\nSync", "sincronizar", "Migración de Datos", "#6366F1", "migracion"),
                ("Reserva\nMasiva", "bloquear", "Reserva Masiva de Folios", "#F43F5E", "reserva_masiva"),
                ("Regularizar\nColaborador", "editar", "Asignación de Colaboradores", "#F59E0B", "regularizar_colaborador"),
                ("Fusión de\nLotes", "enlace", "Unificación de Lotes", "#2563EB", "fusion_lotes"),
                ("Escanear PDF\nFacturas", "documento_historial", "Escanear Delegaciones en Facturas", "#10B981", "update_facturas"),
            ]
        elif category == "CONFIGURACION":
            return [
                ("Parámetros\nGlobales", "parametros", "Configuraciones del Sistema", "#3B82F6", "parametros"),
                ("Selectores\nMotor Bot", "integraciones", "Localizadores y Reglas Web", "#8B5CF6", "localizadores"),
            ]
        return []

    def set_crud_enabled(self, can_add: bool, can_edit: bool):
        """Updates CRUD actions enabled state based on active view and selection."""
        self.act_new.setEnabled(can_add)
        self.act_edit.setEnabled(can_edit)
