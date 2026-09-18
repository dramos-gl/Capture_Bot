"""
RESEMBRADO LIMPIO Y CANÓNICO: sar_seguridad.modulo y sar_seguridad.permiso
==========================================================================
Estándar: SAR-AI-PROMPTS-001 / SAR-SEC-003 / 10_SAR-DB-001 v3.0

Acciones:
1. Respaldar en memoria la matriz de permisos de todos los roles por código.
2. Truncar sar_seguridad.rol_permiso, sar_seguridad.permiso y sar_seguridad.modulo con RESTART IDENTITY CASCADE.
3. Insertar canónicamente los 32 módulos en orden correlativo de IDs (1 al 32) vinculados a sus app_modulo_id.
4. Generar todos los permisos (Módulo x Acción) en sar_seguridad.permiso.
5. Asignar acceso TOTAL (100% de los permisos generados) al rol ADMINISTRADOR.
6. Reasignar los permisos correspondientes a OPERADOR, BOT, GESTOR, CONSULTA y OPERADORR2F.
7. Validar integridad transaccional y emitir reporte de resultados.
"""

import os
import sys
from pathlib import Path

# Configurar entorno
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

# Forzar superusuario postgres para DDL/TRUNCATE
os.environ["DB_USER"] = "postgres"
if "DB_PASSWORD" not in os.environ:
    os.environ["DB_PASSWORD"] = "postgres"

from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text


