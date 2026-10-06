-- =============================================================================
-- MIGRACIÓN 008: Renombrar Esquema PostgreSQL de cancunbot_produccion a satc_produccion
-- =============================================================================
-- Descripción:
--   Estandariza el esquema de base de datos para alinearlo con el nombre corporativo
--   SATC (Sistema de Automatización de Trámites Cancún).
-- =============================================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'cancunbot_produccion') THEN
        ALTER SCHEMA cancunbot_produccion RENAME TO satc_produccion;
        COMMENT ON SCHEMA satc_produccion IS 'Esquema del subsistema SATC (Sistema de Automatización de Trámites Cancún). Lotes, folios, recibos y facturas.';
        RAISE NOTICE 'Esquema cancunbot_produccion renombrado exitosamente a satc_produccion.';
    ELSE
        CREATE SCHEMA IF NOT EXISTS satc_produccion;
        COMMENT ON SCHEMA satc_produccion IS 'Esquema del subsistema SATC (Sistema de Automatización de Trámites Cancún). Lotes, folios, recibos y facturas.';
        RAISE NOTICE 'Esquema satc_produccion verificado / creado.';
    END IF;
END $$;
