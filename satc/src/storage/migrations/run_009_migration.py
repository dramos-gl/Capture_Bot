import os
import sys
import logging
from pathlib import Path

# Agregar raíz del proyecto al path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import create_engine, text
from sar.src.storage.db_connector import DatabaseConnector

logger = logging.getLogger(__name__)

def run_migration():
    connector = DatabaseConnector()
    
    # Intentar ejecutar con la conexión del superusuario (postgres) si sar_app_user no tiene permisos DDL
    db_user = os.getenv("DB_SUPERUSER") or "postgres"
    db_pass = os.getenv("DB_SUPERUSER_PASSWORD") or ""
    db_host = connector.db_host
    db_port = connector.db_port
    db_name = connector.db_name

    super_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    
    try:
        engine = create_engine(super_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'cancunbot_configuracion') THEN
                        ALTER SCHEMA cancunbot_configuracion RENAME TO satc_configuracion;
                    ELSE
                        CREATE SCHEMA IF NOT EXISTS satc_configuracion;
                    END IF;

                    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'cancunbot_catalogo') THEN
                        ALTER SCHEMA cancunbot_catalogo RENAME TO satc_catalogo;
                    ELSE
                        CREATE SCHEMA IF NOT EXISTS satc_catalogo;
                    END IF;

                    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'cancunbot_produccion') THEN
                        ALTER SCHEMA cancunbot_produccion RENAME TO satc_produccion;
                    ELSE
                        CREATE SCHEMA IF NOT EXISTS satc_produccion;
                    END IF;

                    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'cancunbot_archivo') THEN
                        ALTER SCHEMA cancunbot_archivo RENAME TO satc_archivo;
                    ELSE
                        CREATE SCHEMA IF NOT EXISTS satc_archivo;
                    END IF;

                    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'cancunbot_auditoria') THEN
                        ALTER SCHEMA cancunbot_auditoria RENAME TO satc_auditoria;
                    ELSE
                        CREATE SCHEMA IF NOT EXISTS satc_auditoria;
                    END IF;

                    -- Otorgar permisos sobre los nuevos esquemas al usuario sar_app_user
                    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'sar_app_user') THEN
                        GRANT USAGE ON SCHEMA satc_configuracion, satc_catalogo, satc_produccion, satc_archivo, satc_auditoria TO sar_app_user;
                        GRANT ALL ON ALL TABLES IN SCHEMA satc_configuracion, satc_catalogo, satc_produccion, satc_archivo, satc_auditoria TO sar_app_user;
                        GRANT ALL ON ALL SEQUENCES IN SCHEMA satc_configuracion, satc_catalogo, satc_produccion, satc_archivo, satc_auditoria TO sar_app_user;
                    END IF;
                END $$;
            """))
            conn.commit()
            logger.info("=========================================================================")
            logger.info("[OK] MIGRACIÓN 009 EJECUTADA CON ÉXITO EN POSTGRESQL LOCAL!")
            logger.info("Esquemas activos: satc_configuracion, satc_catalogo, satc_produccion, satc_archivo, satc_auditoria.")
            logger.info("Permisos concedidos a 'sar_app_user'.")
            logger.info("=========================================================================")
            return True
    except Exception as e:
        logger.error(f"Error ejecutando migración como superusuario '{db_user}': {e}")
        logger.info("Nota: Para ejecutar la migración DDL sobre PostgreSQL, asegúrate de proporcionar las credenciales de un usuario administrador (ej. postgres).")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migration()
