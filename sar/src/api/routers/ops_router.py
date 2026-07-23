from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sar.src.storage.db_connector import DatabaseConnector
from sar.src.storage.repositories import CatalogoRepository, ProduccionRepository
from sar.src.services.ordenes_service import OrdenesService

router = APIRouter(prefix="/api/ops", tags=["operations"])
db_connector = DatabaseConnector()

def get_db():
    with db_connector.get_session() as session:
        yield session

# Pydantic schemas
class OrdenCrearRequest(BaseModel):
    usuario_id: int
    sesion_id: Optional[int] = None
    descripcion: str
    municipio_id: int
    renglones: List[Dict[str, Any]]

class EstadoChangeRequest(BaseModel):
    usuario_id: int
    sesion_id: Optional[int] = None
    estado_codigo: str

# Endpoints de Catálogos
@router.get("/catalogos")
def get_catalogos(db: Session = Depends(get_db)):
    """Retorna los catálogos activos (RFCs, Conceptos, Delegaciones, Municipios)."""
    repo = CatalogoRepository(db)
    try:
        rfcs = [{"rfc_id": r.rfc_id, "rfc": r.rfc, "razon_social": r.razon_social} for r in repo.get_rfcs_activos()]
        conceptos = [{"concepto_id": c.concepto_id, "nombre": c.nombre} for c in repo.get_conceptos_activos()]
        delegaciones = [{"delegacion_id": d.delegacion_id, "nombre": d.nombre} for d in repo.get_delegaciones_activas()]
        municipios = [{"municipio_id": m.municipio_id, "nombre": m.nombre, "activo": m.activo} for m in repo.get_all_municipios()]
        
        return {
            "rfcs": rfcs,
            "conceptos": conceptos,
            "delegaciones": delegaciones,
            "municipios": municipios
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener catálogos: {str(e)}")

# Endpoints de Órdenes
@router.get("/ordenes")
def list_ordenes(db: Session = Depends(get_db)):
    """Retorna el listado completo de órdenes."""
    repo = ProduccionRepository(db)
    try:
        return repo.get_ordenes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar órdenes: {str(e)}")

@router.post("/ordenes")
def create_orden(request: OrdenCrearRequest, db: Session = Depends(get_db)):
    """Crea una orden manual a partir de renglones detallados."""
    service = OrdenesService(db)
    try:
        nueva_orden = service.crear_orden_manual(
            usuario_id=request.usuario_id,
            sesion_id=request.sesion_id,
            descripcion=request.descripcion,
            municipio_id=request.municipio_id,
            renglones=request.renglones
        )
        return {
            "folio": nueva_orden.folio,
            "orden_id": nueva_orden.orden_id,
            "estado_id": nueva_orden.estado_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear la orden: {str(e)}")

@router.get("/ordenes/{orden_id}/check-ready")
def check_orden_ready(orden_id: int, db: Session = Depends(get_db)):
    """Verifica si una orden está lista para procesamiento masivo y retorna metadatos."""
    repo = ProduccionRepository(db)
    try:
        res = repo.check_orden_ready_for_masivo(orden_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ordenes/{orden_id}/estado-masivo")
def change_orden_estado_masivo(orden_id: int, request: EstadoChangeRequest, db: Session = Depends(get_db)):
    """Cambia el estado de una orden de manera masiva (Autorizar/Rechazar)."""
    repo = ProduccionRepository(db)
    try:
        # Validar si está lista para el cambio
        res = repo.check_orden_ready_for_masivo(orden_id)
        if not res["ready"]:
            raise HTTPException(status_code=400, detail=res["reason"])
        
        repo.update_orden_estado_masivo(
            orden_id=orden_id,
            estado_codigo=request.estado_codigo,
            usuario_id=request.usuario_id,
            sesion_id=request.sesion_id
        )
        return {"detail": f"Orden {orden_id} marcada como {request.estado_codigo} correctamente"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cambiar el estado: {str(e)}")

@router.post("/ordenes/{orden_id}/cancelar")
def cancelar_orden(orden_id: int, request: EstadoChangeRequest, db: Session = Depends(get_db)):
    """Cancela transaccionalmente la orden."""
    repo = ProduccionRepository(db)
    try:
        repo.cancelar_orden_transaccional(
            orden_id=orden_id,
            usuario_id=request.usuario_id,
            sesion_id=request.sesion_id
        )
        return {"detail": f"Orden {orden_id} cancelada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cancelar la orden: {str(e)}")

@router.get("/dashboard-kpis")
def get_dashboard_kpis(orden_ids: Optional[str] = None, db: Session = Depends(get_db)):
    """Retorna los contadores KPI del tablero de control."""
    repo = ProduccionRepository(db)
    try:
        parsed_ids = [int(x) for x in orden_ids.split(",")] if orden_ids else []
        kpis = repo.get_dashboard_kpis(parsed_ids)
        return kpis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener KPIs: {str(e)}")

@router.get("/ordenes/{orden_id}")
def get_orden_detalle(orden_id: int, db: Session = Depends(get_db)):
    """Obtiene el detalle completo y estado de edición de una orden específica."""
    repo = ProduccionRepository(db)
    try:
        data = repo.get_orden_detalle_edicion(orden_id)
        return data
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/ordenes/{orden_id}")
def update_orden(orden_id: int, request: OrdenCrearRequest, db: Session = Depends(get_db)):
    """Actualiza una orden existente modificando sus partidas."""
    service = OrdenesService(db)
    try:
        orden = service.actualizar_orden_manual(
            orden_id=orden_id,
            usuario_id=request.usuario_id,
            sesion_id=request.sesion_id,
            descripcion=request.descripcion,
            municipio_id=request.municipio_id,
            renglones=request.renglones
        )
        return {
            "folio": orden.folio,
            "orden_id": orden.orden_id,
            "estado_id": orden.estado_id
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar la orden: {str(e)}")
