"""Custom SpinBox atom with passive scroll protection."""

from PySide6.QtWidgets import QSpinBox
from PySide6.QtGui import QWheelEvent


class CustomSpinBox(QSpinBox):
    """A styled spinbox integrated with the SAR design system.

    Suppresses passive wheel events to prevent accidental value alterations
    on scroll/hover and ensures events propagate smoothly to parent scroll areas.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)

    def wheelEvent(self, event: QWheelEvent):
        """Suppress passive wheel events so parent scrollable containers can scroll."""
        event.ignore()
