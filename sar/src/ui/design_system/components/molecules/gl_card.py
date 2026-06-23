"""Premium card wrapper molecule."""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel

class CustomCard(QFrame):
    """A card molecule designed to frame UI sections cleanly with design tokens."""
    
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        
        self.card_layout = QVBoxLayout(self)
        self.card_layout.setContentsMargins(16, 16, 16, 16)
        self.card_layout.setSpacing(12)
        
        if title:
            self.header = CustomLabel(title, variant="subheader")
            self.card_layout.addWidget(self.header)
            
        # Layout placeholder to add child widgets
        self.container = QWidget()
        self.container.setObjectName("cardContainer")
        self.container.setStyleSheet("QWidget#cardContainer { background-color: transparent; }")
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)
        self.card_layout.addWidget(self.container)
        
    def add_widget(self, widget: QWidget):
        """Adds a widget to the card container."""
        self.layout.addWidget(widget)
