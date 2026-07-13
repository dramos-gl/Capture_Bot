"""Migration script to add cantidad and porcentaje columns to sar_produccion.referencia."""

import sys
import os
from sqlalchemy import text

# Ensure root dir is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sar.src.storage.db_connector import DatabaseConnector

def run_migration():
    print("Iniciando migración de campos 'cantidad' y 'porcentaje' en tabla 'referencia'...")
    db = DatabaseConnector()
    
    try:
        with db.get_session() as session:
            # 1. Check if cantidad already exists
            check_cantidad = text("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_schema = 'sar_produccion' 
                  AND table_name = 'referencia' 
                  AND column_name = 'cantidad';
            """)
            cantidad_exists = session.execute(check_cantidad).scalar()
            
            if cantidad_exists == 0:
                print("Agregando columna 'cantidad' a 'sar_produccion.referencia'...")
                alter_cantidad = text("""
                    ALTER TABLE sar_produccion.referencia 
                    ADD COLUMN cantidad INTEGER NOT NULL DEFAULT 1;
                """)
                session.execute(alter_cantidad)
                print("¡Columna 'cantidad' agregada!")
            else:
                print("La columna 'cantidad' ya existe.")
                
            # 2. Check if porcentaje already exists
            check_porcentaje = text("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_schema = 'sar_produccion' 
                  AND table_name = 'referencia' 
                  AND column_name = 'porcentaje';
            """)
            porcentaje_exists = session.execute(check_porcentaje).scalar()
            
            if porcentaje_exists == 0:
                print("Agregando columna 'porcentaje' a 'sar_produccion.referencia'...")
                alter_porcentaje = text("""
                    ALTER TABLE sar_produccion.referencia 
                    ADD COLUMN porcentaje INTEGER NOT NULL DEFAULT 100;
                """)
                session.execute(alter_porcentaje)
                print("¡Columna 'porcentaje' agregada!")
            else:
                print("La columna 'porcentaje' ya existe.")
                
            session.commit()
            print("¡Migración de campos completada con éxito!")
    except Exception as e:
        print(f"Error ejecutando migración: {str(e)}")

if __name__ == "__main__":
    run_migration()
