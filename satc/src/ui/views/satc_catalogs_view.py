import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QFrame, QLabel, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QFileDialog
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.atoms.gl_input import CustomInput
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.atoms.gl_checkbox import CustomCheckBox
from sar.src.ui.design_system.components.molecules.gl_combo_box import CustomComboBox
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
from sar.src.ui.design_system.components.organisms.gl_crud_table import CrudTablePanel
from sar.src.ui.design_system.components.organisms.gl_dialog import CustomDialog
from sar.src.storage.repositories import CatalogoRepository
from satc.src.services.housing_life_cycle_service import HousingLifeCycleService


class ViviendasImportWorker(QThread):
    """Worker thread para ejecutar la importación masiva de viviendas sin congelar la interfaz."""
    finished = Signal(bool, dict, str)

    def __init__(self, api_client, db_connector, desarrollo_id: int, regimen_id: Optional[int], records: list, usuario_id: int, sesion_id: Optional[int] = None):
        super().__init__()
        self.api_client = api_client
        self.db_connector = db_connector
        self.desarrollo_id = desarrollo_id
        self.regimen_id = regimen_id
        self.records = records
        self.usuario_id = usuario_id
        self.sesion_id = sesion_id

    def run(self):
        try:
            if self.api_client.connect_via_api:
                payload = {
                    "desarrollo_id": self.desarrollo_id,
                    "regimen_id": self.regimen_id,
                    "usuario_id": self.usuario_id,
                    "sesion_id": self.sesion_id,
                    "records": self.records
                }
                res = self.api_client.request("POST", "/api/admin/satc/viviendas/bulk-import", json=payload)
            else:
                with self.db_connector.get_session() as session:
                    svc = HousingLifeCycleService(session)
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
        self._build_ui()

    def _build_ui(self):
        self.tabs = QTabWidget(self)
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
        # Pestaña 4: Regímenes en Condominio (Macro-Lotes)
        # ---------------------------------------------------------
        self.tab_regimenes = QWidget()
        lay_regimenes = QHBoxLayout(self.tab_regimenes)
        lay_regimenes.setContentsMargins(0, 0, 0, 0)
        self.tbl_regimenes = CrudTablePanel("Regímenes en Condominio (Macro-Lotes)")
        self.tbl_regimenes.setup_table(
            ["ID", "Desarrollo", "Nombre Régimen", "SM", "MZ", "LT", "Total UPEs", "Generadas", "Licencia Matriz", "Clave Catastral", "Estado"],
            ["regimen_id", "desarrollo_nombre", "nombre_regimen", "sm", "mz", "lt", "total_upes", "upes_generadas", "licencia_construccion_matriz", "clave_catastral_matriz", "activo"]
        )
        self.tbl_regimenes.add_requested.connect(self._on_new_regimen)
        self.tbl_regimenes.edit_requested.connect(self._on_edit_regimen)
        self.tbl_regimenes.btn_add.setVisible(self.can_edit)
        self.tbl_regimenes.btn_edit.setVisible(self.can_edit)
        lay_regimenes.addWidget(self.tbl_regimenes)
        self.tabs.addTab(self.tab_regimenes, "Regímenes en Condominio")

        # ---------------------------------------------------------
        # Pestaña 5: Importación y Padrón de Viviendas
        # ---------------------------------------------------------
        self.tab_import_viviendas = QWidget()
        lay_import_viv = QVBoxLayout(self.tab_import_viviendas)
        lay_import_viv.setContentsMargins(12, 12, 12, 12)
        lay_import_viv.setSpacing(12)

        # 1. Banner explicativo
        self.lbl_v_desc = CustomLabel(
            "<b>Importación y Padrón Maestro de Viviendas / UPEs:</b><br/>"
            "Cargue o consulte masivamente el listado de viviendas del desarrollo.<br/>"
            "• <b>Con Régimen en Condominio:</b> Valida estrictamente que el total de viviendas cargadas no exceda las UPEs autorizadas del macro-lote.<br/>"
            "• <b>Sin Régimen (Directo a Desarrollo):</b> Permite la importación de fraccionamientos unifamiliares o manzanas abiertas sin macro-lote.",
            variant="body"
        )
        self.lbl_v_desc.setWordWrap(True)
        self.lbl_v_desc.setStyleSheet(f"background-color: {Colors.SURFACE_LIGHT}; border: 1px solid {Colors.BORDER_LIGHT}; padding: 10px 14px; border-radius: 6px; color: {Colors.TEXT_LIGHT_SECONDARY};")
        lay_import_viv.addWidget(self.lbl_v_desc)

        # 2. Barra de filtros y controles
        ctl_box = QHBoxLayout()
        ctl_box.setSpacing(10)

        ctl_box.addWidget(CustomLabel("Desarrollo *:", variant="body"))
        self.cmb_v_desarrollo = CustomComboBox()
        self.cmb_v_desarrollo.setMinimumWidth(220)
        self.cmb_v_desarrollo.currentIndexChanged.connect(self._on_v_desarrollo_changed)
        ctl_box.addWidget(self.cmb_v_desarrollo)

        ctl_box.addWidget(CustomLabel("Régimen (Opcional):", variant="body"))
        self.cmb_v_regimen = CustomComboBox()
        self.cmb_v_regimen.setMinimumWidth(260)
        self.cmb_v_regimen.currentIndexChanged.connect(self._on_v_regimen_changed)
        ctl_box.addWidget(self.cmb_v_regimen)

        self.btn_v_plantilla = CustomButton("Descargar Plantilla", is_secondary=True, icon_name="excel")
        self.btn_v_plantilla.clicked.connect(self._on_v_descargar_plantilla)
        ctl_box.addWidget(self.btn_v_plantilla)

        self.btn_v_seleccionar = CustomButton("Seleccionar Archivo", is_secondary=True, icon_name="documento_cargar")
        self.btn_v_seleccionar.clicked.connect(self._on_v_seleccionar_archivo)
        ctl_box.addWidget(self.btn_v_seleccionar)

        self.btn_v_limpiar = CustomButton("Limpiar", is_secondary=True, icon_name="cancelar")
        self.btn_v_limpiar.clicked.connect(self._on_v_limpiar)
        ctl_box.addWidget(self.btn_v_limpiar)

        ctl_box.addStretch()

        self.btn_v_ejecutar = CustomButton("Ejecutar Importación", icon_name="guardar")
        self.btn_v_ejecutar.clicked.connect(self._on_v_ejecutar_importacion)
        self.btn_v_ejecutar.setEnabled(False)
        self.btn_v_ejecutar.setVisible(self.can_edit)
        ctl_box.addWidget(self.btn_v_ejecutar)

        lay_import_viv.addLayout(ctl_box)

        # 3. KPI Bar
        self.kpi_v_frame = QFrame()
        self.kpi_v_frame.setStyleSheet(f"background-color: {Colors.SURFACE_LIGHT}; border: 1px solid {Colors.BORDER_LIGHT}; border-radius: 6px; padding: 6px;")
        kpi_lay = QHBoxLayout(self.kpi_v_frame)
        kpi_lay.setContentsMargins(12, 4, 12, 4)

        self.lbl_vkpi_archivo = QLabel("Archivo: Ninguno")
        self.lbl_vkpi_total_arch = QLabel("En Archivo: 0")
        self.lbl_vkpi_nuevos = QLabel("Nuevos: 0")
        self.lbl_vkpi_duplicados = QLabel("Duplicados: 0")
        self.lbl_vkpi_regimen_info = QLabel("Capacidad Régimen: N/A")
        self.lbl_vkpi_bd = QLabel("Registrados en BD: 0")

        self.lbl_vkpi_archivo.setStyleSheet("font-size: 11px; color: #64748B;")
        self.lbl_vkpi_total_arch.setStyleSheet("font-weight: bold; font-size: 11px; color: #1E293B;")
        self.lbl_vkpi_nuevos.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {Colors.SUCCESS};")
        self.lbl_vkpi_duplicados.setStyleSheet("font-weight: bold; font-size: 11px; color: #E11D48;")
        self.lbl_vkpi_regimen_info.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {Colors.ACCENT_VIOLET};")
        self.lbl_vkpi_bd.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {Colors.ACCENT};")

        kpi_lay.addWidget(self.lbl_vkpi_archivo)
        kpi_lay.addStretch()
        kpi_lay.addWidget(self.lbl_vkpi_total_arch)
        kpi_lay.addWidget(self.lbl_vkpi_nuevos)
        kpi_lay.addWidget(self.lbl_vkpi_duplicados)
        kpi_lay.addWidget(self.lbl_vkpi_regimen_info)
        kpi_lay.addWidget(self.lbl_vkpi_bd)
        lay_import_viv.addWidget(self.kpi_v_frame)

        # 4. Tabla de Visualización / Importación
        self.tbl_viviendas = QTableWidget()
        self.tbl_viviendas.setColumnCount(11)
        self.tbl_viviendas.setHorizontalHeaderLabels([
            "Estado Carga", "Régimen / Tipo", "S.M.", "Manzana", "Lote", "Edificio", "Vivienda", "No. UPE", "Calle", "Clave Catastral", "Notas"
        ])
        self.tbl_viviendas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tbl_viviendas.horizontalHeader().setStretchLastSection(True)
        self.tbl_viviendas.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_viviendas.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_viviendas.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.SURFACE_LIGHT};
                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: 6px;
                gridline-color: #E2E8F0;
                font-size: 12px;
            }}
            QHeaderView::section {{
                background-color: #F8FAFC;
                color: #475569;
                font-weight: bold;
                padding: 6px;
                border: none;
                border-bottom: 1px solid {Colors.BORDER_LIGHT};
            }}
        """)
        lay_import_viv.addWidget(self.tbl_viviendas)

        self.tabs.addTab(self.tab_import_viviendas, "Importación de Viviendas")

        self._v_parsed_records = []
        self._v_worker = None

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
    # 4. DIALOGOS & ACCIONES: REGÍMENES EN CONDOMINIO
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

        lbl = CustomLabel("🏢 MACRO-LOTE DE RÉGIMEN EN CONDOMINIO", variant="subheader")
        lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_LIGHT_PRIMARY}; margin-bottom: 2px;")
        lay.addWidget(lbl)

        form = QFormLayout()
        form.setSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)

        self.cmb_r_desarrollo = CustomComboBox(parent=card)
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
            n = self.inp_r_nombre.text().strip()
            mz = self.inp_r_mz.text().strip()
            lt = self.inp_r_lt.text().strip()
            u = self.inp_r_upes.text().strip()
            dialog.btn_save.setEnabled(bool(n and mz and lt and u))

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
        dialog = self._create_regimen_dialog("Nuevo Régimen en Condominio")
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
            QMessageBox.information(self, "Éxito", "Régimen en condominio guardado correctamente.")
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
            for d in self.desarrollos_list:
                self.cmb_v_desarrollo.addItem(d.get("nombre", ""), d.get("desarrollo_id"))
            if current_v_des:
                idx = self.cmb_v_desarrollo.findData(current_v_des)
                if idx >= 0:
                    self.cmb_v_desarrollo.setCurrentIndex(idx)
            self.cmb_v_desarrollo.blockSignals(False)
            self._on_v_desarrollo_changed()

        except Exception as e:
            QMessageBox.critical(self, "Error al cargar catálogos SATC", str(e))

    # =========================================================================
    # 5. HANDLERS: IMPORTACIÓN Y PADRÓN DE VIVIENDAS / UPES
    # =========================================================================
    def _on_v_desarrollo_changed(self):
        """Recarga los regímenes disponibles para el desarrollo y consulta las viviendas en BD."""
        des_id = self.cmb_v_desarrollo.currentData()
        self.cmb_v_regimen.blockSignals(True)
        self.cmb_v_regimen.clear()
        self.cmb_v_regimen.addItem("-- Sin Régimen (Directo a Desarrollo / Fraccionamiento) --", None)

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

                for r in regs:
                    total_u = r.get("total_upes", 0)
                    self.cmb_v_regimen.addItem(f"{r.get('nombre_regimen')} (Capacidad: {total_u} UPEs)", r.get("regimen_id"))
            except Exception as e:
                pass

        self.cmb_v_regimen.blockSignals(False)
        self._on_v_regimen_changed()

    def _on_v_regimen_changed(self):
        """Carga las viviendas existentes en la base de datos para el desarrollo/régimen seleccionado."""
        des_id = self.cmb_v_desarrollo.currentData()
        reg_id = self.cmb_v_regimen.currentData()

        self._v_parsed_records = []
        self.btn_v_ejecutar.setEnabled(False)
        self.lbl_vkpi_archivo.setText("Archivo: Ninguno")
        self.lbl_vkpi_total_arch.setText("En Archivo: 0")
        self.lbl_vkpi_nuevos.setText("Nuevos: 0")
        self.lbl_vkpi_duplicados.setText("Duplicados: 0")

        if not des_id:
            self.tbl_viviendas.setRowCount(0)
            self.lbl_vkpi_bd.setText("Registrados en BD: 0")
            self.lbl_vkpi_regimen_info.setText("Capacidad Régimen: N/A")
            return

        try:
            if self.api_client.connect_via_api:
                params = {"desarrollo_id": des_id}
                if reg_id:
                    params["regimen_id"] = reg_id
                viviendas = self.api_client.request("GET", f"/api/admin/satc/viviendas/{des_id}", data=params)
            else:
                with self.db_connector.get_session() as session:
                    svc = HousingLifeCycleService(session)
                    if reg_id:
                        viviendas = svc.get_viviendas_by_regimen(reg_id)
                    else:
                        viviendas = svc.get_viviendas_by_desarrollo(des_id, solo_sin_regimen=True)

            # Capacidad del régimen
            if reg_id:
                if self.api_client.connect_via_api:
                    all_regs = self.api_client.request("GET", "/api/admin/data/satc_regimenes")
                    target = next((r for r in all_regs if r.get("regimen_id") == reg_id), None)
                    tot_u = target.get("total_upes", 0) if target else 0
                else:
                    with self.db_connector.get_session() as session:
                        svc = HousingLifeCycleService(session)
                        target = svc.regimen_repo.get_by_id(reg_id)
                        tot_u = target.total_upes if target else 0
                self.lbl_vkpi_regimen_info.setText(f"Capacidad Régimen: {tot_u} UPEs")
            else:
                self.lbl_vkpi_regimen_info.setText("Sin Régimen (Abierto)")

            self.lbl_vkpi_bd.setText(f"Registrados en BD: {len(viviendas)}")
            self.tbl_viviendas.setRowCount(len(viviendas))
            for idx, v in enumerate(viviendas):
                item_st = QTableWidgetItem("REGISTRADO")
                item_st.setForeground(Qt.darkGreen)
                self.tbl_viviendas.setItem(idx, 0, item_st)
                self.tbl_viviendas.setItem(idx, 1, QTableWidgetItem(str(v.get("regimen_nombre") or "FRACCIONAMIENTO")))
                self.tbl_viviendas.setItem(idx, 2, QTableWidgetItem(str(v.get("sm") or "")))
                self.tbl_viviendas.setItem(idx, 3, QTableWidgetItem(str(v.get("mz") or "")))
                self.tbl_viviendas.setItem(idx, 4, QTableWidgetItem(str(v.get("lt") or "")))
                self.tbl_viviendas.setItem(idx, 5, QTableWidgetItem(str(v.get("edificio") or "")))
                self.tbl_viviendas.setItem(idx, 6, QTableWidgetItem(str(v.get("vivienda") or "")))
                self.tbl_viviendas.setItem(idx, 7, QTableWidgetItem(str(v.get("numero_upe") or "")))
                self.tbl_viviendas.setItem(idx, 8, QTableWidgetItem(str(v.get("calle") or "")))
                self.tbl_viviendas.setItem(idx, 9, QTableWidgetItem(str(v.get("clave_catastral") or "")))
                self.tbl_viviendas.setItem(idx, 10, QTableWidgetItem(str(v.get("descripcion") or "")))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar las viviendas: {e}")

    def _on_v_limpiar(self):
        self._on_v_regimen_changed()

    def _on_v_descargar_plantilla(self):
        """Genera una plantilla Excel (.xlsx) estandarizada para la carga de viviendas."""
        des_id = self.cmb_v_desarrollo.currentData()
        reg_id = self.cmb_v_regimen.currentData()
        if not des_id:
            QMessageBox.warning(self, "Desarrollo Requerido", "Por favor seleccione un desarrollo para generar la plantilla.")
            return

        nombre_des = "".join(c for c in self.cmb_v_desarrollo.currentText() if c.isalnum() or c in (" ", "_", "-")).strip()
        nombre_sugerido = f"Plantilla_Viviendas_{nombre_des}.xlsx"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Plantilla Excel de Viviendas", nombre_sugerido, "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Viviendas"

            headers = [
                "SM", "MANZANA", "LOTE", "EDIFICIO", "VIVIENDA",
                "NUMERO_UPE", "CALLE", "CLAVE_CATASTRAL", "CUENTA_PREDIAL", "DESCRIPCION"
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

            # Filas de ejemplo según si hay régimen o no
            if reg_id:
                sample_rows = [
                    ["115", "01", "01", "TORRE A", "101", "UPE-001", "AV. HUAYACAN", "", "", "Departamento Nivel 1"],
                    ["115", "01", "01", "TORRE A", "102", "UPE-002", "AV. HUAYACAN", "", "", "Departamento Nivel 1"],
                    ["115", "01", "01", "TORRE B", "201", "UPE-003", "AV. HUAYACAN", "", "", "Departamento Nivel 2"]
                ]
            else:
                sample_rows = [
                    ["15", "01", "10", "", "10", "", "CALLE PRIVADA SOL", "MZ01-LT10", "", "Casa Unifamiliar Prototipo A"],
                    ["15", "01", "11", "", "11", "", "CALLE PRIVADA SOL", "MZ01-LT11", "", "Casa Unifamiliar Prototipo B"]
                ]

            for row in sample_rows:
                ws.append(row)

            # Autoancho
            col_widths = {"A": 10, "B": 14, "C": 12, "D": 16, "E": 14, "F": 16, "G": 24, "H": 22, "I": 20, "J": 32}
            for col_letter, width in col_widths.items():
                ws.column_dimensions[col_letter].width = width

            wb.save(file_path)
            QMessageBox.information(
                self, "Plantilla Generada",
                f"Plantilla Excel generada con éxito en:\n{file_path}\n\n"
                "Puede completarla con los predios y cargarla mediante 'Seleccionar Archivo'."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar la plantilla: {e}")

    def _on_v_seleccionar_archivo(self):
        """Lee el archivo Excel, valida el total de UPEs vs régimen y previsualiza en la tabla."""
        des_id = self.cmb_v_desarrollo.currentData()
        reg_id = self.cmb_v_regimen.currentData()

        if not des_id:
            QMessageBox.warning(self, "Desarrollo Requerido", "Por favor seleccione un Desarrollo antes de cargar el archivo.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Archivo de Viviendas", "", "Excel Files (*.xlsx *.xls)"
        )
        if not file_path:
            return

        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows or len(rows) < 2:
                QMessageBox.warning(self, "Archivo Vacío", "El archivo seleccionado no contiene filas de datos.")
                return

            # Mapeo de cabeceras
            raw_headers = [str(h or "").strip().upper() for h in rows[0]]
            def get_col_idx(*names):
                for name in names:
                    if name.upper() in raw_headers:
                        return raw_headers.index(name.upper())
                return -1

            idx_sm = get_col_idx("SM", "SUPERMANZANA", "REGION")
            idx_mz = get_col_idx("MANZANA", "MZA", "MZ")
            idx_lt = get_col_idx("LOTE", "LT")
            idx_ed = get_col_idx("EDIFICIO", "EDIF", "TORRE")
            idx_vi = get_col_idx("VIVIENDA", "VIV", "DEPTO", "DEPARTAMENTO", "CASA")
            idx_upe = get_col_idx("NUMERO_UPE", "NUM_UPE", "NO_UPE", "UPE")
            idx_calle = get_col_idx("CALLE", "VIALIDAD", "DIRECCION")
            idx_cat = get_col_idx("CLAVE_CATASTRAL", "CATASTRO", "CLAVE_CAT")
            idx_pred = get_col_idx("CUENTA_PREDIAL", "PREDIAL")
            idx_desc = get_col_idx("DESCRIPCION", "DESCRIPCIÓN", "NOTAS", "OBSERVACIONES")

            if idx_mz == -1 or idx_lt == -1 or idx_vi == -1:
                QMessageBox.critical(
                    self, "Encabezados Faltantes",
                    "El archivo debe contener al menos las columnas 'MANZANA', 'LOTE' y 'VIVIENDA'."
                )
                return

            records = []
            for row in rows[1:]:
                if not any(row):
                    continue
                mz = str(row[idx_mz] or "").strip()
                lt = str(row[idx_lt] or "").strip()
                vi = str(row[idx_vi] or "").strip()
                if not mz or not lt or not vi:
                    continue

                sm = str(row[idx_sm] or "").strip() if idx_sm != -1 and row[idx_sm] is not None else ""
                ed = str(row[idx_ed] or "").strip() if idx_ed != -1 and row[idx_ed] is not None else ""
                upe = str(row[idx_upe] or "").strip() if idx_upe != -1 and row[idx_upe] is not None else ""
                calle = str(row[idx_calle] or "").strip() if idx_calle != -1 and row[idx_calle] is not None else ""
                cat = str(row[idx_cat] or "").strip() if idx_cat != -1 and row[idx_cat] is not None else ""
                pred = str(row[idx_pred] or "").strip() if idx_pred != -1 and row[idx_pred] is not None else ""
                desc = str(row[idx_desc] or "").strip() if idx_desc != -1 and row[idx_desc] is not None else ""

                records.append({
                    "sm": sm,
                    "mz": mz,
                    "lt": lt,
                    "edificio": ed,
                    "vivienda": vi,
                    "numero_upe": upe,
                    "calle": calle,
                    "clave_catastral": cat,
                    "cuenta_predial": pred,
                    "descripcion": desc
                })

            if not records:
                QMessageBox.warning(self, "Sin Registros Válidos", "No se detectaron registros con Manzana, Lote y Vivienda válidos.")
                return

            # =========================================================
            # VALIDACIÓN CRÍTICA: TOTAL EN ARCHIVO VS TOTAL UPES EN RÉGIMEN
            # =========================================================
            if reg_id:
                # Obtener capacidad de UPEs
                if self.api_client.connect_via_api:
                    all_regs = self.api_client.request("GET", "/api/admin/data/satc_regimenes")
                    target = next((r for r in all_regs if r.get("regimen_id") == reg_id), None)
                    tot_upes = target.get("total_upes", 0) if target else 0
                else:
                    with self.db_connector.get_session() as session:
                        svc = HousingLifeCycleService(session)
                        target = svc.regimen_repo.get_by_id(reg_id)
                        tot_upes = target.total_upes if target else 0

                if len(records) > tot_upes:
                    QMessageBox.critical(
                        self, "Validación de Capacidad de Régimen (Error)",
                        f"El archivo contiene {len(records)} viviendas, lo cual SUPERA la capacidad autorizada "
                        f"del Régimen ({tot_upes} UPEs).\n\n"
                        f"Por favor corrija el archivo Excel para no exceder las {tot_upes} UPEs del macro-lote."
                    )
                    return

            self._v_parsed_records = records
            self.lbl_vkpi_archivo.setText(f"Archivo: {os.path.basename(file_path)}")
            self.lbl_vkpi_total_arch.setText(f"En Archivo: {len(records)}")

            # Consultar existentes en BD para marcar si es NUEVO o DUPLICADO
            if self.api_client.connect_via_api:
                params = {"desarrollo_id": des_id}
                if reg_id:
                    params["regimen_id"] = reg_id
                v_existentes = self.api_client.request("GET", f"/api/admin/satc/viviendas/{des_id}", data=params)
            else:
                with self.db_connector.get_session() as session:
                    svc = HousingLifeCycleService(session)
                    if reg_id:
                        v_existentes = svc.get_viviendas_by_regimen(reg_id)
                    else:
                        v_existentes = svc.get_viviendas_by_desarrollo(des_id, solo_sin_regimen=True)

            existentes_keys = {
                (
                    (v.get("sm") or "").strip().upper(),
                    (v.get("mz") or "").strip().upper(),
                    (v.get("lt") or "").strip().upper(),
                    (v.get("edificio") or "").strip().upper(),
                    (v.get("vivienda") or "").strip().upper(),
                    (v.get("numero_upe") or "").strip().upper()
                )
                for v in v_existentes
            }

            nuevos_cnt = 0
            duplicados_cnt = 0

            self.tbl_viviendas.setRowCount(len(records))
            reg_label = self.cmb_v_regimen.currentText() if reg_id else "FRACCIONAMIENTO"

            for idx, r in enumerate(records):
                k = (
                    r["sm"].upper(),
                    r["mz"].upper(),
                    r["lt"].upper(),
                    r["edificio"].upper(),
                    r["vivienda"].upper(),
                    r["numero_upe"].upper()
                )
                es_dup = k in existentes_keys
                if es_dup:
                    duplicados_cnt += 1
                    item_st = QTableWidgetItem("DUPLICADO")
                    item_st.setForeground(QColor("#E11D48"))
                else:
                    nuevos_cnt += 1
                    item_st = QTableWidgetItem("NUEVO")
                    item_st.setForeground(QColor("#16A34A"))

                self.tbl_viviendas.setItem(idx, 0, item_st)
                self.tbl_viviendas.setItem(idx, 1, QTableWidgetItem(reg_label))
                self.tbl_viviendas.setItem(idx, 2, QTableWidgetItem(r["sm"]))
                self.tbl_viviendas.setItem(idx, 3, QTableWidgetItem(r["mz"]))
                self.tbl_viviendas.setItem(idx, 4, QTableWidgetItem(r["lt"]))
                self.tbl_viviendas.setItem(idx, 5, QTableWidgetItem(r["edificio"]))
                self.tbl_viviendas.setItem(idx, 6, QTableWidgetItem(r["vivienda"]))
                self.tbl_viviendas.setItem(idx, 7, QTableWidgetItem(r["numero_upe"]))
                self.tbl_viviendas.setItem(idx, 8, QTableWidgetItem(r["calle"]))
                self.tbl_viviendas.setItem(idx, 9, QTableWidgetItem(r["clave_catastral"]))
                self.tbl_viviendas.setItem(idx, 10, QTableWidgetItem(r["descripcion"]))

            self.lbl_vkpi_nuevos.setText(f"Nuevos: {nuevos_cnt}")
            self.lbl_vkpi_duplicados.setText(f"Duplicados: {duplicados_cnt}")
            self.btn_v_ejecutar.setEnabled(nuevos_cnt > 0)

        except Exception as e:
            QMessageBox.critical(self, "Error al Analizar Excel", f"Ocurrió un error al procesar el archivo:\n{e}")

    def _on_v_ejecutar_importacion(self):
        """Ejecuta la importación en un hilo background mediante ViviendasImportWorker."""
        des_id = self.cmb_v_desarrollo.currentData()
        reg_id = self.cmb_v_regimen.currentData()

        if not des_id or not self._v_parsed_records:
            return

        total_recs = len(self._v_parsed_records)
        reg_txt = f"al Régimen '{self.cmb_v_regimen.currentText()}'" if reg_id else "directamente al Desarrollo"

        reply = QMessageBox.question(
            self, "Confirmar Importación",
            f"¿Desea importar {total_recs} registros de vivienda {reg_txt}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply != QMessageBox.Yes:
            return

        self.btn_v_ejecutar.setEnabled(False)
        self.btn_v_seleccionar.setEnabled(False)

        self._v_worker = ViviendasImportWorker(
            api_client=self.api_client,
            db_connector=self.db_connector,
            desarrollo_id=des_id,
            regimen_id=reg_id,
            records=self._v_parsed_records,
            usuario_id=self.current_user_id or 1,
            sesion_id=self.current_sesion_id
        )
        self._v_worker.finished.connect(self._on_v_worker_finished)
        self._v_worker.start()

    def _on_v_worker_finished(self, success: bool, result: dict, error_msg: str):
        self.btn_v_seleccionar.setEnabled(True)
        if success:
            nuevos = result.get("nuevos_insertados", 0)
            dups = result.get("omitidos_duplicados", 0)
            QMessageBox.information(
                self, "Importación Exitosa",
                f"Proceso de importación completado exitosamente.\n\n"
                f"• Nuevas viviendas creadas: {nuevos}\n"
                f"• Omitidas por duplicidad: {dups}"
            )
            self._v_parsed_records = []
            self._on_v_regimen_changed()
            self.refresh_data()
        else:
            QMessageBox.critical(self, "Error en la Importación", f"No se pudo completar la importación:\n{error_msg}")
            self.btn_v_ejecutar.setEnabled(True)

