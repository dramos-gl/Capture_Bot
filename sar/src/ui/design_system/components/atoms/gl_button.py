"""Primary and Secondary Button atoms."""

from PySide6.QtWidgets import QPushButton
from sar.src.ui.design_system.utils.icons import Icons

class CustomButton(QPushButton):
    """A styled button widget representing a basic UI Atom."""
    
    def __init__(self, text: str, is_secondary: bool = False, icon_name: str = None, parent=None):
        super().__init__(text, parent)
        if is_secondary:
            self.setObjectName("secondaryBtn")
        else:
            self.setObjectName("primaryBtn")
            
        if icon_name and hasattr(Icons, icon_name):
            self.setIcon(getattr(Icons, icon_name)())
