-- =============================================================================
-- MIGRACIÓN 003: CancunBot Extension sobre sar_db
-- Módulo: R2F-Cancún (Recibos y Facturas Tesorería Cancún)
-- Versión: 1.0 | Fecha: 2026
-- Motor: PostgreSQL 16+
--
-- REGLAS DE SEGURIDAD:
--   1. SOLO AGREGA — nunca modifica ni elimina estructuras existentes del SAR.
--   2. Todos los INSERT usan ON CONFLICT DO NOTHING (idempotente).
--   3. El ALTER TABLE usa ADD COLUMN IF NOT EXISTS (seguro si ya existe).
--   4. Ejecutar SOLO cuando el usuario autorice explícitamente.
--   5. Ejecutar conectado a la base de datos: sar_db
--
-- Verificación post-ejecución (ver comentario al final del script).
-- =============================================================================


-- =============================================================================
-- SECCIÓN 1: ALTER TABLE — columna 'portal' en localizador_portal
-- Impacto en el SAR existente: CERO
--   - Los bots SAR leen solo valor_selector, nunca leen portal.
--   - Las filas existentes reciben DEFAULT 'SAR'.
--   - El modelo ORM y los repositorios SAR no se rompen.
-- =============================================================================

ALTER TABLE sar_configuracion.localizador_portal
    ADD COLUMN IF NOT EXISTS portal VARCHAR(50) DEFAULT 'SAR';

COMMENT ON COLUMN sar_configuracion.localizador_portal.portal
    IS 'Portal al que pertenece el localizador. SAR: portal original Tributanet/SATQ. CANCUN_RECIBO / CANCUN_FACTURA: portales R2F-Cancun.';

-- Marcar los localizadores existentes del SAR (sin romper nada, es solo un UPDATE)
UPDATE sar_configuracion.localizador_portal
    SET portal = 'SAR'
    WHERE portal IS NULL;


-- =============================================================================
-- SECCIÓN 2: Nuevo esquema exclusivo de CancunBot
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS cancunbot_produccion;

COMMENT ON SCHEMA cancunbot_produccion
    IS 'Esquema del módulo R2F-Cancún. Lotes de folios, folios, recibos y facturas de Tesorería Cancún.';


-- =============================================================================
-- SECCIÓN 3: app_modulo — R2F-Cancún
-- Aparece en el dropdown de módulos del Login del SAR automáticamente.
-- =============================================================================

INSERT INTO sar_seguridad.app_modulo (codigo, nombre, activo)
VALUES ('R2F_CANCUN', 'R2F-Cancún: Recibos y Facturas', TRUE)
ON CONFLICT (codigo) DO NOTHING;


-- =============================================================================
-- SECCIÓN 4: modulo — Módulos funcionales RBAC de R2F-Cancún
-- =============================================================================

INSERT INTO sar_seguridad.modulo (codigo, nombre, descripcion, activo)
VALUES
    ('FOLIOS_CANCUN',   'Folios y Lotes Cancún',   'Importación y gestión de lotes de folios electrónicos', TRUE),
    ('RECIBOS_CANCUN',  'Recibos Cancún',           'Descarga y consulta de recibos de Tesorería Cancún',    TRUE),
    ('FACTURAS_CANCUN', 'Facturas Cancún',          'Generación y consulta de facturas CFDI Cancún',         TRUE)
ON CONFLICT (codigo) DO NOTHING;


-- =============================================================================
-- SECCIÓN 5: estado_sistema — Estados para entidades CancunBot
-- Entidades prefijadas con '_cancun' para no colisionar con estados SAR.
-- =============================================================================

