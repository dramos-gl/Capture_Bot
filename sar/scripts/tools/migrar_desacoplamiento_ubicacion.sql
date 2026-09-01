-- Migration: Desacoplamiento de Ubicacion y AsignacionReferencia (SAR-DB-001)

BEGIN;

-- 1. Agregar columna de administración a sar_archivo.ubicacion
ALTER TABLE sar_archivo.ubicacion ADD COLUMN IF NOT EXISTS descripcion TEXT;

-- 2. Agregar columnas transaccionales a sar_archivo.asignacion_referencia
ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS cliente VARCHAR(250);
ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS credito_titular VARCHAR(250);
ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS pa VARCHAR(250);
ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS no_oficial VARCHAR(250);
ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS fecha_solicitud DATE;
ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS fecha_reporte_notaria DATE;
ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS fecha_ingreso_rpp DATE;
ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS fecha_escritura DATE;
ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS fecha_titulacion DATE;
ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS comentarios TEXT;

-- 3. Migrar datos existentes de ubicacion hacia asignacion_referencia
UPDATE sar_archivo.asignacion_referencia ar
SET 
    cliente = COALESCE(ar.cliente, ubi.cliente),
    credito_titular = COALESCE(ar.credito_titular, ubi.credito_titular),
    pa = COALESCE(ar.pa, ubi.pa),
    no_oficial = COALESCE(ar.no_oficial, ubi.no_oficial, ubi.lote_id_erp),
    fecha_solicitud = COALESCE(ar.fecha_solicitud, ubi.fecha_solicitud),
    fecha_reporte_notaria = COALESCE(ar.fecha_reporte_notaria, ubi.fecha_reporte_notaria),
    fecha_ingreso_rpp = COALESCE(ar.fecha_ingreso_rpp, ubi.fecha_ingreso_rpp),
    fecha_escritura = COALESCE(ar.fecha_escritura, ubi.fecha_escritura),
    fecha_titulacion = COALESCE(ar.fecha_titulacion, ubi.fecha_titulacion),
    comentarios = COALESCE(ar.comentarios, ubi.comentarios)
FROM sar_archivo.ubicacion ubi
WHERE ar.ubicacion_id = ubi.ubicacion_id;

-- 4. Limpieza de columnas obsoletas en sar_archivo.ubicacion
ALTER TABLE sar_archivo.ubicacion 
    DROP COLUMN IF EXISTS cliente,
    DROP COLUMN IF EXISTS fecha_solicitud,
    DROP COLUMN IF EXISTS credito_titular,
    DROP COLUMN IF EXISTS delegacion,
    DROP COLUMN IF EXISTS comentarios,
    DROP COLUMN IF EXISTS pa,
    DROP COLUMN IF EXISTS no_oficial,
    DROP COLUMN IF EXISTS fecha_ingreso_rpp,
    DROP COLUMN IF EXISTS fecha_reporte_notaria,
    DROP COLUMN IF EXISTS fecha_escritura,
    DROP COLUMN IF EXISTS fecha_titulacion;

COMMIT;
