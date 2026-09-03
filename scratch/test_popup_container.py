import sys, os
sys.path.append(os.path.abspath('.'))

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QListView, QFrame, QComboBox, QMainWindow
from PySide6.QtCore import Qt
from sar.src.ui.design_system.theme_manager import ThemeManager

app = QApplication(sys.argv)
ThemeManager.apply_theme(app, is_dark=False)

win = QMainWindow()
win.resize(500, 400)
central = QWidget()
win.setCentralWidget(central)
lay = QVBoxLayout(central)

cb = QComboBox()
cb.addItems(["-- Seleccione Notaría --", "NOTARIA 12", "NOTARIA 68", "NOTARIA 83"])
view = QListView(cb)
view.setFrameShape(QFrame.NoFrame)
cb.setView(view)

# Configure the container
container = view.parentWidget()
if container:
    container.setAttribute(Qt.WA_TranslucentBackground, True)
    container.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)

lay.addWidget(cb)
win.show()
app.processEvents()

cb.showPopup()
app.processEvents()

# Grab the whole window area including popup using screen grab
screen = QApplication.primaryScreen()
if screen:
    pix = screen.grabWindow(0, win.x(), win.y(), win.width(), win.height() + 200)
    pix.save("scratch/screen_combo_grab.png")
    print("Screen grab saved to scratch/screen_combo_grab.png")
