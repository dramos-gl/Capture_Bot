-- =============================================================================
-- MIGRACIÓN 016: Arquitectura de Extracción Metadata-Driven Municipal (SATC)
-- Esquema: satc_configuracion | Motor: PostgreSQL 16+
-- Base de Datos: sar_db / db_satc
--
-- PRINCIPIOS DE PROTECCIÓN ABSOLUTA (SAR-SEC-001 & SAR-DEV-001):
--   1. AISLAMIENTO TOTAL: Modifica exclusivamente el esquema 'satc_configuracion'.
--   2. CERO AFECTACIÓN A SAR: No modifica ni altera ninguna tabla 'sar_*'.
--   3. INTEGRIDAD REFERENCIAL: Vincula en modo solo lectura a 'sar_catalogo.municipio'.
--   4. IDEMPOTENCIA: Uso estricto de IF NOT EXISTS y ON CONFLICT DO NOTHING.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS satc_configuracion;

-- 1. Catálogo Canónico de Campos de Negocio de SATC
CREATE TABLE IF NOT EXISTS satc_configuracion.campo_canonico (
    campo_id BIGSERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,         -- 'clave_catastral', 'folio_electronico', 'padron', 'fecha_alta_folio', 'fecha_alta_cc'
    nombre VARCHAR(100) NOT NULL,               -- Nombre legible para la UI
    descripcion TEXT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

COMMENT ON TABLE satc_configuracion.campo_canonico IS 'Diccionario canónico de campos de negocio a extraer y validar en documentos';

-- 2. Variaciones de Escritura y Anclas (OCR / Documentos / Textos)
CREATE TABLE IF NOT EXISTS satc_configuracion.campo_etiqueta_ancla (
    etiqueta_id BIGSERIAL PRIMARY KEY,
    campo_id BIGINT NOT NULL REFERENCES satc_configuracion.campo_canonico(campo_id) ON DELETE CASCADE,
    etiqueta VARCHAR(100) NOT NULL,             -- 'C.C.', 'Clave Catastral', 'Reg. Catastral', 'UPE'
    regex_ancla TEXT NOT NULL,                  -- Expresión regular insensible a mayúsculas
    prioridad INTEGER NOT NULL DEFAULT 1,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_satc_etiquetas_campo_id ON satc_configuracion.campo_etiqueta_ancla(campo_id);
CREATE INDEX IF NOT EXISTS idx_satc_etiquetas_activo ON satc_configuracion.campo_etiqueta_ancla(activo);

COMMENT ON TABLE satc_configuracion.campo_etiqueta_ancla IS 'Variaciones de etiquetas y anclas de texto para localizar datos en OCR';

-- 3. Formatos y Variantes Estructurales por MUNICIPIO
CREATE TABLE IF NOT EXISTS satc_configuracion.campo_formato_municipio (
    formato_id BIGSERIAL PRIMARY KEY,
    campo_id BIGINT NOT NULL REFERENCES satc_configuracion.campo_canonico(campo_id) ON DELETE CASCADE,
    municipio_id BIGINT NOT NULL REFERENCES sar_catalogo.municipio(municipio_id) ON DELETE RESTRICT,
    nombre_variante VARCHAR(100) NOT NULL,      -- 'Cancún 18 Caracteres', 'Playa Con Guión', etc.
    prioridad INTEGER NOT NULL DEFAULT 1,       -- Orden de evaluación en cascada
    
    -- Extracción y Captura
    regex_extraccion TEXT NOT NULL,             -- Patrón con grupo de captura
    
    -- Validación estricta y normalización
    regex_validacion TEXT NOT NULL,             -- Patrón estricto para verificar el valor limpio
    longitud_min INTEGER NULL,                  -- Rango de longitud mínima
    longitud_max INTEGER NULL,                  -- Rango de longitud máxima
    remover_caracteres VARCHAR(50) DEFAULT ' -/', -- Caracteres que deben limpiarse antes de validar
    permite_sliding_window BOOLEAN DEFAULT FALSE, -- Si true, habilita búsqueda en cadenas fusionadas de OCR (19-39 chars)
    
    descripcion_error VARCHAR(255) NULL,        -- Mensaje informativo de validación
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,

    CONSTRAINT uq_satc_campo_municipio_variante UNIQUE (campo_id, municipio_id, nombre_variante)
);

CREATE INDEX IF NOT EXISTS idx_satc_formatos_campo_municipio 
    ON satc_configuracion.campo_formato_municipio(campo_id, municipio_id, prioridad);
CREATE INDEX IF NOT EXISTS idx_satc_formatos_mun_activo 
    ON satc_configuracion.campo_formato_municipio(activo);

COMMENT ON TABLE satc_configuracion.campo_formato_municipio IS 'Reglas estructurales y variantes de validación y extracción clasificadas por municipio';

-- =============================================================================
-- INSERCIÓN DE DATOS SEMILLA (QUINTANA ROO: CANCÚN, PLAYA DEL CARMEN, TULUM)
-- =============================================================================

-- 1. Campos Canónicos Base
INSERT INTO satc_configuracion.campo_canonico (codigo, nombre, descripcion) VALUES
('clave_catastral', 'Clave Catastral', 'Identificador catastral municipal del predio'),
('folio_electronico', 'Folio Electrónico Inmobiliario', 'Número registral ante el Registro Público de la Propiedad (RPP)'),
('padron', 'Padrón Municipal', 'Número de cuenta o padrón predial municipal'),
('fecha_alta_folio', 'Fecha Alta Folio RPP', 'Fecha de expedición del folio en el RPP'),
('fecha_alta_cc', 'Fecha Alta Clave Catastral', 'Fecha de alta o expedición de la clave en Catastro')
ON CONFLICT (codigo) DO NOTHING;

-- 2. Anclas / Etiquetas para Clave Catastral (Intento 1 en cascada)
INSERT INTO satc_configuracion.campo_etiqueta_ancla (campo_id, etiqueta, regex_ancla, prioridad) 
SELECT c.campo_id, 'Ancla Multi-etiqueta Catastro', 
       '(?i)(?:Clave\s*Catastral|Reg\.\s*Catastral|C\.?\s*C\.?|Catastro|N[ÚU]MERO\s*CATASTRAL|Clave\s*Inmueble)\s*[:\-\.\s]*\s*([a-zA-Z0-9\-]{15,22}|[0-9\-\s]{15,28})', 1
FROM satc_configuracion.campo_canonico c
WHERE c.codigo = 'clave_catastral'
  AND NOT EXISTS (
      SELECT 1 FROM satc_configuracion.campo_etiqueta_ancla a 
      WHERE a.campo_id = c.campo_id AND a.etiqueta = 'Ancla Multi-etiqueta Catastro'
  );

-- Anclas para Folio Electrónico
INSERT INTO satc_configuracion.campo_etiqueta_ancla (campo_id, etiqueta, regex_ancla, prioridad) 
SELECT c.campo_id, 'Ancla Folio Registral RPP', 
       '(?i)(?:Folio\s*(?:Electr[oó]nico|Real|RPP)?|F\.?\s*E\.?)\s*[:\-\.\s]*\s*([a-zA-Z0-9\-]{5,25})', 1
FROM satc_configuracion.campo_canonico c
WHERE c.codigo = 'folio_electronico'
  AND NOT EXISTS (
      SELECT 1 FROM satc_configuracion.campo_etiqueta_ancla a 
      WHERE a.campo_id = c.campo_id AND a.etiqueta = 'Ancla Folio Registral RPP'
  );

-- Anclas para Padrón Municipal
INSERT INTO satc_configuracion.campo_etiqueta_ancla (campo_id, etiqueta, regex_ancla, prioridad) 
SELECT c.campo_id, 'Ancla Padrón Municipal', 
       '(?i)(?:Padr[oó]n(?:\s*Municipal)?|No\.\s*Padr[oó]n|Cuenta\s*Predial)\s*[:\-\.\s]*\s*(\d{5,12})', 1
FROM satc_configuracion.campo_canonico c
WHERE c.codigo = 'padron'
  AND NOT EXISTS (
      SELECT 1 FROM satc_configuracion.campo_etiqueta_ancla a 
      WHERE a.campo_id = c.campo_id AND a.etiqueta = 'Ancla Padrón Municipal'
  );

-- 3. Formatos Municipales de Clave Catastral

-- BENITO JUÁREZ / CANCÚN (municipio_id = 2)
INSERT INTO satc_configuracion.campo_formato_municipio 
(campo_id, municipio_id, nombre_variante, prioridad, regex_extraccion, regex_validacion, longitud_min, longitud_max, permite_sliding_window, descripcion_error)
VALUES
(
    (SELECT campo_id FROM satc_configuracion.campo_canonico WHERE codigo = 'clave_catastral'),
    2,
    'Cancún 18 Caracteres',
    1,
    '\b([1-9](?:\d{17}|\d{16}[A-Z]))\b',
    '^[1-9](?:\d{17}|\d{16}[A-Z])$',
    18, 18, TRUE,
    'La clave catastral para Cancún (18 caracteres) debe iniciar de 1-9 y contener 18 números o 17 números y 1 letra.'
),
(
    (SELECT campo_id FROM satc_configuracion.campo_canonico WHERE codigo = 'clave_catastral'),
    2,
    'Cancún 17 Caracteres',
    2,
    '\b([1-9]\d{15}[A-Z])\b',
    '^[1-9]\d{15}[A-Z]$',
    17, 17, TRUE,
    'La clave catastral para Cancún (17 caracteres) debe iniciar de 1-9 con 16 números seguidos de 1 letra.'
),
(
    (SELECT campo_id FROM satc_configuracion.campo_canonico WHERE codigo = 'clave_catastral'),
    2,
    'Cancún Segmentado Guiones',
    3,
    '\b([1-9]\d{2,}-\d{2,}-\d{2,}-\d{2,}[A-Z0-9\-]*)\b',
    '^[1-9]\d{2,}-\d{2,}-\d{2,}-\d{2,}[A-Z0-9\-]*$',
    12, 25, FALSE,
    'La clave catastral segmentada de Cancún no cumple con el formato estándar con guiones.'
)
ON CONFLICT (campo_id, municipio_id, nombre_variante) DO NOTHING;

-- SOLIDARIDAD / PLAYA DEL CARMEN (municipio_id = 8)
INSERT INTO satc_configuracion.campo_formato_municipio 
(campo_id, municipio_id, nombre_variante, prioridad, regex_extraccion, regex_validacion, longitud_min, longitud_max, permite_sliding_window, descripcion_error)
VALUES
(
    (SELECT campo_id FROM satc_configuracion.campo_canonico WHERE codigo = 'clave_catastral'),
    8,
    'Playa Con Guión',
    1,
    '\b([1-9]\d{14}-\d{1,3})\b',
    '^[1-9]\d{14}-\d{1,3}$',
    17, 19, FALSE,
    'La clave catastral para Solidaridad con guión debe tener 15 dígitos base, guión y de 1 a 3 dígitos sufijo.'
),
(
    (SELECT campo_id FROM satc_configuracion.campo_canonico WHERE codigo = 'clave_catastral'),
    8,
    'Playa Sin Guión',
    2,
    '\b([1-9]\d{14})\b',
    '^[1-9]\d{14}$',
    15, 15, FALSE,
    'La clave catastral continua para Solidaridad debe contener exactamente 15 dígitos numéricos sin iniciar en 0.'
)
ON CONFLICT (campo_id, municipio_id, nombre_variante) DO NOTHING;

-- TULUM (municipio_id = 9)
INSERT INTO satc_configuracion.campo_formato_municipio 
(campo_id, municipio_id, nombre_variante, prioridad, regex_extraccion, regex_validacion, longitud_min, longitud_max, permite_sliding_window, descripcion_error)
VALUES
(
    (SELECT campo_id FROM satc_configuracion.campo_canonico WHERE codigo = 'clave_catastral'),
    9,
    'Tulum Con Guión',
    1,
    '\b([1-9]\d{14}-\d{1,3})\b',
    '^[1-9]\d{14}-\d{1,3}$',
    17, 19, FALSE,
    'La clave catastral para Tulum con guión debe tener 15 dígitos base, guión y de 1 a 3 dígitos sufijo.'
),
(
    (SELECT campo_id FROM satc_configuracion.campo_canonico WHERE codigo = 'clave_catastral'),
    9,
    'Tulum Sin Guión',
    2,
    '\b([1-9]\d{14})\b',
    '^[1-9]\d{14}$',
    15, 15, FALSE,
    'La clave catastral continua para Tulum debe contener exactamente 15 dígitos numéricos sin iniciar en 0.'
)
ON CONFLICT (campo_id, municipio_id, nombre_variante) DO NOTHING;

-- 4. Permisos de Operación para el Usuario de Aplicación (sar_app_user)
GRANT USAGE ON SCHEMA satc_configuracion TO sar_app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA satc_configuracion TO sar_app_user;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA satc_configuracion TO sar_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA satc_configuracion GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO sar_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA satc_configuracion GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO sar_app_user;

