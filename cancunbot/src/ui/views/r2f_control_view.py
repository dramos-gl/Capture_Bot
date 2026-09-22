"""R2F Cancun Recibos y Facturas Admin control panel (CancunBot module)."""

import os
import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QLabel, QScrollArea, QStackedWidget, QFileDialog, QDialog, QTableWidgetItem, QLineEdit, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QDateTime, QSize
from PySide6.QtGui import QDesktopServices, QAction
from PySide6.QtCore import QUrl

from sar.src.ui.design_system.components import (
    CustomCard, CustomButton, StyledDataTable, FilterBar, CustomComboBox, CustomLabel, CustomInput, CustomCheckBox, NavigationSidebar, KeepOpenMenu,
    GLMessageDialog, DialogType, GLMessageBox as QMessageBox
)
from sar.src.ui.design_system.components.molecules.gl_stat_card import StatCard
from sar.src.ui.design_system.utils.icons import Icons
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.theme_manager import ThemeManager
from cancunbot.src.services.r2f_ui_service import R2FUIService

logger = logging.getLogger(__name__)


class R2FLoadWorker(QThread):
    """Background worker thread to load R2F Receipts via R2FUIService with pagination."""
    result_ready = Signal(list, int) # data, total_count
    error_occurred = Signal(str)
    
    def __init__(self, ui_service, limit: int, offset: int, search_text: str, estado_filter: str):
        super().__init__()
        self.ui_service = ui_service
        self.limit = limit
        self.offset = offset
        self.search_text = search_text
        self.estado_filter = estado_filter
        self._is_cancelled = False
        
    def cancel(self):
        self._is_cancelled = True
        
    def run(self):
        try:
            if self._is_cancelled:
                return
            data_list, total_count = self.ui_service.list_recibos_paginated(
                limit=self.limit,
                offset=self.offset,
                search_text=self.search_text,
                estado_filter=self.estado_filter
            )
            if not self._is_cancelled:
                self.result_ready.emit(data_list, total_count)
        except Exception as e:
            if not self._is_cancelled:
                self.error_occurred.emit(str(e))



