import sys, os
sys.path.append(os.path.abspath('.'))

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QListView, QFrame, QComboBox
from PySide6.QtCore import Qt
from sar.src.ui.design_system.theme_manager import ThemeManager

app = QApplication(sys.argv)
ThemeManager.apply_theme(app, is_dark=False)

class CleanComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(130)
        self.setFixedHeight(36)
        
        list_view = QListView(self)
        list_view.setFrameShape(QFrame.NoFrame)
        self.setView(list_view)

    def showPopup(self):
        popup = self.view().window()
        if popup:
            popup.setAttribute(Qt.WA_TranslucentBackground, True)
            popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        super().showPopup()

w = QWidget()
w.resize(400, 300)
lay = QVBoxLayout(w)

cb = CleanComboBox(w)
cb.addItems(["-- Seleccione Notaría --", "NOTARIA 12", "NOTARIA 68", "NOTARIA 83"])
lay.addWidget(cb)
w.show()
app.processEvents()

cb.showPopup()
app.processEvents()

popup = cb.view().window()
print("Popup window isVisible:", popup.isVisible())
print("Popup window flags:", popup.windowFlags())

pix = popup.grab()
pix.save("scratch/clean_combo_before_super.png")
print("Saved scratch/clean_combo_before_super.png")
