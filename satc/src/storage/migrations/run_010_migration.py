"""
SATC — Runner de Migración 010: Ciclo de Vida de Trámites por Vivienda
Ejecuta el script SQL 010_housing_life_cycle_schema.sql sobre la base de datos PostgreSQL.
"""
import os
import sys
import logging
from pathlib import Path

# Configurar path raíz
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import create_engine, text
from sar.src.storage.db_connector import DatabaseConnector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SATC_MIGRATION_010")

def run_migration():
    sql_path = Path(__file__).parent / "010_housing_life_cycle_schema.sql"
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
            # Ejecutar el script completo
            conn.execute(text(sql_content))
            conn.commit()
            logger.info("✅ Migración 010 ejecutada exitosamente en PostgreSQL.")
            
            # Verificación de tablas creadas
            res = conn.execute(text("""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_schema IN ('satc_catalogo', 'satc_produccion')
                  AND table_name IN ('tipo_tramite', 'estado_vivienda', 'estado_tramite', 
                                    'regimen_condominio', 'vivienda', 'tramite_vivienda', 'requisito_documento')
                ORDER BY table_schema, table_name;
            """)).fetchall()
            
            logger.info("Tablas verificadas en base de datos:")
            for schema, table in res:
                logger.info(f"  • {schema}.{table}")
                
        return True
    except Exception as e:
        logger.error(f"❌ Error al ejecutar la migración 010: {e}")
        return False

if __name__ == "__main__":
    run_migration()
