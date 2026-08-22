-- Migration: Add date fields to sar_archivo.ubicacion
BEGIN;

ALTER TABLE sar_archivo.ubicacion ADD COLUMN IF NOT EXISTS fecha_reporte_notaria DATE;
ALTER TABLE sar_archivo.ubicacion ADD COLUMN IF NOT EXISTS fecha_escritura DATE;
ALTER TABLE sar_archivo.ubicacion ADD COLUMN IF NOT EXISTS fecha_titulacion DATE;

COMMIT;
