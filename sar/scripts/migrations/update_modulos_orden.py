import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

# Force postgres owner user for DDL/DML migrations
os.environ["DB_USER"] = "postgres"
if "DB_PASSWORD" not in os.environ:
    os.environ["DB_PASSWORD"] = "postgres"

from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

def update_modulos_orden():
    print("Iniciando actualización de orden secuencial para módulos en sar_seguridad.modulo...")
    db = DatabaseConnector()
    
    with db.get_session() as session:
        # Actualización de la jerarquía de orden en sar_seguridad.modulo
        modulos_orden = [
            ('DASHBOARD', 1.0),
            ('ORDENES', 2.0),
            ('SOLICITUDES', 2.1),
            ('DERECHOS', 2.2),
            ('REFERENCIAS', 2.2),
            ('CONTROL_DERECHOS', 3.0),
            ('CTRL:INVENTARIO', 3.1),
            ('CTRL:ASIGNAR_DERECHO', 3.2),
            ('CTRL:ASIGNAR_VALIDAR', 3.3),
            ('CTRL:RESERVA_DERECHO', 3.4),
            ('CTRL:GESTION_LOTES', 3.5),
            ('SEGURIDAD', 4.0),
            ('CATALOGOS', 5.0),
            ('CONFIGURACION', 6.0),
            ('FOLIOS_CANCUN', 7.0),
            ('RECIBOS_CANCUN', 7.1),
            ('FACTURAS_CANCUN', 7.2)
        ]
        
        for codigo, orden_val in modulos_orden:
            session.execute(text("""
                UPDATE sar_seguridad.modulo
                SET orden = :orden_val
                WHERE codigo = :codigo
            """), {"orden_val": orden_val, "codigo": codigo})
            
        session.commit()
        print("Módulos actualizados con nueva jerarquía de orden.")
        
        # Verificar resultados
        rows = session.execute(text("""
            SELECT modulo_id, orden, codigo, nombre, activo 
            FROM sar_seguridad.modulo 
            ORDER BY orden, modulo_id
        """)).fetchall()
        print("\n=== Catálogo sar_seguridad.modulo Actualizado ===")
        for r in rows:
            print(f"[{r.orden}] ID {r.modulo_id} - {r.codigo}: {r.nombre}")

if __name__ == "__main__":
    update_modulos_orden()
