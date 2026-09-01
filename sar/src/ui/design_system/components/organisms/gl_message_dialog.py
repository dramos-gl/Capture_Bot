"""Standard Message & Alert Dialog Organism for SAR.

Provides a unified, responsive modal dialog that prevents vertical overflows
using styled scrollable content areas, collapsible technical details,
semantic status badges, and drop-in compatibility with QMessageBox.
"""

from typing import Optional, Union, List, Callable
from enum import Enum

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QScrollArea, QPushButton, QPlainTextEdit, QApplication
)
from PySide6.QtCore import Qt, QSize, QPoint
from PySide6.QtGui import QIcon, QFont, QClipboard, QKeySequence, QShortcut

from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.utils.icons import Icons


class DialogType(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    QUESTION = "question"


class GLMessageDialog(QDialog):
    """
    Standardized, overflow-safe modal dialog for alerts, information,
    warnings, errors, and user confirmations in SAR.
    """

    def __init__(
        self,
        title: str = "",
        message: str = "",
        dialog_type: DialogType = DialogType.INFO,
        details: Optional[str] = None,
        confirm_text: str = "Aceptar",
        cancel_text: Optional[str] = None,
        is_danger: bool = False,
        parent=None
    ):
        super().__init__(parent)
        self.dialog_type = dialog_type
        self.details_text = details
        self._drag_pos = None

        # Modal configuration
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Sizing bounds to prevent overflow
        self.setMinimumWidth(440)
        self.setMaximumWidth(580)
        self.setMinimumHeight(190)
        self.setMaximumHeight(500)

        self._init_ui(title, message, confirm_text, cancel_text, is_danger)

    def _get_theme_config(self):
        """Returns colors, icons, and titles according to dialog type."""
        if self.dialog_type == DialogType.SUCCESS:
            return {
                "color": Colors.SUCCESS,
                "bg_color": Colors.SUCCESS_BG,
                "icon_name": "exito",
                "badge_text": "ÉXITO"
            }
        elif self.dialog_type == DialogType.WARNING:
            return {
                "color": Colors.WARNING,
                "bg_color": Colors.WARNING_BG,
                "icon_name": "alerta",
                "badge_text": "ADVERTENCIA"
            }
        elif self.dialog_type == DialogType.ERROR:
            return {
                "color": Colors.ERROR,
                "bg_color": Colors.ERROR_BG,
                "icon_name": "error",
                "badge_text": "ERROR"
            }
        elif self.dialog_type == DialogType.QUESTION:
            return {
                "color": Colors.ACCENT,
                "bg_color": Colors.ACCENT_BG,
                "icon_name": "ayuda",
                "badge_text": "CONFIRMACIÓN"
            }
        else:  # INFO
            return {
                "color": Colors.ACCENT,
                "bg_color": Colors.ACCENT_BG,
                "icon_name": "informacion",
                "badge_text": "INFORMACIÓN"
            }

    def _init_ui(self, title: str, message: str, confirm_text: str, cancel_text: Optional[str], is_danger: bool):
        cfg = self._get_theme_config()

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)

        # Outer card container
        self.card = QWidget(self)
        self.card.setObjectName("messageDialogCard")
        self.card.setStyleSheet("""
            QWidget#messageDialogCard {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 12px;
            }
        """)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # 1. Header (Draggable)
        self.header = QWidget(self.card)
        self.header.setObjectName("dialogHeader")
        self.header.setFixedHeight(48)
        self.header.setStyleSheet(f"""
            QWidget#dialogHeader {{
                background-color: {Colors.PRIMARY};
                border-top-left-radius: 11px;
                border-top-right-radius: 11px;
                border-bottom: 1px solid #E2E8F0;
            }}
        """)

        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(16, 0, 12, 0)
        header_layout.setSpacing(10)

        # Header Title
        self.lbl_header_title = QLabel(title or cfg["badge_text"], self.header)
        self.lbl_header_title.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: bold; background: transparent;")
        header_layout.addWidget(self.lbl_header_title)
        header_layout.addStretch()

        # Close X Button
        btn_close = QPushButton(self.header)
        btn_close.setIcon(Icons.cerrar("#94A3B8"))
        btn_close.setIconSize(QSize(16, 16))
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        btn_close.clicked.connect(self.reject)
        header_layout.addWidget(btn_close)

        card_layout.addWidget(self.header)

        # 2. Body Area with Icon Badge + Scrollable Message
        body_widget = QWidget(self.card)
        body_widget.setStyleSheet("background: transparent;")
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(20, 16, 20, 12)
        body_layout.setSpacing(16)
        body_layout.setAlignment(Qt.AlignTop)

        # Icon Badge
        self.badge_container = QWidget(body_widget)
        self.badge_container.setFixedSize(44, 44)
        self.badge_container.setStyleSheet(f"""
            QWidget {{
                background-color: {cfg['bg_color']};
                border: 1px solid {cfg['color']};
                border-radius: 22px;
            }}
        """)
        badge_layout = QVBoxLayout(self.badge_container)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.setAlignment(Qt.AlignCenter)

        self.badge_icon = QLabel(self.badge_container)
        self.badge_icon.setPixmap(Icons.get_icon(cfg["icon_name"], color=cfg["color"]).pixmap(24, 24))
        self.badge_icon.setAlignment(Qt.AlignCenter)
        self.badge_icon.setStyleSheet("background: transparent; border: none;")
        badge_layout.addWidget(self.badge_icon)

        body_layout.addWidget(self.badge_container, alignment=Qt.AlignTop)

        # Scrollable Message Area
        scroll_area = QScrollArea(body_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: #F1F5F9;
                width: 6px;
                border-radius: 3px;
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
        """)

        msg_content_widget = QWidget()
        msg_content_widget.setStyleSheet("background: transparent;")
        msg_content_layout = QVBoxLayout(msg_content_widget)
        msg_content_layout.setContentsMargins(0, 0, 4, 0)
        msg_content_layout.setSpacing(8)

        self.lbl_message = QLabel(message, msg_content_widget)
        self.lbl_message.setWordWrap(True)
        self.lbl_message.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_message.setStyleSheet("color: #1E293B; font-size: 13px; line-height: 1.4; background: transparent;")
        msg_content_layout.addWidget(self.lbl_message)

        # Collapsible Details (if provided)
        if self.details_text:
            self.btn_toggle_details = QPushButton("▶ Ver detalles técnicos", msg_content_widget)
            self.btn_toggle_details.setCursor(Qt.PointingHandCursor)
            self.btn_toggle_details.setStyleSheet("""
                QPushButton {
                    color: #2563EB;
                    font-size: 11px;
                    font-weight: 600;
                    text-align: left;
                    background: transparent;
                    border: none;
                    padding: 2px 0px;
                }
                QPushButton:hover {
                    color: #1D4ED8;
                    text-decoration: underline;
                }
            """)

            self.txt_details = QPlainTextEdit(msg_content_widget)
            self.txt_details.setPlainText(self.details_text)
            self.txt_details.setReadOnly(True)
            self.txt_details.setFixedHeight(110)
            self.txt_details.setVisible(False)
            self.txt_details.setStyleSheet("""
                QPlainTextEdit {
                    background-color: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 6px;
                    color: #334155;
                    font-family: Consolas, 'Courier New', monospace;
                    font-size: 11px;
                    padding: 6px;
                }
            """)

            def toggle_details():
                is_vis = not self.txt_details.isVisible()
                self.txt_details.setVisible(is_vis)
                self.btn_toggle_details.setText("▼ Ocultar detalles técnicos" if is_vis else "▶ Ver detalles técnicos")

            self.btn_toggle_details.clicked.connect(toggle_details)
            msg_content_layout.addWidget(self.btn_toggle_details)
            msg_content_layout.addWidget(self.txt_details)

        scroll_area.setWidget(msg_content_widget)
        body_layout.addWidget(scroll_area, stretch=1)

        card_layout.addWidget(body_widget, stretch=1)

        # 3. Footer with Action Buttons (Always Visible & Pinned)
        self.footer = QWidget(self.card)
        self.footer.setObjectName("dialogFooter")
        self.footer.setFixedHeight(56)
        self.footer.setStyleSheet("""
            QWidget#dialogFooter {
                background-color: #F8FAFC;
                border-bottom-left-radius: 11px;
                border-bottom-right-radius: 11px;
                border-top: 1px solid #E2E8F0;
            }
        """)

        self.footer_layout = QHBoxLayout(self.footer)
        self.footer_layout.setContentsMargins(16, 0, 16, 0)
        self.footer_layout.setSpacing(10)

        # Copy button if details exist
        if self.details_text:
            btn_copy = QPushButton("Copiar", self.footer)
            btn_copy.setIcon(Icons.copiar("#64748B"))
            btn_copy.setCursor(Qt.PointingHandCursor)
            btn_copy.setFixedHeight(34)
            btn_copy.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    color: #475569;
                    font-size: 12px;
                    padding: 0 12px;
                }
                QPushButton:hover {
                    background-color: #F1F5F9;
                    color: #1E293B;
                }
            """)

            def copy_to_clipboard():
                QApplication.clipboard().setText(f"{message}\n\nDetalles:\n{self.details_text}")
                btn_copy.setText("¡Copiado!")

            btn_copy.clicked.connect(copy_to_clipboard)
            self.footer_layout.addWidget(btn_copy)

        self.footer_layout.addStretch()

        # Cancel button (if provided)
        if cancel_text:
            self.btn_cancel = QPushButton(cancel_text, self.footer)
            self.btn_cancel.setCursor(Qt.PointingHandCursor)
            self.btn_cancel.setFixedHeight(34)
            self.btn_cancel.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    color: #475569;
                    font-size: 12px;
                    font-weight: 500;
                    padding: 0 16px;
                }
                QPushButton:hover {
                    background-color: #F1F5F9;
                    color: #1E293B;
                    border-color: #94A3B8;
                }
            """)
            self.btn_cancel.clicked.connect(self.reject)
            self.footer_layout.addWidget(self.btn_cancel)

        # Confirm / Accept button
        self.btn_confirm = QPushButton(confirm_text, self.footer)
        self.btn_confirm.setCursor(Qt.PointingHandCursor)
        self.btn_confirm.setFixedHeight(34)
        self.btn_confirm.setDefault(True)

        if is_danger or self.dialog_type == DialogType.ERROR:
            btn_bg = "#EF4444"
            btn_hover = "#DC2626"
        elif self.dialog_type == DialogType.SUCCESS:
            btn_bg = "#10B981"
            btn_hover = "#059669"
        else:
            btn_bg = "#2563EB"
            btn_hover = "#1D4ED8"

        self.btn_confirm.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                border: none;
                border-radius: 6px;
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 600;
                padding: 0 18px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
        """)
        self.btn_confirm.clicked.connect(self.accept)
        self.footer_layout.addWidget(self.btn_confirm)

        card_layout.addWidget(self.footer)
        root_layout.addWidget(self.card)

    # Dragging logic
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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.accept()
        else:
            super().keyPressEvent(event)

    # Static High-Level Helpers
    @classmethod
    def info(cls, parent=None, title="Información", message="", details=None, confirm_text="Aceptar") -> bool:
        dlg = cls(title, message, DialogType.INFO, details=details, confirm_text=confirm_text, parent=parent)
        return dlg.exec() == QDialog.Accepted

    @classmethod
    def success(cls, parent=None, title="Éxito", message="", details=None, confirm_text="Aceptar") -> bool:
        dlg = cls(title, message, DialogType.SUCCESS, details=details, confirm_text=confirm_text, parent=parent)
        return dlg.exec() == QDialog.Accepted

    @classmethod
    def warning(cls, parent=None, title="Advertencia", message="", details=None, confirm_text="Aceptar") -> bool:
        dlg = cls(title, message, DialogType.WARNING, details=details, confirm_text=confirm_text, parent=parent)
        return dlg.exec() == QDialog.Accepted

    @classmethod
    def error(cls, parent=None, title="Error", message="", details=None, confirm_text="Aceptar") -> bool:
        dlg = cls(title, message, DialogType.ERROR, details=details, confirm_text=confirm_text, is_danger=True, parent=parent)
        return dlg.exec() == QDialog.Accepted

    @classmethod
    def confirm(
        cls, parent=None, title="Confirmar Acción", message="",
        confirm_text="Aceptar", cancel_text="Cancelar", is_danger=False, details=None
    ) -> bool:
        dlg = cls(
            title, message,
            DialogType.QUESTION,
            details=details,
            confirm_text=confirm_text,
            cancel_text=cancel_text,
            is_danger=is_danger,
            parent=parent
        )
        return dlg.exec() == QDialog.Accepted


