import os
import re
from typing import Optional, List, Dict, Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QFrame, QLabel, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QFileDialog,
    QSizePolicy, QLineEdit
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.utils.icons import Icons
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.atoms.gl_input import CustomInput
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.atoms.gl_checkbox import CustomCheckBox
from sar.src.ui.design_system.components.molecules.gl_combo_box import CustomComboBox
from sar.src.ui.design_system.components.molecules.gl_card import CustomCard
from sar.src.ui.design_system.components.molecules.gl_loading_dialog import GLLoadingDialog
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
from sar.src.ui.design_system.components.organisms.gl_crud_table import CrudTablePanel
from sar.src.ui.design_system.components.organisms.gl_dialog import CustomDialog
from sar.src.storage.repositories import CatalogoRepository
from satc.src.services.housing_life_cycle_service import HousingLifeCycleService


class ViviendasFileAnalyzeWorker(QThread):
    """Worker thread para leer, validar y analizar archivos Excel o Constancias RPP PDF en segundo plano."""
    finished = Signal(bool, dict, str)

    def __init__(self, api_client, db_connector, file_path: str, desarrollo_id: int, regimen_id: Optional[int], modo: str):
        super().__init__()
        self.api_client = api_client
        self.db_connector = db_connector
        self.file_path = file_path
        self.desarrollo_id = desarrollo_id
        self.regimen_id = regimen_id
        self.modo = modo

    def run(self):
        try:
            records = []
            is_pdf = self.file_path.lower().endswith(".pdf")

            if is_pdf:
                if self.modo != "RPP":
                    self.finished.emit(
                        False, {},
                        "El archivo seleccionado es una Constancia de Resolución PDF.\n"
                        "Por favor seleccione la operación '2. Vincular Folios RPP' para procesarlo."
                    )
                    return
                from satc.src.services.rpp_resolution_extractor import RppResolutionExtractor
                raw_extracted = RppResolutionExtractor.extract_from_pdf(self.file_path)
                for r in raw_extracted:
                    records.append({
                        "interior": r["interior"],
                        "edificio": r["edificio"],
                        "nivel": r.get("nivel", ""),
                        "numero_oficial": r.get("numero_oficial", ""),
                        "calle": "",
                        "destino": "HABITACIONAL",
                        "espacio": "VIVIENDA",
                        "folio_electronico": r["folio_electronico"],
                        "clave_catastral": "",
                        "padron": "",
                        "descripcion": f"Folio RPP extraído de Constancia (Frac. #{r['numero_fraccion']})"
                    })
            else:
                wb = openpyxl.load_workbook(self.file_path, data_only=True)
                ws = wb.active
                rows = list(ws.iter_rows(values_only=True))
                if not rows or len(rows) < 2:
                    self.finished.emit(False, {}, "El archivo seleccionado no contiene filas de datos.")
                    return

                raw_headers = [str(h or "").strip().upper() for h in rows[0]]
                def get_col_idx(*names):
                    for name in names:
                        if name.upper() in raw_headers:
                            return raw_headers.index(name.upper())
                    return -1

                idx_int = get_col_idx("INTERIOR", "VIVIENDA", "DEPTO", "DEPARTAMENTO", "CASA")
                idx_ed = get_col_idx("EDIFICIO", "EDIF", "TORRE")
                idx_niv = get_col_idx("NIVEL", "PISO", "PLANTA")
                idx_nof = get_col_idx("NUMERO_OFICIAL", "NO_OFICIAL", "NUMERO_UPE", "NUM_UPE", "UPE")
                idx_calle = get_col_idx("CALLE", "VIALIDAD", "DIRECCION")
                idx_dest = get_col_idx("DESTINO", "USO")
                idx_esp = get_col_idx("ESPACIO", "TIPO_ESPACIO")
                idx_rpp = get_col_idx("FOLIO_ELECTRONICO", "FOLIO_RPP", "RPP")
                idx_cat = get_col_idx("CLAVE_CATASTRAL", "CATASTRO", "CLAVE_CAT")
                idx_pad = get_col_idx("PADRON", "CUENTA_PREDIAL", "PREDIAL")
                idx_desc = get_col_idx("DESCRIPCION", "DESCRIPCIÓN", "NOTAS", "OBSERVACIONES")

                if idx_int == -1:
                    self.finished.emit(
                        False, {},
                        "El archivo debe contener al menos la columna 'INTERIOR' o 'VIVIENDA'."
                    )
                    return

                for row in rows[1:]:
                    if not any(row):
                        continue
                    interior = str(row[idx_int] or "").strip()
                    if not interior:
                        continue

                    ed = str(row[idx_ed] or "").strip() if idx_ed != -1 and row[idx_ed] is not None else ""
                    niv = str(row[idx_niv] or "").strip() if idx_niv != -1 and row[idx_niv] is not None else ""
                    nof = str(row[idx_nof] or "").strip() if idx_nof != -1 and row[idx_nof] is not None else ""
                    calle = str(row[idx_calle] or "").strip() if idx_calle != -1 and row[idx_calle] is not None else ""
                    dest = str(row[idx_dest] or "HABITACIONAL").strip().upper() if idx_dest != -1 and row[idx_dest] is not None else "HABITACIONAL"
                    esp = str(row[idx_esp] or "VIVIENDA").strip().upper() if idx_esp != -1 and row[idx_esp] is not None else "VIVIENDA"
                    rpp = str(row[idx_rpp] or "").strip() if idx_rpp != -1 and row[idx_rpp] is not None else ""
                    cat = str(row[idx_cat] or "").strip() if idx_cat != -1 and row[idx_cat] is not None else ""
                    pad = str(row[idx_pad] or "").strip() if idx_pad != -1 and row[idx_pad] is not None else ""
                    desc = str(row[idx_desc] or "").strip() if idx_desc != -1 and row[idx_desc] is not None else ""

                    records.append({
                        "interior": interior,
                        "edificio": ed,
                        "nivel": niv,
                        "numero_oficial": nof,
                        "calle": calle,
                        "destino": dest,
                        "espacio": esp,
                        "folio_electronico": rpp,
                        "clave_catastral": cat,
                        "padron": pad,
                        "descripcion": desc
                    })

            if not records:
                self.finished.emit(False, {}, "No se detectaron registros con Interior válido.")
                return

            # Validación de UPEs autorizadas vs total en archivo
            tot_upes = 0
            if self.regimen_id:
                if self.api_client.connect_via_api:
                    all_regs = self.api_client.request("GET", "/api/admin/data/satc_regimenes")
                    target = next((r for r in all_regs if r.get("regimen_id") == self.regimen_id), None)
                    tot_upes = target.get("total_upes", 0) if target else 0
                else:
                    with self.db_connector.get_session() as session:
                        svc = HousingLifeCycleService(session)
                        target = svc.regimen_repo.get_by_id(self.regimen_id)
                        tot_upes = target.total_upes if target else 0

                if len(records) > tot_upes:
                    self.finished.emit(
                        False, {},
                        f"El archivo contiene {len(records)} unidades, lo cual SUPERA la capacidad autorizada "
                        f"del Régimen ({tot_upes} UPEs).\n\n"
                        f"Por favor verifique el archivo para no exceder las {tot_upes} UPEs del macro-lote."
                    )
                    return

            # Consultar existentes en BD para marcar si es NUEVO, VINCULABLE o DUPLICADO
            if self.api_client.connect_via_api:
                params = {"desarrollo_id": self.desarrollo_id}
                if self.regimen_id:
                    params["regimen_id"] = self.regimen_id
                v_existentes = self.api_client.request("GET", f"/api/admin/satc/viviendas/{self.desarrollo_id}", data=params)
            else:
                with self.db_connector.get_session() as session:
                    svc = HousingLifeCycleService(session)
                    if self.regimen_id:
                        v_existentes = svc.get_viviendas_by_regimen(self.regimen_id)
                    else:
                        v_existentes = svc.get_viviendas_by_desarrollo(self.desarrollo_id)

            existentes_keys = {
                (
                    (v.get("edificio") or "").strip().upper(),
                    (v.get("interior") or "").strip().upper()
                )
                for v in v_existentes
            }

            # Clasificación de registros y estados
            nuevos_cnt = 0
            duplicados_cnt = 0
            processed_records = []

            for r in records:
                raw_ed = r["edificio"].upper()
                ed_norm = re.sub(r'^(EDIFICIO|TORRE)\s*', '', raw_ed).strip()
                int_norm = r["interior"].upper()

                es_dup = (raw_ed, int_norm) in existentes_keys or (ed_norm, int_norm) in existentes_keys
                if self.modo in ("RPP", "CATASTRO"):
                    if es_dup:
                        status_str = "VINCULABLE"
                        nuevos_cnt += 1
                    else:
                        status_str = "NO ENCONTRADO"
                        duplicados_cnt += 1
                else:
                    if es_dup:
                        status_str = "DUPLICADO"
                        duplicados_cnt += 1
                    else:
                        status_str = "NUEVO"
                        nuevos_cnt += 1

                processed_records.append({
                    "data": r,
                    "status": status_str
                })

            result_data = {
                "records": records,
                "processed_records": processed_records,
                "file_name": os.path.basename(self.file_path),
                "nuevos_cnt": nuevos_cnt,
                "duplicados_cnt": duplicados_cnt,
                "tot_upes": tot_upes
            }
            self.finished.emit(True, result_data, "")
        except Exception as e:
            self.finished.emit(False, {}, str(e))


class ViviendasLoadWorker(QThread):
    """Worker thread para cargar viviendas y capacidad del régimen en segundo plano sin congelar la UI."""
    finished = Signal(bool, dict, str)

    def __init__(self, api_client, db_connector, desarrollo_id: int, regimen_id: Optional[int]):
        super().__init__()
        self.api_client = api_client
        self.db_connector = db_connector
        self.desarrollo_id = desarrollo_id
        self.regimen_id = regimen_id

    def run(self):
        try:
            tot_u = 0
            # 1. Consultar capacidad del régimen si aplica
            if self.regimen_id:
                if self.api_client.connect_via_api:
                    all_regs = self.api_client.request("GET", "/api/admin/data/satc_regimenes")
                    target = next((r for r in all_regs if r.get("regimen_id") == self.regimen_id), None)
                    tot_u = target.get("total_upes", 0) if target else 0
                else:
                    with self.db_connector.get_session() as session:
                        svc = HousingLifeCycleService(session)
                        target = svc.regimen_repo.get_by_id(self.regimen_id)
                        tot_u = target.total_upes if target else 0

            # 2. Consultar viviendas registradas
            if self.api_client.connect_via_api:
                params = {"desarrollo_id": self.desarrollo_id}
                if self.regimen_id:
                    params["regimen_id"] = self.regimen_id
                viviendas = self.api_client.request("GET", f"/api/admin/satc/viviendas/{self.desarrollo_id}", data=params)
            else:
                with self.db_connector.get_session() as session:
                    svc = HousingLifeCycleService(session)
                    if self.regimen_id:
                        viviendas = svc.get_viviendas_by_regimen(self.regimen_id)
                    else:
                        viviendas = svc.get_viviendas_by_desarrollo(self.desarrollo_id)

            res = {
                "viviendas": viviendas,
                "tot_u": tot_u,
                "regimen_id": self.regimen_id,
                "desarrollo_id": self.desarrollo_id
            }
            self.finished.emit(True, res, "")
        except Exception as e:
            self.finished.emit(False, {}, str(e))


