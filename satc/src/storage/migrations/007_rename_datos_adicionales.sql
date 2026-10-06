-- =============================================================================
-- MIGRACIÓN 007: Renombrar datos_adicionales a detalle_concepto en recibo_cancun
-- Módulo: R2F-Cancún
-- Versión: 1.0 | Fecha: 2026
-- Motor: PostgreSQL 16+
--
-- REGLAS DE SEGURIDAD:
--   1. Renombra la columna datos_adicionales a detalle_concepto de forma segura.
--   2. Ejecutar conectado a la base de datos: sar_db
-- =============================================================================

ALTER TABLE cancunbot_produccion.recibo_cancun 
    RENAME COLUMN datos_adicionales TO detalle_concepto;

COMMENT ON COLUMN cancunbot_produccion.recibo_cancun.detalle_concepto 
    IS 'JSONB que contiene el texto completo de DETALLE CONCEPTO DE COBRO y otros metadatos auxiliares del recibo.';
