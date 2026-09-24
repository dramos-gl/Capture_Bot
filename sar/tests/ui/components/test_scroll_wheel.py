"""Unit tests for CustomComboBox and CustomSpinBox passive wheel event suppression."""

import sys
import unittest
from PySide6.QtWidgets import QApplication, QScrollArea, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QWheelEvent

# Ensure single QApplication instance
app = QApplication.instance() or QApplication(sys.argv)

from sar.src.ui.design_system.components.molecules.gl_combo_box import CustomComboBox
from sar.src.ui.design_system.components.atoms.gl_spin_box import CustomSpinBox
from sar.src.ui.design_system.components.organisms.gl_interactive_grid import InteractiveGridRow


class TestWheelEventSuppression(unittest.TestCase):
    """Test suite to ensure passive wheel events are ignored and don't change values."""

    def _create_wheel_event(self, delta_y: int = 120) -> QWheelEvent:
        """Helper to create a standard vertical wheel event."""
        pos = QPointF(10, 10)
        global_pos = QPointF(10, 10)
        pixel_delta = QPoint(0, 0)
        angle_delta = QPoint(0, delta_y)
        return QWheelEvent(
            pos,
            global_pos,
            pixel_delta,
            angle_delta,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False
        )

    def test_custom_combo_box_ignores_wheel_when_closed(self):
        """CustomComboBox must ignore wheel event and NOT change index when closed."""
        combo = CustomComboBox()
        combo.addItems(["Opción 1", "Opción 2", "Opción 3"])
        combo.setCurrentIndex(0)

        event = self._create_wheel_event(delta_y=-120)
        combo.wheelEvent(event)

        # Event must be ignored so parent scroll area receives it
        self.assertFalse(event.isAccepted())
        # Index must remain unchanged
        self.assertEqual(combo.currentIndex(), 0)

    def test_custom_spin_box_ignores_wheel(self):
        """CustomSpinBox must ignore wheel event and NOT change value."""
        spin = CustomSpinBox()
        spin.setRange(1, 100)
        spin.setValue(10)

        event = self._create_wheel_event(delta_y=120)
        spin.wheelEvent(event)

        # Event must be ignored
        self.assertFalse(event.isAccepted())
        # Value must remain unchanged
        self.assertEqual(spin.value(), 10)

    def test_interactive_grid_row_uses_custom_components(self):
        """InteractiveGridRow must use CustomSpinBox and CustomComboBox."""
        row = InteractiveGridRow()
        self.assertIsInstance(row.spin_cantidad, CustomSpinBox)
        self.assertIsInstance(row.combo_rfc, CustomComboBox)
        self.assertIsInstance(row.combo_concepto, CustomComboBox)
        self.assertIsInstance(row.combo_delegacion, CustomComboBox)
        self.assertIsInstance(row.combo_desarrollo, CustomComboBox)


if __name__ == "__main__":
    unittest.main()
