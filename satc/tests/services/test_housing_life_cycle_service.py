# -*- coding: utf-8 -*-
"""Unit tests for HousingLifeCycleService adhering to SATC standards."""

import unittest
from unittest.mock import MagicMock
from satc.src.services.housing_life_cycle_service import HousingLifeCycleService
from satc.src.storage.satc_models import Vivienda, RegimenCondominio, EstadoVivienda


class TestHousingLifeCycleService(unittest.TestCase):
    def setUp(self):
        self.mock_session = MagicMock()
        self.service = HousingLifeCycleService(self.mock_session)

    def test_obtener_viviendas_activas_no_vendidas_query_construction(self):
        """Verifica que la consulta filtre adecuadamente sin referenciar columnas inexistentes (fecha_venta)."""
        # Mocking query chain for EstadoVivienda
        mock_query_estado = MagicMock()
        mock_query_estado.filter.return_value.all.return_value = [(6,), (7,), (8,)]
        
        # Mocking query chain for Vivienda
        mock_query_vivienda = MagicMock()
        mock_vivienda_1 = MagicMock(spec=Vivienda)
        mock_vivienda_1.vivienda_id = 101
        mock_vivienda_1.interior = "101"
        mock_vivienda_1.numero_oficial = "1"
        mock_vivienda_1.activo = True
        mock_vivienda_1.fecha_escrituracion = None
        
        mock_query_vivienda.filter.return_value.order_by.return_value.all.return_value = [mock_vivienda_1]

        def query_side_effect(model):
            if model is EstadoVivienda.estado_vivienda_id:
                return mock_query_estado
            elif model is Vivienda:
                return mock_query_vivienda
            return MagicMock()

        self.mock_session.query.side_effect = query_side_effect

        # Ejecutar método
        resultado = self.service.obtener_viviendas_activas_no_vendidas(regimen_id=1)

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0].vivienda_id, 101)
        self.assertTrue(self.mock_session.query.called)

    def test_detectar_omisiones_regimen_no_numero_upe(self):
        """Verifica que detectar_omisiones_regimen no lance AttributeError por numero_upe."""
        mock_regimen = MagicMock(spec=RegimenCondominio)
        mock_regimen.nombre_regimen = "AURA NOVA PLAYA"
        mock_regimen.total_upes = 10

        v1 = MagicMock(spec=Vivienda)
        v1.numero_oficial = "1"
        v1.interior = "101"
        v1.clave_catastral = "123456789012345678"

        v2 = MagicMock(spec=Vivienda)
        v2.numero_oficial = "2"
        v2.interior = "102"
        v2.clave_catastral = None  # Sin clave

        self.service.regimen_repo = MagicMock()
        self.service.regimen_repo.get_by_id.return_value = mock_regimen
        self.service.vivienda_repo = MagicMock()
        self.service.vivienda_repo.list_by_regimen.return_value = [v1, v2]

        reporte = self.service.detectar_omisiones_regimen(regimen_id=1)

        self.assertEqual(reporte["total_upes_declaradas"], 10)
        self.assertEqual(reporte["upes_registradas"], 2)
        self.assertEqual(reporte["upes_faltantes_registro"], 8)
        self.assertEqual(reporte["upes_sin_clave_catastral"], 1)
        self.assertEqual(reporte["cobertura_porcentaje"], 20.0)

    def test_save_regimen_condominio_with_inscripcion_metadata(self):
        """Verifica que save_regimen_condominio persista adecuadamente los campos de la boleta de inscripción."""
        self.service.regimen_repo = MagicMock()
        mock_regimen = MagicMock(spec=RegimenCondominio)
        mock_regimen.desarrollo_id = 5
        mock_regimen.total_upes = 577
        mock_regimen.sm = "SM-115"
        mock_regimen.mz = "01"
        mock_regimen.lt = "01"
        self.service.regimen_repo.get_by_id.return_value = mock_regimen
        self.service.regimen_repo.find_duplicate.return_value = None
        self.service.vivienda_repo = MagicMock()
        self.service.vivienda_repo.count_by_regimen.return_value = 0

        payload = {
            "regimen_id": 1,
            "desarrollo_id": 5,
            "nombre_regimen": "AURA NOVA PLAYA",
            "sm": "SM-115",
            "mz": "01",
            "lt": "01",
            "total_upes": 577,
            "numero_instrumento": "P.A. 65921",
            "fecha_liberacion": "2026-10-28 14:49",
            "notaria": "68",
            "notario": "FRANCISCO JOSE TRACONIS VARGUEZ",
            "solicitante": "ANA LAURA MORALES PECH",
            "observaciones": "202603000000000161037",
            "activo": True
        }

        res = self.service.save_regimen_condominio(payload)

        self.service.regimen_repo.get_by_id.assert_called_once_with(1)
        self.assertEqual(mock_regimen.numero_instrumento, "P.A. 65921")
        self.assertEqual(mock_regimen.notaria, "68")
        self.assertEqual(mock_regimen.notario, "FRANCISCO JOSE TRACONIS VARGUEZ")
        self.assertEqual(mock_regimen.solicitante, "ANA LAURA MORALES PECH")
        self.assertEqual(mock_regimen.observaciones, "202603000000000161037")
        self.assertIsNotNone(mock_regimen.fecha_liberacion)

    def test_save_regimen_condominio_duplicate_raises_error(self):
        """Verifica que save_regimen_condominio lance ValueError cuando ya existe un régimen con la misma ubicación."""
        self.service.regimen_repo = MagicMock()
        mock_existente = MagicMock(spec=RegimenCondominio)
        mock_existente.regimen_id = 99
        mock_existente.nombre_regimen = "REGIMEN DUPLICADO"
        self.service.regimen_repo.find_duplicate.return_value = mock_existente

        payload = {
            "desarrollo_id": 5,
            "nombre_regimen": "NUEVO REGIMEN",
            "sm": "SM-115",
            "mz": "01",
            "lt": "01",
            "total_upes": 100
        }

        with self.assertRaises(ValueError) as ctx:
            self.service.save_regimen_condominio(payload)

        self.assertIn("Ya existe un régimen registrado para este desarrollo con la misma ubicación", str(ctx.exception))
        self.assertIn("REGIMEN DUPLICADO", str(ctx.exception))

    def test_save_regimen_condominio_with_viviendas_blocks_structural_edits(self):
        """Verifica que se impida alterar desarrollo_id, total_upes o SM/MZ/LT si ya existen viviendas cargadas."""
        self.service.regimen_repo = MagicMock()
        mock_regimen = MagicMock(spec=RegimenCondominio)
        mock_regimen.regimen_id = 10
        mock_regimen.desarrollo_id = 5
        mock_regimen.total_upes = 100
        mock_regimen.sm = "SM-115"
        mock_regimen.mz = "01"
        mock_regimen.lt = "01"
        self.service.regimen_repo.get_by_id.return_value = mock_regimen
        self.service.regimen_repo.find_duplicate.return_value = None

        self.service.vivienda_repo = MagicMock()
        self.service.vivienda_repo.count_by_regimen.return_value = 50  # Ya tiene 50 viviendas cargadas

        # Intento de cambiar desarrollo_id
        payload_des = {
            "regimen_id": 10,
            "desarrollo_id": 8,  # Cambio de desarrollo
            "nombre_regimen": "AURA NOVA",
            "sm": "SM-115",
            "mz": "01",
            "lt": "01",
            "total_upes": 100
        }
        with self.assertRaises(ValueError) as ctx:
            self.service.save_regimen_condominio(payload_des)
        self.assertIn("No es posible cambiar el desarrollo del régimen porque ya tiene 50 viviendas cargadas", str(ctx.exception))

        # Intento de cambiar total_upes
        payload_upes = {
            "regimen_id": 10,
            "desarrollo_id": 5,
            "nombre_regimen": "AURA NOVA",
            "sm": "SM-115",
            "mz": "01",
            "lt": "01",
            "total_upes": 150  # Cambio de UPEs
        }
        with self.assertRaises(ValueError) as ctx:
            self.service.save_regimen_condominio(payload_upes)
        self.assertIn("No es posible modificar el total de UPEs autorizadas", str(ctx.exception))

    def test_analizar_corte_erp_detecta_reincorporacion_por_cancelacion(self):
        """Verifica que el motor detecte el Escenario D (Cancelación de venta y reincorporación a DISPONIBLE)."""
        # Simular vivienda existente en SATC que estaba EN_PROCESO_ESCRITURACION
        mock_vivienda = {
            "vivienda_id": 105,
            "regimen_id": 1,
            "regimen_nombre": "AURA NOVA",
            "regimen_mz": "MZ 01",
            "regimen_lt": "LT 01",
            "interior": "101",
            "condicion_comercial": "EN_PROCESO_ESCRITURACION",
            "folio_electronico": "20260300000000023690",
            "clave_catastral": "1234567890"
        }
        self.service.get_viviendas_by_desarrollo = MagicMock(return_value=[mock_vivienda])
        self.service.tramite_repo = MagicMock()
        self.service.tramite_repo.list_by_vivienda.return_value = []

        # Registro del nuevo corte del ERP donde ahora viene DISPONIBLE (clave 'D')
        records_erp = [
            {
                "Desarrollo": "AURA NOVA",
                "mz": "1",
                "lote": "1",
                "Exterior": "EDIFICIO A",
                "interior": "101",
                "nivel": "PB",
                "status lote": "D",
                "fecha estatus lote": "2026-10-30",
                "cliente": "CLIENTE CANCELADO",
                "nns": "12345678901",
                "etapa": ""
            }
        ]

        resultado = self.service.analizar_corte_erp(desarrollo_id=5, records=records_erp, nombre_archivo="corte_octubre.xlsx")

        self.assertEqual(resultado["total_registros"], 1)
        self.assertEqual(resultado["total_reincorporadas"], 1)
        self.assertEqual(resultado["total_disponibles"], 1)
        delta = resultado["deltas"][0]
        self.assertEqual(delta["vivienda_id"], 105)
        self.assertEqual(delta["delta_tipo"], "REINCORPORADA_CANCELACION")
        self.assertEqual(delta["condicion_anterior"], "EN_PROCESO_ESCRITURACION")
        self.assertEqual(delta["condicion_nueva"], "DISPONIBLE")


if __name__ == "__main__":
    unittest.main()
