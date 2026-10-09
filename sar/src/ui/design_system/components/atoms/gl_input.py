from PySide6.QtWidgets import QLineEdit
from sar.src.ui.design_system.tokens.spacing import Spacing

class CustomInput(QLineEdit):
    """A styled line edit input field representing a basic UI Atom."""
    
    def __init__(self, placeholder: str = "", is_password: bool = False, control_size: str = None, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        if is_password:
            self.setEchoMode(QLineEdit.EchoMode.Password)
            
        if control_size == "sm":
            self.setFixedHeight(Spacing.CONTROL_HEIGHT_COMPACT)
        elif control_size == "md":
            self.setFixedHeight(Spacing.CONTROL_HEIGHT_DEFAULT)
        elif control_size == "lg":
            self.setFixedHeight(Spacing.CONTROL_HEIGHT_LARGE)

