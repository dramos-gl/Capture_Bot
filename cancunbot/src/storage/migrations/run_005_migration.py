import sys
import os

project_root = r"c:\Users\dramos\Documents\Proyecto_CapturaBot"
sys.path.insert(0, project_root)

from sqlalchemy import create_engine, text

def run():
    sql_path = os.path.join(os.path.dirname(__file__), "005_register_ctrl_r2f_app_modulo.sql")
    print(f"Leyendo archivo de migración: {sql_path}")
    with open(sql_path, "r", encoding="utf-8") as f:
        sql_script = f.read()

    engine = create_engine("postgresql+psycopg2://postgres@127.0.0.1:5432/db_sar")
    print("Ejecutando DDL 005_register_ctrl_r2f_app_modulo.sql con usuario postgres...")
    with engine.connect() as conn:
        conn.execute(text(sql_script))
        conn.commit()
    print("[OK] Migración 005 ejecutada exitosamente. Módulo 'CTRL_R2F' registrado en sar_seguridad.app_modulo.")

if __name__ == "__main__":
    run()
