-- ===========================================================================
-- Sistema de Administración de Referencias (SAR)
-- Script SQL para limpiar datos transaccionales, auditoría y archivos PDF.
-- Conserva catálogos, configuración y control de acceso (RBAC).
-- ===========================================================================

BEGIN;

-- Desactivar temporalmente disparadores/constraints si es necesario (opcional)
-- SET CONSTRAINTS ALL DEFERRED;

-- Truncar tablas de producción, archivos, auditoría y sesiones.
-- 'RESTART IDENTITY' reinicia las secuencias (IDs autoincrementales) a 1.
-- 'CASCADE' asegura la integridad referencial en cascada si hubiera dependencias ocultas.
TRUNCATE TABLE 
    sar_archivo.asignacion,
    sar_archivo.factura,
    sar_archivo.archivo_pdf,
    sar_produccion.referencia,
    sar_produccion.solicitud,
    sar_produccion.grupo_referencia,
    sar_produccion.orden_generacion,
    sar_auditoria.auditoria_error,
    sar_auditoria.auditoria_evento,
    sar_auditoria.auditoria_login,
    sar_seguridad.sesion
RESTART IDENTITY CASCADE;

COMMIT;

-- ===========================================================================
-- TABLAS QUE SE CONSERVAN INTACTAS (Catálogo y Configuración):
-- ===========================================================================
-- * sar_seguridad.usuario, rol, usuario_rol, app_modulo, modulo, accion, permiso, rol_permiso
-- * sar_catalogo.municipio, delegacion, concepto, rfc, estado_sistema, evento_sistema
-- * sar_configuracion.parametro_sistema, localizador_portal
-- ===========================================================================
