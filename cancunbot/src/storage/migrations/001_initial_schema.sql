-- =============================================================================
-- CANCUNBOT-DB-001: DDL Inicial de la Base de Datos db_cancunbot
-- Versión: 1.0 | Fecha: 2026
-- Motor: PostgreSQL 16+
-- Metodología: Business-First Architecture (BFA)
-- =============================================================================

-- =============================================================================
-- ESQUEMAS
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS cancunbot_configuracion;
CREATE SCHEMA IF NOT EXISTS cancunbot_catalogo;
CREATE SCHEMA IF NOT EXISTS cancunbot_produccion;
CREATE SCHEMA IF NOT EXISTS cancunbot_archivo;
CREATE SCHEMA IF NOT EXISTS cancunbot_auditoria;

COMMENT ON SCHEMA cancunbot_configuracion IS 'Parámetros de sistema y localizadores de portales';
COMMENT ON SCHEMA cancunbot_catalogo IS 'Catálogos: estados, contribuyentes';
COMMENT ON SCHEMA cancunbot_produccion IS 'Producción: solicitudes, folios, recibos';
COMMENT ON SCHEMA cancunbot_archivo IS 'Gestión documental: facturas';
COMMENT ON SCHEMA cancunbot_auditoria IS 'Bitácora de eventos y errores';


-- =============================================================================
-- MÓDULO: CONFIGURACIÓN
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Tabla: parametro_sistema
-- Almacena parámetros configurables del sistema (URLs, rutas, prefijos)
-- -----------------------------------------------------------------------------
CREATE TABLE cancunbot_configuracion.parametro_sistema
(
    parametro_id BIGSERIAL       PRIMARY KEY,
    codigo       VARCHAR(100)    NOT NULL UNIQUE,
    valor        TEXT            NOT NULL,
    descripcion  TEXT,
    activo       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ
);

COMMENT ON TABLE  cancunbot_configuracion.parametro_sistema             IS 'Parámetros configurables del sistema CancunBot';
COMMENT ON COLUMN cancunbot_configuracion.parametro_sistema.codigo      IS 'Clave única del parámetro (ej: PORTAL_RECIBO_URL)';
COMMENT ON COLUMN cancunbot_configuracion.parametro_sistema.valor       IS 'Valor actual del parámetro';


-- -----------------------------------------------------------------------------
-- Tabla: localizador_portal
-- Almacena selectores de elementos web. NUNCA hardcodear selectores en código.
-- -----------------------------------------------------------------------------
CREATE TABLE cancunbot_configuracion.localizador_portal
(
    localizador_id       BIGSERIAL   PRIMARY KEY,
    portal               VARCHAR(30)  NOT NULL,          -- 'RECIBO' | 'FACTURA'
    nombre_clave         VARCHAR(100) NOT NULL UNIQUE,   -- Ej: 'RECIBO_INPUT_FOLIO'
    label_visible        VARCHAR(200) NOT NULL,          -- Descripción para humanos
    estrategia_selector  VARCHAR(50)  NOT NULL,          -- CSS | ID | ROLE | TEXT | XPATH
    valor_selector       VARCHAR(500) NOT NULL,          -- El selector real
    descripcion          VARCHAR(500),
    activo               BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ,

    CONSTRAINT chk_portal CHECK (portal IN ('RECIBO', 'FACTURA')),
    CONSTRAINT chk_estrategia CHECK (estrategia_selector IN ('CSS', 'ID', 'ROLE', 'TEXT', 'XPATH'))
);

COMMENT ON TABLE  cancunbot_configuracion.localizador_portal                       IS 'Selectores de portales web. Evita hardcodeo en código fuente.';
COMMENT ON COLUMN cancunbot_configuracion.localizador_portal.portal                IS 'Portal al que pertenece: RECIBO o FACTURA';
COMMENT ON COLUMN cancunbot_configuracion.localizador_portal.nombre_clave          IS 'Identificador único del localizador (ej: RECIBO_BTN_CONSULTAR)';
COMMENT ON COLUMN cancunbot_configuracion.localizador_portal.estrategia_selector   IS 'Estrategia de selección: CSS, ID, ROLE, TEXT, XPATH';
COMMENT ON COLUMN cancunbot_configuracion.localizador_portal.valor_selector        IS 'El valor real del selector (ej: #btn-consultar)';


