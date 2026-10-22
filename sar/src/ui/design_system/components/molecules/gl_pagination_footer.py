"""Pagination Footer Molecule for SAR/SATC Design System (Atomic Design)."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Signal, Qt
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.molecules.gl_combo_box import CustomComboBox


class GLPaginationFooter(QWidget):
    """Reusable pagination footer with record counter, page size selector and navigation buttons."""

    page_changed = Signal(int)       # Emits new target page number (1-indexed)
    page_size_changed = Signal(int)  # Emits new page size limit

    def __init__(self, parent=None, default_page_size: int = 50, item_singular: str = "registro", item_plural: str = "registros"):
        super().__init__(parent)
        self.item_singular = item_singular
        self.item_plural = item_plural
        
        self.current_page = 1
        self.total_items = 0
        self.page_size = default_page_size

        self._build_ui()

    def _build_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 8, 0, 0)
        self.layout.setSpacing(10)

        # 1. Left side: Record counter label
        self.lbl_info = CustomLabel("Mostrando 0 a 0 de 0 registros", variant="muted")
        self.lbl_info.setObjectName("dashboardPaginationInfo")
        self.layout.addWidget(self.lbl_info)

        self.layout.addStretch()

        # 2. Page size dropdown selector
        self.cb_page_size = CustomComboBox(self, control_size="sm")
        self.cb_page_size.addItems(["50 por página", "100 por página", "200 por página"])
        
        size_idx_map = {50: 0, 100: 1, 200: 2}
        self.cb_page_size.setCurrentIndex(size_idx_map.get(self.page_size, 0))
        self.cb_page_size.currentIndexChanged.connect(self._on_combo_size_changed)
        self.layout.addWidget(self.cb_page_size)

        # 3. Nav Buttons Container
        self.nav_container = QWidget(self)
        self.nav_layout = QHBoxLayout(self.nav_container)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(4)
        self.layout.addWidget(self.nav_container)

        self._render_buttons()

    def _on_combo_size_changed(self, idx: int):
        sizes = [50, 100, 200]
        if 0 <= idx < len(sizes):
            new_size = sizes[idx]
            if new_size != self.page_size:
                self.page_size = new_size
                self.current_page = 1
                self.page_size_changed.emit(self.page_size)

    def set_pagination(self, current_page: int, total_items: int, current_count: int):
        """Updates the pagination state and redraws buttons and labels."""
        self.current_page = max(1, current_page)
        self.total_items = max(0, total_items)
        
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + current_count, self.total_items)

        if self.total_items == 0:
            self.lbl_info.setText(f"Mostrando 0 a 0 de 0 {self.item_plural}")
        else:
            self.lbl_info.setText(f"Mostrando {start_idx + 1} a {end_idx} de {self.total_items} {self.item_plural}")

        self._render_buttons()

    def _render_buttons(self):
        # Clear existing navigation buttons
        while self.nav_layout.count():
            item = self.nav_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total_pages = max(1, (self.total_items + self.page_size - 1) // self.page_size)

        def _add_btn(text: str, target: int, enabled: bool, is_active: bool = False):
            btn = QPushButton(text, self.nav_container)
            btn.setEnabled(enabled)
            if is_active:
                btn.setObjectName("paginationActivePageBtn")
            elif text in ("<<", "<", ">", ">>"):
                btn.setObjectName("paginationNavBtn")
            else:
                btn.setObjectName("paginationPageBtn")
            btn.clicked.connect(lambda: self._on_page_clicked(target))
            self.nav_layout.addWidget(btn)

        # << First and < Prev
        _add_btn("<<", 1, self.current_page > 1)
        _add_btn("<", self.current_page - 1, self.current_page > 1)

        # Active page number
        _add_btn(str(self.current_page), self.current_page, True, is_active=True)

        # > Next and >> Last
        _add_btn(">", self.current_page + 1, self.current_page < total_pages)
        _add_btn(">>", total_pages, self.current_page < total_pages)

    def _on_page_clicked(self, target_page: int):
        if target_page != self.current_page and target_page >= 1:
            self.current_page = target_page
            self.page_changed.emit(self.current_page)
