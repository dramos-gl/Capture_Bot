"""Help Dialogs for the SAR Administration Module (Atomic Design)."""

import sys
import platform
import time
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QScrollArea, QTextBrowser, QWidget, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QColor

from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.utils.icons import Icons


class AboutDialog(QDialog):
    """About SAR dialog with branding, build details, and system info."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Acerca de SAR")
        self.setFixedSize(520, 440)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header Card
        header_card = QFrame()
        header_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1E293B, stop:1 #0F172A);
                border-radius: 12px;
                padding: 16px;
            }
        """)
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(12, 12, 12, 12)
        h_layout.setSpacing(16)

        # Logo Icon
        logo_lbl = QLabel()
        logo_lbl.setPixmap(Icons.get_pixmap("seguridad", size=48, color="#38BDF8"))
        logo_lbl.setAlignment(Qt.AlignCenter)
        h_layout.addWidget(logo_lbl)

        # Title & Subtitle
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        
        lbl_app = QLabel("SAR — Sistema de Administración de Referencias")
        lbl_app.setStyleSheet("color: #FFFFFF; font-size: 15px; font-weight: bold;")
        
        lbl_ver = QLabel("Versión 2.5 (Edición Empresarial)")
        lbl_ver.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 600;")

        lbl_desc = QLabel("Plataforma Integral de Captura, Control de Derechos y Automatización")
        lbl_desc.setStyleSheet("color: #94A3B8; font-size: 11px;")
        lbl_desc.setWordWrap(True)

        title_box.addWidget(lbl_app)
        title_box.addWidget(lbl_ver)
        title_box.addWidget(lbl_desc)
        h_layout.addLayout(title_box)

        layout.addWidget(header_card)

        # System Information Table
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(6)
        info_layout.setContentsMargins(8, 8, 8, 8)

        details = [
            ("Arquitectura Core:", "Python 3.12 + PySide6 (Qt 6.7) + SQLAlchemy"),
            ("Motor de Automatización:", "Playwright Headless Bot + OCR Vision"),
            ("Base de Datos:", "PostgreSQL Relacional (SAR Schema v3.0)"),
            ("Sistema Operativo:", f"{platform.system()} {platform.release()} ({platform.machine()})"),
            ("Ambiente:", "LAN Corporativo / Red Local"),
            ("Licencia & Uso:", "Uso Exclusivo Interno — Derechos Reservados")
        ]

        for label, val in details:
            row = QHBoxLayout()
            row.setSpacing(8)
            lbl_k = QLabel(label)
            lbl_k.setStyleSheet("color: #64748B; font-weight: 600; font-size: 11px; min-width: 140px;")
            lbl_v = QLabel(val)
            lbl_v.setStyleSheet("color: #1E293B; font-size: 11px;")
            row.addWidget(lbl_k)
            row.addWidget(lbl_v, stretch=1)
            info_layout.addLayout(row)

        layout.addWidget(info_frame)

        # Footer Actions
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()

        btn_close = CustomButton("Cerrar", is_secondary=True)
        btn_close.clicked.connect(self.accept)
        footer_layout.addWidget(btn_close)

        layout.addLayout(footer_layout)


