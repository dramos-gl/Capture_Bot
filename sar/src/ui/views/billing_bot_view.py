"""RPA Bot Dashboard View (Face C - Billing and Timbrado)."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QFrame, QLabel, QPushButton, QCheckBox, QTextEdit, 
    QMessageBox, QProgressBar, QMenu, QFileDialog
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QCursor

from sar.src.ui.design_system.components import CustomCard, StyledDataTable, CustomButton, CustomLabel, CustomCheckBox

class MetricBox(QFrame):
    def __init__(self, title: str, value: str, color: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(105)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-left: 4px solid {color};
                border-radius: 6px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        lbl_title = CustomLabel(title, variant="muted")
        lbl_title.setStyleSheet("font-weight: bold; color: #6b7280; font-size: 11px;")
        layout.addWidget(lbl_title)
        
        self.lbl_value = CustomLabel(value, variant="header")
        self.lbl_value.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {color};")
        layout.addWidget(self.lbl_value)
        
    def set_value(self, value: str):
        self.lbl_value.setText(value)

class BillingBotView(QWidget):
    logout_requested = Signal()

    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.current_bot_context = None
        
        # Force Light Theme styles for this specific view to match Optima Capture Bot
        self.setStyleSheet("""
            QWidget {
                background-color: #f3f4f6;
                color: #1f2937;
                font-family: 'Segoe UI', sans-serif;
            }
            QFrame#card {
                background-color: #ffffff;
                border-radius: 8px;
                border: 1px solid #e5e7eb;
            }
            QLabel {
                background: transparent;
            }
            QPushButton#primaryBtn {
                background-color: #2563eb;
                color: white;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton#primaryBtn:hover {
                background-color: #1d4ed8;
            }
            QPushButton#secondaryBtn {
                background-color: #ffffff;
                color: #4b5563;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #f9fafb;
            }
            QPushButton#iconHeaderBtn {
                background-color: transparent;
                border: none;
                color: #4b5563;
                font-size: 16px;
                padding: 4px;
            }
            QPushButton#iconHeaderBtn:hover {
                background-color: #f3f4f6;
                border-radius: 4px;
            }
            QTextEdit#console {
                background-color: #f8fafc;
                color: #0f172a;
                font-family: 'Consolas', monospace;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                padding: 8px;
            }
            QProgressBar {
                border: 1px solid #e5e7eb;
                border-radius: 4px;
                text-align: center;
                background-color: #f3f4f6;
            }
            QProgressBar::chunk {
                background-color: #2563eb;
            }
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(16)
        
        # Load default RUTA_DERECHOS parameter
        self.default_output_dir = "storage"
        try:
            from sar.src.storage.repositories import ConfigRepository
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
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-left: 4px solid #2563eb;
                border-radius: 8px;
                padding: 12px 24px;
            }
            QLabel {
                color: #0f172a;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(12)
        
        lbl = QLabel("🚀 BOT - FACTURACIÓN Y TIMBRADO (FACE C)")
        h_layout.addWidget(lbl)
        h_layout.addStretch()
        
        self.lbl_portal_status = QLabel("Portal: INACTIVO")
        self.lbl_portal_status.setStyleSheet("background-color: #eff6ff; border: 1px solid #bfdbfe; padding: 4px 12px; border-radius: 12px; font-size: 12px; color: #1e40af; font-weight: bold;")
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

    def _on_gear_clicked(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                color: #1f2937;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 12px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #f3f4f6;
            }
        """)
        
        portal_url = "https://shacienda.qroo.gob.mx/tributanet/"
        try:
            from sar.src.storage.repositories import ConfigRepository
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
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                color: #1f2937;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 12px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #f3f4f6;
            }
        """)
        
        username = "Operador"
        try:
            main_window = self.window()
            current_sesion_id = getattr(main_window, 'current_sesion_id', None)
            if current_sesion_id:
                from sar.src.storage.models import Sesion
                with self.db_connector.get_session() as session:
                    db_sesion = session.get(Sesion, current_sesion_id)
                    if db_sesion and db_sesion.usuario:
                        username = db_sesion.usuario.nombre
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
        
        self.chk_autonomo = CustomCheckBox("Modo Autónomo (Facturación Directa)")
        c_layout.addWidget(self.chk_autonomo)
        
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
        self.btn_browse.setStyleSheet("padding: 4px 8px; font-weight: bold;")
        self.btn_browse.clicked.connect(self._on_browse_path_clicked)
        path_input_layout.addWidget(self.btn_browse, stretch=1)
        c_layout.addLayout(path_input_layout)
        
        # GLStatusIndicator pill under the download path
        from sar.src.ui.design_system.components.atoms.gl_status_indicator import GLStatusIndicator
        self.status_indicator = GLStatusIndicator()
        c_layout.addWidget(self.status_indicator)
        
        self.btn_iniciar = CustomButton("▶ Iniciar Facturación", is_secondary=False)
        self.btn_iniciar.clicked.connect(self._on_iniciar_bot)
        c_layout.addWidget(self.btn_iniciar)
        
        self.btn_seleccionar = CustomButton("📥 Cargar Solicitud Seleccionada", is_secondary=True)
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
        self.box_pendientes = MetricBox("Pendientes", "0", "#3b82f6")
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
        top_layout.addWidget(metricas_frame, stretch=2)
        
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
        self.progress_bar.setValue(0)
        mon_layout.addWidget(self.progress_bar)
        
        self.lbl_mon_status = CustomLabel("ESPERANDO INICIO DE PROCESAMIENTO...", variant="muted")
        self.lbl_mon_status.setStyleSheet("color: #6b7280; font-size: 11px;")
        mon_layout.addWidget(self.lbl_mon_status)
        
        mon_layout.addStretch()
        top_layout.addWidget(monitoreo_frame, stretch=1)
        
        self.main_layout.addLayout(top_layout, stretch=1)

    def _on_browse_path_clicked(self):
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
        
        self.chk_ver_todas = CustomCheckBox("Mostrar completadas y canceladas")
        self.chk_ver_todas.setStyleSheet("margin-right: 8px;")
        self.chk_ver_todas.stateChanged.connect(self._load_solicitudes)
        header_layout.addWidget(self.chk_ver_todas)

        btn_refresh = CustomButton("↻ Actualizar", is_secondary=False)
        btn_refresh.clicked.connect(self._load_solicitudes)
        header_layout.addWidget(btn_refresh)
        
        layout.addLayout(header_layout)
        
        headers = ["ID Solicitud", "Folio Orden", "RFC", "Razón Social", "Concepto", "Solicitadas", "Facturadas/Generadas", "Estado"]
        self.table = StyledDataTable(headers, parent=self)
        self.table.doubleClicked.connect(lambda index: self._on_cargar_solicitud())
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                color: #374151;
                gridline-color: #e5e7eb;
                border: 1px solid #e5e7eb;
            }
            QHeaderView::section {
                background-color: #f9fafb;
                color: #374151;
                font-weight: bold;
                border: none;
                border-bottom: 1px solid #e5e7eb;
                padding: 4px;
            }
        """)
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
        layout.addWidget(self.console)
        
        self.log("Sistema listo. Esperando carga de solicitud...")
        
        self.main_layout.addWidget(panel, stretch=1)

    def log(self, message: str):
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.console.append(f"[{timestamp}] {message}")

    def _load_solicitudes(self):
        self.log("Actualizando tabla de solicitudes asignadas...")
        try:
            from sar.src.storage.repositories import OperacionRepository
            from sar.src.storage.models import Sesion
            
            main_window = self.window()
            current_sesion_id = getattr(main_window, 'current_sesion_id', None)
            
            with self.db_connector.get_session() as session:
                u_id = 1
                if current_sesion_id:
                    db_sesion = session.get(Sesion, current_sesion_id)
                    if db_sesion: u_id = db_sesion.usuario_id
                
                repo = OperacionRepository(session)
                ver_todas = self.chk_ver_todas.isChecked() if hasattr(self, 'chk_ver_todas') else False
                solicitudes = repo.get_solicitudes_asignadas(u_id, ver_todas=ver_todas)
                
                data_rows = []
                for s in solicitudes:
                    data_rows.append([
                        str(s["solicitud_id"]),
                        s["folio"],
                        s["rfc"],
                        s["razon_social"],
                        s["concepto"],
                        str(s["cantidad_solicitada"]),
                        str(s["cantidad_generada"]),
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
        estado = self.table.item(row, 7).text().upper()
        valid_states = ("ASIGNADO", "ASIGNADA", "PROCESANDO", "ERROR")
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
            from sar.src.storage.repositories import OperacionRepository
            with self.db_connector.get_session() as session:
                repo = OperacionRepository(session)
                ctx = repo.get_solicitud_bot_context(sol_id)
                
                main_window = self.window()
                current_sesion_id = getattr(main_window, 'current_sesion_id', None)
                u_id = 1
                if current_sesion_id:
                    from sar.src.storage.models import Sesion
                    db_sesion = session.get(Sesion, current_sesion_id)
                    if db_sesion:
                        u_id = db_sesion.usuario_id
                
                ctx["usuario_id"] = u_id
                self.current_bot_context = ctx
                
                # Update UI labels
                self.lbl_rfc_info.setText(f"RFC: {ctx['rfc']} | Razón Social: {ctx['razon_social']}\nCP: {ctx['codigo_postal']} | Municipio: {ctx['municipio']}")
                
                total = ctx["consecutivo_fin"] - ctx["consecutivo_inicio"] + 1
                completados = ctx["ultimo_consecutivo"] - ctx["consecutivo_inicio"] + 1 if ctx["ultimo_consecutivo"] >= ctx["consecutivo_inicio"] else 0
                pendientes = total - completados
                
                self.box_pendientes.set_value(str(pendientes))
                self.box_exitosos.set_value(str(completados))
                
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
            from sqlalchemy import text
            with self.db_connector.get_session() as session:
                from sar.src.storage.models import Solicitud
                sol = session.get(Solicitud, sol_id)
                if sol:
                    state_code = session.execute(
                        text("SELECT codigo FROM sar_catalogo.estado_sistema WHERE estado_id = :eid"),
                        {"eid": sol.estado_id}
                    ).scalar()
                    valid_states = ("ASIGNADO", "ASIGNADA", "PROCESANDO", "ERROR")
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
        except Exception as e:
            self.log(f"Advertencia al validar estado de solicitud en BD: {str(e)}")
            
        razon_social = self.current_bot_context.get("razon_social", "Desconocido")
        concepto = self.current_bot_context.get("concepto_nombre", "Desconocido")
        consecutivo_inicio = self.current_bot_context.get("consecutivo_inicio", 1)
        consecutivo_fin = self.current_bot_context.get("consecutivo_fin", 1)
        ultimo_consecutivo = self.current_bot_context.get("ultimo_consecutivo")
        
        start_consec = ultimo_consecutivo + 1 if (ultimo_consecutivo is not None and ultimo_consecutivo >= consecutivo_inicio) else consecutivo_inicio
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
            
        headless_mode = self.chk_autonomo.isChecked()
        
        self.log("INICIANDO SECUENCIA DE TIMBRADO RPA...")
        self.btn_iniciar.setText("⏹ Detener Bot")
        self.btn_iniciar.setStyleSheet("background-color: #ef4444; color: white;")
        self.btn_seleccionar.setEnabled(False)
        self.table.setEnabled(False)
        self.chk_autonomo.setEnabled(False)
        self.chk_ver_todas.setEnabled(False)
        self.btn_browse.setEnabled(False)
        
        self.lbl_portal_status.setText("Portal: ACTIVO")
        self.lbl_portal_status.setStyleSheet("background-color: #10b981; padding: 4px 12px; border-radius: 12px; font-size: 12px; color: white; font-weight: bold;")
        
        from sar.src.core.billing_rpa_worker import BillingRpaWorker
        self.worker = BillingRpaWorker(
            db_connector=self.db_connector,
            context=self.current_bot_context,
            headless=headless_mode,
            custom_output_dir=self.selected_custom_path
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
        if name == "pendientes":
            self.box_pendientes.set_value(str(value))
        elif name == "exitosos":
            self.box_exitosos.set_value(str(value))
        elif name == "errores":
            self.box_errores.set_value(str(value))

    def _on_referencia_generada(self, ref_portal: str, rfc: str, status: str):
        self.lbl_m_ref.setText(ref_portal)
        self.lbl_m_rfc.setText(rfc)
        self.lbl_m_est.setText(status)
        if status == "EXITOSO":
            self.lbl_m_est.setStyleSheet("color: #10b981; font-weight: bold;")
        else:
            self.lbl_m_est.setStyleSheet("color: #ef4444; font-weight: bold;")

    def _on_finished_processing(self, success: bool, message: str):
        self.btn_iniciar.setEnabled(True)
        self.btn_iniciar.setText("▶ Iniciar Facturación")
        self.btn_iniciar.setStyleSheet("background-color: #1e293b; color: white;")
        self.btn_seleccionar.setEnabled(True)
        self.table.setEnabled(True)
        self.chk_autonomo.setEnabled(True)
        self.chk_ver_todas.setEnabled(True)
        self.btn_browse.setEnabled(True)
        
        self.lbl_portal_status.setText("Portal: INACTIVO")
        self.lbl_portal_status.setStyleSheet("background-color: #334155; padding: 4px 12px; border-radius: 12px; font-size: 12px; color: white;")
        
        # Reload the requests table to show progress
        self._load_solicitudes()
        
        if success:
            QMessageBox.information(self, "Proceso Terminado", f"El procesamiento de facturación finalizó:\n{message}")
        else:
            QMessageBox.critical(self, "Error de Procesamiento", f"Fallo crítico en el bot de facturación:\n{message}")

    def _verify_and_sync_paths(self):
        """Asynchronously checks write access to the default output dir and triggers sync if connected."""
        from sar.src.core.access_manager import PathVerifyThread
        self.status_indicator.set_status("checking")
        self.path_verify_thread = PathVerifyThread(self.default_output_dir, self)
        self.path_verify_thread.result_ready.connect(self._on_path_verified)
        self.path_verify_thread.start()

    def _on_path_verified(self, path_str, has_access, error_message):
        if has_access:
            self.status_indicator.set_status("online", "CONECTADO")
            self.log(f"Ruta por defecto accesible: {path_str}. Iniciando sincronización...")
            
            # Start sync of local contingency files
            from sar.src.core.access_manager import SyncContingencyThread
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