class ViviendasImportWorker(QThread):
    """Worker thread para ejecutar la importación y vinculación progresiva sin congelar la interfaz."""
    finished = Signal(bool, dict, str)

    def __init__(self, api_client, db_connector, desarrollo_id: int, regimen_id: Optional[int], records: list, usuario_id: int, sesion_id: Optional[int] = None, modo: str = "INICIAL"):
        super().__init__()
        self.api_client = api_client
        self.db_connector = db_connector
        self.desarrollo_id = desarrollo_id
        self.regimen_id = regimen_id
        self.records = records
        self.usuario_id = usuario_id
        self.sesion_id = sesion_id
        self.modo = modo  # "INICIAL", "RPP", "CATASTRO"

    def run(self):
        try:
            if self.api_client.connect_via_api:
                endpoint = "/api/admin/satc/viviendas/bulk-import"
                if self.modo == "RPP":
                    endpoint = f"/api/admin/satc/viviendas/{self.regimen_id}/vincular-rpp"
                elif self.modo == "CATASTRO":
                    endpoint = f"/api/admin/satc/viviendas/{self.regimen_id}/vincular-catastro"

                payload = {
                    "desarrollo_id": self.desarrollo_id,
                    "regimen_id": self.regimen_id,
                    "usuario_id": self.usuario_id,
                    "sesion_id": self.sesion_id,
                    "records": self.records
                }
                res = self.api_client.request("POST", endpoint, json=payload)
            else:
                with self.db_connector.get_session() as session:
                    svc = HousingLifeCycleService(session)
                    if self.modo == "RPP":
                        res = svc.vincular_folios_rpp_excel(
                            regimen_id=self.regimen_id,
                            records=self.records
                        )
                    elif self.modo == "CATASTRO":
                        res = svc.vincular_catastro_excel(
                            regimen_id=self.regimen_id,
                            records=self.records
                        )
                    else:
                        res = svc.importar_viviendas_excel(
                            desarrollo_id=self.desarrollo_id,
                            records=self.records,
                            regimen_id=self.regimen_id,
                            usuario_id=self.usuario_id,
                            sesion_id=self.sesion_id
                        )
            self.finished.emit(True, res, "")
        except Exception as e:
            self.finished.emit(False, {}, str(e))


