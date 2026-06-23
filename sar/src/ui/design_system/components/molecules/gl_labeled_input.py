"""Labeled Input Molecule with Floating Label and Icons."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLineEdit
from PySide6.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, QEvent, Signal
import re
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.atoms.gl_input import CustomInput
from sar.src.ui.design_system.utils.icons import Icons

class LabeledInput(QWidget):
    """A molecule grouping an Input with a Floating Label and icons.
    Supports real-time regex validation."""
    
    validity_changed = Signal(bool)
    
    def __init__(self, label_text: str, placeholder: str = "", is_password: bool = False, icon_name: str = None, parent=None):
        super().__init__(parent)
        
        self._validator_pattern = None
        self._validator_error_msg = ""
        self._is_valid = True
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 10, 0, 0) # Top margin for floating label
        self.layout.setSpacing(4)
        
        # Main Frame container
        self.frame = QFrame(self)
        self.frame.setObjectName("floatingInputFrame")
        self.frame.setFixedHeight(44)
        
        self.frame_layout = QVBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(8, 0, 8, 0)
        
        self.input = CustomInput("", is_password, self.frame)
        self.input.setObjectName("floatingInput")
        
        # Icons
        if icon_name == "user":
            self.input.addAction(Icons.user(), QLineEdit.LeadingPosition)
        elif icon_name == "lock":
            self.input.addAction(Icons.lock(), QLineEdit.LeadingPosition)
            
        if is_password:
            self.eye_action = self.input.addAction(Icons.eye(), QLineEdit.TrailingPosition)
            self.eye_action.triggered.connect(self._toggle_password)
            self._password_visible = False
            
        self.frame_layout.addWidget(self.input)
        
        # Floating Label
        self.label = CustomLabel(label_text, variant="body", parent=self)
        self.label.setStyleSheet("background-color: transparent; color: #64748B; padding: 0 4px;")
        
        # Error Label
        self.error_label = CustomLabel("", variant="muted")
        self.error_label.setVisible(False)
        
        self.layout.addWidget(self.frame)
        self.layout.addWidget(self.error_label)
        
        # Animation properties
        self.animation = QPropertyAnimation(self.label, b"geometry")
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        
        self.input.installEventFilter(self)
        self.input.textChanged.connect(self._on_text_changed)
        
        self._is_active = False

    def set_validator(self, pattern: str, error_msg: str):
        """Sets a regex validation pattern and error message for real-time validation."""
        self._validator_pattern = pattern
        self._validator_error_msg = error_msg
        
    def set_max_length(self, length: int):
        self.input.setMaxLength(length)
        
    def _on_text_changed(self, text):
        self._update_label_state(animate=True)
        self.validate()

    def validate(self) -> bool:
        """Validates current text against regex if set, updates UI, and emits validity."""
        text = self.text().strip()
        is_valid = True
        
        if self._validator_pattern and text:
            if not re.match(self._validator_pattern, text):
                self.show_error(self._validator_error_msg)
                is_valid = False
            else:
                self.clear_error()
                
        if self._is_valid != is_valid:
            self._is_valid = is_valid
            self.validity_changed.emit(is_valid)
            
        return is_valid

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_label_state(animate=False)
        
    def eventFilter(self, obj, event):
        if obj == self.input:
            if event.type() == QEvent.FocusIn:
                self._set_active(True)
            elif event.type() == QEvent.FocusOut:
                if not self.input.text():
                    self._set_active(False)
        return super().eventFilter(obj, event)

    def _set_active(self, active: bool):
        self._is_active = active
        self._update_label_state(animate=True)

    def _update_label_state(self, *args, animate=True):
        if not hasattr(self, 'frame'):
            return
            
        has_text = bool(self.input.text())
        is_active = self._is_active or has_text
        
        frame_rect = self.frame.geometry()
        
        # Apply styles BEFORE calculating geometry so adjustSize() uses the correct font
        if is_active:
            self.label.setStyleSheet("background-color: #E8EEF5; color: #2C3E50; font-size: 11px; padding: 0 4px;")
        else:
            self.label.setStyleSheet("background-color: transparent; color: #64748B; font-size: 13px; padding: 0 4px;")
            
        # Adjust label width to exactly fit content
        self.label.adjustSize()
        lbl_w = self.label.width()
        lbl_h = self.label.height()
        
        start_y = frame_rect.y() + (frame_rect.height() - lbl_h) // 2
        start_x = frame_rect.x() + 32 # Offset for leading icon
        
        end_y = frame_rect.y() - (lbl_h // 2)
        end_x = frame_rect.x() + 12
        
        target_rect = QRect(end_x, end_y, lbl_w, lbl_h) if is_active else QRect(start_x, start_y, lbl_w, lbl_h)
        
        if animate:
            self.animation.setEndValue(target_rect)
            self.animation.start()
        else:
            self.label.setGeometry(target_rect)
            
        # Manage Frame Focus Style unless there's an error
        if not self.error_label.isVisible():
            if self.input.hasFocus():
                self.frame.setStyleSheet("QFrame#floatingInputFrame { border: 1px solid #2C3E50; }")
            else:
                self.frame.setStyleSheet("")

    def _toggle_password(self):
        self._password_visible = not self._password_visible
        if self._password_visible:
            self.input.setEchoMode(QLineEdit.Normal)
            self.eye_action.setIcon(Icons.eye_off())
        else:
            self.input.setEchoMode(QLineEdit.Password)
            self.eye_action.setIcon(Icons.eye())
            
    def text(self) -> str:
        return self.input.text()
        
    def set_text(self, val: str):
        self.input.setText(val)
        self._update_label_state(animate=False)
        
    def set_focus(self):
        self.input.setFocus()
        
    def show_error(self, message: str):
        if message:
            self.error_label.setText(message)
            self.error_label.set_error_style(True)
            self.error_label.setVisible(True)
            self.frame.setStyleSheet("QFrame#floatingInputFrame { border: 1px solid #DC2626; }")
        else:
            self.clear_error()
            
    def clear_error(self):
        self.error_label.setText("")
        self.error_label.setVisible(False)
        self.frame.setStyleSheet("")
