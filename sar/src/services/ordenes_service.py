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

        # Config parameter for max batch size of solicitudes
        lote_size = self.config_repo.get_lote_solicitud_size()

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

    def actualizar_orden_manual(
        self,
        orden_id: int,
        usuario_id: int,
        sesion_id: Optional[int],
        descripcion: str,
        municipio_id: int,
        renglones: List[Dict[str, Any]]
    ) -> OrdenGeneracion:
        """
        Surgically updates an existing manual order.
        - Changes to RFC, Concepto, or Delegacion on rows that already have generated references are prevented.
        - Deleting rows that have generated references is prevented.
        - Reducing quantity below generated references is prevented.
        - Increments in quantity or new rows are generated as new solicitudes.
        """
        # 1. Fetch order
        orden = self.session.get(OrdenGeneracion, orden_id)
        if not orden:
            raise ValueError(f"No se encontró la orden con ID {orden_id}")
            
        # 2. Check if all solicitudes are in allowed states
        from sqlalchemy import text
        stmt_states = text("""
            SELECT es.codigo
            FROM sar_produccion.solicitud s
            JOIN sar_produccion.grupo_referencia gr ON s.grupo_id = gr.grupo_id
            JOIN sar_catalogo.estado_sistema es ON s.estado_id = es.estado_id
            WHERE gr.orden_id = :orden_id
        """)
        states_result = self.session.execute(stmt_states, {"orden_id": orden_id}).scalars().all()
        
        allowed_states = {"PENDIENTE", "ASIGNADA", "COMPLETADA", "COMPLETADO"}
        for state_code in states_result:
            if state_code not in allowed_states:
                raise ValueError("No se puede editar una orden que tiene solicitudes en estados diferentes de PENDIENTE, ASIGNADA o COMPLETADA.")
                
        # Determine current status code
        stmt_curr_state = text("""
            SELECT es.codigo 
            FROM sar_produccion.orden_generacion o
            JOIN sar_catalogo.estado_sistema es ON o.estado_id = es.estado_id
            WHERE o.orden_id = :orden_id
        """)
        curr_state_code = self.session.execute(stmt_curr_state, {"orden_id": orden_id}).scalar()
        if curr_state_code == "CANCELADA":
            raise ValueError("No se puede editar una orden cancelada.")
            
        # 3. Update main fields
        orden.descripcion = descripcion
        orden.municipio_id = municipio_id

        # Determine states catalog IDs
        estado_grupo_id = self._get_estado_id("PENDIENTE")
        estado_sol_id = self._get_estado_id("PENDIENTE")
        lote_size = self.config_repo.get_lote_solicitud_size()

        # 4. Map existing db structure
        # Key: (rfc_id, concepto_id, delegacion_id) -> list of Solicitud objects
        existing_sols = {}
        # Key: (rfc_id, concepto_id) -> GrupoReferencia object
        existing_groups = {}
        
        for group in list(orden.grupos):
            g_key = (group.rfc_id, group.concepto_id)
            existing_groups[g_key] = group
            for sol in list(group.solicitudes):
                s_key = (group.rfc_id, group.concepto_id, sol.delegacion_id)
                if s_key not in existing_sols:
                    existing_sols[s_key] = []
                existing_sols[s_key].append(sol)

        # 5. Process new and updated rows
        processed_keys = set()
        for row in renglones:
            rfc_id = int(row["rfc_id"])
            concepto_id = int(row["concepto_id"])
            delegacion_id = int(row["delegacion_id"])
            nueva_cantidad = int(row["cantidad"])
            
            key = (rfc_id, concepto_id, delegacion_id)
            processed_keys.add(key)
            
            # Check if this row matches an existing row
            if key in existing_sols:
                sols = existing_sols[key]
                total_solicitada = sum(s.cantidad_solicitada for s in sols)
                total_generada = sum(s.cantidad_generada for s in sols if s.cantidad_generada)
                
                # Enforce rule: cannot decrease quantity below what is already generated
                if nueva_cantidad < total_generada:
                    raise ValueError(f"No se puede reducir la cantidad de la partida por debajo de {total_generada} ya que el bot ya ha generado esas referencias.")
                
                if nueva_cantidad < total_solicitada:
                    # Reducing quantity (only allowed if not below total_generada)
                    diff = total_solicitada - nueva_cantidad
                    sols_sorted = sorted(sols, key=lambda s: s.solicitud_id, reverse=True)
                    for sol in sols_sorted:
                        if diff <= 0:
                            break
                        # How much can we decrease from this solicitud?
                        avail_to_decrease = sol.cantidad_solicitada - (sol.cantidad_generada or 0)
                        decrease_amt = min(diff, avail_to_decrease)
                        if decrease_amt > 0:
                            sol.cantidad_solicitada -= decrease_amt
                            sol.consecutivo_fin -= decrease_amt
                            diff -= decrease_amt
                            if sol.cantidad_solicitada == 0:
                                sol.grupo.solicitudes.remove(sol)
                                self.session.delete(sol)
                    # Adjust group total
                    group = existing_groups[(rfc_id, concepto_id)]
                    group.cantidad_solicitada = nueva_cantidad
                    
                elif nueva_cantidad > total_solicitada:
                    # Increasing quantity: add/increase existing or new solicitudes
                    diff = nueva_cantidad - total_solicitada
                    group = existing_groups[(rfc_id, concepto_id)]
                    group.cantidad_solicitada = nueva_cantidad
                    
                    # Sort solicitudes by consecutivo_fin to find the last one
                    sols_sorted = sorted(sols, key=lambda s: s.consecutivo_fin)
                    last_sol = sols_sorted[-1]
                    
                    # Get state code of the last solicitud
                    stmt_sol_state = text("SELECT codigo FROM sar_catalogo.estado_sistema WHERE estado_id = :eid")
                    last_sol_state = self.session.execute(stmt_sol_state, {"eid": last_sol.estado_id}).scalar()
                    
                    # If the last solicitud is still PENDIENTE, or ASIGNADA with 0 generated references, we can increase it up to lote_size
                    if last_sol_state == "PENDIENTE" or (last_sol_state == "ASIGNADA" and (last_sol.cantidad_generada or 0) == 0):
                        space_left = lote_size - last_sol.cantidad_solicitada
                        add_to_last = min(diff, space_left)
                        if add_to_last > 0:
                            last_sol.cantidad_solicitada += add_to_last
                            last_sol.consecutivo_fin += add_to_last
                            diff -= add_to_last
                            
                    if diff > 0:
                        # Find highest consecutivo in the group
                        max_consecutivo = 0
                        for s in group.solicitudes:
                            if s.consecutivo_fin > max_consecutivo:
                                max_consecutivo = s.consecutivo_fin
                                
                        consecutivo_actual = max_consecutivo + 1
                        lotes_requeridos = math.ceil(diff / lote_size)
                        for i in range(lotes_requeridos):
                            cantidad_lote = min(lote_size, diff - (i * lote_size))
                            consecutivo_fin = consecutivo_actual + cantidad_lote - 1
                            
                            solicitud = Solicitud(
                                grupo_id=group.grupo_id,
                                delegacion_id=delegacion_id,
                                cantidad_solicitada=cantidad_lote,
                                consecutivo_inicio=consecutivo_actual,
                                consecutivo_fin=consecutivo_fin,
                                estado_id=estado_sol_id
                            )
                            self.session.add(solicitud)
                            consecutivo_actual = consecutivo_fin + 1
            else:
                # This is a completely new row
                # Check if group already exists (same RFC + Concepto but different delegacion)
                g_key = (rfc_id, concepto_id)
                if g_key in existing_groups:
                    group = existing_groups[g_key]
                    group.cantidad_solicitada += nueva_cantidad
                else:
                    group = GrupoReferencia(
                        orden_id=orden.orden_id,
                        rfc_id=rfc_id,
                        concepto_id=concepto_id,
                        cantidad_solicitada=nueva_cantidad,
                        estado_id=estado_grupo_id
                    )
                    self.session.add(group)
                    self.session.flush()
                    existing_groups[g_key] = group
                
                # Consecutivo starts from max of group or 1
                max_consecutivo = 0
                for s in group.solicitudes:
                    if s.consecutivo_fin > max_consecutivo:
                        max_consecutivo = s.consecutivo_fin
                
                consecutivo_actual = max_consecutivo + 1
                lotes_requeridos = math.ceil(nueva_cantidad / lote_size)
                for i in range(lotes_requeridos):
                    cantidad_lote = min(lote_size, nueva_cantidad - (i * lote_size))
                    consecutivo_fin = consecutivo_actual + cantidad_lote - 1
                    
                    solicitud = Solicitud(
                        grupo_id=group.grupo_id,
                        delegacion_id=delegacion_id,
                        cantidad_solicitada=cantidad_lote,
                        consecutivo_inicio=consecutivo_actual,
                        consecutivo_fin=consecutivo_fin,
                        estado_id=estado_sol_id
                    )
                    self.session.add(solicitud)
                    consecutivo_actual = consecutivo_fin + 1

        # 6. Process deleted rows (existing ones that are not in the new renglones list)
        for key, sols in existing_sols.items():
            if key not in processed_keys:
                total_generada = sum(s.cantidad_generada for s in sols if s.cantidad_generada)
                if total_generada > 0:
                    rfc_text = sols[0].grupo.rfc.rfc if sols[0].grupo.rfc else str(key[0])
                    raise ValueError(f"No se puede eliminar la partida para RFC {rfc_text} porque ya tiene {total_generada} referencias generadas por el bot.")
                
                # Safe to delete
                for sol in sols:
                    group = sol.grupo
                    group.cantidad_solicitada -= sol.cantidad_solicitada
                    group.solicitudes.remove(sol)
                    self.session.delete(sol)
                    
                    if group.cantidad_solicitada <= 0 or len(group.solicitudes) == 0:
                        if group in orden.grupos:
                            orden.grupos.remove(group)
                        self.session.delete(group)
                        g_key = (group.rfc_id, group.concepto_id)
                        if g_key in existing_groups:
                            del existing_groups[g_key]

        self.session.flush()

        # Log event if an audit event exists
        try:
            self.audit_repo.log_evento(
                evento_codigo="MODIFICACION_ORDEN",
                modulo="PRODUCCION",
                usuario_id=usuario_id,
                sesion_id=sesion_id,
                detalle={
                    "folio": orden.folio,
                    "orden_id": orden.orden_id,
                    "grupos": len(orden.grupos),
                    "total_referencias": sum(g.cantidad_solicitada for g in orden.grupos)
                }
            )
        except Exception:
            pass

        return orden
