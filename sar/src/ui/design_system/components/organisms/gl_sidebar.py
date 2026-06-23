"""Sidebar Navigation Organism matching the target design mockup."""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QButtonGroup, QSpacerItem, QSizePolicy, QWidget, QLabel, QMessageBox
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIcon
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.utils.icons import Icons

class NavigationSidebar(QFrame):
    """Sidebar mejorado con mejor jerarquía visual e interacción."""
    
    # Signals
    nav_selected = Signal(str)
    theme_toggled = Signal()
    logout_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarFrame")
        self.setFixedWidth(250)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 24, 16, 16)
        self.layout.setSpacing(10)
        
        self._setup_brand_area()
        self._setup_navigation()
        self._setup_footer()
        
    def _setup_brand_area(self):
        # 1. Brand Logo & Title Area
        self.brand_layout = QHBoxLayout()
        self.brand_layout.setContentsMargins(0, 0, 0, 0)
        self.brand_layout.setSpacing(12)
        
        # Rounded logo box
        self.logo_label = QLabel(self)
        self.logo_label.setFixedSize(42, 42)
        self.logo_label.setObjectName("sidebarLogo")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setPixmap(Icons.file_text("#FFFFFF").pixmap(24, 24))
        self.brand_layout.addWidget(self.logo_label)
        
        self.title_text_layout = QVBoxLayout()
        self.title_text_layout.setContentsMargins(0, 0, 0, 0)
        self.title_text_layout.setSpacing(0)
        
        self.brand_title = CustomLabel("SAR", variant="header")
        self.brand_title.setObjectName("sidebarBrandTitle")
        
        self.brand_subtitle = CustomLabel("CapturaBot System", variant="muted")
        self.brand_subtitle.setObjectName("sidebarBrandSubtitle")
        
        self.title_text_layout.addWidget(self.brand_title)
        self.title_text_layout.addWidget(self.brand_subtitle)
        self.brand_layout.addLayout(self.title_text_layout)
        
        self.layout.addLayout(self.brand_layout)
        self.layout.addSpacing(24)
        
    def _setup_navigation(self):
        # 2. Navigation Button Group
        self.menu_items = [
            ("Dashboard", "dashboard", "dashboard"),
            ("Órdenes", "ordenes", "list_icon"),
            ("Solicitudes", "solicitudes", "file_text"),
            ("Referencias", "referencias", "database"),
            ("Administración", "configuracion", "shield_lock")
        ]
        
        self.buttons = {}
        self.submenu_visible = False
        
        # Submenu container and layout
        self.submenu_container = QWidget()
        self.submenu_container.setObjectName("submenuContainer")
        self.submenu_container.setStyleSheet("""
            QWidget#submenuContainer {
                border-left: none;
                margin-left: 0px;
                padding-left: 0px;
                background: transparent;
            }
        """)
        self.submenu_layout = QVBoxLayout(self.submenu_container)
        self.submenu_layout.setContentsMargins(0, 0, 0, 0)
        self.submenu_layout.setSpacing(4)
        
        self.btn_ordenes_capturadas = QPushButton("Órdenes Capturadas")
        self.btn_ordenes_capturadas.setObjectName("subNavBtn")
        self.btn_ordenes_capturadas.setCheckable(True)
        self.btn_ordenes_capturadas.setIcon(Icons.hollow_dot("#94A3B8"))
        
        self.btn_capturar_nueva = QPushButton("Capturar Nueva Orden")
        self.btn_capturar_nueva.setObjectName("subNavBtn")
        self.btn_capturar_nueva.setCheckable(True)
        self.btn_capturar_nueva.setIcon(Icons.hollow_dot("#94A3B8"))
        
        self.submenu_layout.addWidget(self.btn_ordenes_capturadas)
        self.submenu_layout.addWidget(self.btn_capturar_nueva)
        
        self.buttons["ordenes_capturadas"] = self.btn_ordenes_capturadas
        self.buttons["capturar_orden"] = self.btn_capturar_nueva
        
        def _update_btn_icon(btn, icon_name, checked):
            if hasattr(Icons, icon_name):
                icon_fn = getattr(Icons, icon_name)
                btn.setIcon(icon_fn("#2563EB" if checked else "#475569"))
                
        for index, (text, key, icon_name) in enumerate(self.menu_items):
            btn = QPushButton(text)
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            
            # Connect icon updating to state toggle
            btn.toggled.connect(lambda checked, b=btn, n=icon_name: _update_btn_icon(b, n, checked))
            
            # Select first item by default (Dashboard)
            if index == 0:
                btn.setChecked(True)
                _update_btn_icon(btn, icon_name, True)
            else:
                _update_btn_icon(btn, icon_name, False)
                
            self.layout.addWidget(btn)
            self.buttons[key] = btn
            
            if key == "ordenes":
                # Add layout for chevron label
                arrow_layout = QHBoxLayout(btn)
                arrow_layout.setContentsMargins(0, 0, 16, 0)
                arrow_layout.addStretch()
                self.chevron_label = QLabel()
                self.chevron_label.setStyleSheet("background: transparent;")
                self.chevron_label.setPixmap(Icons.chevron_down("#475569").pixmap(12, 12))
                arrow_layout.addWidget(self.chevron_label)
                
                # Add submenu container immediately below "Órdenes"
                self.layout.addWidget(self.submenu_container)
                self.submenu_container.hide()
            
            # Connect clicked handler
            btn.clicked.connect(lambda checked, k=key: self._on_main_nav_clicked(k))
            
        self.btn_ordenes_capturadas.clicked.connect(lambda: self._on_sub_nav_clicked("ordenes_capturadas"))
        self.btn_capturar_nueva.clicked.connect(lambda: self._on_sub_nav_clicked("capturar_orden"))

    def _setup_footer(self):
        # Add spacer
        self.layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # 3. Bottom controls
        # Theme dropdown toggle button (Sun icon + Dropdown indicator)
        self.theme_btn = QPushButton("Cambiar Tema")
        self.theme_btn.setObjectName("themeToggleBtn")
        self.theme_btn.setIcon(Icons.calendar()) # Place placeholder icon, theme will handle
        self.theme_btn.clicked.connect(self.theme_toggled.emit)
        self.layout.addWidget(self.theme_btn)
        
        # Logout button (Red outline styled with power icon)
        self.logout_btn = QPushButton(" Cerrar Sesión")
        self.logout_btn.setObjectName("logoutBtn")
        self.logout_btn.setIcon(Icons.power("#DC2626"))
        self.logout_btn.clicked.connect(self._on_logout_clicked)
        self.layout.addWidget(self.logout_btn)
        
        self.layout.addSpacing(16)
        
        # 4. User profile status block at the bottom
        self.profile_widget = QWidget(self)
        self.profile_widget.setStyleSheet("background: transparent;")
        self.profile_layout = QHBoxLayout(self.profile_widget)
        self.profile_layout.setContentsMargins(0, 0, 0, 0)
        self.profile_layout.setSpacing(10)
        
        self.lbl_profile_icon = QLabel()
        self.lbl_profile_icon.setPixmap(Icons.user("#64748B").pixmap(20, 20))
        self.lbl_profile_icon.setStyleSheet("background: transparent;")
        
        self.profile_text_layout = QVBoxLayout()
        self.profile_text_layout.setContentsMargins(0, 0, 0, 0)
        self.profile_text_layout.setSpacing(2)
        
        self.lbl_profile_user = CustomLabel("Usuario: Administrador", variant="body")
        self.lbl_profile_user.setObjectName("sidebarProfileUser")
        
        self.lbl_profile_status = CustomLabel("Sesión activa", variant="muted")
        self.lbl_profile_status.setObjectName("sidebarProfileStatus")
        
        self.profile_text_layout.addWidget(self.lbl_profile_user)
        self.profile_text_layout.addWidget(self.lbl_profile_status)
        
        self.profile_layout.addWidget(self.lbl_profile_icon)
        self.profile_layout.addLayout(self.profile_text_layout)
        self.profile_layout.addStretch()
        
        self.layout.addWidget(self.profile_widget)

    def _on_main_nav_clicked(self, clicked_key: str):
        if clicked_key == "ordenes":
            # Toggle submenu visibility
            self.submenu_visible = not self.submenu_visible
            self.submenu_container.setVisible(self.submenu_visible)
            # Update chevron icon based on state
            color = "#2563EB" if self.buttons["ordenes"].isChecked() else "#475569"
            if self.submenu_visible:
                self.chevron_label.setPixmap(Icons.chevron_up(color).pixmap(12, 12))
            else:
                self.chevron_label.setPixmap(Icons.chevron_down(color).pixmap(12, 12))
            
            # If submenus are opened, trigger default submenu navigation (capturar_orden)
            self._on_sub_nav_clicked("capturar_orden")
            return

        # Regular main navigation click - Keep the submenu fixed (do not hide) as requested!
        # Check clicked, uncheck others
        for key, btn in self.buttons.items():
            if key in ["ordenes_capturadas", "capturar_orden"]:
                btn.setChecked(False)
                btn.setIcon(Icons.hollow_dot("#94A3B8"))
            else:
                btn.setChecked(key == clicked_key)
                
        # Keep Órdenes arrow chevron matching its checked state (it's not checked)
        self.chevron_label.setPixmap(Icons.chevron_down("#475569").pixmap(12, 12))
                
        self.nav_selected.emit(clicked_key)
        
    def _on_sub_nav_clicked(self, clicked_key: str):
        # Highlighting the parent menu
        self.buttons["ordenes"].setChecked(True)
        self.chevron_label.setPixmap(Icons.chevron_up("#2563EB").pixmap(12, 12))
        
        # Uncheck all other main nav buttons
        for key, btn in self.buttons.items():
            if key not in ["ordenes", "ordenes_capturadas", "capturar_orden"]:
                btn.setChecked(False)
                
        # Handle submenus check states
        for key in ["ordenes_capturadas", "capturar_orden"]:
            btn = self.buttons[key]
            if key == clicked_key:
                btn.setChecked(True)
                btn.setIcon(Icons.dot("#2563EB"))
            else:
                btn.setChecked(False)
                btn.setIcon(Icons.hollow_dot("#94A3B8"))
                
        self.nav_selected.emit(clicked_key)

    def select_item(self, key: str):
        """Allows programmatically checking a navigation item button."""
        if key in ["ordenes_capturadas", "capturar_orden"]:
            self._on_sub_nav_clicked(key)
        elif key in self.buttons:
            self._on_main_nav_clicked(key)
            
    def hide_item(self, key: str):
        """Hides a specific navigation item by its key."""
        if key in self.buttons:
            self.buttons[key].hide()
            
    def set_username(self, username: str):
        """Updates the username in the profile status widget."""
        self.lbl_profile_user.setText(f"Usuario: {username}")
        
    def _on_logout_clicked(self):
        """Displays a confirmation dialog before emitting logout signal."""
        reply = QMessageBox.question(
            self, "Confirmar Salida",
            "¿Estás seguro de que deseas cerrar sesión?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.logout_requested.emit()
