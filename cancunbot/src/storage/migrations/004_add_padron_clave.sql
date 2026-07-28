-- =============================================================================
-- MIGRACIÓN 004: Adición de Padrón, Clave Catastral y Actualización de Selectores
-- Módulo: R2F-Cancún (Recibos y Facturas)
-- Versión: 1.1 | Fecha: 2026
-- Motor: PostgreSQL 16+
--
-- REGLAS DE SEGURIDAD:
--   1. Solo agrega columnas físicas opcionales (evita rupturas).
--   2. Actualiza selectores confirmados para recibo.tesoreriacancun.com
-- =============================================================================

-- 1. Agregar columnas físicas a recibo_cancun
ALTER TABLE cancunbot_produccion.recibo_cancun
    ADD COLUMN IF NOT EXISTS padron VARCHAR(100),
    ADD COLUMN IF NOT EXISTS clave_catastral VARCHAR(100);

COMMENT ON COLUMN cancunbot_produccion.recibo_cancun.padron IS 'Padrón del contribuyente extraído del detalle de cobro';
COMMENT ON COLUMN cancunbot_produccion.recibo_cancun.clave_catastral IS 'Clave Catastral del predio extraída del detalle de cobro';


-- 2. Actualizar selectores reales y confirmados para el portal CANCUN_RECIBO
UPDATE sar_configuracion.localizador_portal
    SET valor_selector = '#ayo', estrategia_selector = 'CSS'
    WHERE nombre_clave = 'CANCUN_RECIBO_INPUT_FOLIO';

UPDATE sar_configuracion.localizador_portal
    SET valor_selector = 'button:has-text("Consultar")', estrategia_selector = 'CSS'
    WHERE nombre_clave = 'CANCUN_RECIBO_BTN_CONSULTAR';

-- Botón PDF en la tabla de consulta (abre vista previa)
UPDATE sar_configuracion.localizador_portal
    SET valor_selector = 'button:has-text("PDF")', estrategia_selector = 'CSS'
    WHERE nombre_clave = 'CANCUN_RECIBO_BTN_DESCARGAR';

-- 3. Insertar selectores adicionales para el flujo interactivo del portal
-- Input para pase de caja
INSERT INTO sar_configuracion.localizador_portal
    (nombre_clave, label_visible, estrategia_selector, valor_selector, descripcion, portal, activo)
VALUES
    ('CANCUN_RECIBO_INPUT_PASE_CAJA', 'Campo Pase de Caja', 'CSS', '#pase', 'Input donde se ingresa el folio de pase de caja', 'CANCUN_RECIBO', TRUE)
ON CONFLICT (nombre_clave) DO UPDATE SET valor_selector = '#pase';

-- Botón Descargar PDF (en la vista previa del recibo)
INSERT INTO sar_configuracion.localizador_portal
    (nombre_clave, label_visible, estrategia_selector, valor_selector, descripcion, portal, activo)
VALUES
    ('CANCUN_RECIBO_BTN_DESCARGAR_EFECTIVO', 'Botón Descargar PDF Vista Previa', 'CSS', 'button:has-text("Descargar PDF")', 'Botón final para bajar archivo PDF', 'CANCUN_RECIBO', TRUE)
ON CONFLICT (nombre_clave) DO UPDATE SET valor_selector = 'button:has-text("Descargar PDF")';

-- Botón Volver
INSERT INTO sar_configuracion.localizador_portal
    (nombre_clave, label_visible, estrategia_selector, valor_selector, descripcion, portal, activo)
VALUES
    ('CANCUN_RECIBO_BTN_VOLVER', 'Botón Volver', 'CSS', 'button:has-text("Volver")', 'Botón para regresar al buscador de folios', 'CANCUN_RECIBO', TRUE)
ON CONFLICT (nombre_clave) DO UPDATE SET valor_selector = 'button:has-text("Volver")';
