"""Labeled DateEdit Molecule (Atomic Design)."""

import os
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QDateEdit
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QCursor


class LabeledDateEdit(QGroupBox):
    """An outlined date editor with a floating label (fieldset style) and visible calendar indicator."""

    def __init__(self, label_text: str = "Fecha", parent=None):
        super().__init__(label_text, parent)

        calendar_icon_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "icons", "calendar.svg")
        ).replace("\\", "/")

        self.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                margin-top: 8px;
                font-weight: bold;
                color: #2563EB;
                font-size: 11px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 8px;
                padding: 0 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.date_edit = QDateEdit()
        self.date_edit.setFixedHeight(35)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCursor(QCursor(Qt.PointingHandCursor))
        self.date_edit.setStyleSheet(f"""
            QDateEdit {{
                border: none;
                background-color: transparent;
                min-width: 120px;
                height: 35px;
                min-height: 35px;
                max-height: 35px;
                padding: 2px 6px 2px 10px;
                font-size: 13px;
                color: #1e293b;
            }}
            QDateEdit:focus {{
                color: #0f172a;
            }}
            QDateEdit::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border: none;
            }}
            QDateEdit::down-arrow {{
                image: url("{calendar_icon_path}");
                width: 16px;
                height: 16px;
                margin-right: 8px;
            }}
            QCalendarWidget QWidget#qt_datetimedit_calendar {{
                background-color: #ffffff;
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                background-color: #ffffff;
                color: #1e293b;
                selection-background-color: #2563eb;
                selection-color: #ffffff;
            }}
        """)
        layout.addWidget(self.date_edit)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.date_edit.setFocus()

    def date(self) -> QDate:
        return self.date_edit.date()

    def setDate(self, d: QDate):
        self.date_edit.setDate(d)
