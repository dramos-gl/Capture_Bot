"""Order service handling order generation orchestration and range calculations."""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from sar.src.storage.models import (
    OrdenGeneracion,
    GrupoReferencia,
    Solicitud,
    EstadoSistema
)
from sar.src.storage.repositories import OrdenRepository, AuditRepository


class OrderService:
    """Orchestrates order creation, grouping, and consecutive range pre-allocation."""

    def __init__(self, session: Session):
        self.session = session
        self.orden_repo = OrdenRepository(session)
        self.audit_repo = AuditRepository(session)

    def _get_estado_id(self, entidad: str, codigo: str) -> int:
        """Helper to dynamically fetch the state ID from the catalog."""
        stmt = select(EstadoSistema.estado_id).where(
            and_(EstadoSistema.entidad == entidad, EstadoSistema.codigo == codigo)
        )
        estado_id = self.session.execute(stmt).scalar()
        if not estado_id:
            # Si por alguna razón no existe en el catálogo, crearlo en caliente para estabilidad
            nuevo_estado = EstadoSistema(entidad=entidad, codigo=codigo, descripcion=f"Estado {codigo} de {entidad}")
            self.session.add(nuevo_estado)
            self.session.flush()
            return nuevo_estado.estado_id
        return estado_id

    def create_order(
        self,
        descripcion: str,
        usuario_id: int,
        sesion_id: Optional[int],
        items: List[Dict[str, Any]]
    ) -> OrdenGeneracion:
        """
        Creates an Order, groups requests by RFC+Concept, allocates ranges, and generates Solicitudes.
        
        Args:
            descripcion: Description text for the order.
            usuario_id: ID of the user creating the order.
            sesion_id: ID of the active user session.
            items: List of dictionaries: [{"rfc_id": X, "concepto_id": Y, "delegacion_id": Z, "cantidad": N}]
        """
        # 1. Generar un folio único secuencial temporal
        import uuid
        folio_unico = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        # 2. Obtener estado inicial de la Orden
        estado_orden_id = self._get_estado_id("orden_generacion", "ABIERTA")

        # 3. Crear la cabecera de la Orden
        orden = OrdenGeneracion(
            folio=folio_unico,
            descripcion=descripcion,
            estado_id=estado_orden_id,
            usuario_id=usuario_id
        )
        self.orden_repo.create(orden)

        # 4. Agrupar items por (rfc_id, concepto_id)
        grouped_items: Dict[tuple[int, int], List[Dict[str, Any]]] = {}
        for item in items:
            key = (item["rfc_id"], item["concepto_id"])
            if key not in grouped_items:
                grouped_items[key] = []
            grouped_items[key].append(item)

        # Obtener estados iniciales para Grupos y Solicitudes
        estado_grupo_id = self._get_estado_id("grupo_referencia", "PENDIENTE")
        estado_solicitud_id = self._get_estado_id("solicitud", "PENDIENTE")

        # 5. Crear los Grupos y sus correspondientes Solicitudes con rangos pre-asignados
        for (rfc_id, concepto_id), list_items in grouped_items.items():
            # Calcular total solicitado para el grupo
            total_solicitado = sum(item["cantidad"] for item in list_items)

            # Instanciar el Grupo de Referencias
            grupo = GrupoReferencia(
                orden_id=orden.orden_id,
                rfc_id=rfc_id,
                concepto_id=concepto_id,
                cantidad_solicitada=total_solicitado,
                cantidad_generada=0,
                ultimo_consecutivo=0,
                estado_id=estado_grupo_id
            )
            self.session.add(grupo)
            self.session.flush()  # Generar el grupo_id

            # Pre-asignar rangos secuenciales a las Solicitudes dentro de este grupo
            consecutivo_runner = 1  # Cada grupo inicia consecutivo en 1

            for item in list_items:
                cant = item["cantidad"]
                consecutivo_inicio = consecutivo_runner
                consecutivo_fin = consecutivo_runner + cant - 1

                solicitud = Solicitud(
                    grupo=grupo,
                    delegacion_id=item["delegacion_id"],
                    cantidad_solicitada=cant,
                    cantidad_generada=0,
                    consecutivo_inicio=consecutivo_inicio,
                    consecutivo_fin=consecutivo_fin,
                    ultimo_consecutivo=consecutivo_inicio - 1,  # Inicializado en inicio - 1
                    estado_id=estado_solicitud_id
                )
                self.session.add(solicitud)
                
                # Avanzar el runner para la siguiente delegación
                consecutivo_runner = consecutivo_fin + 1

        # 6. Registrar auditoría del evento
        self.audit_repo.log_evento(
            evento_codigo="CREAR_ORDEN",
            modulo="ORDENES",
            usuario_id=usuario_id,
            sesion_id=sesion_id,
            valor_nuevo={"folio": folio_unico, "items_count": len(items)},
            detalle={"mensaje": f"Orden {folio_unico} creada exitosamente con {len(items)} solicitudes."}
        )

        return orden
