"""
CancunBot — POM: Portal de Facturación Electrónica Benito Juárez
Portal: https://benitojuarez.expidefactura.com/

Los selectores NO están hardcodeados aquí.
Se resuelven desde cancunbot_configuracion.localizador_portal (portal='CANCUN_FACTURA').
"""
import logging
from typing import Tuple
from playwright.sync_api import Page

from cancunbot.src.pages.base_page import BasePage

class ExpideFacturaPage(BasePage):
    """
    Page Object Model para el portal benitojuarez.expidefactura.com.
    """

    def __init__(self, page: Page, localizadores: dict):
        super().__init__(page, localizadores)

    def navegar(self, url: str) -> None:
        """Navega al portal de facturación."""
        self.logger.info(f"Navegando a {url}")
        self.page.goto(url)
        self.esperar_carga()
        self.cerrar_modal_aviso()

    def cerrar_modal_aviso(self):
        """Cierra el modal de 'AVISO IMPORTANTE' que aparece al inicio."""
        try:
            btn_cerrar = self._resolver("CANCUN_FACTURA_MODAL_OK")
            if btn_cerrar and btn_cerrar.count() > 0 and btn_cerrar.first.is_visible(timeout=3000):
                self.logger.info("Cerrando modal de aviso inicial...")
                btn_cerrar.first.click()
            else:
                # Si no lo encuentra por selector, intenta con tecla Escape
                self.page.keyboard.press("Escape")
        except Exception as e:
            self.logger.debug(f"Sin modal de aviso o error al cerrarlo: {e}")

    def generar_factura(self, rfc: str, correo: str, folio: str, importe: str, uso_cfdi_val: str = "1") -> bool:
        """
        Ejecuta el flujo lineal para generar la factura.
        uso_cfdi_val: "1" = Adquisición de mercancías por defecto, según el HTML provisto.
        """
        self.logger.info(f"Iniciando generación de factura para el folio {folio} (RFC: {rfc})")
        
        try:
            # 1. Llenar formulario inicial
            inp_rfc = self._resolver("CANCUN_FACTURA_INPUT_RFC")
            inp_correo = self._resolver("CANCUN_FACTURA_INPUT_CORREO")
            inp_folio = self._resolver("CANCUN_FACTURA_INPUT_FOLIO")
            inp_importe = self._resolver("CANCUN_FACTURA_INPUT_IMPORTE")
            btn_cont1 = self._resolver("CANCUN_FACTURA_BTN_CONTINUAR_1")

            inp_rfc.fill(rfc)
            inp_correo.fill(correo)
            inp_folio.fill(folio)
            
            # Para activar el botón continuar en el portal, Angular requiere eventos de teclado (ng-change/onkeyup)
            inp_importe.focus()
            inp_importe.fill("")
            inp_importe.press_sequentially(importe, delay=50)
            
            self.page.wait_for_timeout(500) # Pequeña pausa para validaciones JS
            btn_cont1.click()
            self.esperar_carga()
            self.page.wait_for_timeout(1000)
            self.page.wait_for_timeout(1000)
            
            # Revisar si aparece el modal de "El ticket se encuentra facturado"
            modal_facturado = self.page.locator("text='El ticket se encuentra facturado'")
            if modal_facturado.is_visible():
                self.logger.warning("El ticket ya se encuentra facturado. Interrumpiendo flujo.")
                return False

            # 2. Continuar Datos Generales
            try:
                btn_cont2 = self._resolver("CANCUN_FACTURA_BTN_CONTINUAR_2")
                if btn_cont2 and btn_cont2.count() > 0 and btn_cont2.first.is_visible():
                    btn_cont2.click()
                    self.esperar_carga()
                    self.page.wait_for_timeout(1000)
            except KeyError:
                pass

            # 3. Seleccionar CFDI y continuar
            try:
                sel_cfdi = self._resolver("CANCUN_FACTURA_SELECT_CFDI")
                if sel_cfdi and sel_cfdi.count() > 0 and sel_cfdi.first.is_visible():
                    sel_cfdi.select_option(value=uso_cfdi_val)
                    self.page.wait_for_timeout(500)
                    
                    # VALIDACIÓN TEMPORAL (Pausar el bot con un overlay visual)
                    self.page.evaluate("""
                        let div = document.createElement('div');
                        div.id = 'temp-bot-pause';
                        div.style.position = 'fixed';
                        div.style.top = '0';
                        div.style.left = '0';
                        div.style.width = '100%';
                        div.style.height = '100%';
                        div.style.backgroundColor = 'rgba(0,0,0,0.8)';
                        div.style.color = 'white';
                        div.style.zIndex = '999999';
                        div.style.display = 'flex';
                        div.style.flexDirection = 'column';
                        div.style.alignItems = 'center';
                        div.style.justifyContent = 'center';
                        div.style.fontSize = '24px';
                        div.innerHTML = '<h2 style="color:white; margin-bottom: 20px;">✅ CFDI Seleccionado Automáticamente</h2><p>Por favor valide visualmente la selección en el formulario.</p><button id="btn-bot-resume" style="margin-top:30px; padding: 15px 30px; font-size: 20px; font-weight: bold; cursor: pointer; color: white; background-color: #22c55e; border: none; border-radius: 8px;">CONFIRMAR Y CONTINUAR</button>';
                        document.body.appendChild(div);
                        document.getElementById('btn-bot-resume').onclick = () => div.remove();
                    """)
                    self.page.wait_for_selector("#temp-bot-pause", state="hidden", timeout=0)
            except KeyError:
                pass
            
            try:
                btn_cont3 = self._resolver("CANCUN_FACTURA_BTN_CONTINUAR_3")
                if btn_cont3 and btn_cont3.count() > 0 and btn_cont3.first.is_visible():
                    btn_cont3.click()
                    self.esperar_carga()
                    self.page.wait_for_timeout(1000)
            except KeyError:
                pass
            
            # 4. Continuar Datos Producto
            try:
                btn_cont4 = self._resolver("CANCUN_FACTURA_BTN_CONTINUAR_4")
                if btn_cont4 and btn_cont4.count() > 0 and btn_cont4.first.is_visible():
                    btn_cont4.click()
                    self.esperar_carga()
            except KeyError:
                pass
                
            self.page.wait_for_timeout(2000)
            
            # 5. Generación Exitosa (Cerrar modal de OK)
            try:
                btn_ok_exito = self._resolver("CANCUN_FACTURA_MODAL_EXITO_OK")
                if btn_ok_exito and btn_ok_exito.count() > 0 and btn_ok_exito.first.is_visible():
                    self.logger.info("Cerrando modal de éxito de facturación.")
                    btn_ok_exito.first.click()
                    self.page.wait_for_timeout(1000)
            except KeyError:
                pass
            
            # 6. Buscar botones de descarga como indicio de éxito
            btn_xml = self._resolver("CANCUN_FACTURA_BTN_DESCARGAR_XML", throw_if_missing=False)
            if btn_xml and btn_xml.count() > 0:
                self.logger.info("Factura generada exitosamente. Botones de descarga disponibles.")
                return True
            else:
                self.logger.warning("No se encontraron los botones de descarga tras el flujo.")
                return False

        except Exception as e:
            self.logger.error(f"Error durante el flujo de facturación: {e}")
            return False

    def descargar_archivos(self) -> Tuple[str, str]:
        """
        Descarga el XML y el PDF de la factura generada.
        Returns: (ruta_xml, ruta_pdf)
        """
        self.logger.info("Iniciando descarga de XML y PDF...")
        ruta_xml = ""
        ruta_pdf = ""

        # Descargar XML
        try:
            with self.page.expect_download(timeout=15_000) as dl_info_xml:
                btn_xml = self._resolver("CANCUN_FACTURA_BTN_DESCARGAR_XML")
                btn_xml.click()
            download_xml = dl_info_xml.value
            ruta_xml = download_xml.path()
            self.logger.info(f"XML descargado temporalmente en: {ruta_xml}")
        except Exception as e:
            self.logger.error(f"Error descargando XML: {e}")

        # Descargar PDF
        try:
            with self.page.expect_download(timeout=15_000) as dl_info_pdf:
                btn_pdf = self._resolver("CANCUN_FACTURA_BTN_DESCARGAR_PDF")
                btn_pdf.click()
            download_pdf = dl_info_pdf.value
            ruta_pdf = download_pdf.path()
            self.logger.info(f"PDF descargado temporalmente en: {ruta_pdf}")
        except Exception as e:
            self.logger.error(f"Error descargando PDF: {e}")

        return ruta_xml, ruta_pdf
