"""Custom Styled Data Table Organism."""

from typing import List
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QWidget, QHBoxLayout
from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import Qt
from sar.src.ui.design_system.components.atoms.gl_badge import StatusBadge
from sar.src.ui.design_system.tokens.colors import Colors

class StatusTableWidgetItem(QTableWidgetItem):
    """A custom table widget item that stores the status string but exposes empty display text so Qt never paints it."""
    def __init__(self, text: str):
        super().__init__("")
        self.status_text = text
        
    def text(self) -> str:
        return self.status_text

class StyledDataTable(QTableWidget):
    """A clean, professional data table organism designed with our design system tokens."""
    
    def __init__(self, headers: List[str], parent=None):
        super().__init__(parent)
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # Configure table behavior
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setFocusPolicy(self.focusPolicy().NoFocus)
        self.setShowGrid(False)
        
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        
        # Styling headers
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setHighlightSections(False)
        header.setMinimumSectionSize(120)
        
        # Vertical header styling
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(36)
        
    def populate_rows(self, data: List[List[str]], checkable_first_col: bool = False):
        """Populates the table rows with string data and styled widgets."""
        self.setRowCount(0)
        self.setRowCount(len(data))
        
        status_cols = set()
        for row_idx, row_data in enumerate(data):
            for col_idx, value in enumerate(row_data):
                val_str = str(value)
                
                # Render state string as a StatusBadge pill
                if val_str in ["AUTORIZADA", "PENDIENTE", "ERROR", "GENERADA", "RECHAZADA", "FALLIDO", "EXPIRADA", "ASIGNADA", "BORRADOR", "ABIERTA", "PROCESANDO", "FINALIZADA", "CANCELADA", "PENDIENTE_AUTORIZACION", "AUTORIZACION_PENDIENTE", "COMPLETADA"]:
                    status_cols.add(col_idx)
                    badge_container = QWidget()
                    badge_container.setStyleSheet("background-color: transparent;")
                    badge_layout = QHBoxLayout(badge_container)
                    badge_layout.setContentsMargins(0, 0, 0, 0)
                    badge_layout.setAlignment(Qt.AlignCenter)
                    
                    badge = StatusBadge(val_str)
                    badge_layout.addWidget(badge)
                    
                    item = StatusTableWidgetItem(val_str)
                    self.setItem(row_idx, col_idx, item)
                    self.setCellWidget(row_idx, col_idx, badge_container)
                else:
                    item = QTableWidgetItem(val_str)
                    if checkable_first_col and col_idx == 0:
                        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                        item.setCheckState(Qt.CheckState.Unchecked)
                    
                    self.setItem(row_idx, col_idx, item)
        
        self.resizeColumnsToContents()
        
        # Adjust any status column width so it does not collapse to 0 width
        for col_idx in status_cols:
            self.setColumnWidth(col_idx, 140)
            self.horizontalHeader().setSectionResizeMode(col_idx, QHeaderView.ResizeMode.Interactive)
        
        # Enforce last column stretching to fill viewport width
        if self.columnCount() > 0:
            last_col = self.columnCount() - 1
            if last_col in status_cols:
                # If the last column is a status, let it be interactive/stretched with a minimum width
                self.setColumnWidth(last_col, 140)
            else:
                self.horizontalHeader().setSectionResizeMode(last_col, QHeaderView.ResizeMode.Stretch)
