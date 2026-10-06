-- =============================================================================
-- MIGRACIÓN 005: Integración de Catálogos (RFC y Desarrollo)
-- Módulo: R2F-Cancún (Recibos y Facturas)
-- Versión: 1.2 | Fecha: 2026
-- Motor: PostgreSQL 16+
-- =============================================================================

-- 1. Agregar columnas a folio_cancun
ALTER TABLE cancunbot_produccion.folio_cancun
    ADD COLUMN IF NOT EXISTS rfc_id INTEGER REFERENCES sar_catalogo.rfc(rfc_id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS desarrollo_id INTEGER REFERENCES sar_catalogo.desarrollo(desarrollo_id) ON DELETE SET NULL;

COMMENT ON COLUMN cancunbot_produccion.folio_cancun.rfc_id IS 'Referencia opcional a la empresa en el catálogo de SAR';
COMMENT ON COLUMN cancunbot_produccion.folio_cancun.desarrollo_id IS 'Referencia opcional al desarrollo en el catálogo de SAR';

-- 2. Agregar columnas a recibo_cancun
ALTER TABLE cancunbot_produccion.recibo_cancun
    ADD COLUMN IF NOT EXISTS rfc_id INTEGER REFERENCES sar_catalogo.rfc(rfc_id) ON DELETE SET NULL;

COMMENT ON COLUMN cancunbot_produccion.recibo_cancun.rfc_id IS 'Referencia oficial verificada al RFC en el catálogo de SAR';

-- 3. Registrar el nuevo estado en el catálogo de estados del sistema
INSERT INTO sar_catalogo.estado_sistema (entidad, codigo, descripcion)
VALUES ('folio_cancun', 'ERROR_RFC_NO_CATALOGADO', 'El RFC oficial del recibo descargado no existe en el catálogo maestro del SAR')
ON CONFLICT DO NOTHING;
