"""GLInfoBanner Molecule Component."""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from sar.src.ui.design_system.theme_manager import ThemeManager
from sar.src.ui.design_system.utils.icons import Icons


class GLInfoBanner(QFrame):
    """A discrete, modern info callout banner integrated with the SAR Design System."""

    def __init__(self, text: str = "", variant: str = "info", icon_name: str = "informacion", parent=None):
        super().__init__(parent)
        self.setObjectName("glInfoBanner")
        self._text = text
        self._variant = variant
        self._icon_name = icon_name

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(14, 10, 16, 10)
        self._layout.setSpacing(12)
        self._layout.setAlignment(Qt.AlignVCenter)

        # Icon Label
        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(22, 22)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(self.icon_label)

        # Text Label
        self.text_label = QLabel(self)
        self.text_label.setTextFormat(Qt.RichText)
        self.text_label.setWordWrap(True)
        self.text_label.setText(self._text)
        self._layout.addWidget(self.text_label, stretch=1)

        self._apply_style()

    def set_text(self, text: str):
        self._text = text
        self.text_label.setText(text)

    def _apply_style(self):
        is_dark = ThemeManager.is_dark_active()

        if self._variant in ("tip", "info"):
            bg = "rgba(37, 99, 235, 0.12)" if is_dark else "#EFF6FF"
            border = "rgba(59, 130, 246, 0.35)" if is_dark else "#BFDBFE"
            text_color = "#E2E8F0" if is_dark else "#1E293B"
            icon_color = "#60A5FA" if is_dark else "#2563EB"
        elif self._variant == "warning":
            bg = "rgba(217, 119, 6, 0.12)" if is_dark else "#FFFBEB"
            border = "rgba(245, 158, 11, 0.35)" if is_dark else "#FDE68A"
            text_color = "#E2E8F0" if is_dark else "#451A03"
            icon_color = "#F59E0B" if is_dark else "#D97706"
        elif self._variant == "success":
            bg = "rgba(22, 163, 74, 0.12)" if is_dark else "#F0FDF4"
            border = "rgba(34, 197, 94, 0.35)" if is_dark else "#BBF7D0"
            text_color = "#E2E8F0" if is_dark else "#14532D"
            icon_color = "#22C55E" if is_dark else "#16A34A"
        else: # neutral
            bg = "rgba(100, 116, 139, 0.12)" if is_dark else "#F8FAFC"
            border = "rgba(148, 163, 184, 0.35)" if is_dark else "#E2E8F0"
            text_color = "#E2E8F0" if is_dark else "#334155"
            icon_color = "#94A3B8" if is_dark else "#64748B"

        self.setStyleSheet(f"""
            QFrame#glInfoBanner {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        self.text_label.setStyleSheet(f"color: {text_color}; font-size: 13px; line-height: 1.4;")

        icon = Icons.get_icon(self._icon_name, color=icon_color)
        if not icon.isNull():
            self.icon_label.setPixmap(icon.pixmap(20, 20))
