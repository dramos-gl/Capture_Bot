"""Phone Input Molecule with Formatting and Locking."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLineEdit, QToolButton
from PySide6.QtCore import Qt, Signal
import re
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.atoms.gl_input import CustomInput
from sar.src.ui.design_system.components.molecules.gl_labeled_input import LabeledInput
from sar.src.ui.design_system.utils.icons import Icons

def format_phone(raw_value: str) -> str:
    """Formats a 10 digit string into (XXX) XXX XXXX."""
    digits = "".join(filter(str.isdigit, raw_value))
    if not digits:
        return ""
    if len(digits) <= 3:
        return f"({digits}"
    elif len(digits) <= 6:
        return f"({digits[:3]}) {digits[3:]}"
    else:
        return f"({digits[:3]}) {digits[3:6]} {digits[6:10]}"

class PhoneLineEdit(LabeledInput):
    """Component specialized for 10-digit phone numbers with formatting and locking."""
    
    def __init__(self, label_text: str = "Teléfono (10 dígitos)", parent=None):
        super().__init__(label_text=label_text, parent=parent)
        
        self.input.setMaxLength(14)  # (999) 999 9999
        self.set_validator(r"^\(\d{3}\)\s\d{3}\s\d{4}$", "Formato inválido. Ingrese 10 dígitos.")
        
        # Add Edit/Lock Button
        self.edit_btn = self.input.addAction(Icons.edit(), QLineEdit.TrailingPosition)
        self.edit_btn.triggered.connect(self.toggle_edit)
        
        self.input.textChanged.connect(self._on_phone_text_changed)
        self._is_formatting = False
        
        self.set_edit_mode(True)

    def _on_phone_text_changed(self, text):
        if self._is_formatting:
            return
            
        self._is_formatting = True
        formatted = format_phone(text)
        if self.input.text() != formatted:
            self.input.setText(formatted)
        self._is_formatting = False

    def value(self) -> str:
        """Returns pure 10 digits for DB."""
        return "".join(filter(str.isdigit, self.input.text()))

    def set_value(self, val: str):
        """Accepts pure digits and formats them."""
        self.set_text(format_phone(val))

    def toggle_edit(self):
        """Toggles read-only state."""
        is_locked = self.input.isReadOnly()
        self.input.setReadOnly(not is_locked)
        if not is_locked:
            self.edit_btn.setIcon(Icons.lock()) # Locked state
            self.input.setStyleSheet("color: #64748B;") # Muted when locked
        else:
            self.edit_btn.setIcon(Icons.edit())
            self.input.setStyleSheet("")

    def set_edit_mode(self, is_editing: bool, current_value: str = ""):
        self.set_value(current_value)
        self.input.setReadOnly(not is_editing)
        if not is_editing:
            self.edit_btn.setIcon(Icons.lock())
            self.input.setStyleSheet("color: #64748B;")
        else:
            self.edit_btn.setIcon(Icons.edit())
            self.input.setStyleSheet("")
