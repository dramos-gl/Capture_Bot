"""Service layer for business logic of generating Orders and dividing them into Solicitudes."""

import math
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime

from sar.src.storage.repositories import (
    OrdenRepository,
    AuditRepository,
    ConfigRepository
)
from sar.src.storage.models import (
    OrdenGeneracion,
    GrupoReferencia,
    Solicitud,
    EstadoSistema,
    EventoSistema
)

class OrdenesService:
    """Handles the transactional generation of orders, groups and work requests."""

    def __init__(self, session: Session):
        self.session = session
        self.orden_repo = OrdenRepository(session)
        self.audit_repo = AuditRepository(session)
        self.config_repo = ConfigRepository(session)

    def _get_estado_id(self, codigo: str) -> int:
        """Helper to get state ID from catalog."""
        stmt = select(EstadoSistema.estado_id).where(EstadoSistema.codigo == codigo)
        estado_id = self.session.execute(stmt).scalars().first()
        if not estado_id:
            # Fallback or create dummy if not exists during dev
            # In a real system, the catalog is pre-populated
            estado = EstadoSistema(entidad="GENERAL", codigo=codigo, descripcion=codigo)
            self.session.add(estado)
            self.session.flush()
            return estado.estado_id
        return estado_id

    def crear_orden_manual(
        self,
        usuario_id: int,
        sesion_id: Optional[int],
        descripcion: str,
        municipio_id: int,
        renglones: List[Dict[str, Any]]
    ) -> OrdenGeneracion:
        """
        Registers a new manual order.
        `renglones` format: [{'rfc_id': int, 'concepto_id': int, 'delegacion_id': int, 'cantidad': int}]
        """
        # Determine initial states
        estado_orden_id = self._get_estado_id("PENDIENTE")
        estado_grupo_id = self._get_estado_id("PENDIENTE")
        estado_sol_id = self._get_estado_id("PENDIENTE")

        # Config parameter for max batch size
        lote_size = self.config_repo.get_lote_size()

        # Generate unique Folio (e.g. ORD-YYYYMMDD-HHMMSS)
        folio_str = f"ORD-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        # 1. Create the Order
        nueva_orden = OrdenGeneracion(
            folio=folio_str,
            descripcion=descripcion,
            municipio_id=municipio_id,
            estado_id=estado_orden_id,
            usuario_id=usuario_id
        )
        self.session.add(nueva_orden)
        self.session.flush()

        total_solicitudes_creadas = 0
        total_referencias_solicitadas = 0

        # 2. Group rows by (rfc_id, concepto_id) to avoid UNIQUE constraint violation
        grupos_dict = {}
        for row in renglones:
            key = (row['rfc_id'], row['concepto_id'])
            if key not in grupos_dict:
                grupos_dict[key] = {'cantidad_total': 0, 'filas': []}
            grupos_dict[key]['cantidad_total'] += int(row['cantidad'])
            grupos_dict[key]['filas'].append(row)
            
            total_referencias_solicitadas += int(row['cantidad'])

        # 3. Create Groups and divide into Solicitudes
        for (rfc_id, concepto_id), data in grupos_dict.items():
            cantidad_total = data['cantidad_total']
            
            # Create ONE Group per RFC+Concepto combination
            grupo = GrupoReferencia(
                orden_id=nueva_orden.orden_id,
                rfc_id=rfc_id,
                concepto_id=concepto_id,
                cantidad_solicitada=cantidad_total,
                estado_id=estado_grupo_id
            )
            self.session.add(grupo)
            self.session.flush()

            consecutivo_actual = 1
            
            # Create Solicitudes for each row under this group
            for row in data['filas']:
                delegacion_id = row.get('delegacion_id')
                cantidad_fila = int(row['cantidad'])
                
                # Divide into Solicitudes (batches) based on lote_size
                lotes_requeridos = math.ceil(cantidad_fila / lote_size)

                for i in range(lotes_requeridos):
                    cantidad_lote = min(lote_size, cantidad_fila - (i * lote_size))
                    consecutivo_fin = consecutivo_actual + cantidad_lote - 1

                    solicitud = Solicitud(
                        grupo_id=grupo.grupo_id,
                        delegacion_id=delegacion_id,
                        cantidad_solicitada=cantidad_lote,
                        consecutivo_inicio=consecutivo_actual,
                        consecutivo_fin=consecutivo_fin,
                        estado_id=estado_sol_id
                    )
                    self.session.add(solicitud)
                    consecutivo_actual = consecutivo_fin + 1
                    total_solicitudes_creadas += 1

        self.session.flush()

        # Log event if an audit event exists
        try:
            self.audit_repo.log_evento(
                evento_codigo="CREACION_ORDEN",
                modulo="PRODUCCION",
                usuario_id=usuario_id,
                sesion_id=sesion_id,
                detalle={
                    "folio": folio_str,
                    "grupos": len(renglones),
                    "solicitudes": total_solicitudes_creadas,
                    "total_referencias": total_referencias_solicitadas
                }
            )
        except Exception:
            # EventoSistema might not have CREACION_ORDEN initialized yet
            pass

        return nueva_orden
