"""Sidebar Navigation Organism matching the target design mockup."""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QButtonGroup, QSpacerItem, QSizePolicy, QWidget, QLabel, QScrollArea
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIcon
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
from sar.src.ui.design_system.utils.icons import Icons
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.theme_manager import ThemeManager

class NavigationSidebar(QFrame):
    """Sidebar mejorado con mejor jerarquía visual e interacción, con scrollbar automático."""
    
    # Signals
    nav_selected = Signal(str)
    theme_toggled = Signal()
    logout_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarFrame")
        self.setFixedWidth(250)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Ignored)
        self.setMinimumHeight(0)
        
        # Main outer layout to contain the 3 decoupled areas
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        
        # 1. Brand Area Container (Fixed Top)
        self.brand_widget = QWidget(self)
        self.brand_widget.setObjectName("sidebarBrandContainer")
        self.brand_widget.setStyleSheet("QWidget#sidebarBrandContainer { background: transparent; }")
        self.brand_layout = QVBoxLayout(self.brand_widget)
        self.brand_layout.setContentsMargins(16, 20, 16, 12)
        self.brand_layout.setSpacing(10)
        outer_layout.addWidget(self.brand_widget)
        
        # 2. Scroll Area for navigation items (Middle - Flexible)
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        self.scroll_area.setMinimumHeight(50)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QWidget#scrollContent {
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94A3B8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: transparent;
                height: 0px;
            }
        """)
        
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        scroll_content.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        self.nav_layout = QVBoxLayout(scroll_content)
        self.nav_layout.setContentsMargins(16, 0, 16, 0)
        self.nav_layout.setSpacing(6)
        
        self.scroll_area.setWidget(scroll_content)
        outer_layout.addWidget(self.scroll_area, stretch=1)
        
        # 3. Footer Area Container (Fixed Bottom - Pinned Logout and Profile)
        self.footer_widget = QWidget(self)
        self.footer_widget.setObjectName("sidebarFooterContainer")
        # Borde del footer se adapta al tema activo
        _border_color = Colors.BORDER_DARK if ThemeManager.is_dark_active() else Colors.BORDER_LIGHT
        self.footer_widget.setStyleSheet(
            f"QWidget#sidebarFooterContainer {{ background: transparent; border-top: 1px solid {_border_color}; }}"
        )
        self.footer_layout = QVBoxLayout(self.footer_widget)
        self.footer_layout.setContentsMargins(16, 12, 16, 16)
        self.footer_layout.setSpacing(8)
        outer_layout.addWidget(self.footer_widget)
        
        self._setup_brand_area()
        self._setup_navigation()
        self._setup_footer()
        
    def _setup_brand_area(self):
        self.is_collapsed = False
        
        # Row with Hamburger
        self.hamburger_layout = QHBoxLayout()
        self.hamburger_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_hamburger = QPushButton()
        self.btn_hamburger.setFixedSize(36, 36)
        self.btn_hamburger.setObjectName("secondaryBtn")
        self.btn_hamburger.setIcon(Icons.menu("#475569"))
        self.btn_hamburger.setStyleSheet("border: none; background: transparent;")
        self.btn_hamburger.clicked.connect(self.toggle_collapse)
        
        self.hamburger_layout.addStretch()
        self.hamburger_layout.addWidget(self.btn_hamburger)
        self.brand_layout.addLayout(self.hamburger_layout)
        
        # Row with Brand info
        self.brand_info_layout = QHBoxLayout()
        self.brand_info_layout.setContentsMargins(0, 0, 0, 0)
        self.brand_info_layout.setSpacing(12)
        
        # Rounded logo box
        self.logo_label = QLabel(self)
        self.logo_label.setFixedSize(42, 42)
        self.logo_label.setObjectName("sidebarLogo")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setPixmap(Icons.file_text("#FFFFFF").pixmap(24, 24))
        self.brand_info_layout.addWidget(self.logo_label)
        
        self.title_text_layout = QVBoxLayout()
        self.title_text_layout.setContentsMargins(0, 0, 0, 0)
        self.title_text_layout.setSpacing(0)
        
        self.brand_title = CustomLabel("SAR", variant="header")
        self.brand_title.setObjectName("sidebarBrandTitle")
        
        self.brand_subtitle = CustomLabel("CapturaBot System", variant="muted")
        self.brand_subtitle.setObjectName("sidebarBrandSubtitle")
        
        self.title_text_layout.addWidget(self.brand_title)
        self.title_text_layout.addWidget(self.brand_subtitle)
        self.brand_info_layout.addLayout(self.title_text_layout)
        
        self.brand_layout.addLayout(self.brand_info_layout)
        
    def _setup_navigation(self):
        # 2. Navigation Button Group
        self.menu_items = [
            ("Dashboard", "dashboard", "dashboard"),
            ("Órdenes", "ordenes", "list_icon"),
            ("Derechos", "referencias", "database"),
            ("Control de Derechos", "inventario", "tabla"),
            ("Administración", "configuracion", "shield_lock")
        ]
        
        self.buttons = {}
        self.submenu_visible = False
        self.inv_submenu_visible = False
        
        # --- SUBMENU 1: ÓRDENES ---
        self.submenu_container = QWidget()
        self.submenu_container.setObjectName("submenuContainer")
        self.submenu_container.setStyleSheet("QWidget#submenuContainer { background: transparent; }")
        self.submenu_layout = QVBoxLayout(self.submenu_container)
        self.submenu_layout.setContentsMargins(0, 0, 0, 0)
        self.submenu_layout.setSpacing(4)
        
        self.btn_ordenes_capturadas = QPushButton("Órdenes Capturadas")
        self.btn_ordenes_capturadas.setObjectName("subNavBtn")
        self.btn_ordenes_capturadas.setCheckable(True)
        self.btn_ordenes_capturadas.setIcon(Icons.hollow_dot("#94A3B8"))
        self.btn_ordenes_capturadas.setVisible(False)
        
        self.btn_capturar_nueva = QPushButton("Capturar Nueva Orden")
        self.btn_capturar_nueva.setObjectName("subNavBtn")
        self.btn_capturar_nueva.setCheckable(True)
        self.btn_capturar_nueva.setIcon(Icons.hollow_dot("#94A3B8"))
        self.btn_capturar_nueva.setVisible(False)
        
        self.btn_solicitudes = QPushButton("Solicitudes")
        self.btn_solicitudes.setObjectName("subNavBtn")
        self.btn_solicitudes.setCheckable(True)
        self.btn_solicitudes.setIcon(Icons.hollow_dot("#94A3B8"))
        self.btn_solicitudes.setVisible(False)
        
        self.submenu_layout.addWidget(self.btn_capturar_nueva)
        self.submenu_layout.addWidget(self.btn_ordenes_capturadas)
        self.submenu_layout.addWidget(self.btn_solicitudes)
        
        self.buttons["ordenes_capturadas"] = self.btn_ordenes_capturadas
        self.buttons["capturar_orden"] = self.btn_capturar_nueva
        self.buttons["solicitudes"] = self.btn_solicitudes
 
        # --- SUBMENU 2: INVENTARIO ---
        self.inv_submenu_container = QWidget()
        self.inv_submenu_container.setObjectName("invSubmenuContainer")
        self.inv_submenu_container.setStyleSheet("QWidget#invSubmenuContainer { background: transparent; }")
        self.inv_submenu_layout = QVBoxLayout(self.inv_submenu_container)
        self.inv_submenu_layout.setContentsMargins(0, 0, 0, 0)
        self.inv_submenu_layout.setSpacing(4)
 
        self.btn_inv_facturas = QPushButton("Inventario")
        self.btn_inv_facturas.setObjectName("subNavBtn")
        self.btn_inv_facturas.setCheckable(True)
        self.btn_inv_facturas.setIcon(Icons.hollow_dot("#94A3B8"))
        self.btn_inv_facturas.setVisible(False)
 
        self.btn_inv_masivo = QPushButton("Asignar/Validar por Lotes")
        self.btn_inv_masivo.setObjectName("subNavBtn")
        self.btn_inv_masivo.setCheckable(True)
        self.btn_inv_masivo.setIcon(Icons.hollow_dot("#94A3B8"))
        self.btn_inv_masivo.setVisible(False)
 
        self.btn_inv_apartar = QPushButton("Reserva de Derechos")
        self.btn_inv_apartar.setObjectName("subNavBtn")
        self.btn_inv_apartar.setCheckable(True)
        self.btn_inv_apartar.setIcon(Icons.hollow_dot("#94A3B8"))
        self.btn_inv_apartar.setVisible(False)
 
        self.btn_inv_catalogos = QPushButton("Asignar Derechos")
        self.btn_inv_catalogos.setObjectName("subNavBtn")
        self.btn_inv_catalogos.setCheckable(True)
        self.btn_inv_catalogos.setIcon(Icons.hollow_dot("#94A3B8"))
        self.btn_inv_catalogos.setVisible(False)
 
        self.btn_inv_lotes = QPushButton("Gesti\u00f3n de Asignaciones")
        self.btn_inv_lotes.setObjectName("subNavBtn")
        self.btn_inv_lotes.setCheckable(True)
        self.btn_inv_lotes.setIcon(Icons.hollow_dot("#94A3B8"))
        self.btn_inv_lotes.setVisible(False)
 
        self.inv_submenu_layout.addWidget(self.btn_inv_facturas)
        self.inv_submenu_layout.addWidget(self.btn_inv_catalogos)
        self.inv_submenu_layout.addWidget(self.btn_inv_masivo)
        self.inv_submenu_layout.addWidget(self.btn_inv_apartar)
        self.inv_submenu_layout.addWidget(self.btn_inv_lotes)
 
        self.buttons["inventario_facturas"] = self.btn_inv_facturas
        self.buttons["inventario_masivo"] = self.btn_inv_masivo
        self.buttons["inventario_apartar"] = self.btn_inv_apartar
        self.buttons["inventario_catalogos"] = self.btn_inv_catalogos
        self.buttons["inventario_lotes"] = self.btn_inv_lotes
        
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
                
            self.nav_layout.addWidget(btn)
            btn.setVisible(False)
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
                self.nav_layout.addWidget(self.submenu_container)
                self.submenu_container.hide()

            elif key == "inventario":
                # Add layout for chevron label
                arrow_layout2 = QHBoxLayout(btn)
                arrow_layout2.setContentsMargins(0, 0, 16, 0)
                arrow_layout2.addStretch()
                self.chevron_label2 = QLabel()
                self.chevron_label2.setStyleSheet("background: transparent;")
                self.chevron_label2.setPixmap(Icons.chevron_down("#475569").pixmap(12, 12))
                arrow_layout2.addWidget(self.chevron_label2)
                
                # Add submenu container immediately below "Inventario"
                self.nav_layout.addWidget(self.inv_submenu_container)
                self.inv_submenu_container.hide()
            
            # Connect clicked handler
            btn.clicked.connect(lambda checked, k=key: self._on_main_nav_clicked(k))
            
        self.btn_ordenes_capturadas.clicked.connect(lambda: self._on_sub_nav_clicked("ordenes_capturadas"))
        self.btn_capturar_nueva.clicked.connect(lambda: self._on_sub_nav_clicked("capturar_orden"))
        self.btn_solicitudes.clicked.connect(lambda: self._on_sub_nav_clicked("solicitudes"))

        self.btn_inv_facturas.clicked.connect(lambda: self._on_sub_nav_clicked("inventario_facturas"))
        self.btn_inv_masivo.clicked.connect(lambda: self._on_sub_nav_clicked("inventario_masivo"))
        self.btn_inv_apartar.clicked.connect(lambda: self._on_sub_nav_clicked("inventario_apartar"))
        self.btn_inv_catalogos.clicked.connect(lambda: self._on_sub_nav_clicked("inventario_catalogos"))
        self.btn_inv_lotes.clicked.connect(lambda: self._on_sub_nav_clicked("inventario_lotes"))

        self.nav_layout.addStretch()

    def _setup_footer(self):
        # 3. Bottom controls
        self.theme_btn = QPushButton("Cambiar Tema")
        self.theme_btn.setObjectName("themeToggleBtn")
        self.theme_btn.setIcon(Icons.calendar())
        self.theme_btn.clicked.connect(self.theme_toggled.emit)
        self.footer_layout.addWidget(self.theme_btn)
        
        # Logout button (Pinned and always visible)
        self.logout_btn = QPushButton(" Cerrar Sesión")
        self.logout_btn.setObjectName("logoutBtn")
        self.logout_btn.setIcon(Icons.power("#DC2626"))
        self.logout_btn.clicked.connect(self._on_logout_clicked)
        self.footer_layout.addWidget(self.logout_btn)
        
        self.footer_layout.addSpacing(6)
        
        # 4. User profile status block at the bottom
        self.profile_widget = QWidget(self)
        self.profile_widget.setStyleSheet("background: transparent;")
        self.profile_layout = QHBoxLayout(self.profile_widget)
        self.profile_layout.setContentsMargins(0, 0, 0, 0)
        self.profile_layout.setSpacing(10)
        
        _icon_color = Colors.TEXT_LIGHT_SECONDARY if not ThemeManager.is_dark_active() else Colors.TEXT_DARK_SECONDARY
        self.lbl_profile_icon = QLabel()
        self.lbl_profile_icon.setPixmap(Icons.user(_icon_color).pixmap(20, 20))
        self.lbl_profile_icon.setStyleSheet("background: transparent;")
        
        self.profile_text_layout = QVBoxLayout()
        self.profile_text_layout.setContentsMargins(0, 0, 0, 0)
        self.profile_text_layout.setSpacing(2)
        
        self.lbl_profile_user = CustomLabel("Usuario: Administrador", variant="body")
        self.lbl_profile_user.setObjectName("sidebarProfileUser")
        
        self.lbl_profile_status = CustomLabel("Sesión activa", variant="body")
        self.lbl_profile_status.setObjectName("sidebarProfileStatus")
        _status_color = Colors.SLATE_500
        self.lbl_profile_status.setStyleSheet(f"color: {_status_color}; font-size: 11px; background: transparent;")
        
        self.profile_text_layout.addWidget(self.lbl_profile_user)
        self.profile_text_layout.addWidget(self.lbl_profile_status)
        
        self.profile_layout.addWidget(self.lbl_profile_icon)
        self.profile_layout.addLayout(self.profile_text_layout)
        self.profile_layout.addStretch()
        
        self.footer_layout.addWidget(self.profile_widget)

    def _on_main_nav_clicked(self, clicked_key: str):
        if self.is_collapsed:
            self.toggle_collapse()
        if clicked_key == "ordenes":
            self.submenu_visible = not self.submenu_visible
            self.submenu_container.setVisible(self.submenu_visible)
            # Accordion: close inventario submenu if open
            if self.submenu_visible and self.inv_submenu_visible:
                self.inv_submenu_visible = False
                self.inv_submenu_container.setVisible(False)
                self.chevron_label2.setPixmap(Icons.chevron_down("#475569").pixmap(12, 12))
            color = "#2563EB" if self.buttons["ordenes"].isChecked() else "#475569"
            if self.submenu_visible:
                self.chevron_label.setPixmap(Icons.chevron_up(color).pixmap(12, 12))
            else:
                self.chevron_label.setPixmap(Icons.chevron_down(color).pixmap(12, 12))
            self._on_sub_nav_clicked("capturar_orden")
            return

        if clicked_key == "inventario":
            self.inv_submenu_visible = not self.inv_submenu_visible
            self.inv_submenu_container.setVisible(self.inv_submenu_visible)
            # Accordion: close ordenes submenu if open
            if self.inv_submenu_visible and self.submenu_visible:
                self.submenu_visible = False
                self.submenu_container.setVisible(False)
                self.chevron_label.setPixmap(Icons.chevron_down("#475569").pixmap(12, 12))
            color = "#2563EB" if self.buttons["inventario"].isChecked() else "#475569"
            if self.inv_submenu_visible:
                self.chevron_label2.setPixmap(Icons.chevron_up(color).pixmap(12, 12))
            else:
                self.chevron_label2.setPixmap(Icons.chevron_down(color).pixmap(12, 12))
            self._on_sub_nav_clicked("inventario_facturas")
            return
        # Regular main navigation click - Keep the submenus fixed
        for key, btn in self.buttons.items():
            if key in ["ordenes_capturadas", "capturar_orden", "solicitudes", "inventario_facturas", "inventario_masivo", "inventario_apartar", "inventario_catalogos", "inventario_lotes"]:
                btn.setChecked(False)
                btn.setIcon(Icons.hollow_dot("#94A3B8"))
            else:
                btn.setChecked(key == clicked_key)

                
        self.chevron_label.setPixmap(Icons.chevron_down("#475569").pixmap(12, 12))
        self.chevron_label2.setPixmap(Icons.chevron_down("#475569").pixmap(12, 12))
                
        self.nav_selected.emit(clicked_key)
        
    def _on_sub_nav_clicked(self, clicked_key: str):
        # 1. Handle Órdenes Submenu
        if clicked_key in ["ordenes_capturadas", "capturar_orden", "solicitudes"]:
            self.buttons["ordenes"].setChecked(True)
            self.chevron_label.setPixmap(Icons.chevron_up("#2563EB").pixmap(12, 12))
            self.submenu_visible = True
            self.submenu_container.setVisible(True)
            
            # Uncheck all other parent items except ordenes
            for key, btn in self.buttons.items():
                if key not in ["ordenes", "ordenes_capturadas", "capturar_orden", "solicitudes"]:
                    btn.setChecked(False)
                    if key in ["inventario_facturas", "inventario_masivo", "inventario_apartar", "inventario_catalogos", "inventario_lotes"]:
                        btn.setIcon(Icons.hollow_dot("#94A3B8"))
            
            # Handle Órdenes submenus check states
            for key in ["ordenes_capturadas", "capturar_orden", "solicitudes"]:
                btn = self.buttons[key]
                if key == clicked_key:
                    btn.setChecked(True)
                    btn.setIcon(Icons.dot("#2563EB"))
                else:
                    btn.setChecked(False)
                    btn.setIcon(Icons.hollow_dot("#94A3B8"))
 
        # 2. Handle Inventario Submenu
        elif clicked_key in ["inventario_facturas", "inventario_masivo", "inventario_apartar", "inventario_catalogos", "inventario_lotes"]:
            self.buttons["inventario"].setChecked(True)
            self.chevron_label2.setPixmap(Icons.chevron_up("#2563EB").pixmap(12, 12))
            self.inv_submenu_visible = True
            self.inv_submenu_container.setVisible(True)
            
            # Uncheck all other parent items except inventario
            for key, btn in self.buttons.items():
                if key not in ["inventario", "inventario_facturas", "inventario_masivo", "inventario_apartar", "inventario_catalogos", "inventario_lotes"]:
                    btn.setChecked(False)
                    if key in ["ordenes_capturadas", "capturar_orden", "solicitudes"]:
                        btn.setIcon(Icons.hollow_dot("#94A3B8"))
            
            # Handle Inventario submenus check states
            for key in ["inventario_facturas", "inventario_masivo", "inventario_apartar", "inventario_catalogos", "inventario_lotes"]:
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
        if key in ["ordenes_capturadas", "capturar_orden", "solicitudes", "inventario_facturas", "inventario_masivo", "inventario_apartar", "inventario_catalogos", "inventario_lotes"]:
            self._on_sub_nav_clicked(key)
        elif key in self.buttons:
            self._on_main_nav_clicked(key)

            
    def hide_item(self, key: str):
        """Hides a specific navigation item by its key."""
        if key in self.buttons:
            self.buttons[key].setVisible(False)

    def show_item(self, key: str):
        """Shows a specific navigation item by its key."""
        if key in self.buttons:
            if self.is_collapsed and key in ["ordenes_capturadas", "capturar_orden", "solicitudes", "inventario_facturas", "inventario_masivo", "inventario_apartar", "inventario_catalogos", "inventario_lotes"]:
                self.buttons[key].setVisible(False)
            else:
                self.buttons[key].setVisible(True)
            
    def set_username(self, username: str):
        """Updates the username in the profile status widget."""
        self.lbl_profile_user.setText(f"Usuario: {username}")
        
    def _on_logout_clicked(self):
        """Displays a confirmation dialog before emitting logout signal."""
        reply = QMessageBox.question(
            self, "Cerrar Sesión",
            "¿Estás seguro de que deseas cerrar sesión?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.logout_requested.emit()

    def toggle_collapse(self):
        """Toggles the sidebar between expanded (250px) and collapsed (70px) states."""
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.setFixedWidth(70)
            self.brand_layout.setContentsMargins(8, 20, 8, 12)
            self.nav_layout.setContentsMargins(8, 0, 8, 0)
            self.footer_layout.setContentsMargins(8, 10, 8, 16)
            self.logo_label.hide()
            self.brand_title.hide()
            self.brand_subtitle.hide()
            
            # Hide labels of parent buttons and center icons
            for key, btn in self.buttons.items():
                if key not in ["ordenes_capturadas", "capturar_orden", "solicitudes", "inventario_facturas", "inventario_masivo", "inventario_apartar", "inventario_catalogos", "inventario_lotes"]:
                    btn.setText("")
                    btn.setStyleSheet("padding: 12px 0px; text-align: center;")
                else:
                    btn.setVisible(False)
                    
            # Hide submenus
            self.submenu_container.hide()
            self.inv_submenu_container.hide()
            self.chevron_label.hide()
            self.chevron_label2.hide()
            
            # Hide profile text and bottom buttons texts
            self.theme_btn.setText("")
            self.theme_btn.setStyleSheet("padding: 12px 0px; text-align: center;")
            self.logout_btn.setText("")
            self.logout_btn.setStyleSheet("padding: 12px 0px; text-align: center;")
            self.profile_widget.hide()
        else:
            self.setFixedWidth(250)
            self.brand_layout.setContentsMargins(16, 20, 16, 12)
            self.nav_layout.setContentsMargins(16, 0, 16, 0)
            self.footer_layout.setContentsMargins(16, 12, 16, 16)
            self.logo_label.show()
            self.brand_title.show()
            self.brand_subtitle.show()
            
            # Restore parent buttons texts and styles
            for index, (text, key, icon_name) in enumerate(self.menu_items):
                if key in self.buttons:
                    self.buttons[key].setText(text)
                    self.buttons[key].setStyleSheet("")
            
            self.chevron_label.show()
            self.chevron_label2.show()
            
            # Restore submenu items if they were active
            if self.submenu_visible:
                self.submenu_container.show()
                self.btn_ordenes_capturadas.setVisible(True)
                self.btn_capturar_nueva.setVisible(True)
                self.btn_solicitudes.setVisible(True)
            if self.inv_submenu_visible:
                self.inv_submenu_container.show()
                self.btn_inv_facturas.setVisible(True)
                self.btn_inv_catalogos.setVisible(True)
                self.btn_inv_masivo.setVisible(True)
                self.btn_inv_apartar.setVisible(True)
                self.btn_inv_lotes.setVisible(True)
                
            self.theme_btn.setText("Cambiar Tema")
            self.theme_btn.setStyleSheet("")
            self.logout_btn.setText(" Cerrar Sesión")
            self.logout_btn.setStyleSheet("")
            self.profile_widget.show()
