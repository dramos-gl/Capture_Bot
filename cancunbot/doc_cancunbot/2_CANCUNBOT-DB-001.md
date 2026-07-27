# CANCUNBOT-DB-001: Diseño Físico de Base de Datos
**Categoría:** Ingeniería de Datos  
**Versión:** 1.0  
**Estado:** Baseline Congelada  
**Motor:** PostgreSQL 16+  
**Base de Datos:** `db_cancunbot`  
**Metodología:** Business-First Architecture (BFA)  
**Fecha:** 2026

---

## 1. Objetivo

Definir la estructura física definitiva de la base de datos `db_cancunbot`, incluyendo:
- Configuración y parámetros de sistema
- Catálogos de negocio
- Producción (solicitudes, folios, recibos)
- Gestión documental (facturas)
- Auditoría y trazabilidad

---

## 2. Principios de Diseño

**DBD-001** — La entidad principal del sistema es: `RECIBO`

**DBD-002** — Los archivos PDF se almacenan fuera de la base de datos. La BD conserva: ruta, hash SHA256, nombre.

**DBD-003** — Toda operación crítica debe ser auditable.

**DBD-004** — Ningún selector de portal debe estar hardcodeado. Viven en `cancunbot_configuracion.localizador_portal`.

**DBD-005** — El correo del contribuyente vive en `cancunbot_catalogo.contribuyente`.

---

## 3. Esquemas

```text
cancunbot_configuracion   → Parámetros, localizadores de portales
cancunbot_catalogo        → Estados, contribuyentes
cancunbot_produccion      → Solicitudes, folios, recibos
cancunbot_archivo         → Facturas generadas
cancunbot_auditoria       → Bitácora de eventos y errores
```

---

## 4. Configuración

### Tabla: `cancunbot_configuracion.parametro_sistema`

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `parametro_id` | BIGSERIAL PK | |
| `codigo` | VARCHAR(100) UNIQUE | Clave del parámetro |
| `valor` | TEXT | Valor actual |
| `descripcion` | TEXT | Descripción del parámetro |
| `activo` | BOOLEAN DEFAULT TRUE | |

**Parámetros iniciales (seed):**

| Código | Valor | Descripción |
| :--- | :--- | :--- |
| `PORTAL_RECIBO_URL` | `https://recibo.tesoreriacancun.com` | URL del portal de recibos |
| `PORTAL_FACTURA_URL` | `https://benitojuarez.expidefactura.com/` | URL del portal de facturación |
| `PDF_BASE_PATH` | *(a definir)* | Ruta base del repositorio de PDFs |
| `PDF_NAMING_PATTERN` | `{folio_electronico}` | Patrón de renombrado de PDFs |
| `SOLICITUD_FOLIO_PREFIX` | `SOL` | Prefijo para folio de solicitud |

---

### Tabla: `cancunbot_configuracion.localizador_portal`
**Clave de la estrategia anti-hardcodeo.** Almacena todos los selectores de los portales.

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `localizador_id` | BIGSERIAL PK | |
| `portal` | VARCHAR(30) NOT NULL | `RECIBO` / `FACTURA` |
| `nombre_clave` | VARCHAR(100) UNIQUE | Identificador del localizador |
| `label_visible` | VARCHAR(200) | Descripción legible para humanos |
| `estrategia_selector` | VARCHAR(50) | `CSS` / `ROLE` / `TEXT` / `XPATH` / `ID` |
| `valor_selector` | VARCHAR(500) | El selector real |
| `descripcion` | VARCHAR(500) | Notas adicionales |
| `activo` | BOOLEAN DEFAULT TRUE | |

**Seed de localizadores — Portal RECIBO:**

| nombre_clave | label_visible | estrategia_selector | valor_selector |
| :--- | :--- | :--- | :--- |
| `RECIBO_INPUT_FOLIO` | Input de folio | *(a inspeccionar)* | *(a inspeccionar)* |
| `RECIBO_BTN_CONSULTAR` | Botón Consultar | *(a inspeccionar)* | *(a inspeccionar)* |
| `RECIBO_BTN_DESCARGAR` | Botón Descargar PDF | *(a inspeccionar)* | *(a inspeccionar)* |
| `RECIBO_MSG_NO_ENCONTRADO` | Mensaje "No encontrado" | *(a inspeccionar)* | *(a inspeccionar)* |

