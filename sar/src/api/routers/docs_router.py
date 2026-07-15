from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sar.src.storage.db_connector import DatabaseConnector
from sar.src.storage.repositories import OperacionRepository, ProduccionRepository, SolicitudRepository
from sar.src.storage.models import Solicitud, Referencia, ArchivoPDF, Factura, EstadoSistema

router = APIRouter(prefix="/api/docs", tags=["documents"])
db_connector = DatabaseConnector()

def get_db():
    with db_connector.get_session() as session:
        yield session

# Pydantic schemas
class AsignarSolicitudRequest(BaseModel):
    usuario_id: int

class UpdateSolicitudCantidadRequest(BaseModel):
    nueva_cantidad: int

class RegistrarReferenciaRequest(BaseModel):
    grupo_id: int
    solicitud_id: int
    consecutivo_grupo: int
    referencia_portal: str
    importe: Optional[float] = None
    fecha_generacion: str # YYYY-MM-DD
    fecha_vigencia: Optional[str] = None # YYYY-MM-DD
    usuario_asignado: Optional[int] = None
    estado_codigo: str

class RegistrarPdfRequest(BaseModel):
    tipo_archivo: str
    estado_archivo: str
    nombre_archivo: str
    ruta_archivo: str
    hash_sha256: str
    tamano_bytes: int

# Endpoints de Solicitudes
@router.get("/solicitudes")
def list_solicitudes(orden_ids: Optional[str] = None, db: Session = Depends(get_db)):
    """Retorna solicitudes filtradas opcionalmente por ids de orden."""
    repo = OperacionRepository(db)
    try:
        parsed_ids = [int(x) for x in orden_ids.split(",")] if orden_ids else None
        return repo.get_solicitudes(parsed_ids)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar solicitudes: {str(e)}")

@router.get("/solicitudes/asignadas/{usuario_id}")
def get_solicitudes_asignadas(usuario_id: int, ver_todas: bool = False, db: Session = Depends(get_db)):
    """Retorna solicitudes asignadas a un operador."""
    repo = OperacionRepository(db)
    try:
        return repo.get_solicitudes_asignadas(usuario_id, ver_todas)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener solicitudes asignadas: {str(e)}")

@router.post("/solicitudes/{solicitud_id}/asignar")
def asignar_solicitud(solicitud_id: int, request: AsignarSolicitudRequest, db: Session = Depends(get_db)):
    """Asigna una solicitud a un usuario."""
    repo = OperacionRepository(db)
    try:
        success = repo.asignar_solicitud(solicitud_id, request.usuario_id)
        if not success:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        return {"detail": "Solicitud asignada con éxito"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al asignar solicitud: {str(e)}")

@router.post("/solicitudes/{solicitud_id}/cancelar")
def cancelar_solicitud(solicitud_id: int, db: Session = Depends(get_db)):
    """Cancela una solicitud individual."""
    repo = OperacionRepository(db)
    try:
        success = repo.cancelar_solicitud(solicitud_id)
        return {"success": bool(success)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cancelar la solicitud: {str(e)}")

@router.put("/solicitudes/{solicitud_id}/cantidad")
def editar_cantidad_solicitud(solicitud_id: int, request: UpdateSolicitudCantidadRequest, db: Session = Depends(get_db)):
    """Modifica la cantidad de consecutivas de una solicitud."""
    repo = OperacionRepository(db)
    try:
        success = repo.editar_cantidad_solicitud(solicitud_id, request.nueva_cantidad)
        return {"success": bool(success)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al editar cantidad: {str(e)}")

@router.get("/solicitudes/{solicitud_id}/bot-context")
def get_solicitud_bot_context(solicitud_id: int, db: Session = Depends(get_db)):
    """Retorna el contexto detallado para la ejecución de Playwright."""
    repo = OperacionRepository(db)
    try:
        return repo.get_solicitud_bot_context(solicitud_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener contexto: {str(e)}")

# Endpoints de Referencias
@router.get("/referencias")
def get_referencias_paginated(
    limit: int = 200, 
    offset: int = 0, 
    search_text: str = "", 
    estado_filter: str = "Todos", 
    orden_ids: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    """Retorna el listado paginado y con filtros de referencias."""
    repo = ProduccionRepository(db)
    try:
        parsed_ids = [int(x) for x in orden_ids.split(",")] if orden_ids else None
        records, total_count = repo.get_referencias_paginated(
            limit=limit,
            offset=offset,
            search_text=search_text,
            estado_filter=estado_filter,
            orden_ids=parsed_ids
        )
        return {"records": records, "total_count": total_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener referencias: {str(e)}")

@router.post("/referencias")
def registrar_referencia(request: RegistrarReferenciaRequest, db: Session = Depends(get_db)):
    """Registra una referencia generada por el Bot."""
    from datetime import datetime
    try:
        # Resolver estado_id
        from sqlalchemy import select, and_
        estado = db.execute(
            select(EstadoSistema).where(
                and_(EstadoSistema.entidad == "referencia", EstadoSistema.codigo == request.estado_codigo)
            )
        ).scalars().first()
        if not estado:
            raise HTTPException(status_code=400, detail=f"Estado {request.estado_codigo} no válido para referencias")

        ref = Referencia(
            grupo_id=request.grupo_id,
            solicitud_id=request.solicitud_id,
            consecutivo_grupo=request.consecutivo_grupo,
            referencia_portal=request.referencia_portal,
            importe=request.importe,
            fecha_generacion=datetime.strptime(request.fecha_generacion, "%Y-%m-%d"),
            fecha_vigencia=datetime.strptime(request.fecha_vigencia, "%Y-%m-%d").date() if request.fecha_vigencia else None,
            usuario_asignado=request.usuario_asignado,
            estado_id=estado.estado_id
        )
        db.add(ref)
        db.flush()
        return {"referencia_id": ref.referencia_id, "referencia_portal": ref.referencia_portal}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al registrar referencia: {str(e)}")

@router.post("/referencias/{referencia_id}/pdf")
def registrar_pdf_metadata(referencia_id: int, request: RegistrarPdfRequest, db: Session = Depends(get_db)):
    """Registra la ruta y metadatos del archivo PDF en la unidad compartida."""
    try:
        pdf_meta = ArchivoPDF(
            referencia_id=referencia_id,
            tipo_archivo=request.tipo_archivo,
            estado_archivo=request.estado_archivo,
            nombre_archivo=request.nombre_archivo,
            ruta_archivo=request.ruta_archivo,
            hash_sha256=request.hash_sha256,
            tamano_bytes=request.tamano_bytes
        )
        db.add(pdf_meta)
        db.flush()
        return {"archivo_id": pdf_meta.archivo_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al registrar metadatos PDF: {str(e)}")
