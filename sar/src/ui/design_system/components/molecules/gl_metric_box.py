"""Metric Box Molecule for displaying metrics with a colored side border."""

from PySide6.QtWidgets import QFrame, QVBoxLayout
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel

class MetricBox(QFrame):
    """A card-like frame that displays a title and a large metric value."""
    
    def __init__(self, title: str, value: str, color: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(72)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-left: 4px solid {color};
                border-radius: 6px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)
        
        lbl_title = CustomLabel(title, variant="muted")
        lbl_title.setStyleSheet("font-weight: bold; color: #6b7280; font-size: 11px;")
        layout.addWidget(lbl_title)
        
        self.lbl_value = CustomLabel(value, variant="header")
        self.lbl_value.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {color};")
        layout.addWidget(self.lbl_value)
        
    def set_value(self, value: str):
        """Updates the displayed metric value."""
        self.lbl_value.setText(value)
