"""Custom styled CheckBox atom."""

from PySide6.QtWidgets import QCheckBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor

class CustomCheckBox(QCheckBox):
    """A styled checkbox widget representing a basic UI Atom."""
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        # Background is transparent, and style is governed by theme_manager QSS
        self.setObjectName("customCheckBox")
        
        # UX Improvements
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFocusPolicy(Qt.StrongFocus)
