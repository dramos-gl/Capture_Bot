-- =============================================================================
-- MIGRACIÓN 009: Integración del Ecosistema de Esquemas SATC
-- =============================================================================
-- Descripción:
--   Crea y estandariza los 5 esquemas especializados del subsistema SATC
--   (Sistema de Automatización de Trámites Cancún) reflejando la taxonomía del SAR:
--     1. satc_configuracion (Parámetros y localizadores de portales)
--     2. satc_catalogo      (Estados de trámites y catálogos de contribuyentes)
--     3. satc_produccion    (Órdenes, lotes, folios y recibos extraídos)
--     4. satc_archivo       (Gestión documental, expedientes y CFDI facturados)
--     5. satc_auditoria     (Bitácora de eventos RPA, captchas y registros de error)
-- =============================================================================

DO $$
BEGIN
    -- 1. satc_configuracion
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'cancunbot_configuracion') THEN
        ALTER SCHEMA cancunbot_configuracion RENAME TO satc_configuracion;
        COMMENT ON SCHEMA satc_configuracion IS 'Esquema de configuración de SATC (localizadores de portales y parámetros RPA).';
        RAISE NOTICE 'Esquema cancunbot_configuracion renombrado a satc_configuracion.';
    ELSE
        CREATE SCHEMA IF NOT EXISTS satc_configuracion;
        COMMENT ON SCHEMA satc_configuracion IS 'Esquema de configuración de SATC (localizadores de portales y parámetros RPA).';
    END IF;

    -- 2. satc_catalogo
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'cancunbot_catalogo') THEN
        ALTER SCHEMA cancunbot_catalogo RENAME TO satc_catalogo;
        COMMENT ON SCHEMA satc_catalogo IS 'Esquema de catálogos maestros de SATC.';
        RAISE NOTICE 'Esquema cancunbot_catalogo renombrado a satc_catalogo.';
    ELSE
        CREATE SCHEMA IF NOT EXISTS satc_catalogo;
        COMMENT ON SCHEMA satc_catalogo IS 'Esquema de catálogos maestros de SATC.';
    END IF;

    -- 3. satc_produccion
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'cancunbot_produccion') THEN
        ALTER SCHEMA cancunbot_produccion RENAME TO satc_produccion;
        COMMENT ON SCHEMA satc_produccion IS 'Esquema de producción de SATC (órdenes, lotes, folios y recibos).';
        RAISE NOTICE 'Esquema cancunbot_produccion renombrado a satc_produccion.';
    ELSE
        CREATE SCHEMA IF NOT EXISTS satc_produccion;
        COMMENT ON SCHEMA satc_produccion IS 'Esquema de producción de SATC (órdenes, lotes, folios y recibos).';
    END IF;

    -- 4. satc_archivo
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'cancunbot_archivo') THEN
        ALTER SCHEMA cancunbot_archivo RENAME TO satc_archivo;
        COMMENT ON SCHEMA satc_archivo IS 'Esquema de gestión documental y expedientes de SATC.';
        RAISE NOTICE 'Esquema cancunbot_archivo renombrado a satc_archivo.';
    ELSE
        CREATE SCHEMA IF NOT EXISTS satc_archivo;
        COMMENT ON SCHEMA satc_archivo IS 'Esquema de gestión documental y expedientes de SATC.';
    END IF;

    -- 5. satc_auditoria
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'cancunbot_auditoria') THEN
        ALTER SCHEMA cancunbot_auditoria RENAME TO satc_auditoria;
        COMMENT ON SCHEMA satc_auditoria IS 'Esquema de auditoría de eventos RPA, captchas y errores de SATC.';
        RAISE NOTICE 'Esquema cancunbot_auditoria renombrado a satc_auditoria.';
    ELSE
        CREATE SCHEMA IF NOT EXISTS satc_auditoria;
        COMMENT ON SCHEMA satc_auditoria IS 'Esquema de auditoría de eventos RPA, captchas y errores de SATC.';
    END IF;
END $$;