class ShortcutsDialog(QDialog):
    """Shortcuts overview dialog for power users."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Atajos de Teclado del Sistema")
        self.setFixedSize(580, 480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header_layout = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(Icons.get_pixmap("preferencias", size=24, color="#2563EB"))
        lbl_title = CustomLabel("Guía Rápida de Atajos de Teclado", variant="header")
        header_layout.addWidget(icon_lbl)
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Table of shortcuts
        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Acción / Módulo", "Atajo de Teclado", "Contexto"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                gridline-color: #F1F5F9;
            }
            QHeaderView::section {
                background-color: #F8FAFC;
                font-weight: bold;
                color: #475569;
                border: none;
                border-bottom: 1px solid #CBD5E1;
                padding: 6px;
            }
            QTableWidget::item {
                padding: 4px 8px;
                color: #1E293B;
            }
        """)

        shortcuts_data = [
            ("Abrir Manual de Ayuda", "F1", "Global"),
            ("Ver Atajos de Teclado", "Ctrl + H", "Global"),
            ("Gestión de Usuarios", "Ctrl + 1", "Administración"),
            ("Gestión de Roles", "Ctrl + 2", "Administración"),
            ("Matriz de Permisos", "Ctrl + 3", "Administración"),
            ("Cerrar Sesión", "Ctrl + L", "Global"),
            ("Salir de la Aplicación", "Ctrl + Q", "Global"),
            ("Refrescar Datos de la Grilla", "F5", "Grillas y Tablas"),
            ("Nuevo Registro", "Ctrl + N", "Formularios CRUD"),
            ("Guardar Registro Activo", "Ctrl + S", "Formularios CRUD"),
            ("Cancelar / Cerrar Modal", "Escape", "Diálogos Modales"),
            ("Buscar en Grilla", "Ctrl + F", "Grillas y Tablas")
        ]

        self.table.setRowCount(len(shortcuts_data))
        for row_idx, (action, shortcut, ctx) in enumerate(shortcuts_data):
            item_act = QTableWidgetItem(action)
            
            item_sc = QTableWidgetItem(shortcut)
            item_sc.setTextAlignment(Qt.AlignCenter)
            item_sc.setFont(QFont("Consolas", 10, QFont.Bold))
            item_sc.setForeground(QColor("#2563EB"))

            item_ctx = QTableWidgetItem(ctx)
            item_ctx.setTextAlignment(Qt.AlignCenter)
            item_ctx.setForeground(QColor("#64748B"))

            self.table.setItem(row_idx, 0, item_act)
            self.table.setItem(row_idx, 1, item_sc)
            self.table.setItem(row_idx, 2, item_ctx)

        layout.addWidget(self.table)

        btn_close = CustomButton("Entendido", is_secondary=False)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)


