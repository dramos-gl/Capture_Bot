import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget,
    QFileDialog, QDialog, QFormLayout, QLineEdit, QTextEdit, QLabel, QComboBox,
    QDateEdit, QFrame, QMenu, QScrollArea, QGroupBox, QCheckBox
)

from PySide6.QtCore import Qt, QThread, Signal, QDate, QSize
from PySide6.QtGui import QColor
from sar.src.ui.design_system.components import (
    CustomCard, CustomButton, StyledDataTable, FilterBar, CustomComboBox,
    LabeledComboBox, LabeledDateEdit, KeepOpenMenu, CustomLabel, CustomInput, CustomCheckBox, InteractiveGrid, GLLoadingDialog,
    GLMessageBox as QMessageBox
)
from sar.src.ui.design_system.components.molecules.gl_stat_card import StatCard
from sar.src.ui.design_system.theme_manager import Colors, ThemeManager
from sar.src.services.inventario_ui_service import InventarioUIService
from sar.src.services.excel_inventory_handler import ExcelInventoryHandler
from sar.src.ui.design_system.utils.icons import Icons

class InventoryLoadWorker(QThread):
    """Background worker thread to load references from the DB dynamically with pagination."""
    result_ready = Signal(list, int, dict) # data, total_count, summary
    error_occurred = Signal(str)
    
    def __init__(self, inventario_ui_service, limit: int, offset: int, search_text: str, concepto_id: int, rfc_id: int, filter_assigned: str, start_date: str = None, end_date: str = None, orden_ids: list = None):
        super().__init__()
        self.inventario_ui_service = inventario_ui_service
        self.limit = limit
        self.offset = offset
        self.search_text = search_text
        self.concepto_id = concepto_id
        self.rfc_id = rfc_id
        self.filter_assigned = filter_assigned
        self.start_date = start_date
        self.end_date = end_date
        self.orden_ids = orden_ids
        self._is_cancelled = False
        
    def cancel(self):
        self._is_cancelled = True
        
    def run(self):
        try:
            if self._is_cancelled:
                return
            res = self.inventario_ui_service.get_referencias_facturadas_paginated(
                limit=self.limit,
                offset=self.offset,
                search_text=self.search_text,
                concepto_id=self.concepto_id,
                rfc_id=self.rfc_id,
                filter_assigned=self.filter_assigned,
                start_date=self.start_date,
                end_date=self.end_date,
                orden_ids=self.orden_ids
            )
            if self._is_cancelled:
                return
            summary = self.inventario_ui_service.get_inventario_summary(
                search_text=self.search_text,
                concepto_id=self.concepto_id,
                rfc_id=self.rfc_id,
                start_date=self.start_date,
                end_date=self.end_date,
                orden_ids=self.orden_ids
            )
            if not self._is_cancelled:
                self.result_ready.emit(res["records"], res["total_count"], summary)
        except Exception as e:
            if not self._is_cancelled:
                import traceback
                traceback.print_exc()
                self.error_occurred.emit(str(e))


class AvailabilityWorker(QThread):
    """Lightweight worker to fetch disponibles count for a single grid row without blocking UI."""
    result_ready = Signal(object, int)  # row_widget, count

    def __init__(self, service, row_widget, rfc_id: int, concepto_id: int, delegacion_id: int, orden_ids: list = None):
        super().__init__()
        self.service = service
        self.row_widget = row_widget
        self.rfc_id = rfc_id
        self.concepto_id = concepto_id
        self.delegacion_id = delegacion_id
        self.orden_ids = orden_ids

    def run(self):
        try:
            count = self.service.get_disponibles_count(self.rfc_id, self.concepto_id, self.delegacion_id, orden_ids=self.orden_ids)
            self.result_ready.emit(self.row_widget, count)
        except Exception:
            self.result_ready.emit(self.row_widget, 0)


from sar.src.ui.design_system.components.molecules.gl_loading_dialog import GLLoadingDialog

class ExcelWorker(QThread):
    finished = Signal(bool, str)  # success, message/error

    def __init__(self, file_path, header, data_rows):
        super().__init__()
        self.file_path = file_path
        self.header = header
        self.data_rows = data_rows

    def run(self):
        try:
            from sar.src.services.excel_inventory_handler import ExcelInventoryHandler
            ExcelInventoryHandler.generate_assignment_excel(
                dest_path=self.file_path,
                header=self.header,
                data_rows=self.data_rows,
            )
            self.finished.emit(True, "Excel generado exitosamente.")
        except Exception as e:
            self.finished.emit(False, str(e))


class PdfWorker(QThread):
    finished = Signal(dict) # success, missing, error

    def __init__(self, selected, dest_dir, header_data, inventario_ui_service):
        super().__init__()
        self.selected = selected
        self.dest_dir = dest_dir
        self.header_data = header_data
        self.inventario_ui_service = inventario_ui_service

    def run(self):
        import os
        import re
        import shutil
        from pypdf import PdfWriter, PdfReader

        def sanitize(name: str) -> str:
            return re.sub(r'[^\w\-.]', '_', name or "").strip("_") or "sin_nombre"

        def merge_or_copy_pdfs(pdf_paths: list, dest_path: str):
            valid = [p for p in pdf_paths if p and os.path.exists(p)]
            if not valid:
                return False
            if len(valid) == 1:
                shutil.copy2(valid[0], dest_path)
            else:
                writer = PdfWriter()
                for pp in valid:
                    try:
                        reader = PdfReader(pp)
                        for page in reader.pages:
                            writer.add_page(page)
                    except Exception:
                        pass
                with open(dest_path, "wb") as f:
                    writer.write(f)
            return True

        # Mapeos
        DELEG_MAP = {
            "CANCUN": "CUN",
            "CANCÚN": "CUN",
            "PLAYA DEL CARMEN": "PYA",
            "PLAYA": "PYA",
            "CHETUMAL": "CHE"
        }
        
        CONCEPTO_MAP = {
            "AVISO PREVENTIVO": "Aviso",
            "AVISO": "Aviso",
            "NUEVO_DERECHO_AVISO": "Aviso",
            "ANALISIS": "Analisis",
            "ANÁLISIS": "Analisis",
            "CLG": "CLG"
        }

        def clean_folder_name(name: str) -> str:
            cleaned = re.sub(r'[\\/:*?"<>|]', '_', name or "").strip()
            return cleaned if cleaned else "sin_desarrollo"

        success = error = missing = 0
        consecutivo_por_concepto = {}  # key: (desarrollo, concepto), value: counter
        estado_lote = self.header_data.get("estado_refs", "ASIGNADA")

        for d in self.selected:
            ref_id     = d.get("referencia_id")
            concepto   = sanitize(d.get("concepto", "CONCEPTO"))
            cliente    = sanitize(d.get("cliente", ""))
            referencia = sanitize(d.get("referencia", ""))
            estado_ref = d.get("estado", estado_lote)
            desarrollo_raw = d.get("desarrollo") or "Sin Desarrollo"
            desarrollo_clean = clean_folder_name(desarrollo_raw)

            if not ref_id:
                missing += 1
                continue
            try:
                facturas = self.inventario_ui_service.get_facturas_by_referencia_id(ref_id)
                if not facturas:
                    missing += 1
                    continue

                pdf_paths = []
                for f in facturas:
                    if f.get("pdf_path"):
                        pdf_paths.append(f["pdf_path"])
                    if f.get("pdf2_path") and f["pdf2_path"].lower().endswith(".pdf"):
                        pdf_paths.append(f["pdf2_path"])

                if not any(os.path.exists(p) for p in pdf_paths if p):
                    missing += 1
                    continue

                concepto_pretty = CONCEPTO_MAP.get((d.get("concepto") or "").strip().upper(), concepto)
                deleg_raw = (d.get("delegacion") or "").strip().upper()
                deleg_abbr = DELEG_MAP.get(deleg_raw, deleg_raw[:3] if deleg_raw else "CUN")
                # Determine assignment type (NOTARIA or COLABORADOR)
                tipo_lote = self.header_data.get("tipo_asignacion", "NOTARIA")
                concept_key = concepto_pretty.lower()

                # Rule: organize by Desarrollo/Concept folder and use Notaria naming pattern
                # ONLY for RESERVADA references assigned to a NOTARIA.
                if estado_ref == "RESERVADA" and tipo_lote == "NOTARIA":
                    folder_path = os.path.join(self.dest_dir, desarrollo_clean, concept_key)
                    os.makedirs(folder_path, exist_ok=True)
                    consec_key = (desarrollo_clean.lower(), concept_key)
                    consec_num = consecutivo_por_concepto.get(consec_key, 1)
                    consec = f"{consec_num:03d}"
                    
                    notaria_alias = self.header_data.get("notaria_alias")
                    if not notaria_alias:
                        notaria_raw = self.header_data.get("asignado_a", "Notaria")
                        nums = re.findall(r'\d+', notaria_raw)
                        notaria_alias = f"Not{nums[0]}" if nums else sanitize(notaria_raw)
                    out_name = f"{consec}_{referencia}_{notaria_alias}_{concepto_pretty}_{deleg_abbr}.pdf"
                else:
                    # Flat destination folder
                    folder_path = self.dest_dir
                    consec_key = concept_key
                    consec_num = consecutivo_por_concepto.get(consec_key, 1)
                    consec = f"{consec_num:03d}"

                    if estado_ref == "ASIGNADA":
                        out_name = f"{consec}_{cliente}_{concepto_pretty}.pdf"
                    else:  # COLABORADOR
                        out_name = f"{consec}_{referencia}_{concepto_pretty}_{deleg_abbr}.pdf"

                out_path = os.path.join(folder_path, out_name)
                if merge_or_copy_pdfs(pdf_paths, out_path):
                    success += 1
                    # Increment per‑concept counter
                    consecutivo_por_concepto[consec_key] = consec_num + 1
                else:
                    error += 1
            except Exception:
                error += 1

        self.finished.emit({"success": success, "missing": missing, "error": error})


