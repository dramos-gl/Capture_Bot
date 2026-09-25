"""Safe runner for migration_normalizar_no_oficial.sql."""
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sqlalchemy import text
from sar.src.storage.db_connector import DatabaseConnector

def run_safe_migration():
    print("Iniciando migración segura para normalizar no_oficial en sar_archivo.ubicacion...")
    db = DatabaseConnector()
    with db.get_session() as session:
        # Check current columns
        cols = [r[0] for r in session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'sar_archivo' AND table_name = 'ubicacion';
        """)).fetchall()]
        print("Columnas actuales en sar_archivo.ubicacion:", cols)
        
        if "no_oficial" not in cols:
            print("1. Agregando columna 'no_oficial'...")
            session.execute(text("ALTER TABLE sar_archivo.ubicacion ADD COLUMN IF NOT EXISTS no_oficial VARCHAR(100);"))
        else:
            print("Columna 'no_oficial' ya existe.")

        print("2. Sincronizando valores desde lote_id_erp hacia no_oficial...")
        updated = session.execute(text("""
            UPDATE sar_archivo.ubicacion 
            SET no_oficial = lote_id_erp 
            WHERE no_oficial IS NULL AND lote_id_erp IS NOT NULL;
        """))
        print(f"Filas actualizadas: {updated.rowcount}")

        print("3. Creando índice optimizado idx_ubi_no_oficial...")
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ubi_no_oficial 
            ON sar_archivo.ubicacion (UPPER(TRIM(no_oficial)));
        """))
        session.commit()
        print("✓ Migración ejecutada exitosamente y confirmada (COMMIT).")

if __name__ == "__main__":
    run_safe_migration()
