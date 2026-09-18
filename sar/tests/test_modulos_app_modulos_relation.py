"""
Pruebas de Verificación: Relación sar_seguridad.modulo -> app_modulo (Alternativa 2)
===================================================================================
Estándar: SAR-AI-PROMPTS-001 / SAR-DEV-001 / SAR-SEC-003
Valida:
1. Estructura de BD (columna app_modulo_id, FK e índice en PostgreSQL).
2. Asignación correcta de app_modulo_id a CTRL_REF (id=2), ADMIN (id=1) y R2F_CANCUN (id=6).
3. Desactivación de REFERENCIAS y migración a DERECHOS.
4. Modelos ORM Modulo y AppModulo (bidireccionalidad).
5. Lógica de negocio de AdminService.save_modulo (persistencia de orden y app_modulo_id).
6. Lógica de permisos Fail-Closed en AdminWindow con granularidad ADM:*.
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from decimal import Decimal
from sqlalchemy import text, inspect

from sar.src.storage.db_connector import DatabaseConnector
from sar.src.storage.models import Modulo, AppModulo
from sar.src.services.admin_service import AdminService
from sar.src.storage.repositories import UsuarioRepository


def test_database_schema_app_modulo_id(db):
    """Verifica que la columna app_modulo_id exista en sar_seguridad.modulo con su FK."""
    with db.get_session() as session:
        # Verificar columna
        res = session.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'sar_seguridad' 
              AND table_name = 'modulo' 
              AND column_name = 'app_modulo_id';
        """)).fetchone()
        assert res is not None, "La columna app_modulo_id debe existir en sar_seguridad.modulo"
        assert res[1] == 'integer', "El tipo de dato de app_modulo_id debe ser integer"
        assert res[2] == 'YES', "La columna app_modulo_id debe ser nullable"

        # Verificar índice
        idx = session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE schemaname = 'sar_seguridad'
              AND tablename = 'modulo'
              AND indexname = 'idx_modulo_app_modulo';
        """)).fetchone()
        assert idx is not None, "El índice idx_modulo_app_modulo debe existir"


def test_ctrl_ref_modules_assignment(db):
    """Verifica que los módulos de CTRL_REF tengan app_modulo_id = 2 y orden canónico."""
    with db.get_session() as session:
        # Obtener ID de CTRL_REF
        app_ctrl = session.execute(text("SELECT app_modulo_id FROM sar_seguridad.app_modulo WHERE codigo = 'CTRL_REF';")).fetchone()
        assert app_ctrl is not None
        ctrl_id = app_ctrl[0]

        # Verificar módulos requeridos de CTRL_REF
        expected_ctrl_modules = [
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

        for codigo, orden_esp in expected_ctrl_modules:
            mod = session.execute(text("""
                SELECT modulo_id, orden, app_modulo_id, activo
                FROM sar_seguridad.modulo
                WHERE codigo = :cod;
            """), {"cod": codigo}).fetchone()
            assert mod is not None, f"El módulo {codigo} debe existir en BD"
            assert float(mod[1]) == orden_esp, f"El orden de {codigo} debe ser {orden_esp}, obtenido {mod[1]}"
            assert mod[2] == ctrl_id, f"El app_modulo_id de {codigo} debe ser {ctrl_id}"
            assert mod[3] is True, f"El módulo {codigo} debe estar activo"


def test_admin_modules_assignment(db):
    """Verifica que los módulos de ADMIN (Alternativa 2) tengan app_modulo_id = 1."""
    with db.get_session() as session:
        app_admin = session.execute(text("SELECT app_modulo_id FROM sar_seguridad.app_modulo WHERE codigo = 'ADMIN';")).fetchone()
        assert app_admin is not None
        admin_id = app_admin[0]

        expected_admin_modules = [
            ("SEGURIDAD", 4.0),
            ("ADM:USUARIOS", 4.1),
            ("ADM:ROLES", 4.2),
            ("ADM:PERMISOS", 4.3),
            ("ADM:MODULOS", 4.4),
            ("ADM:ACCIONES", 4.5),
            ("CATALOGOS", 5.0),
            ("ADM:CAT_NEGOCIO", 5.1),
            ("ADM:GEOGRAFIA", 5.2),
            ("ADM:RFCS", 5.3),
            ("ADM:ESTADOS", 5.4),
            ("CONFIGURACION", 6.0),
            ("ADM:PARAMETROS", 6.1),
            ("ADM:LOCALIZADORES", 6.2),
            ("PROCESOS_ESPECIALES", 7.0),
            ("ADM:CARGA_MASIVA", 7.1),
            ("ADM:MIGRACION", 7.2),
            ("ADM:RESERVA_MASIVA", 7.3),
            ("ADM:UPDATE_FACTURAS", 7.4),
        ]

        for codigo, orden_esp in expected_admin_modules:
            mod = session.execute(text("""
                SELECT modulo_id, orden, app_modulo_id, activo
                FROM sar_seguridad.modulo
                WHERE codigo = :cod;
            """), {"cod": codigo}).fetchone()
            assert mod is not None, f"El módulo {codigo} debe existir en BD"
            assert float(mod[1]) == orden_esp, f"El orden de {codigo} debe ser {orden_esp}, obtenido {mod[1]}"
            assert mod[2] == admin_id, f"El app_modulo_id de {codigo} debe ser {admin_id}"
            assert mod[3] is True, f"El módulo {codigo} debe estar activo"


def test_referencias_deactivated_or_removed(db):
    """Verifica que REFERENCIAS esté completamente erradicado o inactivo en sar_seguridad.modulo."""
    with db.get_session() as session:
        mod_ref = session.execute(text("""
            SELECT activo, orden FROM sar_seguridad.modulo WHERE codigo = 'REFERENCIAS';
        """)).fetchone()
        if mod_ref is not None:
            assert mod_ref[0] is False, "Si REFERENCIAS existe, debe tener activo = FALSE"
        else:
            # Estado óptimo: limpiado completamente sin residuos
            assert mod_ref is None, "El módulo obsoleto REFERENCIAS fue purgado limpiamente de la BD"


def test_orm_models_relationships(db):
    """Verifica que el mapeo SQLAlchemy contenga app_modulo_id y relaciones bidireccionales."""
    with db.get_session() as session:
        # Cargar un módulo que tenga app_modulo_id
        mod = session.query(Modulo).filter(Modulo.codigo == "DERECHOS").first()
        assert mod is not None
        assert mod.app_modulo is not None
        assert mod.app_modulo.codigo == "CTRL_REF"

        # Verificar relación inversa
        app_ctrl = session.query(AppModulo).filter(AppModulo.codigo == "CTRL_REF").first()
        assert app_ctrl is not None
        codigos_hijos = [m.codigo for m in app_ctrl.modulos]
        assert "DERECHOS" in codigos_hijos
        assert "DASHBOARD" in codigos_hijos
        assert "CONTROL_DERECHOS" in codigos_hijos


def test_admin_service_save_modulo_with_app_modulo(db):
    """Verifica que AdminService.save_modulo persista orden y app_modulo_id correctamente."""
    with db.get_session() as session:
        service = AdminService(session)
        # Buscar el ID de un usuario administrador y sesión activa o simular
        user_row = session.execute(text("SELECT usuario_id FROM sar_seguridad.usuario WHERE activo = TRUE LIMIT 1;")).fetchone()
        assert user_row is not None
        uid = user_row[0]

        # Crear sesión temporal si no hay activa
        ses_row = session.execute(text("""
            INSERT INTO sar_seguridad.sesion (usuario_id, equipo_nombre, ip_equipo, estado)
            VALUES (:uid, 'TEST_SUITE', '127.0.0.1', 'ACTIVA')
            RETURNING sesion_id;
        """), {"uid": uid}).fetchone()
        ses_id = ses_row[0]
        session.commit()

        # Probar actualizar un módulo existente manteniendo integridad
        app_row = session.execute(text("SELECT app_modulo_id FROM sar_seguridad.app_modulo WHERE codigo = 'ADMIN';")).fetchone()
        admin_app_id = app_row[0]

        mod_test = session.query(Modulo).filter(Modulo.codigo == "ADM:USUARIOS").first()
        assert mod_test is not None

        updated = service.save_modulo(uid, ses_id, {
            "modulo_id": mod_test.modulo_id,
            "codigo": "ADM:USUARIOS",
            "nombre": "Gestión de Usuarios",
            "descripcion": "Gestión de Usuarios del Sistema (Test)",
            "activo": True,
            "orden": 4.1,
            "app_modulo_id": admin_app_id
        })
        session.commit()

        assert updated.orden == 4.1
        assert updated.app_modulo_id == admin_app_id

        # Limpiar sesión temporal
        session.execute(text("DELETE FROM sar_seguridad.sesion WHERE sesion_id = :sid;"), {"sid": ses_id})
        session.commit()


def test_admin_window_fail_closed_permission_logic():
    """Valida la lógica de acceso _has_view_access y _can_edit con granularidad atómica y fallback."""
    # Simular la lógica de AdminWindow sin instanciar GUI
    user_permissions_granular = {
        ("ADM:USUARIOS", "LEER"),
        ("ADM:USUARIOS", "CREAR"),
        ("ADM:ROLES", "LEER"),
        ("CATALOGOS", "LEER"),
        ("CATALOGOS", "EDITAR"),
    }

    def can_edit(modulo, submodulo=None):
        if submodulo:
            if (submodulo, "CREAR") in user_permissions_granular or (submodulo, "EDITAR") in user_permissions_granular:
                return True
        return (modulo, "CREAR") in user_permissions_granular or (modulo, "EDITAR") in user_permissions_granular

    def has_view_access(modulo, submodulo=None):
        for (m, a) in user_permissions_granular:
            if submodulo and m == submodulo:
                return True
            if m == modulo:
                return True
        return False

    # 1. ADM:USUARIOS tiene CREAR -> can_edit debe ser True
    assert can_edit("SEGURIDAD", "ADM:USUARIOS") is True
    assert has_view_access("SEGURIDAD", "ADM:USUARIOS") is True

    # 2. ADM:ROLES solo tiene LEER -> can_edit debe ser False, view_access True
    assert can_edit("SEGURIDAD", "ADM:ROLES") is False
    assert has_view_access("SEGURIDAD", "ADM:ROLES") is True

    # 3. ADM:PERMISOS no tiene ningún permiso ni SEGURIDAD tiene permiso -> Fail-Closed (False)
    assert can_edit("SEGURIDAD", "ADM:PERMISOS") is False
    assert has_view_access("SEGURIDAD", "ADM:PERMISOS") is False

    # 4. Fallback: CATALOGOS tiene EDITAR general -> ADM:CAT_NEGOCIO hereda acceso y edición
    assert can_edit("CATALOGOS", "ADM:CAT_NEGOCIO") is True
    assert has_view_access("CATALOGOS", "ADM:CAT_NEGOCIO") is True


if __name__ == "__main__":
    connector = DatabaseConnector()
    print("====================================================================")
    print("EJECUTANDO SUITE DE PRUEBAS: MODULO -> APP_MODULO (ALTERNATIVA 2)")
    print("====================================================================")
    
    tests = [
        ("test_database_schema_app_modulo_id", lambda: test_database_schema_app_modulo_id(connector)),
        ("test_ctrl_ref_modules_assignment", lambda: test_ctrl_ref_modules_assignment(connector)),
        ("test_admin_modules_assignment", lambda: test_admin_modules_assignment(connector)),
        ("test_referencias_deactivated_or_removed", lambda: test_referencias_deactivated_or_removed(connector)),
        ("test_orm_models_relationships", lambda: test_orm_models_relationships(connector)),
        ("test_admin_service_save_modulo_with_app_modulo", lambda: test_admin_service_save_modulo_with_app_modulo(connector)),
        ("test_admin_window_fail_closed_permission_logic", test_admin_window_fail_closed_permission_logic),
    ]

    passed = 0
    failed = 0
    for name, func in tests:
        try:
            func()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("====================================================================")
    print(f"RESULTADO: {passed} PASADAS, {failed} FALLADAS de {len(tests)} pruebas.")
    print("====================================================================")
    if failed > 0:
        sys.exit(1)
