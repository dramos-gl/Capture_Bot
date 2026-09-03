"""
Design System — Chart Widgets (Molecules)
=========================================
Provides native QPainter chart components that integrate seamlessly with the
SAR Design System. All colors are sourced exclusively from the ``Colors``
token class; no hex literals appear in this module.

Components
----------
- ``DonutChartWidget``  — Circular donut chart for state/category distribution.
- ``BarChartWidget``    — Horizontal bar chart for comparative metrics.

Both widgets:
- Are theme-aware (light / dark) via ``ThemeManager.is_dark_active()``.
- Accept data via ``set_data(data)`` and re-paint automatically.
- Handle empty / zero-total states gracefully (display a placeholder ring/bars).
"""

from __future__ import annotations

import math
from typing import List, Dict, Any

from PySide6.QtWidgets import QWidget, QSizePolicy, QToolTip
from PySide6.QtCore import Qt, QRectF, QPointF, QSize
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QPen, QBrush,
    QLinearGradient, QFontMetrics, QFont, QMouseEvent,
)

from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.theme_manager import ThemeManager


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _hex_to_qcolor(hex_color: str) -> QColor:
    """Converts a CSS hex color (e.g. '#2563EB') to ``QColor``."""
    return QColor(hex_color)


def _text_color() -> QColor:
    """Returns the appropriate primary text color for the active theme."""
    return QColor(
        Colors.TEXT_DARK_PRIMARY if ThemeManager.is_dark_active()
        else Colors.TEXT_LIGHT_PRIMARY
    )


def _muted_color() -> QColor:
    """Returns the muted text color for labels/legends."""
    return QColor(
        Colors.TEXT_DARK_MUTED if ThemeManager.is_dark_active()
        else Colors.TEXT_LIGHT_MUTED
    )


def _surface_color() -> QColor:
    """Returns the surface background color for the active theme."""
    return QColor(
        Colors.SURFACE_DARK if ThemeManager.is_dark_active()
        else Colors.SURFACE_LIGHT
    )


def _border_color() -> QColor:
    return QColor(
        Colors.BORDER_DARK if ThemeManager.is_dark_active()
        else Colors.BORDER_LIGHT
    )


# ---------------------------------------------------------------------------
# DonutChartWidget
# ---------------------------------------------------------------------------

