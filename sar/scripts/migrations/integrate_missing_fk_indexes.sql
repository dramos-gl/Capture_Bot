-- ==============================================================================
-- SAR - Script SQL de Creación de Índices Faltantes de Claves Foráneas (FK)
-- Motor: PostgreSQL 18+
-- Ejecución: Este script debe ser ejecutado por el DBA / Superusuario 'postgres'
-- Base de datos: db_sar
-- ==============================================================================

-- 1. Optimización en sar_produccion.referencia (57,000+ filas)
-- Acelera el filtrado y agrupamiento por operador / usuario asignado
CREATE INDEX IF NOT EXISTS idx_referencia_usuario_asignado 
ON sar_produccion.referencia (usuario_asignado) 
WHERE usuario_asignado IS NOT NULL;

-- 2. Optimización en sar_archivo.asignacion_referencia (11,000+ filas)
-- Acelera consultas forenses y reportes de auditoría de confirmación de lotes
CREATE INDEX IF NOT EXISTS idx_asignacion_referencia_usuario_confirmacion 
ON sar_archivo.asignacion_referencia (usuario_confirmacion) 
WHERE usuario_confirmacion IS NOT NULL;

-- 3. Optimización en sar_produccion.solicitud
-- Acelera cruces relacionales entre solicitudes y su delegación operativa
CREATE INDEX IF NOT EXISTS idx_solicitud_delegacion_id 
ON sar_produccion.solicitud (delegacion_id);

-- 4. Optimización en sar_produccion.orden_generacion
-- Índices para búsqueda por municipio, estado de ciclo de vida y creador de orden
CREATE INDEX IF NOT EXISTS idx_orden_generacion_municipio_id 
ON sar_produccion.orden_generacion (municipio_id);

CREATE INDEX IF NOT EXISTS idx_orden_generacion_estado_id 
ON sar_produccion.orden_generacion (estado_id);

CREATE INDEX IF NOT EXISTS idx_orden_generacion_usuario_id 
ON sar_produccion.orden_generacion (usuario_id);

-- 5. Optimización en sar_catalogo.desarrollo_empresa
-- Acelera resolución de catálogos cruzados con delegaciones
CREATE INDEX IF NOT EXISTS idx_desarrollo_empresa_delegacion_id 
ON sar_catalogo.desarrollo_empresa (delegacion_id);

-- 6. Optimización en sar_seguridad.rol_app_modulo
-- Acelera validación de permisos macro en la navegación inicial
CREATE INDEX IF NOT EXISTS idx_rol_app_modulo_app_modulo_id 
ON sar_seguridad.rol_app_modulo (app_modulo_id);
