"""Migration script to apply date columns to sar_archivo.ubicacion."""

import sys
import os
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sar.src.storage.db_connector import DatabaseConnector

def run_migration():
    print("Iniciando migración de base de datos para nuevas fechas...")
    db = DatabaseConnector()
    
    sql_script = """
    ALTER TABLE sar_archivo.ubicacion ADD COLUMN IF NOT EXISTS fecha_reporte_notaria DATE;
    ALTER TABLE sar_archivo.ubicacion ADD COLUMN IF NOT EXISTS fecha_escritura DATE;
    ALTER TABLE sar_archivo.ubicacion ADD COLUMN IF NOT EXISTS fecha_titulacion DATE;
    """
    
    try:
        with db.get_session() as session:
            session.execute(text(sql_script))
            session.commit()
            print("¡Migración completada exitosamente!")
    except Exception as e:
        print(f"Error ejecutando migración: {str(e)}")

if __name__ == "__main__":
    run_migration()
