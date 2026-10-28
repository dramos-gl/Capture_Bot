"""Bulk Upload references view aligned with Atomic Design and Housing Import UX standard."""

import os
import csv
from datetime import datetime
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFrame, QLabel, QLineEdit, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor

from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.utils.icons import Icons
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.atoms.gl_input import CustomInput
from sar.src.ui.design_system.components.molecules.gl_combo_box import CustomComboBox
from sar.src.ui.design_system.components.molecules.gl_card import CustomCard
from sar.src.ui.design_system.components.molecules.gl_info_banner import GLInfoBanner
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
from sqlalchemy import text


class BulkLoadWorker(QThread):
    """Worker thread to execute bulk CSV preview or import without freezing the UI."""
    finished = Signal(bool, dict, str)  # success, result_data, message

    def __init__(self, mode: str, orden_id: int, registros: list, file_path: str, db_connector, api_client, current_user_id: int, current_sesion_id: int = None, solicitud_id: Optional[int] = None):
        super().__init__()
        self.mode = mode  # 'preview' o 'execute'
        self.orden_id = orden_id
        self.registros = registros
        self.file_path = file_path
        self.db_connector = db_connector
        self.api_client = api_client
        self.current_user_id = current_user_id
        self.current_sesion_id = current_sesion_id
        self.solicitud_id = solicitud_id

    def run(self):
        try:
            # 1. Si no tenemos registros en memoria, leer del CSV
            registros = self.registros
            if not registros and self.file_path and os.path.exists(self.file_path):
                registros = []
                with open(self.file_path, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for idx, row in enumerate(reader, start=2):
                        ref = (row.get('referencia_portal') or '').strip()
                        if not ref:
                            continue
                        registros.append({
                            'fila': idx,
                            'rfc': (row.get('rfc') or '').strip(),
                            'concepto_alias': (row.get('concepto_alias') or '').strip(),
                            'delegacion': (row.get('delegacion') or '').strip(),
                            'referencia_portal': ref,
                            'importe': float(row.get('importe') or 0.0),
                            'fecha_generacion': (row.get('fecha_generacion') or '').strip() or None,
                            'fecha_vigencia': (row.get('fecha_vigencia') or '').strip() or None
                        })

            if not registros:
                self.finished.emit(False, {}, "No se encontraron referencias válidas en el archivo seleccionado.")
                return

            if self.mode == "preview":
                if self.api_client.connect_via_api:
                    payload = {"registros": registros}
                    if self.solicitud_id:
                        payload["solicitud_id"] = self.solicitud_id
                    res = self.api_client.request(
                        "POST",
                        f"/api/admin/ordenes/{self.orden_id}/preview-carga",
                        json=payload
                    )
                else:
                    with self.db_connector.get_session() as session:
                        from sar.src.services.admin_service import AdminService
                        svc = AdminService(session)
                        res = svc.preview_carga_masiva_referencias(self.orden_id, registros, solicitud_id=self.solicitud_id)
                self.finished.emit(True, res, "Precarga y validación completadas.")

            elif self.mode == "execute":
                if self.api_client.connect_via_api:
                    payload = {
                        "registros": registros,
                        "usuario_id": self.current_user_id,
                        "sesion_id": self.current_sesion_id
                    }
                    if self.solicitud_id:
                        payload["solicitud_id"] = self.solicitud_id
                    res = self.api_client.request(
                        "POST",
                        f"/api/admin/ordenes/{self.orden_id}/ejecutar-carga",
                        json=payload
                    )
                else:
                    with self.db_connector.get_session() as session:
                        from sar.src.services.admin_service import AdminService
                        svc = AdminService(session)
                        res = svc.ejecutar_carga_masiva_referencias(
                            orden_id=self.orden_id,
                            registros=registros,
                            usuario_id=self.current_user_id,
                            sesion_id=self.current_sesion_id,
                            solicitud_id=self.solicitud_id
                        )
                        session.commit()
                self.finished.emit(True, res, res.get("mensaje", "Carga masiva completada con éxito."))

        except Exception as e:
            self.finished.emit(False, {}, str(e))


class BulkLoadView(QWidget):
    """View to download template, preview file contents, and trigger bulk load for a selected Order.
    Replicates the UI layout and UX patterns of housing import (tab_import_viviendas).
    """
    action_state_changed = Signal()

    def __init__(self, db_connector, current_user_id, current_sesion_id, can_edit, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.current_user_id = current_user_id
        self.current_sesion_id = current_sesion_id
        self.can_edit = can_edit
        self.worker = None

        self.precarga_data = None  # Almacena el resultado validado de la precarga
        self.current_file_path = None
        self.cached_registros = []
        self._raw_preview_filas = []

        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(12)

        self._build_ui()

    def _build_ui(self):
        # 1. Barra de controles superiores (Elástica y adaptativa a pantallas pequeñas)
        ctl_box = QHBoxLayout()
        ctl_box.setSpacing(10)

        ctl_box.addWidget(CustomLabel("Orden Destino *:", variant="body"))
        self.combo_orden = CustomComboBox()
        self.combo_orden.setMinimumWidth(240)
        self.combo_orden.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_orden.currentIndexChanged.connect(self._on_orden_changed)
        ctl_box.addWidget(self.combo_orden, 1)

        ctl_box.addWidget(CustomLabel("Solicitud Destino:", variant="body"))
        self.combo_solicitud = CustomComboBox()
        self.combo_solicitud.setMinimumWidth(260)
        self.combo_solicitud.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_solicitud.currentIndexChanged.connect(self._on_solicitud_changed)
        ctl_box.addWidget(self.combo_solicitud, 1)

        # Botones operativos desacoplados (sus acciones se invocan principalmente desde la Toolbar superior)
        self.btn_generar = CustomButton("Plantilla Excel", is_secondary=True, icon_name="excel")
        self.btn_generar.clicked.connect(self._on_generar_plantilla)
        self.btn_generar.hide()

        self.btn_seleccionar = CustomButton("Cargar Archivo", is_secondary=True, icon_name="documento_cargar")
        self.btn_seleccionar.clicked.connect(self._on_seleccionar_archivo)
        self.btn_seleccionar.hide()

        self.btn_exportar_datos = CustomButton("Exportar Datos", is_secondary=True, icon_name="excel")
        self.btn_exportar_datos.clicked.connect(self._on_exportar_datos)
        self.btn_exportar_datos.setEnabled(False)
        self.btn_exportar_datos.hide()

        self.btn_limpiar = CustomButton("Limpiar", is_secondary=True, icon_name="cancelar")
        self.btn_limpiar.clicked.connect(self._limpiar_precarga)
        self.btn_limpiar.hide()

        self.btn_ejecutar = CustomButton("Aplicar Cambios", icon_name="guardar")
        self.btn_ejecutar.clicked.connect(self._on_ejecutar_carga)
        self.btn_ejecutar.setEnabled(False)
        self.btn_ejecutar.setVisible(self.can_edit)
        self.btn_ejecutar.hide()

        ctl_box.addStretch()
        self.layout.addLayout(ctl_box)

        # 2. Information Row / Metrics Bar (Limpio, transparente, interactivo con tokens de color)
        self.kpi_frame = QFrame()
        self.kpi_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        kpi_lay = QHBoxLayout(self.kpi_frame)
        kpi_lay.setContentsMargins(0, 4, 0, 4)
        kpi_lay.setSpacing(6)

        self.kpi_containers = {}

        def _make_clickable_kpi(dot_color: str, initial_text: str, kpi_key: str, tooltip_text: str) -> tuple[QFrame, QLabel, CustomLabel]:
            container = QFrame()
            container.setObjectName(f"kpi_{kpi_key}")
            container.setCursor(Qt.PointingHandCursor)
            container.setToolTip(tooltip_text)
            container.setStyleSheet(f"""
                QFrame#{container.objectName()} {{
                    background-color: transparent;
                    border: 1px solid transparent;
                    border-radius: 4px;
                    padding: 2px 4px;
                }}
                QFrame#{container.objectName()}:hover {{
                    background-color: {Colors.NEUTRAL_BG};
                    border: 1px solid {Colors.BORDER_LIGHT};
                }}
            """)

            lay = QHBoxLayout(container)
            lay.setContentsMargins(4, 2, 4, 2)
            lay.setSpacing(6)

            dot = QLabel()
            dot.setFixedSize(10, 10)
            dot.setStyleSheet(f"background-color: {dot_color}; border-radius: 5px; border: none;")

            lbl = CustomLabel(initial_text, variant="body")
            lbl.setStyleSheet("background: transparent;")

            lay.addWidget(dot)
            lay.addWidget(lbl)

            container.mousePressEvent = lambda e, k=kpi_key: self._on_kpi_clicked(k)

            self.kpi_containers[kpi_key] = {
                "container": container,
                "dot": dot,
                "lbl": lbl,
                "dot_color": dot_color
            }
            return container, dot, lbl

        # Puntos e indicadores KPI interactivos
        self.kpi_total_frame, self.dot_kpi_total, self.lbl_kpi_total_arch = _make_clickable_kpi(
            Colors.TEXT_LIGHT_MUTED, "En Archivo: 0", "TOTAL", "Clic para mostrar todas las referencias del archivo"
        )
        self.kpi_nuevos_frame, self.dot_kpi_nuevos, self.lbl_kpi_nuevos = _make_clickable_kpi(
            Colors.SUCCESS, "Válidos / A Crear: 0", "VALIDOS", "Clic para filtrar solo registros válidos listos para carga"
        )
        self.kpi_duplicados_frame, self.dot_kpi_duplicados, self.lbl_kpi_duplicados = _make_clickable_kpi(
            Colors.ERROR, "Con Error / Duplicados: 0", "ERRORES", "Clic para filtrar registros con inconsistencia o duplicados"
        )

        def _make_metric_dot(color_val: str) -> QLabel:
            dot = QLabel()
            dot.setFixedSize(10, 10)
            dot.setStyleSheet(f"background-color: {color_val}; border-radius: 5px; border: none;")
            return dot

        self.dot_kpi_orden = _make_metric_dot(Colors.ACCENT_VIOLET)
        self.lbl_kpi_orden_info = CustomLabel("Tipo Orden: N/A", variant="body")

        self.dot_kpi_solicitudes = _make_metric_dot(Colors.ACCENT)
        self.lbl_kpi_solicitudes = CustomLabel("Nuevas Solicitudes: 0", variant="body")

        kpi_lay.addWidget(self.kpi_total_frame)
        kpi_lay.addSpacing(12)
        kpi_lay.addWidget(self.kpi_nuevos_frame)
        kpi_lay.addSpacing(12)
        kpi_lay.addWidget(self.kpi_duplicados_frame)
        kpi_lay.addSpacing(16)
        kpi_lay.addWidget(self.dot_kpi_orden)
        kpi_lay.addWidget(self.lbl_kpi_orden_info)
        kpi_lay.addSpacing(16)
        kpi_lay.addWidget(self.dot_kpi_solicitudes)
        kpi_lay.addWidget(self.lbl_kpi_solicitudes)
        kpi_lay.addStretch()

        self.layout.addWidget(self.kpi_frame)

        # 3. Contenedor de Tarjeta Estandarizada y Tabla (Atomic Design: CustomCard)
        self.card_preview = CustomCard("Vista Previa de Referencias (Carga Masiva)", parent=self)
        self.card_preview.setObjectName("cardFrame")

        # Indicador de archivo cargado adjunto al encabezado de la tarjeta
        self.lbl_sep = CustomLabel("|", variant="muted")
        self.lbl_sep.setStyleSheet(f"color: {Colors.TEXT_DARK_SECONDARY}; font-size: 14px; font-weight: normal; margin: 0 4px;")
        self.card_preview.add_header_widget(self.lbl_sep)

        self.lbl_kpi_archivo = CustomLabel("Archivo: Ninguno", variant="muted")
        self.lbl_kpi_archivo.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_LIGHT_MUTED}; font-weight: normal;")
        self.card_preview.add_header_widget(self.lbl_kpi_archivo)

        # Selector de Filtro de Estado (Todos, Solo Válidos, Solo Con Error)
        self.cmb_filtro_estado = CustomComboBox(parent=self)
        self.cmb_filtro_estado.setObjectName("bulkFiltroEstado")
        self.cmb_filtro_estado.setMinimumWidth(180)
        self.cmb_filtro_estado.setMaximumWidth(220)
        self.cmb_filtro_estado.addItem("Mostrar: Todos", "TODOS")
        self.cmb_filtro_estado.addItem("Solo Válidos", "VALIDOS")
        self.cmb_filtro_estado.addItem("Solo Con Error", "ERRORES")
        self.cmb_filtro_estado.currentIndexChanged.connect(self._on_filtro_estado_changed)
        self.card_preview.add_header_widget(self.cmb_filtro_estado)

        # Campo Buscar alineado al encabezado de la tabla (Homologado con GlCrudTable)
        self.search_input = CustomInput(control_size="md", parent=self)
        self.search_input.setObjectName("bulkSearchInput")
        self.search_input.setPlaceholderText("Buscar en vista previa...")
        self.search_input.setMinimumWidth(200)
        self.search_input.setMaximumWidth(280)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.addAction(Icons.search(Colors.TEXT_LIGHT_MUTED), QLineEdit.LeadingPosition)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.card_preview.add_header_widget(self.search_input)

        # Tabla de Vista Previa
        self.table_preview = QTableWidget()
        self.table_preview.setColumnCount(7)
        self.table_preview.setHorizontalHeaderLabels([
            "#", "RFC Emisor", "Concepto", "Delegación", "Referencia", "Importe", "Estatus / Validación"
        ])
        self.table_preview.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_preview.horizontalHeader().setStretchLastSection(True)
        self.table_preview.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table_preview.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_preview.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_preview.setShowGrid(False)
        self.table_preview.verticalHeader().setVisible(False)
        self.table_preview.verticalHeader().setDefaultSectionSize(26)

        col_widths = [50, 140, 110, 110, 170, 110, 260]
        for c_idx, width in enumerate(col_widths):
            self.table_preview.setColumnWidth(c_idx, width)

        self.card_preview.layout.addWidget(self.table_preview)
        self.layout.addWidget(self.card_preview)

    def refresh_data(self):
        """Loads the most recent 10 available orders into the combo box with search support."""
        self.combo_orden.blockSignals(True)
        self.combo_orden.clear()

        try:
            if self.api_client.connect_via_api:
                res = self.api_client.request("GET", "/api/admin/data/ordenes", data={"limit": 10})
            else:
                with self.db_connector.get_session() as session:
                    res = session.execute(text("""
                        SELECT orden_id, folio, descripcion, tipo_orden, fecha_creacion 
                        FROM sar_produccion.orden_generacion 
                        ORDER BY orden_id DESC
                        LIMIT 10
                    """)).mappings().all()

            from sar.src.ui.design_system.utils.formatters import format_orden_filter_label
            for r in res:
                tipo = (r.get("tipo_orden") or "ESTANDAR").upper()
                tag_tipo = f" [{tipo}]" if tipo != "ESTANDAR" else ""
                label_base = format_orden_filter_label(r["folio"], r.get("descripcion"))
                label = f"{label_base}{tag_tipo}"
                self.combo_orden.addItem(label, r["orden_id"])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar las órdenes: {e}")

        self.combo_orden.blockSignals(False)
        self._on_orden_changed()

    def _on_orden_changed(self):
        """Refreshes order metadata, populates pending solicitudes, and clears preview."""
        self._limpiar_precarga()
        orden_id = self.combo_orden.currentData()
        self.combo_solicitud.blockSignals(True)
        self.combo_solicitud.clear()
        self.combo_solicitud.addItem("-- [Automático / Según archivo] --", None)

        if not orden_id:
            self.lbl_kpi_orden_info.setText("Tipo Orden: N/A")
            self.combo_solicitud.blockSignals(False)
            return

        try:
            # 1. Obtener tipo de orden para reflejar en el KPI
            if self.api_client.connect_via_api:
                ordenes = self.api_client.request("GET", "/api/admin/data/ordenes", data={"limit": 10})
                ord_info = next((o for o in ordenes if o.get("orden_id") == orden_id), None)
                tipo = (ord_info.get("tipo_orden") if ord_info else "ESTANDAR").upper()
            else:
                with self.db_connector.get_session() as session:
                    row = session.execute(
                        text("SELECT tipo_orden FROM sar_produccion.orden_generacion WHERE orden_id = :oid"),
                        {"oid": orden_id}
                    ).first()
                    tipo = (row[0] if row and row[0] else "ESTANDAR").upper()

            self.lbl_kpi_orden_info.setText(f"Tipo: {tipo}")

            # 2. Cargar solicitudes de la orden
            if self.api_client.connect_via_api:
                sols = self.api_client.request("GET", f"/api/admin/ordenes/{orden_id}/solicitudes-carga")
            else:
                with self.db_connector.get_session() as session:
                    from sar.src.services.admin_service import AdminService
                    svc = AdminService(session)
                    sols = svc.get_solicitudes_orden_carga_masiva(orden_id)

            for s in sols:
                sid = s["solicitud_id"]
                rfc = s["rfc"]
                conc = s.get("concepto_alias") or s.get("concepto_nombre")
                deleg = s.get("delegacion_nombre", "")
                cant_sol = s.get("cantidad_solicitada", 0)
                cant_gen = s.get("cantidad_generada", 0)
                pend = s.get("referencias_pendientes", cant_sol - cant_gen)

                tag_pend = f" [Pendiente: {pend}]" if pend > 0 else f" [Cargadas: {cant_gen}/{cant_sol}]"
                label_sol = f"Sol #{sid}: {rfc} - {conc} ({deleg}){tag_pend}"
                self.combo_solicitud.addItem(label_sol, sid)

        except Exception as e:
            print(f"Error cargando solicitudes de orden {orden_id}: {e}")
            self.lbl_kpi_orden_info.setText("Tipo: ESTANDAR")

        self.combo_solicitud.blockSignals(False)

    def _on_solicitud_changed(self):
        """Disparador al cambiar la solicitud seleccionada."""
        self._limpiar_precarga()

    def _limpiar_precarga(self):
        """Restablece los datos de la precarga y limpia la tabla."""
        self.precarga_data = None
        self.cached_registros = []
        self._raw_preview_filas = []
        self.current_file_path = None
        self.btn_ejecutar.setEnabled(False)
        self.btn_exportar_datos.setEnabled(False)
        self.table_preview.setRowCount(0)

        # Reset KPIs
        self.lbl_kpi_total_arch.setText("En Archivo: 0")
        self.lbl_kpi_nuevos.setText("Válidos / A Crear: 0")
        self.lbl_kpi_duplicados.setText("Con Error / Duplicados: 0")
        self.lbl_kpi_solicitudes.setText("Nuevas Solicitudes: 0")
        self.lbl_kpi_archivo.setText("Archivo: Ninguno")

        self._highlight_kpi_active("TODOS")
        self.action_state_changed.emit()

    def _on_kpi_clicked(self, kpi_key: str):
        """Maneja el clic interactivo en una pastilla KPI para filtrar la tabla con efecto toggle."""
        target_status = "TODOS"
        if kpi_key == "VALIDOS":
            target_status = "VALIDOS"
        elif kpi_key == "ERRORES":
            target_status = "ERRORES"
        elif kpi_key == "TOTAL":
            target_status = "TODOS"

        current_selected = self.cmb_filtro_estado.currentData() if hasattr(self, "cmb_filtro_estado") else "TODOS"

        # Efecto Toggle: Si ya está seleccionado ese filtro, regresar a TODOS
        if target_status != "TODOS" and current_selected == target_status:
            target_status = "TODOS"

        if hasattr(self, "cmb_filtro_estado"):
            found_idx = -1
            for i in range(self.cmb_filtro_estado.count()):
                if self.cmb_filtro_estado.itemData(i) == target_status:
                    found_idx = i
                    break
            if found_idx != -1:
                self.cmb_filtro_estado.setCurrentIndex(found_idx)
            else:
                self._apply_table_filters(custom_status=target_status)
        else:
            self._apply_table_filters(custom_status=target_status)

        self._highlight_kpi_active(target_status)

    def _highlight_kpi_active(self, active_status: str):
        """Actualiza el resalte visual de la pastilla KPI activa acorde a tokens de color."""
        if not hasattr(self, "kpi_containers"):
            return

        key_mapping = {
            "TOTAL": active_status == "TODOS",
            "VALIDOS": active_status == "VALIDOS",
            "ERRORES": active_status == "ERRORES"
        }

        for k, is_active in key_mapping.items():
            info = self.kpi_containers.get(k)
            if not info:
                continue
            container = info["container"]
            lbl = info["lbl"]
            dot_color = info["dot_color"]

            if is_active and active_status != "TODOS":
                container.setStyleSheet(f"""
                    QFrame#{container.objectName()} {{
                        background-color: {Colors.NEUTRAL_BG};
                        border: 1px solid {dot_color};
                        border-radius: 4px;
                        padding: 2px 4px;
                    }}
                """)
                lbl.setStyleSheet(f"background: transparent; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY};")
            else:
                container.setStyleSheet(f"""
                    QFrame#{container.objectName()} {{
                        background-color: transparent;
                        border: 1px solid transparent;
                        border-radius: 4px;
                        padding: 2px 4px;
                    }}
                    QFrame#{container.objectName()}:hover {{
                        background-color: {Colors.NEUTRAL_BG};
                        border: 1px solid {Colors.BORDER_LIGHT};
                    }}
                """)
                lbl.setStyleSheet(f"background: transparent; font-weight: normal; color: {Colors.TEXT_LIGHT_SECONDARY};")

    def _on_filtro_estado_changed(self):
        """Disparador al cambiar la selección en el combo de filtro."""
        status = self.cmb_filtro_estado.currentData() or "TODOS"
        self._highlight_kpi_active(status)
        self._apply_table_filters(custom_status=status)

    def _on_search_text_changed(self):
        """Disparador al escribir en el campo de búsqueda."""
        self._apply_table_filters()

    def _apply_table_filters(self, custom_status: Optional[str] = None):
        """Filtra las filas de la tabla de vista previa combinando estado y texto de búsqueda."""
        if not self._raw_preview_filas:
            self.table_preview.setRowCount(0)
            return

        status_filter = custom_status if custom_status is not None else (self.cmb_filtro_estado.currentData() or "TODOS")
        search_query = self.search_input.text().strip().lower()

        filtered_filas = []
        for f in self._raw_preview_filas:
            is_valido = bool(f.get("valido"))

            # 1. Filtro por Estado
            if status_filter == "VALIDOS" and not is_valido:
                continue
            if status_filter == "ERRORES" and is_valido:
                continue

            # 2. Filtro por Búsqueda de Texto
            if search_query:
                combined_text = f"{f.get('fila', '')} {f.get('rfc', '')} {f.get('concepto', '')} {f.get('delegacion', '')} {f.get('referencia_portal', '')} {f.get('detalle_validacion', '')}".lower()
                if search_query not in combined_text:
                    continue

            filtered_filas.append(f)

        self._render_table_rows(filtered_filas)

    def _render_table_rows(self, filas: list):
        """Pinta las filas especificadas en la tabla."""
        self.table_preview.setRowCount(len(filas))
        for idx, f in enumerate(filas):
            self.table_preview.setItem(idx, 0, QTableWidgetItem(str(f.get("fila", idx + 1))))
            self.table_preview.setItem(idx, 1, QTableWidgetItem(str(f.get("rfc", ""))))
            self.table_preview.setItem(idx, 2, QTableWidgetItem(str(f.get("concepto", ""))))
            self.table_preview.setItem(idx, 3, QTableWidgetItem(str(f.get("delegacion", ""))))
            self.table_preview.setItem(idx, 4, QTableWidgetItem(str(f.get("referencia_portal", ""))))
            self.table_preview.setItem(idx, 5, QTableWidgetItem(f"${f.get('importe', 0.0):,.2f}"))

            item_status = QTableWidgetItem(str(f.get("detalle_validacion", "")))
            if not f.get("valido"):
                item_status.setForeground(QColor(Colors.ERROR))
            else:
                item_status.setForeground(QColor(Colors.SUCCESS))
            self.table_preview.setItem(idx, 6, item_status)

    def _on_generar_plantilla(self):
        """Generates and downloads the official CSV template."""
        orden_id = self.combo_orden.currentData()
        if not orden_id:
            QMessageBox.warning(self, "Atención", "Selecciona una orden destino antes de descargar la plantilla.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Plantilla de Carga Masiva",
            f"plantilla_carga_referencias_orden_{orden_id}.csv",
            "Archivos CSV (*.csv)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'rfc',
                    'concepto_alias',
                    'delegacion',
                    'referencia_portal',
                    'importe',
                    'fecha_generacion',
                    'fecha_vigencia'
                ])
                with self.db_connector.get_session() as session:
                    grupos = session.execute(text("""
                        SELECT r.rfc, c.alias AS concepto_alias, d.nombre AS delegacion
                        FROM sar_produccion.grupo_referencia gr
                        JOIN sar_catalogo.rfc r ON gr.rfc_id = r.rfc_id
                        JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
                        LEFT JOIN sar_produccion.solicitud s ON s.grupo_id = gr.grupo_id
                        LEFT JOIN sar_catalogo.delegacion d ON s.delegacion_id = d.delegacion_id
                        WHERE gr.orden_id = :oid
                    """), {"oid": orden_id}).mappings().all()

                    for g in grupos:
                        writer.writerow([
                            g['rfc'],
                            g['concepto_alias'],
                            g['delegacion'] or 'CANCUN',
                            'EJEMPLO123456789',
                            '0.00',
                            datetime.now().strftime('%Y-%m-%d'),
                            ''
                        ])

            QMessageBox.information(
                self, "Éxito",
                "Plantilla generada exitosamente.\n\n"
                "Edita el archivo CSV agregando las referencias y respetando los RFCs, Conceptos y Delegaciones de la Orden."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar la plantilla: {e}")

    def _on_seleccionar_archivo(self):
        """Opens file dialog, validates and previews file contents."""
        orden_id = self.combo_orden.currentData()
        if not orden_id:
            QMessageBox.warning(self, "Atención", "Debes seleccionar una orden destino primero.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Archivo de Referencias (CSV)", "", "Archivos CSV (*.csv)"
        )
        if not file_path:
            return

        self.current_file_path = file_path
        file_name = os.path.basename(file_path)
        self.lbl_kpi_archivo.setText(f"Archivo: {file_name}")

        solicitud_id = self.combo_solicitud.currentData()

        # Iniciar worker de precarga
        self.worker = BulkLoadWorker(
            mode="preview",
            orden_id=orden_id,
            registros=[],
            file_path=file_path,
            db_connector=self.db_connector,
            api_client=self.api_client,
            current_user_id=self.current_user_id,
            current_sesion_id=self.current_sesion_id,
            solicitud_id=solicitud_id
        )
        self.worker.finished.connect(self._on_precarga_terminada)
        self.worker.start()

    def _on_precarga_terminada(self, success: bool, result_data: dict, msg: str):
        if not success:
            self._limpiar_precarga()
            QMessageBox.critical(self, "Error de Validación", f"Error al procesar el archivo:\n\n{msg}")
            return

        self.precarga_data = result_data
        filas = result_data.get("filas", [])
        self._raw_preview_filas = filas

        self.cached_registros = [
            {
                "rfc": f["rfc"],
                "concepto_alias": f["concepto"],
                "delegacion": f["delegacion"],
                "referencia_portal": f["referencia_portal"],
                "importe": f["importe"],
                "fecha_generacion": None,
                "fecha_vigencia": None
            }
            for f in filas if f.get("valido")
        ]

        # Actualizar métricas KPI
        total_r = result_data.get("total_registros", len(filas))
        validos_r = len(self.cached_registros)
        invalidos = result_data.get("registros_invalidos", total_r - validos_r)
        nuevas_sols = result_data.get("nuevas_solicitudes_estimadas", 0)
        tipo_ord = result_data.get("tipo_orden", "ESTANDAR")

        self.lbl_kpi_total_arch.setText(f"En Archivo: {total_r}")
        self.lbl_kpi_nuevos.setText(f"Válidos / A Crear: {validos_r}")
        self.lbl_kpi_duplicados.setText(f"Con Error / Duplicados: {invalidos}")
        self.lbl_kpi_solicitudes.setText(f"Nuevas Solicitudes: {nuevas_sols}")
        self.lbl_kpi_orden_info.setText(f"Tipo: {tipo_ord}")

        # Renderizar datos en tabla
        self._apply_table_filters()

        # Habilitar acciones según validez
        es_valido = result_data.get("es_valido", False)
        self.btn_ejecutar.setEnabled(es_valido and self.can_edit)
        self.btn_exportar_datos.setEnabled(len(filas) > 0)
        self.action_state_changed.emit()

        if not es_valido:
            QMessageBox.warning(
                self, "Inconsistencias Detectadas",
                f"Se detectaron {invalidos} registro(s) con inconsistencias de un total de {total_r}.\n\n"
                "Por favor consulta las filas marcadas en rojo para verificar referencias duplicadas o datos fuera de catálogo."
            )

    def _on_ejecutar_carga(self):
        """Executes the transactional database load of validated references."""
        orden_id = self.combo_orden.currentData()
        if not orden_id or not self.precarga_data or not self.cached_registros:
            return

        solicitud_id = self.combo_solicitud.currentData()
        total_r = len(self.cached_registros)
        nuevas_sols = self.precarga_data.get("nuevas_solicitudes_estimadas", 0)

        if solicitud_id:
            txt_destino = f"• Se importarán directamente en la Solicitud #{solicitud_id}.\n"
        else:
            txt_destino = f"• Se crearán {nuevas_sols} solicitudes nuevas.\n"

        reply = QMessageBox.question(
            self, "Confirmar Carga Masiva",
            f"¿Está seguro de que desea importar transaccionalmente las {total_r} referencias a la orden seleccionada?\n\n"
            f"{txt_destino}"
            "• Los acumuladores y consecutivos se recalcularán automáticamente de forma secuencial continua.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self.btn_ejecutar.setEnabled(False)
        self.action_state_changed.emit()

        self.worker = BulkLoadWorker(
            mode="execute",
            orden_id=orden_id,
            registros=self.cached_registros,
            file_path="",
            db_connector=self.db_connector,
            api_client=self.api_client,
            current_user_id=self.current_user_id,
            current_sesion_id=self.current_sesion_id,
            solicitud_id=solicitud_id
        )
        self.worker.finished.connect(self._on_carga_terminada)
        self.worker.start()

    def _on_carga_terminada(self, success: bool, result_data: dict, msg: str):
        if success:
            QMessageBox.information(self, "Carga Exitosa", msg)
            self._limpiar_precarga()
            self._on_orden_changed()
        else:
            QMessageBox.critical(self, "Error de Carga", f"Error durante la carga masiva:\n\n{msg}")
            self.btn_ejecutar.setEnabled(True)
            self.action_state_changed.emit()

    def _on_exportar_datos(self):
        """Exports currently displayed rows to a CSV file."""
        if not self.table_preview or self.table_preview.rowCount() == 0:
            QMessageBox.information(self, "Exportar", "No hay registros disponibles para exportar.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Vista Previa de Referencias",
            "exportacion_carga_masiva.csv", "CSV (*.csv)"
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                headers = [
                    self.table_preview.horizontalHeaderItem(c).text()
                    if self.table_preview.horizontalHeaderItem(c) else f"Col {c}"
                    for c in range(self.table_preview.columnCount())
                ]
                writer.writerow(headers)
                for r in range(self.table_preview.rowCount()):
                    row = [
                        self.table_preview.item(r, c).text()
                        if self.table_preview.item(r, c) else ""
                        for c in range(self.table_preview.columnCount())
                    ]
                    writer.writerow(row)
            QMessageBox.information(self, "Éxito", f"Datos exportados correctamente:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error al Exportar", f"No se pudo guardar el archivo: {e}")
