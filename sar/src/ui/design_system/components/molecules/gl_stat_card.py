"""Stat Card Molecule with left icon, status styling, and sparkline wave graph."""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QWidget, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.utils.icons import Icons

class SparklineWidget(QWidget):
    """Draws a smooth wavy sparkline path natively using QPainter."""
    
    def __init__(self, color_hex: str, parent=None):
        super().__init__(parent)
        self.color_hex = color_hex
        self.setFixedHeight(35)
        self.setStyleSheet("background: transparent;")
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Transparent background draw
        painter.fillRect(self.rect(), Qt.transparent)
        
        pen = QPen(QColor(self.color_hex), 2)
        painter.setPen(pen)
        
        path = QPainterPath()
        w = self.width()
        h = self.height()
        
        # Smooth bezier sparkline path
        path.moveTo(0, h * 0.7)
        path.cubicTo(w * 0.25, h * 0.9, w * 0.35, h * 0.1, w * 0.5, h * 0.6)
        path.cubicTo(w * 0.65, h * 0.9, w * 0.8, h * 0.2, w, h * 0.5)
        
        painter.drawPath(path)


class StatCard(QFrame):
    """A molecular component representing a KPI stat card styled to match the target mockup design."""
    
    def __init__(self, title: str, initial_value: str = "0", icon_name: str = None, color_hex: str = "#2563EB", parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setMinimumWidth(200)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 12)
        self.layout.setSpacing(12)
        
        # Header layout (Icon on Left + Text on Right)
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(12)
        
        # Convert hex to rgba for the 10% opacity background
        h = color_hex.lstrip('#')
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        rgba_bg = f"rgba({r}, {g}, {b}, 0.1)"
        
        # Left Icon Frame with 10% opacity colored background
        self.icon_frame = QFrame(self)
        self.icon_frame.setFixedSize(48, 48)
        self.icon_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {rgba_bg};
                border-radius: 12px;
            }}
        """)
        
        self.icon_layout = QVBoxLayout(self.icon_frame)
        self.icon_layout.setContentsMargins(0, 0, 0, 0)
        self.icon_layout.setAlignment(Qt.AlignCenter)
        
        self.lbl_icon = QLabel(self.icon_frame)
        self.lbl_icon.setStyleSheet("background: transparent;")
        if icon_name and hasattr(Icons, icon_name):
            icon_fn = getattr(Icons, icon_name)
            self.lbl_icon.setPixmap(icon_fn(color_hex).pixmap(24, 24))
            
        self.icon_layout.addWidget(self.lbl_icon)
        self.header_layout.addWidget(self.icon_frame)
        
        # Right Text Layout (Title + Large Value + Label)
        self.text_layout = QVBoxLayout()
        self.text_layout.setContentsMargins(0, 0, 0, 0)
        self.text_layout.setSpacing(2)
        
        self.lbl_title = CustomLabel(title, variant="body")
        self.lbl_title.setObjectName("statCardTitle")
        
        self.lbl_value = CustomLabel(initial_value, variant="header")
        self.lbl_value.setStyleSheet(f"color: {color_hex}; font-size: 32px; font-weight: bold; background: transparent;")
        
        self.lbl_sub = CustomLabel("Referencias", variant="muted")
        self.lbl_sub.setObjectName("statCardSub")
        
        self.text_layout.addWidget(self.lbl_title)
        self.text_layout.addWidget(self.lbl_value)
        self.text_layout.addWidget(self.lbl_sub)
        
        self.header_layout.addLayout(self.text_layout)
        self.header_layout.addStretch()
        
        self.layout.addLayout(self.header_layout)
        
        # Bottom Sparkline wave graph
        self.sparkline = SparklineWidget(color_hex, self)
        self.layout.addWidget(self.sparkline)
        
    def set_value(self, val: str):
        self.lbl_value.setText(val)