class BatchValidationWorker(QThread):
    """Background worker thread to parse and validate Excel files asynchronously."""
    result_ready = Signal(list, list) # (parsed_records, validated_records)
    error_occurred = Signal(str)

    def __init__(self, file_path: str, default_rfc_id, completar_notaria_id, orden_ids, solo_reservar, api_client, db_connector):
        super().__init__()
        self.file_path = file_path
        self.default_rfc_id = default_rfc_id
        self.completar_notaria_id = completar_notaria_id
        self.orden_ids = orden_ids
        self.solo_reservar = solo_reservar
        self.api_client = api_client
        self.db_connector = db_connector

    def run(self):
        try:
            parsed = ExcelInventoryHandler.parse_excel_inventory(self.file_path)
            if not parsed:
                self.error_occurred.emit("No se encontraron filas con clientes o referencias válidas en el Excel.")
                return

            if self.api_client and self.api_client.connect_via_api:
                payload = {
                    "parsed_rows": parsed,
                    "default_rfc_id": self.default_rfc_id,
                    "completar_notaria_id": self.completar_notaria_id,
                    "orden_ids": self.orden_ids,
                    "solo_reservar": self.solo_reservar
                }
                validated = self.api_client.request("POST", "/api/docs/inventario/lotes/validar", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    validated = ExcelInventoryHandler.validate_parsed_rows(
                        session, parsed, default_rfc_id=self.default_rfc_id, completar_notaria_id=self.completar_notaria_id,
                        orden_ids=self.orden_ids,
                        solo_reservar=self.solo_reservar
                    )
            self.result_ready.emit(parsed, validated)
        except Exception as e:
            self.error_occurred.emit(str(e))


class BatchConfirmationWorker(QThread):
    """Background worker thread to save/confirm batch assignments without freezing UI."""
    success = Signal(dict)
    error_occurred = Signal(str)

    def __init__(
        self, is_completar: bool, api_client, db_connector, valid_details: list,
        usuario_id: int, tipo_destino: str, notaria_id, colaborador_id,
        solicitante_externo: str, observaciones: str, solo_reservar: bool
    ):
        super().__init__()
        self.is_completar = is_completar
        self.api_client = api_client
        self.db_connector = db_connector
        self.valid_details = valid_details
        self.usuario_id = usuario_id
        self.tipo_destino = tipo_destino
        self.notaria_id = notaria_id
        self.colaborador_id = colaborador_id
        self.solicitante_externo = solicitante_externo
        self.observaciones = observaciones
        self.solo_reservar = solo_reservar

    def run(self):
        try:
            if self.is_completar:
                if self.api_client and self.api_client.connect_via_api:
                    detalles_payload = []
                    for det in self.valid_details:
                        def _fmt_d(v):
                            if not v: return None
                            if hasattr(v, "strftime"): return v.strftime("%Y-%m-%d")
                            return str(v).split()[0] if str(v).strip() else None

                        det_dict = {
                            "lote_detalle_id": det.get("lote_detalle_id"),
                            "cliente": det.get("cliente"),
                            "desarrollo": det.get("desarrollo"),
                            "desarrollo_id": det.get("desarrollo_id"),
                            "concepto_solicitado": det.get("concepto_solicitado"),
                            "referencia_asignada": det.get("referencia_asignada"),
                            "referencia_id": det.get("referencia_id"),
                            "mz": det.get("mz"),
                            "lote": det.get("lote"),
                            "edif": det.get("edif"),
                            "viv": det.get("viv"),
                            "folio_electronico": det.get("folio_electronico"),
                            "estatus_primer_aviso": _fmt_d(det.get("estatus_primer_aviso") or det.get("fecha_ingreso_rpp")),
                            "ubicacion": det.get("ubicacion"),
                            "credito_titular": det.get("credito_titular"),
                            "pa": det.get("pa"),
                            "delegacion": det.get("delegacion"),
                            "fecha_solicitud": _fmt_d(det.get("fecha_solicitud")),
                            "fecha_reporte_notaria": _fmt_d(det.get("fecha_reporte_notaria")),
                            "fecha_ingreso_rpp": _fmt_d(det.get("fecha_ingreso_rpp") or det.get("estatus_primer_aviso")),
                            "fecha_escritura": _fmt_d(det.get("fecha_escritura")),
                            "fecha_titulacion": _fmt_d(det.get("fecha_titulacion")),
                            "comentarios": det.get("comentarios") or det.get("pa")
                        }
                        detalles_payload.append(det_dict)
                    payload = {
                        "detalles": detalles_payload,
                        "usuario_id": self.usuario_id
                    }
                    self.api_client.request("POST", "/api/docs/inventario/lotes/completar", data=payload)
                else:
                    with self.db_connector.get_session() as session:
                        from sar.src.storage.repositories import InventarioRepository
                        repo = InventarioRepository(session)
                        repo.completar_reservaciones(self.valid_details, usuario_id=self.usuario_id)
                        session.commit()
                self.success.emit({"mode": "completar", "total": len(self.valid_details)})
            else:
                if self.api_client and self.api_client.connect_via_api:
                    detalles_payload = []
                    for det in self.valid_details:
                        def _fmt_d(v):
                            if not v: return None
                            if hasattr(v, "strftime"): return v.strftime("%Y-%m-%d")
                            return str(v).split()[0] if str(v).strip() else None

                        det_dict = {
                            "cliente": det.get("cliente"),
                            "desarrollo": det.get("desarrollo"),
                            "desarrollo_id": det.get("desarrollo_id"),
                            "concepto_solicitado": det.get("concepto_solicitado"),
                            "referencia_asignada": det.get("referencia_asignada"),
                            "referencia_id": det.get("referencia_id"),
                            "mz": det.get("mz"),
                            "lote": det.get("lote"),
                            "edif": det.get("edif"),
                            "viv": det.get("viv"),
                            "folio_electronico": det.get("folio_electronico"),
                            "estatus_primer_aviso": _fmt_d(det.get("estatus_primer_aviso") or det.get("fecha_ingreso_rpp")),
                            "ubicacion": det.get("ubicacion"),
                            "credito_titular": det.get("credito_titular"),
                            "pa": det.get("pa"),
                            "delegacion": det.get("delegacion"),
                            "fecha_solicitud": _fmt_d(det.get("fecha_solicitud")),
                            "fecha_reporte_notaria": _fmt_d(det.get("fecha_reporte_notaria")),
                            "fecha_ingreso_rpp": _fmt_d(det.get("fecha_ingreso_rpp") or det.get("estatus_primer_aviso")),
                            "fecha_escritura": _fmt_d(det.get("fecha_escritura")),
                            "fecha_titulacion": _fmt_d(det.get("fecha_titulacion")),
                            "comentarios": det.get("comentarios") or det.get("pa")
                        }
                        detalles_payload.append(det_dict)

                    payload = {
                        "tipo_destino": self.tipo_destino,
                        "notaria_id": self.notaria_id,
                        "colaborador_id": self.colaborador_id,
                        "solicitante_externo": self.solicitante_externo,
                        "observaciones": self.observaciones,
                        "usuario_creacion": self.usuario_id,
                        "detalles": detalles_payload
                    }
                    res = self.api_client.request("POST", "/api/docs/inventario/lotes", data=payload)
                    lote_id = res["lote_id"]
                else:
                    with self.db_connector.get_session() as session:
                        from sar.src.storage.repositories import InventarioRepository
                        repo = InventarioRepository(session)
                        lote_id = repo.crear_lote_asignacion(
                            tipo_destino=self.tipo_destino,
                            notaria_id=self.notaria_id,
                            colaborador_id=self.colaborador_id,
                            solicitante_externo=self.solicitante_externo,
                            observaciones=self.observaciones,
                            usuario_creacion=self.usuario_id,
                            detalles_list=self.valid_details,
                            solo_reservar=self.solo_reservar
                        )
                        session.commit()
                self.success.emit({"mode": "crear", "lote_id": lote_id, "total": len(self.valid_details)})
        except Exception as e:
            self.error_occurred.emit(str(e))


class InventoryView(QWidget):
    """View to manage Invoice/Reference Inventory Control (state: FACTURADA)."""

    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.inventario_ui_service = InventarioUIService(self.db_connector)
        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()
        from sar.src.services.referencias_service import ReferenciasService
        self.referencias_service = ReferenciasService(self.db_connector)
        self.selected_orden_ids = []
        self.todas_las_ordenes = []
        self.is_custom_filter = False
        self.active_worker = None
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)

        # Tab Widget
        self.tabs = QTabWidget(self)

        # 1. Tab: Visor de Inventario
        self.tab_visor = QWidget()
        self._setup_tab_visor()
        self.tabs.addTab(self.tab_visor, "📋 Inventario")

        # 2. Tab: Asignación Masiva
        self.tab_masivo = QWidget()
        self._setup_tab_masivo()
        self.tabs.addTab(self.tab_masivo, "⚡ Asignar & Validar por lotes")

        # 3. Tab: Apartar Referencia
        self.tab_apartar = QWidget()
        self._setup_tab_apartar()
        self.tabs.addTab(self.tab_apartar, "🔑 Reserva de Derechos")

        # 4. Tab: Asignación Individual
        self.tab_individual = QWidget()
        self._setup_tab_individual()
        self.tabs.addTab(self.tab_individual, "👤 Asignar Derechos")

        # 5. Tab: Gestión de Asignaciones
        self.tab_lotes = QWidget()
        self._setup_tab_lotes()
        self.tabs.addTab(self.tab_lotes, "📋 Gestión de Asignaciones")

        # Hide tab bar headers to act as a QStackedWidget
        self.tabs.tabBar().hide()

        self.main_layout.addWidget(self.tabs)
        
        # Initial data loading (load only filters at start to make tab switching instant)
        self.refresh_all(load_catalogs=False)

    def set_active_tab(self, tab_key: str):
        """Switches active widget based on sidebar submenu navigation key."""
        if tab_key == "inventario_facturas":
            self.tabs.setCurrentWidget(self.tab_visor)
        elif tab_key == "inventario_masivo":
            self.tabs.setCurrentWidget(self.tab_masivo)
        elif tab_key == "inventario_apartar":
            self.tabs.setCurrentWidget(self.tab_apartar)
        elif tab_key in ("inventario_catalogos", "inventario_individual"):
            self.tabs.setCurrentWidget(self.tab_individual)
        elif tab_key == "inventario_lotes":
            self.tabs.setCurrentWidget(self.tab_lotes)


    def refresh_all(self, load_catalogs=True):
        if load_catalogs:
            self._load_catalogs_data()
        else:
            self._load_filters_data()
        self.refresh_visor_data()
        self.refresh_lotes_data()


    # =========================================================================
    # TAB 1: VISOR DE INVENTARIO
    # =========================================================================
    def _setup_tab_visor(self):
        tab_layout = QVBoxLayout(self.tab_visor)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        scroll_area = QScrollArea(self.tab_visor)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QWidget#visorScrollContent { background-color: transparent; }
        """)

        scroll_content = QWidget()
        scroll_content.setObjectName("visorScrollContent")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Filter bar
        self.filter_bar = FilterBar(
            search_placeholder="",
            state_options=["Todos", "Disponible", "Asignada", "Reservadas"],
            on_search=None,
            on_state_change=self._on_state_filter_visor,
            on_action=self.refresh_visor_data,
            action_icon_name="actualizar",
            action_tooltip="Actualizar Vista",
            parent=self
        )
        self.filter_bar.inp_search.setVisible(False)
        
        # Add Labeled Concept combo filter to filter bar
        from sar.src.ui.design_system.components.molecules.gl_labeled_combo import LabeledComboBox
        self.labeled_concept = LabeledComboBox("Concepto", ["Todos los conceptos"])
        self.cb_concept_filter = self.labeled_concept.combo
        self.cb_concept_filter.currentTextChanged.connect(self._on_concept_filter_visor)
        self.filter_bar.layout().insertWidget(self.filter_bar.layout().count() - 1, self.labeled_concept)

        # Add Labeled Empresa combo filter to filter bar
        self.labeled_empresa = LabeledComboBox("Empresa", ["Todas las empresas"])
        self.cb_empresa_filter = self.labeled_empresa.combo
        self.cb_empresa_filter.currentTextChanged.connect(self._on_empresa_filter_visor)
        self.filter_bar.layout().insertWidget(self.filter_bar.layout().count() - 1, self.labeled_empresa)
        
        layout.addWidget(self.filter_bar)

        # KPI summary cards
        kpi_widget = QWidget(self)
        kpi_widget.setStyleSheet("background: transparent;")
        self.kpi_layout = QHBoxLayout(kpi_widget)
        self.kpi_layout.setContentsMargins(0, 0, 0, 0)
        self.kpi_layout.setSpacing(12)
        
        self.card_total = StatCard(
            "Total de Derechos",
            "0",
            icon_name="file_text",
            color_hex=Colors.ACCENT,
            show_sparkline=False,
            parent=kpi_widget
        )
        self.card_total.lbl_sub.setText("Disponibles + Asignados + Reservados")
        self.card_total.double_clicked.connect(lambda: self._open_kpi_detail("total"))
        self.kpi_layout.addWidget(self.card_total, stretch=1)
        
        self.card_disponibles = StatCard(
            "Derechos Disponibles",
            "0",
            icon_name="clock",
            color_hex=Colors.PRIMARY,
            show_sparkline=False,
            parent=kpi_widget
        )
        self.card_disponibles.lbl_sub.setText("Total sin asignar")
        self.card_disponibles.double_clicked.connect(lambda: self._open_kpi_detail("disponibles"))
        self.kpi_layout.addWidget(self.card_disponibles, stretch=1)
        
        self.card_asignadas = StatCard(
            "Derechos Asignados",
            "0",
            icon_name="shield_check",
            color_hex=Colors.SUCCESS,
            show_sparkline=False,
            parent=kpi_widget
        )
        self.card_asignadas.lbl_sub.setText("Total asignados")
        self.card_asignadas.double_clicked.connect(lambda: self._open_kpi_detail("asignadas"))
        self.kpi_layout.addWidget(self.card_asignadas, stretch=1)

        self.card_reservadas = StatCard(
            "Derechos Reservados",
            "0",
            icon_name="archive",
            color_hex="#F59E0B",
            show_sparkline=False,
            parent=kpi_widget
        )
        self.card_reservadas.lbl_sub.setText("Total reservados")
        self.card_reservadas.double_clicked.connect(lambda: self._open_kpi_detail("reservadas"))
        self.kpi_layout.addWidget(self.card_reservadas, stretch=1)
        self.kpi_layout.addStretch()
        
        layout.addWidget(kpi_widget)

        # Main Card & Table
        self.card = CustomCard(title="", parent=self)
        
        # Table Header Layout (Title + Search + Filter)
        self.table_header_layout = QHBoxLayout()
        self.table_header_layout.setContentsMargins(0, 0, 0, 0)
        self.table_header_layout.setSpacing(12)
        
        # Section icon & label
        self.lbl_table_icon = QLabel()
        self.lbl_table_icon.setPixmap(Icons.file_text("#2563EB").pixmap(18, 18))
        self.lbl_table_icon.setStyleSheet("background: transparent;")
        
        self.lbl_table_title = CustomLabel("Derechos en Estado FACTURADA", variant="subheader")
        
        self.table_header_layout.addWidget(self.lbl_table_icon)
        self.table_header_layout.addWidget(self.lbl_table_title)
        self.table_header_layout.addStretch()
        
        # Search Box inside Table Header
        self.search_input_visor = QLineEdit(self)
        self.search_input_visor.setPlaceholderText("Buscar referencia...")
        self.search_input_visor.setFixedWidth(240)
        self.search_input_visor.addAction(Icons.search("#64748B"), QLineEdit.LeadingPosition)
        self.search_input_visor.textChanged.connect(self._on_search_visor)
        self.table_header_layout.addWidget(self.search_input_visor)
        
        # Filter Button (Funnel) inside Table Header
        self.btn_filter_orden = QPushButton()
        self.btn_filter_orden.setObjectName("secondaryBtn")
        self.btn_filter_orden.setIcon(Icons.filter_icon("#475569"))
        self.btn_filter_orden.setFixedSize(36, 36)
        self.btn_filter_orden.setToolTip("Filtrar por Órdenes")
        self.btn_filter_orden.clicked.connect(self._show_order_filter_menu)
        self.table_header_layout.addWidget(self.btn_filter_orden)
        
        self.card.layout.addLayout(self.table_header_layout)
        
        headers = ["✔", "ID", "Referencia", "Concepto", "Empresa", "Importe", "Estado", "Asignado A", "Tipo", "Solicitante", "Desarrollo", "Cliente", "Mz", "Lt", "Edif", "Viv", "Folio Electrónico", "Fecha Asignación"]
        self.table = StyledDataTable(headers, parent=self)
        self.table.setMinimumHeight(180)
        self.table.setMinimumWidth(200)
        self.table.setColumnHidden(1, True) # Hide internal ID
        self.card.add_widget(self.table)

        layout.addWidget(self.card)

        scroll_area.setWidget(scroll_content)
        tab_layout.addWidget(scroll_area)

        # Paging Info and Size
        footer_layout = QHBoxLayout()
        self.lbl_pagination_info = CustomLabel("Mostrando 0 a 0 de 0 derechos", variant="muted")
        footer_layout.addWidget(self.lbl_pagination_info)
        footer_layout.addStretch()

        self.cb_page_size = CustomComboBox(self)
        self.cb_page_size.addItems(["50 por página", "100 por página", "200 por página"])
        self.cb_page_size.setCurrentIndex(2) # Default 200
        self.cb_page_size.currentTextChanged.connect(self._on_page_size_changed)
        footer_layout.addWidget(self.cb_page_size)

        self.pagination_widget = QWidget(self)
        self.pag_btn_layout = QHBoxLayout(self.pagination_widget)
        self.pag_btn_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addWidget(self.pagination_widget)
        
        self.card.layout.addLayout(footer_layout)

        # Action Buttons
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        self.btn_limpiar_seleccion = CustomButton("Limpiar Selección", is_secondary=True)
        self.btn_limpiar_seleccion.clicked.connect(self._on_limpiar_seleccion)
        self.btn_limpiar_seleccion.setVisible(False)
        actions_layout.addWidget(self.btn_limpiar_seleccion)

        self.lbl_selected_badge = QLabel("", self)
        self.lbl_selected_badge.setStyleSheet("font-weight: bold; color: #1D4ED8; font-size: 12px; padding: 4px 8px; background-color: #EFF6FF; border-radius: 6px; border: 1px solid #BFDBFE;")
        self.lbl_selected_badge.setVisible(False)
        actions_layout.addWidget(self.lbl_selected_badge)

        actions_layout.addStretch()

        self.btn_asignar_seleccionados = CustomButton("Asignar Seleccionados")
        self.btn_asignar_seleccionados.setIcon(Icons.aceptar("#FFFFFF"))
        self.btn_asignar_seleccionados.setEnabled(False)
        self.btn_asignar_seleccionados.clicked.connect(self._on_asignar_seleccionados)
        actions_layout.addWidget(self.btn_asignar_seleccionados)
        
        self.card.layout.addLayout(actions_layout)
        layout.addWidget(self.card)

        # Pagination & selection state
        self.current_page = 1
        self.page_size = 200
        self.all_data = []
        self.visible_table_data = []
        self.total_items = 0
        self.selected_ref_map = {}
        self.active_worker = None
        self._current_search_text = ""
        self._current_estado_filter = "Todos"
        self._current_concepto_id = None
        self._current_rfc_id = None
        
        self.table.itemChanged.connect(self._on_table_item_changed)
        self.table.cellDoubleClicked.connect(self._on_table_cell_double_clicked)

    def refresh_visor_data(self):
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.cancel()
            try:
                self.active_worker.result_ready.disconnect(self._on_visor_data_loaded)
            except RuntimeError:
                pass
            try:
                self.active_worker.error_occurred.disconnect(self._on_visor_load_error)
            except RuntimeError:
                pass
            self.active_worker.wait()

        self._load_available_orders(preserve_selection=True)
        
        self.lbl_pagination_info.setText("Cargando inventario...")
        self.pagination_widget.setEnabled(False)

        offset = (self.current_page - 1) * self.page_size
        
        self.active_worker = InventoryLoadWorker(
            inventario_ui_service=self.inventario_ui_service,
            limit=self.page_size,
            offset=offset,
            search_text=self._current_search_text,
            concepto_id=self._current_concepto_id,
            rfc_id=self._current_rfc_id,
            filter_assigned=self._current_estado_filter,
            start_date=None,
            end_date=None,
            orden_ids=list(self.selected_orden_ids) if self.selected_orden_ids else None
        )
        self.active_worker.result_ready.connect(self._on_visor_data_loaded)
        self.active_worker.error_occurred.connect(self._on_visor_load_error)
        self.active_worker.start()

    def _on_visor_data_loaded(self, data, total_count, summary):
        self.all_data = data
        self.total_items = total_count
        self.pagination_widget.setEnabled(True)
        
        # Update cards
        disponibles = summary.get("disponibles", 0)
        asignadas = summary.get("asignadas", 0)
        reservadas = summary.get("reservadas", 0)
        total = disponibles + asignadas + reservadas
        
        self.card_total.set_value(f"{total:,}")
        self.card_disponibles.set_value(f"{disponibles:,}")
        self.card_asignadas.set_value(f"{asignadas:,}")
        self.card_reservadas.set_value(f"{reservadas:,}")
        
        self._populate_visor_table()

    def _on_visor_load_error(self, err):
        self.pagination_widget.setEnabled(True)
        self.lbl_pagination_info.setText("Error al cargar inventario.")
        QMessageBox.critical(self, "Error de Datos", f"Fallo al conectar con el servidor:\n{err}")

    def _populate_visor_table(self):
        # 1. Separate selected (pinned) vs unselected data to ensure selected rights remain visible
        selected_refs_list = list(self.selected_ref_map.values())
        selected_ids = set(self.selected_ref_map.keys())
        unselected_data = [r for r in self.all_data if r.get("referencia_id") not in selected_ids]
        
        # Pinned selected items always appear at the top
        self.visible_table_data = selected_refs_list + unselected_data

        rows_data = []
        for r in self.visible_table_data:
            if r.get("estado_codigo") == "RESERVADA":
                state_desc = "Reservada"
            else:
                state_desc = "Asignada" if r.get("asignada") else "Disponible"
            rows_data.append([
                "",
                str(r.get("referencia_id", "")),
                r.get("referencia_portal", ""),
                r.get("concepto", ""),
                r.get("empresa", ""),
                r.get("importe", ""),
                state_desc,
                r.get("asignado_a", ""),
                r.get("tipo_asignacion", ""),
                r.get("solicitante_externo", ""),
                r.get("desarrollo", ""),
                r.get("cliente", ""),
                r.get("mz", ""),
                r.get("lote", ""),
                r.get("edif", ""),
                r.get("viv", ""),
                r.get("folio_electronico", ""),
                r.get("fecha_asignacion", "")
            ])

        self.table.blockSignals(True)
        self.table.populate_rows(rows_data, checkable_first_col=True)
        
        # Configure checkboxes, highlight pinned rows, and disable assigned references
        pinned_bg_color = QColor("#EFF6FF") # Soft blue/primary tint for selected pinned rows
        
        for row_idx, r in enumerate(self.visible_table_data):
            check_item = self.table.item(row_idx, 0)
            if not check_item:
                continue
                
            r_id = r.get("referencia_id")
            is_asignada = r.get("asignada", False) or r.get("estado_codigo") == "ASIGNADA"
            
            if is_asignada:
                check_item.setFlags(check_item.flags() & ~Qt.ItemFlag.ItemIsEnabled & ~Qt.ItemFlag.ItemIsUserCheckable)
                check_item.setCheckState(Qt.CheckState.Unchecked)
                check_item.setToolTip("Los derechos en estado asignado no se pueden volver a asignar.")
            else:
                if r_id in self.selected_ref_map:
                    check_item.setCheckState(Qt.CheckState.Checked)
                    check_item.setToolTip("✓ Derecho seleccionado y fijado en la parte superior.")
                    for c_idx in range(self.table.columnCount()):
                        cell_item = self.table.item(row_idx, c_idx)
                        if cell_item:
                            cell_item.setBackground(pinned_bg_color)
                else:
                    check_item.setCheckState(Qt.CheckState.Unchecked)
                    
        self.table.blockSignals(False)
        self._update_selection_controls()

        # Update labels & paging buttons
        total_pages = max(1, (self.total_items + self.page_size - 1) // self.page_size)
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + len(self.all_data), self.total_items)

        self.lbl_pagination_info.setText(f"Mostrando {start_idx + 1} a {end_idx} de {self.total_items} derechos")

        # Re-draw pagination buttons
        while self.pag_btn_layout.count():
            item = self.pag_btn_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        def add_page_btn(text, target, enabled, is_active=False):
            btn = QPushButton(text)
            btn.setEnabled(enabled)
            if is_active:
                btn.setObjectName("paginationActivePageBtn")
            elif text in ("<<", "<", ">", ">>"):
                btn.setObjectName("paginationNavBtn")
            else:
                btn.setObjectName("paginationPageBtn")
            btn.clicked.connect(lambda: self._set_page(target))
            self.pag_btn_layout.addWidget(btn)

        add_page_btn("<<", 1, self.current_page > 1)
        add_page_btn("<", self.current_page - 1, self.current_page > 1)
        add_page_btn(str(self.current_page), self.current_page, True, is_active=True)
        add_page_btn(">", self.current_page + 1, self.current_page < total_pages)
        add_page_btn(">>", total_pages, self.current_page < total_pages)

    def _set_page(self, page):
        self.current_page = page
        self.refresh_visor_data()

    def _on_search_visor(self, text):
        self._current_search_text = text
        self.current_page = 1
        self.refresh_visor_data()

    def _on_state_filter_visor(self, text):
        if text == "Reservadas":
            self._current_estado_filter = "Reservada"
        else:
            self._current_estado_filter = text
        self.current_page = 1
        self.refresh_visor_data()

    def _on_concept_filter_visor(self, text):
        if text == "Todos los conceptos" or not hasattr(self, '_concepts_map'):
            self._current_concepto_id = None
        else:
            self._current_concepto_id = self._concepts_map.get(text)
        self.current_page = 1
        self.refresh_visor_data()

    def _on_empresa_filter_visor(self, text):
        if text == "Todas las empresas" or not hasattr(self, '_rfcs_map'):
            self._current_rfc_id = None
        else:
            self._current_rfc_id = self._rfcs_map.get(text)
        self.current_page = 1
        self.refresh_visor_data()

    def _open_kpi_detail(self, kpi_type: str):
        """Opens the full drill-down modal dialog for the selected KPI card."""
        from sar.src.ui.views.inventory_kpi_detail_dialog import InventoryKPIDetailDialog
        
        concepto_nom = self.cb_concept_filter.currentText() if hasattr(self, "cb_concept_filter") else "Todos los conceptos"
        empresa_nom = self.cb_empresa_filter.currentText() if hasattr(self, "cb_empresa_filter") else "Todas las empresas"
        
        dlg = InventoryKPIDetailDialog(
            db_connector=self.db_connector,
            kpi_type=kpi_type,
            concepto_id=getattr(self, "_current_concepto_id", None),
            concepto_nombre=concepto_nom,
            rfc_id=getattr(self, "_current_rfc_id", None),
            rfc_nombre=empresa_nom,
            orden_ids=getattr(self, "selected_orden_ids", []),
            ordenes_count=len(getattr(self, "selected_orden_ids", [])),
            start_date=getattr(self, "_current_start_date", None),
            end_date=getattr(self, "_current_end_date", None),
            parent=self
        )
        dlg.exec()

    def _load_available_orders(self, preserve_selection=False):
        try:
            raw_ordenes = self.referencias_service.get_ordenes(include_rejected=False)
            self.todas_las_ordenes = [
                ord for ord in raw_ordenes
                if str(ord.get("estado", "") or ord.get("estado_codigo", "")).upper() not in ("RECHAZADA", "RECHAZADO", "CANCELADA", "CANCELADO")
            ]
            if self.todas_las_ordenes:
                valid_ids = {ord["orden_id"] for ord in self.todas_las_ordenes}
                if preserve_selection and self.is_custom_filter and self.selected_orden_ids:
                    self.selected_orden_ids = [oid for oid in self.selected_orden_ids if oid in valid_ids]
                
                if not self.selected_orden_ids or (preserve_selection and not self.is_custom_filter):
                    self.selected_orden_ids = [ord["orden_id"] for ord in self.todas_las_ordenes if ord.get("total_disponibles", 0) > 0]
                    if not self.selected_orden_ids and self.todas_las_ordenes:
                        self.selected_orden_ids = [self.todas_las_ordenes[0]["orden_id"]]
            else:
                self.selected_orden_ids = []
        except Exception as e:
            print("Error loading available orders for inventory:", e)
            self.todas_las_ordenes = []
            self.selected_orden_ids = []

    def _show_order_filter_menu(self):
        from PySide6.QtGui import QAction
        
        sender_btn = self.sender()
        if not sender_btn:
            sender_btn = self.btn_filter_orden
            
        if not hasattr(self, 'todas_las_ordenes') or not self.todas_las_ordenes:
            self._load_available_orders()
            
        menu = KeepOpenMenu(self)
        order_actions = {}
        
        action_all = QAction("Todas las órdenes", menu, checkable=True)
        is_all_selected = len(self.selected_orden_ids) == len(self.todas_las_ordenes) and len(self.todas_las_ordenes) > 0
        action_all.setChecked(is_all_selected)
        
        def update_all_action_state():
            is_all = len(self.selected_orden_ids) == len(self.todas_las_ordenes) and len(self.todas_las_ordenes) > 0
            action_all.blockSignals(True)
            action_all.setChecked(is_all)
            action_all.blockSignals(False)
        
        def toggle_all(checked):
            self.is_custom_filter = True
            if checked:
                self.selected_orden_ids = [ord["orden_id"] for ord in self.todas_las_ordenes]
            else:
                self.selected_orden_ids = []
            
            # Synchronize visual state of all order check items in menu
            for oid, act in order_actions.items():
                act.blockSignals(True)
                act.setChecked(checked)
                act.blockSignals(False)
                
            self.current_page = 1
            self.current_page_lotes = 1
            self._refresh_active_tab_data()
            
        action_all.triggered.connect(toggle_all)
        menu.addAction(action_all)
        menu.addSeparator()
        
        from sar.src.ui.design_system.utils.formatters import format_orden_filter_label
        for ord in self.todas_las_ordenes:
            oid = ord["orden_id"]
            label = format_orden_filter_label(ord.get("folio", ""), ord.get("descripcion", ""))
            action = QAction(label, menu, checkable=True)
            action.setChecked(oid in self.selected_orden_ids)
            order_actions[oid] = action
            
            def make_toggle_handler(target_oid):
                def handler(checked):
                    self.is_custom_filter = True
                    if checked:
                        if target_oid not in self.selected_orden_ids:
                            self.selected_orden_ids.append(target_oid)
                    else:
                        if target_oid in self.selected_orden_ids:
                            self.selected_orden_ids.remove(target_oid)
                    update_all_action_state()
                    self.current_page = 1
                    self.current_page_lotes = 1
                    self._refresh_active_tab_data()
                return handler
                
            action.triggered.connect(make_toggle_handler(oid))
            menu.addAction(action)
            
        menu.exec(sender_btn.mapToGlobal(sender_btn.rect().bottomLeft()))

    def _refresh_active_tab_data(self):
        active = self.tabs.currentWidget()
        if active == self.tab_visor:
            self.refresh_visor_data()
        elif active == self.tab_individual:
            self._update_all_grids_availability()
            if self._pending_ind_refs:
                self._on_buscar_referencias_ind()
        elif active == self.tab_apartar:
            self._update_all_grids_availability()
        elif active == self.tab_lotes:
            self.refresh_lotes_data()

    def _update_all_grids_availability(self):
        active = self.tabs.currentWidget()
        if active == self.tab_individual:
            for row in self.grid_individual.rows:
                self.grid_individual.availability_requested.emit(row)
        elif active == self.tab_apartar:
            for row in self.grid_apartar.rows:
                self.grid_apartar.availability_requested.emit(row)

    def _on_page_size_changed(self, text):
        if "50" in text: self.page_size = 50
        elif "100" in text: self.page_size = 100
        else: self.page_size = 200
        self.current_page = 1
        self.refresh_visor_data()

    def _update_selection_controls(self):
        count = len(self.selected_ref_map)
            
        if count > 0:
            self.btn_asignar_seleccionados.setEnabled(True)
            self.btn_asignar_seleccionados.setText(f"Asignar Seleccionados ({count})")
            self.btn_limpiar_seleccion.setVisible(True)
            self.lbl_selected_badge.setText(f"{count} derecho(s) seleccionado(s)")
            self.lbl_selected_badge.setVisible(True)
        else:
            self.btn_asignar_seleccionados.setEnabled(False)
            self.btn_asignar_seleccionados.setText("Asignar Seleccionados")
            self.btn_limpiar_seleccion.setVisible(False)
            self.lbl_selected_badge.setVisible(False)

    def _on_table_item_changed(self, item):
        if item.column() == 0:
            row = item.row()
            if 0 <= row < len(self.visible_table_data):
                ref_dict = self.visible_table_data[row]
                r_id = ref_dict.get("referencia_id")
                is_asignada = ref_dict.get("asignada", False) or ref_dict.get("estado_codigo") == "ASIGNADA"
                
                if is_asignada:
                    if item.checkState() == Qt.CheckState.Checked:
                        item.setCheckState(Qt.CheckState.Unchecked)
                    if r_id in self.selected_ref_map:
                        del self.selected_ref_map[r_id]
                else:
                    if item.checkState() == Qt.CheckState.Checked:
                        self.selected_ref_map[r_id] = ref_dict
                    else:
                        if r_id in self.selected_ref_map:
                            del self.selected_ref_map[r_id]
                            
            self._update_selection_controls()

    def _on_table_cell_double_clicked(self, row, column):
        if row < 0 or row >= len(self.visible_table_data):
            return
            
        ref_dict = self.visible_table_data[row]
        is_asignada = ref_dict.get("asignada", False) or ref_dict.get("estado_codigo") == "ASIGNADA"
        if is_asignada:
            QMessageBox.information(self, "Derecho Asignado", "Este derecho ya se encuentra en estado ASIGNADO y no puede volver a asignarse.")
            return

        ref_id = ref_dict.get("referencia_id")
        ref_portal = ref_dict.get("referencia_portal", "")

        dialog = ManualAssignmentDialog(
            self.db_connector,
            [ref_id],
            [ref_portal],
            parent=self,
            selected_refs=[ref_dict]
        )
        if dialog.exec() == QDialog.Accepted:
            if ref_id in self.selected_ref_map:
                del self.selected_ref_map[ref_id]
            self._update_selection_controls()
            self.refresh_visor_data()

    def _on_limpiar_seleccion(self):
        self.selected_ref_map.clear()
        self._populate_visor_table()

    def _on_asignar_seleccionados(self):
        if not self.selected_ref_map:
            QMessageBox.warning(self, "Selección Vacía", "Por favor, selecciona al menos un derecho disponible en la tabla para asignarlo.")
            return

        selected_refs = list(self.selected_ref_map.values())
        ref_ids = [r["referencia_id"] for r in selected_refs]
        ref_portals = [r.get("referencia_portal", "") for r in selected_refs]

        dialog = ManualAssignmentDialog(
            self.db_connector,
            ref_ids,
            ref_portals,
            parent=self,
            selected_refs=selected_refs
        )
        if dialog.exec() == QDialog.Accepted:
            self.selected_ref_map.clear()
            self._update_selection_controls()
            self.refresh_visor_data()

    def _on_asignar_manual(self):
        self._on_asignar_seleccionados()

    def _on_exportar_reporte(self):
        lotes_dialog = ExportLotesDialog(self.db_connector, self)
        lotes_dialog.exec()

    # =========================================================================
    # TAB 2: ASIGNACIÓN MASIVA (EXCEL)
    # =========================================================================
    def _setup_tab_masivo(self):
        tab_layout = QVBoxLayout(self.tab_masivo)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        # 1. Scroll Area to guarantee responsiveness in 1366x768 and small screens
        scroll_area = QScrollArea(self.tab_masivo)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QWidget#masivoScrollContent {
                background-color: transparent;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setObjectName("masivoScrollContent")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        card_form = CustomCard(title="", parent=self)
        
        # Header Layout with Filter Button
        header_layout_masivo = QHBoxLayout()
        lbl_title_masivo = CustomLabel("Asignación Masiva por Lotes", variant="subheader")
        header_layout_masivo.addWidget(lbl_title_masivo)
        header_layout_masivo.addStretch()
        
        self.btn_filter_orden_masivo = QPushButton()
        self.btn_filter_orden_masivo.setObjectName("secondaryBtn")
        self.btn_filter_orden_masivo.setIcon(Icons.filter_icon("#475569"))
        self.btn_filter_orden_masivo.setFixedSize(36, 36)
        self.btn_filter_orden_masivo.setToolTip("Filtrar por Órdenes")
        self.btn_filter_orden_masivo.clicked.connect(self._show_order_filter_menu)
        header_layout_masivo.addWidget(self.btn_filter_orden_masivo)
        card_form.layout.addLayout(header_layout_masivo)
        
        # Checkboxes Container in a sleek 2-column horizontal layout
        chk_container = QWidget(self)
        chk_container.setStyleSheet("background: transparent;")
        chk_layout = QHBoxLayout(chk_container)
        chk_layout.setContentsMargins(4, 4, 4, 8)
        chk_layout.setSpacing(20)

        # Checkbox 1 (Completar Lote Reservado)
        chk1_box = QVBoxLayout()
        chk1_box.setSpacing(2)
        self.chk_completar_reserva = CustomCheckBox("Completar Lote Reservado", self)
        self.chk_completar_reserva.stateChanged.connect(self._on_completar_reserva_changed)
        chk1_box.addWidget(self.chk_completar_reserva)
        lbl_desc1 = QLabel("Asigna ubicación definitiva a derechos que ya han sido reservados.")
        lbl_desc1.setStyleSheet("color: #64748B; font-size: 11px; margin-left: 24px;")
        chk1_box.addWidget(lbl_desc1)
        chk_layout.addLayout(chk1_box, stretch=1)

        # Checkbox 2 (Reservar Derechos)
        chk2_box = QVBoxLayout()
        chk2_box.setSpacing(2)
        self.chk_solo_reservar = CustomCheckBox("Reservar Derechos", self)
        self.chk_solo_reservar.stateChanged.connect(self._on_solo_reservar_changed)
        chk2_box.addWidget(self.chk_solo_reservar)
        lbl_desc2 = QLabel("Reserva derechos ya usados de forma manual sin validación de clientes/dirección.")
        lbl_desc2.setStyleSheet("color: #64748B; font-size: 11px; margin-left: 24px;")
        chk2_box.addWidget(lbl_desc2)
        chk_layout.addLayout(chk2_box, stretch=1)

        card_form.layout.addWidget(chk_container)

        self.form_layout_masivo = QFormLayout()
        self.form_layout_masivo.setVerticalSpacing(8)
        self.form_layout_masivo.setHorizontalSpacing(16)
        self.form_layout_masivo.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.cb_destino_masivo = CustomComboBox(self)
        self.cb_destino_masivo.addItems(["-- Seleccione un tipo de destino --", "NOTARIA", "COLABORADOR"])
        self.cb_destino_masivo.currentTextChanged.connect(self._on_destino_masivo_changed)
        self.form_layout_masivo.addRow("Tipo Destino:", self.cb_destino_masivo)

        self.cb_notarias_masivo = CustomComboBox(self)
        self.form_layout_masivo.addRow("Notaría:", self.cb_notarias_masivo)

        self.cb_colaboradores_masivo = CustomComboBox(self)
        self.form_layout_masivo.addRow("Colaborador:", self.cb_colaboradores_masivo)

        self.cb_empresa_masivo = CustomComboBox(self)
        self.form_layout_masivo.addRow("Empresa por Defecto:", self.cb_empresa_masivo)

        self.txt_solicitante_masivo = QLineEdit(self)
        self.txt_solicitante_masivo.setPlaceholderText("Ej. Pedro Gómez")
        self.txt_solicitante_masivo.setMinimumHeight(36)
        self.form_layout_masivo.addRow("Solicitante Externo (Persona):", self.txt_solicitante_masivo)

        self.txt_obs_masivo = QTextEdit(self)
        self.txt_obs_masivo.setFixedHeight(45)
        self.txt_obs_masivo.setPlaceholderText("Notas u observaciones adicionales para el lote (opcional)...")
        self.form_layout_masivo.addRow("Observaciones:", self.txt_obs_masivo)

        # File picker row
        file_layout = QHBoxLayout()
        file_layout.setSpacing(10)
        self.lbl_excel_path = QLabel("Ningún archivo seleccionado", self)
        self.lbl_excel_path.setStyleSheet("color: #64748B; font-style: italic;")
        
        btn_pick_excel = CustomButton("Seleccionar Excel", is_secondary=True)
        btn_pick_excel.setMinimumHeight(36)
        btn_pick_excel.clicked.connect(self._on_pick_excel_masivo)
        
        btn_download_template = CustomButton("Descargar Plantilla", is_secondary=True)
        btn_download_template.setMinimumHeight(36)
        btn_download_template.clicked.connect(self._on_download_template)
        
        file_layout.addWidget(btn_pick_excel)
        file_layout.addWidget(btn_download_template)
        file_layout.addWidget(self.lbl_excel_path)
        file_layout.addStretch()
        self.form_layout_masivo.addRow("Archivo Excel:", file_layout)

        card_form.layout.addLayout(self.form_layout_masivo)
        layout.addWidget(card_form)

        # Preview list card
        self.card_preview = CustomCard(title="Previsualización de Coincidencias y Validaciones", parent=self)
        self.preview_table = StyledDataTable(["Fila Excel", "Cliente", "Desarrollo", "Delegación", "Concepto", "Referencia", "Ubicación", "Estatus Validation"], parent=self)
        self.preview_table.setMinimumHeight(160)
        self.preview_table.setMinimumWidth(200)
        self.card_preview.add_widget(self.preview_table)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 8, 0, 0)
        btn_layout.setSpacing(12)
        btn_layout.addStretch()
        self.btn_limpiar_preview = CustomButton("Limpiar", is_clean_btn=True)
        self.btn_limpiar_preview.setMinimumHeight(36)
        self.btn_limpiar_preview.clicked.connect(self._on_limpiar_preview)
        btn_layout.addWidget(self.btn_limpiar_preview)
        self.btn_confirmar_masivo = CustomButton("Confirmar")
        self.btn_confirmar_masivo.setMinimumHeight(36)
        self.btn_confirmar_masivo.setEnabled(False)
        self.btn_confirmar_masivo.clicked.connect(self._on_confirmar_masivo)
        btn_layout.addWidget(self.btn_confirmar_masivo)
        self.card_preview.layout.addLayout(btn_layout)

        layout.addWidget(self.card_preview)

        scroll_area.setWidget(scroll_content)
        tab_layout.addWidget(scroll_area)

        self.parsed_records = []
        self.validated_records = []
        
        # Hide internal widgets initially
        self.cb_colaboradores_masivo.hide()
        self.lbl_colab_row = self.form_layout_masivo.labelForField(self.cb_colaboradores_masivo)
        if self.lbl_colab_row: self.lbl_colab_row.hide()

        self.cb_notarias_masivo.hide()
        self.lbl_notaria_row = self.form_layout_masivo.labelForField(self.cb_notarias_masivo)
        if self.lbl_notaria_row: self.lbl_notaria_row.hide()

    def _on_completar_reserva_changed(self, state):
        is_checked = (state == 2 or state == Qt.CheckState.Checked)
        if is_checked:
            # Uncheck and disable mutual conflict
            self.chk_solo_reservar.blockSignals(True)
            self.chk_solo_reservar.setChecked(False)
            self.chk_solo_reservar.blockSignals(False)

            self.cb_destino_masivo.setCurrentText("NOTARIA")
            self.cb_destino_masivo.setEnabled(False)
            self._on_destino_masivo_changed("NOTARIA")
            self.cb_empresa_masivo.setEnabled(False)
            self.txt_solicitante_masivo.setEnabled(False)
            self.txt_obs_masivo.setEnabled(False)
        else:
            self.cb_destino_masivo.setEnabled(True)
            self.cb_empresa_masivo.setEnabled(True)
            self.txt_solicitante_masivo.setEnabled(True)
            self.txt_obs_masivo.setEnabled(True)

    def _on_solo_reservar_changed(self, state):
        is_checked = (state == 2 or state == Qt.CheckState.Checked)
        if is_checked:
            # Uncheck and disable mutual conflict
            self.chk_completar_reserva.blockSignals(True)
            self.chk_completar_reserva.setChecked(False)
            self.chk_completar_reserva.blockSignals(False)
            
            self.cb_destino_masivo.setEnabled(True)
            self.cb_empresa_masivo.setEnabled(True)
            self.txt_solicitante_masivo.setEnabled(True)
            self.txt_obs_masivo.setEnabled(True)

    def _on_destino_masivo_changed(self, text):
        if text == "NOTARIA":
            self.cb_notarias_masivo.show()
            lbl = self.form_layout_masivo.labelForField(self.cb_notarias_masivo)
            if lbl: lbl.show()
            
            self.cb_colaboradores_masivo.hide()
            lbl_c = self.form_layout_masivo.labelForField(self.cb_colaboradores_masivo)
            if lbl_c: lbl_c.hide()
            
            self.txt_solicitante_masivo.setEnabled(True)
        elif text == "COLABORADOR":
            self.cb_notarias_masivo.hide()
            lbl = self.form_layout_masivo.labelForField(self.cb_notarias_masivo)
            if lbl: lbl.hide()
            
            self.cb_colaboradores_masivo.show()
            lbl_c = self.form_layout_masivo.labelForField(self.cb_colaboradores_masivo)
            if lbl_c: lbl_c.show()
            
            self.txt_solicitante_masivo.setEnabled(False)
            self.txt_solicitante_masivo.clear()
        else:
            # Hide both if '-- Seleccione un tipo de destino --' is selected
            self.cb_notarias_masivo.hide()
            lbl = self.form_layout_masivo.labelForField(self.cb_notarias_masivo)
            if lbl: lbl.hide()
            
            self.cb_colaboradores_masivo.hide()
            lbl_c = self.form_layout_masivo.labelForField(self.cb_colaboradores_masivo)
            if lbl_c: lbl_c.hide()
            
            self.txt_solicitante_masivo.setEnabled(False)
            self.txt_solicitante_masivo.clear()

    def _on_download_template(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Plantilla de Importación",
            "Plantilla_Control_Inventario.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return
        try:
            ExcelInventoryHandler.generate_blank_template(file_path)
            QMessageBox.information(self, "Plantilla Descargada", f"Se ha generado la plantilla Excel con éxito en:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar la plantilla Excel:\n{str(e)}")

    def _on_limpiar_preview(self):
        self.parsed_records = []
        self.validated_records = []
        self.lbl_excel_path.setText("Ningún archivo seleccionado")
        self.preview_table.clearContents()
        self.preview_table.setRowCount(0)
        self.btn_confirmar_masivo.setEnabled(False)
        if hasattr(self, "_excel_file_path"):
            del self._excel_file_path

    def _on_pick_excel_masivo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Excel de Control", "", "Excel Files (*.xlsx)")
        if not file_path:
            return
            
        self.lbl_excel_path.setText(os.path.basename(file_path))
        self._excel_file_path = file_path

        # Get selected default RFC/Empresa from dropdown
        default_rfc_id = None
        default_empresa_txt = self.cb_empresa_masivo.currentText()
        if default_empresa_txt != "Seleccione empresa..." and hasattr(self, "_rfcs_map"):
            default_rfc_id = self._rfcs_map.get(default_empresa_txt)

        completar_notaria_id = None
        if self.chk_completar_reserva.isChecked():
            not_name = self.cb_notarias_masivo.currentText()
            completar_notaria_id = self._notarias_map.get(not_name)
            if not completar_notaria_id:
                QMessageBox.warning(self, "Seleccionar Notaría", "Por favor, selecciona una Notaría válida para completar su apartado.")
                return

        # Show Design System circular spinner loading dialog
        self._batch_loading_dialog = GLLoadingDialog("Cargando y validando\nplantilla Excel...", self)

        # Launch background validation worker
        self._batch_worker = BatchValidationWorker(
            file_path=file_path,
            default_rfc_id=default_rfc_id,
            completar_notaria_id=completar_notaria_id,
            orden_ids=list(self.selected_orden_ids) if self.selected_orden_ids else None,
            solo_reservar=self.chk_solo_reservar.isChecked(),
            api_client=self.api_client,
            db_connector=self.db_connector
        )
        self._batch_worker.result_ready.connect(self._on_batch_validation_success)
        self._batch_worker.error_occurred.connect(self._on_batch_validation_error)
        self._batch_worker.start()
        self._batch_loading_dialog.exec()

    def _on_batch_validation_success(self, parsed_records, validated_records):
        if hasattr(self, "_batch_loading_dialog") and self._batch_loading_dialog:
            self._batch_loading_dialog.accept()

        self.parsed_records = parsed_records
        self.validated_records = validated_records

        # Populate preview table
        preview_rows = []
        has_errors = False
        for r in self.validated_records:
            intento = r.get("intento", 1)
            status_txt = r["status"]
            if r["status"] == "ERROR":
                has_errors = True
                status_txt = f"🔴 ERROR: {r['error_message']}"
            elif r["status"] == "WARNING":
                status_txt = f"🟡 WARNING: {r['error_message']}"
            else:
                status_txt = f"🟢 CORRECTO (Intento {intento})" if intento > 1 else "🟢 CORRECTO"

            loc_str = f"Mz {r['mz']} Lt {r['lote']}"
            if r["edif"]: loc_str += f" Edif {r['edif']}"
            if r["viv"]: loc_str += f" Viv {r['viv']}"
            if intento > 1: loc_str += f" [Intento {intento}]"

            preview_rows.append([
                str(r["excel_row"]),
                r["cliente"],
                r["desarrollo"],
                r["delegacion_nombre"],
                r["concepto_solicitado"],
                r["referencia_asignada"],
                loc_str,
                status_txt
            ])

        self.preview_table.populate_rows(preview_rows)
        self.btn_confirmar_masivo.setEnabled(len(self.validated_records) > 0)

        if has_errors:
            # Group error types to show a clear diagnostic report to the QA Auditor
            error_types = set()
            for r in self.validated_records:
                if r["status"] == "ERROR":
                    if "no existe" in r["error_message"].lower():
                        error_types.add("Referencias inexistentes en la base de datos")
                    elif "ya está asignada" in r["error_message"].lower():
                        error_types.add("Referencias ya asignadas/confirmadas previamente")
                    else:
                        error_types.add(r["error_message"])
            
            err_summary = "\n- ".join(error_types)
            QMessageBox.warning(
                self, 
                "Inconsistencias y Errores Detectados", 
                f"Se identificaron los siguientes problemas en el archivo Excel:\n\n- {err_summary}\n\n"
                "Por seguridad, estos registros marcados en ROJO se omitirán durante la importación. Puede corregirlos en el Excel y volver a validar."
            )

    def _on_batch_validation_error(self, error_msg):
        if hasattr(self, "_batch_loading_dialog") and self._batch_loading_dialog:
            self._batch_loading_dialog.accept()
        QMessageBox.critical(self, "Error al Cargar Excel", f"Ocurrió un error al procesar el archivo:\n{error_msg}")

    def _on_confirmar_masivo(self):
        tipo_destino = self.cb_destino_masivo.currentText()
        notaria_id = None
        colaborador_id = None
        
        if tipo_destino == "NOTARIA":
            not_name = self.cb_notarias_masivo.currentText()
            notaria_id = self._notarias_map.get(not_name)
            if not notaria_id:
                QMessageBox.warning(self, "Falta Selección", "Selecciona una notaría válida.")
                return
        else:
            col_name = self.cb_colaboradores_masivo.currentText()
            colaborador_id = self._colaboradores_map.get(col_name)
            if not colaborador_id:
                QMessageBox.warning(self, "Falta Selección", "Selecciona un colaborador válido.")
                return

        solicitante_externo = self.txt_solicitante_masivo.text().strip()
        if tipo_destino == "NOTARIA" and not self.chk_completar_reserva.isChecked() and not solicitante_externo:
            QMessageBox.warning(self, "Falta Acreditación", "Ingresa el nombre del Solicitante Externo (ej. Pedro Gómez) para la Notaría.")
            return

        observaciones = self.txt_obs_masivo.toPlainText().strip()

        # Filter only correct or warned records
        valid_details = []
        warnings_count = 0
        errors_count = 0
        warning_messages = set()
        
        for r in self.validated_records:
            if r["status"] == "ERROR":
                errors_count += 1
                continue
            if r["status"] == "WARNING":
                warnings_count += 1
                if "ya tiene una asignación" in r["error_message"].lower():
                    warning_messages.add("Duplicación de ubicación (se incrementará el número de 'Intento' consecutivamente)")
                else:
                    warning_messages.add(r["error_message"])
            valid_details.append(r)

        if not valid_details:
            QMessageBox.critical(self, "Guardado Fallido", "No hay registros válidos para importar en el lote de asignación.")
            return

        # Prepare a highly detailed and professional QA confirmation prompt
        prompt_msg = (
            f"¿Estás seguro de que deseas guardar y confirmar este lote de asignación?\n\n"
            f"📊 Resumen de registros:\n"
            f"  • Listos para procesar (Reservadas/Asignadas): {len(valid_details) - warnings_count}\n"
            f"  • Registros con advertencias (Ubicación duplicada): {warnings_count}\n"
            f"  • Registros con error crítico (Omitidos): {errors_count}\n\n"
        )
        if warning_messages:
            prompt_msg += "⚠️ ADVERTENCIAS IMPORTANTES:\n- " + "\n- ".join(warning_messages) + "\n\n"
        
        if errors_count > 0:
            prompt_msg += "Nota: Los registros marcados con error crítico no se guardarán en la base de datos.\n\n"

        reply = QMessageBox.question(
            self, "Confirmar Importación de Lote",
            prompt_msg,
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        try:
            parent_window = self.window()
            usuario_id = getattr(parent_window, "current_usuario_id", 1) # Default admin

            # Show GLLoadingDialog with multiline centered message
            msg = "Completando asignaciones\nreservadas..." if self.chk_completar_reserva.isChecked() else "Guardando y confirmando\nlote de asignación..."
            self._confirm_loading_dialog = GLLoadingDialog(msg, self)

            # Launch background confirmation worker
            self._confirm_worker = BatchConfirmationWorker(
                is_completar=self.chk_completar_reserva.isChecked(),
                api_client=self.api_client,
                db_connector=self.db_connector,
                valid_details=valid_details,
                usuario_id=usuario_id,
                tipo_destino=tipo_destino,
                notaria_id=notaria_id,
                colaborador_id=colaborador_id,
                solicitante_externo=solicitante_externo,
                observaciones=observaciones,
                solo_reservar=self.chk_solo_reservar.isChecked()
            )
            self._confirm_worker.success.connect(self._on_confirm_batch_success)
            self._confirm_worker.error_occurred.connect(self._on_confirm_batch_error)
            self._confirm_worker.start()
            self._confirm_loading_dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Error de Inicio", f"No se pudo iniciar el proceso de guardado:\n{str(e)}")

    def _on_confirm_batch_success(self, res_data):
        if hasattr(self, "_confirm_loading_dialog") and self._confirm_loading_dialog:
            self._confirm_loading_dialog.accept()

        mode = res_data.get("mode")
        total = res_data.get("total", 0)
        if mode == "completar":
            QMessageBox.information(self, "Lote Completado", f"Se han completado exitosamente {total} asignaciones reservadas.")
        else:
            lote_id = res_data.get("lote_id")
            QMessageBox.information(self, "Lote Guardado", f"Se ha registrado exitosamente el lote ID {lote_id} con {total} asignaciones.")

        # Reset values
        self.lbl_excel_path.setText("Ningún archivo seleccionado")
        self.txt_obs_masivo.clear()
        self.txt_solicitante_masivo.clear()
        self.preview_table.clearContents()
        self.preview_table.setRowCount(0)
        self.btn_confirmar_masivo.setEnabled(False)
        self.parsed_records = []
        self.validated_records = []

        self.refresh_all()

    def _on_confirm_batch_error(self, error_msg):
        if hasattr(self, "_confirm_loading_dialog") and self._confirm_loading_dialog:
            self._confirm_loading_dialog.accept()
        QMessageBox.critical(self, "Error de Escritura", f"Fallo al guardar en la base de datos:\n{error_msg}")

    # =========================================================================
    # TAB 3: GESTIÓN DE CATALOGOS
    # =========================================================================
    def _setup_tab_individual(self):
        tab_layout = QVBoxLayout(self.tab_individual)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        scroll_area = QScrollArea(self.tab_individual)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QWidget#indScrollContent { background-color: transparent; }
        """)

        scroll_content = QWidget()
        scroll_content.setObjectName("indScrollContent")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        card_ind = CustomCard(parent=self)
        form_layout = QVBoxLayout()
        form_layout.setSpacing(16)

        # Header with Filter Button
        card_header_layout = QHBoxLayout()
        card_title_vbox = QVBoxLayout()
        lbl_card_title = CustomLabel("Asignación de Derechos Directa", variant="subheader")
        card_title_vbox.addWidget(lbl_card_title)
        card_header_layout.addLayout(card_title_vbox)
        card_header_layout.addStretch()
        
        self.btn_filter_orden_ind = QPushButton()
        self.btn_filter_orden_ind.setObjectName("secondaryBtn")
        self.btn_filter_orden_ind.setIcon(Icons.filter_icon("#475569"))
        self.btn_filter_orden_ind.setFixedSize(36, 36)
        self.btn_filter_orden_ind.setToolTip("Filtrar por Órdenes")
        self.btn_filter_orden_ind.clicked.connect(self._show_order_filter_menu)
        card_header_layout.addWidget(self.btn_filter_orden_ind)
        
        form_layout.addLayout(card_header_layout)


        # Destino Selectors
        dest_layout = QHBoxLayout()
        dest_layout.setSpacing(16)

        vbox_tipo = QVBoxLayout()
        lbl_tipo = CustomLabel("Tipo de Destino", variant="body")
        lbl_tipo.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        self.cb_tipo_destino_ind = CustomComboBox(self)
        self.cb_tipo_destino_ind.addItem("-- Seleccione Destino --", None)
        self.cb_tipo_destino_ind.addItems(["NOTARIA", "COLABORADOR"])
        self.cb_tipo_destino_ind.setCurrentIndex(0)
        self.cb_tipo_destino_ind.currentTextChanged.connect(self._on_tipo_destino_ind_changed)
        vbox_tipo.addWidget(lbl_tipo)
        vbox_tipo.addWidget(self.cb_tipo_destino_ind)


        vbox_dest = QVBoxLayout()
        lbl_dest = CustomLabel("Destinatario", variant="body")
        lbl_dest.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        self.cb_destinatario_ind = CustomComboBox(self)
        vbox_dest.addWidget(lbl_dest)
        vbox_dest.addWidget(self.cb_destinatario_ind)

        dest_layout.addLayout(vbox_tipo, stretch=1)
        dest_layout.addLayout(vbox_dest, stretch=1)
        form_layout.addLayout(dest_layout)
        
        # Interactive Grid for filters and counts
        self.grid_individual = InteractiveGrid(self)
        self.grid_individual.setMinimumHeight(180)
        self.grid_individual.set_third_column_label("Delegación")
        self.grid_individual.btn_save.setVisible(False)
        self.grid_individual.btn_cancel.setVisible(False)
        
        # Connect availability and cascade signals for individual grid
        self.grid_individual.availability_requested.connect(self._on_availability_requested_ind)
        self.grid_individual.cascade_rfcs_needed.connect(self._on_cascade_rfcs_needed)
        self.grid_individual.cascade_delegaciones_needed.connect(self._on_cascade_delegaciones_needed)
        self.grid_individual.cascade_conceptos_needed.connect(self._on_cascade_conceptos_needed)

        # Create aligned action buttons to go in the header alongside + Agregar Renglón

        self.btn_buscar_ind = CustomButton("Buscar Derechos", parent=self)
        self.btn_buscar_ind.setMinimumHeight(35)
        self.btn_buscar_ind.setIcon(Icons.get_icon("buscar", color="#FFFFFF"))
        self.btn_buscar_ind.clicked.connect(self._on_buscar_referencias_ind)

        self.btn_confirmar_ind = CustomButton("Continuar Asignación", parent=self)
        self.btn_confirmar_ind.setMinimumHeight(35)
        self.btn_confirmar_ind.setIcon(Icons.get_icon("siguiente", color="#FFFFFF"))
        self.btn_confirmar_ind.setEnabled(False)
        self.btn_confirmar_ind.clicked.connect(self._on_confirmar_asignacion_ind)

        self.btn_limpiar_ind = CustomButton("Limpiar", is_clean_btn=True)
        self.btn_limpiar_ind.clicked.connect(self._on_limpiar_ind)


        # Inject into the InteractiveGrid header layout (before stretch, so they align right next to btn_add)
        self.grid_individual.header_layout.addWidget(self.btn_buscar_ind)
        self.grid_individual.header_layout.addWidget(self.btn_confirmar_ind)
        self.grid_individual.header_layout.addWidget(self.btn_limpiar_ind)

        form_layout.addWidget(self.grid_individual)

        card_ind.layout.addLayout(form_layout)
        layout.addWidget(card_ind)

        # Preview list table
        self.card_preview_ind = CustomCard(title="Referencias Disponibles a Asignar", parent=self)
        self.table_preview_ind = StyledDataTable(["✔", "ID", "Referencia (Portal)", "Concepto", "Empresa", "Importe", "Delegación"], parent=self)
        self.table_preview_ind.setMinimumHeight(240)
        self.table_preview_ind.setColumnHidden(1, True) # Hide internal ID
        self.card_preview_ind.add_widget(self.table_preview_ind)
        layout.addWidget(self.card_preview_ind)

        scroll_area.setWidget(scroll_content)
        tab_layout.addWidget(scroll_area)

        self._pending_ind_refs = []

    def _on_limpiar_ind(self):
        """Clears individual grid rows, destination selections and preview list data."""
        self.grid_individual.clear()
        self.grid_individual.add_row()
        self.table_preview_ind.clearContents()
        self.table_preview_ind.setRowCount(0)
        self._pending_ind_refs = []
        self.btn_confirmar_ind.setEnabled(False)
        self.cb_tipo_destino_ind.setCurrentIndex(0)
        self.cb_destinatario_ind.clear()

    def _on_limpiar_apartar(self):
        """Clears the apartar grid, selected destination, and input fields."""
        self.grid_apartar.clear()
        self.grid_apartar.add_row()
        self.cb_notarias_apartar.setCurrentIndex(-1)
        self.txt_obs_apartar.clear()

    def _on_tipo_destino_ind_changed(self, text):

        self.cb_destinatario_ind.clear()
        if not text or text == "-- Seleccione Destino --":
            self.grid_individual.clear()
            self.grid_individual.set_cascade_mode(False)
            return

        if text == "NOTARIA" and hasattr(self, "_notarias_map"):
            self.cb_destinatario_ind.addItem("-- Seleccione Destinatario --", None)
            self.cb_destinatario_ind.addItems(list(self._notarias_map.keys()))
            self.cb_destinatario_ind.setCurrentIndex(0)
            # NOTARIA: Enable cascade mode (Desarrollo -> RFC -> Delegación -> Concepto)
            if hasattr(self, "_cascade_desarrollos_entries"):
                self.grid_individual.set_cascade_mode(True, self._cascade_desarrollos_entries)
        else:
            if hasattr(self, "_colaboradores_map"):
                self.cb_destinatario_ind.addItem("-- Seleccione Destinatario --", None)
                self.cb_destinatario_ind.addItems(list(self._colaboradores_map.keys()))
                self.cb_destinatario_ind.setCurrentIndex(0)

            # COLABORADOR: Disable cascade mode (independent combos, but Desarrollo remains visible and optional)
            self.grid_individual.set_cascade_mode(False)
            self.grid_individual.set_has_desarrollo(True)
            # Pre-load only RFCs that actually have 'FACTURADA' stock
            try:
                rfcs_con_stock = self.inventario_ui_service.get_rfcs_con_stock_facturadas()
                rfcs_tuples = [(r["rfc_id"], r["razon_social"]) for r in rfcs_con_stock]
                
                concepts_all_tuples = sorted(
                    [(c_id, c_name) for c_name, c_id in self._concepts_map.items()],
                    key=lambda x: x[0]
                )
                delegations_list_tuples = [
                    (dg_id, dg_name) for dg_name, dg_id in self._delegations_map.items()
                ]
                
                # Fetch desarrollos catalog for the optional combo
                desarrollos_tuples = sorted(
                    [
                        (
                            d["desarrollo_id"],
                            d["nombre"],
                            d.get("delegacion_id"),
                            d.get("es_default", False),
                        )
                        for d in self.inventario_ui_service.get_desarrollos()
                    ],
                    key=lambda x: (not x[3], x[1])
                )
                
                self.grid_individual.set_catalogs(rfcs_tuples, concepts_all_tuples, delegations_list_tuples, desarrollos_tuples)
            except Exception as e:
                print("Error loading active stock RFCs for individual grid:", e)


        # Clear and add a clean row to match the new mode
        self.grid_individual.clear()
        self.grid_individual.add_row()



    def _on_availability_requested_ind(self, row_widget):
        self._avail_pending_row = row_widget
        self._avail_timer.start()

    def _on_buscar_referencias_ind(self):
        tipo_destino = self.cb_tipo_destino_ind.currentText()
        if not tipo_destino or tipo_destino == "-- Seleccione Destino --":
            QMessageBox.warning(self, "Destino Requerido", "Debe seleccionar primero un Tipo de Destino válido.")
            return

        grid_data = self.grid_individual.get_all_data()

        if not grid_data:
            QMessageBox.warning(self, "Grilla Vacía", "Por favor, agregue al menos una partida para buscar.")
            return

        for i, row in enumerate(grid_data):
            # If in cascade mode (NOTARIA), rfc, concepto, and delegacion are required.
            # In non-cascade mode (COLABORADOR), desarrollo is hidden but rfc, concepto and delegacion are still required.
            if not row.get("rfc_id") or not row.get("concepto_id") or not row.get("delegacion_id"):
                QMessageBox.warning(self, "Validación", f"El renglón {i+1} debe tener Empresa, Concepto y Delegación seleccionados.")
                return


        self._pending_ind_refs = []
        try:
            for row in grid_data:
                refs = self.inventario_ui_service.get_referencias_disponibles_filtro(
                    row["rfc_id"], row["concepto_id"], row["delegacion_id"], row["cantidad"],
                    orden_ids=list(self.selected_orden_ids) if self.selected_orden_ids else None
                )
                for r in refs:
                    r["desarrollo_id"] = None
                    r["delegacion_id"] = row["delegacion_id"]
                    r["delegacion_nombre"] = self.grid_individual.get_delegacion_text(row["delegacion_id"]) or "Delegación"
                    self._pending_ind_refs.append(r)
            
            table_rows = []
            for item in self._pending_ind_refs:
                table_rows.append([
                    "",  # checked column
                    str(item["referencia_id"]),
                    item["referencia_portal"],
                    item.get("concepto_nombre", ""),
                    item.get("empresa_nombre", ""),
                    f"${float(item['importe']):,.2f}" if item.get("importe") else "$0.00",
                    item["delegacion_nombre"]
                ])
            
            self.table_preview_ind.blockSignals(True)
            self.table_preview_ind.populate_rows(table_rows, checkable_first_col=True)
            for r in range(self.table_preview_ind.rowCount()):
                self.table_preview_ind.item(r, 0).setCheckState(Qt.CheckState.Checked)
            self.table_preview_ind.blockSignals(False)

            self.btn_confirmar_ind.setEnabled(len(self._pending_ind_refs) > 0)
            if not self._pending_ind_refs:
                QMessageBox.information(self, "Sin Coincidencias", "No se encontraron referencias físicas FACTURADAS disponibles con los filtros especificados.")
        except Exception as e:
            QMessageBox.critical(self, "Error al Consultar", f"Ocurrió un error al buscar referencias en la BD:\n{str(e)}")

    def _on_confirmar_asignacion_ind(self):
        selected_refs = []
        for r in range(self.table_preview_ind.rowCount()):
            if self.table_preview_ind.item(r, 0).checkState() == Qt.CheckState.Checked:
                ref_id = int(self.table_preview_ind.item(r, 1).text())
                for item in self._pending_ind_refs:
                    if item["referencia_id"] == ref_id:
                        selected_refs.append(item)
                        break

        if not selected_refs:
            QMessageBox.warning(self, "Selección Vacía", "Por favor, seleccione al menos una referencia de la lista para asignar.")
            return

        tipo_destino = self.cb_tipo_destino_ind.currentText()
        if not tipo_destino or tipo_destino == "-- Seleccione Destino --":
            QMessageBox.warning(self, "Destino Requerido", "Por favor, seleccione un tipo de destino válido.")
            return

        dest_name = self.cb_destinatario_ind.currentText()
        if not dest_name or dest_name == "-- Seleccione Destinatario --":
            QMessageBox.warning(self, "Destinatario Requerido", "Por favor, seleccione un destinatario de la lista.")
            return

        if tipo_destino == "NOTARIA":
            destino_id = self._notarias_map.get(dest_name)
        elif tipo_destino == "COLABORADOR":
            destino_id = self._colaboradores_map.get(dest_name)
        else:
            destino_id = None


        if not destino_id:
            QMessageBox.warning(self, "Destino Inválido", "Por favor, seleccione un destinatario válido.")
            return

        ref_ids = [r["referencia_id"] for r in selected_refs]
        ref_portals = [r["referencia_portal"] for r in selected_refs]
        
        # Instantiate ManualAssignmentDialog to capture all details, passing selected_refs to maintain referential integrity of developments
        dialog = ManualAssignmentDialog(self.db_connector, ref_ids, ref_portals, parent=self, selected_refs=selected_refs)

        
        # Prepopulate the selected destination type and value in the dialog
        idx_dest_type = dialog.cb_destino.findText(tipo_destino)
        if idx_dest_type >= 0:
            dialog.cb_destino.setCurrentIndex(idx_dest_type)
        dialog._on_destino_changed(tipo_destino)
        
        if tipo_destino == "NOTARIA":
            idx_not = dialog.cb_notarias.findText(dest_name)
            if idx_not >= 0:
                dialog.cb_notarias.setCurrentIndex(idx_not)
        else:
            idx_col = dialog.cb_colaboradores.findText(dest_name)
            if idx_col >= 0:
                dialog.cb_colaboradores.setCurrentIndex(idx_col)

        # Execute Dialog
        if dialog.exec() == QDialog.Accepted:
            self.table_preview_ind.clearContents()
            self.table_preview_ind.setRowCount(0)
            self.grid_individual.clear()
            self.grid_individual.add_row()
            self.btn_confirmar_ind.setEnabled(False)
            self.refresh_all()

    def _load_catalogs_data(self):
        try:
            data = self.inventario_ui_service.get_catalogos_data()
            notarias = data["notarias"]
            colaboradores = data["colaboradores"]
            desarrollos = data["desarrollos"]
            concepts_list = data["conceptos"]
            delegations_list = data["delegaciones"]
            rfcs_list = data["rfcs"]
            
            self._notarias_map = {n["nombre"]: n["notaria_id"] for n in notarias}
            self._colaboradores_map = {c["nombre"]: c["colaborador_id"] for c in colaboradores}
            self._desarrollos_map = {d["nombre"]: d["desarrollo_id"] for d in desarrollos}
            self._delegations_map = {dg["nombre"] if isinstance(dg, dict) else dg.nombre: dg["delegacion_id"] if isinstance(dg, dict) else dg.delegacion_id for dg in delegations_list}
            self._concepts_map = {cp["nombre"] if isinstance(cp, dict) else cp.nombre: cp["concepto_id"] if isinstance(cp, dict) else cp.concepto_id for cp in concepts_list}
            self._rfcs_map = {r["razon_social"] if isinstance(r, dict) else r.razon_social: r["rfc_id"] if isinstance(r, dict) else r.rfc_id for r in rfcs_list}

            # Populate Notaría combos — insert explicit placeholder so no record is auto-selected
            self.cb_notarias_masivo.clear()
            self.cb_notarias_masivo.addItem("-- Seleccione una notaría --")
            self.cb_notarias_masivo.addItems(list(self._notarias_map.keys()))
            self.cb_notarias_masivo.setCurrentIndex(0)

            self.cb_notarias_apartar.clear()
            self.cb_notarias_apartar.addItem("-- Seleccione una notaría --")
            for nombre in self._notarias_map:
                self.cb_notarias_apartar.addItem(nombre)
            self.cb_notarias_apartar.setCurrentIndex(0)  # keep placeholder selected

            self.cb_colaboradores_masivo.clear()
            self.cb_colaboradores_masivo.addItem("-- Seleccione un colaborador --")
            self.cb_colaboradores_masivo.addItems(list(self._colaboradores_map.keys()))
            self.cb_colaboradores_masivo.setCurrentIndex(0)

            self.cb_empresa_masivo.clear()
            self.cb_empresa_masivo.addItem("-- Seleccione empresa --")
            self.cb_empresa_masivo.addItems(list(self._rfcs_map.keys()))
            self.cb_empresa_masivo.setCurrentIndex(0)

            current_concept_txt = self.cb_concept_filter.currentText()
            self.cb_concept_filter.clear()
            self.cb_concept_filter.addItem("Todos los conceptos")
            self.cb_concept_filter.addItems(list(self._concepts_map.keys()))
            if current_concept_txt in self._concepts_map:
                self.cb_concept_filter.setCurrentText(current_concept_txt)

            current_empresa_txt = self.cb_empresa_filter.currentText()
            self.cb_empresa_filter.clear()
            self.cb_empresa_filter.addItem("Todas las empresas")
            self.cb_empresa_filter.addItems(list(self._rfcs_map.keys()))
            if current_empresa_txt in self._rfcs_map:
                self.cb_empresa_filter.setCurrentText(current_empresa_txt)





            # Populate tables in Tab 3 — only ACTIVE delegations
            delegations_list_tuples = [
                (
                    d["delegacion_id"] if isinstance(d, dict) else d.delegacion_id,
                    d["nombre"] if isinstance(d, dict) else d.nombre
                )
                for d in delegations_list
                if (d.get("activo", True) if isinstance(d, dict) else getattr(d, "activo", True))
            ]

            # Populate grid_apartar in CASCADE MODE using desarrollos_empresa data
            desarrollos_activos_para_apartar = self.inventario_ui_service.get_desarrollos_activos_para_apartar()
            self._cascade_desarrollos_entries = desarrollos_activos_para_apartar  # cache for new rows
            self.grid_apartar.set_has_desarrollo(True)
            self.grid_apartar.set_cascade_mode(True, desarrollos_activos_para_apartar)
            if not self.grid_apartar.rows:
                self.grid_apartar.add_row()

            # Populate grid_individual by default in CASCADE MODE to match Apartar
            self.grid_individual.set_has_desarrollo(True)
            self.grid_individual.set_cascade_mode(True, desarrollos_activos_para_apartar)
            if not self.grid_individual.rows:
                self.grid_individual.add_row()


        except Exception as e:
            print("Error loading catalog data for inventory view:", e)

    def _load_filters_data(self):
        try:
            data = self.inventario_ui_service.get_filtros_data()
            concepts_list = data["conceptos"]
            rfcs_list = data["rfcs"]
            
            self._concepts_map = {cp["nombre"] if isinstance(cp, dict) else cp.nombre: cp["concepto_id"] if isinstance(cp, dict) else cp.concepto_id for cp in concepts_list}
            self._rfcs_map = {r["razon_social"] if isinstance(r, dict) else r.razon_social: r["rfc_id"] if isinstance(r, dict) else r.rfc_id for r in rfcs_list}

            # Populate filter combos in visor
            current_concept_txt = self.cb_concept_filter.currentText()
            self.cb_concept_filter.clear()
            self.cb_concept_filter.addItem("Todos los conceptos")
            self.cb_concept_filter.addItems(list(self._concepts_map.keys()))
            if current_concept_txt in self._concepts_map:
                self.cb_concept_filter.setCurrentText(current_concept_txt)

            current_empresa_txt = self.cb_empresa_filter.currentText()
            self.cb_empresa_filter.clear()
            self.cb_empresa_filter.addItem("Todas las empresas")
            self.cb_empresa_filter.addItems(list(self._rfcs_map.keys()))
            if current_empresa_txt in self._rfcs_map:
                self.cb_empresa_filter.setCurrentText(current_empresa_txt)


        except Exception as e:
            print("Error loading filter data for inventory view:", e)

    def _on_add_notaria(self):
        name = self.txt_add_notaria.text().strip()
        if not name:
            return
        try:
            self.inventario_ui_service.save_notaria(name)
            self.txt_add_notaria.clear()
            self._load_catalogs_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la notaría (podría estar duplicada):\n{str(e)}")

    def _on_add_colaborador(self):
        name = self.txt_add_colaborador.text().strip()
        if not name:
            return
        try:
            self.inventario_ui_service.save_colaborador(name)
            self.txt_add_colaborador.clear()
            self._load_catalogs_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el colaborador:\n{str(e)}")

    def _on_add_desarrollo(self):
        name = self.txt_add_desarrollo.text().strip()
        deleg_name = self.cb_deleg_desarrollo.currentText()
        deleg_id = self._delegations_map.get(deleg_name)
        
        if not name or not deleg_id:
            return
        try:
            self.inventario_ui_service.save_desarrollo(name, deleg_id)
            self.txt_add_desarrollo.clear()
            self._load_catalogs_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el desarrollo:\n{str(e)}")


    def _setup_tab_apartar(self):
        tab_layout = QVBoxLayout(self.tab_apartar)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        scroll_area = QScrollArea(self.tab_apartar)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QWidget#apartarScrollContent { background-color: transparent; }
        """)

        scroll_content = QWidget()
        scroll_content.setObjectName("apartarScrollContent")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        card_apartar = CustomCard(parent=self)
        form_layout = QVBoxLayout()
        form_layout.setSpacing(16)

        # Build custom header for the card with Filter Button
        card_header_layout = QHBoxLayout()
        card_title_vbox = QVBoxLayout()
        lbl_card_title = CustomLabel("Reserva de Derechos (Apartados)", variant="subheader")
        lbl_card_subtitle = CustomLabel("Completa los datos para reservar derechos para una notaría", variant="muted")
        card_title_vbox.addWidget(lbl_card_title)
        card_title_vbox.addWidget(lbl_card_subtitle)
        card_header_layout.addLayout(card_title_vbox)
        card_header_layout.addStretch()
        
        self.btn_filter_orden_apartar = QPushButton()
        self.btn_filter_orden_apartar.setObjectName("secondaryBtn")
        self.btn_filter_orden_apartar.setIcon(Icons.filter_icon("#475569"))
        self.btn_filter_orden_apartar.setFixedSize(36, 36)
        self.btn_filter_orden_apartar.setToolTip("Filtrar por Órdenes")
        self.btn_filter_orden_apartar.clicked.connect(self._show_order_filter_menu)
        card_header_layout.addWidget(self.btn_filter_orden_apartar)
        
        form_layout.addLayout(card_header_layout)

        # Two-column input layout: Notaria on the left, Observaciones on the right
        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(16)

        # Left side: Notaria — with explicit placeholder so no item is pre-selected
        not_layout = QVBoxLayout()
        lbl_notaria = CustomLabel("Notaría de Destino *", variant="body")
        lbl_notaria.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        self.cb_notarias_apartar = CustomComboBox(self)
        self.cb_notarias_apartar.setMinimumHeight(35)
        self.cb_notarias_apartar.setPlaceholderText("-- Seleccione una notaría --")
        not_layout.addWidget(lbl_notaria)
        not_layout.addWidget(self.cb_notarias_apartar)

        # Right side: Observaciones (obligatorio)
        obs_layout = QVBoxLayout()
        lbl_obs = CustomLabel("Observaciones del Lote *", variant="body")
        lbl_obs.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        self.txt_obs_apartar = CustomInput("Observaciones obligatorias para el apartado...")
        self.txt_obs_apartar.setMinimumHeight(35)
        obs_layout.addWidget(lbl_obs)
        obs_layout.addWidget(self.txt_obs_apartar)

        inputs_layout.addLayout(not_layout, stretch=1)
        inputs_layout.addLayout(obs_layout, stretch=1)
        form_layout.addLayout(inputs_layout)

        # Interactive Grid (cascade mode: Desarrollo → RFC → Delegación → Concepto)
        self.grid_apartar = InteractiveGrid(self)
        self.grid_apartar.set_has_desarrollo(True)
        self.grid_apartar.btn_save.setVisible(False)
        self.grid_apartar.btn_cancel.setVisible(False)
        self.grid_apartar.availability_requested.connect(self._on_availability_requested)
        # Connect cascade signals to the view's handler methods
        self.grid_apartar.cascade_rfcs_needed.connect(self._on_cascade_rfcs_needed)
        self.grid_apartar.cascade_delegaciones_needed.connect(self._on_cascade_delegaciones_needed)
        self.grid_apartar.cascade_conceptos_needed.connect(self._on_cascade_conceptos_needed)
        form_layout.addWidget(self.grid_apartar)

        # Debounce timer and pending availability worker tracking
        from PySide6.QtCore import QTimer
        self._avail_timer = QTimer(self)
        self._avail_timer.setSingleShot(True)
        self._avail_timer.setInterval(220)  # 220ms debounce
        self._avail_pending_row = None
        self._avail_timer.timeout.connect(self._launch_availability_worker)
        self._active_avail_workers = []  # track to avoid premature GC

        # Confirm and Clean Buttons at the bottom
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_limpiar_apartar = CustomButton("Limpiar", is_clean_btn=True)
        self.btn_limpiar_apartar.clicked.connect(self._on_limpiar_apartar)
        btn_layout.addWidget(self.btn_limpiar_apartar)
        self.btn_save_apartar = CustomButton("Confirmar Apartados")
        self.btn_save_apartar.clicked.connect(self._on_save_apartar)
        btn_layout.addWidget(self.btn_save_apartar)
        form_layout.addLayout(btn_layout)

        card_apartar.layout.addLayout(form_layout)
        layout.addWidget(card_apartar)
        
        scroll_area.setWidget(scroll_content)
        tab_layout.addWidget(scroll_area)
        
        # Wait, since _setup_tab_apartar is called during __init__, self._rfcs_map might not exist yet.
        # So we trigger it dynamically when the catalogs are loaded.

    def _on_availability_requested(self, row_widget):
        """Debounce handler: stores the pending row and restarts the 220ms timer."""
        self._avail_pending_row = row_widget
        self._avail_timer.start()  # resets if already running

    def _launch_availability_worker(self):
        """Fires the background worker after the debounce window closes."""
        row = self._avail_pending_row
        if row is None:
            return
        data = row.get_data()
        rfc_id = data.get("rfc_id")
        concepto_id = data.get("concepto_id")
        delegacion_id = data.get("delegacion_id")
        if not rfc_id or not concepto_id or not delegacion_id:
            return

        worker = AvailabilityWorker(
            self.inventario_ui_service, row, rfc_id, concepto_id, delegacion_id,
            orden_ids=list(self.selected_orden_ids) if self.selected_orden_ids else None
        )
        worker.result_ready.connect(self._on_availability_result)
        worker.finished.connect(lambda: self._active_avail_workers.remove(worker) if worker in self._active_avail_workers else None)
        self._active_avail_workers.append(worker)
        worker.start()

    def _on_availability_result(self, row_widget, count: int):
        """Called on the main thread when the worker returns a count.
        Dynamically updates whichever grid contains the row.
        """
        if row_widget in self.grid_apartar.rows:
            self.grid_apartar.update_row_availability(row_widget, count)
        elif row_widget in self.grid_individual.rows:
            self.grid_individual.update_row_availability(row_widget, count)


    # ── Cascade handlers ─────────────────────────────────────────────────────

    def _on_cascade_rfcs_needed(self, row_widget, desarrollo_id: int):
        """Load RFCs for the selected Desarrollo and feed them into the row."""
        try:
            rfcs = self.inventario_ui_service.get_rfcs_por_desarrollo(desarrollo_id)
            row_widget.populate_rfcs(rfcs)
        except Exception as e:
            print(f"Error cargando RFCs para desarrollo {desarrollo_id}: {e}")

    def _on_cascade_delegaciones_needed(self, row_widget, desarrollo_id: int, rfc_id: int):
        """Load Delegaciones for the selected Desarrollo+RFC and feed them into the row."""
        try:
            delegaciones = self.inventario_ui_service.get_delegaciones_por_desarrollo_rfc(desarrollo_id, rfc_id)
            row_widget.populate_delegaciones(delegaciones)
        except Exception as e:
            print(f"Error cargando Delegaciones para desarrollo {desarrollo_id}, rfc {rfc_id}: {e}")

    def _on_cascade_conceptos_needed(self, row_widget, rfc_id: int, delegacion_id: int):
        """Load Conceptos for the selected RFC+Delegación and feed them into the row."""
        try:
            if row_widget in self.grid_individual.rows:
                # No restriction on concepts for Asignación Individual Directa: Load all active concepts
                conceptos_all_tuples = sorted(
                    [{"concepto_id": c_id, "nombre": c_name} for c_name, c_id in self._concepts_map.items()],
                    key=lambda x: x["concepto_id"]
                )
                row_widget.populate_conceptos(conceptos_all_tuples)
            else:
                # Keep stock restriction for Apartar tab
                conceptos = self.inventario_ui_service.get_conceptos_con_stock(rfc_id, delegacion_id)
                row_widget.populate_conceptos(conceptos)
        except Exception as e:
            print(f"Error cargando Conceptos para rfc {rfc_id}, delegacion {delegacion_id}: {e}")


    def _on_save_apartar(self):
        # --- Validación 1: Notaría seleccionada ---
        not_name = self.cb_notarias_apartar.currentText()
        notaria_id = self._notarias_map.get(not_name)
        if not notaria_id:
            QMessageBox.warning(self, "Notaría Faltante", "Por favor, seleccione una Notaría de destino válida.")
            return

        # --- Validación 2: Observaciones obligatorias ---
        obs_text = self.txt_obs_apartar.text().strip()
        if not obs_text:
            QMessageBox.warning(self, "Observaciones Requeridas",
                                "Las observaciones del lote son obligatorias.\n"
                                "Por favor describe el motivo o referencia del apartado.")
            self.txt_obs_apartar.setFocus()
            return
            
        data = self.grid_apartar.get_all_data()
        if not data:
            QMessageBox.warning(self, "Validación", "Debes agregar al menos un renglón para realizar un apartado.")
            return

        # --- Validaciones por renglón ---
        CONCEPTO_AVISO_ID = 2
        CONCEPTO_CLG_ID = 3
        seen_combinations = set()
        rows_data = []
        for i, row in enumerate(data):
            n = i + 1
            if not row["rfc_id"] or not row["concepto_id"] or not row["delegacion_id"]:
                QMessageBox.warning(self, "Validación", f"El renglón {n} debe tener Empresa, Concepto y Delegación seleccionados.")
                return
            if row["concepto_id"] not in (CONCEPTO_AVISO_ID, CONCEPTO_CLG_ID):
                QMessageBox.warning(self, "Validación",
                                    f"El renglón {n} tiene un concepto no permitido.\n"
                                    f"Solo se permiten: Aviso Preventivo (2) y CLG (3).")
                return

            # --- Validación 3: No duplicados ---
            key = (row["rfc_id"], row["concepto_id"], row["delegacion_id"], row.get("desarrollo_id"))
            if key in seen_combinations:
                QMessageBox.warning(self, "Renglón Duplicado",
                                    f"El renglón {n} es duplicado.\n"
                                    f"Ya existe un renglón con la misma Empresa, Concepto, Delegación y Desarrollo.")
                return
            seen_combinations.add(key)

            # --- Validación 4: Cantidad no puede superar disponibles ---
            disp_count = row.get("_disponibles", None)
            # Fetch from the row widget directly for precision
            for row_widget in self.grid_apartar.rows:
                wd = row_widget.get_data()
                if (wd["rfc_id"] == row["rfc_id"] and
                        wd["concepto_id"] == row["concepto_id"] and
                        wd["delegacion_id"] == row["delegacion_id"]):
                    disp_text = row_widget.lbl_disponibles.text()
                    # Parse count from label (e.g. "✓ 15", "⚠ 3", "✗ 0")
                    try:
                        disp_count = int(disp_text.split()[-1])
                    except (ValueError, IndexError):
                        disp_count = None
                    break

            if disp_count is not None and row["cantidad"] > disp_count:
                rfc_name = self.grid_apartar.get_rfc_text(row["rfc_id"]) or f"RFC {row['rfc_id']}"
                concepto_name = self.grid_apartar.get_concepto_text(row["concepto_id"]) or f"Concepto {row['concepto_id']}"
                QMessageBox.warning(
                    self, "Cantidad Excede Disponibles",
                    f"Renglón {n} — {rfc_name} / {concepto_name}:\n"
                    f"La cantidad solicitada ({row['cantidad']}) supera las referencias disponibles ({disp_count}).\n"
                    f"Reduzca la cantidad o verifique los filtros."
                )
                return

            rows_data.append({
                "rfc_id": row["rfc_id"],
                "concepto_id": row["concepto_id"],
                "delegacion_id": row["delegacion_id"],
                "desarrollo_id": row.get("desarrollo_id"),
                "cantidad": row["cantidad"]
            })

        # --- Regla de negocio: cada (empresa, delegación/desarrollo) debe tener AVISO y CLG ---
        pair_concepts: dict = {}  # (rfc_id, desarrollo_id or delegacion_id) -> set of concepto_ids
        for r in rows_data:
            pair_key = (r["rfc_id"], r["desarrollo_id"] if r["desarrollo_id"] else r["delegacion_id"])
            pair_concepts.setdefault(pair_key, set()).add(r["concepto_id"])

        missing_pairs = []
        for (rfc_id, target_id), concepts_set in pair_concepts.items():
            missing = []
            if CONCEPTO_AVISO_ID not in concepts_set:
                missing.append("Aviso Preventivo")
            if CONCEPTO_CLG_ID not in concepts_set:
                missing.append("CLG")
            if missing:
                rfc_name = self.grid_apartar.get_rfc_text(rfc_id) or f"RFC {rfc_id}"
                des_name = None
                has_desarrollo_id = any(
                    r["rfc_id"] == rfc_id and r["desarrollo_id"] == target_id
                    for r in rows_data
                )
                if has_desarrollo_id:
                    des_name = self.grid_apartar.get_desarrollo_text(target_id)
                if not des_name:
                    des_name = self.grid_apartar.get_delegacion_text(target_id) or f"Delegación/Desarrollo {target_id}"
                missing_pairs.append(f"• {rfc_name} / {des_name}: falta(n) {', '.join(missing)}")

        if missing_pairs:
            detail = "\n".join(missing_pairs)
            QMessageBox.warning(
                self, "Regla de Negocio",
                f"Cada combinación de Empresa + Delegación/Desarrollo debe tener un renglón de "
                f"Aviso Preventivo y uno de CLG.\n\nFaltan:\n{detail}"
            )
            return

        # --- Diálogo de confirmación con resumen detallado ---
        total_refs = sum(r["cantidad"] for r in rows_data)
        resumen_lineas = []
        for r in rows_data:
            rfc_name = self.grid_apartar.get_rfc_text(r["rfc_id"]) or f"RFC {r['rfc_id']}"
            concepto_name = self.grid_apartar.get_concepto_text(r["concepto_id"]) or f"Concepto {r['concepto_id']}"
            deleg_name = self.grid_apartar.get_delegacion_text(r["delegacion_id"]) or f"Deleg. {r['delegacion_id']}"
            des_name = ""
            if r["desarrollo_id"]:
                des_name = self.grid_apartar.get_desarrollo_text(r["desarrollo_id"]) or ""
                des_name = f" / {des_name}" if des_name else ""
            resumen_lineas.append(
                f"  • {rfc_name} | {concepto_name} | {deleg_name}{des_name} → {r['cantidad']} ref(s)"
            )
        resumen_texto = "\n".join(resumen_lineas)

        confirm_msg = (
            f"¿Confirmar el apartado de {total_refs} referencias para la notaría '{not_name}'?\n\n"
            f"Resumen de partidas:\n{resumen_texto}\n\n"
            f"Observaciones: {obs_text}\n\n"
            f"Esta operación reservará las referencias en estado RESERVADA y no podrá deshacerse fácilmente."
        )
        reply = QMessageBox.question(
            self, "Confirmar Apartado",
            confirm_msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # --- Ejecución del apartado ---
        try:
            parent_window = self.window()
            usuario_id = getattr(parent_window, "current_usuario_id", 1)
            
            if self.api_client.connect_via_api:
                for row_d in rows_data:
                    payload = {
                        "notaria_id": notaria_id,
                        "rfc_id": row_d["rfc_id"],
                        "concepto_id": row_d["concepto_id"],
                        "delegacion_id": row_d["delegacion_id"],
                        "desarrollo_id": row_d["desarrollo_id"],
                        "cantidad": row_d["cantidad"],
                        "usuario_creacion": usuario_id,
                        "observaciones": obs_text,
                        "orden_ids": list(self.selected_orden_ids) if self.selected_orden_ids else None
                    }
                    self.api_client.request("POST", "/api/docs/inventario/lotes/apartar", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    from sar.src.storage.repositories import InventarioRepository
                    repo = InventarioRepository(session)
                    repo.apartar_referencias_lote(
                        notaria_id=notaria_id,
                        usuario_id=usuario_id,
                        partidas=rows_data,
                        observaciones=obs_text,
                        orden_ids=list(self.selected_orden_ids) if self.selected_orden_ids else None
                    )
                    session.commit()
                    
            QMessageBox.information(
                self, "Apartado Exitoso",
                f"Se han reservado exitosamente {total_refs} referencias en total en estado RESERVADA."
            )
            
            # Reset tabla, observaciones y recargar visor
            self.txt_obs_apartar.clear()
            self.grid_apartar.clear()
            self.grid_apartar.add_row()
            self.cb_notarias_apartar.setCurrentIndex(0)  # Restablecer placeholder
            self.refresh_visor_data()
        except Exception as e:
            QMessageBox.critical(self, "Error al Reservar", f"No se pudo completar el apartado de referencias:\n{str(e)}")

    def _on_apartar_referencias(self):
        # We also want to adapt ApartarReferenciasDialog to use InteractiveGrid
        dialog = ApartarReferenciasDialog(self.db_connector, self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_visor_data()

    # =========================================================================
    # TAB 5: GESTIÓN DE ASIGNACIONES
    # =========================================================================
    def _setup_tab_lotes(self):
        """Sets up the Gestión de Asignaciones tab — shows assignment summary rows."""
        tab_layout = QVBoxLayout(self.tab_lotes)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        scroll_area = QScrollArea(self.tab_lotes)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QWidget#lotesScrollContent { background-color: transparent; }
        """)

        scroll_content = QWidget()
        scroll_content.setObjectName("lotesScrollContent")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # --- Header area ---
        header_layout = QHBoxLayout()
        title_lbl = CustomLabel("📋 Gestión de Asignaciones", variant="subheader")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # --- Filter bar ---
        filter_bar_frame = QFrame(self)
        filter_bar_frame.setObjectName("filterBarFrame")
        filter_row = QHBoxLayout(filter_bar_frame)
        filter_row.setContentsMargins(16, 12, 16, 12)
        filter_row.setSpacing(12)

        # 1. Search Input
        self.search_lotes = QLineEdit()
        self.search_lotes.setObjectName("filterBarSearch")
        self.search_lotes.setPlaceholderText("🔍 Buscar por ID, notaría, colaborador, solicitante...")
        self.search_lotes.setFixedHeight(35)
        self.search_lotes.textChanged.connect(self._on_search_lotes)
        filter_row.addWidget(self.search_lotes, stretch=1, alignment=Qt.AlignmentFlag.AlignBottom)

        # 2. Tipo Destino
        self.labeled_destino_lotes = LabeledComboBox("Tipo Destino", ["Todos", "NOTARIA", "COLABORADOR"])
        self.cb_destino_filter_lotes = self.labeled_destino_lotes.combo
        self.cb_destino_filter_lotes.currentTextChanged.connect(self._on_destino_filter_lotes)
        filter_row.addWidget(self.labeled_destino_lotes, alignment=Qt.AlignmentFlag.AlignBottom)

        # 3. Date Filters (Atomic Design Molecules)
        self.group_start_date = LabeledDateEdit("Desde", parent=self)
        self.start_date_filter = self.group_start_date.date_edit
        self.group_start_date.setDate(QDate.currentDate().addMonths(-3))
        self.start_date_filter.dateChanged.connect(self._on_date_changed_lotes)
        filter_row.addWidget(self.group_start_date, alignment=Qt.AlignmentFlag.AlignBottom)

        self.group_end_date = LabeledDateEdit("Hasta", parent=self)
        self.end_date_filter = self.group_end_date.date_edit
        self.group_end_date.setDate(QDate.currentDate())
        self.end_date_filter.dateChanged.connect(self._on_date_changed_lotes)
        filter_row.addWidget(self.group_end_date, alignment=Qt.AlignmentFlag.AlignBottom)

        # 4. Refresh button
        self.btn_refresh_lotes = QPushButton(self)
        self.btn_refresh_lotes.setObjectName("filterBarActionBtn")
        self.btn_refresh_lotes.setIcon(Icons.actualizar("#FFFFFF"))
        self.btn_refresh_lotes.setIconSize(QSize(20, 20))
        self.btn_refresh_lotes.setFixedSize(35, 35)
        self.btn_refresh_lotes.setToolTip("Actualizar Asignaciones")
        self.btn_refresh_lotes.clicked.connect(self.refresh_lotes_data)
        filter_row.addWidget(self.btn_refresh_lotes, alignment=Qt.AlignmentFlag.AlignBottom)

        # 5. Filter Button (Funnel) for Lotes
        self.btn_filter_orden_lotes = QPushButton()
        self.btn_filter_orden_lotes.setObjectName("secondaryBtn")
        self.btn_filter_orden_lotes.setIcon(Icons.filter_icon("#475569"))
        self.btn_filter_orden_lotes.setFixedSize(35, 35)
        self.btn_filter_orden_lotes.setToolTip("Filtrar por Órdenes")
        self.btn_filter_orden_lotes.clicked.connect(self._show_order_filter_menu)
        filter_row.addWidget(self.btn_filter_orden_lotes, alignment=Qt.AlignmentFlag.AlignBottom)

        layout.addWidget(filter_bar_frame)

        # --- Main Card & Table ---
        self.card_lotes = CustomCard(title="Registro de Asignaciones", parent=self)

        headers = ["ID", "Tipo Destino", "Asignado A", "Solicitante", "Fecha", "Total Refs", "Creado Por", "Observaciones"]
        self.table_lotes = StyledDataTable(headers, parent=self)
        self.table_lotes.setMinimumHeight(350)
        self.table_lotes.setMinimumWidth(200)
        self.card_lotes.add_widget(self.table_lotes)

        # Pagination footer
        footer_layout = QHBoxLayout()
        self.lbl_pagination_info_lotes = CustomLabel("0 asignaciones encontradas", variant="muted")
        footer_layout.addWidget(self.lbl_pagination_info_lotes)
        footer_layout.addStretch()

        self.cb_page_size_lotes = CustomComboBox(self)
        self.cb_page_size_lotes.addItems(["50 por página", "100 por página", "200 por página"])
        self.cb_page_size_lotes.setCurrentIndex(0)
        self.cb_page_size_lotes.currentTextChanged.connect(self._on_page_size_changed_lotes)
        footer_layout.addWidget(self.cb_page_size_lotes)

        self.pagination_widget_lotes = QWidget(self)
        self.pag_btn_layout_lotes = QHBoxLayout(self.pagination_widget_lotes)
        self.pag_btn_layout_lotes.setContentsMargins(0, 0, 0, 0)
        footer_layout.addWidget(self.pagination_widget_lotes)
        self.card_lotes.layout.addLayout(footer_layout)

        # Action buttons
        actions_layout = QHBoxLayout()
        self.btn_exportar_reporte_lotes = CustomButton("📊 Exportar Asignación Seleccionada", is_secondary=True)
        self.btn_exportar_reporte_lotes.clicked.connect(self._on_exportar_lote_seleccionado)
        self.btn_ver_detalles_lote = CustomButton("🔍 Ver Detalle", is_secondary=True)
        self.btn_ver_detalles_lote.clicked.connect(self._on_ver_detalle_lote)
        actions_layout.addStretch()
        actions_layout.addWidget(self.btn_exportar_reporte_lotes)
        actions_layout.addWidget(self.btn_ver_detalles_lote)
        self.card_lotes.layout.addLayout(actions_layout)
        layout.addWidget(self.card_lotes)

        # Hint label
        hint = CustomLabel("💡 Doble clic sobre una asignación para ver sus referencias.", variant="muted")
        layout.addWidget(hint)

        scroll_area.setWidget(scroll_content)
        tab_layout.addWidget(scroll_area)


        # State
        self.current_page_lotes = 1
        self.page_size_lotes = 50
        self.all_lotes_data = []  # List of dicts from get_lotes_asignacion_filtered
        self.total_lotes = 0
        self._current_search_text_lotes = ""
        self._current_tipo_destino_lotes = "Todos"
        self._current_rfc_id_lotes = None

        self.table_lotes.cellDoubleClicked.connect(self._on_table_cell_double_clicked_lotes)


    def refresh_lotes_data(self):
        """Loads assignments from service with active filters and populates the table."""
        if not hasattr(self, 'table_lotes'):
            return
        self.lbl_pagination_info_lotes.setText("Cargando asignaciones...")
        self.pagination_widget_lotes.setEnabled(False)

        tipo_destino = self._current_tipo_destino_lotes if self._current_tipo_destino_lotes != "Todos" else None
        search = self._current_search_text_lotes or None
        
        start_date = self.start_date_filter.date().toString("yyyy-MM-dd")
        end_date = self.end_date_filter.date().toString("yyyy-MM-dd")
        
        offset = (self.current_page_lotes - 1) * self.page_size_lotes

        try:
            lotes, total = self.inventario_ui_service.get_lotes_asignacion_filtered(
                search=search,
                tipo_destino=tipo_destino,
                limit=self.page_size_lotes,
                offset=offset,
                start_date=start_date,
                end_date=end_date,
                orden_ids=list(self.selected_orden_ids) if self.selected_orden_ids else None
            )
            self.all_lotes_data = lotes
            self.total_lotes = total
            self._populate_lotes_table()
        except Exception as e:
            self.lbl_pagination_info_lotes.setText(f"Error al cargar asignaciones: {e}")
            print("[GestionAsignaciones] Error:", e)


    def _populate_lotes_table(self):
        """Populates the lotes table from self.all_lotes_data without the Empresa column."""
        self.table_lotes.setRowCount(0)
        rows = []
        for l in self.all_lotes_data:
            rows.append([
                str(l["lote_asignacion_id"]),
                l["tipo_destino"],
                l["asignado_a"],
                l.get("solicitante_externo", ""),
                l["fecha"],
                str(l["total_referencias"]),
                l.get("creador", ""),
                l.get("observaciones", "")
            ])
        self.table_lotes.populate_rows(rows)

        total_pages = max(1, -(-self.total_lotes // self.page_size_lotes))
        start = (self.current_page_lotes - 1) * self.page_size_lotes + 1 if self.total_lotes > 0 else 0
        end = min(self.current_page_lotes * self.page_size_lotes, self.total_lotes)
        self.lbl_pagination_info_lotes.setText(
            f"Mostrando {start}–{end} de {self.total_lotes} asignaciones"
        )
        self.pagination_widget_lotes.setEnabled(True)

        # Rebuild pagination buttons
        while self.pag_btn_layout_lotes.count():
            item = self.pag_btn_layout_lotes.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        def add_page_btn(text, target, enabled, is_active=False):
            btn = QPushButton(text)
            btn.setEnabled(enabled)
            if is_active:
                btn.setObjectName("paginationActivePageBtn")
            elif text in ("<<", "<", ">", ">>"):
                btn.setObjectName("paginationNavBtn")
            else:
                btn.setObjectName("paginationPageBtn")
            btn.clicked.connect(lambda: self._set_page_lotes(target))
            self.pag_btn_layout_lotes.addWidget(btn)

        add_page_btn("<<", 1, self.current_page_lotes > 1)
        add_page_btn("<", self.current_page_lotes - 1, self.current_page_lotes > 1)
        add_page_btn(str(self.current_page_lotes), self.current_page_lotes, True, is_active=True)
        add_page_btn(">", self.current_page_lotes + 1, self.current_page_lotes < total_pages)
        add_page_btn(">>", total_pages, self.current_page_lotes < total_pages)


    def _set_page_lotes(self, page):
        self.current_page_lotes = page
        self.refresh_lotes_data()

    def _on_search_lotes(self, text):
        self._current_search_text_lotes = text
        self.current_page_lotes = 1
        self.refresh_lotes_data()

    def _on_destino_filter_lotes(self, text):
        self._current_tipo_destino_lotes = text
        self.current_page_lotes = 1
        self.refresh_lotes_data()

    def _on_date_changed_lotes(self, qdate):
        self.current_page_lotes = 1
        self.refresh_lotes_data()

    def _on_page_size_changed_lotes(self, text):
        if "50" in text: self.page_size_lotes = 50
        elif "100" in text: self.page_size_lotes = 100
        else: self.page_size_lotes = 200
        self.current_page_lotes = 1
        self.refresh_lotes_data()

    def _on_table_cell_double_clicked_lotes(self, row, column):
        """Open LoteProcessingDialog on double-click."""
        if not self.all_lotes_data or row >= len(self.all_lotes_data):
            return
        lote = self.all_lotes_data[row]
        lote_id = lote.get("lote_asignacion_id")
        if lote_id:
            dialog = LoteProcessingDialog(self.db_connector, lote_id, self)
            dialog.exec()

    def _on_ver_detalle_lote(self):
        """Open detail dialog for the currently selected lote row."""
        selected = self.table_lotes.selectedItems()
        if not selected:
            QMessageBox.information(self, "Selección", "Selecciona una asignación de la tabla primero.")
            return
        row = selected[0].row()
        self._on_table_cell_double_clicked_lotes(row, 0)

    def _on_exportar_lote_seleccionado(self):
        """Export the selected lote to Excel via ExportLotesDialog pre-filtered."""
        selected = self.table_lotes.selectedItems()
        if not selected:
            QMessageBox.information(self, "Selección", "Selecciona una asignación de la tabla primero.")
            return
        row = selected[0].row()
        if not self.all_lotes_data or row >= len(self.all_lotes_data):
            return
        lote = self.all_lotes_data[row]
        lote_id = lote.get("lote_asignacion_id")
        dest_name = lote.get("asignado_a", "")
        req_name = lote.get("solicitante_externo", "")
        date_str = lote.get("fecha", "")

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Reporte de Asignación",
            f"Control_Inventario_Lote_{lote_id}.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return
        try:
            details = self.inventario_ui_service.get_lote_detalles(lote_id)
            title = "ENTREGA DE DERECHOS"
            subtitle = f"DESTINO: {dest_name.upper()} {f'({req_name.upper()})' if req_name else ''}"
            date_range = date_str.split()[0] if date_str else ""
            ExcelInventoryHandler.generate_excel_inventory_file(
                dest_path=file_path,
                title=title,
                subtitle=subtitle,
                date_range=date_range,
                data_rows=details
            )
            QMessageBox.information(self, "Exportación Completada", f"Archivo generado en:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error de Exportación", f"No se pudo generar el archivo:\n{str(e)}")


# =============================================================================
# DIALOGS
# =============================================================================
class ManualAssignmentDialog(QDialog):
    """Dialog to perform individual or bulk manual reference assignments with a sequential wizard/paginator, per-reference drafting, and dynamic layout."""
    
    def __init__(self, db_connector, ref_ids, ref_portals, parent=None, selected_refs=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.ref_ids = ref_ids
        self.ref_portals = ref_portals or []
        self.selected_refs = selected_refs or []
        self.inventario_ui_service = InventarioUIService(self.db_connector)

        self.total_refs = len(self.ref_ids)
        self.current_idx = 0
        self._is_autocompleting = False

        self._notarias_map = {}
        self._colaboradores_map = {}
        self._desarrollos_map = {}
        self._desarrollos_list = []

        # Initialize per-reference drafts
        self._derechos_data = []
        for i in range(self.total_refs):
            r = self.selected_refs[i] if i < len(self.selected_refs) else {}
            self._derechos_data.append({
                "referencia_id": self.ref_ids[i],
                "referencia_portal": self.ref_portals[i] if i < len(self.ref_portals) else (r.get("referencia_portal", "") or ""),
                "ref_meta": r,
                "tipo_destino": None,
                "notaria_id": None,
                "notaria_name": "",
                "colaborador_id": None,
                "colaborador_name": "",
                "solicitante_externo": "",
                "cliente": str(r.get("cliente", "") or ""),
                "desarrollo_id": r.get("desarrollo_id"),
                "desarrollo_name": str(r.get("desarrollo", "") or ""),
                "sm": str(r.get("sm", "") or ""),
                "mz": str(r.get("mz", "") or ""),
                "lote": str(r.get("lote", "") or ""),
                "edif": str(r.get("edif", "") or ""),
                "viv": str(r.get("viv", "") or ""),
                "folio_electronico": str(r.get("folio_electronico", "") or ""),
                "credito_titular": str(r.get("credito_titular", "") or ""),
                "pa": str(r.get("pa", "") or ""),
                "fecha_sol": datetime.now().strftime("%Y-%m-%d"),
                "fecha_ingreso_rpp": "",
                "fecha_reporte_notaria": "",
                "fecha_escritura": "",
                "fecha_titulacion": "",
                "estatus_aviso": "NUEVO INGRESO",
                "observaciones": "",
                "comentarios": ""
            })

        # Obtenemos tokens dinámicos del Design System según el tema activo
        is_dark = ThemeManager.is_dark_active()
        bg_card = Colors.SURFACE_DARK if is_dark else Colors.SURFACE_LIGHT
        bg_sub = Colors.BG_DARK if is_dark else "#F8FAFC"
        nav_bg = Colors.SURFACE_DARK if is_dark else "#F1F5F9"
        nav_border = Colors.BORDER_DARK if is_dark else "#CBD5E1"
        border_color = Colors.BORDER_DARK if is_dark else "#E2E8F0"
        text_primary = Colors.TEXT_DARK_PRIMARY if is_dark else Colors.TEXT_LIGHT_PRIMARY
        text_secondary = Colors.TEXT_DARK_SECONDARY if is_dark else Colors.TEXT_LIGHT_SECONDARY
        text_muted = Colors.TEXT_DARK_MUTED if is_dark else Colors.TEXT_LIGHT_MUTED
        accent_color = "#60A5FA" if is_dark else "#1D4ED8"
        success_color = Colors.SUCCESS_DARK_TEXT if is_dark else Colors.SUCCESS

        self.setWindowTitle("Asignar Derechos")
        self.setMinimumWidth(540)
        
        main_vlayout = QVBoxLayout(self)
        main_vlayout.setContentsMargins(16, 14, 16, 14)
        main_vlayout.setSpacing(10)

        # Header Info Banner con formato dinámico según el tema
        self.lbl_info = QLabel("", self)
        self.lbl_info.setStyleSheet("padding: 4px 0px;")
        main_vlayout.addWidget(self.lbl_info)

        # -------------------------------------------------------------
        # Barra de Navegación Secuencial (Wizard / Paginador)
        # -------------------------------------------------------------
        self.nav_container = QFrame(self)
        self.nav_container.setObjectName("nav_bar")
        self.nav_container.setStyleSheet(f"QFrame#nav_bar {{ background-color: {nav_bg}; border: 1px solid {nav_border}; border-radius: 6px; padding: 4px 8px; }}")
        nav_lay = QHBoxLayout(self.nav_container)
        nav_lay.setContentsMargins(4, 2, 4, 2)
        nav_lay.setSpacing(10)
        
        self.btn_prev = CustomButton("◀ Anterior", is_secondary=True)
        self.btn_prev.setMaximumWidth(110)
        self.btn_prev.clicked.connect(self._on_prev)
        
        self.lbl_step = QLabel(f"Derecho 1 de {self.total_refs}", self.nav_container)
        self.lbl_step.setAlignment(Qt.AlignCenter)
        self.lbl_step.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_primary};")
        
        self.btn_next = CustomButton("Siguiente ▶", is_secondary=False)
        self.btn_next.setMaximumWidth(110)
        self.btn_next.clicked.connect(self._on_next)
        
        nav_lay.addWidget(self.btn_prev)
        nav_lay.addStretch()
        nav_lay.addWidget(self.lbl_step)
        nav_lay.addStretch()
        nav_lay.addWidget(self.btn_next)
        
        main_vlayout.addWidget(self.nav_container)

        # Replicate checkbox con componente atómico CustomCheckBox
        self.chk_replicar = CustomCheckBox("Aplicar mismos datos / observaciones a los siguientes derechos", self)
        self.chk_replicar.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {text_secondary}; margin-bottom: 2px;")
        main_vlayout.addWidget(self.chk_replicar)
        
        if self.total_refs <= 1:
            self.nav_container.hide()
            self.chk_replicar.hide()

        # -------------------------------------------------------------
        # 1. Selector de Tipo de Destino
        # -------------------------------------------------------------
        dest_form = QFormLayout()
        dest_form.setContentsMargins(0, 0, 0, 4)
        dest_form.setSpacing(8)
        
        self.cb_destino = CustomComboBox(self)
        self.cb_destino.addItems(["-- Seleccione Tipo Destino --", "NOTARIA", "COLABORADOR"])
        self.cb_destino.setCurrentIndex(0)
        self.cb_destino.currentTextChanged.connect(self._on_destino_changed)
        dest_form.addRow("Tipo Destino:", self.cb_destino)
        main_vlayout.addLayout(dest_form)

        # -------------------------------------------------------------
        # 2. CONTENEDOR: MODO COLABORADOR
        # -------------------------------------------------------------
        self.container_colaborador = QFrame(self)
        self.container_colaborador.setObjectName("card_colab")
        self.container_colaborador.setStyleSheet(f"QFrame#card_colab {{ background-color: {bg_sub}; border: 1px solid {border_color}; border-radius: 8px; padding: 8px; }}")
        colab_vlayout = QVBoxLayout(self.container_colaborador)
        colab_vlayout.setContentsMargins(8, 8, 8, 8)
        colab_vlayout.setSpacing(8)

        lbl_colab_title = CustomLabel("👤 ASIGNACIÓN A COLABORADOR (TRÁMITES EXTERNOS)", variant="subheader")
        lbl_colab_title.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {text_secondary};")
        colab_vlayout.addWidget(lbl_colab_title)

        form_colab = QFormLayout()
        form_colab.setSpacing(8)

        self.cb_colaboradores = CustomComboBox(self.container_colaborador)
        form_colab.addRow("Colaborador:", self.cb_colaboradores)

        self.txt_fecha_sol_colab = CustomInput("AAAA-MM-DD", parent=self.container_colaborador)
        self.txt_fecha_sol_colab.setText(datetime.now().strftime("%Y-%m-%d"))
        form_colab.addRow("Fecha Asignación:", self.txt_fecha_sol_colab)

        self.txt_obs_colab = QTextEdit(self.container_colaborador)
        self.txt_obs_colab.setMaximumHeight(90)
        self.txt_obs_colab.setPlaceholderText("Describa el uso exclusivo para trámites externos...")
        self.txt_obs_colab.setStyleSheet(f"background-color: {bg_card}; color: {text_primary}; border: 1px solid {border_color}; border-radius: 4px; padding: 4px;")
        form_colab.addRow("Observaciones *:", self.txt_obs_colab)

        colab_vlayout.addLayout(form_colab)
        main_vlayout.addWidget(self.container_colaborador)

        # -------------------------------------------------------------
        # 3. CONTENEDOR: MODO NOTARIA
        # -------------------------------------------------------------
        self.container_notaria = QFrame(self)
        self.container_notaria.setObjectName("card_notaria")
        self.container_notaria.setStyleSheet(f"QFrame#card_notaria {{ background-color: {bg_card}; border: 1px solid {border_color}; border-radius: 8px; padding: 6px; }}")
        notaria_vlayout = QVBoxLayout(self.container_notaria)
        notaria_vlayout.setContentsMargins(6, 6, 6, 6)
        notaria_vlayout.setSpacing(8)

        # Subsección A: Notaría y Solicitante
        form_notaria_top = QFormLayout()
        form_notaria_top.setSpacing(6)
        
        self.cb_notarias = CustomComboBox(self.container_notaria)
        form_notaria_top.addRow("Notaría *:", self.cb_notarias)

        self.txt_solicitante = CustomInput("Nombre de la persona que solicita", parent=self.container_notaria)
        form_notaria_top.addRow("Solicitante Externo:", self.txt_solicitante)
        notaria_vlayout.addLayout(form_notaria_top)

        # Subsección B: Ubicación del Inmueble
        lbl_sec_ubi = CustomLabel("🏠 UBICACIÓN DEL INMUEBLE", variant="subheader")
        lbl_sec_ubi.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {text_primary}; margin-top: 4px;")
        notaria_vlayout.addWidget(lbl_sec_ubi)

        form_ubi = QFormLayout()
        form_ubi.setSpacing(6)

        self.cb_desarrollo = CustomComboBox(self.container_notaria)
        form_ubi.addRow("Desarrollo:", self.cb_desarrollo)

        # Coordenadas: SM, Mz, Lt, Edif, Viv con CustomInput
        self.txt_sm = CustomInput("SM", parent=self.container_notaria)
        self.txt_mz = CustomInput("Mz", parent=self.container_notaria)
        self.txt_lote = CustomInput("Lt", parent=self.container_notaria)
        self.txt_edif = CustomInput("Edif", parent=self.container_notaria)
        self.txt_viv = CustomInput("Viv", parent=self.container_notaria)

        coords_lay = QHBoxLayout()
        coords_lay.setSpacing(4)
        coords_lay.addWidget(QLabel("SM:"))
        coords_lay.addWidget(self.txt_sm)
        coords_lay.addWidget(QLabel("Mz:"))
        coords_lay.addWidget(self.txt_mz)
        coords_lay.addWidget(QLabel("Lt:"))
        coords_lay.addWidget(self.txt_lote)
        coords_lay.addWidget(QLabel("Edif:"))
        coords_lay.addWidget(self.txt_edif)
        coords_lay.addWidget(QLabel("Viv:"))
        coords_lay.addWidget(self.txt_viv)
        form_ubi.addRow("Coordenadas:", coords_lay)

        # Ubicación existing match indicator
        self.lbl_ubi_match = QLabel("", self.container_notaria)
        self.lbl_ubi_match.setStyleSheet(f"color: {success_color}; font-size: 11px; font-weight: bold;")
        form_ubi.addRow("", self.lbl_ubi_match)

        self.txt_folio = CustomInput("Folio electrónico o número oficial", parent=self.container_notaria)
        form_ubi.addRow("Folio Electrónico:", self.txt_folio)
        notaria_vlayout.addLayout(form_ubi)

        # Subsección C: Datos del Cliente y Crédito
        lbl_sec_cli = CustomLabel("👤 CLIENTE Y CRÉDITO", variant="subheader")
        lbl_sec_cli.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {text_primary}; margin-top: 4px;")
        notaria_vlayout.addWidget(lbl_sec_cli)

        form_cli = QFormLayout()
        form_cli.setSpacing(6)

        self.txt_cliente = CustomInput("Nombre completo del cliente", parent=self.container_notaria)
        form_cli.addRow("Cliente *:", self.txt_cliente)

        fin_lay = QHBoxLayout()
        fin_lay.setSpacing(6)
        self.txt_credito = CustomInput("No. de crédito titular", parent=self.container_notaria)
        self.txt_pa = CustomInput("PA / Paquete", parent=self.container_notaria)
        fin_lay.addWidget(self.txt_credito, 2)
        fin_lay.addWidget(QLabel("PA:"))
        fin_lay.addWidget(self.txt_pa, 1)
        form_cli.addRow("Crédito / PA:", fin_lay)
        notaria_vlayout.addLayout(form_cli)

        # Subsección D: Seguimiento y Fechas Notariales / RPP
        lbl_sec_fechas = CustomLabel("📅 SEGUIMIENTO Y FECHAS NOTARIALES / RPP", variant="subheader")
        lbl_sec_fechas.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {text_primary}; margin-top: 4px;")
        notaria_vlayout.addWidget(lbl_sec_fechas)

        form_fechas = QFormLayout()
        form_fechas.setSpacing(6)

        # Fila 1 Fechas: Solicitud e Ingreso RPP
        f1_lay = QHBoxLayout()
        f1_lay.setSpacing(6)
        self.txt_fecha_sol = CustomInput("AAAA-MM-DD", parent=self.container_notaria)
        self.txt_fecha_sol.setText(datetime.now().strftime("%Y-%m-%d"))
        self.txt_fecha_ingreso_rpp = CustomInput("AAAA-MM-DD", parent=self.container_notaria)
        f1_lay.addWidget(self.txt_fecha_sol)
        f1_lay.addWidget(QLabel("F. Ingreso RPP:"))
        f1_lay.addWidget(self.txt_fecha_ingreso_rpp)
        form_fechas.addRow("F. Solicitud:", f1_lay)

        # Fila 2 Fechas: Reporte Notaría y Escritura
        f2_lay = QHBoxLayout()
        f2_lay.setSpacing(6)
        self.txt_fecha_reporte_notaria = CustomInput("AAAA-MM-DD", parent=self.container_notaria)
        self.txt_fecha_escritura = CustomInput("AAAA-MM-DD", parent=self.container_notaria)
        f2_lay.addWidget(self.txt_fecha_reporte_notaria)
        f2_lay.addWidget(QLabel("F. Escritura:"))
        f2_lay.addWidget(self.txt_fecha_escritura)
        form_fechas.addRow("F. Rep. Notaría:", f2_lay)

        # Fila 3 Fechas: Titulación y Estatus RPP
        f3_lay = QHBoxLayout()
        f3_lay.setSpacing(6)
        self.txt_fecha_titulacion = CustomInput("AAAA-MM-DD", parent=self.container_notaria)
        self.txt_estatus_aviso = CustomInput(parent=self.container_notaria)
        self.txt_estatus_aviso.setText("NUEVO INGRESO")
        f3_lay.addWidget(self.txt_fecha_titulacion)
        f3_lay.addWidget(QLabel("Estatus RPP:"))
        f3_lay.addWidget(self.txt_estatus_aviso)
        form_fechas.addRow("F. Titulación:", f3_lay)
        notaria_vlayout.addLayout(form_fechas)

        # Subsección E: Observaciones y Comentarios
        form_obs = QFormLayout()
        form_obs.setSpacing(6)

        self.txt_comentarios = CustomInput("Comentarios notariales...", parent=self.container_notaria)
        form_obs.addRow("Comentarios:", self.txt_comentarios)

        self.txt_obs_notaria = QTextEdit(self.container_notaria)
        self.txt_obs_notaria.setMaximumHeight(55)
        self.txt_obs_notaria.setPlaceholderText("Observaciones generales...")
        self.txt_obs_notaria.setStyleSheet(f"background-color: {bg_card}; color: {text_primary}; border: 1px solid {border_color}; border-radius: 4px; padding: 4px;")
        form_obs.addRow("Observaciones:", self.txt_obs_notaria)
        notaria_vlayout.addLayout(form_obs)

        main_vlayout.addWidget(self.container_notaria)

        # -------------------------------------------------------------
        # Timers y Búsqueda Predictiva de Ubicación
        # -------------------------------------------------------------
        from PySide6.QtCore import QTimer
        self._ubi_timer = QTimer(self)
        self._ubi_timer.setSingleShot(True)
        self._ubi_timer.setInterval(250)
        self._ubi_timer.timeout.connect(self._lookup_existing_ubicacion)

        self.cb_desarrollo.currentIndexChanged.connect(lambda: self._ubi_timer.start())
        self.txt_sm.textChanged.connect(lambda: self._ubi_timer.start())
        self.txt_mz.textChanged.connect(lambda: self._ubi_timer.start())
        self.txt_lote.textChanged.connect(lambda: self._ubi_timer.start())
        self.txt_edif.textChanged.connect(lambda: self._ubi_timer.start())
        self.txt_viv.textChanged.connect(lambda: self._ubi_timer.start())
        self.txt_credito.textChanged.connect(lambda: self._ubi_timer.start())
        self.txt_pa.textChanged.connect(lambda: self._ubi_timer.start())
        self.txt_folio.textChanged.connect(lambda: self._ubi_timer.start())

        # -------------------------------------------------------------
        # Botones de Acción
        # -------------------------------------------------------------
        btns = QHBoxLayout()
        btns.setContentsMargins(0, 8, 0, 0)
        btn_cancel = CustomButton("Cancelar", is_secondary=True)
        btn_cancel.clicked.connect(self.reject)
        
        self.btn_save = CustomButton("Guardar")
        self.btn_save.clicked.connect(self._on_save)
        
        btns.addStretch()
        btns.addWidget(btn_cancel)
        btns.addWidget(self.btn_save)
        main_vlayout.addLayout(btns)

        # Ocultar contenedores inicialmente hasta elegir destino
        self.container_colaborador.hide()
        self.container_notaria.hide()
        
        self._load_catalogs()
        self._load_current_draft()

    def _update_header_info(self):
        if self.current_idx < 0 or self.current_idx >= len(self._derechos_data):
            return
        d = self._derechos_data[self.current_idx]
        r_meta = d.get("ref_meta", {})
        portal = d.get("referencia_portal", "") or (self.ref_portals[self.current_idx] if self.current_idx < len(self.ref_portals) else "")
        
        # Format Concept Alias
        raw_conc = r_meta.get("concepto") or r_meta.get("concepto_nombre") or "CONCEPTO"
        alias_conc = r_meta.get("concepto_alias")
        if not alias_conc:
            raw_upper = str(raw_conc).upper()
            if "CLG" in raw_upper: alias_conc = "CLG"
            elif "AVISO" in raw_upper: alias_conc = "AVISO"
            elif "ANALISIS" in raw_upper: alias_conc = "ANALISIS"
            else: alias_conc = str(raw_conc)[:10].upper()

        # Format Delegation Alias
        raw_del = r_meta.get("delegacion") or r_meta.get("delegacion_nombre") or "DELEGACIÓN"
        alias_del = r_meta.get("delegacion_alias")
        if not alias_del:
            raw_del_upper = str(raw_del).upper()
            if "CANCUN" in raw_del_upper or "BENITO" in raw_del_upper: alias_del = "CAN"
            elif "PLAYA" in raw_del_upper or "SOLIDARIDAD" in raw_del_upper: alias_del = "PLA"
            elif "COZUMEL" in raw_del_upper: alias_del = "COZ"
            elif "CHETUMAL" in raw_del_upper or "OTHON" in raw_del_upper: alias_del = "CHE"
            elif "TULUM" in raw_del_upper: alias_del = "TUL"
            else: alias_del = str(raw_del)[:5].upper()

        # Format Empresa
        empresa = r_meta.get("empresa") or r_meta.get("rfc_razon_social") or r_meta.get("rfc") or "EMPRESA"

        is_dark = ThemeManager.is_dark_active()
        text_primary = Colors.TEXT_DARK_PRIMARY if is_dark else "#1E293B"
        text_muted = Colors.TEXT_DARK_MUTED if is_dark else "#64748B"
        accent_color = "#60A5FA" if is_dark else "#1D4ED8"

        if self.total_refs > 1:
            self.setWindowTitle(f"Asignar Derechos ({self.current_idx + 1} de {self.total_refs})")
            header_html = (
                f"<div style='margin-bottom: 2px;'>"
                f"<b style='color: {text_primary}; font-size: 13px;'>Asignando Derecho {self.current_idx + 1} de {self.total_refs}:</b> "
                f"<span style='color: {accent_color}; font-weight: bold; font-size: 13px;'>{alias_conc} | {alias_del} | {empresa}</span>"
                f"</div>"
                f"<div style='font-size: 11px; color: {text_muted}; font-weight: bold;'>Referencia Portal: {portal}</div>"
            )
        else:
            self.setWindowTitle("Asignar Derecho")
            header_html = (
                f"<div style='margin-bottom: 2px;'>"
                f"<b style='color: {text_primary}; font-size: 13px;'>Asignando Derecho:</b> "
                f"<span style='color: {accent_color}; font-weight: bold; font-size: 13px;'>{alias_conc} | {alias_del} | {empresa}</span>"
                f"</div>"
                f"<div style='font-size: 11px; color: {text_muted}; font-weight: bold;'>Referencia Portal: {portal}</div>"
            )
        self.lbl_info.setText(header_html)

    def _save_current_draft(self):
        if self.current_idx < 0 or self.current_idx >= len(self._derechos_data):
            return
        d = self._derechos_data[self.current_idx]
        
        tipo_dest = self.cb_destino.currentText()
        d["tipo_destino"] = tipo_dest if tipo_dest in ("NOTARIA", "COLABORADOR") else None
        
        if tipo_dest == "NOTARIA":
            not_name = self.cb_notarias.currentText()
            d["notaria_id"] = self._notarias_map.get(not_name)
            d["notaria_name"] = not_name
            d["solicitante_externo"] = self.txt_solicitante.text().strip()
            d["cliente"] = self.txt_cliente.text().strip()
            des_name = self.cb_desarrollo.currentText()
            if des_name and des_name != "-- Seleccione Desarrollo (Opcional) --":
                d["desarrollo_id"] = self._desarrollos_map.get(des_name)
                d["desarrollo_name"] = des_name
            else:
                d["desarrollo_id"] = None
                d["desarrollo_name"] = ""
            d["sm"] = self.txt_sm.text().strip()
            d["mz"] = self.txt_mz.text().strip()
            d["lote"] = self.txt_lote.text().strip()
            d["edif"] = self.txt_edif.text().strip()
            d["viv"] = self.txt_viv.text().strip()
            d["folio_electronico"] = self.txt_folio.text().strip()
            d["credito_titular"] = self.txt_credito.text().strip()
            d["pa"] = self.txt_pa.text().strip()
            d["fecha_sol"] = self.txt_fecha_sol.text().strip()
            d["fecha_ingreso_rpp"] = self.txt_fecha_ingreso_rpp.text().strip()
            d["fecha_reporte_notaria"] = self.txt_fecha_reporte_notaria.text().strip()
            d["fecha_escritura"] = self.txt_fecha_escritura.text().strip()
            d["fecha_titulacion"] = self.txt_fecha_titulacion.text().strip()
            d["estatus_aviso"] = self.txt_estatus_aviso.text().strip()
            d["observaciones"] = self.txt_obs_notaria.toPlainText().strip()
            d["comentarios"] = self.txt_comentarios.text().strip()
        elif tipo_dest == "COLABORADOR":
            col_name = self.cb_colaboradores.currentText()
            d["colaborador_id"] = self._colaboradores_map.get(col_name)
            d["colaborador_name"] = col_name
            d["fecha_sol"] = self.txt_fecha_sol_colab.text().strip()
            d["observaciones"] = self.txt_obs_colab.toPlainText().strip()
            d["cliente"] = "ASIGNACIÓN A COLABORADOR"

        # If replicate is checked, copy observations/general data to subsequent drafts
        if hasattr(self, "chk_replicar") and self.chk_replicar.isChecked():
            for future_idx in range(self.current_idx + 1, self.total_refs):
                target = self._derechos_data[future_idx]
                target["tipo_destino"] = d["tipo_destino"]
                target["notaria_id"] = d.get("notaria_id")
                target["notaria_name"] = d.get("notaria_name")
                target["colaborador_id"] = d.get("colaborador_id")
                target["colaborador_name"] = d.get("colaborador_name")
                target["solicitante_externo"] = d.get("solicitante_externo", "")
                target["fecha_sol"] = d.get("fecha_sol", "")
                target["observaciones"] = d.get("observaciones", "")
                target["comentarios"] = d.get("comentarios", "")

    def _load_current_draft(self):
        if self.current_idx < 0 or self.current_idx >= len(self._derechos_data):
            return
        
        self._is_autocompleting = True
        try:
            d = self._derechos_data[self.current_idx]
            
            # 1. Update header banner
            self._update_header_info()
            
            # 2. Update navigation controls
            if self.total_refs > 1:
                self.lbl_step.setText(f"Derecho {self.current_idx + 1} de {self.total_refs}")
                self.btn_prev.setEnabled(self.current_idx > 0)
                self.btn_next.setEnabled(self.current_idx < self.total_refs - 1)
            
            # 3. Reload filtered developments for this specific reference
            self._load_desarrollos_for_current_ref()

            # 4. Populate widgets
            tipo_dest = d.get("tipo_destino")
            if tipo_dest:
                idx_dest = self.cb_destino.findText(tipo_dest)
                if idx_dest >= 0:
                    self.cb_destino.setCurrentIndex(idx_dest)
                self._on_destino_changed(tipo_dest)
            else:
                if self.cb_destino.currentIndex() > 0:
                    tipo_dest = self.cb_destino.currentText()
                    self._on_destino_changed(tipo_dest)

            # Destino specifics
            if tipo_dest == "NOTARIA":
                if d.get("notaria_name"):
                    idx_not = self.cb_notarias.findText(d["notaria_name"])
                    if idx_not >= 0: self.cb_notarias.setCurrentIndex(idx_not)
                self.txt_solicitante.setText(d.get("solicitante_externo", ""))
                self.txt_cliente.setText(d.get("cliente", ""))
                if d.get("desarrollo_name"):
                    idx_des = self.cb_desarrollo.findText(d["desarrollo_name"])
                    if idx_des >= 0: self.cb_desarrollo.setCurrentIndex(idx_des)
                else:
                    self.cb_desarrollo.setCurrentIndex(0)
                self.txt_sm.setText(d.get("sm", ""))
                self.txt_mz.setText(d.get("mz", ""))
                self.txt_lote.setText(d.get("lote", ""))
                self.txt_edif.setText(d.get("edif", ""))
                self.txt_viv.setText(d.get("viv", ""))
                self.txt_folio.setText(d.get("folio_electronico", ""))
                self.txt_credito.setText(d.get("credito_titular", ""))
                self.txt_pa.setText(d.get("pa", ""))
                self.txt_fecha_sol.setText(d.get("fecha_sol", datetime.now().strftime("%Y-%m-%d")))
                self.txt_fecha_ingreso_rpp.setText(d.get("fecha_ingreso_rpp", ""))
                self.txt_fecha_reporte_notaria.setText(d.get("fecha_reporte_notaria", ""))
                self.txt_fecha_escritura.setText(d.get("fecha_escritura", ""))
                self.txt_fecha_titulacion.setText(d.get("fecha_titulacion", ""))
                self.txt_estatus_aviso.setText(d.get("estatus_aviso", "NUEVO INGRESO"))
                self.txt_obs_notaria.setPlainText(d.get("observaciones", ""))
                self.txt_comentarios.setText(d.get("comentarios", ""))
            elif tipo_dest == "COLABORADOR":
                if d.get("colaborador_name"):
                    idx_col = self.cb_colaboradores.findText(d["colaborador_name"])
                    if idx_col >= 0: self.cb_colaboradores.setCurrentIndex(idx_col)
                self.txt_fecha_sol_colab.setText(d.get("fecha_sol", datetime.now().strftime("%Y-%m-%d")))
                self.txt_obs_colab.setPlainText(d.get("observaciones", ""))

            self.lbl_ubi_match.setText("")
        finally:
            self._is_autocompleting = False

    def _on_prev(self):
        if self.current_idx > 0:
            self._save_current_draft()
            self.current_idx -= 1
            self._load_current_draft()

    def _on_next(self):
        if self.current_idx < self.total_refs - 1:
            self._save_current_draft()
            self.current_idx += 1
            self._load_current_draft()

    def _lookup_existing_ubicacion(self):
        if getattr(self, "_is_autocompleting", False):
            return

        credito = self.txt_credito.text().strip()
        pa = self.txt_pa.text().strip()
        folio = self.txt_folio.text().strip()

        des_name = self.cb_desarrollo.currentText()
        des_id = self._desarrollos_map.get(des_name) if des_name and des_name != "-- Seleccione Desarrollo (Opcional) --" else None
        sm = self.txt_sm.text().strip() or None
        mz = self.txt_mz.text().strip() or None
        lote = self.txt_lote.text().strip() or None
        edif = self.txt_edif.text().strip() or None
        viv = self.txt_viv.text().strip() or None

        has_cred = len(credito) >= 3
        has_pa = len(pa) >= 2
        has_folio = len(folio) >= 3
        has_coords = bool(des_id and mz and lote)

        if not (has_cred or has_pa or has_folio or has_coords):
            self.lbl_ubi_match.setText("")
            return

        try:
            match_data = self.inventario_ui_service.get_asignacion_by_identificador(
                credito_titular=credito if has_cred else None,
                pa=pa if has_pa else None,
                folio_electronico=folio if has_folio else None,
                desarrollo_id=des_id if has_coords else None,
                mz=mz,
                lote=lote,
                edif=edif,
                viv=viv
            )
            if match_data:
                src = match_data.get("match_source", "coordenadas")
                if src == "credito":
                    msg = f"✓ Coincidencia encontrada por No. de Crédito ({match_data['credito_titular']})"
                elif src == "pa":
                    msg = f"✓ Coincidencia encontrada por PA ({match_data['pa']})"
                elif src == "folio":
                    msg = f"✓ Coincidencia encontrada por Folio Electrónico ({match_data['folio_electronico']})"
                else:
                    msg = f"✓ Ubicación existente encontrada (ID #{match_data.get('ubicacion_id', '')})"
                self.lbl_ubi_match.setText(msg)

                # Autocomplete empty fields safely
                self._is_autocompleting = True
                try:
                    # 1. Cliente
                    if not self.txt_cliente.text().strip() and match_data.get("cliente") and match_data.get("cliente") not in ("RESERVA MASIVA MANUAL", "ASIGNACIÓN A COLABORADOR"):
                        self.txt_cliente.setText(match_data["cliente"])

                    # 2. Desarrollo (if combo is at default and match has desarrollo)
                    if self.cb_desarrollo.currentIndex() <= 0 and match_data.get("desarrollo_nombre"):
                        idx = self.cb_desarrollo.findText(match_data["desarrollo_nombre"])
                        if idx >= 0:
                            self.cb_desarrollo.setCurrentIndex(idx)

                    # 3. Coordenadas
                    if not self.txt_sm.text().strip() and match_data.get("sm"):
                        self.txt_sm.setText(match_data["sm"])
                    if not self.txt_mz.text().strip() and match_data.get("mz"):
                        self.txt_mz.setText(match_data["mz"])
                    if not self.txt_lote.text().strip() and match_data.get("lote"):
                        self.txt_lote.setText(match_data["lote"])
                    if not self.txt_edif.text().strip() and match_data.get("edif"):
                        self.txt_edif.setText(match_data["edif"])
                    if not self.txt_viv.text().strip() and match_data.get("viv"):
                        self.txt_viv.setText(match_data["viv"])

                    # 4. Folio, Crédito, PA
                    if not self.txt_folio.text().strip() and match_data.get("folio_electronico"):
                        self.txt_folio.setText(str(match_data["folio_electronico"]))
                    if not self.txt_credito.text().strip() and match_data.get("credito_titular"):
                        self.txt_credito.setText(match_data["credito_titular"])
                    if not self.txt_pa.text().strip() and match_data.get("pa"):
                        self.txt_pa.setText(match_data["pa"])
                    if not self.txt_comentarios.text().strip() and match_data.get("comentarios"):
                        self.txt_comentarios.setText(match_data["comentarios"])
                finally:
                    self._is_autocompleting = False
            else:
                self.lbl_ubi_match.setText("")
        except Exception as e:
            print("[ManualAssignmentDialog] Error checking identificador:", e)
            self.lbl_ubi_match.setText("")

    def _on_destino_changed(self, text):
        if text == "NOTARIA":
            self.container_notaria.show()
            self.container_colaborador.hide()
        elif text == "COLABORADOR":
            self.container_colaborador.show()
            self.container_notaria.hide()
        else:
            self.container_notaria.hide()
            self.container_colaborador.hide()
        self.adjustSize()

    def _load_catalogs(self):
        try:
            notarias = self.inventario_ui_service.get_notarias()
            colaboradores = self.inventario_ui_service.get_colaboradores()
            self._desarrollos_list = self.inventario_ui_service.get_desarrollos()

            self._notarias_map = {n["nombre"]: n["notaria_id"] for n in notarias}
            self._colaboradores_map = {c["nombre"]: c["colaborador_id"] for c in colaboradores}
            self._desarrollos_map = {d["nombre"]: d["desarrollo_id"] for d in self._desarrollos_list}

            self.cb_notarias.clear()
            self.cb_notarias.addItem("-- Seleccione Notaría --", None)
            for n in notarias:
                self.cb_notarias.addItem(n["nombre"], n["notaria_id"])
            self.cb_notarias.setCurrentIndex(0)

            self.cb_colaboradores.clear()
            self.cb_colaboradores.addItem("-- Seleccione Colaborador --", None)
            for c in colaboradores:
                self.cb_colaboradores.addItem(c["nombre"], c["colaborador_id"])
            self.cb_colaboradores.setCurrentIndex(0)

        except Exception as e:
            print("Error loading catalog data for ManualAssignmentDialog:", e)

    def _load_desarrollos_for_current_ref(self):
        try:
            if not self._desarrollos_list:
                return

            # Extract pair for current reference
            r_meta = self._derechos_data[self.current_idx].get("ref_meta", {}) if self.current_idx < len(self._derechos_data) else {}
            rfc_id = r_meta.get("rfc_id")
            delegacion_id = r_meta.get("delegacion_id")
            
            if not rfc_id or not delegacion_id:
                if self.parent() and hasattr(self.parent(), "grid_individual"):
                    for row in self.parent().grid_individual.get_all_data():
                        rfc_id = rfc_id or row.get("rfc_id")
                        delegacion_id = delegacion_id or row.get("delegacion_id")

            try:
                desarrollo_empresas = self.inventario_ui_service.get_desarrollos_activos_para_apartar()
            except Exception:
                desarrollo_empresas = []

            valid_desarrollo_ids = set()
            for de in desarrollo_empresas:
                if rfc_id and delegacion_id and de.get("rfc_id") == rfc_id and de.get("delegacion_id") == delegacion_id:
                    valid_desarrollo_ids.add(de.get("desarrollo_id"))

            self.cb_desarrollo.clear()
            self.cb_desarrollo.addItem("-- Seleccione Desarrollo (Opcional) --", None)
            
            for d in self._desarrollos_list:
                if not (rfc_id and delegacion_id) or d["desarrollo_id"] in valid_desarrollo_ids:
                    self.cb_desarrollo.addItem(d["nombre"], d["desarrollo_id"])
            
            self.cb_desarrollo.setCurrentIndex(0)
        except Exception as e:
            print("Error filtering developments for current reference:", e)

    def _on_save(self):
        # 1. Save current active screen draft
        self._save_current_draft()

        # 2. Check destination type from active combo
        common_tipo_destino = self.cb_destino.currentText()
        if common_tipo_destino not in ("NOTARIA", "COLABORADOR"):
            QMessageBox.warning(self, "Tipo Destino Requerido", "Por favor seleccione un Tipo de Destino (NOTARIA o COLABORADOR).")
            return

        detalles_list = []
        
        # 3. Validate each draft in sequence
        for idx, d in enumerate(self._derechos_data):
            tipo_dest = d.get("tipo_destino") or common_tipo_destino
            d["tipo_destino"] = tipo_dest
            
            r_id = d["referencia_id"]
            portal_code = d.get("referencia_portal", "")
            
            if tipo_dest == "COLABORADOR":
                col_id = d.get("colaborador_id")
                if not col_id:
                    col_name = self.cb_colaboradores.currentText()
                    col_id = self._colaboradores_map.get(col_name)
                    d["colaborador_id"] = col_id
                if not col_id:
                    self.current_idx = idx
                    self._load_current_draft()
                    QMessageBox.warning(self, "Colaborador Requerido", f"En el Derecho {idx+1} de {self.total_refs}: Por favor seleccione un Colaborador válido.")
                    return

                obs = d.get("observaciones", "").strip()
                if not obs:
                    self.current_idx = idx
                    self._load_current_draft()
                    QMessageBox.warning(self, "Observaciones Requeridas", f"En el Derecho {idx+1} de {self.total_refs}: Debe capturar observaciones describiendo el uso del derecho.")
                    return

                fecha_sol_raw = d.get("fecha_sol", "").strip()
                fecha_sol = None
                if fecha_sol_raw:
                    try:
                        fecha_sol = datetime.strptime(fecha_sol_raw, "%Y-%m-%d").date()
                    except ValueError:
                        self.current_idx = idx
                        self._load_current_draft()
                        QMessageBox.warning(self, "Fecha Inválida", f"En el Derecho {idx+1} de {self.total_refs}: La Fecha de Asignación debe tener formato AAAA-MM-DD.")
                        return

                detalles_list.append({
                    "cliente": "ASIGNACIÓN A COLABORADOR",
                    "desarrollo_id": None,
                    "fecha_solicitud": fecha_sol,
                    "sm": None, "mz": None, "lote": None, "edif": None, "viv": None,
                    "folio_electronico": None,
                    "estatus_primer_aviso": "NUEVO INGRESO",
                    "credito_titular": None, "pa": None,
                    "fecha_reporte_notaria": None, "fecha_ingreso_rpp": None,
                    "fecha_escritura": None, "fecha_titulacion": None,
                    "comentarios": None,
                    "observaciones": obs,
                    "concepto_solicitado": "MANUAL",
                    "referencia_id": r_id,
                    "referencia_asignada": portal_code
                })

            elif tipo_dest == "NOTARIA":
                not_id = d.get("notaria_id")
                if not not_id:
                    not_name = self.cb_notarias.currentText()
                    not_id = self._notarias_map.get(not_name)
                    d["notaria_id"] = not_id
                if not not_id:
                    self.current_idx = idx
                    self._load_current_draft()
                    QMessageBox.warning(self, "Notaría Requerida", f"En el Derecho {idx+1} de {self.total_refs}: Por favor seleccione una Notaría válida.")
                    return

                cliente = d.get("cliente", "").strip()
                if not cliente:
                    self.current_idx = idx
                    self._load_current_draft()
                    QMessageBox.warning(self, "Cliente Requerido", f"En el Derecho {idx+1} de {self.total_refs}: Por favor ingrese el nombre del cliente.")
                    return

                def _parse_d(date_str, field_name):
                    if not date_str: return None
                    try: return datetime.strptime(date_str, "%Y-%m-%d").date()
                    except ValueError: raise ValueError(f"En el Derecho {idx+1} de {self.total_refs}: El campo '{field_name}' debe tener formato AAAA-MM-DD.")

                try:
                    fecha_sol = _parse_d(d.get("fecha_sol"), "Fecha Solicitud")
                    fecha_ingreso_rpp = _parse_d(d.get("fecha_ingreso_rpp"), "Fecha Ingreso RPP")
                    fecha_reporte_notaria = _parse_d(d.get("fecha_reporte_notaria"), "Fecha Reporte Notaría")
                    fecha_escritura = _parse_d(d.get("fecha_escritura"), "Fecha Escritura")
                    fecha_titulacion = _parse_d(d.get("fecha_titulacion"), "Fecha Titulación")
                except ValueError as ve:
                    self.current_idx = idx
                    self._load_current_draft()
                    QMessageBox.warning(self, "Fecha Inválida", str(ve))
                    return

                detalles_list.append({
                    "cliente": cliente,
                    "desarrollo_id": d.get("desarrollo_id"),
                    "fecha_solicitud": fecha_sol,
                    "sm": d.get("sm") or None,
                    "mz": d.get("mz") or None,
                    "lote": d.get("lote") or None,
                    "edif": d.get("edif") or None,
                    "viv": d.get("viv") or None,
                    "folio_electronico": d.get("folio_electronico") or None,
                    "estatus_primer_aviso": d.get("estatus_aviso") or "NUEVO INGRESO",
                    "credito_titular": d.get("credito_titular") or None,
                    "pa": d.get("pa") or None,
                    "fecha_reporte_notaria": fecha_reporte_notaria,
                    "fecha_ingreso_rpp": fecha_ingreso_rpp,
                    "fecha_escritura": fecha_escritura,
                    "fecha_titulacion": fecha_titulacion,
                    "comentarios": d.get("comentarios") or None,
                    "observaciones": d.get("observaciones") or "",
                    "concepto_solicitado": "MANUAL",
                    "referencia_id": r_id,
                    "referencia_asignada": portal_code
                })

        # Confirm action with the user
        if self.total_refs == 1:
            confirm_msg = "¿Está seguro de guardar la asignación del derecho seleccionado?"
        else:
            confirm_msg = f"¿Está seguro de guardar la asignación de los {self.total_refs} derechos seleccionados?"
            
        reply = QMessageBox.question(
            self,
            "Confirmar Asignación",
            confirm_msg,
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            parent_window = self.parent().window()
            usuario_id = getattr(parent_window, "current_usuario_id", 1)

            first_d = self._derechos_data[0]
            notaria_id = first_d.get("notaria_id") if common_tipo_destino == "NOTARIA" else None
            colaborador_id = first_d.get("colaborador_id") if common_tipo_destino == "COLABORADOR" else None
            solicitante_externo = first_d.get("solicitante_externo") or None
            observaciones_global = first_d.get("observaciones") or ""

            self.inventario_ui_service.crear_lote_asignacion(
                tipo_destino=common_tipo_destino,
                notaria_id=notaria_id,
                colaborador_id=colaborador_id,
                solicitante_externo=solicitante_externo,
                observaciones=observaciones_global,
                usuario_creacion=usuario_id,
                detalles_list=detalles_list
            )

            QMessageBox.information(self, "Éxito", f"Se asignaron exitosamente {len(self.ref_ids)} derechos.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error al Guardar", f"No se pudo registrar la asignación en la base de datos:\n{str(e)}")


class ExportLotesDialog(QDialog):
    """Dialog to list historical assignments and export any to Control_Inventario.xlsx format."""
    
    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.inventario_ui_service = InventarioUIService(self.db_connector)
        
        self.setWindowTitle("Exportar Reporte de Asignación")
        self.setMinimumSize(600, 400)
        self.layout = QVBoxLayout(self)
        
        self.layout.addWidget(CustomLabel("Historial de Asignaciones", variant="subheader"))
        
        self.table_lotes = StyledDataTable(["ID Asignación", "Destino", "Asignado A", "Solicitante Externo", "Fecha Creación", "Refs", "Observaciones"], parent=self)
        self.layout.addWidget(self.table_lotes)

        # Buttons
        btns = QHBoxLayout()
        btn_close = CustomButton("Cerrar", is_secondary=True)
        btn_close.clicked.connect(self.reject)
        
        btn_export = CustomButton("Exportar Asignación")
        btn_export.clicked.connect(self._on_export)
        
        btns.addStretch()
        btns.addWidget(btn_close)
        btns.addWidget(btn_export)
        self.layout.addLayout(btns)
        
        self._load_lotes()

    def _load_lotes(self):
        try:
            self.lotes = self.inventario_ui_service.get_lotes_asignacion()
                
            rows = []
            for l in self.lotes:
                rows.append([
                    str(l["lote_asignacion_id"]),
                    l["tipo_destino"],
                    l["asignado_a"],
                    l["solicitante_externo"],
                    l["fecha"],
                    str(l["total_referencias"]),
                    l["observaciones"]
                ])
            self.table_lotes.populate_rows(rows)
        except Exception as e:
            print("Error loading lotes in dialog:", e)

    def _on_export(self):
        selected = self.table_lotes.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selección Requerida", "Por favor selecciona una asignación en la lista para exportarla.")
            return

        row = selected[0].row()
        lote_id = int(self.table_lotes.item(row, 0).text())
        dest_name = self.table_lotes.item(row, 2).text()
        req_name = self.table_lotes.item(row, 3).text()
        date_str = self.table_lotes.item(row, 4).text()

        # Ask where to save
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Reporte de Asignación",
            f"Asignacion_{lote_id}.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            details = self.inventario_ui_service.get_lote_detalles(lote_id)

            # Generate Styled Excel
            title = f"ENTREGA DE DERECHOS"
            subtitle = f"DESTINO: {dest_name.upper()} {f'({req_name.upper()})' if req_name else ''}"
            
            # Simple date range calculation from details
            date_range = date_str.split()[0]
            
            ExcelInventoryHandler.generate_excel_inventory_file(
                dest_path=file_path,
                title=title,
                subtitle=subtitle,
                date_range=date_range,
                data_rows=details
            )

            QMessageBox.information(self, "Exportación Completada", f"Se ha generado y guardado el archivo Excel con éxito en:\n{file_path}")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error de Exportación", f"No se pudo generar el archivo Excel:\n{str(e)}")


class LoteProcessingDialog(QDialog):
    """Dialog to show details of an assignment with rich header, enhanced table,
    Generar Excel and Generar PDF actions."""

    def __init__(self, db_connector, lote_id: int, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.lote_id = lote_id
        self.inventario_ui_service = InventarioUIService(self.db_connector)
        self.header_data: dict = {}
        self.detalles: list = []

        self.setWindowTitle(f"Detalle de Asignación #{lote_id}")
        self.resize(1100, 680)
        self.setMinimumSize(950, 600)
        
        # Main Layout following design_system spacing
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # ── Header Section using CustomLabel ─────────────────────────────────
        self.header_layout = QHBoxLayout()
        self.lbl_title = CustomLabel(f"Detalle de Asignación #{lote_id}", variant="header")
        self.lbl_subtitle = CustomLabel("Cargando información del lote...", variant="body")
        self.lbl_subtitle.setObjectName("assignmentProcessingSubtitle")
        
        title_block = QVBoxLayout()
        title_block.addWidget(self.lbl_title)
        title_block.addWidget(self.lbl_subtitle)
        self.header_layout.addLayout(title_block)
        root.addLayout(self.header_layout)

        # ── Metrics Bar using design system components ───────────────────────
        self.banner_row = QWidget()
        self.banner_row.setStyleSheet("background: transparent;")
        banner_row_layout = QHBoxLayout(self.banner_row)
        banner_row_layout.setContentsMargins(0, 0, 0, 0)
        banner_row_layout.setSpacing(0)
        
        self.metric_frame = QFrame()
        self.metric_frame.setObjectName("assignmentMetricBar")
        # Reuse style pattern of orderProcessingMetricBar
        self.metric_frame.setStyleSheet("""
            QFrame#assignmentMetricBar {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        metric_layout = QHBoxLayout(self.metric_frame)
        metric_layout.setContentsMargins(16, 8, 16, 8)
        metric_layout.setSpacing(20)
        metric_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.lbl_metric_solicitante = CustomLabel("Solicitante: —", variant="body")
        self.lbl_metric_solicitante.setStyleSheet("font-weight: bold;")
        
        self.lbl_metric_fecha = CustomLabel("Fecha: —", variant="body")
        
        self.lbl_metric_estado = CustomLabel("Estado: —", variant="body")
        self.lbl_metric_estado.setStyleSheet("font-weight: bold;")

        metric_layout.addWidget(self.lbl_metric_solicitante)
        metric_layout.addWidget(self.lbl_metric_fecha)
        metric_layout.addWidget(self.lbl_metric_estado)
        
        banner_row_layout.addWidget(self.metric_frame)
        root.addWidget(self.banner_row)

        # ── References table ─────────────────────────────────────────────────

        headers = [
            "✔", "ID", "Ref ID",
            "Estado", "Empresa", "Concepto",
            "Referencia", "Cliente", "Desarrollo",
            "MZA", "Lote", "Ext", "Int",
            "No.Oficial", "P.A.", "Fecha Solicitud",
        ]
        self.table_detalles = StyledDataTable(headers, parent=self)
        self.table_detalles.setColumnHidden(1, True)  # ID interno
        self.table_detalles.setColumnHidden(2, True)  # Ref ID
        self.table_detalles.setMinimumHeight(300)
        root.addWidget(self.table_detalles)

        # ── Buttons ──────────────────────────────────────────────────────────
        btns = QHBoxLayout()
        
        btn_excel = CustomButton("Generar Excel", is_secondary=True)
        btn_excel.setIcon(Icons.file_excel("#16A34A")) # Excel green
        btn_excel.setToolTip("Generar Archivos Excel Lotes")
        btn_excel.clicked.connect(self._on_generate_excel)
        
        btn_pdf = CustomButton("Generar PDF", is_secondary=True)
        btn_pdf.setIcon(Icons.file_pdf("#DC2626")) # PDF red
        btn_pdf.setToolTip("Generar Archivos PDF Unificado")
        btn_pdf.clicked.connect(self._on_generate_pdf)

        btn_close = CustomButton("Cerrar", is_secondary=True)
        btn_close.clicked.connect(self.reject)

        btns.addStretch()
        btns.addWidget(btn_excel)
        btns.addWidget(btn_pdf)
        btns.addWidget(btn_close)
        root.addLayout(btns)

        self._load_all()

    # ── Data loading ─────────────────────────────────────────────────────────
    def _load_all(self):
        """Load header and detail rows."""
        try:
            self.header_data = self.inventario_ui_service.get_lote_asignacion_header(self.lote_id)
            self._apply_header(self.header_data)
        except Exception as e:
            print("[LoteProcessingDialog] Header error:", e)

        try:
            self.detalles = self.inventario_ui_service.get_lote_detalles(self.lote_id)
            self._populate_table()
        except Exception as e:
            QMessageBox.critical(self, "Error al Cargar",
                                 f"No se pudieron cargar los detalles de la asignación:\n{str(e)}")

    def _apply_header(self, h: dict):
        tipo       = h.get("tipo_destino", "")
        asignado   = h.get("asignado_a", "—")
        fecha      = h.get("fecha", "—")
        estado     = h.get("estado_refs", "—")
        solicitante = h.get("solicitante_externo", "")
        icon = "🏛" if tipo == "NOTARIA" else "🤝"

        self.lbl_title.setText(f"Detalle de Asignación #{self.lote_id}")
        self.lbl_subtitle.setText(f"{icon} {tipo}: {asignado}")
        
        self.lbl_metric_solicitante.setText(f"Solicitante: {solicitante}" if solicitante else f"Asignado a: {asignado}")
        self.lbl_metric_fecha.setText(f"Fecha: {fecha}")
        self.lbl_metric_estado.setText(f"Estado: {estado}")
        
        # Color metrics conditionally
        estado_color = "#16A34A" if estado == "ASIGNADA" else "#D97706"
        self.lbl_metric_estado.setStyleSheet(f"font-weight: bold; color: {estado_color};")

    def _populate_table(self):
        rows = []
        for d in self.detalles:
            rows.append([
                "",
                str(d.get("lote_detalle_id", "")),
                str(d.get("referencia_id", "") or ""),
                d.get("estado", ""),
                d.get("empresa", ""),
                d.get("concepto", ""),
                d.get("referencia", ""),
                d.get("cliente", ""),
                d.get("desarrollo", ""),
                d.get("mz", ""),
                d.get("lote", ""),
                d.get("edif", ""),
                d.get("viv", ""),
                d.get("folio_electronico", ""),
                d.get("pa", ""),
                d.get("fecha_solicitud", ""),
            ])
        self.table_detalles.populate_rows(rows, checkable_first_col=True)
        for r in range(self.table_detalles.rowCount()):
            chk = self.table_detalles.item(r, 0)
            if chk:
                chk.setCheckState(Qt.CheckState.Checked)

    def _get_selected_details(self) -> list:
        """Returns detalles list filtered to checked rows."""
        selected = []
        for r in range(self.table_detalles.rowCount()):
            if self.table_detalles.item(r, 0).checkState() == Qt.CheckState.Checked:
                if r < len(self.detalles):
                    selected.append(self.detalles[r])
        return selected

    # ── Excel generation ─────────────────────────────────────────────────────
    def _on_generate_excel(self):
        selected = self._get_selected_details()
        if not selected:
            QMessageBox.warning(self, "Selección Vacía",
                                "Por favor selecciona al menos una referencia.")
            return

        import re
        def _clean(s: str) -> str:
            return re.sub(r'[\\/:*?"<>|]', '_', s or "").strip()

        asignado  = _clean(self.header_data.get("asignado_a", "Asignacion"))
        fecha_raw = self.header_data.get("fecha", "")
        try:
            from datetime import datetime
            fecha_str = datetime.strptime(fecha_raw.split()[0], "%d/%m/%Y").strftime("%Y%m%d")
        except Exception:
            from datetime import date
            fecha_str = date.today().strftime("%Y%m%d")
        total_refs   = len(selected)
        default_name = f"{asignado}_{fecha_str}_{total_refs}refs.xlsx"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Excel de Asignación", default_name, "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        # Show Loading Spinner
        self.loading_dialog = GLLoadingDialog("Generando archivo Excel...", self)

        # Start Worker Thread
        self.excel_worker = ExcelWorker(file_path, self.header_data, selected)
        
        def on_excel_finished(success, message):
            self.loading_dialog.close()
            if success:
                QMessageBox.information(self, "Excel Generado",
                                        f"Archivo guardado exitosamente:\n{file_path}")
            else:
                QMessageBox.critical(self, "Error al Generar Excel", message)
            self.excel_worker.deleteLater()

        self.excel_worker.finished.connect(on_excel_finished)
        self.excel_worker.start()
        self.loading_dialog.exec()

    # ── PDF generation ───────────────────────────────────────────────────────
    def _on_generate_pdf(self):
        selected = self._get_selected_details()
        if not selected:
            QMessageBox.warning(self, "Selección Vacía",
                                "Por favor selecciona al menos una referencia.")
            return

        dest_dir = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Destino")
        if not dest_dir:
            return

        # Show Loading Spinner
        self.loading_dialog = GLLoadingDialog("Generando y uniendo PDFs...", self)

        # Start Worker Thread
        self.pdf_worker = PdfWorker(selected, dest_dir, self.header_data, self.inventario_ui_service)

        def on_pdf_finished(result):
            self.loading_dialog.close()
            success = result["success"]
            missing = result["missing"]
            error = result["error"]
            
            msg = f"PDFs generados exitosamente: {success}\n"
            if missing: msg += f"Referencias sin archivos: {missing}\n"
            if error:   msg += f"Errores al procesar: {error}\n"
            QMessageBox.information(self, "Generación de PDFs Finalizada", msg)
            self.pdf_worker.deleteLater()

        self.pdf_worker.finished.connect(on_pdf_finished)
        self.pdf_worker.start()
        self.loading_dialog.exec()


class ReservaGridRow(QFrame):
    """Dynamic row item inside ApartarReferenciasDialog."""
    deleted = Signal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("reservaGridRow")
        self.setStyleSheet("QFrame#reservaGridRow { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; }")
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(8)
        
        self.cb_empresa = CustomComboBox(self)
        self.cb_empresa.setMinimumWidth(120)
        self.cb_empresa.setPlaceholderText("Empresa...")
        
        self.cb_concepto = CustomComboBox(self)
        self.cb_concepto.setMinimumWidth(120)
        self.cb_concepto.setPlaceholderText("Concepto...")
        
        self.cb_desarrollo = CustomComboBox(self)
        self.cb_desarrollo.setMinimumWidth(140)
        self.cb_desarrollo.setPlaceholderText("Desarrollo...")
        
        from PySide6.QtWidgets import QSpinBox
        self.sb_cantidad = QSpinBox(self)
        self.sb_cantidad.setRange(1, 1000)
        self.sb_cantidad.setValue(10)
        
        from sar.src.ui.design_system.utils.icons import Icons
        self.btn_delete = CustomButton("", is_secondary=True)
        self.btn_delete.setIcon(Icons.trash())
        self.btn_delete.setFixedSize(30, 30)
        self.btn_delete.setStyleSheet("border: none;")
        self.btn_delete.clicked.connect(lambda: self.deleted.emit(self))
        
        self.layout.addWidget(self.cb_empresa)
        self.layout.addWidget(self.cb_concepto)
        self.layout.addWidget(self.cb_desarrollo)
        self.layout.addWidget(self.sb_cantidad)
        self.layout.addWidget(self.btn_delete)

    def populate(self, rfcs, conceptos, desarrollos):
        self.cb_empresa.clear()
        for name, r_id in rfcs.items():
            self.cb_empresa.addItem(name, r_id)
            
        self.cb_concepto.clear()
        for name, c_id in conceptos.items():
            self.cb_concepto.addItem(name, c_id)
            
        self.cb_desarrollo.clear()
        for name, d_id in desarrollos.items():
            self.cb_desarrollo.addItem(name, d_id)
            
    def get_data(self) -> dict:
        return {
            "rfc_id": self.cb_empresa.currentData(),
            "concepto_id": self.cb_concepto.currentData(),
            "desarrollo_id": self.cb_desarrollo.currentData(),
            "cantidad": self.sb_cantidad.value()
        }


class ApartarReferenciasDialog(QDialog):
    """Dialog to pre-reserve (apartar) references for a Notary in RESERVADA state with multi-row options."""
    
    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.inventario_ui_service = InventarioUIService(self.db_connector)
        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()
        
        self.setWindowTitle("Reserva de Derechos (Apartados)")
        self.setMinimumWidth(750)
        self.setMinimumHeight(450)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(12)
        
        # Notaria Selector at the top
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Notaría de Destino:", self))
        self.cb_notarias = CustomComboBox(self)
        self.cb_notarias.setMinimumWidth(250)
        top_layout.addWidget(self.cb_notarias)
        top_layout.addStretch()
        self.layout.addLayout(top_layout)
        
        # Interactive Grid
        self.grid = InteractiveGrid(self)
        self.grid.set_third_column_label("Desarrollo")
        self.grid.btn_save.setVisible(False)
        self.grid.btn_cancel.setVisible(False)
        self.layout.addWidget(self.grid)
        
        # Dialog Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cancel = CustomButton("Cancelar", is_secondary=True)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_save = CustomButton("Confirmar Apartados")
        self.btn_save.clicked.connect(self._on_save)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        self.layout.addLayout(btn_layout)
        
        self._load_catalogs()
        
    def _load_catalogs(self):
        try:
            self._catalogs_data = self.inventario_ui_service.get_catalogos_data()
            self._notarias_map = {n["nombre"]: n["notaria_id"] for n in self._catalogs_data["notarias"]}
            self._rfcs_map = {r["razon_social"] if isinstance(r, dict) else r.razon_social: r["rfc_id"] if isinstance(r, dict) else r.rfc_id for r in self._catalogs_data["rfcs"]}
            self._concepts_map = {c["nombre"] if isinstance(c, dict) else c.nombre: c["concepto_id"] if isinstance(c, dict) else c.concepto_id for c in self._catalogs_data["conceptos"]}
            self._desarrollos_map = {d["nombre"]: d["desarrollo_id"] for d in self._catalogs_data["desarrollos"]}
            
            self.cb_notarias.addItems(list(self._notarias_map.keys()))
            
            rfcs_list_tuples = [(r_id, r_name) for r_name, r_id in self._rfcs_map.items()]
            CONCEPTOS_APARTADO = {2, 3}
            concepts_list_tuples = sorted(
                [
                    (c_id, c_name)
                    for c_name, c_id in self._concepts_map.items()
                    if c_id in CONCEPTOS_APARTADO
                ],
                key=lambda x: x[0]
            )
            delegations_list_tuples = [(d["delegacion_id"] if isinstance(d, dict) else d.delegacion_id, d["nombre"] if isinstance(d, dict) else d.nombre) for d in self._catalogs_data["delegaciones"]]
            
            desarrollos_tuples = []
            for d in self._catalogs_data["desarrollos"]:
                desarrollos_tuples.append((d["desarrollo_id"], d["nombre"], d.get("delegacion_id")))
                
            self.grid.set_has_desarrollo(True)
            self.grid.set_catalogs(rfcs_list_tuples, concepts_list_tuples, delegations_list_tuples, desarrollos_tuples)
            self.grid.add_row()
        except Exception as e:
            print("Error loading dialog catalog data:", e)
            
    def _on_save(self):
        not_name = self.cb_notarias.currentText()
        notaria_id = self._notarias_map.get(not_name)
        if not notaria_id:
            QMessageBox.warning(self, "Notaría Faltante", "Por favor, seleccione una Notaría de destino.")
            return
            
        data = self.grid.get_all_data()
        if not data:
            QMessageBox.warning(self, "Validación", "Debes agregar al menos un renglón para realizar un apartado.")
            return

        seen_combinations = set()
        rows_data = []
        for i, row in enumerate(data):
            if not row["rfc_id"] or not row["concepto_id"] or not row["delegacion_id"]:
                QMessageBox.warning(self, "Validación", f"El renglón {i+1} debe tener todos los campos seleccionados (Empresa, Concepto y Delegación).")
                return
                
            key = (row["rfc_id"], row["concepto_id"], row["delegacion_id"], row.get("desarrollo_id"))
            if key in seen_combinations:
                QMessageBox.warning(self, "Validación", f"El renglón {i+1} tiene una combinación duplicada de Empresa, Concepto, Delegación y Desarrollo.")
                return
            seen_combinations.add(key)
            
            # Si el desarrollo_id no fue seleccionado (es None o "Cualquier Desarrollo"), pasamos el delegacion_id como desarrollo_id a la consulta / repo
            final_desarrollo_id = row.get("desarrollo_id") if row.get("desarrollo_id") else row["delegacion_id"]
            
            rows_data.append({
                "rfc_id": row["rfc_id"],
                "concepto_id": row["concepto_id"],
                "delegacion_id": row["delegacion_id"],
                "desarrollo_id": final_desarrollo_id,
                "cantidad": row["cantidad"]
            })
            
        try:
            parent_window = self.window()
            usuario_id = getattr(parent_window, "current_usuario_id", 1)
            
            if self.api_client.connect_via_api:
                # API sequentially
                for row_d in rows_data:
                    payload = {
                        "notaria_id": notaria_id,
                        "rfc_id": row_d["rfc_id"],
                        "concepto_id": row_d["concepto_id"],
                        "delegacion_id": row_d["delegacion_id"],
                        "desarrollo_id": row_d["desarrollo_id"],
                        "cantidad": row_d["cantidad"],
                        "usuario_creacion": usuario_id
                    }
                    self.api_client.request("POST", "/api/docs/inventario/lotes/apartar", data=payload)
            else:
                # Single session transaction
                with self.db_connector.get_session() as session:
                    from sar.src.storage.repositories import InventarioRepository
                    repo = InventarioRepository(session)
                    for row_d in rows_data:
                        repo.apartar_referencias(
                            notaria_id=notaria_id,
                            rfc_id=row_d["rfc_id"],
                            concepto_id=row_d["concepto_id"],
                            delegacion_id=row_d["delegacion_id"],
                            desarrollo_id=row_d["desarrollo_id"],
                            cantidad=row_d["cantidad"],
                            usuario_id=usuario_id
                        )
                    session.commit()
                    
            total_refs = sum(row_d["cantidad"] for row_d in rows_data)
            QMessageBox.information(self, "Apartado Exitoso", f"Se han reservado exitosamente {total_refs} referencias en total en estado RESERVADA.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error al Reservar", f"No se pudo completar el apartado de referencias:\n{str(e)}")

