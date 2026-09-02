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
def get_admin_entity_data(entity: str, desarrollo_id: Optional[int] = None, db: Session = Depends(get_db)):
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
            return [{"id": m.modulo_id, "codigo": m.codigo, "nombre": m.nombre, "descripcion": m.descripcion, "activo": m.activo} for m in mods]
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
                {"desarrollo_id": d.desarrollo_id, "nombre": d.nombre, "activo": d.activo}
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
                {"delegacion_id": d.delegacion_id, "codigo_portal": d.codigo_portal, "nombre": d.nombre, "municipio_id": d.municipio_id, "activo": d.activo}
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
            res = db.execute(select(
                OrdenGeneracion.orden_id,
                OrdenGeneracion.folio,
                OrdenGeneracion.descripcion,
                OrdenGeneracion.fecha_creacion
            ).order_by(OrdenGeneracion.orden_id.desc())).mappings().all()
            return [dict(r) for r in res]
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

