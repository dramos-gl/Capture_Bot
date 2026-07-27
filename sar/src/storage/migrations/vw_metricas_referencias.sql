-- =============================================================================
-- Vista: sar_produccion.vw_metricas_referencias
-- Descripción: Vista de métricas consolidadas para el tablero de analítica.
--              Combina referencias con empresa (RFC), concepto, delegación y
--              orden de generación para permitir agrupaciones y filtros eficientes.
-- =============================================================================

CREATE OR REPLACE VIEW sar_produccion.vw_metricas_referencias AS
SELECT
    r.referencia_id,
    r.grupo_id,
    r.solicitud_id,
    r.importe,
    r.fecha_generacion,
    -- Orden
    gr.orden_id,
    og.folio                    AS folio_orden,
    -- Empresa (RFC) — viene de grupo_referencia
    gr.rfc_id,
    rfc.rfc                     AS rfc_nombre,
    rfc.razon_social            AS rfc_razon_social,
    -- Concepto — viene de grupo_referencia
    gr.concepto_id,
    c.nombre                    AS concepto_nombre,
    -- Delegación — viene de solicitud
    s.delegacion_id,
    d.nombre                    AS delegacion_nombre,
    -- Estado referencia
    es.codigo                   AS estado_codigo,
    es.descripcion              AS estado_descripcion
FROM sar_produccion.referencia r
JOIN sar_produccion.grupo_referencia gr  ON r.grupo_id       = gr.grupo_id
JOIN sar_produccion.orden_generacion og  ON gr.orden_id      = og.orden_id
JOIN sar_produccion.solicitud s          ON r.solicitud_id   = s.solicitud_id
JOIN sar_catalogo.rfc rfc                ON gr.rfc_id        = rfc.rfc_id
JOIN sar_catalogo.concepto c             ON gr.concepto_id   = c.concepto_id
LEFT JOIN sar_catalogo.delegacion d      ON s.delegacion_id  = d.delegacion_id
JOIN sar_catalogo.estado_sistema es      ON r.estado_id      = es.estado_id;
