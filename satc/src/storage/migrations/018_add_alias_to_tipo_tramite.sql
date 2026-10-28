-- =============================================================================
-- Migración 018: Agregar columna 'alias' al catálogo satc_catalogo.tipo_tramite
-- Fecha: 2026-10-27
-- Contexto: Facilita identificadores cortos y amigables para vistas y reportes.
-- =============================================================================

ALTER TABLE satc_catalogo.tipo_tramite 
ADD COLUMN IF NOT EXISTS alias VARCHAR(100);

COMMENT ON COLUMN satc_catalogo.tipo_tramite.alias IS 'Nombre corto o mnemotécnico para despliegue en interfaces densas, filtros y reportes.';

-- Actualizar alias iniciales por defecto según el nombre oficial
UPDATE satc_catalogo.tipo_tramite SET alias = 'Licencia de Construcción' WHERE codigo = 'LICENCIA_CONSTRUCCION_MATRIZ' AND (alias IS NULL OR alias = '');
UPDATE satc_catalogo.tipo_tramite SET alias = 'Constitución de Régimen' WHERE codigo = 'CONSTITUCION_REGIMEN' AND (alias IS NULL OR alias = '');
UPDATE satc_catalogo.tipo_tramite SET alias = 'Terminación de Obra' WHERE codigo = 'TERMINACION_OBRA_MATRIZ' AND (alias IS NULL OR alias = '');
UPDATE satc_catalogo.tipo_tramite SET alias = 'Individualización Catastral' WHERE codigo = 'INDIVIDUALIZACION_CATASTRAL' AND (alias IS NULL OR alias = '');
UPDATE satc_catalogo.tipo_tramite SET alias = 'Cédula Catastral' WHERE codigo = 'CEDULA_CATASTRAL_UPE' AND (alias IS NULL OR alias = '');
UPDATE satc_catalogo.tipo_tramite SET alias = 'Impuesto Predial' WHERE codigo = 'IMPUESTO_PREDIAL_UPE' AND (alias IS NULL OR alias = '');
UPDATE satc_catalogo.tipo_tramite SET alias = 'No Adeudo Predial (NAP)' WHERE codigo = 'CERTIFICADO_NO_ADEUDO_PREDIAL' AND (alias IS NULL OR alias = '');
UPDATE satc_catalogo.tipo_tramite SET alias = 'No Adeudo de Agua' WHERE codigo = 'DERECHOS_AGUA_INTERCONEXION' AND (alias IS NULL OR alias = '');
UPDATE satc_catalogo.tipo_tramite SET alias = 'Finiquito Municipal' WHERE codigo = 'FINIQUITO_MUNICIPAL' AND (alias IS NULL OR alias = '');
