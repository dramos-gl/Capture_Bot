from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

db = DatabaseConnector()
with db.get_session() as session:
    res = session.execute(text("""
        SELECT estado_id, entidad, codigo, descripcion 
        FROM sar_catalogo.estado_sistema 
        ORDER BY entidad, estado_id;
    """)).fetchall()
    
    print(f"Total estados: {len(res)}")
    for row in res:
        print(f"ID: {row.estado_id} | Entidad: {row.entidad} | Código: {row.codigo} | Descripción: {row.descripcion}")