class R2FControlView(QWidget):
    """Módulo Independiente de Control de Recibos y Facturas (R2F)."""
    logout_requested = Signal()
    
    def __init__(self, db_connector, api_client=None, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.api_client = api_client
        self.ui_service = R2FUIService(db_connector=self.db_connector, api_client=self.api_client)
        self.usuario_id = 1
        
        # Variables de estado para Capturar Orden (Replicando Asignar/Validar)
        self._current_excel_path = None
        self._pending_folios_list = []

        # Layout exterior (Sidebar + Área de Contenido)
        self.main_h_layout = QHBoxLayout(self)
        self.main_h_layout.setContentsMargins(0, 0, 0, 0)
        self.main_h_layout.setSpacing(0)
        
        # 1. SIDEBAR DE NAVEGACIÓN COMPLETO CON HAMBURGUESA ☰
        self.sidebar = NavigationSidebar(self)
        self.sidebar.brand_title.setText("R2F")
        self.sidebar.brand_subtitle.setText("Control de Recibos")
        
        # Omitir explícitamente el botón "Cambiar Tema" (Tema Claro Estricto)
        if hasattr(self.sidebar, "theme_btn") and self.sidebar.theme_btn:
            self.sidebar.theme_btn.hide()
            
        self.sidebar.set_username(self._get_username_string())
        self.sidebar.logout_requested.connect(self.logout_requested.emit)
        
        # Habilitar ítems del submenú Órdenes y Control R2F
        self.sidebar.show_item("dashboard")
        self.sidebar.show_item("ordenes")
        self.sidebar.show_item("capturar_orden")
        self.sidebar.show_item("ordenes_capturadas")
        self.sidebar.show_item("r2f_control")
        self.sidebar.select_item("r2f_control")
        self.sidebar.nav_selected.connect(self._on_sidebar_item_selected)
        
        self.main_h_layout.addWidget(self.sidebar)
        
        # 2. ÁREA PRINCIPAL CON QSTACKEDWIDGET
        self.content_area = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        self.main_stack = QStackedWidget(self.content_area)
        
        # Crear sub-vistas
        self.page_capturar_orden = self._build_capturar_orden_page()
        self.page_ordenes_capturadas = self._build_ordenes_capturadas_page()
        self.page_bandeja_control = self._build_bandeja_control_page()
        
        self.main_stack.addWidget(self.page_capturar_orden)       # Index 0: Capturar Orden
        self.main_stack.addWidget(self.page_ordenes_capturadas)   # Index 1: Órdenes Capturadas
        self.main_stack.addWidget(self.page_bandeja_control)      # Index 2: Bandeja de Control
        
        self.content_layout.addWidget(self.main_stack, stretch=1)
        
        # Pie de página global SAR
        self.global_footer_bar = QWidget(self.content_area)
        self.global_footer_layout = QHBoxLayout(self.global_footer_bar)
        self.global_footer_layout.setContentsMargins(16, 2, 20, 6)
        self.global_footer_layout.setSpacing(0)
        
        self.lbl_global_footer = QLabel("Sistema de Administración de Recibos & Facturas | R2F | v1.0.0", self.global_footer_bar)
        self.lbl_global_footer.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_global_footer.setStyleSheet("color: #94A3B8; font-size: 10px; background: transparent;")
        
        self.global_footer_layout.addStretch()
        self.global_footer_layout.addWidget(self.lbl_global_footer)
        self.content_layout.addWidget(self.global_footer_bar)
        
        self.main_h_layout.addWidget(self.content_area, stretch=1)
        
        # Seleccionar Bandeja de Control por defecto (Index 2)
        self.main_stack.setCurrentIndex(2)

    # -------------------------------------------------------------------------
    # PÁGINA 1: CAPTURAR ÓRDEN / IMPORTAR ARCHIVOS
    # -------------------------------------------------------------------------
    def _build_capturar_orden_page(self) -> QWidget:
        page = QWidget()
        scroll_area = QScrollArea(page)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QWidget#capturaScrollContent {
                background-color: transparent;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setObjectName("capturaScrollContent")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # 1. TARJETA SUPERIOR: CONFIGURACIÓN Y ACCIONES (MODELO ASIGNAR/VALIDAR)
        card_form = CustomCard(title="", parent=scroll_content)
        
        # Header Layout con título en negrita y badge de contexto
        header_layout = QHBoxLayout()
        self.lbl_title_captura = CustomLabel("Captura y Procesamiento de Órdenes R2F", variant="subheader")
        header_layout.addWidget(self.lbl_title_captura)
        
        self.lbl_filtro_orden_info = QLabel(" | Modo: Carga Masiva de Folios", self)
        self.lbl_filtro_orden_info.setStyleSheet("color: #2563EB; font-weight: bold; font-size: 13px; background: transparent;")
        header_layout.addWidget(self.lbl_filtro_orden_info)
        
        header_layout.addStretch()
        card_form.layout.addLayout(header_layout)

        # Grid de Formulario a 2 Columnas
        form_grid = QVBoxLayout()
        form_grid.setSpacing(12)

        # Fila 1: Modo de Orden (Col 1) | Destino de la Orden (Nombre nuevo o Selector existente) (Col 2)
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(16)

        col_modo = QVBoxLayout()
        lbl_modo_orden = CustomLabel("Acción con la Orden *", variant="body")
        lbl_modo_orden.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        self.cb_modo_orden = CustomComboBox(self)
        self.cb_modo_orden.setFixedHeight(36)
        self.cb_modo_orden.addItems(["CREAR NUEVA ORDEN", "ANEXAR A ORDEN EXISTENTE"])
        self.cb_modo_orden.currentTextChanged.connect(self._on_modo_orden_changed)
        col_modo.addWidget(lbl_modo_orden)
        col_modo.addWidget(self.cb_modo_orden)

        self.col_orden_target = QVBoxLayout()
        self.lbl_orden_target = CustomLabel("Descripción de la Nueva Orden *", variant="body")
        self.lbl_orden_target.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        
        self.txt_desc_orden = CustomInput("Ej. Lote Notaría 12 - Septiembre 2026")
        self.txt_desc_orden.setFixedHeight(36)
        
        self.cb_ordenes_existentes = CustomComboBox(self)
        self.cb_ordenes_existentes.setFixedHeight(36)
        self.cb_ordenes_existentes.hide()
        
        self.col_orden_target.addWidget(self.lbl_orden_target)
        self.col_orden_target.addWidget(self.txt_desc_orden)
        self.col_orden_target.addWidget(self.cb_ordenes_existentes)

        row1_layout.addLayout(col_modo, stretch=1)
        row1_layout.addLayout(self.col_orden_target, stretch=1)
        form_grid.addLayout(row1_layout)

        # Fila 2: Tipo de Origen / Fuente (Col 1) | Solicitante / Operador (Col 2)
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(16)

        col_origen = QVBoxLayout()
        lbl_tipo_origen = CustomLabel("Tipo de Origen / Fuente *", variant="body")
        lbl_tipo_origen.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        self.cb_tipo_origen = CustomComboBox(self)
        self.cb_tipo_origen.setFixedHeight(36)
        self.cb_tipo_origen.addItems(["PLANTILLA EXCEL (FOLIOS)", "BOLETAS / PASES DE CAJA (PDF)"])
        col_origen.addWidget(lbl_tipo_origen)
        col_origen.addWidget(self.cb_tipo_origen)

        col_solicitante = QVBoxLayout()
        lbl_solicitante = CustomLabel("Solicitante Externo / Operador", variant="body")
        lbl_solicitante.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        self.txt_solicitante = CustomInput("Ej. Pedro Gómez / Ing. Ramírez")
        self.txt_solicitante.setFixedHeight(36)
        col_solicitante.addWidget(lbl_solicitante)
        col_solicitante.addWidget(self.txt_solicitante)

        row2_layout.addLayout(col_origen, stretch=1)
        row2_layout.addLayout(col_solicitante, stretch=1)
        form_grid.addLayout(row2_layout)

        # Fila 3: Observaciones del Lote
        row3_obs = QHBoxLayout()
        col_obs = QVBoxLayout()
        lbl_obs = CustomLabel("Observaciones del Lote", variant="body")
        lbl_obs.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        self.txt_obs_lote = CustomInput("Notas u observaciones adicionales para el lote (opcional)...")
        self.txt_obs_lote.setFixedHeight(36)
        col_obs.addWidget(lbl_obs)
        col_obs.addWidget(self.txt_obs_lote)
        row3_obs.addLayout(col_obs)
        form_grid.addLayout(row3_obs)

        # Fila 3: Barra Unificada de Acciones (Importar Excel -> Descargar Plantilla -> Confirmar -> Limpiar -> Label Archivo)
        row3_layout = QHBoxLayout()
        row3_layout.setSpacing(10)

        self.btn_importar_excel = CustomButton("Importar Excel", is_secondary=True, min_width=135, parent=self)
        self.btn_importar_excel.setIcon(Icons.excel())
        self.btn_importar_excel.setFixedHeight(36)
        self.btn_importar_excel.setToolTip("Seleccionar y analizar archivo Excel de folios")
        self.btn_importar_excel.clicked.connect(self._on_importar_excel)

        self.btn_importar_pdf = CustomButton("Importar Boletas PDF", is_secondary=True, min_width=150, parent=self)
        self.btn_importar_pdf.setIcon(Icons.documento_descargar(Colors.TEXT_LIGHT_PRIMARY))
        self.btn_importar_pdf.setFixedHeight(36)
        self.btn_importar_pdf.setToolTip("Escanear e importar archivos PDF de Pases de Caja")
        self.btn_importar_pdf.clicked.connect(self._on_importar_pdf)

        self.btn_descargar_plantilla = CustomButton("Descargar Plantilla", is_secondary=True, min_width=150, parent=self)
        self.btn_descargar_plantilla.setIcon(Icons.documento_descargar(Colors.TEXT_LIGHT_PRIMARY))
        self.btn_descargar_plantilla.setFixedHeight(36)
        self.btn_descargar_plantilla.setToolTip("Descargar formato de plantilla Excel oficial")
        self.btn_descargar_plantilla.clicked.connect(self._on_descargar_plantilla)

        self.btn_confirmar_orden = CustomButton("Confirmar", is_secondary=False, min_width=CustomButton.DEFAULT_MIN_WIDTH, parent=self)
        self.btn_confirmar_orden.setIcon(Icons.aceptar("#FFFFFF"))
        self.btn_confirmar_orden.setFixedHeight(36)
        self.btn_confirmar_orden.setToolTip("Confirmar y registrar la orden y folios validados")
        self.btn_confirmar_orden.setEnabled(False)
        self.btn_confirmar_orden.clicked.connect(self._on_confirmar_captura_orden)

        self.btn_limpiar_captura = CustomButton("Limpiar", is_clean_btn=True, min_width=CustomButton.DEFAULT_MIN_WIDTH, parent=self)
        self.btn_limpiar_captura.setFixedHeight(36)
        self.btn_limpiar_captura.setToolTip("Limpiar campos y previsualización")
        self.btn_limpiar_captura.clicked.connect(self._on_limpiar_captura)

        self.lbl_excel_path = QLabel("Ningún archivo seleccionado", self)
        self.lbl_excel_path.setStyleSheet("color: #64748B; font-style: italic; margin-left: 8px;")

        row3_layout.addWidget(self.btn_importar_excel)
        row3_layout.addWidget(self.btn_importar_pdf)
        row3_layout.addWidget(self.btn_descargar_plantilla)
        row3_layout.addWidget(self.btn_confirmar_orden)
        row3_layout.addWidget(self.btn_limpiar_captura)
        row3_layout.addWidget(self.lbl_excel_path)
        row3_layout.addStretch()

        form_grid.addLayout(row3_layout)
        card_form.layout.addLayout(form_grid)
        layout.addWidget(card_form)

        # 2. TARJETA INFERIOR: PREVISUALIZACIÓN DE COINCIDENCIAS Y VALIDACIONES (StyledDataTable)
        self.card_preview = CustomCard(title="Previsualización de Folios y Validaciones", parent=scroll_content)
        self.preview_table = StyledDataTable(
            ["Fila / Item", "Folio Electrónico", "Folio Pase Caja", "Tipo Folio", "RFC Detectado", "Desarrollo", "Estatus Validación"],
            parent=self
        )
        self.preview_table.setMinimumHeight(240)
        self.preview_table.setMinimumWidth(200)
        self.card_preview.add_widget(self.preview_table)
        layout.addWidget(self.card_preview)

        layout.addStretch()

        scroll_area.setWidget(scroll_content)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll_area)
        return page

    # -------------------------------------------------------------------------
    # PÁGINA 2: ÓRDENES CAPTURADAS
    # -------------------------------------------------------------------------
    def _build_ordenes_capturadas_page(self) -> QWidget:
        page = QWidget()
        scroll_area = QScrollArea(page)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header
        h_layout = QHBoxLayout()
        lbl_t = CustomLabel("📋 Órdenes Capturadas Registradas", variant="header")
        h_layout.addWidget(lbl_t)
        h_layout.addStretch()
        
        btn_refresh_ord = QPushButton(scroll_content)
        btn_refresh_ord.setObjectName("filterBarActionBtn")
        btn_refresh_ord.setIcon(Icons.actualizar("#FFFFFF"))
        btn_refresh_ord.setIconSize(QSize(20, 20))
        btn_refresh_ord.setFixedSize(35, 35)
        btn_refresh_ord.setToolTip("Actualizar Órdenes")
        btn_refresh_ord.clicked.connect(self._refresh_ordenes_table)
        h_layout.addWidget(btn_refresh_ord)
        layout.addLayout(h_layout)

        # Card con Tabla de Órdenes
        card = CustomCard("📋 LISTADO DE ÓRDENES CANCÚN", parent=scroll_content)
        self.table_ordenes = StyledDataTable([
            "ID", "Folio Orden", "Descripción", "Lotes", "Total Folios", "Procesados", "Estado", "Fecha Creación"
        ], parent=scroll_content)
        self.table_ordenes.doubleClicked.connect(self._on_orden_double_clicked)
        card.add_widget(self.table_ordenes)
        
        layout.addWidget(card)
        scroll_area.setWidget(scroll_content)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll_area)
        return page

    # -------------------------------------------------------------------------
    # PÁGINA 3: BANDEJA DE CONTROL DE RECIBOS Y FACTURAS
    # -------------------------------------------------------------------------
    def _build_bandeja_control_page(self) -> QWidget:
        page = QWidget()
        scroll_area = QScrollArea(page)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        self.layout = QVBoxLayout(scroll_content)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(20)
        
        # Header
        self.header_layout = QHBoxLayout()
        self.indicator_bar = QFrame(self)
        self.indicator_bar.setFixedWidth(4)
        self.indicator_bar.setFixedHeight(28)
        self.header_layout.addWidget(self.indicator_bar)
        
        title_text_layout = QVBoxLayout()
        self.lbl_title = CustomLabel("Tablero de Control Operativo R2F", variant="header")
        self.lbl_subtitle = CustomLabel("Resumen general del estado de recibos y facturación", variant="muted")
        title_text_layout.addWidget(self.lbl_title)
        title_text_layout.addWidget(self.lbl_subtitle)
        self.header_layout.addLayout(title_text_layout)
        
        self.header_layout.addStretch()

        # Botón para ejecutar el bot de Cancún
        self.btn_ejecutar_bot = CustomButton("🤖 Abrir Bot R2F Cancún", is_secondary=True)
        self.btn_ejecutar_bot.clicked.connect(self._abrir_vista_cancun_ordenes)
        self.header_layout.addWidget(self.btn_ejecutar_bot)

        # Reloj
        self.time_widget = QWidget(self)
        time_layout = QHBoxLayout(self.time_widget)
        time_layout.setContentsMargins(0, 0, 0, 0)
        lbl_cal = QLabel()
        lbl_cal.setPixmap(Icons.calendar().pixmap(16, 16))
        time_layout.addWidget(lbl_cal)
        time_layout.addWidget(CustomLabel(QDateTime.currentDateTime().toString("dd/MM/yyyy  hh:mm AP"), variant="body"))
        self.header_layout.addWidget(self.time_widget)
        
        self.btn_update = QPushButton(self)
        self.btn_update.setObjectName("filterBarActionBtn")
        self.btn_update.setIcon(Icons.actualizar("#FFFFFF"))
        self.btn_update.setFixedSize(35, 35)
        self.btn_update.setToolTip("Actualizar Tablero R2F")
        self.btn_update.clicked.connect(self.refresh_data)
        self.header_layout.addWidget(self.btn_update)
        
        self.layout.addLayout(self.header_layout)
        
        # Tarjetas KPI
        self.kpi_widget = QWidget(self)
        kpi_layout = QHBoxLayout(self.kpi_widget)
        kpi_layout.setContentsMargins(0, 0, 0, 0)
        kpi_layout.setSpacing(10)
        
        self.card_total = StatCard("Total Descargados", "0", "file_text", color_hex=Colors.CHART_EMERALD_DARK, parent=self.kpi_widget, subtitle="Recibos")
        self.card_pendientes = StatCard("Pendientes Facturar", "0", "clock", color_hex=Colors.CHART_AMBER, parent=self.kpi_widget, subtitle="Recibos")
        self.card_facturados = StatCard("Facturados", "0", "shield_check", color_hex=Colors.CHART_TEAL, parent=self.kpi_widget, subtitle="Recibos")
        self.card_errores = StatCard("Errores Factura", "0", "x_circle", color_hex=Colors.CHART_CORAL, parent=self.kpi_widget, subtitle="Recibos")
        self.card_invalidos = StatCard("Invalidos", "0", "alert_triangle", color_hex=Colors.ERROR, parent=self.kpi_widget, subtitle="Recibos")
        self.card_lotes = StatCard("Lotes Activos", "0", "list_icon", color_hex=Colors.CHART_BLUE, parent=self.kpi_widget, subtitle="Lotes")
        
        kpi_layout.addWidget(self.card_total, stretch=1)
        kpi_layout.addWidget(self.card_pendientes, stretch=1)
        kpi_layout.addWidget(self.card_facturados, stretch=1)
        kpi_layout.addWidget(self.card_errores, stretch=1)
        kpi_layout.addWidget(self.card_invalidos, stretch=1)
        kpi_layout.addWidget(self.card_lotes, stretch=1)
        
        self.layout.addWidget(self.kpi_widget)
        
        # Card con Tabla principal y Header de búsqueda en la misma línea
        self.card_frame = QFrame(self)
        self.card_frame.setObjectName("cardFrame")
        self.card_layout = QVBoxLayout(self.card_frame)
        self.card_layout.setContentsMargins(20, 20, 20, 20)
        self.card_layout.setSpacing(16)
        
        # Header Layout (Título de la tabla en línea con la búsqueda y filtros)
        self.table_header_layout = QHBoxLayout()
        self.table_header_layout.setContentsMargins(0, 0, 0, 0)
        self.table_header_layout.setSpacing(12)
        
        self.lbl_table_icon = QLabel()
        self.lbl_table_icon.setPixmap(Icons.file_text("#2563EB").pixmap(18, 18))
        self.lbl_table_icon.setStyleSheet("background: transparent;")
        
        self.lbl_table_title = CustomLabel("Bandeja de Control de Recibos & Facturas", variant="subheader")
        self.lbl_table_title.setObjectName("dashboardTableTitle")
        
        self.table_header_layout.addWidget(self.lbl_table_icon)
        self.table_header_layout.addWidget(self.lbl_table_title)
        self.table_header_layout.addStretch()
        
        # Search Box (Replicated sizing & elasticity from Dashboard/Inventory)
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Buscar por folio, RFC, contribuyente...")
        self.search_input.setMinimumWidth(320)
        self.search_input.setMaximumWidth(520)
        self.search_input.setFixedHeight(36)
        self.search_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.addAction(Icons.search("#64748B"), QLineEdit.LeadingPosition)
        self.search_input.returnPressed.connect(self._on_search_trigger)
        self.search_input.textChanged.connect(self._filter_table_by_text)
        self.table_header_layout.addWidget(self.search_input)
        
        # Botón Buscar explícito
        self.btn_buscar = QPushButton()
        self.btn_buscar.setObjectName("secondaryBtn")
        self.btn_buscar.setIcon(Icons.buscar("#FFFFFF") if ThemeManager.is_dark_active() else Icons.buscar("#334155"))
        self.btn_buscar.setFixedSize(36, 36)
        self.btn_buscar.setToolTip("Buscar (o presione Enter)")
        self.btn_buscar.clicked.connect(self._on_search_trigger)
        self.table_header_layout.addWidget(self.btn_buscar)
        
        # Botón Filtro (con menú de estados)
        self.btn_filter = QPushButton()
        self.btn_filter.setObjectName("secondaryBtn")
        self.btn_filter.setIcon(Icons.filter_icon("#475569"))
        self.btn_filter.setFixedSize(36, 36)
        self.btn_filter.setToolTip("Filtrar por estado del recibo")
        self.btn_filter.clicked.connect(self._show_estado_filter_menu)
        self.table_header_layout.addWidget(self.btn_filter)
        
        # Botón Más Opciones (Acciones contextuales secundarias)
        self.btn_more = QPushButton()
        self.btn_more.setObjectName("secondaryBtn")
        self.btn_more.setIcon(Icons.more_vertical("#475569"))
        self.btn_more.setFixedSize(36, 36)
        self.btn_more.setToolTip("Más opciones")
        self.btn_more.clicked.connect(self._show_more_options_menu)
        self.table_header_layout.addWidget(self.btn_more)
        
        # Botón Actualizar explícito
        self.btn_refresh = QPushButton()
        self.btn_refresh.setObjectName("secondaryBtn")
        self.btn_refresh.setIcon(Icons.actualizar("#334155"))
        self.btn_refresh.setFixedSize(36, 36)
        self.btn_refresh.setToolTip("Actualizar Registros")
        self.btn_refresh.clicked.connect(self.refresh_data)
        self.table_header_layout.addWidget(self.btn_refresh)
        
        self.card_layout.addLayout(self.table_header_layout)
        
        # Tabla principal de control
        headers = ["ID", "Folio/Referencia", "RFC", "Contribuyente", "Concepto de Cobro", "SM", "MZ", "L", "Total", "Fecha", "Estado"]
        self.table = StyledDataTable(headers, parent=self)
        self.table.setMinimumHeight(200)
        self.table.setColumnHidden(0, True)
        self.card_layout.addWidget(self.table)
        
        # Paginador (Diseño idéntico a Dashboard de Derechos)
        self.current_page = 1
        self.page_size = 200
        self.all_data = []
        self.total_items = 0
        self.active_worker = None
        
        self.footer_layout = QHBoxLayout()
        self.footer_layout.setContentsMargins(0, 8, 0, 0)
        
        self.lbl_pagination_info = CustomLabel("Mostrando 0 a 0 de 0 registros", variant="muted")
        self.lbl_pagination_info.setObjectName("dashboardPaginationInfo")
        self.footer_layout.addWidget(self.lbl_pagination_info)
        
        self.footer_layout.addStretch()
        
        # Selector de tamaño de página
        self.cb_page_size = CustomComboBox(self)
        self.cb_page_size.addItems(["50 por página", "100 por página", "200 por página"])
        self.cb_page_size.setFixedWidth(120)
        self.cb_page_size.setCurrentIndex(2)
        self.cb_page_size.currentTextChanged.connect(self._on_page_size_changed)
        self.footer_layout.addWidget(self.cb_page_size)
        
        # Contenedor de botones numéricos de paginación
        self.pagination_widget = QWidget(self)
        self.pagination_widget.setStyleSheet("background: transparent;")
        self.pag_btn_layout = QHBoxLayout(self.pagination_widget)
        self.pag_btn_layout.setContentsMargins(0, 0, 0, 0)
        self.pag_btn_layout.setSpacing(4)
        
        self.footer_layout.addWidget(self.pagination_widget)
        self.card_layout.addLayout(self.footer_layout)
        self.layout.addWidget(self.card_frame)
        
        scroll_area.setWidget(scroll_content)
        
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll_area)
        
        self._current_search_text = ""
        self._current_estado_filter = "Todos"
        
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._on_search_timer_timeout)
        
        self.refresh_data()
        
        return page

    # -------------------------------------------------------------------------
    # NAVEGACIÓN Y HANDLERS DEL SIDEBAR
    # -------------------------------------------------------------------------
    def _on_sidebar_item_selected(self, key: str):
        """Maneja la conmutación entre sub-páginas internas mediante el Sidebar."""
        if key == "capturar_orden":
            self._load_ordenes_combo()
            self.main_stack.setCurrentIndex(0)
        elif key in ("ordenes", "ordenes_capturadas"):
            self._refresh_ordenes_table()
            self.main_stack.setCurrentIndex(1)
        elif key in ("r2f_control", "dashboard"):
            self.main_stack.setCurrentIndex(2)

    def _on_modo_orden_changed(self, text: str):
        """Alterna los campos según la acción seleccionada (Crear nueva vs Anexar existente)."""
        if text == "ANEXAR A ORDEN EXISTENTE":
            self.lbl_orden_target.setText("Seleccionar Orden Existente *")
            self.txt_desc_orden.hide()
            self.cb_ordenes_existentes.show()
            self._load_ordenes_combo()
        else:
            self.lbl_orden_target.setText("Descripción de la Nueva Orden *")
            self.cb_ordenes_existentes.hide()
            self.txt_desc_orden.show()

    def _load_ordenes_combo(self):
        """Carga en el combo las órdenes existentes usando el servicio UI (Directo / API)."""
        try:
            self.cb_ordenes_existentes.blockSignals(True)
            self.cb_ordenes_existentes.clear()
            self._ordenes_map = {} # label -> orden_id

            ordenes_data = self.ui_service.list_ordenes()

            if not ordenes_data:
                self.cb_ordenes_existentes.addItem("-- No hay órdenes registradas --", None)
            else:
                self.cb_ordenes_existentes.addItem("-- Seleccione una orden existente --", None)
                for o in ordenes_data:
                    desc = o.get("descripcion") or "Sin descripción"
                    label = f"{o['folio_orden']} | {desc} ({o.get('total_lotes', 0)} lotes, {o.get('total_folios', 0)} folios)"
                    self.cb_ordenes_existentes.addItem(label, o['orden_id'])
                    self._ordenes_map[label] = o['orden_id']
        except Exception as e:
            logger.error(f"Error cargando combo de órdenes: {e}")
        finally:
            self.cb_ordenes_existentes.blockSignals(False)

    def _refresh_ordenes_table(self):
        """Refresca el listado de Órdenes Cancún usando el servicio UI (Directo / API)."""
        try:
            ordenes = self.ui_service.list_ordenes()
            data = []
            for o in ordenes:
                data.append([
                    str(o.get("orden_id", "")),
                    o.get("folio_orden", "--"),
                    o.get("descripcion") or "--",
                    str(o.get("total_lotes", 0)),
                    str(o.get("total_folios", 0)),
                    str(o.get("folios_procesados", 0)),
                    o.get("estado_codigo") or "--",
                    str(o.get("created_at") or "--")
                ])
            self.table_ordenes.populate_rows(data)
        except Exception as e:
            logger.error(f"Error cargando órdenes: {e}")

    def _on_orden_double_clicked(self, index):
        """Navega a la bandeja de recibos/facturas al hacer doble clic en una orden."""
        self.main_stack.setCurrentIndex(2)

    def _abrir_vista_cancun_ordenes(self):
        """Abre la consola de ejecución del Bot Cancún R2F."""
        from cancunbot.src.ui.views.r2f_cancun_view import R2FCancunWindow
        if not hasattr(self, '_cancun_window') or not self._cancun_window or not self._cancun_window.isVisible():
            self._cancun_window = R2FCancunWindow(self.db_connector, sesion_id=1, usuario_id=self.usuario_id, parent=self)
            self._cancun_window.logout_requested.connect(self.logout_requested.emit)
            self._cancun_window.showMaximized()
        else:
            self._cancun_window.raise_()
            self._cancun_window.activateWindow()

    # -------------------------------------------------------------------------
    # FUNCIONALIDADES MIGRADAS: IMPORTAR EXCEL, PREVISUALIZAR, CONFIRMAR Y LIMPIAR
    # -------------------------------------------------------------------------
    def _on_limpiar_captura(self):
        """Limpia los campos del formulario y la tabla de previsualización."""
        self._current_excel_path = None
        self._pending_folios_list = []
        self.lbl_excel_path.setText("Ningún archivo seleccionado")
        self.txt_desc_orden.clear()
        self.txt_solicitante.clear()
        self.txt_obs_lote.clear()
        self.cb_modo_orden.setCurrentIndex(0)
        self.preview_table.clearContents()
        self.preview_table.setRowCount(0)
        self.btn_confirmar_orden.setEnabled(False)
        self._load_ordenes_combo()

    @staticmethod
    def _clean_excel_value(val) -> str:
        """Limpia cadenas, elimina espacios sobrantes, caracteres no imprimibles y normaliza flotantes."""
        if val is None:
            return ""
        # Si vino como float/int de Excel (ej: 12345.0) y es un folio o número
        if isinstance(val, float) and val.is_integer():
            return str(int(val)).strip()
        s = str(val).strip()
        if s.upper() in ("NONE", "NULL", "NAN", "N/A", "-"):
            return ""
        # Quitar comillas simples y dobles envolventes
        s = s.strip("'\"")
        # Quitar caracteres no imprimibles
        s = "".join(ch for ch in s if ch.isprintable()).strip()
        return s

    @staticmethod
    def _clean_rfc(val) -> str:
        """Limpia el RFC eliminando guiones y espacios intermedios para garantizar coincidencia con el catálogo."""
        s = R2FControlView._clean_excel_value(val).upper()
        return s.replace("-", "").replace(" ", "").replace("_", "")

    def _on_importar_excel(self):
        """Abre cuadro de diálogo, lee y limpia el Excel, detecta duplicados en archivo y BD, y previsualiza."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Archivo Excel de Folios", "", "Archivos de Excel (*.xlsx *.xls)"
        )
        if not file_path:
            return

        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, data_only=True)
            ws = wb.active

            raw_rows = []
            row_idx = 2
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or not any(row):
                    row_idx += 1
                    continue
                
                # Limpieza de datos (Data Sanitization)
                f_elec = self._clean_excel_value(row[0])
                f_pase = self._clean_excel_value(row[1]) if len(row) > 1 else ""
                raw_rfc = self._clean_rfc(row[2]) if len(row) > 2 else ""
                raw_des = self._clean_excel_value(row[3]).upper() if len(row) > 3 else ""
                # Colapsar espacios múltiples en desarrollo
                if raw_des:
                    raw_des = " ".join(raw_des.split())

                if f_elec:
                    raw_rows.append({
                        "excel_row": row_idx,
                        "folio_electronico": f_elec,
                        "folio_pase_caja": "",
                        "tipo_folio": "ELECTRONICO",
                        "raw_rfc": raw_rfc,
                        "raw_des": raw_des
                    })
                elif f_pase:
                    raw_rows.append({
                        "excel_row": row_idx,
                        "folio_electronico": "",
                        "folio_pase_caja": f_pase,
                        "tipo_folio": "PASE_CAJA",
                        "raw_rfc": raw_rfc,
                        "raw_des": raw_des
                    })
                row_idx += 1

            if not raw_rows:
                QMessageBox.warning(self, "Archivo Vacío", "No se encontraron folios válidos tras la limpieza del archivo Excel.")
                return

            # -------------------------------------------------------------
            # VALIDACIÓN DE DUPLICADOS EN EL MISMO ARCHIVO EXCEL
            # -------------------------------------------------------------
            seen_elec = {}
            seen_pase = {}
            for item in raw_rows:
                elec = item["folio_electronico"]
                pase = item["folio_pase_caja"]
                item["duplicate_in_file"] = False
                item["first_seen_row"] = None

                if elec:
                    if elec in seen_elec:
                        item["duplicate_in_file"] = True
                        item["first_seen_row"] = seen_elec[elec]
                    else:
                        seen_elec[elec] = item["excel_row"]
                elif pase:
                    if pase in seen_pase:
                        item["duplicate_in_file"] = True
                        item["first_seen_row"] = seen_pase[pase]
                    else:
                        seen_pase[pase] = item["excel_row"]

            # -------------------------------------------------------------
            # VALIDACIÓN DE DUPLICADOS Y CATÁLOGOS VÍA UI SERVICE (DIRECTO / API)
            # -------------------------------------------------------------
            unique_elec = list(seen_elec.keys())
            unique_pase = list(seen_pase.keys())

            rfc_map, des_map = self.ui_service.get_catalogos()
            db_existing_map = self.ui_service.check_duplicates(unique_elec, unique_pase)

            # -------------------------------------------------------------
            # CONSTRUCCIÓN DE LA PREVISUALIZACIÓN Y CLASIFICACIÓN
            # -------------------------------------------------------------
            preview_rows = []
            self._pending_folios_list = []
            dup_file_count = 0
            dup_db_count = 0
            valid_count = 0

            for item in raw_rows:
                elec = item["folio_electronico"]
                pase = item["folio_pase_caja"]
                raw_rfc = item["raw_rfc"]
                raw_des = item["raw_des"]
                rfc_id = rfc_map.get(raw_rfc)
                des_id = des_map.get(raw_des)

                folio_key = elec if elec else pase
                db_lote_match = db_existing_map.get(folio_key)

                # Jerarquía de Estatus
                is_duplicate = False
                if item["duplicate_in_file"]:
                    status_str = f"🔴 DUPLICADO EN EXCEL (Fila {item['first_seen_row']})"
                    dup_file_count += 1
                    is_duplicate = True
                elif db_lote_match:
                    status_str = f"🟡 YA EXISTE EN BD ({db_lote_match})"
                    dup_db_count += 1
                    is_duplicate = True
                elif raw_rfc and not rfc_id:
                    status_str = "🟡 RFC NO CATALOGADO"
                    valid_count += 1
                elif raw_des and not des_id:
                    status_str = "🟡 DESARROLLO NO REGISTRADO"
                    valid_count += 1
                else:
                    status_str = "🟢 CORRECTO"
                    valid_count += 1

                record_data = {
                    "excel_row": item["excel_row"],
                    "folio_electronico": elec or None,
                    "folio_pase_caja": pase or None,
                    "tipo_folio": item["tipo_folio"],
                    "rfc_id": rfc_id,
                    "desarrollo_id": des_id,
                    "raw_rfc": raw_rfc,
                    "raw_des": raw_des,
                    "is_duplicate": is_duplicate,
                    "status_str": status_str
                }
                self._pending_folios_list.append(record_data)

                preview_rows.append([
                    f"Fila {item['excel_row']}",
                    elec or "-",
                    pase or "-",
                    item["tipo_folio"],
                    raw_rfc or "-",
                    raw_des or "-",
                    status_str
                ])

            self._current_excel_path = file_path
            
            # Etiqueta de resumen detallado
            resumen_info = f"{os.path.basename(file_path)} | Total: {len(raw_rows)} (Válidos: {valid_count}"
            if dup_file_count > 0:
                resumen_info += f", Repetidos en Excel: {dup_file_count}"
            if dup_db_count > 0:
                resumen_info += f", Ya en BD: {dup_db_count}"
            resumen_info += ")"
            self.lbl_excel_path.setText(resumen_info)

            # Autocompletar descripción si está vacía
            if not self.txt_desc_orden.text().strip():
                self.txt_desc_orden.setText(f"Orden Importación {os.path.basename(file_path)}")

            self.preview_table.populate_rows(preview_rows)

            # Solo habilitar si hay al menos un registro no duplicado
            self.btn_confirmar_orden.setEnabled(valid_count > 0)

            # Alerta diagnóstica si hubo duplicados
            if dup_file_count > 0 or dup_db_count > 0:
                msg_alerta = "Se han analizado y detectado registros duplicados:\n"
                if dup_file_count > 0:
                    msg_alerta += f"\n• {dup_file_count} folios repetidos dentro del mismo archivo Excel."
                if dup_db_count > 0:
                    msg_alerta += f"\n• {dup_db_count} folios que ya habían sido importados previamente en el sistema."
                msg_alerta += f"\n\nAl confirmar la orden, el sistema OMITIRÁ automáticamente los folios duplicados e importará únicamente los {valid_count} registros válidos."
                QMessageBox.warning(self, "Detección de Duplicados", msg_alerta)

        except Exception as e:
            logger.error(f"Error importando y analizando Excel: {e}")
            QMessageBox.critical(self, "Error de Importación", f"No se pudo procesar el archivo Excel:\n{e}")

    def _on_confirmar_captura_orden(self):
        """Confirma la inserción en BD (creando nueva orden o anexando a existente) omitiendo duplicados."""
        if not self._pending_folios_list:
            QMessageBox.warning(self, "Sin Registros", "No hay folios listos para procesar.")
            return

        # Filtrar únicamente los folios limpios y no duplicados
        folios_validos_a_insertar = [
            item for item in self._pending_folios_list if not item.get("is_duplicate", False)
        ]

        if not folios_validos_a_insertar:
            QMessageBox.critical(
                self, "Sin Folios Válidos",
                "Todos los folios detectados en el archivo están duplicados (en el archivo o ya existen en BD). "
                "No hay registros nuevos para procesar."
            )
            return

        modo_orden = self.cb_modo_orden.currentText()
        target_orden_id = None
        target_orden_nombre = None

        if modo_orden == "ANEXAR A ORDEN EXISTENTE":
            target_orden_id = self.cb_ordenes_existentes.currentData()
            if not target_orden_id:
                QMessageBox.warning(
                    self, "Orden No Seleccionada",
                    "Por favor selecciona una orden existente de la lista para anexar este lote."
                )
                self.cb_ordenes_existentes.setFocus()
                return
            target_orden_nombre = self.cb_ordenes_existentes.currentText().split(" | ")[0]
        else:
            desc_orden = self.txt_desc_orden.text().strip()
            if not desc_orden:
                QMessageBox.warning(self, "Descripción Requerida", "Por favor ingresa una descripción para la nueva orden.")
                self.txt_desc_orden.setFocus()
                return

        desc_lote = self.txt_obs_lote.text().strip()
        if not desc_lote:
            desc_lote = f"Importado desde {os.path.basename(self._current_excel_path)}" if self._current_excel_path else "Carga masiva"

        solicitante = self.txt_solicitante.text().strip()
        if solicitante and modo_orden != "ANEXAR A ORDEN EXISTENTE":
            desc_orden += f" | Solicitante: {solicitante}"

        total_leidos = len(self._pending_folios_list)
        total_omitidos = total_leidos - len(folios_validos_a_insertar)

        if modo_orden == "ANEXAR A ORDEN EXISTENTE":
            confirm_msg = (
                f"Resumen de la Importación a Anexar:\n\n"
                f"• Acción: Anexar Lote a la Orden Existente [{target_orden_nombre}]\n"
                f"• Descripción del Lote: {desc_lote}\n"
                f"• Total Folios Leídos: {total_leidos}\n"
                f"• Duplicados Omitidos: {total_omitidos}\n"
                f"• Folios Nuevos a Insertar: {len(folios_validos_a_insertar)}\n\n"
                f"¿Deseas confirmar la inserción del nuevo lote en esta orden?"
            )
        else:
            confirm_msg = (
                f"Resumen de la Nueva Orden a Registrar:\n\n"
                f"• Acción: Crear Nueva Orden Cancún\n"
                f"• Descripción: {desc_orden}\n"
                f"• Total Folios Leídos: {total_leidos}\n"
                f"• Duplicados Omitidos: {total_omitidos}\n"
                f"• Folios Nuevos a Insertar: {len(folios_validos_a_insertar)}\n\n"
                f"¿Deseas confirmar la creación de la Orden y el Lote correspondiente?"
            )

        confirm_dialog = GLMessageDialog(
            title="Confirmar Registro de Orden",
            message=confirm_msg,
            dialog_type=DialogType.QUESTION,
            confirm_text="Confirmar y Registrar",
            cancel_text="Cancelar",
            parent=self
        )
        if confirm_dialog.exec() != QDialog.Accepted:
            return

        try:
            modo_api = "ANEXAR" if modo_orden == "ANEXAR A ORDEN EXISTENTE" else "CREAR_NUEVA"
            res = self.ui_service.crear_o_anexar_orden(
                usuario_id=self.usuario_id,
                modo=modo_api,
                folios=folios_validos_a_insertar,
                descripcion_orden=desc_orden if modo_api == "CREAR_NUEVA" else None,
                descripcion_lote=desc_lote,
                target_orden_id=target_orden_id,
                archivo_excel=self._current_excel_path or "",
                solicitante=solicitante if modo_api == "CREAR_NUEVA" else None
            )

            folio_orden_nombre = res.get("folio_orden", "--")
            folio_lote_nombre = res.get("folio_lote", "--")
            guardados = res.get("guardados", len(folios_validos_a_insertar))

            if modo_orden == "ANEXAR A ORDEN EXISTENTE":
                exito_msg = (
                    f"Se anexó exitosamente el nuevo Lote {folio_lote_nombre} a la Orden {folio_orden_nombre}.\n"
                    f"Folios registrados: {guardados}\n"
                    f"Folios duplicados omitidos: {total_omitidos}"
                )
            else:
                exito_msg = (
                    f"Orden: {folio_orden_nombre}\n"
                    f"Lote: {folio_lote_nombre}\n"
                    f"Folios registrados: {guardados}\n"
                    f"Folios duplicados omitidos: {total_omitidos}\n\n"
                    f"La orden se encuentra lista en el listado de Órdenes Capturadas."
                )

            QMessageBox.information(self, "Operación Completada", exito_msg)

            # Limpiar formulario
            self._on_limpiar_captura()
            self._refresh_ordenes_table()

            # Redirigir a la pestaña de Órdenes Capturadas (Index 1)
            self.sidebar.select_item("ordenes_capturadas")
            self.main_stack.setCurrentIndex(1)

        except Exception as e:
            logger.error(f"Error guardando orden Cancún: {e}")
            QMessageBox.critical(self, "Error al Guardar", f"No se pudo completar el registro en base de datos:\n{e}")

    def _on_importar_pdf(self):
        """Abre cuadro de diálogo para seleccionar archivos PDF y lanza la previsualización modal."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar Boletas o Pases de Caja en PDF", "", "Archivos PDF (*.pdf)"
        )
        if not file_paths:
            return

        from cancunbot.src.ui.dialogs.pdf_analysis_dialog import PdfAnalysisDialog
        dialog = PdfAnalysisDialog(
            pdf_paths=file_paths,
            api_client=None,
            db_connector=self.db_connector,
            usuario_id=self.usuario_id,
            parent=self
        )
        if dialog.exec() == QDialog.Accepted:
            self._refresh_ordenes_table()
            self.sidebar.select_item("ordenes_capturadas")
            self.main_stack.setCurrentIndex(1)

    def _on_descargar_plantilla(self):
        """Descarga una plantilla de Excel en blanco."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Plantilla Excel", "Plantilla_Folios_Cancun.xlsx", "Archivos de Excel (*.xlsx)"
        )
        if not file_path:
            return

        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Folios a Procesar"

            ws.cell(row=1, column=1, value="FOLIO_ELECTRONICO")
            ws.cell(row=1, column=2, value="FOLIO_PASE_CAJA")
            ws.cell(row=1, column=3, value="RFC")
            ws.cell(row=1, column=4, value="DESARROLLO")

            ws.cell(row=2, column=1, value="F-2026-615-31044")
            ws.cell(row=2, column=2, value="")
            ws.cell(row=2, column=3, value="XAXX010101000")
            ws.cell(row=2, column=4, value="VALMIRA LIVING")

            ws.cell(row=3, column=1, value="")
            ws.cell(row=3, column=2, value="987654321")
            ws.cell(row=3, column=3, value="CIN010904D31")
            ws.cell(row=3, column=4, value="")

            wb.save(file_path)
            QMessageBox.information(self, "Plantilla Descargada", f"La plantilla se guardó en:\n{file_path}")
        except Exception as e:
            logger.error(f"Error generando plantilla Excel: {e}")
            QMessageBox.critical(self, "Error al guardar", f"No se pudo generar la plantilla: {e}")

    # -------------------------------------------------------------------------
    # OPERACIONES DE TABLA Y CONTROL
    # -------------------------------------------------------------------------
    def _filter_table_by_text(self, text: str):
        self._current_search_text = text
        self.current_page = 1
        self.search_timer.start(300)

    def _on_search_trigger(self):
        self.search_timer.stop()
        self._current_search_text = self.search_input.text().strip()
        self.current_page = 1
        self.refresh_data()

    def _show_estado_filter_menu(self):
        """Despliega menú emergente para filtrar por estado del recibo."""
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        estados = ["Todos", "CAPTURADO", "PENDIENTE_FACTURAR", "FACTURANDO", "FACTURADO", "ERROR_FACTURA"]
        
        for est in estados:
            action = QAction(est, menu)
            action.setCheckable(True)
            action.setChecked(self._current_estado_filter == est)
            
            def make_handler(target_est):
                return lambda: self._filter_table_by_state(target_est)
                
            action.triggered.connect(make_handler(est))
            menu.addAction(action)
            
        menu.exec(self.btn_filter.mapToGlobal(self.btn_filter.rect().bottomLeft()))

    def _show_more_options_menu(self):
        """Despliega menú emergente de acciones secundarias."""
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        
        action_ver_pdf = QAction("📄 Ver PDF Recibo", menu)
        action_ver_pdf.triggered.connect(self._on_ver_pdf)
        menu.addAction(action_ver_pdf)
        
        action_liberar = QAction("⚡ Liberar para Factura", menu)
        action_liberar.triggered.connect(self._on_liberar_factura)
        menu.addAction(action_liberar)
        
        menu.addSeparator()
        
        action_descargar_plantilla = QAction("📥 Descargar Plantilla Excel", menu)
        action_descargar_plantilla.triggered.connect(self._on_descargar_plantilla)
        menu.addAction(action_descargar_plantilla)
        
        menu.exec(self.btn_more.mapToGlobal(self.btn_more.rect().bottomLeft()))

    def _update_filter_title(self):
        """Actualiza el título con el estado seleccionado en el filtro."""
        if hasattr(self, "lbl_table_title"):
            estado_label = self._current_estado_filter
            if estado_label == "Todos":
                self.lbl_table_title.setText("Bandeja de Control de Recibos & Facturas")
            else:
                self.lbl_table_title.setText(
                    f"Bandeja de Control &nbsp;|&nbsp; <span style='font-size: 13px; font-weight: normal;'>Filtro: <b>{estado_label}</b></span>"
                )

    def _set_page(self, page_num: int):
        self.current_page = page_num
        self.refresh_data()

    def _filter_table_by_state(self, state_text: str):
        self._current_estado_filter = state_text
        self._update_filter_title()
        self.current_page = 1
        self.refresh_data()

    def _on_search_timer_timeout(self):
        self.refresh_data()

    def _on_page_size_changed(self, text: str):
        try:
            size_val = int(text.split()[0])
            self.page_size = size_val
            self.current_page = 1
            self.refresh_data()
        except Exception as e:
            logger.error(f"Error cambiando tamaño de página: {e}")

    def refresh_data(self):
        """Carga de recibos/facturas con paginación."""
        if hasattr(self, "pagination_widget"):
            self.pagination_widget.setEnabled(False)
        if hasattr(self, "cb_page_size"):
            self.cb_page_size.setEnabled(False)
            
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.cancel()
            try:
                self.active_worker.result_ready.disconnect()
                self.active_worker.error_occurred.disconnect()
            except RuntimeError:
                pass
            self.active_worker.wait()
            
        offset = (self.current_page - 1) * self.page_size
        self.active_worker = R2FLoadWorker(
            self.ui_service,
            limit=self.page_size,
            offset=offset,
            search_text=self._current_search_text,
            estado_filter=self._current_estado_filter
        )
        self.active_worker.result_ready.connect(self._on_data_loaded)
        self.active_worker.error_occurred.connect(self._on_load_error)
        self.active_worker.start()

    def _on_data_loaded(self, data, total_count):
        self.all_data = data
        self.total_items = total_count
        
        if hasattr(self, "pagination_widget"):
            self.pagination_widget.setEnabled(True)
        if hasattr(self, "cb_page_size"):
            self.cb_page_size.setEnabled(True)
        
        table_rows = []
        for item in data:
            table_rows.append([
                str(item["recibo_id"]),
                item["folio_electronico"],
                item["rfc"],
                item["contribuyente"],
                item["concepto"],
                item["sm"],
                item["mz"],
                item["l"],
                f"${item['total']:,.2f}",
                item["fecha"],
                item["estado"]
            ])
            
        self.table.populate_rows(table_rows)
        
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + len(self.all_data), total_count)
        
        if total_count == 0:
            self.lbl_pagination_info.setText("Mostrando 0 a 0 de 0 registros")
        else:
            self.lbl_pagination_info.setText(f"Mostrando {start_idx + 1} a {end_idx} de {total_count} registros")
            
        if hasattr(self, "card_total"):
            self.card_total.set_value(str(total_count))
            
        # Reconstruir botones numéricos y de navegación
        if hasattr(self, "pag_btn_layout"):
            while self.pag_btn_layout.count():
                item = self.pag_btn_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                    
            total_pages = max(1, (total_count + self.page_size - 1) // self.page_size)
            
            def add_nav_btn(text, target_page, enabled):
                btn = QPushButton(text)
                btn.setObjectName("paginationNavBtn")
                btn.setEnabled(enabled)
                btn.clicked.connect(lambda: self._set_page(target_page))
                self.pag_btn_layout.addWidget(btn)
                
            def add_page_btn(page_num, active):
                btn = QPushButton(str(page_num))
                btn.setObjectName("paginationActivePageBtn" if active else "paginationPageBtn")
                btn.clicked.connect(lambda: self._set_page(page_num))
                self.pag_btn_layout.addWidget(btn)
                
            start_page = max(1, self.current_page - 2)
            end_page = min(total_pages, start_page + 4)
            if end_page - start_page < 4:
                start_page = max(1, end_page - 4)
                
            add_nav_btn("<<", 1, self.current_page > 1)
            add_nav_btn("<", self.current_page - 1, self.current_page > 1)
            
            for p in range(start_page, end_page + 1):
                add_page_btn(p, p == self.current_page)
                
            add_nav_btn(">", self.current_page + 1, self.current_page < total_pages)
            add_nav_btn(">>", total_pages, self.current_page < total_pages)

    def _on_load_error(self, err_msg):
        logger.error(f"Error en R2FLoadWorker: {err_msg}")
        QMessageBox.critical(self, "Error de Carga", f"No se pudieron cargar los registros de R2F:\n{err_msg}")

    def _get_selected_ids(self) -> List[int]:
        selected_rows = self.table.selectionModel().selectedRows()
        ids = []
        for index in selected_rows:
            item_id = self.table.item(index.row(), 0)
            if item_id:
                try:
                    ids.append(int(item_id.text()))
                except ValueError:
                    pass
        return ids

    def _on_liberar_factura(self):
        selected_ids = self._get_selected_ids()
        if not selected_ids:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona al menos un recibo para liberar.")
            return
            
        reply = QMessageBox.question(
            self, "Liberar para Factura",
            f"¿Estás seguro de que deseas liberar {len(selected_ids)} recibos seleccionados?\n"
            "Esto colocará su estado como PENDIENTE_FACTURAR para que sean tomados por el Bot de Facturas.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
            
        try:
            liberados = self.ui_service.liberar_recibos(selected_ids, "PENDIENTE_FACTURAR")
            QMessageBox.information(self, "Proceso Completado", f"Se han liberado {liberados} recibos con éxito.")
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron liberar los registros:\n{e}")

    def _on_ver_pdf(self):
        selected_ids = self._get_selected_ids()
        if not selected_ids or len(selected_ids) > 1:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona un único registro para visualizar su archivo PDF.")
            return
            
        recibo_id = selected_ids[0]
        pdf_path_str = None
        for item in self.all_data:
            if item["recibo_id"] == recibo_id:
                pdf_path_str = item["pdf_ruta"]
                break
                
        if not pdf_path_str or not os.path.exists(pdf_path_str):
            QMessageBox.critical(self, "Archivo No Encontrado", f"El archivo PDF del recibo no existe o la ruta es inválida:\n{pdf_path_str}")
            return
            
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path_str))
        except Exception as e:
            QMessageBox.critical(self, "Error al Abrir", f"No se pudo abrir el archivo PDF:\n{e}")

    def _get_username_string(self) -> str:
        """Obtiene el nombre del usuario firmado para el avatar del sidebar."""
        try:
            parent_window = self.window()
            username = getattr(parent_window, 'current_username', None)
            if username:
                return username
                
            with self.db_connector.get_session() as session:
                from sar.src.storage.models import Sesion
                sesion_id = getattr(parent_window, 'current_sesion_id', None)
                if sesion_id:
                    db_sesion = session.get(Sesion, sesion_id)
                    if db_sesion and db_sesion.usuario:
                        return db_sesion.usuario.username
        except Exception:
            pass
        return "Administrador"
