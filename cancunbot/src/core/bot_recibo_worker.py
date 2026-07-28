"""
CancunBot — Worker Thread: Descarga y Extracción de Recibos (BOT_RECIBO_CUN)
Usa Playwright (Sync API) ejecutándose en un hilo secundario de PySide6 (QThread) para no congelar la interfaz.
"""
import logging
import os
import shutil
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from PySide6.QtCore import QThread, Signal
from playwright.sync_api import sync_playwright

from sar.src.core.playwright_setup import resolve_chromium_executable
from sar.src.storage.db_connector import DatabaseConnector
from sar.src.storage.repositories import ConfigRepository

from cancunbot.src.storage.cancunbot_models import FolioCancun
from cancunbot.src.storage.cancunbot_repos import FolioCancunRepository, ReciboCancunRepository, LoteFolioRepository
from cancunbot.src.services.pdf_extractor import PdfExtractor
from cancunbot.src.pages.recibo_tesoreria_page import ReciboTesoreriaPage

logger = logging.getLogger(__name__)


class BotReciboCunWorker(QThread):
    """
    Worker que descarga los recibos electrónicos del portal del Ayuntamiento de Cancún
    e ingresa los datos extraídos en la base de datos (sar_db).
    """

    # Señales de comunicación con la interfaz de usuario (UI)
    status_changed = Signal(str)            # Logs de estado en consola
    progress_changed = Signal(int, int)     # prog_actual, prog_total
    metric_updated = Signal(str, int)       # metric_name, value ('pendientes', 'exitosos', 'errores')
    finished_processing = Signal(bool, str) # success, message

    def __init__(self, db_connector: DatabaseConnector, lote_id: int, headless: bool = True, custom_output_dir: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.lote_id = lote_id
        self.headless = headless
        self.custom_output_dir = custom_output_dir
        self._stop_requested = False

    def stop(self):
        """Detiene de forma segura el bucle de procesamiento del hilo."""
        self._stop_requested = True
        self.status_changed.emit("🚫 Detención del bot solicitada. Finalizando el folio actual...")

    def run(self):
        self.status_changed.emit("🚀 Iniciando Bot de Recibos Cancún (BOT_RECIBO_CUN)...")
        playwright_inst = None
        browser = None
        browser_context = None

        try:
            # 1. Cargar configuración y selectores desde sar_db
            self.status_changed.emit("Cargando parámetros y localizadores desde la base de datos...")
            with self.db_connector.get_session() as session:
                config_repo = ConfigRepository(session)
                portal_url = config_repo.get_parametro("CANCUN_PORTAL_RECIBO_URL") or "https://recibo.tesoreriacancun.com"
                max_retries = int(config_repo.get_parametro("CANCUN_MAX_REINTENTOS") or 3)
                output_dir_raw = self.custom_output_dir if self.custom_output_dir else (config_repo.get_parametro("CANCUN_PDF_BASE_PATH") or "Y:\\R2F\\Recibos")
                timeout_ms = int(config_repo.get_parametro("CANCUN_BOT_TIMEOUT_MS") or 30000)

                # Obtener selectores de portal y desacoplar sus campos
                db_locators = config_repo.get_localizadores_portal("CANCUN_RECIBO")
                locators = {}
                for k, v in db_locators.items():
                    locators[k] = {
                        "estrategia_selector": v.estrategia_selector,
                        "valor_selector": v.valor_selector
                    }

            # Validar y crear directorio de descarga final
            output_path = Path(output_dir_raw)
            try:
                output_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Error creando directorio final {output_path}: {e}")
                # Fallback al directorio local del proyecto
                output_path = Path("C:\\Users\\dramos\\Documents\\Proyecto_CapturaBot\\PDF_Recibos")
                output_path.mkdir(parents=True, exist_ok=True)

            self.status_changed.emit(f"Ruta de almacenamiento de recibos: {output_path}")

            # 2. Consultar los folios pendientes del lote desde la BD
            with self.db_connector.get_session() as session:
                folio_repo = FolioCancunRepository(session)
                lote_repo = LoteFolioRepository(session)
                
                lote = lote_repo.get_by_id(self.lote_id)
                if not lote:
                    self.finished_processing.emit(False, f"El lote con ID {self.lote_id} no existe.")
                    return
                
                # Actualiza estado del lote a procesando
                lote.estado_id = lote_repo._get_estado_id("lote_folio", "EN_PROCESO")
                session.commit()

                # Obtener folios pendientes del lote
                st_pending_id = folio_repo._get_estado_id("folio_cancun", "PENDIENTE")
                
                # Extraemos y desacoplamos los datos de los folios a diccionarios en memoria dentro de la sesión activa
                folios_pendientes = []
                for f in lote.folios:
                    if f.estado_id == st_pending_id:
                        folios_pendientes.append({
                            "folio_id": f.folio_id,
                            "tipo_folio": f.tipo_folio,
                            "folio_electronico": f.folio_electronico,
                            "folio_pase_caja": f.folio_pase_caja,
                            "intentos": f.intentos
                        })

            total_items = len(folios_pendientes)
            if total_items == 0:
                self.status_changed.emit("No hay folios pendientes por procesar en este lote.")
                self.finished_processing.emit(True, "No se encontraron folios pendientes en este lote.")
                return

            self.status_changed.emit(f"Se encontraron {total_items} folios listos para descargar.")
            self.progress_changed.emit(0, total_items)

            # 3. Inicializar navegador con Playwright
            self.status_changed.emit("Inicializando navegador Playwright...")
            playwright_inst = sync_playwright().start()

            # Resolver ejecutable de Chromium (para despliegues PyInstaller)
            executable_path = resolve_chromium_executable(
                progress_callback=lambda msg: self.status_changed.emit(msg)
            )

            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--ignore-certificate-errors",
            ]
            launch_kwargs = {
                "headless": self.headless,
                "args": launch_args,
            }
            if executable_path:
                launch_kwargs["executable_path"] = executable_path

            browser = playwright_inst.chromium.launch(**launch_kwargs)
            browser_context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                accept_downloads=True,
                ignore_https_errors=True
            )
            browser_context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # 4. Iniciar bucle de procesamiento
            procesados_ok = 0
            procesados_err = 0
            extractor = PdfExtractor()

            for idx, folio_dict in enumerate(folios_pendientes):
                if self._stop_requested:
                    self.status_changed.emit("🛑 Proceso interrumpido por el operador.")
                    break

                self.progress_changed.emit(idx + 1, total_items)
                
                # Obtener el número de folio real a consultar (pase de caja o electrónico)
                tipo_folio = folio_dict["tipo_folio"]
                folio_texto = folio_dict["folio_electronico"] if tipo_folio == "ELECTRONICO" else folio_dict["folio_pase_caja"]
                folio_id = folio_dict["folio_id"]
                self.status_changed.emit(f"[{idx+1}/{total_items}] Procesando folio {tipo_folio}: {folio_texto}...")

                # Actualiza estado del folio a descarga en proceso
                with self.db_connector.get_session() as session:
                    f_repo = FolioCancunRepository(session)
                    f_repo.update_status(folio_id, "DESCARGANDO")
                    session.commit()

                retry_attempt = 0
                step_success = False
                temp_pdf_path = None
                error_msg = ""

                # Reintentos automáticos
                while retry_attempt < max_retries and not step_success:
                    if self._stop_requested:
                        break
                    
                    page = browser_context.new_page()
                    page.set_default_timeout(timeout_ms)

                    try:
                        self.status_changed.emit(f"   -> Conectando al portal (intento {retry_attempt + 1})...")
                        page.goto(portal_url)

                        pom = ReciboTesoreriaPage(page, locators)
                        
                        # Captura e ingresa el folio e inicia consulta
                        if not pom.consultar_folio(folio_texto, tipo_folio):
                            error_msg = "Folio no encontrado en el portal de Tesorería."
                            break

                        # 1. Hacer clic en el botón "PDF" habilitado tras la consulta para abrir la vista previa
                        self.status_changed.emit("   -> Abriendo vista previa del PDF...")
                        pom._resolver("CANCUN_RECIBO_BTN_DESCARGAR").click()  # Selecciona el botón 'PDF'
                        page.wait_for_timeout(1500)  # Espera breve para renderizar la vista previa

                        # 2. Descargar PDF desde el botón 'Descargar PDF' que aparece en la vista previa
                        self.status_changed.emit("   -> Iniciando descarga del archivo...")
                        with page.expect_download(timeout=timeout_ms) as dl_info:
                            pom._resolver("CANCUN_RECIBO_BTN_DESCARGAR_EFECTIVO").click()  # Botón 'Descargar PDF'
                        
                        download = dl_info.value
                        temp_pdf_path = download.path()
                        
                        if temp_pdf_path and os.path.exists(temp_pdf_path):
                            step_success = True
                            self.status_changed.emit("   -> Descarga completada exitosamente.")
                            
                            # 3. Volver al inicio para el siguiente folio (ejecutando reload o botón volver)
                            self.status_changed.emit("   -> Regresando al buscador de folios...")
                            try:
                                pom._resolver("CANCUN_RECIBO_BTN_VOLVER").click()
                            except Exception:
                                page.reload()
                        else:
                            error_msg = "No se generó el archivo temporal PDF."

                    except Exception as e:
                        retry_attempt += 1
                        error_msg = str(e)
                        self.status_changed.emit(f"   ⚠️ Error en intento {retry_attempt}: {error_msg}")
                    finally:
                        page.close()

                # Guardar el resultado en la base de datos
                with self.db_connector.get_session() as session:
                    f_repo = FolioCancunRepository(session)
                    r_repo = ReciboCancunRepository(session)

                    if step_success and temp_pdf_path:
                        try:
                            # Parsear el PDF para extraer los campos clave
                            self.status_changed.emit("   -> Analizando PDF y extrayendo campos...")
                            datos_pdf = extractor.extraer(temp_pdf_path)
                            hash_file = extractor.calcular_hash(temp_pdf_path)

                            # Definir nombre de archivo y ruta organizada
                            pdf_name = f"Recibo_{folio_texto}_{int(datetime.now().timestamp())}.pdf"
                            final_pdf_path = output_path / pdf_name

                            # Mover archivo
                            shutil.move(temp_pdf_path, final_pdf_path)

                            # Estructurar datos a insertar en recibo_cancun
                            dict_recibo = {
                                "folio_pase_caja": datos_pdf.folio_pase_caja or folio_dict["folio_pase_caja"],
                                "folio_electronico": datos_pdf.folio_electronico or folio_dict["folio_electronico"],
                                "fecha_expedicion": datos_pdf.fecha_expedicion,
                                "hora_expedicion": datos_pdf.hora_expedicion,
                                "lugar_expedicion": datos_pdf.lugar_expedicion,
                                "rfc": datos_pdf.rfc,
                                "contribucion": datos_pdf.contribucion,
                                "nombre_contribuyente": datos_pdf.nombre_contribuyente,
                                "concepto": datos_pdf.concepto,
                                "total": datos_pdf.total,
                                "forma_pago": datos_pdf.forma_pago,
                                "pdf_nombre": pdf_name,
                                "pdf_ruta": str(final_pdf_path),
                                "hash_sha256": hash_file,
                                "padron": datos_pdf.padron,
                                "clave_catastral": datos_pdf.clave_catastral,
                                "correo_factura": datos_pdf.datos_adicionales.get("correo")
                            }

                            # Guardar Recibo y actualizar Folio a RECIBO_OK
                            rec = r_repo.save_extracted_receipt(folio_id, dict_recibo)
                            
                            # Alimentar de vuelta los folios extraídos al registro original de Folio (FolioCancun)
                            db_folio = session.get(FolioCancun, folio_id)
                            if db_folio:
                                if dict_recibo["folio_electronico"]:
                                    db_folio.folio_electronico = dict_recibo["folio_electronico"]
                                if dict_recibo["folio_pase_caja"]:
                                    db_folio.folio_pase_caja = dict_recibo["folio_pase_caja"]

                            # Pasar el recibo a PENDIENTE_FACTURAR automáticamente para el siguiente bot
                            r_repo.update_status(rec.recibo_id, "PENDIENTE_FACTURAR")
                            f_repo.update_status(folio_id, "RECIBO_OK")
                            session.commit()
                            
                            procesados_ok += 1
                            self.metric_updated.emit("exitosos", procesados_ok)
                            self.status_changed.emit("   ✅ Recibo capturado y guardado correctamente.")

                        except Exception as parse_error:
                            logger.error(f"Error procesando PDF del folio {folio_texto}: {parse_error}")
                            f_repo.update_status(folio_id, "ERROR_DESCARGA", error_msg=f"Error parseando PDF: {parse_error}")
                            procesados_err += 1
                            self.metric_updated.emit("errores", procesados_err)
                    else:
                        f_repo.update_status(folio_id, "ERROR_DESCARGA", error_msg=error_msg)
                        procesados_err += 1
                        self.metric_updated.emit("errores", procesados_err)
                        self.status_changed.emit(f"   ❌ Error en folio: {error_msg}")

                    session.commit()

            # 5. Actualizar contadores del lote
            with self.db_connector.get_session() as session:
                lote_repo = LoteFolioRepository(session)
                lote_repo.update_metrics_and_status(self.lote_id)
                session.commit()

            self.status_changed.emit(f"Procesamiento finalizado. Exitosos: {procesados_ok}, Errores: {procesados_err}.")
            self.finished_processing.emit(True, "Ejecución finalizada con éxito.")

        except Exception as global_err:
            stack = traceback.format_exc()
            logger.error(f"Error crítico en BotReciboCunWorker: {global_err}\n{stack}")
            self.finished_processing.emit(False, f"Error crítico: {global_err}")

        finally:
            if browser_context:
                browser_context.close()
            if browser:
                browser.close()
            if playwright_inst:
                playwright_inst.stop()
