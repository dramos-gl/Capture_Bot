import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sar.src.storage.db_connector import DatabaseConnector
from sar.src.services.admin_service import AdminService
from sar.src.storage.models import Sesion

def test_session_validation():
    print("Iniciando prueba de validación de Sesión Activa en AdminService...")
    db = DatabaseConnector()
    
    with db.get_session() as session:
        service = AdminService(session)
        
        # 1. Crear una sesión EXPIRADA
        expired_session = Sesion(
            usuario_id=1,
            equipo_nombre="TEST_EXPIRED",
            estado="EXPIRADA"
        )
        session.add(expired_session)
        session.flush()
        
        # 2. Intentar guardar rol con sesión expirada (debe fallar)
        print("Intentando guardar un rol con sesión EXPIRADA...")
        rol_data = {"codigo": "TEST_FAIL_ROLE", "nombre": "Fail Role", "activo": True}
        try:
            service.save_rol(usuario_id=1, sesion_id=expired_session.sesion_id, data=rol_data)
            print("ERROR: La operación se permitió con una sesión expirada.")
            assert False, "Fallo en la validación de seguridad de sesión activa."
        except PermissionError as pe:
            print(f"Éxito: Se denegó la operación correctamente con error: {pe}")
            
        # 3. Crear una sesión ACTIVA
        active_session = Sesion(
            usuario_id=1,
            equipo_nombre="TEST_ACTIVE",
            estado="ACTIVA"
        )
        session.add(active_session)
        session.flush()
        
        # 4. Intentar guardar rol con sesión activa (debe pasar)
        print("Intentando guardar un rol con sesión ACTIVA...")
        try:
            rol = service.save_rol(usuario_id=1, sesion_id=active_session.sesion_id, data=rol_data)
            print(f"Éxito: Operación permitida y rol guardado ID={rol.rol_id}.")
        except PermissionError as pe:
            print(f"ERROR: Se denegó la operación con una sesión activa: {pe}")
            assert False, "Fallo en la validación de sesión activa."
            
        # Revertir todo para no ensuciar la BD
        session.rollback()
        print("\n¡Prueba de sesión activa completada con ÉXITO!")

if __name__ == "__main__":
    test_session_validation()
