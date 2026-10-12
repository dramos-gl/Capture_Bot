-- =============================================================================
-- MIGRACIÓN 010: Gobernanza del Ciclo de Vida de Trámites por Vivienda (UPEs)
-- Módulo: SATC (Sistema de Automatización y Control de Trámites Cancún)
-- Versión: 1.0 | Fecha: 2026
-- Motor: PostgreSQL 16+
-- Base de Datos: sar_db / db_satc
--
-- PRINCIPIOS DE SEGURIDAD (SAR-SEC-001 & SAR-DEV-001):
--   1. AISLAMIENTO TOTAL: Modifica y crea tablas exclusivamente en los esquemas
--      'satc_catalogo' y 'satc_produccion'.
--   2. CERO AFECTACIÓN AL CORE SAR: No altera tablas del esquema 'sar_*'.
--   3. IDEMPOTENCIA PURA: Todos los CREATE usan IF NOT EXISTS y los INSERT usan
--      ON CONFLICT DO NOTHING.
--   4. REVERSIBILIDAD: Script preparado con cláusulas seguras sin riesgo de DROP.
-- =============================================================================

-- =============================================================================
-- SECCIÓN 1: satc_catalogo.tipo_tramite
-- Catálogo maestro de trámites y vigencias por hito (Construcción, Venta, Escrituración)
-- =============================================================================

