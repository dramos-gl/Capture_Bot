"""Vista Administrativa de Unificación / Fusión de Lotes de Asignación (Procesos Especiales)."""

from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QLabel,
    QCheckBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QBrush, QCursor

from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.theme_manager import ThemeManager
from sar.src.ui.design_system.components.molecules.gl_combo_box import CustomComboBox
from sar.src.ui.design_system.components.atoms.gl_button import CustomButton
from sar.src.ui.design_system.components.atoms.gl_label import CustomLabel
from sar.src.ui.design_system.components.atoms.gl_checkbox import CustomCheckBox
from sar.src.ui.design_system.components.organisms.gl_message_dialog import GLMessageBox as QMessageBox
from sar.src.ui.design_system.components.molecules.gl_info_banner import GLInfoBanner
from sar.src.ui.design_system.utils.icons import Icons


class FusionLotesWorker(QThread):
    """Worker en segundo plano para ejecutar la transacción pesimista de fusión de lotes."""
    finished = Signal(bool, dict, str)

    def __init__(self, ui_service, lote_maestro_id: int, lotes_absorber_ids: List[int],
                 usuario_id: int, sesion_id: Optional[int] = None):
        super().__init__()
        self.ui_service = ui_service
        self.lote_maestro_id = lote_maestro_id
        self.lotes_absorber_ids = lotes_absorber_ids
        self.usuario_id = usuario_id
        self.sesion_id = sesion_id

    def run(self):
        try:
            res = self.ui_service.fusionar_lotes(
                lote_maestro_id=self.lote_maestro_id,
                lotes_absorber_ids=self.lotes_absorber_ids,
                usuario_id=self.usuario_id,
                sesion_id=self.sesion_id
            )
            self.finished.emit(True, res or {}, "")
        except Exception as e:
            self.finished.emit(False, {}, str(e))


