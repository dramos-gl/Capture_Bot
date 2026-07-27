"""
CancunBot — POM: Portal de Facturación Electrónica
Portal: https://benitojuarez.expidefactura.com/

Los selectores NO están hardcodeados aquí.
Se resuelven desde cancunbot_configuracion.localizador_portal (portal='FACTURA').
"""
import logging
from playwright.sync_api import Page

from src.pages.base_page import BasePage


class ExpideFacturaPage(BasePage):
    """
    Page Object Model para el portal benitojuarez.expidefactura.com.
    
    Localizadores requeridos en BD (portal='FACTURA'):
        - FACTURA_INPUT_RFC          → Campo RFC del contribuyente
        - FACTURA_INPUT_CORREO       → Campo correo electrónico
        - FACTURA_INPUT_FOLIO        → Campo folio electrónico
        - FACTURA_INPUT_IMPORTE      → Campo importe
        - FACTURA_BTN_GENERAR        → Botón Generar / Timbrar
        - FACTURA_BTN_DESCARGAR_PDF  → Botón Descargar PDF de factura
        - FACTURA_BTN_DESCARGAR_XML  → Botón Descargar XML de factura
        - FACTURA_MSG_EXITO          → Mensaje de éxito
        - FACTURA_MSG_ERROR          → Mensaje de error
    """

    def __init__(self, page: Page, localizadores: dict):
        super().__init__(page, localizadores)

    def navegar(self, url: str) -> None:
        """Navega al portal de facturación."""
        self.logger.info(f"Navegando a {url}")
        self.page.goto(url)
        self.esperar_carga()

    def llenar_formulario(self, rfc: str, correo: str,
                          folio_electronico: str, importe: float) -> None:
        """
        Llena el formulario de facturación con los datos del recibo.
        Implementa Smart Fill: omite el llenado si el campo ya tiene el valor correcto.
        
        Args:
            rfc: RFC del contribuyente
            correo: Correo electrónico para recibir la factura
            folio_electronico: Folio electrónico del recibo
            importe: Importe total del recibo
        """
        self.logger.info(f"Llenando formulario: RFC={rfc}, Folio={folio_electronico}")

        campos = [
            ("FACTURA_INPUT_RFC",    rfc),
            ("FACTURA_INPUT_CORREO", correo),
            ("FACTURA_INPUT_FOLIO",  folio_electronico),
            ("FACTURA_INPUT_IMPORTE", str(importe)),
        ]

        for nombre_clave, valor in campos:
            elemento = self._resolver(nombre_clave)
            elemento.wait_for(state="visible")

            # Smart Fill: omite si el valor ya coincide
            valor_actual = elemento.input_value()
            if valor_actual.strip() == valor.strip():
                self.logger.debug(f"SmartFill: '{nombre_clave}' ya tiene el valor correcto. Omitiendo.")
                continue

            elemento.clear()
            elemento.fill(valor)
            self.logger.debug(f"Llenado: '{nombre_clave}' = '{valor}'")

    def generar_factura(self) -> bool:
        """
        Hace clic en el botón de generar factura y verifica el resultado.
        
        Returns:
            True si la factura fue generada exitosamente, False en caso de error
        """
        self.logger.info("Generando factura...")
        self._resolver("FACTURA_BTN_GENERAR").click()
        self.esperar_carga()

        if self.esta_visible("FACTURA_MSG_EXITO"):
            self.logger.info("Factura generada exitosamente.")
            return True

        if self.esta_visible("FACTURA_MSG_ERROR"):
            self.logger.error("Error al generar la factura — portal reportó error.")
            return False

        self.logger.warning("Estado desconocido tras generar factura.")
        return False

    def descargar_pdf(self) -> str:
        """
        Descarga el PDF de la factura generada.
        
        Returns:
            Ruta temporal del archivo PDF descargado
        """
        self.logger.info("Descargando PDF de factura...")
        with self.page.expect_download(timeout=30_000) as dl_info:
            self._resolver("FACTURA_BTN_DESCARGAR_PDF").click()
        ruta = str(dl_info.value.path())
        self.logger.info(f"PDF de factura descargado en: {ruta}")
        return ruta

    def descargar_xml(self) -> str:
        """
        Descarga el XML (CFDI) de la factura generada.
        
        Returns:
            Ruta temporal del archivo XML descargado
        """
        self.logger.info("Descargando XML de factura...")
        with self.page.expect_download(timeout=30_000) as dl_info:
            self._resolver("FACTURA_BTN_DESCARGAR_XML").click()
        ruta = str(dl_info.value.path())
        self.logger.info(f"XML de factura descargado en: {ruta}")
        return ruta