class DonutChartWidget(QWidget):
    """
    Circular donut chart for displaying category/state distribution.

    Data format
    -----------
    ``set_data`` receives a list of dicts::

        [
            {"label": "Generadas",  "value": 42, "color": Colors.ACCENT},
            {"label": "Autorizadas","value": 18, "color": Colors.SUCCESS},
            ...
        ]

    The ``"color"`` values MUST be ``Colors.*`` token strings.
    """

    _MIN_SIZE = QSize(200, 200)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []
        self._hovered_index: int = -1
        self._total: float = 0.0

        self.setMinimumSize(self._MIN_SIZE)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background: transparent;")
        self.setMouseTracking(True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_data(self, data: List[Dict[str, Any]]) -> None:
        """
        Update chart data and trigger a repaint.

        Parameters
        ----------
        data : list[dict]
            Each entry must have ``"label"`` (str), ``"value"`` (float),
            and ``"color"`` (str — a ``Colors.*`` token hex string).
        """
        self._data = [d for d in data if d.get("value", 0) > 0]
        self._total = sum(d.get("value", 0) for d in self._data)
        self.update()

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event):  # noqa: N802
        if not self.isVisible():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), Qt.transparent)

        w, h = self.width(), self.height()
        legend_h = 0

        # Determine legend height (rows of 2 items each)
        if self._data:
            legend_rows = math.ceil(len(self._data) / 2)
            legend_h = legend_rows * 20 + 8

        # Donut area
        donut_h = h - legend_h
        side = min(w, donut_h)
        cx = w / 2
        cy = donut_h / 2

        outer_r = side * 0.44
        inner_r = outer_r * 0.60

        outer_rect = QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)

        if not self._data or self._total == 0:
            self._draw_empty_donut(painter, outer_rect, inner_r, cx, cy)
        else:
            self._draw_segments(painter, outer_rect, inner_r, cx, cy, outer_r)
            self._draw_center_label(painter, cx, cy, inner_r)

        if self._data:
            self._draw_legend(painter, w, h, legend_h)

        painter.end()

    def _draw_empty_donut(self, painter: QPainter, outer_rect: QRectF,
                          inner_r: float, cx: float, cy: float) -> None:
        pen = QPen(_border_color(), 2, Qt.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(outer_rect)

        lbl = "Sin datos"
        painter.setPen(_muted_color())
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        fm = QFontMetrics(font)
        tw = fm.horizontalAdvance(lbl)
        painter.drawText(int(cx - tw / 2), int(cy + fm.ascent() / 2), lbl)

    def _draw_segments(self, painter: QPainter, outer_rect: QRectF,
                       inner_r: float, cx: float, cy: float, outer_r: float) -> None:
        start_angle = 90 * 16  # Qt angles: 1/16th degrees, starting from 12 o'clock
        gap_deg = 1.5          # Small visual gap between segments

        for idx, segment in enumerate(self._data):
            value = segment.get("value", 0)
            color_hex = segment.get("color", Colors.ACCENT)
            span = (value / self._total) * 360
            span_16 = int((span - gap_deg) * 16)

            color = _hex_to_qcolor(color_hex)
            is_hovered = (idx == self._hovered_index)

            if is_hovered:
                # Expand hovered segment slightly
                expand = outer_r * 0.06
                expanded_rect = outer_rect.adjusted(-expand, -expand, expand, expand)
                draw_rect = expanded_rect
                color = color.lighter(115)
            else:
                draw_rect = outer_rect

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawPie(draw_rect, start_angle, span_16)

            start_angle -= int(span * 16)

        # Punch inner hole
        painter.setBrush(_surface_color())
        painter.setPen(Qt.NoPen)
        hole_rect = QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)
        painter.drawEllipse(hole_rect)

    def _draw_center_label(self, painter: QPainter, cx: float, cy: float,
                           inner_r: float) -> None:
        total_int = int(self._total)
        label_top = "Total"
        label_val = f"{total_int:,}"

        # Value (large, colored)
        font_val = QFont()
        font_val.setPointSize(int(inner_r * 0.38))
        font_val.setBold(True)
        painter.setFont(font_val)
        fm_val = QFontMetrics(font_val)
        tw_val = fm_val.horizontalAdvance(label_val)

        painter.setPen(_hex_to_qcolor(Colors.ACCENT))
        painter.drawText(
            int(cx - tw_val / 2),
            int(cy + fm_val.ascent() * 0.3),
            label_val,
        )

        # "Total" sub-label (muted, smaller)
        font_sub = QFont()
        font_sub.setPointSize(int(inner_r * 0.22))
        painter.setFont(font_sub)
        fm_sub = QFontMetrics(font_sub)
        tw_sub = fm_sub.horizontalAdvance(label_top)
        painter.setPen(_muted_color())
        painter.drawText(
            int(cx - tw_sub / 2),
            int(cy - fm_val.ascent() * 0.4),
            label_top,
        )

    def _draw_legend(self, painter: QPainter, w: int, h: int, legend_h: int) -> None:
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        fm = QFontMetrics(font)

        items_per_row = 2
        item_w = w // items_per_row
        legend_top = h - legend_h + 4
        row, col = 0, 0

        for segment in self._data:
            label = segment.get("label", "")
            value = segment.get("value", 0)
            color = _hex_to_qcolor(segment.get("color", Colors.ACCENT))
            pct = (value / self._total * 100) if self._total > 0 else 0

            x = col * item_w + 8
            y = legend_top + row * 20

            # Color dot
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(int(x), int(y + 3), 8, 8)

            # Label text
            text = f"{label}: {value:,} ({pct:.1f}%)"
            painter.setPen(_muted_color())
            painter.drawText(int(x + 13), int(y + fm.ascent()), text)

            col += 1
            if col >= items_per_row:
                col = 0
                row += 1

    # ------------------------------------------------------------------
    # Mouse interaction (hover for highlight)
    # ------------------------------------------------------------------

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._data or self._total == 0:
            return

        w, h = self.width(), self.height()
        legend_rows = math.ceil(len(self._data) / 2)
        legend_h = legend_rows * 20 + 8
        donut_h = h - legend_h

        side = min(w, donut_h)
        cx, cy = w / 2, donut_h / 2
        outer_r = side * 0.44

        mx, my = event.position().x(), event.position().y()
        dx, dy = mx - cx, my - cy
        dist = math.sqrt(dx * dx + dy * dy)
        inner_r = outer_r * 0.60

        if dist < inner_r or dist > outer_r * 1.1:
            if self._hovered_index != -1:
                self._hovered_index = -1
                self.update()
            return

        angle = math.degrees(math.atan2(-dy, dx))  # counter-clockwise from East
        angle = (90 - angle) % 360                  # rotate to start from North

        cumulative = 0.0
        for idx, segment in enumerate(self._data):
            span = (segment.get("value", 0) / self._total) * 360
            cumulative += span
            if angle <= cumulative:
                if self._hovered_index != idx:
                    self._hovered_index = idx
                    seg = self._data[idx]
                    pct = seg.get("value", 0) / self._total * 100
                    QToolTip.showText(
                        event.globalPosition().toPoint(),
                        f"{seg.get('label', '')}: {seg.get('value', 0):,} ({pct:.1f}%)",
                        self,
                    )
                    self.update()
                return

        if self._hovered_index != -1:
            self._hovered_index = -1
            self.update()

    def leaveEvent(self, event) -> None:
        if self._hovered_index != -1:
            self._hovered_index = -1
            self.update()


# ---------------------------------------------------------------------------
# BarChartWidget
# ---------------------------------------------------------------------------

