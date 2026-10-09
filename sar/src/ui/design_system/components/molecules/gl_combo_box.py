from PySide6.QtWidgets import QComboBox
from PySide6.QtGui import QWheelEvent
from sar.src.ui.design_system.tokens.spacing import Spacing


class CustomComboBox(QComboBox):
    """A styled combobox integrated with the SAR design system and theme manager."""

    def __init__(self, parent=None, control_size: str = None):
        super().__init__(parent)
        self.setMinimumWidth(130)
        if control_size == "sm":
            self.setFixedHeight(Spacing.CONTROL_HEIGHT_COMPACT)
        elif control_size == "md":
            self.setFixedHeight(Spacing.CONTROL_HEIGHT_DEFAULT)
        elif control_size == "lg":
            self.setFixedHeight(Spacing.CONTROL_HEIGHT_LARGE)
        else:
            self.setFixedHeight(Spacing.CONTROL_HEIGHT_COMPACT)

    def wheelEvent(self, event: QWheelEvent):
        """Suppress passive wheel events when the dropdown popup is closed.

        This prevents accidental value changes on scroll/hover and propagates
        the wheel event to the parent scrollable container.
        """
        if self.view() is not None and self.view().isVisible():
            super().wheelEvent(event)
        else:
            event.ignore()
