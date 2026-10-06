-- =============================================================================
-- Migration 005: Registro del Módulo CTRL_R2F en sar_seguridad.app_modulo
-- Permite seleccionar e ingresar directamente al Módulo Control de Recibos & Facturas (R2F).
-- =============================================================================

-- 1. Registrar app_modulo CTRL_R2F
INSERT INTO sar_seguridad.app_modulo (codigo, nombre, activo)
VALUES ('CTRL_R2F', 'Control de Recibos & Facturas (R2F)', TRUE)
ON CONFLICT (codigo) DO UPDATE 
SET nombre = EXCLUDED.nombre, activo = TRUE;

-- 2. Otorgar acceso al módulo a los roles ADMINISTRADOR y OPERADOR
INSERT INTO sar_seguridad.rol_app_modulo (rol_id, app_modulo_id)
SELECT r.rol_id, am.app_modulo_id
FROM sar_seguridad.rol r
CROSS JOIN sar_seguridad.app_modulo am
WHERE r.codigo IN ('ADMINISTRADOR', 'OPERADOR')
  AND am.codigo = 'CTRL_R2F'
ON CONFLICT (rol_id, app_modulo_id) DO NOTHING;