INSERT INTO sar_catalogo.estado_sistema (entidad, codigo, descripcion)
VALUES
    -- Lote de folios
    ('lote_folio',    'NUEVO',               'Lote recién creado, sin procesar'),
    ('lote_folio',    'EN_PROCESO',          'Bot procesando los folios del lote'),
    ('lote_folio',    'COMPLETADO',          'Todos los folios fueron procesados exitosamente'),
    ('lote_folio',    'COMPLETADO_PARCIAL',  'Procesado con errores en algunos folios'),
    ('lote_folio',    'CANCELADO',           'Lote cancelado por el operador'),
    -- Folio individual
    ('folio_cancun',  'PENDIENTE',           'Folio en espera de descarga por Bot Recibos'),
    ('folio_cancun',  'DESCARGANDO',         'Bot Recibos descargando el recibo del portal'),
    ('folio_cancun',  'RECIBO_OK',           'Recibo descargado y datos extraídos correctamente'),
    ('folio_cancun',  'ERROR_DESCARGA',      'Error al consultar o descargar el recibo del portal'),
    ('folio_cancun',  'FACTURADO',           'Folio con factura CFDI generada exitosamente'),
    -- Recibo capturado
    ('recibo_cancun', 'CAPTURADO',           'Datos del recibo extraídos y guardados en BD'),
    ('recibo_cancun', 'PENDIENTE_FACTURAR',  'Recibo listo para proceso de facturación'),
    ('recibo_cancun', 'FACTURANDO',          'Bot Facturas generando la factura en el portal'),
    ('recibo_cancun', 'FACTURADO',           'Factura CFDI generada y descargada exitosamente'),
    ('recibo_cancun', 'ERROR_FACTURA',       'Error al generar la factura en el portal')
ON CONFLICT (entidad, codigo) DO NOTHING;


-- =============================================================================
-- SECCIÓN 6: evento_sistema — Tipos de evento para auditoría CancunBot
-- =============================================================================

INSERT INTO sar_catalogo.evento_sistema (codigo, descripcion)
VALUES
    ('IMPORTAR_LOTE_CANCUN',    'Importación de lote de folios desde Excel o captura manual'),
    ('DESCARGAR_RECIBO_CANCUN', 'Descarga y extracción de datos de recibo electrónico Cancún'),
    ('GENERAR_FACTURA_CANCUN',  'Generación de CFDI para recibo de Tesorería Cancún'),
    ('ERROR_BOT_RECIBO_CUN',    'Error crítico en el proceso del Bot de Recibos Cancún'),
    ('ERROR_BOT_FACTURA_CUN',   'Error crítico en el proceso del Bot de Facturas Cancún')
ON CONFLICT (codigo) DO NOTHING;


-- =============================================================================
-- SECCIÓN 7: parametro_sistema — Configuración de R2F-Cancún
-- Prefijo CANCUN_ para todos los parámetros del módulo.
-- =============================================================================

INSERT INTO sar_configuracion.parametro_sistema (codigo, valor, descripcion, activo)
VALUES
    ('CANCUN_PORTAL_RECIBO_URL',
     'https://recibo.tesoreriacancun.com',
     'URL base del portal de recibos electrónicos de Tesorería Cancún',
     TRUE),

    ('CANCUN_PORTAL_FACTURA_URL',
     'https://benitojuarez.expidefactura.com/',
     'URL base del portal de facturación electrónica Benito Juárez',
     TRUE),

    ('CANCUN_PDF_BASE_PATH',
     'Y:\R2F\Recibos',
     'Ruta base donde se guardarán los PDFs de recibos y facturas de Cancún',
     TRUE),

    ('CANCUN_PDF_NAMING_PATTERN',
     '{folio_electronico}',
     'Patrón de renombrado del PDF descargado. Tokens disponibles: {folio_electronico}, {folio_pase_caja}, {fecha}, {rfc}',
     TRUE),

    ('CANCUN_MAX_REINTENTOS',
     '3',
     'Número máximo de reintentos del bot ante fallas de red o portal',
     TRUE),

    ('CANCUN_BOT_TIMEOUT_MS',
     '30000',
     'Timeout en milisegundos para operaciones de Playwright en bots Cancún',
     TRUE),

    ('CANCUN_CORREO_FACTURA',
     '',
     'Correo electrónico por defecto para recepción de facturas CFDI (puede ser sobreescrito por RFC en catálogo rfc)',
     TRUE),

    ('CANCUN_EXCEL_COL_FOLIO_ELECTRONICO',
     'FOLIO',
     'Nombre del encabezado de columna en Excel para el folio electrónico',
     TRUE),

    ('CANCUN_EXCEL_COL_FOLIO_PASE_CAJA',
     'FOLIO_PASE_CAJA',
     'Nombre del encabezado de columna en Excel para el folio de pase de caja',
     TRUE),

    ('CANCUN_LOTE_FOLIO_PREFIX',
     'LOT',
     'Prefijo para el número de lote (ej: LOT-2026-001)',
     TRUE)
