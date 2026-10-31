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
    print(f"Iniciando migración 019 en {db_name} ({db_host}:{db_port}) conectando como postgres...")
    sql_path = Path(__file__).parent / "019_add_inscripcion_metadata_to_regimen.sql"
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
        print("Migración 019 aplicada con éxito en PostgreSQL.")

        cur.execute("GRANT ALL ON satc_catalogo.regimen TO sar_app_user;")
        conn.commit()
        print("Permisos otorgados a sar_app_user.")

        # Verificar columnas
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'satc_catalogo' AND table_name = 'regimen'
            ORDER BY ordinal_position;
        """)
        cols = cur.fetchall()
        print("\nEstructura actual de satc_catalogo.regimen:")
        for col, dtype in cols:
            print(f" - {col}: {dtype}")

        cur.close()
    except Exception as e:
        conn.rollback()
        print(f"ERROR durante la migración 019: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()

