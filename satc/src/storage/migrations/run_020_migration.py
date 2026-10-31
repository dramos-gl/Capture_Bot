import os
import sys
import psycopg2
from pathlib import Path
import json

ROOT_DIR = Path(__file__).resolve().parents[4]
settings_path = ROOT_DIR / "sar" / "settings.json"

db_host = "127.0.0.1"
db_port = 5432
db_name = "db_sar"

if settings_path.exists():
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            db_host = cfg.get("DB_HOST", db_host)
            db_port = int(cfg.get("DB_PORT", db_port))
            db_name = cfg.get("DB_NAME", db_name)
    except Exception as e:
        print(f"Advertencia al leer settings.json: {e}")

def run_migration():
    print(f"Iniciando migración 020 en {db_name} ({db_host}:{db_port}) conectando como postgres...")
    sql_path = Path(__file__).parent / "020_add_unique_constraint_regimen_sm_mz_lt.sql"
    with open(sql_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user="postgres",
        password=""
    )
    conn.autocommit = False
    try:
        cur = conn.cursor()
        cur.execute(sql_content)
        conn.commit()
        print("Migración 020 completada exitosamente.")
    except Exception as e:
        conn.rollback()
        print(f"Error al ejecutar la migración 020: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()

