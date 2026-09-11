"""Dialog for visual validation of company (RFC) fiscal addresses."""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QSplitter
)
from PySide6.QtCore import Qt, QThread, Signal

from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.theme_manager import ThemeManager
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.atoms.gl_input import CustomInput
from sar.src.ui.design_system.components.organisms.gl_dialog import CustomDialog
from sar.src.ui.design_system.components.organisms.gl_data_table import StyledDataTable
from sar.src.ui.design_system.utils.icons import Icons


class CompanyFiscalLoadWorker(QThread):
    """Background worker thread to fetch RFC fiscal data."""
    data_ready = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, ordenes_ui_service):
        super().__init__()
        self.ordenes_ui_service = ordenes_ui_service

    def run(self):
        try:
            data = self.ordenes_ui_service.get_rfcs_detalle_fiscal()
            self.data_ready.emit(data)
        except Exception as e:
            self.error_occurred.emit(str(e))


class CompanyFiscalValidationDialog(CustomDialog):
    """Modal dialog for viewing and verifying company fiscal domicile information in read-only mode."""

    def __init__(self, ordenes_ui_service, parent=None):
        super().__init__("Validación de Domicilios Fiscales de Empresas", parent=parent)
        self.ordenes_ui_service = ordenes_ui_service
        self.setMinimumWidth(920)
        self.setMinimumHeight(640)

        # Disable dialog save button since this is read-only
        self.btn_save.setVisible(False)
        self.btn_cancel.setText("Cerrar")
        self.btn_cancel.setObjectName("dangerBtn")
        self.btn_cancel.setIcon(Icons.cancelar("#FFFFFF"))
        self.btn_cancel.setToolTip("Cerrar ventana")
        self.btn_cancel.setMinimumWidth(CustomButton.DEFAULT_MIN_WIDTH)

        self._all_rfcs: List[Dict[str, Any]] = []
        self._filtered_rfcs: List[Dict[str, Any]] = []
        self._worker: Optional[CompanyFiscalLoadWorker] = None

        self._build_content()
        self._load_data()

    def _build_content(self):
        body_lay = self.body_layout
        body_lay.setContentsMargins(18, 14, 18, 14)
        body_lay.setSpacing(12)

        is_dark = ThemeManager.is_dark_active()

        # -------------------------------------------------------------
        # 1. GOLDEN RULE / BANNER DE REGLA DE ORO
        # -------------------------------------------------------------
        banner_frame = QFrame(self)
        banner_frame.setObjectName("goldenRuleBanner")
        banner_bg = "rgba(217, 119, 6, 0.15)" if is_dark else "#FEF3C7"
        banner_border = "rgba(245, 158, 11, 0.45)" if is_dark else "#FDE68A"
        banner_text_color = "#FCD34D" if is_dark else "#92400E"

        banner_frame.setStyleSheet(f"""
            QFrame#goldenRuleBanner {{
                background-color: {banner_bg};
                border: 1px solid {banner_border};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)

        banner_lay = QHBoxLayout(banner_frame)
        banner_lay.setContentsMargins(0, 0, 0, 0)
        banner_lay.setSpacing(12)

        lbl_icon = QLabel("⚠️", banner_frame)
        lbl_icon.setStyleSheet("font-size: 22px; background: transparent;")

        lbl_msg = QLabel(
            "<b>ATENCIÓN — REGLA DE ORO:</b> Antes de generar y enviar órdenes de trabajo a los BOTs de automatización, "
            "valida que el domicilio fiscal de cada empresa sea el correcto. "
            "Los derechos generados y facturados se emitirán exactamente como se encuentran registrados en el sistema.",
            banner_frame
        )
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet(f"color: {banner_text_color}; font-size: 12px; line-height: 1.4; background: transparent;")

        banner_lay.addWidget(lbl_icon, 0, Qt.AlignTop)
        banner_lay.addWidget(lbl_msg, 1)

        body_lay.addWidget(banner_frame)

        # -------------------------------------------------------------
        # 2. SEARCH BAR
        # -------------------------------------------------------------
        search_lay = QHBoxLayout()
        search_lay.setSpacing(10)

        self.txt_search = CustomInput("Buscar por RFC, Razón Social, Alias, Código Postal o Municipio...", parent=self)
        self.txt_search.setMinimumHeight(36)
        self.txt_search.textChanged.connect(self._on_search_changed)
        search_lay.addWidget(self.txt_search, 1)

        self.lbl_count = CustomLabel("0 empresas", variant="muted")
        search_lay.addWidget(self.lbl_count)

        body_lay.addLayout(search_lay)

        # -------------------------------------------------------------
        # 3. SPLITTER: TABLE (LEFT) + FISCAL CARD PREVIEW (RIGHT)
        # -------------------------------------------------------------
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setChildrenCollapsible(False)

        # Left Container: Table
        table_container = QWidget(splitter)
        table_lay = QVBoxLayout(table_container)
        table_lay.setContentsMargins(0, 0, 0, 0)
        table_lay.setSpacing(6)

        headers = ["ID", "RFC", "Razón Social / Comercial", "Municipio", "Estado"]
        self.tbl_rfcs = StyledDataTable(headers, parent=table_container)
        self.tbl_rfcs.setColumnHidden(0, True)  # Ocultar ID
        self.tbl_rfcs.itemSelectionChanged.connect(self._on_row_selected)

        table_lay.addWidget(self.tbl_rfcs)
        splitter.addWidget(table_container)

        # Right Container: Detailed Fiscal Domicile Card
        detail_container = QWidget(splitter)
        detail_lay = QVBoxLayout(detail_container)
        detail_lay.setContentsMargins(0, 0, 0, 0)
        detail_lay.setSpacing(8)

        card_detail = QFrame(detail_container)
        card_detail.setObjectName("cardDetailFiscal")
        card_bg = Colors.SURFACE_DARK if is_dark else Colors.SLATE_50
        card_border = Colors.BORDER_DARK if is_dark else Colors.SLATE_200
        card_detail.setStyleSheet(f"""
            QFrame#cardDetailFiscal {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 8px;
                padding: 14px;
            }}
        """)

        card_inner_lay = QVBoxLayout(card_detail)
        card_inner_lay.setContentsMargins(0, 0, 0, 0)
        card_inner_lay.setSpacing(12)

        lbl_card_title = CustomLabel("🏛️ FICHA FISCAL REGISTRADA", variant="subheader")
        lbl_card_title.setStyleSheet("font-size: 12px; font-weight: bold; margin-bottom: 2px;")
        card_inner_lay.addWidget(lbl_card_title)

        # Fiscal Info Rows
        self.lbl_det_rfc = CustomLabel("RFC: —", variant="body")
        self.lbl_det_rfc.setStyleSheet("font-weight: bold; font-size: 14px; color: #2563EB;")

        self.lbl_det_rs = CustomLabel("Razón Social: —", variant="body")
        self.lbl_det_rs.setStyleSheet("font-weight: 600;")
        self.lbl_det_rs.setWordWrap(True)

        self.lbl_det_alias = CustomLabel("Alias: —", variant="muted")

        # Domicilio
        lbl_sub_dom = CustomLabel("📍 Domicilio Fiscal:", variant="body")
        lbl_sub_dom.setStyleSheet("font-weight: bold; margin-top: 6px;")

        self.lbl_det_calle = CustomLabel("Calle: —", variant="body")
        self.lbl_det_numeros = CustomLabel("Números Ext/Int: —", variant="body")
        self.lbl_det_colonia = CustomLabel("Colonia / C.P.: —", variant="body")
        self.lbl_det_ubicacion = CustomLabel("Municipio / Estado: —", variant="body")

        card_inner_lay.addWidget(self.lbl_det_rfc)
        card_inner_lay.addWidget(self.lbl_det_rs)
        card_inner_lay.addWidget(self.lbl_det_alias)
        card_inner_lay.addWidget(lbl_sub_dom)
        card_inner_lay.addWidget(self.lbl_det_calle)
        card_inner_lay.addWidget(self.lbl_det_numeros)
        card_inner_lay.addWidget(self.lbl_det_colonia)
        card_inner_lay.addWidget(self.lbl_det_ubicacion)
        card_inner_lay.addStretch()

        # Status Capsule
        self.lbl_status_capsule = QLabel("Estado: ACTIVO", card_detail)
        self.lbl_status_capsule.setAlignment(Qt.AlignCenter)
        self.lbl_status_capsule.setStyleSheet("""
            background-color: rgba(34, 197, 94, 0.20);
            color: #16A34A;
            border: 1px solid rgba(34, 197, 94, 0.40);
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 11px;
            font-weight: bold;
        """)
        card_inner_lay.addWidget(self.lbl_status_capsule)

        detail_lay.addWidget(card_detail)
        splitter.addWidget(detail_container)

        # Set splitter proportions: 60% table, 40% card
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        body_lay.addWidget(splitter, 1)

    def _load_data(self):
        """Loads data in background thread."""
        self._worker = CompanyFiscalLoadWorker(self.ordenes_ui_service)
        self._worker.data_ready.connect(self._on_data_loaded)
        self._worker.error_occurred.connect(self._on_data_error)
        self._worker.start()

    def _on_data_loaded(self, rfcs: List[Dict[str, Any]]):
        self._all_rfcs = rfcs
        self._apply_filter()

    def _on_data_error(self, err_msg: str):
        from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
        QMessageBox.critical(self, "Error al Cargar Empresas", f"No se pudieron cargar los datos fiscales:\n{err_msg}")

    def _on_search_changed(self, text: str):
        self._apply_filter()

    def _apply_filter(self):
        search = self.txt_search.text().strip().lower()
        if not search:
            self._filtered_rfcs = list(self._all_rfcs)
        else:
            self._filtered_rfcs = [
                r for r in self._all_rfcs
                if (search in (r.get("rfc") or "").lower() or
                    search in (r.get("razon_social") or "").lower() or
                    search in (r.get("alias") or "").lower() or
                    search in (r.get("codigo_postal") or "").lower() or
                    search in (r.get("municipio") or "").lower())
            ]

        self.lbl_count.setText(f"{len(self._filtered_rfcs)} empresas")
        self._populate_table()

    def _populate_table(self):
        table_rows = []
        for r in self._filtered_rfcs:
            display_name = r.get("razon_social") or ""
            if r.get("alias"):
                display_name = f"{display_name} ({r.get('alias')})"
            
            table_rows.append([
                r.get("rfc_id", ""),
                r.get("rfc", ""),
                display_name,
                r.get("municipio", "—") or "—",
                r.get("estado", "—") or "—"
            ])

        self.tbl_rfcs.populate_rows(table_rows)

        # Select first row if available
        if self._filtered_rfcs:
            self.tbl_rfcs.selectRow(0)
            self._show_fiscal_detail(self._filtered_rfcs[0])
        else:
            self._clear_fiscal_detail()

    def _on_row_selected(self):
        selected_row = self.tbl_rfcs.currentRow()
        if 0 <= selected_row < len(self._filtered_rfcs):
            rfc_data = self._filtered_rfcs[selected_row]
            self._show_fiscal_detail(rfc_data)

    def _show_fiscal_detail(self, data: Dict[str, Any]):
        rfc = data.get("rfc") or "—"
        rs = data.get("razon_social") or "—"
        alias = data.get("alias") or "—"
        calle = data.get("calle") or "No registrada"
        no_ext = data.get("no_exterior") or "S/N"
        no_int = data.get("no_interior") or ""
        colonia = data.get("colonia") or "—"
        cp = data.get("codigo_postal") or "—"
        loc = data.get("localidad") or ""
        mun = data.get("municipio") or "—"
        est = data.get("estado") or "—"

        numeros = f"Ext: {no_ext}" + (f"  |  Int: {no_int}" if no_int else "")
        ubicacion = f"{mun}, {est}" + (f" ({loc})" if loc and loc != mun else "")

        self.lbl_det_rfc.setText(f"RFC: {rfc}")
        self.lbl_det_rs.setText(f"Razón Social:\n{rs}")
        self.lbl_det_alias.setText(f"Alias Comercial: {alias}")
        self.lbl_det_calle.setText(f"Calle: {calle}")
        self.lbl_det_numeros.setText(f"Números: {numeros}")
        self.lbl_det_colonia.setText(f"Colonia / CP: {colonia} (C.P. {cp})")
        self.lbl_det_ubicacion.setText(f"Ubicación: {ubicacion}")

        is_activo = data.get("activo", True)
        if is_activo:
            self.lbl_status_capsule.setText("Estado: ACTIVO")
            self.lbl_status_capsule.setStyleSheet("""
                background-color: rgba(34, 197, 94, 0.20);
                color: #16A34A;
                border: 1px solid rgba(34, 197, 94, 0.40);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            """)
        else:
            self.lbl_status_capsule.setText("Estado: INACTIVO")
            self.lbl_status_capsule.setStyleSheet("""
                background-color: rgba(239, 68, 68, 0.20);
                color: #EF4444;
                border: 1px solid rgba(239, 68, 68, 0.40);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            """)

    def _clear_fiscal_detail(self):
        self.lbl_det_rfc.setText("RFC: —")
        self.lbl_det_rs.setText("Razón Social: —")
        self.lbl_det_alias.setText("Alias: —")
        self.lbl_det_calle.setText("Calle: —")
        self.lbl_det_numeros.setText("Números: —")
        self.lbl_det_colonia.setText("Colonia / CP: —")
        self.lbl_det_ubicacion.setText("Ubicación: —")
        self.lbl_status_capsule.setText("Sin selección")
