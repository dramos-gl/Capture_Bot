# Blueprint de Arquitectura: Ecosistema SAR & Optima Capture Bot
*Guía de Arquitectura, Patrones de Diseño e Integración para Fases A, B y C*

---

## Registro de Documentos del Sistema (SAR)

A continuación se presenta la relación de documentos técnicos oficiales que componen el ecosistema SAR:

| Código | Nombre Formal | Categoría | Archivo de Documento |
| :--- | :--- | :--- | :--- |
| **SAR-BLUEPRINT-001** | Blueprint Empresarial SAR | Arquitectura Empresarial | [1_SAR.md](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/1_SAR.md) |
| **SAR-DAT-001** | Modelo de Datos de Negocio | Análisis de Datos | [2_SAR-DAT-001.md](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/2_SAR-DAT-001.md) |
| **SAR-OPS-001** | Modelo Operativo y Procesos | Operación y Negocio | [3_SAR-OPS-001.md](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/3_SAR-OPS-001.md) |
| **SAR-UIX-001** | Especificación UX/UI | Experiencia de Usuario | [4_SAR-UIX-001.md](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/4_SAR-UIX-001.md) |
| **SAR-TEC-001** | Arquitectura Técnica | Arquitectura de Solución | [6_SAR-TEC-001.md](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/6_SAR-TEC-001.md) |
| **SAR-SEC-001** | Arquitectura de Seguridad y Auditoría | Seguridad | [8_SAR-SEC-001.md](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/8_SAR-SEC-001.md) |
| **SAR-DB-001** | Diseño Físico de Base de Datos | Ingeniería de Datos | [10_SAR-DB-001 v2.0.md](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/10_SAR-DB-001%20v2.0.md) |
| **SAR-DEV-001** | Guía de Desarrollo y Estándares | Ingeniería de Software | [7_SAR-DEV-001.md](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/7_SAR-DEV-001.md) |

---

## 1. Perspectiva del Producto (Product Owner & Business Analyst)

### Objetivo del Ecosistema
Automatizar de manera íntegra, segura y auditable el ciclo de vida de las referencias de pago y facturación del contribuyente. El **Sistema de Administración de Referencias (SAR)** es la base de datos única y el motor de orquestación central que alimenta y conecta:
1.  **FASE A (Generación - Portal Tributanet):** Creación y descarga automatizada de referencias de pago en base a Órdenes y Grupos de Referencias.
2.  **NUEVA FASE B (Conciliación e Ingesta):** Emparejamiento de los PDFs de pago físicos con los registros de la base de datos de SAR para la construcción determinista de lotes.
3.  **FASE C (Facturación - Portal SATQ):** Consulta del estado de pago, timbrado de facturas y descarga de comprobantes en el portal tributario SATQ.

### Requisitos Estratégicos del Negocio
*   **Concurrencia de Workers Seguro:** Múltiples instancias de automatización pueden interactuar a la vez; el sistema debe asegurar que no existan folios o consecutivos duplicados mediante transaccionalidad estricta (`FOR UPDATE`).
*   **Evolución del Bot de Escritorio:** Mantener una interfaz de usuario interactiva (CustomTkinter) que permita al operador alternar entre el modo asistido (para validaciones críticas del login y timbrado) y el modo autónomo de ejecución masiva.
*   **Trazabilidad Forense:** Registrar evidencias físicas en caliente (capturas de pantalla de errores en portales, logs rotativos de ejecución, registros de auditoría forense en base de datos).

---

## 2. Estructura del Código Organizada por Responsabilidades

Para integrar las nuevas capacidades de la **Fase A (SAR)** y el motor de base de datos relacional, la estructura de la carpeta `app/` debe refinarse bajo patrones de arquitectura de software claros:

```text
app/
│
├── gui.py                      # Capa de Presentación (UI CustomTkinter y eventos)
├── orchestrator.py             # Orquestador del Sistema (Coordina UI, Scrapers y DB)
│
├── core/                       # Núcleo del Navegador y Automatización
│   ├── browser_factory.py      # Configuración de Playwright, Evitación de Bots y Headless/Headful
│   └── session_manager.py      # Gestión persistente del almacenamiento de sesión de portales
│
├── pages/                      # Page Object Model (POM) - Interacción con UI de Portales
│   ├── tributanet_page.py      # Selectores y acciones para la Fase A (Generación de Referencias)
│   └── satq_page.py            # Selectores y acciones para la Fase C (Timbrado de Facturas)
│
├── storage/                    # Capa de Persistencia y Datos
│   ├── db_connector.py         # Conector a PostgreSQL (sar_seguridad, sar_produccion)
│   ├── repositories.py         # Repositorios (Guardar Referencias, Checkpoints, Auditoría)
│   └── excel_handler.py        # Generador de entregables (Lotes de 299 referencias en formato Excel)
│
├── services/                   # Servicios Auxiliares de Negocio
│   ├── pdf_extractor.py        # Extractor y validador de PDFs de pago (Nueva Fase B)
│   └── settings.py             # Configuración del bot (Persistencia y Variables de Entorno)
│
└── paths.py                    # Constantes de rutas de archivos del sistema
```

