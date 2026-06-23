"""Custom styled CheckBox atom."""

from PySide6.QtWidgets import QCheckBox

class CustomCheckBox(QCheckBox):
    """A styled checkbox widget representing a basic UI Atom."""
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        # Background is transparent, and style is governed by theme_manager QSS
        self.setObjectName("customCheckBox")
