"""Checkable Pop-up Menu Molecule for Filters (Atomic Design)."""

from PySide6.QtWidgets import QMenu


class KeepOpenMenu(QMenu):
    """
    A styled QMenu that keeps the popup open when clicking checkable items,
    seamlessly themed via SAR Design System ThemeManager.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("keepOpenMenu")

    def mouseReleaseEvent(self, event):
        action = self.actionAt(event.position().toPoint())
        if action and action.isCheckable():
            action.trigger()
            event.accept()
        else:
            super().mouseReleaseEvent(event)
