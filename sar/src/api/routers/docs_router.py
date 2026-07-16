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

@router.get("/solicitudes/references-metadata")
def get_references_metadata(solicitud_ids: str, db: Session = Depends(get_db)):
    """Retorna los metadatos de referencias para un grupo de solicitudes."""
    from sqlalchemy import text
    try:
        parsed_ids = [int(x) for x in solicitud_ids.split(",")] if solicitud_ids else []
        if not parsed_ids:
            return []
            
        query = text("""
            SELECT 
                r.consecutivo_grupo,
                r.referencia_portal,
                r.importe,
                r.cantidad,
                r.porcentaje,
                pdf.ruta_archivo,
                rfc.rfc,
                c.alias AS concepto_alias
            FROM sar_produccion.referencia r
            LEFT JOIN sar_archivo.archivo_pdf pdf ON r.referencia_id = pdf.referencia_id
            JOIN sar_produccion.grupo_referencia gr ON r.grupo_id = gr.grupo_id
            JOIN sar_catalogo.rfc rfc ON gr.rfc_id = rfc.rfc_id
            JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
            WHERE r.solicitud_id IN :sol_ids
            ORDER BY r.consecutivo_grupo ASC
        """)
        
        rows = db.execute(query, {"sol_ids": tuple(parsed_ids)}).all()
        return [
            {
                "consecutivo_grupo": r.consecutivo_grupo,
                "referencia_portal": r.referencia_portal,
                "importe": float(r.importe) if r.importe is not None else None,
                "cantidad": r.cantidad,
                "porcentaje": float(r.porcentaje) if r.porcentaje is not None else None,
                "ruta_archivo": r.ruta_archivo,
                "rfc": r.rfc,
                "concepto_alias": r.concepto_alias
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener metadatos de referencias: {str(e)}")

@router.get("/config/ruta-derechos")
def get_ruta_derechos(db: Session = Depends(get_db)):
    """Retorna el parámetro del sistema RUTA_DERECHOS."""
    from sar.src.storage.repositories import ConfigRepository
    try:
        repo = ConfigRepository(db)
        ruta = repo.get_parametro("RUTA_DERECHOS")
        return {"ruta_derechos": ruta}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener RUTA_DERECHOS: {str(e)}")

@router.get("/solicitudes/{solicitud_id}/orden-id")
def get_solicitud_orden_id(solicitud_id: int, db: Session = Depends(get_db)):
    """Retorna el orden_id asociado a una solicitud."""
    try:
        from sqlalchemy import select
        from sar.src.storage.models import Solicitud
        sol = db.get(Solicitud, solicitud_id)
        if not sol or not sol.grupo:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        return {"orden_id": sol.grupo.orden_id}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Bot-A endpoints

@router.get("/config/parametro/{nombre}")
def get_config_parametro(nombre: str, db: Session = Depends(get_db)):
    from sar.src.storage.repositories import ConfigRepository
    try:
        repo = ConfigRepository(db)
        val = repo.get_parametro(nombre)
        return {"nombre": nombre, "valor": val}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config/localizadores")
def get_config_localizadores(db: Session = Depends(get_db)):
    from sar.src.storage.repositories import ConfigRepository
    try:
        repo = ConfigRepository(db)
        locs = repo.get_localizadores()
        return {k: v.valor_selector for k, v in locs.items()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class EstadoSolicitudRequest(BaseModel):
    status_code: str

@router.post("/solicitudes/{solicitud_id}/estado")
def update_solicitud_estado(solicitud_id: int, request: EstadoSolicitudRequest, db: Session = Depends(get_db)):
    from sqlalchemy import text
    try:
        def get_or_create_status(session, entidad: str, codigo: str) -> int:
            stmt = text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad = :entidad AND codigo = :codigo LIMIT 1")
            eid = session.execute(stmt, {"entidad": entidad, "codigo": codigo}).scalar()
            if not eid:
                ins_stmt = text("""
                    INSERT INTO sar_catalogo.estado_sistema (entidad, codigo, descripcion)
                    VALUES (:entidad, :codigo, :desc)
                    RETURNING estado_id
                """)
                eid = session.execute(ins_stmt, {
                    "entidad": entidad,
                    "codigo": codigo,
                    "desc": f"Estado {codigo} de {entidad}"
                }).scalar()
                session.flush()
            return eid

        state_id = get_or_create_status(db, "solicitud", request.status_code)
        from sar.src.storage.models import Solicitud
        sol = db.get(Solicitud, solicitud_id)
        if sol:
            sol.estado_id = state_id
            db.commit()
            return {"detail": f"Solicitud {solicitud_id} actualizada a {request.status_code}"}
        else:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/solicitudes/{solicitud_id}/finalizar")
def finalize_solicitud(solicitud_id: int, request: EstadoSolicitudRequest, db: Session = Depends(get_db)):
    from sqlalchemy import text
    from sar.src.storage.models import Solicitud, GrupoReferencia, OrdenGeneracion
    import datetime
    try:
        def get_or_create_status(session, entidad: str, codigo: str) -> int:
            stmt = text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad = :entidad AND codigo = :codigo LIMIT 1")
            eid = session.execute(stmt, {"entidad": entidad, "codigo": codigo}).scalar()
            if not eid:
                ins_stmt = text("""
                    INSERT INTO sar_catalogo.estado_sistema (entidad, codigo, descripcion)
                    VALUES (:entidad, :codigo, :desc)
                    RETURNING estado_id
                """)
                eid = session.execute(ins_stmt, {
                    "entidad": entidad,
                    "codigo": codigo,
                    "desc": f"Estado {codigo} de {entidad}"
                }).scalar()
                session.flush()
            return eid

        sol_status_id = get_or_create_status(db, "solicitud", request.status_code)
        sol = db.get(Solicitud, solicitud_id)
        if not sol:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")

        sol.estado_id = sol_status_id
        sol.fecha_fin = datetime.datetime.now(datetime.timezone.utc)
        db.flush()
        
        if request.status_code == "COMPLETADA":
            pending_auth_status_id = get_or_create_status(db, "referencia", "PENDIENTE_AUTORIZACION")
            upd_ref_stmt = text("""
                UPDATE sar_produccion.referencia
                SET estado_id = :new_state
                WHERE solicitud_id = :sol_id
            """)
            db.execute(upd_ref_stmt, {"new_state": pending_auth_status_id, "sol_id": solicitud_id})
            db.flush()

        grupo = db.get(GrupoReferencia, sol.grupo_id)
        if grupo:
            all_sol_stm = text("""
                SELECT COUNT(*) FROM sar_produccion.solicitud s
                JOIN sar_catalogo.estado_sistema es ON s.estado_id = es.estado_id
                WHERE s.grupo_id = :grupo_id AND es.codigo != 'COMPLETADA'
            """)
            pending_sols = db.execute(all_sol_stm, {"grupo_id": grupo.grupo_id}).scalar()
            
            if pending_sols == 0 or (grupo.cantidad_generada or 0) >= grupo.cantidad_solicitada:
                grupo_status_id = get_or_create_status(db, "grupo_referencia", "COMPLETADO")
                grupo.estado_id = grupo_status_id
                db.flush()

            orden = db.get(OrdenGeneracion, grupo.orden_id)
            if orden:
                all_grupo_stm = text("""
                    SELECT COUNT(*) FROM sar_produccion.grupo_referencia gr
                    JOIN sar_catalogo.estado_sistema es ON gr.estado_id = es.estado_id
                    WHERE gr.orden_id = :orden_id AND es.codigo != 'COMPLETADO'
                """)
                pending_grupos = db.execute(all_grupo_stm, {"orden_id": orden.orden_id}).scalar()
                
                total_req_stm = text("SELECT SUM(cantidad_solicitada), SUM(cantidad_generada) FROM sar_produccion.grupo_referencia WHERE orden_id = :orden_id")
                tot_req, tot_gen = db.execute(total_req_stm, {"orden_id": orden.orden_id}).fetchone()
                
                if pending_grupos == 0 or (tot_gen and tot_req and tot_gen >= tot_req):
                    orden_status_id = get_or_create_status(db, "orden_generacion", "COMPLETADO")
                    orden.estado_id = orden_status_id
                    db.flush()
        
        db.commit()
        return {"detail": "Solicitud finalizada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AuditEventRequest(BaseModel):
    evento_codigo: str
    modulo: str
    usuario_id: int
    sesion_id: Optional[int] = None
    detalle: Optional[Dict[str, Any]] = None

@router.post("/audit/evento")
def log_audit_event(request: AuditEventRequest, db: Session = Depends(get_db)):
    from sar.src.storage.repositories import AuditRepository
    try:
        repo = AuditRepository(db)
        repo.log_evento(
            evento_codigo=request.evento_codigo,
            modulo=request.modulo,
            usuario_id=request.usuario_id,
            sesion_id=request.sesion_id,
            detalle=request.detalle
        )
        db.commit()
        return {"detail": "Evento registrado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AuditErrorRequest(BaseModel):
    usuario_id: int
    sesion_id: Optional[int] = None
    modulo: str
    mensaje: str
    stack_trace: str

@router.post("/audit/error")
def log_audit_error(request: AuditErrorRequest, db: Session = Depends(get_db)):
    from sar.src.storage.repositories import AuditRepository
    try:
        repo = AuditRepository(db)
        repo.log_error(
            usuario_id=request.usuario_id,
            sesion_id=request.sesion_id,
            modulo=request.modulo,
            mensaje=request.mensaje,
            stack_trace=request.stack_trace
        )
        db.commit()
        return {"detail": "Error registrado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SyncPathsRequest(BaseModel):
    filename: str
    new_path: str

@router.post("/contingency/sync-paths")
def sync_contingency_paths(request: SyncPathsRequest, db: Session = Depends(get_db)):
    from sqlalchemy import text
    try:
        upd_pdf = text("""
            UPDATE sar_archivo.archivo_pdf
            SET ruta_archivo = :new_path
            WHERE nombre_archivo = :filename
        """)
        db.execute(upd_pdf, {"new_path": request.new_path, "filename": request.filename})
        
        upd_fact = text("""
            UPDATE sar_archivo.factura
            SET pdf_path = :new_path
            WHERE pdf_path LIKE :pattern
        """)
        db.execute(upd_fact, {"new_path": request.new_path, "pattern": f"%{request.filename}"})
        db.commit()
        return {"detail": "Ruta actualizada en contingencia"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class RegistrarReferenciaBotRequest(BaseModel):
    solicitud_id: int
    grupo_id: int
    consecutivo: int
    referencia_portal: str
    importe: float
    fecha_vigencia: Optional[str] = None
    usuario_id: int
    pdf_filename: str
    pdf_path: str
    pdf_hash: str
    pdf_size: int

@router.post("/referencias/bot")
def registrar_referencia_bot(request: RegistrarReferenciaBotRequest, db: Session = Depends(get_db)):
    from sqlalchemy import text
    import datetime
    from sar.src.storage.models import Referencia, ArchivoPDF, Solicitud, GrupoReferencia
    try:
        state_stmt = text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad = 'referencia' AND codigo = 'GENERADA' LIMIT 1")
        state_id = db.execute(state_stmt).scalar() or 1
        
        fecha_vig = None
        if request.fecha_vigencia:
            fecha_vig = datetime.datetime.strptime(request.fecha_vigencia, "%Y-%m-%d").date()

        ref = Referencia(
            grupo_id=request.grupo_id,
            solicitud_id=request.solicitud_id,
            consecutivo_grupo=request.consecutivo,
            referencia_portal=request.referencia_portal,
            importe=request.importe,
            fecha_generacion=datetime.datetime.now(datetime.timezone.utc),
            fecha_vigencia=fecha_vig,
            estado_id=state_id,
            usuario_asignado=request.usuario_id
        )
        db.add(ref)
        db.flush()

        pdf = ArchivoPDF(
            referencia_id=ref.referencia_id,
            tipo_archivo="BOLETA_PAGO",
            estado_archivo="DESCARGADO",
            nombre_archivo=request.pdf_filename,
            ruta_archivo=request.pdf_path,
            hash_sha256=request.pdf_hash,
            tamano_bytes=request.pdf_size
        )
        db.add(pdf)

        sol = db.get(Solicitud, request.solicitud_id)
        if sol:
            sol.ultimo_consecutivo = request.consecutivo
            sol.cantidad_generada = (sol.cantidad_generada or 0) + 1
            if request.consecutivo >= sol.consecutivo_fin:
                sol.fecha_fin = datetime.datetime.now(datetime.timezone.utc)
            if not sol.fecha_inicio:
                sol.fecha_inicio = datetime.datetime.now(datetime.timezone.utc)

        grupo = db.get(GrupoReferencia, request.grupo_id)
        if grupo:
            if request.consecutivo > (grupo.ultimo_consecutivo or 0):
                grupo.ultimo_consecutivo = request.consecutivo
            grupo.cantidad_generada = (grupo.cantidad_generada or 0) + 1

        db.commit()
        return {"referencia_id": ref.referencia_id, "referencia_portal": ref.referencia_portal}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
