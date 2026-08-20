-- ============================================================================
-- SAR — SEED DE PRUEBAS: CONTROL DE INVENTARIO
-- ============================================================================
-- Propósito  : Cambiar a estado FACTURADA las primeras 100 referencias de
--              cada solicitud vinculada a la orden_id = 1.
--              Esto permite realizar pruebas reales del módulo de inventario
--              sin necesidad de ejecutar el bot de facturación (Fase C).
--
-- Contexto   : Todas las referencias están actualmente en estado RECHAZADA.
--              Al promoverlas a FACTURADA se ajustan los siguientes contadores:
--                · grupo_referencia.cantidad_rechazada  → DECREMENTA en N
--                · grupo_referencia.cantidad_facturada  → INCREMENTA en N
--                · solicitud.cantidad_facturada         → INCREMENTA en N
--
-- Alcance    : orden_generacion.orden_id = 1
--              → todos los grupo_referencia de esa orden
--              → todas las solicitudes de cada grupo
--              → primeras 100 referencias por solicitud (ORDER BY consecutivo_grupo ASC)
--
-- Idempotente: Si una referencia ya está en FACTURADA, no se re-procesa.
--
-- Reversión  : Ver BLOQUE 6 al final del script (seed_revertir).
--
-- Ejecutar con: psql -U <usuario> -d <base_de_datos> -f seed_inventario_pruebas.sql
-- ============================================================================


-- ============================================================================
-- BLOQUE 0: DIAGNÓSTICO PREVIO
-- ============================================================================
-- Ejecutar este bloque primero para revisar los datos antes de modificar.
-- Muestra: por solicitud → cuántas referencias existen y cuántas serán afectadas.
-- ============================================================================

SELECT
    s.solicitud_id,
    gr.grupo_id,
    rfc.rfc                                                             AS rfc,
    c.alias                                                             AS concepto_alias,
    d.nombre                                                            AS delegacion,
    COUNT(r.referencia_id)                                              AS total_referencias,
    COUNT(r.referencia_id) FILTER (WHERE es_ref.codigo = 'FACTURADA')  AS ya_facturadas,
    LEAST(COUNT(r.referencia_id) FILTER (WHERE es_ref.codigo != 'FACTURADA'), 100) AS seran_actualizadas
FROM sar_produccion.solicitud s
JOIN sar_produccion.grupo_referencia gr  ON s.grupo_id    = gr.grupo_id
JOIN sar_produccion.orden_generacion og  ON gr.orden_id   = og.orden_id
JOIN sar_produccion.referencia r         ON r.solicitud_id = s.solicitud_id
JOIN sar_catalogo.estado_sistema es_ref  ON r.estado_id   = es_ref.estado_id
JOIN sar_catalogo.rfc rfc                ON gr.rfc_id     = rfc.rfc_id
JOIN sar_catalogo.concepto c             ON gr.concepto_id = c.concepto_id
LEFT JOIN sar_catalogo.delegacion d      ON s.delegacion_id = d.delegacion_id
WHERE og.orden_id = 1
GROUP BY
    s.solicitud_id, gr.grupo_id, rfc.rfc, c.alias, d.nombre
ORDER BY
    gr.grupo_id, s.solicitud_id;


-- ============================================================================
-- BLOQUE 1 → 5: ACTUALIZACIÓN TRANSACCIONAL (atómica e idempotente)
-- ============================================================================

BEGIN;

DO $$
DECLARE
    v_estado_facturada_id   BIGINT;
    v_estado_rechazada_id   BIGINT;
    v_filas_referencia      INTEGER;
    v_filas_solicitud       INTEGER;
    v_filas_grupo_facturada INTEGER;
    v_filas_grupo_rechazada INTEGER;
