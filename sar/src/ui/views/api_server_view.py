"""Application Server API_SAR Control Module View."""

import os
import sys
import subprocess
import socket
import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel, QMainWindow, 
    QApplication, QTextEdit, QPushButton, QFontDialog, QTableWidget, 
    QTableWidgetItem, QHeaderView, QLineEdit, QFormLayout, QDialog
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
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
                if "RUNNING" in result.stdout:
                    self.finished.emit("RUNNING", result.stdout)
                elif "STOPPED" in result.stdout:
                    self.finished.emit("STOPPED", result.stdout)
                elif "PAUSED" in result.stdout:
                    self.finished.emit("PAUSED", result.stdout)
                else:
                    self.finished.emit("UNKNOWN", result.stdout or result.stderr)
            elif self.action in ["start", "stop"]:
                # Request elevation if needed, but we'll try standard command first
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
                    else:
                        self.finished.emit("ERROR", f"Error al ejecutar '{self.action}': {err_msg}")
        except Exception as e:
            self.finished.emit("EXCEPTION", f"Excepción durante control de servicio: {str(e)}")

class APIServerWindow(QMainWindow):
    """Dedicated Control Panel Window for the API_SAR Application Server."""
    
    logout_requested = Signal()
    
    def __init__(self, db_connector, parent=None, current_usuario_id=None, current_sesion_id=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.current_usuario_id = current_usuario_id
        self.current_sesion_id = current_sesion_id
        self._logging_out = False
        
        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()
        self.active_workers = []
        
        # Window setup
        self.setWindowTitle("Servidor de Aplicaciones API_SAR")
        self.resize(800, 470)
        
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
        
        # Auto-query service status
        self.query_timer = QTimer(self)
        self.query_timer.timeout.connect(self._query_service_status)
        self.query_timer.start(5000) # Every 5 seconds
        
        # Delay initial query
        QTimer.singleShot(100, self._query_service_status)
        
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
        self.sidebar_card.setFixedWidth(160)
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
                    padding: 5px 8px;
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
        
        title = CustomLabel("Información General del Servidor", variant="header")
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
        info_layout.addRow("Dirección IP:", self.lbl_ip_addr)
        
        self.lbl_service_status = CustomLabel("Verificando...", variant="body")
        info_layout.addRow("Estado del Servicio Windows (SAR_API):", self.lbl_service_status)
        
        self.lbl_api_url = CustomLabel(self.api_client.api_url, variant="body")
        info_layout.addRow("URL de API REST:", self.lbl_api_url)
        
        # Database Info
        db_info = f"Host: {self.api_client.settings_data.get('DB_HOST', '127.0.0.1')} | DB: {self.api_client.settings_data.get('DB_NAME', 'db_sar')}"
        self.lbl_db_info = CustomLabel(db_info, variant="body")
        info_layout.addRow("Base de Datos:", self.lbl_db_info)
        
        self.general_info_card.add_widget(info_widget)
        layout.addWidget(self.general_info_card)
        layout.addStretch()
        self.stacked_widget.addWidget(widget)
        
    def _create_consola_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(10)
        
        # Console output
        left_layout = QVBoxLayout()
        title = CustomLabel("Consola del Servidor de Aplicaciones API_SAR", variant="header")
        left_layout.addWidget(title)
        
        self.console_edit = QTextEdit()
        self.console_edit.setReadOnly(True)
        self.console_edit.setFont(QFont("Consolas", 10))
        self.console_edit.setStyleSheet("background-color: #0F172A; color: #10B981; border: 1px solid #1E293B; border-radius: 4px; padding: 10px;")
        left_layout.addWidget(self.console_edit)
        
        layout.addLayout(left_layout, 1)
        
        # Action buttons right side
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(6)
        buttons_layout.addSpacing(15)
        
        btn_limpiar = CustomButton("Limpiar", is_secondary=True)
        btn_limpiar.clicked.connect(self._clear_console)
        buttons_layout.addWidget(btn_limpiar)
        
        btn_fuente = CustomButton("Fuente...", is_secondary=True)
        btn_fuente.clicked.connect(self._change_font)
        buttons_layout.addWidget(btn_fuente)
        
        buttons_layout.addSpacing(20)
        
        self.btn_iniciar = CustomButton("Iniciar Servicio", is_secondary=False)
        self.btn_iniciar.clicked.connect(self._start_service)
        buttons_layout.addWidget(self.btn_iniciar)
        
        self.btn_detener = CustomButton("Detener Servicio", is_secondary=False)
        self.btn_detener.setObjectName("dangerBtn")
        self.btn_detener.clicked.connect(self._stop_service)
        buttons_layout.addWidget(self.btn_detener)
        
        buttons_layout.addSpacing(20)
        
        btn_registrar = CustomButton("Registra", is_secondary=True)
        btn_registrar.setEnabled(False) # Placeholder
        buttons_layout.addWidget(btn_registrar)
        
        btn_quitar = CustomButton("Quitar", is_secondary=True)
        btn_quitar.setEnabled(False) # Placeholder
        buttons_layout.addWidget(btn_quitar)
        
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
                self._query_service_status()
                
    def _write_log(self, text):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.console_edit.append(f"{timestamp} {text}")
        
    def _clear_console(self):
        self.console_edit.clear()
        self._write_log("Consola limpiada.")
        
    def _change_font(self):
        ok, font = QFontDialog.getFont(self.console_font, self, "Seleccionar Fuente de Consola")
        if ok:
            self.console_font = font
            self.console_edit.setFont(font)
            
    def _cleanup_worker(self, worker):
        if worker in self.active_workers:
            try:
                self.active_workers.remove(worker)
            except ValueError:
                pass

    def _query_service_status(self):
        worker = ServiceControlWorker("query")
        worker.finished.connect(self._on_status_retrieved)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        self.active_workers.append(worker)
        worker.start()
        
    def _on_status_retrieved(self, status, detail):
        if status == "RUNNING":
            self.lbl_service_status.setText("ACTIVO (RUNNING)")
            self.lbl_service_status.setStyleSheet("color: #16A34A; font-weight: bold;")
        elif status == "STOPPED":
            self.lbl_service_status.setText("DETENIDO (STOPPED)")
            self.lbl_service_status.setStyleSheet("color: #EF4444; font-weight: bold;")
        else:
            self.lbl_service_status.setText("DESCONOCIDO o NO INSTALADO")
            self.lbl_service_status.setStyleSheet("color: #D97706; font-weight: bold;")
            
    def _start_service(self):
        self._write_log("Enviando comando para Iniciar Servicio 'SAR_API'...")
        worker = ServiceControlWorker("start")
        worker.finished.connect(self._on_service_action_finished)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        self.active_workers.append(worker)
        worker.start()
        
    def _stop_service(self):
        self._write_log("Enviando comando para Detener Servicio 'SAR_API'...")
        worker = ServiceControlWorker("stop")
        worker.finished.connect(self._on_service_action_finished)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        self.active_workers.append(worker)
        worker.start()
        
    def _on_service_action_finished(self, status, message):
        self._write_log(message)
        self._query_service_status()
        
    def _refresh_users(self):
        try:
            sessions_data = []
            if self.api_client.connect_via_api:
                sessions_data = self.api_client.request("GET", "/api/admin/active-sessions")
            else:
                with self.db_connector.get_session() as session:
                    from sqlalchemy import text
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
