-- =============================================================================
-- MIGRACIÓN 015: Incorporación de fecha_alta_folio y fecha_alta_cc en satc_catalogo.vivienda
-- Módulo: SATC (Sistema de Automatización y Control de Trámites Cancún)
-- Versión: 1.0 | Fecha: 2026
-- Motor: PostgreSQL 16+
-- Base de Datos: sar_db / db_satc
--
-- PRINCIPIOS DE PROTECCIÓN ABSOLUTA (SAR-SEC-001 & SAR-DEV-001):
--   1. AISLAMIENTO TOTAL: Modifica exclusivamente el esquema 'satc_catalogo'.
--   2. CERO AFECTACIÓN A SAR: No toca ni altera ninguna tabla 'sar_*'.
--   3. IDEMPOTENCIA Y SEGURIDAD TRANSACCIONAL: Bloques seguros IF NOT EXISTS.
-- =============================================================================

ALTER TABLE satc_catalogo.vivienda 
    ADD COLUMN IF NOT EXISTS fecha_alta_folio DATE,
    ADD COLUMN IF NOT EXISTS fecha_alta_cc DATE;

COMMENT ON COLUMN satc_catalogo.vivienda.fecha_alta_folio IS 'Fecha de alta o expedición del folio electrónico en el RPP';
COMMENT ON COLUMN satc_catalogo.vivienda.fecha_alta_cc IS 'Fecha de alta o expedición de la clave catastral en Catastro Municipal';