**Seed de localizadores — Portal FACTURA:**

| nombre_clave | label_visible | estrategia_selector | valor_selector |
| :--- | :--- | :--- | :--- |
| `FACTURA_INPUT_RFC` | Input RFC | *(a inspeccionar)* | *(a inspeccionar)* |
| `FACTURA_INPUT_CORREO` | Input Correo | *(a inspeccionar)* | *(a inspeccionar)* |
| `FACTURA_INPUT_FOLIO` | Input Folio Electrónico | *(a inspeccionar)* | *(a inspeccionar)* |
| `FACTURA_INPUT_IMPORTE` | Input Importe | *(a inspeccionar)* | *(a inspeccionar)* |
| `FACTURA_BTN_GENERAR` | Botón Generar Factura | *(a inspeccionar)* | *(a inspeccionar)* |
| `FACTURA_BTN_DESCARGAR_PDF` | Botón Descargar PDF | *(a inspeccionar)* | *(a inspeccionar)* |
| `FACTURA_BTN_DESCARGAR_XML` | Botón Descargar XML | *(a inspeccionar)* | *(a inspeccionar)* |

> **Nota:** Los valores de selector se completan durante la fase DEV-02 mediante inspección del portal.

---

## 5. Catálogos

### Tabla: `cancunbot_catalogo.estado_sistema`
Catálogo de estados por entidad.

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `estado_id` | BIGSERIAL PK | |
| `entidad` | VARCHAR(100) NOT NULL | `SOLICITUD` / `FOLIO` / `RECIBO` |
| `codigo` | VARCHAR(50) NOT NULL | Código del estado |
| `descripcion` | VARCHAR(200) | |

Restricción: `UNIQUE(entidad, codigo)`

**Seed de estados:**

| Entidad | Código | Descripción |
| :--- | :--- | :--- |
| `SOLICITUD` | `NUEVA` | Solicitud recién creada |
| `SOLICITUD` | `EN_PROCESO` | Bot procesando folios |
| `SOLICITUD` | `COMPLETADA` | Todos los folios procesados |
| `SOLICITUD` | `CON_ERRORES` | Completada con errores parciales |
| `FOLIO` | `PENDIENTE` | Folio en espera de descarga |
| `FOLIO` | `DESCARGANDO` | Bot descargando recibo |
| `FOLIO` | `DESCARGADO` | Recibo descargado correctamente |
| `FOLIO` | `ERROR_DESCARGA` | Error al descargar el recibo |
| `RECIBO` | `CAPTURADO` | Datos extraídos y guardados |
| `RECIBO` | `PENDIENTE_FACTURAR` | Listo para facturación |
| `RECIBO` | `FACTURANDO` | Bot generando factura |
| `RECIBO` | `FACTURADO` | Factura generada exitosamente |
| `RECIBO` | `ERROR_FACTURA` | Error en proceso de facturación |

---

### Tabla: `cancunbot_catalogo.contribuyente`
Catálogo de contribuyentes. Fuente del correo para facturación.

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `contribuyente_id` | BIGSERIAL PK | |
| `rfc` | VARCHAR(13) UNIQUE NOT NULL | RFC fiscal |
| `razon_social` | VARCHAR(500) NOT NULL | Nombre o razón social |
| `correo_electronico` | VARCHAR(200) | Correo por defecto para facturas |
| `activo` | BOOLEAN DEFAULT TRUE | |
| `created_at` | TIMESTAMPTZ DEFAULT NOW() | |
| `updated_at` | TIMESTAMPTZ | |

---

## 6. Producción

