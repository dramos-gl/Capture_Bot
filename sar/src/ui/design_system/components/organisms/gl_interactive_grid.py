"""Interactive Grid Organism for dynamic data entry."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QComboBox, QSpinBox,
    QPushButton, QFrame, QToolButton, QMenu, QLabel
)
from PySide6.QtCore import Qt, Signal
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.molecules.gl_combo_box import CustomComboBox
from sar.src.ui.design_system.utils.icons import Icons

class InteractiveGridRow(QFrame):
    """A single row in the interactive grid."""
    
    deleted = Signal(object) # emits self
    changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("interactiveGridRow")
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(12)
        
        # Widgets
        self.combo_rfc = CustomComboBox()
        self.combo_rfc.setPlaceholderText("Seleccionar RFC")
        self.combo_rfc.setMinimumWidth(150)
        
        self.combo_concepto = CustomComboBox()
        self.combo_concepto.setPlaceholderText("Seleccionar Concepto")
        self.combo_concepto.setMinimumWidth(150)
        
        self.combo_delegacion = CustomComboBox()
        self.combo_delegacion.setPlaceholderText("Delegación")
        self.combo_delegacion.setMinimumWidth(120)
        
        self.spin_cantidad = QSpinBox()
        self.spin_cantidad.setMinimum(1)
        self.spin_cantidad.setMaximum(100000)
        self.spin_cantidad.setValue(1)
        self.spin_cantidad.setMinimumWidth(100)
        
        self.btn_delete = CustomButton("", is_secondary=True)
        self.btn_delete.setIcon(Icons.trash())
        self.btn_delete.setFixedSize(30, 30)
        self.btn_delete.setStyleSheet("border: none;")
        self.btn_delete.clicked.connect(lambda: self.deleted.emit(self))
        
        self.layout.addWidget(self.combo_rfc)
        self.layout.addWidget(self.combo_concepto)
        self.layout.addWidget(self.combo_delegacion)
        self.layout.addWidget(self.spin_cantidad)
        self.layout.addWidget(self.btn_delete)
        
        self.combo_rfc.currentIndexChanged.connect(lambda _: self.changed.emit())
        self.combo_concepto.currentIndexChanged.connect(lambda _: self.changed.emit())
        self.combo_delegacion.currentIndexChanged.connect(lambda _: self.changed.emit())
        self.spin_cantidad.valueChanged.connect(lambda _: self.changed.emit())
        
    def populate(self, rfcs, conceptos, delegaciones):
        """Populates combo boxes with provided data. Lists of tuples (id, display_text)"""
        for r_id, r_text in rfcs:
            self.combo_rfc.addItem(r_text, r_id)
            
        for c_id, c_text in conceptos:
            self.combo_concepto.addItem(c_text, c_id)
            
        for d_id, d_text in delegaciones:
            self.combo_delegacion.addItem(d_text, d_id)

    def get_data(self) -> dict:
        return {
            "rfc_id": self.combo_rfc.currentData(),
            "concepto_id": self.combo_concepto.currentData(),
            "delegacion_id": self.combo_delegacion.currentData(),
            "cantidad": self.spin_cantidad.value()
        }


class InteractiveGrid(QWidget):
    """Dynamic grid container for multiple entry rows."""
    
    data_changed = Signal()
    save_triggered = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(12)
        
        # Header layout
        self.header_layout = QHBoxLayout()
        
        self.lbl_title = CustomLabel("Partidas", variant="header")
        self.lbl_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.header_layout.addWidget(self.lbl_title)
        
        # Add badge count
        self.lbl_badge = QLabel("1", self)
        self.lbl_badge.setObjectName("gridBadge")
        self.header_layout.addWidget(self.lbl_badge)
        
        self.header_layout.addStretch()
        
        # Buttons
        self.btn_add = QPushButton("+ Agregar Renglón", self)
        self.btn_add.setObjectName("primaryBtn")
        self.btn_add.setMinimumHeight(35)
        self.btn_add.clicked.connect(self.add_row)
        
        self.btn_save = QPushButton("Guardar Orden", self)
        self.btn_save.setObjectName("primaryBtn")
        self.btn_save.setMinimumHeight(35)
        self.btn_save.clicked.connect(self.save_triggered.emit)
        
        self.header_layout.addWidget(self.btn_add)
        self.header_layout.addWidget(self.btn_save)
        
        self.main_layout.addLayout(self.header_layout)
        
        # Scroll area for rows
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.rows_container = QWidget()
        self.rows_container.setObjectName("rowsContainer")
        self.rows_container.setStyleSheet("QWidget#rowsContainer { background-color: transparent; }")
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setAlignment(Qt.AlignTop)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(8)
        
        # Table Headers
        table_header_layout = QHBoxLayout()
        table_header_layout.setContentsMargins(8, 0, 8, 0)
        table_header_layout.setSpacing(12)
        
        lbl_h_rfc = CustomLabel("Empresa (RFC)", variant="body")
        lbl_h_rfc.setMinimumWidth(150)
        lbl_h_concepto = CustomLabel("Concepto", variant="body")
        lbl_h_concepto.setMinimumWidth(150)
        lbl_h_del = CustomLabel("Delegación", variant="body")
        lbl_h_del.setMinimumWidth(120)
        lbl_h_cant = CustomLabel("Cantidad", variant="body")
        lbl_h_cant.setMinimumWidth(100)
        lbl_h_empty = CustomLabel("", variant="body")
        lbl_h_empty.setFixedSize(30, 20)
        
        table_header_layout.addWidget(lbl_h_rfc)
        table_header_layout.addWidget(lbl_h_concepto)
        table_header_layout.addWidget(lbl_h_del)
        table_header_layout.addWidget(lbl_h_cant)
        table_header_layout.addWidget(lbl_h_empty)
        
        self.rows_layout.addLayout(table_header_layout)
        
        self.scroll_area.setWidget(self.rows_container)
        self.main_layout.addWidget(self.scroll_area)
        
        self.rows = []
        
        # Stored catalog data
        self._rfcs = []
        self._conceptos = []
        self._delegaciones = []
        
    def set_catalogs(self, rfcs, conceptos, delegaciones):
        self._rfcs = rfcs
        self._conceptos = conceptos
        self._delegaciones = delegaciones
        
    def add_row(self):
        row_widget = InteractiveGridRow(self.rows_container)
        row_widget.populate(self._rfcs, self._conceptos, self._delegaciones)
        row_widget.deleted.connect(self._remove_row)
        row_widget.changed.connect(self.data_changed.emit)
        
        self.rows_layout.addWidget(row_widget)
        self.rows.append(row_widget)
        self.data_changed.emit()
        
    def _remove_row(self, row_widget: InteractiveGridRow):
        self.rows_layout.removeWidget(row_widget)
        self.rows.remove(row_widget)
        row_widget.deleteLater()
        self.data_changed.emit()
        
    def get_all_data(self) -> list:
        return [row.get_data() for row in self.rows]
    
    def clear(self):
        for row in list(self.rows):
            self._remove_row(row)
            
    def get_rfc_text(self, id_val):
        for r_id, r_text in self._rfcs:
            if r_id == id_val: return r_text
        return None
        
    def get_concepto_text(self, id_val):
        for c_id, c_text in self._conceptos:
            if c_id == id_val: return c_text
        return None
        
    def get_delegacion_text(self, id_val):
        for d_id, d_text in self._delegaciones:
            if d_id == id_val: return d_text
        return None
