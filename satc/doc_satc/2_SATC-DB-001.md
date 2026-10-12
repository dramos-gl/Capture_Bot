# SATC-DB-001: Diseño Físico de Base de Datos
**Categoría:** Ingeniería de Datos  
**Versión:** 1.0  
**Estado:** Baseline Congelada  
**Motor:** PostgreSQL 16+  
**Base de Datos:** `db_satc`  
**Metodología:** Business-First Architecture (BFA)  
**Fecha:** 2026

---

## 1. Objetivo

Definir la estructura física definitiva de la base de datos `db_satc`, incluyendo:
- Configuración y parámetros de sistema
- Catálogos de negocio
- Producción (solicitudes, folios, recibos)
- Gestión documental (facturas)
- Auditoría y trazabilidad

---

## 2. Principios de Diseño

**DBD-001** — La entidad soberana del sistema es: `VIVIENDA` / `UNIDAD PRIVATIVA (UPE)`. Los recibos y facturas son documentos probatorios del ciclo de vida de dicha unidad.

**DBD-002** — Todo desarrollo bajo Régimen de Condominio debe declarar su macro-lote (MZ, LT) y su número de Unidades de Propiedad Exclusiva (`total_upes`), vinculando sus viviendas hijas mediante `regimen_id`.

**DBD-003** — Los archivos PDF y XML se almacenan en sistema de archivos estructurado jerárquicamente (`Desarrollo/Manzana/Lote_o_UPE/`). La BD conserva: ruta, hash SHA256, nombre y fecha.

**DBD-004** — Toda operación crítica debe ser auditable en `satc_auditoria.bitacora_evento`.

**DBD-005** — Ningún selector de portal debe estar hardcodeado. Viven en `satc_configuracion.localizador_portal`.

**DBD-006** — El correo del contribuyente vive en `satc_catalogo.contribuyente` y se complementa con `sar_catalogo.rfc`.

**DBD-007** — Trazabilidad ERP: Toda factura y recibo debe asociarse opcionalmente a un número de Orden de Compra (`orden_compra_erp`) y bandera de comprobación contable (`comprobado_erp`).

---

## 3. Esquemas

```text
satc_configuracion   → Parámetros, localizadores de portales
satc_catalogo        → Tipos de proyecto, regímenes de condominio, viviendas/UPEs, tipos de trámite, estados, contribuyentes
satc_produccion      → Trámites de vivienda, solicitudes/órdenes, folios, recibos
satc_archivo         → Facturas generadas (CFDI PDF/XML)
satc_auditoria       → Bitácora de eventos, cambios y errores
```

---

## 4. Configuración

### Tabla: `satc_configuracion.parametro_sistema`

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
| `CANCUN_PORTAL_RECIBO_URL` | `https://recibo.tesoreriacancun.com` | URL del portal de recibos de Tesorería Cancún |
| `CANCUN_PORTAL_FACTURA_URL` | `https://benitojuarez.expidefactura.com/` | URL del portal de facturación de Benito Juárez |
| `CANCUN_PDF_BASE_PATH` | `T:\CANCUN` | Ruta base del repositorio de almacenado de PDFs |
| `CANCUN_MAX_REINTENTOS` | `3` | Límite máximo de reintentos automáticos por folio |
| `CANCUN_BOT_TIMEOUT_MS` | `30000` | Tiempo de espera límite por transacción Playwright (ms) |
| `PDF_NAMING_PATTERN` | `{folio_electronico}` | Patrón de renombrado de PDFs |
| `SOLICITUD_FOLIO_PREFIX` | `SOL` | Prefijo para folio de lote o solicitud |

---

### Tabla: `satc_configuracion.localizador_portal`
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

### Tabla: `satc_catalogo.estado_vivienda`
Catálogo dedicado para los estados del ciclo de vida físico, jurídico y comercial de la vivienda.

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `estado_vivienda_id` | BIGSERIAL PK | Identificador único |
| `codigo` | VARCHAR(50) UNIQUE NOT NULL | Ej: `EN_CONSTRUCCION`, `EN_INDIVIDUALIZACION`, `ESCRITURADA` |
| `nombre` | VARCHAR(100) NOT NULL | Nombre legible para UI |
| `descripcion` | VARCHAR(250) | Explicación del estado |
| `orden_flujo` | INTEGER NOT NULL | Secuencia lógica en el embudo (1 a 8) |
| `permite_venta` | BOOLEAN DEFAULT FALSE | Candado comercial |
| `permite_escrituracion` | BOOLEAN DEFAULT FALSE | Candado notarial estricto |
| `activo` | BOOLEAN DEFAULT TRUE | |

