import os
import sys  
import shutil
import random
import time
import logging
from datetime import datetime
from enum import Enum
from playwright.sync_api import sync_playwright
from app.paths import DOWNLOADS_DIR, SCREENSHOTS_DIR, TEMP_DIR

logger = logging.getLogger("OptimaCaptureBot.Scraper")

class SatqScraper:
    class Escenario(Enum):
        NO_GENERADA = 1
        YA_GENERADA = 2
        INVALIDA = 3
        DESCONOCIDO = 4
    def __init__(self, download_root=None, screenshot_dir=None):
        self.download_root = str(DOWNLOADS_DIR) if download_root is None else download_root
        self.screenshot_dir = str(SCREENSHOTS_DIR) if screenshot_dir is None else screenshot_dir
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        from app import settings
        self.satq_url = settings.get_satq_url()
        
        # Crear directorios de soporte si no existen
        os.makedirs(self.download_root, exist_ok=True)
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def iniciar_navegador(self):
        """
        Inicia el navegador en modo visible (headed) usando el canal de Chrome de tu sistema
        y con un perfil persistente para conservar cookies y sesiones.
        """
        try:
            logger.info("Iniciando Playwright...")
            self.playwright = sync_playwright().start()
            
            # Directorio del perfil persistente exclusivo para el bot
            user_data_dir = str(TEMP_DIR / "perfil_bot")
            os.makedirs(user_data_dir, exist_ok=True)
            logger.info(f"Usando perfil persistente de Chrome en: {user_data_dir}")
            # Directorio temporal para las descargas intermedias de Playwright (evita UUIDs en descargas del usuario)
            playwright_downloads = os.path.join(str(TEMP_DIR), "playwright_downloads")
            os.makedirs(playwright_downloads, exist_ok=True)

            try:
                self.context = self.playwright.chromium.launch_persistent_context(
                    user_data_dir,
                    channel="chrome",  # Usar Google Chrome real instalado en el sistema
                    headless=False,
                    viewport=None,      # Maximizado real
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    args=[
                        "--start-maximized",
                        "--disable-blink-features=AutomationControlled"
                    ],
                    ignore_default_args=["--enable-automation"],
                    accept_downloads=True,
                    downloads_path=playwright_downloads
                )
            except Exception as chrome_err:
                logger.warning(f"Google Chrome real no detectado o falló al iniciar: {chrome_err}. Intentando fallback con Microsoft Edge...")
                try:
                    self.context = self.playwright.chromium.launch_persistent_context(
                        user_data_dir,
                        channel="msedge",  # Usar Microsoft Edge real instalado en el sistema
                        headless=False,
                        viewport=None,      # Maximizado real
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        args=[
                            "--start-maximized", 
                            "--disable-blink-features=AutomationControlled"
                        ],
                        ignore_default_args=["--enable-automation"],
                        accept_downloads=True,
                        downloads_path=playwright_downloads
                    )
                except Exception as edge_err:
                    logger.error(f"Fallback a Microsoft Edge también falló: {edge_err}")
                    raise Exception("No se detectó Google Chrome ni Microsoft Edge instalados en el sistema Windows. Por favor, instale alguno para ejecutar la automatización.")
            
            # Evitar detección básica en el contexto
            self.context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            # launch_persistent_context abre una pestaña automáticamente. La reutilizamos.
            if len(self.context.pages) > 0:
                self.page = self.context.pages[0]
            else:
                self.page = self.context.new_page()
                
            logger.info(f"Navegando a la URL del SATQ: {self.satq_url}")
            
            max_intentos = 3
            for intento in range(max_intentos):
                try:
                    self.page.goto(self.satq_url, timeout=45000)
                    self.page.wait_for_load_state('networkidle')
                    logger.info("Portal cargado exitosamente.")
                    break
                except Exception as err_red:
                    logger.warning(f"Intento de carga {intento + 1}/{max_intentos} falló: {err_red}")
                    if intento == max_intentos - 1:
                        raise Exception(f"No se pudo conectar al portal tras {max_intentos} intentos. Revise su internet.")
                    time.sleep(3)
            
            return True
        except Exception as e:
            logger.error(f"Error al iniciar el navegador con perfil persistente: {e}")
            self.cerrar()
            return False

    def esperar_login_manual(self, callback_check_stop=None):
        """
        Pausa y espera de forma segura a que el operador ingrese sus datos y resuelva el CAPTCHA.
        Verifica periódicamente si el usuario ya ingresó a la sección interna de consulta o si se solicitó detener.
        """
        logger.info("Esperando a que el operador inicie sesión y resuelva el CAPTCHA manualmente...")
        
        # Elementos comunes o patrones de URL que indican sesión activa en SATQ
        # (ej. url contiene 'dashboard', 'consulta', o existe un botón de Cerrar Sesión)
        while True:
            # Si el orquestador solicita detener el proceso
            if callback_check_stop and callback_check_stop():
                logger.info("Espera de login manual cancelada por el usuario.")
                return False
                
            try:
                current_url = self.page.url
                
                # Criterio 1: La URL cambió a la sección interna
                if "consulta" in current_url or "dashboard" in current_url or "inicio" in current_url:
                    logger.info("Sesión activa detectada mediante URL.")
                    return True
                    
                # Criterio 2: Presencia de un botón de salir/logout típico
                logout_element = self.page.query_selector("text=Cerrar Sesión") or self.page.query_selector("text=Salir")
                if logout_element:
                    logger.info("Sesión activa detectada mediante botón de salida en el DOM.")
                    return True
                    
            except Exception as e:
                # Si se cierra la página del navegador de forma inesperada
                logger.error(f"El navegador o la página se cerró inesperadamente durante la espera de login: {e}")
                return False
                
            time.sleep(1.5)

    def emular_espera_humana(self, min_s=1.5, max_s=4.0):
        """
        Genera retardos aleatorios para emular comportamiento humano genuino.
        """
        delay = random.uniform(min_s, max_s)
        logger.debug(f"Emulando espera humana: {delay:.2f} segundos...")
        time.sleep(delay)

    def procesar_registro(self, referencia, rfc, carpeta_lote, razon_social="", cp="", callback_validar_timbrar=None, solo_no_generadas=False):
        """
        Navega, realiza la búsqueda de la referencia de factura, la descarga y la clasifica.
        :param solo_no_generadas: Si True, las referencias YA GENERADAS se omiten inmediatamente sin descargar.
        Retorna (estado, lote_asignado, mensaje_error, screenshot_path).
        """
        # Preparar directorio del lote
        ruta_lote = os.path.join(self.download_root, carpeta_lote)
        os.makedirs(ruta_lote, exist_ok=True)

        # Cargar configuración de reintentos
        from app import settings
        max_retries = settings.get_max_timbrado_retries()
        auto_retry = settings.get_reintento_automatico()
        intento = 0
        while True:
            try:
                logger.info(f"Iniciando consulta automatizada para referencia: {referencia} (RFC: {rfc})")
                # --- 1. Emulación de navegación humana ---
                self.emular_espera_humana(2.0, 3.5)

                # Buscar iframe del portal
                self.main_frame = self.page
                for f in self.page.frames:
                    if "shacienda.qroo.gob.mx" in f.url:
                        self.main_frame = f
                        break

                # --- 2. Rellenar inputs de referencia y RFC ---
                # Referencia
                input_ref = self.main_frame.wait_for_selector("input#Referencia", timeout=10000)
                if not input_ref:
                    raise Exception("No se localizó el campo de entrada 'Referencia' (input#Referencia) en el iframe.")
                input_ref.click()
                self.page.keyboard.press("Control+A")
                self.page.keyboard.press("Backspace")
                for char in referencia:
                    self.page.keyboard.type(char)
                    time.sleep(random.uniform(0.05, 0.15))
                self.emular_espera_humana(0.8, 1.5)

                # RFC
                input_rfc = self.main_frame.wait_for_selector("input#RFC", timeout=5000)
                if not input_rfc:
                    raise Exception("No se localizó el campo de entrada 'RFC' (input#RFC) en el iframe.")
                input_rfc.click()
                self.page.keyboard.press("Control+A")
                self.page.keyboard.press("Backspace")
                for char in rfc:
                    self.page.keyboard.type(char)
                    time.sleep(random.uniform(0.05, 0.15))
                self.emular_espera_humana(1.0, 2.0)

                # Botón Buscar
                btn_buscar = self.main_frame.wait_for_selector("button[type='submit']", timeout=5000)
                btn_buscar.click()
                logger.info("Botón Buscar pulsado, esperando resultados...")
                self.page.wait_for_load_state('networkidle')

                # Detectar escenario y procesar según caso
                escenario = self._detectar_escenario()
                if escenario == self.Escenario.NO_GENERADA:
                    self._generar_cfdi(razon_social, cp, callback_validar_timbrar)
                elif escenario == self.Escenario.YA_GENERADA:
                    if solo_no_generadas:
                        # Modo empresarial: omitir las ya generadas inmediatamente
                        logger.info(f"Referencia {referencia} ya generada. Omitiendo por configuración del operador.")
                        return "OMITIDO-YA GENERADA", carpeta_lote, None, None
                elif escenario == self.Escenario.INVALIDA:
                    raise Exception("Referencia o RFC no válidos según portal")

                # Descargar PDFs generados y devolver rutas
                pdf_paths = self._descargar_pdfs(referencia, rfc, ruta_lote)
                
                # VALIDACIÓN POST-DESCARGA: Asegurar la existencia de los archivos físicos
                if not pdf_paths:
                    raise Exception("No se descargó ningún PDF de CFDI tras el timbrado / consulta.")

                # Una vez garantizada la descarga, asignar estado definitivo
                if escenario == self.Escenario.NO_GENERADA:
                    estado_final = "OK-GENERADA"
                elif escenario == self.Escenario.YA_GENERADA:
                    estado_final = "OK-YA GENERADA"
                else:
                    estado_final = "EXITOSO"

                return estado_final, carpeta_lote, None, pdf_paths

            except Exception as e:
                # Si es un error de portal y podemos reintentar
                if auto_retry and intento < max_retries:
                    intento += 1
                    logger.warning(f"[REINTENTO] Error del portal detectado ({e}), reintentando {intento}/{max_retries}...")
                    try:
                        self.page.reload()
                        self.page.wait_for_load_state('networkidle')
                    except Exception as reload_err:
                        logger.error(f"Fallo al recargar la página: {reload_err}")
                    continue
                else:
                    logger.error(f"Error crítico del portal sin posibilidad de reintento: {e}")
                    return "ERROR_REINTENTABLE", None, str(e), None

    def _detectar_escenario(self):
        """Detecta cuál de los tres escenarios se presenta después de pulsar Buscar.
        Returns:
            Escenario Enum
        """
        # Esperar que algún elemento clave aparezca
        time.sleep(2)  # pequeña pausa para que el DOM se actualice
        # Caso: botón Generar CFDI presente
        btn_generar = self.main_frame.query_selector("button:has-text('Generar CFDI'), a:has-text('Generar CFDI')")
        if btn_generar:
            # En HTML el atributo disabled puede ser un boolean o un string
            disabled = btn_generar.get_attribute('disabled')
            es_disabled = disabled is not None and str(disabled).lower() != 'false'
            if es_disabled:
                return self.Escenario.YA_GENERADA
            else:
                return self.Escenario.NO_GENERADA
        # Caso: mensaje de referencia no encontrada o RFC inválido
        alerta = self.main_frame.query_selector("text=No se encontraron registros") or self.main_frame.query_selector("text=Referencia no válida") or self.main_frame.query_selector("text=RFC no válido")
        if alerta:
            return self.Escenario.INVALIDA
        # Si hay un botón de PDF, entonces ya está generada y quizá no había botón "Generar CFDI"
        if self.main_frame.query_selector("button:has-text('PDF'), a:has-text('PDF')"):
            return self.Escenario.YA_GENERADA
            
        # Si no se detecta nada, devolver desconocido
        return self.Escenario.DESCONOCIDO

    def _generar_cfdi(self, razon_social, cp, callback_validar_timbrar=None):
        """Realiza los pasos de generación de CFDI: clic en Generar, rellenar datos y timbrar."""
        # Click en Generar CFDI con espera explícita
        try:
            btn_generar = self.main_frame.wait_for_selector("button:has-text('Generar CFDI'), a:has-text('Generar CFDI')", timeout=10000)
        except Exception:
            raise Exception('Botón Generar CFDI no encontrado en escenario NO_GENERADA (timeout)')
        btn_generar.click()
        logger.info("Clic en Generar CFDI ejecutado.")
        
        # Esperar carga del formulario de validación
        self.page.wait_for_load_state('networkidle')
        self.emular_espera_humana(1.5, 2.5)
        
        # Rellenar Razón Social y Código Postal
        # Selectores exactos del portal SATQ con espera explícita
        try:
            input_razon = self.main_frame.wait_for_selector("input#NombreReceptor", timeout=10000)
        except Exception:
            input_razon = None
            
        try:
            input_cp = self.main_frame.wait_for_selector("input#DomicilioFiscalReceptor", timeout=10000)
        except Exception:
            input_cp = None
        
        if input_razon:
            # --- RAZÓN SOCIAL: fill() directo + verificación + fallback a tipeo ---
            input_razon.click()
            self.emular_espera_humana(0.2, 0.4)
            
            # Estrategia 1: fill() instantáneo (borra y escribe todo de golpe)
            input_razon.fill(str(razon_social))
            
            # Verificación: confirmar que el valor quedó correctamente
            valor_actual_razon = input_razon.input_value()
            if valor_actual_razon.strip() != str(razon_social).strip():
                # Fallback: el portal rechazó el fill(), usamos tipeo letra por letra
                logger.warning(f"fill() no funcionó para Razón Social. Usando tipeo como fallback.")
                input_razon.fill("")  # limpiar antes del fallback
                self.page.keyboard.press("Control+A")
                self.page.keyboard.press("Delete")
                for char in str(razon_social):
                    self.page.keyboard.type(char)
                    time.sleep(random.uniform(0.02, 0.04))
            
            logger.info(f"Razón Social establecida: '{input_razon.input_value()}'")
        else:
            logger.warning("No se encontró el campo Razón Social (input#NombreReceptor).")
            
        if input_cp:
            # --- CÓDIGO POSTAL: fill() directo + verificación + fallback a tipeo ---
            input_cp.click()
            self.emular_espera_humana(0.2, 0.4)
            
            # Estrategia 1: fill() instantáneo
            input_cp.fill(str(cp))
            
            # Verificación: confirmar que el valor quedó correctamente
            valor_actual_cp = input_cp.input_value()
            if valor_actual_cp.strip() != str(cp).strip():
                # Fallback: el portal rechazó el fill(), usamos tipeo letra por letra
                logger.warning(f"fill() no funcionó para Código Postal. Usando tipeo como fallback.")
                input_cp.fill("")  # limpiar antes del fallback
                self.page.keyboard.press("Control+A")
                self.page.keyboard.press("Delete")
                for char in str(cp):
                    self.page.keyboard.type(char)
                    time.sleep(random.uniform(0.02, 0.04))
            
            logger.info(f"Código Postal establecido: '{input_cp.input_value()}'")
        else:
            logger.warning("No se encontró el campo Código Postal (input#DomicilioFiscalReceptor).")
            
        logger.info("Datos de validación rellenados y verificados.")
        self.emular_espera_humana(1.0, 2.0)

        # --- VALIDACIÓN POST-FILL (Extra Cautela ante inputs vacíos o incorrectos) ---
        if input_razon:
            val_r = input_razon.input_value().strip()
            if not val_r or val_r != str(razon_social).strip():
                raise Exception(f"Fallo de integridad: Razón Social en portal ('{val_r}') no coincide con catálogo ('{razon_social}')")
        if input_cp:
            val_c = input_cp.input_value().strip()
            if not val_c or val_c != str(cp).strip():
                raise Exception(f"Fallo de integridad: CP en portal ('{val_c}') no coincide con catálogo ('{cp}')")
        
        # --- MODO VALIDACIÓN: Pausa antes de Timbrar para revisión del operador ---
        if callback_validar_timbrar:
            logger.info(
                f"[VALIDACIÓN] Campos listos. Revise en Chrome antes de timbrar:\n"
                f"  · Razón Social → '{razon_social}'\n"
                f"  · Código Postal → '{cp}'\n"
                f"Haga clic en 'Aprobar Timbrado' en la aplicación para continuar."
            )
            # Bloquear el hilo del scraper hasta que el operador apruebe desde la GUI
            aprobado = callback_validar_timbrar(razon_social, cp)
            if not aprobado:
                logger.warning("[VALIDACIÓN] Timbrado cancelado por el operador. Fila marcada para revisión manual.")
                raise Exception("Timbrado cancelado por el operador durante la validación previa.")
            logger.info("[VALIDACIÓN] Aprobado por el operador. Procediendo a timbrar...")
        
        # Click en botón Timbrar con espera explícita
        try:
            btn_timbrar = self.main_frame.wait_for_selector("button#btnTimbrar", timeout=10000)
            btn_timbrar.click()
            logger.info("Clic en Timbrar ejecutado.")
        except Exception as e:
            logger.error(f"Botón Timbrar no encontrado o no clickeable (timeout): {e}")
            raise Exception("Botón Timbrar no encontrado o no clickeable en el portal")

        # --- DETECCIÓN DE CONGELAMIENTO O HTTP ERROR 500 POST-TIMBRADO ---
        logger.info("Esperando confirmación de timbrado o botones PDF...")
        inicio_espera = time.time()
        timbrado_ok = False
        
        while time.time() - inicio_espera < 35:
            # 1. ¿Apareció el botón de PDF o descarga? (Éxito)
            if self.main_frame.query_selector("button:has-text('PDF'), a:has-text('PDF')"):
                timbrado_ok = True
                break
                
            # 2. ¿Apareció un error HTTP 500 del servidor / IIS / FastCGI?
            error_html = self.page.content()
            if "HTTP Error 500.0" in error_html or "FastCGI" in error_html or "Internal Server Error" in error_html:
                logger.error("[PORTAL] Servidor SATQ reportó error HTTP 500 / FastCGI Timeout.")
                self.capturar_pantalla("HTTP500_Error")
                # Estrategia B: Forzar recarga total de la pestaña
                logger.info("Ejecutando recarga total de página como mitigación...")
                try:
                    self.page.goto(self.satq_url, timeout=30000)
                    self.page.wait_for_load_state('networkidle')
                except Exception as reload_err:
                    logger.error(f"No se pudo recargar la página tras error 500: {reload_err}")
                raise Exception("Error 500.0 de FastCGI en servidor SATQ tras timbrado")

            # 3. ¿El proceso sigue colgado en "Esperar..." pero el botón de Salir está visible?
            if time.time() - inicio_espera > 15:
                btn_salir = self.main_frame.query_selector("a.btn.btn-default[href='./'], a:has-text('Salir')")
                if btn_salir:
                    logger.warning("[PORTAL] Timbrado colgado en 'Esperar...'. Utilizando botón Salir para reiniciar transacción...")
                    self.capturar_pantalla("Cuelgue_Esperar")
                    try:
                        btn_salir.click()
                        self.page.wait_for_load_state('networkidle')
                    except Exception as click_err:
                        logger.error(f"Error al hacer clic en Salir: {click_err}")
                    raise Exception("Transacción colgada en portal (Esperar...). Se reintentó vía botón Salir.")

            time.sleep(1.0)
            
        if not timbrado_ok:
            logger.error("[PORTAL] Tiempo de espera agotado sin obtener respuesta de timbrado exitoso.")
            # Si el botón de salir sigue ahí, hacer clic como último recurso antes de lanzar excepción
            btn_salir = self.main_frame.query_selector("a.btn.btn-default[href='./'], a:has-text('Salir')")
            if btn_salir:
                try:
                    btn_salir.click()
                    self.page.wait_for_load_state('networkidle')
                except Exception:
                    pass
            raise Exception("Timeout esperando respuesta de timbrado del portal SATQ")

        self.page.wait_for_load_state('networkidle')
        self.emular_espera_humana(2.0, 4.0)

    def capturar_pantalla(self, referencia):
        """
        Toma una captura de pantalla del estado actual del navegador para auditoría visual.
        """
        try:
            if self.page:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"{referencia}_{timestamp}_error.png"
                filepath = os.path.join(self.screenshot_dir, filename)
                self.page.screenshot(path=filepath)
                logger.info(f"Evidencia visual guardada exitosamente en {filepath}")
                return filepath
        except Exception as ex:
            logger.error(f"No se pudo tomar la captura de pantalla de evidencia: {ex}")
        return None

    def cerrar(self):
        """Cierra de forma segura el contexto y Playwright si están activos."""
        try:
            if self.context:
                self.context.close()
                logger.info("Contexto de Playwright cerrado correctamente.")
        except Exception as e:
            logger.warning(f"Error al cerrar contexto Playwright: {e}")
        try:
            if self.playwright:
                self.playwright.stop()
                logger.info("Playwright detenido correctamente.")
        except Exception as e:
            logger.warning(f"Error al detener Playwright: {e}")
            
        # Limpiar directorio de descargas temporales
        try:
            playwright_downloads = os.path.join(str(TEMP_DIR), "playwright_downloads")
            if os.path.exists(playwright_downloads):
                shutil.rmtree(playwright_downloads, ignore_errors=True)
                logger.info("Directorio temporal de descargas de Playwright limpiado.")
        except Exception as e:
            logger.warning(f"No se pudo limpiar el directorio temporal de descargas: {e}")
            
        # Reset references
        self.context = None
        self.browser = None
        self.page = None
        self.playwright = None

    def _descargar_pdfs(self, referencia, rfc, destino=None):
        """Descarga los PDFs generados tras timbrar y los guarda en el directorio indicado.
        :param destino: Ruta absoluta de la carpeta destino. Si es None, usa self.download_root.
        Returns a list with the absolute paths of the downloaded files.
        """
        carpeta = destino if destino else self.download_root
        os.makedirs(carpeta, exist_ok=True)
        pdf_paths = []
        # Esperar a que los botones PDF aparezcan (portal puede tardar en generarlos)
        try:
            self.main_frame.wait_for_selector(
                "button:has-text('PDF'), a:has-text('PDF')",
                timeout=30000
            )
        except Exception:
            logger.warning("Tiempo de espera agotado buscando botones PDF.")

        # Encontrar todos los enlaces o botones que contienen "PDF"
        botones = self.main_frame.query_selector_all(
            "a:has-text('PDF'), button:has-text('PDF')"
        )
        if not botones:
            logger.warning("No se encontraron enlaces PDF después del timbrado.")
            return pdf_paths

        for idx, btn in enumerate(botones[:2]):  # Limitamos a los dos primeros
            try:
                # Usar contexto de descarga de Playwright
                with self.page.expect_download(timeout=30000) as download_info:
                    btn.click()
                download = download_info.value
                # Guardar con nombre basado en referencia, RFC e índice
                suggested_path = os.path.join(carpeta, f"{referencia}_{rfc}_{idx+1}.pdf")
                download.save_as(suggested_path)
                pdf_paths.append(suggested_path)
                logger.info(f"PDF {idx+1} guardado en {suggested_path}")
            except Exception as e:
                logger.error(f"Error descargando PDF {idx+1}: {e}")

        return pdf_paths
