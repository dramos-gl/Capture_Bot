"""Ordenes UI Service to decouple orders view from direct SQL/APIClient and backend service."""

from typing import List, Dict, Any, Tuple
from sar.src.storage.api_client import APIClient
from sar.src.storage.repositories import CatalogoRepository, ProduccionRepository
from sar.src.services.ordenes_service import OrdenesService

class OrdenesUIService:
    """Service layer for the UI to manage order operations using either API or local DB."""

    def __init__(self, db_connector=None):
        self.db_connector = db_connector
        self.api_client = APIClient()

    def get_ordenes(self) -> List[Dict[str, Any]]:
        """Fetches all available orders."""
        if self.api_client.connect_via_api:
            return self.api_client.request("GET", "/api/ops/ordenes")
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = ProduccionRepository(session)
                return repo.get_ordenes()

    def get_catalogos(self) -> Dict[str, Any]:
        """Fetches active RFCS, concepts, delegaciones, and active municipios."""
        if self.api_client.connect_via_api:
            return self.api_client.request("GET", "/api/ops/catalogos")
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = CatalogoRepository(session)
                rfcs = [(r.rfc_id, r.rfc) for r in repo.get_rfcs_activos()]
                conceptos = [(c.concepto_id, c.nombre) for c in repo.get_conceptos_activos()]
                delegaciones = [(d.delegacion_id, d.nombre) for d in repo.get_delegaciones_activas()]
                municipios = [{"nombre": m.nombre, "municipio_id": m.municipio_id, "activo": m.activo} for m in repo.get_all_municipios() if m.activo]
                return {
                    "rfcs": [{"rfc_id": r[0], "rfc": r[1]} for r in rfcs],
                    "conceptos": [{"concepto_id": c[0], "nombre": c[1]} for c in conceptos],
                    "delegaciones": [{"delegacion_id": d[0], "nombre": d[1]} for d in delegaciones],
                    "municipios": municipios
                }

    def check_orden_ready_for_masivo(self, orden_id: int) -> Dict[str, Any]:
        """Checks if the order is ready for mass action."""
        if self.api_client.connect_via_api:
            return self.api_client.request("GET", f"/api/ops/ordenes/{orden_id}/check-ready")
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = ProduccionRepository(session)
                return repo.check_orden_ready_for_masivo(orden_id)

    def update_orden_estado_masivo(self, orden_id: int, estado_codigo: str, usuario_id: int, sesion_id: int = None) -> None:
        """Updates the state of multiple references within the order to a new state."""
        if self.api_client.connect_via_api:
            payload = {
                "usuario_id": usuario_id,
                "sesion_id": sesion_id,
                "estado_codigo": estado_codigo
            }
            self.api_client.request("POST", f"/api/ops/ordenes/{orden_id}/estado-masivo", data=payload)
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                from sar.src.storage.models import Sesion
                db_sesion = session.get(Sesion, sesion_id) if sesion_id else None
                real_usuario_id = db_sesion.usuario_id if db_sesion else usuario_id
                
                repo = ProduccionRepository(session)
                repo.update_orden_estado_masivo(orden_id, estado_codigo, usuario_id=real_usuario_id, sesion_id=sesion_id)
                session.commit()

    def crear_orden_manual(self, usuario_id: int, sesion_id: int, descripcion: str, municipio_id: int, renglones: List[Dict[str, Any]]) -> str:
        """Creates a new order manually."""
        if self.api_client.connect_via_api:
            payload = {
                "usuario_id": usuario_id,
                "sesion_id": sesion_id,
                "descripcion": descripcion,
                "municipio_id": municipio_id,
                "renglones": renglones
            }
            res = self.api_client.request("POST", "/api/ops/ordenes", data=payload)
            return res["folio"]
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                from sar.src.storage.models import Sesion
                db_sesion = session.get(Sesion, sesion_id) if sesion_id else None
                real_usuario_id = db_sesion.usuario_id if db_sesion else usuario_id
                
                service = OrdenesService(session)
                nueva_orden = service.crear_orden_manual(
                    usuario_id=real_usuario_id,
                    sesion_id=sesion_id,
                    descripcion=descripcion,
                    municipio_id=municipio_id,
                    renglones=renglones
                )
                session.commit()
                return nueva_orden.folio

    def actualizar_orden_manual(self, orden_id: int, usuario_id: int, sesion_id: int, descripcion: str, municipio_id: int, renglones: List[Dict[str, Any]]) -> str:
        """Updates an existing order manually."""
        if self.api_client.connect_via_api:
            payload = {
                "usuario_id": usuario_id,
                "sesion_id": sesion_id,
                "descripcion": descripcion,
                "municipio_id": municipio_id,
                "renglones": renglones
            }
            res = self.api_client.request("PUT", f"/api/ops/ordenes/{orden_id}", data=payload)
            return res["folio"]
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                from sar.src.storage.models import Sesion
                db_sesion = session.get(Sesion, sesion_id) if sesion_id else None
                real_usuario_id = db_sesion.usuario_id if db_sesion else usuario_id
                
                service = OrdenesService(session)
                nueva_orden = service.actualizar_orden_manual(
                    orden_id=orden_id,
                    usuario_id=real_usuario_id,
                    sesion_id=sesion_id,
                    descripcion=descripcion,
                    municipio_id=municipio_id,
                    renglones=renglones
                )
                session.commit()
                return nueva_orden.folio

    def cancelar_orden_transaccional(self, orden_id: int, usuario_id: int, sesion_id: int = None) -> None:
        """Cancels an order and all its child requests/references."""
        if self.api_client.connect_via_api:
            payload = {
                "usuario_id": usuario_id,
                "sesion_id": sesion_id,
                "estado_codigo": "CANCELADA"
            }
            self.api_client.request("POST", f"/api/ops/ordenes/{orden_id}/cancelar", data=payload)
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                from sar.src.storage.models import Sesion
                db_sesion = session.get(Sesion, sesion_id) if sesion_id else None
                real_usuario_id = db_sesion.usuario_id if db_sesion else usuario_id

                repo = ProduccionRepository(session)
                repo.cancelar_orden_transaccional(orden_id, usuario_id=real_usuario_id, sesion_id=sesion_id)
                session.commit()
