-- =============================================================================
-- MIGRACIÓN 011: Vía Paralela de Gobernanza (orden_tramite & solicitud_tramite)
-- Módulo: SATC (Sistema de Automatización y Control de Trámites Cancún)
-- Versión: 1.0 | Fecha: 2026
-- Motor: PostgreSQL 16+
-- Base de Datos: sar_db / db_satc
--
-- PRINCIPIOS DE SEGURIDAD (SAR-SEC-001 & SAR-DEV-001):
--   1. NO-REGRESIÓN: NO modifica, elimina ni renombra 'orden_cancun', 'lote_folio'
--      ni 'folio_cancun'. La Vía A permanece 100% operativa.
--   2. CONEXIÓN PARALELA: Crea 'orden_tramite' y 'solicitud_tramite' en 'satc_produccion'.
--   3. VINCULACIÓN SEGURA: Añade 'solicitud_tramite_id' a 'tramite_vivienda'
--      mediante ADD COLUMN IF NOT EXISTS.
--   4. IDEMPOTENCIA TOTAL: Todos los objetos usan IF NOT EXISTS.
-- =============================================================================

-- =============================================================================
-- SECCIÓN 1: satc_produccion.orden_tramite
-- Equivalente evolucionado de orden_cancun (agrupador macro por Desarrollo/Régimen)
-- =============================================================================

CREATE TABLE IF NOT EXISTS satc_produccion.orden_tramite (
    orden_tramite_id BIGSERIAL PRIMARY KEY,
    folio_orden VARCHAR(50) UNIQUE NOT NULL,
    desarrollo_id BIGINT NOT NULL REFERENCES sar_catalogo.desarrollo(desarrollo_id) ON DELETE RESTRICT,
    regimen_id BIGINT REFERENCES satc_catalogo.regimen_condominio(regimen_id) ON DELETE SET NULL,
    descripcion TEXT,
    total_solicitudes INTEGER NOT NULL DEFAULT 0,
    total_viviendas INTEGER NOT NULL DEFAULT 0,
    total_concluidos INTEGER NOT NULL DEFAULT 0,
    total_comprobados_erp INTEGER NOT NULL DEFAULT 0,
    estado_id BIGINT NOT NULL REFERENCES satc_catalogo.estado_tramite(estado_tramite_id),
    usuario_id BIGINT NOT NULL REFERENCES sar_seguridad.usuario(usuario_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

COMMENT ON TABLE satc_produccion.orden_tramite IS 'Macro-orden ejecutiva de trámites para gobernanza de viviendas y regímenes.';

CREATE INDEX IF NOT EXISTS idx_orden_trm_desarrollo ON satc_produccion.orden_tramite (desarrollo_id);
CREATE INDEX IF NOT EXISTS idx_orden_trm_regimen ON satc_produccion.orden_tramite (regimen_id);
CREATE INDEX IF NOT EXISTS idx_orden_trm_estado ON satc_produccion.orden_tramite (estado_id);


-- =============================================================================
-- SECCIÓN 2: satc_produccion.solicitud_tramite
-- Equivalente evolucionado de lote_folio (paquete radicado ante el municipio)
-- =============================================================================

CREATE TABLE IF NOT EXISTS satc_produccion.solicitud_tramite (
    solicitud_tramite_id BIGSERIAL PRIMARY KEY,
    orden_tramite_id BIGINT NOT NULL REFERENCES satc_produccion.orden_tramite(orden_tramite_id) ON DELETE CASCADE,
    folio_solicitud VARCHAR(50) UNIQUE NOT NULL,
    tipo_tramite_id BIGINT NOT NULL REFERENCES satc_catalogo.tipo_tramite(tipo_tramite_id) ON DELETE RESTRICT,
    expediente_municipal VARCHAR(100),
    fecha_ingreso_municipio DATE,
    total_viviendas INTEGER NOT NULL DEFAULT 0,
    viviendas_procesadas INTEGER NOT NULL DEFAULT 0,
    viviendas_facturadas INTEGER NOT NULL DEFAULT 0,
    viviendas_concluidas INTEGER NOT NULL DEFAULT 0,
    archivo_origen VARCHAR(500),
    estado_id BIGINT NOT NULL REFERENCES satc_catalogo.estado_tramite(estado_tramite_id),
    usuario_id BIGINT NOT NULL REFERENCES sar_seguridad.usuario(usuario_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

COMMENT ON TABLE satc_produccion.solicitud_tramite IS 'Paquete o lote de solicitud radicado ante Catastro o Tesorería municipal.';

CREATE INDEX IF NOT EXISTS idx_sol_trm_orden ON satc_produccion.solicitud_tramite (orden_tramite_id);
CREATE INDEX IF NOT EXISTS idx_sol_trm_tipo ON satc_produccion.solicitud_tramite (tipo_tramite_id);
CREATE INDEX IF NOT EXISTS idx_sol_trm_estado ON satc_produccion.solicitud_tramite (estado_id);


-- =============================================================================
-- SECCIÓN 3: Vincular tramite_vivienda con solicitud_tramite (Opcional, Seguro)
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'satc_produccion' 
          AND table_name = 'tramite_vivienda' 
          AND column_name = 'solicitud_tramite_id'
    ) THEN
        ALTER TABLE satc_produccion.tramite_vivienda 
            ADD COLUMN solicitud_tramite_id BIGINT 
            REFERENCES satc_produccion.solicitud_tramite(solicitud_tramite_id) ON DELETE SET NULL;
            
        CREATE INDEX idx_tramite_solicitud ON satc_produccion.tramite_vivienda (solicitud_tramite_id);
    END IF;
END $$;
