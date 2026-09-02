import sys, os
sys.path.append(os.path.abspath('.'))

from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QSpinBox, QLabel
from sar.src.ui.design_system.theme_manager import ThemeManager

app = QApplication(sys.argv)

w = QWidget()
w.setFixedSize(500, 220)
lay = QVBoxLayout(w)

icons_dir = os.path.abspath("sar/src/ui/assets/icons").replace("\\", "/")
up_light = f"{icons_dir}/chevron_up.svg"
down_light = f"{icons_dir}/chevron_down.svg"
up_dark = f"{icons_dir}/chevron_up_dark.svg"
down_dark = f"{icons_dir}/chevron_down_dark.svg"

def make_spin_qss(is_dark):
    bg = "#1E293B" if is_dark else "#FFFFFF"
    border = "#334155" if is_dark else "#A9A9A9"
    divider = "#475569" if is_dark else "#CBD5E1"
    hover_bg = "rgba(255, 255, 255, 0.08)" if is_dark else "#F1F5F9"
    txt = "#F8FAFC" if is_dark else "#1E293B"
    up_path = up_dark if is_dark else up_light
    down_path = down_dark if is_dark else down_light

    return f"""
    QSpinBox, QDoubleSpinBox {{
        background-color: {bg};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 2px 26px 2px 10px;
        color: {txt};
        font-size: 13px;
        height: 35px;
        min-height: 35px;
        max-height: 35px;
    }}
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1.5px solid #2563EB;
    }}
    QSpinBox::up-button, QDoubleSpinBox::up-button {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 22px;
        border-left: 1px solid {divider};
        border-bottom: 0.5px solid {divider};
        background-color: transparent;
        margin: 1px 1px 0px 0px;
    }}
    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
        background-color: {hover_bg};
    }}
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
        image: url("{up_path}");
        width: 10px;
        height: 10px;
    }}
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        subcontrol-origin: padding;
        subcontrol-position: bottom right;
        width: 22px;
        border-left: 1px solid {divider};
        border-top: 0.5px solid {divider};
        background-color: transparent;
        margin: 0px 1px 1px 0px;
    }}
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
        background-color: {hover_bg};
    }}
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
        image: url("{down_path}");
        width: 10px;
        height: 10px;
    }}
    """

# Light sample
row_light = QHBoxLayout()
lbl_l = QLabel("Light Mode:")
spin_l = QSpinBox()
spin_l.setStyleSheet(make_spin_qss(False))
spin_l.setValue(6)
spin_l.setFixedHeight(35)
spin_l.setFixedWidth(120)
row_light.addWidget(lbl_l)
row_light.addWidget(spin_l)
lay.addLayout(row_light)

# Dark sample
row_dark = QHBoxLayout()
lbl_d = QLabel("Dark Mode:")
spin_d = QSpinBox()
spin_d.setStyleSheet(make_spin_qss(True))
spin_d.setValue(12)
spin_d.setFixedHeight(35)
spin_d.setFixedWidth(120)
row_dark.addWidget(lbl_d)
row_dark.addWidget(spin_d)
lay.addLayout(row_dark)

w.show()
pixmap = w.grab()
pixmap.save("scratch/spinbox_comparison.png")
print("Comparison saved!")
