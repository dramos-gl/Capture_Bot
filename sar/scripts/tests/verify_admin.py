import sys
import os

# Ensure the root dir is in Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sar.src.storage.db_connector import DatabaseConnector
from sar.src.services.admin_service import AdminService

def main():
    db_connector = DatabaseConnector()
    
    with db_connector.get_session() as session:
        service = AdminService(session)
        
        # Create a dummy active session for testing
        from sar.src.storage.models import Sesion
        dummy_session = Sesion(
            usuario_id=1,
            equipo_nombre="LOCAL_TEST",
            estado="ACTIVA"
        )
        session.add(dummy_session)
        session.flush()
        
        # Test Save Rol
        print("Testing Save Rol...")
        rol_data = {"codigo": "TEST_ROLE", "nombre": "Role for testing", "activo": True}
        rol = service.save_rol(usuario_id=1, sesion_id=dummy_session.sesion_id, data=rol_data)
        session.flush()
        print(f"Created Rol: ID={rol.rol_id}, Nombre={rol.nombre}")

        # Test Save Municipio
        print("Testing Save Municipio...")
        mun_data = {"nombre": "TEST_MUNICIPIO", "activo": True}
        mun = service.save_municipio(usuario_id=1, sesion_id=dummy_session.sesion_id, data=mun_data)
        session.flush()
        print(f"Created Municipio: ID={mun.municipio_id}, Nombre={mun.nombre}")

        # Test Save Localizador
        print("Testing Save Localizador...")
        loc_data = {"nombre_clave": "TEST_BTN", "valor_selector": "#test-btn", "activo": True}
        loc = service.save_localizador(usuario_id=1, sesion_id=dummy_session.sesion_id, data=loc_data)
        session.flush()
        print(f"Created Localizador: ID={loc.localizador_id}, Nombre Clave={loc.nombre_clave}")
        
        # Verify Audit Log
        from sar.src.storage.models import AuditoriaEvento
        from sqlalchemy import select
        
        stmt = select(AuditoriaEvento).order_by(AuditoriaEvento.evento_auditoria_id.desc()).limit(3)
        logs = list(session.execute(stmt).scalars().all())
        
        print("\nAudit Logs recorded:")
        for log in logs:
            print(f"- Modulo: {log.modulo}, Event ID: {log.evento_id}")
            print(f"  New Val: {log.valor_nuevo}")
            
        session.rollback()
        print("Test passed! Transaction rolled back.")

if __name__ == "__main__":
    main()
