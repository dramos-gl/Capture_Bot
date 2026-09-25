-- ===========================================================================
-- MIGRACIÓN SEGURA: Normalización de 'no_oficial' en sar_archivo.ubicacion
-- Objetivo: Agregar columna no_oficial a sar_archivo.ubicacion, migrar datos
--           desde lote_id_erp y crear índice de búsqueda optimizado,
--           preservando 'lote_id_erp' intacto para compatibilidad 100%.
-- ===========================================================================

BEGIN;

-- 1. Agregar la columna no_oficial si no existe
ALTER TABLE sar_archivo.ubicacion 
    ADD COLUMN IF NOT EXISTS no_oficial VARCHAR(100);

-- 2. Poblar no_oficial con los datos existentes en lote_id_erp
UPDATE sar_archivo.ubicacion 
SET no_oficial = lote_id_erp 
WHERE no_oficial IS NULL AND lote_id_erp IS NOT NULL;

-- 3. Crear índice para búsquedas rápidas por no_oficial
CREATE INDEX IF NOT EXISTS idx_ubi_no_oficial 
    ON sar_archivo.ubicacion (UPPER(TRIM(no_oficial)));

COMMIT;
