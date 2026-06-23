"""Date Field Molecule with Calendar Popup."""

from PySide6.QtWidgets import QWidget, QLineEdit, QCalendarWidget, QDialog, QVBoxLayout
from PySide6.QtCore import Qt, QDate
from sar.src.ui.design_system.components.molecules.gl_labeled_input import LabeledInput
from sar.src.ui.design_system.utils.icons import Icons

class DateField(LabeledInput):
    """Component for selecting dates, wrapped in a LabeledInput."""
    
    def __init__(self, label_text: str = "Fecha", allow_past: bool = True, parent=None):
        super().__init__(label_text=label_text, parent=parent)
        
        self.input.setReadOnly(True)
        self.input.setPlaceholderText("DD/MM/AAAA")
        self.allow_past = allow_past
        
        # Add Calendar Icon
        self.cal_action = self.input.addAction(Icons.calendar(), QLineEdit.TrailingPosition)
        self.cal_action.triggered.connect(self._open_picker)
        
        # We can also open it when clicking the input
        self.input.mousePressEvent = self._on_input_click
        
        self._iso_value = ""

    def _on_input_click(self, event):
        super(type(self.input), self.input).mousePressEvent(event)
        self._open_picker()

    def _open_picker(self):
        # Create a simple popup dialog with a calendar
        dialog = QDialog(self)
        dialog.setWindowTitle("Seleccionar Fecha")
        dialog.setWindowFlags(Qt.Popup)
        dialog.setFixedSize(300, 250)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        
        calendar = QCalendarWidget(dialog)
        calendar.setGridVisible(True)
        
        if not self.allow_past:
            calendar.setMinimumDate(QDate.currentDate())
            
        if self._iso_value:
            calendar.setSelectedDate(QDate.fromString(self._iso_value, Qt.ISODate))
            
        calendar.clicked.connect(lambda date: self._date_selected(date, dialog))
        
        layout.addWidget(calendar)
        
        # Position dialog below the input
        pos = self.input.mapToGlobal(self.input.rect().bottomLeft())
        dialog.move(pos)
        
        dialog.exec()

    def _date_selected(self, date: QDate, dialog: QDialog):
        self._iso_value = date.toString(Qt.ISODate) # YYYY-MM-DD
        self.set_text(date.toString("dd/MM/yyyy")) # DD/MM/AAAA
        dialog.accept()

    def value(self) -> str:
        """Returns ISO format 'YYYY-MM-DD'."""
        return self._iso_value

    def set_value(self, iso_date_str: str):
        """Sets the date from ISO format 'YYYY-MM-DD'."""
        self._iso_value = iso_date_str
        if iso_date_str:
            qdate = QDate.fromString(iso_date_str, Qt.ISODate)
            self.set_text(qdate.toString("dd/MM/yyyy"))
        else:
            self.set_text("")
