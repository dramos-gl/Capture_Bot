-- =============================================================================
-- SAR — Actualización de Rutas Físicas de Facturas (Orden ID: 5)
-- =============================================================================
-- Propósito : Actualizar de forma segura e idempotente las rutas físicas en:
--             1. sar_archivo.factura (pdf_path, pdf2_path, xml_path)
--             2. sar_archivo.archivo_pdf (ruta_archivo)
--             Para todas las referencias vinculadas a la orden_id = 5.
--
-- Folio     : 'ORD-20260828-173742-MIG'  --->  'ORD-SUB-20250505'
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Actualización de rutas en sar_archivo.factura (pdf_path, pdf2_path, xml_path)
-- -----------------------------------------------------------------------------
UPDATE sar_archivo.factura f
SET
    pdf_path  = REPLACE(f.pdf_path,  'ORD-20260828-173742-MIG', 'ORD-SUB-20250505'),
    pdf2_path = CASE 
                    WHEN f.pdf2_path IS NOT NULL 
                    THEN REPLACE(f.pdf2_path, 'ORD-20260828-173742-MIG', 'ORD-SUB-20250505') 
                    ELSE f.pdf2_path 
                END,
    xml_path  = CASE 
                    WHEN f.xml_path IS NOT NULL 
                    THEN REPLACE(f.xml_path,  'ORD-20260828-173742-MIG', 'ORD-SUB-20250505') 
                    ELSE f.xml_path 
                END
FROM sar_produccion.referencia r
JOIN sar_produccion.grupo_referencia gr ON r.grupo_id = gr.grupo_id
WHERE f.referencia_id = r.referencia_id
  AND gr.orden_id = 5
  AND (
      f.pdf_path  LIKE '%ORD-20260828-173742-MIG%' OR
      f.pdf2_path LIKE '%ORD-20260828-173742-MIG%' OR
      f.xml_path  LIKE '%ORD-20260828-173742-MIG%'
  );

-- -----------------------------------------------------------------------------
-- 2. Actualización de rutas en sar_archivo.archivo_pdf (si aplica)
-- -----------------------------------------------------------------------------
UPDATE sar_archivo.archivo_pdf ap
SET
    ruta_archivo = REPLACE(ap.ruta_archivo, 'ORD-20260828-173742-MIG', 'ORD-SUB-20250505')
FROM sar_produccion.referencia r
JOIN sar_produccion.grupo_referencia gr ON r.grupo_id = gr.grupo_id
WHERE ap.referencia_id = r.referencia_id
  AND gr.orden_id = 5
  AND ap.ruta_archivo LIKE '%ORD-20260828-173742-MIG%';

-- -----------------------------------------------------------------------------
-- 3. Verificación de muestra posterior
-- -----------------------------------------------------------------------------
SELECT 
    f.factura_id,
    r.referencia_portal,
    f.rfc_emisor,
    f.pdf_path,
    f.xml_path
FROM sar_archivo.factura f
JOIN sar_produccion.referencia r ON f.referencia_id = r.referencia_id
JOIN sar_produccion.grupo_referencia gr ON r.grupo_id = gr.grupo_id
WHERE gr.orden_id = 5
ORDER BY f.factura_id ASC
LIMIT 10;

COMMIT;