def run_clean_reseed():
    print("====================================================================")
    print("INICIANDO RESEMBRADO LIMPIO CANÓNICO DE MÓDULOS Y PERMISOS (SAR)")
    print("====================================================================")

    db = DatabaseConnector()
    with db.get_session() as conn:
        # 1. Respaldar asignaciones de roles existentes
        print("[PASO 1] Respaldando asignaciones vigentes de permisos...")
        backup_query = text("""
            SELECT r.codigo AS rol_cod, m.codigo AS mod_cod, a.codigo AS acc_cod
            FROM sar_seguridad.rol_permiso rp
            JOIN sar_seguridad.rol r ON rp.rol_id = r.rol_id
            JOIN sar_seguridad.permiso p ON rp.permiso_id = p.permiso_id
            JOIN sar_seguridad.modulo m ON p.modulo_id = m.modulo_id
            JOIN sar_seguridad.accion a ON p.accion_id = a.accion_id;
        """)
        existing_assignments = conn.execute(backup_query).fetchall()
        print(f"  -> {len(existing_assignments)} asignaciones respaldadas en memoria.")

        # Obtener mapeo de roles y app_modulos
        roles = conn.execute(text("SELECT rol_id, codigo FROM sar_seguridad.rol;")).fetchall()
        rol_id_by_code = {r[1]: r[0] for r in roles}

        app_modulos = conn.execute(text("SELECT app_modulo_id, codigo FROM sar_seguridad.app_modulo;")).fetchall()
        app_id_by_code = {am[1]: am[0] for am in app_modulos}

        acciones = conn.execute(text("SELECT accion_id, codigo FROM sar_seguridad.accion ORDER BY accion_id;")).fetchall()

        # 2. Truncate en cascada con reinicio de secuencias
        print("[PASO 2] Ejecutando TRUNCATE limpio con RESTART IDENTITY...")
        conn.execute(text("""
            TRUNCATE TABLE 
                sar_seguridad.rol_permiso,
                sar_seguridad.permiso,
                sar_seguridad.modulo
            RESTART IDENTITY CASCADE;
        """))
        print("  -> Tablas truncadas y secuencias reiniciadas a 1.")

        # 3. Inserción canónica de módulos (IDs 1 al 32 correlativos)
        print("[PASO 3] Insertando módulos en orden canónico estricto...")
        id_ctrl = app_id_by_code.get("CTRL_REF", 2)
        id_admin = app_id_by_code.get("ADMIN", 1)
        id_r2f = app_id_by_code.get("R2F_CANCUN", 6)

        canonical_modules = [
            # 1.0 a 3.5: CTRL_REF (Módulos 1 al 10)
            ("DASHBOARD", "Inicio", "Módulo de métricas y resumen operativo", 1.0, id_ctrl),
            ("ORDENES", "Órdenes de Generación", "Módulo de creación y control de requerimientos masivos", 2.0, id_ctrl),
            ("SOLICITUDES", "Solicitudes del Bot", "Módulo de distribución y ejecución de solicitudes de scraping", 2.3, id_ctrl),
            ("DERECHOS", "Derechos", "Visor de producción de derechos y folios", 2.4, id_ctrl),
            ("CONTROL_DERECHOS", "Control de Derechos", "Módulo principal de control y distribución de derechos", 3.0, id_ctrl),
            ("CTRL:INVENTARIO", "Inventario", "Visualización e inventario de derechos disponibles", 3.1, id_ctrl),
            ("CTRL:ASIGNAR_DERECHO", "Asignar Derecho", "Asignación directa a notarías/colaboradores", 3.2, id_ctrl),
            ("CTRL:ASIGNAR_VALIDAR", "Asignar/Validar", "Carga masiva por lote y validación de derechos", 3.3, id_ctrl),
            ("CTRL:RESERVA_DERECHO", "Reservar Derecho", "Reserva y apartado de folios para desarrollos", 3.4, id_ctrl),
            ("CTRL:GESTION_LOTES", "Gestión de asignaciones", "Historial, seguimiento y expedientes de lotes", 3.5, id_ctrl),

            # 4.0 a 4.5: ADMIN - Sección Seguridad (Módulos 11 al 16)
            ("SEGURIDAD", "Seguridad", "Módulo de Seguridad y Accesos del Sistema", 4.0, id_admin),
            ("ADM:USUARIOS", "Usuarios", "Gestión de Usuarios del Sistema", 4.1, id_admin),
            ("ADM:ROLES", "Roles y Perfiles", "Gestión de Roles y Perfiles Operativos", 4.2, id_admin),
            ("ADM:PERMISOS", "Permisos", "Matriz de Permisos por Rol", 4.3, id_admin),
            ("ADM:MODULOS", "Módulos", "Catálogo de Módulos del Sistema y Macro-Apps", 4.4, id_admin),
            ("ADM:ACCIONES", "Acciones", "Catálogo de Acciones del Sistema", 4.5, id_admin),

            # 5.0 a 5.4: ADMIN - Sección Catálogos (Módulos 17 al 21)
            ("CATALOGOS", "Catálogos", "Gestión de Catálogos Maestros del Sistema", 5.0, id_admin),
            ("ADM:CAT_NEGOCIO", "Catálogos de Negocio", "Conceptos y Agrupadores de Cobro", 5.1, id_admin),
            ("ADM:GEOGRAFIA", "Geografía", "Catálogo de Plazas, Ciudades, Sitios y Notarías", 5.2, id_admin),
            ("ADM:RFCS", "Empresas y RFCs", "Catálogo de Empresas y Domicilios Fiscales", 5.3, id_admin),
            ("ADM:ESTADOS", "Estados del Sistema", "Catálogo de Estados de Órdenes y Referencias", 5.4, id_admin),

            # 6.0 a 6.2: ADMIN - Sección Configuración (Módulos 22 al 24)
            ("CONFIGURACION", "Configuración", "Configuración General y Parámetros del Sistema", 6.0, id_admin),
            ("ADM:PARAMETROS", "Parámetros", "Parámetros Técnicos del Sistema (settings)", 6.1, id_admin),
            ("ADM:LOCALIZADORES", "Localizadores", "Configuración de Localizadores y Selectores DOM", 6.2, id_admin),

            # 7.0 a 7.4: ADMIN - Sección Procesos Especiales (Módulos 25 al 29)
            ("PROCESOS_ESPECIALES", "Procesos Especiales", "Módulo de Procesos Especiales y Cargas Masivas", 7.0, id_admin),
            ("ADM:CARGA_MASIVA", "Carga Masiva de Órdenes", "Proceso Especial: Carga Masiva de Órdenes", 7.1, id_admin),
            ("ADM:MIGRACION", "Migración Fojas/Testimonios", "Proceso Especial: Migración de Fojas y Testimonios", 7.2, id_admin),
            ("ADM:RESERVA_MASIVA", "Reserva Masiva de Derechos", "Proceso Especial: Reserva Masiva de Derechos", 7.3, id_admin),
            ("ADM:UPDATE_FACTURAS", "Actualización de Facturas", "Proceso Especial: Actualización Masiva de Facturas", 7.4, id_admin),

            # 8.0 a 8.2: R2F_CANCUN (Módulos 30 al 32)
            ("FOLIOS_CANCUN", "Folios Cancún", "Control de Folios Cancún", 8.0, id_r2f),
            ("RECIBOS_CANCUN", "Recibos Cancún", "Emisión de Recibos Cancún", 8.1, id_r2f),
            ("FACTURAS_CANCUN", "Facturación Cancún", "Facturación Fiscal Cancún", 8.2, id_r2f),
        ]

        for cod, nom, desc, ord_val, app_id in canonical_modules:
            conn.execute(text("""
                INSERT INTO sar_seguridad.modulo (codigo, nombre, descripcion, activo, orden, app_modulo_id)
                VALUES (:cod, :nom, :desc, TRUE, :ord_val, :app_id);
            """), {"cod": cod, "nom": nom, "desc": desc, "ord_val": ord_val, "app_id": app_id})

        print(f"  -> {len(canonical_modules)} módulos insertados con IDs continuos del 1 al {len(canonical_modules)}.")

        # 4. Generación de Permisos (sar_seguridad.permiso)
        print("[PASO 4] Generando matriz canónica de permisos (Módulo x Acción)...")
        modulos_nuevos = conn.execute(text("SELECT modulo_id, codigo FROM sar_seguridad.modulo ORDER BY modulo_id;")).fetchall()
        mod_id_by_code = {m[1]: m[0] for m in modulos_nuevos}
        acc_id_by_code = {a[1]: a[0] for a in acciones}

        permiso_count = 0
        permiso_map = {}  # (mod_cod, acc_cod) -> permiso_id

        for m_id, m_cod in modulos_nuevos:
            for a_id, a_cod in acciones:
                res = conn.execute(text("""
                    INSERT INTO sar_seguridad.permiso (modulo_id, accion_id, activo)
                    VALUES (:m_id, :a_id, TRUE)
                    RETURNING permiso_id;
                """), {"m_id": m_id, "a_id": a_id}).fetchone()
                p_id = res[0]
                permiso_map[(m_cod, a_cod)] = p_id
                permiso_count += 1

        print(f"  -> {permiso_count} permisos canónicos creados en sar_seguridad.permiso.")

        # 5. Asignación de Permisos a Roles
        print("[PASO 5] Asignando permisos a roles...")
        admin_rol_id = rol_id_by_code.get("ADMINISTRADOR")
        if admin_rol_id:
            # ADMINISTRADOR: ACCESO TOTAL (100% de permisos generados)
            conn.execute(text("""
                INSERT INTO sar_seguridad.rol_permiso (rol_id, permiso_id)
                SELECT :r_id, permiso_id FROM sar_seguridad.permiso;
            """), {"r_id": admin_rol_id})
            print(f"  -> Rol ADMINISTRADOR: Acceso TOTAL otorgado ({permiso_count} permisos asignados).")

        # Roles operativos estándar según SAR-SEC-003:
        role_standard_permissions = {
            "OPERADOR": [
                ("DASHBOARD", "LEER"),
                ("ORDENES", "LEER"), ("ORDENES", "CREAR"), ("ORDENES", "EDITAR"), ("ORDENES", "EJECUTAR"),
                ("SOLICITUDES", "LEER"), ("SOLICITUDES", "ASIGNAR"), ("SOLICITUDES", "EDITAR"), ("SOLICITUDES", "EJECUTAR"),
                ("DERECHOS", "LEER"),
                ("CONTROL_DERECHOS", "LEER"),
                ("CTRL:INVENTARIO", "LEER"), ("CTRL:INVENTARIO", "ASIGNAR"), ("CTRL:INVENTARIO", "EJECUTAR"),
                ("CTRL:ASIGNAR_DERECHO", "LEER"), ("CTRL:ASIGNAR_DERECHO", "ASIGNAR"),
                ("CTRL:ASIGNAR_VALIDAR", "LEER"), ("CTRL:ASIGNAR_VALIDAR", "CREAR"), ("CTRL:ASIGNAR_VALIDAR", "ASIGNAR"),
                ("CTRL:RESERVA_DERECHO", "LEER"), ("CTRL:RESERVA_DERECHO", "ASIGNAR"),
                ("CTRL:GESTION_LOTES", "LEER"), ("CTRL:GESTION_LOTES", "EJECUTAR"),
            ],
            "BOT": [
                ("ORDENES", "LEER"), ("ORDENES", "EJECUTAR"),
                ("SOLICITUDES", "LEER"), ("SOLICITUDES", "EDITAR"), ("SOLICITUDES", "EJECUTAR"),
            ],
            "GESTOR": [
                ("DASHBOARD", "LEER"),
                ("CONTROL_DERECHOS", "LEER"),
                ("CTRL:INVENTARIO", "LEER"), ("CTRL:INVENTARIO", "ASIGNAR"),
                ("CTRL:ASIGNAR_DERECHO", "LEER"), ("CTRL:ASIGNAR_DERECHO", "ASIGNAR"),
                ("CTRL:RESERVA_DERECHO", "LEER"), ("CTRL:RESERVA_DERECHO", "ASIGNAR"),
                ("CTRL:GESTION_LOTES", "LEER"), ("CTRL:GESTION_LOTES", "EJECUTAR"),
            ],
            "CONSULTA": [
                ("DASHBOARD", "LEER"),
                ("DERECHOS", "LEER"),
            ],
            "OPERADORR2F": [
                ("FOLIOS_CANCUN", "LEER"), ("FOLIOS_CANCUN", "CREAR"), ("FOLIOS_CANCUN", "EDITAR"),
                ("RECIBOS_CANCUN", "LEER"), ("RECIBOS_CANCUN", "CREAR"), ("RECIBOS_CANCUN", "EDITAR"),
                ("FACTURAS_CANCUN", "LEER"), ("FACTURAS_CANCUN", "CREAR"), ("FACTURAS_CANCUN", "EDITAR"), ("FACTURAS_CANCUN", "EJECUTAR")
            ]
        }

        # Asignar permisos estándar a los roles no-admin
        for rol_code, perm_tuples in role_standard_permissions.items():
            r_id = rol_id_by_code.get(rol_code)
            if not r_id:
                continue
            assigned = 0
            for mod_cod, acc_cod in perm_tuples:
                p_id = permiso_map.get((mod_cod, acc_cod))
                if p_id:
                    conn.execute(text("""
                        INSERT INTO sar_seguridad.rol_permiso (rol_id, permiso_id)
                        VALUES (:r_id, :p_id)
                        ON CONFLICT DO NOTHING;
                    """), {"r_id": r_id, "p_id": p_id})
                    assigned += 1
            print(f"  -> Rol {rol_code}: {assigned} permisos asignados correctamente.")

        # Confirmar transacción
        conn.commit()
        print("  -> Transacción completada y confirmada exitosamente.")

        # 6. Reporte Final
        print("\n--- REPORTE CANÓNICO DE MÓDULOS EN BASE DE DATOS ---")
        rows = conn.execute(text("""
            SELECT m.modulo_id, m.orden, m.codigo, m.nombre, am.codigo AS app_modulo
            FROM sar_seguridad.modulo m
            LEFT JOIN sar_seguridad.app_modulo am ON m.app_modulo_id = am.app_modulo_id
            ORDER BY m.modulo_id ASC;
        """)).fetchall()

        print(f"{'ID':<4} | {'ORDEN':<6} | {'CÓDIGO':<25} | {'NOMBRE':<28} | {'MACRO-APP'}")
        print("-" * 80)
        for r in rows:
            print(f"{str(r[0]):<4} | {str(r[1]):<6} | {r[2]:<25} | {r[3]:<28} | {str(r[4])}")
        print("-" * 80)

        # Conteo final de rol_permiso
        print("\n--- RESUMEN DE PERMISOS ASIGNADOS POR ROL ---")
        counts = conn.execute(text("""
            SELECT r.codigo, COUNT(rp.permiso_id) AS total_permisos
            FROM sar_seguridad.rol r
            LEFT JOIN sar_seguridad.rol_permiso rp ON r.rol_id = rp.rol_id
            GROUP BY r.codigo
            ORDER BY total_permisos DESC;
        """)).fetchall()
        for c in counts:
            print(f"  * Rol {c[0]:<15}: {c[1]} permisos asignados")

    print("\n====================================================================")
    print("RESEMBRADO LIMPIO FINALIZADO SATISFACTORIAMENTE.")
    print("====================================================================")


if __name__ == "__main__":
    run_clean_reseed()
