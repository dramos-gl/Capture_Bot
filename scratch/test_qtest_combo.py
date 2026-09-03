import sys, os
sys.path.append(os.path.abspath('.'))

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QListView, QFrame, QComboBox
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from sar.src.ui.design_system.theme_manager import ThemeManager
from sar.src.ui.design_system.components import CustomComboBox

app = QApplication(sys.argv)
ThemeManager.apply_theme(app, is_dark=False)

w = QWidget()
w.resize(400, 300)
lay = QVBoxLayout(w)

cb = CustomComboBox(w)
cb.addItems(["-- Seleccione Notaría --", "NOTARIA 12", "NOTARIA 68", "NOTARIA 83"])
lay.addWidget(cb)
w.show()
app.processEvents()

# Click the combobox
QTest.mouseClick(cb, Qt.LeftButton, pos=QPoint(cb.width() // 2, cb.height() // 2))
app.processEvents()

# Find the popup container
container = cb.view().parentWidget()
print("container:", container)
print("container isVisible:", container.isVisible() if container else None)
print("container stylesheet:", container.styleSheet() if container else None)

if container and container.isVisible():
    pix = container.grab()
    pix.save("scratch/qtest_combo_click.png")
    print("Saved scratch/qtest_combo_click.png")
