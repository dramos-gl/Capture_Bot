"""Custom styled RadioButton atom adhering to SAR Atomic Design."""

from PySide6.QtWidgets import QRadioButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor

class CustomRadioButton(QRadioButton):
    """A styled radio button widget representing a basic UI Atom."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        # Background is transparent, and style is governed centrally by ThemeManager QSS
        self.setObjectName("customRadioButton")

        # UX Improvements
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFocusPolicy(Qt.NoFocus)
