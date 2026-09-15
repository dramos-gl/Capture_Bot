import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sar.src.storage.db_connector import DatabaseConnector
from sar.src.services.security_service import SecurityService
from sar.src.services.admin_service import AdminService
from sar.src.storage.repositories import UsuarioRepository

def run_verification():
    print("Verificando Niveles de Acceso y RBAC...")
    db = DatabaseConnector()
    
    with db.get_session() as session:
        sec = SecurityService(session)
        repo = UsuarioRepository(session)
        
        # 1. Obtener usuario admin
        admin_user = repo.get_by_username("admin")
        if not admin_user:
            print("ERROR: Usuario admin no encontrado.")
            return
            
        print(f"\nUsuario: {admin_user.username}")
        # Verificar Nivel 1
        for mod in ["ADMIN", "CTRL_REF", "BOT_FACE_A", "BOT_C"]:
            has_access = sec.has_app_module_access(admin_user.usuario_id, mod)
            print(f"  - ¿Acceso a Módulo {mod}?: {has_access}")
            
        # Verificar Nivel 2
        print(f"  - ¿Permiso (SEGURIDAD, LEER)?: {sec.has_permission(admin_user.usuario_id, 'SEGURIDAD', 'LEER')}")
        print(f"  - ¿Permiso (CONFIGURACION, EDITAR)?: {sec.has_permission(admin_user.usuario_id, 'CONFIGURACION', 'EDITAR')}")
        
        # 2. Crear un usuario operador de prueba si no existe
        op_username = "op_test"
        op_user = repo.get_by_username(op_username)
        
        if not op_user:
            print(f"\nCreando usuario de prueba '{op_username}' con rol OPERADOR...")
            from argon2 import PasswordHasher
            ph = PasswordHasher()
            pwd_hash = ph.hash("op123456")
            
            from sar.src.storage.models import Usuario, Rol
            from sqlalchemy import select
            op_rol = session.execute(select(Rol).where(Rol.codigo == "OPERADOR")).scalar_one()
            
            op_user = Usuario(
                username=op_username,
                nombre="Operador de Prueba",
                correo="op@test.com",
                password_hash=pwd_hash,
                activo=True
            )
            op_user.roles.append(op_rol)
            session.add(op_user)
            session.flush()
            
        print(f"\nUsuario: {op_user.username}")
        # Verificar Nivel 1
        for mod in ["ADMIN", "CTRL_REF", "BOT_FACE_A", "BOT_C"]:
            has_access = sec.has_app_module_access(op_user.usuario_id, mod)
            print(f"  - ¿Acceso a Módulo {mod}?: {has_access}")
            
        # Verificar Nivel 2
        print(f"  - ¿Permiso (SEGURIDAD, LEER)?: {sec.has_permission(op_user.usuario_id, 'SEGURIDAD', 'LEER')}")
        print(f"  - ¿Permiso (CONFIGURACION, EDITAR)?: {sec.has_permission(op_user.usuario_id, 'CONFIGURACION', 'EDITAR')}")
        print(f"  - ¿Permiso (ORDENES, LEER)?: {sec.has_permission(op_user.usuario_id, 'ORDENES', 'LEER')}")
        print(f"  - ¿Permiso (SOLICITUDES, EJECUTAR)?: {sec.has_permission(op_user.usuario_id, 'SOLICITUDES', 'EJECUTAR')}")
        
        # Eliminar el usuario de prueba para dejar la BD limpia
        print(f"\nEliminando usuario de prueba '{op_username}'...")
        session.delete(op_user)
        session.commit()
        
    print("\n¡Verificación completada con éxito!")

if __name__ == "__main__":
    run_verification()
