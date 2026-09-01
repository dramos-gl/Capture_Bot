"""Solicitudes UI Service to decouple requests view from direct SQL/APIClient."""

from typing import List, Dict, Any
from sar.src.storage.api_client import APIClient
from sar.src.storage.repositories import OperacionRepository, ProduccionRepository, ConfigRepository, UsuarioRepository

class SolicitudesUIService:
    """Service layer for the UI to manage solicitud operations using either API or local DB."""

    def __init__(self, db_connector=None):
        self.db_connector = db_connector
        self.api_client = APIClient()

    def get_solicitudes(self, orden_ids: List[int] = None) -> List[Dict[str, Any]]:
        """Fetches the list of solicitudes."""
        if self.api_client.connect_via_api:
            payload = {"orden_ids": ",".join([str(x) for x in orden_ids])} if orden_ids else {}
            return self.api_client.request("GET", "/api/docs/solicitudes", data=payload)
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = OperacionRepository(session)
                return repo.get_solicitudes(orden_ids=orden_ids)

    def get_ordenes(self, include_rejected: bool = False) -> List[Dict[str, Any]]:
        """Fetches available orders, excluding rejected/cancelled orders by default."""
        if self.api_client.connect_via_api:
            res = self.api_client.request("GET", "/api/ops/ordenes")
            if not include_rejected and res:
                return [
                    ord for ord in res
                    if str(ord.get("estado", "") or ord.get("estado_codigo", "")).upper() not in ("RECHAZADA", "RECHAZADO", "CANCELADA", "CANCELADO")
                ]
            return res
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = ProduccionRepository(session)
                return repo.get_ordenes(include_rejected=include_rejected)

    def get_orden_id_by_solicitud(self, sol_id: int) -> int:
        """Fetches parent orden_id for a given solicitud."""
        if self.api_client.connect_via_api:
            data = self.api_client.request("GET", f"/api/docs/solicitudes/{sol_id}/orden-id")
            return data["orden_id"]
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                from sar.src.storage.models import Solicitud
                sol = session.get(Solicitud, sol_id)
                if not sol or not sol.grupo:
                    raise ValueError(f"Solicitud ID {sol_id} not found or has no group.")
                return sol.grupo.orden_id

    def get_ruta_derechos(self) -> str:
        """Fetches RUTA_DERECHOS config parameter."""
        if self.api_client.connect_via_api:
            data = self.api_client.request("GET", "/api/docs/config/ruta-derechos")
            return data.get("ruta_derechos", "")
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                config_repo = ConfigRepository(session)
                return config_repo.get_parametro("RUTA_DERECHOS")

    def get_all_usuarios(self) -> List[Dict[str, Any]]:
        """Fetches all users for assignment options."""
        if self.api_client.connect_via_api:
            return self.api_client.request("GET", "/api/auth/users")
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = UsuarioRepository(session)
                usuarios = repo.get_all_usuarios()
                return [{"usuario_id": u.usuario_id, "nombre": u.nombre, "username": u.username} for u in usuarios]

    def asignar_solicitud(self, sol_id: int, usuario_id: int) -> None:
        """Assigns a solicitud to a user."""
        if self.api_client.connect_via_api:
            self.api_client.request("POST", f"/api/docs/solicitudes/{sol_id}/asignar", data={"usuario_id": usuario_id})
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = OperacionRepository(session)
                repo.asignar_solicitud(sol_id, usuario_id)
                session.commit()

    def editar_cantidad_solicitud(self, sol_id: int, nueva_cantidad: int) -> None:
        """Edits requested quantity of a solicitud."""
        if self.api_client.connect_via_api:
            self.api_client.request("PUT", f"/api/docs/solicitudes/{sol_id}/cantidad", data={"nueva_cantidad": nueva_cantidad})
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = OperacionRepository(session)
                repo.editar_cantidad_solicitud(sol_id, nueva_cantidad)
                session.commit()

    def cancelar_solicitud(self, sol_id: int) -> None:
        """Cancels a single solicitud."""
        if self.api_client.connect_via_api:
            self.api_client.request("POST", f"/api/docs/solicitudes/{sol_id}/cancelar")
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = OperacionRepository(session)
                repo.cancelar_solicitud(sol_id)
                session.commit()
