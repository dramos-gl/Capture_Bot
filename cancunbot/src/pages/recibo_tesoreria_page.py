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
        """Navega al portal de recibos."""
        self.logger.info(f"Navegando a {url}")
        self.page.goto(url)
        self.esperar_carga()

    def consultar_folio(self, folio: str, tipo_folio: str) -> bool:
        """
        Ingresa el folio en el campo de búsqueda correspondiente, omitiendo el prefijo 'F-' si aplica,
        y limpia el otro campo para no confundir al portal.
        
        Args:
            folio: Folio electrónico o pase de caja a consultar
            tipo_folio: 'ELECTRONICO' o 'PASE_CAJA'
        
        Returns:
            True si el folio fue encontrado, False si no existe
        """
        self.logger.info(f"Consultando folio tipo {tipo_folio}: {folio}")

        # Resolver campos de entrada
        inp_elec = self._resolver("CANCUN_RECIBO_INPUT_FOLIO")              # #ayo
        inp_pase = self._resolver("CANCUN_RECIBO_INPUT_PASE_CAJA")          # #pase

        # Limpieza segura tolerante a visibilidad
        try:
            inp_elec.wait_for(state="visible", timeout=3000)
            inp_elec.clear()
        except Exception:
            self.logger.warning("Campo folio electrónico (#ayo) no está visible.")
            
        try:
            inp_pase.clear()
        except Exception:
            pass

        if tipo_folio == "ELECTRONICO":
            # Si el folio inicia con "F-", se remueve ya que el portal lo incluye por defecto.
            folio_limpio = folio
            if folio.upper().startswith("F-"):
                folio_limpio = folio[2:]
            self.logger.info(f"Folio electrónico formateado para búsqueda: {folio_limpio}")
            inp_elec.fill(folio_limpio)
        else:
            self.logger.info(f"Folio Pase de Caja para búsqueda: {folio}")
            inp_pase.fill(folio)

        self._resolver("CANCUN_RECIBO_BTN_CONSULTAR").click()
        self.esperar_carga()

        # Verificar si el folio no fue encontrado
        if self.esta_visible("CANCUN_RECIBO_MSG_NO_ENCONTRADO"):
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
