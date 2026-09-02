-- ============================================================================
-- Migración: Incorporación del campo 'alias' a la tabla sar_catalogo.rfc
-- Fecha: 2026-09-02
-- Objetivo: Permitir abreviaciones cortas / mnemotécnicas de las razones sociales
-- Compatibilidad: Retrocompatible (NULLable), no bloqueante en PostgreSQL 11+
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'sar_catalogo' 
          AND table_name = 'rfc' 
          AND column_name = 'alias'
    ) THEN
        ALTER TABLE sar_catalogo.rfc ADD COLUMN alias VARCHAR(100);
        RAISE NOTICE 'Columna alias agregada exitosamente a sar_catalogo.rfc';
    ELSE
        RAISE NOTICE 'La columna alias ya existe en sar_catalogo.rfc';
    END IF;
END $$;
