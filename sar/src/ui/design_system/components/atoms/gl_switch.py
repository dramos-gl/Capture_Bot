"""Custom switch/toggle widget implementing a modern toggle control."""

from PySide6.QtWidgets import QAbstractButton
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt, QRect, QPropertyAnimation, Property, QSize
from sar.src.ui.design_system.tokens.colors import Colors

class CustomSwitch(QAbstractButton):
    """A custom toggle switch styled like a capsule track with a circular thumb."""
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self._thumb_position = 0.0  # 0.0 (unchecked) to 1.0 (checked)
        self.setCursor(Qt.PointingHandCursor)
        
        self._anim = QPropertyAnimation(self, b"thumb_position", self)
        self._anim.setDuration(120)
        
        # Color Tokens
        self.color_track_checked = QColor(Colors.ACCENT_BLUE)
        self.color_track_unchecked = QColor("#D1D5DB")  # Neutral gray
        self.color_thumb = QColor("#4B5563")  # Slate gray (as in the legacy image)
        
    @Property(float)
    def thumb_position(self) -> float:
        return self._thumb_position
        
    @thumb_position.setter
    def thumb_position(self, pos: float):
        self._thumb_position = pos
        self.update()
        
    def nextCheckState(self):
        super().nextCheckState()
        end_val = 1.0 if self.isChecked() else 0.0
        self._anim.stop()
        self._anim.setEndValue(end_val)
        self._anim.start()
        
    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._thumb_position = 1.0 if checked else 0.0
        self.update()
        
    def sizeHint(self) -> QSize:
        font_metrics = self.fontMetrics()
        text_width = font_metrics.horizontalAdvance(self.text())
        height = max(24, font_metrics.height())
        # Track (44px) + spacing (10px) + text
        return QSize(44 + 10 + text_width, height)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        h = self.height()
        
        # 1. Draw capsule track
        track_h = 16
        track_w = 38
        track_y = (h - track_h) // 2
        track_rect = QRect(2, track_y, track_w, track_h)
        
        # Interpolate track background color
        c_checked = self.color_track_checked
        c_unchecked = self.color_track_unchecked
        r = int(c_unchecked.red() + (c_checked.red() - c_unchecked.red()) * self._thumb_position)
        g = int(c_unchecked.green() + (c_checked.green() - c_unchecked.green()) * self._thumb_position)
        b = int(c_unchecked.blue() + (c_checked.blue() - c_unchecked.blue()) * self._thumb_position)
        track_color = QColor(r, g, b)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(track_color))
        painter.drawRoundedRect(track_rect, track_h / 2, track_h / 2)
        
        # 2. Draw circular thumb/handle
        thumb_d = 20
        # Calculate dynamic X position based on interpolation
        thumb_min_x = 0
        thumb_max_x = track_w - thumb_d + 4
        thumb_x = int(thumb_min_x + (thumb_max_x - thumb_min_x) * self._thumb_position)
        thumb_y = (h - thumb_d) // 2
        thumb_rect = QRect(thumb_x, thumb_y, thumb_d, thumb_d)
        
        painter.setBrush(QBrush(self.color_thumb))
        painter.drawEllipse(thumb_rect)
        
        # 3. Draw text label
        if self.text():
            font_metrics = self.fontMetrics()
            text_y = (h - font_metrics.height()) // 2 + font_metrics.ascent()
            text_x = track_w + 12
            
            # Use theme text color from stylesheet context
            painter.setPen(QPen(QColor(Colors.TEXT_LIGHT_PRIMARY)))
            painter.drawText(text_x, text_y, self.text())
