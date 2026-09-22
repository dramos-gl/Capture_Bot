"""Custom File Dialog molecule for Design System (Atomic Design).

Standardizes QFileDialog size, centering, responsiveness, and window controls
(Maximize/Minimize) across the SAR application.
"""

from typing import Tuple, List, Optional
import os

from PySide6.QtWidgets import QFileDialog, QWidget, QApplication
from PySide6.QtCore import Qt, QPoint


class GLFileDialog(QFileDialog):
    """Enhanced QFileDialog with responsive sizing, auto-centering,
    and explicit window controls (Maximize / Minimize)."""

    def __init__(self, parent: Optional[QWidget] = None, caption: str = "", directory: str = "", filter: str = ""):
        super().__init__(parent, caption, directory, filter)
        self._configure_dialog(parent)

    def _configure_dialog(self, parent: Optional[QWidget] = None):
        """Applies responsive geometry, center positioning, and window flags."""
        # Enable maximize, minimize, and close hints
        flags = self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint
        self.setWindowFlags(flags)

        # Minimum dimensions to prevent cramming
        self.setMinimumSize(680, 400)

        # Calculate responsive size based on screen or parent
        target_screen = None
        if parent and hasattr(parent, "screen") and parent.screen():
            target_screen = parent.screen()
        elif parent and hasattr(parent, "window") and parent.window() and hasattr(parent.window(), "screen"):
            target_screen = parent.window().screen()

        if not target_screen:
            target_screen = QApplication.primaryScreen()

        if target_screen:
            avail = target_screen.availableGeometry()
            # Default to ~58% width and ~62% height of screen, bounded comfortably
            ideal_w = min(960, max(720, int(avail.width() * 0.58)))
            ideal_h = min(620, max(460, int(avail.height() * 0.62)))
            self.resize(ideal_w, ideal_h)

            # Center relative to parent window if available, else center on screen
            if parent and parent.isVisible():
                parent_geo = parent.window().geometry() if hasattr(parent, "window") else parent.geometry()
                cx = parent_geo.x() + (parent_geo.width() - ideal_w) // 2
                cy = parent_geo.y() + (parent_geo.height() - ideal_h) // 2
                # Clamp within screen bounds
                cx = max(avail.x(), min(cx, avail.x() + avail.width() - ideal_w))
                cy = max(avail.y(), min(cy, avail.y() + avail.height() - ideal_h))
                self.move(cx, cy)
            else:
                cx = avail.x() + (avail.width() - ideal_w) // 2
                cy = avail.y() + (avail.height() - ideal_h) // 2
                self.move(cx, cy)
        else:
            self.resize(850, 520)

    @classmethod
    def getSaveFileName(
        cls,
        parent: Optional[QWidget] = None,
        caption: str = "Guardar Archivo",
        dir: str = "",
        filter: str = "",
        selectedFilter: str = "",
        options: Optional[QFileDialog.Option] = None
    ) -> Tuple[str, str]:
        """Convenience method mirroring QFileDialog.getSaveFileName with standard geometry and controls."""
        dialog = cls(parent, caption)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)

        if options:
            dialog.setOptions(options)

        if filter:
            dialog.setNameFilter(filter)
            if selectedFilter:
                dialog.selectNameFilter(selectedFilter)

        if dir:
            # If dir has a filename portion
            if os.path.isdir(dir):
                dialog.setDirectory(dir)
            else:
                dirname, filename = os.path.split(dir)
                if dirname and os.path.exists(dirname):
                    dialog.setDirectory(dirname)
                if filename:
                    dialog.selectFile(filename)

        if dialog.exec():
            selected_files = dialog.selectedFiles()
            chosen_file = selected_files[0] if selected_files else ""
            chosen_filter = dialog.selectedNameFilter()
            return chosen_file, chosen_filter

        return "", ""

    @classmethod
    def getExistingDirectory(
        cls,
        parent: Optional[QWidget] = None,
        caption: str = "Seleccionar Carpeta",
        dir: str = "",
        options: Optional[QFileDialog.Option] = None
    ) -> str:
        """Convenience method mirroring QFileDialog.getExistingDirectory with standard geometry and controls."""
        dialog = cls(parent, caption)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        opts = dialog.options() | QFileDialog.Option.ShowDirsOnly
        if options:
            opts |= options
        dialog.setOptions(opts)

        if dir and os.path.exists(dir):
            dialog.setDirectory(dir)

        if dialog.exec():
            selected_files = dialog.selectedFiles()
            return selected_files[0] if selected_files else ""

        return ""

    @classmethod
    def getOpenFileName(
        cls,
        parent: Optional[QWidget] = None,
        caption: str = "Abrir Archivo",
        dir: str = "",
        filter: str = "",
        selectedFilter: str = "",
        options: Optional[QFileDialog.Option] = None
    ) -> Tuple[str, str]:
        """Convenience method mirroring QFileDialog.getOpenFileName with standard geometry and controls."""
        dialog = cls(parent, caption)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)

        if options:
            dialog.setOptions(options)

        if filter:
            dialog.setNameFilter(filter)
            if selectedFilter:
                dialog.selectNameFilter(selectedFilter)

        if dir:
            if os.path.isdir(dir):
                dialog.setDirectory(dir)
            else:
                dirname, filename = os.path.split(dir)
                if dirname and os.path.exists(dirname):
                    dialog.setDirectory(dirname)
                if filename:
                    dialog.selectFile(filename)

        if dialog.exec():
            selected_files = dialog.selectedFiles()
            chosen_file = selected_files[0] if selected_files else ""
            chosen_filter = dialog.selectedNameFilter()
            return chosen_file, chosen_filter

        return "", ""
