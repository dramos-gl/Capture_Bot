"""Labeled DateEdit Molecule (Atomic Design)."""

from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QDateEdit
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QCursor


class LabeledDateEdit(QGroupBox):
    """An outlined date editor with a floating label (fieldset style) and visible calendar indicator."""

    def __init__(self, label_text: str = "Fecha", parent=None):
        super().__init__(label_text, parent)
        self.setObjectName("labeledGroup")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.date_edit = QDateEdit(self)
        self.date_edit.setFixedHeight(35)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCursor(QCursor(Qt.PointingHandCursor))

        layout.addWidget(self.date_edit)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.date_edit.setFocus()

    def date(self) -> QDate:
        return self.date_edit.date()

    def setDate(self, d: QDate):
        self.date_edit.setDate(d)