class SystemDiagnosticsDialog(QDialog):
    """Runs live connectivity and health checks for PostgreSQL and SAR system."""

    def __init__(self, db_connector, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.setWindowTitle("Diagnóstico del Sistema y Conectividad")
        self.setFixedSize(620, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._build_ui()
        # Run check on open
        QTimer.singleShot(200, self.run_diagnostics)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header_layout = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(Icons.get_pixmap("actividad", size=24, color="#059669"))
        lbl_title = CustomLabel("Monitor de Diagnóstico y Estado del Servidor", variant="header")
        header_layout.addWidget(icon_lbl)
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Status Summary Card
        self.summary_card = QFrame()
        self.summary_card.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        self.summary_layout = QVBoxLayout(self.summary_card)
        self.summary_layout.setSpacing(8)
        self.lbl_overall = QLabel("Ejecutando pruebas de conectividad...")
        self.lbl_overall.setStyleSheet("font-weight: bold; font-size: 13px; color: #475569;")
        self.summary_layout.addWidget(self.lbl_overall)
        layout.addWidget(self.summary_card)

        # Results Table
        self.results_table = QTableWidget(self)
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Componente / Prueba", "Estado", "Detalle / Latencia"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #F8FAFC;
                font-weight: bold;
                color: #475569;
                border: none;
                border-bottom: 1px solid #CBD5E1;
                padding: 6px;
            }
        """)
        layout.addWidget(self.results_table)

        # Bottom controls
        btn_layout = QHBoxLayout()
        self.btn_retest = CustomButton("Reintentar Diagnóstico", is_secondary=True)
        self.btn_retest.setIcon(Icons.get_icon("actualizar", color="#475569"))
        self.btn_retest.clicked.connect(self.run_diagnostics)
        btn_layout.addWidget(self.btn_retest)

        btn_layout.addStretch()

        btn_close = CustomButton("Cerrar", is_secondary=False)
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def run_diagnostics(self):
        """Executes actual diagnostics queries."""
        self.lbl_overall.setText("Evaluando componentes del sistema...")
        self.lbl_overall.setStyleSheet("font-weight: bold; font-size: 13px; color: #2563EB;")
        self.results_table.setRowCount(0)

        checks = []

        # 1. Base de datos PostgreSQL
        try:
            t0 = time.perf_counter()
            with self.db_connector.get_session() as session:
                from sqlalchemy import text
                version_res = session.execute(text("SHOW server_version;")).scalar()
                db_name = session.execute(text("SELECT current_database();")).scalar()
                user_name = session.execute(text("SELECT current_user;")).scalar()
                latency_ms = round((time.perf_counter() - t0) * 1000, 1)
                
                checks.append((
                    "Base de Datos PostgreSQL",
                    "🟢 ONLINE",
                    f"DB: '{db_name}' | Usuario: '{user_name}' | Latencia: {latency_ms} ms | Ver: {version_res}"
                ))
        except Exception as e:
            checks.append((
                "Base de Datos PostgreSQL",
                "🔴 ERROR",
                f"No se pudo conectar: {str(e)[:90]}"
            ))

        # 2. Esquemas SAR
        try:
            with self.db_connector.get_session() as session:
                from sqlalchemy import text
                schema_cnt = session.execute(text(
                    "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name IN ('sar_seguridad', 'sar_catalogo', 'sar_referencia', 'sar_configuracion', 'sar_auditoria');"
                )).scalar()
                
                if schema_cnt >= 5:
                    checks.append(("Esquemas Relacionales SAR", "🟢 OK", f"5/5 Esquemas verificados e íntegros."))
                else:
                    checks.append(("Esquemas Relacionales SAR", "🟡 INCOMPLETO", f"{schema_cnt}/5 Esquemas encontrados."))
        except Exception as e:
            checks.append(("Esquemas Relacionales SAR", "🔴 ERROR", str(e)[:90]))

        # 3. Motor de UI / Python
        checks.append((
            "Entorno de Ejecución",
            "🟢 OK",
            f"Python {platform.python_version()} | Qt 6.7 / PySide6 | SO: {platform.system()}"
        ))

        # 4. Modo de Conexión
        from sar.src.storage.api_client import APIClient
        client = APIClient()
        if client.connect_via_api:
            checks.append(("Modo de Comunicación", "🌐 API REST", f"URL Base: {client.base_url}"))
        else:
            checks.append(("Modo de Comunicación", "⚡ Conexión Directa DB", "SQLAlchemy ORM + Connection Pooling"))

        # Populate table
        self.results_table.setRowCount(len(checks))
        has_error = False
        for row, (comp, status, detail) in enumerate(checks):
            it_comp = QTableWidgetItem(comp)
            it_stat = QTableWidgetItem(status)
            it_det = QTableWidgetItem(detail)

            if "ERROR" in status:
                has_error = True
                it_stat.setForeground(QColor("#DC2626"))
            elif "ONLINE" in status or "OK" in status:
                it_stat.setForeground(QColor("#059669"))
            else:
                it_stat.setForeground(QColor("#D97706"))

            self.results_table.setItem(row, 0, it_comp)
            self.results_table.setItem(row, 1, it_stat)
            self.results_table.setItem(row, 2, it_det)

        if has_error:
            self.lbl_overall.setText("⚠️ Se detectaron problemas en las pruebas de diagnóstico.")
            self.lbl_overall.setStyleSheet("font-weight: bold; font-size: 13px; color: #DC2626;")
        else:
            self.lbl_overall.setText("✅ Todos los servicios y conexiones operan correctamente.")
            self.lbl_overall.setStyleSheet("font-weight: bold; font-size: 13px; color: #059669;")


class SupportDialog(QDialog):
    """Technical support and helpdesk contact dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mesa de Ayuda y Soporte Técnico")
        self.setFixedSize(520, 380)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(Icons.get_pixmap("soporte", size=28, color="#2563EB"))
        lbl_title = CustomLabel("Mesa de Ayuda y Soporte Técnico", variant="header")
        header_layout.addWidget(icon_lbl)
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        info_items = [
            ("🎧 Atención Nivel 1 y 2:", "Soporte Operativo & Automatización SAR"),
            ("📧 Correo de Contacto:", "soporte.sar@empresa.local / dramos@empresa.local"),
            ("⏰ Horario de Soporte:", "Lunes a Viernes de 08:00 a 18:00 hrs"),
            ("📋 Reporte de Incidentes:", "Al reportar una falla, indique el usuario, módulo y la hora exacta del evento."),
            ("📁 Archivos de Registro:", "Los archivos de bitácora se generan en el directorio local logs/")
        ]

        for title, val in info_items:
            row = QVBoxLayout()
            row.setSpacing(2)
            lbl_t = QLabel(title)
            lbl_t.setStyleSheet("font-weight: bold; color: #1E293B; font-size: 11px;")
            lbl_v = QLabel(val)
            lbl_v.setStyleSheet("color: #475569; font-size: 11px;")
            lbl_v.setWordWrap(True)
            row.addWidget(lbl_t)
            row.addWidget(lbl_v)
            card_layout.addLayout(row)

        layout.addWidget(card)

        btn_close = CustomButton("Aceptar", is_secondary=False)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)


