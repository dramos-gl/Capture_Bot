# CANCUNBOT-DEV-001: Guía de Desarrollo y Estándares
**Categoría:** Ingeniería de Software  
**Versión:** 1.0  
**Estado:** Baseline Inicial  
**Metodología:** Business-First Architecture (BFA)  
**Fecha:** 2026

---

## 1. Objetivo

Definir la guía oficial de construcción del proyecto CancunBot, incluyendo:
- Estructura del repositorio.
- Tecnologías congeladas.
- Patrones de diseño.
- Fases de construcción.
- Estándares de código.

---

## 2. Tecnologías Congeladas

| Componente | Tecnología |
| :--- | :--- |
| Lenguaje | Python 3.13 |
| UI Desktop | PySide6 |
| Automatización | Playwright (sync_api) |
| Base de Datos | PostgreSQL 16+ (`db_cancunbot`) |
| ORM | SQLAlchemy 2.x |
| Extracción PDF | `pdfplumber` + `pypdf` |
| Excel Import | `openpyxl` |
| Entorno Virtual | `.venv_sar` (compartido en raíz) |
| Configuración | `.env` + `settings.json` + BD |
| Estándares | PEP8, Type Hints, Docstrings |

---

## 3. Estructura del Repositorio

```text
cancunbot/
│
├── main.py                         # Punto de entrada — GUI PySide6
├── main_bot_a.py                   # Launcher CLI Bot A (sin GUI)
├── main_bot_c.py                   # Launcher CLI Bot C (sin GUI)
├── settings.json                   # Configuración de conexión y rutas
├── .env                            # Credenciales (NO versionado)
├── requirements.txt                # Dependencias del proyecto
│
├── doc_cancunbot/                  # Documentación oficial
│   ├── 0_CANCUNBOT.md
│   ├── 1_CANCUNBOT-BLUEPRINT-001.md
│   ├── 2_CANCUNBOT-DB-001.md
│   └── 3_CANCUNBOT-DEV-001.md
│
└── src/
    │
    ├── core/                       # Núcleo del navegador
    │   ├── __init__.py
    │   ├── browser_factory.py      # Configuración Playwright
    │   └── session_manager.py      # Gestión de sesión de portales
    │
    ├── pages/                      # Page Object Model — sin hardcodeo
    │   ├── __init__.py
    │   ├── base_page.py            # Clase base con resolver de localizadores
    │   ├── recibo_tesoreria_page.py   # POM: recibo.tesoreriacancun.com
    │   └── expide_factura_page.py     # POM: benitojuarez.expidefactura.com
    │
    ├── storage/                    # Capa de persistencia
    │   ├── __init__.py
    │   ├── db_connector.py         # Conector PostgreSQL
    │   ├── repositories.py         # Repositorios de negocio
    │   └── migrations/
    │       ├── 001_initial_schema.sql   # DDL completo
    │       └── 002_seed_data.sql        # Seed: estados, parámetros, localizadores
    │
    ├── services/                   # Servicios de negocio
    │   ├── __init__.py
    │   ├── pdf_extractor.py        # Extracción de campos del PDF de recibo
    │   ├── file_manager.py         # Renombrado y organización de PDFs
    │   ├── excel_importer.py       # Importación de folios desde Excel
    │   └── settings.py             # Lectura de settings.json y .env
    │
    ├── ui/                         # GUI PySide6 — Atomic Design
    │   ├── __init__.py
    │   ├── assets/                 # Íconos e imágenes
    │   ├── design_system/
    │   │   ├── atoms/              # Botones, labels, inputs
    │   │   ├── molecules/          # Dialogs, cards, tablas
    │   │   └── organisms/          # Barras de herramientas, paneles
    │   └── views/
    │       ├── main_view.py        # Vista principal / shell
    │       ├── solicitudes_view.py # Vista de gestión de solicitudes
    │       ├── bot_a_view.py       # Vista del Bot A (descarga)
    │       ├── bot_c_view.py       # Vista del Bot C (facturación)
    │       └── configuracion_view.py  # Vista de configuración y localizadores
    │
    └── paths.py                    # Constantes de rutas del proyecto
```

---

## 4. Patrones de Diseño

### A. Page Object Model (POM) — Anti-hardcodeo

**Principio:** Ningún selector CSS, XPath o texto de portal está escrito en el código Python.  
**Implementación:** Los localizadores se cargan desde `cancunbot_configuracion.localizador_portal` al inicializar cada Page Object.

