"""Custom LineEdit input atom."""

from PySide6.QtWidgets import QLineEdit

class CustomInput(QLineEdit):
    """A styled line edit input field representing a basic UI Atom."""
    
    def __init__(self, placeholder: str = "", is_password: bool = False, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        if is_password:
            self.setEchoMode(QLineEdit.EchoMode.Password)
