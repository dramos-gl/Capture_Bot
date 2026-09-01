"""Migration script to decouple ubicacion and asignacion_referencia in PostgreSQL."""
import os
import sys
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sar.src.storage.db_connector import DatabaseConnector

def run_migration():
    print("Iniciando migración de desacoplamiento de Ubicación y Asignación de Referencia...")
    db_connector = DatabaseConnector()
    
    sql_statements = [
        "ALTER TABLE sar_archivo.ubicacion ADD COLUMN IF NOT EXISTS descripcion TEXT;",
        "ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS cliente VARCHAR(250);",
        "ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS credito_titular VARCHAR(250);",
        "ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS pa VARCHAR(250);",
        "ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS no_oficial VARCHAR(250);",
        "ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS fecha_solicitud DATE;",
        "ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS fecha_reporte_notaria DATE;",
        "ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS fecha_ingreso_rpp DATE;",
        "ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS fecha_escritura DATE;",
        "ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS fecha_titulacion DATE;",
        "ALTER TABLE sar_archivo.asignacion_referencia ADD COLUMN IF NOT EXISTS comentarios TEXT;",
        """
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
        """,
        """
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
        """
    ]
    
    with db_connector.get_session() as session:
        for stmt in sql_statements:
            session.execute(text(stmt))
        session.commit()
    print("Migración completada exitosamente.")

if __name__ == "__main__":
    run_migration()
