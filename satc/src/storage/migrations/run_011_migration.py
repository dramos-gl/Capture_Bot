"""
SATC — Runner de Migración 011: Vía Paralela de Gobernanza de Trámites
Ejecuta 011_tramite_parallel_workflow.sql sobre PostgreSQL y concede permisos a sar_app_user.
"""
import os
import sys
import logging
from pathlib import Path

# Configurar path raíz: 5 niveles arriba hasta Proyecto_CapturaBot
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import create_engine, text
from sar.src.storage.db_connector import DatabaseConnector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SATC_MIGRATION_011")

def run_migration():
    sql_path = Path(__file__).parent / "011_tramite_parallel_workflow.sql"
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
            
            # Conceder permisos sobre las nuevas tablas al usuario de la aplicación
            conn.execute(text("""
                DO $$
                BEGIN
                    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'sar_app_user') THEN
                        GRANT ALL ON TABLE satc_produccion.orden_tramite, satc_produccion.solicitud_tramite TO sar_app_user;
                        GRANT ALL ON ALL SEQUENCES IN SCHEMA satc_produccion TO sar_app_user;
                    END IF;
                END $$;
            """))
            conn.commit()
            logger.info("✅ Migración 011 ejecutada exitosamente en PostgreSQL y permisos concedidos.")
            
            # Verificación
            res = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'satc_produccion' 
                  AND table_name IN ('orden_tramite', 'solicitud_tramite', 'tramite_vivienda', 'orden_cancun', 'lote_folio')
                ORDER BY table_name;
            """)).fetchall()
            
            logger.info("Tablas verificadas en satc_produccion (Ambas vías activas):")
            for (t,) in res:
                logger.info(f"  • satc_produccion.{t}")
                
        return True
    except Exception as e:
        logger.error(f"❌ Error al ejecutar la migración 011: {e}")
        return False

if __name__ == "__main__":
    run_migration()
