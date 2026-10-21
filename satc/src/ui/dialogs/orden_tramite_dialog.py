"""
SATC — Diálogo Modal para Creación de Orden de Trámites y Renglones (Solicitudes)
Implementa el flujo en cascada:
  1. Selección de Desarrollo
  2. Selección de Régimen en Condominio (con conteo en vivo de UPEs y exclusión de vendidas)
  3. Selección de Tipo de Trámite (Renglón de Solicitud)
  4. Expediente Municipal y generación atómica de trámites.

Cumple con Atomic Design y tokens de sar/src/ui/design_system/.
"""
import logging
from typing import Dict, Any, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QWidget, QScrollArea, QMessageBox
)

from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.tokens.typography import Typography
from sar.src.ui.design_system.tokens.spacing import Spacing
from sar.src.ui.design_system.components import (
    CustomButton, CustomInput, CustomComboBox, CustomLabel, GLMessageDialog, DialogType
)
from satc.src.services.housing_life_cycle_service import HousingLifeCycleService
from satc.src.storage.satc_repos import (
    RegimenCondominioRepository, ViviendaRepository, OrdenTramiteRepository, SolicitudTramiteRepository
)
from satc.src.storage.satc_models import TipoTramite, RegimenCondominio

logger = logging.getLogger(__name__)


