-- =============================================================================
-- MIGRACIÓN 017: Creación de la Bitácora de Historial de Estados de Vivienda
-- Esquema: satc_catalogo | Motor: PostgreSQL 16+
-- Base de Datos: db_sar / db_satc
--
-- PRINCIPIOS DE PROTECCIÓN ABSOLUTA (SAR-SEC-001 & SAR-DEV-001):
--   1. AISLAMIENTO TOTAL: Modifica exclusivamente el esquema 'satc_catalogo'.
--   2. CERO AFECTACIÓN A SAR: No modifica ni altera ninguna tabla 'sar_*'.
--   3. AUDITORÍA SOBERANA: Registra vivienda_id, estado_anterior, estado_nuevo, usuario y motivo.
--   4. IDEMPOTENCIA: Uso estricto de IF NOT EXISTS y asignación de permisos.
-- =============================================================================

CREATE TABLE IF NOT EXISTS satc_catalogo.vivienda_historial_estado (
    historial_id BIGSERIAL PRIMARY KEY,
    vivienda_id BIGINT NOT NULL REFERENCES satc_catalogo.vivienda(vivienda_id) ON DELETE CASCADE,
    estado_anterior_id BIGINT NULL REFERENCES satc_catalogo.estado_vivienda(estado_vivienda_id) ON DELETE RESTRICT,
    estado_nuevo_id BIGINT NOT NULL REFERENCES satc_catalogo.estado_vivienda(estado_vivienda_id) ON DELETE RESTRICT,
    usuario_id BIGINT NULL REFERENCES sar_seguridad.usuario(usuario_id) ON DELETE SET NULL,
    sesion_id BIGINT NULL,
    origen_cambio VARCHAR(50) NOT NULL DEFAULT 'MANUAL', -- 'CARGA_INICIAL', 'VINCULAR_RPP', 'VINCULAR_CATASTRO', 'MANUAL', 'API'
    motivo VARCHAR(255) NULL,
    metadata_adicional JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices de consulta rápida para trazabilidad y auditoría
CREATE INDEX IF NOT EXISTS idx_vivienda_hist_vivienda_id ON satc_catalogo.vivienda_historial_estado(vivienda_id);
CREATE INDEX IF NOT EXISTS idx_vivienda_hist_usuario_id ON satc_catalogo.vivienda_historial_estado(usuario_id);
CREATE INDEX IF NOT EXISTS idx_vivienda_hist_created_at ON satc_catalogo.vivienda_historial_estado(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_vivienda_hist_origen ON satc_catalogo.vivienda_historial_estado(origen_cambio);

COMMENT ON TABLE satc_catalogo.vivienda_historial_estado IS 'Bitácora histórica inmutable de cambios de estado del ciclo de vida físico-jurídico de la vivienda.';
COMMENT ON COLUMN satc_catalogo.vivienda_historial_estado.origen_cambio IS 'Identificador del proceso o disparador que ocasionó el cambio de estado.';

-- Permisos de Operación para el usuario de aplicación
GRANT SELECT, INSERT, UPDATE, DELETE ON satc_catalogo.vivienda_historial_estado TO sar_app_user;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE satc_catalogo.vivienda_historial_estado_historial_id_seq TO sar_app_user;

-- =============================================================================
-- DISPARADOR AUTOMÁTICO VÍA TRIGGER (PostgreSQL)
-- Actúa como salvaguarda absoluta en base de datos para registrar transiciones
-- de estado manuales o externas donde no se haya insertado el historial en Python.
-- =============================================================================

CREATE OR REPLACE FUNCTION satc_catalogo.trg_vivienda_cambio_estado()
RETURNS TRIGGER AS $$
DECLARE
    v_usuario_id BIGINT;
    v_sesion_id BIGINT;
    v_origen VARCHAR(50);
    v_motivo VARCHAR(255);
    v_already_logged BOOLEAN;
BEGIN
    -- Evaluar exclusivamente si hubo una transición real en estado_vivienda_id
    IF (OLD.estado_vivienda_id IS DISTINCT FROM NEW.estado_vivienda_id) THEN
        
        -- Verificar si en la misma transacción ya se insertó un historial para esta vivienda y este estado nuevo
        SELECT EXISTS(
            SELECT 1 
            FROM satc_catalogo.vivienda_historial_estado
            WHERE vivienda_id = NEW.vivienda_id
              AND estado_nuevo_id = NEW.estado_vivienda_id
        ) INTO v_already_logged;

        IF NOT v_already_logged THEN
            -- Leer variables de sesión contextuales (si fueron seteadas por la app)
            BEGIN
                v_usuario_id := NULLIF(current_setting('app.current_user_id', true), '')::BIGINT;
            EXCEPTION WHEN OTHERS THEN
                v_usuario_id := NULL;
            END;

            BEGIN
                v_sesion_id := NULLIF(current_setting('app.current_sesion_id', true), '')::BIGINT;
            EXCEPTION WHEN OTHERS THEN
                v_sesion_id := NULL;
            END;

            v_origen := COALESCE(NULLIF(current_setting('app.origen_cambio', true), ''), 'TRIGGER_BD');
            v_motivo := COALESCE(NULLIF(current_setting('app.motivo_cambio', true), ''), 'Transición de estado detectada por motor PostgreSQL');

            INSERT INTO satc_catalogo.vivienda_historial_estado (
                vivienda_id,
                estado_anterior_id,
                estado_nuevo_id,
                usuario_id,
                sesion_id,
                origen_cambio,
                motivo,
                metadata_adicional,
                created_at
            ) VALUES (
                NEW.vivienda_id,
                OLD.estado_vivienda_id,
                NEW.estado_vivienda_id,
                v_usuario_id,
                v_sesion_id,
                v_origen,
                v_motivo,
                jsonb_build_object(
                    'interior', NEW.interior,
                    'edificio', NEW.edificio,
                    'numero_oficial', NEW.numero_oficial,
                    'folio_electronico', NEW.folio_electronico,
                    'clave_catastral', NEW.clave_catastral
                ),
                NOW()
            );
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_vivienda_historial_estado ON satc_catalogo.vivienda;
CREATE TRIGGER trg_vivienda_historial_estado
    AFTER UPDATE OF estado_vivienda_id
    ON satc_catalogo.vivienda
    FOR EACH ROW
    WHEN (OLD.estado_vivienda_id IS DISTINCT FROM NEW.estado_vivienda_id)
    EXECUTE FUNCTION satc_catalogo.trg_vivienda_cambio_estado();

