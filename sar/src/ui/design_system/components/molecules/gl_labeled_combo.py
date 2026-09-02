"""Labeled ComboBox Molecule."""

from typing import List, Optional
from PySide6.QtWidgets import QGroupBox, QVBoxLayout
from sar.src.ui.design_system.components.molecules.gl_combo_box import CustomComboBox


class LabeledComboBox(QGroupBox):
    """An outlined combobox with a floating label (fieldset style)."""

    def __init__(self, label_text: str, options: Optional[List[str]] = None, parent=None):
        super().__init__(label_text, parent)
        self.setObjectName("labeledGroup")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.combo = CustomComboBox(self)
        self.combo.setFixedHeight(35)

        if options:
            self.combo.addItems(options)

        layout.addWidget(self.combo)
