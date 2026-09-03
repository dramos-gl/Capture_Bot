import sys, os
sys.path.append(os.path.abspath('.'))

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QListView, QFrame, QComboBox
from PySide6.QtCore import Qt
from sar.src.ui.design_system.theme_manager import ThemeManager

app = QApplication(sys.argv)
ThemeManager.apply_theme(app, is_dark=False)

cb = QComboBox()
cb.addItems(["-- Seleccione Notaría --", "NOTARIA 12", "NOTARIA 68", "NOTARIA 83"])
view = QListView(cb)
view.setFrameShape(QFrame.NoFrame)
cb.setView(view)

# Let's inspect the container
container = view.parentWidget()
print("view.parentWidget():", container)
if container:
    print("container class:", container.__class__.__name__)
    print("container metaObject:", container.metaObject().className())

cb.show()
app.processEvents()

cb.showPopup()
app.processEvents()

# Find all top-level widgets in app
for top in QApplication.topLevelWidgets():
    if top.isVisible() and top != cb.window():
        print("Top level popup:", top, top.metaObject().className())
        top.setStyleSheet("QFrame { border: none; background: transparent; }")
        pix = top.grab()
        pix.save("scratch/top_level_popup_test.png")
        print("Saved top level popup test screenshot")
