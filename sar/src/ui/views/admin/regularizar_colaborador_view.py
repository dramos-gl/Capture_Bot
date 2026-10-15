"""Regularización de asignaciones históricas a colaboradores view in Administration Processes."""

import os
import openpyxl
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QTextEdit, QLabel
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QBrush

from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.components.molecules.gl_combo_box import CustomComboBox
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
from sar.src.ui.design_system.utils.icons import Icons


class RegularizarColaboradorWorker(QThread):
    """Worker thread to execute regularization of references asynchronously."""
    finished = Signal(bool, dict, str)

    def __init__(self, api_client, db_connector, colaborador_id: int, usuario_id: int,
                 registros: List[Dict[str, Any]], observaciones: Optional[str] = None,
                 sesion_id: Optional[int] = None):
        super().__init__()
        self.api_client = api_client
        self.db_connector = db_connector
        self.colaborador_id = colaborador_id
        self.usuario_id = usuario_id
        self.registros = registros
        self.observaciones = observaciones
        self.sesion_id = sesion_id

    def run(self):
        try:
            if self.api_client.connect_via_api:
                payload = {
                    "colaborador_id": self.colaborador_id,
                    "usuario_id": self.usuario_id,
                    "sesion_id": self.sesion_id,
                    "observaciones": self.observaciones,
                    "registros": self.registros
                }
                res = self.api_client.request("POST", "/api/admin/referencias/regularizar-colaborador", json=payload)
            else:
                from sar.src.storage.repositories import InventarioRepository
                with self.db_connector.get_session() as session:
                    repo = InventarioRepository(session)
                    res = repo.regularizar_referencias_colaborador(
                        colaborador_id=self.colaborador_id,
                        usuario_id=self.usuario_id,
                        registros=self.registros,
                        observaciones_lote=self.observaciones,
                        sesion_id=self.sesion_id
                    )
                    session.commit()
            self.finished.emit(True, res, "")
        except Exception as e:
            self.finished.emit(False, {}, str(e))


