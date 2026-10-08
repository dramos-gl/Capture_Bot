"""Migración Segura e Idempotente para agregar columna alias en tablas desarrollo y delegacion."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

# Forzar usuario postgres (owner de las tablas) para operaciones DDL seguras
os.environ["DB_USER"] = "postgres"
if "DB_PASSWORD" not in os.environ:
    os.environ["DB_PASSWORD"] = "postgres"

from sqlalchemy import text
from sar.src.storage.db_connector import DatabaseConnector


def migrate_alias_columns():
    print("Iniciando migración segura: agregar columna alias en tablas desarrollo y delegacion...")
    db = DatabaseConnector()

    with db.get_session() as session:
        # 1. Agregar columna alias en sar_catalogo.desarrollo si no existe
        session.execute(text("""
            ALTER TABLE sar_catalogo.desarrollo 
            ADD COLUMN IF NOT EXISTS alias VARCHAR(50);
        """))
        session.execute(text("""
            COMMENT ON COLUMN sar_catalogo.desarrollo.alias IS 'Alias corto o identificador abreviado del desarrollo para futuras implementaciones';
        """))
        print("Columna sar_catalogo.desarrollo.alias verificada/creada con éxito.")

        # 2. Agregar columna alias en sar_catalogo.delegacion si no existe
        session.execute(text("""
            ALTER TABLE sar_catalogo.delegacion 
            ADD COLUMN IF NOT EXISTS alias VARCHAR(50);
        """))
        session.execute(text("""
            COMMENT ON COLUMN sar_catalogo.delegacion.alias IS 'Alias o identificador corto de la delegación para futuras implementaciones';
        """))
        print("Columna sar_catalogo.delegacion.alias verificada/creada con éxito.")

        session.commit()
        print("¡MIGRACIÓN DE ALIAS FINALIZADA EXITOSAMENTE!")


if __name__ == "__main__":
    migrate_alias_columns()
