"""R2F UI Service to decouple Control de Recibos y Facturas (Cancún) from direct SQL / APIClient."""

import os
from typing import List, Dict, Any, Tuple, Optional
from sar.src.storage.api_client import APIClient
from cancunbot.src.storage.cancunbot_repos import (
    OrdenCancunRepository, LoteFolioRepository, FolioCancunRepository, ReciboCancunRepository
)
from sar.src.utils.telemetry import track_perf


class R2FUIService:
    """Capa de servicio para la UI de R2F (Cancún) con soporte híbrido 100% transparente (Directo / API)."""

    def __init__(self, db_connector=None, api_client: Optional[APIClient] = None):
        self.db_connector = db_connector
        self.api_client = api_client or APIClient()

    @property
    def is_api_mode(self) -> bool:
        return bool(self.api_client and self.api_client.connect_via_api)

    def get_catalogos(self) -> Tuple[Dict[str, int], Dict[str, int]]:
        """Obtiene mapas de RFCs y Desarrollos activos: (rfc_map, des_map)."""
        transport = "API" if self.is_api_mode else "LOCAL"
        with track_perf("R2FUIService.get_catalogos", transport=transport):
            if self.is_api_mode:
                try:
                    res = self.api_client.request("GET", "/api/docs/cancun/catalogos")
                    if isinstance(res, dict):
                        return res.get("rfcs", {}), res.get("desarrollos", {})
                except Exception as e:
                    print(f"Error R2FUIService.get_catalogos API: {e}")
                    raise e
                return {}, {}
            else:
                with self.db_connector.get_session() as session:
                    from sqlalchemy import text
                    rfc_rows = session.execute(text("SELECT UPPER(rfc), rfc_id FROM sar_catalogo.rfc WHERE activo = true")).fetchall()
                    rfc_map = {r[0]: r[1] for r in rfc_rows}

                    des_rows = session.execute(text("SELECT UPPER(nombre), desarrollo_id FROM sar_catalogo.desarrollo WHERE activo = true")).fetchall()
                    des_map = {r[0]: r[1] for r in des_rows}
                    return rfc_map, des_map

    def list_ordenes(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de todas las órdenes de Cancún."""
        transport = "API" if self.is_api_mode else "LOCAL"
        with track_perf("R2FUIService.list_ordenes", transport=transport):
            if self.is_api_mode:
                try:
                    res = self.api_client.request("GET", "/api/docs/cancun/ordenes")
                    return res if isinstance(res, list) else []
                except Exception as e:
                    print(f"Error R2FUIService.list_ordenes API: {e}")
                    raise e
            else:
                with self.db_connector.get_session() as session:
                    repo = OrdenCancunRepository(session)
                    ordenes = repo.list_all()
                    data = []
                    for o in ordenes:
                        data.append({
                            "orden_id": o.orden_id,
                            "folio_orden": o.folio_orden,
                            "descripcion": o.descripcion or "Sin descripción",
                            "total_lotes": o.total_lotes,
                            "total_folios": o.total_folios,
                            "folios_procesados": o.folios_procesados,
                            "estado_codigo": o.estado.codigo if o.estado else "--",
                            "created_at": o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else "--"
                        })
                    return data

    def list_recibos_paginated(
        self, limit: int, offset: int, search_text: str = "", estado_filter: str = "Todos"
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Obtiene recibos paginados y conteo total de registros."""
        transport = "API" if self.is_api_mode else "LOCAL"
        with track_perf("R2FUIService.list_recibos_paginated", transport=transport):
            if self.is_api_mode:
                try:
                    res = self.api_client.request(
                        "GET",
                        f"/api/docs/cancun/recibos?limit={limit}&offset={offset}&search_text={search_text}&estado_filter={estado_filter}"
                    )
                    if isinstance(res, dict):
                        return res.get("recibos", []), res.get("total", 0)
                except Exception as e:
                    print(f"Error R2FUIService.list_recibos_paginated API: {e}")
                    raise e
                return [], 0
            else:
                with self.db_connector.get_session() as session:
                    repo = ReciboCancunRepository(session)
                    recibos, total_count = repo.get_recibos_paginated(limit, offset, search_text, estado_filter)

                    data_list = []
                    for r in recibos:
                        status_lbl = "--"
                        if r.estado:
                            status_lbl = r.estado.codigo

                        data_list.append({
                            "recibo_id": r.recibo_id,
                            "folio_electronico": r.folio_electronico or r.folio_pase_caja or "--",
                            "rfc": r.rfc or "--",
                            "contribuyente": r.nombre_contribuyente or "--",
                            "concepto": r.concepto or "--",
                            "total": float(r.total) if r.total else 0.0,
                            "pdf_ruta": r.pdf_ruta,
                            "sm": r.sm or "--",
                            "mz": r.mz or "--",
                            "l": r.l or "--",
                            "estado": status_lbl,
                            "fecha": r.fecha_expedicion.strftime("%Y-%m-%d") if r.fecha_expedicion else "--"
                        })
                    return data_list, total_count

    def check_duplicates(self, folios_electronicos: List[str], folios_pase_caja: List[str]) -> Dict[str, str]:
        """Consulta en lote contra la base de datos si los folios ya existen."""
        transport = "API" if self.is_api_mode else "LOCAL"
        with track_perf("R2FUIService.check_duplicates", transport=transport):
            if self.is_api_mode:
                try:
                    payload = {
                        "folios_electronicos": folios_electronicos,
                        "folios_pase_caja": folios_pase_caja
                    }
                    res = self.api_client.request("POST", "/api/docs/cancun/check-duplicates", data=payload)
                    if isinstance(res, dict):
                        return res.get("existing_map", {})
                except Exception as e:
                    print(f"Error R2FUIService.check_duplicates API: {e}")
                    raise e
                return {}
            else:
                unique_elec = [x for x in folios_electronicos if x]
                unique_pase = [x for x in folios_pase_caja if x]
                db_existing_map = {}

                if unique_elec or unique_pase:
                    with self.db_connector.get_session() as session:
                        from sqlalchemy import text
                        sql_dup = """
                            SELECT f.folio_electronico, f.folio_pase_caja, l.folio_lote
                            FROM cancunbot_produccion.folio_cancun f
                            LEFT JOIN cancunbot_produccion.lote_folio l ON f.lote_id = l.lote_id
                            WHERE (f.folio_electronico = ANY(:elec_arr)) OR (f.folio_pase_caja = ANY(:pase_arr))
                        """
                        res_dup = session.execute(text(sql_dup), {
                            "elec_arr": unique_elec if unique_elec else [""],
                            "pase_arr": unique_pase if unique_pase else [""]
                        }).fetchall()

                        for r in res_dup:
                            f_el = r[0]
                            f_pa = r[1]
                            lote_nom = r[2] or "LOTE-PREVIO"
                            if f_el:
                                db_existing_map[f_el] = lote_nom
                            if f_pa:
                                db_existing_map[f_pa] = lote_nom
                return db_existing_map

    def crear_o_anexar_orden(
        self,
        usuario_id: int,
        modo: str, # "CREAR_NUEVA" o "ANEXAR"
        folios: List[Dict[str, Any]],
        descripcion_orden: Optional[str] = None,
        descripcion_lote: Optional[str] = None,
        target_orden_id: Optional[int] = None,
        archivo_excel: Optional[str] = None,
        solicitante: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crea una nueva orden o anexa un nuevo lote de folios a una orden existente."""
        transport = "API" if self.is_api_mode else "LOCAL"
        with track_perf("R2FUIService.crear_o_anexar_orden", transport=transport):
            if self.is_api_mode:
                payload = {
                    "usuario_id": usuario_id,
                    "modo": modo,
                    "target_orden_id": target_orden_id,
                    "descripcion_orden": descripcion_orden,
                    "descripcion_lote": descripcion_lote,
                    "archivo_excel": archivo_excel,
                    "solicitante": solicitante,
                    "folios": folios
                }
                res = self.api_client.request("POST", "/api/docs/cancun/ordenes/crear-o-anexar", data=payload)
                if not isinstance(res, dict) or not res.get("success"):
                    raise RuntimeError(res.get("detail", "Error al procesar orden vía API"))
                return res
            else:
                with self.db_connector.get_session() as session:
                    orden_repo = OrdenCancunRepository(session)
                    lote_repo = LoteFolioRepository(session)
                    folio_repo = FolioCancunRepository(session)

                    if modo == "ANEXAR":
                        if not target_orden_id:
                            raise ValueError("Debe seleccionar una orden existente para anexar el lote.")
                        orden = orden_repo.get_by_id(target_orden_id)
                        if not orden:
                            raise ValueError(f"La orden ID {target_orden_id} no existe.")
                    else:
                        full_desc_orden = descripcion_orden or "Nueva Orden Cancún"
                        if solicitante:
                            full_desc_orden += f" | Solicitante: {solicitante}"
                        orden = orden_repo.create(usuario_id=usuario_id, descripcion=full_desc_orden)

                    lote = lote_repo.create(
                        usuario_id=usuario_id,
                        origen="EXCEL",
                        descripcion=descripcion_lote or "Lote importado",
                        archivo_excel=archivo_excel or "",
                        orden_id=orden.orden_id
                    )

                    guardados = folio_repo.create_bulk(lote.lote_id, folios)
                    lote_repo.update_metrics_and_status(lote.lote_id)
                    orden_repo.update_metrics_and_status(orden.orden_id)
                    session.commit()

                    return {
                        "success": True,
                        "orden_id": orden.orden_id,
                        "folio_orden": orden.folio_orden,
                        "lote_id": lote.lote_id,
                        "folio_lote": lote.folio_lote,
                        "guardados": guardados
                    }

    def liberar_recibos(self, recibo_ids: List[int], estado_codigo: str = "PENDIENTE_FACTURAR") -> int:
        """Actualiza en bloque el estado de recibos a PENDIENTE_FACTURAR."""
        transport = "API" if self.is_api_mode else "LOCAL"
        with track_perf("R2FUIService.liberar_recibos", transport=transport):
            if self.is_api_mode:
                payload = {
                    "recibo_ids": recibo_ids,
                    "estado_codigo": estado_codigo
                }
                res = self.api_client.request("POST", "/api/docs/cancun/recibos/liberar", data=payload)
                if isinstance(res, dict) and res.get("success"):
                    return res.get("liberados", len(recibo_ids))
                raise RuntimeError(res.get("detail", "Error al liberar recibos vía API"))
            else:
                with self.db_connector.get_session() as session:
                    repo = ReciboCancunRepository(session)
                    liberados = 0
                    for rid in recibo_ids:
                        repo.update_status(rid, estado_codigo)
                        liberados += 1
                    session.commit()
                    return liberados