class RegularizarColaboradorView(QWidget):
    """View to regularize references previously reserved to collaborators with complete location and file data."""

    def __init__(self, db_connector, current_user_id, current_sesion_id, can_edit, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.current_user_id = current_user_id
        self.current_sesion_id = current_sesion_id
        self.can_edit = can_edit

        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()

        self.payload_validado: List[Dict[str, Any]] = []
        self.desarrollos_cache: Dict[str, int] = {}
        self.worker: Optional[RegularizarColaboradorWorker] = None

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(16)

        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        # 1. Header & Title
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        title_lbl = CustomLabel("Regularización de Asignaciones (Colaboradores)", variant="subheader")
        header_layout.addWidget(title_lbl)

        info_icon = Icons.info() if hasattr(Icons, "info") else None
        if info_icon:
            info_lbl = QLabel()
            info_lbl.setPixmap(info_icon.pixmap(16, 16))
            header_layout.addWidget(info_lbl)

        header_layout.addStretch()

        self.btn_actualizar = CustomButton("Actualizar Catálogos", is_secondary=True, icon_name="sincronizar")
        self.btn_actualizar.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.btn_actualizar)

        self.layout.addLayout(header_layout)

        # 2. Form Card
        self.form_card = QFrame()
        self.form_card.setObjectName("cardFrame")
        form_card_layout = QVBoxLayout(self.form_card)
        form_card_layout.setContentsMargins(16, 14, 16, 14)
        form_card_layout.setSpacing(12)

        row_layout = QHBoxLayout()
        row_layout.setSpacing(24)
        row_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Left Column: Colaborador
        left_col = QVBoxLayout()
        left_col.setSpacing(4)
        left_col.setAlignment(Qt.AlignmentFlag.AlignTop)

        colab_title_lbl = QLabel()
        colab_title_lbl.setText("Colaborador con Referencias Apartadas <font color='#EF4444'>*</font>")
        colab_title_lbl.setStyleSheet("font-weight: bold; font-size: 13px;")
        left_col.addWidget(colab_title_lbl)

        self.cb_colaborador = CustomComboBox()
        self.cb_colaborador.setMinimumHeight(38)
        left_col.addWidget(self.cb_colaborador)

        colab_help_lbl = CustomLabel("Seleccione el colaborador asignatario de las referencias a regularizar.", variant="muted")
        left_col.addWidget(colab_help_lbl)
        row_layout.addLayout(left_col, stretch=1)

        # Right Column: Observaciones
        right_col = QVBoxLayout()
        right_col.setSpacing(4)
        right_col.setAlignment(Qt.AlignmentFlag.AlignTop)

        obs_header_layout = QHBoxLayout()
        obs_header_layout.setSpacing(6)
        obs_title_lbl = CustomLabel("Observaciones de la Regularización", variant="body")
        obs_title_lbl.setStyleSheet("font-weight: bold; font-size: 13px;")
        obs_header_layout.addWidget(obs_title_lbl)
        obs_header_layout.addStretch()
        self.lbl_char_counter = CustomLabel("0 / 500", variant="muted")
        obs_header_layout.addWidget(self.lbl_char_counter)
        right_col.addLayout(obs_header_layout)

        self.txt_observaciones = QTextEdit()
        self.txt_observaciones.setFixedHeight(50)
        self.txt_observaciones.setPlaceholderText("Motivo o expediente de regularización de este lote...")
        self.txt_observaciones.textChanged.connect(self._on_txt_changed)
        right_col.addWidget(self.txt_observaciones)
        row_layout.addLayout(right_col, stretch=1)

        form_card_layout.addLayout(row_layout)

        # Actions Row
        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)

        self.btn_descargar = CustomButton("Descargar Plantilla", is_secondary=True, icon_name="documento_cargar")
        self.btn_descargar.setFixedWidth(170)
        self.btn_descargar.clicked.connect(self._on_descargar_plantilla)
        actions_row.addWidget(self.btn_descargar)

        self.btn_seleccionar_excel = CustomButton("Seleccionar Archivo", is_secondary=True, icon_name="buscar")
        self.btn_seleccionar_excel.setFixedWidth(170)
        self.btn_seleccionar_excel.clicked.connect(self._on_seleccionar_excel)
        actions_row.addWidget(self.btn_seleccionar_excel)

        self.btn_limpiar = CustomButton("Limpiar", is_secondary=True, icon_name="cancelar")
        self.btn_limpiar.setFixedWidth(110)
        self.btn_limpiar.clicked.connect(self._on_limpiar)
        actions_row.addWidget(self.btn_limpiar)

        actions_row.addStretch()

        self.btn_confirmar = CustomButton("Confirmar Regularización", icon_name="guardar")
        self.btn_confirmar.setFixedWidth(200)
        self.btn_confirmar.setEnabled(False)
        self.btn_confirmar.clicked.connect(self._on_confirmar_regularizacion)
        actions_row.addWidget(self.btn_confirmar)

        form_card_layout.addLayout(actions_row)
        self.layout.addWidget(self.form_card, stretch=0)

        # 3. KPI / Status Summary Bar
        self.kpi_frame = QFrame()
        self.kpi_frame.setStyleSheet(f"background-color: {Colors.SURFACE_LIGHT}; border: 1px solid {Colors.BORDER_LIGHT}; border-radius: 6px; padding: 6px;")
        kpi_layout = QHBoxLayout(self.kpi_frame)
        kpi_layout.setContentsMargins(12, 6, 12, 6)

        self.lbl_kpi_archivo = QLabel("Archivo: Ninguno seleccionado")
        self.lbl_kpi_archivo.setStyleSheet("font-size: 12px; color: #64748B;")
        kpi_layout.addWidget(self.lbl_kpi_archivo)
        kpi_layout.addStretch()

        self.lbl_kpi_total = QLabel("Total en Archivo: 0")
        self.lbl_kpi_total.setStyleSheet("font-weight: bold; font-size: 12px; color: #1E293B;")
        kpi_layout.addWidget(self.lbl_kpi_total)

        self.lbl_kpi_validos = QLabel("Válidos: 0")
        self.lbl_kpi_validos.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {Colors.SUCCESS};")
        kpi_layout.addWidget(self.lbl_kpi_validos)

        self.lbl_kpi_errores = QLabel("Con Errores: 0")
        self.lbl_kpi_errores.setStyleSheet("font-weight: bold; font-size: 12px; color: #E11D48;")
        kpi_layout.addWidget(self.lbl_kpi_errores)

        self.layout.addWidget(self.kpi_frame)

        # 4. Preview Table Card
        self.results_card = QFrame()
        self.results_card.setObjectName("cardFrame")
        results_card_layout = QVBoxLayout(self.results_card)
        results_card_layout.setContentsMargins(16, 16, 16, 16)
        results_card_layout.setSpacing(12)

        res_title_layout = QHBoxLayout()
        table_icon = Icons.tabla() if hasattr(Icons, "tabla") else None
        if table_icon:
            t_icon_lbl = QLabel()
            t_icon_lbl.setPixmap(table_icon.pixmap(16, 16))
            res_title_layout.addWidget(t_icon_lbl)
        res_title_lbl = CustomLabel("Previsualización de Registros a Regularizar", variant="subheader")
        res_title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #1E293B;")
        res_title_layout.addWidget(res_title_lbl)
        res_title_layout.addStretch()
        results_card_layout.addLayout(res_title_layout)

        self.preview_container = QFrame()
        self.preview_container.setStyleSheet("background-color: transparent; border: none;")
        self.preview_stack = QVBoxLayout(self.preview_container)
        self.preview_stack.setContentsMargins(0, 0, 0, 0)

        # Table Component
        self.table = QTableWidget()
        headers = [
            "Referencia", "Validación", "Detalle", "Cliente", "Desarrollo",
            "SM", "Manzana", "Lote", "Edificio", "Vivienda", "No. Oficial",
            "Crédito", "PA", "F. Solicitud", "F. Escritura"
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                gridline-color: #F1F5F9;
                background-color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #F8FAFC;
                padding: 8px;
                font-weight: bold;
                border: none;
                border-bottom: 1px solid #E2E8F0;
                color: #475569;
            }
        """)
        self.table.setVisible(False)
        self.preview_stack.addWidget(self.table)

        # Placeholder Component
        self.placeholder_widget = QWidget()
        self.placeholder_widget.setStyleSheet("background-color: transparent;")
        placeholder_layout = QVBoxLayout(self.placeholder_widget)
        placeholder_layout.setContentsMargins(40, 40, 40, 40)
        placeholder_layout.setSpacing(10)
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        search_icon = Icons.buscar() if hasattr(Icons, "buscar") else None
        if search_icon:
            search_icon_lbl = QLabel()
            search_icon_lbl.setPixmap(search_icon.pixmap(48, 48))
            search_icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder_layout.addWidget(search_icon_lbl)

        placeholder_title = CustomLabel("No hay archivo cargado", variant="subheader")
        placeholder_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_title.setStyleSheet("font-weight: bold; color: #475569;")
        placeholder_layout.addWidget(placeholder_title)

        placeholder_sub = CustomLabel("Seleccione un archivo Excel para validar y previsualizar las asignaciones a regularizar.", variant="muted")
        placeholder_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(placeholder_sub)

        self.preview_stack.addWidget(self.placeholder_widget)
        results_card_layout.addWidget(self.preview_container)

        self.layout.addWidget(self.results_card, stretch=1)

    def _on_txt_changed(self):
        txt = self.txt_observaciones.toPlainText()
        if len(txt) > 500:
            txt = txt[:500]
            self.txt_observaciones.setPlainText(txt)
            cursor = self.txt_observaciones.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.txt_observaciones.setTextCursor(cursor)
        self.lbl_char_counter.setText(f"{len(txt)} / 500")

    def refresh_data(self):
        """Fetches collaborators and developments from database or API."""
        self.cb_colaborador.clear()
        self.cb_colaborador.addItem("-- Seleccione un Colaborador --", None)
        self.desarrollos_cache.clear()

        try:
            if self.api_client.connect_via_api:
                colabs = self.api_client.request("GET", "/api/admin/data/colaboradores")
                for c in colabs:
                    if c.get("activo", True):
                        self.cb_colaborador.addItem(c["nombre"], c["colaborador_id"])

                desarrs = self.api_client.request("GET", "/api/admin/data/desarrollos")
                for d in desarrs:
                    if d.get("activo", True):
                        self.desarrollos_cache[str(d["nombre"]).strip().upper()] = d["desarrollo_id"]
                        if d.get("alias"):
                            self.desarrollos_cache[str(d["alias"]).strip().upper()] = d["desarrollo_id"]
            else:
                from sqlalchemy import select
                from sar.src.storage.models import Colaborador, Desarrollo
                with self.db_connector.get_session() as session:
                    stmt_c = select(Colaborador).where(Colaborador.activo == True).order_by(Colaborador.nombre)
                    for c in session.execute(stmt_c).scalars().all():
                        self.cb_colaborador.addItem(c.nombre, c.colaborador_id)

                    stmt_d = select(Desarrollo).where(Desarrollo.activo == True).order_by(Desarrollo.nombre)
                    for d in session.execute(stmt_d).scalars().all():
                        self.desarrollos_cache[d.nombre.strip().upper()] = d.desarrollo_id
                        if d.alias:
                            self.desarrollos_cache[d.alias.strip().upper()] = d.desarrollo_id
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar catálogos: {e}")

    def _on_limpiar(self):
        """Resets the UI form, loaded payload, observations, and table preview."""
        self.payload_validado = []
        self.btn_confirmar.setEnabled(False)
        self.txt_observaciones.clear()
        self.cb_colaborador.setCurrentIndex(0)
        self.table.setRowCount(0)
        self.table.setVisible(False)
        self.placeholder_widget.setVisible(True)
        self.lbl_kpi_archivo.setText("Archivo: Ninguno seleccionado")
        self.lbl_kpi_total.setText("Total en Archivo: 0")
        self.lbl_kpi_validos.setText("Válidos: 0")
        self.lbl_kpi_errores.setText("Con Errores: 0")

    def _on_descargar_plantilla(self):
        """Generates and saves the Excel template for regularizing collaborator assignments."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Plantilla de Regularización",
            "plantilla_regularizacion_colaborador.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Regularización"

            cols = [
                "REFERENCIA", "CLIENTE", "DESARROLLO", "SM", "MANZANA", "LOTE",
                "EXT", "INT", "NO_OFICIAL", "CREDITO_TITULAR", "PA",
                "FECHA_SOLICITUD", "FECHA_ESCRITURA", "OBSERVACIONES"
            ]
            for col_idx, col_name in enumerate(cols, 1):
                cell = ws.cell(row=1, column=col_idx, value=col_name)
                cell.font = openpyxl.styles.Font(bold=True, color="FFFFFF")
                cell.fill = openpyxl.styles.PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")

            # Sample row
            sample_dev = next(iter(self.desarrollos_cache.keys()), "DESARROLLO EJEMPLO")
            sample_data = [
                "1234567890", "JUAN PEREZ LOPEZ", sample_dev, "10", "2UC2", "15",
                "A", "101", "OF-501", "CRED-99882", "PA-01",
                "2026-01-15", "2026-03-20", "Regularización de trámite"
            ]
            for col_idx, val in enumerate(sample_data, 1):
                ws.cell(row=2, column=col_idx, value=val)

            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = openpyxl.utils.get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

            wb.save(file_path)
            QMessageBox.information(
                self, "Plantilla Descargada",
                "Plantilla guardada con éxito.\nLas columnas de coordenadas (SM, MANZANA, LOTE, EXT, INT) sanitizarán automáticamente espacios intermedios."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar la plantilla: {e}")

    def _on_seleccionar_excel(self):
        """Loads and pre-validates Excel file, checking reference reservation state and collaborator match."""
        colab_id = self.cb_colaborador.currentData()
        if not colab_id:
            QMessageBox.warning(self, "Seleccionar Colaborador", "Por favor seleccione el colaborador antes de cargar el archivo.")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo de Regularización", "", "Excel Files (*.xlsx)")
        if not file_path:
            return

        try:
            wb = openpyxl.load_workbook(file_path, read_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if len(rows) <= 1:
                QMessageBox.warning(self, "Archivo Vacío", "El archivo no contiene filas de datos.")
                return

            raw_headers = [str(c).strip().upper() for c in rows[0] if c is not None]
            header_map = {name: idx for idx, name in enumerate(raw_headers)}

            req_cols = ["REFERENCIA", "DESARROLLO"]
            missing = [c for c in req_cols if c not in header_map]
            if missing:
                QMessageBox.critical(self, "Columnas Faltantes", f"El archivo debe contener al menos las columnas: {', '.join(missing)}")
                return

            def _clean_str(val: Any) -> Optional[str]:
                if val is None:
                    return None
                s = str(val).strip().upper()
                return s if s else None

            def _clean_coord(val: Any) -> Optional[str]:
                if val is None:
                    return None
                s = str(val).replace(" ", "").strip().upper()
                return s if s else None

            parsed_rows = []
            all_refs = set()

            for r_idx, row in enumerate(rows[1:], 2):
                ref_idx = header_map.get("REFERENCIA")
                ref_val = _clean_str(row[ref_idx]) if ref_idx is not None and len(row) > ref_idx else None
                if not ref_val:
                    continue

                all_refs.add(ref_val)
                des_idx = header_map.get("DESARROLLO")
                des_val = _clean_str(row[des_idx]) if des_idx is not None and len(row) > des_idx else None

                cli_idx = header_map.get("CLIENTE")
                sm_idx = header_map.get("SM")
                mz_idx = header_map.get("MANZANA") if "MANZANA" in header_map else header_map.get("MZ")
                lt_idx = header_map.get("LOTE") if "LOTE" in header_map else header_map.get("LT")
                ed_idx = header_map.get("EXT") if "EXT" in header_map else header_map.get("EDIF")
                vi_idx = header_map.get("INT") if "INT" in header_map else header_map.get("VIV")
                no_idx = header_map.get("NO_OFICIAL")
                cr_idx = header_map.get("CREDITO_TITULAR")
                pa_idx = header_map.get("PA")
                fs_idx = header_map.get("FECHA_SOLICITUD")
                fe_idx = header_map.get("FECHA_ESCRITURA")
                ob_idx = header_map.get("OBSERVACIONES")

                parsed_rows.append({
                    "row_num": r_idx,
                    "referencia": ref_val,
                    "desarrollo_str": des_val,
                    "cliente": _clean_str(row[cli_idx]) if cli_idx is not None and len(row) > cli_idx else None,
                    "sm": _clean_coord(row[sm_idx]) if sm_idx is not None and len(row) > sm_idx else None,
                    "mz": _clean_coord(row[mz_idx]) if mz_idx is not None and len(row) > mz_idx else None,
                    "lote": _clean_coord(row[lt_idx]) if lt_idx is not None and len(row) > lt_idx else None,
                    "edif": _clean_coord(row[ed_idx]) if ed_idx is not None and len(row) > ed_idx else None,
                    "viv": _clean_coord(row[vi_idx]) if vi_idx is not None and len(row) > vi_idx else None,
                    "no_oficial": _clean_str(row[no_idx]) if no_idx is not None and len(row) > no_idx else None,
                    "credito_titular": _clean_str(row[cr_idx]) if cr_idx is not None and len(row) > cr_idx else None,
                    "pa": _clean_str(row[pa_idx]) if pa_idx is not None and len(row) > pa_idx else None,
                    "fecha_solicitud": str(row[fs_idx]).strip() if fs_idx is not None and len(row) > fs_idx and row[fs_idx] else None,
                    "fecha_escritura": str(row[fe_idx]).strip() if fe_idx is not None and len(row) > fe_idx and row[fe_idx] else None,
                    "observaciones": _clean_str(row[ob_idx]) if ob_idx is not None and len(row) > ob_idx else None,
                })

            if not parsed_rows:
                QMessageBox.warning(self, "Sin Registros", "No se encontraron referencias en las filas del archivo.")
                return

            # Batch query reference state and owner from DB/API
            db_ref_info = {}
            if all_refs:
                from sqlalchemy import select
                from sar.src.storage.models import Referencia, AsignacionReferencia, LoteDetalle, LoteAsignacion, EstadoSistema
                with self.db_connector.get_session() as session:
                    refs_list = list(all_refs)
                    chunk_size = 500
                    for i in range(0, len(refs_list), chunk_size):
                        chunk = refs_list[i:i + chunk_size]
                        stmt = (
                            select(
                                Referencia.referencia_portal,
                                EstadoSistema.codigo.label("estado_codigo"),
                                LoteAsignacion.colaborador_id
                            )
                            .join(EstadoSistema, Referencia.estado_id == EstadoSistema.estado_id)
                            .outerjoin(AsignacionReferencia, Referencia.referencia_id == AsignacionReferencia.referencia_id)
                            .outerjoin(LoteDetalle, AsignacionReferencia.lote_detalle_id == LoteDetalle.lote_detalle_id)
                            .outerjoin(LoteAsignacion, LoteDetalle.lote_asignacion_id == LoteAsignacion.lote_asignacion_id)
                            .where(Referencia.referencia_portal.in_(chunk))
                        )
                        for row_db in session.execute(stmt).all():
                            db_ref_info[row_db.referencia_portal] = {
                                "estado": row_db.estado_codigo,
                                "colaborador_id": row_db.colaborador_id
                            }

            # Classify rows
            self.payload_validado = []
            results_to_render = []
            valid_count = 0
            error_count = 0

            for p in parsed_rows:
                ref_portal = p["referencia"]
                info = db_ref_info.get(ref_portal)

                is_valid = True
                msg = "VÁLIDA: Lista para regularizar"

                if not info:
                    is_valid = False
                    msg = "ERROR: La referencia no existe en el sistema."
                elif info.get("estado") != "RESERVADA":
                    is_valid = False
                    msg = f"ERROR: Estado actual '{info.get('estado')}', debe ser 'RESERVADA'."
                elif info.get("colaborador_id") != colab_id:
                    is_valid = False
                    msg = f"ERROR: Apartada a otro colaborador o sin asignación (ID: {info.get('colaborador_id')})."
                elif not p["desarrollo_str"]:
                    is_valid = False
                    msg = "ERROR: Columna DESARROLLO requerida."
                elif p["desarrollo_str"] not in self.desarrollos_cache:
                    is_valid = False
                    msg = f"ERROR: Desarrollo '{p['desarrollo_str']}' no existe en el catálogo."

                if is_valid:
                    valid_count += 1
                    des_id = self.desarrollos_cache[p["desarrollo_str"]]
                    self.payload_validado.append({
                        "referencia": ref_portal,
                        "desarrollo_id": des_id,
                        "cliente": p["cliente"],
                        "sm": p["sm"],
                        "mz": p["mz"],
                        "lote": p["lote"],
                        "edif": p["edif"],
                        "viv": p["viv"],
                        "no_oficial": p["no_oficial"],
                        "credito_titular": p["credito_titular"],
                        "pa": p["pa"],
                        "fecha_solicitud": p["fecha_solicitud"],
                        "fecha_escritura": p["fecha_escritura"],
                        "observaciones": p["observaciones"]
                    })
                else:
                    error_count += 1

                results_to_render.append({
                    "valido": is_valid,
                    "msg": msg,
                    **p
                })

            # Render Table
            self.table.setRowCount(0)
            self.table.setRowCount(len(results_to_render))

            for idx, r in enumerate(results_to_render):
                item_ref = QTableWidgetItem(r["referencia"])
                item_val = QTableWidgetItem("🟢 VÁLIDO" if r["valido"] else "🔴 ERROR")
                item_msg = QTableWidgetItem(r["msg"])
                item_cli = QTableWidgetItem(r["cliente"] or "")
                item_des = QTableWidgetItem(r["desarrollo_str"] or "")
                item_sm = QTableWidgetItem(r["sm"] or "")
                item_mz = QTableWidgetItem(r["mz"] or "")
                item_lt = QTableWidgetItem(r["lote"] or "")
                item_ed = QTableWidgetItem(r["edif"] or "")
                item_vi = QTableWidgetItem(r["viv"] or "")
                item_no = QTableWidgetItem(r["no_oficial"] or "")
                item_cr = QTableWidgetItem(r["credito_titular"] or "")
                item_pa = QTableWidgetItem(r["pa"] or "")
                item_fs = QTableWidgetItem(r["fecha_solicitud"] or "")
                item_fe = QTableWidgetItem(r["fecha_escritura"] or "")

                if not r["valido"]:
                    brush = QBrush(QColor("#FEE2E2"))
                    for itm in [item_ref, item_val, item_msg, item_cli, item_des, item_sm, item_mz, item_lt, item_ed, item_vi, item_no, item_cr, item_pa, item_fs, item_fe]:
                        itm.setBackground(brush)

                self.table.setItem(idx, 0, item_ref)
                self.table.setItem(idx, 1, item_val)
                self.table.setItem(idx, 2, item_msg)
                self.table.setItem(idx, 3, item_cli)
                self.table.setItem(idx, 4, item_des)
                self.table.setItem(idx, 5, item_sm)
                self.table.setItem(idx, 6, item_mz)
                self.table.setItem(idx, 7, item_lt)
                self.table.setItem(idx, 8, item_ed)
                self.table.setItem(idx, 9, item_vi)
                self.table.setItem(idx, 10, item_no)
                self.table.setItem(idx, 11, item_cr)
                self.table.setItem(idx, 12, item_pa)
                self.table.setItem(idx, 13, item_fs)
                self.table.setItem(idx, 14, item_fe)

            self.table.resizeColumnsToContents()
            self.placeholder_widget.setVisible(False)
            self.table.setVisible(True)

            file_name = os.path.basename(file_path)
            self.lbl_kpi_archivo.setText(f"Archivo: {file_name}")
            self.lbl_kpi_total.setText(f"Total en Archivo: {len(results_to_render)}")
            self.lbl_kpi_validos.setText(f"Válidos: {valid_count}")
            self.lbl_kpi_errores.setText(f"Con Errores: {error_count}")

            self.btn_confirmar.setEnabled(valid_count > 0 and self.can_edit)

            if valid_count > 0:
                QMessageBox.information(
                    self, "Validación Completa",
                    f"Archivo validado.\nReferencias listas para regularizar: {valid_count}\nReferencias con error: {error_count}"
                )
            else:
                QMessageBox.warning(
                    self, "Sin Registros Válidos",
                    f"No se encontró ninguna referencia válida para regularizar.\nTotal errores: {error_count}"
                )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al procesar el archivo Excel: {e}")

    def _on_confirmar_regularizacion(self):
        """Executes regularization via background worker."""
        colab_id = self.cb_colaborador.currentData()
        colab_name = self.cb_colaborador.currentText()
        if not colab_id or not self.payload_validado:
            return

        reply = QMessageBox.question(
            self, "Confirmar Regularización",
            f"¿Está seguro de consolidar y regularizar {len(self.payload_validado)} referencias para el colaborador '{colab_name}'?\n\nLas referencias pasarán de RESERVADA a ASIGNADA con su ubicación y expediente registrado.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            return

        self.btn_confirmar.setEnabled(False)
        self.btn_seleccionar_excel.setEnabled(False)
        self.btn_limpiar.setEnabled(False)

        obs = self.txt_observaciones.toPlainText()

        self.worker = RegularizarColaboradorWorker(
            api_client=self.api_client,
            db_connector=self.db_connector,
            colaborador_id=colab_id,
            usuario_id=self.current_user_id,
            registros=self.payload_validado,
            observaciones=obs,
            sesion_id=self.current_sesion_id
        )
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    def _on_worker_finished(self, success: bool, result: dict, error_msg: str):
        self.btn_seleccionar_excel.setEnabled(True)
        self.btn_limpiar.setEnabled(True)

        if success:
            exitos = result.get("exitos", 0)
            errores = result.get("errores", 0)
            QMessageBox.information(
                self, "Proceso Finalizado",
                f"Regularización completada exitosamente.\n\nReferencias regularizadas: {exitos}\nReferencias no procesadas: {errores}"
            )
            self._on_limpiar()
        else:
            self.btn_confirmar.setEnabled(True)
            QMessageBox.critical(self, "Error al Regularizar", f"Ocurrió un error en la transacción:\n{error_msg}")