class UserManualDialog(QDialog):
    """Interactive User and Administrator Guide dialog with categorized topics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manual de Administración y Guía de Operación")
        self.resize(780, 560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(Icons.get_pixmap("documento_abrir", size=24, color="#2563EB"))
        lbl_title = CustomLabel("Guía Operativa y Manual del Módulo de Administración", variant="header")
        header_layout.addWidget(icon_lbl)
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Tab widget for manual sections
        self.tabs = QTabWidget(self)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                background-color: #FFFFFF;
                padding: 12px;
            }
            QTabBar::tab {
                background: #F1F5F9;
                color: #475569;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 600;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                color: #2563EB;
                border-bottom: 2px solid #2563EB;
            }
        """)

        manual_topics = [
            ("1. Seguridad y Accesos", """
                <h3 style='color: #1E293B;'>Gestión de Usuarios, Roles y Permisos</h3>
                <p>El esquema <code>sar_seguridad</code> controla quién ingresa al sistema y qué acciones puede realizar.</p>
                <ul>
                    <li><b>Gestión de Usuarios:</b> Permite crear usuarios, modificar nombre/correo, asignar roles y cambiar contraseñas. Para desactivar a un operador, desmarque la casilla <i>Usuario Activo</i> (baja lógica).</li>
                    <li><b>Gestión de Roles:</b> Asigna qué módulos de aplicación puede ver cada perfil de usuario.</li>
                    <li><b>Matriz de Permisos:</b> Configura el cruce granular entre Roles, Módulos y Acciones (<i>LEER, CREAR, EDITAR, DESACTIVAR</i>).</li>
                </ul>
            """),
            ("2. Catálogos Base", """
                <h3 style='color: #1E293B;'>Administración de Catálogos de Negocio y Geografía</h3>
                <ul>
                    <li><b>Catálogos de Negocio:</b> Gestiona <i>Conceptos</i> (códigos de pago y referencias), <i>Notarías</i>, <i>Colaboradores</i> y <i>Desarrollos con sus RFCs asociados</i>.</li>
                    <li><b>Geografía Operativa:</b> Municipios y Delegaciones. Las delegaciones están vinculadas a su municipio correspondiente y soportan el <code>codigo_portal</code> necesario para la automatización del Bot.</li>
                    <li><b>Contribuyentes (RFC):</b> Registra empresas y personas físicas con su domicilio fiscal completo.</li>
                    <li><b>Estados del Sistema:</b> Define los estados transaccionales válidos (<i>PENDIENTE, CAPTURADO, FACTURADO</i>, etc.).</li>
                </ul>
            """),
            ("3. Configuración Core", """
                <h3 style='color: #1E293B;'>Parámetros Globales y Selectores del Bot</h3>
                <ul>
                    <li><b>Parámetros del Sistema:</b> Controla variables globales de operación como tamaños de lote (<code>TAMANO_LOTE</code>), timeouts y límites operativos.</li>
                    <li><b>Localizadores del Motor Bot:</b> Selectores Playwright dinámicos (XPath / CSS) para interactuar con los portales web gubernamentales o bancarios sin necesidad de recompilar la aplicación.</li>
                </ul>
            """),
            ("4. Procesos Especiales", """
                <h3 style='color: #1E293B;'>Herramientas de Carga, Migración y Auditoría</h3>
                <ul>
                    <li><b>Carga Masiva de Referencias:</b> Importación estructurada desde archivos Excel/CSV con validación automática de duplicados.</li>
                    <li><b>Migración de Referencias:</b> Sincronización entre bases de datos legadas y el esquema SAR v3.0.</li>
                    <li><b>Reserva Masiva:</b> Bloqueo controlado de folios de referencias para proyectos o empresas específicas.</li>
                    <li><b>Escaneo de Facturas (PDF):</b> Extracción automática de delegaciones y montos desde documentos PDF de facturas.</li>
                </ul>
            """)
        ]

        for tab_name, html_content in manual_topics:
            browser = QTextBrowser()
            browser.setHtml(f"""
                <div style='font-family: Segoe UI, sans-serif; font-size: 13px; line-height: 1.6; color: #334155;'>
                    {html_content}
                </div>
            """)
            browser.setStyleSheet("border: none; background: transparent;")
            self.tabs.addTab(browser, tab_name)

        layout.addWidget(self.tabs)

        btn_close = CustomButton("Cerrar Guía", is_secondary=False)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)
