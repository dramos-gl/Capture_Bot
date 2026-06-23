"""Custom styled Label atoms."""

from PySide6.QtWidgets import QLabel

class CustomLabel(QLabel):
    """A styled label widget representing a basic UI Atom."""
    
    def __init__(self, text: str = "", variant: str = "body", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("background-color: transparent;")
        if variant == "header":
            self.setObjectName("headerLabel")
        elif variant == "subheader":
            self.setObjectName("subheaderLabel")
        elif variant == "muted":
            self.setObjectName("mutedLabel")
        else:
            self.setObjectName("bodyLabel")
            
    def set_error_style(self, is_error: bool):
        """Highlights the label text as error color."""
        if is_error:
            self.setStyleSheet("color: #EF4444; font-weight: bold;")
        else:
            self.setStyleSheet("")
