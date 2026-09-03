import sys, os
sys.path.append(os.path.abspath('.'))

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QListView, QFrame
from PySide6.QtCore import Qt
from sar.src.ui.design_system.theme_manager import ThemeManager, Colors
from sar.src.ui.design_system.components import CustomComboBox

app = QApplication(sys.argv)

for is_dark in [False, True]:
    ThemeManager.apply_theme(app, is_dark=is_dark)

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
    mode_name = "dark" if is_dark else "light"
    pix = popup_window.grab()
    pix.save(f"scratch/combo_popup_clean_{mode_name}.png")
    print(f"Saved scratch/combo_popup_clean_{mode_name}.png")
