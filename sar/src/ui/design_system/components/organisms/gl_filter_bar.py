"""Filter Bar Organism for Data Tables."""

from typing import List, Callable, Optional
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QPushButton, QSizePolicy
from PySide6.QtCore import Qt, QTimer, QSize
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.theme_manager import ThemeManager
from sar.src.ui.design_system.utils.icons import Icons

class FilterBar(QFrame):
    """A reusable filter bar containing search, search button, state dropdown, and an action button."""
    
    def __init__(self, 
                 search_placeholder: str = "Buscar...",
                 state_options: Optional[List[str]] = None,
                 on_search: Optional[Callable[[str], None]] = None,
                 on_state_change: Optional[Callable[[str], None]] = None,
                 on_action: Optional[Callable[[], None]] = None,
                 action_icon_name: str = None,
                 action_tooltip: str = "Agregar / Actualizar",
                 debounce_ms: int = 700,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("filterBarFrame")
        self._on_search_callback = on_search
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # Debounce timer para búsqueda responsiva sin latencia
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(debounce_ms)
        self._search_timer.timeout.connect(self._trigger_search)
        
        # Search Input
        self.inp_search = QLineEdit()
        self.inp_search.setObjectName("filterBarSearch")
        self.inp_search.setPlaceholderText(f"{search_placeholder}")
        self.inp_search.setFixedHeight(36)
        self.inp_search.setClearButtonEnabled(True)
        self.inp_search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.inp_search.addAction(Icons.search("#64748B"), QLineEdit.LeadingPosition)
        
        self.inp_search.textChanged.connect(self._on_text_changed)
        self.inp_search.returnPressed.connect(self._trigger_search)
        
        # Botón Buscar explícito
        self.btn_search = QPushButton()
        self.btn_search.setObjectName("secondaryBtn")
        self.btn_search.setIcon(Icons.buscar("#FFFFFF") if ThemeManager.is_dark_active() else Icons.buscar("#334155"))
        self.btn_search.setFixedSize(36, 36)
        self.btn_search.setToolTip("Buscar (o presione Enter)")
        self.btn_search.clicked.connect(self._trigger_search)

        if not search_placeholder and not on_search:
            self.inp_search.setVisible(False)
            self.btn_search.setVisible(False)
        else:
            layout.addWidget(self.inp_search, stretch=1)
            layout.addWidget(self.btn_search)
        
        # State Filter
        self.cmb_estado = None
        if state_options:
            from sar.src.ui.design_system.components.molecules.gl_labeled_combo import LabeledComboBox
            
            self.labeled_combo = LabeledComboBox("Estado", state_options)
            self.cmb_estado = self.labeled_combo.combo
            
            if on_state_change:
                self.cmb_estado.currentTextChanged.connect(on_state_change)
                
            layout.addWidget(self.labeled_combo)
            
        # Action / Plus Button
        if on_action:
            self.btn_add = QPushButton()
            self.btn_add.setObjectName("filterBarActionBtn")
            self.btn_add.setFixedSize(36, 36)
            
            if action_icon_name and hasattr(Icons, action_icon_name):
                self.btn_add.setIcon(getattr(Icons, action_icon_name)("#FFFFFF"))
                self.btn_add.setIconSize(QSize(20, 20))
            else:
                self.btn_add.setText("+")
            self.btn_add.setToolTip(action_tooltip)
            self.btn_add.clicked.connect(on_action)
            layout.addWidget(self.btn_add)

    def _on_text_changed(self, text: str):
        trimmed = text.strip()
        if not trimmed:
            self._search_timer.stop()
            self._trigger_search()
        else:
            self._search_timer.start()

    def _trigger_search(self):
        self._search_timer.stop()
        if self._on_search_callback:
            self._on_search_callback(self.inp_search.text().strip())
