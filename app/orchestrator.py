import os
import csv
import time
import queue
import logging
import threading
from datetime import datetime
import openpyxl

from app.excel_handler import cargar_registros, cargar_catalog_rfc, actualizar_fila, verificar_bloqueo, SHEET_DATA, COL_ERROR
from app.validator import validar_rfc, validar_referencia, validar_duplicados_locales
from app.scraper import SatqScraper
from app.paths import LOGS_DIR

logger = logging.getLogger("OptimaCaptureBot.Orchestrator")

class BotOrchestrator:
    def __init__(self, excel_path, event_queue):
        self.excel_path = excel_path
        self.event_queue = event_queue
        
        # Estado de ejecución
        self.hilo_trabajo = None
        self.is_running = False
        self.is_paused = False
        self.stop_requested = False
        
        # Scraper de Playwright
        self.scraper = None
        
        # Datos del catálogo
        self.empresa_datos = None
        self.registros = []
        
        # Lock de sincronización para estados
        self.state_lock = threading.Lock()
        
        # Evento de sincronización para la validación previa al timbrado
        self._timbrar_event = threading.Event()
        self._timbrar_aprobado = False
        
        # Configuración de modo de descarga
        self.solo_no_generadas = False

    def enviar_log(self, mensaje, nivel="INFO"):
        """
        Envía un log formateado tanto al sistema local como a la cola de la interfaz de usuario.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] [{nivel}] {mensaje}"
        
        # Log del sistema
        if nivel == "ERROR":
            logger.error(mensaje)
        elif nivel == "WARNING":
            logger.warning(mensaje)
        else:
            logger.info(mensaje)
            
        # Enviar a la UI
        self.event_queue.put({"type": "log", "message": log_msg, "nivel": nivel})

    def actualizar_metricas_ui(self):
        """
        Calcula las métricas actuales del lote y las envía a la UI.
        """
        pendientes = sum(1 for r in self.registros if r["estado"] in ["PENDIENTE", "VALIDADO", "EN_PROCESO"])
        exitosos   = sum(1 for r in self.registros if r["estado"] in ["EXITOSO", "OK-GENERADA", "OK-YA GENERADA"])
        errores    = sum(1 for r in self.registros if r["estado"] in ["ERROR_PORTAL", "ERROR_VALIDACION", "ERROR_LOCAL"])
        omitidos   = sum(1 for r in self.registros if r["estado"] in ["OMITIDO", "OMITIDO-YA GENERADA", "DUPLICADO"])
        revision   = sum(1 for r in self.registros if r["estado"] == "REQUIERE_REVISION")
        
        self.event_queue.put({
            "type": "metrics",
            "pendientes": pendientes,
            "exitosos": exitosos,
            "errores": errores,
            "omitidos": omitidos,
            "revision": revision,
            "total": len(self.registros)
        })

    def iniciar(self, solo_no_generadas=False):
        """
        Lanza el proceso de automatización en un hilo secundario para mantener responsiva la UI.
        :param solo_no_generadas: Si True, el bot omite las referencias que ya fueron generadas en el portal.
        """
        with self.state_lock:
            if self.is_running:
                return False
            
            self.is_running = True
            self.is_paused = False
            self.stop_requested = False
            self.solo_no_generadas = solo_no_generadas
            
            self.hilo_trabajo = threading.Thread(target=self._worker, name="BotWorkerThread")
            self.hilo_trabajo.daemon = True
            self.hilo_trabajo.start()
            return True

    def pausar(self):
        """
        Pausa la ejecución al terminar el registro actual.
        """
        with self.state_lock:
            if self.is_running and not self.is_paused:
                self.is_paused = True
                self.enviar_log("Pausa solicitada. El bot se detendrá al completar el registro actual.", "WARNING")
                return True
        return False

    def reanudar(self):
        """
        Reanuda la ejecución pausada.
        """
        with self.state_lock:
            if self.is_running and self.is_paused:
                self.is_paused = False
                self.enviar_log("Reanudando ejecución...", "INFO")
                return True
        return False

    def detener(self):
        """
        Detiene la ejecución del bot de forma segura.
        """
        with self.state_lock:
            if self.is_running:
                self.stop_requested = True
                self.is_paused = False
                self.enviar_log("Detención segura solicitada. Cerrando procesos...", "WARNING")
                return True
        return False

    def notificar_login_completado(self):
        """
        Permite al operador notificar desde la UI que la fase de autenticación manual terminó.
        """
        self.event_queue.put({"type": "login_completado_senal"})

    def notificar_timbrado_aprobado(self):
        """
        El operador aprobó los datos desde la GUI: el bot puede proceder a timbrar.
        """
        self._timbrar_aprobado = True
        self._timbrar_event.set()

    def notificar_timbrado_cancelado(self):
        """
        El operador rechazó los datos desde la GUI: el bot cancela el timbrado de esta fila.
        """
        self._timbrar_aprobado = False
        self._timbrar_event.set()

    def _registrar_auditoria(self, razon_social, cp, aprobado, modo):
        """
        Escribe cada decisión de timbrado en logs/auditoria_timbrado.csv
        para trazabilidad fiscal completa y revisión posterior.
        Columnas: timestamp, razon_social, cp, aprobado, modo
        """
        audit_file = str(LOGS_DIR / "auditoria_timbrado.csv")
        agregar_encabezado = not os.path.exists(audit_file)
        try:
            with open(audit_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if agregar_encabezado:
                    writer.writerow(["timestamp", "razon_social", "cp", "aprobado", "modo"])
                writer.writerow([
                    datetime.now().isoformat(timespec="seconds"),
                    razon_social,
                    cp,
                    "SI" if aprobado else "NO",
                    modo.upper()
                ])
        except Exception as audit_err:
            self.enviar_log(f"[AUDITÓRÍA] No se pudo escribir el registro de auditoría: {audit_err}", "WARNING")

    def _callback_validar_timbrar(self, razon_social, cp):
        """
        Callback que el Scraper invoca antes de timbrar.

        Modo ASISTIDO: Notifica a la GUI, bloquea el hilo hasta que el operador decida.
        Modo AUTÓNOMO: Aprueba de inmediato y escribe registro de auditoría sin interrumpir el flujo.

        Retorna True (proceder) o False (cancelar) según el modo y la decisión del operador.
        """
        from app import settings
        modo = settings.get_modo_timbrado()   # Lee el valor persistido en settings.json

        if modo == "autonomo":
            # ── MODO AUTÓNOMO: aprobar sin pausa ──────────────────────────────
            self.enviar_log(
                f"[AUTÓNOMO] ✓ Timbrado aprobado automáticamente. "
                f"Razón Social='{razon_social}' | CP='{cp}'",
                "WARNING"  # WARNING para que quede visible y resaltado en la consola
            )
            self._registrar_auditoria(razon_social, cp, aprobado=True, modo="autonomo")
            return True
        else:
            # ── MODO ASISTIDO: pausa y espera aprobación manual ──────────────────
            # Limpiar el evento antes de esperar
            self._timbrar_event.clear()
            self._timbrar_aprobado = False

            # Enviar evento a la GUI para mostrar el panel de validación
            self.event_queue.put({
                "type": "waiting_timbrar",
                "razon_social": razon_social,
                "cp": cp
            })

            # Bloquear el hilo del bot hasta que el operador decida (timeout de seguridad 5 min)
            self.enviar_log(
                f"[VALIDACIÓN] Esperando aprobación del operador. "
                f"Razón Social='{razon_social}' | CP='{cp}'", "WARNING"
            )
            aprobado_antes_de_timeout = self._timbrar_event.wait(timeout=300)

            # Ocultar el panel de validación en la GUI
            self.event_queue.put({"type": "timbrar_respondido"})

            if not aprobado_antes_de_timeout:
                self.enviar_log("[VALIDACIÓN] ⏳ El tiempo de espera (5 min) expiró sin respuesta del operador.", "ERROR")
                self._registrar_auditoria(
                    razon_social, cp,
                    aprobado=False,
                    modo="asistido_timeout"
                )
                return False

            self._registrar_auditoria(
                razon_social, cp,
                aprobado=self._timbrar_aprobado,
                modo="asistido"
            )
            return self._timbrar_aprobado

    def _verificar_espera_pausa(self):
        """
        Bucle de espera pasiva si el bot se encuentra pausado.
        Retorna True si se solicitó detener mientras estaba en pausa.
        """
        while True:
            with self.state_lock:
                if self.stop_requested:
                    return True
                if not self.is_paused:
                    return False
            time.sleep(0.5)

    def _worker(self):
        """
        Bucle de trabajo del hilo secundario. Ejecuta las fases del bot con extra cautela.
        """
        try:
            self.enviar_log("Iniciando orquestador operativo...", "INFO")
            
            # --- FASE 1: Carga e integridad inicial del Excel ---
            self.enviar_log("Cargando catálogo de RFC y registros del Excel...", "INFO")
            
            # Verificar bloqueo de archivo antes de cargar
            if verificar_bloqueo(self.excel_path):
                self.event_queue.put({
                    "type": "blocked", 
                    "message": "El archivo Optima_Capture_Bot.xlsx está bloqueado por Excel. Por favor, ciérrelo en Windows."
                })
                self.is_running = False
                return
                
            self.empresa_datos = cargar_catalog_rfc(self.excel_path)
            self.registros = cargar_registros(self.excel_path)
            
            self.enviar_log(f"Catálogo RFC: {self.empresa_datos['rfc']} ({self.empresa_datos['razon_social']})", "INFO")
            self.enviar_log(f"Total registros cargados de Excel: {len(self.registros)}", "INFO")
            self.actualizar_metricas_ui()
            
            # --- FASE 2: Validación sintáctica inicial y anti-duplicados ---
            self.enviar_log("Ejecutando depuración previa y detección de duplicados locales...", "INFO")
            rfc_valido, rfc_err = validar_rfc(self.empresa_datos["rfc"])
            if not rfc_valido:
                self.enviar_log(f"Error crítico de negocio: {rfc_err}", "ERROR")
                self.is_running = False
                return
                
            filas_duplicadas = validar_duplicados_locales(self.registros)
            
            # Procesamiento de validación previa fila por fila
            for reg in self.registros:
                fila = reg["fila_excel"]
                ref = reg["referencia"]
                
                if reg["estado"] == "PENDIENTE":
                    # Validar referencia
                    ref_valida, ref_err = validar_referencia(ref)
                    
                    if not ref_valida:
                        self.enviar_log(f"Fila {fila}: validación fallida de referencia. Motivo: {ref_err}", "WARNING")
                        actualizar_fila(self.excel_path, fila, "ERROR_VALIDACION", rfc=self.empresa_datos["rfc"], detalle_error=ref_err)
                        reg["estado"] = "ERROR_VALIDACION"
                    elif fila in filas_duplicadas:
                        self.enviar_log(f"Fila {fila}: Referencia duplicada detectada internamente.", "WARNING")
                        actualizar_fila(self.excel_path, fila, "DUPLICADO", rfc=self.empresa_datos["rfc"], detalle_error="Referencia repetida en el lote")
                        reg["estado"] = "DUPLICADO"
                    else:
                        # Marcamos como validado
                        actualizar_fila(self.excel_path, fila, "VALIDADO", rfc=self.empresa_datos["rfc"])
                        reg["estado"] = "VALIDADO"
                        
            self.actualizar_metricas_ui()
            self.enviar_log("Depuración previa completada de forma segura.", "INFO")
            
            # Verificar si quedan registros válidos por procesar
            pendientes = [r for r in self.registros if r["estado"] in ["VALIDADO", "ERROR_REINTENTABLE"]]
            if not pendientes:
                self.enviar_log("No existen referencias pendientes de consulta en el portal SATQ.", "INFO")
                self.event_queue.put({"type": "finished"})
                self.is_running = False
                return
                
            # --- FASE 3: Inicialización de Playwright y Autenticación Asistida ---
            self.enviar_log("Iniciando navegador Playwright...", "INFO")
            from app import settings
            download_dir = settings.get_download_dir() or "downloads"
            self.scraper = SatqScraper(download_root=download_dir)
            
            if not self.scraper.iniciar_navegador():
                self.enviar_log("No se pudo iniciar el navegador de Playwright.", "ERROR")
                self.is_running = False
                return
                
            # El portal no requiere autenticación; continuar directamente
            self.enviar_log("No se requiere inicio de sesión manual. Continuando con el proceso.", "INFO")
            login_exitoso = True

            
            # --- FASE 4: Procesamiento Secuencial Fila por Fila ---
            for reg in self.registros:
                # Comprobar pausa segura
                if self._verificar_espera_pausa():
                    break
                    
                # Comprobar detención segura
                with self.state_lock:
                    if self.stop_requested:
                        break
                        
                fila = reg["fila_excel"]
                ref = reg["referencia"]
                
                # Procesar solo registros listos
                if reg["estado"] not in ["VALIDADO", "ERROR_REINTENTABLE"]:
                    continue
                    
                # Notificar fila actual a la UI
                self.event_queue.put({
                    "type": "status",
                    "fila": fila,
                    "referencia": ref,
                    "rfc": self.empresa_datos["rfc"],
                    "estado": "EN_PROCESO",
                    "accion": "Iniciando consulta..."
                })
                
                # Clasificación automática de lote (carpetas físicas cada 100 filas)
                # Fila 2 a 101 -> Lote_1, Fila 102 a 201 -> Lote_2, etc.
                numero_lote = ((fila - 2) // 100) + 1
                nombre_lote = f"Lote_{numero_lote}"
                
                # Actualizar celda a EN_PROCESO en caliente
                self.enviar_log(f"Procesando Fila {fila}: [Referencia: {ref}] en carpeta {nombre_lote}", "INFO")
                
                # Reintentos automáticos ante bloqueos del Excel (Extra Cautela)
                guardado_ok = False
                while not guardado_ok:
                    try:
                        actualizar_fila(self.excel_path, fila, "EN_PROCESO", lote=nombre_lote)
                        guardado_ok = True
                    except PermissionError:
                        self.enviar_log("Advertencia: El archivo Excel está bloqueado. Pausando bot.", "WARNING")
                        self.event_queue.put({
                            "type": "blocked", 
                            "message": f"Cierre Optima_Capture_Bot.xlsx para guardar progreso de Fila {fila}."
                        })
                        # Esperar hasta que se libere el archivo Excel
                        time.sleep(3.0)
                        
                reg["estado"] = "EN_PROCESO"
                self.actualizar_metricas_ui()
                
                # Ejecutar consulta web y descargas
                self.event_queue.put({
                    "type": "status",
                    "fila": fila,
                    "referencia": ref,
                    "rfc": self.empresa_datos["rfc"],
                    "estado": "EN_PROCESO",
                    "accion": "Buscando documento..."
                })
                
                estado_res, lote_res, error_res, screenshot_res = self.scraper.procesar_registro(
                    referencia=ref,
                    rfc=self.empresa_datos["rfc"],
                    carpeta_lote=nombre_lote,
                    razon_social=self.empresa_datos["razon_social"],
                    cp=self.empresa_datos["cp"],
                    callback_validar_timbrar=self._callback_validar_timbrar,
                    solo_no_generadas=self.solo_no_generadas
                )
                # If the scraper indicates a reintentoable error, pause execution for user intervention
                if estado_res == "ERROR_REINTENTABLE":
                    self.enviar_log("Se detectó error reintentable; pausando el bot.", "WARNING")
                    self.pausar()
                    self.event_queue.put({"type": "paused", "reason": "ERROR_REINTENTABLE"})
                
                # --- FASE 5: Actualización atómica del resultado en Excel ---
                guardado_ok = False
                while not guardado_ok:
                    try:
                        actualizar_fila(
                            self.excel_path, 
                            fila, 
                            estado_res, 
                            lote=lote_res, 
                            detalle_error=error_res, 
                            rfc=self.empresa_datos["rfc"]
                        )
                        # Si tiene captura de pantalla (string), registrarla en la columna de control dedicada. Omitir si es una lista de archivos.
                        if screenshot_res and not isinstance(screenshot_res, list):
                            wb = openpyxl.load_workbook(self.excel_path)
                            ws = wb[SHEET_DATA]
                            ws.cell(row=fila, column=COL_ERROR + 1, value=str(screenshot_res)) # Columna H
                            wb.save(self.excel_path)
                            wb.close()
                            
                        guardado_ok = True
                    except PermissionError:
                        self.enviar_log("Advertencia: El archivo Excel está bloqueado. Pausando bot para guardar el resultado.", "WARNING")
                        self.event_queue.put({
                            "type": "blocked", 
                            "message": f"Cierre el Excel para registrar el resultado final de la Fila {fila}."
                        })
                        time.sleep(3.0)
                    except Exception as err_critico:
                        self.enviar_log(f"Error fatal del sistema al intentar guardar la Fila {fila}: {err_critico}", "ERROR")
                        estado_res = "ERROR_LOCAL"
                        error_res = str(err_critico)
                        guardado_ok = True  # Salir del bucle para no colgar el bot y continuar con la siguiente fila
                        
                reg["estado"] = estado_res

                # Enviar reporte del registro a la UI
                if estado_res in ("EXITOSO", "OK-YA GENERADA", "OK-GENERADA"):
                    self.enviar_log(f"Referencia {ref} procesada con éxito.", "SUCCESS")
                else:
                    self.enviar_log(f"Referencia {ref} falló: {error_res}", "ERROR")
                
                self.actualizar_metricas_ui()                
            self.enviar_log("Procesamiento de registros completado.", "INFO")
            
        except Exception as e:
            self.enviar_log(f"Error crítico en el hilo de procesamiento del orquestador: {e}", "ERROR")
            
        finally:
            # El navegador permanece abierto para que el usuario lo cierre manualmente
            if self.scraper:
                self.enviar_log("El navegador permanece abierto. Ciérrelo manualmente cuando lo desee.", "INFO")
            self.is_running = False
            self.event_queue.put({"type": "finished"})
            self.enviar_log("Orquestador finalizado de forma ordenada.", "INFO")
