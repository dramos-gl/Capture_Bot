"""Service layer for Administration operations (CRUD and Auditing)."""

import functools
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from argon2 import PasswordHasher
from sar.src.storage.repositories import (
    UsuarioRepository,
    CatalogoRepository,
    ConfigRepository,
    AuditRepository
)
from sar.src.storage.models import (
    Usuario, Rfc, Concepto, ParametroSistema, EventoSistema,
    Rol, LocalizadorPortal, Municipio, Delegacion,
    AppModulo, Modulo, EstadoSistema, Accion, Notaria, Colaborador, Desarrollo, DesarrolloEmpresa
)

def require_active_session(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        sesion_id = kwargs.get("sesion_id")
        if sesion_id is None and len(args) >= 2:
            sesion_id = args[1]
        
        self._validate_session(sesion_id)
        return func(self, *args, **kwargs)
    return wrapper

class AdminService:
    """Handles business logic for the System Administration Module."""

    def __init__(self, session: Session):
        self.session = session
        self.user_repo = UsuarioRepository(session)
        self.cat_repo = CatalogoRepository(session)
        self.config_repo = ConfigRepository(session)
        self.audit_repo = AuditRepository(session)
        self.ph = PasswordHasher()

    def _validate_session(self, sesion_id: Optional[int]) -> None:
        """Helper to strictly validate if the session exists and is active."""
        if not sesion_id:
            raise PermissionError("Acceso denegado: Sesión requerida.")
        from sar.src.services.security_service import SecurityService
        sec_service = SecurityService(self.session)
        if not sec_service.is_session_active(sesion_id):
            raise PermissionError("Acceso denegado: La sesión no está activa o ha expirado.")

    def _ensure_evento(self, codigo: str) -> None:
        """Ensures the event code exists in EventoSistema to prevent crash."""
        from sqlalchemy import select
        stmt = select(EventoSistema).where(EventoSistema.codigo == codigo)
        if not self.session.execute(stmt).scalar_one_or_none():
            ev = EventoSistema(codigo=codigo, descripcion=f"Auto-generated for {codigo}")
            self.session.add(ev)
            self.session.flush()

    def _log_audit(self, usuario_id: Optional[int], sesion_id: Optional[int], modulo: str, action: str, 
                   old_val: Optional[dict], new_val: Optional[dict], detalle: dict):
        """Logs the transactional change to the audit table."""
        self._ensure_evento(action)
        try:
            self.audit_repo.log_evento(
                evento_codigo=action,
                modulo=modulo,
                usuario_id=usuario_id,
                sesion_id=sesion_id,
                valor_anterior=old_val,
                valor_nuevo=new_val,
                detalle=detalle
            )
        except Exception as e:
            print(f"Failed to audit {action}: {e}")

    @require_active_session
    def save_usuario(self, usuario_id: Optional[int], sesion_id: Optional[int], data: Dict[str, Any]) -> Usuario:
        modulo = "ADMIN_USUARIOS"
        action = "CREAR_REGISTRO"
        old_val = None

        if data.get("usuario_id"):
            # Update existing
            user = self.user_repo.get_by_id(data["usuario_id"])
            if not user:
                raise ValueError("Usuario no encontrado.")
            action = "ACTUALIZAR_REGISTRO"
            old_val = {
                "username": user.username,
                "nombre": user.nombre,
                "correo": user.correo,
                "activo": user.activo
            }
            
            user.username = data.get("username", user.username)
            user.nombre = data.get("nombre", user.nombre)
            user.correo = data.get("correo", user.correo)
            if "activo" in data:
                user.activo = data["activo"]
            if data.get("password_raw"):
                user.password_hash = self.ph.hash(data["password_raw"])
        else:
            # Create new
            if not data.get("password_raw"):
                raise ValueError("La contraseña es obligatoria para un nuevo usuario.")
            user = Usuario(
                username=data["username"],
                nombre=data["nombre"],
                correo=data.get("correo"),
                password_hash=self.ph.hash(data["password_raw"]),
                activo=data.get("activo", True)
            )

        if "rol_ids" in data:
            roles = []
            if data["rol_ids"]:
                roles = self.session.query(Rol).filter(Rol.rol_id.in_(data["rol_ids"])).all()
            user.roles = roles

        self.user_repo.save(user)
        
        new_val = {
            "usuario_id": user.usuario_id,
            "username": user.username,
            "nombre": user.nombre,
            "correo": user.correo,
            "activo": user.activo
        }
        
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"username": user.username})
        return user

    @require_active_session
    def save_rfc(self, usuario_id: Optional[int], sesion_id: Optional[int], data: Dict[str, Any]) -> Rfc:
        modulo = "ADMIN_CATALOGOS"
        action = "CREAR_REGISTRO"
        old_val = None

        if data.get("rfc_id"):
            rfc = self.session.get(Rfc, data["rfc_id"])
            action = "ACTUALIZAR_REGISTRO"
            old_val = {"rfc": rfc.rfc, "razon_social": rfc.razon_social, "alias": rfc.alias, "activo": rfc.activo}
            
            rfc.rfc = data.get("rfc", rfc.rfc)
            rfc.razon_social = data.get("razon_social", rfc.razon_social)
            rfc.alias = data.get("alias", rfc.alias)
            rfc.calle = data.get("calle", rfc.calle)
            rfc.no_exterior = data.get("no_exterior", rfc.no_exterior)
            rfc.no_interior = data.get("no_interior", rfc.no_interior)
            rfc.colonia = data.get("colonia", rfc.colonia)
            rfc.codigo_postal = data.get("codigo_postal", rfc.codigo_postal)
            rfc.localidad = data.get("localidad", rfc.localidad)
            rfc.municipio = data.get("municipio", rfc.municipio)
            rfc.estado = data.get("estado", rfc.estado)
            if "activo" in data:
                rfc.activo = data["activo"]
        else:
            rfc = Rfc(
                rfc=data["rfc"],
                razon_social=data["razon_social"],
                alias=data.get("alias"),
                calle=data.get("calle"),
                no_exterior=data.get("no_exterior"),
                no_interior=data.get("no_interior"),
                colonia=data.get("colonia"),
                codigo_postal=data.get("codigo_postal"),
                localidad=data.get("localidad"),
                municipio=data.get("municipio"),
                estado=data.get("estado"),
                activo=data.get("activo", True)
            )

        self.cat_repo.save_rfc(rfc)
        new_val = {"rfc_id": rfc.rfc_id, "rfc": rfc.rfc, "razon_social": rfc.razon_social, "alias": rfc.alias, "activo": rfc.activo}
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"rfc": rfc.rfc})
        return rfc

    @require_active_session
    def save_concepto(self, usuario_id: Optional[int], sesion_id: Optional[int], data: Dict[str, Any]) -> Concepto:
        modulo = "ADMIN_CATALOGOS"
        action = "CREAR_REGISTRO"
        old_val = None

        if data.get("concepto_id"):
            concepto = self.session.get(Concepto, data["concepto_id"])
            action = "ACTUALIZAR_REGISTRO"
            old_val = {"codigo_portal": concepto.codigo_portal, "nombre": concepto.nombre, "alias": concepto.alias, "activo": concepto.activo}
            
            concepto.codigo_portal = data.get("codigo_portal", concepto.codigo_portal)
            concepto.nombre = data.get("nombre", concepto.nombre)
            concepto.alias = data.get("alias", concepto.alias)
            if "activo" in data:
                concepto.activo = data["activo"]
        else:
            concepto = Concepto(
                codigo_portal=data.get("codigo_portal"),
                nombre=data["nombre"],
                alias=data.get("alias"),
                activo=data.get("activo", True)
            )

        self.cat_repo.save_concepto(concepto)
        new_val = {"concepto_id": concepto.concepto_id, "nombre": concepto.nombre, "alias": concepto.alias, "activo": concepto.activo}
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"nombre": concepto.nombre})
        return concepto

    @require_active_session
    def save_notaria(self, usuario_id: Optional[int], sesion_id: Optional[int], data: Dict[str, Any]) -> Notaria:
        modulo = "ADMIN_CATALOGOS"
        action = "CREAR_REGISTRO"
        old_val = None

        if data.get("notaria_id"):
            notaria = self.session.get(Notaria, data["notaria_id"])
            action = "ACTUALIZAR_REGISTRO"
            old_val = {"nombre": notaria.nombre, "alias": notaria.alias, "activo": notaria.activo}
            notaria.nombre = data.get("nombre", notaria.nombre).strip().upper()
            notaria.alias = data.get("alias", notaria.alias).strip() if data.get("alias") else None
            if "activo" in data:
                notaria.activo = data["activo"]
        else:
            notaria = Notaria(
                nombre=data["nombre"].strip().upper(),
                alias=data.get("alias").strip() if data.get("alias") else None,
                activo=data.get("activo", True)
            )

        self.cat_repo.save_notaria(notaria)
        new_val = {"notaria_id": notaria.notaria_id, "nombre": notaria.nombre, "alias": notaria.alias, "activo": notaria.activo}
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"nombre": notaria.nombre})
        return notaria

    @require_active_session
    def save_colaborador(self, usuario_id: Optional[int], sesion_id: Optional[int], data: Dict[str, Any]) -> Colaborador:
        modulo = "ADMIN_CATALOGOS"
        action = "CREAR_REGISTRO"
        old_val = None

        if data.get("colaborador_id"):
            colaborador = self.session.get(Colaborador, data["colaborador_id"])
            action = "ACTUALIZAR_REGISTRO"
            old_val = {"nombre": colaborador.nombre, "activo": colaborador.activo}
            colaborador.nombre = data.get("nombre", colaborador.nombre).strip().upper()
            if "activo" in data:
                colaborador.activo = data["activo"]
        else:
            colaborador = Colaborador(
                nombre=data["nombre"].strip().upper(),
                activo=data.get("activo", True)
            )

        self.cat_repo.save_colaborador(colaborador)
        new_val = {"colaborador_id": colaborador.colaborador_id, "nombre": colaborador.nombre, "activo": colaborador.activo}
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"nombre": colaborador.nombre})
        return colaborador

    @require_active_session
    def save_desarrollo(self, usuario_id: Optional[int], sesion_id: Optional[int], data: Dict[str, Any]) -> Desarrollo:
        modulo = "ADMIN_CATALOGOS"
        action = "CREAR_REGISTRO"
        old_val = None

        if data.get("desarrollo_id"):
            desarrollo = self.session.get(Desarrollo, data["desarrollo_id"])
            action = "ACTUALIZAR_REGISTRO"
            old_val = {"nombre": desarrollo.nombre, "alias": desarrollo.alias, "activo": desarrollo.activo}
            desarrollo.nombre = data.get("nombre", desarrollo.nombre).strip().upper()
            if "alias" in data:
                raw_alias = data["alias"]
                desarrollo.alias = raw_alias.strip().upper() if raw_alias and raw_alias.strip() else None
            if "activo" in data:
                desarrollo.activo = data["activo"]
        else:
            raw_alias = data.get("alias")
            desarrollo = Desarrollo(
                nombre=data["nombre"].strip().upper(),
                alias=raw_alias.strip().upper() if raw_alias and raw_alias.strip() else None,
                activo=data.get("activo", True)
            )

        self.cat_repo.save_desarrollo(desarrollo)
        new_val = {"desarrollo_id": desarrollo.desarrollo_id, "nombre": desarrollo.nombre, "alias": desarrollo.alias, "activo": desarrollo.activo}
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"nombre": desarrollo.nombre})
        return desarrollo

    @require_active_session
    def save_desarrollo_empresa(self, usuario_id: Optional[int], sesion_id: Optional[int], data: Dict[str, Any]) -> DesarrolloEmpresa:
        modulo = "ADMIN_CATALOGOS"
        action = "CREAR_REGISTRO"
        old_val = None

        if data.get("desarrollo_empresa_id"):
            de = self.session.get(DesarrolloEmpresa, data["desarrollo_empresa_id"])
            action = "ACTUALIZAR_REGISTRO"
            old_val = {
                "desarrollo_id": de.desarrollo_id,
                "rfc_id": de.rfc_id,
                "delegacion_id": de.delegacion_id,
                "es_default": de.es_default,
                "activo": de.activo
            }
            de.desarrollo_id = data.get("desarrollo_id", de.desarrollo_id)
            de.rfc_id = data.get("rfc_id", de.rfc_id)
            de.delegacion_id = data.get("delegacion_id", de.delegacion_id)
            if "es_default" in data:
                de.es_default = data["es_default"]
            if "activo" in data:
                de.activo = data["activo"]
        else:
            de = DesarrolloEmpresa(
                desarrollo_id=data["desarrollo_id"],
                rfc_id=data["rfc_id"],
                delegacion_id=data["delegacion_id"],
                es_default=data.get("es_default", False),
                activo=data.get("activo", True)
            )

        # Business rule: if es_default is True, make sure other records for the same desarrollo_id are NOT default
        if de.es_default:
            from sqlalchemy import update
            self.session.execute(
                update(DesarrolloEmpresa)
                .where(DesarrolloEmpresa.desarrollo_id == de.desarrollo_id)
                .where(DesarrolloEmpresa.desarrollo_empresa_id != (de.desarrollo_empresa_id or 0))
                .values(es_default=False)
            )

        self.cat_repo.save_desarrollo_empresa(de)
        new_val = {
            "desarrollo_empresa_id": de.desarrollo_empresa_id,
            "desarrollo_id": de.desarrollo_id,
            "rfc_id": de.rfc_id,
            "delegacion_id": de.delegacion_id,
            "es_default": de.es_default,
            "activo": de.activo
        }
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"desarrollo_id": de.desarrollo_id, "rfc_id": de.rfc_id})
        return de



    @require_active_session
    def save_estado_sistema(self, usuario_id: Optional[int], sesion_id: Optional[int], data: Dict[str, Any]) -> EstadoSistema:
        modulo = "ADMIN_CATALOGOS"
        action = "CREAR_REGISTRO"
        old_val = None

        if data.get("estado_id"):
            est = self.session.get(EstadoSistema, data["estado_id"])
            action = "ACTUALIZAR_REGISTRO"
            old_val = {"entidad": est.entidad, "codigo": est.codigo, "descripcion": est.descripcion}
            
            est.entidad = data.get("entidad", est.entidad)
            est.codigo = data.get("codigo", est.codigo)
            est.descripcion = data.get("descripcion", est.descripcion)
        else:
            est = EstadoSistema(
                entidad=data["entidad"],
                codigo=data["codigo"],
                descripcion=data.get("descripcion", "")
            )

        self.cat_repo.save_estado_sistema(est)
        new_val = {"estado_id": est.estado_id, "entidad": est.entidad, "codigo": est.codigo, "descripcion": est.descripcion}
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"codigo": est.codigo})
        return est

    @require_active_session
    def save_parametro(self, usuario_id: Optional[int], sesion_id: Optional[int], data: Dict[str, Any]) -> ParametroSistema:
        modulo = "ADMIN_CONFIG"
        action = "CREAR_REGISTRO"
        old_val = None

        if data.get("parametro_id"):
            param = self.session.get(ParametroSistema, data["parametro_id"])
            action = "ACTUALIZAR_REGISTRO"
            old_val = {"codigo": param.codigo, "valor": param.valor, "activo": param.activo}
            
            param.codigo = data.get("codigo", param.codigo)
            param.valor = data.get("valor", param.valor)
            if "activo" in data:
                param.activo = data["activo"]
        else:
            param = ParametroSistema(
                codigo=data["codigo"],
                valor=data["valor"],
                activo=data.get("activo", True)
            )

        self.config_repo.save_parametro(param)
        new_val = {"parametro_id": param.parametro_id, "codigo": param.codigo, "valor": param.valor, "activo": param.activo}
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"codigo": param.codigo})
        return param

    @require_active_session
    def save_rol(self, usuario_id: Optional[int], sesion_id: Optional[int], data: Dict[str, Any]) -> Rol:
        modulo = "ADMIN_SEGURIDAD"
        action = "CREAR_REGISTRO"
        old_val = None

        if data.get("rol_id"):
            rol = self.session.get(Rol, data["rol_id"])
            action = "ACTUALIZAR_REGISTRO"
            old_val = {"codigo": rol.codigo, "nombre": rol.nombre, "activo": rol.activo}
            
            rol.codigo = data.get("codigo", rol.codigo)
            rol.nombre = data.get("nombre", rol.nombre)
            if "activo" in data:
                rol.activo = data["activo"]
        else:
            rol = Rol(
                codigo=data["codigo"],
                nombre=data.get("nombre", ""),
                activo=data.get("activo", True)
            )

        if "permisos_matrix" in data:
            from sar.src.storage.models import Permiso
            from sqlalchemy import select, and_
            
            new_permisos = []
            for mod_id, acc_id in data["permisos_matrix"]:
                stmt = select(Permiso).where(and_(Permiso.modulo_id == mod_id, Permiso.accion_id == acc_id))
                permiso = self.session.execute(stmt).scalar_one_or_none()
                if not permiso:
                    permiso = Permiso(modulo_id=mod_id, accion_id=acc_id, activo=True)
                    self.session.add(permiso)
                    self.session.flush()
                new_permisos.append(permiso)
            rol.permisos = new_permisos

        if "app_modulo_ids" in data:
            new_app_mods = []
            if data["app_modulo_ids"]:
                new_app_mods = self.session.query(AppModulo).filter(AppModulo.app_modulo_id.in_(data["app_modulo_ids"])).all()
            rol.app_modulos = new_app_mods

        self.user_repo.save_rol(rol)
        new_val = {"rol_id": rol.rol_id, "codigo": rol.codigo, "nombre": rol.nombre, "activo": rol.activo}
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"nombre": rol.nombre})
        return rol

    @require_active_session
    def save_app_modulo(self, usuario_id: Optional[int], sesion_id: Optional[int], data: Dict[str, Any]) -> AppModulo:
        modulo = "ADMIN_SEGURIDAD"
        action = "CREAR_REGISTRO"
        old_val = None

        if data.get("app_modulo_id"):
            am = self.session.get(AppModulo, data["app_modulo_id"])
            action = "ACTUALIZAR_REGISTRO"
            old_val = {"codigo": am.codigo, "nombre": am.nombre, "activo": am.activo}
            
            am.codigo = data.get("codigo", am.codigo)
            am.nombre = data.get("nombre", am.nombre)
            if "activo" in data:
                am.activo = data["activo"]
        else:
            am = AppModulo(
                codigo=data["codigo"],
                nombre=data["nombre"],
                activo=data.get("activo", True)
            )

        self.session.add(am)
        self.session.flush()
        new_val = {"app_modulo_id": am.app_modulo_id, "codigo": am.codigo, "nombre": am.nombre, "activo": am.activo}
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"nombre": am.nombre})
        return am

    @require_active_session
    def save_modulo(self, usuario_id: Optional[int], sesion_id: Optional[int], data: Dict[str, Any]) -> Modulo:
        modulo = "ADMIN_SEGURIDAD"
        action = "CREAR_REGISTRO"
        old_val = None

        if data.get("modulo_id"):
            m = self.session.get(Modulo, data["modulo_id"])
            action = "ACTUALIZAR_REGISTRO"
            old_val = {
                "codigo": m.codigo,
                "nombre": m.nombre,
                "descripcion": m.descripcion,
                "activo": m.activo,
                "orden": m.orden,
                "app_modulo_id": m.app_modulo_id
            }
            
            m.codigo = data.get("codigo", m.codigo)
            m.nombre = data.get("nombre", m.nombre)
            m.descripcion = data.get("descripcion", m.descripcion)
            if "activo" in data:
                m.activo = data["activo"]
            if "orden" in data and data["orden"] is not None:
                m.orden = float(data["orden"])
            if "app_modulo_id" in data:
                m.app_modulo_id = data["app_modulo_id"]
        else:
            m = Modulo(
                codigo=data["codigo"],
                nombre=data["nombre"],
                descripcion=data.get("descripcion", ""),
                activo=data.get("activo", True),
                orden=float(data.get("orden", 1.0)),
                app_modulo_id=data.get("app_modulo_id")
            )

        self.session.add(m)
        self.session.flush()
        new_val = {
            "modulo_id": m.modulo_id,
            "codigo": m.codigo,
            "nombre": m.nombre,
            "descripcion": m.descripcion,
            "activo": m.activo,
            "orden": m.orden,
            "app_modulo_id": m.app_modulo_id
        }
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"nombre": m.nombre})
        return m

    @require_active_session
    def save_accion(self, usuario_id: Optional[int], sesion_id: Optional[int], data: Dict[str, Any]):
        modulo = "ADMIN_SEGURIDAD"
        action = "CREAR_REGISTRO"
        old_val = None

        if data.get("accion_id"):
            a = self.session.get(Accion, data["accion_id"])
            action = "ACTUALIZAR_REGISTRO"
            old_val = {"codigo": a.codigo, "nombre": a.nombre, "descripcion": a.descripcion, "activo": a.activo}
            
            a.codigo = data.get("codigo", a.codigo)
            a.nombre = data.get("nombre", a.nombre)
            a.descripcion = data.get("descripcion", a.descripcion)
            if "activo" in data:
                a.activo = data["activo"]
        else:
            a = Accion(
                codigo=data["codigo"],
                nombre=data["nombre"],
                descripcion=data.get("descripcion", ""),
                activo=data.get("activo", True)
            )

        self.session.add(a)
        self.session.flush()
        new_val = {"accion_id": a.accion_id, "codigo": a.codigo, "nombre": a.nombre, "descripcion": a.descripcion, "activo": a.activo}
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"nombre": a.nombre})
        return a

    @require_active_session
    def save_localizador(self, usuario_id: Optional[int], sesion_id: Optional[int], data: Dict[str, Any]) -> LocalizadorPortal:
        modulo = "ADMIN_CONFIG"
        action = "CREAR_REGISTRO"
        old_val = None

        if data.get("localizador_id"):
            loc = self.session.get(LocalizadorPortal, data["localizador_id"])
            action = "ACTUALIZAR_REGISTRO"
            old_val = {
                "nombre_clave": loc.nombre_clave,
                "label_visible": loc.label_visible,
                "estrategia_selector": loc.estrategia_selector,
                "valor_selector": loc.valor_selector,
                "descripcion": loc.descripcion,
                "activo": loc.activo
            }
            
            loc.nombre_clave = data.get("nombre_clave", loc.nombre_clave)
            loc.label_visible = data.get("label_visible", loc.label_visible)
            loc.estrategia_selector = data.get("estrategia_selector", loc.estrategia_selector)
            loc.valor_selector = data.get("valor_selector", loc.valor_selector)
            loc.descripcion = data.get("descripcion", loc.descripcion)
            if "activo" in data:
                loc.activo = data["activo"]
        else:
            loc = LocalizadorPortal(
                nombre_clave=data["nombre_clave"],
                label_visible=data.get("label_visible", ""),
                estrategia_selector=data.get("estrategia_selector", "css"),
                valor_selector=data["valor_selector"],
                descripcion=data.get("descripcion", ""),
                activo=data.get("activo", True)
            )

        self.config_repo.save_localizador(loc)
        new_val = {
            "localizador_id": loc.localizador_id,
            "nombre_clave": loc.nombre_clave,
            "label_visible": loc.label_visible,
            "estrategia_selector": loc.estrategia_selector,
            "valor_selector": loc.valor_selector,
            "descripcion": loc.descripcion,
            "activo": loc.activo
        }
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"nombre_clave": loc.nombre_clave})
        return loc

    @require_active_session
    def save_municipio(self, usuario_id: Optional[int], sesion_id: Optional[int], data: Dict[str, Any]) -> Municipio:
        modulo = "ADMIN_CATALOGOS"
        action = "CREAR_REGISTRO"
        old_val = None

        if data.get("municipio_id"):
            mun = self.session.get(Municipio, data["municipio_id"])
            action = "ACTUALIZAR_REGISTRO"
            old_val = {"codigo_portal": mun.codigo_portal, "nombre": mun.nombre, "activo": mun.activo}
            
            mun.codigo_portal = data.get("codigo_portal", mun.codigo_portal)
            mun.nombre = data.get("nombre", mun.nombre)
            if "activo" in data:
                mun.activo = data["activo"]
        else:
            mun = Municipio(
                codigo_portal=data.get("codigo_portal"),
                nombre=data["nombre"],
                activo=data.get("activo", True)
            )

        self.cat_repo.save_municipio(mun)
        new_val = {"municipio_id": mun.municipio_id, "nombre": mun.nombre, "activo": mun.activo}
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"nombre": mun.nombre})
        return mun

    @require_active_session
    def save_delegacion(self, usuario_id: Optional[int], sesion_id: Optional[int], data: Dict[str, Any]) -> Delegacion:
        modulo = "ADMIN_CATALOGOS"
        action = "CREAR_REGISTRO"
        old_val = None

        if data.get("delegacion_id"):
            d = self.session.get(Delegacion, data["delegacion_id"])
            action = "ACTUALIZAR_REGISTRO"
            old_val = {"codigo_portal": d.codigo_portal, "nombre": d.nombre, "alias": d.alias, "municipio_id": d.municipio_id, "activo": d.activo}
            
            d.codigo_portal = data.get("codigo_portal", d.codigo_portal)
            d.nombre = data.get("nombre", d.nombre)
            if "alias" in data:
                raw_alias = data["alias"]
                d.alias = raw_alias.strip().upper() if raw_alias and raw_alias.strip() else None
            d.municipio_id = data.get("municipio_id", d.municipio_id)
            if "activo" in data:
                d.activo = data["activo"]
        else:
            raw_alias = data.get("alias")
            d = Delegacion(
                codigo_portal=data.get("codigo_portal"),
                nombre=data["nombre"],
                alias=raw_alias.strip().upper() if raw_alias and raw_alias.strip() else None,
                municipio_id=data["municipio_id"],
                activo=data.get("activo", True)
            )

        self.cat_repo.save_delegacion(d)
        new_val = {"delegacion_id": d.delegacion_id, "nombre": d.nombre, "alias": d.alias, "municipio_id": d.municipio_id, "activo": d.activo}
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"nombre": d.nombre})
        return d

    def get_ubicaciones_by_desarrollo(self, desarrollo_id: int) -> List[Dict[str, Any]]:
        return self.cat_repo.get_ubicaciones_by_desarrollo(desarrollo_id)

    @require_active_session
    def importar_catalogo_ubicaciones(
        self, usuario_id: Optional[int], sesion_id: Optional[int], desarrollo_id: int, records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        return self.cat_repo.importar_catalogo_ubicaciones(
            desarrollo_id=desarrollo_id,
            records=records,
            usuario_id=usuario_id or 1,
            sesion_id=sesion_id
        )

    def get_resumen_orden_carga_masiva(self, orden_id: int) -> List[Dict[str, Any]]:
        """Obtiene el resumen de grupos, solicitados y generados para una orden dada."""
        from sqlalchemy import text
        resumen = self.session.execute(text("""
            SELECT gr.grupo_id, r.rfc, c.alias AS concepto_alias,
                   gr.cantidad_solicitada, gr.cantidad_generada, gr.cantidad_autorizada
            FROM sar_produccion.grupo_referencia gr
            JOIN sar_catalogo.rfc r ON gr.rfc_id = r.rfc_id
            JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
            WHERE gr.orden_id = :oid
            ORDER BY gr.grupo_id
        """), {"oid": orden_id}).mappings().all()
        return [dict(r) for r in resumen]

    def get_solicitudes_orden_carga_masiva(self, orden_id: int) -> List[Dict[str, Any]]:
        """Obtiene la lista de solicitudes de la orden indicando RFC, concepto, delegación y avance."""
        from sqlalchemy import text
        sols = self.session.execute(text("""
            SELECT s.solicitud_id, s.grupo_id, s.delegacion_id, d.nombre AS delegacion_nombre,
                   r.rfc, c.alias AS concepto_alias, c.nombre AS concepto_nombre,
                   s.cantidad_solicitada, s.cantidad_generada, s.consecutivo_inicio, s.consecutivo_fin,
                   (s.cantidad_solicitada - s.cantidad_generada) AS referencias_pendientes
            FROM sar_produccion.solicitud s
            JOIN sar_produccion.grupo_referencia gr ON s.grupo_id = gr.grupo_id
            JOIN sar_catalogo.rfc r ON gr.rfc_id = r.rfc_id
            JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
            JOIN sar_catalogo.delegacion d ON s.delegacion_id = d.delegacion_id
            WHERE gr.orden_id = :oid
            ORDER BY s.solicitud_id ASC
        """), {"oid": orden_id}).mappings().all()
        return [dict(s) for s in sols]

    def get_resumen_orden_migracion(self, orden_id: int) -> List[Dict[str, Any]]:
        """Obtiene el resumen de referencias por delegación y grupo para migración de una orden."""
        from sqlalchemy import text
        resumen = self.session.execute(text("""
            SELECT gr.grupo_id, r.rfc, c.alias AS concepto_alias,
                   d.nombre AS delegacion_actual, d.delegacion_id,
                   COUNT(ref.referencia_id) AS total_refs
            FROM sar_produccion.grupo_referencia gr
            JOIN sar_catalogo.rfc r ON gr.rfc_id = r.rfc_id
            JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
            JOIN sar_produccion.solicitud sol ON sol.grupo_id = gr.grupo_id
            JOIN sar_catalogo.delegacion d ON sol.delegacion_id = d.delegacion_id
            JOIN sar_produccion.referencia ref ON ref.grupo_id = gr.grupo_id
            WHERE gr.orden_id = :oid
            GROUP BY gr.grupo_id, r.rfc, c.alias, d.nombre, d.delegacion_id
            ORDER BY gr.grupo_id, d.delegacion_id
        """), {"oid": orden_id}).mappings().all()
        return [dict(r) for r in resumen]

    def preview_carga_masiva_referencias(self, orden_id: int, registros: List[Dict[str, Any]], solicitud_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Valida sintáctica y referencialmente un conjunto de registros para carga masiva sin persistir.
        Verifica RFC, concepto, delegación, y busca duplicados en base de datos.
        Si se especifica solicitud_id, valida que los registros pertenezcan exactamente a esa solicitud.
        Calcula si se crearán nuevas solicitudes o se integrarán a existentes.
        """
        from sqlalchemy import text
        from datetime import datetime

        # 1. Obtener orden
        orden = self.session.execute(
            text("SELECT orden_id, folio, descripcion, tipo_orden FROM sar_produccion.orden_generacion WHERE orden_id = :oid"),
            {"oid": orden_id}
        ).mappings().first()
        if not orden:
            raise ValueError(f"La orden con ID {orden_id} no existe.")

        tipo_orden = orden["tipo_orden"] or "ESTANDAR"

        # 1.1 Si se especificó una solicitud puntual, obtener su metadata
        solicitud_especifica = None
        if solicitud_id:
            sol_row = self.session.execute(text("""
                SELECT s.solicitud_id, s.grupo_id, s.delegacion_id, d.nombre AS delegacion_nombre,
                       r.rfc, c.alias AS concepto_alias, c.nombre AS concepto_nombre,
                       s.cantidad_solicitada, s.cantidad_generada, s.consecutivo_inicio, s.consecutivo_fin
                FROM sar_produccion.solicitud s
                JOIN sar_produccion.grupo_referencia gr ON s.grupo_id = gr.grupo_id
                JOIN sar_catalogo.rfc r ON gr.rfc_id = r.rfc_id
                JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
                JOIN sar_catalogo.delegacion d ON s.delegacion_id = d.delegacion_id
                WHERE s.solicitud_id = :sid AND gr.orden_id = :oid
            """), {"sid": solicitud_id, "oid": orden_id}).mappings().first()
            if not sol_row:
                raise ValueError(f"La solicitud {solicitud_id} no pertenece a la orden {orden_id}.")
            solicitud_especifica = dict(sol_row)

        # 2. Catálogos base
        delegaciones_db = self.session.execute(text("SELECT delegacion_id, nombre FROM sar_catalogo.delegacion")).mappings().all()
        map_delegaciones = {d['nombre'].upper().strip(): d['delegacion_id'] for d in delegaciones_db}

        # Catálogo global de RFCs
        rfcs_db = self.session.execute(text("SELECT rfc_id, rfc FROM sar_catalogo.rfc")).mappings().all()
        map_rfcs_global = {r['rfc'].upper().strip(): r['rfc_id'] for r in rfcs_db}

        # Catálogo global de Conceptos (por alias y por nombre)
        conceptos_db = self.session.execute(text("SELECT concepto_id, nombre, alias, es_cancelacion FROM sar_catalogo.concepto")).mappings().all()
        map_conceptos_global = {}
        for c in conceptos_db:
            if c['alias']:
                map_conceptos_global[c['alias'].upper().strip()] = dict(c)
            if c['nombre']:
                map_conceptos_global[c['nombre'].upper().strip()] = dict(c)

        grupos_db = self.session.execute(text("""
            SELECT gr.grupo_id, r.rfc, c.alias AS concepto_alias, c.nombre AS concepto_nombre
            FROM sar_produccion.grupo_referencia gr
            JOIN sar_catalogo.rfc r ON gr.rfc_id = r.rfc_id
            JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
            WHERE gr.orden_id = :oid
        """), {"oid": orden_id}).mappings().all()
        map_grupos = {(g['rfc'].upper().strip(), (g['concepto_alias'] or g['concepto_nombre']).upper().strip()): g['grupo_id'] for g in grupos_db}

        # 3. Solicitudes existentes
        solicitudes_db = self.session.execute(text("""
            SELECT s.solicitud_id, s.grupo_id, s.delegacion_id
            FROM sar_produccion.solicitud s
            WHERE s.grupo_id IN (SELECT grupo_id FROM sar_produccion.grupo_referencia WHERE orden_id = :oid)
        """), {"oid": orden_id}).mappings().all()
        solicitudes_existentes = {(s['grupo_id'], s['delegacion_id']) for s in solicitudes_db}

        # 4. Validar duplicados de portal en BD
        portal_refs = [str(r.get('referencia_portal', '')).strip() for r in registros if str(r.get('referencia_portal', '')).strip()]
        duplicados_db_set = set()
        chunk_size = 1000
        for i in range(0, len(portal_refs), chunk_size):
            chunk = portal_refs[i:i+chunk_size]
            dups = self.session.execute(
                text("SELECT referencia_portal FROM sar_produccion.referencia WHERE referencia_portal = ANY(:refs)"),
                {"refs": chunk}
            ).scalars().all()
            for d in dups:
                duplicados_db_set.add(d)

        refs_en_archivo = set()
        filas_preview = []
        errores = []
        solicitudes_a_crear_count = 0
        solicitudes_nuevas_keys = set()

        for idx, reg in enumerate(registros, start=1):
            rfc_val = str(reg.get('rfc', '')).upper().strip()
            concepto_val = str(reg.get('concepto_alias', '')).upper().strip()
            deleg_val = str(reg.get('delegacion', '')).upper().strip()
            ref_portal = str(reg.get('referencia_portal', '')).strip()
            importe = float(reg.get('importe') or 0.0)

            fila_error = None
            if not ref_portal:
                fila_error = "Referencia vacía"
            elif ref_portal in refs_en_archivo:
                fila_error = "Referencia duplicada dentro del archivo"
            elif ref_portal in duplicados_db_set:
                fila_error = "Referencia ya existe en la base de datos"
            elif rfc_val not in map_rfcs_global:
                fila_error = f"RFC '{rfc_val}' no existe en el catálogo de empresas"
            elif concepto_val not in map_conceptos_global:
                fila_error = f"Concepto '{concepto_val}' no existe en el catálogo"
            elif deleg_val not in map_delegaciones:
                fila_error = f"Delegación '{deleg_val}' no existe en catálogo"
            else:
                # Si se seleccionó una solicitud específica, validar correspondencia exacta
                if solicitud_especifica:
                    sol_rfc = solicitud_especifica["rfc"].upper().strip()
                    sol_conc_alias = (solicitud_especifica["concepto_alias"] or "").upper().strip()
                    sol_conc_nom = (solicitud_especifica["concepto_nombre"] or "").upper().strip()
                    sol_deleg = solicitud_especifica["delegacion_nombre"].upper().strip()

                    if rfc_val != sol_rfc:
                        fila_error = f"RFC '{rfc_val}' no coincide con la solicitud seleccionada ({sol_rfc})"
                    elif concepto_val not in (sol_conc_alias, sol_conc_nom):
                        fila_error = f"Concepto '{concepto_val}' no coincide con la solicitud seleccionada ({sol_conc_alias})"
                    elif deleg_val != sol_deleg:
                        fila_error = f"Delegación '{deleg_val}' no coincide con la solicitud seleccionada ({sol_deleg})"
                else:
                    # Validar afinidad de concepto con la orden
                    conc_info = map_conceptos_global[concepto_val]
                    if tipo_orden == "CANCELACION" and not conc_info.get("es_cancelacion"):
                        fila_error = f"Concepto '{concepto_val}' no es de tipo Cancelación para esta orden"
                    elif tipo_orden == "ESTANDAR" and (rfc_val, concepto_val) not in map_grupos:
                        fila_error = f"RFC '{rfc_val}' y Concepto '{concepto_val}' no pertenecen a la Orden Estándar"

            refs_en_archivo.add(ref_portal)

            gid = map_grupos.get((rfc_val, concepto_val))
            did = map_delegaciones.get(deleg_val)

            es_nueva_sol = False
            if not fila_error:
                if solicitud_especifica:
                    # Se inyecta directamente en la solicitud existente seleccionada
                    es_nueva_sol = False
                elif tipo_orden != "ESTANDAR":
                    # En órdenes anuales (Cancelación, Pagadas, etc.), siempre se generará una nueva solicitud para los datos del archivo
                    sol_key = (rfc_val, concepto_val, deleg_val)
                    if sol_key not in solicitudes_nuevas_keys:
                        solicitudes_nuevas_keys.add(sol_key)
                    es_nueva_sol = True
                else:
                    if (gid, did) not in solicitudes_existentes:
                        solicitudes_nuevas_keys.add((gid, did))
                        es_nueva_sol = True

            if fila_error:
                errores.append(f"Fila {idx}: {fila_error}")

            filas_preview.append({
                "fila": idx,
                "rfc": rfc_val,
                "concepto": concepto_val,
                "delegacion": deleg_val,
                "referencia_portal": ref_portal,
                "importe": importe,
                "valido": fila_error is None,
                "detalle_validacion": "Válido" if fila_error is None else fila_error,
                "generara_nueva_solicitud": es_nueva_sol
            })

        solicitudes_a_crear_count = len(solicitudes_nuevas_keys)

        # Validación de cupo / capacidad si se seleccionó una solicitud puntual
        if solicitud_especifica and len(errores) == 0:
            cant_sol = solicitud_especifica.get("cantidad_solicitada", 0)
            cant_gen = solicitud_especifica.get("cantidad_generada", 0)
            disponibles = max(0, cant_sol - cant_gen)
            total_validos = len(registros)
            if cant_sol > 0 and total_validos > disponibles:
                errores.append(
                    f"El archivo contiene {total_validos} referencias, pero la Solicitud #{solicitud_especifica['solicitud_id']} "
                    f"solo tiene capacidad para {disponibles} referencia(s) pendiente(s) (Solicitadas: {cant_sol}, Generadas: {cant_gen})."
                )

        return {
            "orden_id": orden_id,
            "folio_orden": orden["folio"],
            "tipo_orden": tipo_orden,
            "total_registros": len(registros),
            "registros_validos": len(registros) - len(errores),
            "registros_invalidos": len(errores),
            "nuevas_solicitudes_estimadas": solicitudes_a_crear_count,
            "filas": filas_preview,
            "errores": errores,
            "es_valido": len(errores) == 0 and len(registros) > 0
        }

    def ejecutar_carga_masiva_referencias(
        self,
        orden_id: int,
        registros: List[Dict[str, Any]],
        usuario_id: int = 1,
        sesion_id: Optional[int] = None,
        solicitud_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta la inserción atómica de referencias masivas.
        Si se especifica solicitud_id, inyecta las referencias directamente en esa solicitud existente.
        Si la orden no es de tipo ESTANDAR y no se pasa solicitud_id, crea obligatoriamente nuevas solicitudes respetando
        la correlación de consecutivos incrementales.
        """
        from sqlalchemy import text
        from datetime import datetime
        from sar.src.storage.models import Referencia

        # 1. Validar orden
        orden = self.session.execute(
            text("SELECT orden_id, folio, descripcion, tipo_orden, estado_id FROM sar_produccion.orden_generacion WHERE orden_id = :oid"),
            {"oid": orden_id}
        ).mappings().first()
        if not orden:
            raise ValueError(f"La orden con ID {orden_id} no existe.")

        tipo_orden = orden["tipo_orden"] or "ESTANDAR"

        # 1.1 Si se especificó una solicitud puntual, obtener su metadata
        solicitud_especifica = None
        if solicitud_id:
            sol_row = self.session.execute(text("""
                SELECT s.solicitud_id, s.grupo_id, s.delegacion_id, d.nombre AS delegacion_nombre,
                       r.rfc, c.alias AS concepto_alias, c.nombre AS concepto_nombre,
                       s.cantidad_solicitada, s.cantidad_generada, s.consecutivo_inicio, s.consecutivo_fin
                FROM sar_produccion.solicitud s
                JOIN sar_produccion.grupo_referencia gr ON s.grupo_id = gr.grupo_id
                JOIN sar_catalogo.rfc r ON gr.rfc_id = r.rfc_id
                JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
                JOIN sar_catalogo.delegacion d ON s.delegacion_id = d.delegacion_id
                WHERE s.solicitud_id = :sid AND gr.orden_id = :oid
            """), {"sid": solicitud_id, "oid": orden_id}).mappings().first()
            if not sol_row:
                raise ValueError(f"La solicitud {solicitud_id} no pertenece a la orden {orden_id}.")
            solicitud_especifica = dict(sol_row)

        # 2. Validar estados
        estado_ref_autorizada = self.session.execute(
            text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad='referencia' AND codigo='AUTORIZADA'")
        ).scalar()
        estado_sol_autorizada = self.session.execute(
            text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad='solicitud' AND codigo='AUTORIZADA'")
        ).scalar()
        estado_sol_pendiente = self.session.execute(
            text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad='solicitud' AND codigo='PENDIENTE'")
        ).scalar() or estado_sol_autorizada
        estado_ord_autorizada = self.session.execute(
            text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad='orden_generacion' AND codigo='AUTORIZADA'")
        ).scalar()

        if not all([estado_ref_autorizada, estado_sol_autorizada, estado_ord_autorizada]):
            raise ValueError("No se encontraron los estados de sistema requeridos (AUTORIZADA).")

        # 3. Delegaciones y Grupos
        delegaciones_db = self.session.execute(text("SELECT delegacion_id, nombre FROM sar_catalogo.delegacion")).mappings().all()
        map_delegaciones = {d['nombre'].upper().strip(): d['delegacion_id'] for d in delegaciones_db}

        # Catálogos globales
        rfcs_db = self.session.execute(text("SELECT rfc_id, rfc FROM sar_catalogo.rfc")).mappings().all()
        map_rfcs_global = {r['rfc'].upper().strip(): r['rfc_id'] for r in rfcs_db}

        conceptos_db = self.session.execute(text("SELECT concepto_id, nombre, alias, es_cancelacion FROM sar_catalogo.concepto")).mappings().all()
        map_conceptos_global = {}
        for c in conceptos_db:
            if c['alias']:
                map_conceptos_global[c['alias'].upper().strip()] = dict(c)
            if c['nombre']:
                map_conceptos_global[c['nombre'].upper().strip()] = dict(c)

        grupos_db = self.session.execute(text("""
            SELECT gr.grupo_id, gr.rfc_id, r.rfc, gr.concepto_id, c.alias AS concepto_alias, c.nombre AS concepto_nombre,
                   gr.cantidad_solicitada, gr.cantidad_generada, gr.ultimo_consecutivo
            FROM sar_produccion.grupo_referencia gr
            JOIN sar_catalogo.rfc r ON gr.rfc_id = r.rfc_id
            JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
            WHERE gr.orden_id = :oid
        """), {"oid": orden_id}).mappings().all()
        map_grupos = {(g['rfc'].upper().strip(), (g['concepto_alias'] or g['concepto_nombre']).upper().strip()): dict(g) for g in grupos_db}

        # 4. Solicitudes existentes
        solicitudes_db = self.session.execute(text("""
            SELECT s.solicitud_id, s.grupo_id, s.delegacion_id, s.cantidad_solicitada, s.cantidad_generada,
                   s.consecutivo_inicio, s.consecutivo_fin
            FROM sar_produccion.solicitud s
            WHERE s.grupo_id IN (SELECT grupo_id FROM sar_produccion.grupo_referencia WHERE orden_id = :oid)
            ORDER BY s.consecutivo_inicio
        """), {"oid": orden_id}).mappings().all()

        map_solicitudes_existentes = {(s['grupo_id'], s['delegacion_id']): dict(s) for s in solicitudes_db}
        solicitudes_por_grupo = {}
        for s in solicitudes_db:
            gid = s['grupo_id']
            solicitudes_por_grupo.setdefault(gid, []).append(dict(s))

        # Determinar el consecutivo siguiente por grupo
        consecutivos_siguiente = {}
        for gid, g_info in [(g['grupo_id'], g) for g in map_grupos.values()]:
            if solicitud_especifica and solicitud_especifica['grupo_id'] == gid:
                # Si se seleccionó una solicitud puntual, usar sus consecutivos ya reservados
                c_ini = solicitud_especifica['consecutivo_inicio']
                c_gen = solicitud_especifica.get('cantidad_generada', 0)
                consecutivos_siguiente[gid] = c_ini + c_gen
            else:
                sols = solicitudes_por_grupo.get(gid, [])
                if sols:
                    max_consec = max([s['consecutivo_fin'] for s in sols if s['consecutivo_fin'] is not None] or [0])
                    consecutivos_siguiente[gid] = max(max_consec, g_info.get('ultimo_consecutivo') or 0) + 1
                else:
                    consecutivos_siguiente[gid] = (g_info.get('ultimo_consecutivo') or 0) + 1

        # 5. Agrupar registros del archivo para crear/asignar solicitudes
        solicitudes_activas_lote = {} # (gid, did) -> dict con metadata de la solicitud
        referencias_a_insertar = []
        nuevas_referencias_por_solicitud = {}
        nuevas_referencias_por_grupo = {}
        total_solicitudes_creadas = 0

        now = datetime.now()

        for reg in registros:
            rfc_val = str(reg.get('rfc', '')).upper().strip()
            concepto_val = str(reg.get('concepto_alias', '')).upper().strip()
            deleg_val = str(reg.get('delegacion', '')).upper().strip()
            ref_portal = str(reg.get('referencia_portal', '')).strip()
            importe = float(reg.get('importe') or 0.0)

            g_key = (rfc_val, concepto_val)
            if g_key not in map_grupos:
                if tipo_orden != "ESTANDAR":
                    # En órdenes no-estándar (como Cancelación o Pagadas), se crea automáticamente el grupo si el RFC y concepto son válidos
                    if rfc_val not in map_rfcs_global:
                        raise ValueError(f"El RFC '{rfc_val}' no existe en el catálogo.")
                    if concepto_val not in map_conceptos_global:
                        raise ValueError(f"El Concepto '{concepto_val}' no existe en el catálogo.")
                    
                    rfc_id_nuevo = map_rfcs_global[rfc_val]
                    concepto_id_nuevo = map_conceptos_global[concepto_val]['concepto_id']
                    
                    estado_grp_autorizado = self.session.execute(
                        text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad='grupo_referencia' AND codigo='AUTORIZADO'")
                    ).scalar() or 1

                    res_grp = self.session.execute(text("""
                        INSERT INTO sar_produccion.grupo_referencia
                        (orden_id, rfc_id, concepto_id, cantidad_solicitada, cantidad_generada, cantidad_autorizada, ultimo_consecutivo, estado_id)
                        VALUES
                        (:oid, :rid, :cid, 0, 0, 0, 0, :eid)
                        RETURNING grupo_id
                    """), {
                        "oid": orden_id, "rid": rfc_id_nuevo, "cid": concepto_id_nuevo, "eid": estado_grp_autorizado
                    })
                    nuevo_gid = res_grp.scalar()
                    grupo_nuevo_dict = {
                        'grupo_id': nuevo_gid,
                        'rfc_id': rfc_id_nuevo,
                        'concepto_id': concepto_id_nuevo,
                        'cantidad_solicitada': 0,
                        'cantidad_generada': 0,
                        'ultimo_consecutivo': 0
                    }
                    map_grupos[g_key] = grupo_nuevo_dict
                    consecutivos_siguiente[nuevo_gid] = 1
                    solicitudes_por_grupo[nuevo_gid] = []
                else:
                    raise ValueError(f"Grupo con RFC '{rfc_val}' y Concepto '{concepto_val}' no pertenece a la orden {orden_id}.")

            grupo = map_grupos[g_key]
            gid = grupo['grupo_id']

            if deleg_val not in map_delegaciones:
                raise ValueError(f"Delegación '{deleg_val}' no existe en catálogo.")
            did = map_delegaciones[deleg_val]

            # Determinar si usamos una solicitud existente o creamos una nueva
            sid = None
            if solicitud_especifica:
                # REGLA: Si el usuario seleccionó una solicitud puntual, usarla obligatoriamente
                sid = solicitud_especifica['solicitud_id']
                if gid not in solicitudes_por_grupo or not any(s['solicitud_id'] == sid for s in solicitudes_por_grupo[gid]):
                    solicitudes_por_grupo.setdefault(gid, []).append(solicitud_especifica)
            elif tipo_orden != "ESTANDAR":
                # REGLA: Si la orden no es ESTANDAR, crear SIEMPRE una nueva solicitud para este lote
                if (gid, did) not in solicitudes_activas_lote:
                    c_inicio = consecutivos_siguiente.get(gid, 1)
                    res_sol = self.session.execute(text("""
                        INSERT INTO sar_produccion.solicitud 
                        (grupo_id, delegacion_id, cantidad_solicitada, cantidad_generada, cantidad_autorizada,
                         consecutivo_inicio, consecutivo_fin, ultimo_consecutivo, estado_id, 
                         fecha_inicio, fecha_fin, fecha_asignacion)
                        VALUES 
                        (:gid, :del_id, 0, 0, 0, :c_ini, :c_ini, :c_ini, :eid, :now, :now, :now)
                        RETURNING solicitud_id
                    """), {
                        "gid": gid, "del_id": did, "c_ini": c_inicio, "eid": estado_sol_autorizada, "now": now
                    })

                    sid = res_sol.scalar()
                    total_solicitudes_creadas += 1
                    nueva_sol_info = {
                        'solicitud_id': sid,
                        'grupo_id': gid,
                        'delegacion_id': did,
                        'cantidad_solicitada': 0,
                        'cantidad_generada': 0,
                        'consecutivo_inicio': c_inicio,
                        'consecutivo_fin': c_inicio - 1,
                        'es_nueva': True
                    }
                    solicitudes_activas_lote[(gid, did)] = nueva_sol_info
                    solicitudes_por_grupo.setdefault(gid, []).append(nueva_sol_info)
                else:
                    sid = solicitudes_activas_lote[(gid, did)]['solicitud_id']
            else:
                # Orden ESTANDAR: Reutilizar si ya existe la delegación, sino crear nueva
                if (gid, did) in map_solicitudes_existentes:
                    sid = map_solicitudes_existentes[(gid, did)]['solicitud_id']
                elif (gid, did) in solicitudes_activas_lote:
                    sid = solicitudes_activas_lote[(gid, did)]['solicitud_id']
                else:
                    c_inicio = consecutivos_siguiente.get(gid, 1)
                    res_sol = self.session.execute(text("""
                        INSERT INTO sar_produccion.solicitud 
                        (grupo_id, delegacion_id, cantidad_solicitada, cantidad_generada, cantidad_autorizada,
                         consecutivo_inicio, consecutivo_fin, ultimo_consecutivo, estado_id, 
                         fecha_inicio, fecha_fin, fecha_asignacion)
                        VALUES 
                        (:gid, :del_id, 0, 0, 0, :c_ini, :c_ini, :c_ini, :eid, :now, :now, :now)
                        RETURNING solicitud_id
                    """), {
                        "gid": gid, "del_id": did, "c_ini": c_inicio, "eid": estado_sol_autorizada, "now": now
                    })
                    sid = res_sol.scalar()
                    total_solicitudes_creadas += 1
                    nueva_sol_info = {
                        'solicitud_id': sid,
                        'grupo_id': gid,
                        'delegacion_id': did,
                        'cantidad_solicitada': 0,
                        'cantidad_generada': 0,
                        'consecutivo_inicio': c_inicio,
                        'consecutivo_fin': c_inicio - 1,
                        'es_nueva': True
                    }
                    solicitudes_activas_lote[(gid, did)] = nueva_sol_info
                    solicitudes_por_grupo.setdefault(gid, []).append(nueva_sol_info)

            consecutivo_actual = consecutivos_siguiente.get(gid, 1)
            consecutivos_siguiente[gid] = consecutivo_actual + 1

            # Fechas
            f_gen = reg.get('fecha_generacion')
            f_vig = reg.get('fecha_vigencia')

            referencias_a_insertar.append({
                'grupo_id': gid,
                'solicitud_id': sid,
                'consecutivo_grupo': consecutivo_actual,
                'referencia_portal': ref_portal,
                'importe': importe,
                'fecha_generacion': f_gen if f_gen else now.date(),
                'fecha_vigencia': f_vig,
                'estado_id': estado_ref_autorizada,
                'cantidad': 1,
                'porcentaje': 100
            })

            nuevas_referencias_por_solicitud[sid] = nuevas_referencias_por_solicitud.get(sid, 0) + 1
            nuevas_referencias_por_grupo[gid] = nuevas_referencias_por_grupo.get(gid, 0) + 1

        # 6. Bulk insert en sar_produccion.referencia
        self.session.bulk_insert_mappings(Referencia, referencias_a_insertar)
        self.session.flush()

        # 7. Actualizar solicitudes
        for sid, count in nuevas_referencias_por_solicitud.items():
            sol = next(s for s_list in solicitudes_por_grupo.values() for s in s_list if s['solicitud_id'] == sid)
            nueva_cant_gen = sol['cantidad_generada'] + count
            
            # Si la solicitud ya tenía cantidad_solicitada reservada (ej: 4 solicitadas, 0 generadas)
            # se ocupan los lugares ya reservados sin sumar extra.
            if sol['cantidad_solicitada'] >= nueva_cant_gen:
                nueva_cant_sol = sol['cantidad_solicitada']
                nuevo_consecutivo_fin = sol['consecutivo_fin']
            else:
                nueva_cant_sol = nueva_cant_gen
                nuevo_consecutivo_fin = sol['consecutivo_inicio'] + nueva_cant_sol - 1

            ultimo_c_sol = sol['consecutivo_inicio'] + nueva_cant_gen - 1
            nuevo_estado_sol = estado_sol_autorizada if nueva_cant_gen >= nueva_cant_sol else estado_sol_pendiente

            self.session.execute(text("""
                UPDATE sar_produccion.solicitud
                SET cantidad_solicitada = :cs, cantidad_generada = :cg, cantidad_autorizada = :cg,
                    consecutivo_fin = :cfin, ultimo_consecutivo = :uc, estado_id = :eid
                WHERE solicitud_id = :sid
            """), {
                "cs": nueva_cant_sol, "cg": nueva_cant_gen, "cfin": nuevo_consecutivo_fin, "uc": ultimo_c_sol,
                "eid": nuevo_estado_sol, "sid": sid
            })

        # 8. Actualizar grupos
        for gid, count in nuevas_referencias_por_grupo.items():
            g_db = next(g for g in map_grupos.values() if g['grupo_id'] == gid)
            nueva_cant_gen = g_db['cantidad_generada'] + count
            
            # Si el grupo ya tenía la cantidad solicitada (cuota original reservada)
            if g_db['cantidad_solicitada'] >= nueva_cant_gen:
                nueva_cant_sol = g_db['cantidad_solicitada']
            else:
                nueva_cant_sol = nueva_cant_gen

            ultimo_c = max(g_db.get('ultimo_consecutivo') or 0, consecutivos_siguiente.get(gid, 1) - 1)

            self.session.execute(text("""
                UPDATE sar_produccion.grupo_referencia
                SET cantidad_solicitada = :cs, cantidad_generada = :cg, cantidad_autorizada = :cg,
                    ultimo_consecutivo = :uc
                WHERE grupo_id = :gid
            """), {
                "cs": nueva_cant_sol, "cg": nueva_cant_gen, "uc": ultimo_c, "gid": gid
            })

        # 9. Manejo de estado de la Orden respetando órdenes anuales:
        # Las órdenes anuales/no-estándar (CANCELACION, PAGADAS, etc.) permanecen en su estado actual (ABIERTA) durante todo el año.
        if tipo_orden == "ESTANDAR":
            # Para órdenes estándar, verificar si ya se completaron todos sus grupos
            pendientes_orden = self.session.execute(text("""
                SELECT COUNT(*) FROM sar_produccion.grupo_referencia 
                WHERE orden_id = :oid AND (cantidad_solicitada > cantidad_generada OR cantidad_generada = 0)
            """), {"oid": orden_id}).scalar() or 0

            if pendientes_orden == 0:
                self.session.execute(
                    text("UPDATE sar_produccion.orden_generacion SET estado_id = :eid WHERE orden_id = :oid"),
                    {"eid": estado_ord_autorizada, "oid": orden_id}
                )

        # 10. Auditoría formal
        self._log_audit(
            usuario_id=usuario_id,
            sesion_id=sesion_id,
            modulo="ADMINISTRACION",
            action="CARGA_MASIVA_REFERENCIAS",
            old_val=None,
            new_val={
                "folio": orden["folio"],
                "tipo_orden": tipo_orden,
                "referencias_cargadas": len(referencias_a_insertar),
                "solicitudes_creadas": total_solicitudes_creadas
            },
            detalle={
                "orden_id": orden_id,
                "mensaje": f"Carga masiva completada para orden {orden['folio']}: {len(referencias_a_insertar)} referencias y {total_solicitudes_creadas} solicitudes."
            }
        )

        return {
            "orden_id": orden_id,
            "folio_orden": orden["folio"],
            "tipo_orden": tipo_orden,
            "total_referencias_cargadas": len(referencias_a_insertar),
            "solicitudes_creadas": total_solicitudes_creadas,
            "mensaje": f"Se cargaron exitosamente {len(referencias_a_insertar)} referencias a la orden {orden['folio']}."
        }

