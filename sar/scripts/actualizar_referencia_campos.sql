-- ===========================================================================
-- Sistema de Administración de Referencias (SAR)
-- Script SQL para agregar columnas 'cantidad' y 'porcentaje' a la tabla referencia
-- ===========================================================================

ALTER TABLE sar_produccion.referencia ADD COLUMN IF NOT EXISTS cantidad INTEGER NOT NULL DEFAULT 1;
ALTER TABLE sar_produccion.referencia ADD COLUMN IF NOT EXISTS porcentaje INTEGER NOT NULL DEFAULT 100;
