"""Metrics and advanced reports dashboard dialog — native QPainter charts."""

from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QFrame,
    QPushButton, QMenu, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QMargins
from PySide6.QtGui import QPainter, QColor, QAction

from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.molecules.gl_combo_box import CustomComboBox
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.molecules.gl_card import CustomCard
from sar.src.ui.design_system.components.molecules.gl_stat_card import StatCard
from sar.src.ui.design_system.components.organisms.gl_data_table import StyledDataTable
from sar.src.ui.design_system.components.molecules.gl_menu import KeepOpenMenu
from sar.src.ui.design_system.components.molecules.gl_chart_widgets import DonutChartWidget, BarChartWidget
from sar.src.ui.design_system.utils.icons import Icons
from sar.src.ui.design_system.theme_manager import Colors
from sar.src.services.referencias_service import ReferenciasService
from sar.src.services.ordenes_ui_service import OrdenesUIService


# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------

class MetricsLoadWorker(QThread):
    """Fetches aggregated metrics report (grouped table + charts)."""
    result_ready = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, service: ReferenciasService, rfc_id, concepto_id,
                 delegacion_id, orden_ids, parent=None):
        super().__init__(parent)
        self.service = service
        self.rfc_id = rfc_id
        self.concepto_id = concepto_id
        self.delegacion_id = delegacion_id
        self.orden_ids = orden_ids

    def run(self):
        try:
            data = self.service.get_metrics_report(
                self.rfc_id, self.concepto_id, self.delegacion_id, self.orden_ids
            )
            self.result_ready.emit(data)
        except Exception as e:
            self.error_occurred.emit(str(e))


class MetricsSummaryWorker(QThread):
    """Fetches KPI summary: total refs, total amount, and per-status breakdown."""
    result_ready = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, service: ReferenciasService, rfc_id, concepto_id,
                 delegacion_id, orden_ids, parent=None):
        super().__init__(parent)
        self.service = service
        self.rfc_id = rfc_id
        self.concepto_id = concepto_id
        self.delegacion_id = delegacion_id
        self.orden_ids = orden_ids

    def run(self):
        try:
            data = self.service.get_metrics_summary(
                self.rfc_id, self.concepto_id, self.delegacion_id, self.orden_ids
            )
            self.result_ready.emit(data)
        except Exception as e:
            self.error_occurred.emit(str(e))


# ---------------------------------------------------------------------------
# State → display config map
# ---------------------------------------------------------------------------
_ESTADO_CONFIG = {
    "GENERADA":                {"label": "Generadas",                "icon": "file_text",     "color": Colors.ACCENT},
    "PENDIENTE_AUTORIZACION":  {"label": "Pend. Autorización",       "icon": "clock",         "color": Colors.WARNING},
    "AUTORIZACION_PENDIENTE":  {"label": "Pend. Autorización",       "icon": "clock",         "color": Colors.WARNING},
    "AUTORIZADA":              {"label": "Autorizadas",              "icon": "shield_check",  "color": Colors.SUCCESS},
    "RECHAZADA":               {"label": "Rechazadas",               "icon": "alert_triangle","color": Colors.ERROR},
    "ERROR":                   {"label": "Con Error",                "icon": "alert_triangle","color": Colors.ERROR},
    "EXPIRADA":                {"label": "Expiradas",                "icon": "alert_triangle","color": Colors.ACCENT_AMBER},
    "ASIGNADA":                {"label": "Asignadas",                "icon": "shield_check",  "color": Colors.ACCENT_EMERALD},
    "FACTURADA":               {"label": "Facturadas",               "icon": "file_text",     "color": Colors.ACCENT_INDIGO},
    "CANCELADA":               {"label": "Canceladas",               "icon": "alert_triangle","color": Colors.SLATE_500},
    "COMPLETADA":              {"label": "Completadas",              "icon": "shield_check",  "color": Colors.SUCCESS},
    "PENDIENTE":               {"label": "Pendientes",               "icon": "clock",         "color": Colors.WARNING},
}

_DEFAULT_ESTADO = {"label": None, "icon": "file_text", "color": Colors.SLATE_500}


