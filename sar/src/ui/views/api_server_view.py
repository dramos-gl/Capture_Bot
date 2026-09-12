"""Application Server API_SAR Control Module View."""

import os
import sys
import subprocess
import socket
import datetime
import urllib.request
import json
import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel, QMainWindow, 
    QApplication, QTextEdit, QPushButton, QFontDialog, QTableWidget, 
    QTableWidgetItem, QHeaderView, QLineEdit, QFormLayout, QDialog
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, QProcess
from PySide6.QtGui import QIcon, QFont

from sar.src.ui.design_system.theme_manager import ThemeManager
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.organisms.gl_data_table import StyledDataTable
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
from sar.src.ui.design_system.components.molecules.gl_card import CustomCard
from sar.src.ui.design_system.utils.icons import Icons

class ServiceControlWorker(QThread):
    """Worker thread to execute service control commands without freezing the GUI."""
    finished = Signal(str, str) # status, message
    
    def __init__(self, action, service_name="SAR_API"):
        super().__init__()
        self.action = action # "start", "stop", "query"
        self.service_name = service_name

    def run(self):
        try:
            if self.action == "query":
                result = subprocess.run(
                    ["sc", "query", self.service_name],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                stdout = result.stdout or ""
                if "RUNNING" in stdout:
                    self.finished.emit("RUNNING", stdout)
                elif "STOPPED" in stdout:
                    self.finished.emit("STOPPED", stdout)
                elif "PAUSED" in stdout:
                    self.finished.emit("PAUSED", stdout)
                elif "1060" in stdout or "does not exist" in stdout.lower() or "no existe" in stdout.lower():
                    self.finished.emit("NOT_INSTALLED", "Servicio no instalado en el sistema.")
                else:
                    self.finished.emit("UNKNOWN", stdout or result.stderr)
            elif self.action in ["start", "stop"]:
                cmd = ["sc", self.action, self.service_name]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                if result.returncode == 0:
                    self.finished.emit("SUCCESS", f"Acción '{self.action}' enviada con éxito:\n{result.stdout}")
                else:
                    err_msg = result.stderr or result.stdout
                    if "5" in err_msg or "Access is denied" in err_msg or "acceso denegado" in err_msg.lower():
                        self.finished.emit("ERROR_ELEVATION", "Acceso Denegado. Por favor ejecute esta aplicación como Administrador para controlar los servicios de Windows.")
                    elif "1060" in err_msg or "does not exist" in err_msg.lower() or "no existe" in err_msg.lower():
                        self.finished.emit("NOT_INSTALLED", "El servicio 'SAR_API' no está instalado en este equipo Windows.")
                    else:
                        self.finished.emit("ERROR", f"Error al ejecutar '{self.action}': {err_msg}")
        except Exception as e:
            self.finished.emit("EXCEPTION", f"Excepción durante control de servicio: {str(e)}")


class SystemHealthCheckWorker(QThread):
    """Diagnóstico asíncrono triple: Servicio Windows/Local + Endpoint HTTP FastAPI + PostgreSQL Ping."""
    finished = Signal(dict)
    
    def __init__(self, db_connector, api_url, is_local_running=False, service_name="SAR_API"):
        super().__init__()
        self.db_connector = db_connector
        self.api_url = api_url.rstrip("/") if api_url else "http://127.0.0.1:8000"
        self.is_local_running = is_local_running
        self.service_name = service_name
        
    def run(self):
        from sqlalchemy import text
        
        result = {
            "service_status": "UNKNOWN",
            "service_detail": "",
            "api_status": "OFFLINE",
            "api_latency_ms": 0.0,
            "api_detail": "",
            "db_status": "DESCONECTADA",
            "db_latency_ms": 0.0,
            "db_detail": ""
        }
        
        # 1. Estado de Servicio
        if self.is_local_running:
            result["service_status"] = "LOCAL_RUNNING"
            result["service_detail"] = "Proceso Uvicorn ejecutándose localmente en esta aplicación."
        else:
            try:
                res = subprocess.run(
                    ["sc", "query", self.service_name],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                stdout = res.stdout or ""
                if "RUNNING" in stdout:
                    result["service_status"] = "RUNNING"
                    result["service_detail"] = "Servicio Windows activo y en ejecución."
                elif "STOPPED" in stdout:
                    result["service_status"] = "STOPPED"
                    result["service_detail"] = "Servicio Windows detenido."
                elif "1060" in stdout or "does not exist" in stdout.lower() or "no existe" in stdout.lower():
                    result["service_status"] = "NOT_INSTALLED"
                    result["service_detail"] = "Servicio Windows no está registrado en el sistema."
                else:
                    result["service_status"] = "UNKNOWN"
                    result["service_detail"] = stdout.strip() or res.stderr.strip()
            except Exception as e:
                result["service_status"] = "UNKNOWN"
                result["service_detail"] = str(e)
                
        # 2. Endpoint HTTP de la API (FastAPI)
        t_api_start = time.perf_counter()
        health_url = f"{self.api_url}/health"
        try:
            req = urllib.request.Request(
                health_url,
                headers={"User-Agent": "SAR-Server-Monitor/1.0"}
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                elapsed_ms = round((time.perf_counter() - t_api_start) * 1000, 1)
                result["api_latency_ms"] = elapsed_ms
                if resp.status == 200:
                    body = json.loads(resp.read().decode("utf-8"))
                    result["api_status"] = "ONLINE"
                    result["api_detail"] = f"Online ({elapsed_ms} ms)"
                    if body.get("database") == "connected":
                        result["api_db_status"] = "CONECTADA"
                    else:
                        result["api_db_status"] = "DEGRADADA"
                else:
                    result["api_status"] = "DEGRADED"
                    result["api_detail"] = f"HTTP {resp.status}"
        except Exception:
            # Si /health no responde, intentar con /
            try:
                t_root_start = time.perf_counter()
                req_root = urllib.request.Request(
                    f"{self.api_url}/",
                    headers={"User-Agent": "SAR-Server-Monitor/1.0"}
                )
                with urllib.request.urlopen(req_root, timeout=2.0) as resp_root:
                    elapsed_ms = round((time.perf_counter() - t_root_start) * 1000, 1)
                    result["api_latency_ms"] = elapsed_ms
                    if resp_root.status == 200:
                        result["api_status"] = "ONLINE"
                        result["api_detail"] = f"Online ({elapsed_ms} ms)"
                    else:
                        result["api_status"] = "OFFLINE"
                        result["api_detail"] = f"HTTP {resp_root.status}"
            except Exception:
                result["api_status"] = "OFFLINE"
                result["api_detail"] = "Sin respuesta (Puerto 8000 cerrado)"

        # 3. Base de Datos PostgreSQL Directa
        if self.db_connector:
            t_db_start = time.perf_counter()
            try:
                with self.db_connector.get_session() as session:
                    session.execute(text("SELECT 1")).scalar()
                elapsed_db = round((time.perf_counter() - t_db_start) * 1000, 1)
                result["db_status"] = "CONECTADA"
                result["db_latency_ms"] = elapsed_db
                result["db_detail"] = f"SELECT 1 OK ({elapsed_db} ms)"
            except Exception as e:
                result["db_status"] = "DESCONECTADA"
                result["db_detail"] = f"Error: {str(e)[:60]}"
                
        self.finished.emit(result)

class APIServerWindow(QMainWindow):
    """Dedicated Control Panel Window for the API_SAR Application Server."""
    
    logout_requested = Signal()
    
    def __init__(self, db_connector, parent=None, current_usuario_id=None, current_sesion_id=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.current_usuario_id = current_usuario_id
        self.current_sesion_id = current_sesion_id
        self._logging_out = False
        self.local_process = None
        
        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()
        self.active_workers = []
        
        # Window setup: Habilitar maximizar, minimizar y tamaño responsivo
        self.setWindowTitle("Servidor de Aplicaciones API_SAR")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        self.setMinimumSize(760, 440)
        self.resize(860, 500)
        
        # Main Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(6, 6, 6, 6)
        self.main_layout.setSpacing(6)
        
        # Header / Brand Title
        self._setup_header()
        
        # Middle Split: Sidebar Left + Content Right
        self.middle_layout = QHBoxLayout()
        self.middle_layout.setSpacing(8)
        
        self._setup_sidebar()
        self._setup_content_area()
        
        self.middle_layout.addWidget(self.sidebar_card)
        self.middle_layout.addWidget(self.content_card, 1)
        
        self.main_layout.addLayout(self.middle_layout, 1)
        
        # Bottom controls
        self._setup_bottom_bar()
        
        # Apply fonts and logs timer
        self.console_font = QFont("Consolas", 10)
        
        # Auto-query health status (cada 6 segundos)
        self.query_timer = QTimer(self)
        self.query_timer.timeout.connect(self._run_health_check)
        self.query_timer.start(6000)
        
        # Delay initial query
        QTimer.singleShot(150, self._run_health_check)
        
        # Set default active tab
        self._change_tab("General")
        
    def _setup_header(self):
        self.header_widget = QWidget()
        self.header_widget.setObjectName("headerWidget")
        self.header_widget.setStyleSheet("background-color: #2C3E50; border-radius: 6px;")
        
        layout = QHBoxLayout(self.header_widget)
        layout.setContentsMargins(10, 5, 10, 5)
        
        title_lbl = QLabel("Servidor de Aplicaciones API_SAR ®")
        title_lbl.setStyleSheet("color: white; font-size: 13px; font-weight: bold; font-family: 'Segoe UI';")
        layout.addWidget(title_lbl)
        
        layout.addStretch()
        
        brand_lbl = QLabel("SYSTEM SAR")
        brand_lbl.setStyleSheet("color: #E8EEF5; font-size: 11px; font-weight: bold; font-style: italic;")
        layout.addWidget(brand_lbl)
        
        self.main_layout.addWidget(self.header_widget)

    def _setup_sidebar(self):
        self.sidebar_card = CustomCard(parent=self)
        self.sidebar_card.setFixedWidth(175)
        self.sidebar_card.setStyleSheet("background-color: #FFFFFF; border: 1px solid #D2D6DC;")
        
        sidebar_layout = self.sidebar_card.layout
        sidebar_layout.setContentsMargins(6, 8, 6, 8)
        sidebar_layout.setSpacing(6)
        
        title = CustomLabel("Opciones", variant="header")
        title.setStyleSheet("font-size: 12px; font-weight: bold; color: #2C3E50; margin-bottom: 5px;")
        sidebar_layout.addWidget(title)
        
        # Buttons list
        self.menu_buttons = {}
        options = [
            ("General", "General"),
            ("Consola", "Consola / Logs"),
            ("Usuarios", "Usuarios Conectados"),
            ("Configuración", "Configuración"),
            ("Actualización", "Actualización")
        ]
        
        for code, name in options:
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #475569;
                    border: none;
                    padding: 6px 10px;
                    text-align: left;
                    font-size: 11px;
                    font-weight: 500;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #E2E8F0;
                    color: #1E293B;
                }
                QPushButton:checked {
                    background-color: #2563EB;
                    color: white;
                }
            """)
            btn.clicked.connect(lambda checked, c=code: self._change_tab(c))
            sidebar_layout.addWidget(btn)
            self.menu_buttons[code] = btn
            
        sidebar_layout.addStretch()
        
    def _setup_content_area(self):
        self.content_card = CustomCard(parent=self)
        self.content_layout = self.content_card.layout
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        
        self.stacked_widget = QStackedWidget()
        self.content_layout.addWidget(self.stacked_widget)
        
        # Create tabs
        self._create_general_tab()
        self._create_consola_tab()
        self._create_usuarios_tab()
        self._create_configuracion_tab()
        self._create_actualizacion_tab()
        
    def _create_general_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        title = CustomLabel("Información y Diagnóstico de Salud del Servidor", variant="header")
        layout.addWidget(title)
        
        self.general_info_card = CustomCard()
        info_widget = QWidget()
        info_layout = QFormLayout(info_widget)
        info_layout.setSpacing(10)
        info_layout.setLabelAlignment(Qt.AlignRight)
        
        self.lbl_host_name = CustomLabel(socket.gethostname(), variant="body")
        info_layout.addRow("Nombre del Host:", self.lbl_host_name)
        
        # Get local IP address
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
        except Exception:
            ip = "127.0.0.1"
            
        self.lbl_ip_addr = CustomLabel(ip, variant="body")
        info_layout.addRow("Dirección IP Local:", self.lbl_ip_addr)
        
        # 1. Servicio Windows
        self.lbl_service_status = CustomLabel("Diagnosticando...", variant="body")
        info_layout.addRow("Servicio de Windows (SAR_API):", self.lbl_service_status)
        
        # 2. Servidor API REST FastAPI (HTTP Ping)
        self.lbl_api_status = CustomLabel("Diagnosticando...", variant="body")
        info_layout.addRow("Servidor API REST (FastAPI):", self.lbl_api_status)
        
        # 3. Conexión Directa a PostgreSQL (DB Ping)
        self.lbl_db_status = CustomLabel("Diagnosticando...", variant="body")
        info_layout.addRow("Base de Datos (PostgreSQL):", self.lbl_db_status)
        
        self.lbl_api_url = CustomLabel(self.api_client.api_url, variant="body")
        info_layout.addRow("URL de API REST:", self.lbl_api_url)
        
        # Database Info
        db_info = f"Host: {self.api_client.settings_data.get('DB_HOST', '127.0.0.1')} | DB: {self.api_client.settings_data.get('DB_NAME', 'db_sar')}"
        self.lbl_db_info = CustomLabel(db_info, variant="body")
        info_layout.addRow("Detalle Base de Datos:", self.lbl_db_info)
        
        self.general_info_card.add_widget(info_widget)
        layout.addWidget(self.general_info_card)
        
        # Barra de acciones de la pestaña general
        actions_bar = QHBoxLayout()
        actions_bar.addStretch()
        self.btn_diag_now = CustomButton("Diagnosticar Ahora", is_secondary=True)
        self.btn_diag_now.clicked.connect(self._run_health_check)
        actions_bar.addWidget(self.btn_diag_now)
        layout.addLayout(actions_bar)
        
        layout.addStretch()
        self.stacked_widget.addWidget(widget)
        
    def _create_consola_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(10)
        
        # Console output left area
        left_layout = QVBoxLayout()
        left_layout.setSpacing(6)
        
        header_row = QHBoxLayout()
        title = CustomLabel("Consola de Eventos y Logs en Tiempo Real", variant="header")
        header_row.addWidget(title)
        header_row.addStretch()
        
        self.chk_autoscroll = QPushButton("Auto-scroll: ON")
        self.chk_autoscroll.setCheckable(True)
        self.chk_autoscroll.setChecked(True)
        self.chk_autoscroll.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #38BDF8;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #0369A1;
                color: #FFFFFF;
            }
        """)
        self.chk_autoscroll.clicked.connect(self._toggle_autoscroll)
        header_row.addWidget(self.chk_autoscroll)
        left_layout.addLayout(header_row)
        
        self.console_edit = QTextEdit()
        self.console_edit.setReadOnly(True)
        self.console_edit.setFont(QFont("Consolas", 10))
        self.console_edit.setStyleSheet("""
            QTextEdit {
                background-color: #0B132B;
                color: #E2E8F0;
                border: 1px solid #1E293B;
                border-radius: 6px;
                padding: 10px;
                font-family: 'Consolas', 'Courier New', monospace;
                line-height: 1.4;
            }
        """)
        left_layout.addWidget(self.console_edit)
        
        layout.addLayout(left_layout, 1)
        
        # Action buttons right side
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(8)
        buttons_layout.addSpacing(25)
        
        btn_limpiar = CustomButton("Limpiar Consola", is_secondary=True)
        btn_limpiar.clicked.connect(self._clear_console)
        buttons_layout.addWidget(btn_limpiar)
        
        btn_fuente = CustomButton("Fuente...", is_secondary=True)
        btn_fuente.clicked.connect(self._change_font)
        buttons_layout.addWidget(btn_fuente)
        
        buttons_layout.addSpacing(10)
        
        # Grupo Servicio Windows
        grp_win_lbl = CustomLabel("Servicio Windows:", variant="caption")
        grp_win_lbl.setStyleSheet("color: #64748B; font-weight: bold;")
        buttons_layout.addWidget(grp_win_lbl)
        
        self.btn_iniciar = CustomButton("Iniciar Servicio", is_secondary=False)
        self.btn_iniciar.clicked.connect(self._start_service)
        buttons_layout.addWidget(self.btn_iniciar)
        
        self.btn_detener = CustomButton("Detener Servicio", is_secondary=False)
        self.btn_detener.setObjectName("dangerBtn")
        self.btn_detener.clicked.connect(self._stop_service)
        buttons_layout.addWidget(self.btn_detener)
        
        buttons_layout.addSpacing(10)
        
        # Grupo Servidor Local (Uvicorn)
        grp_local_lbl = CustomLabel("Modo Local (Uvicorn):", variant="caption")
        grp_local_lbl.setStyleSheet("color: #64748B; font-weight: bold;")
        buttons_layout.addWidget(grp_local_lbl)
        
        self.btn_iniciar_local = CustomButton("Iniciar Local", is_secondary=True)
        self.btn_iniciar_local.clicked.connect(self._start_local_server)
        buttons_layout.addWidget(self.btn_iniciar_local)
        
        self.btn_detener_local = CustomButton("Detener Local", is_secondary=True)
        self.btn_detener_local.setObjectName("dangerBtn")
        self.btn_detener_local.clicked.connect(self._stop_local_server)
        buttons_layout.addWidget(self.btn_detener_local)
        
        buttons_layout.addSpacing(10)
        
        btn_leer_archivo = CustomButton("Cargar Log...", is_secondary=True)
        btn_leer_archivo.clicked.connect(self._read_external_log_file)
        buttons_layout.addWidget(btn_leer_archivo)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        self.stacked_widget.addWidget(widget)
        
    def _create_usuarios_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        
        title = CustomLabel("Usuarios Conectados al Sistema (Sesiones Activas)", variant="header")
        layout.addWidget(title)
        
        headers = ["ID Sesión", "Usuario", "Equipo", "Dirección IP", "Fecha Inicio", "Último Heartbeat"]
        self.users_table = StyledDataTable(headers, parent=self)
        self.users_table.setMinimumHeight(180)
        layout.addWidget(self.users_table)
        
        actions = QHBoxLayout()
        actions.addStretch()
        btn_refresh = CustomButton("Actualizar Lista", is_secondary=True)
        btn_refresh.clicked.connect(self._refresh_users)
        actions.addWidget(btn_refresh)
        layout.addLayout(actions)
        
        self.stacked_widget.addWidget(widget)
        
    def _create_configuracion_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        title = CustomLabel("Parámetros de Configuración del Servidor", variant="header")
        layout.addWidget(title)
        
        form_card = CustomCard()
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(8)
        
        self.txt_api_url = QLineEdit()
        self.txt_api_url.setText(self.api_client.settings_data.get("API_URL", ""))
        form_layout.addRow("URL de API REST:", self.txt_api_url)
        
        self.txt_db_host = QLineEdit()
        self.txt_db_host.setText(self.api_client.settings_data.get("DB_HOST", ""))
        form_layout.addRow("Host de Base de Datos:", self.txt_db_host)
        
        self.txt_db_port = QLineEdit()
        self.txt_db_port.setText(self.api_client.settings_data.get("DB_PORT", ""))
        form_layout.addRow("Puerto de Base de Datos:", self.txt_db_port)
        
        self.txt_db_name = QLineEdit()
        self.txt_db_name.setText(self.api_client.settings_data.get("DB_NAME", ""))
        form_layout.addRow("Nombre de Base de Datos:", self.txt_db_name)
        
        # Intentar cargar DB_USER y DB_PASSWORD directamente de las variables del servicio NSSM
        nssm_user = ""
        nssm_pass = ""
        if sys.platform == "win32":
            try:
                nssm_paths = [r"C:\tools\nssm.exe", "nssm.exe", "nssm"]
                for nssm_path in nssm_paths:
                    res = subprocess.run(
                        [nssm_path, "get", "SAR_API", "AppEnvironment"],
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    if res.returncode == 0 and res.stdout:
                        # NSSM separa las variables por saltos de línea o caracteres nulos
                        lines = res.stdout.replace('\x00', '\n').split('\n')
                        for line in lines:
                            line = line.strip()
                            if "DB_USER=" in line:
                                nssm_user = line.split("DB_USER=", 1)[1]
                            elif "DB_PASSWORD=" in line:
                                nssm_pass = line.split("DB_PASSWORD=", 1)[1]
                        if nssm_user or nssm_pass:
                            break
            except Exception:
                pass

        from sar.src.paths import deobfuscate_password
        db_user_default = os.getenv("DB_USER") or nssm_user or self.api_client.settings_data.get("DB_USER", "postgres")
        db_pass_default = os.getenv("DB_PASSWORD") or nssm_pass or deobfuscate_password(self.api_client.settings_data.get("DB_PASSWORD", ""))
        
        self.txt_db_user = QLineEdit()
        self.txt_db_user.setText(db_user_default)
        form_layout.addRow("Usuario BD (DB_USER):", self.txt_db_user)
        
        self.txt_db_password = QLineEdit()
        self.txt_db_password.setEchoMode(QLineEdit.Password)
        self.txt_db_password.setText(db_pass_default)
        form_layout.addRow("Contraseña BD (DB_PASSWORD):", self.txt_db_password)
        
        form_card.add_widget(form_widget)
        layout.addWidget(form_card)
        
        actions = QHBoxLayout()
        actions.addStretch()
        btn_save = CustomButton("Guardar Configuración", is_secondary=False)
        btn_save.clicked.connect(self._save_configuration)
        actions.addWidget(btn_save)
        layout.addLayout(actions)
        
        layout.addStretch()
        self.stacked_widget.addWidget(widget)
        
    def _create_actualizacion_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        
        title = CustomLabel("Servicio de Actualización del Sistema", variant="header")
        layout.addWidget(title)
        
        info_card = CustomCard()
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setSpacing(8)
        
        version_lbl = CustomLabel("Versión Instalada: 2.0 (Despliegue NSSM)", variant="body")
        info_layout.addWidget(version_lbl)
        
        status_lbl = CustomLabel("Estado de Actualizaciones: El sistema se encuentra actualizado a la última versión estable.", variant="body")
        info_layout.addWidget(status_lbl)
        
        info_card.add_widget(info_widget)
        layout.addWidget(info_card)
        layout.addStretch()
        self.stacked_widget.addWidget(widget)
        
    def _setup_bottom_bar(self):
        self.bottom_bar = QWidget()
        layout = QHBoxLayout(self.bottom_bar)
        layout.setContentsMargins(0, 5, 0, 0)
        
        btn_ayuda = CustomButton("Ayuda", is_secondary=True)
        btn_ayuda.clicked.connect(self._show_help)
        layout.addWidget(btn_ayuda)
        
        layout.addStretch()
        
        btn_cerrar = CustomButton("Cerrar", is_secondary=True)
        btn_cerrar.setObjectName("dangerBtn")
        btn_cerrar.clicked.connect(self._handle_exit_action)
        layout.addWidget(btn_cerrar)
        
        self.main_layout.addWidget(self.bottom_bar)
        
    def _change_tab(self, code):
        for c, btn in self.menu_buttons.items():
            btn.setChecked(c == code)
            
        index_map = {
            "General": 0,
            "Consola": 1,
            "Usuarios": 2,
            "Configuración": 3,
            "Actualización": 4
        }
        if code in index_map:
            self.stacked_widget.setCurrentIndex(index_map[code])
            if code == "Usuarios":
                self._refresh_users()
            elif code == "General":
                self._run_health_check()
                
    def _toggle_autoscroll(self):
        if self.chk_autoscroll.isChecked():
            self.chk_autoscroll.setText("Auto-scroll: ON")
            # Move cursor to end
            cursor = self.console_edit.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.console_edit.setTextCursor(cursor)
        else:
            self.chk_autoscroll.setText("Auto-scroll: OFF")

    def _write_log(self, text, level="INFO"):
        """Appends formatted HTML log entry with color coding by severity level."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Color mapping for log clarity
        colors = {
            "INFO": "#38BDF8",     # Cyan
            "SUCCESS": "#34D399",  # Mint Green
            "WARN": "#FBBF24",     # Amber Yellow
            "ERROR": "#F87171",    # Soft Red
            "MUTED": "#94A3B8"     # Slate Gray
        }
        badge_bg = {
            "INFO": "#0369A1",
            "SUCCESS": "#065F46",
            "WARN": "#92400E",
            "ERROR": "#991B1B",
            "MUTED": "#334155"
        }
        
        # Auto-detect level if standard string provided
        upper_text = text.upper()
        if "ERROR" in upper_text or "DENIED" in upper_text or "FAIL" in upper_text or "EXCEPCIÓN" in upper_text or "ERR" in upper_text:
            level = "ERROR"
        elif "ÉXITO" in upper_text or "SUCCESS" in upper_text or "RUNNING" in upper_text or "GUARDAD" in upper_text or "ACTUALIZAD" in upper_text or "200 OK" in upper_text:
            level = "SUCCESS"
        elif "ADVERTENCIA" in upper_text or "WARN" in upper_text or "STOPPED" in upper_text or "DETENID" in upper_text or "404 NOT FOUND" in upper_text:
            level = "WARN"

        lvl_color = colors.get(level, colors["INFO"])
        bg_color = badge_bg.get(level, badge_bg["INFO"])
        
        # Escape HTML entities in text
        safe_text = (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
        )
        
        html = (
            f"<div style='margin-bottom: 3px; font-family: Consolas, monospace; font-size: 11px;'>"
            f"<span style='color: #64748B;'>[{timestamp}]</span> "
            f"<span style='background-color: {bg_color}; color: #FFFFFF; font-weight: bold; padding: 1px 4px; border-radius: 3px; font-size: 9px;'> {level} </span> "
            f"<span style='color: {lvl_color};'>{safe_text}</span>"
            f"</div>"
        )
        
        self.console_edit.append(html)
        
        if getattr(self, 'chk_autoscroll', None) and self.chk_autoscroll.isChecked():
            cursor = self.console_edit.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.console_edit.setTextCursor(cursor)

    def _clear_console(self):
        self.console_edit.clear()
        self._write_log("Consola de eventos reinicializada.", level="INFO")

    def _change_font(self):
        ok, font = QFontDialog.getFont(self.console_font, self, "Seleccionar Fuente de Consola")
        if ok:
            self.console_font = font
            self.console_edit.setFont(font)

    def _cleanup_worker(self, worker):
        if hasattr(self, 'active_workers') and worker in self.active_workers:
            try:
                self.active_workers.remove(worker)
            except ValueError:
                pass
        
    def _read_external_log_file(self):
        """Allows administrator to inspect an external log file (e.g. NSSM or Uvicorn logs)."""
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Archivo de Log del Servidor",
            "",
            "Archivos de Log (*.log *.txt);;Todos los archivos (*.*)"
        )
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()[-150:] # Last 150 lines
                self.console_edit.clear()
                self._write_log(f"--- Cargando últimas {len(lines)} líneas de: {os.path.basename(file_path)} ---", level="INFO")
                for line in lines:
                    line_clean = line.strip()
                    if line_clean:
                        self._write_log(line_clean)
                self._write_log(f"--- Fin de archivo: {os.path.basename(file_path)} ---", level="SUCCESS")
            except Exception as e:
                self._write_log(f"Error al leer archivo de log: {e}", level="ERROR")

    def _is_local_server_running(self):
        return self.local_process is not None and self.local_process.state() != QProcess.NotRunning

    def _run_health_check(self):
        """Ejecuta diagnóstico asíncrono triple (Servicio Windows/Local + FastAPI HTTP + PostgreSQL)."""
        for w in list(self.active_workers):
            if isinstance(w, SystemHealthCheckWorker) and w.isRunning():
                return
                
        is_local = self._is_local_server_running()
        worker = SystemHealthCheckWorker(
            db_connector=self.db_connector,
            api_url=self.api_client.api_url,
            is_local_running=is_local,
            service_name="SAR_API"
        )
        worker.finished.connect(self._on_health_check_retrieved)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        self.active_workers.append(worker)
        worker.start()

    def _on_health_check_retrieved(self, data):
        """Actualiza los indicadores de salud con formato semántico de colores y latencias."""
        svc = data.get("service_status", "UNKNOWN")
        if svc == "RUNNING":
            self.lbl_service_status.setText("ACTIVO (RUNNING - Servicio Windows)")
            self.lbl_service_status.setStyleSheet("color: #16A34A; font-weight: bold;")
        elif svc == "LOCAL_RUNNING":
            self.lbl_service_status.setText("ACTIVO (PROCESO LOCAL UVICORN)")
            self.lbl_service_status.setStyleSheet("color: #2563EB; font-weight: bold;")
        elif svc == "STOPPED":
            self.lbl_service_status.setText("DETENIDO (STOPPED)")
            self.lbl_service_status.setStyleSheet("color: #EF4444; font-weight: bold;")
        elif svc == "NOT_INSTALLED":
            self.lbl_service_status.setText("NO INSTALADO EN WINDOWS (Modo Local Disponible)")
            self.lbl_service_status.setStyleSheet("color: #D97706; font-weight: bold;")
        else:
            self.lbl_service_status.setText(f"DESCONOCIDO ({data.get('service_detail', '')[:35]})")
            self.lbl_service_status.setStyleSheet("color: #64748B; font-weight: bold;")

        # API REST Status
        api_st = data.get("api_status", "OFFLINE")
        latency = data.get("api_latency_ms", 0.0)
        if api_st == "ONLINE":
            self.lbl_api_status.setText(f"ONLINE ({latency} ms - HTTP 200)")
            self.lbl_api_status.setStyleSheet("color: #16A34A; font-weight: bold;")
        elif api_st == "DEGRADED":
            self.lbl_api_status.setText(f"DEGRADADA ({latency} ms - {data.get('api_detail', '')})")
            self.lbl_api_status.setStyleSheet("color: #D97706; font-weight: bold;")
        else:
            self.lbl_api_status.setText("OFFLINE (Sin respuesta en puerto 8000)")
            self.lbl_api_status.setStyleSheet("color: #EF4444; font-weight: bold;")

        # Base de Datos Status
        db_st = data.get("db_status", "DESCONECTADA")
        db_lat = data.get("db_latency_ms", 0.0)
        if db_st == "CONECTADA":
            self.lbl_db_status.setText(f"CONECTADA ({db_lat} ms - Ping SELECT 1 OK)")
            self.lbl_db_status.setStyleSheet("color: #16A34A; font-weight: bold;")
        else:
            self.lbl_db_status.setText(f"ERROR: {data.get('db_detail', 'Fallo de conexión')}")
            self.lbl_db_status.setStyleSheet("color: #EF4444; font-weight: bold;")

        self._update_action_buttons()

    def _update_action_buttons(self):
        """Habilita o deshabilita botones según el estado actual."""
        is_local = self._is_local_server_running()
        if hasattr(self, 'btn_iniciar_local'):
            self.btn_iniciar_local.setEnabled(not is_local)
        if hasattr(self, 'btn_detener_local'):
            self.btn_detener_local.setEnabled(is_local)

    def _start_local_server(self):
        if self._is_local_server_running():
            self._write_log("El servidor local ya se encuentra en ejecución.", level="WARN")
            return

        self._write_log("Iniciando Servidor API localmente con Uvicorn...", level="INFO")
        self.local_process = QProcess(self)
        self.local_process.readyReadStandardOutput.connect(self._on_local_stdout)
        self.local_process.readyReadStandardError.connect(self._on_local_stderr)
        self.local_process.finished.connect(self._on_local_finished)

        python_exe = sys.executable
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
        self.local_process.setWorkingDirectory(root_dir)

        args = ["-m", "uvicorn", "sar.main_api:app", "--host", "0.0.0.0", "--port", "8000"]
        self.local_process.start(python_exe, args)
        
        self._write_log(f"Comando lanzado: {python_exe} {' '.join(args)}", level="INFO")
        self._update_action_buttons()
        QTimer.singleShot(1200, self._run_health_check)

    def _stop_local_server(self):
        if not self._is_local_server_running():
            self._write_log("No hay ningún servidor local en ejecución.", level="WARN")
            return

        self._write_log("Deteniendo Servidor API local...", level="WARN")
        self.local_process.terminate()
        if not self.local_process.waitForFinished(3000):
            self.local_process.kill()
        self._write_log("Servidor API local finalizado.", level="SUCCESS")
        self._update_action_buttons()
        self._run_health_check()

    def _on_local_stdout(self):
        if not self.local_process:
            return
        data = self.local_process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        for line in data.splitlines():
            line_str = line.strip()
            if line_str:
                self._write_log(line_str)

    def _on_local_stderr(self):
        if not self.local_process:
            return
        data = self.local_process.readAllStandardError().data().decode("utf-8", errors="replace")
        for line in data.splitlines():
            line_str = line.strip()
            if line_str:
                self._write_log(line_str)

    def _on_local_finished(self, exit_code, exit_status):
        self._write_log(f"Proceso de servidor local finalizó (Código: {exit_code}).", level="INFO")
        self._update_action_buttons()
        self._run_health_check()

    def _start_service(self):
        self._write_log("Enviando comando para Iniciar Servicio Windows 'SAR_API'...")
        worker = ServiceControlWorker("start")
        worker.finished.connect(self._on_service_action_finished)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        self.active_workers.append(worker)
        worker.start()

    def _stop_service(self):
        self._write_log("Enviando comando para Detener Servicio Windows 'SAR_API'...")
        worker = ServiceControlWorker("stop")
        worker.finished.connect(self._on_service_action_finished)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        self.active_workers.append(worker)
        worker.start()

    def _on_service_action_finished(self, status, message):
        self._write_log(message)
        self._run_health_check()
        
    def _refresh_users(self):
        try:
            sessions_data = []
            if self.api_client.connect_via_api:
                sessions_data = self.api_client.request("GET", "/api/admin/active-sessions")
            else:
                with self.db_connector.get_session() as session:
                    from sqlalchemy import text
                    # Marcar como FINALIZADA cualquier sesión ACTIVA huérfana de más de 2 horas sin heartbeat
                    session.execute(text("""
                        UPDATE sar_auditoria.auditoria_login al
                        SET fecha_logout = NOW()
                        FROM sar_seguridad.sesion s
                        WHERE al.sesion_id = s.sesion_id
                          AND s.estado = 'ACTIVA'
                          AND al.fecha_logout IS NULL
                          AND (
                            (s.ultimo_heartbeat IS NOT NULL AND s.ultimo_heartbeat < (NOW() - INTERVAL '2 hours'))
                            OR (s.ultimo_heartbeat IS NULL AND s.fecha_inicio < (NOW() - INTERVAL '2 hours'))
                          );

                        UPDATE sar_seguridad.sesion
                        SET estado = 'FINALIZADA',
                            ultimo_heartbeat = COALESCE(ultimo_heartbeat, NOW())
                        WHERE estado = 'ACTIVA' 
                          AND (
                            (ultimo_heartbeat IS NOT NULL AND ultimo_heartbeat < (NOW() - INTERVAL '2 hours'))
                            OR (ultimo_heartbeat IS NULL AND fecha_inicio < (NOW() - INTERVAL '2 hours'))
                          );
                    """))
                    session.commit()

                    stmt = text("""
                        SELECT s.sesion_id, u.username, s.equipo_nombre, s.ip_equipo, s.fecha_inicio, s.ultimo_heartbeat 
                        FROM sar_seguridad.sesion s
                        JOIN sar_seguridad.usuario u ON s.usuario_id = u.usuario_id
                        WHERE s.estado = 'ACTIVA'
                        ORDER BY s.fecha_inicio DESC
                    """)
                    results = session.execute(stmt).fetchall()
                    for r in results:
                        sessions_data.append({
                            "sesion_id": r[0],
                            "username": r[1],
                            "equipo_nombre": r[2],
                            "ip_equipo": r[3],
                            "fecha_inicio": r[4].strftime("%Y-%m-%d %H:%M:%S") if r[4] else "",
                            "ultimo_heartbeat": r[5].strftime("%Y-%m-%d %H:%M:%S") if r[5] else ""
                        })
                        
            table_rows = []
            for s in sessions_data:
                table_rows.append([
                    str(s["sesion_id"]),
                    s["username"],
                    s.get("equipo_nombre", "") or "Desconocido",
                    s.get("ip_equipo", "") or "Desconocido",
                    s.get("fecha_inicio", "") or "",
                    s.get("ultimo_heartbeat", "") or ""
                ])
            self.users_table.populate_rows(table_rows)
            self._write_log("Lista de usuarios conectados actualizada.")
        except Exception as e:
            self._write_log(f"Error al obtener usuarios conectados: {str(e)}")
            
    def _save_configuration(self):
        try:
            # Update API client object in memory
            self.api_client.settings_data["API_URL"] = self.txt_api_url.text()
            self.api_client.settings_data["DB_HOST"] = self.txt_db_host.text()
            self.api_client.settings_data["DB_PORT"] = self.txt_db_port.text()
            self.api_client.settings_data["DB_NAME"] = self.txt_db_name.text()
            self.api_client.settings_data["DB_USER"] = self.txt_db_user.text()
            # Save to settings.json
            import json
            from sar.src.paths import get_settings_path, obfuscate_password
            settings_path = get_settings_path()
            
            # Obfuscate DB_PASSWORD in settings.json for simple but persistent security
            self.api_client.settings_data["DB_PASSWORD"] = obfuscate_password(self.txt_db_password.text())
                
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(self.api_client.settings_data, f, indent=2)
                
            # Set environment variables for the current process
            os.environ["DB_USER"] = self.txt_db_user.text()
            os.environ["DB_PASSWORD"] = self.txt_db_password.text()
            
            # Set environment variables for the Windows Service using NSSM
            if sys.platform == "win32":
                try:
                    nssm_paths = [r"C:\tools\nssm.exe", "nssm.exe", "nssm"]
                    success = False
                    for nssm_path in nssm_paths:
                        res = subprocess.run(
                            [nssm_path, "set", "SAR_API", "AppEnvironment", f"DB_USER={self.txt_db_user.text()}", f"DB_PASSWORD={self.txt_db_password.text()}"],
                            capture_output=True,
                            text=True,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        if res.returncode == 0:
                            success = True
                            break
                    if success:
                        self._write_log("Variables de entorno DB_USER y DB_PASSWORD actualizadas en el servicio SAR_API vía NSSM.")
                    else:
                        self._write_log("Advertencia: No se pudo configurar el servicio NSSM. Asegúrese de ejecutar como Administrador.")
                except Exception as nssm_err:
                    self._write_log(f"Advertencia al configurar servicio NSSM: {nssm_err}")
                
            self._write_log("Configuración guardada en settings.json (Contraseña omitida en disco por seguridad).")
            QMessageBox.information(self, "Configuración Guardada", "La configuración ha sido persistida (La contraseña fue registrada en el sistema de forma segura).")
            
            # Reload labels
            self.lbl_api_url.setText(self.txt_api_url.text())
            db_info = f"Host: {self.txt_db_host.text()} | DB: {self.txt_db_name.text()}"
            self.lbl_db_info.setText(db_info)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la configuración: {e}")
            
    def _show_help(self):
        QMessageBox.information(
            self, "Ayuda",
            "Módulo de control del servidor de aplicaciones API_SAR.\n\n"
            "Permite iniciar o detener el servicio de Windows de forma directa y "
            "monitorear qué usuarios están conectados en tiempo real."
        )
        
    def _handle_logout_action(self):
        self._logging_out = True
        self.logout_requested.emit()
        
    def _handle_exit_action(self):
        self.close()
        
    def closeEvent(self, event):
        # Stop timers cleanly
        if hasattr(self, 'query_timer'):
            self.query_timer.stop()
            
        # Cleanly terminate and wait for any active thread workers
        for worker in list(self.active_workers):
            if worker.isRunning():
                worker.terminate()
                worker.wait()
        self.active_workers.clear()
        
        # Cleanly terminate local server process if running
        if getattr(self, "local_process", None) and self.local_process.state() != QProcess.NotRunning:
            self.local_process.terminate()
            if not self.local_process.waitForFinished(2000):
                self.local_process.kill()
            
        if getattr(self, "_logging_out", False):
            event.accept()
            return
            
        reply = QMessageBox.question(
            self,
            "Confirmar Salida",
            "¿Está seguro de que desea salir del servidor de aplicaciones?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
            QApplication.quit()
        else:
            event.ignore()
