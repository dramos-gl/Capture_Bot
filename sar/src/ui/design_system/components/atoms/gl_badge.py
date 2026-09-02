"""Status Badge Atom for representing states with rounded pills and icons."""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from sar.src.ui.design_system.utils.icons import Icons
from sar.src.ui.design_system.tokens.colors import Colors


class StatusBadge(QFrame):
    """A pill badge representing visual state statuses with corresponding color tokens and icons."""

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.raw_text = text
        self.setObjectName("statusBadge")
        self.setFixedHeight(22)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 0, 8, 0)
        self.layout.setSpacing(4)
        self.layout.setAlignment(Qt.AlignCenter)

        self.label = QLabel(text.upper().strip())
        self.label.setAlignment(Qt.AlignCenter)

        normalized = text.upper().strip()
        variant = "neutral"
        icon_name = None
        icon_color = Colors.SLATE_500

        if "AUTORIZADA" in normalized or "COMPLETA" in normalized or "FINALIZADA" in normalized or "DISPONIBLE" in normalized:
            variant = "success"
            icon_name = "check"
            icon_color = Colors.SUCCESS
        elif "ASIGNADA" in normalized or "ASIGNADO" in normalized:
            variant = "assigned"
            icon_name = "clock"
            icon_color = Colors.ASSIGNED
        elif "RESERVADA" in normalized or "RESERVADO" in normalized or "APARTADA" in normalized or "APARTADO" in normalized:
            variant = "reserved"
            icon_name = "clock"
            icon_color = Colors.RESERVED
        elif "GENERADA" in normalized or "ABIERTA" in normalized or "EMITIDA" in normalized:
            variant = "accent"
            icon_name = "clock"
            icon_color = Colors.ACCENT
        elif "PENDIENTE" in normalized or "ESPERA" in normalized or "PROCESANDO" in normalized:
            variant = "warning"
            icon_name = "clock"
            icon_color = Colors.WARNING
        elif "ERROR" in normalized or "FALLIDO" in normalized or "RECHAZADA" in normalized or "EXPIRADA" in normalized or "CANCELADA" in normalized or "VENCIDA" in normalized:
            variant = "error"
            icon_name = "alert_triangle"
            icon_color = Colors.ERROR
        else:
            variant = "neutral"
            icon_name = "clock"
            icon_color = Colors.SLATE_500

        self.setProperty("badge_variant", variant)

        if icon_name and hasattr(Icons, icon_name):
            lbl_icon = QLabel(self)
            lbl_icon.setStyleSheet("background: transparent; border: none;")
            lbl_icon.setPixmap(getattr(Icons, icon_name)(icon_color).pixmap(12, 12))
            self.layout.addWidget(lbl_icon)

        self.layout.addWidget(self.label)

    def text(self) -> str:
        return self.label.text()
