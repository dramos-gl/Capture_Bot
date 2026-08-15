"""
Script de consulta: Muestra la estructura de una orden (grupos + solicitudes)
con todos los IDs necesarios para la carga masiva de referencias.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

ORDEN_ID = 4  # <-- Cambiar si se necesita otra orden

def main():
    db = DatabaseConnector()
    
    with db.get_session() as session:
        # 1. Info de la orden
        orden_info = session.execute(text("""
            SELECT o.orden_id, o.folio, o.descripcion, o.fecha_creacion,
                   es.codigo AS estado, u.nombre AS creador
            FROM sar_produccion.orden_generacion o
            JOIN sar_catalogo.estado_sistema es ON o.estado_id = es.estado_id
            JOIN sar_seguridad.usuario u ON o.usuario_id = u.usuario_id
            WHERE o.orden_id = :oid
        """), {"oid": ORDEN_ID}).mappings().first()
        
        if not orden_info:
            print(f"ERROR: No se encontro la orden con ID {ORDEN_ID}")
            return
        
        print("=" * 80)
        print(f"  ORDEN: {orden_info['folio']}")
        print(f"  ID: {orden_info['orden_id']} | Estado: {orden_info['estado']}")
        print(f"  Descripcion: {orden_info['descripcion']}")
        print(f"  Creador: {orden_info['creador']} | Fecha: {orden_info['fecha_creacion']}")
        print("=" * 80)
        
        # 2. Grupos de referencia
        grupos = session.execute(text("""
            SELECT gr.grupo_id, r.rfc, r.razon_social, c.alias AS concepto_alias,
                   c.nombre AS concepto_nombre, gr.cantidad_solicitada,
                   gr.cantidad_generada, gr.cantidad_autorizada,
                   es.codigo AS estado
            FROM sar_produccion.grupo_referencia gr
            JOIN sar_catalogo.rfc r ON gr.rfc_id = r.rfc_id
            JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
            JOIN sar_catalogo.estado_sistema es ON gr.estado_id = es.estado_id
            WHERE gr.orden_id = :oid
            ORDER BY gr.grupo_id
        """), {"oid": ORDEN_ID}).mappings().all()
        
        print(f"\n GRUPOS DE REFERENCIA ({len(grupos)} grupos)")
        print("-" * 80)
        print(f"{'grupo_id':<10} {'RFC':<15} {'Concepto':<8} {'Solicitadas':<12} {'Generadas':<10} {'Estado':<12}")
        print("-" * 80)
        
        for g in grupos:
            print(f"{g['grupo_id']:<10} {g['rfc']:<15} {g['concepto_alias'] or 'N/A':<8} "
                  f"{g['cantidad_solicitada']:<12} {g['cantidad_generada']:<10} {g['estado']:<12}")
            print(f"           -> {g['razon_social'][:50]}")
        
        # 3. Solicitudes por grupo
        print(f"\n SOLICITUDES POR GRUPO")
        print("-" * 100)
        print(f"{'solicitud_id':<14} {'grupo_id':<10} {'Delegacion':<18} {'Cant.Sol':<10} "
              f"{'Consec.Ini':<12} {'Consec.Fin':<12} {'Estado':<12}")
        print("-" * 100)
        
        solicitudes = session.execute(text("""
            SELECT s.solicitud_id, s.grupo_id, d.nombre AS delegacion,
                   s.cantidad_solicitada, s.cantidad_generada,
                   s.consecutivo_inicio, s.consecutivo_fin,
                   es.codigo AS estado
            FROM sar_produccion.solicitud s
            JOIN sar_catalogo.delegacion d ON s.delegacion_id = d.delegacion_id
            JOIN sar_catalogo.estado_sistema es ON s.estado_id = es.estado_id
            WHERE s.grupo_id IN (
                SELECT grupo_id FROM sar_produccion.grupo_referencia WHERE orden_id = :oid
            )
            ORDER BY s.grupo_id, s.solicitud_id
        """), {"oid": ORDEN_ID}).mappings().all()
        
        for s in solicitudes:
            print(f"{s['solicitud_id']:<14} {s['grupo_id']:<10} {s['delegacion']:<18} "
                  f"{s['cantidad_solicitada']:<10} {s['consecutivo_inicio']:<12} "
                  f"{s['consecutivo_fin']:<12} {s['estado']:<12}")
        
        # 4. Resumen
        total_solicitadas = sum(g['cantidad_solicitada'] for g in grupos)
        total_generadas = sum(g['cantidad_generada'] for g in grupos)
        print(f"\n RESUMEN: {total_solicitadas} referencias solicitadas, "
              f"{total_generadas} generadas, {len(solicitudes)} solicitudes")
        print("=" * 80)


if __name__ == "__main__":
    main()
