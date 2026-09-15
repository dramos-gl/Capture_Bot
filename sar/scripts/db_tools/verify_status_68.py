import sys, os
sys.path.insert(0, os.path.abspath("."))
from sar.src.storage.db_connector import DatabaseConnector
from sar.src.storage.repositories import ProduccionRepository
from sqlalchemy import text

db = DatabaseConnector()
with db.get_session() as s:
    print("=== ESTADOS DE ORDEN_GENERACION EN BD ===")
    stmt = text("SELECT estado_id, entidad, codigo, descripcion FROM sar_catalogo.estado_sistema WHERE entidad = 'orden_generacion' ORDER BY estado_id")
    res = s.execute(stmt).fetchall()
    for row in res:
        print(f"ID: {row[0]:<4} | Código: {row[2]:<25} | Descripción: {row[3]}")
    
    print("\n=== ÓRDENES Y SU ESTADO VISUAL RESUELTO ===")
    repo = ProduccionRepository(s)
    ordenes = repo.get_ordenes(include_rejected=True)
    for o in ordenes:
        print(f"Orden ID: {o['orden_id']} | Folio: {o['folio']} | Estado: {o['estado']} | Solicitadas: {o['total_solicitadas']} | Generadas: {o['total_generadas']}")

    print("\n=== VALIDACIÓN DE ACCIÓN MASIVA (check_orden_ready_for_masivo) ===")
    for o in ordenes:
        ready_info = repo.check_orden_ready_for_masivo(o['orden_id'])
        print(f"Orden ID: {o['orden_id']} (Folio: {o['folio']}) -> Ready: {ready_info.get('ready')}")
