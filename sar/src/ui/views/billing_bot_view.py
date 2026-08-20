"""RPA Bot Dashboard View (Face C - Billing and Timbrado)."""

import datetime
import re
from sqlalchemy import text

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QFrame, QLabel, QPushButton, QCheckBox, QTextEdit, 
    QMessageBox, QProgressBar, QMenu, QFileDialog
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QCursor

from sar.src.ui.design_system.components import CustomCard, StyledDataTable, CustomButton, CustomLabel, CustomCheckBox, CustomSwitch, MetricBox
from sar.src.ui.design_system.components.atoms.gl_status_indicator import GLStatusIndicator
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.storage.repositories import ConfigRepository, OperacionRepository
from sar.src.storage.models import Sesion, Solicitud
from sar.src.core.billing_rpa_worker import BillingRpaWorker
from sar.src.core.access_manager import PathVerifyThread, SyncContingencyThread

class BillingBotView(QWidget):
    logout_requested = Signal()

    def __init__(self, db_connector, sesion_id, usuario_id, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.sesion_id = sesion_id
        self.usuario_id = usuario_id
        self.current_bot_context = None
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        
        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()
        
        # Load default RUTA_DERECHOS parameter
        self.default_output_dir = "storage"
        try:
            if self.api_client.connect_via_api:
                res = self.api_client.request("GET", "/api/docs/config/parametro/RUTA_DERECHOS")
                db_dir = res.get("valor")
            else:
                with self.db_connector.get_session() as session:
                    repo = ConfigRepository(session)
                    db_dir = repo.get_parametro("RUTA_DERECHOS")
            if db_dir:
                self.default_output_dir = db_dir
        except Exception as e:
            print("Error loading default output dir:", e)
        
        self._build_header()
        self._build_top_panels()
        self._build_table_panel()
        self._build_console_panel()
        
        # Initial path check and sync trigger
        self._verify_and_sync_paths()
        
        # Initial data load
        self._load_solicitudes()
        
    def _build_header(self):
        header_frame = QFrame()
        header_frame.setObjectName("botHeaderFaceC")
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(12)
        
        lbl = QLabel("🚀 BOT - FACTURACIÓN Y TIMBRADO DE DERECHOS")
        h_layout.addWidget(lbl)
        h_layout.addStretch()
        
        self.lbl_portal_status = QLabel("Portal: INACTIVO")
        self.lbl_portal_status.setStyleSheet("background-color: #334155; padding: 4px 12px; border-radius: 12px; font-size: 12px; color: white;")
        h_layout.addWidget(self.lbl_portal_status)
        
        # Gear / Config button
        self.btn_gear = QPushButton("⚙")
        self.btn_gear.setObjectName("iconHeaderBtn")
        self.btn_gear.clicked.connect(self._on_gear_clicked)
        h_layout.addWidget(self.btn_gear)
        
        # User Profile button
        self.btn_user = QPushButton("👤")
        self.btn_user.setObjectName("iconHeaderBtn")
        self.btn_user.clicked.connect(self._on_user_clicked)
        h_layout.addWidget(self.btn_user)
        
        self.main_layout.addWidget(header_frame)

    def _create_styled_menu(self):
        menu = QMenu(self)
        menu.setObjectName("botMenu")
        return menu

    def _on_gear_clicked(self):
        menu = self._create_styled_menu()
        
        # Get Portal URL from DB parameter or fallback
        portal_url = "https://shacienda.qroo.gob.mx/tributanet/"
        try:
            if self.api_client.connect_via_api:
                res = self.api_client.request("GET", "/api/docs/config/parametro/SATQ_URL")
                db_url = res.get("valor")
            else:
                with self.db_connector.get_session() as session:
                    repo = ConfigRepository(session)
                    db_url = repo.get_parametro("SATQ_URL")
            if db_url: portal_url = db_url
        except:
            pass
            
        action_url = menu.addAction(f"🔗 Portal: {portal_url}")
        action_url.setEnabled(False)
        
        menu.exec_(QCursor.pos())

    def _on_user_clicked(self):
        menu = self._create_styled_menu()
        
        # Get Current Username
        username = "Operador"
        try:
            if self.usuario_id:
                if self.api_client.connect_via_api:
                    users = self.api_client.request("GET", "/api/auth/users")
                    for u in users:
                        if u["usuario_id"] == self.usuario_id:
                            username = u["nombre"]
                            break
                else:
                    with self.db_connector.get_session() as session:
                        from sar.src.storage.models import Usuario
                        db_user = session.get(Usuario, self.usuario_id)
                        if db_user:
                            username = db_user.nombre
        except:
            pass
            
        action_user = menu.addAction(f"👤 Usuario: {username}")
        action_user.setEnabled(False)
        
        menu.addSeparator()
        
        action_logout = menu.addAction("🚪 Cerrar Sesión")
        action_logout.triggered.connect(self.logout_requested.emit)
        
        menu.exec_(QCursor.pos())
        
    def _build_top_panels(self):
        top_layout = QHBoxLayout()
        top_layout.setSpacing(16)
        
        # 1. Controles Operativos
        controles_frame = QFrame()
        controles_frame.setObjectName("card")
        c_layout = QVBoxLayout(controles_frame)
        
        lbl_c = CustomLabel("⚙ CONTROLES OPERATIVOS", variant="subheader")
        c_layout.addWidget(lbl_c)
        
        self.chk_autonomo = CustomSwitch("🤖 Modo Autónomo (Visible Recomendado)")
        self.chk_autonomo.setChecked(True)
        self.chk_autonomo.setEnabled(False)
        c_layout.addWidget(self.chk_autonomo)
        
        self.chk_incluir_ya_descargadas = CustomSwitch("Incluir 'Ya descargadas'")
        self.chk_incluir_ya_descargadas.setChecked(False)
        self.chk_incluir_ya_descargadas.setToolTip("Activado: Procesa y vuelve a descargar facturas ya descargadas/registradas en base de datos")
        c_layout.addWidget(self.chk_incluir_ya_descargadas)
        
        self.chk_capturar_delegacion = CustomSwitch("Capturar Delegación")
        self.chk_capturar_delegacion.setChecked(False)
        self.chk_capturar_delegacion.setToolTip("Extraer temporalmente la delegación (Cancun o Playa del Carmen) desde las facturas PDF")
        c_layout.addWidget(self.chk_capturar_delegacion)
        
        # Custom Download Path selector
        lbl_path_title = CustomLabel("📁 Ruta de Descarga / Facturas:", variant="body")
        lbl_path_title.setStyleSheet("font-weight: bold;")
        c_layout.addWidget(lbl_path_title)
        
        path_input_layout = QHBoxLayout()
        display_label_text = f"Por defecto ({self.default_output_dir})"
        self.lbl_download_path_display = CustomLabel(display_label_text, variant="body")
        self.lbl_download_path_display.setStyleSheet("background-color: #f9fafb; padding: 6px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 11px;")
        self.selected_custom_path = None
        path_input_layout.addWidget(self.lbl_download_path_display, stretch=4)
        
        self.btn_browse = CustomButton("...", is_secondary=True)
        self.btn_browse.setObjectName("secondaryBtn")
        self.btn_browse.setStyleSheet("padding: 4px 8px; font-weight: bold;")
        self.btn_browse.clicked.connect(self._on_browse_path_clicked)
        path_input_layout.addWidget(self.btn_browse, stretch=1)
        c_layout.addLayout(path_input_layout)
        
        # GLStatusIndicator pill under the download path
        self.status_indicator = GLStatusIndicator()
        c_layout.addWidget(self.status_indicator)
        
        self.btn_iniciar = CustomButton("▶ Iniciar Bot", is_secondary=False)
        self.btn_iniciar.setObjectName("primaryBtn")
        self.btn_iniciar.clicked.connect(self._on_iniciar_bot)
        c_layout.addWidget(self.btn_iniciar)
        
        self.btn_seleccionar = CustomButton("📥 Cargar Solicitud Seleccionada", is_secondary=True)
        self.btn_seleccionar.setObjectName("secondaryBtn")
        self.btn_seleccionar.clicked.connect(self._on_cargar_solicitud)
        c_layout.addWidget(self.btn_seleccionar)
        
        c_layout.addStretch()
        
        top_layout.addWidget(controles_frame, stretch=1)
        
        # 2. Métricas del Lote
        metricas_frame = QFrame()
        metricas_frame.setObjectName("card")
        m_layout = QVBoxLayout(metricas_frame)
        
        lbl_m = CustomLabel("📊 MÉTRICAS DE FACTURACIÓN", variant="subheader")
        m_layout.addWidget(lbl_m)
        
        grid_m = QGridLayout()
        self.box_pendientes = MetricBox("Por Facturar", "0", "#3b82f6")
        self.box_exitosos = MetricBox("Facturadas", "0", "#10b981")
        self.box_errores = MetricBox("Errores", "0", "#ef4444")
        
        grid_m.addWidget(self.box_pendientes, 0, 0)
        grid_m.addWidget(self.box_exitosos, 0, 1)
        grid_m.addWidget(self.box_errores, 0, 2)
        
        self.lbl_rfc_info = CustomLabel("RFC: -- | Razón Social: --\nCP: --", variant="muted")
        self.lbl_rfc_info.setStyleSheet("color: #6b7280; font-size: 11px; background: #f9fafb; padding: 8px; border: 1px solid #e5e7eb; border-radius: 4px;")
        grid_m.addWidget(self.lbl_rfc_info, 1, 0, 1, 3)
        
        m_layout.addLayout(grid_m)
        m_layout.addStretch()
        top_layout.addWidget(metricas_frame, stretch=1)
        
        # 3. Monitoreo en Tiempo Real
        monitoreo_frame = QFrame()
        monitoreo_frame.setObjectName("card")
        mon_layout = QVBoxLayout(monitoreo_frame)
        
        lbl_mon = CustomLabel("📡 MONITOREO EN TIEMPO REAL", variant="subheader")
        mon_layout.addWidget(lbl_mon)
        
        grid_data = QGridLayout()
        grid_data.addWidget(CustomLabel("Referencia:", variant="body"), 0, 0)
        self.lbl_m_ref = CustomLabel("--", variant="body")
        grid_data.addWidget(self.lbl_m_ref, 0, 1)
        
        grid_data.addWidget(CustomLabel("RFC:", variant="body"), 1, 0)
        self.lbl_m_rfc = CustomLabel("--", variant="body")
        grid_data.addWidget(self.lbl_m_rfc, 1, 1)
        
        grid_data.addWidget(CustomLabel("Estado:", variant="body"), 2, 0)
        self.lbl_m_est = CustomLabel("--", variant="body")
        grid_data.addWidget(self.lbl_m_est, 2, 1)
        mon_layout.addLayout(grid_data)
        
        mon_layout.addWidget(CustomLabel("Progreso Lote", variant="body"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setValue(0)
        mon_layout.addWidget(self.progress_bar)
        
        self.lbl_mon_status = CustomLabel("ESPERANDO INICIO DE PROCESAMIENTO...", variant="muted")
        self.lbl_mon_status.setStyleSheet("color: #6b7280; font-size: 11px;")
        mon_layout.addWidget(self.lbl_mon_status)
        
        mon_layout.addStretch()
        top_layout.addWidget(monitoreo_frame, stretch=1)
        
        self.main_layout.addLayout(top_layout, stretch=1)

    def _on_browse_path_clicked(self):
        reply = QMessageBox.question(
            self,
            "Confirmar Cambio de Ruta",
            f"Se recomienda encarecidamente utilizar la ruta por defecto ({self.default_output_dir}) para garantizar la sincronización automática y auditoría centralizada.\n\n¿Estás seguro de que deseas cambiar la ruta de descarga?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            return
            
        dir_path = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Descarga de Facturas")
        if dir_path:
            self.selected_custom_path = dir_path
            display_path = dir_path if len(dir_path) < 35 else "..." + dir_path[-32:]
            self.lbl_download_path_display.setText(display_path)
            self.log(f"Ruta de almacenamiento cambiada a: {dir_path}")

    def _build_table_panel(self):
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        
        header_layout = QHBoxLayout()
        lbl = CustomLabel("⚙ SOLICITUDES PARA FACTURACIÓN", variant="subheader")
        header_layout.addWidget(lbl)
        header_layout.addStretch()
        
        self.chk_ver_todas = CustomCheckBox("Mostrar solicitudes facturadas")
        self.chk_ver_todas.setStyleSheet("margin-right: 8px;")
        self.chk_ver_todas.stateChanged.connect(self._load_solicitudes)
        header_layout.addWidget(self.chk_ver_todas)

        btn_refresh = CustomButton("↻ Actualizar", is_secondary=False)
        btn_refresh.clicked.connect(self._load_solicitudes)
        header_layout.addWidget(btn_refresh)
        
        layout.addLayout(header_layout)
        
        headers = ["ID Solicitud", "Folio Orden", "RFC", "Razón Social", "Concepto", "Solicitadas", "P. x Facturar", "Facturadas", "Estado"]
        self.table = StyledDataTable(headers, parent=self)
        self.table.setObjectName("botTable")
        self.table.doubleClicked.connect(lambda index: self._on_cargar_solicitud())
        self.table.setMinimumHeight(150)
        self.table.setMaximumHeight(200)
        layout.addWidget(self.table)
        
        self.main_layout.addWidget(panel, stretch=2)

    def _build_console_panel(self):
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        
        lbl = CustomLabel("⚙ CONSOLA DE LOGS DE ACTIVIDAD", variant="subheader")
        layout.addWidget(lbl)
        
        self.console = QTextEdit()
        self.console.setObjectName("console")
        self.console.setReadOnly(True)
        self.console.setMinimumHeight(100)
        self.console.setMaximumHeight(140)
        layout.addWidget(self.console)
        
        self.log("Sistema listo. Esperando carga de solicitud...")
        
        self.main_layout.addWidget(panel, stretch=1)

    def log(self, message: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.console.append(f"[{timestamp}] {message}")

    def _load_solicitudes(self):
        self.log("Actualizando tabla de solicitudes asignadas...")
        try:
            u_id = self.usuario_id if self.usuario_id else 1
            ver_todas = self.chk_ver_todas.isChecked() if hasattr(self, 'chk_ver_todas') else False
            
            if self.api_client.connect_via_api:
                solicitudes = self.api_client.request("GET", f"/api/docs/solicitudes/facturacion/{u_id}", data={"ver_facturadas": ver_todas})
            else:
                with self.db_connector.get_session() as session:
                    repo = OperacionRepository(session)
                    solicitudes = repo.get_solicitudes_facturacion(u_id, ver_facturadas=ver_todas)
            
            data_rows = []
            for s in solicitudes:
                del_raw = (s.get("delegacion") or "").upper()
                del_abrev = ""
                if "CANCUN" in del_raw or "CANCÚN" in del_raw:
                    del_abrev = "CUN"
                elif "PLAYA" in del_raw:
                    del_abrev = "PYA"
                else:
                    del_abrev = "".join(c for c in del_raw if c.isalnum())[:3]
                
                concepto_formatted = f"{s['concepto']}-{del_abrev}" if del_abrev else s["concepto"]
                
                data_rows.append([
                    str(s["solicitud_id"]),
                    s["folio"],
                    s["rfc"],
                    s["razon_social"],
                    concepto_formatted,
                    str(s["cantidad_solicitada"]),
                    str(s.get("cantidad_autorizada", 0)),
                    str(s.get("cantidad_facturada", 0)),
                    s["estado"]
                ])
                
            self.table.populate_rows(data_rows)
            self.log(f"Se cargaron {len(solicitudes)} solicitudes.")
        except Exception as e:
            self.log(f"ERROR: {str(e)}")
            QMessageBox.critical(self, "Error", f"No se pudieron cargar las solicitudes:\n{str(e)}")

    def _on_cargar_solicitud(self):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            return
            
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Atención", "Selecciona una fila de la tabla primero.")
            return
            
        row = selected[0].row()
        estado = self.table.item(row, 8).text().upper()
        valid_states = ("AUTORIZADA", "AUTORIZACION_PARCIAL", "ERROR_VALIDACION", "FACTURADA_PARCIAL", "ERROR", "PROCESANDO")
        if estado not in valid_states:
            QMessageBox.warning(
                self, 
                "Atención", 
                f"No se puede procesar esta solicitud. Estado actual: '{estado}'.\n"
                f"El robot solo puede procesar solicitudes en estado: {', '.join(valid_states)}."
            )
            return
            
        sol_id = int(self.table.item(row, 0).text())
        self.log(f"Cargando contexto para Solicitud {sol_id}...")
        
        try:
            u_id = self.usuario_id if self.usuario_id else 1
            if self.api_client.connect_via_api:
                ctx = self.api_client.request("GET", f"/api/docs/solicitudes/{sol_id}/bot-context")
            else:
                with self.db_connector.get_session() as session:
                    repo = OperacionRepository(session)
                    ctx = repo.get_solicitud_bot_context(sol_id)
                
            ctx["usuario_id"] = u_id
            self.current_bot_context = ctx
                
            # Update UI labels
            razon_social_clean = self._clean_razon_social(ctx['razon_social'])
            self.lbl_rfc_info.setText(f"RFC: {ctx['rfc']} | Razón Social: {razon_social_clean}\nCP: {ctx['codigo_postal']} | Municipio: {ctx.get('municipio_nombre', '')}")
            
            # --- Resetear métricas antes de calcular para evitar residuos de cargas previas ---
            self.box_pendientes.set_value("0")
            self.box_exitosos.set_value("0")
            self.box_errores.set_value("0")
            
            total = ctx["consecutivo_fin"] - ctx["consecutivo_inicio"] + 1
            # Facturas ya procesadas/timbradas exitosamente.
            facturadas = ctx["facturas_procesadas"]
            errores = ctx.get("referencias_con_error", 0)
            
            # Guardar variables de estado para el decremento dinámico
            self.total_referencias = total
            self.errores_iniciales = errores
            self.current_success = facturadas
            self.current_errors = errores
            
            # Referencias autorizadas pendientes de facturar (total autorizado menos lo ya facturado y lo que falló)
            autorizadas_pendientes = total - facturadas - errores
            
            # Tarjeta "Por Facturar": muestra cuántas referencias aún están por facturar
            self.box_pendientes.set_value(str(max(0, autorizadas_pendientes)))
            # Tarjeta "Facturadas": muestra cuántas ya fueron timbradas en sesiones previas
            self.box_exitosos.set_value(str(max(0, facturadas)))
            # Tarjeta "Errores": muestra cuántas fallaron previamente
            self.box_errores.set_value(str(max(0, errores)))
            
            self.log(f"ÉXITO: Contexto de {ctx['rfc']} cargado para facturación.")
            self.log(f"Concepto: {ctx['concepto_nombre']} | Rango de Facturación: {ctx['consecutivo_inicio']} al {ctx['consecutivo_fin']}")
            
            QMessageBox.information(self, "Contexto Listo", "Datos cargados en memoria.\nEl Bot de Facturación está listo para iniciar.")
                
        except Exception as e:
            self.log(f"ERROR al cargar caché: {str(e)}")
            QMessageBox.critical(self, "Error", f"Fallo al obtener datos:\n{str(e)}")

    def _on_iniciar_bot(self):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.btn_iniciar.setEnabled(False)
            self.btn_iniciar.setText("⏹ Deteniendo...")
            self.worker.stop()
            return

        if not self.current_bot_context:
            QMessageBox.warning(self, "Atención", "No hay contexto cargado. Primero selecciona y carga una solicitud.")
            return
            
        sol_id = self.current_bot_context.get("solicitud_id")
        try:
            state_code = None
            if self.api_client.connect_via_api:
                u_id = self.usuario_id if self.usuario_id else 1
                sols = self.api_client.request("GET", f"/api/docs/solicitudes/facturacion/{u_id}", data={"ver_facturadas": True})
                for s in sols:
                    if s["solicitud_id"] == sol_id:
                        state_code = s["estado"].upper()
                        break
            else:
                with self.db_connector.get_session() as session:
                    sol = session.get(Solicitud, sol_id)
                    if sol:
                        state_code = session.execute(
                            text("SELECT codigo FROM sar_catalogo.estado_sistema WHERE estado_id = :eid"),
                            {"eid": sol.estado_id}
                        ).scalar()
            
            if state_code:
                valid_states = ("AUTORIZADA", "AUTORIZACION_PARCIAL", "PROCESANDO", "ERROR", "ERROR_VALIDACION", "FACTURADA_PARCIAL")
                if state_code not in valid_states:
                    QMessageBox.warning(
                        self, 
                        "Atención", 
                        f"El estado de la solicitud es '{state_code}' y no se puede procesar.\n"
                        f"El robot solo puede iniciar solicitudes en estado: {', '.join(valid_states)}."
                    )
                    self.current_bot_context = None
                    self._load_solicitudes()
                    return
                if state_code == "PROCESANDO":
                    reply_proc = QMessageBox.warning(
                        self,
                        "Colisión Detectada",
                        "Esta solicitud está actualmente en estado PROCESANDO (posiblemente por otro bot o una ejecución previa no cerrada correctamente).\n\nSi fuerzas el inicio podrías duplicar operaciones y causar errores.\n\n¿Estás seguro de forzar el inicio?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if reply_proc == QMessageBox.StandardButton.No:
                        return
        except Exception as e:
            self.log(f"Advertencia al validar estado de solicitud: {str(e)}")
            
        razon_social = self.current_bot_context.get("razon_social", "Desconocido")
        concepto = self.current_bot_context.get("concepto_nombre", "Desconocido")
        consecutivo_inicio = self.current_bot_context.get("consecutivo_inicio", 1)
        consecutivo_fin = self.current_bot_context.get("consecutivo_fin", 1)
        facturadas = self.current_bot_context.get("facturas_procesadas", 0)
        
        start_consec = consecutivo_inicio + facturadas
        cantidad_a_procesar = consecutivo_fin - start_consec + 1
        
        if cantidad_a_procesar <= 0:
            QMessageBox.information(self, "Atención", "Todas las referencias de esta solicitud ya han sido procesadas / timbradas.")
            return

        confirm_text = (
            f"¿Deseas iniciar el proceso de facturación y timbrado CFDI?\n\n"
            f"🏢 Razón Social: {razon_social}\n"
            f"📄 Concepto: {concepto}\n"
            f"🔢 Cantidad a procesar: {cantidad_a_procesar} referencias (del {start_consec} al {consecutivo_fin})"
        )
        
        reply = QMessageBox.question(
            self, 
            "Confirmar Facturación", 
            confirm_text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            self.log("Inicio del Bot cancelado por el usuario.")
            return
            
        # Inverted logic: Checked/ON = Visible (headless=False), Unchecked/OFF = Invisible (headless=True)
        headless_mode = not self.chk_autonomo.isChecked()
        
        self.log("INICIANDO SECUENCIA DE TIMBRADO RPA...")
        self.btn_iniciar.setText("⏹ Detener Bot")
        self.btn_iniciar.setStyleSheet(f"background-color: {Colors.ERROR}; color: white;")
        self.btn_seleccionar.setEnabled(False)
        self.table.setEnabled(False)
        self.chk_autonomo.setEnabled(False)
        self.chk_incluir_ya_descargadas.setEnabled(False)
        self.chk_capturar_delegacion.setEnabled(False)
        self.chk_ver_todas.setEnabled(False)
        self.btn_browse.setEnabled(False)
        self.btn_gear.setEnabled(False)
        self.btn_user.setEnabled(False)
        
        self.lbl_portal_status.setText("Portal: ACTIVO")
        self.lbl_portal_status.setStyleSheet(f"background-color: {Colors.ACCENT_EMERALD}; padding: 4px 12px; border-radius: 12px; font-size: 12px; color: white; font-weight: bold;")
        
        omitir_ya_gen = not self.chk_incluir_ya_descargadas.isChecked()
        capturar_del = self.chk_capturar_delegacion.isChecked()
        self.worker = BillingRpaWorker(
            db_connector=self.db_connector,
            context=self.current_bot_context,
            headless=headless_mode,
            custom_output_dir=self.selected_custom_path,
            omitir_ya_generadas=omitir_ya_gen,
            capturar_delegacion=capturar_del
        )
        
        # Connect Signals
        self.worker.status_changed.connect(self.log)
        self.worker.progress_changed.connect(self.progress_bar.setValue)
        self.worker.metric_updated.connect(self._on_metric_updated)
        self.worker.referencia_generada.connect(self._on_referencia_generada)
        self.worker.finished_processing.connect(self._on_finished_processing)
        
        # Start Worker Thread
        self.worker.start()

    def _on_metric_updated(self, name: str, value: int):
        if name == "exitosos":
            self.current_success = value
            self.box_exitosos.set_value(str(value))
        elif name == "errores":
            self.current_errors = self.errores_iniciales + value
            self.box_errores.set_value(str(self.current_errors))
        elif name in ("pendientes", "autorizadas"):
            self.box_pendientes.set_value(str(value))
            return

        # Recalculate remaining pending/por facturar dynamically
        if hasattr(self, "total_referencias"):
            remaining = self.total_referencias - self.current_success - self.current_errors
            self.box_pendientes.set_value(str(max(0, remaining)))

    def _on_referencia_generada(self, ref_portal: str, rfc: str, status: str):
        self.lbl_m_ref.setText(ref_portal)
        self.lbl_m_rfc.setText(rfc)
        self.lbl_m_est.setText(status)
        if status == "EXITOSO":
            self.lbl_m_est.setStyleSheet(f"color: {Colors.ACCENT_EMERALD}; font-weight: bold;")
        else:
            self.lbl_m_est.setStyleSheet(f"color: {Colors.ERROR}; font-weight: bold;")

    def _on_finished_processing(self, success: bool, message: str):
        self.btn_iniciar.setEnabled(True)
        self.btn_iniciar.setText("▶ Iniciar Bot")
        self.btn_iniciar.setStyleSheet(f"background-color: {Colors.SURFACE_DARK}; color: white;")
        self.btn_seleccionar.setEnabled(True)
        self.table.setEnabled(True)
        self.chk_autonomo.setEnabled(True)
        self.chk_incluir_ya_descargadas.setEnabled(True)
        self.chk_capturar_delegacion.setEnabled(True)
        self.chk_ver_todas.setEnabled(True)
        self.btn_browse.setEnabled(True)
        self.btn_gear.setEnabled(True)
        self.btn_user.setEnabled(True)
        
        self.lbl_portal_status.setText("Portal: INACTIVO")
        self.lbl_portal_status.setStyleSheet(f"background-color: {Colors.BORDER_DARK}; padding: 4px 12px; border-radius: 12px; font-size: 12px; color: white;")
        
        # Reload the requests table to show progress
        self._load_solicitudes()
        
        if success:
            QMessageBox.information(self, "Proceso Terminado", f"El procesamiento de facturación finalizó:\n{message}")
        else:
            QMessageBox.critical(self, "Error de Procesamiento", f"Fallo crítico en el bot de facturación:\n{message}")

    def _verify_and_sync_paths(self):
        """Asynchronously checks write access to the default output dir and triggers sync if connected."""
        self.status_indicator.set_status("checking")
        self.path_verify_thread = PathVerifyThread(self.default_output_dir, self)
        self.path_verify_thread.result_ready.connect(self._on_path_verified)
        self.path_verify_thread.start()

    def _on_path_verified(self, path_str, has_access, error_message):
        if has_access:
            self.status_indicator.set_status("online", "CONECTADO")
            self.log(f"Ruta por defecto accesible: {path_str}. Iniciando sincronización...")
            
            # Start sync of local contingency files
            self.sync_thread = SyncContingencyThread(self.db_connector, self.default_output_dir, self)
            self.sync_thread.progress_msg.connect(self.log)
            self.sync_thread.finished_sync.connect(self._on_sync_finished)
            self.sync_thread.start()
        else:
            self.status_indicator.set_status("offline", "SIN ACCESO")
            self.log(f"ADVERTENCIA: La ruta por defecto '{path_str}' no es accesible. Error: {error_message}")
            self.log("Las facturas descargadas se guardarán temporalmente en contingencia local en caso de iniciarse el bot.")

    def _on_sync_finished(self, success, migrated_count, message):
        if success:
            if migrated_count > 0:
                self.log(f"Sincronización de contingencia exitosa: {message}")
                QMessageBox.information(self, "Sincronización Exitosa", f"Se migraron {migrated_count} facturas de contingencia local a la unidad de red por defecto con éxito.")
        else:
            self.log(f"Fallo en sincronización de contingencia: {message}")

    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            QMessageBox.warning(
                self, 
                "Operación en Curso", 
                "No se puede cerrar la aplicación mientras el bot esté en proceso activo.\n"
                "Por favor, detenga o pause la ejecución antes de salir."
            )
            event.ignore()
            return
        event.accept()

    def _clean_razon_social(self, name: str) -> str:
        """Strips Mexican capital regimes and suffixes from business names to comply with CFDI 4.0 validation."""
        if not name:
            return ""
        
        name_clean = name.upper().strip()
        
        # Regex patterns for common Mexican capital regimes
        regimes = [
            r"\bS\.?\s*A\.?\s*D\.?\s*E\.?\s*C\.?\s*V\.?\b",
            r"\bS\.?\s*D\.?\s*E\.?\s*R\.?\s*L\.?\s*D\.?\s*E\.?\s*C\.?\s*V\.?\b",
            r"\bS\.?\s*A\.?\s*P\.?\s*I\.?\s*D\.?\s*E\.?\s*C\.?\s*V\.?\b",
            r"\bS\.?\s*A\.?\s*B\.?\s*D\.?\s*E\.?\s*C\.?\s*V\.?\b",
            r"\bS\.?\s*A\.?\b",
            r"\bA\.?\s*C\.?\b",
            r"\bS\.?\s*C\.?\b",
            r"\bS\.?\s*D\.?\s*E\.?\s*R\.?\s*L\.?\b",
            r"\bS\.?\s*P\.?\s*R\.?\b",
        ]
        
        for r in regimes:
            name_clean = re.sub(r, "", name_clean)
            
        # Clean trailing commas and collapse extra spacing
        name_clean = re.sub(r"\s*,\s*$", "", name_clean)
        name_clean = re.sub(r"\s+", " ", name_clean)
        return name_clean.strip()

from PySide6.QtWidgets import QMainWindow
from PySide6.QtCore import Signal

class BillingBotWindow(QMainWindow):
    logout_requested = Signal()

    def __init__(self, db_connector, sesion_id, usuario_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SAR - Bot Face C (Facturación y Timbrado)")
        self.resize(1100, 750)
        self.view = BillingBotView(db_connector, sesion_id, usuario_id, self)
        self.setCentralWidget(self.view)
        
        # Propagate logout signal
        self.view.logout_requested.connect(self.logout_requested.emit)

    def closeEvent(self, event):
        # Delegate close event validation directly to the child view
        self.view.closeEvent(event)

