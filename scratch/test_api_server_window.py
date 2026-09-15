import sys
import os
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath("."))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from sar.src.ui.views.api_server_view import APIServerWindow

class TestAPIServerWindow(unittest.TestCase):
    def test_window_init_without_local_buttons(self):
        mock_db = MagicMock()
        window = APIServerWindow(db_connector=mock_db, current_usuario_id=1, current_sesion_id=1)
        # Check that local buttons are gone
        self.assertFalse(hasattr(window, 'btn_iniciar_local'))
        self.assertFalse(hasattr(window, 'btn_detener_local'))
        # Check that windows service buttons exist
        self.assertTrue(hasattr(window, 'btn_iniciar'))
        self.assertTrue(hasattr(window, 'btn_detener'))
        window._logging_out = True
        window.close()

if __name__ == "__main__":
    unittest.main()
