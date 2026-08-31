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
    """A single row in the interactive grid.

    Supports two operating modes controlled by ``cascade_mode``:

    * ``False`` (default / legacy): All combos are independent —
      used by ``grid_individual`` (manual assignment).
    * ``True`` (apartar mode): Desarrollo → RFC → Delegación → Concepto
      cascade with smart auto-complete from ``desarrollo_empresa``.
    """

    deleted = Signal(object)         # emits self
    changed = Signal()
    availability_requested = Signal(object)  # emits self when all active combos are valid
    # Emitted in cascade_mode when the row needs dynamic data from the service layer
    cascade_rfcs_needed = Signal(object, int)          # (self, desarrollo_id)
    cascade_delegaciones_needed = Signal(object, int, int)  # (self, desarrollo_id, rfc_id)
    cascade_conceptos_needed = Signal(object, int, int)     # (self, rfc_id, delegacion_id)

    def __init__(self, parent=None, cascade_mode: bool = False):
        super().__init__(parent)
        self.setObjectName("interactiveGridRow")

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(12)

        self._has_desarrollo = False
        self._all_desarrollos = []  # Legacy: Tuplas (desarrollo_id, nombre, delegacion_id, es_default)
        self._cascade_mode = cascade_mode

        # ── Widgets ──────────────────────────────────────────────────────────

        # Desarrollo
        self.combo_desarrollo = CustomComboBox()
        self.combo_desarrollo.setPlaceholderText("Seleccionar Desarrollo")
        self.combo_desarrollo.setMinimumWidth(160)
        self.combo_desarrollo.setVisible(False)

        # RFC / Empresa
        self.combo_rfc = CustomComboBox()
        self.combo_rfc.setPlaceholderText("Seleccionar RFC")
        self.combo_rfc.setMinimumWidth(150)

        # Delegación
        self.combo_delegacion = CustomComboBox()
        self.combo_delegacion.setPlaceholderText("Delegación")
        self.combo_delegacion.setMinimumWidth(120)

        # Concepto
        self.combo_concepto = CustomComboBox()
        self.combo_concepto.setPlaceholderText("Seleccionar Concepto")
        self.combo_concepto.setMinimumWidth(150)

        # Cantidad
        self.spin_cantidad = QSpinBox()
        self.spin_cantidad.setMinimum(1)
        self.spin_cantidad.setMaximum(100000)
        self.spin_cantidad.setValue(1)
        self.spin_cantidad.setMinimumWidth(100)

        # Disponibles (semáforo read-only)
        self.lbl_disponibles = QLabel("—")
        self.lbl_disponibles.setAlignment(Qt.AlignCenter)
        self.lbl_disponibles.setMinimumWidth(80)
        self.lbl_disponibles.setMaximumWidth(100)
        self.lbl_disponibles.setStyleSheet(
            "background: #F1F5F9; color: #94A3B8; border: 1px solid #E2E8F0; "
            "border-radius: 4px; padding: 4px 6px; font-size: 11px; font-weight: 600;"
        )

        # Delete button
        self.btn_delete = CustomButton("", is_secondary=True)
        self.btn_delete.setIcon(Icons.trash())
        self.btn_delete.setFixedSize(30, 30)
        self.btn_delete.setStyleSheet("border: none;")
        self.btn_delete.clicked.connect(lambda: self.deleted.emit(self))

        # ── Layout (order: Desarrollo → RFC → Delegación → Concepto → Cant → Disp → Del) ─
        self.layout.addWidget(self.combo_desarrollo, stretch=1)
        self.layout.addWidget(self.combo_rfc, stretch=1)
        self.layout.addWidget(self.combo_delegacion, stretch=1)
        self.layout.addWidget(self.combo_concepto, stretch=1)
        self.layout.addWidget(self.spin_cantidad)
        self.layout.addWidget(self.lbl_disponibles)
        self.layout.addWidget(self.btn_delete)

        # ── Signal connections ───────────────────────────────────────────────
        self.combo_desarrollo.currentIndexChanged.connect(self._on_desarrollo_changed)
        self.combo_rfc.currentIndexChanged.connect(self._on_rfc_changed)
        self.combo_delegacion.currentIndexChanged.connect(self._on_delegacion_changed)
        self.combo_concepto.currentIndexChanged.connect(self._on_concepto_changed)
        self.spin_cantidad.valueChanged.connect(lambda _: self.changed.emit())

    # ── Public API ────────────────────────────────────────────────────────────

    def set_has_desarrollo(self, enabled: bool):
        self._has_desarrollo = enabled
        self.combo_desarrollo.setVisible(enabled)

    def set_cascade_mode(self, enabled: bool):
        """Switch between cascade mode (apartar) and legacy mode (individual)."""
        self._cascade_mode = enabled
        self.set_has_desarrollo(enabled)


    # ── Populate helpers ─────────────────────────────────────────────────────

    def populate(self, rfcs, conceptos, delegaciones, desarrollos=None):
        """Legacy populate — all combos loaded at once (for grid_individual).
        rfcs, conceptos, delegaciones: list of (id, display_text) tuples.
        desarrollos: list of (desarrollo_id, nombre, delegacion_id, es_default).
        """
        self.combo_rfc.blockSignals(True)
        self.combo_concepto.blockSignals(True)
        self.combo_delegacion.blockSignals(True)
        self.combo_desarrollo.blockSignals(True)

        self.combo_rfc.clear()
        for r_id, r_text in rfcs:
            self.combo_rfc.addItem(r_text, r_id)

        self.combo_concepto.clear()
        for c_id, c_text in conceptos:
            self.combo_concepto.addItem(c_text, c_id)

        self.combo_delegacion.clear()
        for d_id, d_text in delegaciones:
            self.combo_delegacion.addItem(d_text, d_id)

        if desarrollos:
            self._all_desarrollos = desarrollos
            self._update_desarrollo_options_legacy()

        self.combo_rfc.blockSignals(False)
        self.combo_concepto.blockSignals(False)
        self.combo_delegacion.blockSignals(False)
        self.combo_desarrollo.blockSignals(False)

    def populate_cascade_desarrollos(self, desarrollos_entries: list):
        """Cascade mode: load the Desarrollo combo.
        desarrollos_entries: list of dicts from get_desarrollos_activos_para_apartar().
        Duplicates are collapsed; default entry shown first.
        """
        self.combo_desarrollo.blockSignals(True)
        self.combo_desarrollo.clear()

        seen = {}  # desarrollo_id → dict
        for entry in desarrollos_entries:
            d_id = entry["desarrollo_id"]
            if d_id not in seen or entry.get("es_default"):
                seen[d_id] = entry

        # Sort: default entries first, then alphabetically
        sorted_entries = sorted(seen.values(), key=lambda x: (not x.get("es_default", False), x["nombre"]))
        for entry in sorted_entries:
            self.combo_desarrollo.addItem(entry["nombre"], entry["desarrollo_id"])

        self.combo_desarrollo.blockSignals(False)

    def populate_rfcs(self, rfcs: list, default_rfc_id: int = None):
        """Cascade mode: refresh the RFC combo after a Desarrollo is selected."""
        self.combo_rfc.blockSignals(True)
        self.combo_rfc.clear()
        default_idx = 0
        for i, rfc in enumerate(rfcs):
            self.combo_rfc.addItem(rfc["razon_social"], rfc["rfc_id"])
            if rfc.get("es_default") or (default_rfc_id and rfc["rfc_id"] == default_rfc_id):
                default_idx = i
        self.combo_rfc.setCurrentIndex(default_idx)
        self.combo_rfc.blockSignals(False)
        # Trigger delegacion refresh manually after unblocking
        self._on_rfc_changed()

    def populate_delegaciones(self, delegaciones: list, default_delegacion_id: int = None):
        """Cascade mode: refresh Delegación combo after Desarrollo+RFC selection."""
        self.combo_delegacion.blockSignals(True)
        self.combo_delegacion.clear()
        default_idx = 0
        for i, d in enumerate(delegaciones):
            self.combo_delegacion.addItem(d["nombre"], d["delegacion_id"])
            if d.get("es_default") or (default_delegacion_id and d["delegacion_id"] == default_delegacion_id):
                default_idx = i
        self.combo_delegacion.setCurrentIndex(default_idx)
        self.combo_delegacion.blockSignals(False)
        # Trigger concepto refresh manually after unblocking
        self._on_delegacion_changed()

    def populate_conceptos(self, conceptos: list):
        """Cascade mode: refresh Concepto combo after RFC+Delegación selection."""
        self.combo_concepto.blockSignals(True)
        self.combo_concepto.clear()
        for c in conceptos:
            self.combo_concepto.addItem(c["nombre"], c["concepto_id"])
        self.combo_concepto.blockSignals(False)
        # Trigger availability refresh
        self._on_concepto_changed()

    # ── Legacy desarrollo update (used when cascade_mode=False) ──────────────

    def _update_desarrollo_options_legacy(self):
        """Legacy: filter Desarrollo by selected Delegación (old behavior)."""
        if not self._has_desarrollo or self._cascade_mode:
            return
        self.combo_desarrollo.blockSignals(True)
        self.combo_desarrollo.clear()
        self.combo_desarrollo.addItem("Cualquier Desarrollo", None)
        delegacion_id = self.combo_delegacion.currentData()
        for tpl in self._all_desarrollos:
            d_id, d_name, d_del_id = tpl[0], tpl[1], tpl[2]
            es_default = tpl[3] if len(tpl) > 3 else False
            if delegacion_id and d_del_id != delegacion_id:
                continue
            label = f"★ {d_name}" if es_default else d_name
            self.combo_desarrollo.addItem(label, d_id)
        self.combo_desarrollo.blockSignals(False)

    # ── Cascade signal handlers ───────────────────────────────────────────────

    def _on_desarrollo_changed(self):
        desarrollo_id = self.combo_desarrollo.currentData()
        if self._cascade_mode and desarrollo_id:
            # Signal to the parent view to load RFCs for this desarrollo
            self.cascade_rfcs_needed.emit(self, desarrollo_id)
        elif not self._cascade_mode:
            self._update_desarrollo_options_legacy()
            self._on_combo_changed_generic()

    def _on_rfc_changed(self):
        if self._cascade_mode:
            desarrollo_id = self.combo_desarrollo.currentData()
            rfc_id = self.combo_rfc.currentData()
            if desarrollo_id and rfc_id:
                self.cascade_delegaciones_needed.emit(self, desarrollo_id, rfc_id)
        else:
            self._update_desarrollo_options_legacy()
            self._on_combo_changed_generic()

    def _on_delegacion_changed(self):
        if self._cascade_mode:
            rfc_id = self.combo_rfc.currentData()
            delegacion_id = self.combo_delegacion.currentData()
            if rfc_id and delegacion_id:
                self.cascade_conceptos_needed.emit(self, rfc_id, delegacion_id)
        else:
            self._update_desarrollo_options_legacy()
            self._on_combo_changed_generic()

    def _on_concepto_changed(self):
        self._on_combo_changed_generic()

    def _on_combo_changed_generic(self):
        """Common final step: emit changed and request availability if all fields are set."""
        self.changed.emit()
        rfc_id = self.combo_rfc.currentData()
        concepto_id = self.combo_concepto.currentData()
        delegacion_id = self.combo_delegacion.currentData()
        if rfc_id and concepto_id and delegacion_id:
            self.lbl_disponibles.setText("...")
            self.lbl_disponibles.setStyleSheet(
                "background: #F1F5F9; color: #94A3B8; border: 1px solid #E2E8F0; "
                "border-radius: 4px; padding: 4px 6px; font-size: 11px; font-weight: 600;"
            )
            self.availability_requested.emit(self)
        else:
            self.set_disponibles(None)

    # ── Availability display ──────────────────────────────────────────────────

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

    # ── Data access ───────────────────────────────────────────────────────────

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
            if not self._cascade_mode:
                self._update_desarrollo_options_legacy()
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
    # Cascade signals — forwarded from InteractiveGridRow to the parent view
    cascade_rfcs_needed = Signal(object, int)           # (row, desarrollo_id)
    cascade_delegaciones_needed = Signal(object, int, int)  # (row, desarrollo_id, rfc_id)
    cascade_conceptos_needed = Signal(object, int, int)     # (row, rfc_id, delegacion_id)
    
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
        self.lbl_title.setVisible(False)
        self.header_layout.addWidget(self.lbl_title)
        
        # Add badge count
        self.lbl_badge = QLabel("1", self)
        self.lbl_badge.setObjectName("gridBadge")
        self.lbl_badge.setVisible(False)
        self.header_layout.addWidget(self.lbl_badge)
        
        self.header_layout.addStretch()
        
        # Buttons
        self.btn_add = CustomButton("+ Agregar Renglón", parent=self)
        self.btn_add.setMinimumHeight(35)
        self.btn_add.clicked.connect(self.add_row)
        
        self.btn_cancel = CustomButton("Cancelar Edición", is_secondary=True, parent=self)
        self.btn_cancel.setMinimumHeight(35)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self.cancel_triggered.emit)
        
        self.btn_save = CustomButton("Guardar Orden", parent=self)
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

        self.lbl_h_desarrollo = CustomLabel("Desarrollo", variant="body")
        self.lbl_h_desarrollo.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 600;")
        self.lbl_h_desarrollo.setVisible(False)

        self.lbl_h_rfc = CustomLabel("Empresa (RFC)", variant="body")
        self.lbl_h_rfc.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 600;")

        self.lbl_h_del = CustomLabel("Delegación", variant="body")
        self.lbl_h_del.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 600;")

        self.lbl_h_concepto = CustomLabel("Concepto", variant="body")
        self.lbl_h_concepto.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 600;")

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

        # Build header layout — order matches the row widget layout:
        # Desarrollo | RFC | Delegación | Concepto | Cantidad | Disponibles | (del)
        self.table_header_layout.addWidget(self.lbl_h_desarrollo, stretch=1)
        self.table_header_layout.addWidget(self.lbl_h_rfc, stretch=1)
        self.table_header_layout.addWidget(self.lbl_h_del, stretch=1)
        self.table_header_layout.addWidget(self.lbl_h_concepto, stretch=1)
        self.table_header_layout.addWidget(self.lbl_h_cant)
        self.table_header_layout.addWidget(self.lbl_h_disp)
        self.table_header_layout.addWidget(self.lbl_h_empty)
        
        self.rows_layout.addLayout(self.table_header_layout)
        
        self.scroll_area.setWidget(self.rows_container)
        self.main_layout.addWidget(self.scroll_area)
        
        self.rows = []
        
        self._rfcs = []
        self._conceptos = []
        self._delegaciones = []
        self._desarrollos = []
        self._cascade_mode = False
        self._cascade_desarrollos_entries = []


    def set_has_desarrollo(self, enabled: bool):
        self._has_desarrollo = enabled
        self.lbl_h_desarrollo.setVisible(enabled)
        for r in self.rows:
            r.set_has_desarrollo(enabled)

    def set_cascade_mode(self, enabled: bool, desarrollos_entries: list = None):
        """Enable cascade mode for the grid (used by the Apartar tab).
        desarrollos_entries: full list of dicts from get_desarrollos_activos_para_apartar().
        """
        self._cascade_mode = enabled
        if desarrollos_entries is not None:
            self._cascade_desarrollos_entries = desarrollos_entries
        self.set_has_desarrollo(enabled)
        for r in self.rows:
            r.set_cascade_mode(enabled)

    def set_catalogs(self, rfcs, conceptos, delegaciones, desarrollos=None):
        """Legacy catalog setter — used by grid_individual."""
        self._rfcs = rfcs
        self._conceptos = conceptos
        self._delegaciones = delegaciones
        if desarrollos:
            self._desarrollos = desarrollos

    def set_third_column_label(self, label: str):
        """Deprecated: kept for compatibility."""
        pass

    def add_row(self):
        row_widget = InteractiveGridRow(self.rows_container, cascade_mode=self._cascade_mode)
        row_widget.set_has_desarrollo(self._has_desarrollo)
        if self._cascade_mode:
            # In cascade mode, populate only the Desarrollo combo initially
            row_widget.populate_cascade_desarrollos(self._cascade_desarrollos_entries)
        else:
            row_widget.populate(self._rfcs, self._conceptos, self._delegaciones, self._desarrollos)
        row_widget.deleted.connect(self._remove_row)
        row_widget.changed.connect(self.data_changed.emit)
        row_widget.availability_requested.connect(self.availability_requested.emit)
        if self._cascade_mode:
            row_widget.cascade_rfcs_needed.connect(self.cascade_rfcs_needed)
            row_widget.cascade_delegaciones_needed.connect(self.cascade_delegaciones_needed)
            row_widget.cascade_conceptos_needed.connect(self.cascade_conceptos_needed)
        self.rows_layout.addWidget(row_widget)
        self.rows.append(row_widget)
        self._update_badge()
        self.data_changed.emit()

    def add_row_with_data(self, rfc_id, concepto_id, delegacion_id, cantidad, cantidad_generada=0, desarrollo_id=None):
        row_widget = InteractiveGridRow(self.rows_container, cascade_mode=False)  # legacy
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
