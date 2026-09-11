"""Primary and Secondary Button atoms."""

from PySide6.QtWidgets import QPushButton
from sar.src.ui.design_system.utils.icons import Icons
from sar.src.ui.design_system.tokens.colors import Colors

class CustomButton(QPushButton):
    """A styled button widget representing a basic UI Atom."""
    
    DEFAULT_MIN_WIDTH = 110

    # Semantic action presets (text, is_secondary, icon_name, tooltip, object_name)
    VARIANTS = {
        "autorizar": ("Autorizar", False, "aceptar", "Autorizar elemento seleccionado", "primaryBtn"),
        "rechazar": ("Rechazar", True, "rechazar", "Rechazar elemento seleccionado", "outlineDangerBtn"),
        "cancelar": ("Cancelar", False, "cancelar", "Cancelar y cerrar", "dangerBtn"),
        "cerrar": ("Cerrar", False, "cancelar", "Cerrar ventana", "dangerBtn"),
        "editar": ("Editar", True, "editar", "Editar elemento seleccionado", "secondaryBtn"),
        "agregar": ("Agregar", True, "guardar_nuevo", "Agregar nuevo elemento", "secondaryBtn"),
        "guardar": ("Guardar", False, "guardar", "Guardar cambios", "primaryBtn"),
        "asignar": ("Asignar", True, "usuario", "Asignar elemento", "secondaryBtn"),
        "buscar": ("Buscar", True, "buscar", "Buscar o consultar", "secondaryBtn"),
        "excel": ("Generar", True, "excel", "Generar y exportar archivos Excel", "secondaryBtn"),
        "pdf": ("Generar", True, "pdf", "Generar y exportar archivos PDF", "secondaryBtn"),
    }
    
    def __init__(
        self,
        text: str = "",
        is_secondary: bool = False,
        icon_name: str = None,
        is_clean_btn: bool = False,
        min_width: int = None,
        variant: str = None,
        parent=None
    ):
        v_obj = None
        # Apply semantic variant defaults if specified
        if variant and variant.lower() in self.VARIANTS:
            v_text, v_sec, v_icon, v_tip, v_obj = self.VARIANTS[variant.lower()]
            text = text or v_text
            is_secondary = v_sec if is_secondary is False else is_secondary
            icon_name = icon_name or v_icon
            if min_width is None:
                min_width = self.DEFAULT_MIN_WIDTH

        super().__init__(text, parent)

        if v_obj:
            self.setObjectName(v_obj)
        elif is_secondary or is_clean_btn:
            self.setObjectName("secondaryBtn")
        else:
            self.setObjectName("primaryBtn")
            
        if is_clean_btn:
            self.setIcon(Icons.get_icon("limpiar", color=Colors.TEXT_LIGHT_SECONDARY))
        elif icon_name:
            if icon_name == "excel":
                self.setIcon(Icons.excel())
            elif icon_name == "pdf":
                self.setIcon(Icons.pdf())
            elif icon_name == "rechazar":
                self.setIcon(Icons.rechazar(Colors.ERROR))
            elif icon_name == "cancelar":
                is_danger = (self.objectName() == "dangerBtn")
                self.setIcon(Icons.cancelar("#FFFFFF" if is_danger else Colors.ERROR))
            elif icon_name == "aceptar":
                self.setIcon(Icons.aceptar("#FFFFFF"))
            elif icon_name == "editar":
                self.setIcon(Icons.editar(Colors.TEXT_LIGHT_PRIMARY))
            elif hasattr(Icons, icon_name):
                self.setIcon(getattr(Icons, icon_name)())
            
        if min_width:
            self.setMinimumWidth(min_width)

        if variant and variant.lower() in self.VARIANTS:
            _, _, _, v_tip, _ = self.VARIANTS[variant.lower()]
            if not self.toolTip():
                self.setToolTip(v_tip)

    # Class factory helpers for standard design system actions
    @classmethod
    def action_autorizar(cls, parent=None, min_width: int = DEFAULT_MIN_WIDTH) -> "CustomButton":
        return cls(variant="autorizar", min_width=min_width, parent=parent)

    @classmethod
    def action_rechazar(cls, parent=None, min_width: int = DEFAULT_MIN_WIDTH) -> "CustomButton":
        return cls(variant="rechazar", min_width=min_width, parent=parent)

    @classmethod
    def action_cancelar(cls, parent=None, min_width: int = DEFAULT_MIN_WIDTH) -> "CustomButton":
        return cls(variant="cancelar", min_width=min_width, parent=parent)

    @classmethod
    def action_cerrar(cls, parent=None, min_width: int = DEFAULT_MIN_WIDTH) -> "CustomButton":
        return cls(variant="cerrar", min_width=min_width, parent=parent)

    @classmethod
    def action_editar(cls, parent=None, min_width: int = DEFAULT_MIN_WIDTH) -> "CustomButton":
        return cls(variant="editar", min_width=min_width, parent=parent)

    @classmethod
    def action_asignar(cls, parent=None, min_width: int = DEFAULT_MIN_WIDTH) -> "CustomButton":
        return cls(variant="asignar", min_width=min_width, parent=parent)

    @classmethod
    def action_agregar(cls, parent=None, min_width: int = DEFAULT_MIN_WIDTH) -> "CustomButton":
        return cls(variant="agregar", min_width=min_width, parent=parent)

    @classmethod
    def action_guardar(cls, parent=None, min_width: int = DEFAULT_MIN_WIDTH) -> "CustomButton":
        return cls(variant="guardar", min_width=min_width, parent=parent)

    @classmethod
    def action_buscar(cls, parent=None, min_width: int = DEFAULT_MIN_WIDTH) -> "CustomButton":
        return cls(variant="buscar", min_width=min_width, parent=parent)

    @classmethod
    def action_excel(cls, parent=None, min_width: int = DEFAULT_MIN_WIDTH) -> "CustomButton":
        return cls(variant="excel", min_width=min_width, parent=parent)

    @classmethod
    def action_pdf(cls, parent=None, min_width: int = DEFAULT_MIN_WIDTH) -> "CustomButton":
        return cls(variant="pdf", min_width=min_width, parent=parent)