### Tabla: `cancunbot_produccion.solicitud`
Agrupa un conjunto de folios a procesar. Análogo a `sar_produccion.solicitud`.

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `solicitud_id` | BIGSERIAL PK | |
| `folio_solicitud` | VARCHAR(50) UNIQUE NOT NULL | Ej: SOL-2026-001 |
| `origen` | VARCHAR(20) NOT NULL | `EXCEL` / `MANUAL` |
| `descripcion` | TEXT | Nota del lote |
| `total_folios` | INTEGER NOT NULL DEFAULT 0 | Total de folios en la solicitud |
| `folios_procesados` | INTEGER NOT NULL DEFAULT 0 | Con recibo descargado |
| `folios_facturados` | INTEGER NOT NULL DEFAULT 0 | Con factura generada |
| `folios_error` | INTEGER NOT NULL DEFAULT 0 | Con error |
| `archivo_excel` | VARCHAR(500) | Ruta del Excel importado |
| `estado_id` | BIGINT FK | Estado actual |
| `usuario_id` | BIGINT | Operador que creó la solicitud |
| `created_at` | TIMESTAMPTZ DEFAULT NOW() | |
| `updated_at` | TIMESTAMPTZ | |

FK: `estado_id` → `cancunbot_catalogo.estado_sistema(estado_id)`

---

### Tabla: `cancunbot_produccion.folio`
Cada folio individual. Es la unidad de trabajo de los Bots.

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `folio_id` | BIGSERIAL PK | |
| `solicitud_id` | BIGINT FK NOT NULL | Solicitud padre |
| `folio_electronico` | VARCHAR(50) | Ej: F-2026-615-31044 |
| `folio_pase_caja` | VARCHAR(50) | Alternativo al electrónico |
| `tipo_folio` | VARCHAR(20) NOT NULL | `ELECTRONICO` / `PASE_CAJA` |
| `intentos` | INTEGER NOT NULL DEFAULT 0 | Reintentos de descarga |
| `ultimo_error` | TEXT | Último error registrado |
| `estado_id` | BIGINT FK NOT NULL | Estado actual |
| `created_at` | TIMESTAMPTZ DEFAULT NOW() | |
| `updated_at` | TIMESTAMPTZ | |

Restricción: `CHECK (folio_electronico IS NOT NULL OR folio_pase_caja IS NOT NULL)`  
FK: `solicitud_id` → `cancunbot_produccion.solicitud(solicitud_id)`  
FK: `estado_id` → `cancunbot_catalogo.estado_sistema(estado_id)`

---

### Tabla: `cancunbot_produccion.recibo`
Datos extraídos del PDF. Relación 1-a-1 con `folio`.

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `recibo_id` | BIGSERIAL PK | |
| `folio_id` | BIGINT FK UNIQUE NOT NULL | Folio origen |
| `folio_pase_caja` | VARCHAR(50) | Extraído del PDF |
| `folio_electronico` | VARCHAR(50) UNIQUE | Extraído del PDF |
| `fecha_expedicion` | DATE | Extraído del PDF |
| `hora_expedicion` | TIME | Extraído del PDF |
| `lugar_expedicion` | VARCHAR(200) | Extraído del PDF |
| `rfc` | VARCHAR(13) | Extraído del PDF |
| `contribucion` | VARCHAR(300) | Extraído del PDF |
| `nombre_contribuyente` | VARCHAR(500) | Ej: CADU INMOBILIARIA |
| `concepto` | TEXT | Detalle concepto de cobro |
| `total` | NUMERIC(14,2) | Importe total |
| `forma_pago` | VARCHAR(100) | Opcional |
| `datos_adicionales` | JSONB | Campos extras encontrados en el PDF |
| `pdf_nombre` | VARCHAR(500) | Nombre final del PDF |
| `pdf_ruta` | VARCHAR(1000) | Ruta completa del PDF organizado |
| `hash_sha256` | VARCHAR(64) | Integridad del archivo |
| `estado_id` | BIGINT FK NOT NULL | Estado actual |
| `created_at` | TIMESTAMPTZ DEFAULT NOW() | |
| `updated_at` | TIMESTAMPTZ | |

FK: `folio_id` → `cancunbot_produccion.folio(folio_id)`  
FK: `estado_id` → `cancunbot_catalogo.estado_sistema(estado_id)`

> **Nota:** El campo `datos_adicionales (JSONB)` permite capturar cualquier campo adicional que aparezca en el PDF sin modificar el esquema.

