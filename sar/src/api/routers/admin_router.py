from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from sar.src.storage.db_connector import DatabaseConnector
from sar.src.storage.repositories import UsuarioRepository, CatalogoRepository, ConfigRepository
from sar.src.services.admin_service import AdminService
from sar.src.storage.models import (
    Usuario, Rol, Permiso, AppModulo, Modulo, Accion,
    Concepto, Municipio, Delegacion, Rfc, EstadoSistema, ParametroSistema, LocalizadorPortal,
    DesarrolloEmpresa, OrdenGeneracion
)

router = APIRouter(prefix="/api/admin", tags=["admin"])
db_connector = DatabaseConnector()

def get_db():
    with db_connector.get_session() as session:
        yield session

class AdminSaveRequest(BaseModel):
    usuario_id: int
    sesion_id: Optional[int] = None
    data: Dict[str, Any]

@router.get("/data/{entity}")
def get_admin_entity_data(entity: str, desarrollo_id: Optional[int] = None, limit: Optional[int] = None, db: Session = Depends(get_db)):
    try:
        user_repo = UsuarioRepository(db)
        cat_repo = CatalogoRepository(db)
        config_repo = ConfigRepository(db)
        
        if entity == "usuarios":
            users = user_repo.get_all_usuarios()
            return [
                {"usuario_id": u.usuario_id, "username": u.username, "nombre": u.nombre, "correo": u.correo, "activo": u.activo}
                for u in users
            ]
        elif entity == "roles":
            roles = user_repo.get_all_roles()
            return [
                {"rol_id": r.rol_id, "codigo": r.codigo, "nombre": r.nombre, "activo": r.activo}
                for r in roles
            ]
        elif entity == "permisos":
            stmt = select(Permiso)
            perms = db.execute(stmt).scalars().all()
            return [
                {"permiso_id": p.permiso_id, "modulo_id": p.modulo_id, "accion_id": p.accion_id, "activo": p.activo}
                for p in perms
            ]
        elif entity == "modulos":
            mods = user_repo.get_all_modulos()
            return [
                {
                    "modulo_id": m.modulo_id,
                    "id": m.modulo_id,
                    "codigo": m.codigo,
                    "nombre": m.nombre,
                    "orden": getattr(m, 'orden', 1.0),
                    "descripcion": m.descripcion,
                    "activo": m.activo,
                    "app_modulo_id": m.app_modulo_id
                }
                for m in mods
            ]
        elif entity == "acciones":
            accs = user_repo.get_all_acciones()
            return [{"id": a.accion_id, "codigo": a.codigo, "nombre": a.nombre, "descripcion": a.descripcion, "activo": a.activo} for a in accs]
        elif entity == "app_modulos":
            app_mods = user_repo.get_all_app_modulos()
            return [{"id": am.app_modulo_id, "codigo": am.codigo, "nombre": am.nombre, "activo": am.activo} for am in app_mods]
        elif entity == "conceptos":
            items = cat_repo.get_all_conceptos()
            return [
                {"concepto_id": c.concepto_id, "codigo_portal": c.codigo_portal, "nombre": c.nombre, "alias": c.alias, "activo": c.activo}
                for c in items
            ]
        elif entity == "notarias":
            items = cat_repo.get_all_notarias()
            return [
                {"notaria_id": n.notaria_id, "nombre": n.nombre, "alias": n.alias, "activo": n.activo}
                for n in items
            ]
        elif entity == "colaboradores":
            items = cat_repo.get_all_colaboradores()
            return [
                {"colaborador_id": c.colaborador_id, "nombre": c.nombre, "activo": c.activo}
                for c in items
            ]
        elif entity == "desarrollos":
            items = cat_repo.get_all_desarrollos()
            return [
                {"desarrollo_id": d.desarrollo_id, "nombre": d.nombre, "alias": d.alias, "activo": d.activo}
                for d in items
            ]
        elif entity == "desarrollo_empresas":
            if desarrollo_id:
                items = cat_repo.get_desarrollo_empresas(desarrollo_id)
            else:
                items = []
            return [
                {
                    "desarrollo_empresa_id": de.desarrollo_empresa_id,
                    "desarrollo_id": de.desarrollo_id,
                    "rfc_id": de.rfc_id,
                    "rfc_nombre": de.rfc.rfc if de.rfc else "",
                    "rfc_razon_social": de.rfc.razon_social if de.rfc else "",
                    "delegacion_id": de.delegacion_id,
                    "delegacion_nombre": de.delegacion.nombre if de.delegacion else "",
                    "es_default": de.es_default,
                    "activo": de.activo
                }
                for de in items
            ]
        elif entity == "municipios":
            items = cat_repo.get_all_municipios()
            return [
                {"municipio_id": m.municipio_id, "codigo_portal": m.codigo_portal, "nombre": m.nombre, "activo": m.activo}
                for m in items
            ]
        elif entity == "delegaciones":
            items = cat_repo.get_all_delegaciones_list()
            return [
                {"delegacion_id": d.delegacion_id, "codigo_portal": d.codigo_portal, "nombre": d.nombre, "alias": d.alias, "municipio_id": d.municipio_id, "activo": d.activo}
                for d in items
            ]
        elif entity == "rfcs":
            items = cat_repo.get_all_rfcs()
            return [
                {
                    "rfc_id": r.rfc_id, "rfc": r.rfc, "razon_social": r.razon_social,
                    "alias": r.alias,
                    "calle": r.calle, "no_exterior": r.no_exterior, "no_interior": r.no_interior,
                    "colonia": r.colonia, "codigo_postal": r.codigo_postal, "localidad": r.localidad,
                    "municipio": r.municipio, "estado": r.estado, "activo": r.activo
                }
                for r in items
            ]
        elif entity == "estados":
            items = cat_repo.get_all_estados_sistema()
            return [
                {"estado_id": e.estado_id, "entidad": e.entidad, "codigo": e.codigo, "descripcion": e.descripcion}
                for e in items
            ]
        elif entity == "parametros":
            items = config_repo.get_all_parametros()
            return [
                {"parametro_id": p.parametro_id, "codigo": p.codigo, "valor": p.valor, "activo": p.activo}
                for p in items
            ]
        elif entity == "localizadores":
            items = config_repo.get_all_localizadores_list()
            return [
                {
                    "localizador_id": l.localizador_id, "nombre_clave": l.nombre_clave,
                    "label_visible": l.label_visible, "estrategia_selector": l.estrategia_selector,
                    "valor_selector": l.valor_selector, "descripcion": l.descripcion, "activo": l.activo
                }
                for l in items
            ]
        elif entity == "ordenes":
            stmt = select(
                OrdenGeneracion.orden_id,
                OrdenGeneracion.folio,
                OrdenGeneracion.descripcion,
                OrdenGeneracion.tipo_orden,
                OrdenGeneracion.fecha_creacion
            ).order_by(OrdenGeneracion.orden_id.desc())
            if limit and limit > 0:
                stmt = stmt.limit(limit)
            res = db.execute(stmt).mappings().all()
            return [dict(r) for r in res]
        elif entity == "satc_tipos_tramite":
            from satc.src.services.housing_life_cycle_service import HousingLifeCycleService
            satc_svc = HousingLifeCycleService(db)
            items = satc_svc.get_all_tipos_tramite()
            return [
                {
                    "tipo_tramite_id": t.tipo_tramite_id,
                    "codigo": t.codigo,
                    "alias": t.alias,
                    "nombre": t.nombre,
                    "aplica_a": t.aplica_a,
                    "etapa_disparador": t.etapa_disparador,
                    "dias_vigencia": t.dias_vigencia,
                    "es_obligatorio": t.es_obligatorio,
                    "activo": t.activo
                }
                for t in items
            ]
        elif entity == "satc_estados_tramite":
            from satc.src.services.housing_life_cycle_service import HousingLifeCycleService
            satc_svc = HousingLifeCycleService(db)
            items = satc_svc.get_all_estados_tramite()
            return [
                {
                    "estado_tramite_id": e.estado_tramite_id,
                    "codigo": e.codigo,
                    "nombre": e.nombre,
                    "fase": e.fase,
                    "es_bloqueante": e.es_bloqueante,
                    "es_terminal": e.es_terminal,
                    "activo": e.activo
                }
                for e in items
            ]
        elif entity == "satc_estados_vivienda":
            from satc.src.services.housing_life_cycle_service import HousingLifeCycleService
            satc_svc = HousingLifeCycleService(db)
            items = satc_svc.get_all_estados_vivienda()
            return [
                {
                    "estado_vivienda_id": e.estado_vivienda_id,
                    "codigo": e.codigo,
                    "nombre": e.nombre,
                    "descripcion": e.descripcion,
                    "orden_flujo": e.orden_flujo,
                    "permite_venta": e.permite_venta,
                    "permite_escrituracion": e.permite_escrituracion,
                    "activo": e.activo
                }
                for e in items
            ]
        elif entity == "satc_regimenes":
            from satc.src.services.housing_life_cycle_service import HousingLifeCycleService
            satc_svc = HousingLifeCycleService(db)
            items = satc_svc.get_all_regimenes()
            return [
                {
                    "regimen_id": r.regimen_id,
                    "desarrollo_id": r.desarrollo_id,
                    "desarrollo_nombre": r.desarrollo.nombre if r.desarrollo else "N/A",
                    "nombre_regimen": r.nombre_regimen,
                    "sm": r.sm or "",
                    "mz": r.mz,
                    "lt": r.lt,
                    "total_upes": r.total_upes,
                    "upes_generadas": r.upes_generadas,
                    "licencia_construccion_matriz": r.licencia_construccion_matriz or "",
                    "clave_catastral_matriz": r.clave_catastral_matriz or "",
                    "activo": r.activo
                }
                for r in items
            ]
        elif entity == "satc_formatos_municipio":
            from satc.src.storage.satc_repos import MetadataRulesRepository
            repo = MetadataRulesRepository(db)
            items = repo.list_all_formatos(solo_activos=False)
            return [
                {
                    "formato_id": f.formato_id,
                    "campo_id": f.campo_id,
                    "campo_nombre": f.campo.nombre if f.campo else "N/A",
                    "campo_codigo": f.campo.codigo if f.campo else "",
                    "municipio_id": f.municipio_id,
                    "municipio_nombre": f.municipio.nombre if f.municipio else "N/A",
                    "nombre_variante": f.nombre_variante,
                    "prioridad": f.prioridad,
                    "regex_extraccion": f.regex_extraccion,
                    "regex_validacion": f.regex_validacion,
                    "longitud_min": f.longitud_min,
                    "longitud_max": f.longitud_max,
                    "remover_caracteres": f.remover_caracteres or "",
                    "permite_sliding_window": f.permite_sliding_window,
                    "descripcion_error": f.descripcion_error or "",
                    "activo": f.activo
                }
                for f in items
            ]
        elif entity == "satc_campos":
            from satc.src.storage.satc_repos import MetadataRulesRepository
            repo = MetadataRulesRepository(db)
            items = repo.list_campos(solo_activos=False)
            return [
                {
                    "campo_id": c.campo_id,
                    "codigo": c.codigo,
                    "nombre": c.nombre,
                    "descripcion": c.descripcion or "",
                    "activo": c.activo
                }
                for c in items
            ]
        else:
            raise HTTPException(status_code=400, detail=f"Entidad desconocida: {entity}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/roles-for-user/{user_id}")
