"""
SATC — Runner de Migración 013: Normalización de Vivienda
Ejecuta el script SQL 013_normalize_vivienda_schema.sql sobre PostgreSQL.
Aislamiento Total: Solo opera sobre satc_catalogo sin tocar tablas de SAR.
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
logger = logging.getLogger("SATC_MIGRATION_013")


def run_migration():
    sql_path = Path(__file__).parent / "013_normalize_vivienda_schema.sql"
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
            # 1. Ejecución del script DDL
            conn.execute(text(sql_content))
            conn.commit()
            logger.info("✅ Migración 013 ejecutada exitosamente.")

            # 2. Verificación de la estructura resultante de satc_catalogo.vivienda
            cols = conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'satc_catalogo' AND table_name = 'vivienda'
                ORDER BY ordinal_position;
            """)).fetchall()

            logger.info("Estructura final verificada de satc_catalogo.vivienda:")
            for col_name, dtype, nullable, default_val in cols:
                logger.info(f"  • {col_name:<20} {dtype:<18} (Nullable: {nullable})")

        return True
    except Exception as e:
        logger.error(f"❌ Error al ejecutar la migración 013: {e}")
        return False


if __name__ == "__main__":
    run_migration()