-- =============================================================================
-- MÓDULO: CATÁLOGOS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Tabla: estado_sistema
-- Catálogo de estados posibles por entidad de negocio
-- -----------------------------------------------------------------------------
CREATE TABLE cancunbot_catalogo.estado_sistema
(
    estado_id   BIGSERIAL    PRIMARY KEY,
    entidad     VARCHAR(100) NOT NULL,   -- 'SOLICITUD' | 'FOLIO' | 'RECIBO'
    codigo      VARCHAR(50)  NOT NULL,
    descripcion VARCHAR(200),

    CONSTRAINT uq_estado_entidad_codigo UNIQUE (entidad, codigo)
);

COMMENT ON TABLE  cancunbot_catalogo.estado_sistema         IS 'Catálogo de estados por entidad del sistema';
COMMENT ON COLUMN cancunbot_catalogo.estado_sistema.entidad IS 'Nombre de la entidad: SOLICITUD, FOLIO, RECIBO';
COMMENT ON COLUMN cancunbot_catalogo.estado_sistema.codigo  IS 'Código del estado (ej: PENDIENTE, DESCARGADO)';


-- -----------------------------------------------------------------------------
-- Tabla: contribuyente
-- Catálogo de contribuyentes. Fuente del correo electrónico para facturación.
-- -----------------------------------------------------------------------------
CREATE TABLE cancunbot_catalogo.contribuyente
(
    contribuyente_id    BIGSERIAL    PRIMARY KEY,
    rfc                 VARCHAR(13)  NOT NULL UNIQUE,
    razon_social        VARCHAR(500) NOT NULL,
    correo_electronico  VARCHAR(200),
    activo              BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ
);

COMMENT ON TABLE  cancunbot_catalogo.contribuyente                       IS 'Catálogo de contribuyentes. El correo es el default para facturación.';
COMMENT ON COLUMN cancunbot_catalogo.contribuyente.rfc                   IS 'RFC fiscal del contribuyente (único)';
COMMENT ON COLUMN cancunbot_catalogo.contribuyente.correo_electronico    IS 'Correo electrónico por defecto para recibir facturas';


-- =============================================================================
-- MÓDULO: PRODUCCIÓN
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Tabla: solicitud
-- Agrupa un conjunto de folios a procesar.
-- Análogo a sar_produccion.solicitud en el ecosistema SAR.
-- Puede originarse desde importación Excel o captura manual.
-- -----------------------------------------------------------------------------
CREATE TABLE cancunbot_produccion.solicitud
(
    solicitud_id        BIGSERIAL    PRIMARY KEY,
    folio_solicitud     VARCHAR(50)  NOT NULL UNIQUE,   -- Ej: SOL-2026-001
    origen              VARCHAR(20)  NOT NULL,           -- 'EXCEL' | 'MANUAL'
    descripcion         TEXT,
    total_folios        INTEGER      NOT NULL DEFAULT 0,
    folios_procesados   INTEGER      NOT NULL DEFAULT 0,
    folios_facturados   INTEGER      NOT NULL DEFAULT 0,
    folios_error        INTEGER      NOT NULL DEFAULT 0,
    archivo_excel       VARCHAR(500),                    -- Ruta del Excel (si aplica)
    estado_id           BIGINT       NOT NULL,
    usuario_id          BIGINT,                          -- Usuario que creó la solicitud
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ,

    CONSTRAINT chk_origen CHECK (origen IN ('EXCEL', 'MANUAL')),
    CONSTRAINT fk_solicitud_estado FOREIGN KEY (estado_id)
        REFERENCES cancunbot_catalogo.estado_sistema(estado_id)
);

COMMENT ON TABLE  cancunbot_produccion.solicitud                     IS 'Lote de folios a procesar. Origen: Excel importado o captura manual.';
COMMENT ON COLUMN cancunbot_produccion.solicitud.folio_solicitud     IS 'Folio único de la solicitud (ej: SOL-2026-001)';
COMMENT ON COLUMN cancunbot_produccion.solicitud.origen              IS 'Origen de la solicitud: EXCEL o MANUAL';
COMMENT ON COLUMN cancunbot_produccion.solicitud.total_folios        IS 'Total de folios en esta solicitud';
COMMENT ON COLUMN cancunbot_produccion.solicitud.folios_procesados   IS 'Folios con recibo descargado exitosamente';
COMMENT ON COLUMN cancunbot_produccion.solicitud.folios_facturados   IS 'Folios con factura generada exitosamente';
COMMENT ON COLUMN cancunbot_produccion.solicitud.folios_error        IS 'Folios con error de descarga o facturación';
COMMENT ON COLUMN cancunbot_produccion.solicitud.archivo_excel       IS 'Ruta del archivo Excel importado (solo si origen=EXCEL)';


