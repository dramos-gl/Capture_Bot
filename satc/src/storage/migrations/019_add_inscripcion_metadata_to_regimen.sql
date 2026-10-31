-- MIGRACIÓN 019: Agregar metadatos notariales y de boleta de inscripción a satc_catalogo.regimen
-- Módulo: SATC (Sistema de Automatización y Control de Trámites Cancún)
-- Versión: 1.0 | Fecha: 2026

DO $$
BEGIN
    RAISE NOTICE 'Iniciando Migración 019: Incorporación de metadatos de Boleta de Inscripción en satc_catalogo.regimen...';

    -- 1. Agregar columnas opcionales a satc_catalogo.regimen
    ALTER TABLE satc_catalogo.regimen
        ADD COLUMN IF NOT EXISTS numero_instrumento VARCHAR(100),
        ADD COLUMN IF NOT EXISTS fecha_liberacion DATE,
        ADD COLUMN IF NOT EXISTS notaria VARCHAR(50),
        ADD COLUMN IF NOT EXISTS notario VARCHAR(200),
        ADD COLUMN IF NOT EXISTS solicitante VARCHAR(200),
        ADD COLUMN IF NOT EXISTS observaciones TEXT;

    -- 2. Crear índice para optimizar búsquedas por número de instrumento / P.A.
    CREATE INDEX IF NOT EXISTS idx_regimen_instrumento 
        ON satc_catalogo.regimen (numero_instrumento);

    -- 3. Documentación en diccionario de datos de PostgreSQL
    COMMENT ON COLUMN satc_catalogo.regimen.numero_instrumento IS 'Número de instrumento notarial o P.A. de constitución de régimen (ej. P.A. 65921).';
    COMMENT ON COLUMN satc_catalogo.regimen.fecha_liberacion IS 'Fecha de liberación o expedición de la boleta de inscripción en el RPP.';
    COMMENT ON COLUMN satc_catalogo.regimen.notaria IS 'Número o clave de la notaría pública que formalizó el régimen (ej. 68).';
    COMMENT ON COLUMN satc_catalogo.regimen.notario IS 'Nombre completo del notario público titular o auxiliar.';
    COMMENT ON COLUMN satc_catalogo.regimen.solicitante IS 'Persona física o moral solicitante de la inscripción ante el RPP.';
    COMMENT ON COLUMN satc_catalogo.regimen.observaciones IS 'Observaciones adicionales, no. de control interno o notas registrales.';

    RAISE NOTICE 'Migración 019 completada exitosamente.';
END $$;