BEGIN

    -- -----------------------------------------------------------------------
    -- PASO 1: Obtener los estado_id necesarios
    -- -----------------------------------------------------------------------
    SELECT estado_id
      INTO v_estado_facturada_id
      FROM sar_catalogo.estado_sistema
     WHERE entidad = 'referencia'
       AND codigo  = 'FACTURADA'
     LIMIT 1;

    IF v_estado_facturada_id IS NULL THEN
        RAISE EXCEPTION
            '[SAR-SEED] No se encontró estado FACTURADA para entidad=referencia.';
    END IF;

    SELECT estado_id
      INTO v_estado_rechazada_id
      FROM sar_catalogo.estado_sistema
     WHERE entidad = 'referencia'
       AND codigo  = 'RECHAZADA'
     LIMIT 1;

    IF v_estado_rechazada_id IS NULL THEN
        RAISE EXCEPTION
            '[SAR-SEED] No se encontró estado RECHAZADA para entidad=referencia.';
    END IF;

    RAISE NOTICE '[SAR-SEED] estado_id FACTURADA=%  RECHAZADA=%',
        v_estado_facturada_id, v_estado_rechazada_id;

    -- -----------------------------------------------------------------------
    -- PASO 2: Identificar y actualizar las primeras 100 referencias por solicitud
    --         de la orden_id = 1, que estén en estado RECHAZADA.
    --
    -- Estrategia:
    --   CTE candidatas → ROW_NUMBER() PARTITION BY solicitud_id
    --                    ORDER BY consecutivo_grupo ASC (determinístico)
    --   Solo rn <= 100 y estado = RECHAZADA
    --   (Si ya está en FACTURADA, se excluye → idempotencia)
    -- -----------------------------------------------------------------------

    WITH candidatas AS (
        SELECT
            r.referencia_id,
            ROW_NUMBER() OVER (
                PARTITION BY r.solicitud_id
                ORDER BY r.consecutivo_grupo ASC
            ) AS rn
        FROM sar_produccion.referencia r
        JOIN sar_produccion.solicitud s         ON r.solicitud_id = s.solicitud_id
        JOIN sar_produccion.grupo_referencia gr ON s.grupo_id     = gr.grupo_id
        JOIN sar_produccion.orden_generacion og ON gr.orden_id    = og.orden_id
        WHERE og.orden_id  = 1
          AND r.estado_id  = v_estado_rechazada_id   -- Solo RECHAZADAS (excluye FACTURADAS → idempotencia)
    ),
    objetivo AS (
        SELECT referencia_id
        FROM candidatas
        WHERE rn <= 100
    )
    UPDATE sar_produccion.referencia r
       SET estado_id = v_estado_facturada_id
      FROM objetivo o
     WHERE r.referencia_id = o.referencia_id;

    GET DIAGNOSTICS v_filas_referencia = ROW_COUNT;
    RAISE NOTICE '[SAR-SEED] Referencias actualizadas a FACTURADA: %', v_filas_referencia;

    -- -----------------------------------------------------------------------
    -- PASO 3: Recalcular cantidad_facturada en solicitud
    -- -----------------------------------------------------------------------

    UPDATE sar_produccion.solicitud s
       SET cantidad_facturada = sub.total_facturadas
      FROM (
          SELECT
              r.solicitud_id,
              COUNT(*) AS total_facturadas
          FROM sar_produccion.referencia r
          JOIN sar_produccion.solicitud s2        ON r.solicitud_id = s2.solicitud_id
          JOIN sar_produccion.grupo_referencia gr ON s2.grupo_id    = gr.grupo_id
          JOIN sar_produccion.orden_generacion og ON gr.orden_id    = og.orden_id
          WHERE og.orden_id = 1
            AND r.estado_id = v_estado_facturada_id
          GROUP BY r.solicitud_id
      ) sub
     WHERE s.solicitud_id = sub.solicitud_id;

    GET DIAGNOSTICS v_filas_solicitud = ROW_COUNT;
    RAISE NOTICE '[SAR-SEED] Solicitudes con cantidad_facturada actualizada: %', v_filas_solicitud;

    -- -----------------------------------------------------------------------
    -- PASO 4: Recalcular cantidad_facturada en grupo_referencia
    -- -----------------------------------------------------------------------

    UPDATE sar_produccion.grupo_referencia gr
       SET cantidad_facturada = sub.total_facturadas
      FROM (
          SELECT
              r.grupo_id,
              COUNT(*) AS total_facturadas
          FROM sar_produccion.referencia r
          JOIN sar_produccion.grupo_referencia gr2 ON r.grupo_id   = gr2.grupo_id
          JOIN sar_produccion.orden_generacion og  ON gr2.orden_id = og.orden_id
          WHERE og.orden_id = 1
            AND r.estado_id = v_estado_facturada_id
          GROUP BY r.grupo_id
      ) sub
     WHERE gr.grupo_id = sub.grupo_id;

    GET DIAGNOSTICS v_filas_grupo_facturada = ROW_COUNT;
    RAISE NOTICE '[SAR-SEED] Grupos con cantidad_facturada actualizada: %', v_filas_grupo_facturada;

    -- -----------------------------------------------------------------------
    -- PASO 5: Recalcular cantidad_rechazada en grupo_referencia
    --         (las referencias promovidas ya no están RECHAZADAS)
    -- -----------------------------------------------------------------------

    UPDATE sar_produccion.grupo_referencia gr
       SET cantidad_rechazada = sub.total_rechazadas
      FROM (
          SELECT
              r.grupo_id,
              COUNT(*) AS total_rechazadas
          FROM sar_produccion.referencia r
          JOIN sar_produccion.grupo_referencia gr2 ON r.grupo_id   = gr2.grupo_id
          JOIN sar_produccion.orden_generacion og  ON gr2.orden_id = og.orden_id
          WHERE og.orden_id = 1
            AND r.estado_id = v_estado_rechazada_id
          GROUP BY r.grupo_id
      ) sub
     WHERE gr.grupo_id = sub.grupo_id;

    GET DIAGNOSTICS v_filas_grupo_rechazada = ROW_COUNT;
    RAISE NOTICE '[SAR-SEED] Grupos con cantidad_rechazada recalculada: %', v_filas_grupo_rechazada;

    -- -----------------------------------------------------------------------
    -- RESUMEN
    -- -----------------------------------------------------------------------
    RAISE NOTICE '========================================================';
    RAISE NOTICE '[SAR-SEED] RESUMEN DE OPERACIÓN';
    RAISE NOTICE '  Referencias RECHAZADA → FACTURADA : %', v_filas_referencia;
    RAISE NOTICE '  Solicitudes (cantidad_facturada)  : %', v_filas_solicitud;
    RAISE NOTICE '  Grupos (cantidad_facturada)       : %', v_filas_grupo_facturada;
    RAISE NOTICE '  Grupos (cantidad_rechazada)       : %', v_filas_grupo_rechazada;
    RAISE NOTICE '========================================================';

