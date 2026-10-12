-- =============================================================================
-- SAR — Actualización de Rutas Físicas de Facturas (Orden Cancelación ID: 6)
-- =============================================================================
-- Propósito : Actualizar de forma segura e idempotente las rutas físicas en:
--             1. sar_archivo.factura (pdf_path, pdf2_path, xml_path)
--             2. sar_archivo.archivo_pdf (ruta_archivo)
--             Para todas las referencias vinculadas a la orden_id = 6.
--
-- Cambio    : 'ORD-CANCEL-2026'  --->  'ORD-CLX-AV-2026'
--
-- Ejemplo   :
--   Antes  : Q:\BOT\facturas\2026\ORD-CANCEL-2026\CIN010904D31\CXLAVISO\...
--   Después: Q:\BOT\facturas\2026\ORD-CLX-AV-2026\CIN010904D31\CXLAVISO\...
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- PASO 1: Diagnóstico previo (Filas afectadas antes del cambio)
-- -----------------------------------------------------------------------------
DO $$
DECLARE
    v_total_facturas INT;
    v_total_archivos_pdf INT;
BEGIN
    SELECT COUNT(*) INTO v_total_facturas
    FROM sar_archivo.factura f
    JOIN sar_produccion.referencia r ON f.referencia_id = r.referencia_id
    JOIN sar_produccion.grupo_referencia gr ON r.grupo_id = gr.grupo_id
    WHERE gr.orden_id = 6
      AND (f.pdf_path LIKE '%ORD-CANCEL-2026%' OR f.pdf2_path LIKE '%ORD-CANCEL-2026%' OR f.xml_path LIKE '%ORD-CANCEL-2026%');

    SELECT COUNT(*) INTO v_total_archivos_pdf
    FROM sar_archivo.archivo_pdf ap
    JOIN sar_produccion.referencia r ON ap.referencia_id = r.referencia_id
    JOIN sar_produccion.grupo_referencia gr ON r.grupo_id = gr.grupo_id
    WHERE gr.orden_id = 6
      AND ap.ruta_archivo LIKE '%ORD-CANCEL-2026%';

    RAISE NOTICE 'Registros a actualizar para orden_id 6: Facturas = %, Archivos PDF = %', v_total_facturas, v_total_archivos_pdf;
END $$;

-- -----------------------------------------------------------------------------
-- PASO 2: Actualización de rutas en sar_archivo.factura
-- -----------------------------------------------------------------------------
UPDATE sar_archivo.factura f
SET
    pdf_path  = REPLACE(f.pdf_path,  'ORD-CANCEL-2026', 'ORD-CLX-AV-2026'),
    pdf2_path = CASE 
                    WHEN f.pdf2_path IS NOT NULL 
                    THEN REPLACE(f.pdf2_path, 'ORD-CANCEL-2026', 'ORD-CLX-AV-2026') 
                    ELSE f.pdf2_path 
                END,
    xml_path  = CASE 
                    WHEN f.xml_path IS NOT NULL 
                    THEN REPLACE(f.xml_path,  'ORD-CANCEL-2026', 'ORD-CLX-AV-2026') 
                    ELSE f.xml_path 
                END
FROM sar_produccion.referencia r
JOIN sar_produccion.grupo_referencia gr ON r.grupo_id = gr.grupo_id
WHERE f.referencia_id = r.referencia_id
  AND gr.orden_id = 6
  AND (
      f.pdf_path  LIKE '%ORD-CANCEL-2026%' OR
      f.pdf2_path LIKE '%ORD-CANCEL-2026%' OR
      f.xml_path  LIKE '%ORD-CANCEL-2026%'
  );

-- -----------------------------------------------------------------------------
-- PASO 3: Actualización de rutas en sar_archivo.archivo_pdf (si aplica)
-- -----------------------------------------------------------------------------
UPDATE sar_archivo.archivo_pdf ap
SET
    ruta_archivo = REPLACE(ap.ruta_archivo, 'ORD-CANCEL-2026', 'ORD-CLX-AV-2026')
FROM sar_produccion.referencia r
JOIN sar_produccion.grupo_referencia gr ON r.grupo_id = gr.grupo_id
WHERE ap.referencia_id = r.referencia_id
  AND gr.orden_id = 6
  AND ap.ruta_archivo LIKE '%ORD-CANCEL-2026%';

-- -----------------------------------------------------------------------------
-- PASO 4: Verificación posterior (Muestra de registros actualizados)
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
WHERE gr.orden_id = 6
ORDER BY f.factura_id ASC
LIMIT 10;

COMMIT;
