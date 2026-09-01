"""Status Badge Atom for representing states with rounded pills and icons."""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from sar.src.ui.design_system.utils.icons import Icons

from sar.src.ui.design_system.tokens.colors import Colors

class StatusBadge(QFrame):
    """A pill badge representing visual state statuses with corresponding color tokens and icons."""
    
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(22)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 0, 8, 0)
        self.layout.setSpacing(4)
        self.layout.setAlignment(Qt.AlignCenter)
        
        self.label = QLabel(text.upper().strip())
        self.label.setAlignment(Qt.AlignCenter)
        
        # Default colors
        color = Colors.SLATE_500
        bg_color = Colors.NEUTRAL_BG
        icon_name = None
        
        normalized = text.upper().strip()
        if "AUTORIZADA" in normalized or "COMPLETA" in normalized or "FINALIZADA" in normalized:
            color = Colors.SUCCESS  # Green
            bg_color = Colors.SUCCESS_BG
            icon_name = "check"
        elif "GENERADA" in normalized or "ABIERTA" in normalized:
            color = Colors.ACCENT  # Blue
            bg_color = Colors.ACCENT_BG
            icon_name = "clock"
        elif "PENDIENTE" in normalized or "ESPERA" in normalized or "ASIGNADA" in normalized or "PROCESANDO" in normalized:
            color = Colors.WARNING  # Orange/Amber
            bg_color = Colors.WARNING_BG
            icon_name = "clock"
        elif "ERROR" in normalized or "FALLIDO" in normalized or "RECHAZADA" in normalized or "EXPIRADA" in normalized or "CANCELADA" in normalized:
            color = Colors.ERROR  # Red
            bg_color = Colors.ERROR_BG
            icon_name = "alert_triangle"
        elif "SUSTITUIDO" in normalized or "BORRADOR" in normalized:
            color = Colors.SLATE_500  # Gray/Neutral
            bg_color = Colors.NEUTRAL_BG
            icon_name = "clock"
            
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 10px;
                border: none;
            }}
            QLabel {{
                color: {color};
                font-weight: bold;
                font-size: 10px;
                background: transparent;
                border: none;
            }}
        """)
        
        if icon_name and hasattr(Icons, icon_name):
            self.lbl_icon = QLabel()
            self.lbl_icon.setStyleSheet("background: transparent; border: none;")
            self.lbl_icon.setPixmap(getattr(Icons, icon_name)(color).pixmap(12, 12))
            self.layout.addWidget(self.lbl_icon)
            
        self.layout.addWidget(self.label)
        
    def text(self) -> str:
        return self.label.text()