-- -----------------------------------------------------------------------------
-- Tabla: folio
-- Cada folio individual dentro de una solicitud.
-- Es la unidad de trabajo de los Bots A y C.
-- -----------------------------------------------------------------------------
CREATE TABLE cancunbot_produccion.folio
(
    folio_id            BIGSERIAL    PRIMARY KEY,
    solicitud_id        BIGINT       NOT NULL,
    folio_electronico   VARCHAR(50),                    -- Ej: F-2026-615-31044
    folio_pase_caja     VARCHAR(50),                    -- Alternativo
    tipo_folio          VARCHAR(20)  NOT NULL,           -- 'ELECTRONICO' | 'PASE_CAJA'
    intentos            INTEGER      NOT NULL DEFAULT 0,
    ultimo_error        TEXT,
    estado_id           BIGINT       NOT NULL,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ,

    CONSTRAINT chk_tipo_folio CHECK (tipo_folio IN ('ELECTRONICO', 'PASE_CAJA')),
    CONSTRAINT chk_folio_no_nulo CHECK (
        folio_electronico IS NOT NULL OR folio_pase_caja IS NOT NULL
    ),
    CONSTRAINT fk_folio_solicitud FOREIGN KEY (solicitud_id)
        REFERENCES cancunbot_produccion.solicitud(solicitud_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_folio_estado FOREIGN KEY (estado_id)
        REFERENCES cancunbot_catalogo.estado_sistema(estado_id)
);

COMMENT ON TABLE  cancunbot_produccion.folio                     IS 'Folio individual a procesar. Unidad de trabajo de los Bots.';
COMMENT ON COLUMN cancunbot_produccion.folio.folio_electronico   IS 'Folio electrónico (ej: F-2026-615-31044)';
COMMENT ON COLUMN cancunbot_produccion.folio.folio_pase_caja     IS 'Folio de pase de caja (alternativo al electrónico)';
COMMENT ON COLUMN cancunbot_produccion.folio.tipo_folio          IS 'Tipo de folio: ELECTRONICO o PASE_CAJA';
COMMENT ON COLUMN cancunbot_produccion.folio.intentos            IS 'Número de intentos de descarga realizados';
COMMENT ON COLUMN cancunbot_produccion.folio.ultimo_error        IS 'Último mensaje de error registrado';


-- -----------------------------------------------------------------------------
-- Tabla: recibo
-- Datos extraídos del PDF de recibo descargado.
-- Relación 1-a-1 con folio.
-- -----------------------------------------------------------------------------
CREATE TABLE cancunbot_produccion.recibo
(
    recibo_id               BIGSERIAL       PRIMARY KEY,
    folio_id                BIGINT          NOT NULL UNIQUE,    -- 1-a-1 con folio
    folio_pase_caja         VARCHAR(50),                        -- Extraído del PDF
    folio_electronico       VARCHAR(50)     UNIQUE,             -- Extraído del PDF
    fecha_expedicion        DATE,                               -- Extraído del PDF
    hora_expedicion         TIME,                               -- Extraído del PDF
    lugar_expedicion        VARCHAR(200),                       -- Extraído del PDF
    rfc                     VARCHAR(13),                        -- Extraído del PDF
    contribucion            VARCHAR(300),                       -- Extraído del PDF
    nombre_contribuyente    VARCHAR(500),                       -- Extraído del PDF
    concepto                TEXT,                               -- Detalle concepto de cobro
    total                   NUMERIC(14,2),                      -- Importe total
    forma_pago              VARCHAR(100),                       -- Opcional
    datos_adicionales       JSONB,                              -- Campos extras del PDF
    pdf_nombre              VARCHAR(500),                       -- Nombre final del PDF
    pdf_ruta                VARCHAR(1000),                      -- Ruta del PDF organizado
    hash_sha256             VARCHAR(64),                        -- Integridad del archivo
    estado_id               BIGINT          NOT NULL,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ,

    CONSTRAINT fk_recibo_folio FOREIGN KEY (folio_id)
        REFERENCES cancunbot_produccion.folio(folio_id),
    CONSTRAINT fk_recibo_estado FOREIGN KEY (estado_id)
        REFERENCES cancunbot_catalogo.estado_sistema(estado_id)
);

COMMENT ON TABLE  cancunbot_produccion.recibo                         IS 'Datos extraídos del PDF de recibo electrónico. 1-a-1 con folio.';
COMMENT ON COLUMN cancunbot_produccion.recibo.folio_electronico       IS 'Folio electrónico extraído del PDF (ej: F-2026-615-31044)';
COMMENT ON COLUMN cancunbot_produccion.recibo.datos_adicionales       IS 'JSONB para campos extras encontrados en el PDF sin modificar el esquema';
COMMENT ON COLUMN cancunbot_produccion.recibo.hash_sha256             IS 'Hash SHA256 del archivo PDF para verificación de integridad';


-- =============================================================================
-- MÓDULO: ARCHIVO
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Tabla: factura
-- Comprobante fiscal (CFDI) generado a partir de un recibo.
-- -----------------------------------------------------------------------------
CREATE TABLE cancunbot_archivo.factura
(
    factura_id          BIGSERIAL       PRIMARY KEY,
    recibo_id           BIGINT          NOT NULL UNIQUE,    -- 1-a-1 con recibo
    uuid                VARCHAR(36)     UNIQUE,             -- UUID fiscal del CFDI
    folio_fiscal        VARCHAR(100),
    rfc_emisor          VARCHAR(13),
    fecha_factura       TIMESTAMPTZ,
    pdf_path            VARCHAR(1000),
    xml_path            VARCHAR(1000),
    estado              VARCHAR(30)     NOT NULL,
    datos_adicionales   JSONB,                              -- Datos extras del portal
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ,

    CONSTRAINT fk_factura_recibo FOREIGN KEY (recibo_id)
        REFERENCES cancunbot_produccion.recibo(recibo_id)
);

COMMENT ON TABLE  cancunbot_archivo.factura                       IS 'Factura CFDI generada a partir de un recibo.';
COMMENT ON COLUMN cancunbot_archivo.factura.uuid                  IS 'UUID fiscal único del CFDI';
COMMENT ON COLUMN cancunbot_archivo.factura.datos_adicionales     IS 'JSONB para datos extras capturados del portal de facturación';


-- =============================================================================
-- MÓDULO: AUDITORÍA
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Tabla: auditoria_evento
-- Bitácora de todas las operaciones relevantes del sistema
-- -----------------------------------------------------------------------------
CREATE TABLE cancunbot_auditoria.auditoria_evento
(
    evento_id   BIGSERIAL       PRIMARY KEY,
    modulo      VARCHAR(100)    NOT NULL,   -- 'BOT_A' | 'BOT_C' | 'UI' | 'SISTEMA'
    accion      VARCHAR(100)    NOT NULL,   -- Descripción de la acción
    entidad     VARCHAR(50),               -- 'folio' | 'recibo' | 'factura'
    entidad_id  BIGINT,                    -- ID de la entidad afectada
    detalle     JSONB,                     -- Datos adicionales del evento
    fecha       TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE cancunbot_auditoria.auditoria_evento IS 'Bitácora de operaciones del sistema CancunBot';


-- -----------------------------------------------------------------------------
-- Tabla: auditoria_error
-- Registro de todos los errores ocurridos en el sistema
-- -----------------------------------------------------------------------------
CREATE TABLE cancunbot_auditoria.auditoria_error
(
    error_id    BIGSERIAL       PRIMARY KEY,
    modulo      VARCHAR(100)    NOT NULL,
    entidad     VARCHAR(50),
    entidad_id  BIGINT,
    mensaje     TEXT            NOT NULL,
    stack_trace TEXT,
    fecha       TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE cancunbot_auditoria.auditoria_error IS 'Registro de errores del sistema CancunBot';


-- =============================================================================
-- ÍNDICES DE RENDIMIENTO
-- =============================================================================

-- Producción
CREATE INDEX idx_folio_solicitud_id ON cancunbot_produccion.folio (solicitud_id);
CREATE INDEX idx_folio_estado_id    ON cancunbot_produccion.folio (estado_id);
CREATE INDEX idx_recibo_folio_id    ON cancunbot_produccion.recibo (folio_id);
CREATE INDEX idx_recibo_estado_id   ON cancunbot_produccion.recibo (estado_id);
CREATE INDEX idx_recibo_rfc         ON cancunbot_produccion.recibo (rfc);

-- Archivo
CREATE INDEX idx_factura_recibo_id ON cancunbot_archivo.factura (recibo_id);

-- Auditoría (orden cronológico inverso para consultas recientes)
CREATE INDEX idx_audit_evento_fecha ON cancunbot_auditoria.auditoria_evento (fecha DESC);
CREATE INDEX idx_audit_error_fecha  ON cancunbot_auditoria.auditoria_error  (fecha DESC);
CREATE INDEX idx_audit_evento_modulo ON cancunbot_auditoria.auditoria_evento (modulo);