**Seed de estados de vivienda:**
1. `PROYECTADA` (Orden 1, permite_venta: FALSE, permite_escrituracion: FALSE)
2. `EN_CONSTRUCCION` (Orden 2, permite_venta: FALSE, permite_escrituracion: FALSE)
3. `EN_INDIVIDUALIZACION` (Orden 3, permite_venta: FALSE, permite_escrituracion: FALSE)
4. `LISTA_PARA_VENTA` (Orden 4, permite_venta: TRUE, permite_escrituracion: FALSE)
5. `EN_ESCRITURACION` (Orden 5, permite_venta: TRUE, permite_escrituracion: FALSE)
6. `ESCRITURADA` (Orden 6, permite_venta: TRUE, permite_escrituracion: TRUE)
7. `EN_GARANTIA` (Orden 7, permite_venta: FALSE, permite_escrituracion: TRUE)
8. `CONCLUIDA` (Orden 8, permite_venta: FALSE, permite_escrituracion: TRUE)

---

### Tabla: `satc_catalogo.estado_tramite`
Catálogo dedicado para los estados operativos, documentales y financieros de cada trámite.

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `estado_tramite_id` | BIGSERIAL PK | Identificador único |
| `codigo` | VARCHAR(50) UNIQUE NOT NULL | Ej: `NO_INICIADO`, `INGRESADO_MUNICIPIO`, `FACTURADO`, `COMPROBADO_ERP` |
| `nombre` | VARCHAR(100) NOT NULL | Nombre legible |
| `fase` | VARCHAR(50) NOT NULL | `PREVENTIVA`, `DOCUMENTAL`, `OPERATIVA`, `AUTOMATIZADA`, `FINANCIERA`, `CIERRE` |
| `es_bloqueante` | BOOLEAN DEFAULT TRUE | Si detiene el avance de la vivienda a la siguiente etapa |
| `es_terminal` | BOOLEAN DEFAULT FALSE | Si representa la conclusión exitosa del trámite |
| `activo` | BOOLEAN DEFAULT TRUE | |

**Seed de estados de trámite:**
1. `NO_INICIADO` (Fase: PREVENTIVA, bloqueante: TRUE, terminal: FALSE)
2. `REQUISITOS_PENDIENTES` (Fase: DOCUMENTAL, bloqueante: TRUE, terminal: FALSE)
3. `INGRESADO_MUNICIPIO` (Fase: OPERATIVA, bloqueante: TRUE, terminal: FALSE)
4. `OBSERVADO` (Fase: OPERATIVA, bloqueante: TRUE, terminal: FALSE)
5. `ORDEN_COMPRA_ERP` (Fase: FINANCIERA, bloqueante: TRUE, terminal: FALSE)
6. `PAGO_EMITIDO` (Fase: FINANCIERA, bloqueante: TRUE, terminal: FALSE)
7. `RECIBO_DESCARGADO` (Fase: AUTOMATIZADA, bloqueante: TRUE, terminal: FALSE) — *Bot A*
8. `FACTURADO` (Fase: AUTOMATIZADA, bloqueante: FALSE, terminal: FALSE) — *Bot C*
9. `COMPROBADO_ERP` (Fase: FINANCIERA, bloqueante: FALSE, terminal: FALSE) — *ERP Póliza*
10. `CONCLUIDO` (Fase: CIERRE, bloqueante: FALSE, terminal: TRUE)

---

### Tabla: `satc_catalogo.tipo_tramite`
Catálogo maestro de trámites disponibles por vivienda o régimen.

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `tipo_tramite_id` | BIGSERIAL PK | Identificador único |
| `codigo` | VARCHAR(50) UNIQUE NOT NULL | Ej: `INDIVIDUALIZACION_CATASTRAL`, `NO_ADEUDO_PREDIAL` |
| `nombre` | VARCHAR(200) NOT NULL | Nombre descriptivo |
| `aplica_a` | VARCHAR(30) NOT NULL | `REGIMEN_MATRIZ`, `VIVIENDA_INDIVIDUAL`, `AMBOS` |
| `etapa_disparador` | VARCHAR(30) NOT NULL | `CONSTRUCCION`, `VENTA`, `ESCRITURACION` |
| `dias_vigencia` | INTEGER DEFAULT 0 | Días de vigencia del documento (0 = sin caducidad) |
| `es_obligatorio` | BOOLEAN DEFAULT TRUE | Si bloquea la fase de escrituración |
| `activo` | BOOLEAN DEFAULT TRUE | |

---

### Tabla: `satc_catalogo.contribuyente`
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

