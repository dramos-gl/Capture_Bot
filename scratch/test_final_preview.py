import sys, os
sys.path.append(os.path.abspath('.'))

from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QSpinBox
from sar.src.ui.design_system.theme_manager import ThemeManager

app = QApplication(sys.argv)
ThemeManager.apply_theme(app, is_dark=False)

w = QWidget()
w.setFixedSize(300, 100)
lay = QHBoxLayout(w)
spin = QSpinBox()
spin.setValue(6)
spin.setFixedHeight(35)
spin.setFixedWidth(120)
lay.addWidget(spin)

w.show()
pixmap = w.grab()
pixmap.save("scratch/final_spinbox_preview.png")
print("Saved final preview!")