def get_roles_for_user(user_id: int, db: Session = Depends(get_db)):
    try:
        repo = UsuarioRepository(db)
        return repo.get_roles_for_user(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/permisos-for-rol/{rol_id}")
def get_permisos_for_rol(rol_id: int, db: Session = Depends(get_db)):
    try:
        repo = UsuarioRepository(db)
        rows = repo.get_permisos_for_rol(rol_id)
        # Convert SQLAlchemy Row tuples to plain [modulo_id, accion_id] lists
        return [[r[0], r[1]] for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/app-modulos-for-rol/{rol_id}")
def get_app_modulos_for_rol(rol_id: int, db: Session = Depends(get_db)):
    try:
        repo = UsuarioRepository(db)
        return repo.get_app_modulos_for_rol(rol_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save/{entity}")
def save_admin_entity(entity: str, request: AdminSaveRequest, db: Session = Depends(get_db)):
    try:
        service = AdminService(db)
        
        # Enforce that session exists and is validated inside save methods
        if entity == "usuarios":
            res = service.save_usuario(request.usuario_id, request.sesion_id, request.data)
            db.commit()
            return {"detail": "Usuario guardado con éxito", "id": res.usuario_id}
        elif entity == "roles":
            res = service.save_rol(request.usuario_id, request.sesion_id, request.data)
            db.commit()
            return {"detail": "Rol guardado con éxito", "id": res.rol_id}
        elif entity == "conceptos":
            res = service.save_concepto(request.usuario_id, request.sesion_id, request.data)
            db.commit()
            return {"detail": "Concepto guardado con éxito", "id": res.concepto_id}
        elif entity == "notarias":
            res = service.save_notaria(request.usuario_id, request.sesion_id, request.data)
            db.commit()
            return {"detail": "Notaría guardada con éxito", "id": res.notaria_id}
        elif entity == "colaboradores":
            res = service.save_colaborador(request.usuario_id, request.sesion_id, request.data)
            db.commit()
            return {"detail": "Colaborador guardado con éxito", "id": res.colaborador_id}
        elif entity == "desarrollos":
            res = service.save_desarrollo(request.usuario_id, request.sesion_id, request.data)
            db.commit()
            return {"detail": "Desarrollo guardado con éxito", "id": res.desarrollo_id}
        elif entity == "desarrollo_empresas":
            res = service.save_desarrollo_empresa(request.usuario_id, request.sesion_id, request.data)
            db.commit()
            return {"detail": "Empresa asociada guardada con éxito", "id": res.desarrollo_empresa_id}
        elif entity == "municipios":
            res = service.save_municipio(request.usuario_id, request.sesion_id, request.data)
            db.commit()
            return {"detail": "Municipio guardado con éxito", "id": res.municipio_id}
        elif entity == "delegaciones":
            res = service.save_delegacion(request.usuario_id, request.sesion_id, request.data)
            db.commit()
            return {"detail": "Delegación guardada con éxito", "id": res.delegacion_id}
        elif entity == "rfcs":
            res = service.save_rfc(request.usuario_id, request.sesion_id, request.data)
            db.commit()
            return {"detail": "RFC guardado con éxito", "id": res.rfc_id}
        elif entity == "estados":
            res = service.save_estado_sistema(request.usuario_id, request.sesion_id, request.data)
            db.commit()
            return {"detail": "Estado de sistema guardado con éxito", "id": res.estado_id}
        elif entity == "parametros":
            res = service.save_parametro(request.usuario_id, request.sesion_id, request.data)
            db.commit()
            return {"detail": "Parámetro guardado con éxito", "id": res.parametro_id}
        elif entity == "localizadores":
            res = service.save_localizador(request.usuario_id, request.sesion_id, request.data)
            db.commit()
            return {"detail": "Localizador guardado con éxito", "id": res.localizador_id}
        elif entity == "app_modulos":
            res = service.save_app_modulo(request.usuario_id, request.sesion_id, request.data)
            db.commit()
            return {"detail": "Módulo de aplicación guardado con éxito", "id": res.app_modulo_id}
        elif entity == "modulos":
            res = service.save_modulo(request.usuario_id, request.sesion_id, request.data)
            db.commit()
            return {"detail": "Módulo guardado con éxito", "id": res.modulo_id}
        elif entity == "acciones":
            res = service.save_accion(request.usuario_id, request.sesion_id, request.data)
            db.commit()
            return {"detail": "Acción guardada con éxito", "id": res.accion_id}
        elif entity == "satc_tipos_tramite":
            from satc.src.services.housing_life_cycle_service import HousingLifeCycleService
            satc_svc = HousingLifeCycleService(db)
            res = satc_svc.save_tipo_tramite(request.data)
            db.commit()
            return {"detail": "Tipo de trámite guardado con éxito", "id": res.tipo_tramite_id}
        elif entity == "satc_estados_tramite":
            from satc.src.services.housing_life_cycle_service import HousingLifeCycleService
            satc_svc = HousingLifeCycleService(db)
            res = satc_svc.save_estado_tramite(request.data)
            db.commit()
            return {"detail": "Estado de trámite guardado con éxito", "id": res.estado_tramite_id}
        elif entity == "satc_estados_vivienda":
            from satc.src.services.housing_life_cycle_service import HousingLifeCycleService
            satc_svc = HousingLifeCycleService(db)
            res = satc_svc.save_estado_vivienda(request.data)
            db.commit()
            return {"detail": "Estado de vivienda guardado con éxito", "id": res.estado_vivienda_id}
        elif entity == "satc_regimenes":
            from satc.src.services.housing_life_cycle_service import HousingLifeCycleService
            satc_svc = HousingLifeCycleService(db)
            res = satc_svc.save_regimen_condominio(request.data)
            db.commit()
            return {"detail": "Régimen en condominio guardado con éxito", "id": res.regimen_id}
        elif entity == "satc_formatos_municipio":
            from satc.src.storage.satc_repos import MetadataRulesRepository
            from satc.src.services.metadata_extraction_service import MetadataExtractionService
            repo = MetadataRulesRepository(db)
            res = repo.save_formato(request.data)
            db.commit()
            MetadataExtractionService.clear_cache()
            return {"detail": "Regla de formato municipal guardada con éxito", "id": res.formato_id}
        else:
            raise HTTPException(status_code=400, detail=f"Entidad desconocida para guardar: {entity}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/permissions-for-user/{user_id}")
def get_user_permissions(user_id: int, db: Session = Depends(get_db)):
    try:
        repo = UsuarioRepository(db)
        perms = repo.get_user_permissions(user_id)
        return [[p[0], p[1]] for p in perms]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active-sessions")
def get_active_sessions(db: Session = Depends(get_db)):
    try:
        from sar.src.storage.models import Sesion, Usuario
        from sqlalchemy import text
        # Depurar sesiones huérfanas inactivas (más de 2 horas sin actividad/heartbeat)
        db.execute(text("""
            UPDATE sar_auditoria.auditoria_login al
            SET fecha_logout = NOW()
            FROM sar_seguridad.sesion s
            WHERE al.sesion_id = s.sesion_id
              AND s.estado = 'ACTIVA'
              AND al.fecha_logout IS NULL
              AND (
                (s.ultimo_heartbeat IS NOT NULL AND s.ultimo_heartbeat < (NOW() - INTERVAL '2 hours'))
                OR (s.ultimo_heartbeat IS NULL AND s.fecha_inicio < (NOW() - INTERVAL '2 hours'))
              );

            UPDATE sar_seguridad.sesion
            SET estado = 'FINALIZADA',
                ultimo_heartbeat = COALESCE(ultimo_heartbeat, NOW())
            WHERE estado = 'ACTIVA' 
              AND (
                (ultimo_heartbeat IS NOT NULL AND ultimo_heartbeat < (NOW() - INTERVAL '2 hours'))
                OR (ultimo_heartbeat IS NULL AND fecha_inicio < (NOW() - INTERVAL '2 hours'))
              );
        """))
        db.commit()

        stmt = (
            select(
                Sesion.sesion_id,
                Usuario.username,
                Sesion.equipo_nombre,
                Sesion.ip_equipo,
                Sesion.fecha_inicio,
                Sesion.ultimo_heartbeat,
                Sesion.estado
            )
            .join(Usuario, Sesion.usuario_id == Usuario.usuario_id)
            .where(Sesion.estado == "ACTIVA")
            .order_by(Sesion.fecha_inicio.desc())
        )
        results = db.execute(stmt).all()
        return [
            {
                "sesion_id": r.sesion_id,
                "username": r.username,
                "equipo_nombre": r.equipo_nombre,
                "ip_equipo": r.ip_equipo,
                "fecha_inicio": r.fecha_inicio.isoformat() if r.fecha_inicio else None,
                "ultimo_heartbeat": r.ultimo_heartbeat.isoformat() if r.ultimo_heartbeat else None,
                "estado": r.estado
            }
            for r in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/operations-log")
def get_operations_log(db: Session = Depends(get_db)):
    try:
        from sar.src.storage.models import AuditoriaEvento, Usuario
        stmt = (
            select(
                AuditoriaEvento.evento_auditoria_id,
                Usuario.username,
                AuditoriaEvento.fecha,
                AuditoriaEvento.modulo,
                AuditoriaEvento.detalle
            )
            .outerjoin(Usuario, AuditoriaEvento.usuario_id == Usuario.usuario_id)
            .order_by(AuditoriaEvento.fecha.desc())
            .limit(200)
        )
        results = db.execute(stmt).all()
        return [
            {
                "evento_auditoria_id": r.evento_auditoria_id,
                "username": r.username or "Sistema",
                "fecha": r.fecha.isoformat() if r.fecha else None,
                "modulo": r.modulo,
                "detalle": r.detalle
            }
            for r in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ValidarBatchRequest(BaseModel):
    referencias: List[str]

class ReservarLoteManualRequest(BaseModel):
    colaborador_id: int
    observaciones: Optional[str] = None
    usuario_id: int
    referencias_estados: List[Dict[str, str]]

@router.post("/referencias/validar-batch")
def validar_referencias_batch(payload: ValidarBatchRequest, db: Session = Depends(get_db)):
    """Valida en lote qué referencias existen en la base de datos (O(N) por chunks)."""
    try:
        from sar.src.storage.models import Referencia
        refs_set = set(payload.referencias)
        existing_refs = set()
        if refs_set:
            refs_list = list(refs_set)
            chunk_size = 500
            for i in range(0, len(refs_list), chunk_size):
                chunk = refs_list[i:i + chunk_size]
                stmt = select(Referencia.referencia_portal).where(Referencia.referencia_portal.in_(chunk))
                chunk_existing = db.execute(stmt).scalars().all()
                existing_refs.update(chunk_existing)
        return {"existentes": list(existing_refs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al validar lote de referencias: {str(e)}")

@router.post("/referencias/reservar-lote-manual")
def reservar_lote_manual(payload: ReservarLoteManualRequest, db: Session = Depends(get_db)):
    """Ejecuta la reserva manual de referencias con control transaccional estricto."""
    try:
        from sar.src.storage.repositories import InventarioRepository
        repo = InventarioRepository(db)
        result = repo.reservar_lote_manual_colaborador(
            colaborador_id=payload.colaborador_id,
            observaciones=payload.observaciones,
            usuario_id=payload.usuario_id,
            referencias_estados=payload.referencias_estados
        )
        db.commit()
        return result
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al procesar reserva de lote: {str(e)}")

class RegularizarColaboradorRequest(BaseModel):
    colaborador_id: int
    usuario_id: int
    sesion_id: Optional[int] = None
    observaciones: Optional[str] = None
    registros: List[Dict[str, Any]]

@router.post("/referencias/regularizar-colaborador")
def regularizar_referencias_colaborador(payload: RegularizarColaboradorRequest, db: Session = Depends(get_db)):
    """Regulariza y consolida referencias previamente apartadas a colaboradores con datos de expediente y ubicación."""
    try:
        from sar.src.storage.repositories import InventarioRepository
        repo = InventarioRepository(db)
        result = repo.regularizar_referencias_colaborador(
            colaborador_id=payload.colaborador_id,
            usuario_id=payload.usuario_id,
            registros=payload.registros,
            observaciones_lote=payload.observaciones,
            sesion_id=payload.sesion_id
        )
        db.commit()
        return result
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al regularizar asignaciones de colaborador: {str(e)}")

@router.post("/referencias/info-regularizacion-batch")
def info_regularizacion_batch(payload: ValidarBatchRequest, db: Session = Depends(get_db)):
    """Obtiene el estado y colaborador asignatario de un lote de referencias para validación de regularización."""
    try:
        from sar.src.storage.models import Referencia, AsignacionReferencia, LoteDetalle, LoteAsignacion, EstadoSistema
        refs_set = set(payload.referencias)
        db_ref_info = {}
        if refs_set:
            refs_list = list(refs_set)
            chunk_size = 500
            for i in range(0, len(refs_list), chunk_size):
                chunk = refs_list[i:i + chunk_size]
                stmt = (
                    select(
                        Referencia.referencia_portal,
                        EstadoSistema.codigo.label("estado_codigo"),
                        LoteAsignacion.colaborador_id
                    )
                    .join(EstadoSistema, Referencia.estado_id == EstadoSistema.estado_id)
                    .outerjoin(AsignacionReferencia, Referencia.referencia_id == AsignacionReferencia.referencia_id)
                    .outerjoin(LoteDetalle, AsignacionReferencia.lote_detalle_id == LoteDetalle.lote_detalle_id)
                    .outerjoin(LoteAsignacion, LoteDetalle.lote_asignacion_id == LoteAsignacion.lote_asignacion_id)
                    .where(Referencia.referencia_portal.in_(chunk))
                )
                for row_db in db.execute(stmt).all():
                    db_ref_info[row_db.referencia_portal] = {
                        "estado": row_db.estado_codigo,
                        "colaborador_id": row_db.colaborador_id
                    }
        return {"referencias": db_ref_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener info de regularización: {str(e)}")

# ===========================================================================
# ENDPOINTS: Catálogo de Ubicaciones (Procesos Especiales)
# ===========================================================================

class ImportarUbicacionesRequest(BaseModel):
    desarrollo_id: int
    usuario_id: int
    sesion_id: Optional[int] = None
    records: List[Dict[str, Any]]

@router.get("/ubicaciones/{desarrollo_id}")
def get_ubicaciones_by_desarrollo(desarrollo_id: int, db: Session = Depends(get_db)):
    """Retorna el listado de ubicaciones registradas para un desarrollo."""
    try:
        from sar.src.storage.repositories import CatalogoRepository
        repo = CatalogoRepository(db)
        return repo.get_ubicaciones_by_desarrollo(desarrollo_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar ubicaciones del desarrollo: {str(e)}")

@router.post("/ubicaciones/bulk-import")
def bulk_import_ubicaciones(payload: ImportarUbicacionesRequest, db: Session = Depends(get_db)):
    """Importa masivamente un lote de ubicaciones para un desarrollo con deduplicación y auditoría."""
    try:
        from sar.src.storage.repositories import CatalogoRepository
        repo = CatalogoRepository(db)
        res = repo.importar_catalogo_ubicaciones(
            desarrollo_id=payload.desarrollo_id,
            records=payload.records,
            usuario_id=payload.usuario_id,
            sesion_id=payload.sesion_id
        )
        db.commit()
        return res
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al importar catálogo de ubicaciones: {str(e)}")

# ===========================================================================
# ENDPOINTS: Importación y Consulta de Viviendas SATC (Ciclo de Vida)
# ===========================================================================

class ImportarViviendasSATCRequest(BaseModel):
    desarrollo_id: int
    regimen_id: Optional[int] = None
    usuario_id: int
    sesion_id: Optional[int] = None
    records: List[Dict[str, Any]]

@router.get("/satc/viviendas/{desarrollo_id}")
def get_satc_viviendas_by_desarrollo(desarrollo_id: int, regimen_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Retorna las viviendas registradas por desarrollo o por régimen."""
    try:
        from satc.src.services.housing_life_cycle_service import HousingLifeCycleService
        svc = HousingLifeCycleService(db)
        if regimen_id:
            return svc.get_viviendas_by_regimen(regimen_id)
        return svc.get_viviendas_by_desarrollo(desarrollo_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar viviendas SATC: {str(e)}")

@router.post("/satc/viviendas/bulk-import")
def bulk_import_satc_viviendas(payload: ImportarViviendasSATCRequest, db: Session = Depends(get_db)):
    """Ejecuta la importación masiva de viviendas con validación de UPEs autorizadas vs total en archivo."""
    try:
        from satc.src.services.housing_life_cycle_service import HousingLifeCycleService
        svc = HousingLifeCycleService(db)
        res = svc.importar_viviendas_excel(
            desarrollo_id=payload.desarrollo_id,
            records=payload.records,
            regimen_id=payload.regimen_id,
            usuario_id=payload.usuario_id,
            sesion_id=payload.sesion_id
        )
        return res
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al importar viviendas SATC: {str(e)}")

@router.post("/satc/viviendas/{regimen_id}/vincular-rpp")
def vincular_folios_rpp_satc(regimen_id: int, payload: ImportarViviendasSATCRequest, db: Session = Depends(get_db)):
    """Vincula los folios electrónicos del RPP para las viviendas de un régimen."""
    try:
        from satc.src.services.housing_life_cycle_service import HousingLifeCycleService
        svc = HousingLifeCycleService(db)
        res = svc.vincular_folios_rpp_excel(
            regimen_id=regimen_id,
            records=payload.records,
            usuario_id=payload.usuario_id,
            sesion_id=payload.sesion_id
        )
        return res
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al vincular folios RPP: {str(e)}")

@router.post("/satc/viviendas/{regimen_id}/vincular-catastro")
def vincular_catastro_satc(regimen_id: int, payload: ImportarViviendasSATCRequest, db: Session = Depends(get_db)):
    """Vincula claves catastrales y cuentas prediales para las viviendas de un régimen."""
    try:
        from satc.src.services.housing_life_cycle_service import HousingLifeCycleService
        svc = HousingLifeCycleService(db)
        res = svc.vincular_catastro_excel(
            regimen_id=regimen_id,
            records=payload.records,
            usuario_id=payload.usuario_id,
            sesion_id=payload.sesion_id
        )
        return res
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al vincular datos catastrales: {str(e)}")

# ===========================================================================
# ENDPOINTS: Resúmenes de Órdenes para Procesos Especiales
# ===========================================================================

@router.get("/ordenes/{orden_id}/resumen-carga")
def get_resumen_orden_carga(orden_id: int, db: Session = Depends(get_db)):
    """Retorna el resumen de grupos y cuotas para la carga masiva de una orden."""
    try:
        service = AdminService(db)
        return service.get_resumen_orden_carga_masiva(orden_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener resumen de carga para la orden {orden_id}: {str(e)}")

@router.get("/ordenes/{orden_id}/resumen-migracion")
def get_resumen_orden_migracion(orden_id: int, db: Session = Depends(get_db)):
    """Retorna el resumen de referencias por delegación para migración de una orden."""
    try:
        service = AdminService(db)
        return service.get_resumen_orden_migracion(orden_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener resumen de migración para la orden {orden_id}: {str(e)}")

@router.get("/ordenes/{orden_id}/solicitudes-carga")
def get_solicitudes_orden_carga(orden_id: int, db: Session = Depends(get_db)):
    """Retorna la lista de solicitudes de la orden para selección puntual de carga masiva."""
    try:
        service = AdminService(db)
        return service.get_solicitudes_orden_carga_masiva(orden_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener solicitudes de la orden {orden_id}: {str(e)}")

@router.post("/ordenes/{orden_id}/preview-carga")
def preview_carga_masiva(
    orden_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Valida los registros de carga masiva sin persistir."""
    try:
        service = AdminService(db)
        registros = payload.get("registros", [])
        solicitud_id = payload.get("solicitud_id")
        return service.preview_carga_masiva_referencias(orden_id, registros, solicitud_id=solicitud_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al validar carga masiva: {str(e)}")

@router.post("/ordenes/{orden_id}/ejecutar-carga")
def ejecutar_carga_masiva(
    orden_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Ejecuta la inserción transaccional de referencias masivas."""
    try:
        service = AdminService(db)
        registros = payload.get("registros", [])
        usuario_id = payload.get("usuario_id", 1)
        sesion_id = payload.get("sesion_id")
        solicitud_id = payload.get("solicitud_id")
        return service.ejecutar_carga_masiva_referencias(
            orden_id=orden_id,
            registros=registros,
            usuario_id=usuario_id,
            sesion_id=sesion_id,
            solicitud_id=solicitud_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al ejecutar carga masiva: {str(e)}")




