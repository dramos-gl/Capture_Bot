-- =============================================================================
-- Migration 003: Integración de la Entidad OrdenCancun en R2F CancúnBot
-- Preserva la integridad de los registros existentes vinculándolos a una Orden Histórica Legacy.
-- =============================================================================

-- 1. Crear tabla orden_cancun
CREATE TABLE IF NOT EXISTS cancunbot_produccion.orden_cancun (
    orden_id           BIGSERIAL       PRIMARY KEY,
    folio_orden        VARCHAR(50)     NOT NULL UNIQUE,
    descripcion        TEXT,
    total_lotes        INTEGER         NOT NULL DEFAULT 0,
    total_folios       INTEGER         NOT NULL DEFAULT 0,
    folios_procesados  INTEGER         NOT NULL DEFAULT 0,
    folios_error       INTEGER         NOT NULL DEFAULT 0,
    folios_facturados  INTEGER         NOT NULL DEFAULT 0,
    estado_id          BIGINT          NOT NULL REFERENCES sar_catalogo.estado_sistema(estado_id),
    usuario_id         BIGINT          NOT NULL REFERENCES sar_seguridad.usuario(usuario_id),
    created_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ
);

COMMENT ON TABLE cancunbot_produccion.orden_cancun IS 'Agrupa N lotes de folios para control de generación y procesamiento en CancúnBot';

-- 2. Agregar columna orden_id a la tabla lote_folio (NULLABLE para compatibilidad)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'cancunbot_produccion' 
          AND table_name = 'lote_folio' 
          AND column_name = 'orden_id'
    ) THEN
        ALTER TABLE cancunbot_produccion.lote_folio 
        ADD COLUMN orden_id BIGINT REFERENCES cancunbot_produccion.orden_cancun(orden_id) ON DELETE SET NULL;
    END IF;
END $$;

-- 3. Crear Orden Legacy Histórica para migrar de forma transparente registros previos existentes
INSERT INTO cancunbot_produccion.orden_cancun (
    folio_orden,
    descripcion,
    total_lotes,
    total_folios,
    folios_procesados,
    folios_error,
    folios_facturados,
    estado_id,
    usuario_id
)
SELECT 
    'ORD-CUN-LEGACY',
    'Orden de Migración Histórica para Lotes Previos',
    (SELECT COUNT(*) FROM cancunbot_produccion.lote_folio WHERE orden_id IS NULL),
    COALESCE((SELECT SUM(total_folios) FROM cancunbot_produccion.lote_folio WHERE orden_id IS NULL), 0),
    COALESCE((SELECT SUM(folios_procesados) FROM cancunbot_produccion.lote_folio WHERE orden_id IS NULL), 0),
    COALESCE((SELECT SUM(folios_error) FROM cancunbot_produccion.lote_folio WHERE orden_id IS NULL), 0),
    COALESCE((SELECT SUM(folios_facturados) FROM cancunbot_produccion.lote_folio WHERE orden_id IS NULL), 0),
    (SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad = 'lote_folio' AND codigo = 'COMPLETADO' LIMIT 1),
    1 -- Usuario Administrador por defecto
WHERE NOT EXISTS (
    SELECT 1 FROM cancunbot_produccion.orden_cancun WHERE folio_orden = 'ORD-CUN-LEGACY'
);

-- 4. Vincular retroactivamente todos los lotes existentes que no tengan orden asignada
UPDATE cancunbot_produccion.lote_folio
SET orden_id = (SELECT orden_id FROM cancunbot_produccion.orden_cancun WHERE folio_orden = 'ORD-CUN-LEGACY')
WHERE orden_id IS NULL;