---

## 7. Gestión Documental

### Tabla: `cancunbot_archivo.factura`
Factura generada a partir de un recibo.

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `factura_id` | BIGSERIAL PK | |
| `recibo_id` | BIGINT FK UNIQUE NOT NULL | Recibo origen |
| `uuid` | VARCHAR(36) UNIQUE | UUID fiscal del CFDI |
| `folio_fiscal` | VARCHAR(100) | Folio fiscal asignado |
| `rfc_emisor` | VARCHAR(13) | RFC del emisor |
| `fecha_factura` | TIMESTAMPTZ | Fecha de timbrado |
| `pdf_path` | VARCHAR(1000) | Ruta del PDF de factura |
| `xml_path` | VARCHAR(1000) | Ruta del XML de factura |
| `estado` | VARCHAR(30) NOT NULL | Estado de la factura |
| `datos_adicionales` | JSONB | Datos extra capturados del portal |
| `created_at` | TIMESTAMPTZ DEFAULT NOW() | |

FK: `recibo_id` → `cancunbot_produccion.recibo(recibo_id)`

---

## 8. Auditoría

### Tabla: `cancunbot_auditoria.auditoria_evento`

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `evento_id` | BIGSERIAL PK | |
| `modulo` | VARCHAR(100) NOT NULL | `BOT_A` / `BOT_C` / `UI` |
| `accion` | VARCHAR(100) NOT NULL | Descripción de la acción |
| `entidad` | VARCHAR(50) | `folio` / `recibo` / `factura` |
| `entidad_id` | BIGINT | ID de la entidad afectada |
| `detalle` | JSONB | Datos adicionales del evento |
| `fecha` | TIMESTAMPTZ DEFAULT NOW() | |

### Tabla: `cancunbot_auditoria.auditoria_error`

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `error_id` | BIGSERIAL PK | |
| `modulo` | VARCHAR(100) NOT NULL | Módulo donde ocurrió |
| `entidad` | VARCHAR(50) | Entidad afectada |
| `entidad_id` | BIGINT | ID de la entidad afectada |
| `mensaje` | TEXT NOT NULL | Mensaje de error |
| `stack_trace` | TEXT | Traza completa del error |
| `fecha` | TIMESTAMPTZ DEFAULT NOW() | |

---

## 9. Índices de Rendimiento

```sql
-- Producción
CREATE INDEX idx_folio_solicitud_id ON cancunbot_produccion.folio (solicitud_id);
CREATE INDEX idx_folio_estado_id ON cancunbot_produccion.folio (estado_id);
CREATE INDEX idx_recibo_folio_id ON cancunbot_produccion.recibo (folio_id);
CREATE INDEX idx_recibo_estado_id ON cancunbot_produccion.recibo (estado_id);
CREATE INDEX idx_recibo_rfc ON cancunbot_produccion.recibo (rfc);

-- Archivo
CREATE INDEX idx_factura_recibo_id ON cancunbot_archivo.factura (recibo_id);

-- Auditoría
CREATE INDEX idx_audit_evento_fecha ON cancunbot_auditoria.auditoria_evento (fecha DESC);
CREATE INDEX idx_audit_error_fecha ON cancunbot_auditoria.auditoria_error (fecha DESC);
```

---

## 10. Decisiones Congeladas

- **DBD-001** PostgreSQL oficial para `db_cancunbot`.
- **DBD-002** El recibo es la entidad principal.
- **DBD-003** PDFs fuera de la base de datos; sólo se almacena ruta y hash.
- **DBD-004** Selectores de portal en tabla `localizador_portal`, nunca en código.
- **DBD-005** Correo del contribuyente en catálogo `contribuyente` por RFC.
- **DBD-006** Campo `datos_adicionales JSONB` en recibo y factura para extensibilidad.
- **DBD-007** SHA256 obligatorio para PDFs descargados.
- **DBD-008** Auditoría obligatoria de eventos y errores.

---

## Estado

```
CANCUNBOT-DB-001 v1.0
BASELINE CONGELADA
APROBADA PARA DESARROLLO
```
