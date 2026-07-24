"""Standalone entry point for the API_SAR Application Server Manager."""

import sys
import os

# Ensure the root dir is in Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from sar.src.ui.design_system.theme_manager import ThemeManager
from sar.src.ui.views.api_server_view import APIServerWindow
from sar.src.storage.db_connector import DatabaseConnector

def main():
    # Register explicit AppUserModelID for Windows Taskbar grouping/icon representation
    if sys.platform == "win32":
        try:
            import ctypes
            myappid = "dramos.gl.sar.server.manager"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            print("Error setting AppUserModelID:", e)

    app = QApplication(sys.argv)
    
    # Apply global window icon
    icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "src", "ui", "assets", "sar_logo.png"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Apply theme
    ThemeManager.apply_theme(app, is_dark=False)
    
    db_connector = DatabaseConnector()
    
    # Instantiate standalone API Server Window
    window = APIServerWindow(db_connector)
    
    # Center window on screen and show in normal size (no full screen/maximized)
    window.resize(800, 470)
    screen_geometry = QApplication.primaryScreen().geometry()
    window_geometry = window.frameGeometry()
    x = (screen_geometry.width() - window_geometry.width()) // 2
    y = (screen_geometry.height() - window_geometry.height()) // 2
    window.move(x, y)
    
    # Show normal
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