# ---------------------------------------------------------------------------
# Dashboard View
# ---------------------------------------------------------------------------

class MetricsDashboardDialog(QWidget):
    """Advanced Metrics Dashboard View — Integrated inside MainView stacked container."""
    
    # Signal emitted when user wants to return to the main dashboard
    back_requested = Signal()

    def __init__(self, db_connector, initial_orden_ids: list = None, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.service = ReferenciasService(self.db_connector)
        self.ordenes_service = OrdenesUIService(self.db_connector)

        self.active_report_worker = None
        self.active_summary_worker = None
        self.todas_las_ordenes: List[dict] = []
        self.selected_orden_ids: List[int] = list(initial_orden_ids) if initial_orden_ids else []

        # Dict to hold estado StatCard widgets keyed by estado_codigo
        self._estado_cards: Dict[str, StatCard] = {}

        # Scrollable root so everything fits on small screens
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        root_widget = QWidget()
        root_widget.setStyleSheet("background: transparent;")
        self.main_layout = QVBoxLayout(root_widget)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(20)
        scroll.setWidget(root_widget)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(scroll)

        self._setup_header()
        self._setup_filters()
        self._setup_kpi_summary_area()
        self._setup_charts_area()
        self._setup_table_area()

        self._load_filters_data()

    # =========================================================================
    # Header
    # =========================================================================
    def _setup_header(self):
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        # Botón Volver / Atrás minimalista
        self.btn_back = QPushButton()
        self.btn_back.setObjectName("secondaryBtn")
        self.btn_back.setFixedSize(32, 32)
        self.btn_back.setIcon(Icons.volver(Colors.TEXT_LIGHT_PRIMARY))
        self.btn_back.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(self.btn_back)

        bar = QFrame(self)
        bar.setFixedWidth(4)
        bar.setFixedHeight(28)
        bar.setStyleSheet(f"background-color: {Colors.PRIMARY}; border-radius: 2px;")
        header_layout.addWidget(bar)

        txt = QVBoxLayout()
        txt.setSpacing(2)
        txt.setContentsMargins(0, 0, 0, 0)
        txt.addWidget(CustomLabel("Métricas y Analítica de Producción", variant="header"))
        txt.addWidget(CustomLabel("Reportes avanzados por empresa, conceptos y delegaciones", variant="muted"))
        header_layout.addLayout(txt)
        header_layout.addStretch()



        self.main_layout.addLayout(header_layout)

    # =========================================================================
    # Filters
    # =========================================================================
    # =========================================================================
    # Filters
    # =========================================================================
    def _setup_filters(self):
        self.card_filters = CustomCard(title="Filtros Analíticos", parent=self)
        # Ajustamos márgenes del layout interno para hacerlo más compacto
        self.card_filters.layout.setContentsMargins(12, 4, 12, 8)
        self.card_filters.layout.setSpacing(10)
        
        fl = QHBoxLayout()
        fl.setSpacing(14)

        # Orden
        v = QVBoxLayout()
        v.setSpacing(4)
        v.addWidget(CustomLabel("Orden / Folio:", variant="body"))
        self.btn_orden_filter = QPushButton("  Seleccionar Orden")
        self.btn_orden_filter.setObjectName("secondaryBtn")
        self.btn_orden_filter.setIcon(Icons.filter_icon(Colors.TEXT_LIGHT_SECONDARY))
        self.btn_orden_filter.setFixedHeight(32)
        self.btn_orden_filter.clicked.connect(self._show_orden_filter_menu)
        v.addWidget(self.btn_orden_filter)
        fl.addLayout(v, stretch=1)

        # RFC
        v2 = QVBoxLayout()
        v2.setSpacing(4)
        v2.addWidget(CustomLabel("Empresa (RFC):", variant="body"))
        self.cb_rfc = CustomComboBox(self)
        self.cb_rfc.setFixedHeight(32)
        self.cb_rfc.currentIndexChanged.connect(self.refresh_metrics)
        v2.addWidget(self.cb_rfc)
        fl.addLayout(v2, stretch=1)

        # Concepto
        v3 = QVBoxLayout()
        v3.setSpacing(4)
        v3.addWidget(CustomLabel("Concepto:", variant="body"))
        self.cb_concepto = CustomComboBox(self)
        self.cb_concepto.setFixedHeight(32)
        self.cb_concepto.currentIndexChanged.connect(self.refresh_metrics)
        v3.addWidget(self.cb_concepto)
        fl.addLayout(v3, stretch=1)

        # Delegación
        v4 = QVBoxLayout()
        v4.setSpacing(4)
        v4.addWidget(CustomLabel("Delegación:", variant="body"))
        self.cb_deleg = CustomComboBox(self)
        self.cb_deleg.setFixedHeight(32)
        self.cb_deleg.currentIndexChanged.connect(self.refresh_metrics)
        v4.addWidget(self.cb_deleg)
        fl.addLayout(v4, stretch=1)

        # Reset — usando patrón is_clean_btn del Design System (ícono + estilo correcto)
        v_reset = QVBoxLayout()
        v_reset.setSpacing(4)
        v_reset.addWidget(CustomLabel("", variant="body"))  # spacer label para alinear con combos
        btn_reset = CustomButton("Limpiar Filtros", is_clean_btn=True)
        btn_reset.setFixedHeight(32)
        btn_reset.setMinimumWidth(140)
        btn_reset.clicked.connect(self._reset_filters)
        v_reset.addWidget(btn_reset)
        fl.addLayout(v_reset)

        self.card_filters.layout.addLayout(fl)
        self.main_layout.addWidget(self.card_filters)

    # =========================================================================
    # KPI Summary cards (total + per-estado)
    # =========================================================================
    def _setup_kpi_summary_area(self):
        """Creates the row of KPI stat cards. Estado cards are added dynamically on first data load."""
        kpi_widget = QWidget(self)
        kpi_widget.setStyleSheet("background: transparent;")
        self._kpi_layout = QHBoxLayout(kpi_widget)
        self._kpi_layout.setContentsMargins(0, 0, 0, 0)
        self._kpi_layout.setSpacing(8)

        # Static "Total General" card (monto)
        self.card_total_monto = StatCard(
            "Monto Total General",
            "$ 0",
            icon_name="file_text",
            color_hex=Colors.PRIMARY,
            show_sparkline=False,
            parent=kpi_widget
        )
        self.card_total_monto.lbl_sub.setText("Monto acumulado filtrado")
        self._kpi_layout.addWidget(self.card_total_monto, stretch=1)

        # Static "Total Referencias" card
        self.card_total_refs = StatCard(
            "Total Referencias",
            "0",
            icon_name="file_text",
            color_hex=Colors.ACCENT,
            show_sparkline=False,
            parent=kpi_widget
        )
        self.card_total_refs.lbl_sub.setText("Bajo los filtros activos")
        self._kpi_layout.addWidget(self.card_total_refs, stretch=1)

        self._kpi_layout.addStretch()
        self.main_layout.addWidget(kpi_widget)
        self._kpi_estado_widget = kpi_widget

    def _update_kpi_cards(self, summary: dict):
        """Updates static KPI cards, per-estado stat cards, and the donut chart."""
        total_refs = summary.get("total_referencias", 0)
        importe = summary.get("importe_total", 0.0)
        por_estado: Dict[str, dict] = summary.get("por_estado", {})

        # Update static cards
        self.card_total_monto.set_value(f"$ {importe:,.0f}")
        self.card_total_refs.set_value(f"{total_refs:,}")

        # Merge PENDIENTE_AUTORIZACION + AUTORIZACION_PENDIENTE under one key
        merged: Dict[str, dict] = {}
        for codigo, vals in por_estado.items():
            key = "PENDIENTE_AUTORIZACION" if codigo in ("PENDIENTE_AUTORIZACION", "AUTORIZACION_PENDIENTE") else codigo
            if key not in merged:
                merged[key] = {"total": 0, "importe": 0.0}
            merged[key]["total"] += vals["total"]
            merged[key]["importe"] += vals["importe"]

        # Remove cards for states no longer present
        for codigo in list(self._estado_cards.keys()):
            if codigo not in merged:
                card = self._estado_cards.pop(codigo)
                self._kpi_layout.removeWidget(card)
                card.deleteLater()

        # Create or update per-estado cards
        for codigo, vals in merged.items():
            cfg = _ESTADO_CONFIG.get(codigo, _DEFAULT_ESTADO)
            label = cfg["label"] or codigo.replace("_", " ").title()
            color = cfg["color"]
            icon = cfg["icon"]
            count = vals["total"]

            if codigo not in self._estado_cards:
                card = StatCard(label, str(count), icon_name=icon, color_hex=color, show_sparkline=False,
                                parent=self._kpi_estado_widget)
                card.lbl_sub.setText(f"$ {vals['importe']:,.0f}")
                self._estado_cards[codigo] = card
                # Insert before the stretch (last item)
                self._kpi_layout.insertWidget(self._kpi_layout.count() - 1, card, stretch=1)
            else:
                card = self._estado_cards[codigo]
                card.set_value(f"{count:,}")
                card.lbl_sub.setText(f"$ {vals['importe']:,.0f}")

        # Feed the donut chart with state distribution data
        donut_data = [
            {
                "label": _ESTADO_CONFIG.get(cod, _DEFAULT_ESTADO).get("label") or cod.replace("_", " ").title(),
                "value": vals["total"],
                "color": _ESTADO_CONFIG.get(cod, _DEFAULT_ESTADO).get("color", Colors.ACCENT),
            }
            for cod, vals in merged.items()
            if vals["total"] > 0
        ]
        self.donut_chart.set_data(donut_data)

    # =========================================================================
    # Charts
    # =========================================================================
    def _setup_charts_area(self):
        """Creates the charts section: one donut (state distribution) + two horizontal bar charts."""
        charts_widget = QWidget(self)
        charts_widget.setStyleSheet("background: transparent;")
        cl = QHBoxLayout(charts_widget)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(20)

        # --- Left column: Donut de estados ---
        self.card_chart_donut = CustomCard(title="Distribución por Estado", parent=self)
        self.card_chart_donut.layout.setContentsMargins(8, 4, 8, 8)
        self.donut_chart = DonutChartWidget(parent=self.card_chart_donut)
        self.donut_chart.setMinimumHeight(260)
        self.card_chart_donut.add_widget(self.donut_chart)

        # --- Right column: two stacked bar charts ---
        right_col = QWidget(self)
        right_col.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        # Bar chart — quantity
        self.card_chart_qty = CustomCard(title="Referencias por Delegación", parent=self)
        self.card_chart_qty.layout.setContentsMargins(8, 4, 8, 8)
        self.bar_chart_qty = BarChartWidget(parent=self.card_chart_qty)
        self.bar_chart_qty.setMinimumHeight(130)
        self.card_chart_qty.add_widget(self.bar_chart_qty)

        # Bar chart — amounts
        self.card_chart_amount = CustomCard(title="Importe Total por Delegación ($)", parent=self)
        self.card_chart_amount.layout.setContentsMargins(8, 4, 8, 8)
        self.bar_chart_amount = BarChartWidget(
            value_formatter=lambda v: f"${v:,.0f}",
            parent=self.card_chart_amount,
        )
        self.bar_chart_amount.setMinimumHeight(130)
        self.card_chart_amount.add_widget(self.bar_chart_amount)

        right_layout.addWidget(self.card_chart_qty, stretch=1)
        right_layout.addWidget(self.card_chart_amount, stretch=1)

        cl.addWidget(self.card_chart_donut, stretch=1)
        cl.addWidget(right_col, stretch=2)
        self.main_layout.addWidget(charts_widget, stretch=1)

    # =========================================================================
    # Table
    # =========================================================================
    def _setup_table_area(self):
        self.card_table = CustomCard(title="Reporte de Consolidación Métrica", parent=self)
        self.card_table.layout.setContentsMargins(8, 4, 8, 8)
        
        headers = ["Empresa (RFC)", "Concepto", "Delegación", "Cantidad", "Monto Solicitado ($)"]
        self.table = StyledDataTable(headers, parent=self)
        self.table.setMinimumHeight(150)
        self.card_table.add_widget(self.table)
        self.main_layout.addWidget(self.card_table, stretch=1)

    # =========================================================================
    # Data loading
    # =========================================================================
    def _load_filters_data(self):
        try:
            self.cb_rfc.blockSignals(True)
            self.cb_concepto.blockSignals(True)
            self.cb_deleg.blockSignals(True)

            data = self.ordenes_service.get_catalogos()
            self.cb_rfc.addItem("Todas las Empresas", 0)
            for r in data.get("rfcs", []):
                self.cb_rfc.addItem(r["rfc"], r["rfc_id"])
            self.cb_concepto.addItem("Todos los Conceptos", 0)
            for c in data.get("conceptos", []):
                self.cb_concepto.addItem(c["nombre"], c["concepto_id"])
            self.cb_deleg.addItem("Todas las Delegaciones", 0)
            for d in data.get("delegaciones", []):
                self.cb_deleg.addItem(d["nombre"], d["delegacion_id"])
        except Exception as e:
            print("Error loading catalogs in metrics dialog:", e)
        finally:
            self.cb_rfc.blockSignals(False)
            self.cb_concepto.blockSignals(False)
            self.cb_deleg.blockSignals(False)

        try:
            raw_ordenes = self.ordenes_service.get_ordenes()
            self.todas_las_ordenes = [
                ord for ord in raw_ordenes
                if str(ord.get("estado", "") or ord.get("estado_codigo", "")).upper() not in ("RECHAZADA", "RECHAZADO", "CANCELADA", "CANCELADO")
            ]
            if not self.selected_orden_ids and self.todas_las_ordenes:
                self.selected_orden_ids = [self.todas_las_ordenes[0]["orden_id"]]
        except Exception as e:
            print("Error loading orders in metrics dialog:", e)
            self.todas_las_ordenes = []

        self._update_orden_filter_label()
        self.refresh_metrics()

    def _update_orden_filter_label(self):
        if not self.selected_orden_ids or not self.todas_las_ordenes:
            self.btn_orden_filter.setText("  Todas las Órdenes")
            return
        from sar.src.ui.design_system.utils.formatters import format_orden_filter_label
        if len(self.selected_orden_ids) == 1:
            orden = next((o for o in self.todas_las_ordenes
                          if o["orden_id"] == self.selected_orden_ids[0]), None)
            if orden:
                self.btn_orden_filter.setText(f"  {format_orden_filter_label(orden.get('folio', ''), orden.get('descripcion', ''), max_desc_len=25)}")
                return
        self.btn_orden_filter.setText(f"  {len(self.selected_orden_ids)} órdenes")

    # =========================================================================
    # Orden filter menu
    # =========================================================================
    def _show_orden_filter_menu(self):
        menu = KeepOpenMenu(self)
        order_actions = {}

        action_all = QAction("Todas las órdenes", menu, checkable=True)
        action_all.setChecked(
            len(self.selected_orden_ids) == len(self.todas_las_ordenes)
            and len(self.todas_las_ordenes) > 0
        )

        def update_all_action_state():
            is_all = len(self.selected_orden_ids) == len(self.todas_las_ordenes) and len(self.todas_las_ordenes) > 0
            action_all.blockSignals(True)
            action_all.setChecked(is_all)
            action_all.blockSignals(False)

        def toggle_all(checked):
            self.selected_orden_ids = (
                [o["orden_id"] for o in self.todas_las_ordenes] if checked else []
            )
            
            # Synchronize visual state of all order check items in menu
            for oid, act in order_actions.items():
                act.blockSignals(True)
                act.setChecked(checked)
                act.blockSignals(False)

            self._update_orden_filter_label()
            self.refresh_metrics()

        action_all.triggered.connect(toggle_all)
        menu.addAction(action_all)
        menu.addSeparator()

        from sar.src.ui.design_system.utils.formatters import format_orden_filter_label
        for orden in self.todas_las_ordenes:
            oid = orden["orden_id"]
            action = QAction(format_orden_filter_label(orden.get("folio", ""), orden.get("descripcion", "")), menu, checkable=True)
            action.setChecked(oid in self.selected_orden_ids)
            order_actions[oid] = action

            def make_handler(target_oid):
                def handler(checked):
                    if checked:
                        if target_oid not in self.selected_orden_ids:
                            self.selected_orden_ids.append(target_oid)
                    else:
                        if target_oid in self.selected_orden_ids:
                            self.selected_orden_ids.remove(target_oid)
                    update_all_action_state()
                    self._update_orden_filter_label()
                    self.refresh_metrics()
                return handler

            action.triggered.connect(make_handler(oid))
            menu.addAction(action)

        menu.exec(self.btn_orden_filter.mapToGlobal(self.btn_orden_filter.rect().bottomLeft()))

    # =========================================================================
    # Refresh — launches both workers simultaneously
    # =========================================================================
    def refresh_metrics(self):
        rfc_id      = self.cb_rfc.currentData() or None
        concepto_id = self.cb_concepto.currentData() or None
        deleg_id    = self.cb_deleg.currentData() or None
        if rfc_id == 0:      rfc_id = None
        if concepto_id == 0: concepto_id = None
        if deleg_id == 0:    deleg_id = None
        orden_ids = self.selected_orden_ids if self.selected_orden_ids else None

        # --- Report worker ---
        if self.active_report_worker and self.active_report_worker.isRunning():
            self.active_report_worker.terminate()
            self.active_report_worker.wait()
        self.active_report_worker = MetricsLoadWorker(
            self.service, rfc_id, concepto_id, deleg_id, orden_ids, self
        )
        self.active_report_worker.result_ready.connect(self._on_report_ready)
        self.active_report_worker.error_occurred.connect(
            lambda e: print("Metrics report error:", e)
        )
        self.active_report_worker.start()

        # --- Summary worker ---
        if self.active_summary_worker and self.active_summary_worker.isRunning():
            self.active_summary_worker.terminate()
            self.active_summary_worker.wait()
        self.active_summary_worker = MetricsSummaryWorker(
            self.service, rfc_id, concepto_id, deleg_id, orden_ids, self
        )
        self.active_summary_worker.result_ready.connect(self._update_kpi_cards)
        self.active_summary_worker.error_occurred.connect(
            lambda e: print("Metrics summary error:", e)
        )
        self.active_summary_worker.start()

    # =========================================================================
    # Callbacks
    # =========================================================================
    def _on_report_ready(self, data: List[Dict[str, Any]]):
        # Table
        self.table.populate_rows([
            [
                row["rfc_name"],
                row["concepto_name"],
                row["delegacion_name"],
                f"{row['total_referencias']:,}",
                f"$ {row['importe_total']:,.2f}",
            ]
            for row in data
        ])

        # Actualizar títulos de las tarjetas de gráficos dinámicamente
        rfc_txt = self.cb_rfc.currentText()
        if self.cb_rfc.currentIndex() == 0:
            rfc_txt = "Todas"

        concepto_txt = self.cb_concepto.currentText()
        if self.cb_concepto.currentIndex() == 0:
            concepto_txt = "Todos"
        else:
            if len(concepto_txt) > 25:
                concepto_txt = concepto_txt[:22] + "..."

        self.card_chart_qty.header.setText(f"Referencias por Delegación ({rfc_txt} - {concepto_txt})")
        self.card_chart_amount.header.setText(f"Importe por Delegación ({rfc_txt} - {concepto_txt})")

        # Aggregate by delegación for bar charts
        del_data: Dict[str, Dict] = {}
        for row in data:
            d = row["delegacion_name"]
            if d not in del_data:
                del_data[d] = {"qty": 0, "amount": 0.0}
            del_data[d]["qty"] += row["total_referencias"]
            del_data[d]["amount"] += row["importe_total"]

        # Bar chart 1 — References per delegation
        qty_data = [
            {"label": delegacion, "value": vals["qty"],    "color": Colors.ACCENT}
            for delegacion, vals in del_data.items()
        ]
        self.bar_chart_qty.set_data(qty_data)

        # Bar chart 2 — Amounts per delegation
        amt_data = [
            {"label": delegacion, "value": vals["amount"], "color": Colors.PRIMARY}
            for delegacion, vals in del_data.items()
        ]
        self.bar_chart_amount.set_data(amt_data)

    # =========================================================================
    # Reset
    # =========================================================================
    def _reset_filters(self):
        for cb in (self.cb_rfc, self.cb_concepto, self.cb_deleg):
            cb.blockSignals(True)
            cb.setCurrentIndex(0)
            cb.blockSignals(False)
        self.selected_orden_ids = (
            [self.todas_las_ordenes[0]["orden_id"]] if self.todas_las_ordenes else []
        )
        self._update_orden_filter_label()
        self.refresh_metrics()

    # =========================================================================
    # PDF Export Integration
    # =========================================================================
    def _export_to_pdf(self):
        """Generates a professional PDF report containing active filters, KPIs, charts, and data table."""
        from PySide6.QtWidgets import QFileDialog
        from sar.src.ui.design_system.components import GLMessageBox as QMessageBox
        from PySide6.QtGui import QPixmap, QImage
        import tempfile
        import os

        # 1. Ask user for destination file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Reporte en PDF",
            "Reporte_Analitica_Produccion.pdf",
            "PDF Files (*.pdf)"
        )
        if not file_path:
            return

        try:
            # 2. Capture charts as temporary image files
            temp_dir = tempfile.gettempdir()
            chart_donut_path = os.path.join(temp_dir, "temp_chart_donut.png")
            chart_qty_path = os.path.join(temp_dir, "temp_chart_qty.png")
            chart_amount_path = os.path.join(temp_dir, "temp_chart_amount.png")

            # Capture Donut
            pixmap_donut = self.donut_chart.grab()
            pixmap_donut.save(chart_donut_path, "PNG")

            # Capture Bar Chart 1 (References)
            pixmap_qty = self.bar_chart_qty.grab()
            pixmap_qty.save(chart_qty_path, "PNG")

            # Capture Bar Chart 2 (Amounts)
            pixmap_amt = self.bar_chart_amount.grab()
            pixmap_amt.save(chart_amount_path, "PNG")

            # 3. Gather filter information for the PDF header
            orden_txt = self.btn_orden_filter.text().strip()
            rfc_txt = self.cb_rfc.currentText()
            concepto_txt = self.cb_concepto.currentText()
            delegacion_txt = self.cb_deleg.currentText()

            # 4. Gather KPI values
            monto_kpi = self.card_total_monto.lbl_value.text()
            refs_kpi = self.card_total_refs.lbl_value.text()
            estados_info = []
            for cod, card in self._estado_cards.items():
                estados_info.append(f"{card.lbl_title.text()}: {card.lbl_value.text()} refs ({card.lbl_sub.text()})")

            # 5. Gather data table records
            table_rows = []
            for r in range(self.table.rowCount()):
                row_data = []
                for c in range(self.table.columnCount()):
                    item = self.table.item(r, c)
                    row_data.append(item.text() if item else "")
                table_rows.append(row_data)

            # 6. Generate the PDF structure using pypdf
            # Since ReportLab is not in the environment, we write a clean HTML/Print format or use PySide6 QPdfWriter.
            # QPdfWriter is native, doesn't require third-party libraries, and renders perfectly on Windows.
            from PySide6.QtGui import QPdfWriter, QPageLayout, QPageSize, QFont, QTextDocument
            from PySide6.QtCore import QSizeF

            writer = QPdfWriter(file_path)
            writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            writer.setPageOrientation(QPageLayout.Orientation.Portrait)
            writer.setPageMargins(QMargins(20, 20, 20, 20))

            # Build HTML layout for rendering to PDF
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: 'Segoe UI', sans-serif; color: #1E293B; margin: 20px; }}
                    h1 {{ color: #2C3E50; font-size: 24px; border-bottom: 2px solid #2C3E50; padding-bottom: 6px; }}
                    .section-title {{ color: #2C3E50; font-size: 16px; font-weight: bold; margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px; }}
                    th {{ background-color: #F1F5F9; color: #475569; font-weight: bold; text-align: left; padding: 6px; border: 1px solid #E2E8F0; }}
                    td {{ padding: 6px; border: 1px solid #E2E8F0; }}
                    tr:nth-child(even) {{ background-color: #F8FAFC; }}
                    .kpi-container {{ display: table; width: 100%; margin-top: 15px; margin-bottom: 15px; }}
                    .kpi-box {{ display: table-cell; width: 50%; padding: 10px; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; text-align: center; }}
                    .kpi-title {{ font-size: 12px; color: #64748B; font-weight: bold; }}
                    .kpi-value {{ font-size: 20px; color: #2563EB; font-weight: bold; margin-top: 4px; }}
                    .filter-info {{ background-color: #F8FAFC; border-left: 4px solid #2563EB; padding: 10px; font-size: 12px; margin-bottom: 15px; line-height: 1.5; }}
                    .chart-container {{ text-align: center; margin-top: 20px; }}
                    .chart-img {{ width: 45%; max-width: 320px; display: inline-block; margin: 10px; border: 1px solid #E2E8F0; border-radius: 6px; }}
                </style>
            </head>
            <body>
                <h1>Tablero de Métricas Avanzadas y Producción</h1>
                
                <div class="filter-info">
                    <strong>Filtros aplicados al reporte:</strong><br/>
                    • <strong>Orden/Folio:</strong> {orden_txt}<br/>
                    • <strong>Empresa:</strong> {rfc_txt}<br/>
                    • <strong>Concepto:</strong> {concepto_txt}<br/>
                    • <strong>Delegación:</strong> {delegacion_txt}
                </div>

                <div class="section-title">Resumen de KPIs Generales</div>
                <div class="kpi-container">
                    <div class="kpi-box" style="border-right: none;">
                        <div class="kpi-title">Monto Total General</div>
                        <div class="kpi-value">{monto_kpi}</div>
                    </div>
                    <div class="kpi-box">
                        <div class="kpi-title">Total Referencias</div>
                        <div class="kpi-value">{refs_kpi}</div>
                    </div>
                </div>

                <div style="font-size: 11px; margin-bottom: 15px; color: #475569;">
                    <strong>Desglose de Estados:</strong> {', '.join(estados_info)}
                </div>

                <div class="section-title">Gráficos de Producción por Delegación</div>
                <div class="chart-container">
                    <img class="chart-img" src="{chart_qty_path}" />
                    <img class="chart-img" src="{chart_amount_path}" />
                </div>

                <div style="page-break-before: always;"></div>

                <div class="section-title">Tabla de Consolidación Métrica (Detalle Completo)</div>
                <table>
                    <thead>
                        <tr>
                            <th>Empresa (RFC)</th>
                            <th>Concepto</th>
                            <th>Delegación</th>
                            <th style="text-align: right;">Cantidad</th>
                            <th style="text-align: right;">Monto Solicitado ($)</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for row in table_rows:
                html_content += f"""
                        <tr>
                            <td>{row[0]}</td>
                            <td>{row[1]}</td>
                            <td>{row[2]}</td>
                            <td style="text-align: right;">{row[3]}</td>
                            <td style="text-align: right;">{row[4]}</td>
                        </tr>
                """

            html_content += """
                    </tbody>
                </table>
            </body>
            </html>
            """

            # 7. Render html structure directly to the QPdfWriter PDF document
            doc = QTextDocument()
            # Set document search path for local temp files (images)
            doc.setDocumentLayout(doc.documentLayout())
            doc.setHtml(html_content)
            
            # Print document to writer
            doc.print_(writer)

            # 8. Clean up temp images safely
            try:
                if os.path.exists(chart_qty_path): os.remove(chart_qty_path)
                if os.path.exists(chart_amount_path): os.remove(chart_amount_path)
            except Exception:
                pass

            QMessageBox.information(
                self,
                "Reporte Exportado",
                f"El reporte de métricas y analítica se ha exportado exitosamente en PDF:\n{file_path}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error de Exportación",
                f"No se pudo exportar el reporte PDF debido al siguiente detalle:\n{str(e)}"
            )