```python
# src/pages/base_page.py
from playwright.sync_api import Page
import logging

class BasePage:
    """Clase base para todos los Page Objects de CancunBot."""

    def __init__(self, page: Page, localizadores: dict):
        self.page = page
        self.logger = logging.getLogger(self.__class__.__name__)
        self._locs = localizadores

    def _resolver(self, nombre_clave: str):
        """
        Resuelve un localizador por nombre_clave consultando el
        diccionario cargado desde la BD. Nunca falla silenciosamente.
        """
        loc = self._locs.get(nombre_clave)
        if not loc:
            raise KeyError(f"Localizador '{nombre_clave}' no encontrado en BD.")

        estrategia = loc["estrategia_selector"]
        valor = loc["valor_selector"]

        match estrategia:
            case "CSS":
                return self.page.locator(valor)
            case "ID":
                return self.page.locator(f"#{valor}")
            case "TEXT":
                return self.page.get_by_text(valor)
            case "ROLE":
                role, name = valor.split("|", 1)
                return self.page.get_by_role(role, name=name)
            case "XPATH":
                return self.page.locator(f"xpath={valor}")
            case _:
                raise ValueError(f"Estrategia desconocida: {estrategia}")
```

```python
# src/pages/recibo_tesoreria_page.py
from playwright.sync_api import Page
from .base_page import BasePage

class ReciboTesoreriaPage(BasePage):
    """POM para el portal recibo.tesoreriacancun.com"""

    def __init__(self, page: Page, localizadores: dict):
        super().__init__(page, localizadores)
        # Los localizadores se resuelven en tiempo de ejecución, no aquí
        # para evitar fallos si el portal no está cargado

    def consultar_folio(self, folio: str) -> bool:
        """Ingresa el folio y hace clic en Consultar."""
        self.logger.info(f"Consultando folio: {folio}")
        inp = self._resolver("RECIBO_INPUT_FOLIO")
        inp.clear()
        inp.fill(folio)
        self._resolver("RECIBO_BTN_CONSULTAR").click()
        self.page.wait_for_load_state("networkidle")
        # Verificar si hay resultado
        if self._resolver("RECIBO_MSG_NO_ENCONTRADO").is_visible():
            self.logger.warning(f"Folio {folio} no encontrado en portal.")
            return False
        return True

    def descargar_recibo(self) -> str:
        """Descarga el PDF y retorna la ruta del archivo descargado."""
        with self.page.expect_download() as dl_info:
            self._resolver("RECIBO_BTN_DESCARGAR").click()
        download = dl_info.value
        ruta = download.path()
        self.logger.info(f"Recibo descargado en: {ruta}")
        return ruta
```

### B. Repository Pattern

Toda interacción con la base de datos pasa por repositorios especializados:

```python
# src/storage/repositories.py (estructura)
class SolicitudRepository:
    def crear(self, datos: dict) -> int: ...
    def obtener_por_id(self, solicitud_id: int) -> dict: ...
    def listar_activas(self) -> list[dict]: ...
    def actualizar_contadores(self, solicitud_id: int): ...

class FolioRepository:
    def crear_lote(self, solicitud_id: int, folios: list[str]): ...
    def obtener_pendientes(self) -> list[dict]: ...
    def actualizar_estado(self, folio_id: int, estado: str): ...
    def registrar_error(self, folio_id: int, error: str): ...

class ReciboRepository:
    def crear(self, datos: dict) -> int: ...
    def obtener_pendientes_facturar(self) -> list[dict]: ...
    def actualizar_estado(self, recibo_id: int, estado: str): ...

class LocalizadorRepository:
    def cargar_por_portal(self, portal: str) -> dict: ...
    # Retorna dict: {nombre_clave: {estrategia_selector, valor_selector}}
```

### C. Factory de Playwright

```python
# src/core/browser_factory.py
from playwright.sync_api import sync_playwright, Browser, Page
from .session_manager import SessionManager

class BrowserFactory:
    """Gestiona la creación y configuración de instancias de Playwright."""

    @staticmethod
    def crear_browser(headless: bool = False) -> Browser:
        pw = sync_playwright().start()
        return pw.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"]
        )

    @staticmethod
    def crear_contexto(browser: Browser, portal: str):
        storage_state = SessionManager.cargar_estado(portal)
        return browser.new_context(
            storage_state=storage_state,
            viewport={"width": 1280, "height": 900},
            locale="es-MX"
        )
```

---

## 5. Configuración (`settings.json`)

```json
{
    "DB_HOST": "127.0.0.1",
    "DB_PORT": "5432",
    "DB_NAME": "db_cancunbot",
    "DB_USER": "postgres",
    "DB_PASSWORD": "",
    "LOG_LEVEL": "INFO",
    "PDF_DOWNLOAD_TEMP": "temp/downloads/",
    "SESSION_STATE_DIR": "temp/sessions/"
}
```

> **Nota:** Las credenciales sensibles se gestionan mediante variables en `.env`. El `settings.json` apunta a configuraciones no sensibles.

---

## 6. Servicio de Extracción de PDF

```python
# src/services/pdf_extractor.py (contrato esperado)
import pdfplumber
import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class DatosRecibo:
    folio_pase_caja: Optional[str]
    folio_electronico: Optional[str]
    fecha_expedicion: Optional[str]
    hora_expedicion: Optional[str]
    lugar_expedicion: Optional[str]
    rfc: Optional[str]
    contribucion: Optional[str]
    nombre_contribuyente: Optional[str]
    concepto: Optional[str]
    total: Optional[float]
    forma_pago: Optional[str]
    datos_adicionales: dict  # Captura campos extras

class PdfExtractor:
    """Extrae datos estructurados de un PDF de recibo electrónico."""

    def extraer(self, ruta_pdf: str) -> DatosRecibo:
        """
        Lee el PDF y extrae los campos del recibo usando expresiones
        regulares y patrones definidos. Retorna DatosRecibo.
        Los campos no encontrados quedan como None.
        """
        ...
```

