-- =============================================================================
-- MIGRACIÓN 006: Adición de campos SM, MZ y L de catastro
-- Módulo: R2F-Cancún (Recibos y Facturas)
-- Versión: 1.3 | Fecha: 2026
-- Motor: PostgreSQL 16+
-- =============================================================================

-- 1. Agregar columnas a recibo_cancun
ALTER TABLE cancunbot_produccion.recibo_cancun
    ADD COLUMN IF NOT EXISTS sm VARCHAR(50),
    ADD COLUMN IF NOT EXISTS mz VARCHAR(50),
    ADD COLUMN IF NOT EXISTS l VARCHAR(50);

COMMENT ON COLUMN cancunbot_produccion.recibo_cancun.sm IS 'Super manzana catastral extraída de concepto/domicilio';
COMMENT ON COLUMN cancunbot_produccion.recibo_cancun.mz IS 'Manzana catastral extraída de concepto/domicilio';
COMMENT ON COLUMN cancunbot_produccion.recibo_cancun.l IS 'Lote catastral extraído de concepto/domicilio';