class GLMessageBox(GLMessageDialog):
    """
    Drop-in replacement for QMessageBox supporting both static methods
    (information, warning, critical, question) and object instantiation
    (addButton, clickedButton, exec, etc.).
    """
    # Standard Qt Roles
    AcceptRole = 0
    RejectRole = 1
    YesRole = 2
    NoRole = 3

    # Standard Qt Buttons
    Ok = 0x00000400
    Cancel = 0x00400000
    Yes = 0x00004000
    No = 0x00010000
    NoButton = 0x00000000

    # Standard Qt Icons
    NoIcon = 0
    Information = 1
    Warning = 2
    Critical = 3
    Question = 4

    def __init__(self, parent=None, title="", text="", icon=1):
        dialog_type = DialogType.INFO
        if icon == 2:
            dialog_type = DialogType.WARNING
        elif icon == 3:
            dialog_type = DialogType.ERROR
        elif icon == 4:
            dialog_type = DialogType.QUESTION

        super().__init__(
            title=title,
            message=text,
            dialog_type=dialog_type,
            confirm_text="Aceptar",
            parent=parent
        )
        self._custom_buttons = []
        self._clicked_button = None

    def setWindowTitle(self, title: str):
        if hasattr(self, 'lbl_header_title'):
            self.lbl_header_title.setText(title)

    def setText(self, text: str):
        if hasattr(self, 'lbl_message'):
            self.lbl_message.setText(text)

    def setIcon(self, icon):
        if icon in (self.Warning, DialogType.WARNING):
            self.dialog_type = DialogType.WARNING
        elif icon in (self.Critical, DialogType.ERROR):
            self.dialog_type = DialogType.ERROR
        elif icon in (self.Question, DialogType.QUESTION):
            self.dialog_type = DialogType.QUESTION
        else:
            self.dialog_type = DialogType.INFO

        cfg = self._get_theme_config()
        self.badge_container.setStyleSheet(f"""
            QWidget {{
                background-color: {cfg['bg_color']};
                border: 1px solid {cfg['color']};
                border-radius: 22px;
            }}
        """)
        self.badge_icon.setPixmap(Icons.get_icon(cfg["icon_name"], color=cfg["color"]).pixmap(24, 24))

    def addButton(self, text: str, role=0):
        # Hide default buttons when first custom button is added
        if not self._custom_buttons:
            self.btn_confirm.setVisible(False)
            if hasattr(self, 'btn_cancel'):
                self.btn_cancel.setVisible(False)

        btn = QPushButton(text, self)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(34)
        if role in (self.YesRole, self.AcceptRole):
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.ACCENT};
                    border: none;
                    border-radius: 6px;
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 0 16px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.ACCENT_HOVER};
                }}
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {{
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    color: #475569;
                    font-size: 12px;
                    font-weight: 500;
                    padding: 0 14px;
                }}
                QPushButton:hover {{
                    background-color: #F1F5F9;
                    color: #1E293B;
                    border-color: #94A3B8;
                }}
            """)

        def on_click():
            self._clicked_button = btn
            if role in (self.RejectRole, self.NoRole):
                self.reject()
            else:
                self.accept()

        btn.clicked.connect(on_click)
        self._custom_buttons.append(btn)
        self.footer_layout.addWidget(btn)
        return btn

    def setDefaultButton(self, btn):
        if btn:
            btn.setDefault(True)

    def clickedButton(self):
        return self._clicked_button

    # Static helpers
    @classmethod
    def information(cls, parent, title, text, buttons=Ok, defaultButton=NoButton):
        GLMessageDialog.info(parent=parent, title=title, message=str(text))
        return cls.Ok

    @classmethod
    def success(cls, parent, title, text, buttons=Ok, defaultButton=NoButton):
        GLMessageDialog.success(parent=parent, title=title, message=str(text))
        return cls.Ok

    @classmethod
    def warning(cls, parent, title, text, buttons=Ok, defaultButton=NoButton):
        if buttons & cls.Yes or buttons & cls.Cancel:
            accepted = GLMessageDialog.confirm(
                parent=parent, title=title, message=str(text),
                confirm_text="Sí" if buttons & cls.Yes else "Aceptar",
                cancel_text="No" if buttons & cls.No else "Cancelar"
            )
            return cls.Yes if accepted else cls.No
        GLMessageDialog.warning(parent=parent, title=title, message=str(text))
        return cls.Ok

    @classmethod
    def critical(cls, parent, title, text, buttons=Ok, defaultButton=NoButton):
        GLMessageDialog.error(parent=parent, title=title, message=str(text))
        return cls.Ok

    @classmethod
    def question(cls, parent, title, text, buttons=Yes | No, defaultButton=NoButton):
        confirm_label = "Sí" if (buttons & cls.Yes) else "Aceptar"
        cancel_label = "No" if (buttons & cls.No) else "Cancelar"
        accepted = GLMessageDialog.confirm(
            parent=parent, title=title, message=str(text),
            confirm_text=confirm_label, cancel_text=cancel_label
        )
        if buttons & cls.Yes:
            return cls.Yes if accepted else cls.No
        return cls.Ok if accepted else cls.Cancel
