-- =============================================================================
-- SAR — Script de Migración de Unidad de Red  (Y: → Q:)
-- =============================================================================
-- Propósito : Actualizar la letra de unidad de red en rutas de archivos físicos
--             después de la migración de unidad compartida Y: → Q:
-- Ejemplo   : Y:\BOT\facturas\... → Q:\BOT\facturas\...
--
-- Tablas y campos cubiertos:
--   1. sar_archivo.factura           → pdf_path, pdf2_path
--   2. sar_archivo.archivo_pdf       → ruta_archivo
--   3. cancunbot_produccion.recibo_cancun → pdf_ruta
--
-- Autor     : DBA SAR (generado por Equipo 2 — SAR-AI-PROMPTS-001)
-- Fecha     : 2026-09-11
-- Versión   : 1.3
--
-- NOTA TÉCNICA:
--   Se usa LEFT(campo,2)='Y:' en lugar de ILIKE 'Y:\%' para evitar el bug
--   de escape de PostgreSQL donde \% se interpreta como % literal.
--
-- PRE-REQUISITO — Respaldo de las tablas afectadas:
--   pg_dump -U postgres -d db_sar \
--     -t sar_archivo.factura \
--     -t sar_archivo.archivo_pdf \
--     -t cancunbot_produccion.recibo_cancun \
--     -f backup_pre_mig_Y_a_Q_$(date +%Y%m%d).sql
-- =============================================================================


-- =============================================================================
-- BLOQUE 1: DIAGNÓSTICO PREVIO  (Solo lectura — sin efectos sobre datos)
-- =============================================================================

SELECT
    tabla,
    campo,
    COUNT(*) AS registros_a_actualizar
FROM (
    -- sar_archivo.factura
    SELECT 'sar_archivo.factura'     AS tabla, 'pdf_path'      AS campo FROM sar_archivo.factura     WHERE LEFT(pdf_path,  2) = 'Y:'
    UNION ALL
    SELECT 'sar_archivo.factura',              'pdf2_path'              FROM sar_archivo.factura     WHERE LEFT(pdf2_path, 2) = 'Y:'
    -- sar_archivo.archivo_pdf
    UNION ALL
    SELECT 'sar_archivo.archivo_pdf',          'ruta_archivo'           FROM sar_archivo.archivo_pdf WHERE LEFT(ruta_archivo, 2) = 'Y:'
    -- cancunbot_produccion.recibo_cancun
    UNION ALL
    SELECT 'cancunbot_produccion.recibo_cancun', 'pdf_ruta'             FROM cancunbot_produccion.recibo_cancun WHERE LEFT(pdf_ruta, 2) = 'Y:'
) conteos
GROUP BY tabla, campo
ORDER BY tabla, campo;


-- Vista previa de rutas afectadas por tabla (máx. 10 filas c/u)
SELECT 'factura'    AS origen, factura_id AS id, pdf_path AS ruta FROM sar_archivo.factura         WHERE LEFT(pdf_path,     2) = 'Y:' LIMIT 10;
SELECT 'factura'    AS origen, factura_id AS id, pdf2_path        FROM sar_archivo.factura         WHERE LEFT(pdf2_path,    2) = 'Y:' LIMIT 10;
SELECT 'archivo_pdf' AS origen, archivo_id AS id, ruta_archivo    FROM sar_archivo.archivo_pdf     WHERE LEFT(ruta_archivo, 2) = 'Y:' LIMIT 10;
SELECT 'recibo_cancun' AS origen, recibo_id AS id, pdf_ruta       FROM cancunbot_produccion.recibo_cancun WHERE LEFT(pdf_ruta, 2) = 'Y:' LIMIT 10;


-- =============================================================================
-- BLOQUE 2: ACTUALIZACIÓN EN TRANSACCIÓN EXPLÍCITA
-- =============================================================================
-- IMPORTANTE: Revisar conteos del Bloque 1 antes de ejecutar.

