"""Checkable Pop-up Menu Molecule for Filters (Atomic Design)."""

import os
from PySide6.QtWidgets import QMenu


class KeepOpenMenu(QMenu):
    """
    A styled QMenu that keeps the popup open when clicking checkable items,
    styled with modern Design System checkbox indicators.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        icon_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "icons", "check.svg")
        ).replace("\\", "/")

        self.setStyleSheet(f"""
            QMenu {{
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 7px 20px 7px 34px;
                border-radius: 6px;
                color: #1E293B;
                font-size: 13px;
            }}
            QMenu::item:selected {{
                background-color: #F1F5F9;
                color: #0F172A;
            }}
            QMenu::separator {{
                height: 1px;
                background-color: #E2E8F0;
                margin: 4px 6px;
            }}
            QMenu::indicator {{
                width: 16px;
                height: 16px;
                left: 8px;
                border: 1.5px solid #94A3B8;
                border-radius: 4px;
                background-color: #FFFFFF;
            }}
            QMenu::indicator:hover {{
                border-color: #2563EB;
            }}
            QMenu::indicator:checked {{
                border: 1.5px solid #2563EB;
                border-radius: 4px;
                background-color: #2563EB;
                image: url("{icon_path}");
            }}
            QMenu::indicator:checked:hover {{
                border-color: #1D4ED8;
                background-color: #1D4ED8;
            }}
        """)

    def mouseReleaseEvent(self, event):
        action = self.actionAt(event.position().toPoint())
        if action and action.isCheckable():
            action.trigger()
            event.accept()
        else:
            super().mouseReleaseEvent(event)
