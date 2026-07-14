import sys
import os
import traceback

# Ensure the root dir is in Python path when run from scratch/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import QApplication
from sar.src.storage.db_connector import DatabaseConnector
from sar.src.ui.views.admin_view import AdminWindow

try:
    app = QApplication(sys.argv)
    db = DatabaseConnector()
    w = AdminWindow(db)
    print("SUCCESS")
except Exception as e:
    traceback.print_exc()
