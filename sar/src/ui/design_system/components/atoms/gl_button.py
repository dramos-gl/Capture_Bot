"""Primary and Secondary Button atoms."""

from PySide6.QtWidgets import QPushButton
from sar.src.ui.design_system.utils.icons import Icons

class CustomButton(QPushButton):
    """A styled button widget representing a basic UI Atom."""
    
    def __init__(self, text: str, is_secondary: bool = False, icon_name: str = None, is_clean_btn: bool = False, parent=None):
        super().__init__(text, parent)
        if is_secondary or is_clean_btn:
            self.setObjectName("secondaryBtn")
        else:
            self.setObjectName("primaryBtn")
            
        if is_clean_btn:
            self.setIcon(Icons.get_icon("limpiar", color="#475569"))
        elif icon_name and hasattr(Icons, icon_name):
            self.setIcon(getattr(Icons, icon_name)())