ON CONFLICT (codigo) DO NOTHING;


-- =============================================================================
-- SECCIÓN 8: localizador_portal — Selectores de portales CancunBot
-- portal = 'CANCUN_RECIBO'  → portal recibos (https://recibo.tesoreriacancun.com)
-- portal = 'CANCUN_FACTURA' → portal facturas (https://benitojuarez.expidefactura.com/)
-- NOTA: valor_selector = '[PENDIENTE_INSPECCION]' — actualizar tras inspección.
-- =============================================================================

INSERT INTO sar_configuracion.localizador_portal
    (nombre_clave, label_visible, estrategia_selector, valor_selector, descripcion, activo, portal)
VALUES
-- --- Portal de Recibos ---
('CANCUN_RECIBO_INPUT_FOLIO',
 'Campo de folio',           'CSS', '[PENDIENTE_INSPECCION]',
 'Input donde se ingresa el folio electrónico o pase de caja', TRUE, 'CANCUN_RECIBO'),

('CANCUN_RECIBO_BTN_CONSULTAR',
 'Botón Consultar',          'CSS', '[PENDIENTE_INSPECCION]',
 'Botón que ejecuta la consulta del folio en el portal', TRUE, 'CANCUN_RECIBO'),

('CANCUN_RECIBO_BTN_DESCARGAR',
 'Botón Descargar PDF',      'CSS', '[PENDIENTE_INSPECCION]',
 'Botón que inicia la descarga del PDF del recibo electrónico', TRUE, 'CANCUN_RECIBO'),

('CANCUN_RECIBO_MSG_NO_ENCONTRADO',
 'Mensaje folio no encontrado', 'CSS', '[PENDIENTE_INSPECCION]',
 'Elemento visible cuando el folio consultado no existe en el portal', TRUE, 'CANCUN_RECIBO'),

-- --- Portal de Facturación ---
('CANCUN_FACTURA_INPUT_RFC',
 'Campo RFC del contribuyente',  'CSS', '[PENDIENTE_INSPECCION]',
 'Input donde se ingresa el RFC para generar la factura', TRUE, 'CANCUN_FACTURA'),

('CANCUN_FACTURA_INPUT_CORREO',
 'Campo correo electrónico',     'CSS', '[PENDIENTE_INSPECCION]',
 'Input donde se ingresa el correo del contribuyente receptor', TRUE, 'CANCUN_FACTURA'),

('CANCUN_FACTURA_INPUT_FOLIO',
 'Campo folio del recibo',       'CSS', '[PENDIENTE_INSPECCION]',
 'Input donde se ingresa el folio electrónico del recibo a facturar', TRUE, 'CANCUN_FACTURA'),

('CANCUN_FACTURA_INPUT_IMPORTE',
 'Campo importe',                'CSS', '[PENDIENTE_INSPECCION]',
 'Input donde se ingresa el importe total del recibo', TRUE, 'CANCUN_FACTURA'),

('CANCUN_FACTURA_BTN_GENERAR',
 'Botón Generar / Timbrar',      'CSS', '[PENDIENTE_INSPECCION]',
 'Botón que ejecuta el timbrado de la factura CFDI', TRUE, 'CANCUN_FACTURA'),

('CANCUN_FACTURA_BTN_DESCARGAR_PDF',
 'Botón Descargar PDF factura',  'CSS', '[PENDIENTE_INSPECCION]',
 'Botón para descargar el PDF de la factura generada', TRUE, 'CANCUN_FACTURA'),

('CANCUN_FACTURA_BTN_DESCARGAR_XML',
 'Botón Descargar XML factura',  'CSS', '[PENDIENTE_INSPECCION]',
 'Botón para descargar el XML fiscal de la factura generada', TRUE, 'CANCUN_FACTURA'),

('CANCUN_FACTURA_MSG_EXITO',
 'Mensaje factura exitosa',      'CSS', '[PENDIENTE_INSPECCION]',
 'Elemento visible cuando la factura fue generada con éxito', TRUE, 'CANCUN_FACTURA'),

('CANCUN_FACTURA_MSG_ERROR',
 'Mensaje error en facturación', 'CSS', '[PENDIENTE_INSPECCION]',
 'Elemento visible cuando ocurre un error en el proceso de facturación', TRUE, 'CANCUN_FACTURA')

ON CONFLICT (nombre_clave) DO NOTHING;


-- =============================================================================
-- SECCIÓN 9: Tablas nuevas en cancunbot_produccion
-- Diseño basado en 001_initial_schema.sql (que ya tenía buen detalle)
-- adaptado para vivir en sar_db con FKs a sar_seguridad y sar_catalogo.
-- =============================================================================

-- -----------------------------------------------------------------------
-- lote_folio: agrupa folios. 'solicitud' en nomenclatura anterior del proyecto.
-- Se renombra para no colisionar con sar_produccion.solicitud.
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cancunbot_produccion.lote_folio (
    lote_id             BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    folio_lote          VARCHAR(50)  NOT NULL UNIQUE,
    descripcion         TEXT,
    origen              VARCHAR(20)  NOT NULL DEFAULT 'EXCEL',
    total_folios        INTEGER      NOT NULL DEFAULT 0,
    folios_procesados   INTEGER      NOT NULL DEFAULT 0,
    folios_error        INTEGER      NOT NULL DEFAULT 0,
    folios_facturados   INTEGER      NOT NULL DEFAULT 0,
    archivo_excel       VARCHAR(500),
    estado_id           BIGINT       NOT NULL,
    usuario_id          BIGINT       NOT NULL,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ,

    CONSTRAINT chk_lote_origen  CHECK (origen IN ('EXCEL', 'MANUAL')),
    CONSTRAINT fk_lote_estado   FOREIGN KEY (estado_id)
        REFERENCES sar_catalogo.estado_sistema(estado_id) ON DELETE RESTRICT,
    CONSTRAINT fk_lote_usuario  FOREIGN KEY (usuario_id)
        REFERENCES sar_seguridad.usuario(usuario_id) ON DELETE RESTRICT
);

COMMENT ON TABLE  cancunbot_produccion.lote_folio            IS 'Lote de folios a procesar. Origen: Excel importado o captura manual.';
COMMENT ON COLUMN cancunbot_produccion.lote_folio.folio_lote IS 'Folio único del lote (ej: LOT-2026-001)';
COMMENT ON COLUMN cancunbot_produccion.lote_folio.origen     IS 'Fuente del lote: EXCEL o MANUAL';


-- -----------------------------------------------------------------------
-- folio_cancun: folio individual. Unidad de trabajo de ambos bots.
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cancunbot_produccion.folio_cancun (
    folio_id            BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    lote_id             BIGINT       NOT NULL,
    folio_electronico   VARCHAR(100),
    folio_pase_caja     VARCHAR(100),
    tipo_folio          VARCHAR(20)  NOT NULL DEFAULT 'ELECTRONICO',
    intentos            INTEGER      NOT NULL DEFAULT 0,
    ultimo_error        TEXT,
    estado_id           BIGINT       NOT NULL,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ,

    CONSTRAINT chk_folio_tipo     CHECK (tipo_folio IN ('ELECTRONICO', 'PASE_CAJA')),
    CONSTRAINT chk_folio_no_nulo  CHECK (
        folio_electronico IS NOT NULL OR folio_pase_caja IS NOT NULL
    ),
    CONSTRAINT fk_folio_lote      FOREIGN KEY (lote_id)
        REFERENCES cancunbot_produccion.lote_folio(lote_id) ON DELETE CASCADE,
    CONSTRAINT fk_folio_estado    FOREIGN KEY (estado_id)
        REFERENCES sar_catalogo.estado_sistema(estado_id) ON DELETE RESTRICT
);

COMMENT ON TABLE  cancunbot_produccion.folio_cancun                   IS 'Folio individual a procesar. Unidad de trabajo de Bot Recibos y Bot Facturas.';
COMMENT ON COLUMN cancunbot_produccion.folio_cancun.folio_electronico IS 'Folio electrónico (ej: F-2026-615-31044)';
COMMENT ON COLUMN cancunbot_produccion.folio_cancun.intentos          IS 'Número de intentos de descarga realizados';


-- -----------------------------------------------------------------------
-- recibo_cancun: datos extraídos del PDF de recibo. 1-a-1 con folio_cancun.
-- datos_adicionales JSONB absorbe campos extras sin modificar el esquema.
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cancunbot_produccion.recibo_cancun (
    recibo_id               BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    folio_id                BIGINT          NOT NULL UNIQUE,
    folio_pase_caja         VARCHAR(100),
    folio_electronico       VARCHAR(100)    UNIQUE,
    fecha_expedicion        DATE,
    hora_expedicion         TIME,
    lugar_expedicion        VARCHAR(300),
    rfc                     VARCHAR(13),
    contribucion            VARCHAR(300),
    nombre_contribuyente    VARCHAR(500),
    concepto                TEXT,
    total                   NUMERIC(14,2),
    forma_pago              VARCHAR(100),
    datos_adicionales       JSONB,
    pdf_nombre              VARCHAR(500),
    pdf_ruta                VARCHAR(1000),
    hash_sha256             VARCHAR(64),
    correo_factura          VARCHAR(200),
    estado_id               BIGINT          NOT NULL,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ,

    CONSTRAINT fk_recibo_folio  FOREIGN KEY (folio_id)
        REFERENCES cancunbot_produccion.folio_cancun(folio_id) ON DELETE CASCADE,
    CONSTRAINT fk_recibo_estado FOREIGN KEY (estado_id)
        REFERENCES sar_catalogo.estado_sistema(estado_id) ON DELETE RESTRICT
);

COMMENT ON TABLE  cancunbot_produccion.recibo_cancun                   IS 'Datos extraídos del PDF de recibo electrónico. 1-a-1 con folio_cancun.';
COMMENT ON COLUMN cancunbot_produccion.recibo_cancun.datos_adicionales IS 'JSONB para campos extras del PDF sin modificar el esquema';
COMMENT ON COLUMN cancunbot_produccion.recibo_cancun.hash_sha256       IS 'SHA256 del PDF descargado para verificación de integridad';
COMMENT ON COLUMN cancunbot_produccion.recibo_cancun.correo_factura    IS 'Correo del contribuyente para recibir la factura CFDI';


-- -----------------------------------------------------------------------
-- factura_cancun: CFDI generado. 1-a-1 con recibo_cancun.
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cancunbot_produccion.factura_cancun (
    factura_id              BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    recibo_id               BIGINT          NOT NULL UNIQUE,
    uuid_cfdi               VARCHAR(36)     UNIQUE,
    folio_fiscal            VARCHAR(100),
    rfc_emisor              VARCHAR(13),
    rfc_receptor            VARCHAR(13),
    razon_social_receptor   VARCHAR(500),
    cp_receptor             VARCHAR(10),
    fecha_timbrado          TIMESTAMPTZ,
    pdf_path                VARCHAR(1000),
    xml_path                VARCHAR(1000),
    datos_adicionales       JSONB,
    estado                  VARCHAR(30)     NOT NULL DEFAULT 'PENDIENTE',
    mensaje_error           TEXT,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ,

    CONSTRAINT fk_factura_recibo FOREIGN KEY (recibo_id)
        REFERENCES cancunbot_produccion.recibo_cancun(recibo_id) ON DELETE RESTRICT
);

COMMENT ON TABLE  cancunbot_produccion.factura_cancun                   IS 'Factura CFDI generada. 1-a-1 con recibo_cancun.';
COMMENT ON COLUMN cancunbot_produccion.factura_cancun.uuid_cfdi         IS 'UUID fiscal único del CFDI';
COMMENT ON COLUMN cancunbot_produccion.factura_cancun.datos_adicionales IS 'JSONB para datos extras del portal de facturación';


-- =============================================================================
-- SECCIÓN 10: Índices de rendimiento
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_folio_cancun_lote_id    ON cancunbot_produccion.folio_cancun  (lote_id);
CREATE INDEX IF NOT EXISTS idx_folio_cancun_estado_id  ON cancunbot_produccion.folio_cancun  (estado_id);
CREATE INDEX IF NOT EXISTS idx_recibo_cancun_folio_id  ON cancunbot_produccion.recibo_cancun (folio_id);
CREATE INDEX IF NOT EXISTS idx_recibo_cancun_estado_id ON cancunbot_produccion.recibo_cancun (estado_id);
CREATE INDEX IF NOT EXISTS idx_recibo_cancun_rfc       ON cancunbot_produccion.recibo_cancun (rfc);
CREATE INDEX IF NOT EXISTS idx_factura_cancun_recibo   ON cancunbot_produccion.factura_cancun (recibo_id);
CREATE INDEX IF NOT EXISTS idx_factura_cancun_estado   ON cancunbot_produccion.factura_cancun (estado);


-- =============================================================================
-- SECCIÓN 11: Permisos RBAC — módulos CancunBot × acciones existentes
-- =============================================================================

INSERT INTO sar_seguridad.permiso (modulo_id, accion_id, activo)
SELECT m.modulo_id, a.accion_id, TRUE
FROM sar_seguridad.modulo m
CROSS JOIN sar_seguridad.accion a
WHERE m.codigo IN ('FOLIOS_CANCUN', 'RECIBOS_CANCUN', 'FACTURAS_CANCUN')
ON CONFLICT (modulo_id, accion_id) DO NOTHING;


-- =============================================================================
-- SECCIÓN 12: Acceso al app_modulo R2F_CANCUN por rol
-- =============================================================================

INSERT INTO sar_seguridad.rol_app_modulo (rol_id, app_modulo_id)
SELECT r.rol_id, am.app_modulo_id
FROM sar_seguridad.rol r
CROSS JOIN sar_seguridad.app_modulo am
WHERE r.codigo IN ('ADMINISTRADOR', 'OPERADOR')
  AND am.codigo = 'R2F_CANCUN'
ON CONFLICT DO NOTHING;


-- =============================================================================
-- SECCIÓN 13: Asignación de permisos de roles en módulos CancunBot
-- ADMINISTRADOR: todos los permisos (CREAR, LEER, EDITAR, ELIMINAR, ASIGNAR, EJECUTAR)
-- OPERADOR: solo LEER y EJECUTAR
-- =============================================================================

INSERT INTO sar_seguridad.rol_permiso (rol_id, permiso_id)
SELECT
    (SELECT rol_id FROM sar_seguridad.rol WHERE codigo = 'ADMINISTRADOR'),
    p.permiso_id
FROM sar_seguridad.permiso p
JOIN sar_seguridad.modulo m ON p.modulo_id = m.modulo_id
WHERE m.codigo IN ('FOLIOS_CANCUN', 'RECIBOS_CANCUN', 'FACTURAS_CANCUN')
ON CONFLICT DO NOTHING;

INSERT INTO sar_seguridad.rol_permiso (rol_id, permiso_id)
SELECT
    (SELECT rol_id FROM sar_seguridad.rol WHERE codigo = 'OPERADOR'),
    p.permiso_id
FROM sar_seguridad.permiso p
JOIN sar_seguridad.modulo m ON p.modulo_id = m.modulo_id
JOIN sar_seguridad.accion a ON p.accion_id = a.accion_id
WHERE m.codigo IN ('FOLIOS_CANCUN', 'RECIBOS_CANCUN', 'FACTURAS_CANCUN')
  AND a.codigo IN ('LEER', 'EJECUTAR')
ON CONFLICT DO NOTHING;


-- =============================================================================
-- SECCIÓN 14: Sincronización de secuencias
-- =============================================================================

SELECT setval(
    COALESCE(pg_get_serial_sequence('cancunbot_produccion.lote_folio', 'lote_id'),
             'cancunbot_produccion.lote_folio_lote_id_seq'),
    COALESCE((SELECT MAX(lote_id) FROM cancunbot_produccion.lote_folio), 0) + 1, false);

SELECT setval(
    COALESCE(pg_get_serial_sequence('cancunbot_produccion.folio_cancun', 'folio_id'),
             'cancunbot_produccion.folio_cancun_folio_id_seq'),
    COALESCE((SELECT MAX(folio_id) FROM cancunbot_produccion.folio_cancun), 0) + 1, false);

SELECT setval(
    COALESCE(pg_get_serial_sequence('cancunbot_produccion.recibo_cancun', 'recibo_id'),
             'cancunbot_produccion.recibo_cancun_recibo_id_seq'),
    COALESCE((SELECT MAX(recibo_id) FROM cancunbot_produccion.recibo_cancun), 0) + 1, false);

SELECT setval(
    COALESCE(pg_get_serial_sequence('cancunbot_produccion.factura_cancun', 'factura_id'),
             'cancunbot_produccion.factura_cancun_factura_id_seq'),
    COALESCE((SELECT MAX(factura_id) FROM cancunbot_produccion.factura_cancun), 0) + 1, false);


-- =============================================================================
-- FIN DE MIGRACIÓN 003 — R2F-Cancún
--
-- VERIFICACIONES RECOMENDADAS DESPUÉS DE EJECUTAR:
--
-- 1. Columna portal agregada:
--    SELECT column_name, data_type, column_default
--    FROM information_schema.columns
--    WHERE table_schema='sar_configuracion'
--      AND table_name='localizador_portal'
--      AND column_name='portal';
--
-- 2. Esquema y tablas creadas:
--    SELECT table_name FROM information_schema.tables
--    WHERE table_schema='cancunbot_produccion' ORDER BY table_name;
--
-- 3. Módulo visible en login:
--    SELECT codigo, nombre, activo FROM sar_seguridad.app_modulo
--    WHERE codigo='R2F_CANCUN';
--
-- 4. Estados cargados:
--    SELECT entidad, codigo FROM sar_catalogo.estado_sistema
--    WHERE entidad IN ('lote_folio','folio_cancun','recibo_cancun')
--    ORDER BY entidad, codigo;
--
-- 5. Parámetros cargados:
--    SELECT codigo, valor FROM sar_configuracion.parametro_sistema
--    WHERE codigo LIKE 'CANCUN_%' ORDER BY codigo;
--
-- 6. Localizadores con portal:
--    SELECT nombre_clave, portal FROM sar_configuracion.localizador_portal
--    WHERE portal LIKE 'CANCUN_%' ORDER BY portal, nombre_clave;
-- =============================================================================