END;
$$;

COMMIT;


-- ============================================================================
-- BLOQUE 6: VERIFICACIÓN POST-EJECUCIÓN
-- ============================================================================
-- Valida que los contadores de referencia, solicitud y grupo sean consistentes.
-- ============================================================================

SELECT
    og.orden_id,
    og.folio                                                             AS folio_orden,
    gr.grupo_id,
    gr.cantidad_facturada                                                AS grupo_cant_facturada,
    gr.cantidad_rechazada                                                AS grupo_cant_rechazada,
    s.solicitud_id,
    rfc.rfc                                                              AS rfc,
    c.alias                                                              AS concepto,
    d.nombre                                                             AS delegacion,
    s.cantidad_solicitada,
    s.cantidad_facturada                                                 AS sol_cant_facturada,
    COUNT(r.referencia_id)                                               AS total_refs,
    COUNT(r.referencia_id) FILTER (WHERE es.codigo = 'FACTURADA')       AS refs_facturadas,
    COUNT(r.referencia_id) FILTER (WHERE es.codigo = 'RECHAZADA')       AS refs_rechazadas,
    COUNT(r.referencia_id) FILTER (WHERE es.codigo NOT IN ('FACTURADA','RECHAZADA')) AS refs_otros_estados
FROM sar_produccion.orden_generacion og
JOIN sar_produccion.grupo_referencia gr  ON og.orden_id    = gr.orden_id
JOIN sar_produccion.solicitud s          ON gr.grupo_id    = s.grupo_id
JOIN sar_produccion.referencia r         ON s.solicitud_id = r.solicitud_id
JOIN sar_catalogo.estado_sistema es      ON r.estado_id    = es.estado_id
JOIN sar_catalogo.rfc rfc                ON gr.rfc_id      = rfc.rfc_id
JOIN sar_catalogo.concepto c             ON gr.concepto_id = c.concepto_id
LEFT JOIN sar_catalogo.delegacion d      ON s.delegacion_id = d.delegacion_id
WHERE og.orden_id = 1
GROUP BY
    og.orden_id, og.folio, gr.grupo_id, gr.cantidad_facturada, gr.cantidad_rechazada,
    s.solicitud_id, rfc.rfc, c.alias, d.nombre,
    s.cantidad_solicitada, s.cantidad_facturada
