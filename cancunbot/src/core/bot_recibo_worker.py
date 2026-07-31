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

from sqlalchemy import text
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
    folio_status_changed = Signal(dict)     # metadata dict: {"referencia": str, "rfc": str, "estado": str}

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
                            "intentos": f.intentos,
                            "rfc_id": f.rfc_id,
                            "desarrollo_nombre": f.desarrollo_asoc.nombre if f.desarrollo_asoc else None
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
            
            # Instanciar la página persistente fuera del bucle de folios
            page = browser_context.new_page()
            page.set_default_timeout(timeout_ms)
            page_needs_init = True

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

                # Emitir señal de cambio de estado en el monitor
                self.folio_status_changed.emit({
                    "referencia": folio_texto,
                    "rfc": "Consultando...",
                    "estado": "Conectando al portal..."
                })

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
                    
                    if page_needs_init:
                        self.status_changed.emit(f"   -> Inicializando ventana del portal (intento {retry_attempt + 1})...")
                        try:
                            # Si la página vieja seguía abierta pero en estado inválido, la cerramos de forma segura
                            try:
                                page.close()
                            except Exception:
                                pass
                            page = browser_context.new_page()
                            page.set_default_timeout(timeout_ms)
                            page.goto(portal_url)
                            page_needs_init = False
                        except Exception as init_err:
                            retry_attempt += 1
                            error_msg = f"Error conectando al sitio: {init_err}"
                            self.status_changed.emit(f"   ⚠️ Fallo de conexión: {error_msg}")
                            page_needs_init = True
                            continue
                    
                    try:
                        pom = ReciboTesoreriaPage(page, locators)
                        
                        # Captura e ingresa el folio e inicia consulta
                        if not pom.consultar_folio(folio_texto, tipo_folio):
                            error_msg = "Folio no encontrado en el portal de Tesorería."
                            break

                        # 1. Hacer clic en el botón "PDF" habilitado tras la consulta para abrir la vista previa
                        self.status_changed.emit("   -> Abriendo vista previa del PDF...")
                        btn_pdf = pom._resolver("CANCUN_RECIBO_BTN_DESCARGAR")
                        btn_pdf.wait_for(state="visible", timeout=10000)
                        btn_pdf.scroll_into_view_if_needed()
                        btn_pdf.click()  # Selecciona el botón 'PDF'
                        page.wait_for_timeout(1500)  # Espera breve para renderizar la vista previa

                        # 2. Descargar PDF desde el botón 'Descargar PDF' que aparece en la vista previa
                        self.status_changed.emit("   -> Iniciando descarga del archivo...")
                        btn_pdf_efectivo = pom._resolver("CANCUN_RECIBO_BTN_DESCARGAR_EFECTIVO")
                        btn_pdf_efectivo.wait_for(state="visible", timeout=10000)
                        btn_pdf_efectivo.scroll_into_view_if_needed()
                        with page.expect_download(timeout=timeout_ms) as dl_info:
                            btn_pdf_efectivo.click()  # Botón 'Descargar PDF'
                        
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
                                try:
                                    page.reload()
                                except Exception:
                                    page_needs_init = True
                        else:
                            error_msg = "No se generó el archivo temporal PDF."

                    except Exception as e:
                        retry_attempt += 1
                        error_msg = str(e)
                        self.status_changed.emit(f"   ⚠️ Error en intento {retry_attempt}: {error_msg}")
                        # Forzar el cierre y reapertura de la ventana en el siguiente reintento
                        page_needs_init = True

                # Guardar el resultado en la base de datos
                with self.db_connector.get_session() as session:
                    f_repo = FolioCancunRepository(session)
                    r_repo = ReciboCancunRepository(session)

                    if step_success and temp_pdf_path:
                        try:
                            # Parsear el PDF para extraer los campos clave
                            self.status_changed.emit("   -> Analizando PDF y extrayendo campos...")
                            datos_pdf = extractor.extraer(temp_pdf_path, db_session=session)
                            hash_file = extractor.calcular_hash(temp_pdf_path)

                            # Definir subcarpeta de Desarrollo dinámicamente forzando subdirectorio \Recibos\
                            des_name = folio_dict.get("desarrollo_nombre")
                            des_folder = "".join([c if c.isalnum() or c in (" ", "_", "-") else "" for c in des_name]).strip() if des_name else "Sin_Desarrollo"
                             
                            # Si output_path ya termina con "Recibos", no lo duplicamos, de lo contrario lo añadimos
                            if output_path.name.lower() == "recibos":
                                target_des_dir = output_path / des_folder
                            else:
                                target_des_dir = output_path / "Recibos" / des_folder
                              
                            try:
                                target_des_dir.mkdir(parents=True, exist_ok=True)
                            except Exception as dir_err:
                                logger.warning(f"No se pudo crear subcarpeta de desarrollo {target_des_dir}: {dir_err}. Usando raíz de salida.")
                                target_des_dir = output_path

                            # Definir nombre de archivo y ruta organizada
                            pdf_name = f"Recibo_{folio_texto}_{int(datetime.now().timestamp())}.pdf"
                            final_pdf_path = target_des_dir / pdf_name

                            # Mover archivo
                            shutil.move(temp_pdf_path, final_pdf_path)

                            # Estructurar datos a insertar en recibo_cancun
                            dict_recibo = {
                                "folio_pase_caja": datos_pdf.folio_pase_caja or folio_dict["folio_pase_caja"],
                                "folio_electronico": datos_pdf.folio_electronico or folio_dict["folio_electronico"],
                                "fecha_expedicion": datos_pdf.fecha_expedicion,
                                "hora_expedicion": datos_pdf.hora_expedicion,
                                "lugar_expedicion": datos_pdf.lugar_expedicion,
                                "rfc": datos_pdf.rfc or None,
                                "contribucion": datos_pdf.contribucion,
                                "nombre_contribuyente": datos_pdf.nombre_contribuyente or "CONTRIBUYENTE GENERAL",
                                "concepto": datos_pdf.concepto,
                                "total": datos_pdf.total,
                                "forma_pago": datos_pdf.forma_pago,
                                "pdf_nombre": pdf_name,
                                "pdf_ruta": str(final_pdf_path),
                                "hash_sha256": hash_file,
                                "padron": datos_pdf.padron or None,
                                "clave_catastral": datos_pdf.clave_catastral or None,
                                "sm": datos_pdf.sm or None,
                                "mz": datos_pdf.mz or None,
                                "l": datos_pdf.l or None,
                                "correo_factura": datos_pdf.datos_adicionales.get("correo"),
                                "datos_adicionales": datos_pdf.datos_adicionales
                            }

                            # Lógica de Validación de RFC
                            rfc_pdf = (datos_pdf.rfc or "").strip().upper()
                            rfc_id_final = folio_dict.get("rfc_id")
                            error_rfc_detectado = False

                            # Tratamos el RFC genérico XAXX010101000 igual que si estuviera vacío
                            # para forzar la resolución por el nombre limpio del contribuyente
                            es_generico = rfc_pdf in ("XAXX010101000", "XEXX010101000")

                            if rfc_pdf and not es_generico:
                                # 1. Resolver el rfc_id real del PDF desde el catálogo maestro
                                db_rfc_row = session.execute(
                                    text("SELECT rfc_id FROM sar_catalogo.rfc WHERE rfc = :r AND activo = true"),
                                    {"r": rfc_pdf}
                                ).fetchone()
                                
                                rfc_id_catalogo = db_rfc_row[0] if db_rfc_row else None

                                if rfc_id_catalogo:
                                    # Coincide o se corrige al ID existente del catálogo
                                    if rfc_id_final != rfc_id_catalogo:
                                        if rfc_id_final is not None:
                                            self.status_changed.emit(f"   ⚠️ Corrigiendo RFC: De base {rfc_id_final} a real {rfc_pdf} ({rfc_id_catalogo}).")
                                        rfc_id_final = rfc_id_catalogo
                                else:
                                    # El RFC real no existe en el catálogo maestro
                                    error_rfc_detectado = True
                                    self.status_changed.emit(f"   ❌ ERROR: El RFC '{rfc_pdf}' extraído del PDF no está catalogado en SAR.")
                            else:
                                # Si el RFC no viene en el PDF o es el genérico, resolverlo dinámicamente mediante el nombre de contribuyente limpio
                                nombre_limpio = dict_recibo["nombre_contribuyente"]
                                rfc_id_resuelto = None
                                rfc_texto_resuelto = None
                                
                                if nombre_limpio and nombre_limpio != "CONTRIBUYENTE GENERAL":
                                    # Buscar coincidencia aproximada (ILIKE) en el catálogo de RFCs usando la razón social limpia
                                    # Compara tanto con el inicio de la razón social como buscando palabras clave
                                    db_match = session.execute(
                                        text("""
                                            SELECT rfc_id, rfc, razon_social 
                                            FROM sar_catalogo.rfc 
                                            WHERE (razon_social ILIKE :n OR :n_clean ILIKE '%' || razon_social || '%')
                                              AND activo = true
                                            LIMIT 1
                                        """),
                                        {"n": f"%{nombre_limpio}%", "n_clean": nombre_limpio}
                                    ).fetchone()
                                    
                                    if db_match:
                                        rfc_id_resuelto = db_match[0]
                                        rfc_texto_resuelto = db_match[1]
                                        self.status_changed.emit(f"   ℹ️ RFC resuelto por Nombre: '{nombre_limpio}' -> {rfc_texto_resuelto} ({db_match[2]})")
                                
                                if rfc_id_resuelto:
                                    rfc_id_final = rfc_id_resuelto
                                    # Inyectar el RFC resuelto al diccionario de recibo para que no se guarde vacío en la columna RFC
                                    dict_recibo["rfc"] = rfc_texto_resuelto
                                else:
                                    self.status_changed.emit(f"   ℹ️ RFC no especificado en el recibo y no pudo ser resuelto por el nombre '{nombre_limpio}'.")
                                    rfc_id_final = None

                            # Asignar rfc_id al recibo
                            dict_recibo["rfc_id"] = rfc_id_final

                            if error_rfc_detectado:
                                # Guardar con error de RFC no catalogado
                                f_repo.update_status(folio_id, "ERROR_RFC_NO_CATALOGADO", error_msg=f"El RFC {rfc_pdf} del PDF no existe en el catálogo maestro.")
                                session.commit()
                                procesados_err += 1
                                self.metric_updated.emit("errores", procesados_err)
                                self.folio_status_changed.emit({
                                    "referencia": folio_texto,
                                    "rfc": rfc_pdf,
                                    "estado": "ERROR_RFC_NO_CATALOGADO"
                                })
                            else:
                                # Guardar Recibo y actualizar Folio a RECIBO_OK
                                rec = r_repo.save_extracted_receipt(folio_id, dict_recibo)
                                
                                # Alimentar de vuelta los folios extraídos al registro original de Folio (FolioCancun)
                                db_folio = session.get(FolioCancun, folio_id)
                                if db_folio:
                                    if dict_recibo["folio_electronico"]:
                                        db_folio.folio_electronico = dict_recibo["folio_electronico"]
                                    if dict_recibo["folio_pase_caja"]:
                                        db_folio.folio_pase_caja = dict_recibo["folio_pase_caja"]
                                    db_folio.rfc_id = rfc_id_final

                                # Pasar el recibo a PENDIENTE_FACTURAR automáticamente para el siguiente bot
                                r_repo.update_status(rec.recibo_id, "PENDIENTE_FACTURAR")
                                f_repo.update_status(folio_id, "RECIBO_OK")
                                session.commit()
                                
                                procesados_ok += 1
                                self.metric_updated.emit("exitosos", procesados_ok)
                                self.status_changed.emit("   ✅ Recibo capturado y guardado correctamente.")
                                self.folio_status_changed.emit({
                                    "referencia": folio_texto,
                                    "rfc": rfc_pdf or "No detectado",
                                    "estado": "RECIBO_OK"
                                })

                        except Exception as parse_error:
                            logger.error(f"Error procesando PDF del folio {folio_texto}: {parse_error}")
                            f_repo.update_status(folio_id, "ERROR_DESCARGA", error_msg=f"Error parseando PDF: {parse_error}")
                            procesados_err += 1
                            self.metric_updated.emit("errores", procesados_err)
                            self.folio_status_changed.emit({
                                "referencia": folio_texto,
                                "rfc": "Error PDF",
                                "estado": "ERROR_DESCARGA"
                            })
                    else:
                        f_repo.update_status(folio_id, "ERROR_DESCARGA", error_msg=error_msg)
                        procesados_err += 1
                        self.metric_updated.emit("errores", procesados_err)
                        self.status_changed.emit(f"   ❌ Error en folio: {error_msg}")
                        self.folio_status_changed.emit({
                            "referencia": folio_texto,
                            "rfc": "Fallo",
                            "estado": "ERROR_DESCARGA"
                        })

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
