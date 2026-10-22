"""
SATC — Runner de Migración 016: Arquitectura de Extracción Metadata-Driven Municipal
Ejecuta el script SQL 016_metadata_driven_extraction_schema.sql sobre PostgreSQL.
Aislamiento Total: Modifica únicamente el esquema satc_configuracion.
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
logger = logging.getLogger("SATC_MIGRATION_016")


def run_migration():
    sql_path = Path(__file__).parent / "016_metadata_driven_extraction_schema.sql"
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
        raw_conn = engine.raw_connection()
        try:
            cursor = raw_conn.cursor()
            cursor.execute(sql_content)
            raw_conn.commit()
            cursor.close()
        finally:
            raw_conn.close()

        logger.info("Migración 016 ejecutada exitosamente.")
        with engine.connect() as conn:

            # Verificación en information_schema
            tables = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'satc_configuracion' 
                  AND table_name IN ('campo_canonico', 'campo_etiqueta_ancla', 'campo_formato_municipio');
            """)).fetchall()

            logger.info("Tablas verificadas en satc_configuracion:")
            for (tname,) in tables:
                logger.info(f"  • satc_configuracion.{tname}")

            # Conteo de registros insertados
            c_campos = conn.execute(text("SELECT count(*) FROM satc_configuracion.campo_canonico;")).scalar()
            c_anclas = conn.execute(text("SELECT count(*) FROM satc_configuracion.campo_etiqueta_ancla;")).scalar()
            c_formatos = conn.execute(text("SELECT count(*) FROM satc_configuracion.campo_formato_municipio;")).scalar()

            logger.info(f"Semillas activas: {c_campos} campos, {c_anclas} anclas, {c_formatos} formatos municipales.")

        return True
    except Exception as e:
        logger.error(f"Error al ejecutar la migración 016: {e}")
        return False


if __name__ == "__main__":
    run_migration()
