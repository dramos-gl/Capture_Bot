import sys
import os

project_root = r"c:\Users\dramos\Documents\Proyecto_CapturaBot"
sys.path.insert(0, project_root)

from sqlalchemy import create_engine, text
import json

def run():
    sql_path = os.path.join(os.path.dirname(__file__), "003_add_orden_cancun.sql")
    print(f"Leyendo archivo de migración: {sql_path}")
    with open(sql_path, "r", encoding="utf-8") as f:
        sql_script = f.read()

    # Intentar conexión con postgres
    engine = create_engine("postgresql+psycopg2://postgres@127.0.0.1:5432/db_sar")
    print("Ejecutando DDL de migración 003_add_orden_cancun.sql con usuario postgres...")
    with engine.connect() as conn:
        conn.execute(text(sql_script))
        # Otorgar permisos al usuario de la aplicación
        conn.execute(text("GRANT ALL ON ALL TABLES IN SCHEMA cancunbot_produccion TO sar_app_user;"))
        conn.execute(text("GRANT ALL ON ALL SEQUENCES IN SCHEMA cancunbot_produccion TO sar_app_user;"))
        conn.execute(text("GRANT ALL ON SCHEMA cancunbot_produccion TO sar_app_user;"))
        conn.commit()
    print("[OK] Migración 003 ejecutada exitosamente en PostgreSQL. La tabla 'cancunbot_produccion.orden_cancun' ya está lista y con permisos concedidos a sar_app_user.")

if __name__ == "__main__":
    run()