class BarChartWidget(QWidget):
    """
    Horizontal bar chart for comparative metrics (e.g. references per delegation).

    Data format
    -----------
    ``set_data`` receives::

        [
            {"label": "CDMX Norte", "value": 120, "color": Colors.ACCENT},
            {"label": "CDMX Sur",   "value": 85,  "color": Colors.ACCENT},
        ]

    If ``"color"`` is omitted, ``Colors.ACCENT`` is used.
    ``value_formatter`` is an optional callable ``(float) -> str`` for the
    value labels (default: integer formatting).
    """

    _BAR_HEIGHT = 22
    _BAR_GAP = 10
    _LABEL_WIDTH_RATIO = 0.30   # fraction of total width for category labels
    _VALUE_LABEL_MARGIN = 6     # px between bar end and value label

    def __init__(self, value_formatter=None, parent=None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []
        self._max_value: float = 0.0
        self._formatter = value_formatter or (lambda v: f"{int(v):,}")
        self._hovered_index: int = -1

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setStyleSheet("background: transparent;")
        self.setMouseTracking(True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_data(self, data: List[Dict[str, Any]]) -> None:
        """Update bar chart data and repaint."""
        self._data = data
        self._max_value = max((d.get("value", 0) for d in data), default=0)
        n = len(data)
        needed_h = n * (self._BAR_HEIGHT + self._BAR_GAP) + 20 if n else 60
        self.setMinimumHeight(needed_h)
        self.update()

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), Qt.transparent)

        if not self._data or self._max_value == 0:
            self._draw_empty(painter)
            painter.end()
            return

        w, h = self.width(), self.height()
        label_w = int(w * self._LABEL_WIDTH_RATIO)
        bar_area_w = w - label_w - 80  # reserve 80px for value labels

        font_label = QFont()
        font_label.setPointSize(8)
        painter.setFont(font_label)
        fm = QFontMetrics(font_label)

        for idx, item in enumerate(self._data):
            label = item.get("label", "")
            value = item.get("value", 0)
            color_hex = item.get("color", Colors.ACCENT)

            y_top = 10 + idx * (self._BAR_HEIGHT + self._BAR_GAP)

            # --- Category label (truncated) ---
            truncated = label
            while fm.horizontalAdvance(truncated) > label_w - 8 and len(truncated) > 3:
                truncated = truncated[:-4] + "…"
            painter.setPen(_muted_color())
            painter.drawText(
                0,
                int(y_top + (self._BAR_HEIGHT + fm.ascent()) / 2 - 2),
                truncated,
            )

            # --- Bar ---
            bar_x = label_w
            bar_w = max(2, int((value / self._max_value) * bar_area_w))

            is_hovered = (idx == self._hovered_index)
            color = _hex_to_qcolor(color_hex)
            if is_hovered:
                color = color.lighter(120)

            # Gradient fill
            grad = QLinearGradient(QPointF(bar_x, 0), QPointF(bar_x + bar_w, 0))
            grad.setColorAt(0, color)
            end_color = QColor(color)
            end_color.setAlpha(180)
            grad.setColorAt(1, end_color)

            bar_rect = QRectF(bar_x, y_top, bar_w, self._BAR_HEIGHT)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(grad))

            # Rounded bar
            path = QPainterPath()
            radius = min(self._BAR_HEIGHT / 2, bar_w / 2, 6.0)
            path.addRoundedRect(bar_rect, radius, radius)
            painter.drawPath(path)

            # --- Value label ---
            val_str = self._formatter(value)
            painter.setPen(_text_color())
            font_val = QFont()
            font_val.setPointSize(8)
            font_val.setBold(True)
            painter.setFont(font_val)
            fm_val = QFontMetrics(font_val)
            val_x = bar_x + bar_w + self._VALUE_LABEL_MARGIN
            val_y = int(y_top + (self._BAR_HEIGHT + fm_val.ascent()) / 2 - 2)
            painter.drawText(val_x, val_y, val_str)

            # Reset font for next label iteration
            painter.setFont(font_label)

        painter.end()

    def _draw_empty(self, painter: QPainter) -> None:
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(_muted_color())
        fm = QFontMetrics(font)
        msg = "Sin datos disponibles"
        tw = fm.horizontalAdvance(msg)
        painter.drawText(
            int(self.width() / 2 - tw / 2),
            int(self.height() / 2 + fm.ascent() / 2),
            msg,
        )

    # ------------------------------------------------------------------
    # Mouse hover
    # ------------------------------------------------------------------

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._data:
            return

        my = event.position().y()
        idx = int((my - 10) / (self._BAR_HEIGHT + self._BAR_GAP))

        if 0 <= idx < len(self._data):
            if self._hovered_index != idx:
                self._hovered_index = idx
                item = self._data[idx]
                tip = f"{item.get('label', '')}: {self._formatter(item.get('value', 0))}"
                QToolTip.showText(event.globalPosition().toPoint(), tip, self)
                self.update()
        else:
            if self._hovered_index != -1:
                self._hovered_index = -1
                self.update()

    def leaveEvent(self, event) -> None:
        if self._hovered_index != -1:
            self._hovered_index = -1
            self.update()
