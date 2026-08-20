"""Inspeccion de schema y rutas reales de facturas."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

def main():
    db = DatabaseConnector()
    with db.get_session() as s:
        print("=== COLUMNAS DE sar_archivo.factura ===")
        cols = s.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema='sar_archivo' AND table_name='factura' ORDER BY ordinal_position"
        )).all()
        for c in cols:
            print(f"  {c[0]} ({c[1]})")

        print("\n=== MUESTRA DE RUTAS DE FACTURAS (CADURMA) ===")
        rows = s.execute(text(
            "SELECT f.factura_id, f.referencia_id, f.pdf_path, f.pdf2_path, f.delegacion "
            "FROM sar_archivo.factura f "
            "JOIN sar_produccion.referencia r ON f.referencia_id = r.referencia_id "
            "WHERE r.grupo_id IN (23,24,25,26,27,28) "
            "AND f.pdf_path IS NOT NULL "
            "LIMIT 8"
        )).mappings().all()
        for r in rows:
            print(f"  factura_id={r['factura_id']} | ref={r['referencia_id']}")
            print(f"    pdf_path:  {r['pdf_path']}")
            print(f"    pdf2_path: {r['pdf2_path']}")
            print(f"    delegacion: {r['delegacion']}")

if __name__ == "__main__":
    main()