---

## 3. Patrones de Diseño y Alineación de Tecnología

### A. Page Object Model (POM) en Portales
Toda la lógica de interacción con formularios, clicks y búsquedas en portales se separa del orquestador:
*   `TributanetPage` (**Fase A**): Expone métodos como `seleccionar_municipio()`, `capturar_rfc()`, `generar_boleta()`.
*   `SATQPage` (**Fase C**): Expone métodos como `buscar_referencia()`, `llenar_datos_fiscales()`, `timbrar_y_descargar()`.
*   **Beneficio:** Si SATQ o Tributanet actualizan sus elementos visuales, solo se modifica el archivo de la página correspondiente.

### B. Factory Pattern para Playwright (`BrowserFactory`)
Abstrae la inicialización del navegador, permitiendo al operador:
*   Usar un perfil persistente para retener las sesiones del SATQ/Tributanet.
*   Alternar de manera fluida entre ejecución Headless y visible desde la GUI.
*   Configurar de manera uniforme parámetros de evasión de detección de bots.

### C. Repository Pattern conectado a PostgreSQL (`sar_produccion`)
*   Elimina la dependencia exclusiva del Excel como estado actual del proceso. 
*   Toda transacción operativa se registra primero en base de datos.
*   El archivo de Excel se reduce a un *entregable de transporte* para la Fase C legacy.

---

## 4. Ejemplos de Lógica Transaccional de Negocio

### A. Control Transaccional de Consecutivos (RN-017, RN-018)
Implementación en Python para evitar colisiones entre Workers al generar consecutivos únicos por Grupo de Referencias (RFC + Concepto) mediante bloqueos a nivel de fila (`FOR UPDATE`):

```python
import psycopg2
from storage.db_connector import get_db_connection

def obtener_y_actualizar_consecutivo(grupo_id: int) -> int:
    """
    Obtiene el siguiente consecutivo de forma atómica bloqueando el registro del grupo
    para evitar colisiones debido a la concurrencia de múltiples Workers.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Bloqueo exclusivo del grupo
            cursor.execute("""
                SELECT ultimo_consecutivo 
                FROM sar_produccion.grupo_referencia 
                WHERE grupo_id = %s 
                FOR UPDATE;
            """, (grupo_id,))
            
            ultimo_consecutivo = cursor.fetchone()[0]
            nuevo_consecutivo = ultimo_consecutivo + 1
            
            # Actualizar el contador en el grupo
            cursor.execute("""
                UPDATE sar_produccion.grupo_referencia 
                SET ultimo_consecutivo = %s 
                WHERE grupo_id = %s;
            """, (nuevo_consecutivo, grupo_id))
            
            conn.commit()
            return nuevo_consecutivo
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
```

### B. Estructura de un Page Object Model (POM) para SATQ
Código estructurado para interactuar de forma segura con la interfaz de SATQ en la Fase C:

```python
from playwright.sync_api import Page
import logging

class SATQPage:
    def __init__(self, page: Page):
        self.page = page
        self.logger = logging.getLogger("SATQPage")
        
        # Localizadores Semánticos y de Accesibilidad
        self.txt_referencia = page.get_by_role("textbox", name="Referencia")
        self.btn_buscar = page.get_by_role("button", name="Buscar")
        self.btn_timbrar = page.get_by_role("button", name="Timbrar")
        self.lbl_mensaje_alerta = page.locator(".alert-message")

    def buscar_referencia(self, referencia: str):
        self.logger.info(f"Buscando referencia: {referencia}")
        self.txt_referencia.fill(referencia)
        self.btn_buscar.click()
        self.page.wait_for_load_state("networkidle")

    def verificar_estado(self) -> str:
        """Determina si la factura está timbrada o si requiere llenado."""
        if self.page.locator("text=Descargar Factura").is_visible():
            return "YA_TIMBRADA"
        return "PENDIENTE"
```

---

## 5. Directrices del Product Owner para el Equipo de Desarrollo

1.  **Aislamiento de Entornos:** Configurar las credenciales de base de datos y portales exclusivamente mediante el archivo `.env` o a través del panel de configuración de la GUI, nunca hardcodeados.
2.  **Estrategia de Log In Completo:** El `SessionManager` debe persistir el estado de la sesión (`storage_state.json`) en una ruta de usuario local segura (`appdata`) para evitar el bloqueo del portal por accesos repetidos.
3.  **Compatibilidad Hacia Atrás:** Aunque el motor de datos migre a PostgreSQL, los servicios de exportación de `excel_handler.py` deben garantizar la generación exacta del archivo Excel de 299 referencias para que la Fase C heredada continúe operando sin fricción.
4.  **Optimización de Captura Inteligente (Smart Fill):** Para evitar retrasos innecesarios en la automatización, el bot de Playwright deberá leer el atributo `value` actual de los inputs cargados por defecto en el portal (p. ej. Calle, Colonia, Localidad, CP, Razón Social). Si dicho valor ya coincide con los datos del RFC que provienen de la base de datos de SAR, se omitirá la acción de rellenado (`fill`), disminuyendo los tiempos de interacción y la tasa de error por latencia.
