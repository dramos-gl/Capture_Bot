"""Integration test for BrowserFactory and TributanetPage POM."""

import os
import asyncio
import logging
import sys
from datetime import datetime

from playwright.async_api import async_playwright, Route, Request

# Ensure sar is in the import path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sar.src.core.browser_factory import BrowserFactory
from sar.src.pages.tributanet_page import TributanetPage
from sar.src.storage.db_connector import DatabaseConnector
from sar.src.storage.repositories import ConfigRepository

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Mock HTML Pages ---
HTML_LOGIN = """
<html>
<body>
  <h2>Acceso Tributanet RPP</h2>
  <form id="loginForm" method="POST" action="https://shacienda.qroo.gob.mx/tributanet/rpp/dec_rpp_control.php?step=2">
    <select name="claveMunicipio">
      <option value="01">OTHON P. BLANCO</option>
      <option value="02">BENITO JUAREZ</option>
    </select>
    <input name="RFC" type="text" />
    <input type="submit" value="Enviar" />
  </form>
</body>
</html>
"""

HTML_FORM = """
<html>
<body>
  <h2>Formulario Principal RPP</h2>
  <form id="mainForm" method="POST" action="https://shacienda.qroo.gob.mx/tributanet/rpp/dec_rpp_control.php?step=3">
    <input id="Nombre" value="" />
    <input id="RFC" value="TEST900101AA1" readonly />
    <input id="Calle" value="" />
    <input id="Colonia" value="" />
    <input id="Numero_Exterior" value="" />
    <input id="Numero_Interior" value="" />
    <input id="Codigo_Postal" value="" />
    <input id="Localidad" value="" />
    <select name="Delegacion">
      <option value="CANCUN">Delegación Cancun (Benito Juarez, Isla Mujeres y Lazaro cardenas)</option>
    </select>
    <select id="conceptos">
      <option value="132-1 Análisis y calificación de documentos que contengan actos inscribibles-CT-65.00-117.31-">1. Análisis y calificación</option>
    </select>
    <input id="agregar" type="button" value="Agregar" onclick="document.getElementById('status').innerText='Concept Added';" />
    <span id="status"></span>
    <input id="generar" type="submit" value="Generar" />
  </form>
</body>
</html>
"""

HTML_TICKET = """
<html>
<body>
  <h2>Boleta de Pago Generada</h2>
  <div>
    <b>REFERENCIA: 12345678901234567</b>
    <a class="datomostrar">17/06/2026 15:55:00</a>
    <b>IMPORTE: $1,250.00</b>
    <font>FECHA LIMITE: 30/06/2026</font>
  </div>
  <form method="POST" action="https://shacienda.qroo.gob.mx/tributanet/rpp/download.pdf">
    <input name="Imprimir" type="submit" value="Imprimir" />
  </form>
</body>
</html>
"""

MOCK_PDF_CONTENT = b"%PDF-1.4 mock pdf content for Tributanet ticket"


async def handle_route(route: Route, request: Request):
    """Intercepts network requests and returns mock HTML responses to avoid hitting live servers."""
    url = request.url
    logger.info(f"Intercepting request: {url}")
    
    if "step=2" in url:
        await route.fulfill(status=200, content_type="text/html; charset=utf-8", body=HTML_FORM)
    elif "step=3" in url:
        await route.fulfill(status=200, content_type="text/html; charset=utf-8", body=HTML_TICKET)
    elif "download.pdf" in url:
        await route.fulfill(
            status=200,
            content_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=boleta.pdf"},
            body=MOCK_PDF_CONTENT
        )
    else:
        # Default starting login page
        await route.fulfill(status=200, content_type="text/html; charset=utf-8", body=HTML_LOGIN)


