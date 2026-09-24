"""Verification script to test connection and query seeded RBAC data."""

import sys
import os

# Añadir el directorio raíz de Proyecto_CapturaBot al path de Python para resolver importaciones
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from sar.src.storage.db_connector import DatabaseConnector
from sar.src.storage.models import Usuario, Rol


def test_connection():
    print("Iniciando prueba de conexión a PostgreSQL...")
    
    # Habilitar variables de entorno si se requieren credenciales customizadas
    # Por defecto usará: postgres:postgres@localhost:5432/db_sar o db_sar
    # Cambia los valores por defecto en tu entorno si tu usuario/clave de Postgres es distinto.
    os.environ["DB_NAME"] = "db_sar"  # Ajustado al nombre del esquema del usuario
    os.environ["DB_USER"] = "postgres"
    os.environ["DB_PASSWORD"] = ""  # Ajusta si tu contraseña es diferente

    try:
        connector = DatabaseConnector()
        print(f"Intentando conectar a: {connector.db_host}:{connector.db_port}/{connector.db_name}")
        
        with connector.get_session() as session:
            # Query el usuario admin semilla
            admin_user = session.query(Usuario).filter(Usuario.username == "admin").first()
            
            if admin_user:
                print("\n¡CONEXIÓN Y ORM CONFIGURADOS CORRECTAMENTE!")
                print(f"Usuario Encontrado: {admin_user.nombre} ({admin_user.username})")
                print(f"Correo: {admin_user.correo}")
                print(f"Estado Activo: {admin_user.activo}")
                
                # Listar roles asignados
                roles = [rol.nombre for rol in admin_user.roles]
                print(f"Roles Asignados: {', '.join(roles)}")
                
                # Listar algunos permisos del primer rol
                if admin_user.roles:
                    primer_rol = admin_user.roles[0]
                    permisos_count = len(primer_rol.permisos)
                    print(f"Cantidad de permisos en rol '{primer_rol.codigo}': {permisos_count}")
            else:
                print("\n[!] Conexión establecida pero no se encontró el usuario semilla 'admin'.")
                print("Por favor, asegúrate de haber cargado el script SQL 'sar_db.sql' en la base de datos.")
                
    except Exception as e:
        print(f"\n[ERROR] Falló la prueba de conexión a la base de datos.")
        try:
            err_msg = str(e)
        except UnicodeDecodeError:
            err_msg = repr(e)
        print(f"Detalle del error: {err_msg}")
        print("\nSugerencias de resolución:")
        print("1. Verifica que el servicio de PostgreSQL esté iniciado.")
        print("2. Valida que el usuario 'postgres' y su contraseña sean correctos.")
        print("3. Si tu contraseña de PostgreSQL no es 'postgres', puedes definirla temporalmente en tu consola ejecutando:")
        print("   $env:DB_PASSWORD=\"tu_contraseña\" (en PowerShell) o set DB_PASSWORD=tu_contraseña (en CMD) antes de correr el test.")


if __name__ == "__main__":
    test_connection()
