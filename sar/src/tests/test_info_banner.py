"""Unit tests for GLInfoBanner molecule component."""

import sys
import unittest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Ensure single QApplication instance
app = QApplication.instance() or QApplication(sys.argv)

from sar.src.ui.design_system.components.molecules.gl_info_banner import GLInfoBanner


class TestGLInfoBanner(unittest.TestCase):
    """Test suite to validate the GLInfoBanner component behavior."""

    def test_info_banner_initialization(self):
        """Test default creation and text assignment."""
        banner = GLInfoBanner(
            "<b>Atajo:</b> Doble clic para abrir.",
            variant="info",
            icon_name="informacion"
        )
        self.assertIn("Doble clic", banner.text_label.text())
        self.assertEqual(banner.text_label.textFormat(), Qt.RichText)
        self.assertTrue(banner.text_label.wordWrap())

    def test_info_banner_variants(self):
        """Test that different variants apply without throwing errors."""
        for var in ["info", "tip", "warning", "success", "neutral"]:
            banner = GLInfoBanner("Texto de prueba", variant=var)
            self.assertIsNotNone(banner.styleSheet())

    def test_info_banner_set_text(self):
        """Test dynamic text update."""
        banner = GLInfoBanner("Original")
        banner.set_text("Nuevo mensaje actualizado")
        self.assertEqual(banner.text_label.text(), "Nuevo mensaje actualizado")

    def test_inventory_orders_banner_formatting(self):
        """Test the logic used for displaying active filtered orders in GLInfoBanner."""
        banner = GLInfoBanner(variant="tip")

        # Scenario 1: No orders selected
        total_orders = 5
        selected_ids = []
        if total_orders == 0 or len(selected_ids) == 0:
            order_text = '<span style="color: #EF4444; font-weight: bold;">(Ninguna orden seleccionada)</span>'
        banner.set_text(f"Órdenes activas: {order_text}")
        self.assertIn("Ninguna orden seleccionada", banner.text_label.text())

        # Scenario 2: All orders selected
        selected_ids = [1, 2, 3, 4, 5]
        if len(selected_ids) == total_orders:
            order_text = '<span style="color: #10B981; font-weight: bold;">Todas las órdenes</span>'
        banner.set_text(f"Órdenes activas: {order_text}")
        self.assertIn("Todas las órdenes", banner.text_label.text())

        # Scenario 3: 2 orders selected (<= 3)
        from sar.src.ui.design_system.utils.formatters import format_orden_filter_label
        todas = [
            {"orden_id": 1, "folio": "ORD-20260801-143022-X", "descripcion": "Subsidios Agosto 2026"},
            {"orden_id": 2, "folio": "ORD-20260303-112233", "descripcion": "Subsidios 2026 manual"}
        ]
        selected_ids = [1, 2]
        selected_objs = [o for o in todas if o["orden_id"] in selected_ids]
        names = []
        for o in selected_objs:
            label = format_orden_filter_label(o.get("folio", ""), o.get("descripcion", ""), max_desc_len=25)
            parts = label.split(" - ", 1)
            if len(parts) == 2:
                names.append(f"<b>{parts[0]}</b> ({parts[1]})")
            else:
                names.append(f"<b>{label}</b>")
        order_text = ", ".join(names)
        banner.set_text(f"Órdenes activas: {order_text}")
        self.assertIn("ORD-20260801", banner.text_label.text())
        self.assertNotIn("ORD-20260801-143022-X", banner.text_label.text())
        self.assertIn("ORD-20260303", banner.text_label.text())

        # Scenario 4: 4 orders selected (> 3)
        todas = [
            {"orden_id": 1, "folio": "ORD-20260801-143022-X", "descripcion": "A"},
            {"orden_id": 2, "folio": "ORD-20260303-112233", "descripcion": "B"},
            {"orden_id": 3, "folio": "ORD-20260828-999999", "descripcion": "C"},
            {"orden_id": 4, "folio": "ORD-20260901-000000", "descripcion": "D"}
        ]
        selected_ids = [1, 2, 3, 4]
        selected_objs = [o for o in todas if o["orden_id"] in selected_ids]
        names = []
        for o in selected_objs[:2]:
            label = format_orden_filter_label(o.get("folio", ""), o.get("descripcion", ""), max_desc_len=20)
            parts = label.split(" - ", 1)
            if len(parts) == 2:
                names.append(f"<b>{parts[0]}</b> ({parts[1]})")
            else:
                names.append(f"<b>{label}</b>")
        remaining = len(selected_objs) - 2
        order_text = f"{', '.join(names)} y +{remaining} órdenes más"
        banner.set_text(f"Órdenes activas: {order_text}")
        self.assertIn("+2 órdenes más", banner.text_label.text())
        self.assertIn("ORD-20260801", banner.text_label.text())


if __name__ == "__main__":
    unittest.main()