### Tabla: `satc_catalogo.regimen_condominio`
Gobierna los macro-lotes que constituyen un Régimen en Condominio con $N$ UPEs.

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `regimen_id` | BIGSERIAL PK | Identificador único del régimen |
| `desarrollo_id` | BIGINT FK NOT NULL | Desarrollo inmobiliario matriz (`sar_catalogo.desarrollo`) |
| `nombre_regimen` | VARCHAR(200) NOT NULL | Ej: "REGIMEN AURA NOVA PLAYA MZ1 LT1" |
| `sm` | VARCHAR(50) | Supermanzana |
| `mz` | VARCHAR(50) NOT NULL | Manzana física |
| `lt` | VARCHAR(50) NOT NULL | Lote físico |
| `total_upes` | INTEGER NOT NULL | Número total de UPEs autorizadas (ej: 577) |
| `upes_generadas` | INTEGER NOT NULL DEFAULT 0 | Contador de UPEs dadas de alta en el sistema |
| `licencia_construccion_matriz` | VARCHAR(100) | Folio de la licencia de construcción general |
| `clave_catastral_matriz` | VARCHAR(100) | Clave catastral del macro-lote previo a individualizar |
| `activo` | BOOLEAN DEFAULT TRUE | |
| `created_at` | TIMESTAMPTZ DEFAULT NOW() | |
| `updated_at` | TIMESTAMPTZ | |

---

### Tabla: `satc_catalogo.vivienda`
Unidad individual de control de trámites (Lote individual en fraccionamiento o UPE en régimen de condominio).

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `vivienda_id` | BIGSERIAL PK | Identificador único de la vivienda / UPE |
| `desarrollo_id` | BIGINT FK NOT NULL | Desarrollo al que pertenece (`sar_catalogo.desarrollo`) |
| `regimen_id` | BIGINT FK NULL | Régimen en condominio (`satc_catalogo.regimen_condominio`). NULL si es Fraccionamiento |
| `tipo_proyecto` | VARCHAR(30) NOT NULL | `FRACCIONAMIENTO` / `REGIMEN_CONDOMINIO` |
| `sm` | VARCHAR(50) NULL | Supermanzana (heredada de régimen o directa de lote) |
| `mz` | VARCHAR(50) NOT NULL | Manzana física |
| `lt` | VARCHAR(50) NOT NULL | Lote físico |
| `edificio` | VARCHAR(50) NULL | Edificio / Torre / Clúster (ej. "Torre A", "Edif 2", NULL si unifamiliar) |
| `vivienda` | VARCHAR(50) NOT NULL | Número de vivienda, casa o interior (ej. "101", "Casa 4", "Depto 3B") |
| `numero_upe` | VARCHAR(50) NULL | Consecutivo de Unidad de Propiedad Exclusiva (ej: "UPE-001" a "UPE-577") |
| `calle` | VARCHAR(200) NULL | Nombre de la vialidad, calle o avenida |
| `clave_catastral` | VARCHAR(100) NULL | Clave catastral individualizada asignada por Catastro |
| `cuenta_predial` | VARCHAR(100) NULL | Número de cuenta de impuesto predial individual |
| `descripcion` | TEXT NULL | Notas descriptivas de la vivienda (orientación, prototipo, etc.) |
| `estado_vivienda_id` | BIGINT FK NOT NULL | Estado actual de la vivienda (`satc_catalogo.estado_vivienda`) |
| `estatus_obra` | VARCHAR(50) DEFAULT 'EN_CONSTRUCCION' | `EN_CONSTRUCCION`, `TERMINADA`, `ENTREGADA` |
| `fecha_venta` | DATE NULL | Fecha de contrato de compraventa |
| `fecha_escrituracion` | DATE NULL | Fecha de firma notarial |
| `activo` | BOOLEAN DEFAULT TRUE | |
| `created_at` | TIMESTAMPTZ DEFAULT NOW() | |
| `updated_at` | TIMESTAMPTZ | |

---

## 6. Producción

### Tabla: `satc_produccion.tramite_vivienda`
Instancia del ciclo de vida de un trámite asociado a una vivienda individual o macro-régimen.
Gobierna el estado operativo, documental y financiero.

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `tramite_vivienda_id` | BIGSERIAL PK | |
| `vivienda_id` | BIGINT FK NULL | Vivienda o UPE asociada (NULL si es trámite matriz) |
| `regimen_id` | BIGINT FK NULL | Régimen asociado (si aplica) |
| `tipo_tramite_id` | BIGINT FK NOT NULL | Tipo de trámite (`satc_catalogo.tipo_tramite`) |
| `estado_tramite_id` | BIGINT FK NOT NULL | Estado actual del trámite (`satc_catalogo.estado_tramite`) |
| `folio_pase_caja` | VARCHAR(100) NULL | Folio de pago municipal previo |
| `folio_electronico` | VARCHAR(100) NULL | Folio emitido por Tesorería |
| `recibo_id` | BIGINT FK NULL | Recibo oficial asociado (`satc_produccion.recibo_cancun`) |
| `factura_id` | BIGINT FK NULL | Factura CFDI timbrada (`satc_produccion.factura_cancun`) |
| `orden_compra_erp` | VARCHAR(50) NULL | Orden de Compra registrada en el ERP |
| `poliza_comprobacion_erp` | VARCHAR(50) NULL | Folio de póliza contable de comprobación en ERP |
| `comprobado_erp` | BOOLEAN DEFAULT FALSE | Bandera de cierre financiero en ERP |
| `fecha_inicio` | DATE DEFAULT CURRENT_DATE | Fecha de apertura de gestión |
| `fecha_conclusion` | DATE NULL | Fecha de obtención de documento final / cierre |
| `usuario_responsable_id` | BIGINT FK NULL | Gestor o tramitador asignado |
| `observaciones` | TEXT NULL | Notas de seguimiento |
| `created_at` | TIMESTAMPTZ DEFAULT NOW() | |
| `updated_at` | TIMESTAMPTZ | |

