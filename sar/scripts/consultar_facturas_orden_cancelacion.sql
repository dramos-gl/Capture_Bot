-- =============================================================================
-- SAR — Consulta de Facturas para Orden de Cancelación de Avisos
-- =============================================================================
-- Propósito : Consultar y auditar todos los registros en sar_archivo.factura
--             asociados a la orden de cancelación (por ID de orden o por tipo).
-- =============================================================================

-- Opción 1: Filtrado exacto por orden_id = 6
SELECT 
    og.orden_id,
    og.folio               AS folio_orden,
    og.tipo_orden,
    r.referencia_portal,
    f.factura_id,
    f.uuid,
    f.rfc_emisor,
    f.fecha_factura,
    f.pdf_path,
    f.pdf2_path,
    f.xml_path,
    f.estado               AS estado_factura,
    f.delegacion
FROM sar_archivo.factura f
JOIN sar_produccion.referencia r          ON f.referencia_id = r.referencia_id
JOIN sar_produccion.grupo_referencia gr   ON r.grupo_id = gr.grupo_id
JOIN sar_produccion.orden_generacion og   ON gr.orden_id = og.orden_id
WHERE og.orden_id = 6
ORDER BY f.factura_id ASC;


-- =============================================================================
-- Opción 2: Filtrado dinámico por tipo_orden = 'CANCELACION' o prefijo de folio
-- (Útil para consultar cualquier orden de cancelación independientemente de su ID)
-- =============================================================================
SELECT 
    og.orden_id,
    og.folio               AS folio_orden,
    og.tipo_orden,
    r.referencia_portal,
    f.factura_id,
    f.uuid,
    f.rfc_emisor,
    f.fecha_factura,
    f.pdf_path,
    f.xml_path,
    f.estado               AS estado_factura
FROM sar_archivo.factura f
JOIN sar_produccion.referencia r          ON f.referencia_id = r.referencia_id
JOIN sar_produccion.grupo_referencia gr   ON r.grupo_id = gr.grupo_id
JOIN sar_produccion.orden_generacion og   ON gr.orden_id = og.orden_id
WHERE og.tipo_orden = 'CANCELACION'
   OR og.folio LIKE 'ORD-CLX-AV-%'
   OR og.folio LIKE 'ORD-CANCEL-%'
ORDER BY og.orden_id ASC, f.factura_id ASC;


-- =============================================================================
-- Resumen / Conteo de registros asociados a la Orden de Cancelación
-- =============================================================================
SELECT 
    og.orden_id,
    og.folio               AS folio_orden,
    COUNT(f.factura_id)    AS total_facturas,
    COUNT(f.pdf_path)      AS facturas_con_pdf,
    COUNT(f.xml_path)      AS facturas_con_xml
FROM sar_produccion.orden_generacion og
JOIN sar_produccion.grupo_referencia gr   ON og.orden_id = gr.orden_id
JOIN sar_produccion.referencia r          ON gr.grupo_id = r.grupo_id
JOIN sar_archivo.factura f                ON r.referencia_id = f.referencia_id
WHERE og.orden_id = 6
   OR og.tipo_orden = 'CANCELACION'
GROUP BY og.orden_id, og.folio;
