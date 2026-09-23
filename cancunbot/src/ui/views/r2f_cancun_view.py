"""
R2F-Cancún — Unified Dashboard View (Standalone Window)
Permite gestionar la descarga de Recibos y la posterior generación de Facturas
en una interfaz unificada mediante un interruptor de modo (CustomSwitch).
"""
import datetime
import os
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QFrame, QLabel, QPushButton, QTextEdit, 
    QProgressBar, QMenu, QFileDialog, QTabWidget, QDialog
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QCursor

# Reutilizar componentes del Design System del SAR
from sar.src.ui.design_system.components import (
    CustomCard, StyledDataTable, CustomButton, CustomLabel, 
    CustomCheckBox, CustomSwitch, MetricBox,
    GLMessageDialog, DialogType,
    GLMessageBox as QMessageBox
)
from sar.src.ui.design_system.components.atoms.gl_status_indicator import GLStatusIndicator
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.storage.repositories import ConfigRepository

from cancunbot.src.storage.cancunbot_repos import OrdenCancunRepository, LoteFolioRepository, FolioCancunRepository, ReciboCancunRepository
from cancunbot.src.core.bot_recibo_worker import BotReciboCunWorker

logger = logging.getLogger(__name__)


class R2FCancunWindow(QMainWindow):
    """MainWindow wrapper que cumple con el patrón de ventanas independientes del SAR (ej: BillingBotWindow)."""
    logout_requested = Signal()

    def __init__(self, db_connector, sesion_id, usuario_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("R2F-Cancún (Recibos y Facturación)")
        self.resize(1100, 750)
        
        self.view = R2FCancunView(db_connector, sesion_id, usuario_id, self)
        self.setCentralWidget(self.view)
        
        # Propagar señal de logout
        self.view.logout_requested.connect(self.logout_requested.emit)

    def closeEvent(self, event):
        self.view.closeEvent(event)


class R2FCancunView(QWidget):
    """Vista del dashboard unificado con selector de modo (Recibos / Facturas)."""
    logout_requested = Signal()

    def __init__(self, db_connector, sesion_id, usuario_id, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.sesion_id = sesion_id
        self.usuario_id = usuario_id
        
        self.active_worker = None
        self.selected_lote_id = None
        
        # Layout principal — Mirror Bot Face A
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(8)

        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()

        # Cargar ruta base configurada
        self.default_output_dir = "T:\\CANCUN"
        try:
            if self.api_client.connect_via_api:
                res = self.api_client.request("GET", "/api/docs/config/parametro/CANCUN_PDF_BASE_PATH")
                db_dir = res.get("valor")
            else:
                with self.db_connector.get_session() as session:
                    repo = ConfigRepository(session)
                    db_dir = repo.get_parametro("CANCUN_PDF_BASE_PATH")
            if db_dir:
                self.default_output_dir = db_dir
        except Exception as e:
            logger.error(f"Error cargando directorio de Cancún: {e}")

        self.selected_custom_path = None
        
        # Obtener correo del usuario
        self.correo_usuario = ""
        try:
            if not self.api_client.connect_via_api:
                from sar.src.storage.repositories import UsuarioRepository
                with self.db_connector.get_session() as session:
                    repo = UsuarioRepository(session)
                    u = repo.get_by_id(self.usuario_id)
                    if u and u.correo:
                        self.correo_usuario = u.correo
            else:
                res = self.api_client.request("GET", f"/api/admin/data/usuario") # generic data fetch not perfect but handled gracefully
                # If we have a specific endpoint, we can use it. Since we don't, we just catch the exception
                pass 
        except Exception as e:
            logger.error(f"Error cargando correo de usuario: {e}")

        # Construir paneles de UI
        self._build_header()
        self._build_controls_and_metrics()
        self._build_tables_panel()
        self._build_console_panel()

        # Cargar datos iniciales
        self._refresh_lotes_table()
        self._verify_paths()

    def _build_header(self):
        header_frame = QFrame()
        header_frame.setObjectName("botHeaderFaceA")  # Reusar estilos CSS del SAR
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(12)

        self.lbl_titulo = QLabel("🚀 BOT - CONSULTA Y DESCARGA DE RECIBOS (R2F-CANCÚN)")
        h_layout.addWidget(self.lbl_titulo)
        h_layout.addStretch()

        # Switch de Modo (RECIBOS / FACTURAS) con texto en blanco para el header oscuro
        self.switch_modo = CustomSwitch("MODO FACTURAS")
        self.switch_modo.setChecked(False)
        self.switch_modo.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px;")
        self.switch_modo.toggled.connect(self._on_modo_toggled)
        h_layout.addWidget(self.switch_modo)

        # Indicador de estado del portal
        self.lbl_portal_status = QLabel("Portal: INACTIVO")
        self.lbl_portal_status.setStyleSheet("background-color: #334155; padding: 4px 12px; border-radius: 12px; font-size: 12px; color: white;")
        h_layout.addWidget(self.lbl_portal_status)

        # Botones de Gear y User
        self.btn_gear = QPushButton("⚙")
        self.btn_gear.setObjectName("iconHeaderBtn")
        self.btn_gear.clicked.connect(self._on_gear_clicked)
        h_layout.addWidget(self.btn_gear)

        self.btn_user = QPushButton("👤")
        self.btn_user.setObjectName("iconHeaderBtn")
        self.btn_user.clicked.connect(self._on_user_clicked)
        h_layout.addWidget(self.btn_user)

        self.main_layout.addWidget(header_frame)

    def _build_controls_and_metrics(self):
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        # 1. Panel de Controles
        controles_frame = QFrame()
        controles_frame.setObjectName("card")
        c_layout = QVBoxLayout(controles_frame)
        c_layout.setContentsMargins(8, 6, 8, 6)
        c_layout.setSpacing(4)

        lbl_c = CustomLabel("⚙ CONTROLES OPERATIVOS", variant="subheader")
        c_layout.addWidget(lbl_c)

        self.chk_autonomo = CustomSwitch("🤖 Modo Autónomo (Visible)")
        self.chk_autonomo.setChecked(True)
        self.chk_autonomo.setEnabled(False)
        c_layout.addWidget(self.chk_autonomo)

        # Ruta de descarga selector
        lbl_path_title = CustomLabel("📁 Ruta de Descarga / Almacenamiento:", variant="body")
        lbl_path_title.setStyleSheet("font-weight: bold;")
        c_layout.addWidget(lbl_path_title)
        
        path_input_layout = QHBoxLayout()
        display_label_text = f"Por defecto ({self.default_output_dir})"
        self.lbl_download_path_display = CustomLabel(display_label_text, variant="body")
        self.lbl_download_path_display.setStyleSheet("background-color: #f9fafb; padding: 4px 6px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 11px;")
        path_input_layout.addWidget(self.lbl_download_path_display, stretch=4)
        
        self.btn_browse = CustomButton("...", is_secondary=True)
        self.btn_browse.setObjectName("secondaryBtn")
        self.btn_browse.setStyleSheet("padding: 2px 6px; font-weight: bold;")
        self.btn_browse.clicked.connect(self._on_browse_path_clicked)
        path_input_layout.addWidget(self.btn_browse, stretch=1)
        c_layout.addLayout(path_input_layout)

        # GLStatusIndicator pill under download path
        self.status_indicator = GLStatusIndicator()
        c_layout.addWidget(self.status_indicator)

        self.btn_iniciar = CustomButton("▶ Iniciar Bot", is_secondary=False)
        self.btn_iniciar.setObjectName("primaryBtn")
        self.btn_iniciar.setFixedHeight(30)
        self.btn_iniciar.clicked.connect(self._on_iniciar_bot)
        c_layout.addWidget(self.btn_iniciar)

        self.btn_cargar_lote = CustomButton("📥 Cargar Lote Seleccionado", is_secondary=True)
        self.btn_cargar_lote.setObjectName("secondaryBtn")
        self.btn_cargar_lote.setFixedHeight(30)
        self.btn_cargar_lote.clicked.connect(self._on_cargar_lote_clicked)
        c_layout.addWidget(self.btn_cargar_lote)

        top_layout.addWidget(controles_frame, stretch=1)

        # 2. Panel de Métricas (Replicado de Bot Face A)
        metricas_frame = QFrame()
        metricas_frame.setObjectName("card")
        m_layout = QVBoxLayout(metricas_frame)
        m_layout.setContentsMargins(8, 6, 8, 6)
        m_layout.setSpacing(4)

        self.lbl_m_titulo = CustomLabel("📊 MÉTRICAS DE DESCARGA DE RECIBOS", variant="subheader")
        m_layout.addWidget(self.lbl_m_titulo)

        grid_m = QGridLayout()
        self.box_pendientes = MetricBox("Por Generar", "0", "#3b82f6")
        self.box_exitosos = MetricBox("Generados", "0", "#10b981")
        self.box_errores = MetricBox("Errores", "0", "#ef4444")

        grid_m.addWidget(self.box_pendientes, 0, 0)
        grid_m.addWidget(self.box_exitosos, 0, 1)
        grid_m.addWidget(self.box_errores, 0, 2)

        self.lbl_lote_actual_info = CustomLabel("RFC: -- | Razón Social: --\nCP: --", variant="muted")
        self.lbl_lote_actual_info.setStyleSheet("color: #6b7280; font-size: 11px; background: #f9fafb; padding: 4px; border: 1px solid #e5e7eb; border-radius: 4px;")
        grid_m.addWidget(self.lbl_lote_actual_info, 1, 0, 1, 3)

        m_layout.addLayout(grid_m)
        top_layout.addWidget(metricas_frame, stretch=1)

        # 3. Panel de Monitoreo en Tiempo Real (Replicado de Bot Face A)
        monitoreo_frame = QFrame()
        monitoreo_frame.setObjectName("card")
        mon_layout = QVBoxLayout(monitoreo_frame)
        mon_layout.setContentsMargins(8, 6, 8, 6)
        mon_layout.setSpacing(4)

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

        mon_layout.addWidget(CustomLabel("Progreso", variant="body"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setValue(0)
        mon_layout.addWidget(self.progress_bar)

        self.lbl_mon_status = CustomLabel("ESPERANDO INICIO DE PROCESAMIENTO...", variant="muted")
        self.lbl_mon_status.setStyleSheet("color: #6b7280; font-size: 11px;")
        mon_layout.addWidget(self.lbl_mon_status)

        top_layout.addWidget(monitoreo_frame, stretch=1)

        self.main_layout.addLayout(top_layout, stretch=0)

    def _build_tables_panel(self):
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        header_layout = QHBoxLayout()
        lbl = CustomLabel("⚙ SOLICITUDES / LOTES ASIGNADOS", variant="subheader")
        header_layout.addWidget(lbl)
        header_layout.addStretch()

        self.chk_ver_todos = CustomCheckBox("Mostrar completados y cancelados")
        self.chk_ver_todos.setStyleSheet("margin-right: 8px;")
        self.chk_ver_todos.stateChanged.connect(self._refresh_lotes_table)
        header_layout.addWidget(self.chk_ver_todos)

        self.btn_refresh = CustomButton("↻ Actualizar", is_secondary=False)
        self.btn_refresh.clicked.connect(self._refresh_lotes_table)
        header_layout.addWidget(self.btn_refresh)

        layout.addLayout(header_layout)

        # Tabla de Lotes Asignados (Directa, sin pestañas, espejo exacto de Bot Face A)
        headers = ["ID Lote", "Folio Lote", "Origen", "Total Folios", "Procesados", "Estado"]
        self.table_lotes = StyledDataTable(headers, parent=self)
        self.table_lotes.setObjectName("botTable")
        self.table_lotes.doubleClicked.connect(self._on_lote_double_clicked)
        self.table_lotes.setMinimumHeight(130)
        layout.addWidget(self.table_lotes, stretch=1)

        self.main_layout.addWidget(panel, stretch=3)

    def _build_console_panel(self):
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        lbl = CustomLabel("⚙ CONSOLA DE LOGS DE ACTIVIDAD", variant="subheader")
        layout.addWidget(lbl)

        self.txt_console = QTextEdit()
        self.txt_console.setObjectName("console")
        self.txt_console.setReadOnly(True)
        self.txt_console.setMinimumHeight(80)
        self.txt_console.setStyleSheet("""
            QTextEdit#console {
                background-color: #0f172a;
                color: #22c55e;
                font-family: 'Consolas', 'Cascadia Code', 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 6px;
            }
        """)

        layout.addWidget(self.txt_console, stretch=1)
        self._write_log("Sistema R2F-Cancún listo. Esperando carga de lote...")
        self.main_layout.addWidget(panel, stretch=2)

    def _on_cargar_lote_clicked(self):
        """Maneja el clic en 'Cargar Lote Seleccionado' espejo de Bot Face A."""
        if hasattr(self, 'active_worker') and self.active_worker and self.active_worker.isRunning():
            return

        selected = self.table_lotes.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Atención", "Selecciona una fila de la tabla de lotes primero.")
            return

        row = selected[0].row()
        lote_id_item = self.table_lotes.item(row, 0)
        if lote_id_item:
            lote_id = int(lote_id_item.text())
            self.selected_lote_id = lote_id
            self._write_log(f"Cargando contexto para Lote #{lote_id}...")
            self._load_lote_detalles(lote_id)

    def _on_modo_toggled(self, is_checked: bool):
        """Alterna el modo de trabajo del dashboard."""
        if self.active_worker and self.active_worker.isRunning():
            self.switch_modo.setChecked(not is_checked)
            QMessageBox.warning(self, "Acción Bloqueada", "No puede cambiar de modo mientras el Bot está activo.")
            return

        if is_checked:
            self.lbl_titulo.setText("🧾 BOT - GENERACIÓN Y DESCARGA DE FACTURAS (R2F-CANCÚN)")
            if hasattr(self, 'lbl_m_titulo'):
                self.lbl_m_titulo.setText("📊 MÉTRICAS DE GENERACIÓN Y DESCARGA DE FACTURAS")
            if hasattr(self, 'btn_importar_excel'): self.btn_importar_excel.setEnabled(False)
            self.btn_iniciar.setEnabled(True)
            self._write_log("Modo cambiado a FACTURACIÓN. Listo para iniciar.")
        else:
            self.lbl_titulo.setText("🚀 BOT - CONSULTA Y DESCARGA DE RECIBOS (R2F-CANCÚN)")
            if hasattr(self, 'lbl_m_titulo'):
                self.lbl_m_titulo.setText("📊 MÉTRICAS DE DESCARGA DE RECIBOS")
            if hasattr(self, 'btn_importar_excel'): self.btn_importar_excel.setEnabled(True)
            self.btn_iniciar.setEnabled(True)
            self._write_log("Modo cambiado a RECIBOS.")

    def _on_iniciar_bot(self):
        """Lanza o detiene el worker de Playwright para descargas de recibos."""
        # Si el hilo ya se encuentra en ejecución, se solicita detención segura
        if self.active_worker and self.active_worker.isRunning():
            self.btn_iniciar.setEnabled(False)
            self.btn_iniciar.setText("⏹ Deteniendo...")
            self.active_worker.stop()
            return

        if not self.selected_lote_id:
            QMessageBox.warning(self, "Lote no seleccionado", "Selecciona un lote haciendo doble clic en la tabla de lotes.")
            return

        # Validar disponibilidad de la unidad de red o ruta por defecto
        if hasattr(self, 'is_path_online') and not self.is_path_online:
            target_path = self.selected_custom_path if self.selected_custom_path else self.default_output_dir
            reply = QMessageBox.warning(
                self,
                "Unidad de Red No Conectada",
                f"La ruta de almacenamiento 'CANCUN_PDF_BASE_PATH' ({target_path}) se encuentra NO CONECTADA.\n\n"
                f"Por favor revise su conexión a la red o reporte la falla al departamento de TI.\n\n"
                f"¿Desea continuar guardando temporalmente en contingencia local?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                self._write_log("Inicio de procesamiento cancelado por falta de conexión a la unidad de red.")
                return

        # Validar el estado del lote en la base de datos o API antes de iniciar
        try:
            if self.api_client and getattr(self.api_client, 'connect_via_api', False):
                lote_data = self.api_client.request("GET", f"/api/docs/cancun/lotes/{self.selected_lote_id}/detalles") or {}
                estado_lote = lote_data.get("estado_codigo", "NUEVO")
            else:
                with self.db_connector.get_session() as session:
                    from sqlalchemy import text
                    lote_row = session.execute(
                        text("""
                            SELECT e.codigo 
                            FROM cancunbot_produccion.lote_folio l
                            JOIN sar_catalogo.estado_sistema e ON l.estado_id = e.estado_id
                            WHERE l.lote_id = :lid
                        """),
                        {"lid": self.selected_lote_id}
                    ).fetchone()
                    estado_lote = lote_row[0] if lote_row else "NUEVO"

            if estado_lote == "COMPLETADO":
                QMessageBox.information(
                    self, 
                    "Lote Completado", 
                    "Este lote ya ha sido procesado de forma exitosa en su totalidad.\nNo hay folios pendientes de descargar."
                )
                return

            # Si es un lote con errores (COMPLETADO_PARCIAL), reactivar los folios fallidos
            if estado_lote in ("COMPLETADO_PARCIAL", "EN_PROCESO"):
                reply = QMessageBox.question(
                    self,
                    "Reintentar Errores",
                    "El lote seleccionado ya fue procesado pero contiene errores o descargas pendientes.\n"
                    "¿Deseas reactivar los folios con error y volver a procesarlos?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    if self.api_client and getattr(self.api_client, 'connect_via_api', False):
                        self.api_client.request("POST", f"/api/docs/cancun/lotes/{self.selected_lote_id}/reactivar-errores")
                    else:
                        with self.db_connector.get_session() as session:
                            from sqlalchemy import text
                            st_pendiente = session.execute(
                                text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad = 'folio_cancun' AND codigo = 'PENDIENTE'")
                            ).scalar()
                            st_error = session.execute(
                                text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad = 'folio_cancun' AND codigo = 'ERROR_DESCARGA'")
                            ).scalar()
                            
                            session.execute(
                                text("""
                                    UPDATE cancunbot_produccion.folio_cancun 
                                    SET estado_id = :st_p, ultimo_error = NULL
                                    WHERE lote_id = :lid AND estado_id = :st_e
                                """),
                                {"st_p": st_pendiente, "lid": self.selected_lote_id, "st_e": st_error}
                            )
                            session.commit()
                    self._write_log(f"Reactivando folios con error del lote {self.selected_lote_id} para reintento.")
                elif estado_lote == "COMPLETADO_PARCIAL":
                    return
        except Exception as e:
            logger.error(f"Error validando estado del lote antes de iniciar: {e}")

        # 4. Diálogo de confirmación antes de iniciar el bot
        modo_ejecucion = "Navegador Visible (Manual)" if self.chk_autonomo.isChecked() else "En Segundo Plano (Autónomo)"
        lote_info = f"Lote ID #{self.selected_lote_id}" if self.selected_lote_id else "Sin Lote"

        confirm_dialog = GLMessageDialog(
            title="Confirmar Inicio de Bot",
            message=f"¿Deseas iniciar la descarga de recibos del portal de Tesorería de Cancún?\n\n"
                    f"• {lote_info}\n"
                    f"• Modo de Ejecución: {modo_ejecucion}\n"
                    f"• Destino: {self.selected_custom_path or self.default_output_dir}",
            dialog_type=DialogType.QUESTION,
            confirm_text="Iniciar Bot",
            cancel_text="Cancelar",
            parent=self
        )
        if confirm_dialog.exec() != QDialog.Accepted:
            self._write_log("Ejecución del Bot cancelada por el usuario.")
            return

        self.btn_iniciar.setText("⏹ Detener Bot")
        self.btn_iniciar.setStyleSheet(f"background-color: {Colors.ERROR}; color: white;")
        
        # Deshabilitar TODOS los controles de UI para blindar ante errores humanos
        self.switch_modo.setEnabled(False)
        self.chk_autonomo.setEnabled(False)
        if hasattr(self, 'btn_cargar_lote'): self.btn_cargar_lote.setEnabled(False)
        if hasattr(self, 'btn_refresh'): self.btn_refresh.setEnabled(False)
        if hasattr(self, 'chk_ver_todos'): self.chk_ver_todos.setEnabled(False)
        if hasattr(self, 'btn_importar_excel'): self.btn_importar_excel.setEnabled(False)
        if hasattr(self, 'btn_importar_pdf'): self.btn_importar_pdf.setEnabled(False)
        if hasattr(self, 'btn_descargar_plantilla'): self.btn_descargar_plantilla.setEnabled(False)
        self.btn_browse.setEnabled(False)
        if hasattr(self, 'btn_control_r2f'): self.btn_control_r2f.setEnabled(False)
        self.table_lotes.setEnabled(False)
        if hasattr(self, 'table_detalles'): self.table_detalles.setEnabled(False)

        # Si el interruptor de visible está activo (Checked), headless debe ser False (Navegador visible)
        es_visible = self.chk_autonomo.isChecked()
        headless_mode = not es_visible

        # Cargar/refrescar métricas del lote actual en las tarjetas superiores antes de arrancar
        self._load_lote_detalles(self.selected_lote_id)

        # Inicializar el QThread Worker pasando la ruta personalizada si existe y el cliente API
        es_modo_facturas = self.switch_modo.isChecked()
        if es_modo_facturas:
            from cancunbot.src.core.bot_factura_worker import BotFacturaCunWorker
            self.active_worker = BotFacturaCunWorker(
                db_connector=self.db_connector,
                lote_id=self.selected_lote_id,
                headless=headless_mode,
                custom_output_dir=self.selected_custom_path,
                api_client=self.api_client,
                correo_usuario=getattr(self, "correo_usuario", "")
            )
        else:
            self.active_worker = BotReciboCunWorker(
                db_connector=self.db_connector,
                lote_id=self.selected_lote_id,
                headless=headless_mode,
                custom_output_dir=self.selected_custom_path,
                api_client=self.api_client
            )

        self.active_worker.status_changed.connect(self._write_log)
        self.active_worker.metric_updated.connect(self._on_metric_updated)
        self.active_worker.progress_changed.connect(self._on_progress_changed)
        self.active_worker.folio_status_changed.connect(self._on_folio_status_changed)
        self.active_worker.finished_processing.connect(self._on_worker_finished)
        self.active_worker.start()

        self.lbl_portal_status.setText("Portal: ACTIVO")
        self.lbl_portal_status.setStyleSheet(f"background-color: {Colors.ACCENT_EMERALD}; padding: 4px 12px; border-radius: 12px; font-size: 12px; color: white; font-weight: bold;")

    def _on_worker_finished(self, success: bool, message: str):
        self.btn_iniciar.setEnabled(True)
        self.btn_iniciar.setText("▶ Iniciar Bot")
        self.btn_iniciar.setStyleSheet(f"background-color: {Colors.SURFACE_DARK}; color: white;")
        
        # Rehabilitar controles de UI tras finalizar el proceso
        self.switch_modo.setEnabled(True)
        self.chk_autonomo.setEnabled(True)
        if hasattr(self, 'btn_cargar_lote'): self.btn_cargar_lote.setEnabled(True)
        if hasattr(self, 'btn_refresh'): self.btn_refresh.setEnabled(True)
        if hasattr(self, 'chk_ver_todos'): self.chk_ver_todos.setEnabled(True)
        if hasattr(self, 'btn_importar_excel'): self.btn_importar_excel.setEnabled(True)
        if hasattr(self, 'btn_importar_pdf'): self.btn_importar_pdf.setEnabled(True)
        if hasattr(self, 'btn_descargar_plantilla'): self.btn_descargar_plantilla.setEnabled(True)
        self.btn_browse.setEnabled(True)
        if hasattr(self, 'btn_control_r2f'): self.btn_control_r2f.setEnabled(True)
        self.table_lotes.setEnabled(True)
        if hasattr(self, 'table_detalles'): self.table_detalles.setEnabled(True)
        
        self.lbl_portal_status.setText("Portal: INACTIVO")
        self.lbl_portal_status.setStyleSheet(f"background-color: {Colors.BORDER_DARK}; padding: 4px 12px; border-radius: 12px; font-size: 12px; color: white;")

        if success:
            QMessageBox.information(self, "Proceso Finalizado", message)
        else:
            QMessageBox.critical(self, "Error del Bot", message)

        self._refresh_lotes_table()
        if self.selected_lote_id:
            self._load_lote_detalles(self.selected_lote_id)

    def closeEvent(self, event):
        """Asegura la detención limpia del worker al cerrar la vista/pestaña."""
        if hasattr(self, 'active_worker') and self.active_worker and self.active_worker.isRunning():
            self.active_worker.stop()
            self.active_worker.wait(3000)
        super().closeEvent(event)

    def _on_metric_updated(self, metric: str, value: int):
        if metric == "exitosos":
            self.box_exitosos.set_value(str(value))
            if hasattr(self, "exitosos_base"):
                self.current_success = self.exitosos_base + value
            else:
                self.current_success = value
        elif metric == "errores":
            self.box_errores.set_value(str(value))
            if hasattr(self, "errores_base"):
                self.current_errors = self.errores_base + value
            else:
                self.current_errors = value
        elif metric == "pendientes":
            self.box_pendientes.set_value(str(value))
            return
        
        # Lógica exacta del Bot Face A (bot_view.py):
        # Pendientes se calcula dinámicamente: total_referencias - total_exitosos - total_errores
        if hasattr(self, "total_referencias"):
            cur_succ = getattr(self, "current_success", 0)
            cur_err = getattr(self, "current_errors", 0)
            remaining = self.total_referencias - cur_succ - cur_err
            nuevo_pendientes = max(0, remaining)
            self.box_pendientes.set_value(str(nuevo_pendientes))
            logger.debug(f"Métricas (Face A logic): Total={self.total_referencias}, Succ={cur_succ}, Err={cur_err} -> Pendientes={nuevo_pendientes}")

    def _on_progress_changed(self, current: int, total: int):
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.lbl_mon_status.setText(f"PROCESANDO FOLIO {current} DE {total} ({percentage}%)")

    def _on_folio_status_changed(self, data: dict):
        self.lbl_m_ref.setText(data.get("referencia", "--"))
        self.lbl_m_rfc.setText(data.get("rfc", "--"))
        self.lbl_m_est.setText(data.get("estado", "--"))

    def _refresh_lotes_table(self):
        """Carga la lista de lotes desde la base de datos o API REST usando el estándar populate_rows de StyledDataTable."""
        try:
            data = []
            if self.api_client and getattr(self.api_client, 'connect_via_api', False):
                lotes = self.api_client.request("GET", "/api/docs/cancun/lotes")
                for lote in lotes:
                    data.append([
                        str(lote["lote_id"]),
                        lote["folio_lote"],
                        lote["origen"],
                        str(lote["total_folios"]),
                        str(lote["folios_procesados"]),
                        lote["estado_codigo"]
                    ])
            else:
                with self.db_connector.get_session() as session:
                    repo = LoteFolioRepository(session)
                    lotes = repo.list_all()
                    for lote in lotes:
                        data.append([
                            str(lote.lote_id),
                            lote.folio_lote,
                            lote.origen,
                            str(lote.total_folios),
                            str(lote.folios_procesados),
                            lote.estado.codigo
                        ])
            self.table_lotes.populate_rows(data)
        except Exception as e:
            logger.error(f"Error cargando tabla de lotes: {e}")

    def _refresh_ordenes_table(self):
        """Carga la lista de órdenes desde la base de datos o API REST."""
        try:
            data = []
            if self.api_client and getattr(self.api_client, 'connect_via_api', False):
                ordenes = self.api_client.request("GET", "/api/docs/cancun/ordenes")
                for ord_item in ordenes:
                    data.append([
                        str(ord_item["orden_id"]),
                        ord_item["folio_orden"],
                        ord_item.get("descripcion", "--"),
                        str(ord_item.get("total_lotes", 0)),
                        str(ord_item.get("total_folios", 0)),
                        str(ord_item.get("folios_procesados", 0)),
                        ord_item.get("estado_codigo", "ABIERTA"),
                        ord_item.get("created_at", "--")
                    ])
            else:
                with self.db_connector.get_session() as session:
                    repo = OrdenCancunRepository(session)
                    ordenes = repo.list_all()
                    for ord_item in ordenes:
                        data.append([
                            str(ord_item.orden_id),
                            ord_item.folio_orden,
                            ord_item.descripcion or "--",
                            str(ord_item.total_lotes),
                            str(ord_item.total_folios),
                            str(ord_item.folios_procesados),
                            ord_item.estado.codigo if ord_item.estado else "--",
                            ord_item.created_at.strftime("%Y-%m-%d %H:%M") if ord_item.created_at else "--"
                        ])
            if hasattr(self, 'table_ordenes'):
                self.table_ordenes.populate_rows(data)
        except Exception as e:
            logger.error(f"Error cargando tabla de órdenes: {e}")

    def _on_orden_double_clicked(self, index):
        """Maneja el doble clic en una fila de la tabla de Órdenes para navegar a sus lotes asociados."""
        if not hasattr(self, 'table_ordenes'):
            return
        row = index.row()
        orden_id_item = self.table_ordenes.item(row, 0)
        if orden_id_item:
            orden_id = int(orden_id_item.text())
            self.selected_orden_id = orden_id
            self.lbl_lote_actual_info.setText(f"Orden seleccionada: ID {orden_id}")
            if hasattr(self, 'tab_widget'):
                self.tab_widget.setCurrentIndex(1)

    def _on_administrar_recibos_clicked(self):
        """Abre el panel de control administrativo de R2F en un diálogo modal independiente maximizado."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Control de Recibos & Facturas (R2F)")
        
        # Habilitar botones de maximizar/minimizar de la ventana
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        
        from cancunbot.src.ui.views.r2f_control_view import R2FControlView
        control_view = R2FControlView(self.db_connector, dialog)
        layout.addWidget(control_view)

        # Guardar el diálogo activo en la lista de diálogos del objeto para poder cerrarlo en caso de logout
        if not hasattr(self, '_open_dialogs'):
            self._open_dialogs = []
        self._open_dialogs.append(dialog)
        
        # Remover el diálogo de la lista cuando se cierre
        dialog.finished.connect(lambda: self._open_dialogs.remove(dialog) if dialog in self._open_dialogs else None)
        
        # Mostrar el diálogo maximizado por defecto
        dialog.showMaximized()
        dialog.exec()

    def _on_lote_double_clicked(self, index):
        row = index.row()
        lote_id_item = self.table_lotes.item(row, 0)
        if lote_id_item:
            lote_id = int(lote_id_item.text())
            self.selected_lote_id = lote_id
            correo_display = f" | Correo: {self.correo_usuario}" if getattr(self, "correo_usuario", "") else ""
            self.lbl_lote_actual_info.setText(f"Lote seleccionado: ID {lote_id}{correo_display}")
            self._load_lote_detalles(lote_id)

    def _load_lote_detalles(self, lote_id: int):
        try:
            if self.api_client and getattr(self.api_client, 'connect_via_api', False):
                lote = self.api_client.request("GET", f"/api/docs/cancun/lotes/{lote_id}/detalles")
                if lote:
                    self.total_referencias = lote["total_folios"]
                    self.exitosos_base = lote["folios_procesados"]
                    self.errores_base = lote["folios_error"]
                    self.current_success = self.exitosos_base
                    self.current_errors = self.errores_base

                    pendientes = max(0, self.total_referencias - self.current_success - self.current_errors)
                    self.box_pendientes.set_value(str(pendientes))
                    self.box_exitosos.set_value(str(self.current_success))
                    self.box_errores.set_value(str(self.current_errors))

                    data = []
                    for folio in lote.get("folios", []):
                        data.append([
                            str(folio["folio_id"]),
                            folio["folio_texto"],
                            folio["tipo_folio"],
                            str(folio["intentos"]),
                            folio["estado_codigo"]
                        ])
                    if hasattr(self, 'table_detalles'):
                        self.table_detalles.populate_rows(data)
            else:
                with self.db_connector.get_session() as session:
                    lote_repo = LoteFolioRepository(session)
                    lote = lote_repo.get_by_id(lote_id)
                    if lote:
                        self.total_referencias = lote.total_folios
                        self.exitosos_base = lote.folios_procesados
                        self.errores_base = lote.folios_error
                        self.current_success = self.exitosos_base
                        self.current_errors = self.errores_base

                        pendientes = max(0, self.total_referencias - self.current_success - self.current_errors)
                        self.box_pendientes.set_value(str(pendientes))
                        self.box_exitosos.set_value(str(self.current_success))
                        self.box_errores.set_value(str(self.current_errors))

                        data = []
                        for folio in lote.folios:
                            f_text = folio.folio_electronico if folio.tipo_folio == "ELECTRONICO" else folio.folio_pase_caja
                            data.append([
                                str(folio.folio_id),
                                f_text,
                                folio.tipo_folio,
                                str(folio.intentos),
                                folio.estado.codigo
                            ])
                        if hasattr(self, 'table_detalles'):
                            self.table_detalles.populate_rows(data)
        except Exception as e:
            logger.error(f"Error cargando folios de lote: {e}")

    def _on_importar_excel(self):
        """Diálogo para seleccionar e importar un archivo Excel validando duplicados contra la base de datos."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Importar Lote Excel", "", "Archivos de Excel (*.xlsx *.xls)"
        )
        if not file_path:
            return

        from sar.src.ui.design_system.components import GLLoadingDialog
        from PySide6.QtCore import QCoreApplication

        loading_dialog = GLLoadingDialog("Leyendo y analizando archivo Excel...", self)
        loading_dialog.show()
        QCoreApplication.processEvents()

        try:
            from cancunbot.src.services.excel_importer import ExcelImporter
            importer = ExcelImporter(db_connector=self.db_connector, api_client=self.api_client)

            # Validar y cargar folios desde el archivo usando la lógica del servicio
            try:
                lista_folios_dict = importer.importar(file_path)
            finally:
                loading_dialog.close()

            if not lista_folios_dict:
                QMessageBox.warning(self, "Archivo Vacío", "No se encontraron folios validos en el archivo de excel")
                return

            folios_mapeados = []
            folios_texto_nuevos = set()
            
            # Contadores de control
            duplicados_excel = 0
            duplicados_db = 0
            total_leidos = len(lista_folios_dict)
            
            use_api = (self.api_client is not None and getattr(self.api_client, "connect_via_api", False))

            if use_api:
                # Vía REST API: El servidor realiza el filtrado de duplicados e inserción transaccional
                for f in lista_folios_dict:
                    tipo = f["tipo_folio"]
                    folios_mapeados.append({
                        "folio_electronico": f.get("folio_electronico"),
                        "folio_pase_caja": f.get("folio_pase_caja"),
                        "tipo_folio": tipo,
                        "rfc_id": f.get("rfc_id"),
                        "desarrollo_id": f.get("desarrollo_id")
                    })
            else:
                db_check_loading = GLLoadingDialog("Verificando duplicados en la Base de Datos...", self)
                db_check_loading.show()
                QCoreApplication.processEvents()

                try:
                    # Obtener folios ya existentes en BD de forma directa para omitir duplicados
                    with self.db_connector.get_session() as session:
                        from sqlalchemy import select
                        from cancunbot.src.storage.cancunbot_models import FolioCancun
                        
                        db_folios_elec = set(session.scalars(select(FolioCancun.folio_electronico).where(FolioCancun.folio_electronico.isnot(None))).all())
                        db_folios_pase = set(session.scalars(select(FolioCancun.folio_pase_caja).where(FolioCancun.folio_pase_caja.isnot(None))).all())

                    for f in lista_folios_dict:
                        tipo = f["tipo_folio"]
                        val = f["folio_electronico"] if tipo == "ELECTRONICO" else f["folio_pase_caja"]
                        
                        # 1. Validar duplicados dentro del propio archivo Excel
                        if val in folios_texto_nuevos:
                            duplicados_excel += 1
                            continue

                        # 2. Validar duplicados contra la Base de Datos
                        if tipo == "ELECTRONICO" and val in db_folios_elec:
                            duplicados_db += 1
                            continue
                        if tipo == "PASE_CAJA" and val in db_folios_pase:
                            duplicados_db += 1
                            continue

                        folios_texto_nuevos.add(val)
                        folios_mapeados.append({
                            "folio_electronico": f["folio_electronico"],
                            "folio_pase_caja": f["folio_pase_caja"],
                            "tipo_folio": tipo,
                            "rfc_id": f.get("rfc_id"),
                            "desarrollo_id": f.get("desarrollo_id")
                        })
                finally:
                    db_check_loading.close()

                # Si no hay folios nuevos válidos que procesar en modo LAN
                if not folios_mapeados:
                    msg_error = (
                        f"No hay folios nuevos para importar.\n\n"
                        f"• Total en Excel: {total_leidos}\n"
                        f"• Duplicados en Excel: {duplicados_excel}\n"
                        f"• Ya existentes en BD: {duplicados_db}"
                    )
                    QMessageBox.warning(self, "Importación Cancelada", msg_error)
                    return

            # Contar resoluciones de catálogos
            con_rfc = sum(1 for x in folios_mapeados if x.get("rfc_id") is not None)
            con_des = sum(1 for x in folios_mapeados if x.get("desarrollo_id") is not None)

            # 3. Cuadro de Confirmación estandarizado con GLMessageDialog del SAR Design System
            desc_lote = f"Importado desde {Path(file_path).name}"
            confirm_msg = (
                f"Resumen del archivo Excel a importar:\n\n"
                f"• Registros leídos del archivo: {total_leidos}\n"
                f"• Folios preparados para procesar: {len(folios_mapeados)}\n\n"
                f"Asociación con Catálogos Maestros SAR:\n"
                f"• RFCs vinculados: {con_rfc} de {len(folios_mapeados)}\n"
                f"• Desarrollos vinculados: {con_des} de {len(folios_mapeados)}\n\n"
                f"¿Deseas confirmar la inserción y crear un nuevo Lote de Folios?"
            )
            
            confirm_dialog = GLMessageDialog(
                title="Confirmar Importación de Excel",
                message=confirm_msg,
                dialog_type=DialogType.QUESTION,
                confirm_text="Importar y Crear Lote",
                cancel_text="Cancelar",
                parent=self
            )
            
            if confirm_dialog.exec() != QDialog.Accepted:
                self._write_log("Importación cancelada por el usuario.")
                return

            # Mostrar nuevamente la ventana modal de carga durante la inserción física
            save_loading = GLLoadingDialog("Creando Lote e insertando registros...", self)
            save_loading.show()
            QCoreApplication.processEvents()

            try:
                if use_api:
                    # Inserción vía REST API
                    resp = self.api_client.request("POST", "/api/docs/cancun/lotes/importar-excel", json={
                        "usuario_id": self.usuario_id,
                        "origen": "EXCEL",
                        "descripcion": desc_lote,
                        "archivo_excel": file_path,
                        "folios": folios_mapeados
                    })
                    save_loading.close()
                    if resp and resp.get("lote_id"):
                        folio_lote_nombre = resp.get("folio_lote", f"ID #{resp.get('lote_id')}")
                        guardados = resp.get("total_folios", 0)
                        dup_db = resp.get("duplicados_db", 0)
                        dup_excel = resp.get("duplicados_excel", 0)
                        extra_msg = f"\n(Omitidos: {dup_excel} duplicados en Excel, {dup_db} ya en BD)" if (dup_db + dup_excel) > 0 else ""
                        
                        QMessageBox.information(
                            self, "Importación Completada", 
                            f"Lote {folio_lote_nombre} creado con éxito vía API REST.\n"
                            f"Se insertaron {guardados} folios nuevos.{extra_msg}"
                        )
                    else:
                        QMessageBox.critical(self, "Error API", "No se pudo crear el lote desde el servidor API.")
                else:
                    # Inserción de forma directa en BD (modo LAN)
                    with self.db_connector.get_session() as session:
                        orden_repo = OrdenCancunRepository(session)
                        lote_repo = LoteFolioRepository(session)
                        folio_repo = FolioCancunRepository(session)

                        orden = orden_repo.create(
                            usuario_id=self.usuario_id,
                            descripcion=f"Orden para importación {Path(file_path).name}"
                        )

                        lote = lote_repo.create(
                            usuario_id=self.usuario_id,
                            origen="EXCEL",
                            descripcion=desc_lote,
                            archivo_excel=file_path,
                            orden_id=orden.orden_id
                        )
                        
                        guardados = folio_repo.create_bulk(lote.lote_id, folios_mapeados)
                        lote_repo.update_metrics_and_status(lote.lote_id)
                        session.commit()
                        
                        folio_lote_nombre = lote.folio_lote
                        folio_orden_nombre = orden.folio_orden

                    save_loading.close()
                    QMessageBox.information(
                        self, "Importación Completada", 
                        f"Orden {folio_orden_nombre} y Lote {folio_lote_nombre} creados con éxito.\n"
                        f"Se insertaron {guardados} folios nuevos."
                    )

                self._refresh_ordenes_table()
                self._refresh_lotes_table()
            finally:
                save_loading.close()

        except Exception as err:
            logger.error(f"Error importando lote desde Excel: {err}")
            QMessageBox.critical(self, "Error de Importación", f"No se pudo procesar el archivo Excel: {err}")

    def _on_importar_pdf(self):
        """Abre diálogo para seleccionar uno o varios archivos PDF de Pases de Caja y lanza la previsualización modal."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Seleccionar Boletas o Pases de Caja en PDF",
            "",
            "Archivos PDF (*.pdf)"
        )
        if not file_paths:
            return

        from cancunbot.src.ui.dialogs.pdf_analysis_dialog import PdfAnalysisDialog
        dialog = PdfAnalysisDialog(
            pdf_paths=file_paths,
            api_client=self.api_client,
            db_connector=self.db_connector,
            usuario_id=self.usuario_id,
            parent=self
        )
        if dialog.exec() == QDialog.Accepted:
            self._write_log(f"Lote #{dialog.created_lote_id} generado exitosamente desde importación PDF.")
            self._refresh_lotes_table()

    def _on_descargar_plantilla(self):
        """Genera y descarga una plantilla Excel vacía con el formato de columnas aceptado por el validador."""
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

            # Escribir encabezados oficiales requeridos por el importador
            ws.cell(row=1, column=1, value="FOLIO_ELECTRONICO")
            ws.cell(row=1, column=2, value="FOLIO_PASE_CAJA")
            ws.cell(row=1, column=3, value="RFC")
            ws.cell(row=1, column=4, value="DESARROLLO")

            # Ejemplo visual en la fila 2
            ws.cell(row=2, column=1, value="F-2026-615-31044")
            ws.cell(row=2, column=2, value="")
            ws.cell(row=2, column=3, value="XAXX010101000")
            ws.cell(row=2, column=4, value="VALMIRA LIVING")

            ws.cell(row=3, column=1, value="")
            ws.cell(row=3, column=2, value="987654321")
            ws.cell(row=3, column=3, value="CIN010904D31")
            ws.cell(row=3, column=4, value="")

            wb.save(file_path)
            QMessageBox.information(
                self, "Plantilla Descargada", 
                f"La plantilla se guardó en:\n{file_path}\n\nPuedes llenar los folios electrónicos en la columna 'FOLIO_ELECTRONICO' o los pases de caja en 'FOLIO_PASE_CAJA'."
            )
        except Exception as e:
            logger.error(f"Error generando plantilla Excel: {e}")
            QMessageBox.critical(self, "Error al guardar", f"No se pudo generar la plantilla: {e}")

    def _on_gear_clicked(self):
        """Muestra un menú contextual con las URLs de los portales activos (según el modo)."""
        menu = QMenu(self)
        menu.setObjectName("botMenu")

        url_recibos = "https://recibo.tesoreriacancun.com"
        url_facturas = "https://benitojuarez.expidefactura.com/"

        try:
            if self.api_client and getattr(self.api_client, 'connect_via_api', False):
                res_r = self.api_client.request("GET", "/api/docs/config/parametro/CANCUN_PORTAL_RECIBO_URL")
                res_f = self.api_client.request("GET", "/api/docs/config/parametro/CANCUN_PORTAL_FACTURA_URL")
                if res_r.get("valor"): url_recibos = res_r.get("valor")
                if res_f.get("valor"): url_facturas = res_f.get("valor")
            else:
                with self.db_connector.get_session() as session:
                    repo = ConfigRepository(session)
                    db_url_r = repo.get_parametro("CANCUN_PORTAL_RECIBO_URL")
                    db_url_f = repo.get_parametro("CANCUN_PORTAL_FACTURA_URL")
                    if db_url_r:
                        url_recibos = db_url_r
                    if db_url_f:
                        url_facturas = db_url_f
        except Exception as e:
            logger.error(f"Error cargando URLs para menú de configuración: {e}")

        # Determinar cuál URL mostrar como activa según el switch de modo
        es_modo_facturas = self.switch_modo.isChecked()
        if es_modo_facturas:
            action = menu.addAction(f"🔗 Portal Facturación: {url_facturas}")
        else:
            action = menu.addAction(f"🔗 Portal Recibos: {url_recibos}")
        action.setEnabled(False)

        menu.exec_(QCursor.pos())

    def _on_user_clicked(self):
        """Muestra la información de perfil del usuario firmado y opción para desloguear."""
        menu = QMenu(self)
        menu.setObjectName("botMenu")

        nombre_usuario = f"Usuario ID: {self.usuario_id}"
        try:
            if self.api_client and getattr(self.api_client, 'connect_via_api', False):
                parent_window = self.window()
                cached_name = getattr(parent_window, 'current_username', None)
                if not cached_name and parent_window and parent_window.parent():
                    cached_name = getattr(parent_window.parent(), 'current_username', None)
                
                if cached_name:
                    nombre_usuario = cached_name
                elif self.usuario_id:
                    users_list = self.api_client.request("GET", "/api/auth/users")
                    if isinstance(users_list, list):
                        for u in users_list:
                            if u.get("usuario_id") == self.usuario_id or u.get("id") == self.usuario_id:
                                nombre_usuario = u.get("nombre") or u.get("username") or nombre_usuario
                                break
            else:
                with self.db_connector.get_session() as session:
                    from sar.src.storage.models import Usuario
                    db_user = session.get(Usuario, self.usuario_id)
                    if db_user and db_user.nombre:
                        nombre_usuario = db_user.nombre
        except Exception as e:
            logger.error(f"Error cargando perfil de usuario: {e}")

        menu.addAction(f"👤 Operador: {nombre_usuario}").setEnabled(False)
        menu.addSeparator()
        
        logout_action = menu.addAction("🚪 Cerrar Sesión")
        logout_action.triggered.connect(self._handle_logout_intent)
        
        menu.exec_(QCursor.pos())

    def _handle_logout_intent(self):
        """Valida que no haya diálogos o procesos activos antes de notificar la señal de logout."""
        open_dialogs = getattr(self, '_open_dialogs', [])
        if open_dialogs:
            reply = QMessageBox.question(
                self, "Confirmar Cierre de Sesión",
                f"Tiene una o más ventanas de Control R2F abiertas ({len(open_dialogs)}).\n"
                "¿Está seguro de que desea cerrar la sesión de todos modos? Se cerrarán las ventanas activas.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            
            # Cerrar todas las ventanas abiertas en el pool
            for diag in list(open_dialogs):
                try:
                    diag.reject()
                except Exception:
                    pass
            self._open_dialogs = []
        else:
            reply = QMessageBox.question(
                self, "Cerrar Sesión",
                "¿Estás seguro de que deseas cerrar sesión?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        self.logout_requested.emit()

    def _write_log(self, text: str):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.txt_console.append(f"[{timestamp}] {text}")

    def closeEvent(self, event):
        # Primero validar diálogos activos
        open_dialogs = getattr(self, '_open_dialogs', [])
        if open_dialogs:
            reply = QMessageBox.question(
                self, "Cerrar Ventana",
                "Tiene ventanas secundarias de Control R2F abiertas.\n"
                "¿Desea cerrar el bot y todas sus ventanas vinculadas?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return

        if self.active_worker and self.active_worker.isRunning():
            reply = QMessageBox.question(
                self, "Bot en ejecución",
                "El bot de descarga está activo. ¿Deseas detenerlo y cerrar?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.active_worker.stop()
                self.active_worker.wait()
                
                # Cerrar secundarias
                for diag in list(open_dialogs):
                    try:
                        diag.reject()
                    except Exception:
                        pass
                event.accept()
            else:
                event.ignore()
        else:
            # Cerrar secundarias
            for diag in list(open_dialogs):
                try:
                    diag.reject()
                except Exception:
                    pass
            event.accept()

    def _verify_paths(self):
        """Replicando la lógica de verificación de acceso a la ruta de Face A."""
        if hasattr(self, 'status_indicator') and self.status_indicator:
            self.status_indicator.set_status("checking")
            
            from sar.src.core.access_manager import PathVerifyThread
            target_dir = self.selected_custom_path if self.selected_custom_path else self.default_output_dir
            
            self.path_verify_thread = PathVerifyThread(target_dir, self)
            self.path_verify_thread.result_ready.connect(self._on_path_verified)
            self.path_verify_thread.start()

    def _on_path_verified(self, path_str, has_access, error_message):
        self.is_path_online = has_access
        if has_access:
            self.status_indicator.set_status("online", "CONECTADO")
            self._write_log(f"Ruta de almacenamiento 'CANCUN_PDF_BASE_PATH' accesible y verificada: {path_str}")
        else:
            self.status_indicator.set_status("offline", "NO CONECTADO")
            self._write_log(f"⚠️ ADVERTENCIA CRÍTICA: La ruta por defecto 'CANCUN_PDF_BASE_PATH' ('{path_str}') no está accesible o su unidad de red está desconectada.")
            self._write_log("👉 Por favor revise que la unidad de red esté conectada o reporte el problema al área de TI.")

    def _on_browse_path_clicked(self):
        """Diálogo de selección de directorio de almacenamiento, replicando la confirmación de Face A."""
        if self.active_worker and self.active_worker.isRunning():
            return

        reply = QMessageBox.question(
            self,
            "Confirmar Cambio de Ruta",
            f"Se recomienda utilizar la ruta por defecto ({self.default_output_dir}) para la sincronización y auditoría.\n\n¿Estás seguro de que deseas cambiar la ruta de descarga?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.No:
            return
            
        dir_path = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Almacenamiento de Recibos")
        if dir_path:
            self.selected_custom_path = dir_path
            # Truncar visualmente la ruta si es demasiado larga
            display_path = dir_path if len(dir_path) < 35 else "..." + dir_path[-32:]
            self.lbl_download_path_display.setText(display_path)
            self._write_log(f"Ruta de almacenamiento cambiada a: {dir_path}")
            self._verify_paths()
