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
        self.setMinimumWidth(360)
        self.setMinimumHeight(300)
        
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

        self.btn_max = CustomButton("", is_secondary=True)
        self.btn_max.setIcon(Icons.pantalla_completa())
        self.btn_max.setFixedSize(30, 30)
        self.btn_max.setObjectName("dialogHeaderBtn")
        self.btn_max.clicked.connect(self._toggle_maximize)

        self.btn_close = CustomButton("", is_secondary=True)
        self.btn_close.setIcon(Icons.close())
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setObjectName("dialogHeaderBtn")
        self.btn_close.clicked.connect(self.reject)

        self.header_layout.addWidget(self.lbl_title)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.btn_min)
        self.header_layout.addWidget(self.btn_max)
        self.header_layout.addWidget(self.btn_close)

        # Body (for content injection)
        self.body_container = QWidget(self.main_frame)
        self.body_layout = QVBoxLayout(self.body_container)
        self.body_layout.setContentsMargins(16, 16, 16, 16)
        self.body_layout.setSpacing(12)

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

        # Dragging and Resizing support
        self._drag_pos = None
        self._resize_edge = None
        self._is_maximized = False
        self._normal_geometry = None
        self.setMouseTracking(True)
        self.main_frame.setMouseTracking(True)
        self.header.setMouseTracking(True)

    def showEvent(self, event):
        super().showEvent(event)
        # Cap dialog size to fit screen/parent height so footer (Guardar/Cancelar) is always visible
        screen_geo = None
        if self.parent():
            screen_geo = self.parent().window().geometry()
        elif self.screen():
            screen_geo = self.screen().availableGeometry()

        if screen_geo:
            max_h = max(300, screen_geo.height() - 40)
            max_w = max(360, screen_geo.width() - 40)
            target_w = min(self.width(), max_w)
            target_h = min(self.height(), max_h)
            if self.width() > target_w or self.height() > target_h:
                self.resize(target_w, target_h)

    def _toggle_maximize(self):
        if self._is_maximized:
            if self._normal_geometry:
                self.setGeometry(self._normal_geometry)
            self._is_maximized = False
        else:
            self._normal_geometry = self.geometry()
            if self.parent():
                parent_geo = self.parent().window().geometry()
                self.setGeometry(parent_geo)
            else:
                screen = self.screen()
                if screen:
                    self.setGeometry(screen.availableGeometry())
            self._is_maximized = True

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            margin = 8
            w, h = self.width(), self.height()
            
            # Check edge resize
            edge = 0
            if pos.x() >= w - margin: edge |= 2  # Right
            if pos.y() >= h - margin: edge |= 8  # Bottom
            
            if edge > 0 and not self._is_maximized:
                self._resize_edge = edge
                self._drag_pos = event.globalPosition().toPoint()
            elif self.header.geometry().contains(pos):
                self._drag_pos = event.globalPosition().toPoint()
                self._resize_edge = None
            event.accept()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        margin = 8
        w, h = self.width(), self.height()
        
        # Cursor styling for resize margins
        if not self._is_maximized:
            if pos.x() >= w - margin and pos.y() >= h - margin:
                self.setCursor(Qt.SizeFDiagCursor)
            elif pos.x() >= w - margin:
                self.setCursor(Qt.SizeHorCursor)
            elif pos.y() >= h - margin:
                self.setCursor(Qt.SizeVerCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

        if self._resize_edge and event.buttons() == Qt.LeftButton:
            diff = event.globalPosition().toPoint() - self._drag_pos
            new_w = max(self.minimumWidth(), self.width() + diff.x())
            new_h = max(self.minimumHeight(), self.height() + diff.y())
            self.resize(new_w, new_h)
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()
        elif self._drag_pos is not None and event.buttons() == Qt.LeftButton and not self._resize_edge:
            if not self._is_maximized:
                diff = event.globalPosition().toPoint() - self._drag_pos
                self.move(self.pos() + diff)
                self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        self._resize_edge = None
        event.accept()

    def add_widget(self, widget: QWidget):
        self.body_layout.addWidget(widget)

    def add_stretch(self):
        self.body_layout.addStretch()