class SatcCatalogsView(QWidget):
    """Sub-vista integrada para la administración de catálogos maestros de SATC."""
    action_state_changed = Signal()

    def __init__(self, db_connector, current_user_id, current_sesion_id, can_edit, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.current_user_id = current_user_id
        self.current_sesion_id = current_sesion_id
        self.can_edit = can_edit

        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.desarrollos_list = []
        self._v_loading_dialog: Optional[GLLoadingDialog] = None
        self._build_ui()

    def _build_ui(self):
        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("seamlessTabWidget")
        self.tabs.tabBar().setVisible(False)
        self.layout.addWidget(self.tabs)

        # ---------------------------------------------------------
        # Pestaña 1: Tipos de Trámite Municipal
        # ---------------------------------------------------------
        self.tab_tipos = QWidget()
        lay_tipos = QHBoxLayout(self.tab_tipos)
        lay_tipos.setContentsMargins(0, 0, 0, 0)
        self.tbl_tipos = CrudTablePanel("Catálogo de Tipos de Trámite SATC")
        self.tbl_tipos.setup_table(
            ["ID", "Código", "Nombre", "Aplica A", "Etapa Disparador", "Vigencia (Días)", "Obligatorio", "Estado"],
            ["tipo_tramite_id", "codigo", "nombre", "aplica_a", "etapa_disparador", "dias_vigencia", "es_obligatorio", "activo"]
        )
        self.tbl_tipos.add_requested.connect(self._on_new_tipo)
        self.tbl_tipos.edit_requested.connect(self._on_edit_tipo)
        self.tbl_tipos.btn_add.setVisible(self.can_edit)
        self.tbl_tipos.btn_edit.setVisible(self.can_edit)
        lay_tipos.addWidget(self.tbl_tipos)
        self.tabs.addTab(self.tab_tipos, "Tipos de Trámite")

        # ---------------------------------------------------------
        # Pestaña 2: Estados de Trámite
        # ---------------------------------------------------------
        self.tab_est_tramite = QWidget()
        lay_est_tramite = QHBoxLayout(self.tab_est_tramite)
        lay_est_tramite.setContentsMargins(0, 0, 0, 0)
        self.tbl_est_tramite = CrudTablePanel("Estados de Trámite SATC")
        self.tbl_est_tramite.setup_table(
            ["ID", "Código", "Nombre", "Fase", "Bloqueante", "Terminal", "Estado"],
            ["estado_tramite_id", "codigo", "nombre", "fase", "es_bloqueante", "es_terminal", "activo"]
        )
        self.tbl_est_tramite.add_requested.connect(self._on_new_est_tramite)
        self.tbl_est_tramite.edit_requested.connect(self._on_edit_est_tramite)
        self.tbl_est_tramite.btn_add.setVisible(self.can_edit)
        self.tbl_est_tramite.btn_edit.setVisible(self.can_edit)
        lay_est_tramite.addWidget(self.tbl_est_tramite)
        self.tabs.addTab(self.tab_est_tramite, "Estados de Trámite")

        # ---------------------------------------------------------
        # Pestaña 3: Estados de Vivienda (Ciclo Físico-Comercial)
        # ---------------------------------------------------------
        self.tab_est_vivienda = QWidget()
        lay_est_vivienda = QHBoxLayout(self.tab_est_vivienda)
        lay_est_vivienda.setContentsMargins(0, 0, 0, 0)
        self.tbl_est_vivienda = CrudTablePanel("Estados de Vivienda / UPE")
        self.tbl_est_vivienda.setup_table(
            ["ID", "Código", "Nombre", "Descripción", "Orden", "Permite Venta", "Permite Escrituración", "Estado"],
            ["estado_vivienda_id", "codigo", "nombre", "descripcion", "orden_flujo", "permite_venta", "permite_escrituracion", "activo"]
        )
        self.tbl_est_vivienda.add_requested.connect(self._on_new_est_vivienda)
        self.tbl_est_vivienda.edit_requested.connect(self._on_edit_est_vivienda)
        self.tbl_est_vivienda.btn_add.setVisible(self.can_edit)
        self.tbl_est_vivienda.btn_edit.setVisible(self.can_edit)
        lay_est_vivienda.addWidget(self.tbl_est_vivienda)
        self.tabs.addTab(self.tab_est_vivienda, "Estados de Vivienda")

        # ---------------------------------------------------------
        # Pestaña 4: Regímenes mz
        # ---------------------------------------------------------
        self.tab_regimenes = QWidget()
        lay_regimenes = QHBoxLayout(self.tab_regimenes)
        lay_regimenes.setContentsMargins(0, 0, 0, 0)
        self.tbl_regimenes = CrudTablePanel("Regímenes mz")
        self.tbl_regimenes.setup_table(
            ["ID", "Desarrollo", "Nombre Régimen", "SM", "MZ", "LT", "Total UPEs", "Generadas", "Licencia Matriz", "Clave Catastral", "Estado"],
            ["regimen_id", "desarrollo_nombre", "nombre_regimen", "sm", "mz", "lt", "total_upes", "upes_generadas", "licencia_construccion_matriz", "clave_catastral_matriz", "activo"]
        )
        self.tbl_regimenes.add_requested.connect(self._on_new_regimen)
        self.tbl_regimenes.edit_requested.connect(self._on_edit_regimen)
        self.tbl_regimenes.btn_add.setVisible(self.can_edit)
        self.tbl_regimenes.btn_edit.setVisible(self.can_edit)
        lay_regimenes.addWidget(self.tbl_regimenes)
        self.tabs.addTab(self.tab_regimenes, "Regímenes mz")

        # ---------------------------------------------------------
        # Pestaña 5: Importación y Padrón de Viviendas
        # ---------------------------------------------------------
        self.tab_import_viviendas = QWidget()
        lay_import_viv = QVBoxLayout(self.tab_import_viviendas)
        lay_import_viv.setContentsMargins(12, 12, 12, 12)
        lay_import_viv.setSpacing(12)

        # 1. Barra de filtros y controles (Elástica y adaptativa a pantallas pequeñas)
        ctl_box = QHBoxLayout()
        ctl_box.setSpacing(10)

        ctl_box.addWidget(CustomLabel("Desarrollo *:", variant="body"))
        self.cmb_v_desarrollo = CustomComboBox()
        self.cmb_v_desarrollo.setMinimumWidth(160)
        self.cmb_v_desarrollo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.cmb_v_desarrollo.currentIndexChanged.connect(self._on_v_desarrollo_changed)
        ctl_box.addWidget(self.cmb_v_desarrollo, 1)

        ctl_box.addWidget(CustomLabel("Régimen *:", variant="body"))
        self.cmb_v_regimen = CustomComboBox()
        self.cmb_v_regimen.setMinimumWidth(180)
        self.cmb_v_regimen.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.cmb_v_regimen.currentIndexChanged.connect(self._on_v_regimen_changed)
        ctl_box.addWidget(self.cmb_v_regimen, 1)

        ctl_box.addWidget(CustomLabel("Operación:", variant="body"))
        self.cmb_v_modo = CustomComboBox()
        self.cmb_v_modo.setMinimumWidth(180)
        self.cmb_v_modo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.cmb_v_modo.addItem("-- Selecciona Operación --", None)
        self.cmb_v_modo.addItem("1. Carga Inicial (Física)", "INICIAL")
        self.cmb_v_modo.addItem("2. Vincular Folios RPP", "RPP")
        self.cmb_v_modo.addItem("3. Vincular Cédula / Catastro", "CATASTRO")
        self.cmb_v_modo.currentIndexChanged.connect(self._on_v_modo_changed)
        ctl_box.addWidget(self.cmb_v_modo)

        ctl_box.addStretch()

        # Botones operativos desacoplados (sus acciones se invocan desde la Toolbar superior)
        self.btn_v_plantilla = CustomButton("Plantilla Excel", is_secondary=True, icon_name="excel")
        self.btn_v_plantilla.clicked.connect(self._on_v_descargar_plantilla)
        self.btn_v_plantilla.hide()

        self.btn_v_seleccionar = CustomButton("Cargar Archivo", is_secondary=True, icon_name="documento_cargar")
        self.btn_v_seleccionar.clicked.connect(self._on_v_seleccionar_archivo)
        self.btn_v_seleccionar.hide()

        self.btn_v_exportar_datos = CustomButton("Exportar Datos", is_secondary=True, icon_name="excel")
        self.btn_v_exportar_datos.clicked.connect(self._on_v_exportar_datos)
        self.btn_v_exportar_datos.setEnabled(False)
        self.btn_v_exportar_datos.hide()

        self.btn_v_limpiar = CustomButton("Limpiar", is_secondary=True, icon_name="cancelar")
        self.btn_v_limpiar.clicked.connect(self._on_v_limpiar)
        self.btn_v_limpiar.hide()

        self.btn_v_ejecutar = CustomButton("Aplicar Cambios", icon_name="guardar")
        self.btn_v_ejecutar.clicked.connect(self._on_v_ejecutar_importacion)
        self.btn_v_ejecutar.setEnabled(False)
        self.btn_v_ejecutar.setVisible(self.can_edit)
        self.btn_v_ejecutar.hide()

        lay_import_viv.addLayout(ctl_box)

        # 2. Information Row / Metrics Bar (Limpio, transparente, perfectamente distribuido y uniforme)
        self.kpi_v_frame = QFrame()
        self.kpi_v_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        kpi_lay = QHBoxLayout(self.kpi_v_frame)
        kpi_lay.setContentsMargins(0, 4, 0, 4)
        kpi_lay.setSpacing(6)

        def _make_metric_dot(color_val: str) -> QLabel:
            dot = QLabel()
            dot.setFixedSize(10, 10)
            dot.setStyleSheet(f"background-color: {color_val}; border-radius: 5px; border: none;")
            return dot

        # Puntos indicadores de color (Atomic Design: Tokens de Colors)
        self.dot_vkpi_total = _make_metric_dot(Colors.TEXT_LIGHT_MUTED)
        self.lbl_vkpi_total_arch = CustomLabel("En Archivo: 0", variant="body")

        self.dot_vkpi_nuevos = _make_metric_dot(Colors.SUCCESS)
        self.lbl_vkpi_nuevos = CustomLabel("Nuevos / Vinculables: 0", variant="body")

        self.dot_vkpi_duplicados = _make_metric_dot(Colors.ERROR)
        self.lbl_vkpi_duplicados = CustomLabel("Duplicados / Sin Coincidencia: 0", variant="body")

        self.dot_vkpi_regimen = _make_metric_dot(Colors.ACCENT_VIOLET)
        self.lbl_vkpi_regimen_info = CustomLabel("Total UPE: N/A", variant="body")

        self.dot_vkpi_bd = _make_metric_dot(Colors.ACCENT)
        self.lbl_vkpi_bd = CustomLabel("EnBD: 0", variant="body")

        self.dot_vkpi_rpp = _make_metric_dot(Colors.WARNING)
        self.lbl_vkpi_con_rpp = CustomLabel("Con Folio: 0", variant="body")

        self.dot_vkpi_catastro = _make_metric_dot(Colors.SUCCESS)
        self.lbl_vkpi_con_catastro = CustomLabel("Con CC: 0", variant="body")

        # Layout equitativo y balanceado de manera uniforme sin hueco central
        kpi_lay.addWidget(self.dot_vkpi_total)
        kpi_lay.addWidget(self.lbl_vkpi_total_arch)
        kpi_lay.addSpacing(16)

        kpi_lay.addWidget(self.dot_vkpi_nuevos)
        kpi_lay.addWidget(self.lbl_vkpi_nuevos)
        kpi_lay.addSpacing(16)

        kpi_lay.addWidget(self.dot_vkpi_duplicados)
        kpi_lay.addWidget(self.lbl_vkpi_duplicados)
        kpi_lay.addSpacing(16)

        kpi_lay.addWidget(self.dot_vkpi_regimen)
        kpi_lay.addWidget(self.lbl_vkpi_regimen_info)
        kpi_lay.addSpacing(16)

        kpi_lay.addWidget(self.dot_vkpi_bd)
        kpi_lay.addWidget(self.lbl_vkpi_bd)
        kpi_lay.addSpacing(16)

        kpi_lay.addWidget(self.dot_vkpi_rpp)
        kpi_lay.addWidget(self.lbl_vkpi_con_rpp)
        kpi_lay.addSpacing(16)

        kpi_lay.addWidget(self.dot_vkpi_catastro)
        kpi_lay.addWidget(self.lbl_vkpi_con_catastro)

        kpi_lay.addStretch()

        lay_import_viv.addWidget(self.kpi_v_frame)

        # 3. Contenedor de Tarjeta Estandarizada y Tabla (Atomic Design: CustomCard)
        self.card_viviendas = CustomCard("Padrón e Importación de Viviendas", parent=self)
        self.card_viviendas.setObjectName("cardFrame")

        # Indicador de archivo cargado adjunto al título de la tabla
        self.lbl_v_sep = CustomLabel("|", variant="muted")
        self.lbl_v_sep.setStyleSheet("color: #94A3B8; font-size: 14px; font-weight: normal; margin: 0 4px;")
        self.card_viviendas.add_header_widget(self.lbl_v_sep)

        self.lbl_vkpi_archivo = CustomLabel("Archivo: Ninguno", variant="muted")
        self.lbl_vkpi_archivo.setStyleSheet("font-size: 12px; color: #64748B; font-weight: normal;")
        self.card_viviendas.add_header_widget(self.lbl_vkpi_archivo)

        # Campo Buscar alineado al encabezado de la tabla (Homologado con GlCrudTable)
        self.search_viviendas_input = CustomInput(control_size="md", parent=self)
        self.search_viviendas_input.setObjectName("viviendasSearchInput")
        self.search_viviendas_input.setPlaceholderText("Buscar en padrón...")
        self.search_viviendas_input.setMinimumWidth(220)
        self.search_viviendas_input.setMaximumWidth(320)
        self.search_viviendas_input.setClearButtonEnabled(True)
        self.search_viviendas_input.addAction(Icons.search("#64748B"), QLineEdit.LeadingPosition)
        self.search_viviendas_input.textChanged.connect(self._on_search_viviendas_text_changed)
        self.card_viviendas.add_header_widget(self.search_viviendas_input)

        self.tbl_viviendas = QTableWidget()
        self.tbl_viviendas.setColumnCount(13)
        self.tbl_viviendas.setHorizontalHeaderLabels([
            "Estado Carga", "Régimen Matriz", "No. Oficial", "Interior", "Edificio", "Nivel", 
            "Destino", "Espacio", "Folio RPP", "Clave Catastral", "Padrón", "Calle", "Notas"
        ])
        self.tbl_viviendas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tbl_viviendas.horizontalHeader().setStretchLastSection(True)
        self.tbl_viviendas.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_viviendas.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_viviendas.setShowGrid(False)
        self.tbl_viviendas.verticalHeader().setVisible(False)
        self.tbl_viviendas.verticalHeader().setDefaultSectionSize(26)
        
        self.card_viviendas.layout.addWidget(self.tbl_viviendas)
        lay_import_viv.addWidget(self.card_viviendas)

        self.tabs.addTab(self.tab_import_viviendas, "Importación de Viviendas")

        self._v_parsed_records = []
        self._v_worker = None
        self._v_load_worker = None

    # =========================================================================
    # 1. DIALOGOS & ACCIONES: TIPO DE TRÁMITE
    # =========================================================================
    def _create_tipo_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        dialog.setMinimumWidth(560)

        card = QFrame(dialog)
        card.setObjectName("card_tipo")
        card.setStyleSheet(f"""
            QFrame#card_tipo {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        lbl = CustomLabel("📄 CONFIGURACIÓN DE TIPO DE TRÁMITE", variant="subheader")
        lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay.addWidget(lbl)

        form = QFormLayout()
        form.setSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)

        self.inp_t_codigo = CustomInput("Código único (ej. LICENCIA_CONSTRUCCION)", parent=card)
        self.inp_t_codigo.setMaxLength(50)
        self.inp_t_codigo.textEdited.connect(lambda t: self.inp_t_codigo.setText(t.upper()))
        self.inp_t_codigo.text = self.inp_t_codigo.text
        self.inp_t_codigo.set_text = self.inp_t_codigo.setText
        self.inp_t_codigo.set_focus = self.inp_t_codigo.setFocus

        self.inp_t_nombre = CustomInput("Nombre del trámite municipal", parent=card)
        self.inp_t_nombre.setMaxLength(200)
        self.inp_t_nombre.text = self.inp_t_nombre.text
        self.inp_t_nombre.set_text = self.inp_t_nombre.setText

        self.cmb_t_aplica = CustomComboBox(parent=card)
        self.cmb_t_aplica.add_items(["AMBOS", "REGIMEN_MATRIZ", "VIVIENDA_INDIVIDUAL"])

        self.cmb_t_etapa = CustomComboBox(parent=card)
        self.cmb_t_etapa.add_items(["CONSTRUCCION", "VENTA", "ESCRITURACION"])

        self.inp_t_vigencia = CustomInput("Días de vigencia (0 = Indefinida)", parent=card)
        self.inp_t_vigencia.setMaxLength(6)
        self.inp_t_vigencia.text = self.inp_t_vigencia.text
        self.inp_t_vigencia.set_text = self.inp_t_vigencia.setText

        self.chk_t_obligatorio = CustomCheckBox("Obligatorio (Bloquea fases subsecuentes)", parent=card)
        self.chk_t_obligatorio.setChecked(True)

        self.chk_t_activo = CustomCheckBox("Activo", parent=card)
        self.chk_t_activo.setChecked(True)

        form.addRow("Código *:", self.inp_t_codigo)
        form.addRow("Nombre *:", self.inp_t_nombre)
        form.addRow("Aplica A *:", self.cmb_t_aplica)
        form.addRow("Etapa Disparador *:", self.cmb_t_etapa)
        form.addRow("Vigencia (Días):", self.inp_t_vigencia)
        form.addRow("", self.chk_t_obligatorio)
        form.addRow("", self.chk_t_activo)

        lay.addLayout(form)
        dialog.add_widget(card)

        def _val():
            c = self.inp_t_codigo.text().strip()
            n = self.inp_t_nombre.text().strip()
            dialog.btn_save.setEnabled(bool(c and n))

        self.inp_t_codigo.textChanged.connect(_val)
        self.inp_t_nombre.textChanged.connect(_val)
        _val()

        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_t_codigo.setReadOnly(True)
            self.inp_t_nombre.setReadOnly(True)
            self.inp_t_vigencia.setReadOnly(True)

        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_tipo(dialog))
        return dialog

    def _on_new_tipo(self):
        self.current_tipo_id = None
        dialog = self._create_tipo_dialog("Nuevo Tipo de Trámite")
        self.inp_t_vigencia.set_text("0")
        self.inp_t_codigo.set_focus()
        dialog.exec()

    def _on_edit_tipo(self, data: dict):
        self.current_tipo_id = data.get("tipo_tramite_id")
        dialog = self._create_tipo_dialog(f"Editar Tipo de Trámite: {data.get('codigo')}")
        self.inp_t_codigo.set_text(data.get("codigo", "") or "")
        self.inp_t_nombre.set_text(data.get("nombre", "") or "")
        self.cmb_t_aplica.set_current_text(data.get("aplica_a", "AMBOS"))
        self.cmb_t_etapa.set_current_text(data.get("etapa_disparador", "CONSTRUCCION"))
        self.inp_t_vigencia.set_text(str(data.get("dias_vigencia", 0) or 0))
        self.chk_t_obligatorio.setChecked(bool(data.get("es_obligatorio", True)))
        self.chk_t_activo.setChecked(bool(data.get("activo", True)))
        self.inp_t_codigo.setReadOnly(True)  # Clave inmutable
        self.inp_t_nombre.set_focus()
        dialog.exec()

    def _save_tipo(self, dialog: CustomDialog):
        data = {
            "tipo_tramite_id": self.current_tipo_id,
            "codigo": self.inp_t_codigo.text().strip().upper(),
            "nombre": self.inp_t_nombre.text().strip(),
            "aplica_a": self.cmb_t_aplica.currentText(),
            "etapa_disparador": self.cmb_t_etapa.currentText(),
            "dias_vigencia": int(self.inp_t_vigencia.text().strip() or 0),
            "es_obligatorio": self.chk_t_obligatorio.isChecked(),
            "activo": self.chk_t_activo.isChecked()
        }
        try:
            if self.api_client.connect_via_api:
                payload = {"usuario_id": self.current_user_id, "sesion_id": self.current_sesion_id, "data": data}
                self.api_client.request("POST", "/api/admin/save/satc_tipos_tramite", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    svc = HousingLifeCycleService(session)
                    svc.save_tipo_tramite(data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Tipo de trámite guardado correctamente.")
            dialog.accept()
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # =========================================================================
    # 2. DIALOGOS & ACCIONES: ESTADOS DE TRÁMITE
    # =========================================================================
    def _create_est_tramite_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        dialog.setMinimumWidth(540)

        card = QFrame(dialog)
        card.setObjectName("card_est_tramite")
        card.setStyleSheet(f"""
            QFrame#card_est_tramite {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        lbl = CustomLabel("🚦 ESTADO DE TRÁMITE OPERATIVO", variant="subheader")
        lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay.addWidget(lbl)

        form = QFormLayout()
        form.setSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)

        self.inp_et_codigo = CustomInput("Código único (ej. INGRESADO_MUNICIPIO)", parent=card)
        self.inp_et_codigo.setMaxLength(50)
        self.inp_et_codigo.textEdited.connect(lambda t: self.inp_et_codigo.setText(t.upper()))
        self.inp_et_codigo.text = self.inp_et_codigo.text
        self.inp_et_codigo.set_text = self.inp_et_codigo.setText
        self.inp_et_codigo.set_focus = self.inp_et_codigo.setFocus

        self.inp_et_nombre = CustomInput("Nombre descriptivo del estado", parent=card)
        self.inp_et_nombre.setMaxLength(100)
        self.inp_et_nombre.text = self.inp_et_nombre.text
        self.inp_et_nombre.set_text = self.inp_et_nombre.setText

        self.cmb_et_fase = CustomComboBox(parent=card)
        self.cmb_et_fase.add_items(["PREVENTIVA", "DOCUMENTAL", "OPERATIVA", "AUTOMATIZADA", "FINANCIERA", "CIERRE"])

        self.chk_et_bloqueante = CustomCheckBox("Semáforo Bloqueante (Impide continuar sin solventar)", parent=card)
        self.chk_et_bloqueante.setChecked(True)

        self.chk_et_terminal = CustomCheckBox("Estado Terminal (Concluye el ciclo de vida del trámite)", parent=card)
        self.chk_et_terminal.setChecked(False)

        self.chk_et_activo = CustomCheckBox("Activo", parent=card)
        self.chk_et_activo.setChecked(True)

        form.addRow("Código *:", self.inp_et_codigo)
        form.addRow("Nombre *:", self.inp_et_nombre)
        form.addRow("Fase Operativa *:", self.cmb_et_fase)
        form.addRow("", self.chk_et_bloqueante)
        form.addRow("", self.chk_et_terminal)
        form.addRow("", self.chk_et_activo)

        lay.addLayout(form)
        dialog.add_widget(card)

        def _val():
            c = self.inp_et_codigo.text().strip()
            n = self.inp_et_nombre.text().strip()
            dialog.btn_save.setEnabled(bool(c and n))

        self.inp_et_codigo.textChanged.connect(_val)
        self.inp_et_nombre.textChanged.connect(_val)
        _val()

        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_et_codigo.setReadOnly(True)
            self.inp_et_nombre.setReadOnly(True)

        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_est_tramite(dialog))
        return dialog

    def _on_new_est_tramite(self):
        self.current_est_tramite_id = None
        dialog = self._create_est_tramite_dialog("Nuevo Estado de Trámite")
        self.inp_et_codigo.set_focus()
        dialog.exec()

    def _on_edit_est_tramite(self, data: dict):
        self.current_est_tramite_id = data.get("estado_tramite_id")
        dialog = self._create_est_tramite_dialog(f"Editar Estado: {data.get('codigo')}")
        self.inp_et_codigo.set_text(data.get("codigo", "") or "")
        self.inp_et_nombre.set_text(data.get("nombre", "") or "")
        self.cmb_et_fase.set_current_text(data.get("fase", "OPERATIVA"))
        self.chk_et_bloqueante.setChecked(bool(data.get("es_bloqueante", True)))
        self.chk_et_terminal.setChecked(bool(data.get("es_terminal", False)))
        self.chk_et_activo.setChecked(bool(data.get("activo", True)))
        self.inp_et_codigo.setReadOnly(True)
        self.inp_et_nombre.set_focus()
        dialog.exec()

    def _save_est_tramite(self, dialog: CustomDialog):
        data = {
            "estado_tramite_id": self.current_est_tramite_id,
            "codigo": self.inp_et_codigo.text().strip().upper(),
            "nombre": self.inp_et_nombre.text().strip(),
            "fase": self.cmb_et_fase.currentText(),
            "es_bloqueante": self.chk_et_bloqueante.isChecked(),
            "es_terminal": self.chk_et_terminal.isChecked(),
            "activo": self.chk_et_activo.isChecked()
        }
        try:
            if self.api_client.connect_via_api:
                payload = {"usuario_id": self.current_user_id, "sesion_id": self.current_sesion_id, "data": data}
                self.api_client.request("POST", "/api/admin/save/satc_estados_tramite", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    svc = HousingLifeCycleService(session)
                    svc.save_estado_tramite(data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Estado de trámite guardado correctamente.")
            dialog.accept()
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # =========================================================================
    # 3. DIALOGOS & ACCIONES: ESTADOS DE VIVIENDA
    # =========================================================================
    def _create_est_vivienda_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        dialog.setMinimumWidth(540)

        card = QFrame(dialog)
        card.setObjectName("card_est_vivienda")
        card.setStyleSheet(f"""
            QFrame#card_est_vivienda {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        lbl = CustomLabel("🏠 CICLO FÍSICO-COMERCIAL DE LA VIVIENDA", variant="subheader")
        lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay.addWidget(lbl)

        form = QFormLayout()
        form.setSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)

        self.inp_ev_codigo = CustomInput("Código único (ej. EN_INDIVIDUALIZACION)", parent=card)
        self.inp_ev_codigo.setMaxLength(50)
        self.inp_ev_codigo.textEdited.connect(lambda t: self.inp_ev_codigo.setText(t.upper()))
        self.inp_ev_codigo.text = self.inp_ev_codigo.text
        self.inp_ev_codigo.set_text = self.inp_ev_codigo.setText
        self.inp_ev_codigo.set_focus = self.inp_ev_codigo.setFocus

        self.inp_ev_nombre = CustomInput("Nombre del estado", parent=card)
        self.inp_ev_nombre.setMaxLength(100)
        self.inp_ev_nombre.text = self.inp_ev_nombre.text
        self.inp_ev_nombre.set_text = self.inp_ev_nombre.setText

        self.inp_ev_desc = CustomInput("Descripción u observaciones", parent=card)
        self.inp_ev_desc.setMaxLength(250)
        self.inp_ev_desc.text = self.inp_ev_desc.text
        self.inp_ev_desc.set_text = self.inp_ev_desc.setText

        self.inp_ev_orden = CustomInput("Orden secuencial de flujo (1 a 10)", parent=card)
        self.inp_ev_orden.setMaxLength(3)
        self.inp_ev_orden.text = self.inp_ev_orden.text
        self.inp_ev_orden.set_text = self.inp_ev_orden.setText

        self.chk_ev_venta = CustomCheckBox("Habilita Permiso de Venta", parent=card)
        self.chk_ev_escrituracion = CustomCheckBox("Habilita Permiso de Escrituración", parent=card)
        self.chk_ev_activo = CustomCheckBox("Activo", parent=card)
        self.chk_ev_activo.setChecked(True)

        form.addRow("Código *:", self.inp_ev_codigo)
        form.addRow("Nombre *:", self.inp_ev_nombre)
        form.addRow("Descripción:", self.inp_ev_desc)
        form.addRow("Orden Flujo *:", self.inp_ev_orden)
        form.addRow("", self.chk_ev_venta)
        form.addRow("", self.chk_ev_escrituracion)
        form.addRow("", self.chk_ev_activo)

        lay.addLayout(form)
        dialog.add_widget(card)

        def _val():
            c = self.inp_ev_codigo.text().strip()
            n = self.inp_ev_nombre.text().strip()
            dialog.btn_save.setEnabled(bool(c and n))

        self.inp_ev_codigo.textChanged.connect(_val)
        self.inp_ev_nombre.textChanged.connect(_val)
        _val()

        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_ev_codigo.setReadOnly(True)
            self.inp_ev_nombre.setReadOnly(True)
            self.inp_ev_orden.setReadOnly(True)

        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_est_vivienda(dialog))
        return dialog

    def _on_new_est_vivienda(self):
        self.current_est_vivienda_id = None
        dialog = self._create_est_vivienda_dialog("Nuevo Estado de Vivienda")
        self.inp_ev_orden.set_text("1")
        self.inp_ev_codigo.set_focus()
        dialog.exec()

    def _on_edit_est_vivienda(self, data: dict):
        self.current_est_vivienda_id = data.get("estado_vivienda_id")
        dialog = self._create_est_vivienda_dialog(f"Editar Estado: {data.get('codigo')}")
        self.inp_ev_codigo.set_text(data.get("codigo", "") or "")
        self.inp_ev_nombre.set_text(data.get("nombre", "") or "")
        self.inp_ev_desc.set_text(data.get("descripcion", "") or "")
        self.inp_ev_orden.set_text(str(data.get("orden_flujo", 1) or 1))
        self.chk_ev_venta.setChecked(bool(data.get("permite_venta", False)))
        self.chk_ev_escrituracion.setChecked(bool(data.get("permite_escrituracion", False)))
        self.chk_ev_activo.setChecked(bool(data.get("activo", True)))
        self.inp_ev_codigo.setReadOnly(True)
        self.inp_ev_nombre.set_focus()
        dialog.exec()

    def _save_est_vivienda(self, dialog: CustomDialog):
        data = {
            "estado_vivienda_id": self.current_est_vivienda_id,
            "codigo": self.inp_ev_codigo.text().strip().upper(),
            "nombre": self.inp_ev_nombre.text().strip(),
            "descripcion": self.inp_ev_desc.text().strip(),
            "orden_flujo": int(self.inp_ev_orden.text().strip() or 1),
            "permite_venta": self.chk_ev_venta.isChecked(),
            "permite_escrituracion": self.chk_ev_escrituracion.isChecked(),
            "activo": self.chk_ev_activo.isChecked()
        }
        try:
            if self.api_client.connect_via_api:
                payload = {"usuario_id": self.current_user_id, "sesion_id": self.current_sesion_id, "data": data}
                self.api_client.request("POST", "/api/admin/save/satc_estados_vivienda", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    svc = HousingLifeCycleService(session)
                    svc.save_estado_vivienda(data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Estado de vivienda guardado correctamente.")
            dialog.accept()
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # =========================================================================
    # 4. DIALOGOS & ACCIONES: REGÍMENES MZ
    # =========================================================================
    def _create_regimen_dialog(self, title: str) -> CustomDialog:
        dialog = CustomDialog(title, self)
        dialog.setMinimumWidth(580)

        card = QFrame(dialog)
        card.setObjectName("card_regimen")
        card.setStyleSheet(f"""
            QFrame#card_regimen {{
                background-color: {Colors.SLATE_50};
                border: 1px solid {Colors.SLATE_200};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        lbl = CustomLabel("🏢 MACRO-LOTE DE RÉGIMEN MZ", variant="subheader")
        lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay.addWidget(lbl)

        form = QFormLayout()
        form.setSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)

        self.cmb_r_desarrollo = CustomComboBox(parent=card)
        self.cmb_r_desarrollo.addItem("-- Selecciona un Desarrollo --", None)
        for des in self.desarrollos_list:
            self.cmb_r_desarrollo.addItem(des.get("nombre", ""), des.get("desarrollo_id"))

        self.inp_r_nombre = CustomInput("Nombre del régimen (ej. REGIMEN AURA NOVA PLAYA)", parent=card)
        self.inp_r_nombre.setMaxLength(200)
        self.inp_r_nombre.text = self.inp_r_nombre.text
        self.inp_r_nombre.set_text = self.inp_r_nombre.setText
        self.inp_r_nombre.set_focus = self.inp_r_nombre.setFocus

        self.inp_r_sm = CustomInput("Super Manzana (ej. SM-115 / Opcional)", parent=card)
        self.inp_r_sm.setMaxLength(50)
        self.inp_r_sm.text = self.inp_r_sm.text
        self.inp_r_sm.set_text = self.inp_r_sm.setText

        self.inp_r_mz = CustomInput("Manzana (ej. MZ-01)", parent=card)
        self.inp_r_mz.setMaxLength(50)
        self.inp_r_mz.text = self.inp_r_mz.text
        self.inp_r_mz.set_text = self.inp_r_mz.setText

        self.inp_r_lt = CustomInput("Lote matriz (ej. LT-01)", parent=card)
        self.inp_r_lt.setMaxLength(50)
        self.inp_r_lt.text = self.inp_r_lt.text
        self.inp_r_lt.set_text = self.inp_r_lt.setText

        self.inp_r_upes = CustomInput("Total de UPEs autorizadas (ej. 577)", parent=card)
        self.inp_r_upes.setMaxLength(6)
        self.inp_r_upes.text = self.inp_r_upes.text
        self.inp_r_upes.set_text = self.inp_r_upes.setText

        self.inp_r_licencia = CustomInput("Licencia de construcción matriz (Opcional)", parent=card)
        self.inp_r_licencia.setMaxLength(100)
        self.inp_r_licencia.text = self.inp_r_licencia.text
        self.inp_r_licencia.set_text = self.inp_r_licencia.setText

        self.inp_r_clave = CustomInput("Clave catastral matriz (Opcional)", parent=card)
        self.inp_r_clave.setMaxLength(100)
        self.inp_r_clave.text = self.inp_r_clave.text
        self.inp_r_clave.set_text = self.inp_r_clave.setText

        self.chk_r_activo = CustomCheckBox("Activo", parent=card)
        self.chk_r_activo.setChecked(True)

        form.addRow("Desarrollo *:", self.cmb_r_desarrollo)
        form.addRow("Nombre Régimen *:", self.inp_r_nombre)
        form.addRow("S.M.:", self.inp_r_sm)
        form.addRow("Manzana *:", self.inp_r_mz)
        form.addRow("Lote Matriz *:", self.inp_r_lt)
        form.addRow("Total UPEs *:", self.inp_r_upes)
        form.addRow("Licencia Matriz:", self.inp_r_licencia)
        form.addRow("Clave Matriz:", self.inp_r_clave)
        form.addRow("", self.chk_r_activo)

        lay.addLayout(form)
        dialog.add_widget(card)

        def _val():
            d = self.cmb_r_desarrollo.currentData()
            n = self.inp_r_nombre.text().strip()
            mz = self.inp_r_mz.text().strip()
            lt = self.inp_r_lt.text().strip()
            u = self.inp_r_upes.text().strip()
            dialog.btn_save.setEnabled(bool(d and n and mz and lt and u))

        self.cmb_r_desarrollo.currentIndexChanged.connect(_val)
        self.inp_r_nombre.textChanged.connect(_val)
        self.inp_r_mz.textChanged.connect(_val)
        self.inp_r_lt.textChanged.connect(_val)
        self.inp_r_upes.textChanged.connect(_val)
        _val()

        if not self.can_edit:
            dialog.btn_save.setVisible(False)
            self.inp_r_nombre.setReadOnly(True)
            self.inp_r_mz.setReadOnly(True)
            self.inp_r_lt.setReadOnly(True)
            self.inp_r_upes.setReadOnly(True)

        dialog.btn_save.clicked.disconnect()
        dialog.btn_save.clicked.connect(lambda: self._save_regimen(dialog))
        return dialog

    def _on_new_regimen(self):
        self.current_regimen_id = None
        dialog = self._create_regimen_dialog("Nuevo Régimen mz")
        self.cmb_r_desarrollo.setCurrentIndex(0)
        self.inp_r_upes.set_text("1")
        self.inp_r_nombre.set_focus()
        dialog.exec()

    def _on_edit_regimen(self, data: dict):
        self.current_regimen_id = data.get("regimen_id")
        dialog = self._create_regimen_dialog(f"Editar Régimen: {data.get('nombre_regimen')}")
        self.inp_r_nombre.set_text(data.get("nombre_regimen", "") or "")
        self.inp_r_sm.set_text(data.get("sm", "") or "")
        self.inp_r_mz.set_text(data.get("mz", "") or "")
        self.inp_r_lt.set_text(data.get("lt", "") or "")
        self.inp_r_upes.set_text(str(data.get("total_upes", 1) or 1))
        self.inp_r_licencia.set_text(data.get("licencia_construccion_matriz", "") or "")
        self.inp_r_clave.set_text(data.get("clave_catastral_matriz", "") or "")
        self.chk_r_activo.setChecked(bool(data.get("activo", True)))

        des_id = data.get("desarrollo_id")
        if des_id:
            idx = self.cmb_r_desarrollo.findData(des_id)
            if idx >= 0:
                self.cmb_r_desarrollo.setCurrentIndex(idx)

        self.inp_r_nombre.set_focus()
        dialog.exec()

    def _save_regimen(self, dialog: CustomDialog):
        des_id = self.cmb_r_desarrollo.currentData()
        if not des_id:
            QMessageBox.warning(self, "Validación", "Debe seleccionar un desarrollo.")
            return

        data = {
            "regimen_id": self.current_regimen_id,
            "desarrollo_id": int(des_id),
            "nombre_regimen": self.inp_r_nombre.text().strip(),
            "sm": self.inp_r_sm.text().strip() or None,
            "mz": self.inp_r_mz.text().strip(),
            "lt": self.inp_r_lt.text().strip(),
            "total_upes": int(self.inp_r_upes.text().strip() or 1),
            "licencia_construccion_matriz": self.inp_r_licencia.text().strip() or None,
            "clave_catastral_matriz": self.inp_r_clave.text().strip() or None,
            "activo": self.chk_r_activo.isChecked()
        }
        try:
            if self.api_client.connect_via_api:
                payload = {"usuario_id": self.current_user_id, "sesion_id": self.current_sesion_id, "data": data}
                self.api_client.request("POST", "/api/admin/save/satc_regimenes", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    svc = HousingLifeCycleService(session)
                    svc.save_regimen_condominio(data)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Régimen guardado correctamente.")
            dialog.accept()
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # =========================================================================
    # CARGA Y REFRESH DE DATOS
    # =========================================================================
    def refresh_data(self):
        try:
            if self.api_client.connect_via_api:
                self.desarrollos_list = self.api_client.request("GET", "/api/admin/data/desarrollos")
                tipos = self.api_client.request("GET", "/api/admin/data/satc_tipos_tramite")
                est_tramite = self.api_client.request("GET", "/api/admin/data/satc_estados_tramite")
                est_vivienda = self.api_client.request("GET", "/api/admin/data/satc_estados_vivienda")
                regimenes = self.api_client.request("GET", "/api/admin/data/satc_regimenes")
            else:
                with self.db_connector.get_session() as session:
                    cat_repo = CatalogoRepository(session)
                    des_objs = cat_repo.get_all_desarrollos()
                    self.desarrollos_list = [
                        {"desarrollo_id": d.desarrollo_id, "nombre": d.nombre, "alias": d.alias}
                        for d in des_objs
                    ]

                    satc_svc = HousingLifeCycleService(session)
                    tipos_objs = satc_svc.get_all_tipos_tramite()
                    tipos = [
                        {
                            "tipo_tramite_id": t.tipo_tramite_id,
                            "codigo": t.codigo,
                            "nombre": t.nombre,
                            "aplica_a": t.aplica_a,
                            "etapa_disparador": t.etapa_disparador,
                            "dias_vigencia": t.dias_vigencia,
                            "es_obligatorio": t.es_obligatorio,
                            "activo": t.activo
                        }
                        for t in tipos_objs
                    ]

                    est_tr_objs = satc_svc.get_all_estados_tramite()
                    est_tramite = [
                        {
                            "estado_tramite_id": e.estado_tramite_id,
                            "codigo": e.codigo,
                            "nombre": e.nombre,
                            "fase": e.fase,
                            "es_bloqueante": e.es_bloqueante,
                            "es_terminal": e.es_terminal,
                            "activo": e.activo
                        }
                        for e in est_tr_objs
                    ]

                    est_viv_objs = satc_svc.get_all_estados_vivienda()
                    est_vivienda = [
                        {
                            "estado_vivienda_id": e.estado_vivienda_id,
                            "codigo": e.codigo,
                            "nombre": e.nombre,
                            "descripcion": e.descripcion,
                            "orden_flujo": e.orden_flujo,
                            "permite_venta": e.permite_venta,
                            "permite_escrituracion": e.permite_escrituracion,
                            "activo": e.activo
                        }
                        for e in est_viv_objs
                    ]

                    reg_objs = satc_svc.get_all_regimenes()
                    regimenes = [
                        {
                            "regimen_id": r.regimen_id,
                            "desarrollo_id": r.desarrollo_id,
                            "desarrollo_nombre": r.desarrollo.nombre if r.desarrollo else "N/A",
                            "nombre_regimen": r.nombre_regimen,
                            "sm": r.sm or "",
                            "mz": r.mz,
                            "lt": r.lt,
                            "total_upes": r.total_upes,
                            "upes_generadas": r.upes_generadas,
                            "licencia_construccion_matriz": r.licencia_construccion_matriz or "",
                            "clave_catastral_matriz": r.clave_catastral_matriz or "",
                            "activo": r.activo
                        }
                        for r in reg_objs
                    ]

            self.tbl_tipos.populate(tipos)
            self.tbl_est_tramite.populate(est_tramite)
            self.tbl_est_vivienda.populate(est_vivienda)
            self.tbl_regimenes.populate(regimenes)

            # Actualizar dropdown de desarrollos en pestaña de viviendas
            current_v_des = self.cmb_v_desarrollo.currentData()
            self.cmb_v_desarrollo.blockSignals(True)
            self.cmb_v_desarrollo.clear()
            self.cmb_v_desarrollo.addItem("-- Selecciona un Desarrollo --", None)
            for d in self.desarrollos_list:
                self.cmb_v_desarrollo.addItem(d.get("nombre", ""), d.get("desarrollo_id"))
            if current_v_des:
                idx = self.cmb_v_desarrollo.findData(current_v_des)
                if idx >= 0:
                    self.cmb_v_desarrollo.setCurrentIndex(idx)
                else:
                    self.cmb_v_desarrollo.setCurrentIndex(0)
            else:
                self.cmb_v_desarrollo.setCurrentIndex(0)
            self.cmb_v_desarrollo.blockSignals(False)
            self._on_v_desarrollo_changed()

        except Exception as e:
            QMessageBox.critical(self, "Error al cargar catálogos SATC", str(e))

    # =========================================================================
    # 5. HANDLERS: IMPORTACIÓN Y PADRÓN DE VIVIENDAS / UPES
    # =========================================================================
    def _on_v_desarrollo_changed(self):
        """Recarga los regímenes disponibles para el desarrollo y limpia la tabla si no hay selección."""
        des_id = self.cmb_v_desarrollo.currentData()
        self.cmb_v_regimen.blockSignals(True)
        self.cmb_v_regimen.clear()
        self.cmb_v_regimen.addItem("-- Seleccione un Régimen --", None)

        if des_id:
            try:
                if self.api_client.connect_via_api:
                    all_regs = self.api_client.request("GET", "/api/admin/data/satc_regimenes")
                    regs = [r for r in all_regs if r.get("desarrollo_id") == des_id and r.get("activo", True)]
                else:
                    with self.db_connector.get_session() as session:
                        svc = HousingLifeCycleService(session)
                        all_regs = svc.get_all_regimenes()
                        regs = [
                            {"regimen_id": r.regimen_id, "nombre_regimen": r.nombre_regimen, "total_upes": r.total_upes}
                            for r in all_regs if r.desarrollo_id == des_id and r.activo
                        ]

                self.cmb_v_regimen.addItem("-- Sin Régimen (Directo a Desarrollo / Fraccionamiento) --", "SIN_REGIMEN")
                for r in regs:
                    total_u = r.get("total_upes", 0)
                    self.cmb_v_regimen.addItem(f"{r.get('nombre_regimen')} (Capacidad: {total_u} UPEs)", r.get("regimen_id"))
            except Exception:
                pass

        self.cmb_v_regimen.blockSignals(False)
        self._on_v_regimen_changed()

    def _on_v_regimen_changed(self):
        """Carga las viviendas de forma asíncrona en segundo plano sin congelar la interfaz."""
        des_id = self.cmb_v_desarrollo.currentData()
        raw_reg_id = self.cmb_v_regimen.currentData()
        reg_id = None if raw_reg_id in (None, "SIN_REGIMEN") else raw_reg_id

        self._v_parsed_records = []
        self.btn_v_ejecutar.setEnabled(False)
        self.btn_v_exportar_datos.setEnabled(False)
        self.lbl_vkpi_archivo.setText("Archivo: Ninguno")
        self.lbl_vkpi_total_arch.setText("En Archivo: 0")
        self.lbl_vkpi_nuevos.setText("Nuevos / Vinculables: 0")
        self.lbl_vkpi_duplicados.setText("Duplicados / Sin Coincidencia: 0")
        self.search_viviendas_input.blockSignals(True)
        self.search_viviendas_input.clear()
        self.search_viviendas_input.blockSignals(False)

        # Si no se ha seleccionado desarrollo o régimen, mantener la tabla limpia sin congelamiento
        if not des_id or raw_reg_id is None:
            self.tbl_viviendas.setRowCount(0)
            self.lbl_vkpi_bd.setText("EnBD: 0")
            self.lbl_vkpi_regimen_info.setText("Total UPE: N/A")
            self.lbl_vkpi_con_rpp.setText("Con Folio: 0")
            self.lbl_vkpi_con_catastro.setText("Con CC: 0")
            self.action_state_changed.emit()
            return

        # Desplegar indicador de carga no bloqueante
        self._v_loading_dialog = GLLoadingDialog("Cargando padrón de viviendas...", self)
        self._v_loading_dialog.show()

        # Iniciar worker en background
        self._v_load_worker = ViviendasLoadWorker(
            api_client=self.api_client,
            db_connector=self.db_connector,
            desarrollo_id=des_id,
            regimen_id=reg_id
        )
        self._v_load_worker.finished.connect(self._on_v_load_finished)
        self._v_load_worker.start()

    def _on_v_load_finished(self, success: bool, result_data: dict, error_msg: str):
        """Puebla la tabla de viviendas y las métricas una vez culminada la consulta asíncrona."""
        if self._v_loading_dialog:
            self._v_loading_dialog.close()
            self._v_loading_dialog = None

        if not success:
            QMessageBox.critical(self, "Error al Cargar Viviendas", f"No se pudieron cargar las viviendas: {error_msg}")
            return

        viviendas = result_data.get("viviendas", [])
        tot_u = result_data.get("tot_u", 0)
        reg_id = result_data.get("regimen_id")

        if reg_id:
            self.lbl_vkpi_regimen_info.setText(f"Total UPE: {tot_u}")
        else:
            self.lbl_vkpi_regimen_info.setText("Sin Régimen (Abierto)")

        self.lbl_vkpi_bd.setText(f"EnBD: {len(viviendas)}")

        con_rpp = sum(1 for v in viviendas if v.get("folio_electronico"))
        con_cat = sum(1 for v in viviendas if v.get("clave_catastral"))
        self.lbl_vkpi_con_rpp.setText(f"Con Folio: {con_rpp}")
        self.lbl_vkpi_con_catastro.setText(f"Con CC: {con_cat}")

        self.tbl_viviendas.setUpdatesEnabled(False)
        try:
            self.tbl_viviendas.setRowCount(len(viviendas))
            for idx, v in enumerate(viviendas):
                item_st = QTableWidgetItem("REGISTRADO")
                item_st.setForeground(Qt.darkGreen)
                self.tbl_viviendas.setItem(idx, 0, item_st)
                self.tbl_viviendas.setItem(idx, 1, QTableWidgetItem(str(v.get("regimen_nombre") or "")))
                self.tbl_viviendas.setItem(idx, 2, QTableWidgetItem(str(v.get("numero_oficial") or "")))
                self.tbl_viviendas.setItem(idx, 3, QTableWidgetItem(str(v.get("interior") or "")))
                self.tbl_viviendas.setItem(idx, 4, QTableWidgetItem(str(v.get("edificio") or "")))
                self.tbl_viviendas.setItem(idx, 5, QTableWidgetItem(str(v.get("nivel") or "")))
                self.tbl_viviendas.setItem(idx, 6, QTableWidgetItem(str(v.get("destino") or "HABITACIONAL")))
                self.tbl_viviendas.setItem(idx, 7, QTableWidgetItem(str(v.get("espacio") or "VIVIENDA")))
                self.tbl_viviendas.setItem(idx, 8, QTableWidgetItem(str(v.get("folio_electronico") or "")))
                self.tbl_viviendas.setItem(idx, 9, QTableWidgetItem(str(v.get("clave_catastral") or "")))
                self.tbl_viviendas.setItem(idx, 10, QTableWidgetItem(str(v.get("padron") or "")))
                self.tbl_viviendas.setItem(idx, 11, QTableWidgetItem(str(v.get("calle") or "")))
                self.tbl_viviendas.setItem(idx, 12, QTableWidgetItem(str(v.get("descripcion") or "")))
        finally:
            self.tbl_viviendas.setUpdatesEnabled(True)

        self.action_state_changed.emit()

    def _on_search_viviendas_text_changed(self, text: str):
        """Filtra reactivamente las filas visibles en la tabla de viviendas en base al texto buscado."""
        search_term = text.strip().lower()
        self.tbl_viviendas.setUpdatesEnabled(False)
        try:
            for row in range(self.tbl_viviendas.rowCount()):
                if not search_term:
                    self.tbl_viviendas.setRowHidden(row, False)
                    continue

                row_matches = False
                for col in range(self.tbl_viviendas.columnCount()):
                    item = self.tbl_viviendas.item(row, col)
                    if item and search_term in item.text().lower():
                        row_matches = True
                        break
                self.tbl_viviendas.setRowHidden(row, not row_matches)
        finally:
            self.tbl_viviendas.setUpdatesEnabled(True)

    def _on_v_limpiar(self):
        """Limpia completamente la pantalla, filtros, registros cargados, tabla e indicadores de métricas."""
        self.cmb_v_desarrollo.blockSignals(True)
        self.cmb_v_regimen.blockSignals(True)
        self.cmb_v_modo.blockSignals(True)
        try:
            self.cmb_v_desarrollo.setCurrentIndex(0)
            self.cmb_v_regimen.clear()
            self.cmb_v_regimen.addItem("-- Seleccione un Régimen --", None)
            self.cmb_v_regimen.setCurrentIndex(0)
            self.cmb_v_modo.setCurrentIndex(0)
        finally:
            self.cmb_v_desarrollo.blockSignals(False)
            self.cmb_v_regimen.blockSignals(False)
            self.cmb_v_modo.blockSignals(False)

        self._v_parsed_records = []
        self.btn_v_ejecutar.setEnabled(False)
        self.btn_v_exportar_datos.setEnabled(False)
        self.search_viviendas_input.blockSignals(True)
        self.search_viviendas_input.clear()
        self.search_viviendas_input.blockSignals(False)

        # Reset completo de indicadores KPI (Nomenclatura concisa)
        self.lbl_vkpi_archivo.setText("Archivo: Ninguno")
        self.lbl_vkpi_total_arch.setText("En Archivo: 0")
        self.lbl_vkpi_nuevos.setText("Nuevos / Vinculables: 0")
        self.lbl_vkpi_duplicados.setText("Duplicados / Sin Coincidencia: 0")
        self.lbl_vkpi_regimen_info.setText("Total UPE: N/A")
        self.lbl_vkpi_bd.setText("EnBD: 0")
        self.lbl_vkpi_con_rpp.setText("Con Folio: 0")
        self.lbl_vkpi_con_catastro.setText("Con CC: 0")

        # Limpiar tabla
        self.tbl_viviendas.setRowCount(0)
        self.action_state_changed.emit()

    def _on_v_exportar_datos(self):
        """Descarga los registros analizados/extraídos a una plantilla Excel (.xlsx) para validación visual humana."""
        if not self._v_parsed_records:
            QMessageBox.warning(self, "Sin Datos", "No hay datos cargados para exportar.")
            return

        modo = self.cmb_v_modo.currentData()
        nombre_des = "".join(c for c in self.cmb_v_desarrollo.currentText() if c.isalnum() or c in (" ", "_", "-")).strip()
        nombre_sugerido = f"Datos_Extraidos_{modo}_{nombre_des}.xlsx"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Descargar Datos Extraídos para Validación", nombre_sugerido, "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = f"Datos_{modo}"

            headers = [
                "NUMERO_OFICIAL", "INTERIOR", "EDIFICIO", "NIVEL", "DESTINO", 
                "ESPACIO", "FOLIO_ELECTRONICO", "CLAVE_CATASTRAL", "PADRON", "CALLE", "DESCRIPCION"
            ]
            ws.append(headers)

            # Estilos de encabezado
            header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            border_thin = Border(
                left=Side(style='thin', color='CBD5E1'),
                right=Side(style='thin', color='CBD5E1'),
                top=Side(style='thin', color='CBD5E1'),
                bottom=Side(style='thin', color='CBD5E1')
            )

            for col_num in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_num)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = border_thin

            for r in self._v_parsed_records:
                ws.append([
                    r.get("numero_oficial", ""),
                    r.get("interior", ""),
                    r.get("edificio", ""),
                    r.get("nivel", ""),
                    r.get("destino", "HABITACIONAL"),
                    r.get("espacio", "VIVIENDA"),
                    r.get("folio_electronico", ""),
                    r.get("clave_catastral", ""),
                    r.get("padron", ""),
                    r.get("calle", ""),
                    r.get("descripcion", "")
                ])

            # Autoancho de columnas
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

            wb.save(file_path)
            QMessageBox.information(
                self, "Exportación Exitosa",
                f"Se han exportado exitosamente {len(self._v_parsed_records)} registros a:\n{file_path}\n\n"
                "Puede abrir el archivo en Excel para su cotejo visual."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error al Exportar", f"No se pudo guardar el archivo Excel:\n{e}")

    def _on_v_modo_changed(self):
        """Actualiza el texto descriptivo del banner y limpia la selección previa."""
        modo = self.cmb_v_modo.currentData()
        self._v_parsed_records = []
        self.btn_v_ejecutar.setEnabled(False)
        self.btn_v_exportar_datos.setEnabled(False)
        self.lbl_vkpi_archivo.setText("Archivo: Ninguno")
        self.lbl_vkpi_total_arch.setText("En Archivo: 0")
        self.lbl_vkpi_nuevos.setText("Nuevos / Vinculables: 0")
        self.lbl_vkpi_duplicados.setText("Duplicados / Sin Coincidencia: 0")

        if hasattr(self, "lbl_v_desc") and self.lbl_v_desc is not None:
            if modo == "RPP":
                self.lbl_v_desc.setText(
                    "<b>2. Vinculación de Folios Electrónicos del RPP:</b><br/>"
                    "Cargue la relación de folios registrales para las viviendas ya existentes en el régimen.<br/>"
                    "• Relaciona cada registro mediante <b>EDIFICIO</b> e <b>INTERIOR</b>.<br/>"
                    "• Al asignar el folio RPP, la vivienda avanza automáticamente al estado <b>EN_INDIVIDUALIZACION</b>."
                )
            elif modo == "CATASTRO":
                self.lbl_v_desc.setText(
                    "<b>3. Vinculación de Cédula Catastral y Padrón Municipal:</b><br/>"
                    "Cargue las claves catastrales y cuentas prediales asignadas por Catastro Cancún.<br/>"
                    "• Enlaza mediante <b>FOLIO_ELECTRONICO</b> o por <b>(EDIFICIO, INTERIOR)</b>.<br/>"
                    "• Al completar los datos catastrales, la vivienda transiciona a <b>LISTA_PARA_VENTA</b>."
                )
            else:
                self.lbl_v_desc.setText(
                    "<b>1. Carga Inicial de Viviendas (Física):</b><br/>"
                    "Importe masivamente las viviendas/espacios privativos autorizados para el régimen.<br/>"
                    "• Se dan de alta en estado <b>PROYECTADA</b> (con interior, edificio, nivel, destino y espacio).<br/>"
                    "• No requieren folios RPP ni claves catastrales en esta etapa."
                )

    def _on_v_descargar_plantilla(self):
        """Genera una plantilla Excel (.xlsx) estandarizada según el modo de operación seleccionado."""
        des_id = self.cmb_v_desarrollo.currentData()
        reg_id = self.cmb_v_regimen.currentData()
        modo = self.cmb_v_modo.currentData()

        if not des_id or not reg_id:
            QMessageBox.warning(self, "Régimen Requerido", "Por favor seleccione un desarrollo y un régimen para generar la plantilla.")
            return

        nombre_des = "".join(c for c in self.cmb_v_desarrollo.currentText() if c.isalnum() or c in (" ", "_", "-")).strip()
        nombre_reg = "".join(c for c in self.cmb_v_regimen.currentText() if c.isalnum() or c in (" ", "_", "-")).strip()
        nombre_sugerido = f"Plantilla_{modo}_{nombre_des}_{nombre_reg}.xlsx"

        file_path, _ = QFileDialog.getSaveFileName(
            self, f"Guardar Plantilla Excel ({modo})", nombre_sugerido, "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            wb = openpyxl.Workbook()
            ws = wb.active

            if modo == "RPP":
                ws.title = "Folios_RPP"
                headers = ["EDIFICIO", "INTERIOR", "FOLIO_ELECTRONICO"]
                sample_rows = [
                    ["TORRE A", "101", "RPP-CUN-0012345"],
                    ["TORRE A", "102", "RPP-CUN-0012346"],
                    ["TORRE A", "103", "RPP-CUN-0012347"]
                ]
            elif modo == "CATASTRO":
                ws.title = "Catastro_Padron"
                headers = ["EDIFICIO", "INTERIOR", "FOLIO_ELECTRONICO", "CLAVE_CATASTRAL", "PADRON"]
                sample_rows = [
                    ["TORRE A", "101", "RPP-CUN-0012345", "101-01-001-001-001", "PAD-2026-001"],
                    ["TORRE A", "102", "RPP-CUN-0012346", "101-01-001-001-002", "PAD-2026-002"],
                    ["TORRE A", "103", "RPP-CUN-0012347", "101-01-001-001-003", "PAD-2026-003"]
                ]
            else:
                ws.title = "Viviendas_Inicial"
                headers = [
                    "NUMERO_OFICIAL", "INTERIOR", "EDIFICIO", "NIVEL", "CALLE",
                    "DESTINO", "ESPACIO", "DESCRIPCION"
                ]
                sample_rows = [
                    ["UPE-001", "101", "TORRE A", "NIVEL 1", "AV. HUAYACAN", "HABITACIONAL", "VIVIENDA", "Depto Tipo A 2 Recámaras"],
                    ["UPE-002", "102", "TORRE A", "NIVEL 1", "AV. HUAYACAN", "HABITACIONAL", "VIVIENDA", "Depto Tipo B 3 Recámaras"],
                    ["EST-001", "E-01", "TORRE A", "PLANTA BAJA", "AV. HUAYACAN", "SERVICIO", "AREAS COMUNES", "Cajón Privativo"]
                ]

            ws.append(headers)

            # Estilos de encabezado
            header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            border_thin = Border(
                left=Side(style='thin', color='CBD5E1'),
                right=Side(style='thin', color='CBD5E1'),
                top=Side(style='thin', color='CBD5E1'),
                bottom=Side(style='thin', color='CBD5E1')
            )

            for col_num in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_num)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = border_thin

            for row in sample_rows:
                ws.append(row)

            # Autoancho
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 5, 12)

            wb.save(file_path)
            QMessageBox.information(
                self, "Plantilla Generada",
                f"Plantilla Excel generada con éxito en:\n{file_path}\n\n"
                "Puede completarla con los predios y cargarla mediante 'Cargar Archivo'."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar la plantilla: {e}")

    def _on_v_seleccionar_archivo(self):
        """Abre el diálogo de archivo y ejecuta la lectura y validación en segundo plano sin congelar la UI."""
        des_id = self.cmb_v_desarrollo.currentData()
        reg_id = self.cmb_v_regimen.currentData()
        modo = self.cmb_v_modo.currentData()

        if not des_id:
            QMessageBox.warning(self, "Desarrollo Requerido", "Por favor seleccione un Desarrollo antes de cargar el archivo.")
            return

        filtro = "Todos los Soportados (*.xlsx *.xls *.pdf);;Constancias RPP PDF (*.pdf);;Plantillas Excel (*.xlsx *.xls)"
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Archivo (Excel o Constancia PDF)", "", filtro
        )
        if not file_path:
            return

        is_pdf = file_path.lower().endswith(".pdf")
        if is_pdf and modo != "RPP":
            QMessageBox.warning(
                self, "Modo de Operación Requerido",
                "El archivo seleccionado es una Constancia de Resolución PDF.\n"
                "Por favor seleccione la operación '2. Vincular Folios RPP' para procesarlo."
            )
            return

        # Deshabilitar botones operativos mientras se analiza el archivo
        self.btn_v_seleccionar.setEnabled(False)
        self.btn_v_ejecutar.setEnabled(False)
        self.btn_v_exportar_datos.setEnabled(False)

        # Mostrar indicador de carga no bloqueante
        loading_msg = "Extrayendo Constancia PDF..." if is_pdf else "Analizando archivo y validando datos..."
        self._v_loading_dialog = GLLoadingDialog(loading_msg, self)
        self._v_loading_dialog.show()

        # Iniciar worker en background
        self._v_analyze_worker = ViviendasFileAnalyzeWorker(
            api_client=self.api_client,
            db_connector=self.db_connector,
            file_path=file_path,
            desarrollo_id=des_id,
            regimen_id=reg_id,
            modo=modo
        )
        self._v_analyze_worker.finished.connect(self._on_v_file_analyze_finished)
        self._v_analyze_worker.start()

    def _on_v_file_analyze_finished(self, success: bool, result_data: dict, error_msg: str):
        """Maneja el resultado del análisis asíncrono y actualiza la tabla y métricas de forma fluida."""
        if self._v_loading_dialog:
            self._v_loading_dialog.close()
            self._v_loading_dialog = None

        self.btn_v_seleccionar.setEnabled(True)

        if not success:
            QMessageBox.critical(self, "Error al Analizar Archivo", error_msg)
            return

        records = result_data.get("records", [])
        processed = result_data.get("processed_records", [])
        file_name = result_data.get("file_name", "")
        nuevos_cnt = result_data.get("nuevos_cnt", 0)
        duplicados_cnt = result_data.get("duplicados_cnt", 0)
        modo = self.cmb_v_modo.currentData()
        reg_id = self.cmb_v_regimen.currentData()
        reg_label = self.cmb_v_regimen.currentText() if reg_id else ""

        self._v_parsed_records = records
        self.lbl_vkpi_archivo.setText(f"Archivo: {file_name}")
        self.lbl_vkpi_total_arch.setText(f"En Archivo: {len(records)}")

        self.tbl_viviendas.setUpdatesEnabled(False)
        try:
            self.tbl_viviendas.setRowCount(len(processed))
            for idx, item in enumerate(processed):
                r = item["data"]
                st_text = item["status"]

                item_st = QTableWidgetItem(st_text)
                if st_text in ("NUEVO", "VINCULABLE"):
                    item_st.setForeground(QColor("#16A34A"))
                else:
                    item_st.setForeground(QColor("#DC2626"))

                self.tbl_viviendas.setItem(idx, 0, item_st)
                self.tbl_viviendas.setItem(idx, 1, QTableWidgetItem(reg_label))
                self.tbl_viviendas.setItem(idx, 2, QTableWidgetItem(r["numero_oficial"]))
                self.tbl_viviendas.setItem(idx, 3, QTableWidgetItem(r["interior"]))
                self.tbl_viviendas.setItem(idx, 4, QTableWidgetItem(r["edificio"]))
                self.tbl_viviendas.setItem(idx, 5, QTableWidgetItem(r["nivel"]))
                self.tbl_viviendas.setItem(idx, 6, QTableWidgetItem(r["destino"]))
                self.tbl_viviendas.setItem(idx, 7, QTableWidgetItem(r["espacio"]))
                self.tbl_viviendas.setItem(idx, 8, QTableWidgetItem(r["folio_electronico"]))
                self.tbl_viviendas.setItem(idx, 9, QTableWidgetItem(r["clave_catastral"]))
                self.tbl_viviendas.setItem(idx, 10, QTableWidgetItem(r["padron"]))
                self.tbl_viviendas.setItem(idx, 11, QTableWidgetItem(r["calle"]))
                self.tbl_viviendas.setItem(idx, 12, QTableWidgetItem(r["descripcion"]))
        finally:
            self.tbl_viviendas.setUpdatesEnabled(True)

        self._v_nuevos_cnt = nuevos_cnt
        self._v_duplicados_cnt = duplicados_cnt

        if modo in ("RPP", "CATASTRO"):
            self.lbl_vkpi_nuevos.setText(f"Vinculables: {nuevos_cnt}")
            self.lbl_vkpi_duplicados.setText(f"Sin Coincidencia: {duplicados_cnt}")
            self.btn_v_ejecutar.setEnabled(nuevos_cnt > 0)
        else:
            self.lbl_vkpi_nuevos.setText(f"Nuevos: {nuevos_cnt}")
            self.lbl_vkpi_duplicados.setText(f"Duplicados: {duplicados_cnt}")
            self.btn_v_ejecutar.setEnabled(nuevos_cnt > 0)

        self.btn_v_exportar_datos.setEnabled(len(records) > 0)
        self.action_state_changed.emit()

    def _on_v_ejecutar_importacion(self):
        """Ejecuta la importación en un hilo background mediante ViviendasImportWorker mostrando indicador visual."""
        des_id = self.cmb_v_desarrollo.currentData()
        reg_id = self.cmb_v_regimen.currentData()

        if not des_id or not self._v_parsed_records:
            return

        total_recs = len(self._v_parsed_records)
        target_cnt = getattr(self, "_v_nuevos_cnt", total_recs)
        sin_coincidencia = getattr(self, "_v_duplicados_cnt", 0)
        reg_txt = self.cmb_v_regimen.currentText() if reg_id else "Directo a Desarrollo"
        des_txt = self.cmb_v_desarrollo.currentText()

        modo = self.cmb_v_modo.currentData()
        if modo == "RPP":
            modo_titulo = "Vinculación de Folios RPP"
            modo_desc = f"¿Está seguro de vincular los <b>Folios Electrónicos RPP</b> para las <b>{target_cnt}</b> viviendas detectadas?"
            loading_txt = f"Vinculando {target_cnt} Folios RPP...\nPor favor espere."
            detalle_procesar = f"<b>Total a vincular:</b> {target_cnt} viviendas (de {total_recs} en archivo)"
            if sin_coincidencia > 0:
                detalle_procesar += f"<br/><b>Sin coincidencia:</b> {sin_coincidencia} registros omitidos"
        elif modo == "CATASTRO":
            modo_titulo = "Vinculación Catastral y Predial"
            modo_desc = f"¿Está seguro de vincular las <b>Claves Catastrales y Padrones</b> para las <b>{target_cnt}</b> viviendas detectadas?"
            loading_txt = f"Vinculando Catastro y Padrón para {target_cnt} viviendas...\nPor favor espere."
            detalle_procesar = f"<b>Total a vincular:</b> {target_cnt} viviendas (de {total_recs} en archivo)"
            if sin_coincidencia > 0:
                detalle_procesar += f"<br/><b>Sin coincidencia:</b> {sin_coincidencia} registros omitidos"
        else:
            modo_titulo = "Carga Inicial de Viviendas"
            modo_desc = f"¿Está seguro de aplicar la <b>Carga Inicial</b> de <b>{target_cnt}</b> viviendas nuevas en estado <i>PROYECTADA</i>?"
            loading_txt = f"Importando {target_cnt} viviendas nuevas...\nPor favor espere."
            detalle_procesar = f"<b>Nuevas a crear:</b> {target_cnt} viviendas (de {total_recs} en archivo)"
            if sin_coincidencia > 0:
                detalle_procesar += f"<br/><b>Duplicadas:</b> {sin_coincidencia} registros omitidos"

        msg_confirm = (
            f"{modo_desc}<br/><br/>"
            f"<b>Desarrollo:</b> {des_txt}<br/>"
            f"<b>Régimen:</b> {reg_txt}<br/>"
            f"{detalle_procesar}"
        )

        reply = QMessageBox.question(
            self, f"Confirmar {modo_titulo}",
            msg_confirm,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply != QMessageBox.Yes:
            return

        self.btn_v_ejecutar.setEnabled(False)
        self.btn_v_seleccionar.setEnabled(False)

        # Mostrar indicador de carga no bloqueante
        self._v_loading_dialog = GLLoadingDialog(loading_txt, self)
        self._v_loading_dialog.show()

        self._v_worker = ViviendasImportWorker(
            api_client=self.api_client,
            db_connector=self.db_connector,
            desarrollo_id=des_id,
            regimen_id=reg_id,
            records=self._v_parsed_records,
            usuario_id=self.current_user_id or 1,
            sesion_id=self.current_sesion_id,
            modo=modo
        )
        self._v_worker.finished.connect(self._on_v_worker_finished)
        self._v_worker.start()

    def _on_v_worker_finished(self, success: bool, result: dict, error_msg: str):
        # Cerrar el indicador de carga si está activo
        if self._v_loading_dialog:
            self._v_loading_dialog.close()
            self._v_loading_dialog = None

        self.btn_v_seleccionar.setEnabled(True)
        modo = self.cmb_v_modo.currentData()
        if success:
            if modo == "RPP":
                act = result.get("actualizados", 0)
                no_enc = result.get("no_encontrados", 0)
                QMessageBox.information(
                    self, "Vinculación RPP Exitosa",
                    f"Folios RPP vinculados exitosamente:\n\n"
                    f"• Viviendas actualizadas a 'EN_INDIVIDUALIZACION': {act}\n"
                    f"• Registros no encontrados en el régimen: {no_enc}"
                )
            elif modo == "CATASTRO":
                act = result.get("actualizados", 0)
                no_enc = result.get("no_encontrados", 0)
                QMessageBox.information(
                    self, "Vinculación Catastral Exitosa",
                    f"Claves Catastrales y Padrones vinculados exitosamente:\n\n"
                    f"• Viviendas actualizadas a 'LISTA_PARA_VENTA': {act}\n"
                    f"• Registros no encontrados en el régimen: {no_enc}"
                )
            else:
                nuevos = result.get("nuevos_insertados", 0)
                dups = result.get("omitidos_duplicados", 0)
                QMessageBox.information(
                    self, "Carga Inicial Exitosa",
                    f"Proceso de importación inicial completado exitosamente:\n\n"
                    f"• Viviendas creadas en 'PROYECTADA': {nuevos}\n"
                    f"• Omitidas por duplicidad: {dups}"
                )

            self._v_parsed_records = []
            self.tbl_viviendas.setUpdatesEnabled(False)
            try:
                self._on_v_regimen_changed()
            finally:
                self.tbl_viviendas.setUpdatesEnabled(True)
        else:
            QMessageBox.critical(self, "Error en la Operación", f"No se pudo completar la operación:\n{error_msg}")
            self.btn_v_ejecutar.setEnabled(True)

