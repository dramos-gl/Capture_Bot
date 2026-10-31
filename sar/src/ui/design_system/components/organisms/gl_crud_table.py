from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLineEdit, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.atoms.gl_input import CustomInput
from sar.src.ui.design_system.components.molecules.gl_card import CustomCard
from sar.src.ui.design_system.components.molecules.gl_pagination_footer import GLPaginationFooter
from sar.src.ui.design_system.utils.icons import Icons


class CrudTablePanel(CustomCard):
    """A generic panel containing a data table, header search bar and pagination footer framed as a card."""
    
    add_requested = Signal()
    item_selected = Signal(dict) # Emits on single click (for selection/master-detail)
    edit_requested = Signal(dict) # Emits on double click (for opening edit forms)
    
    def __init__(self, title: str, parent=None, default_page_size: int = 50):
        super().__init__(title="", parent=parent)
        self.setObjectName("cardFrame")
        self._all_data: List[Dict[str, Any]] = []
        self._filtered_data: List[Dict[str, Any]] = []
        self._current_page_data: List[Dict[str, Any]] = []
        self._headers: List[str] = []
        self._data_keys: List[str] = []
        
        # 1. Header controls (Title + Count Badge + Search Input aligned)
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(12)
        
        self.lbl_title = CustomLabel(title, variant="header")
        self.lbl_title.setObjectName("dashboardTableTitle")
        self.header_layout.addWidget(self.lbl_title)
        
        self.header_layout.addStretch()

        # Custom header widgets layout (inserted next to search input)
        self.header_custom_layout = QHBoxLayout()
        self.header_custom_layout.setContentsMargins(0, 0, 0, 0)
        self.header_custom_layout.setSpacing(8)
        self.header_layout.addLayout(self.header_custom_layout)

        self._custom_filter_predicate = None
        
        # Search input with magnifying glass icon
        self.search_input = CustomInput(control_size="md", parent=self)
        self.search_input.setObjectName("filterBarSearch")
        self.search_input.setPlaceholderText("Buscar...")
        self.search_input.setMinimumWidth(240)
        self.search_input.setMaximumWidth(420)
        self.search_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.addAction(Icons.search("#64748B"), QLineEdit.LeadingPosition)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.header_layout.addWidget(self.search_input)
        
        # Control de permisos y acciones (desacoplado de la renderización visual)
        self.btn_add = CustomButton("+ Nuevo")
        self.btn_add.hide()
        self.btn_add.clicked.connect(self.add_requested.emit)
        self._can_add = True
        
        def _set_add_visible(v: bool):
            self._can_add = bool(v)
        self.btn_add.setVisible = _set_add_visible
        self.btn_add.isVisible = lambda: self._can_add
        
        self.btn_edit = CustomButton("Editar")
        self.btn_edit.hide()
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self._on_edit_button_clicked)
        self._can_edit_permission = True
        
        def _set_edit_visible(v: bool):
            self._can_edit_permission = bool(v)
        self.btn_edit.setVisible = _set_edit_visible
        self.btn_edit.isVisible = lambda: self._can_edit_permission
        
        self.layout.addLayout(self.header_layout)
        
        # 2. Table
        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(26)

        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.itemDoubleClicked.connect(self._on_double_clicked)
        
        self.layout.addWidget(self.table)
        
        # 3. GLPaginationFooter Molecule (Corporativo)
        self.pagination_footer = GLPaginationFooter(self, default_page_size=default_page_size)
        self.pagination_footer.page_changed.connect(self._on_page_changed)
        self.pagination_footer.page_size_changed.connect(self._on_page_size_changed)
        self.layout.addWidget(self.pagination_footer)
        
    def set_header_button(self, text: str, callback, icon_name: str = 'guardar_nuevo', tooltip: str = ''):
        """Adds a visible semantic action button in the card header (ideal for master-detail detail panels)."""
        btn = CustomButton.action_agregar(parent=self)
        btn.setText(text)
        if tooltip:
            btn.setToolTip(tooltip)
        if icon_name and hasattr(Icons, icon_name):
            btn.setIcon(getattr(Icons, icon_name)('#FFFFFF'))
        btn.clicked.connect(callback)
        self.header_layout.addWidget(btn)
        return btn

    def setup_table(self, headers: list[str], data_keys: list[str]):
        """Sets up the table columns. data_keys map to the dictionary keys in data."""
        self._headers = headers
        self._data_keys = data_keys
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
    def populate(self, data: list[dict]):
        """Fills the table with a list of dictionaries with client-side pagination."""
        self._all_data = list(data) if data else []
        self._apply_filter_and_paginate(reset_page=True)
                
    def set_custom_filter(self, predicate):
        """Asigna un predicado de filtrado personalizado fn(item: dict) -> bool."""
        self._custom_filter_predicate = predicate
        self._apply_filter_and_paginate(reset_page=True)

    def _apply_filter_and_paginate(self, reset_page: bool = False):
        """Filters data according to search input, custom predicate and renders current slice in table."""
        search_term = self.search_input.text().strip().lower()
        data_pool = self._all_data
        if self._custom_filter_predicate:
            data_pool = [item for item in data_pool if self._custom_filter_predicate(item)]

        if not search_term:
            self._filtered_data = list(data_pool)
        else:
            self._filtered_data = [
                item for item in data_pool
                if any(search_term in str(item.get(k, "")).lower() for k in self._data_keys)
            ]

        if reset_page:
            self.pagination_footer.current_page = 1

        total_items = len(self._filtered_data)
        page_size = self.pagination_footer.page_size
        current_page = self.pagination_footer.current_page
        
        # In-memory slice calculation
        start_idx = (current_page - 1) * page_size
        end_idx = start_idx + page_size
        self._current_page_data = self._filtered_data[start_idx:end_idx]

        self.table.setRowCount(len(self._current_page_data))
        
        for row_idx, row_data in enumerate(self._current_page_data):
            for col_idx, key in enumerate(self._data_keys):
                val = row_data.get(key, "")
                if isinstance(val, bool):
                    val = "Activo" if val else "Inactivo"
                item = QTableWidgetItem(str(val))
                if col_idx == 0:
                    item.setData(Qt.UserRole, row_data)
                self.table.setItem(row_idx, col_idx, item)
        
        self.table.resizeColumnsToContents()
        if self.table.columnCount() > 0:
            self.table.horizontalHeader().setSectionResizeMode(self.table.columnCount() - 1, QHeaderView.ResizeMode.Stretch)

        # Update footer metadata
        self.pagination_footer.set_pagination(
            current_page=current_page,
            total_items=total_items,
            current_count=len(self._current_page_data)
        )
        self.btn_edit.setEnabled(False)

    def _on_search_text_changed(self, text: str):
        self._apply_filter_and_paginate(reset_page=True)

    def _on_page_changed(self, new_page: int):
        self.pagination_footer.current_page = new_page
        self._apply_filter_and_paginate(reset_page=False)

    def _on_page_size_changed(self, new_page_size: int):
        self.pagination_footer.page_size = new_page_size
        self._apply_filter_and_paginate(reset_page=True)

    def _on_selection_changed(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            self.btn_edit.setEnabled(False)
            return
            
        self.btn_edit.setEnabled(True)
        row = selected_items[0].row()
        item = self.table.item(row, 0)
        if item:
            data = item.data(Qt.UserRole)
            self.item_selected.emit(data)

    def _on_edit_button_clicked(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
        row = selected_items[0].row()
        item = self.table.item(row, 0)
        if item:
            data = item.data(Qt.UserRole)
            self.edit_requested.emit(data)

    def _on_double_clicked(self, item):
        row = item.row()
        first_col_item = self.table.item(row, 0)
        if first_col_item:
            data = first_col_item.data(Qt.UserRole)
            self.edit_requested.emit(data)

