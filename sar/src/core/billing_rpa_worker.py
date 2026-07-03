"""RPA Worker Thread for CFDI invoicing and timbrado using Playwright (Synchronous)."""

import os
import time
import random
import datetime
import traceback
import hashlib
import shutil
import uuid
from typing import Optional, Dict, Any, List
from PySide6.QtCore import QThread, Signal
from playwright.sync_api import sync_playwright
from sqlalchemy import text

from sar.src.storage.repositories import ReferenciaRepository, AuditRepository, ConfigRepository
from sar.src.storage.models import Referencia, EstadoSistema, Solicitud, GrupoReferencia, OrdenGeneracion

class BillingRpaWorker(QThread):
    """Secondary thread to run Playwright steps without freezing the PyQt GUI."""
    
    # UI Interaction Signals
    status_changed = Signal(str)
    progress_changed = Signal(int)
    metric_updated = Signal(str, int)  # metric_name ('pendientes', 'exitosos', 'errores'), value
    referencia_generada = Signal(str, str, str)  # ref_portal, rfc, status
    finished_processing = Signal(bool, str)  # success, message

    def __init__(self, db_connector, context: dict, headless: bool = False, custom_output_dir: Optional[str] = None, omitir_ya_generadas: bool = True, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.ctx = context
        self.headless = headless
        self.custom_output_dir = custom_output_dir
        self.omitir_ya_generadas = omitir_ya_generadas
        self._stop_requested = False

    def stop(self):
        """Safely requests the worker to stop processing between loops."""
        self._stop_requested = True
        self.status_changed.emit("Detención de facturación solicitada. Finalizando ciclo...")

    def run(self):
        self.status_changed.emit("Iniciando Worker RPA de Facturación...")
        playwright_inst = None
        browser = None
        context = None
        
        try:
            # 1. Load Parameters and Locators from DB
            self.status_changed.emit("Cargando parámetros y localizadores de la base de datos...")
            with self.db_connector.get_session() as db_session:
                config_repo = ConfigRepository(db_session)
                audit_repo = AuditRepository(db_session)
                
                # Fetch System Parameters
                satq_url = config_repo.get_parametro("SATQ_URL") or "https://shacienda.qroo.gob.mx/tributanet/"
                retries_str = config_repo.get_parametro("REINTENTOS_AUTOMATICOS")
                max_retries = int(retries_str) if retries_str else 4
                
                # Fetch RUTA_DERECHOS
                self.default_output_dir = config_repo.get_parametro("RUTA_DERECHOS") or "storage"
                
                # Fetch Portal Locators and extract values
                db_locators = config_repo.get_localizadores()
                locators = {k: v.valor_selector for k, v in db_locators.items()}
                
            self._log_event_db("PROCESAR_FACTURACION", f"Inicio procesamiento lote facturación solicitud {self.ctx['solicitud_id']}", detalle={"consecutivo_inicio": self.ctx['consecutivo_inicio'], "consecutivo_fin": self.ctx['consecutivo_fin']})
            
            # 2. Reclamar la solicitud para prevenir concurrencia (Race Condition Lock)
            self.status_changed.emit("Bloqueando solicitud (PROCESANDO)...")
            self._update_solicitud_estado("PROCESANDO")
            
            # 3. Launch Playwright
            self.status_changed.emit("Iniciando navegador Playwright (Headed)...")
            playwright_inst = sync_playwright().start()
            
            # Persist profile to save cache
            user_data_dir = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "perfil_bot_facturacion")
            os.makedirs(user_data_dir, exist_ok=True)
            
            playwright_downloads = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "playwright_downloads_facturacion")
            os.makedirs(playwright_downloads, exist_ok=True)
            
            # launch_persistent_context espejando la estrategia del bot legacy (perfil persistente + anti-detección)
            context = playwright_inst.chromium.launch_persistent_context(
                user_data_dir,
                headless=self.headless,
                accept_downloads=True,
                downloads_path=playwright_downloads,
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                ignore_default_args=["--enable-automation"],
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox"
                ]
            )
            
            # Eliminar marca de webdriver para evitar detección de bots por el portal
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            page = context.pages[0] if len(context.pages) > 0 else context.new_page()
            page.set_default_timeout(35000)
            
            # Load initial portal
            self.status_changed.emit(f"Navegando al portal SATQ: {satq_url}")
            page.goto(satq_url)
            page.wait_for_load_state("networkidle")
            
            # 3. Execution Loop
            facturas_procesadas = self.ctx.get("facturas_procesadas", 0)
            total_items = self.ctx["consecutivo_fin"] - self.ctx["consecutivo_inicio"] + 1
            
            with self.db_connector.get_session() as db_session:
                status_filter = "('AUTORIZADA', 'ERROR', 'ERROR_VALIDACION')" if self.omitir_ya_generadas else "('AUTORIZADA', 'FACTURADA', 'ERROR', 'ERROR_VALIDACION')"
                stmt = text(f"""
                    SELECT r.consecutivo_grupo
                    FROM sar_produccion.referencia r
                    JOIN sar_catalogo.estado_sistema es ON r.estado_id = es.estado_id
                    WHERE r.solicitud_id = :solicitud_id 
                      AND es.codigo IN {status_filter}
                    ORDER BY r.consecutivo_grupo ASC
                """)
                rows = db_session.execute(stmt, {"solicitud_id": self.ctx["solicitud_id"]}).fetchall()
                consecutivos_to_process = [row[0] for row in rows]
                
            success_count = facturas_procesadas
            error_count = 0
            
            if not consecutivos_to_process:
                self.status_changed.emit("No hay referencias procesables para esta solicitud.")
            else:
                self.status_changed.emit(f"Facturando {len(consecutivos_to_process)} referencia(s) pendiente(s)...")
            
            for current in consecutivos_to_process:
                if self._stop_requested:
                    self.status_changed.emit("Proceso detenido por el usuario.")
                    break
                
                # Fetch reference portal string from database
                referencia_portal = None
                referencia_id = None
                importe = 0.0
                with self.db_connector.get_session() as db_session:
                    stmt = text("""
                        SELECT r.referencia_id, r.referencia_portal, r.importe, es.codigo as estado_codigo
                        FROM sar_produccion.referencia r
                        JOIN sar_catalogo.estado_sistema es ON r.estado_id = es.estado_id
                        WHERE r.solicitud_id = :solicitud_id 
                          AND r.consecutivo_grupo = :consecutivo
                    """)
                    row = db_session.execute(stmt, {"solicitud_id": self.ctx["solicitud_id"], "consecutivo": current}).fetchone()
                    if row:
                        if row.estado_codigo == 'FACTURADA' and self.omitir_ya_generadas:
                            self.status_changed.emit(f"Consecutivo {current} ya está FACTURADA y opción 'Omitir' está activa. Saltando...")
                        else:
                            referencia_id = row.referencia_id
                            referencia_portal = row.referencia_portal
                            importe = float(row.importe) if row.importe else 0.0
                
                if not referencia_portal:
                    if not row or (row and row.estado_codigo != 'FACTURADA'):
                        self.status_changed.emit(f"Consecutivo {current} no tiene referencia procesable en BD. Saltando...")
                    success_count += 1
                    pct = int(((success_count + error_count) / total_items) * 100) if total_items > 0 else 100
                    self.progress_changed.emit(pct)
                    continue
                
                self.status_changed.emit(f"Facturando referencia {referencia_portal} (Consecutivo {current})...")
                
                retry_attempt = 0
                step_success = False
                # Lista de rutas temporales para ambas facturas de la referencia
                temp_pdf_paths = [None, None]
                
                while retry_attempt < max_retries and not step_success:
                    if self._stop_requested:
                        break
                    try:
                        self.status_changed.emit(f"Cargando portal (Intento {retry_attempt + 1})...")
                        page.goto(satq_url)
                        page.wait_for_load_state("networkidle")
                        
                        # Localizar el iframe del portal (equivalente al legacy)
                        main_frame = page
                        for f in page.frames:
                            if "shacienda.qroo.gob.mx" in f.url:
                                main_frame = f
                                break
                        
                        # ── LLENADO ROBUSTO DE REFERENCIA (P1-Fix1) ──────────────────────────
                        # Estrategia: click + limpieza teclado + tipeo char-by-char (igual que legacy)
                        sel_ref = locators.get("input_referencia") or "input#Referencia"
                        input_ref = main_frame.wait_for_selector(sel_ref, timeout=10000)
                        input_ref.click()
                        page.keyboard.press("Control+A")
                        page.keyboard.press("Backspace")
                        for char in referencia_portal:
                            page.keyboard.type(char)
                            time.sleep(random.uniform(0.04, 0.12))
                        time.sleep(random.uniform(0.5, 1.0))
                        
                        # ── LLENADO ROBUSTO DE RFC (P1-Fix1) ─────────────────────────────────
                        sel_rfc = locators.get("input_rfc") or "input#RFC"
                        input_rfc = main_frame.wait_for_selector(sel_rfc, timeout=5000)
                        input_rfc.click()
                        page.keyboard.press("Control+A")
                        page.keyboard.press("Backspace")
                        for char in self.ctx["rfc"]:
                            page.keyboard.type(char)
                            time.sleep(random.uniform(0.04, 0.12))
                        time.sleep(random.uniform(0.8, 1.5))
                        
                        # Click Buscar
                        sel_buscar = locators.get("btn_buscar") or "button[type='submit']"
                        main_frame.wait_for_selector(sel_buscar, timeout=5000).click()
                        page.wait_for_load_state("networkidle")
                        time.sleep(2)
                        
                        # ── DETECCIÓN DE ESCENARIO (P1-Fix6: agrega caso INVALIDA) ───────────
                        escenario = "DESCONOCIDO"
                        sel_pdf = locators.get("btn_pdf") or "button:has-text('PDF'), a:has-text('PDF')"
                        sel_generar = locators.get("btn_generar_cfdi") or "button:has-text('Generar CFDI'), a:has-text('Generar CFDI')"
                        sel_salir = locators.get("btn_salir") or "a.btn.btn-default[href='./'], a:has-text('Salir')"
                        
                        alerta_danger = main_frame.query_selector("div.alert-danger, .alert-danger")
                        if alerta_danger:
                            texto_alerta = alerta_danger.inner_text().strip().lower()
                            if "no existe" in texto_alerta and "con el rfc" in texto_alerta:
                                escenario = "RFC_INCORRECTO"
                        
                        if escenario == "DESCONOCIDO":
                            btn_generar = main_frame.query_selector(sel_generar)
                            if btn_generar:
                                disabled = btn_generar.get_attribute('disabled')
                                es_disabled = disabled is not None and str(disabled).lower() != 'false'
                                escenario = "YA_GENERADA" if es_disabled else "NO_GENERADA"
                        
                        if escenario == "DESCONOCIDO":
                            # Caso: ya generada y portal solo muestra botón PDF (sin Generar CFDI)
                            if main_frame.query_selector(sel_pdf):
                                escenario = "YA_GENERADA"
                        
                        if escenario == "DESCONOCIDO":
                            # Caso: referencia o RFC no encontrados en el portal
                            invalida_el = (
                                main_frame.query_selector("text=No se encontraron registros") or
                                main_frame.query_selector("text=Referencia no válida") or
                                main_frame.query_selector("text=RFC no válido")
                            )
                            if invalida_el:
                                escenario = "INVALIDA"
                            
                        self.status_changed.emit(f"Escenario detectado en portal: {escenario}")
                        
                        if escenario == "RFC_INCORRECTO":
                            raise ValueError(f"VALIDACION: Referencia {referencia_portal} no coincide con el RFC {self.ctx['rfc']} en el portal.")
                        
                        if escenario == "INVALIDA":
                            raise ValueError(f"VALIDACION: Referencia {referencia_portal} no encontrada o inválida en el portal SATQ.")
                        if escenario == "YA_GENERADA":
                            self.status_changed.emit(f"La referencia {referencia_portal} ya está generada. Omitiendo timbrado y procediendo a descargar PDFs...")
                        
                        if escenario == "NO_GENERADA":
                            # Click Generar CFDI
                            main_frame.wait_for_selector(sel_generar, timeout=10000).click()
                            page.wait_for_load_state("networkidle")
                            time.sleep(random.uniform(1.2, 2.0))
                            
                            # ── LLENADO ROBUSTO DE RAZÓN SOCIAL (P1-Fix1) ────────────────────
                            sel_nombre = locators.get("input_nombre_receptor") or "input#NombreReceptor"
                            input_nombre = main_frame.wait_for_selector(sel_nombre, timeout=10000)
                            input_nombre.click()
                            time.sleep(random.uniform(0.2, 0.4))
                            # Estrategia 1: fill() directo
                            input_nombre.fill(str(self.ctx["razon_social"]))
                            # Verificar valor y usar fallback si el portal rechazó el fill()
                            if input_nombre.input_value().strip() != str(self.ctx["razon_social"]).strip():
                                self.status_changed.emit("fill() rechazado en Razón Social. Usando tipeo char-by-char como fallback...")
                                input_nombre.fill("")
                                page.keyboard.press("Control+A")
                                page.keyboard.press("Delete")
                                for char in str(self.ctx["razon_social"]):
                                    page.keyboard.type(char)
                                    time.sleep(random.uniform(0.02, 0.04))
                            # Validación de integridad post-fill
                            val_nombre = input_nombre.input_value().strip()
                            if not val_nombre or val_nombre != str(self.ctx["razon_social"]).strip():
                                raise Exception(f"Integridad fallida: Razón Social en portal ('{val_nombre}') != catálogo ('{self.ctx['razon_social']}')")
                            
                            # ── LLENADO ROBUSTO DE CÓDIGO POSTAL (P1-Fix1) ───────────────────
                            sel_domicilio = locators.get("input_domicilio_fiscal_receptor") or "input#DomicilioFiscalReceptor"
                            input_cp = main_frame.wait_for_selector(sel_domicilio, timeout=10000)
                            input_cp.click()
                            time.sleep(random.uniform(0.2, 0.4))
                            # Estrategia 1: fill() directo
                            input_cp.fill(str(self.ctx["codigo_postal"]))
                            # Verificar valor y usar fallback si el portal rechazó el fill()
                            if input_cp.input_value().strip() != str(self.ctx["codigo_postal"]).strip():
                                self.status_changed.emit("fill() rechazado en Código Postal. Usando tipeo char-by-char como fallback...")
                                input_cp.fill("")
                                page.keyboard.press("Control+A")
                                page.keyboard.press("Delete")
                                for char in str(self.ctx["codigo_postal"]):
                                    page.keyboard.type(char)
                                    time.sleep(random.uniform(0.02, 0.04))
                            # Validación de integridad post-fill
                            val_cp = input_cp.input_value().strip()
                            if not val_cp or val_cp != str(self.ctx["codigo_postal"]).strip():
                                raise Exception(f"Integridad fallida: CP en portal ('{val_cp}') != catálogo ('{self.ctx['codigo_postal']}')")
                            
                            time.sleep(random.uniform(0.8, 1.5))
                            
                            # Timbrar
                            sel_timbrar = locators.get("btn_timbrar") or "button#btnTimbrar"
                            main_frame.wait_for_selector(sel_timbrar, timeout=10000).click()
                            self.status_changed.emit("Timbrado enviado. Esperando confirmación del portal...")
                            
                            # ── LOOP DE ESPERA POST-TIMBRADO (P1-Fix2) ───────────────────────
                            # 3 criterios de mitigación activa (igual que legacy)
                            timbrado_ok = False
                            inicio_espera = time.time()
                            while time.time() - inicio_espera < 35:
                                try:
                                    # Criterio 1: ¿Apareció el botón PDF? → ÉXITO
                                    if main_frame.query_selector(sel_pdf):
                                        timbrado_ok = True
                                        break
                                    
                                    # Criterio 2: ¿Error HTTP 500 / FastCGI?
                                    error_html = page.content()
                                    if ("HTTP Error 500" in error_html or
                                        "FastCGI" in error_html or
                                        "Internal Server Error" in error_html):
                                        self.status_changed.emit("[PORTAL] Error HTTP 500 detectado y reintentando...")
                                        try:
                                            page.goto(satq_url, timeout=30000)
                                            page.wait_for_load_state("networkidle")
                                        except Exception:
                                            pass
                                        raise Exception("Error HTTP 500 / FastCGI en servidor SATQ tras timbrado.")
                                    
                                    # Criterio 3: ¿Cuelgue en 'Esperar...' con botón Salir visible?
                                    if time.time() - inicio_espera > 15:
                                        btn_salir = main_frame.query_selector(sel_salir)
                                        if btn_salir:
                                            self.status_changed.emit("[PORTAL] Timbrado colgado. Usando botón 'Salir' como mitigación...")
                                            try:
                                                btn_salir.click()
                                                page.wait_for_load_state("networkidle")
                                            except Exception:
                                                pass
                                            raise Exception("Transacción colgada en portal (Esperar...). Se usó botón Salir.")
                                except Exception as loop_err:
                                    # Propagar solo nuestras excepciones de mitigación
                                    err_str = str(loop_err)
                                    if "HTTP 500" in err_str or "Transacción colgada" in err_str:
                                        raise loop_err
                                    # Para errores de Playwright por recarga/navegación, re-localizar iframe
                                    self.status_changed.emit(f"Error temporal en portal (posible recarga): {loop_err}. Re-localizando iframe...")
                                    try:
                                        main_frame = page
                                        for f in page.frames:
                                            if "shacienda.qroo.gob.mx" in f.url:
                                                main_frame = f
                                                break
                                    except Exception:
                                        pass
                                time.sleep(1.0)
                            
                            if not timbrado_ok:
                                # Último recurso: clic en Salir antes de lanzar excepción
                                btn_salir_final = main_frame.query_selector(sel_salir)
                                if btn_salir_final:
                                    try:
                                        btn_salir_final.click()
                                        page.wait_for_load_state("networkidle")
                                    except Exception:
                                        pass
                                raise Exception("Timeout (35s) esperando respuesta de timbrado CFDI del portal SATQ.")
                                
                        # ── DESCARGA ROBUSTA DE PDFs (P1-Fix3) ───────────────────────────────
                        # Esperar explícitamente a que los botones PDF aparezcan (igual que legacy)
                        try:
                            main_frame.wait_for_selector(sel_pdf, timeout=30000)
                        except Exception:
                            self.status_changed.emit("Timeout esperando botones PDF. Intentando continuar...")
                        
                        # Descargar ambos PDFs de la referencia (cada referencia genera 2 facturas)
                        botones = main_frame.query_selector_all(sel_pdf)
                        if not botones:
                            raise Exception("No se encontraron botones de descarga de PDF tras espera de 30s.")
                        
                        # Descargar cada botón PDF encontrado (máximo 2)
                        num_pdfs = min(len(botones), 2)
                        for idx_pdf in range(num_pdfs):
                            temp_path = os.path.join(
                                os.environ.get("TEMP", "C:\\Temp"),
                                f"temp_factura_{referencia_portal}_{idx_pdf + 1}.pdf"
                            )
                            with page.expect_download(timeout=30000) as download_info:
                                botones[idx_pdf].click()
                            dl = download_info.value
                            dl.save_as(temp_path)
                            
                            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                                temp_pdf_paths[idx_pdf] = temp_path
                            else:
                                raise Exception(f"Archivo PDF {idx_pdf + 1} de referencia {referencia_portal} está vacío o no se guardó.")
                            
                            # Pequeña pausa entre descargas para no saturar el portal
                            if idx_pdf < num_pdfs - 1:
                                time.sleep(1)
                        
                        # Verificar que al menos el primer PDF fue descargado
                        if temp_pdf_paths[0]:
                            step_success = True
                        else:
                            raise Exception("El primer archivo PDF de la referencia no fue descargado correctamente.")
                            
                    except Exception as e:
                        if isinstance(e, ValueError) and str(e).startswith("VALIDACION:"):
                            retry_attempt = max_retries
                        else:
                            retry_attempt += 1
                            self.status_changed.emit(f"Advertencia en intento {retry_attempt}/{max_retries}: {str(e)}")
                        # Limpiar todos los temporales en caso de error
                        for tp in temp_pdf_paths:
                            if tp and os.path.exists(tp):
                                try: os.remove(tp)
                                except: pass
                        temp_pdf_paths = [None, None]
                        if retry_attempt >= max_retries:
                            err_trace = traceback.format_exc()
                            if isinstance(e, ValueError) and str(e).startswith("VALIDACION:"):
                                error_msg = str(e).replace("VALIDACION:", "").strip()
                                self.status_changed.emit(f"ERROR DE VALIDACIÓN: {error_msg}")
                                self._log_error_db(error_msg, err_trace)
                                self._mark_referencia_estado(referencia_id, "ERROR_VALIDACION", current)
                                self.referencia_generada.emit(referencia_portal, self.ctx["rfc"], "ERROR_VALIDACION")
                            else:
                                self.status_changed.emit(f"ERROR DE SISTEMA en referencia {referencia_portal}: {str(e)}")
                                self._log_error_db(str(e), err_trace)
                                self._mark_referencia_estado(referencia_id, "ERROR", current)
                                self.referencia_generada.emit(referencia_portal, self.ctx["rfc"], "ERROR")
                            
                            error_count += 1
                            self.metric_updated.emit("errores", error_count)
                            pct = int(((success_count + error_count) / total_items) * 100)
                            self.progress_changed.emit(pct)
                            break
                        # ── REINICIO DE SESIÓN EN RETRY (P1-Fix4) ────────────────────────────
                        # En lugar de solo dormir, recargar el portal para limpiar estado corrupto
                        self.status_changed.emit(f"Reiniciando portal para reintento {retry_attempt}...")
                        try:
                            page.goto(satq_url, timeout=30000)
                            page.wait_for_load_state("networkidle")
                        except Exception as reload_err:
                            self.status_changed.emit(f"No se pudo recargar el portal: {reload_err}")
                        time.sleep(random.uniform(2.0, 3.5))
                
                if step_success:
                    # Renombrado de archivos: {referencia_portal}_{DEL_PART}{grupo_id}_{n}.pdf
                    # Ejemplo: 1234567890_CAN4_1.pdf  y  1234567890_CAN4_2.pdf
                    del_part = "".join(c for c in self.ctx["delegacion_nombre"] if c.isalnum())[:3].upper()
                    grupo_id = self.ctx["grupo_id"]
                    
                    # Estructura de directorio: Facturas/[Año]/[RFC]/[Concepto]/
                    current_year = str(datetime.datetime.now().year)
                    concepto_folder = "".join(c for c in (self.ctx.get("concepto_alias") or "CONCEPTO") if c.isalnum() or c in ("-", "_"))
                    base_dir = self.custom_output_dir if self.custom_output_dir else getattr(self, "default_output_dir", "storage")
                    
                    # Verificar acceso de escritura a la ruta base
                    from sar.src.core.access_manager import check_write_access
                    is_accessible, _ = check_write_access(base_dir)
                    
                    if not is_accessible:
                        self.status_changed.emit("ALERTA: Ruta base no accesible. Activando contingencia local temporal...")
                        dest_dir = os.path.abspath(os.path.join("storage", "contingencia", "facturas", current_year, self.ctx["rfc"], concepto_folder))
                    else:
                        dest_dir = os.path.abspath(os.path.join(base_dir, "facturas" if not self.custom_output_dir else "", current_year, self.ctx["rfc"], concepto_folder))
                        
                    os.makedirs(dest_dir, exist_ok=True)
                    
                    # Mover y renombrar ambos PDFs al destino final
                    final_pdf_paths = []
                    for idx_pdf, temp_path in enumerate(temp_pdf_paths):
                        if temp_path and os.path.exists(temp_path):
                            filename = f"{referencia_portal}_{del_part}{grupo_id}_{idx_pdf + 1}.pdf"
                            final_path = os.path.join(dest_dir, filename)
                            if os.path.exists(final_path):
                                os.remove(final_path)
                            shutil.move(temp_path, final_path)
                            final_pdf_paths.append(final_path)
                            self.status_changed.emit(f"Factura {idx_pdf + 1} guardada como: {filename}")
                    
                    # Persistir registros de facturas en BD
                    self._save_facturas_db(referencia_id, final_pdf_paths, current)
                    
                    success_count += 1
                    self.metric_updated.emit("exitosos", success_count)
                    self.referencia_generada.emit(referencia_portal, self.ctx["rfc"], "EXITOSO")
                    
                    pct = int(((success_count + error_count) / total_items) * 100)
                    self.progress_changed.emit(pct)
                    self.status_changed.emit(f"Referencia {referencia_portal} procesada: {len(final_pdf_paths)} factura(s) timbrada(s) y guardada(s).")
                else:
                    # El error ya se procesó de forma resiliente en el manejador de intentos
                    pass
            
            # Final state update
            final_status = "AUTORIZADA"
            try:
                with self.db_connector.get_session() as session:
                    stmt = text("""
                        SELECT es.codigo, COUNT(r.referencia_id)
                        FROM sar_produccion.referencia r
                        JOIN sar_catalogo.estado_sistema es ON r.estado_id = es.estado_id
                        WHERE r.solicitud_id = :solicitud_id
                        GROUP BY es.codigo
                    """)
                    rows = session.execute(stmt, {"solicitud_id": self.ctx["solicitud_id"]}).fetchall()
                    
                    status_counts = {row[0]: row[1] for row in rows}
                    total_refs = sum(status_counts.values())
                    
                    facturadas = status_counts.get("FACTURADA", 0)
                    validaciones = status_counts.get("ERROR_VALIDACION", 0)
                    errores = status_counts.get("ERROR", 0)
                    total_errores = validaciones + errores
                    autorizadas = status_counts.get("AUTORIZADA", 0)
                    rechazadas = status_counts.get("RECHAZADA", 0)
                    pendientes = autorizadas
                    
                    original_state = "AUTORIZACION_PARCIAL" if rechazadas > 0 else "AUTORIZADA"
                    
                    if total_refs > 0:
                        if pendientes > 0 or total_errores > 0:
                            if facturadas > 0:
                                final_status = "FACTURADA_PARCIAL"
                            else:
                                final_status = "ERROR_VALIDACION" if validaciones > 0 else ("ERROR" if errores > 0 else original_state)
                        else:
                            # Ya se terminaron de procesar todas las AUTORIZADAS, ERROR, etc (todo es facturado)
                            final_status = "FACTURADA_PARCIAL" if rechazadas > 0 else "FACTURADA"
                    else:
                        final_status = "AUTORIZADA"
            except Exception as db_err:
                self.status_changed.emit(f"Advertencia al calcular estado final de la solicitud en BD: {db_err}")
            
            self._finalize_solicitud_in_db(final_status)
            
            if self._stop_requested:
                self.finished_processing.emit(True, f"Facturación pausada por el usuario. Estado: {final_status}")
            else:
                self._log_event_db("PROCESAR_FACTURACION", f"Finalización de facturación solicitud {self.ctx['solicitud_id']} con estado {final_status}")
                self.finished_processing.emit(True, f"Procesamiento de facturación finalizado con estado: {final_status}")

        except Exception as e:
            err_trace = traceback.format_exc()
            self.status_changed.emit(f"ERROR CRÍTICO: {str(e)}")
            self._log_error_db(str(e), err_trace)
            
            # Calculate final status dynamically instead of hardcoding "ERROR"
            final_status = "AUTORIZADA"
            try:
                with self.db_connector.get_session() as session:
                    stmt = text("""
                        SELECT es.codigo, COUNT(r.referencia_id)
                        FROM sar_produccion.referencia r
                        JOIN sar_catalogo.estado_sistema es ON r.estado_id = es.estado_id
                        WHERE r.solicitud_id = :solicitud_id
                        GROUP BY es.codigo
                    """)
                    rows = session.execute(stmt, {"solicitud_id": self.ctx["solicitud_id"]}).fetchall()
                    status_counts = {row[0]: row[1] for row in rows}
                    total_refs = sum(status_counts.values())
                    facturadas = status_counts.get("FACTURADA", 0)
                    validaciones = status_counts.get("ERROR_VALIDACION", 0)
                    errores = status_counts.get("ERROR", 0)
                    total_errores = validaciones + errores
                    autorizadas = status_counts.get("AUTORIZADA", 0)
                    rechazadas = status_counts.get("RECHAZADA", 0)
                    pendientes = autorizadas
                    
                    original_state = "AUTORIZACION_PARCIAL" if rechazadas > 0 else "AUTORIZADA"
                    
                    if total_refs > 0:
                        if pendientes > 0 or total_errores > 0:
                            if facturadas > 0:
                                final_status = "FACTURADA_PARCIAL"
                            else:
                                final_status = "ERROR_VALIDACION" if validaciones > 0 else ("ERROR" if errores > 0 else original_state)
                        else:
                            final_status = "FACTURADA_PARCIAL" if rechazadas > 0 else "FACTURADA"
            except:
                pass
            
            self._finalize_solicitud_in_db(final_status)
            self.finished_processing.emit(False, str(e))
            
        finally:
            if context:
                try: context.close()
                except: pass
            if playwright_inst:
                try: playwright_inst.stop()
                except: pass
                
            # Clean up playwright download folder
            try:
                playwright_downloads = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "playwright_downloads_facturacion")
                if os.path.exists(playwright_downloads):
                    shutil.rmtree(playwright_downloads, ignore_errors=True)
            except:
                pass

    def _save_facturas_db(self, referencia_id: int, pdf_paths: list, consecutivo: int):
        """Persiste los registros de factura para una referencia con múltiples archivos PDF.
        
        Cada referencia puede tener hasta 2 facturas (pdf_paths[0] y pdf_paths[1]).
        El primer PDF se guarda en pdf_path, el segundo en xml_path (campo reutilizado).
        Si ya existe un registro para esta referencia, se actualiza con las rutas correctas.
        """
        with self.db_connector.get_session() as session:
            # Verificar si ya existe un registro de factura para esta referencia
            dup_stmt = text("SELECT factura_id FROM sar_archivo.factura WHERE referencia_id = :rid LIMIT 1")
            dup_id = session.execute(dup_stmt, {"rid": referencia_id}).scalar()
            
            pdf_path_1 = pdf_paths[0] if len(pdf_paths) > 0 else None
            pdf_path_2 = pdf_paths[1] if len(pdf_paths) > 1 else None
            filename_1 = os.path.basename(pdf_path_1) if pdf_path_1 else ""
            
            if not dup_id:
                # Insertar nuevo registro de factura
                factura_uuid = str(uuid.uuid4())
                ins_factura = text("""
                    INSERT INTO sar_archivo.factura (referencia_id, uuid, folio, rfc_emisor, fecha_factura, pdf_path, xml_path, estado)
                    VALUES (:rid, :uuid, :folio, :rfc_emisor, :fecha, :pdf, :xml, :estado)
                """)
                session.execute(ins_factura, {
                    "rid": referencia_id,
                    "uuid": factura_uuid,
                    "folio": filename_1.replace(".pdf", ""),
                    "rfc_emisor": self.ctx["rfc"],
                    "fecha": datetime.datetime.now(datetime.timezone.utc),
                    "pdf": pdf_path_1,
                    # xml_path reutilizado para almacenar la ruta de la 2da factura hasta refactorizar el esquema
                    "xml": pdf_path_2,
                    "estado": "TIMBRADA"
                })
            else:
                # Actualizar rutas de PDFs si ya existe el registro
                upd_stmt = text("""
                    UPDATE sar_archivo.factura
                    SET pdf_path = :pdf, xml_path = :xml, estado = 'TIMBRADA'
                    WHERE factura_id = :fid
                """)
                session.execute(upd_stmt, {
                    "pdf": pdf_path_1,
                    "xml": pdf_path_2,
                    "fid": dup_id
                })
            
            # Actualizar estado de la referencia a FACTURADA
            stmt_status = text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad = 'referencia' AND codigo = 'FACTURADA' LIMIT 1")
            ref_status_id = session.execute(stmt_status).scalar()
            if not ref_status_id:
                ins_ref_stmt = text("""
                    INSERT INTO sar_catalogo.estado_sistema (entidad, codigo, descripcion)
                    VALUES ('referencia', 'FACTURADA', 'FACTURADA')
                    RETURNING estado_id
                """)
                ref_status_id = session.execute(ins_ref_stmt).scalar()
                session.flush()
                
            ref = session.get(Referencia, referencia_id)
            if ref:
                ref.estado_id = ref_status_id
            
            # Actualizar último consecutivo en Solicitud
            sol = session.get(Solicitud, self.ctx["solicitud_id"])
            if sol:
                sol.ultimo_consecutivo = consecutivo
                if consecutivo >= self.ctx["consecutivo_fin"]:
                    sol.fecha_fin = datetime.datetime.now(datetime.timezone.utc)
                if not sol.fecha_inicio:
                    sol.fecha_inicio = datetime.datetime.now(datetime.timezone.utc)
            
            # Actualizar último consecutivo en GrupoReferencia
            grupo = session.get(GrupoReferencia, self.ctx["grupo_id"])
            if grupo:
                if consecutivo > (grupo.ultimo_consecutivo or 0):
                    grupo.ultimo_consecutivo = consecutivo
                    
            session.commit()
    
    def _save_factura_db(self, referencia_id: int, pdf_path: str, filename: str, consecutivo: int):
        """Compatibilidad hacia atrás: delega a _save_facturas_db con una sola ruta."""
        self._save_facturas_db(referencia_id, [pdf_path], consecutivo)

    def _update_solicitud_estado(self, status_code: str):
        try:
            with self.db_connector.get_session() as session:
                stmt = text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad = 'solicitud' AND codigo = :codigo LIMIT 1")
                eid = session.execute(stmt, {"codigo": status_code}).scalar()
                if not eid:
                    ins_stmt = text("""
                        INSERT INTO sar_catalogo.estado_sistema (entidad, codigo, descripcion)
                        VALUES ('solicitud', :codigo, :desc)
                        RETURNING estado_id
                    """)
                    eid = session.execute(ins_stmt, {
                        "codigo": status_code,
                        "desc": f"Estado {status_code} de solicitud"
                    }).scalar()
                    session.flush()
                
                sol = session.get(Solicitud, self.ctx["solicitud_id"])
                if sol:
                    sol.estado_id = eid
                    session.commit()
        except Exception as e:
            self.status_changed.emit(f"Error actualizando estado de solicitud a {status_code}: {str(e)}")

    def _finalize_solicitud_in_db(self, status_code: str):
        try:
            with self.db_connector.get_session() as session:
                # Update Solicitud Status
                stmt = text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad = 'solicitud' AND codigo = :codigo LIMIT 1")
                sol_status_id = session.execute(stmt, {"codigo": status_code}).scalar()
                if not sol_status_id:
                    ins_stmt = text("""
                        INSERT INTO sar_catalogo.estado_sistema (entidad, codigo, descripcion)
                        VALUES ('solicitud', :codigo, :desc)
                        RETURNING estado_id
                    """)
                    sol_status_id = session.execute(ins_stmt, {
                        "codigo": status_code,
                        "desc": f"Estado {status_code} de solicitud"
                    }).scalar()
                    session.flush()
                    
                sol = session.get(Solicitud, self.ctx["solicitud_id"])
                if sol:
                    sol.estado_id = sol_status_id
                    sol.fecha_fin = datetime.datetime.now(datetime.timezone.utc)
                    session.commit()
        except Exception as e:
            self.status_changed.emit(f"Error finalizando solicitud en DB: {str(e)}")

    def _log_event_db(self, modulo: str, mensaje: str, detalle: Optional[dict] = None):
        try:
            from sar.src.storage.models import EventoSistema
            import json
            with self.db_connector.get_session() as session:
                stmt_event = text("SELECT evento_id FROM sar_catalogo.evento_sistema WHERE codigo = 'PROCESAR_SOLICITUD' LIMIT 1")
                event_id = session.execute(stmt_event).scalar()
                if not event_id:
                    event_id = 1
                
                # Insert event trace log manually or using models
                ins_stmt = text("""
                    INSERT INTO sar_auditoria.auditoria_evento (evento_id, usuario_id, sesion_id, fecha, modulo, detalle)
                    VALUES (:eid, :uid, :sid, :fecha, :modulo, :detalle)
                """)
                session.execute(ins_stmt, {
                    "eid": event_id,
                    "uid": self.ctx.get("usuario_id", 1),
                    "sid": None,
                    "fecha": datetime.datetime.now(datetime.timezone.utc),
                    "modulo": modulo,
                    "detalle": json.dumps(detalle) if detalle else None
                })
                session.commit()
        except Exception as e:
            print("DB logging event error:", e)

    def _log_error_db(self, mensaje: str, trace: str):
        try:
            with self.db_connector.get_session() as session:
                ins_stmt = text("""
                    INSERT INTO sar_auditoria.auditoria_error (usuario_id, sesion_id, modulo, mensaje, stack_trace, fecha)
                    VALUES (:uid, :sid, :mod, :msg, :trace, :fecha)
                """)
                session.execute(ins_stmt, {
                    "uid": self.ctx.get("usuario_id", 1),
                    "sid": None,
                    "mod": "BOT_FACTURACION",
                    "msg": mensaje,
                    "trace": trace,
                    "fecha": datetime.datetime.now(datetime.timezone.utc)
                })
                session.commit()
        except Exception as e:
            print("DB logging error failed:", e)

    def _capturar_pantalla(self, page, nombre_captura: str):
        """Toma una captura de pantalla completa del estado actual de la página para auditoría/soporte."""
        try:
            evidencia_dir = os.path.abspath(os.path.join("storage", "evidencia"))
            os.makedirs(evidencia_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{nombre_captura}.png"
            path_completo = os.path.join(evidencia_dir, filename)
            
            page.screenshot(path=path_completo, full_page=True)
            self.status_changed.emit(f"Evidencia guardada: {filename}")
        except Exception as e:
            self.status_changed.emit(f"Advertencia: No se pudo capturar pantalla: {str(e)}")

    def _mark_referencia_estado(self, referencia_id: int, estado_codigo: str, consecutivo: int):
        try:
            with self.db_connector.get_session() as session:
                # Get or create status in estado_sistema
                stmt_status = text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad = 'referencia' AND codigo = :codigo LIMIT 1")
                ref_status_id = session.execute(stmt_status, {"codigo": estado_codigo}).scalar()
                if not ref_status_id:
                    ins_ref_stmt = text("""
                        INSERT INTO sar_catalogo.estado_sistema (entidad, codigo, descripcion)
                        VALUES ('referencia', :codigo, :desc)
                        RETURNING estado_id
                    """)
                    ref_status_id = session.execute(ins_ref_stmt, {
                        "codigo": estado_codigo,
                        "desc": f"Estado {estado_codigo} de referencia"
                    }).scalar()
                    session.flush()
                
                # Update reference status
                ref = session.get(Referencia, referencia_id)
                if ref:
                    ref.estado_id = ref_status_id
                
                # Update last consecutive in Solicitud
                sol = session.get(Solicitud, self.ctx["solicitud_id"])
                if sol:
                    sol.ultimo_consecutivo = consecutivo
                    if not sol.fecha_inicio:
                        sol.fecha_inicio = datetime.datetime.now(datetime.timezone.utc)
                    if consecutivo >= self.ctx["consecutivo_fin"]:
                        sol.fecha_fin = datetime.datetime.now(datetime.timezone.utc)
                        
                # Update last consecutive in GrupoReferencia
                grupo = session.get(GrupoReferencia, self.ctx["grupo_id"])
                if grupo:
                    if consecutivo > (grupo.ultimo_consecutivo or 0):
                        grupo.ultimo_consecutivo = consecutivo
                        
                session.commit()
        except Exception as e:
            self.status_changed.emit(f"Error al registrar estado {estado_codigo} para referencia {referencia_id}: {str(e)}")