---

### Tabla: `satc_produccion.requisito_documento`
Expediente digital de evidencias documentales (planos, acuses, constancias, cédulas).

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `documento_id` | BIGSERIAL PK | |
| `tramite_vivienda_id` | BIGINT FK NOT NULL | Trámite al que pertenece la evidencia |
| `tipo_documento` | VARCHAR(50) NOT NULL | `PLANO`, `ACUSE_INGRESO`, `CEDULA_CATASTRAL`, `CERTIFICADO_NO_ADEUDO`, `OTRO` |
| `nombre_archivo` | VARCHAR(255) NOT NULL | Nombre físico del archivo |
| `ruta_archivo` | VARCHAR(1000) NOT NULL | Ruta física o URI en almacenamiento central |
| `hash_sha256` | VARCHAR(64) NOT NULL | Sello criptográfico de integridad |
| `tamano_bytes` | BIGINT NOT NULL | Tamaño del archivo |
| `fecha_emision` | DATE NULL | Fecha del documento |
| `fecha_vencimiento` | DATE NULL | Fecha límite de vigencia (alerta de caducidad) |
| `vigente` | BOOLEAN DEFAULT TRUE | Estado de validez del documento |
| `created_at` | TIMESTAMPTZ DEFAULT NOW() | |

---

### Tabla: `satc_produccion.solicitud`
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

FK: `estado_id` → `satc_catalogo.estado_sistema(estado_id)`

---

### Tabla: `satc_produccion.folio`
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
FK: `solicitud_id` → `satc_produccion.solicitud(solicitud_id)`  
FK: `estado_id` → `satc_catalogo.estado_sistema(estado_id)`

---

### Tabla: `satc_produccion.recibo`
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

FK: `folio_id` → `satc_produccion.folio(folio_id)`  
FK: `estado_id` → `satc_catalogo.estado_sistema(estado_id)`

> **Nota:** El campo `datos_adicionales (JSONB)` permite capturar cualquier campo adicional que aparezca en el PDF sin modificar el esquema.

---

## 7. Gestión Documental

### Tabla: `satc_archivo.factura`
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

FK: `recibo_id` → `satc_produccion.recibo(recibo_id)`

---

## 8. Auditoría

### Tabla: `satc_auditoria.auditoria_evento`

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `evento_id` | BIGSERIAL PK | |
| `modulo` | VARCHAR(100) NOT NULL | `BOT_A` / `BOT_C` / `UI` |
| `accion` | VARCHAR(100) NOT NULL | Descripción de la acción |
| `entidad` | VARCHAR(50) | `folio` / `recibo` / `factura` |
| `entidad_id` | BIGINT | ID de la entidad afectada |
| `detalle` | JSONB | Datos adicionales del evento |
| `fecha` | TIMESTAMPTZ DEFAULT NOW() | |

### Tabla: `satc_auditoria.auditoria_error`

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
CREATE INDEX idx_folio_solicitud_id ON satc_produccion.folio (solicitud_id);
CREATE INDEX idx_folio_estado_id ON satc_produccion.folio (estado_id);
CREATE INDEX idx_recibo_folio_id ON satc_produccion.recibo (folio_id);
CREATE INDEX idx_recibo_estado_id ON satc_produccion.recibo (estado_id);
CREATE INDEX idx_recibo_rfc ON satc_produccion.recibo (rfc);

-- Archivo
CREATE INDEX idx_factura_recibo_id ON satc_archivo.factura (recibo_id);

-- Auditoría
CREATE INDEX idx_audit_evento_fecha ON satc_auditoria.auditoria_evento (fecha DESC);
CREATE INDEX idx_audit_error_fecha ON satc_auditoria.auditoria_error (fecha DESC);
```

---

## 10. Decisiones Congeladas

- **DBD-001** PostgreSQL oficial para `db_satc`.
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
SATC-DB-001 v1.0
BASELINE CONGELADA
APROBADA PARA DESARROLLO
```
