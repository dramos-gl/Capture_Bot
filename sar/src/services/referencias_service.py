"""Referencias Service to decouple view from direct SQL or APIClient."""

from typing import List, Tuple, Dict, Any
from sar.src.storage.api_client import APIClient
from sar.src.storage.repositories import ProduccionRepository

class ReferenciasService:
    """Service layer to manage reference operations using either API or DB Repository."""

    def __init__(self, db_connector=None):
        self.db_connector = db_connector
        self.api_client = APIClient()

    def get_referencias_paginated(
        self, limit: int, offset: int, search_text: str, estado_filter: str, orden_ids: list = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Fetches paginated references based on filters."""
        if self.api_client.connect_via_api:
            orden_ids_str = ",".join([str(x) for x in orden_ids]) if orden_ids else None
            payload = {
                "limit": limit,
                "offset": offset,
                "search_text": search_text,
                "estado_filter": estado_filter,
                "orden_ids": orden_ids_str
            }
            res = self.api_client.request("GET", "/api/docs/referencias", data=payload)
            return res["records"], res["total_count"]
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = ProduccionRepository(session)
                return repo.get_referencias_paginated(
                    limit=limit,
                    offset=offset,
                    search_text=search_text,
                    estado_filter=estado_filter,
                    orden_ids=orden_ids
                )

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

    def get_pending_authorization_stats(self, selected_ids: List[int]) -> Dict[str, Any]:
        """Retrieves the total pending references count for requests associated with selected_ids."""
        if not selected_ids:
            return {"sol_ids": [], "total_pendientes": 0}
            
        if self.api_client.connect_via_api:
            payload = {"referencia_ids": ",".join(map(str, selected_ids))}
            # Fallback or API request if supported
            return self.api_client.request("GET", "/api/docs/referencias/pending-stats", data=payload)
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            from sqlalchemy import text
            with self.db_connector.get_session() as session:
                stmt_sols = text("""
                    SELECT DISTINCT solicitud_id FROM sar_produccion.referencia
                    WHERE referencia_id IN :ref_ids
                """)
                sol_rows = session.execute(stmt_sols, {"ref_ids": tuple(selected_ids)}).fetchall()
                sol_ids = [r[0] for r in sol_rows if r[0]]
                
                if not sol_ids:
                    return {"sol_ids": [], "total_pendientes": 0}
                    
                stmt_pending = text("""
                    SELECT COUNT(*) FROM sar_produccion.referencia r
                    JOIN sar_catalogo.estado_sistema es ON r.estado_id = es.estado_id
                    WHERE r.solicitud_id IN :sol_ids AND es.codigo = 'PENDIENTE_AUTORIZACION'
                """)
                total_pendientes = session.execute(stmt_pending, {"sol_ids": tuple(sol_ids)}).scalar() or 0
                return {"sol_ids": sol_ids, "total_pendientes": total_pendientes}

    def update_referencias_estado_masivo(
        self, selected_ids: List[int], nuevo_estado: str, rechazar_restantes: bool = False
    ) -> None:
        """Updates the state of multiple references."""
        if not selected_ids:
            return
            
        if self.api_client.connect_via_api:
            payload = {
                "referencia_ids": selected_ids,
                "estado": nuevo_estado,
                "rechazar_restantes": rechazar_restantes
            }
            self.api_client.request("POST", "/api/docs/referencias/cambiar-estado-masivo", data=payload)
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = ProduccionRepository(session)
                repo.update_referencias_estado_masivo(selected_ids, nuevo_estado, rechazar_restantes)
                session.commit()

    def get_dashboard_kpis(self, orden_ids: list = None) -> Dict[str, Any]:
        """Fetches dashboard KPI metrics."""
        if self.api_client.connect_via_api:
            orden_ids_str = ",".join([str(x) for x in orden_ids]) if orden_ids else ""
            return self.api_client.request("GET", "/api/ops/dashboard-kpis", data={"orden_ids": orden_ids_str})
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            with self.db_connector.get_session() as session:
                repo = ProduccionRepository(session)
                return repo.get_dashboard_kpis(orden_ids)

    def get_metrics_report(self, rfc_id: int = None, concepto_id: int = None, delegacion_id: int = None, orden_ids: list = None) -> List[Dict[str, Any]]:
        """Retrieves aggregated metrics using the vw_metricas_referencias view.
        
        The view encapsulates the correct JOINs between referencia, grupo_referencia
        (rfc_id, concepto_id), solicitud (delegacion_id), and orden_generacion.
        """
        if orden_ids is not None and len(orden_ids) == 0:
            return []

        if self.api_client.connect_via_api:
            payload = {}
            if rfc_id: payload["rfc_id"] = rfc_id
            if concepto_id: payload["concepto_id"] = concepto_id
            if delegacion_id: payload["delegacion_id"] = delegacion_id
            if orden_ids: payload["orden_ids"] = ",".join(str(x) for x in orden_ids)
            try:
                return self.api_client.request("GET", "/api/docs/referencias/metrics", data=payload)
            except Exception:
                return []
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            from sqlalchemy import text
            with self.db_connector.get_session() as session:
                # Build dynamic WHERE using the view columns
                conditions = ["1=1"]
                params = {}

                if orden_ids:
                    conditions.append("orden_id IN :orden_ids")
                    params["orden_ids"] = tuple(orden_ids)
                if rfc_id:
                    conditions.append("rfc_id = :rfc_id")
                    params["rfc_id"] = rfc_id
                if concepto_id:
                    conditions.append("concepto_id = :concepto_id")
                    params["concepto_id"] = concepto_id
                if delegacion_id:
                    conditions.append("delegacion_id = :delegacion_id")
                    params["delegacion_id"] = delegacion_id

                where_clause = " AND ".join(conditions)

                query = f"""
                    SELECT
                        rfc_nombre                         AS rfc_name,
                        concepto_nombre                    AS concepto_name,
                        COALESCE(delegacion_nombre, 'Sin Delegacion') AS delegacion_name,
                        COUNT(referencia_id)               AS total_referencias,
                        COALESCE(SUM(importe), 0)          AS importe_total
                    FROM sar_produccion.vw_metricas_referencias
                    WHERE {where_clause}
                    GROUP BY rfc_nombre, concepto_nombre, delegacion_nombre
                    ORDER BY rfc_nombre, concepto_nombre, delegacion_nombre
                """

                rows = session.execute(text(query), params).fetchall()
                return [
                    {
                        "rfc_name": r[0],
                        "concepto_name": r[1],
                        "delegacion_name": r[2],
                        "total_referencias": r[3],
                        "importe_total": float(r[4])
                    }
                    for r in rows
                ]

    def get_metrics_summary(self, rfc_id: int = None, concepto_id: int = None, delegacion_id: int = None, orden_ids: list = None) -> Dict[str, Any]:
        """Returns KPI summary from vw_metricas_referencias: total amount, total refs, and count/amount per estado_codigo."""
        if orden_ids is not None and len(orden_ids) == 0:
            return {"total_referencias": 0, "importe_total": 0.0, "por_estado": {}}

        if self.api_client.connect_via_api:
            try:
                payload = {}
                if rfc_id: payload["rfc_id"] = rfc_id
                if concepto_id: payload["concepto_id"] = concepto_id
                if delegacion_id: payload["delegacion_id"] = delegacion_id
                if orden_ids: payload["orden_ids"] = ",".join(str(x) for x in orden_ids)
                return self.api_client.request("GET", "/api/docs/referencias/metrics-summary", data=payload)
            except Exception:
                return {"total_referencias": 0, "importe_total": 0.0, "por_estado": {}}
        else:
            if not self.db_connector:
                raise ValueError("db_connector is required when connect_via_api is False")
            from sqlalchemy import text
            with self.db_connector.get_session() as session:
                conditions = ["1=1"]
                params = {}
                if orden_ids:
                    conditions.append("orden_id IN :orden_ids")
                    params["orden_ids"] = tuple(orden_ids)
                if rfc_id:
                    conditions.append("rfc_id = :rfc_id")
                    params["rfc_id"] = rfc_id
                if concepto_id:
                    conditions.append("concepto_id = :concepto_id")
                    params["concepto_id"] = concepto_id
                if delegacion_id:
                    conditions.append("delegacion_id = :delegacion_id")
                    params["delegacion_id"] = delegacion_id
                where_clause = " AND ".join(conditions)

                # Global totals
                total_row = session.execute(text(f"""
                    SELECT COUNT(referencia_id), COALESCE(SUM(importe), 0)
                    FROM sar_produccion.vw_metricas_referencias
                    WHERE {where_clause}
                """), params).fetchone()

                # Per-status breakdown
                estado_rows = session.execute(text(f"""
                    SELECT estado_codigo, COUNT(referencia_id), COALESCE(SUM(importe), 0)
                    FROM sar_produccion.vw_metricas_referencias
                    WHERE {where_clause}
                    GROUP BY estado_codigo
                    ORDER BY estado_codigo
                """), params).fetchall()

                por_estado = {
                    r[0]: {"total": r[1], "importe": float(r[2])}
                    for r in estado_rows
                }

                return {
                    "total_referencias": total_row[0] if total_row else 0,
                    "importe_total": float(total_row[1]) if total_row else 0.0,
                    "por_estado": por_estado,
                }