BEGIN;

-- -------------------------------------------------------
-- 2.1  sar_archivo.factura — pdf_path
-- -------------------------------------------------------
UPDATE sar_archivo.factura
SET    pdf_path = 'Q:' || SUBSTRING(pdf_path FROM 3)
WHERE  LEFT(pdf_path, 2) = 'Y:';

-- -------------------------------------------------------
-- 2.2  sar_archivo.factura — pdf2_path
-- -------------------------------------------------------
UPDATE sar_archivo.factura
SET    pdf2_path = 'Q:' || SUBSTRING(pdf2_path FROM 3)
WHERE  LEFT(pdf2_path, 2) = 'Y:';

-- -------------------------------------------------------
-- 2.3  sar_archivo.archivo_pdf — ruta_archivo
-- -------------------------------------------------------
UPDATE sar_archivo.archivo_pdf
SET    ruta_archivo = 'Q:' || SUBSTRING(ruta_archivo FROM 3)
WHERE  LEFT(ruta_archivo, 2) = 'Y:';

-- -------------------------------------------------------
-- 2.4  cancunbot_produccion.recibo_cancun — pdf_ruta
-- -------------------------------------------------------
UPDATE cancunbot_produccion.recibo_cancun
SET    pdf_ruta = 'Q:' || SUBSTRING(pdf_ruta FROM 3)
WHERE  LEFT(pdf_ruta, 2) = 'Y:';


-- =============================================================================
-- BLOQUE 3: VERIFICACIÓN POST-UPDATE  (Ejecutar ANTES del COMMIT)
-- =============================================================================
-- Todas las columnas deben devolver 0 registros remanentes con Y:

SELECT
    tabla,
    campo,
    COUNT(*) AS remanentes_con_Y   -- ← debe ser 0 en TODAS las filas
FROM (
    SELECT 'sar_archivo.factura'               AS tabla, 'pdf_path'      AS campo FROM sar_archivo.factura           WHERE LEFT(pdf_path,     2) = 'Y:'
    UNION ALL
    SELECT 'sar_archivo.factura',                        'pdf2_path'              FROM sar_archivo.factura           WHERE LEFT(pdf2_path,    2) = 'Y:'
    UNION ALL
    SELECT 'sar_archivo.archivo_pdf',                    'ruta_archivo'           FROM sar_archivo.archivo_pdf       WHERE LEFT(ruta_archivo, 2) = 'Y:'
    UNION ALL
    SELECT 'cancunbot_produccion.recibo_cancun',         'pdf_ruta'               FROM cancunbot_produccion.recibo_cancun WHERE LEFT(pdf_ruta, 2) = 'Y:'
) verificacion
GROUP BY tabla, campo
ORDER BY tabla, campo;

-- Muestra de rutas actualizadas (deben iniciar con Q:\)
SELECT factura_id, LEFT(pdf_path, 30) AS pdf_path_nuevo FROM sar_archivo.factura         WHERE LEFT(pdf_path,     2) = 'Q:' LIMIT 5;
SELECT archivo_id, LEFT(ruta_archivo, 30)               FROM sar_archivo.archivo_pdf     WHERE LEFT(ruta_archivo, 2) = 'Q:' LIMIT 5;
SELECT recibo_id,  LEFT(pdf_ruta, 30)                   FROM cancunbot_produccion.recibo_cancun WHERE LEFT(pdf_ruta, 2) = 'Q:' LIMIT 5;


-- =============================================================================
-- Si verificación muestra 0 remanentes en TODAS las filas → COMMIT
-- Si algo no es correcto                                  → ROLLBACK
-- =============================================================================

-- COMMIT;    -- <-- Descomentar para confirmar
-- ROLLBACK;  -- <-- Descomentar para revertir

-- =============================================================================
-- FIN DEL SCRIPT  v1.3
-- =============================================================================
