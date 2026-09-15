import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Configure path
sys.path.insert(0, os.path.abspath("."))

from PySide6.QtWidgets import QApplication, QWidget
app = QApplication.instance() or QApplication(sys.argv)

from sar.src.ui.views.inventory_view import LoteProcessingDialog, ExportLotesDialog
from sar.src.services.inventario_ui_service import InventarioUIService
from sar.src.services.excel_inventory_handler import ExcelInventoryHandler

class MockInventoryView(QWidget):
    def __init__(self):
        super().__init__()
        self.current_usuario_id = 1
        self.inventario_ui_service = MagicMock(spec=InventarioUIService)
        self.api_client = MagicMock()
        self.api_client.connect_via_api = True
        self._checked_calls = []

    def _check_permission(self, modulo_codigo, accion_codigo):
        self._checked_calls.append((modulo_codigo, accion_codigo))
        return True

class TestLoteProcessingDialogPerms(unittest.TestCase):

    def setUp(self):
        self.mock_parent = MockInventoryView()

    def test_dialog_init_reuses_parent_services(self):
        with patch.object(LoteProcessingDialog, '_load_all', return_value=None):
            dialog = LoteProcessingDialog(db_connector=None, lote_id=999, parent=self.mock_parent)
            self.assertEqual(dialog.inventario_ui_service, self.mock_parent.inventario_ui_service)
            self.assertEqual(dialog.api_client, self.mock_parent.api_client)

    def test_permission_delegates_to_parent(self):
        with patch.object(LoteProcessingDialog, '_load_all', return_value=None):
            dialog = LoteProcessingDialog(db_connector=None, lote_id=999, parent=self.mock_parent)
            perm = dialog._check_permission("CTRL:GESTION_LOTES", "EJECUTAR")
            self.assertTrue(perm)
            self.assertIn(("CTRL:GESTION_LOTES", "EJECUTAR"), self.mock_parent._checked_calls)

    def test_permission_api_fallback_without_parent_check_fn(self):
        standalone_parent = QWidget()
        standalone_parent.current_usuario_id = 2
        standalone_parent.inventario_ui_service = MagicMock(spec=InventarioUIService)
        standalone_parent.api_client = MagicMock()
        standalone_parent.api_client.connect_via_api = True
        standalone_parent.api_client.request.return_value = {
            "CTRL:GESTION_LOTES": {"EJECUTAR": True}
        }

        with patch.object(LoteProcessingDialog, '_load_all', return_value=None):
            dialog = LoteProcessingDialog(db_connector=None, lote_id=999, parent=standalone_parent)
            perm = dialog._check_permission("CTRL:GESTION_LOTES", "EJECUTAR")
            self.assertTrue(perm)
            standalone_parent.api_client.request.assert_called_with("GET", "/api/auth/permissions/2")

    def test_excel_generation_data_handling(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tf:
            temp_path = tf.name

        try:
            header = {
                "tipo_destino": "NOTARIA",
                "asignado_a": "Lic. Test",
                "fecha": "14/09/2026",
                "estado_refs": "ASIGNADA"
            }
            data_rows = [
                {
                    "referencia_id": 101,
                    "referencia": "REF12345",
                    "concepto": "AVISO",
                    "cliente": "CLIENTE DE PRUEBA",
                    "desarrollo": "DESARROLLO A",
                    "mz": "01",
                    "lote": "02",
                    "edif": "",
                    "viv": "101",
                    "folio_electronico": "FE-9999",
                    "pa": "PA-1",
                    "fecha_solicitud": "14/09/2026",
                    "estado": "ASIGNADA"
                }
            ]
            ExcelInventoryHandler.generate_assignment_excel(
                dest_path=temp_path,
                header=header,
                data_rows=data_rows
            )
            self.assertTrue(os.path.exists(temp_path))
            self.assertGreater(os.path.getsize(temp_path), 0)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

if __name__ == "__main__":
    unittest.main()
