-- Migración 021: Módulo de Cortes de Disponibilidad ERP y Bitácora de Estados Comerciales
-- Esquema: satc_auditoria, satc_catalogo

BEGIN;

-- 1. Tabla de cabecera de cortes del ERP
CREATE TABLE IF NOT EXISTS satc_auditoria.corte_erp (
    corte_id SERIAL PRIMARY KEY,
    desarrollo_id INT NOT NULL REFERENCES sar_catalogo.desarrollo(desarrollo_id) ON DELETE RESTRICT,
    nombre_archivo VARCHAR(255) NOT NULL,
    hash_sha256 VARCHAR(64) NOT NULL,
    fecha_corte_declarada TIMESTAMP NULL,
    total_registros INT NOT NULL DEFAULT 0,
    total_disponibles INT NOT NULL DEFAULT 0,
    total_en_escrituracion INT NOT NULL DEFAULT 0,
    total_tituladas INT NOT NULL DEFAULT 0,
    total_reincorporadas INT NOT NULL DEFAULT 0,
    total_sin_cambio INT NOT NULL DEFAULT 0,
    usuario_id INT NOT NULL REFERENCES sar_seguridad.usuario(usuario_id) ON DELETE RESTRICT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_corte_erp_desarrollo ON satc_auditoria.corte_erp(desarrollo_id);
CREATE INDEX IF NOT EXISTS idx_corte_erp_fecha ON satc_auditoria.corte_erp(created_at DESC);

-- 2. Extender tabla de viviendas con metadatos de disponibilidad ERP
ALTER TABLE satc_catalogo.vivienda
    ADD COLUMN IF NOT EXISTS condicion_comercial VARCHAR(50) DEFAULT 'DISPONIBLE' NOT NULL,
    ADD COLUMN IF NOT EXISTS ultimo_corte_id INT REFERENCES satc_auditoria.corte_erp(corte_id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS fecha_estatus_erp TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS cliente_erp VARCHAR(200) NULL,
    ADD COLUMN IF NOT EXISTS nss_cliente VARCHAR(50) NULL,
    ADD COLUMN IF NOT EXISTS etapa_erp VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS es_reincorporada BOOLEAN DEFAULT FALSE NOT NULL;

CREATE INDEX IF NOT EXISTS idx_vivienda_condicion ON satc_catalogo.vivienda(condicion_comercial);
CREATE INDEX IF NOT EXISTS idx_vivienda_ultimo_corte ON satc_catalogo.vivienda(ultimo_corte_id);

-- 3. Tabla de log histórico granular por vivienda en cada corte
CREATE TABLE IF NOT EXISTS satc_auditoria.vivienda_corte_log (
    log_id BIGSERIAL PRIMARY KEY,
    corte_id INT NOT NULL REFERENCES satc_auditoria.corte_erp(corte_id) ON DELETE CASCADE,
    vivienda_id INT NOT NULL REFERENCES satc_catalogo.vivienda(vivienda_id) ON DELETE CASCADE,
    condicion_anterior VARCHAR(50) NULL,
    condicion_nueva VARCHAR(50) NOT NULL,
    status_erp_raw VARCHAR(50) NULL,
    etapa_erp_raw VARCHAR(100) NULL,
    cliente_raw VARCHAR(200) NULL,
    nss_raw VARCHAR(50) NULL,
    delta_tipo VARCHAR(50) NOT NULL, -- 'SIN_CAMBIO', 'AVANCE_ESCRITURACION', 'TITULADA', 'REINCORPORADA_CANCELACION', 'NUEVA_DISPONIBLE'
    observaciones TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_vivienda_corte_log_corte ON satc_auditoria.vivienda_corte_log(corte_id);
CREATE INDEX IF NOT EXISTS idx_vivienda_corte_log_vivienda ON satc_auditoria.vivienda_corte_log(vivienda_id);
CREATE INDEX IF NOT EXISTS idx_vivienda_corte_log_delta ON satc_auditoria.vivienda_corte_log(delta_tipo);

-- 4. Conceder permisos de aplicación
GRANT SELECT, INSERT, UPDATE ON TABLE satc_auditoria.corte_erp TO sar_app_user;
GRANT USAGE, SELECT ON SEQUENCE satc_auditoria.corte_erp_corte_id_seq TO sar_app_user;

GRANT SELECT, INSERT, UPDATE ON TABLE satc_auditoria.vivienda_corte_log TO sar_app_user;
GRANT USAGE, SELECT ON SEQUENCE satc_auditoria.vivienda_corte_log_log_id_seq TO sar_app_user;

GRANT SELECT, UPDATE ON TABLE satc_catalogo.vivienda TO sar_app_user;

COMMIT;

