"""
Runner para la migración 008: Renombrar esquema cancunbot_produccion a satc_produccion.
"""
import logging
from sqlalchemy import text
from satc.src.storage.db_connector import DatabaseConnector

logger = logging.getLogger(__name__)

def run_migration():
    connector = DatabaseConnector()
    if not connector.check_connection():
        logger.error("No hay conexión con la base de datos.")
        return False
    
    with connector.get_session() as session:
        session.execute(text("""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'cancunbot_produccion') THEN
                    ALTER SCHEMA cancunbot_produccion RENAME TO satc_produccion;
                    COMMENT ON SCHEMA satc_produccion IS 'Esquema del subsistema SATC. Lotes, folios, recibos y facturas.';
                ELSE
                    CREATE SCHEMA IF NOT EXISTS satc_produccion;
                END IF;
            END $$;
        """))
        session.commit()
        logger.info("[OK] Migración 008 ejecutada exitosamente: Esquema 'satc_produccion' activo.")
        return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migration()
