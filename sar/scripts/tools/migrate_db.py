"""Migration script to apply municipio_id column to sar_produccion.orden_generacion."""

import sys
import os
from sqlalchemy import text

# Ensure root dir is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sar.src.storage.db_connector import DatabaseConnector

def run_migration():
    print("Iniciando migración en la base de datos física PostgreSQL...")
    db = DatabaseConnector()
    
    try:
        with db.get_session() as session:
            # 1. Check if column already exists
            check_col_query = text("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_schema = 'sar_produccion' 
                  AND table_name = 'orden_generacion' 
                  AND column_name = 'municipio_id';
            """)
            exists = session.execute(check_col_query).scalar()
            
            if exists == 0:
                print("Agregando columna 'municipio_id' y llave foránea a 'sar_produccion.orden_generacion'...")
                
                # We alter the table to add municipio_id and set a default constraint
                alter_query = text("""
                    ALTER TABLE sar_produccion.orden_generacion 
                    ADD COLUMN municipio_id BIGINT NOT NULL DEFAULT 2;
                    
                    ALTER TABLE sar_produccion.orden_generacion 
                    ADD CONSTRAINT fk_orden_generacion_municipio 
                    FOREIGN KEY (municipio_id) REFERENCES sar_catalogo.municipio(municipio_id) ON DELETE RESTRICT;
                """)
                session.execute(alter_query)
                print("¡Columna agregada exitosamente!")
            else:
                print("La columna 'municipio_id' ya existe en la base de datos física. No se requiere alteración.")
                
            # 2. Add 'alias' column to sar_catalogo.concepto if it does not exist
            check_alias_query = text("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_schema = 'sar_catalogo' 
                  AND table_name = 'concepto' 
                  AND column_name = 'alias';
            """)
            alias_exists = session.execute(check_alias_query).scalar()
            
            if alias_exists == 0:
                print("Agregando columna 'alias' a 'sar_catalogo.concepto'...")
                alter_alias_query = text("""
                    ALTER TABLE sar_catalogo.concepto 
                    ADD COLUMN alias VARCHAR(20);
                """)
                session.execute(alter_alias_query)
                
                # Backfill concept aliases
                backfill_aliases = text("""
                    UPDATE sar_catalogo.concepto 
                    SET alias = CASE 
                        WHEN nombre LIKE '%Análisis%' THEN 'ANA'
                        WHEN nombre LIKE '%Aviso%' THEN 'AVI'
                        WHEN nombre LIKE '%Certificados%' THEN 'CLG'
                        ELSE 'UNK'
                    END;
                """)
                session.execute(backfill_aliases)
                print("¡Columna 'alias' agregada y populada exitosamente!")
            else:
                print("La columna 'alias' en la tabla de conceptos ya existe.")
                
            session.commit()
            print("¡Migración completada con éxito!")
    except Exception as e:
        print(f"Error ejecutando migración: {str(e)}")

if __name__ == "__main__":
    run_migration()
