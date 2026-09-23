"""
CancunBot — Worker Thread: Generación de Facturas (BOT_FACTURA_CUN)
Usa Playwright (Sync API) ejecutándose en un hilo secundario de PySide6 (QThread).
"""
import logging
import os
import shutil
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal
from playwright.sync_api import sync_playwright

from sqlalchemy import text
from sar.src.core.playwright_setup import resolve_chromium_executable
from sar.src.storage.db_connector import DatabaseConnector
from sar.src.storage.repositories import ConfigRepository

from cancunbot.src.storage.cancunbot_repos import LoteFolioRepository, ReciboCancunRepository
from cancunbot.src.pages.expide_factura_page import ExpideFacturaPage

logger = logging.getLogger(__name__)


class BotFacturaCunWorker(QThread):
    """
    Worker que interactúa con el portal de facturación Benito Juárez.
    """
    status_changed = Signal(str)
    progress_changed = Signal(int, int)
    metric_updated = Signal(str, int)
    finished_processing = Signal(bool, str)
    folio_status_changed = Signal(dict)

    def __init__(self, db_connector: DatabaseConnector, lote_id: int, headless: bool = True, custom_output_dir: Optional[str] = None, api_client=None, correo_usuario: str = "", parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.lote_id = lote_id
        self.headless = headless
        self.custom_output_dir = custom_output_dir
        self.api_client = api_client
        self.correo_usuario = correo_usuario
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True
        self.status_changed.emit("🚫 Detención del bot solicitada. Finalizando el folio actual...")

    def run(self):
        self.status_changed.emit("🚀 Iniciando Bot de Facturas Cancún (BOT_FACTURA_CUN)...")
        playwright_inst = None
        browser = None
        browser_context = None

        use_api = (self.api_client is not None and getattr(self.api_client, "connect_via_api", False))

        try:
            self.status_changed.emit("Cargando parámetros y localizadores de portal...")
            if use_api:
                resp_cfg = self.api_client.request("GET", "/api/docs/cancun/bot-config")
                portal_url = resp_cfg.get("portal_factura_url", "https://benitojuarez.expidefactura.com/")
                output_dir_raw = self.custom_output_dir if self.custom_output_dir else resp_cfg.get("output_dir_raw", "Y:\\R2F\\Recibos")
                timeout_ms = int(resp_cfg.get("timeout_ms", 30000))
                locators = resp_cfg.get("locators", {}) # Asegurarse de que el endpoint incluya los de CANCUN_FACTURA
            else:
                with self.db_connector.get_session() as session:
                    config_repo = ConfigRepository(session)
                    portal_url = config_repo.get_parametro("CANCUN_PORTAL_FACTURA_URL") or "https://benitojuarez.expidefactura.com/"
                    output_dir_raw = self.custom_output_dir if self.custom_output_dir else (config_repo.get_parametro("CANCUN_PDF_BASE_PATH") or "Y:\\R2F\\Recibos")
                    timeout_ms = int(config_repo.get_parametro("CANCUN_BOT_TIMEOUT_MS") or 30000)

                    db_locators = config_repo.get_localizadores_portal("CANCUN_FACTURA")
                    locators = {}
                    for k, v in db_locators.items():
                        locators[k] = {
                            "estrategia_selector": v.estrategia_selector,
                            "valor_selector": v.valor_selector
                        }

            output_path = Path(output_dir_raw)
            try:
                output_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Error creando directorio final {output_path}: {e}")
                output_path = Path("C:\\Users\\dramos\\Documents\\Proyecto_CapturaBot\\PDF_Recibos")
                output_path.mkdir(parents=True, exist_ok=True)

            self.status_changed.emit(f"Obteniendo recibos PENDIENTE_FACTURAR del lote {self.lote_id}...")
            if use_api:
                # Mock temporal en modo API, se recomienda crear un endpoint específico
                pendientes = [] 
            else:
                with self.db_connector.get_session() as session:
                    # Traer recibos con estado PENDIENTE_FACTURAR del lote
                    # (Esto requiere un join desde folio_cancun)
                    query = text("""
                        SELECT r.recibo_id, r.rfc, r.correo_factura, f.folio_electronico, r.total, r.detalle_concepto as datos_adicionales, r.folio_id
                        FROM cancunbot_produccion.recibo_cancun r
                        JOIN cancunbot_produccion.folio_cancun f ON r.folio_id = f.folio_id
                        JOIN sar_catalogo.estado_sistema e ON r.estado_id = e.estado_id
                        WHERE f.lote_id = :lid AND e.codigo = 'PENDIENTE_FACTURAR'
                    """)
                    result = session.execute(query, {"lid": self.lote_id}).fetchall()
                    pendientes = [dict(row._mapping) for row in result]

            total_pendientes = len(pendientes)
            self.status_changed.emit(f"Se encontraron {total_pendientes} recibos listos para facturar.")

            if total_pendientes == 0:
                self.finished_processing.emit(True, "No hay recibos pendientes de facturar en este lote.")
                return

            exitosos = 0
            errores = 0

            self.status_changed.emit("Resolviendo ejecutable del navegador...")
            exec_path = resolve_chromium_executable(progress_callback=self.status_changed.emit)

            self.status_changed.emit("Iniciando instancia de Playwright...")
            playwright_inst = sync_playwright().start()
            
            launch_kwargs = {
                "headless": self.headless,
                "args": ["--start-maximized", "--disable-blink-features=AutomationControlled", "--no-sandbox"]
            }
            if exec_path:
                launch_kwargs["executable_path"] = exec_path
                self.status_changed.emit(f"Usando ejecutable de navegador: {exec_path}")

            browser = playwright_inst.chromium.launch(**launch_kwargs)
            
            tmp_download_dir = output_path / "tmp_downloads_factura"
            tmp_download_dir.mkdir(exist_ok=True)
            
            browser_context = browser.new_context(
                accept_downloads=True,
                viewport={"width": 1366, "height": 768}
            )

            page = browser_context.new_page()
            page.set_default_timeout(timeout_ms)

            factura_page = ExpideFacturaPage(page, locators)
            
            # Navegar una sola vez al inicio si la sesión se mantiene
            factura_page.navegar(portal_url)

            for i, rec in enumerate(pendientes, 1):
                if self._stop_requested:
                    break

                recibo_id = rec["recibo_id"]
                folio_id = rec["folio_id"]
                rfc = rec["rfc"] or ""
                # Si el usuario logueado tiene correo, usar ese por prioridad, si no, usar el registrado en el recibo
                correo = self.correo_usuario if self.correo_usuario else (rec["correo_factura"] or "")
                folio_elec = rec["folio_electronico"] or ""
                importe = str(rec["total"]) if rec["total"] else "0"
                datos_adicionales = rec["datos_adicionales"] or {}
                
                # Obtener Uso CFDI (default 1 = Adquisición de mercancías)
                uso_cfdi = datos_adicionales.get("uso_cfdi", "1")

                self.progress_changed.emit(i, total_pendientes)
                self.folio_status_changed.emit({
                    "referencia": folio_elec,
                    "rfc": rfc,
                    "estado": "PROCESANDO FACTURACIÓN"
                })
                self.status_changed.emit(f"Generando factura para folio {folio_elec} (RFC: {rfc})...")

                success = factura_page.generar_factura(rfc, correo, folio_elec, importe, uso_cfdi)

                if success:
                    ruta_xml_tmp, ruta_pdf_tmp = factura_page.descargar_archivos()
                    
                    if ruta_xml_tmp and ruta_pdf_tmp:
                        # Mover a ruta final
                        base_name = f"{folio_elec}_FACTURA"
                        final_xml_path = output_path / f"{base_name}.xml"
                        final_pdf_path = output_path / f"{base_name}.pdf"
                        
                        shutil.move(ruta_xml_tmp, str(final_xml_path))
                        shutil.move(ruta_pdf_tmp, str(final_pdf_path))
                        
                        # Actualizar estado en BD a FACTURADO
                        if not use_api:
                            with self.db_connector.get_session() as session:
                                st_facturado = session.execute(
                                    text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad = 'recibo_cancun' AND codigo = 'FACTURADO'")
                                ).scalar()
                                session.execute(
                                    text("UPDATE cancunbot_produccion.recibo_cancun SET estado_id = :st WHERE recibo_id = :rid"),
                                    {"st": st_facturado, "rid": recibo_id}
                                )
                                session.commit()

                        exitosos += 1
                        self.metric_updated.emit("exitosos", 1)
                        self.folio_status_changed.emit({"referencia": folio_elec, "rfc": rfc, "estado": "FACTURADO"})
                    else:
                        errores += 1
                        self.metric_updated.emit("errores", 1)
                        self.folio_status_changed.emit({"referencia": folio_elec, "rfc": rfc, "estado": "ERROR DESCARGA FACTURA"})
                else:
                    errores += 1
                    self.metric_updated.emit("errores", 1)
                    self.folio_status_changed.emit({"referencia": folio_elec, "rfc": rfc, "estado": "ERROR FACTURACIÓN"})
                    
                    if not use_api:
                        with self.db_connector.get_session() as session:
                            st_error = session.execute(
                                text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad = 'recibo_cancun' AND codigo = 'ERROR_FACTURA'")
                            ).scalar()
                            session.execute(
                                text("UPDATE cancunbot_produccion.recibo_cancun SET estado_id = :st WHERE recibo_id = :rid"),
                                {"st": st_error, "rid": recibo_id}
                            )
                            session.commit()

                # Recargar portal para el siguiente
                if i < total_pendientes and not self._stop_requested:
                    factura_page.navegar(portal_url)

            # Cleanup tmp dir
            try:
                if tmp_download_dir.exists():
                    shutil.rmtree(tmp_download_dir)
            except Exception as e:
                logger.error(f"Error limpiando directorio temporal: {e}")

            msg = f"Proceso Finalizado. {exitosos} exitosos, {errores} errores."
            if self._stop_requested:
                msg = f"Proceso Detenido por usuario. {exitosos} exitosos, {errores} errores."
            self.finished_processing.emit(True, msg)

        except Exception as e:
            trace = traceback.format_exc()
            logger.error(f"Error fatal en BotFacturaCunWorker: {trace}")
            self.status_changed.emit(f"Error crítico: {e}")
            self.finished_processing.emit(False, str(e))
        finally:
            if browser_context:
                browser_context.close()
            if browser:
                browser.close()
            if playwright_inst:
                playwright_inst.stop()
