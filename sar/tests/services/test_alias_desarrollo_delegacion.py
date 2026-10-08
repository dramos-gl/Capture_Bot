import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sar.src.storage.db_connector import DatabaseConnector
from sar.src.storage.repositories import CatalogoRepository
from sar.src.services.admin_service import AdminService
from sar.src.storage.models import Desarrollo, Delegacion, Municipio, Sesion, Usuario


class TestAliasDesarrolloDelegacion(unittest.TestCase):
    def setUp(self):
        self.db = DatabaseConnector()

    def test_alias_desarrollo_persistence_and_update(self):
        with self.db.get_session() as session:
            # Crear usuario y sesión activa de prueba
            user = session.query(Usuario).first()
            self.assertIsNotNone(user, "Debe existir al menos un usuario para auditoría")

            active_session = Sesion(
                usuario_id=user.usuario_id,
                equipo_nombre="TEST_RUNNER",
                estado="ACTIVA"
            )
            session.add(active_session)
            session.flush()

            service = AdminService(session)
            repo = CatalogoRepository(session)

            test_name = "TEST_PROYECTO_ALIAS_AUTO"
            test_alias = "TPA"
            updated_alias = "TPA_EDIT"

            # 1. Limpieza previa por si existe registro de prueba
            existing = session.query(Desarrollo).filter(Desarrollo.nombre == test_name).first()
            if existing:
                session.delete(existing)
                session.flush()

            # 2. Creación con alias
            desarrollo = service.save_desarrollo(
                usuario_id=user.usuario_id,
                sesion_id=active_session.sesion_id,
                data={"nombre": test_name, "alias": test_alias, "activo": True}
            )
            session.flush()
            desarrollo_id = desarrollo.desarrollo_id

            self.assertIsNotNone(desarrollo_id)
            self.assertEqual(desarrollo.nombre, test_name)
            self.assertEqual(desarrollo.alias, test_alias)

            # 3. Consulta desde repositorio
            desarrollos = repo.get_all_desarrollos()
            found = next((d for d in desarrollos if d.desarrollo_id == desarrollo_id), None)
            self.assertIsNotNone(found)
            self.assertEqual(found.alias, test_alias)

            # 4. Actualización de alias
            updated = service.save_desarrollo(
                usuario_id=user.usuario_id,
                sesion_id=active_session.sesion_id,
                data={"desarrollo_id": desarrollo_id, "nombre": test_name, "alias": updated_alias, "activo": True}
            )
            session.flush()
            self.assertEqual(updated.alias, updated_alias)

            # Revertir para mantener la base de datos limpia
            session.rollback()

    def test_alias_delegacion_persistence_and_update(self):
        with self.db.get_session() as session:
            user = session.query(Usuario).first()
            self.assertIsNotNone(user, "Debe existir al menos un usuario para auditoría")

            active_session = Sesion(
                usuario_id=user.usuario_id,
                equipo_nombre="TEST_RUNNER",
                estado="ACTIVA"
            )
            session.add(active_session)
            session.flush()

            service = AdminService(session)
            repo = CatalogoRepository(session)

            # Buscar municipio base para prueba
            mun = session.query(Municipio).first()
            self.assertIsNotNone(mun, "Debe existir al menos un municipio en el catálogo")

            test_name = "TEST_DELEGACION_ALIAS_AUTO"
            test_alias = "TDA"
            updated_alias = "TDA_EDIT"

            # 1. Limpieza previa
            existing = session.query(Delegacion).filter(Delegacion.nombre == test_name).first()
            if existing:
                session.delete(existing)
                session.flush()

            # 2. Creación con alias
            delegacion = service.save_delegacion(
                usuario_id=user.usuario_id,
                sesion_id=active_session.sesion_id,
                data={
                    "municipio_id": mun.municipio_id,
                    "codigo_portal": "PORTAL_TEST",
                    "nombre": test_name,
                    "alias": test_alias,
                    "activo": True
                }
            )
            session.flush()
            delegacion_id = delegacion.delegacion_id

            self.assertIsNotNone(delegacion_id)
            self.assertEqual(delegacion.nombre, test_name)
            self.assertEqual(delegacion.alias, test_alias)

            # 3. Consulta desde repositorio
            delegaciones = repo.get_all_delegaciones_list()
            found = next((d for d in delegaciones if d.delegacion_id == delegacion_id), None)
            self.assertIsNotNone(found)
            self.assertEqual(found.alias, test_alias)

            # 4. Actualización de alias
            updated = service.save_delegacion(
                usuario_id=user.usuario_id,
                sesion_id=active_session.sesion_id,
                data={
                    "delegacion_id": delegacion_id,
                    "municipio_id": mun.municipio_id,
                    "codigo_portal": "PORTAL_TEST",
                    "nombre": test_name,
                    "alias": updated_alias,
                    "activo": True
                }
            )
            session.flush()
            self.assertEqual(updated.alias, updated_alias)

            # Revertir para mantener la base de datos limpia
            session.rollback()


if __name__ == "__main__":
    unittest.main()
