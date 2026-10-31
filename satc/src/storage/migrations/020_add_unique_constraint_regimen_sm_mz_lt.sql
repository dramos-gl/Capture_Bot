-- Migración 020: Restricción de Unicidad para Regímenes Condominio (Macro-Lotes)
-- Objetivo: Prevenir registros duplicados de régimen para un mismo desarrollo con la misma SM, MZ y LT.
-- Esquema: satc_catalogo.regimen

BEGIN;

-- Crear índice único funcional normalizado (UPPER, TRIM y COALESCE para SM vacía o NULL)
CREATE UNIQUE INDEX IF NOT EXISTS uq_regimen_desarrollo_sm_mz_lt 
ON satc_catalogo.regimen (
    desarrollo_id, 
    UPPER(TRIM(COALESCE(sm, ''))), 
    UPPER(TRIM(mz)), 
    UPPER(TRIM(lt))
);

COMMIT;

