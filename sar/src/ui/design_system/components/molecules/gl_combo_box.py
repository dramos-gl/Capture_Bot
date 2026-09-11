"""Custom ComboBox Molecule."""

from PySide6.QtWidgets import QComboBox
from PySide6.QtGui import QWheelEvent


class CustomComboBox(QComboBox):
    """A styled combobox integrated with the SAR design system and theme manager."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(130)
        self.setFixedHeight(36)

    def wheelEvent(self, event: QWheelEvent):
        """Suppress passive wheel events when the dropdown popup is closed.

        This prevents accidental value changes on scroll/hover and propagates
        the wheel event to the parent scrollable container.
        """
        if self.view() is not None and self.view().isVisible():
            super().wheelEvent(event)
        else:
            event.ignore()