class FusionLotesView(QWidget):
    """Vista de Administración para unificar y fusionar múltiples lotes de asignación en uno solo."""

    def __init__(self, db_connector, current_user=None, current_session=None, can_edit=True, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.current_user = current_user
        self.current_session = current_session
        self.can_edit = can_edit

        from sar.src.services.inventario_ui_service import InventarioUIService
        self.inventario_ui_service = InventarioUIService(self.db_connector)

        self._lotes_candidatos: List[Dict[str, Any]] = []
        self._notarias_map: Dict[str, int] = {}
        self._colaboradores_map: Dict[str, int] = {}

        self._build_ui()
        self._load_destinatarios()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # 1. Cabecera Informativa
        header_lay = QVBoxLayout()
        header_lay.setSpacing(4)
        lbl_title = CustomLabel("🔗 Unificación / Fusión de Lotes de Asignación", variant="header")
        lbl_subtitle = CustomLabel(
            "Consolide y absorba múltiples lotes preexistentes de una misma Notaría o Colaborador en un único Lote Maestro, "
            "evitando la fragmentación de expedientes y preservando la trazabilidad completa.",
            variant="muted"
        )
        header_lay.addWidget(lbl_title)
        header_lay.addWidget(lbl_subtitle)
        main_layout.addLayout(header_lay)

        # Banner de Advertencia de Gobernanza
        self.banner_info = GLInfoBanner(
            "Modo Exclusivo de Administrador: Al fusionar lotes, todos los derechos y expedientes asociados se reasignan al Lote Maestro seleccionado. Los lotes absorbidos se consolidan y depuran del inventario activo.",
            variant="info",
            parent=self
        )
        main_layout.addWidget(self.banner_info)

        # 2. Tarjeta de Selección de Destinatario y Lote Maestro
        card_filtros = QFrame(self)
        card_filtros.setObjectName("cardFrame")
        form_lay = QFormLayout(card_filtros)
        form_lay.setContentsMargins(16, 16, 16, 16)
        form_lay.setSpacing(12)

        # Selector Tipo Destino
        self.cb_tipo_destino = CustomComboBox(card_filtros, control_size="md")
        self.cb_tipo_destino.addItems(["-- Seleccione Tipo Destino --", "NOTARIA", "COLABORADOR"])
        self.cb_tipo_destino.currentTextChanged.connect(self._on_tipo_destino_changed)
        form_lay.addRow("Tipo Destino:", self.cb_tipo_destino)

        # Selector Destinatario
        self.cb_destinatario = CustomComboBox(card_filtros, control_size="md")
        self.cb_destinatario.addItem("-- Seleccione Destinatario --", None)
        self.cb_destinatario.currentIndexChanged.connect(self._on_destinatario_changed)
        form_lay.addRow("Destinatario:", self.cb_destinatario)

        # Selector Lote Maestro
        self.cb_lote_maestro = CustomComboBox(card_filtros, control_size="md")
        self.cb_lote_maestro.addItem("-- Seleccione Lote Maestro (Destino) --", None)
        self.cb_lote_maestro.currentIndexChanged.connect(self._on_lote_maestro_changed)
        form_lay.addRow("Lote Maestro (Conservar):", self.cb_lote_maestro)

        main_layout.addWidget(card_filtros)

        # 3. Tabla de Lotes Candidatos a Absorber
        lbl_sec_absorber = CustomLabel("📦 Lotes a Absorber y Fusionar:", variant="subheader")
        main_layout.addWidget(lbl_sec_absorber)

        self.table_lotes = QTableWidget(self)
        self.table_lotes.setColumnCount(6)
        self.table_lotes.setHorizontalHeaderLabels([
            "Seleccionar", "ID Lote", "Fecha Creación", "Derechos", "Solicitante", "Observaciones"
        ])
        self.table_lotes.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_lotes.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_lotes.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_lotes.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_lotes.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_lotes.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table_lotes.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_lotes.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_lotes.setAlternatingRowColors(True)
        self.table_lotes.setShowGrid(False)
        self.table_lotes.verticalHeader().setVisible(False)
        self.table_lotes.verticalHeader().setDefaultSectionSize(26)
        main_layout.addWidget(self.table_lotes, stretch=1)

        # 4. Pie de Acciones
        bottom_lay = QHBoxLayout()
        bottom_lay.setContentsMargins(0, 8, 0, 0)

        self.lbl_resumen = CustomLabel("Seleccione el destinatario y los lotes a procesar.", variant="muted")
        bottom_lay.addWidget(self.lbl_resumen)
        bottom_lay.addStretch()

        self.btn_select_all = CustomButton("Seleccionar Todos", is_secondary=True, control_size="sm", parent=self)
        self.btn_select_all.clicked.connect(self._toggle_select_all)
        bottom_lay.addWidget(self.btn_select_all)

        self.btn_fusionar = CustomButton("Ejecutar Fusión de Lotes", is_secondary=False, control_size="md", parent=self)
        self.btn_fusionar.setIcon(Icons.sincronizar(Colors.SURFACE_LIGHT))
        self.btn_fusionar.setEnabled(False)
        self.btn_fusionar.clicked.connect(self._on_ejecutar_fusion)
        bottom_lay.addWidget(self.btn_fusionar)

        main_layout.addLayout(bottom_lay)

    def _load_destinatarios(self):
        """Carga los catálogos de notarias y colaboradores."""
        try:
            notarias = self.inventario_ui_service.get_notarias()
            colaboradores = self.inventario_ui_service.get_colaboradores()

            self._notarias_map = {n["nombre"]: n["notaria_id"] for n in notarias}
            self._colaboradores_map = {c["nombre"]: c["colaborador_id"] for c in colaboradores}
        except Exception as e:
            print("[FusionLotesView] Error al cargar catálogos de destinatarios:", e)

    def refresh_data(self):
        """Called automatically when the view is selected in AdminWindow."""
        self._load_destinatarios()
        if self.cb_destinatario.currentIndex() > 0:
            self._on_destinatario_changed()

    def _on_tipo_destino_changed(self, text):
        self.cb_destinatario.clear()
        self.cb_lote_maestro.clear()
        self.table_lotes.setRowCount(0)
        self._lotes_candidatos = []
        self.btn_fusionar.setEnabled(False)

        if text == "NOTARIA":
            self.cb_destinatario.addItem("-- Seleccione Notaría --", None)
            for nom, n_id in self._notarias_map.items():
                self.cb_destinatario.addItem(nom, n_id)
        elif text == "COLABORADOR":
            self.cb_destinatario.addItem("-- Seleccione Colaborador --", None)
            for nom, c_id in self._colaboradores_map.items():
                self.cb_destinatario.addItem(nom, c_id)
        else:
            self.cb_destinatario.addItem("-- Seleccione Tipo Destino Primero --", None)

    def _on_destinatario_changed(self):
        tipo_dest = self.cb_tipo_destino.currentText()
        dest_id = self.cb_destinatario.currentData()

        self.cb_lote_maestro.clear()
        self.table_lotes.setRowCount(0)
        self._lotes_candidatos = []
        self.btn_fusionar.setEnabled(False)

        if not dest_id or tipo_dest not in ("NOTARIA", "COLABORADOR"):
            self.cb_lote_maestro.addItem("-- Seleccione Destinatario Primero --", None)
            return

        try:
            lotes = self.inventario_ui_service.get_lotes_activos_por_destinatario(
                tipo_destino=tipo_dest,
                destinatario_id=dest_id,
                limit=100
            )
            self._lotes_candidatos = lotes

            self.cb_lote_maestro.addItem("-- Seleccione Lote Maestro (Destino) --", None)
            for lote in lotes:
                l_id = lote["lote_asignacion_id"]
                f_str = lote.get("fecha", "")[:10]
                refs_cnt = lote.get("total_referencias", 0)
                solic = lote.get("solicitante_externo")
                solic_txt = f" | {solic}" if solic else ""
                self.cb_lote_maestro.addItem(f"Lote #{l_id} ({f_str}) - {refs_cnt} refs{solic_txt}", l_id)

            if len(lotes) < 2:
                self.lbl_resumen.setText(f"Este destinatario tiene {len(lotes)} lote(s). Se requieren al menos 2 lotes para fusionar.")
            else:
                self.lbl_resumen.setText(f"Se encontraron {len(lotes)} lotes para este destinatario.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron consultar los lotes del destinatario:\n{str(e)}")

    def _on_lote_maestro_changed(self):
        maestro_id = self.cb_lote_maestro.currentData()
        self.table_lotes.setRowCount(0)
        self.btn_fusionar.setEnabled(False)

        if not maestro_id:
            return

        # Poblar tabla con todos los lotes excepto el maestro
        candidatos_absorber = [l for l in self._lotes_candidatos if l["lote_asignacion_id"] != maestro_id]
        self.table_lotes.setRowCount(len(candidatos_absorber))

        for row_idx, lote in enumerate(candidatos_absorber):
            l_id = lote["lote_asignacion_id"]

            chk = CustomCheckBox()
            chk.toggled.connect(self._recalcular_seleccion)

            # Centrar checkbox
            chk_widget = QWidget()
            chk_lay = QHBoxLayout(chk_widget)
            chk_lay.addWidget(chk)
            chk_lay.setAlignment(Qt.AlignCenter)
            chk_lay.setContentsMargins(0, 0, 0, 0)

            self.table_lotes.setCellWidget(row_idx, 0, chk_widget)
            self.table_lotes.setItem(row_idx, 1, QTableWidgetItem(f"#{l_id}"))
            self.table_lotes.setItem(row_idx, 2, QTableWidgetItem(lote.get("fecha", "")))
            self.table_lotes.setItem(row_idx, 3, QTableWidgetItem(str(lote.get("total_referencias", 0))))
            self.table_lotes.setItem(row_idx, 4, QTableWidgetItem(lote.get("solicitante_externo", "")))
            self.table_lotes.setItem(row_idx, 5, QTableWidgetItem(lote.get("observaciones", "")))

            # Guardar ID en columna 1
            self.table_lotes.item(row_idx, 1).setData(Qt.UserRole, l_id)
            self.table_lotes.item(row_idx, 3).setData(Qt.UserRole, lote.get("total_referencias", 0))

        self._recalcular_seleccion()

    def _toggle_select_all(self):
        any_unchecked = False
        for r in range(self.table_lotes.rowCount()):
            w = self.table_lotes.cellWidget(r, 0)
            if w:
                chk = w.findChild(CustomCheckBox)
                if chk and not chk.isChecked():
                    any_unchecked = True
                    break

        new_state = any_unchecked
        for r in range(self.table_lotes.rowCount()):
            w = self.table_lotes.cellWidget(r, 0)
            if w:
                chk = w.findChild(CustomCheckBox)
                if chk:
                    chk.setChecked(new_state)

        self._recalcular_seleccion()

    def _recalcular_seleccion(self):
        maestro_id = self.cb_lote_maestro.currentData()
        if not maestro_id:
            self.btn_fusionar.setEnabled(False)
            return

        seleccionados = []
        total_refs = 0

        for r in range(self.table_lotes.rowCount()):
            w = self.table_lotes.cellWidget(r, 0)
            if w:
                chk = w.findChild(CustomCheckBox)
                if chk and chk.isChecked():
                    l_id = self.table_lotes.item(r, 1).data(Qt.UserRole)
                    refs_cnt = self.table_lotes.item(r, 3).data(Qt.UserRole) or 0
                    seleccionados.append(l_id)
                    total_refs += refs_cnt

        if seleccionados:
            self.btn_fusionar.setEnabled(True)
            self.lbl_resumen.setText(
                f"Lote Maestro #{maestro_id} absorberá {len(seleccionados)} lote(s) "
                f"({', '.join(f'#{i}' for i in seleccionados)}) con un total de {total_refs} derecho(s)."
            )
        else:
            self.btn_fusionar.setEnabled(False)
            self.lbl_resumen.setText("Marque las casillas de los lotes que desea absorber.")

    def _on_ejecutar_fusion(self):
        if not self.can_edit:
            QMessageBox.warning(self, "Acceso Denegado", "No tiene permisos suficientes para fusionar lotes.")
            return

        maestro_id = self.cb_lote_maestro.currentData()
        if not maestro_id:
            QMessageBox.warning(self, "Lote Maestro Requerido", "Por favor seleccione el Lote Maestro.")
            return

        seleccionados = []
        for r in range(self.table_lotes.rowCount()):
            w = self.table_lotes.cellWidget(r, 0)
            if w:
                chk = w.findChild(CustomCheckBox)
                if chk and chk.isChecked():
                    l_id = self.table_lotes.item(r, 1).data(Qt.UserRole)
                    seleccionados.append(l_id)

        if not seleccionados:
            QMessageBox.warning(self, "Selección Requerida", "Debe marcar al menos un lote a absorber.")
            return

        confirm_msg = (
            f"¿Está completamente seguro de proceder con la unificación?\n\n"
            f"• Lote Maestro (Prevalecerá): #{maestro_id}\n"
            f"• Lote(s) a Absorber y Depurar: {', '.join(f'#{i}' for i in seleccionados)}\n\n"
            f"Esta operación es transaccional y registrará una traza en la bitácora de auditoría del sistema."
        )

        reply = QMessageBox.question(self, "Confirmar Fusión de Lotes", confirm_msg, QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # Deshabilitar UI durante el procesamiento
        self.btn_fusionar.setEnabled(False)
        self.btn_select_all.setEnabled(False)

        usr_id = getattr(self.current_user, "usuario_id", None) or 1
        ses_id = getattr(self.current_session, "sesion_id", None)

        self._worker = FusionLotesWorker(
            ui_service=self.inventario_ui_service,
            lote_maestro_id=maestro_id,
            lotes_absorber_ids=seleccionados,
            usuario_id=usr_id,
            sesion_id=ses_id
        )
        self._worker.finished.connect(self._on_fusion_terminada)
        self._worker.start()

    def _on_fusion_terminada(self, success: bool, res: dict, error_msg: str):
        self.btn_select_all.setEnabled(True)

        if success:
            maestro_id = res.get("lote_maestro_id")
            total_transferidas = res.get("total_transferidas", 0)
            absorbidos = res.get("lotes_absorbidos", [])
            abs_txt = ", ".join(f"#{i}" for i in absorbidos)

            QMessageBox.information(
                self,
                "Fusión Completada con Éxito",
                f"Se han unificado exitosamente los lotes.\n\n"
                f"• Lote Maestro: #{maestro_id}\n"
                f"• Lotes Absorbidos y Consolidados: {abs_txt}\n"
                f"• Total de Derechos Reasignados: {total_transferidas}"
            )

            # Refrescar listado
            self._on_destinatario_changed()
        else:
            self.btn_fusionar.setEnabled(True)
            QMessageBox.critical(self, "Error en la Fusión", f"No se pudo completar la fusión de lotes:\n\n{error_msg}")
