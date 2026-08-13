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
    
    deleted = Signal(object)         # emits self
    changed = Signal()
    availability_requested = Signal(object)  # emits self when all active combos have valid selection
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("interactiveGridRow")
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(12)
        
        self._has_desarrollo = False
        self._all_desarrollos = []  # Tuplas (desarrollo_id, nombre, delegacion_id)
        
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
        
        self.combo_desarrollo = CustomComboBox()
        self.combo_desarrollo.setPlaceholderText("Desarrollo (Opcional)")
        self.combo_desarrollo.setMinimumWidth(150)
        self.combo_desarrollo.setVisible(False)
        
        self.spin_cantidad = QSpinBox()
        self.spin_cantidad.setMinimum(1)
        self.spin_cantidad.setMaximum(100000)
        self.spin_cantidad.setValue(1)
        self.spin_cantidad.setMinimumWidth(100)

        # Read-only availability label
        self.lbl_disponibles = QLabel("—")
        self.lbl_disponibles.setAlignment(Qt.AlignCenter)
        self.lbl_disponibles.setMinimumWidth(80)
        self.lbl_disponibles.setMaximumWidth(100)
        self.lbl_disponibles.setStyleSheet(
            "background: #F1F5F9; color: #94A3B8; border: 1px solid #E2E8F0; "
            "border-radius: 4px; padding: 4px 6px; font-size: 11px; font-weight: 600;"
        )
        
        self.btn_delete = CustomButton("", is_secondary=True)
        self.btn_delete.setIcon(Icons.trash())
        self.btn_delete.setFixedSize(30, 30)
        self.btn_delete.setStyleSheet("border: none;")
        self.btn_delete.clicked.connect(lambda: self.deleted.emit(self))
        
        self.layout.addWidget(self.combo_rfc, stretch=1)
        self.layout.addWidget(self.combo_concepto, stretch=1)
        self.layout.addWidget(self.combo_delegacion, stretch=1)
        self.layout.addWidget(self.combo_desarrollo, stretch=1)
        self.layout.addWidget(self.spin_cantidad)
        self.layout.addWidget(self.lbl_disponibles)
        self.layout.addWidget(self.btn_delete)
        
        self.combo_rfc.currentIndexChanged.connect(self._on_rfc_changed)
        self.combo_concepto.currentIndexChanged.connect(self._on_combo_changed)
        self.combo_delegacion.currentIndexChanged.connect(self._on_delegacion_changed)
        self.combo_desarrollo.currentIndexChanged.connect(self._on_combo_changed)
        self.spin_cantidad.valueChanged.connect(lambda _: self.changed.emit())

    def set_has_desarrollo(self, enabled: bool):
        self._has_desarrollo = enabled
        self.combo_desarrollo.setVisible(enabled)

    def _on_rfc_changed(self):
        self._update_desarrollo_options()
        self._on_combo_changed()

    def _on_delegacion_changed(self):
        self._update_desarrollo_options()
        self._on_combo_changed()

    def _update_desarrollo_options(self):
        if not self._has_desarrollo:
            return
        
        self.combo_desarrollo.blockSignals(True)
        self.combo_desarrollo.clear()
        self.combo_desarrollo.addItem("Cualquier Desarrollo", None)
        
        delegacion_id = self.combo_delegacion.currentData()
        
        # Tuplas: (desarrollo_id, nombre, delegacion_id, es_default)
        # La lista ya viene ordenada: defaults primero, luego alfabetico.
        for tpl in self._all_desarrollos:
            d_id, d_name, d_del_id = tpl[0], tpl[1], tpl[2]
            es_default = tpl[3] if len(tpl) > 3 else False
            # Si hay delegación seleccionada, filtrar por coincidencia
            if delegacion_id and d_del_id != delegacion_id:
                continue
            label = f"★ {d_name}" if es_default else d_name  # ★ marca el default
            self.combo_desarrollo.addItem(label, d_id)
            
        self.combo_desarrollo.blockSignals(False)

    def _on_combo_changed(self):
        self.changed.emit()
        # Request availability refresh only when all required combos have a valid selection
        if self.combo_rfc.currentData() and self.combo_concepto.currentData() and self.combo_delegacion.currentData():
            self.lbl_disponibles.setText("...")
            self.lbl_disponibles.setStyleSheet(
                "background: #F1F5F9; color: #94A3B8; border: 1px solid #E2E8F0; "
                "border-radius: 4px; padding: 4px 6px; font-size: 11px; font-weight: 600;"
            )
            self.availability_requested.emit(self)
        else:
            self.set_disponibles(None)

    def set_disponibles(self, count):
        """Update the read-only availability label with semaphoric color."""
        if count is None:
            self.lbl_disponibles.setText("—")
            self.lbl_disponibles.setStyleSheet(
                "background: #F1F5F9; color: #94A3B8; border: 1px solid #E2E8F0; "
                "border-radius: 4px; padding: 4px 6px; font-size: 11px; font-weight: 600;"
            )
            return
        requested = self.spin_cantidad.value()
        if count == 0:
            icon, bg, fg, border = "✗", "#FEF2F2", "#DC2626", "#FECACA"
        elif count < requested:
            icon, bg, fg, border = "⚠", "#FFFBEB", "#D97706", "#FDE68A"
        else:
            icon, bg, fg, border = "✓", "#F0FDF4", "#16A34A", "#BBF7D0"
        self.lbl_disponibles.setText(f"{icon} {count}")
        self.lbl_disponibles.setStyleSheet(
            f"background: {bg}; color: {fg}; border: 1px solid {border}; "
            f"border-radius: 4px; padding: 4px 6px; font-size: 11px; font-weight: 600;"
        )
        
    def populate(self, rfcs, conceptos, delegaciones, desarrollos=None):
        """Populates combo boxes with provided data.
        - rfcs, conceptos, delegaciones: lists of tuples (id, display_text)
        - desarrollos: list of tuples (desarrollo_id, nombre, delegacion_id, es_default)
          already sorted defaults-first.
        """
        for r_id, r_text in rfcs:
            self.combo_rfc.addItem(r_text, r_id)
            
        for c_id, c_text in conceptos:
            self.combo_concepto.addItem(c_text, c_id)
            
        for d_id, d_text in delegaciones:
            self.combo_delegacion.addItem(d_text, d_id)
            
        if desarrollos:
            self._all_desarrollos = desarrollos
            self._update_desarrollo_options()

    def set_values(self, rfc_id, concepto_id, delegacion_id, cantidad, cantidad_generada=0, desarrollo_id=None):
        """Pre-selects options and sets quantity on row creation/loading."""
        self._cantidad_generada = cantidad_generada
        
        idx_rfc = self.combo_rfc.findData(rfc_id)
        if idx_rfc >= 0:
            self.combo_rfc.setCurrentIndex(idx_rfc)
            
        idx_concepto = self.combo_concepto.findData(concepto_id)
        if idx_concepto >= 0:
            self.combo_concepto.setCurrentIndex(idx_concepto)
            
        idx_delegacion = self.combo_delegacion.findData(delegacion_id)
        if idx_delegacion >= 0:
            self.combo_delegacion.setCurrentIndex(idx_delegacion)
            
        if self._has_desarrollo and desarrollo_id is not None:
            self._update_desarrollo_options()
            idx_des = self.combo_desarrollo.findData(desarrollo_id)
            if idx_des >= 0:
                self.combo_desarrollo.setCurrentIndex(idx_des)
            
        self.spin_cantidad.setValue(cantidad)
        
        # If references have already been generated, lock fields
        if cantidad_generada > 0:
            self.combo_rfc.setEnabled(False)
            self.combo_concepto.setEnabled(False)
            self.combo_delegacion.setEnabled(False)
            self.combo_desarrollo.setEnabled(False)
            self.btn_delete.setEnabled(False)
            # Only allow increasing the quantity (minimum is the current quantity)
            self.spin_cantidad.setMinimum(cantidad)
        else:
            self.combo_rfc.setEnabled(True)
            self.combo_concepto.setEnabled(True)
            self.combo_delegacion.setEnabled(True)
            self.combo_desarrollo.setEnabled(True)
            self.btn_delete.setEnabled(True)
            self.spin_cantidad.setMinimum(1)

    def get_data(self) -> dict:
        return {
            "rfc_id": self.combo_rfc.currentData(),
            "concepto_id": self.combo_concepto.currentData(),
            "delegacion_id": self.combo_delegacion.currentData(),
            "desarrollo_id": self.combo_desarrollo.currentData() if self._has_desarrollo else None,
            "cantidad": self.spin_cantidad.value(),
            "cantidad_generada": getattr(self, "_cantidad_generada", 0)
        }


