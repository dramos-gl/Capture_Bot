import os
import sys
import psycopg2
from pathlib import Path

# Cargar configuración desde sar/settings.json
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
    print(f"Iniciando migración 018 en {db_name} ({db_host}:{db_port}) conectando como postgres (dueño de tablas)...")
    sql_path = Path(__file__).parent / "018_add_alias_to_tipo_tramite.sql"
    with open(sql_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Conectar como postgres (dueño del catálogo)
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
        print("Migración 018 aplicada con éxito en PostgreSQL.")

        # Conceder permisos a sar_app_user si fuera necesario
        cur.execute("GRANT ALL ON satc_catalogo.tipo_tramite TO sar_app_user;")
        conn.commit()

        # Verificar resultados
        cur.execute("SELECT tipo_tramite_id, codigo, alias, nombre FROM satc_catalogo.tipo_tramite ORDER BY tipo_tramite_id ASC;")
        rows = cur.fetchall()
        print("\n--- Catálogo satc_catalogo.tipo_tramite Actualizado ---")
        for r in rows:
            print(f"ID {r[0]} | Código: {r[1]} | Alias: {r[2]} | Nombre: {r[3]}")

        cur.close()
    except Exception as e:
        conn.rollback()
        print(f"Error al ejecutar migración: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
