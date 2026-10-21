"""
SATC — Vista Principal de Gestión y Captura de Trámites por Vivienda (Vía B)
Módulo: satc.src.ui.views.tramites_control_view

Implementa la arquitectura formal homologada a 'Capturar Nueva Orden' (OrdersView):
  - QStackedWidget con navegación entre dos modos:
      * Modo 0: 'Capturar Nueva Orden de Trámites' (Configuración + Grilla de Renglones)
      * Modo 1: 'Historial de Órdenes y Renglones' (Filtro + Tablas jerárquicas con StatusBadge)
  - Eliminación de tarjetas KPI (StatCard) para una experiencia limpia y enfocada.
  - Diseño Atomic Design con CustomCard, CustomComboBox, CustomInput, CustomButton,
    StyledDataTable, GLInfoBanner y StatusBadge.
  - Cero CSS/QSS hardcodeado; 100% gobernado por ThemeManager, Tokens y selectores de objeto.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QStackedWidget, QScrollArea, QHeaderView, QTableWidgetItem
)

from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.tokens.typography import Typography
from sar.src.ui.design_system.tokens.spacing import Spacing
from sar.src.ui.design_system.theme_manager import ThemeManager
from sar.src.ui.design_system.components import (
    CustomButton, CustomCard, StyledDataTable, FilterBar, CustomLabel,
    CustomComboBox, CustomInput, StatusBadge, GLInfoBanner, GLMessageDialog, DialogType
)
from sar.src.ui.design_system.utils.icons import Icons

from satc.src.storage.satc_repos import (
    OrdenTramiteRepository, SolicitudTramiteRepository, TramiteViviendaRepository,
    RegimenCondominioRepository
)
from satc.src.storage.satc_models import TipoTramite, RegimenCondominio
from satc.src.services.housing_life_cycle_service import HousingLifeCycleService

logger = logging.getLogger(__name__)


class TramiteRowWidget(QFrame):
    """Fila interactiva de captura para un renglón de solicitud de trámite (Atomic Design)."""
    deleted = Signal(object)
    changed = Signal()

    def __init__(self, tipos_tramite: List[Dict[str, Any]], universo_upes: int = 0, parent=None):
        super().__init__(parent)
        self.tipos_tramite = tipos_tramite
        self.universo_upes = universo_upes
        self.setObjectName("interactiveGridRow")
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 4, 8, 4)
        self.layout.setSpacing(12)
        self.layout.setAlignment(Qt.AlignVCenter)

        # 1. Selector de Tipo de Trámite
        self.combo_tipo = CustomComboBox(control_size="sm")
        self.combo_tipo.setPlaceholderText("Seleccionar Tipo de Trámite...")
        self.combo_tipo.setMinimumWidth(240)
        for t in self.tipos_tramite:
            vig = f" ({t['dias_vigencia']} d vig.)" if t.get('dias_vigencia', 0) > 0 else " (Indefinida)"
            self.combo_tipo.addItem(f"{t['nombre']}{vig}", t['tipo_tramite_id'])
        self.combo_tipo.currentIndexChanged.connect(self._on_field_changed)

        # 2. Expediente Municipal / Radicación
        self.txt_expediente = CustomInput("Expediente / Folio Ventanilla (Opcional)", control_size="sm")
        self.txt_expediente.setMinimumWidth(200)
        self.txt_expediente.textChanged.connect(self._on_field_changed)

        # 3. Contador de Viviendas Amparadas (Read-only basado en régimen activo)
        self.lbl_viviendas = CustomLabel(str(self.universo_upes), variant="body")
        self.lbl_viviendas.setObjectName("totalGeneralValue")
        self.lbl_viviendas.setAlignment(Qt.AlignCenter)
        self.lbl_viviendas.setMinimumWidth(100)

        # 4. Botón Eliminar Renglón
        self.btn_delete = CustomButton(is_secondary=True, control_size="sm", parent=self)
        self.btn_delete.setIcon(Icons.cancelar(Colors.ERROR))
        self.btn_delete.setToolTip("Eliminar este renglón de trámite")
        self.btn_delete.setFixedSize(30, 30)
        self.btn_delete.clicked.connect(lambda: self.deleted.emit(self))

        self.layout.addWidget(self.combo_tipo, stretch=3)
        self.layout.addWidget(self.txt_expediente, stretch=3)
        self.layout.addWidget(self.lbl_viviendas, stretch=1)
        self.layout.addWidget(self.btn_delete)

    def _on_field_changed(self):
        self.changed.emit()

    def set_universo_upes(self, upes: int):
        self.universo_upes = upes
        self.lbl_viviendas.setText(str(upes))

    def get_data(self) -> Dict[str, Any]:
        return {
            "tipo_tramite_id": self.combo_tipo.currentData(),
            "tipo_tramite_nombre": self.combo_tipo.currentText(),
            "expediente_municipal": self.txt_expediente.text().strip() or None,
            "viviendas_amparadas": self.universo_upes
        }


class TramitesControlView(QWidget):
    """
    Vista de Captura y Gestión de Trámites por Vivienda.
    Estructura modular homologada a OrdersView (SAR):
      - Tab / Modo 0: Capturar Nueva Orden de Trámites (Configuración + Renglones + Universo de UPEs)
      - Tab / Modo 1: Historial de Órdenes y Solicitudes (Filtros + DataTables con StatusBadge)
    """

    def __init__(self, db_connector, usuario_id: int = 1, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.usuario_id = usuario_id
        
        self._tipos_tramite_cache: List[Dict[str, Any]] = []
        self._rows: List[TramiteRowWidget] = []
        self._universo_actual_upes: int = 0
        self._orden_seleccionada_id: Optional[int] = None
        self._all_ordenes_raw: List[Any] = []

        self._init_ui()
        QTimer.singleShot(10, self._cargar_catalogos)
        QTimer.singleShot(30, self.refresh_historial)

    def _check_permission(self, modulo_codigo: str, accion_codigo: str) -> bool:
        """Helper para verificar permisos RBAC (soportando sesión directa y API REST)."""
        parent_window = self.window()
        usuario_id = getattr(parent_window, 'current_usuario_id', self.usuario_id)
        if not usuario_id:
            return True

        try:
            perms = getattr(parent_window, '_permissions_cache', None)
            if perms is None or getattr(parent_window, '_permissions_cache_user_id', None) != usuario_id:
                from sar.src.storage.api_client import APIClient
                api_client = getattr(parent_window, 'api_client', APIClient())
                if getattr(api_client, 'connect_via_api', False):
                    perms = api_client.request("GET", f"/api/auth/permissions/{usuario_id}")
                else:
                    with self.db_connector.get_session() as session:
                        from sar.src.services.security_service import SecurityService
                        sec_service = SecurityService(session)
                        perms = sec_service.get_user_permissions(usuario_id)
                setattr(parent_window, '_permissions_cache', perms)
                setattr(parent_window, '_permissions_cache_user_id', usuario_id)
            return perms.get(modulo_codigo, {}).get(accion_codigo, False)
        except Exception as e:
            logger.warning(f"Error verificando permiso RBAC {modulo_codigo}:{accion_codigo}: {e}")
            return True

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll principal idéntico a OrdersView (sin bordes)
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.NoFrame)

        scroll_content = QWidget()
        scroll_content.setObjectName("ordersScrollContent")
        self.layout_content = QVBoxLayout(scroll_content)
        self.layout_content.setContentsMargins(24, 24, 24, 24)
        self.layout_content.setSpacing(24)

        # ── QStackedWidget para Modos (Gobernados desde el Menú Lateral) ──────
        self.stack = QStackedWidget(self)
        self.page_captura = QWidget()
        self.page_historial = QWidget()
        self.stack.addWidget(self.page_captura)    # Index 0: Capturar Nueva Orden
        self.stack.addWidget(self.page_historial)  # Index 1: Historial de Órdenes

        self._setup_captura_tab()
        self._setup_historial_tab()

        self.layout_content.addWidget(self.stack)
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

    def _cambiar_modo(self, index: int):
        """Conmuta entre Captura (0) e Historial (1) desde el menú lateral."""
        self.stack.setCurrentIndex(index)
        if index == 0:
            self._sync_sidebar_selection("tramites_vivienda")
        else:
            self.refresh_historial()
            self._sync_sidebar_selection("historial_tramites")

    def _sync_sidebar_selection(self, item_key: str):
        """Mantiene sincronizado el estado visual del sidebar padre si existe."""
        parent_view = self.parent()
        while parent_view and not hasattr(parent_view, "sidebar"):
            parent_view = parent_view.parent()
        if parent_view and hasattr(parent_view, "sidebar") and parent_view.sidebar:
            try:
                parent_view.sidebar.blockSignals(True)
                parent_view.sidebar.select_item(item_key)
                parent_view.sidebar.blockSignals(False)
            except Exception:
                pass

    # =========================================================================
    # MODO 0: CAPTURAR NUEVA ORDEN (REPLICANDO DISEÑO DE ORDERSVIEW)
    # =========================================================================
    def _setup_captura_tab(self):
        layout = QVBoxLayout(self.page_captura)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)

        # Card Principal de Configuración de la Orden (Idéntica a OrdersView.card)
        self.card_captura = CustomCard(parent=self.page_captura)
        card_layout = self.card_captura.layout
        card_layout.setSpacing(16)

        # Header con Título + Subtítulo agrupados (VBox) y Total General a la derecha (OrdersView)
        card_header = QHBoxLayout()

        card_title_vbox = QVBoxLayout()
        card_title_vbox.setSpacing(2)
        self.lbl_card_title = CustomLabel("Configuración de la Orden de Trámites", variant="subheader")
        self.lbl_card_title.setObjectName("cardHeaderTitle")
        self.lbl_card_subtitle = CustomLabel("Selecciona el desarrollo matriz, régimen y tipos de trámites a radicar", variant="muted")
        self.lbl_card_subtitle.setObjectName("cardHeaderSubtitle")
        card_title_vbox.addWidget(self.lbl_card_title)
        card_title_vbox.addWidget(self.lbl_card_subtitle)
        card_header.addLayout(card_title_vbox)
        card_header.addStretch()

        # Marco de Universo de Viviendas Amparadas (badge de total, idéntico a totalGeneralFrame)
        self.universo_frame = QFrame()
        self.universo_frame.setObjectName("totalGeneralFrame")
        self.universo_frame.setFixedHeight(32)
        universo_layout = QHBoxLayout(self.universo_frame)
        universo_layout.setContentsMargins(0, 0, 0, 0)
        universo_layout.setSpacing(8)

        lbl_tot_text = CustomLabel("UPEs Elegibles:", variant="body")
        lbl_tot_text.setObjectName("totalGeneralTitle")
        self.lbl_tot_val = CustomLabel("0", variant="header")
        self.lbl_tot_val.setObjectName("totalGeneralValue")
        universo_layout.addWidget(lbl_tot_text, alignment=Qt.AlignVCenter)
        universo_layout.addWidget(self.lbl_tot_val, alignment=Qt.AlignVCenter)
        card_header.addWidget(self.universo_frame, alignment=Qt.AlignVCenter)

        card_layout.addLayout(card_header)

        # Fila de 3 Columnas: Desarrollo (stretch 1) | Régimen (stretch 1) | Descripción (stretch 2)
        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(16)

        # Columna 1: Desarrollo
        col_des = QVBoxLayout()
        col_des.setSpacing(4)
        lbl_des = CustomLabel("Desarrollo Matriz *", variant="body")
        lbl_des.setObjectName("formFieldLabel")
        self.combo_desarrollo = CustomComboBox(control_size="sm")
        self.combo_desarrollo.currentIndexChanged.connect(self._on_desarrollo_changed)
        col_des.addWidget(lbl_des)
        col_des.addWidget(self.combo_desarrollo)

        # Columna 2: Régimen mz
        col_reg = QVBoxLayout()
        col_reg.setSpacing(4)
        lbl_reg = CustomLabel("Régimen mz (Macro-Lote) *", variant="body")
        lbl_reg.setObjectName("formFieldLabel")
        self.combo_regimen = CustomComboBox(control_size="sm")
        self.combo_regimen.currentIndexChanged.connect(self._on_regimen_changed)
        col_reg.addWidget(lbl_reg)
        col_reg.addWidget(self.combo_regimen)

        # Columna 3: Descripción de la Orden
        col_desc = QVBoxLayout()
        col_desc.setSpacing(4)
        lbl_desc = CustomLabel("Descripción / Observaciones de la Orden", variant="body")
        lbl_desc.setObjectName("formFieldLabel")
        self.txt_desc_orden = CustomInput("Ej. Radicación de Prediales y Cédulas 2026...", control_size="sm")
        col_desc.addWidget(lbl_desc)
        col_desc.addWidget(self.txt_desc_orden)

        inputs_layout.addLayout(col_des, stretch=1)
        inputs_layout.addLayout(col_reg, stretch=1)
        inputs_layout.addLayout(col_desc, stretch=2)
        card_layout.addLayout(inputs_layout)

        # Línea divisoria formal limpia (igual que OrdersView.divider)
        divider = QFrame()
        divider.setObjectName("dividerLine")
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        card_layout.addWidget(divider)

        # ── Sección de Renglones de Trámite (Partidas - Homologada a InteractiveGrid) ──
        renglones_header = QHBoxLayout()
        lbl_partidas_title = CustomLabel("Renglones de Solicitud de Trámites", variant="subheader")
        self.lbl_badge_renglones = QLabel("0", self)
        self.lbl_badge_renglones.setObjectName("gridBadge")

        renglones_header.addWidget(lbl_partidas_title)
        renglones_header.addWidget(self.lbl_badge_renglones)
        renglones_header.addStretch()

        self.btn_agregar_renglon = CustomButton.action_agregar(parent=self)
        self.btn_agregar_renglon.setToolTip("Agregar nuevo renglón de trámite")
        self.btn_agregar_renglon.clicked.connect(self._agregar_renglon)
        self.btn_agregar_renglon.setEnabled(False)

        self.btn_limpiar = CustomButton("Limpiar", is_secondary=True, control_size="sm")
        self.btn_limpiar.clicked.connect(self._reset_formulario)

        self.btn_guardar_orden = CustomButton.action_guardar(parent=self)
        self.btn_guardar_orden.setToolTip("Generar orden y renglones de trámite")
        self.btn_guardar_orden.clicked.connect(self._on_guardar_orden)
        self.btn_guardar_orden.setEnabled(False)

        renglones_header.addWidget(self.btn_agregar_renglon)
        renglones_header.addWidget(self.btn_limpiar)
        renglones_header.addWidget(self.btn_guardar_orden)
        card_layout.addLayout(renglones_header)

        # Cabecera de Columnas para los Renglones (alineadas con InteractiveGrid)
        header_cols = QHBoxLayout()
        header_cols.setContentsMargins(8, 2, 8, 2)
        header_cols.setSpacing(12)

        lbl_h_tipo = CustomLabel("Tipo de Trámite a Radicar", variant="muted")
        lbl_h_tipo.setObjectName("formFieldLabel")
        lbl_h_exp = CustomLabel("Expediente Municipal / Folio de Ventanilla", variant="muted")
        lbl_h_exp.setObjectName("formFieldLabel")
        lbl_h_upes = CustomLabel("UPEs Amparadas", variant="muted")
        lbl_h_upes.setObjectName("formFieldLabel")
        lbl_h_upes.setMinimumWidth(100)
        lbl_h_upes.setAlignment(Qt.AlignCenter)
        #lbl_h_act = CustomLabel("Acción", variant="muted")
        #lbl_h_act.setObjectName("formFieldLabel")
        #bl_h_act.setFixedWidth(30)

        header_cols.addWidget(lbl_h_tipo, stretch=3)
        header_cols.addWidget(lbl_h_exp, stretch=3)
        header_cols.addWidget(lbl_h_upes, stretch=1)
        #header_cols.addWidget(lbl_h_act)
        card_layout.addLayout(header_cols)

        # Scroll Area / Contenedor transparente de Renglones (igual que InteractiveGrid)
        self.scroll_renglones = QScrollArea(self)
        self.scroll_renglones.setWidgetResizable(True)
        self.scroll_renglones.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_renglones.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_renglones.setFrameShape(QFrame.NoFrame)
        self.scroll_renglones.setMinimumHeight(120)
        self.scroll_renglones.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.renglones_container = QWidget()
        self.renglones_container.setObjectName("rowsContainer")
        self.renglones_container.setStyleSheet("QWidget#rowsContainer { background-color: transparent; border: none; }")
        self.renglones_layout = QVBoxLayout(self.renglones_container)
        self.renglones_layout.setContentsMargins(0, 0, 0, 0)
        self.renglones_layout.setSpacing(5)
        self.renglones_layout.setAlignment(Qt.AlignTop)

        self.scroll_renglones.setWidget(self.renglones_container)
        card_layout.addWidget(self.scroll_renglones)

        # Banner Atómico de Resumen Fiduciario (Ubicado como footer contextual)
        self.banner_auditoria = GLInfoBanner(
            text="Selecciona un desarrollo y régimen de condominio para evaluar el universo de viviendas activas.",
            variant="info",
            icon_name="informacion",
            parent=self.card_captura
        )
        card_layout.addWidget(self.banner_auditoria)

        layout.addWidget(self.card_captura)

    # =========================================================================
    # MODO 1: HISTORIAL DE ÓRDENES Y RENGLONES (ORDERSVIEW)
    # =========================================================================
    def _setup_historial_tab(self):
        layout = QVBoxLayout(self.page_historial)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Barra de Filtros (FilterBar)
        self.filter_bar = FilterBar(
            search_placeholder="Buscar orden por folio, desarrollo, régimen...",
            state_options=["Todas", "NO_INICIADO", "EN_PROCESO", "PARCIAL", "CONCLUIDO", "COMPLETADA", "CANCELADO"],
            on_search=self._on_historial_search,
            on_state_change=self._on_historial_state_change,
            on_action=self.refresh_historial,
            action_icon_name="actualizar",
            action_tooltip="Actualizar Historial",
            parent=self.page_historial
        )
        layout.addWidget(self.filter_bar)

        # Card de Órdenes Generadas
        self.historial_card = CustomCard(title="Macro-Órdenes de Trámites Capturadas", parent=self.page_historial)
        headers_ordenes = [
            "Folio Orden", "Desarrollo", "Régimen / Lote", "Renglones", "Viviendas", "Estado", "Fecha Creación"
        ]
        self.tabla_ordenes = StyledDataTable(headers_ordenes, parent=self.page_historial)
        self.tabla_ordenes.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_ordenes.setMinimumHeight(240)
        self.tabla_ordenes.itemSelectionChanged.connect(self._on_orden_seleccionada)
        self.historial_card.add_widget(self.tabla_ordenes)
        layout.addWidget(self.historial_card)

        # Card de Detalle de Renglones de Solicitud de la Orden Seleccionada
        self.solicitudes_card = CustomCard(title="Renglones de Solicitud por Orden Seleccionada", parent=self.page_historial)
        headers_solicitudes = [
            "Folio Solicitud", "Tipo de Trámite", "Expediente Municipal", "Viviendas", "Recibos (Bot A)", "Facturas (Bot C)", "Estado"
        ]
        self.tabla_solicitudes = StyledDataTable(headers_solicitudes, parent=self.page_historial)
        self.tabla_solicitudes.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_solicitudes.setMinimumHeight(200)
        self.solicitudes_card.add_widget(self.tabla_solicitudes)
        layout.addWidget(self.solicitudes_card)

    # =========================================================================
    # LÓGICA DE NEGOCIO Y CARGA DE CATÁLOGOS
    # =========================================================================
    def _cargar_catalogos(self):
        try:
            with self.db_connector.get_session() as session:
                from sar.src.storage.models import Desarrollo
                desarrollos = session.query(Desarrollo).filter(Desarrollo.activo.is_(True)).order_by(Desarrollo.nombre.asc()).all()
                self.combo_desarrollo.clear()
                self.combo_desarrollo.addItem("-- Seleccione un Desarrollo Matriz --", userData=None)
                for d in desarrollos:
                    self.combo_desarrollo.addItem(d.nombre, userData=d.desarrollo_id)

                tipos = session.query(TipoTramite).filter(TipoTramite.activo.is_(True)).order_by(TipoTramite.nombre.asc()).all()
                self._tipos_tramite_cache = [
                    {
                        "tipo_tramite_id": t.tipo_tramite_id,
                        "codigo": t.codigo,
                        "nombre": t.nombre,
                        "dias_vigencia": t.dias_vigencia
                    }
                    for t in tipos
                ]
        except Exception as e:
            logger.error(f"Error al cargar catálogos de trámites: {e}", exc_info=True)

    def _on_desarrollo_changed(self, index: int):
        desarrollo_id = self.combo_desarrollo.currentData()
        self.combo_regimen.clear()
        self._limpiar_renglones()
        self._universo_actual_upes = 0
        self.lbl_tot_val.setText("0")
        self.btn_guardar_orden.setEnabled(False)
        self.btn_agregar_renglon.setEnabled(False)
        self.banner_auditoria.set_text("Selecciona un régimen para evaluar el universo de viviendas activas.")

        if not desarrollo_id:
            return

        with self.db_connector.get_session() as session:
            repo = RegimenCondominioRepository(session)
            regimenes = repo.get_by_desarrollo(desarrollo_id)
            self.combo_regimen.addItem("-- Seleccione un Régimen / Lote --", userData=None)
            for r in regimenes:
                self.combo_regimen.addItem(f"{r.nombre_regimen} ({r.total_upes} UPEs)", userData=r.regimen_id)

    def _on_regimen_changed(self, index: int):
        regimen_id = self.combo_regimen.currentData()
        self._limpiar_renglones()
        if not regimen_id:
            self._universo_actual_upes = 0
            self.lbl_tot_val.setText("0")
            self.btn_guardar_orden.setEnabled(False)
            self.btn_agregar_renglon.setEnabled(False)
            self.banner_auditoria.set_text("Selecciona un régimen para evaluar el universo de viviendas activas.")
            return

        with self.db_connector.get_session() as session:
            service = HousingLifeCycleService(session)
            auditoria = service.detectar_omisiones_regimen(regimen_id)
            activas = service.obtener_viviendas_activas_no_vendidas(regimen_id)

            tot = auditoria["total_upes_declaradas"]
            reg = auditoria["upes_registradas"]
            disp = len(activas)
            vendidas = reg - disp

            self._universo_actual_upes = disp
            self.lbl_tot_val.setText(str(disp))

            msg = (
                f"<b>Régimen:</b> {auditoria['regimen']} | "
                f"<b>Declaradas:</b> {tot} UPEs | "
                f"<b>Registradas:</b> {reg} UPEs | "
                f"<b>Vendidas / Escrituradas (Excluidas):</b> {vendidas} UPEs | "
                f"<b>Universo Activo Elegible:</b> {disp} UPEs"
            )
            self.banner_auditoria.set_text(msg)
            self.btn_agregar_renglon.setEnabled(True)

            # Agregar automáticamente el primer renglón si hay UPEs disponibles
            if disp > 0:
                self._agregar_renglon()

    def _agregar_renglon(self):
        if not self._tipos_tramite_cache:
            return
        row_widget = TramiteRowWidget(
            tipos_tramite=self._tipos_tramite_cache,
            universo_upes=self._universo_actual_upes,
            parent=self.renglones_container
        )
        row_widget.deleted.connect(self._eliminar_renglon)
        row_widget.changed.connect(self._actualizar_resumen_renglones)
        
        self.renglones_layout.addWidget(row_widget)
        self._rows.append(row_widget)
        self._actualizar_resumen_renglones()

    def _eliminar_renglon(self, row_widget: TramiteRowWidget):
        if row_widget in self._rows:
            self._rows.remove(row_widget)
            self.renglones_layout.removeWidget(row_widget)
            row_widget.deleteLater()
            self._actualizar_resumen_renglones()

    def _limpiar_renglones(self):
        for r in list(self._rows):
            self.renglones_layout.removeWidget(r)
            r.deleteLater()
        self._rows.clear()
        self._actualizar_resumen_renglones()

    def _actualizar_resumen_renglones(self):
        count = len(self._rows)
        self.lbl_badge_renglones.setText(str(count))
        
        # Validar si se habilita el botón de guardar
        valido = count > 0 and self._universo_actual_upes > 0 and self.combo_regimen.currentData() is not None
        self.btn_guardar_orden.setEnabled(valido)

    def _reset_formulario(self):
        self.combo_desarrollo.setCurrentIndex(0)
        self.combo_regimen.clear()
        self.txt_desc_orden.clear()
        self._limpiar_renglones()
        self._universo_actual_upes = 0
        self.lbl_tot_val.setText("0")
        self.btn_guardar_orden.setEnabled(False)
        self.btn_agregar_renglon.setEnabled(False)
        self.banner_auditoria.set_text("Selecciona un desarrollo y régimen de condominio para evaluar el universo de viviendas.")

    def _on_guardar_orden(self):
        desarrollo_id = self.combo_desarrollo.currentData()
        regimen_id = self.combo_regimen.currentData()
        desc = self.txt_desc_orden.text().strip() or None

        if not self._check_permission("TRAMITES_VIVIENDA", "CREAR"):
            GLMessageDialog.warning(
                parent=self,
                title="Acceso Denegado",
                message="No tiene permisos para crear órdenes de trámites por vivienda (TRAMITES_VIVIENDA:CREAR)."
            )
            return

        if not desarrollo_id or not regimen_id:
            GLMessageDialog.warning(
                parent=self,
                title="Campos Requeridos",
                message="Debe seleccionar un desarrollo y un régimen de condominio."
            )
            return

        if not self._rows:
            GLMessageDialog.warning(
                parent=self,
                title="Sin Renglones",
                message="Debe agregar al menos un renglón de trámite a radicar."
            )
            return

        partidas_data = [r.get_data() for r in self._rows]

        try:
            with self.db_connector.get_session() as session:
                service = HousingLifeCycleService(session)
                regimen_repo = RegimenCondominioRepository(session)
                regimen = regimen_repo.get_by_id(regimen_id)
                orden_repo = OrdenTramiteRepository(session)

                # 1. Crear la Macro-Orden de Trámites
                orden = orden_repo.create(
                    desarrollo_id=desarrollo_id,
                    regimen_id=regimen_id,
                    usuario_id=self.usuario_id,
                    descripcion=desc or f"Apertura de trámites para {regimen.nombre_regimen}"
                )

                # 2. Generar cada Solicitud / Renglón con sus viviendas asociadas
                total_solicitudes_creadas = 0
                for p in partidas_data:
                    tipo_id = p["tipo_tramite_id"]
                    expediente = p["expediente_municipal"]
                    service.crear_solicitud_tramite(
                        orden_tramite_id=orden.orden_tramite_id,
                        tipo_tramite_id=tipo_id,
                        usuario_id=self.usuario_id,
                        expediente_municipal=expediente
                    )
                    total_solicitudes_creadas += 1

                folio_creado = orden.folio_orden
                total_viv = orden.total_viviendas

            GLMessageDialog.success(
                parent=self,
                title="Orden de Trámites Creada",
                message=(
                    f"Se generó exitosamente la Macro-Orden con sus renglones:\n\n"
                    f"• Folio Orden: {folio_creado}\n"
                    f"• Renglones de Trámite: {total_solicitudes_creadas}\n"
                    f"• Viviendas Amparadas por Renglón: {self._universo_actual_upes} UPEs\n"
                    f"• Total Viviendas Vinculadas: {total_viv}\n\n"
                    f"Las solicitudes se encuentran listas para seguimiento y captura de pases de caja."
                )
            )

            self._reset_formulario()
            self._cambiar_modo(1)

        except Exception as e:
            logger.error(f"Error al guardar orden de trámite: {e}", exc_info=True)
            GLMessageDialog.error(
                parent=self,
                title="Error al Guardar Orden",
                message=f"Ocurrió un error al procesar la orden:\n{e}"
            )

    # =========================================================================
    # HISTORIAL Y BÚSQUEDA
    # =========================================================================
    def cargar_datos(self):
        """Punto de entrada estándar para actualizar catálogos e historial."""
        self._cargar_catalogos()
        self.refresh_historial()

    def refresh_historial(self):
        """Carga el listado de Macro-Órdenes en la tabla histórica con StatusBadge."""
        try:
            with self.db_connector.get_session() as session:
                repo = OrdenTramiteRepository(session)
                self._all_ordenes_raw = repo.list_all()

                data_rows = []
                for ord in self._all_ordenes_raw:
                    des_nombre = ord.desarrollo.nombre if ord.desarrollo else "N/A"
                    reg_nombre = ord.regimen.nombre_regimen if ord.regimen else "Lotes Tradicionales"
                    sol_count = str(len(ord.solicitudes))
                    viv_count = str(ord.total_viviendas)
                    estado_nom = ord.estado.nombre if ord.estado else "NO_INICIADO"
                    fecha_str = ord.created_at.strftime("%Y-%m-%d %H:%M") if ord.created_at else "-"

                    data_rows.append([
                        ord.folio_orden,
                        des_nombre,
                        reg_nombre,
                        sol_count,
                        viv_count,
                        estado_nom,
                        fecha_str
                    ])

                self.tabla_ordenes.populate_rows(data_rows)

                # Asociar orden_tramite_id a cada celda de folio
                for row_idx, ord in enumerate(self._all_ordenes_raw):
                    item = self.tabla_ordenes.item(row_idx, 0)
                    if item:
                        item.setData(Qt.UserRole, ord.orden_tramite_id)

            if self.tabla_ordenes.rowCount() > 0:
                self.tabla_ordenes.selectRow(0)
            else:
                self.tabla_solicitudes.setRowCount(0)

        except Exception as e:
            logger.error(f"Error al refrescar historial de órdenes: {e}", exc_info=True)

    def _on_orden_seleccionada(self):
        selected_rows = self.tabla_ordenes.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        item_folio = self.tabla_ordenes.item(row, 0)
        if not item_folio:
            return

        orden_id = item_folio.data(Qt.UserRole)
        self._orden_seleccionada_id = orden_id
        self._cargar_solicitudes_orden(orden_id)

    def _cargar_solicitudes_orden(self, orden_id: int):
        with self.db_connector.get_session() as session:
            repo = SolicitudTramiteRepository(session)
            solicitudes = repo.list_by_orden(orden_id)

            data_rows = []
            for sol in solicitudes:
                trm_nombre = sol.tipo_tramite.nombre if sol.tipo_tramite else "N/A"
                expediente = sol.expediente_municipal or "En Ventanilla"
                viv_count = str(sol.total_viviendas)
                rec_count = str(sol.viviendas_procesadas)
                fac_count = str(sol.viviendas_facturadas)
                estado_nom = sol.estado.nombre if sol.estado else "NO_INICIADO"

                data_rows.append([
                    sol.folio_solicitud,
                    trm_nombre,
                    expediente,
                    viv_count,
                    rec_count,
                    fac_count,
                    estado_nom
                ])

            self.tabla_solicitudes.populate_rows(data_rows)

    def _on_historial_search(self, text: str):
        query = text.strip().lower()
        for row in range(self.tabla_ordenes.rowCount()):
            match = False
            for col in range(self.tabla_ordenes.columnCount()):
                item = self.tabla_ordenes.item(row, col)
                if item and query in item.text().lower():
                    match = True
                    break
            self.tabla_ordenes.setRowHidden(row, not match)

    def _on_historial_state_change(self, estado: str):
        for row in range(self.tabla_ordenes.rowCount()):
            if estado == "Todas":
                self.tabla_ordenes.setRowHidden(row, False)
            else:
                item_estado = self.tabla_ordenes.item(row, 5)
                ocultar = (item_estado.text().upper() != estado.upper()) if item_estado else True
                self.tabla_ordenes.setRowHidden(row, ocultar)
