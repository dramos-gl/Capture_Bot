"""Inventario UI Service to decouple inventory view from direct SQL/APIClient."""

from typing import List, Dict, Any
from sar.src.storage.api_client import APIClient
from sar.src.storage.repositories import InventarioRepository

class InventarioUIService:
    """Service layer for the UI to manage inventory operations using either API or local DB."""

    def __init__(self, db_connector=None):
        self.db_connector = db_connector
        self.api_client = APIClient()

    def get_referencias_facturadas_paginated(self, limit: int, offset: int, search_text: str, concepto_id: int, rfc_id: int, filter_assigned: str, start_date: str = None, end_date: str = None, orden_ids: list = None) -> Dict[str, Any]:
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
            if orden_ids:
                payload["orden_ids"] = orden_ids
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
                    end_date=end_date,
                    orden_ids=orden_ids
                )
                return {"records": res, "total_count": total_count}

    def get_inventario_summary(self, search_text: str = "", concepto_id: int = None, rfc_id: int = None, start_date: str = None, end_date: str = None, orden_ids: list = None) -> Dict[str, Any]:
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
            if orden_ids:
                payload["orden_ids"] = orden_ids
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
                    end_date=end_date,
                    orden_ids=orden_ids
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

    def get_disponibles_count(self, rfc_id: int, concepto_id: int, delegacion_id: int, orden_ids: list = None) -> int:
        """Returns the count of FACTURADA references available for the given (rfc, concepto, delegacion).
        Used by the real-time availability column in the InteractiveGrid.
        """
        if self.api_client.connect_via_api:
            try:
                params = {"rfc_id": rfc_id, "concepto_id": concepto_id, "delegacion_id": delegacion_id}
                if orden_ids:
                    params["orden_ids"] = orden_ids
                result = self.api_client.request(
                    "GET", "/api/docs/inventario/disponibles",
                    data=params
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
                    return repo.count_referencias_disponibles(rfc_id, concepto_id, delegacion_id, orden_ids=orden_ids)
            except Exception:
                return 0

    def get_rfcs_con_stock_facturadas(self) -> List[Dict[str, Any]]:
        """Returns active RFCs that have at least one reference in 'FACTURADA' state."""
        if self.api_client.connect_via_api:
            try:
                return self.api_client.request("GET", "/api/docs/inventario/rfcs-con-stock")
            except Exception:
                return []
        else:
            if not self.db_connector:
                return []
            try:
                with self.db_connector.get_session() as session:
                    repo = InventarioRepository(session)
                    return repo.get_rfcs_con_stock_facturadas()
            except Exception as e:
                print(f"Error get_rfcs_con_stock_facturadas: {e}")
                return []


    def get_desarrollos_activos_para_apartar(self) -> List[Dict[str, Any]]:
        """Returns all active desarrollo_empresa entries (desarrollo+rfc+delegacion) for cascade population."""
        if self.api_client.connect_via_api:
            try:
                return self.api_client.request("GET", "/api/docs/inventario/desarrollos-activos-apartar")
            except Exception:
                return []
        else:
            if not self.db_connector:
                return []
            try:
                with self.db_connector.get_session() as session:
                    repo = InventarioRepository(session)
                    return repo.get_desarrollos_activos_para_apartar()
            except Exception as e:
                print(f"Error get_desarrollos_activos_para_apartar: {e}")
                return []

    def get_rfcs_por_desarrollo(self, desarrollo_id: int) -> List[Dict[str, Any]]:
        """Returns all RFCs linked to a desarrollo (active, from desarrollo_empresa)."""
        if self.api_client.connect_via_api:
            try:
                return self.api_client.request("GET", f"/api/docs/inventario/desarrollos/{desarrollo_id}/rfcs")
            except Exception:
                return []
        else:
            if not self.db_connector:
                return []
            try:
                with self.db_connector.get_session() as session:
                    repo = InventarioRepository(session)
                    return repo.get_rfcs_por_desarrollo(desarrollo_id)
            except Exception as e:
                print(f"Error get_rfcs_por_desarrollo: {e}")
                return []

    def get_delegaciones_por_desarrollo_rfc(self, desarrollo_id: int, rfc_id: int) -> List[Dict[str, Any]]:
        """Returns delegaciones for a (desarrollo, rfc) combination."""
        if self.api_client.connect_via_api:
            try:
                return self.api_client.request(
                    "GET", f"/api/docs/inventario/desarrollos/{desarrollo_id}/rfcs/{rfc_id}/delegaciones"
                )
            except Exception:
                return []
        else:
            if not self.db_connector:
                return []
            try:
                with self.db_connector.get_session() as session:
                    repo = InventarioRepository(session)
                    return repo.get_delegaciones_por_desarrollo_rfc(desarrollo_id, rfc_id)
            except Exception as e:
                print(f"Error get_delegaciones_por_desarrollo_rfc: {e}")
                return []

    def get_conceptos_con_stock(self, rfc_id: int, delegacion_id: int) -> List[Dict[str, Any]]:
        """Returns concepts that have FACTURADA stock for the given rfc + delegacion."""
        if self.api_client.connect_via_api:
            try:
                return self.api_client.request(
                    "GET", "/api/docs/inventario/conceptos-con-stock",
                    data={"rfc_id": rfc_id, "delegacion_id": delegacion_id}
                )
            except Exception:
                return []
        else:
            if not self.db_connector:
                return []
            try:
                with self.db_connector.get_session() as session:
                    repo = InventarioRepository(session)
                    return repo.get_conceptos_con_stock(rfc_id, delegacion_id)
            except Exception as e:
                print(f"Error get_conceptos_con_stock: {e}")
                return []


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
                concepts = session.execute(select(Concepto).where(Concepto.activo == True).order_by(Concepto.nombre)).scalars().all()
                delegations = session.execute(select(Delegacion).where(Delegacion.activo == True).order_by(Delegacion.nombre)).scalars().all()
                rfcs = session.execute(select(Rfc).where(Rfc.activo == True).order_by(Rfc.razon_social)).scalars().all()
                
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
                concepts = session.execute(select(Concepto).where(Concepto.activo == True).order_by(Concepto.nombre)).scalars().all()
                rfcs = session.execute(select(Rfc).where(Rfc.activo == True).order_by(Rfc.razon_social)).scalars().all()
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

    def crear_lote_asignacion(self, tipo_destino: str, notaria_id: int, colaborador_id: int, solicitante_externo: str, observaciones: str, usuario_creacion: int, detalles_list: List[Dict[str, Any]], solo_reservar: bool = False) -> None:
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
                "detalles": detalles_payload,
                "solo_reservar": solo_reservar
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
                    detalles_list=detalles_list,
                    solo_reservar=solo_reservar
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

    def get_lotes_asignacion_filtered(
        self,
        search: str = None,
        tipo_destino: str = None,
        limit: int = 50,
        offset: int = 0,
        start_date: str = None,
        end_date: str = None,
        orden_ids: list = None
    ):
        """Fetches paginated, filterable lotes. Returns (list, total_count)."""
        if self.api_client.connect_via_api:
            # API mode: pass filters as query params
            params = {"limit": limit, "offset": offset}
            if search:
                params["search"] = search
            if tipo_destino:
                params["tipo_destino"] = tipo_destino
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            if orden_ids:
                params["orden_ids"] = orden_ids
            result = self.api_client.request("GET", "/api/docs/inventario/lotes/filtrados", data=params)
            return result.get("lotes", []), result.get("total", 0)
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                return repo.get_lotes_asignacion_filtered(
                    search=search,
                    tipo_destino=tipo_destino,
                    limit=limit,
                    offset=offset,
                    start_date=start_date,
                    end_date=end_date,
                    orden_ids=orden_ids
                )

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

    def get_lote_asignacion_header(self, lote_id: int) -> Dict[str, Any]:
        """Fetches rich header info for a single lote_asignacion."""
        if self.api_client.connect_via_api:
            return self.api_client.request("GET", f"/api/docs/inventario/lotes/{lote_id}/header")
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                return repo.get_lote_asignacion_header(lote_id)

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

    def get_ubicacion_by_coordenadas(
        self, desarrollo_id: int, mz: str, lote: str, edif: str = None, viv: str = None
    ) -> Optional[Dict[str, Any]]:
        """Searches for existing Ubicacion by development and coordinates."""
        if not desarrollo_id or not mz or not lote:
            return None
        if self.api_client.connect_via_api:
            params = {
                "desarrollo_id": desarrollo_id,
                "mz": mz,
                "lote": lote
            }
            if edif:
                params["edif"] = edif
            if viv:
                params["viv"] = viv
            return self.api_client.request("GET", "/api/docs/inventario/ubicaciones/buscar", data=params)
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                return repo.get_ubicacion_by_coordenadas(desarrollo_id, mz, lote, edif, viv)

    def get_asignacion_by_identificador(
        self,
        credito_titular: str = None,
        pa: str = None,
        folio_electronico: str = None,
        desarrollo_id: int = None,
        mz: str = None,
        lote: str = None,
        edif: str = None,
        viv: str = None
    ) -> Optional[Dict[str, Any]]:
        """Multi-criteria search by business identifiers or coordinates."""
        if self.api_client.connect_via_api:
            params = {}
            if credito_titular: params["credito_titular"] = credito_titular
            if pa: params["pa"] = pa
            if folio_electronico: params["folio_electronico"] = folio_electronico
            if desarrollo_id: params["desarrollo_id"] = desarrollo_id
            if mz: params["mz"] = mz
            if lote: params["lote"] = lote
            if edif: params["edif"] = edif
            if viv: params["viv"] = viv
            return self.api_client.request("GET", "/api/docs/inventario/buscar-identificador", data=params)
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                return repo.get_asignacion_by_identificador(
                    credito_titular=credito_titular,
                    pa=pa,
                    folio_electronico=folio_electronico,
                    desarrollo_id=desarrollo_id,
                    mz=mz,
                    lote=lote,
                    edif=edif,
                    viv=viv
                )

    def get_referencias_disponibles_filtro(
        self, rfc_id: int, concepto_id: int, delegacion_id: int, cantidad: int, orden_ids: list = None
    ) -> List[Dict[str, Any]]:
        """Fetches available references under given criteria using FIFO."""
        if self.api_client.connect_via_api:
            payload = {
                "rfc_id": rfc_id,
                "concepto_id": concepto_id,
                "delegacion_id": delegacion_id,
                "cantidad": cantidad
            }
            if orden_ids:
                payload["orden_ids"] = orden_ids
            return self.api_client.request("GET", "/api/docs/inventario/disponibles/filtro", data=payload)
        else:
            if not self.db_connector:
                return []
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                return repo.get_referencias_disponibles_filtro(rfc_id, concepto_id, delegacion_id, cantidad, orden_ids=orden_ids)

    def asignar_referencias_directo(
        self, tipo_destino: str, destino_id: int, usuario_id: int, referencias_data: List[dict],
        solicitante_externo: Optional[str] = None, observaciones: Optional[str] = None
    ) -> int:
        """Assigns selected references directly to Notaria or Colaborador."""
        if self.api_client.connect_via_api:
            payload = {
                "tipo_destino": tipo_destino,
                "destino_id": destino_id,
                "usuario_id": usuario_id,
                "referencias": referencias_data,
                "solicitante_externo": solicitante_externo,
                "observaciones": observaciones
            }
            res = self.api_client.request("POST", "/api/docs/inventario/lotes/asignar-directo", data=payload)
            return res.get("lote_id", 0)
        else:
            if not self.db_connector:
                return 0
            with self.db_connector.get_session() as session:
                repo = InventarioRepository(session)
                lote_id = repo.asignar_referencias_directo(
                    tipo_destino, destino_id, usuario_id, referencias_data, solicitante_externo, observaciones
                )
                session.commit()
                return lote_id
