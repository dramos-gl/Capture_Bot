"""
SATC — Runner de Migración 017: Creación de satc_catalogo.vivienda_historial_estado
Ejecuta el script SQL 017_create_vivienda_historial_estado.sql sobre PostgreSQL.
Aislamiento Total: Modifica exclusivamente satc_catalogo sin tocar tablas de SAR.
"""
import os
import sys
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import create_engine, text
from sar.src.storage.db_connector import DatabaseConnector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SATC_MIGRATION_017")


def run_migration():
    sql_path = Path(__file__).parent / "017_create_vivienda_historial_estado.sql"
    if not sql_path.exists():
        logger.error(f"No se encontró el archivo de migración: {sql_path}")
        return False

    with open(sql_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    connector = DatabaseConnector()
    db_user = os.getenv("DB_SUPERUSER") or "postgres"
    db_pass = os.getenv("DB_SUPERUSER_PASSWORD") or ""
    db_host = connector.db_host
    db_port = connector.db_port
    db_name = connector.db_name

    super_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    logger.info(f"Conectando a {db_name} en {db_host}:{db_port} como {db_user}...")
    try:
        engine = create_engine(super_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text(sql_content))
            conn.commit()
            logger.info("Migración 017 ejecutada exitosamente con superusuario.")

            # Verificación en information_schema
            cols = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'satc_catalogo' 
                  AND table_name = 'vivienda_historial_estado'
                ORDER BY ordinal_position;
            """)).fetchall()

            logger.info("Columnas verificadas en satc_catalogo.vivienda_historial_estado:")
            for cname, dtype in cols:
                logger.info(f"  • {cname} ({dtype})")

        return True
    except Exception as e:
        logger.warning(f"No se pudo conectar como {db_user} ({e}). Intentando con conexión regular sar_app_user...")
        try:
            with connector.get_session() as s:
                s.execute(text(sql_content))
                s.commit()
                logger.info("Migración 017 ejecutada exitosamente con sesión de aplicación.")
            return True
        except Exception as e2:
            logger.error(f"Error definitivo al ejecutar la migración 017: {e2}")
            return False


if __name__ == "__main__":
    run_migration()
