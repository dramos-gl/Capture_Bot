"""RPA Worker Thread for reference generation using Playwright (Synchronous)."""

import os
import time
import datetime
import traceback
import hashlib
import shutil
from typing import Optional, Dict, Any
from PySide6.QtCore import QThread, Signal
from playwright.sync_api import sync_playwright
from sar.src.core.playwright_setup import resolve_chromium_executable
from sqlalchemy import text

from sar.src.storage.repositories import ReferenciaRepository, AuditRepository, ConfigRepository
from sar.src.storage.models import Referencia, ArchivoPDF, EstadoSistema, Solicitud, GrupoReferencia, OrdenGeneracion

class RpaWorker(QThread):
    """Secondary thread to run Playwright steps without freezing the PyQt GUI."""
    
    # UI Interaction Signals
    status_changed = Signal(str)
    progress_changed = Signal(int)
    metric_updated = Signal(str, int)  # metric_name ('pendientes', 'exitosos', 'errores'), value
    referencia_generada = Signal(str, str, str)  # ref_portal, rfc, status
    finished_processing = Signal(bool, str)  # success, message

    def __init__(self, db_connector, context: dict, headless: bool = False, custom_output_dir: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.ctx = context
        self.headless = headless
        self.custom_output_dir = custom_output_dir
        self._stop_requested = False
        
        from sar.src.storage.api_client import APIClient
        self.api_client = APIClient()

    def stop(self):
        """Safely requests the worker to stop processing between loops."""
        self._stop_requested = True
        self.status_changed.emit("Detención solicitada. Finalizando el ciclo actual...")

    def run(self):
        self.status_changed.emit("Iniciando Worker RPA...")
        playwright_inst = None
        browser = None
        context = None
        
        try:
            # 1. Load Parameters and Locators
            self.status_changed.emit("Cargando parámetros y localizadores...")
            if self.api_client.connect_via_api:
                res_url = self.api_client.request("GET", "/api/docs/config/parametro/TRIBUTANET_RPP_URL")
                rpp_url = res_url.get("valor") or "https://shacienda.qroo.gob.mx/tributanet/rpp/dec_rpp_control.php?tipo_declaracion=1"
                
                res_retries = self.api_client.request("GET", "/api/docs/config/parametro/REINTENTOS_AUTOMATICOS")
                retries_str = res_retries.get("valor")
                max_retries = int(retries_str) if retries_str else 3
                
                res_ruta = self.api_client.request("GET", "/api/docs/config/parametro/RUTA_DERECHOS")
                self.default_output_dir = res_ruta.get("valor") or "storage"
                
                locators = self.api_client.request("GET", "/api/docs/config/localizadores")
            else:
                with self.db_connector.get_session() as db_session:
                    config_repo = ConfigRepository(db_session)
                    rpp_url = config_repo.get_parametro("TRIBUTANET_RPP_URL") or "https://shacienda.qroo.gob.mx/tributanet/rpp/dec_rpp_control.php?tipo_declaracion=1"
                    retries_str = config_repo.get_parametro("REINTENTOS_AUTOMATICOS")
                    max_retries = int(retries_str) if retries_str else 3
                    self.default_output_dir = config_repo.get_parametro("RUTA_DERECHOS") or "storage"
                    db_locators = config_repo.get_localizadores()
                    locators = {k: v.valor_selector for k, v in db_locators.items()}
                
            # Log Start of Batch in Audit Event
            self._log_event_db("PROCESAR_SOLICITUD", f"Inicio procesamiento lote solicitud {self.ctx['solicitud_id']}", detalle={"consecutivo_inicio": self.ctx['consecutivo_inicio'], "consecutivo_fin": self.ctx['consecutivo_fin']})
            self._update_solicitud_estado("PROCESANDO")
            
            # 2. Launch Playwright (Synchronous mode)
            self.status_changed.emit("Verificando navegador Playwright...")
            playwright_inst = sync_playwright().start()
            
            # Resolve browser executable (handles frozen PyInstaller deployments)
            executable_path = resolve_chromium_executable(
                progress_callback=lambda msg: self.status_changed.emit(msg)
            )
            
            # Browser setup with stealth arguments
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
            
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                accept_downloads=True,
                ignore_https_errors=True
            )
            
            # Avoid webdriver detection
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 3. Execution Loop
            start_consecutivo = self.ctx["ultimo_consecutivo"] + 1 if self.ctx["ultimo_consecutivo"] >= self.ctx["consecutivo_inicio"] else self.ctx["consecutivo_inicio"]
            end_consecutivo = self.ctx["consecutivo_fin"]
            total_items = end_consecutivo - self.ctx["consecutivo_inicio"] + 1
            
            success_count = self.ctx["ultimo_consecutivo"] - self.ctx["consecutivo_inicio"] + 1 if self.ctx["ultimo_consecutivo"] >= self.ctx["consecutivo_inicio"] else 0
            error_count = 0
            
            self.status_changed.emit(f"Procesando desde consecutivo {start_consecutivo} al {end_consecutivo}...")
            
            for current in range(start_consecutivo, end_consecutivo + 1):
                if self._stop_requested:
                    self.status_changed.emit("Proceso detenido por el usuario.")
                    break
                
                self.status_changed.emit(f"Generando consecutivo {current} de {end_consecutivo}...")
                
                # Setup page and direct navigation
                page = context.new_page()
                page.set_default_timeout(30000)
                
                retry_attempt = 0
                step_success = False
                ref_portal = ""
                importe_val = 0.0
                fecha_vencimiento_val = None
                temp_pdf_path = None
                
                while retry_attempt < max_retries and not step_success:
                    if self._stop_requested:
                        break
                    try:
                        self.status_changed.emit(f"Navegando al portal (Intento {retry_attempt + 1})...")
                        page.goto(rpp_url)
                        
                        # Step A: Select Municipio and Fill RFC on Access Form
                        mun_selector = locators.get("ddlMunicipio")
                        if mun_selector:
                            page.wait_for_selector(mun_selector, state="visible")
                            page.locator(mun_selector).select_option(value=self.ctx["municipio"])
                            
                        self._fill_locator(page, locators.get("txtRFC"), self.ctx["rfc"])
                        self._click_locator(page, locators.get("btnEnviar"))
                        
                        # Step B: Main Form Page
                        page.wait_for_load_state("domcontentloaded")
                        
                        # Set customer address & info (Matching elements 1-9 on form screen capture)
                        self._fill_locator(page, locators.get("txtNombre"), self.ctx["razon_social"])      # 1
                        self._fill_locator(page, locators.get("txtCalle"), self.ctx["calle"] or "Calle Conocida") # 2
                        self._fill_locator(page, locators.get("txtColonia"), self.ctx["colonia"])          # 3
                        self._fill_locator(page, locators.get("txtNumeroExterior"), self.ctx["no_exterior"])# 4
                        self._fill_locator(page, locators.get("txtNumeroInterior"), self.ctx["no_interior"])# 5
                        self._fill_locator(page, locators.get("txtCodigoPostal"), self.ctx["codigo_postal"])# 6
                        self._fill_locator(page, locators.get("txtLocalidad"), self.ctx["localidad"])      # 7
                        self._fill_locator(page, locators.get("txtMunicipioRfc"), self.ctx.get("rfc_municipio", "")) # 8
                        self._fill_locator(page, locators.get("txtEstadoRfc"), self.ctx.get("rfc_estado", ""))       # 9
                        
                        # Select Delegacion (10)
                        self._select_option_fuzzy(page, locators.get("ddlDelegacion"), self.ctx["delegacion_nombre"])
                        
                        # Select Concepto (11)
                        concepto_alias = self.ctx.get("concepto_alias", "").upper()
                        concepto_codigo = self.ctx.get("concepto_codigo_portal", "")
                        concepto_nombre = self.ctx.get("concepto_nombre", "")
                        
                        es_analisis = (concepto_alias in ("ANA", "ANALISIS") or
                                       "ANÁLISIS Y CALIFICACIÓN" in concepto_nombre.upper() or
                                       "ANALISIS Y CALIFICACION" in concepto_nombre.upper() or
                                       (concepto_codigo and concepto_codigo.startswith("132-1")))
                        
                        ddl_concepto = locators.get("ddlConcepto")
                        if es_analisis:
                            try:
                                page.wait_for_selector(ddl_concepto, state="visible")
                                selected_val = page.locator(ddl_concepto).input_value()
                                if selected_val and selected_val.startswith("132-1"):
                                    self.status_changed.emit("El concepto 'Análisis y calificación...' ya está seleccionado por defecto. Omitiendo selección del desplegable.")
                                else:
                                    self.status_changed.emit("Seleccionando concepto 'Análisis y calificación...' por valor de portal...")
                                    page.locator(ddl_concepto).select_option(value=concepto_codigo)
                            except Exception as e:
                                self.status_changed.emit(f"Error verificando selección por defecto: {str(e)}. Seleccionando por valor...")
                                try:
                                    page.locator(ddl_concepto).select_option(value=concepto_codigo)
                                except:
                                    self._select_option_fuzzy(page, ddl_concepto, concepto_nombre)
                        else:
                            # For other concepts, strictly select by the portal code value to avoid errors
                            if concepto_codigo:
                                self.status_changed.emit(f"Seleccionando concepto '{concepto_nombre}' estrictamente por valor de portal...")
                                page.wait_for_selector(ddl_concepto, state="visible")
                                page.locator(ddl_concepto).select_option(value=concepto_codigo)
                            else:
                                self.status_changed.emit(f"Advertencia: no se encontró código de portal para el concepto. Usando selección fuzzy...")
                                self._select_option_fuzzy(page, ddl_concepto, concepto_nombre)
                        
                        # Click Add Concept
                        self._click_locator(page, locators.get("btnAgregarConcepto"))
                        time.sleep(1) # Allow page scripts to add row
                        
                        # Click Generate Boleta
                        self._click_locator(page, locators.get("btnGenerarBoleta"))
                        page.wait_for_load_state("networkidle")
                        
                        # Step C: Extract results
                        ref_text_raw = self._get_text_locator(page, locators.get("lblBoletaReferencia"))
                        # Sanitize reference (usually contains text like "REFERENCIA: 012629...")
                        ref_portal = "".join(filter(str.isdigit, ref_text_raw))
                        
                        imp_text_raw = self._get_text_locator(page, locators.get("lblBoletaImporte"))
                        # Extract float value
                        imp_clean = "".join(c for c in imp_text_raw if c.isdigit() or c == '.')
                        importe_val = float(imp_clean) if imp_clean else 0.0
                        
                        date_text_raw = self._get_text_locator(page, locators.get("lblBoletaFechaLimite"))
                        # Parse date (Tributanet standard DD/MM/YYYY)
                        fecha_vencimiento_val = self._parse_portal_date(date_text_raw)
                        
                        # Step D: Save the generated screen boleta directly as PDF (instead of opening system print dialog)
                        temp_pdf_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), f"temp_bot_{ref_portal}.pdf")
                        
                        # Generate PDF file natively from current Chromium tab state
                        page.pdf(
                            path=temp_pdf_path,
                            format="Letter",
                            print_background=True,
                            margin={"top": "0.4in", "right": "0.4in", "bottom": "0.4in", "left": "0.4in"}
                        )
                        
                        if os.path.exists(temp_pdf_path) and os.path.getsize(temp_pdf_path) > 0:
                            step_success = True
                        else:
                            raise Exception("La conversión nativa a PDF de la boleta falló.")
                            
                    except Exception as e:
                        retry_attempt += 1
                        self.status_changed.emit(f"Advertencia en intento {retry_attempt}: {str(e)}")
                        if temp_pdf_path and os.path.exists(temp_pdf_path):
                            try: os.remove(temp_pdf_path)
                            except: pass
                        if retry_attempt >= max_retries:
                            raise e
                        time.sleep(2)
                
                page.close()
                
                if step_success:
                    # Rename Face A: referencia_DELEGACION_3_GRUPO_ID_[CONSECUTIVO_5].pdf
                    del_part = "".join(c for c in self.ctx["delegacion_nombre"] if c.isalnum())[:3].upper()
                    grupo_id = self.ctx["grupo_id"]
                    consec_str = str(current).zfill(5)
                    filename = f"{ref_portal}_{del_part}_{grupo_id}_{consec_str}.pdf"
                    
                    folio_clean = "".join(c for c in self.ctx["orden_folio"] if c.isalnum() or c in ("-", "_"))
                    concepto_folder = "".join(c for c in (self.ctx.get("concepto_alias") or "CONCEPTO") if c.isalnum() or c in ("-", "_"))
                    base_dir = self.custom_output_dir if self.custom_output_dir else getattr(self, "default_output_dir", "storage")
                    
                    # Verify write access to base_dir
                    from sar.src.core.access_manager import check_write_access
                    is_accessible, _ = check_write_access(base_dir)
                    
                    if not is_accessible:
                        self.status_changed.emit("ALERTA: Ruta base no accesible. Activando contingencia local temporal...")
                        # Save in local contingency folder preserving structural folders: contingencia/boletas/orden/RFC/concepto/
                        dest_dir = os.path.abspath(os.path.join("storage", "contingencia", "boletas", folio_clean, self.ctx["rfc"], concepto_folder))
                    else:
                        dest_dir = os.path.abspath(os.path.join(base_dir, "boletas" if not self.custom_output_dir else "", folio_clean, self.ctx["rfc"], concepto_folder))
                        
                    os.makedirs(dest_dir, exist_ok=True)
                    
                    final_pdf_path = os.path.join(dest_dir, filename)
                    shutil.move(temp_pdf_path, final_pdf_path)
                    
                    # Compute SHA-256 hash of the final PDF
                    pdf_hash = self._get_file_sha256(final_pdf_path)
                    pdf_size = os.path.getsize(final_pdf_path)
                    
                    # 4. Save to DB
                    self._save_referencia_db(current, ref_portal, importe_val, fecha_vencimiento_val, filename, final_pdf_path, pdf_hash, pdf_size)
                    
                    success_count += 1
                    self.metric_updated.emit("exitosos", success_count)
                    self.referencia_generada.emit(ref_portal, self.ctx["rfc"], "EXITOSO")
                    
                    # Calculate progress percentage
                    pct = int((success_count / total_items) * 100)
                    self.progress_changed.emit(pct)
                    self.status_changed.emit(f"Referencia {ref_portal} guardada como {filename}")
                else:
                    error_count += 1
                    self.metric_updated.emit("errores", error_count)
                    self.referencia_generada.emit("FALLA", self.ctx["rfc"], "ERROR")
            
            # Final state update
            if self._stop_requested:
                self._update_solicitud_estado("ASIGNADA")
                self.finished_processing.emit(True, "Ejecución pausada por el usuario.")
            else:
                self._finalize_solicitud_in_db("COMPLETADA")
                self._log_event_db("PROCESAR_SOLICITUD", f"Finalización exitosa lote solicitud {self.ctx['solicitud_id']}")
                self.finished_processing.emit(True, "Procesamiento completado con éxito.")
                
        except Exception as e:
            err_trace = traceback.format_exc()
            self.status_changed.emit(f"ERROR CRÍTICO: {str(e)}")
            self._log_error_db(str(e), err_trace)
            self._update_solicitud_estado("ERROR")
            self.finished_processing.emit(False, str(e))
            
        finally:
            if context:
                try: context.close()
                except: pass
            if browser:
                try: browser.close()
                except: pass
            if playwright_inst:
                try: playwright_inst.stop()
                except: pass

    # Helper Database Transactions
    def _save_referencia_db(self, consecutivo: int, ref_portal: str, importe: float, fecha_vig: Optional[datetime.date], filename: str, path: str, sha256: str, size: int):
        if self.api_client.connect_via_api:
            fecha_vig_str = fecha_vig.strftime("%Y-%m-%d") if fecha_vig else None
            payload = {
                "solicitud_id": self.ctx["solicitud_id"],
                "grupo_id": self.ctx["grupo_id"],
                "consecutivo": consecutivo,
                "referencia_portal": ref_portal,
                "importe": importe,
                "fecha_vigencia": fecha_vig_str,
                "usuario_id": self.ctx.get("usuario_id") or 1,
                "pdf_filename": filename,
                "pdf_path": path,
                "pdf_hash": sha256,
                "pdf_size": size
            }
            self.api_client.request("POST", "/api/docs/referencias/bot", data=payload)
        else:
            with self.db_connector.get_session() as session:
                state_stmt = text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad = 'referencia' AND codigo = 'GENERADA' LIMIT 1")
                state_id = session.execute(state_stmt).scalar()
                if not state_id:
                    state_id = session.execute(text("SELECT estado_id FROM sar_catalogo.estado_sistema LIMIT 1")).scalar() or 1
                    
                ref = Referencia(
                    grupo_id=self.ctx["grupo_id"],
                    solicitud_id=self.ctx["solicitud_id"],
                    consecutivo_grupo=consecutivo,
                    referencia_portal=ref_portal,
                    importe=importe,
                    fecha_generacion=datetime.datetime.now(datetime.timezone.utc),
                    fecha_vigencia=fecha_vig,
                    estado_id=state_id,
                    usuario_asignado=self.ctx.get("usuario_id")
                )
                session.add(ref)
                session.flush()
                
                pdf = ArchivoPDF(
                    referencia_id=ref.referencia_id,
                    tipo_archivo="BOLETA_PAGO",
                    estado_archivo="DESCARGADO",
                    nombre_archivo=filename,
                    ruta_archivo=path,
                    hash_sha256=sha256,
                    tamano_bytes=size
                )
                session.add(pdf)
                
                sol = session.get(Solicitud, self.ctx["solicitud_id"])
                if sol:
                    sol.ultimo_consecutivo = consecutivo
                    sol.cantidad_generada = (sol.cantidad_generada or 0) + 1
                    if consecutivo >= self.ctx["consecutivo_fin"]:
                        sol.fecha_fin = datetime.datetime.now(datetime.timezone.utc)
                    if not sol.fecha_inicio:
                        sol.fecha_inicio = datetime.datetime.now(datetime.timezone.utc)
                        
                grupo = session.get(GrupoReferencia, self.ctx["grupo_id"])
                if grupo:
                    if consecutivo > (grupo.ultimo_consecutivo or 0):
                        grupo.ultimo_consecutivo = consecutivo
                    grupo.cantidad_generada = (grupo.cantidad_generada or 0) + 1
                    
                session.commit()

    def _update_solicitud_estado(self, status_code: str):
        try:
            if self.api_client.connect_via_api:
                self.api_client.request("POST", f"/api/docs/solicitudes/{self.ctx['solicitud_id']}/estado", data={"status_code": status_code})
            else:
                with self.db_connector.get_session() as session:
                    def get_or_create_status(entidad: str, codigo: str) -> int:
                        stmt = text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad = :entidad AND codigo = :codigo LIMIT 1")
                        eid = session.execute(stmt, {"entidad": entidad, "codigo": codigo}).scalar()
                        if not eid:
                            ins_stmt = text("""
                                INSERT INTO sar_catalogo.estado_sistema (entidad, codigo, descripcion)
                                VALUES (:entidad, :codigo, :desc)
                                RETURNING estado_id
                            """)
                            eid = session.execute(ins_stmt, {
                                "entidad": entidad,
                                "codigo": codigo,
                                "desc": f"Estado {codigo} de {entidad}"
                            }).scalar()
                            session.flush()
                        return eid

                    state_id = get_or_create_status("solicitud", status_code)
                    sol = session.get(Solicitud, self.ctx["solicitud_id"])
                    if sol:
                        sol.estado_id = state_id
                        session.commit()
        except Exception as e:
            self.status_changed.emit(f"Error actualizando estado a {status_code}: {str(e)}")

    def _finalize_solicitud_in_db(self, status_code: str):
        """Updates status of Solicitud, checks group status, and cascades up to OrdenGeneracion if all done."""
        try:
            if self.api_client.connect_via_api:
                self.api_client.request("POST", f"/api/docs/solicitudes/{self.ctx['solicitud_id']}/finalizar", data={"status_code": status_code})
            else:
                with self.db_connector.get_session() as session:
                    def get_or_create_status(entidad: str, codigo: str) -> int:
                        stmt = text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad = :entidad AND codigo = :codigo LIMIT 1")
                        eid = session.execute(stmt, {"entidad": entidad, "codigo": codigo}).scalar()
                        if not eid:
                            ins_stmt = text("""
                                INSERT INTO sar_catalogo.estado_sistema (entidad, codigo, descripcion)
                                VALUES (:entidad, :codigo, :desc)
                                RETURNING estado_id
                            """)
                            eid = session.execute(ins_stmt, {
                                "entidad": entidad,
                                "codigo": codigo,
                                "desc": f"Estado {codigo} de {entidad}"
                            }).scalar()
                            session.flush()
                        return eid

                    sol_status_id = get_or_create_status("solicitud", status_code)
                    sol = session.get(Solicitud, self.ctx["solicitud_id"])
                    if sol:
                        sol.estado_id = sol_status_id
                        sol.fecha_fin = datetime.datetime.now(datetime.timezone.utc)
                        session.flush()
                        
                        if status_code == "COMPLETADA":
                            pending_auth_status_id = get_or_create_status("referencia", "PENDIENTE_AUTORIZACION")
                            upd_ref_stmt = text("""
                                UPDATE sar_produccion.referencia
                                SET estado_id = :new_state
                                WHERE solicitud_id = :sol_id
                            """)
                            session.execute(upd_ref_stmt, {"new_state": pending_auth_status_id, "sol_id": self.ctx["solicitud_id"]})
                            session.flush()

                        grupo = session.get(GrupoReferencia, sol.grupo_id)
                        if grupo:
                            all_sol_stm = text("""
                                SELECT COUNT(*) FROM sar_produccion.solicitud s
                                JOIN sar_catalogo.estado_sistema es ON s.estado_id = es.estado_id
                                WHERE s.grupo_id = :grupo_id AND es.codigo != 'COMPLETADA'
                            """)
                            pending_sols = session.execute(all_sol_stm, {"grupo_id": grupo.grupo_id}).scalar()
                            
                            if pending_sols == 0 or (grupo.cantidad_generada or 0) >= grupo.cantidad_solicitada:
                                grupo_status_id = get_or_create_status("grupo_referencia", "COMPLETADO")
                                grupo.estado_id = grupo_status_id
                                session.flush()

                            orden = session.get(OrdenGeneracion, grupo.orden_id)
                            if orden:
                                all_grupo_stm = text("""
                                    SELECT COUNT(*) FROM sar_produccion.grupo_referencia gr
                                    JOIN sar_catalogo.estado_sistema es ON gr.estado_id = es.estado_id
                                    WHERE gr.orden_id = :orden_id AND es.codigo != 'COMPLETADO'
                                """)
                                pending_grupos = session.execute(all_grupo_stm, {"orden_id": orden.orden_id}).scalar()
                                
                                total_req_stm = text("SELECT SUM(cantidad_solicitada), SUM(cantidad_generada) FROM sar_produccion.grupo_referencia WHERE orden_id = :orden_id")
                                tot_req, tot_gen = session.execute(total_req_stm, {"orden_id": orden.orden_id}).fetchone()
                                
                                if pending_grupos == 0 or (tot_gen and tot_req and tot_gen >= tot_req):
                                    orden_status_id = get_or_create_status("orden_generacion", "PENDIENTE_AUTORIZACION")
                                    orden.estado_id = orden_status_id
                                    session.flush()
                    
                    session.commit()
        except Exception as e:
            self.status_changed.emit(f"Error al finalizar la solicitud en la base de datos: {str(e)}")

    def _log_event_db(self, event_code: str, message: str, detalle: Optional[dict] = None):
        try:
            if self.api_client.connect_via_api:
                payload = {
                    "evento_codigo": event_code,
                    "modulo": "BOT_FACE_A",
                    "usuario_id": self.ctx.get("usuario_id") or 1,
                    "sesion_id": None,
                    "detalle": detalle
                }
                self.api_client.request("POST", "/api/docs/audit/evento", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    repo = AuditRepository(session)
                    repo.log_evento(
                        evento_codigo=event_code,
                        modulo="BOT_FACE_A",
                        usuario_id=1,
                        sesion_id=None,
                        detalle=detalle
                    )
                    session.commit()
        except:
            pass

    def _log_error_db(self, message: str, traceback_str: str):
        try:
            if self.api_client.connect_via_api:
                payload = {
                    "usuario_id": self.ctx.get("usuario_id") or 1,
                    "sesion_id": None,
                    "modulo": "BOT_FACE_A",
                    "mensaje": message,
                    "stack_trace": traceback_str
                }
                self.api_client.request("POST", "/api/docs/audit/error", data=payload)
            else:
                with self.db_connector.get_session() as session:
                    repo = AuditRepository(session)
                    repo.log_error(
                        usuario_id=1,
                        sesion_id=None,
                        modulo="BOT_FACE_A",
                        mensaje=message,
                        stack_trace=traceback_str
                    )
                    session.commit()
        except Exception as ex:
            self.status_changed.emit(f"Error escribiendo logs de error en BD: {str(ex)}")

    # Playwright Web Helpers
    def _fill_locator(self, page, selector: Optional[str], value):
        if not selector or not value: return
        page.wait_for_selector(selector, state="visible")
        page.locator(selector).fill(str(value))

    def _click_locator(self, page, selector: Optional[str]):
        if not selector: return
        page.wait_for_selector(selector, state="visible")
        page.locator(selector).click()

    def _get_text_locator(self, page, selector: Optional[str]) -> str:
        if not selector: return ""
        page.wait_for_selector(selector, state="visible")
        return page.locator(selector).inner_text().strip()

    def _select_option_fuzzy(self, page, selector: Optional[str], option_name: str):
        if not selector or not option_name: return
        page.wait_for_selector(selector, state="visible")
        
        # Try fuzzy match in dropdown options
        options = page.locator(f"{selector} option").all_inner_texts()
        self.status_changed.emit(f"Desplegable {selector}: buscando '{option_name}' entre {len(options)} opciones...")
        
        match_val = None
        for opt in options:
            if option_name.upper() in opt.upper() or opt.upper() in option_name.upper():
                # Extract value attribute
                match_val = page.eval_on_selector(
                    f"{selector}",
                    f"(sel, name) => Array.from(sel.options).find(o => o.text.toUpperCase().includes(name.toUpperCase()) || name.toUpperCase().includes(o.text.toUpperCase()))?.value",
                    option_name
                )
                if match_val:
                    self.status_changed.emit(f"Coincidencia encontrada para '{option_name}': valor '{match_val}'")
                    break
                
        if match_val:
            page.locator(selector).select_option(value=match_val)
        else:
            # Fallback direct selection by label
            try:
                self.status_changed.emit(f"Intentando selección directa de etiqueta para '{option_name}'...")
                page.locator(selector).select_option(label=option_name)
            except Exception as select_err:
                self.status_changed.emit(f"Fallo al seleccionar etiqueta. Seleccionando primera opción disponible por defecto.")
                # Fallback to index 1 (usually the first real option after placeholder)
                try:
                    page.locator(selector).select_option(index=1)
                except:
                    pass

    def _parse_portal_date(self, raw_date_text: str) -> Optional[datetime.date]:
        # Formats: "FECHA LIMITE: 2026-06-30", "FECHA LIMITE: 28/06/2026", etc.
        try:
            cleaned = "".join(c for c in raw_date_text if c.isdigit() or c in ('/', '-'))
            if '-' in cleaned:
                parts = cleaned.split('-')
                if len(parts) == 3:
                    # YYYY-MM-DD
                    if len(parts[0]) == 4:
                        return datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
                    # DD-MM-YYYY
                    elif len(parts[2]) == 4:
                        return datetime.date(int(parts[2]), int(parts[1]), int(parts[0]))
            elif '/' in cleaned:
                parts = cleaned.split('/')
                if len(parts) == 3:
                    # DD/MM/YYYY
                    if len(parts[2]) == 4:
                        return datetime.date(int(parts[2]), int(parts[1]), int(parts[0]))
        except:
            pass
        return None

    def _get_file_sha256(self, filepath: str) -> str:
        h = hashlib.sha256()
        with open(filepath, 'rb') as file:
            while True:
                chunk = file.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