async def run_test():
    # Attempt to load locators and configs from database
    db = DatabaseConnector()
    locators = {}
    rpp_url = "https://shacienda.qroo.gob.mx/tributanet/rpp/dec_rpp_control.php?tipo_declaracion=1"
    
    try:
        with db.get_session() as session:
            repo = ConfigRepository(session)
            db_locators = repo.get_localizadores()
            for k, loc in db_locators.items():
                locators[k] = loc.valor_selector
            
            db_url = repo.get_parametro("TRIBUTANET_RPP_URL")
            if db_url:
                rpp_url = db_url
            logger.info(f"Loaded {len(locators)} locators from database.")
    except Exception as e:
        logger.warning(f"Could not load locators from DB, using fallback defaults. Error: {e}")
        # Fallback dictionary of locators if DB isn't running or configured
        locators = {
            'ddlMunicipio': 'select[name="claveMunicipio"]',
            'txtRFC': 'input[name="RFC"]',
            'btnEnviar': 'input[type="submit"]',
            'txtNombre': 'input#Nombre',
            'txtRfcReadOnly': 'input#RFC',
            'txtCalle': 'input#Calle',
            'txtColonia': 'input#Colonia',
            'txtNumeroExterior': 'input#Numero_Exterior',
            'txtNumeroInterior': 'input#Numero_Interior',
            'txtCodigoPostal': 'input#Codigo_Postal',
            'txtLocalidad': 'input#Localidad',
            'ddlDelegacion': 'select[name="Delegacion"]',
            'ddlConcepto': 'select#conceptos',
            'btnAgregarConcepto': 'input#agregar',
            'btnGenerarBoleta': 'input#generar',
            'lblBoletaReferencia': '//b[contains(text(), "REFERENCIA")]',
            'lblBoletaFechaAlta': 'a.datomostrar',
            'lblBoletaImporte': '//b[contains(text(), "IMPORTE")]',
            'lblBoletaFechaLimite': '//font[contains(text(), "FECHA LIMITE")]',
            'btnImprimirBoleta': 'input[name="Imprimir"]'
        }

    # Playwright setup
    async with async_playwright() as playwright:
        # Launch browser in headless mode
        browser = await BrowserFactory.launch_browser(playwright, headless=True)
        context = await BrowserFactory.create_context(browser)
        page = await context.new_page()

        # Enable route hijacking to keep tests entirely local
        await page.route("**/tributanet/**", handle_route)

        # POM initialization
        tributanet = TributanetPage(page, locators)

        # 1. Navigate
        await tributanet.navigate_to_rpp(rpp_url)

        # 2. Login
        await tributanet.login_rpp(municipio_code="02", rfc="TEST900101AA1")

        # 3. Fill Contributor Details
        rfc_details = {
            "rfc": "TEST900101AA1",
            "razon_social": "JUAN PEREZ GONZALEZ",
            "calle": "AV. TULUM KM 5",
            "colonia": "CENTRO",
            "no_exterior": "123",
            "no_interior": "A",
            "codigo_postal": "77500",
            "localidad": "CANCUN"
        }
        await tributanet.fill_rfc_details(rfc_details)

        # 4. Select dropdown values and add concept
        await tributanet.select_delegacion_and_concepto(
            delegacion_portal_code="Delegación Cancun (Benito Juarez, Isla Mujeres y Lazaro cardenas)",
            concepto_portal_code="132-1 Análisis y calificación de documentos que contengan actos inscribibles-CT-65.00-117.31-"
        )

        # 5. Generate Reference ticket
        ticket_data = await tributanet.generate_reference_ticket()
        print("\n=== GENERATED TICKET DETAILS ===")
        for key, val in ticket_data.items():
            print(f"{key}: {val}")
        print("================================\n")

        # Assert reference values parsed correctly
        assert ticket_data["referencia_portal"] == "12345678901234567"
        assert ticket_data["importe"] == 1250.0

        # 6. Download PDF
        scratch_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "scratch"))
        os.makedirs(scratch_dir, exist_ok=True)
        pdf_path = os.path.join(scratch_dir, "test_boleta.pdf")
        
        await tributanet.download_pdf(pdf_path)
        
        # Verification of downloaded file
        assert os.path.exists(pdf_path), "PDF file was not downloaded!"
        assert os.path.getsize(pdf_path) > 0, "PDF file is empty!"
        print(f"Integration Test Success! PDF downloaded to: {pdf_path}")

        # Clean up files
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(run_test())
