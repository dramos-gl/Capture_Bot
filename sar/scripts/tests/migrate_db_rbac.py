import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

def migrate_rbac():
    print("Iniciando migración de base de datos para Control de Acceso y RBAC...")
    db = DatabaseConnector()
    
    with db.get_session() as session:
        # 1. Crear tabla rol_app_modulo si no existe
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS sar_seguridad.rol_app_modulo (
                rol_id BIGINT NOT NULL,
                app_modulo_id INTEGER NOT NULL,
                PRIMARY KEY (rol_id, app_modulo_id),
                FOREIGN KEY (rol_id) REFERENCES sar_seguridad.rol(rol_id) ON DELETE CASCADE,
                FOREIGN KEY (app_modulo_id) REFERENCES sar_seguridad.app_modulo(app_modulo_id) ON DELETE CASCADE
            );
        """))
        print("Tabla sar_seguridad.rol_app_modulo verificada/creada.")
        
        # 2. Insertar módulo CONFIGURACION si no existe
        session.execute(text("""
            INSERT INTO sar_seguridad.modulo (codigo, nombre, descripcion, activo)
            VALUES ('CONFIGURACION', 'Configuración General', 'Módulo de parámetros del sistema y localizadores', TRUE)
            ON CONFLICT (codigo) DO NOTHING;
        """))
        print("Módulo CONFIGURACION verificado/insertado.")
        
        # 3. Generar permisos cruzados (intersección modulo x accion) para CONFIGURACION
        session.execute(text("""
            INSERT INTO sar_seguridad.permiso (modulo_id, accion_id, activo)
            SELECT m.modulo_id, a.accion_id, TRUE
            FROM sar_seguridad.modulo m
            CROSS JOIN sar_seguridad.accion a
            WHERE m.codigo = 'CONFIGURACION'
            ON CONFLICT (modulo_id, accion_id) DO NOTHING;
        """))
        print("Permisos para CONFIGURACION generados.")

        # 4. Asignar permisos de CONFIGURACION al rol ADMINISTRADOR
        session.execute(text("""
            INSERT INTO sar_seguridad.rol_permiso (rol_id, permiso_id)
            SELECT (SELECT rol_id FROM sar_seguridad.rol WHERE codigo = 'ADMINISTRADOR'), p.permiso_id
            FROM sar_seguridad.permiso p
            JOIN sar_seguridad.modulo m ON p.modulo_id = m.modulo_id
            WHERE m.codigo = 'CONFIGURACION'
            ON CONFLICT (rol_id, permiso_id) DO NOTHING;
        """))
        print("Permisos de CONFIGURACION asignados al ADMINISTRADOR.")

        # 5. Poblar rol_app_modulo
        # Borrar primero duplicados potenciales para evitar conflictos
        session.execute(text("TRUNCATE TABLE sar_seguridad.rol_app_modulo CASCADE;"))
        
        # ADMINISTRADOR recibe ADMIN, CTRL_REF, BOT_FACE_A, BOT_C
        session.execute(text("""
            INSERT INTO sar_seguridad.rol_app_modulo (rol_id, app_modulo_id)
            SELECT (SELECT rol_id FROM sar_seguridad.rol WHERE codigo = 'ADMINISTRADOR'), app_modulo_id
            FROM sar_seguridad.app_modulo;
        """))
        
        # OPERADOR recibe CTRL_REF, BOT_FACE_A, BOT_C
        session.execute(text("""
            INSERT INTO sar_seguridad.rol_app_modulo (rol_id, app_modulo_id)
            SELECT (SELECT rol_id FROM sar_seguridad.rol WHERE codigo = 'OPERADOR'), app_modulo_id
            FROM sar_seguridad.app_modulo
            WHERE codigo IN ('CTRL_REF', 'BOT_FACE_A', 'BOT_C');
        """))
        print("Relaciones de rol_app_modulo (Nivel 1 de acceso) establecidas correctamente.")
        
        session.commit()
        print("¡MIGRACIÓN DE RBAC Y ACCESOS FINALIZADA CON ÉXITO!")

if __name__ == "__main__":
    migrate_rbac()
