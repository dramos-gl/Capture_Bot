import sys, os
sys.path.append(os.path.abspath('.'))

from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QComboBox, QSpinBox, QLabel, QPushButton
from PySide6.QtCore import Qt

app = QApplication(sys.argv)

icons_dir = os.path.abspath("sar/src/ui/assets/icons").replace("\\", "/")
up_path = f"{icons_dir}/chevron_up.svg"
down_path = f"{icons_dir}/chevron_down.svg"

qss = f"""
QWidget {{
    background-color: #F8FAFC;
    font-size: 13px;
}}
QComboBox {{
    background-color: #FFFFFF;
    border: 1px solid #A9A9A9;
    border-radius: 6px;
    padding: 3px 10px;
    min-height: 28px;
    max-height: 28px;
    color: #1E293B;
}}
QComboBox::drop-down {{
    border: none;
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: url("{down_path}");
    width: 14px;
    height: 14px;
}}
QSpinBox {{
    background-color: #FFFFFF;
    border: 1px solid #A9A9A9;
    border-radius: 6px;
    padding: 3px 26px 3px 10px;
    min-height: 28px;
    max-height: 28px;
    color: #1E293B;
}}
QSpinBox::up-button {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 22px;
    border-left: 1px solid #CBD5E1;
    border-bottom: 0.5px solid #CBD5E1;
    background-color: transparent;
    margin: 1px 1px 0px 0px;
}}
QSpinBox::up-arrow {{
    image: url("{up_path}");
    width: 9px;
    height: 9px;
}}
QSpinBox::down-button {{
    subcontrol-origin: padding;
    subcontrol-position: bottom right;
    width: 22px;
    border-left: 1px solid #CBD5E1;
    border-top: 0.5px solid #CBD5E1;
    background-color: transparent;
    margin: 0px 1px 1px 0px;
}}
QSpinBox::down-arrow {{
    image: url("{down_path}");
    width: 9px;
    height: 9px;
}}
QLabel#disponibles {{
    background-color: #EFF6FF;
    color: #1D4ED8;
    border: 1px solid #BFDBFE;
    border-radius: 6px;
    font-weight: bold;
    font-size: 13px;
}}
QPushButton#delBtn {{
    border: none;
    background: transparent;
}}
"""

app.setStyleSheet(qss)

w = QWidget()
w.setFixedSize(700, 100)
lay = QHBoxLayout(w)
lay.setContentsMargins(12, 12, 12, 12)
lay.setSpacing(12)
lay.setAlignment(Qt.AlignVCenter)

cb = QComboBox()
cb.addItem("Seleccionar Concepto")
cb.setFixedHeight(36)

spin = QSpinBox()
spin.setValue(1)
spin.setFixedHeight(36)
spin.setFixedWidth(100)

lbl_disp = QLabel("—")
lbl_disp.setObjectName("disponibles")
lbl_disp.setAlignment(Qt.AlignCenter)
lbl_disp.setFixedHeight(36)
lbl_disp.setFixedWidth(80)

btn_del = QPushButton("🗑")
btn_del.setObjectName("delBtn")
btn_del.setFixedSize(36, 36)

lay.addWidget(cb, stretch=1)
lay.addWidget(spin)
lay.addWidget(lbl_disp)
lay.addWidget(btn_del)

w.show()
app.processEvents()

print(f"QComboBox:       y={cb.y()}, h={cb.height()}")
print(f"QSpinBox:        y={spin.y()}, h={spin.height()}")
print(f"lbl_disponibles: y={lbl_disp.y()}, h={lbl_disp.height()}")
print(f"btn_delete:      y={btn_del.y()}, h={btn_del.height()}")

pixmap = w.grab()
pixmap.save("scratch/perfect_aligned_row.png")
print("Saved scratch/perfect_aligned_row.png")
