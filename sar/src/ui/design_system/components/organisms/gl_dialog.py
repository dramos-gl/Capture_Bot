"""Custom Frameless Dialog Organism."""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtCore import Qt
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.utils.icons import Icons

class CustomDialog(QDialog):
    """A frameless floating dialog with custom header and footer."""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(400)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.main_frame = QWidget(self)
        self.main_frame.setObjectName("dialogMainFrame")
        self.main_layout = QVBoxLayout(self.main_frame)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Header
        self.header = QWidget(self.main_frame)
        self.header.setObjectName("dialogHeader")
        self.header.setFixedHeight(40)
        self.header_layout = QHBoxLayout(self.header)
        self.header_layout.setContentsMargins(16, 0, 8, 0)
        
        self.lbl_title = CustomLabel(title, variant="header")
        self.lbl_title.setStyleSheet("background-color: transparent; font-size: 14px; font-weight: bold; color: white;")
        
        self.btn_min = CustomButton("", is_secondary=True)
        self.btn_min.setIcon(Icons.minimize())
        self.btn_min.setFixedSize(30, 30)
        self.btn_min.setObjectName("dialogHeaderBtn")
        self.btn_min.clicked.connect(self.showMinimized)
        
        self.btn_close = CustomButton("", is_secondary=True)
        self.btn_close.setIcon(Icons.close())
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setObjectName("dialogHeaderBtn")
        self.btn_close.clicked.connect(self.reject)
        
        self.header_layout.addWidget(self.lbl_title)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.btn_min)
        self.header_layout.addWidget(self.btn_close)
        
        # Body (for content injection)
        self.body_container = QWidget(self.main_frame)
        self.body_layout = QVBoxLayout(self.body_container)
        self.body_layout.setContentsMargins(24, 24, 24, 24)
        self.body_layout.setSpacing(16)
        
        # Footer
        self.footer = QWidget(self.main_frame)
        self.footer.setObjectName("dialogFooter")
        self.footer.setFixedHeight(60)
        self.footer_layout = QHBoxLayout(self.footer)
        self.footer_layout.setContentsMargins(24, 0, 24, 0)
        
        self.btn_cancel = CustomButton("Cancelar", is_secondary=True, icon_name="close")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_save = CustomButton("Guardar", icon_name="save")
        self.btn_save.clicked.connect(self.accept)
        
        self.footer_layout.addStretch()
        self.footer_layout.addWidget(self.btn_cancel)
        self.footer_layout.addWidget(self.btn_save)
        
        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(self.body_container, stretch=1)
        self.main_layout.addWidget(self.footer)
        
        self.layout.addWidget(self.main_frame)
        
        # Dragging support
        self._drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.header.geometry().contains(event.pos()):
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            diff = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + diff)
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()
        
    def add_widget(self, widget: QWidget):
        self.body_layout.addWidget(widget)
        
    def add_stretch(self):
        self.body_layout.addStretch()
