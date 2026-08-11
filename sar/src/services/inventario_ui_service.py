"""Inventario UI Service to decouple inventory view from direct SQL/APIClient."""

from typing import List, Dict, Any
from sar.src.storage.api_client import APIClient
from sar.src.storage.repositories import InventarioRepository

class InventarioUIService:
    """Service layer for the UI to manage inventory operations using either API or local DB."""

    def __init__(self, db_connector=None):
        self.db_connector = db_connector
        self.api_client = APIClient()

    def get_referencias_facturadas_paginated(self, limit: int, offset: int, search_text: str, concepto_id: int, rfc_id: int, filter_assigned: str, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Fetches paginated facturadas references."""
        if self.api_client.connect_via_api:
            payload = {
                "limit": limit,
                "offset": offset,
                "search_text": search_text,
                "filter_assigned": filter_assigned
            }
            if concepto_id:
                payload["concepto_id"] = concepto_id
            if rfc_id:
                payload["rfc_id"] = rfc_id
            if start_date:
                payload["start_date"] = start_date
            if end_date:
                payload["end_date"] = end_date
            res = self.api_client.request("GET", "/api/docs/inventario/referencias-facturadas", data=payload)
            return {"records": res["records"], "total_count": res["total_count"]}
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                res, total_count = repo.get_referencias_facturadas_paginated(
                    limit=limit,
                    offset=offset,
                    search_text=search_text,
                    concepto_id=concepto_id,
                    rfc_id=rfc_id,
                    filter_assigned=filter_assigned,
                    start_date=start_date,
                    end_date=end_date
                )
                return {"records": res, "total_count": total_count}

    def get_inventario_summary(self, search_text: str = "", concepto_id: int = None, rfc_id: int = None, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Fetches inventory counts (disponibles, asignadas) under active filters."""
        if self.api_client.connect_via_api:
            payload = {}
            if search_text:
                payload["search_text"] = search_text
            if concepto_id:
                payload["concepto_id"] = concepto_id
            if rfc_id:
                payload["rfc_id"] = rfc_id
            if start_date:
                payload["start_date"] = start_date
            if end_date:
                payload["end_date"] = end_date
            return self.api_client.request("GET", "/api/docs/inventario/referencias-facturadas-summary", data=payload)
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                return repo.get_inventario_summary(
                    search_text=search_text,
                    concepto_id=concepto_id,
                    rfc_id=rfc_id,
                    start_date=start_date,
                    end_date=end_date
                )

    def get_notarias(self) -> List[Dict[str, Any]]:
        """Fetches notarias."""
        if self.api_client.connect_via_api:
            return self.api_client.request("GET", "/api/docs/inventario/notarias")
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                return repo.get_notarias()

    def get_colaboradores(self) -> List[Dict[str, Any]]:
        """Fetches colaboradores."""
        if self.api_client.connect_via_api:
            return self.api_client.request("GET", "/api/docs/inventario/colaboradores")
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                return repo.get_colaboradores()

    def get_desarrollos(self) -> List[Dict[str, Any]]:
        """Fetches desarrollos."""
        if self.api_client.connect_via_api:
            return self.api_client.request("GET", "/api/docs/inventario/desarrollos")
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                return repo.get_desarrollos()

    def get_disponibles_count(self, rfc_id: int, concepto_id: int, desarrollo_id: int) -> int:
        """Returns the count of FACTURADA references available for the given (rfc, concepto, desarrollo).
        Used by the real-time availability column in the InteractiveGrid.
        """
        if self.api_client.connect_via_api:
            try:
                result = self.api_client.request(
                    "GET", "/api/docs/inventario/disponibles",
                    params={"rfc_id": rfc_id, "concepto_id": concepto_id, "desarrollo_id": desarrollo_id}
                )
                return result.get("count", 0) if isinstance(result, dict) else 0
            except Exception:
                return 0
        else:
            if not self.db_connector:
                return 0
            try:
                with self.db_connector.get_session() as session:
                    repo = InventarioRepository(session)
                    return repo.count_referencias_disponibles(rfc_id, concepto_id, desarrollo_id)
            except Exception:
                return 0

    def get_catalogos_data(self) -> Dict[str, Any]:
        """Fetches all catalogs required for the inventory view."""
        if self.api_client.connect_via_api:
            notarias = self.api_client.request("GET", "/api/docs/inventario/notarias")
            colaboradores = self.api_client.request("GET", "/api/docs/inventario/colaboradores")
            desarrollos = self.api_client.request("GET", "/api/docs/inventario/desarrollos")
            cats = self.api_client.request("GET", "/api/ops/catalogos")
            return {
                "notarias": notarias,
                "colaboradores": colaboradores,
                "desarrollos": desarrollos,
                "conceptos": cats["conceptos"],
                "delegaciones": cats["delegaciones"],
                "rfcs": cats.get("rfcs", [])
            }
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                notarias = repo.get_notarias()
                colaboradores = repo.get_colaboradores()
                desarrollos = repo.get_desarrollos()
                
                from sar.src.storage.models import Concepto, Delegacion, Rfc
                from sqlalchemy import select
                concepts = session.execute(select(Concepto).where(Concepto.activo == True)).scalars().all()
                delegations = session.execute(select(Delegacion)).scalars().all()
                rfcs = session.execute(select(Rfc).where(Rfc.activo == True)).scalars().all()
                
                return {
                    "notarias": notarias,
                    "colaboradores": colaboradores,
                    "desarrollos": desarrollos,
                    "conceptos": [{"concepto_id": c.concepto_id, "nombre": c.nombre} for c in concepts],
                    "delegaciones": [{"delegacion_id": d.delegacion_id, "nombre": d.nombre} for d in delegations],
                    "rfcs": [{"rfc_id": r.rfc_id, "razon_social": r.razon_social} for r in rfcs]
                }

    def get_filtros_data(self) -> Dict[str, Any]:
        """Fetches only the lightweight catalogs needed for visor filters (conceptos and rfcs)."""
        if self.api_client.connect_via_api:
            cats = self.api_client.request("GET", "/api/ops/catalogos")
            return {
                "conceptos": cats["conceptos"],
                "rfcs": cats.get("rfcs", [])
            }
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                from sar.src.storage.models import Concepto, Rfc
                from sqlalchemy import select
                concepts = session.execute(select(Concepto).where(Concepto.activo == True)).scalars().all()
                rfcs = session.execute(select(Rfc).where(Rfc.activo == True)).scalars().all()
                return {
                    "conceptos": [{"concepto_id": c.concepto_id, "nombre": c.nombre} for c in concepts],
                    "rfcs": [{"rfc_id": r.rfc_id, "razon_social": r.razon_social} for r in rfcs]
                }

    def save_notaria(self, name: str) -> None:
        """Saves a new notaria entry."""
        if self.api_client.connect_via_api:
            self.api_client.request("POST", "/api/docs/inventario/notarias", data={"nombre": name})
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                repo.save_notaria(name)
                session.commit()

    def save_colaborador(self, name: str) -> None:
        """Saves a new colaborador entry."""
        if self.api_client.connect_via_api:
            self.api_client.request("POST", "/api/docs/inventario/colaboradores", data={"nombre": name})
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                repo.save_colaborador(name)
                session.commit()

    def save_desarrollo(self, name: str, delegacion_id: int) -> None:
        """Saves a new desarrollo entry."""
        if self.api_client.connect_via_api:
            self.api_client.request("POST", "/api/docs/inventario/desarrollos", data={"nombre": name, "delegacion_id": delegacion_id})
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                repo.save_desarrollo(name, delegacion_id)
                session.commit()

    def crear_lote_asignacion(self, tipo_destino: str, notaria_id: int, colaborador_id: int, solicitante_externo: str, observaciones: str, usuario_creacion: int, detalles_list: List[Dict[str, Any]]) -> None:
        """Registers a new assignment lote."""
        if self.api_client.connect_via_api:
            detalles_payload = []
            for det in detalles_list:
                det_dict = dict(det)
                if det_dict.get("fecha_solicitud") and not isinstance(det_dict["fecha_solicitud"], str):
                    det_dict["fecha_solicitud"] = det_dict["fecha_solicitud"].strftime("%Y-%m-%d")
                detalles_payload.append(det_dict)

            payload = {
                "tipo_destino": tipo_destino,
                "notaria_id": notaria_id,
                "colaborador_id": colaborador_id,
                "solicitante_externo": solicitante_externo,
                "observaciones": observaciones,
                "usuario_creacion": usuario_creacion,
                "detalles": detalles_payload
            }
            self.api_client.request("POST", "/api/docs/inventario/lotes", data=payload)
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                repo.crear_lote_asignacion(
                    tipo_destino=tipo_destino,
                    notaria_id=notaria_id,
                    colaborador_id=colaborador_id,
                    solicitante_externo=solicitante_externo,
                    observaciones=observaciones,
                    usuario_creacion=usuario_creacion,
                    detalles_list=detalles_list
                )
                session.commit()

    def get_lotes_asignacion(self) -> List[Dict[str, Any]]:
        """Fetches assignment lotes."""
        if self.api_client.connect_via_api:
            return self.api_client.request("GET", "/api/docs/inventario/lotes")
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                return repo.get_lotes_asignacion()

    def get_lote_detalles(self, lote_id: int) -> List[Dict[str, Any]]:
        """Fetches details of an assignment lote."""
        if self.api_client.connect_via_api:
            return self.api_client.request("GET", f"/api/docs/inventario/lotes/{lote_id}/detalles")
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                return repo.get_lote_detalles(lote_id)

    def get_facturas_by_referencia_id(self, referencia_id: int) -> List[Dict[str, Any]]:
        """Fetches invoices (facturas) associated with a reference ID."""
        if self.api_client.connect_via_api:
            return self.api_client.request("GET", f"/api/docs/inventario/referencias/{referencia_id}/facturas")
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                return repo.get_facturas_by_referencia_id(referencia_id)
