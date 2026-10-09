from PySide6.QtWidgets import QSpinBox
from PySide6.QtGui import QWheelEvent
from sar.src.ui.design_system.tokens.spacing import Spacing


class CustomSpinBox(QSpinBox):
    """A styled spinbox integrated with the SAR design system.

    Suppresses passive wheel events to prevent accidental value alterations
    on scroll/hover and ensures events propagate smoothly to parent scroll areas.
    """

    def __init__(self, parent=None, control_size: str = None):
        super().__init__(parent)
        if control_size == "sm":
            self.setFixedHeight(Spacing.CONTROL_HEIGHT_COMPACT)
        elif control_size == "md":
            self.setFixedHeight(Spacing.CONTROL_HEIGHT_DEFAULT)
        elif control_size == "lg":
            self.setFixedHeight(Spacing.CONTROL_HEIGHT_LARGE)
        else:
            self.setFixedHeight(Spacing.CONTROL_HEIGHT_COMPACT)

    def wheelEvent(self, event: QWheelEvent):
        """Suppress passive wheel events so parent scrollable containers can scroll."""
        event.ignore()