class InteractiveGrid(QWidget):
    """Dynamic grid container for multiple entry rows."""
    
    data_changed = Signal()
    save_triggered = Signal()
    cancel_triggered = Signal()
    availability_requested = Signal(object)  # re-emits row's availability_requested
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(12)
        
        self._has_desarrollo = False
        
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
        
        self.btn_cancel = QPushButton("Cancelar Edición", self)
        self.btn_cancel.setObjectName("secondaryBtn")
        self.btn_cancel.setMinimumHeight(35)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self.cancel_triggered.emit)
        
        self.btn_save = QPushButton("Guardar Orden", self)
        self.btn_save.setObjectName("primaryBtn")
        self.btn_save.setMinimumHeight(35)
        self.btn_save.clicked.connect(self.save_triggered.emit)
        
        self.header_layout.addWidget(self.btn_add)
        self.header_layout.addWidget(self.btn_cancel)
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
        
        # Table Headers — use same spacing/margins as rows (8px margin, 12px spacing)
        self.table_header_layout = QHBoxLayout()
        self.table_header_layout.setContentsMargins(8, 4, 8, 4)
        self.table_header_layout.setSpacing(12)

        self.lbl_h_rfc = CustomLabel("Empresa (RFC)", variant="body")
        self.lbl_h_rfc.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 600;")

        self.lbl_h_concepto = CustomLabel("Concepto", variant="body")
        self.lbl_h_concepto.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 600;")

        self.lbl_h_del = CustomLabel("Delegación", variant="body")
        self.lbl_h_del.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 600;")

        self.lbl_h_desarrollo = CustomLabel("Desarrollo", variant="body")
        self.lbl_h_desarrollo.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 600;")
        self.lbl_h_desarrollo.setVisible(False)

        self.lbl_h_cant = CustomLabel("Cantidad", variant="body")
        self.lbl_h_cant.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 600;")
        self.lbl_h_cant.setMinimumWidth(100)
        self.lbl_h_cant.setMaximumWidth(120)

        self.lbl_h_disp = CustomLabel("Disponibles", variant="body")
        self.lbl_h_disp.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 600;")
        self.lbl_h_disp.setMinimumWidth(80)
        self.lbl_h_disp.setMaximumWidth(100)
        self.lbl_h_disp.setAlignment(Qt.AlignCenter)

        self.lbl_h_empty = CustomLabel("", variant="body")
        self.lbl_h_empty.setFixedSize(30, 20)

        # Build initial layout
        self.table_header_layout.addWidget(self.lbl_h_rfc, stretch=1)
        self.table_header_layout.addWidget(self.lbl_h_concepto, stretch=1)
        self.table_header_layout.addWidget(self.lbl_h_del, stretch=1)
        self.table_header_layout.addWidget(self.lbl_h_desarrollo, stretch=1)
        self.table_header_layout.addWidget(self.lbl_h_cant)
        self.table_header_layout.addWidget(self.lbl_h_disp)
        self.table_header_layout.addWidget(self.lbl_h_empty)
        
        self.rows_layout.addLayout(self.table_header_layout)
        
        self.scroll_area.setWidget(self.rows_container)
        self.main_layout.addWidget(self.scroll_area)
        
        self.rows = []
        
        # Stored catalog data
        self._rfcs = []
        self._conceptos = []
        self._delegaciones = []
        self._desarrollos = []

    def set_has_desarrollo(self, enabled: bool):
        self._has_desarrollo = enabled
        self.lbl_h_desarrollo.setVisible(enabled)
        # Update existing rows if any
        for r in self.rows:
            r.set_has_desarrollo(enabled)
        
    def set_catalogs(self, rfcs, conceptos, delegaciones, desarrollos=None):
        self._rfcs = rfcs
        self._conceptos = conceptos
        self._delegaciones = delegaciones
        if desarrollos:
            self._desarrollos = desarrollos
        
    def set_third_column_label(self, label: str):
        """Deprecated: kept for compatibility. The third column is always Delegación."""
        pass  # Third column (lbl_h_del) is always 'Delegación'; do not override

    def add_row(self):
        row_widget = InteractiveGridRow(self.rows_container)
        row_widget.set_has_desarrollo(self._has_desarrollo)
        row_widget.populate(self._rfcs, self._conceptos, self._delegaciones, self._desarrollos)
        row_widget.deleted.connect(self._remove_row)
        row_widget.changed.connect(self.data_changed.emit)
        row_widget.availability_requested.connect(self.availability_requested.emit)
        
        self.rows_layout.addWidget(row_widget)
        self.rows.append(row_widget)
        self._update_badge()
        self.data_changed.emit()

    def add_row_with_data(self, rfc_id, concepto_id, delegacion_id, cantidad, cantidad_generada=0, desarrollo_id=None):
        row_widget = InteractiveGridRow(self.rows_container)
        row_widget.set_has_desarrollo(self._has_desarrollo)
        row_widget.populate(self._rfcs, self._conceptos, self._delegaciones, self._desarrollos)
        row_widget.set_values(rfc_id, concepto_id, delegacion_id, cantidad, cantidad_generada, desarrollo_id)
        row_widget.deleted.connect(self._remove_row)
        row_widget.changed.connect(self.data_changed.emit)
        row_widget.availability_requested.connect(self.availability_requested.emit)
        
        self.rows_layout.addWidget(row_widget)
        self.rows.append(row_widget)
        self._update_badge()
        self.data_changed.emit()

    def update_row_availability(self, row: InteractiveGridRow, count: int):
        """Update the availability label for a specific row. Safe to call from any thread."""
        if row in self.rows:
            row.set_disponibles(count)
        
    def _remove_row(self, row_widget: InteractiveGridRow):
        self.rows_layout.removeWidget(row_widget)
        self.rows.remove(row_widget)
        row_widget.deleteLater()
        self._update_badge()
        self.data_changed.emit()

    def _update_badge(self):
        self.lbl_badge.setText(str(len(self.rows)))
        
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

    def get_desarrollo_text(self, id_val):
        # Tuplas: (desarrollo_id, nombre, delegacion_id, es_default) — el 4to elemento es opcional
        for tpl in self._desarrollos:
            if tpl[0] == id_val:
                return tpl[1]
        return None
