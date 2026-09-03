import sys, os
sys.path.append(os.path.abspath('.'))

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QFrame, QScrollArea, QWidget, QTextEdit, QSizePolicy
)
from PySide6.QtCore import Qt
from sar.src.ui.design_system.theme_manager import ThemeManager
from sar.src.ui.design_system.components import (
    CustomButton, CustomComboBox, CustomInput, CustomLabel, CustomCheckBox
)

app = QApplication(sys.argv)
ThemeManager.apply_theme(app, is_dark=False)

dialog = QDialog()
dialog.setWindowTitle("Asignar Derechos (1 de 2)")
dialog.resize(720, 580)

main_lay = QVBoxLayout(dialog)
main_lay.setContentsMargins(16, 12, 16, 12)
main_lay.setSpacing(8)

# 1. Fixed Header
lbl_info = QLabel(
    "<div><b style='color: #1E293B; font-size: 13px;'>Asignando Derecho 1 de 2:</b> "
    "<span style='color: #1D4ED8; font-weight: bold; font-size: 13px;'>CLG | PLA | CADURMA SA DE CV</span></div>"
    "<div style='font-size: 11px; color: #64748B; font-weight: bold;'>Referencia Portal: 70028672859919879</div>"
)
main_lay.addWidget(lbl_info)

# Nav Bar
nav = QFrame()
nav.setStyleSheet("background-color: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 6px; padding: 2px 8px;")
nav_lay = QHBoxLayout(nav)
nav_lay.setContentsMargins(4, 2, 4, 2)
btn_prev = CustomButton("◀ Anterior", is_secondary=True)
btn_prev.setMaximumWidth(100)
lbl_step = QLabel("Derecho 1 de 2")
lbl_step.setAlignment(Qt.AlignCenter)
lbl_step.setStyleSheet("font-weight: bold; font-size: 12px; color: #0F172A;")
btn_next = CustomButton("Siguiente ▶", is_secondary=False)
btn_next.setMaximumWidth(100)
nav_lay.addWidget(btn_prev)
nav_lay.addStretch()
nav_lay.addWidget(lbl_step)
nav_lay.addStretch()
nav_lay.addWidget(btn_next)
main_lay.addWidget(nav)

# Checkbox & Tipo Destino
chk = CustomCheckBox("Aplicar mismos datos / observaciones a los siguientes derechos")
main_lay.addWidget(chk)

dest_lay = QHBoxLayout()
dest_lay.addWidget(QLabel("Tipo Destino:"))
cb_dest = CustomComboBox()
cb_dest.addItems(["NOTARIA", "COLABORADOR"])
dest_lay.addWidget(cb_dest, stretch=1)
main_lay.addLayout(dest_lay)

# 2. Scrollable Body
scroll = QScrollArea()
scroll.setWidgetResizable(True)
scroll.setFrameShape(QFrame.NoFrame)
scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

content = QWidget()
content_lay = QVBoxLayout(content)
content_lay.setContentsMargins(0, 4, 0, 4)
content_lay.setSpacing(10)

# Card Notaria
card = QFrame()
card.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px;")
card_lay = QVBoxLayout(card)
card_lay.setContentsMargins(8, 8, 8, 8)
card_lay.setSpacing(8)

# Notaria & Solicitante
f1 = QFormLayout()
f1.addRow("Notaría *:", CustomComboBox())
f1.addRow("Solicitante Externo:", CustomInput("Nombre de la persona que solicita"))
card_lay.addLayout(f1)

# Ubicación
card_lay.addWidget(CustomLabel("🏠 UBICACIÓN DEL INMUEBLE", variant="subheader"))
f2 = QFormLayout()
f2.addRow("Desarrollo:", CustomComboBox())

coords_lay = QHBoxLayout()
coords_lay.setSpacing(4)
for name in ["SM", "Mz", "Lt", "Edif", "Viv"]:
    coords_lay.addWidget(QLabel(f"{name}:"))
    coords_lay.addWidget(CustomInput(name))
f2.addRow("Coordenadas:", coords_lay)
f2.addRow("Folio Electrónico:", CustomInput("Folio electrónico o número oficial"))
card_lay.addLayout(f2)

# Cliente y Crédito
card_lay.addWidget(CustomLabel("👤 CLIENTE Y CRÉDITO", variant="subheader"))
f3 = QFormLayout()
f3.addRow("Cliente *:", CustomInput("Nombre completo del cliente"))
fin_lay = QHBoxLayout()
fin_lay.addWidget(CustomInput("No. de crédito titular"), 2)
fin_lay.addWidget(QLabel("PA:"))
fin_lay.addWidget(CustomInput("PA / Paquete"), 1)
f3.addRow("Crédito / PA:", fin_lay)
card_lay.addLayout(f3)

# Fechas
card_lay.addWidget(CustomLabel("📅 SEGUIMIENTO Y FECHAS NOTARIALES / RPP", variant="subheader"))
f4 = QFormLayout()
row_fechas1 = QHBoxLayout()
row_fechas1.addWidget(CustomInput("AAAA-MM-DD"))
row_fechas1.addWidget(QLabel("F. Ingreso RPP:"))
row_fechas1.addWidget(CustomInput("AAAA-MM-DD"))
f4.addRow("F. Solicitud:", row_fechas1)

row_fechas2 = QHBoxLayout()
row_fechas2.addWidget(CustomInput("AAAA-MM-DD"))
row_fechas2.addWidget(QLabel("F. Escritura:"))
row_fechas2.addWidget(CustomInput("AAAA-MM-DD"))
f4.addRow("F. Rep. Notaría:", row_fechas2)

row_fechas3 = QHBoxLayout()
row_fechas3.addWidget(CustomInput("AAAA-MM-DD"))
row_fechas3.addWidget(QLabel("Estatus RPP:"))
row_fechas3.addWidget(CustomInput("NUEVO INGRESO"))
f4.addRow("F. Titulación:", row_fechas3)
card_lay.addLayout(f4)

# Comentarios & Obs
f5 = QFormLayout()
f5.addRow("Comentarios:", CustomInput("Comentarios notariales..."))
obs = QTextEdit()
obs.setMaximumHeight(60)
obs.setPlaceholderText("Observaciones generales...")
f5.addRow("Observaciones:", obs)
card_lay.addLayout(f5)

content_lay.addWidget(card)
scroll.setWidget(content)
main_lay.addWidget(scroll, stretch=1)

# 3. Fixed Footer
footer_lay = QHBoxLayout()
footer_lay.setContentsMargins(0, 4, 0, 0)
btn_cancel = CustomButton("Cancelar", is_secondary=True)
btn_save = CustomButton("Guardar")
footer_lay.addStretch()
footer_lay.addWidget(btn_cancel)
footer_lay.addWidget(btn_save)
main_lay.addLayout(footer_lay)

dialog.show()
app.processEvents()

pixmap = dialog.grab()
pixmap.save("scratch/dialog_responsive_preview.png")
print("Preview saved to scratch/dialog_responsive_preview.png")
