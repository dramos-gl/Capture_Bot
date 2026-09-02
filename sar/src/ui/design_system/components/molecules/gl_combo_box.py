"""Custom ComboBox Molecule."""

from PySide6.QtWidgets import QComboBox


class CustomComboBox(QComboBox):
    """A styled combobox integrated with the SAR design system and theme manager."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(130)
        self.setFixedHeight(36)