CREATE TABLE IF NOT EXISTS satc_catalogo.tipo_tramite (
    tipo_tramite_id BIGSERIAL PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(200) NOT NULL,
    aplica_a VARCHAR(30) NOT NULL DEFAULT 'AMBOS', -- 'REGIMEN_MATRIZ', 'VIVIENDA_INDIVIDUAL', 'AMBOS'
    etapa_disparador VARCHAR(30) NOT NULL,          -- 'CONSTRUCCION', 'VENTA', 'ESCRITURACION'
    dias_vigencia INTEGER NOT NULL DEFAULT 0,      -- 0 = Sin caducidad
    es_obligatorio BOOLEAN NOT NULL DEFAULT TRUE,  -- Bloquea escrituración si no está concluido
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE satc_catalogo.tipo_tramite IS 'Catálogo maestro de trámites y derechos municipales en Cancún.';

-- Seed de trámites indispensables
INSERT INTO satc_catalogo.tipo_tramite (codigo, nombre, aplica_a, etapa_disparador, dias_vigencia, es_obligatorio)
VALUES
    ('LICENCIA_CONSTRUCCION_MATRIZ', 'Licencia de Construcción Matriz del Régimen', 'REGIMEN_MATRIZ', 'CONSTRUCCION', 365, TRUE),
    ('CONSTITUCION_REGIMEN', 'Constitución de Régimen en Condominio', 'REGIMEN_MATRIZ', 'CONSTRUCCION', 0, TRUE),
    ('TERMINACION_OBRA_MATRIZ', 'Terminación de Obra Régimen / Macro-Lote', 'REGIMEN_MATRIZ', 'CONSTRUCCION', 0, TRUE),
    ('INDIVIDUALIZACION_CATASTRAL', 'Individualización Catastral por UPE / Asignación de Clave', 'VIVIENDA_INDIVIDUAL', 'VENTA', 0, TRUE),
    ('CEDULA_CATASTRAL_UPE', 'Cédula Catastral Individual por Vivienda / UPE', 'VIVIENDA_INDIVIDUAL', 'VENTA', 365, TRUE),
    ('IMPUESTO_PREDIAL_UPE', 'Impuesto Predial Individualizado (Ejercicio Vigente)', 'VIVIENDA_INDIVIDUAL', 'VENTA', 365, TRUE),
    ('CERTIFICADO_NO_ADEUDO_PREDIAL', 'Certificado de No Adeudo Predial para Notaría', 'VIVIENDA_INDIVIDUAL', 'ESCRITURACION', 30, TRUE),
    ('DERECHOS_AGUA_INTERCONEXION', 'Constancia de No Adeudo de Agua y Drenaje', 'VIVIENDA_INDIVIDUAL', 'ESCRITURACION', 60, TRUE),
    ('FINIQUITO_MUNICIPAL', 'Finiquito de Derechos y Cancelación Fiduciaria', 'AMBOS', 'ESCRITURACION', 0, FALSE)
ON CONFLICT (codigo) DO NOTHING;


-- =============================================================================
-- SECCIÓN 2: satc_catalogo.estado_vivienda
-- Catálogo dedicado a los estados del ciclo de vida físico-comercial de la vivienda
-- =============================================================================

CREATE TABLE IF NOT EXISTS satc_catalogo.estado_vivienda (
    estado_vivienda_id BIGSERIAL PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion VARCHAR(250),
    orden_flujo INTEGER NOT NULL,
    permite_venta BOOLEAN NOT NULL DEFAULT FALSE,
    permite_escrituracion BOOLEAN NOT NULL DEFAULT FALSE,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

COMMENT ON TABLE satc_catalogo.estado_vivienda IS 'Catálogo de estados del ciclo de vida de la vivienda con candados de venta y escrituración.';

INSERT INTO satc_catalogo.estado_vivienda (codigo, nombre, descripcion, orden_flujo, permite_venta, permite_escrituracion)
VALUES
    ('PROYECTADA', 'Proyectada / En Plano', 'UPE registrada en planos sin inicio de edificación física.', 1, FALSE, FALSE),
    ('EN_CONSTRUCCION', 'En Construcción', 'Edificación activa de la manzana o torre.', 2, FALSE, FALSE),
    ('EN_INDIVIDUALIZACION', 'En Individualización', 'Gestión catastral abierta para segregar la UPE del macro-lote.', 3, FALSE, FALSE),
    ('LISTA_PARA_VENTA', 'Lista para Venta', 'Clave catastral individualizada asignada; apta para comercialización.', 4, TRUE, FALSE),
    ('EN_ESCRITURACION', 'En Escrituración', 'Expediente notarial activo; requiere trámite de no adeudo concluido.', 5, TRUE, FALSE),
    ('ESCRITURADA', 'Escriturada', 'Protocolización notarial formalizada y firmada.', 6, TRUE, TRUE),
    ('EN_GARANTIA', 'En Garantía / Post-Venta', 'Obligaciones remanentes y garantías de obra.', 7, FALSE, TRUE),
    ('CONCLUIDA', 'Ciclo Concluido', 'Expediente digital auditado, concluido y comprobado en ERP.', 8, FALSE, TRUE)
ON CONFLICT (codigo) DO NOTHING;


-- =============================================================================
-- SECCIÓN 3: satc_catalogo.estado_tramite
-- Catálogo dedicado a los estados operativos, documentales y financieros del trámite
-- =============================================================================

CREATE TABLE IF NOT EXISTS satc_catalogo.estado_tramite (
    estado_tramite_id BIGSERIAL PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    fase VARCHAR(50) NOT NULL, -- 'PREVENTIVA', 'DOCUMENTAL', 'OPERATIVA', 'AUTOMATIZADA', 'FINANCIERA', 'CIERRE'
    es_bloqueante BOOLEAN NOT NULL DEFAULT TRUE,
    es_terminal BOOLEAN NOT NULL DEFAULT FALSE,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

COMMENT ON TABLE satc_catalogo.estado_tramite IS 'Catálogo de estados del trámite con clasificación de fase y semáforo bloqueante.';

INSERT INTO satc_catalogo.estado_tramite (codigo, nombre, fase, es_bloqueante, es_terminal)
VALUES
    ('NO_INICIADO', 'No Iniciado', 'PREVENTIVA', TRUE, FALSE),
    ('REQUISITOS_PENDIENTES', 'Requisitos Pendientes', 'DOCUMENTAL', TRUE, FALSE),
    ('INGRESADO_MUNICIPIO', 'Ingresado en Municipio', 'OPERATIVA', TRUE, FALSE),
    ('OBSERVADO', 'Observado / Prevenido', 'OPERATIVA', TRUE, FALSE),
    ('ORDEN_COMPRA_ERP', 'Orden de Compra ERP', 'FINANCIERA', TRUE, FALSE),
    ('PAGO_EMITIDO', 'Pago Emitido / Pase de Caja', 'FINANCIERA', TRUE, FALSE),
    ('RECIBO_DESCARGADO', 'Recibo Descargado (Bot A)', 'AUTOMATIZADA', TRUE, FALSE),
    ('FACTURADO', 'Facturado CFDI (Bot C)', 'AUTOMATIZADA', FALSE, FALSE),
    ('COMPROBADO_ERP', 'Comprobado en ERP', 'FINANCIERA', FALSE, FALSE),
    ('CONCLUIDO', 'Trámite Concluido', 'CIERRE', FALSE, TRUE)
ON CONFLICT (codigo) DO NOTHING;


-- =============================================================================
-- SECCIÓN 4: satc_catalogo.regimen_condominio
-- Macro-Lotes que constituyen un Régimen en Condominio con N UPEs autorizadas
-- =============================================================================

CREATE TABLE IF NOT EXISTS satc_catalogo.regimen_condominio (
    regimen_id BIGSERIAL PRIMARY KEY,
    desarrollo_id BIGINT NOT NULL REFERENCES sar_catalogo.desarrollo(desarrollo_id) ON DELETE RESTRICT,
    nombre_regimen VARCHAR(200) NOT NULL,
    sm VARCHAR(50),
    mz VARCHAR(50) NOT NULL,
    lt VARCHAR(50) NOT NULL,
    total_upes INTEGER NOT NULL CHECK (total_upes > 0),
    upes_generadas INTEGER NOT NULL DEFAULT 0,
    licencia_construccion_matriz VARCHAR(100),
    clave_catastral_matriz VARCHAR(100),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

COMMENT ON TABLE satc_catalogo.regimen_condominio IS 'Gobierna los macro-lotes que constituyen un Régimen en Condominio (ej. Aura Nova Playa MZ1 LT1 con 577 UPEs).';

CREATE INDEX IF NOT EXISTS idx_regimen_desarrollo ON satc_catalogo.regimen_condominio (desarrollo_id);
CREATE INDEX IF NOT EXISTS idx_regimen_sm_mz_lt ON satc_catalogo.regimen_condominio (sm, mz, lt);


-- =============================================================================
-- SECCIÓN 5: satc_catalogo.vivienda
-- Entidad física soberana: Lotes individuales o UPEs en condominio
-- Incluye: calle, clave_catastral y descripcion
-- =============================================================================

CREATE TABLE IF NOT EXISTS satc_catalogo.vivienda (
    vivienda_id BIGSERIAL PRIMARY KEY,
    desarrollo_id BIGINT NOT NULL REFERENCES sar_catalogo.desarrollo(desarrollo_id) ON DELETE RESTRICT,
    regimen_id BIGINT REFERENCES satc_catalogo.regimen_condominio(regimen_id) ON DELETE SET NULL,
    tipo_proyecto VARCHAR(30) NOT NULL DEFAULT 'REGIMEN_CONDOMINIO', -- 'FRACCIONAMIENTO', 'REGIMEN_CONDOMINIO'
    sm VARCHAR(50),
    mz VARCHAR(50) NOT NULL,
    lt VARCHAR(50) NOT NULL,
    edificio VARCHAR(50),                                            -- Torre A, Edif 1, etc.
    vivienda VARCHAR(50) NOT NULL,                                   -- Depto 101, Casa 4, etc.
    numero_upe VARCHAR(50),                                          -- Consecutivo UPE-001 a UPE-577
    calle VARCHAR(200),                                              -- Nombre de calle o vialidad
    clave_catastral VARCHAR(100),                                    -- Clave catastral asignada
    cuenta_predial VARCHAR(100),                                     -- Cuenta de impuesto predial
    descripcion TEXT,                                                -- Notas descriptivas / prototipo
    estado_vivienda_id BIGINT NOT NULL REFERENCES satc_catalogo.estado_vivienda(estado_vivienda_id),
    estatus_obra VARCHAR(50) NOT NULL DEFAULT 'EN_CONSTRUCCION',
    fecha_venta DATE,
    fecha_escrituracion DATE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

COMMENT ON TABLE satc_catalogo.vivienda IS 'Catálogo e inventario de viviendas individuales y unidades de propiedad exclusiva (UPEs).';

CREATE INDEX IF NOT EXISTS idx_vivienda_desarrollo ON satc_catalogo.vivienda (desarrollo_id);
CREATE INDEX IF NOT EXISTS idx_vivienda_regimen ON satc_catalogo.vivienda (regimen_id);
CREATE INDEX IF NOT EXISTS idx_vivienda_estado ON satc_catalogo.vivienda (estado_vivienda_id);
CREATE INDEX IF NOT EXISTS idx_vivienda_clave_cat ON satc_catalogo.vivienda (clave_catastral);
CREATE INDEX IF NOT EXISTS idx_vivienda_ubicacion ON satc_catalogo.vivienda (sm, mz, lt, edificio, vivienda);


-- =============================================================================
-- SECCIÓN 6: satc_produccion.tramite_vivienda
-- Instancia viva del trámite por vivienda con trazabilidad documental y ERP
-- =============================================================================

CREATE TABLE IF NOT EXISTS satc_produccion.tramite_vivienda (
    tramite_vivienda_id BIGSERIAL PRIMARY KEY,
    vivienda_id BIGINT REFERENCES satc_catalogo.vivienda(vivienda_id) ON DELETE CASCADE,
    regimen_id BIGINT REFERENCES satc_catalogo.regimen_condominio(regimen_id) ON DELETE CASCADE,
    tipo_tramite_id BIGINT NOT NULL REFERENCES satc_catalogo.tipo_tramite(tipo_tramite_id) ON DELETE RESTRICT,
    estado_tramite_id BIGINT NOT NULL REFERENCES satc_catalogo.estado_tramite(estado_tramite_id) ON DELETE RESTRICT,
    folio_pase_caja VARCHAR(100),
    folio_electronico VARCHAR(100),
    recibo_id BIGINT REFERENCES satc_produccion.recibo_cancun(recibo_id) ON DELETE SET NULL,
    factura_id BIGINT REFERENCES satc_produccion.factura_cancun(factura_id) ON DELETE SET NULL,
    orden_compra_erp VARCHAR(50),
    poliza_comprobacion_erp VARCHAR(50),
    comprobado_erp BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_inicio DATE NOT NULL DEFAULT CURRENT_DATE,
    fecha_conclusion DATE,
    usuario_responsable_id BIGINT REFERENCES sar_seguridad.usuario(usuario_id) ON DELETE SET NULL,
    observaciones TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    CONSTRAINT chk_tramite_sujeto CHECK (vivienda_id IS NOT NULL OR regimen_id IS NOT NULL)
);

COMMENT ON TABLE satc_produccion.tramite_vivienda IS 'Expediente del ciclo de vida de un trámite por vivienda con vinculación a bots y comprobación ERP.';

CREATE INDEX IF NOT EXISTS idx_tramite_vivienda ON satc_produccion.tramite_vivienda (vivienda_id);
CREATE INDEX IF NOT EXISTS idx_tramite_regimen ON satc_produccion.tramite_vivienda (regimen_id);
CREATE INDEX IF NOT EXISTS idx_tramite_tipo ON satc_produccion.tramite_vivienda (tipo_tramite_id);
CREATE INDEX IF NOT EXISTS idx_tramite_estado ON satc_produccion.tramite_vivienda (estado_tramite_id);
CREATE INDEX IF NOT EXISTS idx_tramite_recibo ON satc_produccion.tramite_vivienda (recibo_id);
CREATE INDEX IF NOT EXISTS idx_tramite_factura ON satc_produccion.tramite_vivienda (factura_id);
CREATE INDEX IF NOT EXISTS idx_tramite_oc_erp ON satc_produccion.tramite_vivienda (orden_compra_erp);


-- =============================================================================
-- SECCIÓN 7: satc_produccion.requisito_documento
-- Expediente digital probatorio (planos, cédulas, constancias con hash SHA-256)
-- =============================================================================

CREATE TABLE IF NOT EXISTS satc_produccion.requisito_documento (
    documento_id BIGSERIAL PRIMARY KEY,
    tramite_vivienda_id BIGINT NOT NULL REFERENCES satc_produccion.tramite_vivienda(tramite_vivienda_id) ON DELETE CASCADE,
    tipo_documento VARCHAR(50) NOT NULL, -- 'PLANO', 'ACUSE_INGRESO', 'CEDULA_CATASTRAL', 'CERTIFICADO_NO_ADEUDO', 'OTRO'
    nombre_archivo VARCHAR(255) NOT NULL,
    ruta_archivo VARCHAR(1000) NOT NULL,
    hash_sha256 VARCHAR(64) NOT NULL,
    tamano_bytes BIGINT NOT NULL,
    fecha_emision DATE,
    fecha_vencimiento DATE,
    vigente BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE satc_produccion.requisito_documento IS 'Resguardo digital de evidencias documentales de trámites con validación criptográfica SHA-256.';

CREATE INDEX IF NOT EXISTS idx_req_doc_tramite ON satc_produccion.requisito_documento (tramite_vivienda_id);
CREATE INDEX IF NOT EXISTS idx_req_doc_vigente ON satc_produccion.requisito_documento (vigente, fecha_vencimiento);
