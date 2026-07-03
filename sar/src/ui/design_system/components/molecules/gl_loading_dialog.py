"""Circular Loading Dialog molecule for Design System."""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel

class CircularSpinner(QWidget):
    """Circular spinning loader using custom QPainter drawing."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.timer.start(50)  # Rotate every 50ms
        self.setFixedSize(50, 50)
        self.setStyleSheet("background: transparent;")

    def rotate(self):
        self.angle = (self.angle + 30) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Center origin
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self.angle)
        
        # Pen setup
        pen = QPen()
        pen.setWidth(4)
        pen.setCapStyle(Qt.RoundCap)
        
        # Faint gray track background
        pen.setColor(QColor("#E2E8F0"))
        painter.setPen(pen)
        painter.drawArc(-18, -18, 36, 36, 0, 360 * 16)
        
        # Blue spinning segment
        pen.setColor(QColor("#2563EB"))  # ACCENT color standard
        painter.setPen(pen)
        painter.drawArc(-18, -18, 36, 36, 0, 120 * 16)


class GLLoadingDialog(QDialog):
    """Frameless Modal Dialog showing a circular spinner and description message."""

    def __init__(self, message: str = "Procesando...", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setModal(True)
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)
        
        # Spinner widget
        self.spinner = CircularSpinner(self)
        self.main_layout.addWidget(self.spinner, alignment=Qt.AlignCenter)
        
        # Text label
        self.label = CustomLabel(message, variant="body", parent=self)
        self.label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.label)
        
        # Base styling for modern floating card look
        self.setStyleSheet("""
            GLLoadingDialog {
                background-color: #FFFFFF;
                border: 2px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        
        self.setFixedSize(220, 150)
        
    def set_message(self, message: str):
        """Allows dynamically updating the message on the dialog."""
        self.label.setText(message)
