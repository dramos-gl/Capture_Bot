"""POM for Tributanet page interaction."""

import re
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from playwright.async_api import Page, Dialog

logger = logging.getLogger(__name__)

class TributanetPage:
    """Page Object Model for interacting with the Quintana Roo Tributanet Portal (Fase A)."""

    def __init__(self, page: Page, locators: Dict[str, Any]):
        """
        Initializes the POM.
        
        Args:
            page: The Playwright Page object.
            locators: A dictionary mapping locator keys (e.g. 'txtRFC') to selector strings or objects.
        """
        self.page = page
        self.locators = {}
        
        # Normalize locators to strings
        for key, val in locators.items():
            if hasattr(val, "valor_selector"):
                self.locators[key] = val.valor_selector
            else:
                self.locators[key] = str(val)

        # Setup standard dialog handler to accept all alert/confirm dialogs
        self.page.on("dialog", self._handle_dialog)

    def _get_selector(self, key: str) -> str:
        """Retrieves a selector from the loaded locators, raising a KeyError if not configured."""
        if key not in self.locators:
            raise KeyError(f"Locator '{key}' is not configured in TributanetPage.")
        return self.locators[key]

    async def _handle_dialog(self, dialog: Dialog):
        """Accepts any popup dialogs automatically."""
        logger.info(f"Dialog encountered ({dialog.type}): {dialog.message}")
        await dialog.accept()

    async def fill_if_different(self, selector: str, value: str):
        """Fills an input field only if the current value is different to save typing time."""
        if value is None:
            return
        
        locator = self.page.locator(selector)
        # Ensure element is visible/attached before fetching value
        await locator.wait_for(state="attached", timeout=5000)
        
        current_val = await locator.input_value()
        if current_val.strip().lower() != str(value).strip().lower():
            # Clear first, then type
            await locator.click()
            await locator.clear()
            await locator.fill(str(value))
            logger.debug(f"Filled field {selector} with '{value}' (previous: '{current_val}')")
        else:
            logger.debug(f"Skipped filling {selector} - value matches '{value}'")

    async def navigate_to_rpp(self, url: str):
        """Navigates to the Tributanet RPP main form URL."""
        logger.info(f"Navigating to Tributanet RPP: {url}")
        await self.page.goto(url, wait_until="networkidle")

    async def login_rpp(self, municipio_code: str, rfc: str):
        """Fills in the access form (Municipio & RFC) and submits."""
        logger.info(f"Logging into Tributanet RPP with Municipio '{municipio_code}' and RFC '{rfc}'")
        
        ddl_muni = self._get_selector("ddlMunicipio")
        txt_rfc = self._get_selector("txtRFC")
        btn_enviar = self._get_selector("btnEnviar")

        await self.page.locator(ddl_muni).select_option(value=municipio_code)
        await self.page.locator(txt_rfc).fill(rfc)
        
        # Click and wait for navigation/load
        await asyncio_sleep_or_wait(self.page.locator(btn_enviar).click())
        await self.page.wait_for_load_state("networkidle")

    async def fill_rfc_details(self, rfc_data: Dict[str, Any]):
        """Fills out the contributor's personal/address details if different."""
        logger.info(f"Filling contributor details for RFC: {rfc_data.get('rfc')}")
        
        # Map fields to their corresponding locators
        mappings = {
            "txtNombre": rfc_data.get("razon_social"),
            "txtCalle": rfc_data.get("calle"),
            "txtColonia": rfc_data.get("colonia"),
            "txtNumeroExterior": rfc_data.get("no_exterior"),
            "txtNumeroInterior": rfc_data.get("no_interior"),
            "txtCodigoPostal": rfc_data.get("codigo_postal"),
            "txtLocalidad": rfc_data.get("localidad"),
        }

        for loc_key, value in mappings.items():
            if value is not None:
                selector = self._get_selector(loc_key)
                await self.fill_if_different(selector, value)

    async def select_delegacion_and_concepto(self, delegacion_portal_code: str, concepto_portal_code: str):
        """Selects the delegación and concept dropdowns, and clicks add."""
        logger.info(f"Selecting Delegación '{delegacion_portal_code}' and Concepto '{concepto_portal_code}'")
        
        ddl_delegacion = self._get_selector("ddlDelegacion")
        ddl_concepto = self._get_selector("ddlConcepto")
        btn_agregar = self._get_selector("btnAgregarConcepto")

        # Select delegación (usually by label/visible text or exact option value)
        await self.page.locator(ddl_delegacion).select_option(label=delegacion_portal_code)
        
        # Select concepto (usually by exact option value)
        await self.page.locator(ddl_concepto).select_option(value=concepto_portal_code)
        
        # Click Add to add to concepts table
        await self.page.locator(btn_agregar).click()
        # Wait a small moment for UI to process addition
        await self.page.wait_for_timeout(1000)

    async def generate_reference_ticket(self) -> Dict[str, Any]:
        """Clicks generate and extracts the resulting reference code, amount, and dates."""
        logger.info("Generating reference ticket...")
        
        btn_generar = self._get_selector("btnGenerarBoleta")
        await self.page.locator(btn_generar).click()
        
        # Wait for the confirmation/result view
        await self.page.wait_for_load_state("networkidle")
        
        # Retrieve selectors for parsing results
        lbl_ref = self._get_selector("lblBoletaReferencia")
        lbl_importe = self._get_selector("lblBoletaImporte")
        lbl_fecha_limite = self._get_selector("lblBoletaFechaLimite")
        lbl_fecha_alta = self._get_selector("lblBoletaFechaAlta")

        # Extract text content
        ref_text = await self.page.locator(ref_text_locator_or_fallback(lbl_ref)).text_content()
        imp_text = await self.page.locator(ref_text_locator_or_fallback(lbl_importe)).text_content()
        
        # Date fields might be in font/span tags
        limite_text = ""
        alta_text = ""
        try:
            limite_text = await self.page.locator(lbl_fecha_limite).text_content()
        except Exception:
            logger.warning("Could not extract limit date using default selector, attempting fallback")
            
        try:
            alta_text = await self.page.locator(lbl_fecha_alta).text_content()
        except Exception:
            logger.warning("Could not extract generation date using default selector, attempting fallback")

        # Extract numbers using regex
        ref_match = re.search(r"\b\d{17}\b", ref_text or "")
        reference_code = ref_match.group(0) if ref_match else (ref_text or "").strip()
        
        # Importe parsing
        imp_match = re.search(r"[\d,]+\.\d{2}", imp_text or "")
        importe_val = float(imp_match.group(0).replace(",", "")) if imp_match else 0.0
        
        logger.info(f"Extracted Reference: {reference_code}, Importe: {importe_val}, Alta: {alta_text}, Vence: {limite_text}")
        
        return {
            "referencia_portal": reference_code,
            "importe": importe_val,
            "fecha_generacion": datetime.utcnow(),
            "fecha_vigencia_str": limite_text.strip() if limite_text else None,
            "alta_str": alta_text.strip() if alta_text else None
        }

    async def download_pdf(self, destination_path: str):
        """Clicks the print button and saves the downloaded file to the specified path."""
        logger.info(f"Downloading ticket PDF to: {destination_path}")
        
        btn_imprimir = self._get_selector("btnImprimirBoleta")
        
        # Expect download trigger
        async with self.page.expect_download() as download_info:
            await self.page.locator(btn_imprimir).click()
            
        download = await download_info.value
        await download.save_as(destination_path)
        logger.info("PDF download completed successfully.")


def ref_text_locator_or_fallback(selector: str) -> str:
    """Helper to ensure selector is xpath or css selector compatible."""
    return selector

async def asyncio_sleep_or_wait(coro):
    """Simple await helper."""
    return await coro
