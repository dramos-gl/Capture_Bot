"""Custom ComboBox Molecule."""

import os
from PySide6.QtWidgets import QComboBox

class CustomComboBox(QComboBox):
    """A styled combobox with a custom dropdown arrow."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'assets', 'icons', 'chevron_down.svg'))
        icon_path = icon_path.replace('\\', '/')
        
        self.setStyleSheet(f"""
            QComboBox {{ 
                padding: 2px 10px; 
                height: 35px;
                min-height: 35px;
                max-height: 35px;
                border: 1px solid #cbd5e1; 
                border-radius: 8px; 
                background-color: white; 
                min-width: 150px;
                color: #1e293b;
                font-size: 13px;
            }}
            QComboBox:focus {{
                border: 2px solid #3b82f6;
            }}
            QComboBox::drop-down {{ 
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: url("{icon_path}");
                width: 16px;
                height: 16px;
                margin-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                background-color: white;
                selection-background-color: #f1f5f9;
                selection-color: #1e293b;
                outline: none;
            }}
        """)
