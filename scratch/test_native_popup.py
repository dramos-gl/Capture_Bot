import sys, os
sys.path.append(os.path.abspath('.'))

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QListView, QFrame, QComboBox
from PySide6.QtCore import Qt
from sar.src.ui.design_system.theme_manager import ThemeManager

app = QApplication(sys.argv)
ThemeManager.apply_theme(app, is_dark=False)

w = QWidget()
w.resize(400, 300)
lay = QVBoxLayout(w)

cb = QComboBox()
cb.addItems(["-- Seleccione Notaría --", "NOTARIA 12", "NOTARIA 68", "NOTARIA 83"])
lay.addWidget(cb)
w.show()
app.processEvents()

cb.showPopup()
app.processEvents()

# Find the popup window
popup = None
for top in QApplication.topLevelWidgets():
    if top.isVisible() and top != w:
        popup = top
        break

if popup:
    print("Found popup:", popup)
    pix = popup.grab()
    pix.save("scratch/native_default_popup.png")
    print("Saved scratch/native_default_popup.png")
