"""RPA Worker Thread for CFDI invoicing and timbrado using Playwright (Synchronous)."""

import os
import time
import datetime
import traceback
import hashlib
import shutil
import uuid
from typing import Optional, Dict, Any
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

    def __init__(self, db_connector, context: dict, headless: bool = False, custom_output_dir: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.ctx = context
        self.headless = headless
        self.custom_output_dir = custom_output_dir
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
                max_retries = int(retries_str) if retries_str else 3
                
                # Fetch Portal Locators and extract values
                db_locators = config_repo.get_localizadores()
                locators = {k: v.valor_selector for k, v in db_locators.items()}
                
            self._log_event_db("PROCESAR_FACTURACION", f"Inicio procesamiento lote facturación solicitud {self.ctx['solicitud_id']}", detalle={"consecutivo_inicio": self.ctx['consecutivo_inicio'], "consecutivo_fin": self.ctx['consecutivo_fin']})
            self._update_solicitud_estado("PROCESANDO")
            
            # 2. Launch Playwright
            self.status_changed.emit("Iniciando navegador Playwright (Headed)...")
            playwright_inst = sync_playwright().start()
            
            # Persist profile to save cache
            user_data_dir = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "perfil_bot_facturacion")
            os.makedirs(user_data_dir, exist_ok=True)
            
            playwright_downloads = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "playwright_downloads_facturacion")
            os.makedirs(playwright_downloads, exist_ok=True)
            
            # launch_persistent_context to match optima_capture_bot's persistent profiles
            context = playwright_inst.chromium.launch_persistent_context(
                user_data_dir,
                headless=self.headless,
                accept_downloads=True,
                downloads_path=playwright_downloads,
                viewport={"width": 1280, "height": 800},
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox"
                ]
            )
            
            # Avoid basic detection script
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            page = context.pages[0] if len(context.pages) > 0 else context.new_page()
            page.set_default_timeout(35000)
            
            # Load initial portal
            self.status_changed.emit(f"Navegando al portal SATQ: {satq_url}")
            page.goto(satq_url)
            page.wait_for_load_state("networkidle")
            
            # 3. Execution Loop
            start_consecutivo = self.ctx["ultimo_consecutivo"] + 1 if self.ctx["ultimo_consecutivo"] >= self.ctx["consecutivo_inicio"] else self.ctx["consecutivo_inicio"]
            end_consecutivo = self.ctx["consecutivo_fin"]
            total_items = end_consecutivo - self.ctx["consecutivo_inicio"] + 1
            
            success_count = self.ctx["ultimo_consecutivo"] - self.ctx["consecutivo_inicio"] + 1 if self.ctx["ultimo_consecutivo"] >= self.ctx["consecutivo_inicio"] else 0
            error_count = 0
            
            self.status_changed.emit(f"Facturando consecutivas desde {start_consecutivo} al {end_consecutivo}...")
            
            for current in range(start_consecutivo, end_consecutivo + 1):
                if self._stop_requested:
                    self.status_changed.emit("Proceso detenido por el usuario.")
                    break
                
                # Fetch reference portal string from database
                referencia_portal = None
                referencia_id = None
                importe = 0.0
                with self.db_connector.get_session() as db_session:
                    stmt = text("""
                        SELECT referencia_id, referencia_portal, importe 
                        FROM sar_produccion.referencia 
                        WHERE solicitud_id = :solicitud_id AND consecutivo_grupo = :consecutivo
                    """)
                    row = db_session.execute(stmt, {"solicitud_id": self.ctx["solicitud_id"], "consecutivo": current}).fetchone()
                    if row:
                        referencia_id = row.referencia_id
                        referencia_portal = row.referencia_portal
                        importe = float(row.importe) if row.importe else 0.0
                
                if not referencia_portal:
                    self.status_changed.emit(f"ADVERTENCIA: Consecutivo {current} no tiene referencia generada en BD. Saltando...")
                    error_count += 1
                    self.metric_updated.emit("errores", error_count)
                    continue
                
                self.status_changed.emit(f"Facturando referencia {referencia_portal} (Consecutivo {current})...")
                
                retry_attempt = 0
                step_success = False
                temp_pdf_path = None
                
                while retry_attempt < max_retries and not step_success:
                    if self._stop_requested:
                        break
                    try:
                        self.status_changed.emit(f"Cargando portal (Intento {retry_attempt + 1})...")
                        page.goto(satq_url)
                        page.wait_for_load_state("networkidle")
                        
                        # Find frame
                        main_frame = page
                        for f in page.frames:
                            if "shacienda.qroo.gob.mx" in f.url:
                                main_frame = f
                                break
                        
                        # Rellenar inputs de referencia y RFC
                        sel_ref = locators.get("input_referencia") or "input#Referencia"
                        main_frame.wait_for_selector(sel_ref, timeout=10000)
                        main_frame.locator(sel_ref).fill(referencia_portal)
                        
                        sel_rfc = locators.get("input_rfc") or "input#RFC"
                        main_frame.locator(sel_rfc).fill(self.ctx["rfc"])
                        
                        # Click Buscar
                        sel_buscar = locators.get("btn_buscar") or "button[type='submit']"
                        main_frame.locator(sel_buscar).click()
                        page.wait_for_load_state("networkidle")
                        time.sleep(2)
                        
                        # Detect scenario
                        escenario = "DESCONOCIDO"
                        
                        # Check alert error
                        alerta_danger = main_frame.query_selector("div.alert-danger, .alert-danger")
                        if alerta_danger:
                            texto_alerta = alerta_danger.inner_text().strip().lower()
                            if "no existe" in texto_alerta:
                                escenario = "RFC_INCORRECTO"
                        
                        sel_generar = locators.get("btn_generar_cfdi") or "button:has-text('Generar CFDI'), a:has-text('Generar CFDI')"
                        btn_generar = main_frame.query_selector(sel_generar)
                        if btn_generar:
                            disabled = btn_generar.get_attribute('disabled')
                            if disabled is not None and str(disabled).lower() != 'false':
                                escenario = "YA_GENERADA"
                            else:
                                escenario = "NO_GENERADA"
                        
                        sel_pdf = locators.get("btn_pdf") or "button:has-text('PDF'), a:has-text('PDF')"
                        if main_frame.query_selector(sel_pdf):
                            escenario = "YA_GENERADA"
                            
                        self.status_changed.emit(f"Escenario detectado en portal: {escenario}")
                        
                        if escenario == "RFC_INCORRECTO":
                            raise Exception(f"Referencia {referencia_portal} no coincide con el RFC {self.ctx['rfc']} en el portal.")
                        
                        if escenario == "NO_GENERADA":
                            # Click Generar CFDI
                            main_frame.locator(sel_generar).click()
                            page.wait_for_load_state("networkidle")
                            time.sleep(1.5)
                            
                            # Rellenar Razón Social y CP
                            sel_nombre = locators.get("input_nombre_receptor") or "input#NombreReceptor"
                            main_frame.wait_for_selector(sel_nombre, timeout=10000)
                            main_frame.locator(sel_nombre).fill(self.ctx["razon_social"])
                            
                            sel_domicilio = locators.get("input_domicilio_fiscal_receptor") or "input#DomicilioFiscalReceptor"
                            main_frame.locator(sel_domicilio).fill(self.ctx["codigo_postal"])
                            time.sleep(1)
                            
                            # Timbrar
                            sel_timbrar = locators.get("btn_timbrar") or "button#btnTimbrar"
                            main_frame.locator(sel_timbrar).click()
                            
                            # Mitigación cuelgues 35s
                            timbrado_ok = False
                            inicio_espera = time.time()
                            while time.time() - inicio_espera < 35:
                                if main_frame.query_selector(sel_pdf):
                                    timbrado_ok = True
                                    break
                                time.sleep(1)
                                
                            if not timbrado_ok:
                                raise Exception("Tiempo de espera excedido (35s) esperando respuesta de timbrado CFDI.")
                                
                        # Descargar PDF
                        botones = main_frame.query_selector_all(sel_pdf)
                        if not botones:
                            raise Exception("No se encontraron botones de descarga de PDF.")
                            
                        # Expect download
                        temp_pdf_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), f"temp_factura_{referencia_portal}.pdf")
                        with page.expect_download(timeout=30000) as download_info:
                            botones[0].click()
                        download = download_info.value
                        download.save_as(temp_pdf_path)
                        
                        if os.path.exists(temp_pdf_path) and os.path.getsize(temp_pdf_path) > 0:
                            step_success = True
                        else:
                            raise Exception("Archivo PDF descargado está vacío o no se guardó correctamente.")
                            
                    except Exception as e:
                        retry_attempt += 1
                        self.status_changed.emit(f"Advertencia en intento {retry_attempt}: {str(e)}")
                        if temp_pdf_path and os.path.exists(temp_pdf_path):
                            try: os.remove(temp_pdf_path)
                            except: pass
                        if retry_attempt >= max_retries:
                            raise e
                        time.sleep(2)
                
                if step_success:
                    # Move PDF to final path
                    # Pattern: [Download_Dir]/[Folio_Orden]/[RFC]/[RFC_DEL_CON_GRUPO_CONSEC_FACTURA.pdf]
                    rfc_part = self.ctx["rfc"][:3].upper()
                    del_part = "".join(c for c in self.ctx["delegacion_nombre"] if c.isalnum())[:3].upper()
                    con_part = self.ctx["concepto_alias"][:3].upper()
                    grupo_id = self.ctx["grupo_id"]
                    consec_str = str(current).zfill(5)
                    filename = f"{rfc_part}_{del_part}_{con_part}_{grupo_id}_{consec_str}_FACTURA.pdf"
                    
                    folio_clean = "".join(c for c in self.ctx["orden_folio"] if c.isalnum() or c in ("-", "_"))
                    base_dir = self.custom_output_dir if self.custom_output_dir else "storage"
                    dest_dir = os.path.abspath(os.path.join(base_dir, "facturas" if not self.custom_output_dir else "", folio_clean, self.ctx["rfc"]))
                    os.makedirs(dest_dir, exist_ok=True)
                    
                    final_pdf_path = os.path.join(dest_dir, filename)
                    shutil.move(temp_pdf_path, final_pdf_path)
                    
                    # Persist factura to DB
                    self._save_factura_db(referencia_id, final_pdf_path, filename, current)
                    
                    success_count += 1
                    self.metric_updated.emit("exitosos", success_count)
                    self.referencia_generada.emit(referencia_portal, self.ctx["rfc"], "EXITOSO")
                    
                    pct = int((success_count / total_items) * 100)
                    self.progress_changed.emit(pct)
                    self.status_changed.emit(f"Factura timbrada y guardada como {filename}")
                else:
                    error_count += 1
                    self.metric_updated.emit("errores", error_count)
                    self.referencia_generada.emit(referencia_portal, self.ctx["rfc"], "ERROR")
            
            # Final state update
            if self._stop_requested:
                self._update_solicitud_estado("ASIGNADO")
                self.finished_processing.emit(True, "Facturación pausada por el usuario.")
            else:
                self._finalize_solicitud_in_db("COMPLETADA")
                self._log_event_db("PROCESAR_FACTURACION", f"Finalización exitosa facturación solicitud {self.ctx['solicitud_id']}")
                self.finished_processing.emit(True, "Procesamiento de facturación completado con éxito.")
                
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

    def _save_factura_db(self, referencia_id: int, pdf_path: str, filename: str, consecutivo: int):
        with self.db_connector.get_session() as session:
            # Generate random unique UUID
            factura_uuid = str(uuid.uuid4())
            
            # Check if exists
            dup_stmt = text("SELECT factura_id FROM sar_archivo.factura WHERE referencia_id = :rid LIMIT 1")
            dup_id = session.execute(dup_stmt, {"rid": referencia_id}).scalar()
            
            if not dup_id:
                ins_factura = text("""
                    INSERT INTO sar_archivo.factura (referencia_id, uuid, folio, rfc_emisor, fecha_factura, pdf_path, xml_path, estado)
                    VALUES (:rid, :uuid, :folio, :rfc_emisor, :fecha, :pdf, :xml, :estado)
                """)
                session.execute(ins_factura, {
                    "rid": referencia_id,
                    "uuid": factura_uuid,
                    "folio": filename.replace("_FACTURA.pdf", ""),
                    "rfc_emisor": self.ctx["rfc"],
                    "fecha": datetime.datetime.now(datetime.timezone.utc),
                    "pdf": pdf_path,
                    "xml": None,
                    "estado": "TIMBRADA"
                })
            
            # Update last consecutivo on Solicitud
            sol = session.get(Solicitud, self.ctx["solicitud_id"])
            if sol:
                sol.ultimo_consecutivo = consecutivo
                # Update generated references counter if it represents progress
                if consecutivo >= self.ctx["consecutivo_fin"]:
                    sol.fecha_fin = datetime.datetime.now(datetime.timezone.utc)
                if not sol.fecha_inicio:
                    sol.fecha_inicio = datetime.datetime.now(datetime.timezone.utc)
            
            # Update last consecutivo on GrupoReferencia
            grupo = session.get(GrupoReferencia, self.ctx["grupo_id"])
            if grupo:
                if consecutivo > (grupo.ultimo_consecutivo or 0):
                    grupo.ultimo_consecutivo = consecutivo
                    
            session.commit()

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
