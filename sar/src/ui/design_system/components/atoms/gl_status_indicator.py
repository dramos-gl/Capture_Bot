"""Status Indicator Atom for network path availability checking."""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QSize
from sar.src.ui.design_system.utils.icons import Icons
from sar.src.ui.design_system.tokens.colors import Colors

class GLStatusIndicator(QFrame):
    """An atomic widget indicating connection/path status (Green/Red/Orange)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(24)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 0, 8, 0)
        self.layout.setSpacing(6)
        self.layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        self.lbl_icon = QLabel()
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        self.lbl_icon.setFixedSize(14, 14)
        
        self.lbl_text = QLabel("VERIFICANDO...")
        self.lbl_text.setStyleSheet("font-size: 10px; font-weight: bold; background: transparent; border: none;")
        
        self.layout.addWidget(self.lbl_icon)
        self.layout.addWidget(self.lbl_text)
        
        self.set_status("checking")
        
    def set_status(self, status: str, message: str = ""):
        """
        Updates the indicator visual state.
        status options: 'online' | 'offline' | 'checking'
        """
        status = status.lower().strip()
        
        if status == "online":
            bg_color = Colors.SUCCESS_BG
            text_color = Colors.SUCCESS
            icon_pixmap = Icons.check(Colors.SUCCESS).pixmap(12, 12)
            display_text = "CONECTADO" if not message else message.upper()
        elif status == "offline":
            bg_color = Colors.ERROR_BG
            text_color = Colors.ERROR
            icon_pixmap = Icons.alert_triangle(Colors.ERROR).pixmap(12, 12)
            display_text = "SIN ACCESO" if not message else message.upper()
        else: # checking
            bg_color = Colors.WARNING_BG
            text_color = Colors.WARNING
            icon_pixmap = Icons.clock(Colors.WARNING).pixmap(12, 12)
            display_text = "VERIFICANDO..." if not message else message.upper()
            
        self.lbl_icon.setPixmap(icon_pixmap)
        self.lbl_text.setText(display_text)
        self.lbl_text.setStyleSheet(f"color: {text_color}; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 12px;
                border: 1px solid {text_color}33;
            }}
        """)
