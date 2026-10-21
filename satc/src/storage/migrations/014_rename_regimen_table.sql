-- =============================================================================
-- MIGRACIÓN 014: Renombrar satc_catalogo.regimen_condominio a satc_catalogo.regimen
-- Módulo: SATC (Sistema de Automatización y Control de Trámites Cancún)
-- Versión: 1.0 | Fecha: 2026
-- Motor: PostgreSQL 16+
-- Base de Datos: sar_db / db_satc
--
-- PRINCIPIOS DE PROTECCIÓN ABSOLUTA (SAR-SEC-001 & SAR-DEV-001):
--   1. AISLAMIENTO TOTAL: Modifica exclusivamente el esquema 'satc_catalogo'.
--   2. CERO AFECTACIÓN A SAR: No altera tablas del esquema 'sar_*'.
--   3. PRESERVACIÓN DE INTEGRIDAD REFERENCIAL: PostgreSQL actualiza automáticamente
--      las llaves foráneas existentes que apuntan a la tabla renombrada.
--   4. IDEMPOTENCIA PURA: Valida la existencia previa antes de renombrar.
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Iniciando Migración 014: Renombrar regimen_condominio a regimen...';

    -- Si existe la tabla con el nombre antiguo, renombrarla
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'satc_catalogo' 
          AND table_name = 'regimen_condominio'
    ) THEN
        ALTER TABLE satc_catalogo.regimen_condominio RENAME TO regimen;
        RAISE NOTICE 'Tabla satc_catalogo.regimen_condominio renombrada a satc_catalogo.regimen exitosamente.';
    ELSE
        RAISE NOTICE 'La tabla satc_catalogo.regimen_condominio ya fue renombrada previamente o no existe.';
    END IF;

    -- Renombrar la secuencia asociada si existe
    IF EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'satc_catalogo' AND c.relname = 'regimen_condominio_regimen_id_seq'
    ) THEN
        ALTER SEQUENCE satc_catalogo.regimen_condominio_regimen_id_seq RENAME TO regimen_regimen_id_seq;
    END IF;

    -- Renombrar los índices asociados para mantener la convención limpia
    IF EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'satc_catalogo' AND c.relname = 'regimen_condominio_pkey'
    ) THEN
        ALTER INDEX satc_catalogo.regimen_condominio_pkey RENAME TO regimen_pkey;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'satc_catalogo' AND c.relname = 'idx_regimen_sm_mz_lt'
    ) THEN
        -- El índice ya posee el prefijo idx_regimen_
        NULL;
    END IF;
END $$;

COMMENT ON TABLE satc_catalogo.regimen IS 'Macro-lotes fiduciarios que constituyen un Régimen en Condominio o Fraccionamiento (SATC).';
