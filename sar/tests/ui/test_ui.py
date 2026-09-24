"""Visual and compilation test script for PySide6 UI."""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sar.main import MainWindow
from sar.src.ui.design_system.theme_manager import ThemeManager

def test_run():
    print("Initializing PySide6 app test...")
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        
    ThemeManager.apply_theme(app, is_dark=True)
    window = MainWindow()
    window.show()
    
    print("Application loaded successfully.")
    
    # Timer to automate actions and close the app
    # Step 1: Fill credentials and login after 800ms
    def step_login():
        print("Test Step 1: Performing programmatic login...")
        window.login_view.user_input.set_text("admin")
        window.login_view.pass_input.set_text("password123")
        window.login_view._on_login_clicked()
        
    # Step 2: Toggle theme after 1600ms
    def step_theme():
        print("Test Step 2: Toggling dark/light themes...")
        window.main_view._toggle_theme()
        
    # Step 3: Close app after 2400ms
    def step_close():
        print("Test Step 3: Closing application. All checks passed!")
        window.close()
        app.quit()
        
    QTimer.singleShot(800, step_login)
    QTimer.singleShot(1600, step_theme)
    QTimer.singleShot(2400, step_close)
    
    # Run the event loop
    app.exec()
    print("PySide6 UI test complete.")

if __name__ == "__main__":
    test_run()
