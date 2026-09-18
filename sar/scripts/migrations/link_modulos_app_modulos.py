"""
MIGRACIÓN DDL/DML: Relación sar_seguridad.modulo -> sar_seguridad.app_modulo (Alternativa 2)
===========================================================================================
Objetivo:
1. Añadir columna app_modulo_id a sar_seguridad.modulo con Foreign Key a app_modulo.
2. Actualizar el orden canónico y asociar app_modulo_id a los módulos existentes de CTRL_REF (1.0 - 3.5).
3. Insertar e indexar canónicamente submódulos granulares ADM:* y PROCESOS_ESPECIALES para ADMIN (app_modulo_id = 1).
4. Asociar módulos de R2F_CANCUN a app_modulo_id = 6 con orden 8.0, 8.1, 8.2.
5. Desactivar el módulo redundante REFERENCIAS (activo = FALSE), migrando previamente sus permisos a DERECHOS.
6. Generar permisos correspondientes en sar_seguridad.permiso y asignarlos al rol ADMINISTRADOR.

Estándar: SAR-AI-PROMPTS-001 / 10_SAR-DB-001 v3.0 / SAR-SEC-003
"""

import sys
import os
from pathlib import Path

# Configurar entorno
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

# Force postgres owner user for DDL migrations
os.environ["DB_USER"] = "postgres"
if "DB_PASSWORD" not in os.environ:
    os.environ["DB_PASSWORD"] = "postgres"

from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

