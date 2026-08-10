"""Generic CRUD Table Organism."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLineEdit
)
from PySide6.QtCore import Qt, Signal
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel

class CrudTablePanel(QWidget):
    """A generic panel containing a data table, search bar and add button."""
    
    add_requested = Signal()
    item_selected = Signal(dict) # Emits on single click (for selection/master-detail)
    edit_requested = Signal(dict) # Emits on double click (for opening edit forms)
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(16)
        
        # Header controls
        self.header_layout = QHBoxLayout()
        self.lbl_title = CustomLabel(title, variant="header")
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar...")
        self.search_input.setFixedWidth(200)

        self.search_input.textChanged.connect(self._filter_table)
        
        self.btn_add = CustomButton("+ Nuevo")
        self.btn_add.clicked.connect(self.add_requested.emit)
        
        self.btn_edit = CustomButton("Editar")
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self._on_edit_button_clicked)
        
        self.header_layout.addWidget(self.lbl_title)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.search_input)
        self.header_layout.addWidget(self.btn_add)
        self.header_layout.addWidget(self.btn_edit)
        
        self.layout.addLayout(self.header_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.verticalHeader().setVisible(False)

        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.itemDoubleClicked.connect(self._on_double_clicked)
        
        self.layout.addWidget(self.table)
        
        self._current_data = []
        self._headers = []
        
    def setup_table(self, headers: list[str], data_keys: list[str]):
        """Sets up the table columns. data_keys map to the dictionary keys in data."""
        self._headers = headers
        self._data_keys = data_keys
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
    def populate(self, data: list[dict]):
        """Fills the table with a list of dictionaries."""
        self._current_data = data
        self.table.setRowCount(len(data))
        
        for row_idx, row_data in enumerate(data):
            for col_idx, key in enumerate(self._data_keys):
                val = row_data.get(key, "")
                if isinstance(val, bool):
                    val = "Activo" if val else "Inactivo"
                item = QTableWidgetItem(str(val))
                # Store the original dict in the first column for easy retrieval
                if col_idx == 0:
                    item.setData(Qt.UserRole, row_data)
                self.table.setItem(row_idx, col_idx, item)
        
        self.table.resizeColumnsToContents()
        
        # Enforce last column stretching to fill viewport width
        if self.table.columnCount() > 0:
            self.table.horizontalHeader().setSectionResizeMode(self.table.columnCount() - 1, QHeaderView.ResizeMode.Stretch)
                
    def _on_selection_changed(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            self.btn_edit.setEnabled(False)
            return
            
        self.btn_edit.setEnabled(True)
        # The data is stored in the first column of the selected row
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
            
    def _filter_table(self, text: str):
        text = text.lower()
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)
