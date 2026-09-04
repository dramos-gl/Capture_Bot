"""Stat Card Molecule with left icon, status styling, and sparkline wave graph."""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QSizePolicy
from PySide6.QtCore import Qt, Signal
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
    clicked = Signal()
    double_clicked = Signal()
    
    def __init__(self, title: str, initial_value: str = "0", icon_name: str = None, color_hex: str = "#2563EB", show_sparkline: bool = True, parent=None, subtitle: str = "Derechos"):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setMinimumWidth(80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setCursor(Qt.PointingHandCursor)
        
        self.color_hex = color_hex
        self._current_value = initial_value
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 8)
        self.layout.setSpacing(6)
        
        # 1. Title at the top spanning full width
        self.lbl_title = CustomLabel(title, variant="body")
        self.lbl_title.setObjectName("statCardTitle")
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setStyleSheet("font-weight: bold; background: transparent;")
        self.layout.addWidget(self.lbl_title)
        
        # 2. Content layout (Icon on Left + Value/Sub on Right)
        self.content_layout = QHBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        
        # Convert hex to rgba for the 10% opacity background
        h = color_hex.lstrip('#')
        r = int(h[0:2], 16) if len(h) >= 6 else 37
        g = int(h[2:4], 16) if len(h) >= 6 else 99
        b = int(h[4:6], 16) if len(h) >= 6 else 235
        rgba_bg = f"rgba({r}, {g}, {b}, 0.1)"
        
        # Left Icon Frame
        self.icon_frame = QFrame(self)
        self.icon_frame.setFixedSize(38, 38)
        self.icon_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {rgba_bg};
                border-radius: 10px;
            }}
        """)
        
        self.icon_layout = QVBoxLayout(self.icon_frame)
        self.icon_layout.setContentsMargins(0, 0, 0, 0)
        self.icon_layout.setAlignment(Qt.AlignCenter)
        
        self.lbl_icon = QLabel(self.icon_frame)
        self.lbl_icon.setStyleSheet("background: transparent;")
        if icon_name and hasattr(Icons, icon_name):
            icon_fn = getattr(Icons, icon_name)
            self.lbl_icon.setPixmap(icon_fn(color_hex).pixmap(20, 20))
            
        self.icon_layout.addWidget(self.lbl_icon)
        self.content_layout.addWidget(self.icon_frame)
        
        # Right Value & Sub layout
        self.value_layout = QVBoxLayout()
        self.value_layout.setContentsMargins(0, 0, 0, 0)
        self.value_layout.setSpacing(0)
        
        self.lbl_value = CustomLabel(initial_value, variant="header")
        self.lbl_value.setScaledContents(False)
        self.lbl_value.setStyleSheet(f"color: {color_hex}; font-weight: bold; background: transparent;")
        
        self.lbl_sub = CustomLabel(subtitle, variant="muted")
        self.lbl_sub.setObjectName("statCardSub")
        self.lbl_sub.setWordWrap(True)
        
        self.value_layout.addWidget(self.lbl_value)
        self.value_layout.addWidget(self.lbl_sub)
        
        self.content_layout.addLayout(self.value_layout, stretch=1)
        self.layout.addLayout(self.content_layout)
        
        # Bottom Sparkline wave graph (Conditional)
        if show_sparkline:
            self.sparkline = SparklineWidget(color_hex, self)
            self.layout.addWidget(self.sparkline)
        else:
            self.sparkline = None
            
        self._update_font_sizes()
        
    def _update_font_sizes(self):
        """Calculates dynamic font size based on current widget width and text length."""
        w = max(self.width(), 90)
        text_len = max(len(str(self._current_value)), 1)
        
        # Compute suitable font size (between 13px and 22px)
        # Factor width available for text: roughly total width minus icon (38px) and margins (~35px)
        available_w = max(w - 75, 45)
        # Estimate char width based on size
        calculated_size = int((available_w * 1.5) / text_len)
        font_size = max(13, min(calculated_size, 22))
        
        self.lbl_value.setStyleSheet(
            f"color: {self.color_hex}; font-size: {font_size}px; font-weight: bold; background: transparent;"
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_font_sizes()
        
    def set_value(self, val: str):
        self._current_value = val
        self.lbl_value.setText(val)
        self._update_font_sizes()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)

