import sys, os
sys.path.append(os.path.abspath('.'))

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QListView, QFrame
from PySide6.QtCore import Qt
from sar.src.ui.design_system.theme_manager import ThemeManager
from sar.src.ui.design_system.components import CustomComboBox

app = QApplication(sys.argv)
ThemeManager.apply_theme(app, is_dark=False)

w = QWidget()
w.resize(400, 300)
lay = QVBoxLayout(w)

cb1 = CustomComboBox(w)
cb1.addItems(["-- Seleccione Notaría --", "NOTARIA 12", "NOTARIA 68", "NOTARIA 83"])
lay.addWidget(cb1)

w.show()
app.processEvents()

cb1.showPopup()
app.processEvents()

popup_window = cb1.view().window()
print("Popup window class:", popup_window.__class__.__name__)
print("Popup window flags:", popup_window.windowFlags())

pix = popup_window.grab()
pix.save("scratch/popup_window_grab.png")
print("Saved scratch/popup_window_grab.png")