class OrdenTramiteDialog(QDialog):
    """Diálogo modal guiado para la apertura de una Macro-Orden de Trámites y su primera Solicitud."""
    orden_creada = Signal(int)  # Emite el orden_tramite_id al crearse

    def __init__(self, db_connector, usuario_id: int, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.usuario_id = usuario_id
        
        self.setWindowTitle("Apertura de Orden de Trámites y Gestión de Viviendas")
        self.setMinimumWidth(640)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {Colors.SURFACE_LIGHT}; color: {Colors.TEXT_LIGHT_PRIMARY};")
        
        self._init_ui()
        self._cargar_catalogos()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # 1. Cabecera
        header_layout = QVBoxLayout()
        title = CustomLabel("Nueva Orden de Trámites por Desarrollo / Régimen", variant="header")
        subtitle = CustomLabel("Gobierna el ciclo de vida, vigencias y prevención de omisiones por vivienda.", variant="muted")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        # Línea divisoria
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {Colors.BORDER_LIGHT};")
        main_layout.addWidget(line)

        # 2. Formulario en Cascada
        form_layout = QVBoxLayout()
        form_layout.setSpacing(12)

        # Paso 1: Desarrollo
        lbl_des = CustomLabel("1. Desarrollo Matriz:", variant="body")
        self.combo_desarrollo = CustomComboBox()
        self.combo_desarrollo.currentIndexChanged.connect(self._on_desarrollo_changed)
        form_layout.addWidget(lbl_des)
        form_layout.addWidget(self.combo_desarrollo)

        # Paso 2: Régimen mz
        lbl_reg = CustomLabel("2. Régimen mz (Macro-Lote):", variant="body")
        self.combo_regimen = CustomComboBox()
        self.combo_regimen.currentIndexChanged.connect(self._on_regimen_changed)
        form_layout.addWidget(lbl_reg)
        form_layout.addWidget(self.combo_regimen)

        # Card de Resumen en Vivo del Régimen Seleccionado
        self.card_resumen = QFrame()
        self.card_resumen.setStyleSheet(
            f"background-color: {Colors.NEUTRAL_BG}; "
            f"border: 1px solid {Colors.BORDER_LIGHT}; "
            f"border-radius: 8px; padding: 12px;"
        )
        card_layout = QVBoxLayout(self.card_resumen)
        
        self.lbl_info_upes = CustomLabel("Seleccione un desarrollo y régimen para evaluar el universo de viviendas.", variant="muted")
        card_layout.addWidget(self.lbl_info_upes)
        
        form_layout.addWidget(self.card_resumen)

        # Paso 3: Tipo de Trámite Inicial (Renglón de Solicitud)
        lbl_trm = CustomLabel("3. Tipo de Trámite a Radicar (Primer Renglón):", variant="body")
        self.combo_tipo_tramite = CustomComboBox()
        form_layout.addWidget(lbl_trm)
        form_layout.addWidget(self.combo_tipo_tramite)

        # Paso 4: Expediente Municipal / Descripción
        lbl_exp = CustomLabel("4. Expediente Municipal o Folio de Radicación (Opcional):", variant="body")
        self.input_expediente = CustomInput(placeholder="Ej: EXP-CAT-2026-8812")
        form_layout.addWidget(lbl_exp)
        form_layout.addWidget(self.input_expediente)

        main_layout.addLayout(form_layout)

        # 3. Botones de Acción
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.btn_cancelar = CustomButton("Cancelar", variant="secondary")
        self.btn_cancelar.clicked.connect(self.reject)
        
        self.btn_crear = CustomButton("Crear Orden y Renglón de Solicitud", variant="primary")
        self.btn_crear.clicked.connect(self._on_crear_orden)
        self.btn_crear.setEnabled(False)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancelar)
        btn_layout.addWidget(self.btn_crear)
        main_layout.addLayout(btn_layout)

    def _cargar_catalogos(self):
        """Carga inicial de desarrollos y tipos de trámite."""
        with self.db_connector.get_session() as session:
            from sar.src.storage.models import Desarrollo
            desarrollos = session.query(Desarrollo).filter(Desarrollo.activo.is_(True)).order_by(Desarrollo.nombre.asc()).all()
            
            self.combo_desarrollo.clear()
            self.combo_desarrollo.addItem("-- Seleccione un Desarrollo --", userData=None)
            for d in desarrollos:
                self.combo_desarrollo.addItem(d.nombre, userData=d.desarrollo_id)

            tipos = session.query(TipoTramite).filter(TipoTramite.activo.is_(True)).order_by(TipoTramite.nombre.asc()).all()
            self.combo_tipo_tramite.clear()
            for t in tipos:
                dias = f" ({t.dias_vigencia} días vigencia)" if t.dias_vigencia > 0 else " (Vigencia indefinida)"
                self.combo_tipo_tramite.addItem(f"{t.nombre}{dias}", userData=t.tipo_tramite_id)

    def _on_desarrollo_changed(self, index: int):
        desarrollo_id = self.combo_desarrollo.currentData()
        self.combo_regimen.clear()
        self.btn_crear.setEnabled(False)
        self.lbl_info_upes.setText("Seleccione un régimen para evaluar el universo de viviendas.")
        self.lbl_info_upes.setStyleSheet(f"color: {Colors.TEXT_LIGHT_MUTED};")

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
        if not regimen_id:
            self.btn_crear.setEnabled(False)
            self.lbl_info_upes.setText("Seleccione un régimen para evaluar el universo de viviendas.")
            self.lbl_info_upes.setStyleSheet(f"color: {Colors.TEXT_LIGHT_MUTED};")
            return

        with self.db_connector.get_session() as session:
            service = HousingLifeCycleService(session)
            auditoria = service.detectar_omisiones_regimen(regimen_id)
            activas = service.obtener_viviendas_activas_no_vendidas(regimen_id)
            
            tot = auditoria["total_upes_declaradas"]
            reg = auditoria["upes_registradas"]
            disp = len(activas)
            vendidas = reg - disp

            msg = (
                f"<b>Régimen:</b> {auditoria['regimen']}<br>"
                f"• <b>Total UPEs Fiduciarias:</b> {tot}<br>"
                f"• <b>UPEs dadas de alta en sistema:</b> {reg}<br>"
                f"• <b>Viviendas Vendidas/Escrituradas (Excluidas):</b> {vendidas}<br>"
                f"• <font color='{Colors.SUCCESS_DARK}'><b>Universo Activo a Tramitar en este Renglón:</b> {disp} UPEs</font>"
            )
            self.lbl_info_upes.setText(msg)
            self.btn_crear.setEnabled(True)

    def _on_crear_orden(self):
        desarrollo_id = self.combo_desarrollo.currentData()
        regimen_id = self.combo_regimen.currentData()
        tipo_tramite_id = self.combo_tipo_tramite.currentData()
        expediente = self.input_expediente.text().strip() or None

        if not desarrollo_id or not regimen_id or not tipo_tramite_id:
            GLMessageDialog.show_message(
                self, "Campos Requeridos", "Debe seleccionar un desarrollo, régimen y tipo de trámite.",
                dialog_type=DialogType.WARNING
            )
            return

        try:
            with self.db_connector.get_session() as session:
                service = HousingLifeCycleService(session)
                regimen_repo = RegimenCondominioRepository(session)
                regimen = regimen_repo.get_by_id(regimen_id)
                
                # 1. Crear Orden Macro
                orden_repo = OrdenTramiteRepository(session)
                orden = orden_repo.create(
                    desarrollo_id=desarrollo_id,
                    regimen_id=regimen_id,
                    usuario_id=self.usuario_id,
                    descripcion=f"Apertura de trámites para {regimen.nombre_regimen}"
                )
                
                # 2. Crear Primer Renglón (solicitud_tramite) con filtro inteligente
                solicitud = service.crear_solicitud_tramite(
                    orden_tramite_id=orden.orden_tramite_id,
                    tipo_tramite_id=tipo_tramite_id,
                    usuario_id=self.usuario_id,
                    expediente_municipal=expediente
                )
                
                orden_id = orden.orden_tramite_id
                folio_sol = solicitud.folio_solicitud
                tot_viv = solicitud.total_viviendas

            GLMessageDialog.show_message(
                self,
                "Orden de Trámites Creada",
                f"Se creó con éxito la orden y el primer renglón:\n\n"
                f"• Solicitud: {folio_sol}\n"
                f"• Viviendas asociadas: {tot_viv} UPEs\n\n"
                f"El lote está listo para asignación de pases de caja y ejecución de bots.",
                dialog_type=DialogType.SUCCESS
            )
            self.orden_creada.emit(orden_id)
            self.accept()

        except Exception as e:
            logger.error(f"Error al crear orden de trámite: {e}", exc_info=True)
            GLMessageDialog.show_message(
                self, "Error al Crear Orden", f"Ocurrió un error al procesar la solicitud:\n{e}",
                dialog_type=DialogType.ERROR
            )
