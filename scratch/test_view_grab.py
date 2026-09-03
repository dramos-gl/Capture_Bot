import sys, os
sys.path.append(os.path.abspath('.'))

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QComboBox
from PySide6.QtCore import Qt

app = QApplication(sys.argv)

qss_test = """
QWidget {
    background-color: #F8FAFC;
    color: #0F172A;
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 13px;
}
QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 3px 10px;
    min-height: 28px;
    max-height: 28px;
    color: #0F172A;
}
QComboBox:focus, QComboBox:on {
    border: 1.5px solid #2563EB;
}
QComboBox::drop-down {
    border: none;
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 30px;
}
QComboBox QAbstractItemView {
    border: 1px solid #CBD5E1;
    background-color: #FFFFFF;
    color: #0F172A;
    selection-background-color: #EEF2FF;
    selection-color: #1E293B;
    padding: 2px;
    outline: 0px;
}
QComboBox QAbstractItemView::item {
    min-height: 28px;
    padding: 4px 10px;
    background-color: #FFFFFF;
    color: #0F172A;
}
QComboBox QAbstractItemView::item:selected {
    background-color: #EEF2FF;
    color: #1E293B;
}
QComboBox QAbstractItemView::item:hover {
    background-color: #F1F5F9;
    color: #0F172A;
}
"""

app.setStyleSheet(qss_test)

w = QWidget()
w.resize(400, 300)
lay = QVBoxLayout(w)

cb = QComboBox(w)
cb.addItems(["-- Seleccione Tipo Destino --", "NOTARIA", "COLABORADOR"])
lay.addWidget(cb)
w.show()
app.processEvents()

cb.showPopup()
app.processEvents()

# Grab cb.view()
view = cb.view()
pix = view.grab()
pix.save("scratch/view_clean_grab.png")
print("Saved scratch/view_clean_grab.png")
