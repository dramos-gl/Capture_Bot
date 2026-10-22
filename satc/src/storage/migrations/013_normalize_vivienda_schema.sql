-- =============================================================================
-- MIGRACIÓN 013: Normalización Soberana de la Entidad Vivienda (SATC)
-- Módulo: SATC (Sistema de Automatización y Control de Trámites Cancún)
-- Versión: 1.0 | Fecha: 2026
-- Motor: PostgreSQL 16+
-- Base de Datos: sar_db / db_satc
--
-- PRINCIPIOS DE PROTECCIÓN ABSOLUTA (SAR-SEC-001 & SAR-DEV-001):
--   1. AISLAMIENTO TOTAL: Modifica exclusivamente el esquema 'satc_catalogo'.
--   2. CERO AFECTACIÓN A SAR: No toca ni altera ninguna tabla 'sar_*'.
--   3. PRESERVACIÓN DE DATOS EXISTENTES: Migra los campos 'vivienda' y 'numero_upe'
--      hacia 'interior' y 'numero_oficial' antes de retirar columnas redundantes.
--   4. IDEMPOTENCIA Y SEGURIDAD TRANSACCIONAL: Emplea bloques seguros condicionales.
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Iniciando Migración 013: Normalización de satc_catalogo.vivienda...';
END $$;

-- 1. Agregar nuevas columnas si no existen
ALTER TABLE satc_catalogo.vivienda 
    ADD COLUMN IF NOT EXISTS numero_oficial VARCHAR(50),
    ADD COLUMN IF NOT EXISTS interior VARCHAR(50),
    ADD COLUMN IF NOT EXISTS nivel VARCHAR(30),
    ADD COLUMN IF NOT EXISTS destino VARCHAR(30) DEFAULT 'HABITACIONAL',
    ADD COLUMN IF NOT EXISTS espacio VARCHAR(30) DEFAULT 'VIVIENDA',
    ADD COLUMN IF NOT EXISTS folio_electronico VARCHAR(100),
    ADD COLUMN IF NOT EXISTS padron VARCHAR(100);

-- 2. Migrar datos existentes de forma segura hacia los nuevos campos
DO $$
BEGIN
    -- Si existe la columna 'vivienda', mapearla a 'interior' en registros donde interior sea NULL
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'satc_catalogo' 
          AND table_name = 'vivienda' 
          AND column_name = 'vivienda'
    ) THEN
        UPDATE satc_catalogo.vivienda
        SET interior = COALESCE(interior, vivienda, 'SIN_NUMERO')
        WHERE interior IS NULL;
    ELSE
        UPDATE satc_catalogo.vivienda
        SET interior = 'SIN_NUMERO'
        WHERE interior IS NULL;
    END IF;

    -- Si existe la columna 'numero_upe', respaldarla en numero_oficial si este estuviera vacío
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'satc_catalogo' 
          AND table_name = 'vivienda' 
          AND column_name = 'numero_upe'
    ) THEN
        UPDATE satc_catalogo.vivienda
        SET numero_oficial = COALESCE(numero_oficial, numero_upe)
        WHERE numero_oficial IS NULL;
    END IF;

    -- Si existe la columna 'cuenta_predial', respaldarla en 'padron'
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'satc_catalogo' 
          AND table_name = 'vivienda' 
          AND column_name = 'cuenta_predial'
    ) THEN
        UPDATE satc_catalogo.vivienda
        SET padron = COALESCE(padron, cuenta_predial)
        WHERE padron IS NULL;
    END IF;

    -- Normalizar coherencia de dominio: Destino = SERVICIO debe ser espacio = AREAS_COMUNES
    UPDATE satc_catalogo.vivienda
    SET espacio = 'AREAS_COMUNES'
    WHERE UPPER(TRIM(destino)) = 'SERVICIO' 
      AND (espacio IS NULL OR UPPER(TRIM(espacio)) = 'VIVIENDA');
END $$;

-- Asegurar que interior no sea nulo tras la migración
ALTER TABLE satc_catalogo.vivienda 
    ALTER COLUMN interior SET NOT NULL,
    ALTER COLUMN destino SET NOT NULL,
    ALTER COLUMN espacio SET NOT NULL;

-- 3. Retirar constraints o índices antiguos que dependan de columnas redundantes
DROP INDEX IF EXISTS satc_catalogo.idx_vivienda_desarrollo;
DROP INDEX IF EXISTS satc_catalogo.idx_vivienda_ubicacion;

-- 4. Retirar columnas redundantes identificadas (violación de 3FN respecto a regimen_condominio)
DO $$
BEGIN
    -- Retirar foreign key a desarrollo si existe en vivienda
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_schema = 'satc_catalogo' 
          AND table_name = 'vivienda' 
          AND constraint_name = 'vivienda_desarrollo_id_fkey'
    ) THEN
        ALTER TABLE satc_catalogo.vivienda DROP CONSTRAINT vivienda_desarrollo_id_fkey;
    END IF;
END $$;

ALTER TABLE satc_catalogo.vivienda 
    DROP COLUMN IF EXISTS desarrollo_id,
    DROP COLUMN IF EXISTS sm,
    DROP COLUMN IF EXISTS mz,
    DROP COLUMN IF EXISTS lt,
    DROP COLUMN IF EXISTS tipo_proyecto,
    DROP COLUMN IF EXISTS vivienda,
    DROP COLUMN IF EXISTS numero_upe,
    DROP COLUMN IF EXISTS cuenta_predial,
    DROP COLUMN IF EXISTS estatus_obra,
    DROP COLUMN IF EXISTS fecha_venta;

-- 5. Agregar restricciones de dominio seguras
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_schema = 'satc_catalogo' 
          AND table_name = 'vivienda' 
          AND constraint_name = 'chk_vivienda_destino'
    ) THEN
        ALTER TABLE satc_catalogo.vivienda 
            ADD CONSTRAINT chk_vivienda_destino 
            CHECK (destino IN ('HABITACIONAL', 'SERVICIO', 'COMERCIAL', 'MIXTO'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_schema = 'satc_catalogo' 
          AND table_name = 'vivienda' 
          AND constraint_name = 'chk_vivienda_espacio'
    ) THEN
        ALTER TABLE satc_catalogo.vivienda 
            ADD CONSTRAINT chk_vivienda_espacio 
            CHECK (espacio IN ('VIVIENDA', 'AREAS_COMUNES', 'ESTACIONAMIENTO', 'BODEGA'));
    END IF;
END $$;

-- 6. Crear índices de rendimiento para búsquedas y conciliación catastral/registral
CREATE INDEX IF NOT EXISTS idx_vivienda_regimen ON satc_catalogo.vivienda(regimen_id);
CREATE INDEX IF NOT EXISTS idx_vivienda_clave_cat ON satc_catalogo.vivienda(clave_catastral);
CREATE INDEX IF NOT EXISTS idx_vivienda_folio_elec ON satc_catalogo.vivienda(folio_electronico);
CREATE INDEX IF NOT EXISTS idx_vivienda_padron ON satc_catalogo.vivienda(padron);
CREATE INDEX IF NOT EXISTS idx_vivienda_interior ON satc_catalogo.vivienda(regimen_id, edificio, interior);

COMMENT ON TABLE satc_catalogo.vivienda IS 'Catálogo normalizado de unidades privativas y espacios bajo Régimen de Condominio (SATC).';
