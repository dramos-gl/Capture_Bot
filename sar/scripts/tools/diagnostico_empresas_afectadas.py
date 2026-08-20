"""
Diagnostico de las 2 empresas afectadas: CAD1001263P4 (CADURMA) e INM1309035E8 (INMOCCIDENTE)
Verifica referencias, facturas y archivos PDF vinculados para evaluar el impacto de la migracion.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

RFCS_AFECTADOS = ('CAD1001263P4', 'INM1309035E8')

def main():
    db = DatabaseConnector()
    with db.get_session() as s:

        print("=" * 90)
        print("  DIAGNOSTICO DE EMPRESAS MAL CLASIFICADAS - ORDEN 4")
        print("=" * 90)

        # 1. Resumen por grupo y solicitud
        rows = s.execute(text("""
            SELECT
                r.rfc,
                r.razon_social,
                c.alias            AS concepto,
                d.nombre           AS delegacion_solicitud,
                gr.grupo_id,
                sol.solicitud_id,
                sol.consecutivo_inicio,
                sol.consecutivo_fin,
                COUNT(ref.referencia_id)   AS total_refs,
                COUNT(f.factura_id)        AS total_facturas,
                COUNT(ap.archivo_id)       AS total_archivos_pdf,
                MIN(ap.ruta_archivo)       AS ruta_muestra
            FROM sar_produccion.referencia ref
            JOIN sar_produccion.grupo_referencia gr  ON ref.grupo_id    = gr.grupo_id
            JOIN sar_produccion.solicitud sol         ON ref.solicitud_id = sol.solicitud_id
            JOIN sar_catalogo.rfc r                   ON gr.rfc_id        = r.rfc_id
            JOIN sar_catalogo.concepto c              ON gr.concepto_id   = c.concepto_id
            JOIN sar_catalogo.delegacion d            ON sol.delegacion_id = d.delegacion_id
            LEFT JOIN sar_archivo.factura f           ON f.referencia_id  = ref.referencia_id
            LEFT JOIN sar_archivo.archivo_pdf ap      ON ap.referencia_id = ref.referencia_id
            WHERE gr.orden_id = 4
              AND r.rfc = ANY(:rfcs)
            GROUP BY r.rfc, r.razon_social, c.alias, d.nombre, gr.grupo_id,
                     sol.solicitud_id, sol.consecutivo_inicio, sol.consecutivo_fin
            ORDER BY r.rfc, c.alias, sol.solicitud_id
        """), {"rfcs": list(RFCS_AFECTADOS)}).mappings().all()

        total_refs      = 0
        total_facturas  = 0
        total_archivos  = 0

        for row in rows:
            print(f"\nRFC: {row['rfc']} | {row['razon_social'][:40]}")
            print(f"  Concepto:        {row['concepto']}")
            print(f"  Delegacion (sol): {row['delegacion_solicitud']}")
            print(f"  grupo_id:        {row['grupo_id']}  |  solicitud_id: {row['solicitud_id']}")
            print(f"  Consecutivos:    {row['consecutivo_inicio']} - {row['consecutivo_fin']}")
            print(f"  Referencias:     {row['total_refs']}")
            print(f"  Facturas:        {row['total_facturas']}")
            print(f"  Archivos PDF:    {row['total_archivos_pdf']}")
            if row['ruta_muestra']:
                print(f"  Ruta muestra:    {row['ruta_muestra']}")
            total_refs     += row['total_refs']
            total_facturas += row['total_facturas']
            total_archivos += row['total_archivos_pdf']

        print("\n" + "=" * 90)
        print(f"  TOTALES: {total_refs} referencias | {total_facturas} facturas | {total_archivos} archivos PDF")
        print("=" * 90)

        # 2. Verificar si hay asignaciones activas en lote
        asignaciones = s.execute(text("""
            SELECT COUNT(ar.asignacion_referencia_id) AS total_asignaciones
            FROM sar_archivo.asignacion_referencia ar
            JOIN sar_produccion.referencia ref ON ar.referencia_id = ref.referencia_id
            JOIN sar_produccion.grupo_referencia gr ON ref.grupo_id = gr.grupo_id
            JOIN sar_catalogo.rfc r ON gr.rfc_id = r.rfc_id
            WHERE gr.orden_id = 4
              AND r.rfc = ANY(:rfcs)
        """), {"rfcs": list(RFCS_AFECTADOS)}).scalar()

        print(f"\n  Asignaciones en lote activas: {asignaciones}")

        # 3. Muestra de rutas de facturas descargadas
        print("\n  MUESTRA DE RUTAS DE FACTURAS:")
        rutas = s.execute(text("""
            SELECT DISTINCT f.pdf_path, f.xml_path
            FROM sar_archivo.factura f
            JOIN sar_produccion.referencia ref ON f.referencia_id = ref.referencia_id
            JOIN sar_produccion.grupo_referencia gr ON ref.grupo_id = gr.grupo_id
            JOIN sar_catalogo.rfc r ON gr.rfc_id = r.rfc_id
            WHERE gr.orden_id = 4
              AND r.rfc = ANY(:rfcs)
              AND f.pdf_path IS NOT NULL
            LIMIT 10
        """), {"rfcs": list(RFCS_AFECTADOS)}).mappings().all()

        for ruta in rutas:
            print(f"  PDF: {ruta['pdf_path']}")
            print(f"  XML: {ruta['xml_path']}")
            print()

        print("=" * 90)
        print("  FIN DEL DIAGNOSTICO")
        print("=" * 90)

if __name__ == "__main__":
    main()
