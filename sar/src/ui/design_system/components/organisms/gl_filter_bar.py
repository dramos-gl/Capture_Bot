"""Filter Bar Organism for Data Tables."""

from typing import List, Callable, Optional
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QPushButton, QSizePolicy
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel

class FilterBar(QFrame):
    """A reusable filter bar containing search, state dropdown, and an action button."""
    
    def __init__(self, 
                 search_placeholder: str = "Buscar...",
                 state_options: Optional[List[str]] = None,
                 on_search: Optional[Callable[[str], None]] = None,
                 on_state_change: Optional[Callable[[str], None]] = None,
                 on_action: Optional[Callable[[], None]] = None,
                 action_icon_name: str = None,
                 action_tooltip: str = "Agregar / Actualizar",
                 parent=None):
        super().__init__(parent)
        self.setObjectName("filterBarFrame")
        
        from PySide6.QtCore import Qt
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(24)
        
        # Search Input
        self.inp_search = QLineEdit()
        self.inp_search.setObjectName("filterBarSearch")
        self.inp_search.setPlaceholderText(f"🔍 {search_placeholder}")
        self.inp_search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if on_search:
            self.inp_search.textChanged.connect(on_search)
            
        layout.addWidget(self.inp_search, stretch=1, alignment=Qt.AlignmentFlag.AlignBottom)
        
        # State Filter
        self.cmb_estado = None
        if state_options:
            from sar.src.ui.design_system.components.molecules.gl_labeled_combo import LabeledComboBox
            
            self.labeled_combo = LabeledComboBox("Estado", state_options)
            self.cmb_estado = self.labeled_combo.combo
            
            if on_state_change:
                self.cmb_estado.currentTextChanged.connect(on_state_change)
                
            layout.addWidget(self.labeled_combo, alignment=Qt.AlignmentFlag.AlignBottom)
            
        # Plus Button
        if on_action:
            self.btn_add = QPushButton()
            self.btn_add.setObjectName("filterBarActionBtn")
            self.btn_add.setFixedSize(40, 40)
            
            from sar.src.ui.design_system.utils.icons import Icons
            if action_icon_name and hasattr(Icons, action_icon_name):
                self.btn_add.setIcon(getattr(Icons, action_icon_name)())
                from PySide6.QtCore import QSize
                self.btn_add.setIconSize(QSize(20, 20))
            else:
                self.btn_add.setText("+")
            self.btn_add.setToolTip(action_tooltip)
            self.btn_add.clicked.connect(on_action)
            layout.addWidget(self.btn_add, alignment=Qt.AlignmentFlag.AlignBottom)
