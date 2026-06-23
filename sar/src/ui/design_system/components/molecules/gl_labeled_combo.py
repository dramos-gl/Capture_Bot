"""Labeled ComboBox Molecule."""

from typing import List, Optional
from PySide6.QtWidgets import QGroupBox, QVBoxLayout
from sar.src.ui.design_system.components.molecules.gl_combo_box import CustomComboBox

class LabeledComboBox(QGroupBox):
    """An outlined combobox with a floating label (fieldset style)."""
    
    def __init__(self, label_text: str, options: Optional[List[str]] = None, parent=None):
        super().__init__(label_text, parent)
        
        self.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                margin-top: 14px;
                font-weight: bold;
                color: #2563EB;
                font-size: 11px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        
        self.combo = CustomComboBox()
        # Override combo box border so the groupbox acts as the only border
        self.combo.setStyleSheet(self.combo.styleSheet() + "\nQComboBox { border: none; background-color: white; min-width: 130px; }")
        
        if options:
            self.combo.addItems(options)
            
        layout.addWidget(self.combo)
