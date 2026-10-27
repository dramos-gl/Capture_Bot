"""Circular Loading Dialog molecule for Design System."""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel

class CircularSpinner(QWidget):
    """Circular spinning loader using custom QPainter drawing with optional progress text."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.progress_text = ""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.timer.start(50)  # Rotate every 50ms
        self.setFixedSize(64, 64)
        self.setStyleSheet("background: transparent;")

    def set_progress(self, current: int, total: int):
        """Permite mostrar el avance numérico incremental dentro del spinner."""
        if total > 0:
            pct = int((current / total) * 100)
            self.progress_text = f"{pct}%"
        else:
            self.progress_text = str(current)
        self.update()

    def set_progress_text(self, text: str):
        """Permite asignar texto directo al centro del spinner (ej: '5/9' o '50%')."""
        self.progress_text = text
        self.update()

    def rotate(self):
        self.angle = (self.angle + 30) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Centro del widget
        cx = self.width() / 2
        cy = self.height() / 2
        radius = 22

        # 1. Dibujar pista de fondo (gris tenue)
        pen_track = QPen()
        pen_track.setWidth(4)
        pen_track.setCapStyle(Qt.RoundCap)
        pen_track.setColor(QColor("#E2E8F0"))
        painter.setPen(pen_track)
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        # 2. Dibujar segmento giratorio animado (Azul acento)
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle)
        pen_spinner = QPen()
        pen_spinner.setWidth(4)
        pen_spinner.setCapStyle(Qt.RoundCap)
        pen_spinner.setColor(QColor("#2563EB"))  # ACCENT color standard
        painter.setPen(pen_spinner)
        painter.drawArc(-radius, -radius, radius * 2, radius * 2, 0, 120 * 16)
        painter.restore()

        # 3. Dibujar texto numérico incremental centrado si está activo
        if self.progress_text:
            painter.setPen(QColor("#1E293B"))
            font = painter.font()
            font.setPointSize(9)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, self.progress_text)


class GLLoadingDialog(QDialog):
    """Frameless Modal Dialog showing a circular spinner and description message."""

    def __init__(self, message: str = "Procesando...", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(12)
        
        # Spinner widget
        self.spinner = CircularSpinner(self)
        self.main_layout.addWidget(self.spinner, alignment=Qt.AlignCenter)
        
        # Text label with word wrap and centered alignment
        self.label = CustomLabel(message, variant="body", parent=self)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background-color: transparent; font-size: 13px; font-weight: 500; color: #1E293B; line-height: 1.3;")
        self.main_layout.addWidget(self.label)
        
        # Base styling for modern floating card look
        self.setStyleSheet("""
            GLLoadingDialog {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 12px;
            }
        """)
        
        self.setFixedSize(280, 175)
        
    def set_message(self, message: str):
        """Allows dynamically updating the message on the dialog."""
        self.label.setText(message)

    def set_progress(self, current: int, total: int, extra_text: str = ""):
        """Actualiza el porcentaje numérico en el centro del spinner y opcionalmente el texto."""
        self.spinner.set_progress(current, total)
        if extra_text:
            self.label.setText(extra_text)
