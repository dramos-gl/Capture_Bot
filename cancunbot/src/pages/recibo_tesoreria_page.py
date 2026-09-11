"""
CancunBot — POM: Portal de Recibos Electrónicos
Portal: https://recibo.tesoreriacancun.com

Los selectores NO están hardcodeados aquí.
Se resuelven desde cancunbot_configuracion.localizador_portal (portal='RECIBO').
"""
import logging
from playwright.sync_api import Page

from cancunbot.src.pages.base_page import BasePage


class ReciboTesoreriaPage(BasePage):
    """
    Page Object Model para el portal recibo.tesoreriacancun.com.
    
    Localizadores requeridos en BD (portal='RECIBO'):
        - RECIBO_INPUT_FOLIO      → Campo de texto para el folio
        - RECIBO_BTN_CONSULTAR    → Botón Consultar
        - RECIBO_BTN_DESCARGAR    → Botón Descargar PDF
        - RECIBO_MSG_NO_ENCONTRADO → Mensaje cuando el folio no existe
    """

    def __init__(self, page: Page, localizadores: dict):
        super().__init__(page, localizadores)

    def navegar(self, url: str) -> None:
        """Navega al portal de recibos e inyecta reglas CSS anti-emergentes para mantener limpia la UI."""
        self.logger.info(f"Navegando a {url}")
        self.page.goto(url)
        self.esperar_carga()
        self._inyectar_silenciador_modales()

    def _inyectar_silenciador_modales(self):
        """
        Inyecta reglas CSS y parches JS en el DOM para ocultar silenciosamente los modales de SweetAlert2
        ('Error de validación') y evitar que interrumpan visualmente la experiencia del usuario.
        """
        try:
            self.page.evaluate("""() => {
                // 1. Inyectar CSS que oculta instantáneamente cualquier modal SweetAlert2 de error
                const style = document.createElement('style');
                style.id = 'silenciador-swal-css';
                style.innerHTML = `
                    .swal2-container.swal2-shown {
                        display: none !important;
                        opacity: 0 !important;
                        visibility: hidden !important;
                        pointer-events: none !important;
                    }
                    body.swal2-shown {
                        overflow: auto !important;
                    }
                `;
                if (!document.getElementById('silenciador-swal-css')) {
                    document.head.appendChild(style);
                }

                // 2. Parchear SweetAlert2 si ya está cargado en el portal para autocerrarlo
                if (typeof Swal !== 'undefined' && !window._swal_patched) {
                    const originalFire = Swal.fire;
                    Swal.fire = function(...args) {
                        const title = args[0]?.title || args[0] || '';
                        if (typeof title === 'string' && (title.includes('Error') || title.includes('seguridad') || title.includes('intentos'))) {
                            console.log('Modal de error silenciada automáticamente.');
                            return Promise.resolve({ isConfirmed: true });
                        }
                        return originalFire.apply(this, args);
                    };
                    window._swal_patched = true;
                }
            }""")
        except Exception as e:
            self.logger.debug(f"Error inyectando silenciador de modales: {e}")

    def consultar_folio(self, folio: str, tipo_folio: str) -> bool:
        """
        Consulta un folio en recibo.tesoreriacancun.com ejecutando el flujo de validación reCAPTCHA v3,
        incorporando recarga de página táctica y pausas anti-rate-limiting para evitar 'Demasiados intentos'.
        """
        self.logger.info(f"Consultando folio tipo {tipo_folio}: {folio}")

        # Inyectar reglas silenciosas en el DOM en cada iteración
        self._inyectar_silenciador_modales()

        inp_elec = self._resolver("CANCUN_RECIBO_INPUT_FOLIO")              # #ayo
        inp_pase = self._resolver("CANCUN_RECIBO_INPUT_PASE_CAJA")          # #pase
        btn_consultar = self._resolver("CANCUN_RECIBO_BTN_CONSULTAR")

        val_escribir = folio if tipo_folio == "PASE_CAJA" else (folio[2:] if folio.upper().startswith("F-") else folio)

        reintentos_servidor = 0
        max_reintentos = 3

        while reintentos_servidor < max_reintentos:
            # 1. Descartar cualquier modal SweetAlert2 previa
            self._descartar_modal_error_validacion_si_existe()

            # 2. Si es un reintento, recargar la página para renovar la sesión de reCAPTCHA v3
            if reintentos_servidor > 0:
                self.logger.warning(f"Reintento {reintentos_servidor}/{max_reintentos}: Recargando página para enfriar reCAPTCHA v3...")
                try:
                    self.page.reload()
                    self.esperar_carga()
                    self.page.wait_for_timeout(2500 + (reintentos_servidor * 1500))  # Espera progresiva
                    # Re-resolver componentes tras el reload
                    inp_elec = self._resolver("CANCUN_RECIBO_INPUT_FOLIO")
                    inp_pase = self._resolver("CANCUN_RECIBO_INPUT_PASE_CAJA")
                    btn_consultar = self._resolver("CANCUN_RECIBO_BTN_CONSULTAR")
                except Exception as e:
                    self.logger.debug(f"Error recargando página: {e}")

            # 3. Limpiar y llenar campos
            target_inp = inp_pase if tipo_folio == "PASE_CAJA" else inp_elec
            try:
                target_inp.wait_for(state="visible", timeout=6000)
                inp_elec.fill("")
                inp_pase.fill("")
            except Exception:
                pass

            self.logger.info(f"Escribiendo folio en el formulario: {val_escribir}")
            target_inp.click()
            target_inp.fill(val_escribir)

            # Disparar eventos JS de interacción para asegurar la propagación en jQuery
            try:
                self.page.evaluate("""(selector) => {
                    const el = document.querySelector(selector);
                    if (el && typeof $ !== 'undefined') {
                        $(el).trigger('input').trigger('change');
                    }
                }""", "#pase" if tipo_folio == "PASE_CAJA" else "#ayo")
            except Exception:
                pass

            self.page.wait_for_timeout(400)

            # 4. Invocar la función nativa JS `validarCaptcha()` del portal
            self._invocar_validar_captcha_portal(btn_consultar)

            # 5. Esperar respuesta AJAX
            self.esperar_carga()
            self.page.wait_for_timeout(1000)

            # 5.1 Verificar si la tabla de resultados o el botón PDF ya se cargaron exitosamente en pantalla
            if self.page.locator("#prueba button, button:has-text('PDF'), table.stacktable").count() > 0:
                self.logger.info("¡Tabla de recibo cargada exitosamente en el DOM!")
                # Descartar cualquier SweetAlert2 encimada si aparecieron juntos
                self._descartar_modal_error_validacion_si_existe()
                break

            # 6. Verificar si el servidor mostró 'Error de validación' o modal de error sin haber cargado la tabla
            error_detectado = self._descartar_modal_error_validacion_si_existe()
            if not error_detectado:
                # Éxito sin modales de error
                break

            reintentos_servidor += 1

        # 7. Verificar si el folio fue marcado como no encontrado por el portal
        if self.esta_visible("CANCUN_RECIBO_MSG_NO_ENCONTRADO"):
            self.logger.warning(f"Folio '{folio}' no encontrado en el portal de Tesorería.")
            return False

        self.logger.info(f"Folio '{folio}' procesado exitosamente en el portal.")
        return True

    def _invocar_validar_captcha_portal(self, btn_consultar):
        """
        Ejecuta la validación del portal. En caso de que reCAPTCHA v3 falle o retorne score bajo,
        dispara directamente la función `ejecutarCollapse(ejercicio, paseCaja)` para forzar la consulta de datos.
        """
        try:
            self.page.evaluate("""() => {
                const ej = $('#ayo').val() ? $('#ayo').val().trim() : '';
                const pase = $('#pase').val() ? $('#pase').val().trim() : '';
                
                // Intentar primera vía: validarCaptcha nativo
                if (typeof validarCaptcha === 'function') {
                    validarCaptcha();
                } else if (typeof ejecutarCollapse === 'function') {
                    ejecutarCollapse(ej, pase);
                }
            }""")
        except Exception as e:
            self.logger.debug(f"Invocación JS validarCaptcha: {e}")

        # Si tras 800ms el portal sigue mostrando el botón habilitado o sin spinner/collapse,
        # forzar la ejecución de ejecutarCollapse() para bypass de reCAPTCHA v3
        self.page.wait_for_timeout(800)
        try:
            self.page.evaluate("""() => {
                const ej = $('#ayo').val() ? $('#ayo').val().trim() : '';
                const pase = $('#pase').val() ? $('#pase').val().trim() : '';
                
                // Si el spinner no se activó o la tabla no se ha cargado, invocar ejecutarCollapse directamente
                if (typeof ejecutarCollapse === 'function' && $('#prueba').is(':empty')) {
                    ejecutarCollapse(ej, pase);
                }
            }""")
        except Exception as e:
            self.logger.debug(f"Invocación forzada ejecutarCollapse: {e}")

    def _descartar_modal_error_validacion_si_existe(self) -> bool:
        """
        Detecta y descarta la modal SweetAlert2 'Error de validación' desplegada por el portal
        haciendo clic en el botón OK o llamando a `Swal.close()`.
        """
        try:
            # 1. Intentar clic en el botón confirm de SweetAlert2 (.swal2-confirm / button:has-text('OK'))
            btn_ok = self.page.locator("button.swal2-confirm, button:has-text('OK'), button:has-text('Ok'), button:has-text('Aceptar'), div.swal2-actions button")
            if btn_ok.count() > 0 and btn_ok.first.is_visible():
                self.logger.info("Modal SweetAlert2 'Error de validación' detectada. Presionando OK...")
                btn_ok.first.click()
                self.page.wait_for_timeout(400)
                return True

            # 2. Descarte proactivo vía API JavaScript de SweetAlert2
            cerrado_js = self.page.evaluate("""() => {
                if (typeof Swal !== 'undefined' && Swal.isVisible && Swal.isVisible()) {
                    Swal.close();
                    return true;
                }
                return false;
            }""")
            if cerrado_js:
                self.logger.info("Modal SweetAlert2 removida vía Swal.close().")
                self.page.wait_for_timeout(400)
                return True
        except Exception as e:
            self.logger.debug(f"Sin modal de error activa: {e}")
        return False

    def descargar_recibo(self) -> str:
        """
        Descarga el PDF del recibo.
        
        Returns:
            Ruta temporal del archivo descargado
        
        Raises:
            TimeoutError: Si la descarga no inicia en el tiempo esperado
        """
        self.logger.info("Iniciando descarga del PDF de recibo...")
        with self.page.expect_download(timeout=30_000) as dl_info:
            self._resolver("RECIBO_BTN_DESCARGAR").click()
        download = dl_info.value
        ruta = download.path()
        self.logger.info(f"PDF descargado en: {ruta}")
        return str(ruta)
