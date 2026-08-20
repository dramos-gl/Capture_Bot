"""
Genera la plantilla CSV mínima para la migración de referencias.
Incluye TODAS las referencias de la Orden 4 con los IDs reales de la BD.
El usuario solo necesita corregir la columna 'delegacion_id' donde sea necesario.
El script de migración ignorará las filas cuya delegacion_id no haya cambiado.
"""
import sys, os, csv
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

ORDEN_ID = 4
OUT_PATH = os.path.join(os.path.dirname(__file__), 'plantilla_migracion_orden5.csv')

def main():
    db = DatabaseConnector()
    with db.get_session() as s:
        # Catálogo de delegaciones
        deleg_rows = s.execute(text(
            "SELECT delegacion_id, nombre FROM sar_catalogo.delegacion ORDER BY delegacion_id"
        )).all()
        print("Delegaciones disponibles (usa estos IDs en la columna delegacion_id):")
        for d in deleg_rows:
            print(f"  ID={d[0]:2d} | {d[1]}")

        # Catálogo de conceptos
        con_rows = s.execute(text(
            "SELECT concepto_id, alias FROM sar_catalogo.concepto ORDER BY concepto_id"
        )).all()
        print("\nConceptos:")
        for c in con_rows:
            print(f"  ID={c[0]:2d} | {c[1]}")

        # Resumen de grupos de la Orden
        print(f"\nResumen de grupos en Orden {ORDEN_ID}:")
        resumen = s.execute(text("""
            SELECT gr.grupo_id, r.rfc, c.alias AS concepto_alias,
                   d.nombre AS delegacion_actual, d.delegacion_id,
                   COUNT(ref.referencia_id) AS total_refs
            FROM sar_produccion.grupo_referencia gr
            JOIN sar_catalogo.rfc r ON gr.rfc_id = r.rfc_id
            JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
            JOIN sar_produccion.solicitud sol ON sol.grupo_id = gr.grupo_id
            JOIN sar_catalogo.delegacion d ON sol.delegacion_id = d.delegacion_id
            JOIN sar_produccion.referencia ref ON ref.grupo_id = gr.grupo_id
            WHERE gr.orden_id = :oid
            GROUP BY gr.grupo_id, r.rfc, c.alias, d.nombre, d.delegacion_id
            ORDER BY gr.grupo_id, d.delegacion_id
        """), {"oid": ORDEN_ID}).mappings().all()

        for row in resumen:
            print(f"  grupo_id={row['grupo_id']:3d} | {row['rfc']:<15} | {row['concepto_alias']:<20} | "
                  f"Del={row['delegacion_id']} ({row['delegacion_actual']:<20}) | {row['total_refs']} refs")

        # Extraer TODAS las referencias de la Orden
        print(f"\nExtrayendo todas las referencias de la Orden {ORDEN_ID}...")
        refs = s.execute(text("""
            SELECT
                ref.referencia_portal,
                gr.rfc_id,
                r.rfc,
                gr.concepto_id,
                c.alias          AS concepto_alias,
                sol.delegacion_id,
                d.nombre         AS delegacion_actual,
                ref.grupo_id,
                sol.solicitud_id,
                ref.consecutivo_grupo
            FROM sar_produccion.referencia ref
            JOIN sar_produccion.grupo_referencia gr ON ref.grupo_id    = gr.grupo_id
            JOIN sar_produccion.solicitud sol        ON ref.solicitud_id = sol.solicitud_id
            JOIN sar_catalogo.rfc r                  ON gr.rfc_id        = r.rfc_id
            JOIN sar_catalogo.concepto c             ON gr.concepto_id   = c.concepto_id
            JOIN sar_catalogo.delegacion d           ON sol.delegacion_id = d.delegacion_id
            WHERE gr.orden_id = :oid
            ORDER BY gr.grupo_id, ref.consecutivo_grupo
        """), {"oid": ORDEN_ID}).mappings().all()

        total = len(refs)
        print(f"Total de referencias: {total}")

        with open(OUT_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'referencia_portal',  # NO modificar
                'rfc_id',             # NO modificar
                'rfc',                # Solo referencia visual
                'concepto_id',        # NO modificar
                'concepto_alias',     # Solo referencia visual
                'delegacion_id',      # <<< UNICO CAMPO A CORREGIR si está mal
                'delegacion_actual',  # Muestra la delegación actual (referencia visual)
                'grupo_id_ord4',      # NO modificar
            ])
            for r in refs:
                writer.writerow([
                    r['referencia_portal'],
                    r['rfc_id'],
                    r['rfc'],
                    r['concepto_id'],
                    r['concepto_alias'],
                    r['delegacion_id'],      # ← Corrige este valor si es incorrecto
                    r['delegacion_actual'],
                    r['grupo_id'],
                ])

        print(f"\nPlantilla generada: {OUT_PATH}")
        print(f"Total referencias exportadas: {total}")
        print("\nINSTRUCCIONES:")
        print("  1. Abre el archivo en Excel.")
        print("  2. Usa filtros por 'grupo_id_ord4' o 'rfc' para localizar")
        print("     las referencias con delegacion incorrecta.")
        print("  3. Cambia SOLO la columna 'delegacion_id' donde sea necesario.")
        print("  4. Guarda como CSV (UTF-8), mismo nombre.")
        print("  5. Ejecuta: .venv_sar\\Scripts\\python.exe sar/scripts/migrar_orden4_a_orden5.py")
        print("\n  El script de migracion solo procesara los grupos cuya")
        print("  delegacion_id haya cambiado respecto a la BD actual.")

if __name__ == "__main__":
    main()