def run_migration():
    print("====================================================================")
    print("INICIANDO MIGRACIÓN: Relación modulo -> app_modulo (Alternativa 2)")
    print("====================================================================")

    db = DatabaseConnector()
    with db.get_session() as conn:
        # 1. Añadir columna app_modulo_id si no existe
        print("[PASO 1] Verificando/añadiendo columna 'app_modulo_id' en sar_seguridad.modulo...")
        conn.execute(text("""
            ALTER TABLE sar_seguridad.modulo
            ADD COLUMN IF NOT EXISTS app_modulo_id INTEGER NULL
            REFERENCES sar_seguridad.app_modulo(app_modulo_id) ON DELETE SET NULL;
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_modulo_app_modulo
            ON sar_seguridad.modulo(app_modulo_id);
        """))
        print("  -> Columna e índice verificados con éxito.")

        # 2. Mapear IDs de app_modulo
        print("[PASO 2] Consultando IDs de app_modulo...")
        result = conn.execute(text("SELECT app_modulo_id, codigo FROM sar_seguridad.app_modulo;")).fetchall()
        app_mod_map = {row[1]: row[0] for row in result}
        print(f"  -> Mapeo obtenido: {app_mod_map}")

        id_admin = app_mod_map.get("ADMIN", 1)
        id_ctrl_ref = app_mod_map.get("CTRL_REF", 2)
        id_r2f_cancun = app_mod_map.get("R2F_CANCUN", 6)

        # 3. Actualizar submódulos de CTRL_REF (1.0 a 3.5)
        print("[PASO 3] Actualizando orden y app_modulo_id para CTRL_REF...")
        ctrl_ref_updates = [
            ("DASHBOARD", 1.0),
            ("ORDENES", 2.0),
            ("SOLICITUDES", 2.3),
            ("DERECHOS", 2.4),
            ("CONTROL_DERECHOS", 3.0),
            ("CTRL:INVENTARIO", 3.1),
            ("CTRL:ASIGNAR_DERECHO", 3.2),
            ("CTRL:ASIGNAR_VALIDAR", 3.3),
            ("CTRL:RESERVA_DERECHO", 3.4),
            ("CTRL:GESTION_LOTES", 3.5),
        ]
        for cod, ord_val in ctrl_ref_updates:
            conn.execute(text("""
                UPDATE sar_seguridad.modulo
                SET app_modulo_id = :app_id, orden = :ord_val, activo = TRUE
                WHERE codigo = :cod;
            """), {"app_id": id_ctrl_ref, "ord_val": ord_val, "cod": cod})

        # 4. Migrar permisos de REFERENCIAS a DERECHOS y desactivar REFERENCIAS
        print("[PASO 4] Consolidando módulo REFERENCIAS hacia DERECHOS...")
        res_ref = conn.execute(text("SELECT modulo_id FROM sar_seguridad.modulo WHERE codigo = 'REFERENCIAS';")).fetchone()
        res_der = conn.execute(text("SELECT modulo_id FROM sar_seguridad.modulo WHERE codigo = 'DERECHOS';")).fetchone()

        if res_ref and res_der:
            mod_id_ref = res_ref[0]
            mod_id_der = res_der[0]

            # Copiar asignaciones de rol_permiso vinculadas a REFERENCIAS hacia DERECHOS si no existen
            conn.execute(text("""
                INSERT INTO sar_seguridad.rol_permiso (rol_id, permiso_id)
                SELECT rp.rol_id, p_der.permiso_id
                FROM sar_seguridad.rol_permiso rp
                JOIN sar_seguridad.permiso p_ref ON rp.permiso_id = p_ref.permiso_id
                JOIN sar_seguridad.permiso p_der ON p_ref.accion_id = p_der.accion_id AND p_der.modulo_id = :der_id
                WHERE p_ref.modulo_id = :ref_id
                ON CONFLICT (rol_id, permiso_id) DO NOTHING;
            """), {"ref_id": mod_id_ref, "der_id": mod_id_der})

            # Desactivar REFERENCIAS
            conn.execute(text("""
                UPDATE sar_seguridad.modulo
                SET activo = FALSE, app_modulo_id = :app_id, orden = 99.0
                WHERE modulo_id = :ref_id;
            """), {"app_id": id_ctrl_ref, "ref_id": mod_id_ref})
            print("  -> Permisos clonados a DERECHOS y REFERENCIAS desactivado (activo = FALSE).")

        # 5. Insertar / Actualizar módulos de ADMIN (Alternativa 2: Módulos y Submódulos Atómicos)
        print("[PASO 5] Configurando módulos y submódulos de ADMIN (Alternativa 2)...")
        admin_modules = [
            # 4.0 Sección Seguridad
            ("SEGURIDAD", "Seguridad", "Módulo de Seguridad del Sistema", 4.0),
            ("ADM:USUARIOS", "Usuarios", "Gestión de Usuarios del Sistema", 4.1),
            ("ADM:ROLES", "Roles y Perfiles", "Gestión de Roles y Perfiles", 4.2),
            ("ADM:PERMISOS", "Permisos", "Matriz de Permisos por Rol", 4.3),
            ("ADM:MODULOS", "Módulos", "Catálogo de Módulos del Sistema", 4.4),
            ("ADM:ACCIONES", "Acciones", "Catálogo de Acciones del Sistema", 4.5),

            # 5.0 Sección Catálogos
            ("CATALOGOS", "Catálogos", "Gestión de Catálogos Maestros", 5.0),
            ("ADM:CAT_NEGOCIO", "Catálogos de Negocio", "Catálogos de Negocio (Tipos de Orden, etc.)", 5.1),
            ("ADM:GEOGRAFIA", "Geografía", "Catálogo de Geografía (Plazas, Ciudades, Sitios)", 5.2),
            ("ADM:RFCS", "Empresas y RFCs", "Catálogo de Empresas y RFCs", 5.3),
            ("ADM:ESTADOS", "Estados del Sistema", "Catálogo de Estados de Órdenes y Referencias", 5.4),

            # 6.0 Sección Configuración
            ("CONFIGURACION", "Configuración", "Configuración General y Parámetros del Sistema", 6.0),
            ("ADM:PARAMETROS", "Parámetros", "Parámetros del Sistema (settings)", 6.1),
            ("ADM:LOCALIZADORES", "Localizadores", "Configuración de Localizadores de Folios", 6.2),

            # 7.0 Sección Procesos Especiales
            ("PROCESOS_ESPECIALES", "Procesos Especiales", "Módulo de Procesos Especiales y Cargas Masivas", 7.0),
            ("ADM:CARGA_MASIVA", "Carga Masiva de Órdenes", "Proceso Especial: Carga Masiva de Órdenes", 7.1),
            ("ADM:MIGRACION", "Migración Fojas/Testimonios", "Proceso Especial: Migración de Fojas y Testimonios", 7.2),
            ("ADM:RESERVA_MASIVA", "Reserva Masiva de Derechos", "Proceso Especial: Reserva Masiva de Derechos", 7.3),
            ("ADM:UPDATE_FACTURAS", "Actualización de Facturas", "Proceso Especial: Actualización Masiva de Facturas", 7.4),
        ]

        for cod, nom, desc, ord_val in admin_modules:
            # Upsert en sar_seguridad.modulo
            conn.execute(text("""
                INSERT INTO sar_seguridad.modulo (codigo, nombre, descripcion, activo, orden, app_modulo_id)
                VALUES (:cod, :nom, :desc, TRUE, :ord_val, :app_id)
                ON CONFLICT (codigo) DO UPDATE
                SET nombre = EXCLUDED.nombre,
                    descripcion = EXCLUDED.descripcion,
                    activo = TRUE,
                    orden = EXCLUDED.orden,
                    app_modulo_id = EXCLUDED.app_modulo_id;
            """), {"cod": cod, "nom": nom, "desc": desc, "ord_val": ord_val, "app_id": id_admin})

        # 6. Actualizar módulos de R2F_CANCUN
        print("[PASO 6] Configurando módulos de R2F_CANCUN...")
        r2f_modules = [
            ("FOLIOS_CANCUN", "Folios Cancún", "Control de Folios Cancún", 8.0),
            ("RECIBOS_CANCUN", "Recibos Cancún", "Emisión de Recibos Cancún", 8.1),
            ("FACTURAS_CANCUN", "Facturación Cancún", "Facturación Cancún", 8.2),
        ]
        for cod, nom, desc, ord_val in r2f_modules:
            conn.execute(text("""
                INSERT INTO sar_seguridad.modulo (codigo, nombre, descripcion, activo, orden, app_modulo_id)
                VALUES (:cod, :nom, :desc, TRUE, :ord_val, :app_id)
                ON CONFLICT (codigo) DO UPDATE
                SET nombre = EXCLUDED.nombre,
                    descripcion = EXCLUDED.descripcion,
                    activo = TRUE,
                    orden = EXCLUDED.orden,
                    app_modulo_id = EXCLUDED.app_modulo_id;
            """), {"cod": cod, "nom": nom, "desc": desc, "ord_val": ord_val, "app_id": id_r2f_cancun})

        # 7. Generar permisos para los nuevos módulos en sar_seguridad.permiso
        print("[PASO 7] Generando permisos (sar_seguridad.permiso) y asignando al rol ADMINISTRADOR...")
        acciones = conn.execute(text("SELECT accion_id, codigo FROM sar_seguridad.accion;")).fetchall()
        roles_admin = conn.execute(text("SELECT rol_id FROM sar_seguridad.rol WHERE nombre = 'ADMINISTRADOR';")).fetchall()
        admin_rol_id = roles_admin[0][0] if roles_admin else None

        # Para cada módulo nuevo de ADMIN y R2F, asegurar que existan los permisos CRUD/VER/ACCEDER
        # Obtener todos los módulos activos
        modulos = conn.execute(text("SELECT modulo_id, codigo FROM sar_seguridad.modulo WHERE activo = TRUE;")).fetchall()

        permisos_creados = 0
        permisos_asignados = 0

        for mod_id, mod_cod in modulos:
            for acc_id, acc_cod in acciones:
                # Crear permiso si no existe
                res = conn.execute(text("""
                    INSERT INTO sar_seguridad.permiso (modulo_id, accion_id, activo)
                    VALUES (:m_id, :a_id, TRUE)
                    ON CONFLICT (modulo_id, accion_id) DO NOTHING
                    RETURNING permiso_id;
                """), {"m_id": mod_id, "a_id": acc_id}).fetchone()

                if res:
                    permisos_creados += 1
                    p_id = res[0]
                else:
                    p_row = conn.execute(text("""
                        SELECT permiso_id FROM sar_seguridad.permiso
                        WHERE modulo_id = :m_id AND accion_id = :a_id;
                    """), {"m_id": mod_id, "a_id": acc_id}).fetchone()
                    p_id = p_row[0] if p_row else None

                # Si es rol ADMINISTRADOR, asignar permiso automáticamente
                if admin_rol_id and p_id:
                    res_rp = conn.execute(text("""
                        INSERT INTO sar_seguridad.rol_permiso (rol_id, permiso_id)
                        VALUES (:r_id, :p_id)
                        ON CONFLICT (rol_id, permiso_id) DO NOTHING
                        RETURNING rol_id;
                    """), {"r_id": admin_rol_id, "p_id": p_id}).fetchone()
                    if res_rp:
                        permisos_asignados += 1

        # Confirmar todos los cambios transaccionales
        conn.commit()
        print("  -> Transacción confirmada en base de datos.")

        # 8. Reporte final de validación
        print("[PASO 8] Generando reporte de validación final...")
        report = conn.execute(text("""
            SELECT m.orden, m.codigo, m.descripcion, m.activo, am.codigo AS app_modulo
            FROM sar_seguridad.modulo m
            LEFT JOIN sar_seguridad.app_modulo am ON m.app_modulo_id = am.app_modulo_id
            ORDER BY m.orden ASC;
        """)).fetchall()

        print("\n--- REPORTE CANÓNICO DE MÓDULOS EN BASE DE DATOS ---")
        print(f"{'ORDEN':<7} | {'CÓDIGO':<25} | {'APP_MODULO':<12} | {'ACTIVO':<6} | {'DESCRIPCIÓN'}")
        print("-" * 85)
        for r in report:
            print(f"{str(r[0]):<7} | {r[1]:<25} | {str(r[4]):<12} | {str(r[3]):<6} | {r[2]}")
        print("-" * 85)

    print("MIGRACIÓN FINALIZADA SATISFACTORIAMENTE.")

if __name__ == "__main__":
    run_migration()