ORDER BY
    gr.grupo_id, s.solicitud_id;


-- ============================================================================
-- BLOQUE 7: SCRIPT DE REVERSIÓN (ejecutar solo si necesitas deshacer la prueba)
-- ============================================================================
-- Revierte las referencias de FACTURADA → RECHAZADA y recalcula contadores.
-- PRECAUCIÓN: Solo aplica si las referencias fueron modificadas únicamente
--             por este script de prueba y no por el bot real.
-- ============================================================================

/* -- Elimina el bloque /* ... */ para ejecutar la reversión

BEGIN;

DO $$
DECLARE
    v_estado_facturada_id  BIGINT;
    v_estado_rechazada_id  BIGINT;
    v_filas                INTEGER;
BEGIN
    SELECT estado_id INTO v_estado_facturada_id
      FROM sar_catalogo.estado_sistema
     WHERE entidad = 'referencia' AND codigo = 'FACTURADA' LIMIT 1;

    SELECT estado_id INTO v_estado_rechazada_id
      FROM sar_catalogo.estado_sistema
     WHERE entidad = 'referencia' AND codigo = 'RECHAZADA' LIMIT 1;

    -- Revertir estado de referencias
    UPDATE sar_produccion.referencia r
       SET estado_id = v_estado_rechazada_id
      FROM sar_produccion.solicitud s
      JOIN sar_produccion.grupo_referencia gr ON s.grupo_id  = gr.grupo_id
      JOIN sar_produccion.orden_generacion og ON gr.orden_id = og.orden_id
     WHERE r.solicitud_id = s.solicitud_id
       AND og.orden_id    = 1
       AND r.estado_id    = v_estado_facturada_id;

    GET DIAGNOSTICS v_filas = ROW_COUNT;
    RAISE NOTICE '[SAR-REVERT] Referencias revertidas a RECHAZADA: %', v_filas;

    -- Recalcular cantidad_facturada en solicitud → 0 (no quedan FACTURADAS)
    UPDATE sar_produccion.solicitud s
       SET cantidad_facturada = 0
      FROM sar_produccion.grupo_referencia gr
      JOIN sar_produccion.orden_generacion og ON gr.orden_id = og.orden_id
     WHERE s.grupo_id = gr.grupo_id
       AND og.orden_id = 1;

    -- Recalcular cantidad_facturada en grupo → 0
    UPDATE sar_produccion.grupo_referencia gr
       SET cantidad_facturada = 0
      FROM sar_produccion.orden_generacion og
     WHERE gr.orden_id = og.orden_id
       AND og.orden_id = 1;

    -- Recalcular cantidad_rechazada en grupo (recuento real)
    UPDATE sar_produccion.grupo_referencia gr
       SET cantidad_rechazada = sub.total
      FROM (
          SELECT r.grupo_id, COUNT(*) AS total
            FROM sar_produccion.referencia r
            JOIN sar_produccion.grupo_referencia gr2 ON r.grupo_id = gr2.grupo_id
            JOIN sar_produccion.orden_generacion og  ON gr2.orden_id = og.orden_id
           WHERE og.orden_id = 1
             AND r.estado_id = v_estado_rechazada_id
           GROUP BY r.grupo_id
      ) sub
     WHERE gr.grupo_id = sub.grupo_id;

    RAISE NOTICE '[SAR-REVERT] Contadores restaurados correctamente.';
END;
$$;

COMMIT;

*/ -- Fin bloque de reversión

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
