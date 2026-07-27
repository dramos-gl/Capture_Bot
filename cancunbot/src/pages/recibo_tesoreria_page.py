"""
CancunBot — POM: Portal de Recibos Electrónicos
Portal: https://recibo.tesoreriacancun.com

Los selectores NO están hardcodeados aquí.
Se resuelven desde cancunbot_configuracion.localizador_portal (portal='RECIBO').
"""
import logging
from playwright.sync_api import Page

from src.pages.base_page import BasePage


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
        """Navega al portal de recibos."""
        self.logger.info(f"Navegando a {url}")
        self.page.goto(url)
        self.esperar_carga()

    def consultar_folio(self, folio: str) -> bool:
        """
        Ingresa el folio en el campo de búsqueda y ejecuta la consulta.
        
        Args:
            folio: Folio electrónico o pase de caja a consultar
        
        Returns:
            True si el folio fue encontrado, False si no existe
        """
        self.logger.info(f"Consultando folio: {folio}")

        inp = self._resolver("RECIBO_INPUT_FOLIO")
        inp.wait_for(state="visible")
        inp.clear()
        inp.fill(folio)

        self._resolver("RECIBO_BTN_CONSULTAR").click()
        self.esperar_carga()

        # Verificar si el folio no fue encontrado
        if self.esta_visible("RECIBO_MSG_NO_ENCONTRADO"):
            self.logger.warning(f"Folio '{folio}' no encontrado en el portal.")
            return False

        self.logger.info(f"Folio '{folio}' encontrado en el portal.")
        return True

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
