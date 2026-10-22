# -*- coding: utf-8 -*-
import unittest
from sar.src.storage.db_connector import DatabaseConnector
from sar.src.services.admin_service import AdminService
from sar.src.api.routers.admin_router import get_resumen_orden_carga, get_resumen_orden_migracion

class TestAdminOrderSummaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseConnector()

    def test_resumen_orden_carga_service_and_api(self):
        with self.db.get_session() as session:
            service = AdminService(session)
            from sqlalchemy import select
            from sar.src.storage.models import OrdenGeneracion
            orden = session.execute(select(OrdenGeneracion.orden_id).order_by(OrdenGeneracion.orden_id.desc())).scalars().first()
            if not orden:
                self.skipTest('No existen ordenes en la base de datos.')
            res_svc = service.get_resumen_orden_carga_masiva(orden)
            self.assertIsInstance(res_svc, list)
            res_api = get_resumen_orden_carga(orden, db=session)
            self.assertIsInstance(res_api, list)
            self.assertEqual(len(res_svc), len(res_api))

    def test_resumen_orden_migracion_service_and_api(self):
        with self.db.get_session() as session:
            service = AdminService(session)
            from sqlalchemy import select
            from sar.src.storage.models import OrdenGeneracion
            orden = session.execute(select(OrdenGeneracion.orden_id).order_by(OrdenGeneracion.orden_id.desc())).scalars().first()
            if not orden:
                self.skipTest('No existen ordenes en la base de datos.')
            res_svc = service.get_resumen_orden_migracion(orden)
            self.assertIsInstance(res_svc, list)
            res_api = get_resumen_orden_migracion(orden, db=session)
            self.assertIsInstance(res_api, list)
            self.assertEqual(len(res_svc), len(res_api))

if __name__ == '__main__':
    unittest.main()
