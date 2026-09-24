"""Unit tests for Empresa/RFC display formatting in SAR orders module."""

import sys
import unittest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication

# Ensure single QApplication instance
app = QApplication.instance() or QApplication(sys.argv)

from sar.src.ui.views.orders_view import OrdersView
from sar.src.ui.design_system.components.organisms.gl_interactive_grid import InteractiveGrid, InteractiveGridRow


class TestRFCDisplayFormat(unittest.TestCase):
    """Test suite to ensure RFC display format is correctly rendered as alias | rfc."""

    def test_interactive_grid_populate_legacy(self):
        """Test that legacy populate correctly sets alias | rfc in the combobox."""
        grid = InteractiveGrid()
        rfcs = [
            (1, "Cancún | GCA101010ABC"),
            (2, "XAXX010101000")
        ]
        conceptos = [(1, "Análisis"), (2, "Aviso")]
        delegaciones = [(1, "Cancún"), (2, "Playa")]

        grid.set_catalogs(rfcs, conceptos, delegaciones)
        grid.add_row()

        row = grid.rows[0]
        self.assertEqual(row.combo_rfc.count(), 2)
        self.assertEqual(row.combo_rfc.itemText(0), "Cancún | GCA101010ABC")
        self.assertEqual(row.combo_rfc.itemData(0), 1)
        self.assertEqual(row.combo_rfc.itemText(1), "XAXX010101000")
        self.assertEqual(row.combo_rfc.itemData(1), 2)

    def test_interactive_grid_populate_rfcs_cascade(self):
        """Test that cascade populate_rfcs creates alias | rfc formatted entries."""
        row = InteractiveGridRow()
        rfcs_data = [
            {
                "rfc_id": 10,
                "rfc": "GCA101010ABC",
                "alias": "Cancún",
                "razon_social": "GRUPO CANCUN SA DE CV",
                "es_default": True
            },
            {
                "rfc_id": 20,
                "rfc": "XAXX010101000",
                "alias": None,
                "razon_social": "PUBLICO EN GENERAL",
                "es_default": False
            }
        ]
        row.populate_rfcs(rfcs_data)

        self.assertEqual(row.combo_rfc.count(), 2)
        self.assertEqual(row.combo_rfc.itemText(0), "Cancún | GCA101010ABC")
        self.assertEqual(row.combo_rfc.itemData(0), 10)
        self.assertEqual(row.combo_rfc.itemText(1), "XAXX010101000")
        self.assertEqual(row.combo_rfc.itemData(1), 20)

    def test_orders_ui_service_catalogo_mock(self):
        """Test that OrdenesUIService extracts and includes alias in its catalog dictionary."""
        from sar.src.services.ordenes_ui_service import OrdenesUIService
        
        mock_repo = MagicMock()
        mock_rfc_1 = MagicMock(rfc_id=1, rfc="GCA101010ABC", alias="Cancún", razon_social="GRUPO CANCUN SA")
        mock_rfc_2 = MagicMock(rfc_id=2, rfc="XAXX010101000", alias=None, razon_social="PUBLICO EN GENERAL")
        mock_repo.get_rfcs_activos.return_value = [mock_rfc_1, mock_rfc_2]
        mock_repo.get_conceptos_activos.return_value = []
        mock_repo.get_delegaciones_activas.return_value = []
        mock_repo.get_all_municipios.return_value = []

        mock_session = MagicMock()
        mock_connector = MagicMock()
        mock_connector.get_session.return_value.__enter__.return_value = mock_session

        service = OrdenesUIService(db_connector=mock_connector)
        service.api_client.connect_via_api = False

        with unittest.mock.patch("sar.src.services.ordenes_ui_service.CatalogoRepository", return_value=mock_repo):
            catalogs = service.get_catalogos()

        self.assertIn("rfcs", catalogs)
        self.assertEqual(len(catalogs["rfcs"]), 2)
        self.assertEqual(catalogs["rfcs"][0]["alias"], "Cancún")
        self.assertEqual(catalogs["rfcs"][0]["rfc"], "GCA101010ABC")
        self.assertIsNone(catalogs["rfcs"][1]["alias"])


if __name__ == "__main__":
    unittest.main()