---

## 7. Servicio de Importación Excel

```python
# src/services/excel_importer.py (contrato esperado)
class ExcelImporter:
    """
    Importa folios desde una hoja de cálculo Excel.
    Espera una columna con encabezado 'FOLIO' (folio electrónico)
    y opcionalmente 'FOLIO_PASE_CAJA'.
    """
    COLUMNA_FOLIO_ELECTRONICO = "FOLIO"
    COLUMNA_FOLIO_PASE_CAJA = "FOLIO_PASE_CAJA"

    def importar(self, ruta_excel: str) -> list[dict]:
        """Retorna lista de dicts con claves: folio_electronico, folio_pase_caja."""
        ...
```

---

## 8. Fases de Construcción

### FASE DEV-01: Fundación y Documentación ✅
- Blueprint empresarial.
- Diseño de BD.
- Guía de desarrollo.
- Estructura de carpetas.

### FASE DEV-02: Base de Datos
**Entregables:**
- `001_initial_schema.sql`: DDL de todos los esquemas y tablas.
- `002_seed_data.sql`: Estados, parámetros y localizadores iniciales.

**Criterio de aceptación:** Ejecutar los scripts sin error en PostgreSQL.

### FASE DEV-03: Gestión de Solicitudes
**Entregables:**
- `SolicitudRepository`, `FolioRepository`.
- `ExcelImporter`.
- Vista UI: Importar Excel y captura manual de folios.

**Criterio de aceptación:** Crear solicitud con N folios desde Excel y desde captura manual.

### FASE DEV-04: Bot A — Descarga de Recibos
**Entregables:**
- `BrowserFactory`, `SessionManager`.
- `ReciboTesoreriaPage` (POM).
- `PdfExtractor`.
- `FileManager`.

**Criterio de aceptación:** Dado un folio en estado PENDIENTE, el bot descarga el PDF, extrae los datos y los guarda en BD.

### FASE DEV-05: Repositorio de Recibos
**Entregables:**
- `ReciboRepository`.
- Lógica de actualización de estados.

**Criterio de aceptación:** Registro completo en BD con todos los campos del recibo.

### FASE DEV-06: Bot C — Facturación
**Entregables:**
- `ExpideFacturaPage` (POM).
- Lógica de facturación + `FacturaRepository`.

**Criterio de aceptación:** Factura generada y descargada para un recibo en estado PENDIENTE_FACTURAR.

### FASE DEV-07: UI Completa
**Entregables:**
- Vista de solicitudes con progreso en tiempo real.
- Vista Bot A con logs de ejecución.
- Vista Bot C con logs de ejecución.
- Vista de configuración de localizadores.

**Criterio de aceptación:** Operación end-to-end desde GUI.

### FASE DEV-08: Auditoría
**Entregables:**
- Registro automático de eventos y errores en `cancunbot_auditoria`.

**Criterio de aceptación:** Trazabilidad completa de cada folio desde creación hasta facturación.

---

## 9. Estándares de Código

- **PEP8** obligatorio.
- **Type Hints** en todas las funciones y métodos.
- **Docstrings** en todas las clases y métodos públicos.
- **Logging** mediante `logging.getLogger(__name__)` — nunca `print()`.
- **Manejo de errores:** Try/except con logging de stack trace completo en auditoría.
- **Sin hardcodeo** de selectores, URLs ni rutas absolutas.

---

## 10. Gestión de Configuración

| Variable | Fuente | Descripción |
| :--- | :--- | :--- |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` | `settings.json` | Conexión a PostgreSQL |
| `DB_PASSWORD` | `.env` | Contraseña (nunca en código) |
| `PDF_BASE_PATH` | BD `parametro_sistema` | Ruta base del repositorio PDF |
| `PORTAL_RECIBO_URL` | BD `parametro_sistema` | URL del portal de recibos |
| `PORTAL_FACTURA_URL` | BD `parametro_sistema` | URL del portal de facturación |
| Selectores | BD `localizador_portal` | Todos los selectores de portales |

---

## 11. Riesgos Técnicos y Mitigaciones

| Riesgo | Mitigación |
| :--- | :--- |
| Cambios en el portal de Tesorería | Selectores en BD — solo se actualiza la tabla, no el código |
| Cambios en el portal de Facturación | Mismo patrón anti-hardcodeo |
| PDF con formato inesperado | Campo `datos_adicionales JSONB` + logging de advertencia |
| Folio no encontrado | Estado `ERROR_DESCARGA` + retry configurable |
| Fallo de facturación | Estado `ERROR_FACTURA` + retry manual desde UI |
| Pérdida de sesión del portal | `SessionManager` con re-login automático |
