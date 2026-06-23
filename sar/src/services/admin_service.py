"""Service layer for Administration operations (CRUD and Auditing)."""

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
    AppModulo, Modulo, EstadoSistema, Accion
)

class AdminService:
    """Handles business logic for the System Administration Module."""

    def __init__(self, session: Session):
        self.session = session
        self.user_repo = UsuarioRepository(session)
        self.cat_repo = CatalogoRepository(session)
        self.config_repo = ConfigRepository(session)
        self.audit_repo = AuditRepository(session)
        self.ph = PasswordHasher()

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

    def save_rfc(self, usuario_id: Optional[int], sesion_id: Optional[int], data: Dict[str, Any]) -> Rfc:
        modulo = "ADMIN_CATALOGOS"
        action = "CREAR_REGISTRO"
        old_val = None

        if data.get("rfc_id"):
            rfc = self.session.get(Rfc, data["rfc_id"])
            action = "ACTUALIZAR_REGISTRO"
            old_val = {"rfc": rfc.rfc, "razon_social": rfc.razon_social, "activo": rfc.activo}
            
            rfc.rfc = data.get("rfc", rfc.rfc)
            rfc.razon_social = data.get("razon_social", rfc.razon_social)
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
        new_val = {"rfc_id": rfc.rfc_id, "rfc": rfc.rfc, "razon_social": rfc.razon_social, "activo": rfc.activo}
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"rfc": rfc.rfc})
        return rfc

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

        self.user_repo.save_rol(rol)
        new_val = {"rol_id": rol.rol_id, "codigo": rol.codigo, "nombre": rol.nombre, "activo": rol.activo}
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"nombre": rol.nombre})
        return rol

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

    def save_modulo(self, usuario_id: Optional[int], sesion_id: Optional[int], data: Dict[str, Any]) -> Modulo:
        modulo = "ADMIN_SEGURIDAD"
        action = "CREAR_REGISTRO"
        old_val = None

        if data.get("modulo_id"):
            m = self.session.get(Modulo, data["modulo_id"])
            action = "ACTUALIZAR_REGISTRO"
            old_val = {"codigo": m.codigo, "nombre": m.nombre, "descripcion": m.descripcion, "activo": m.activo}
            
            m.codigo = data.get("codigo", m.codigo)
            m.nombre = data.get("nombre", m.nombre)
            m.descripcion = data.get("descripcion", m.descripcion)
            if "activo" in data:
                m.activo = data["activo"]
        else:
            m = Modulo(
                codigo=data["codigo"],
                nombre=data["nombre"],
                descripcion=data.get("descripcion", ""),
                activo=data.get("activo", True)
            )

        self.session.add(m)
        self.session.flush()
        new_val = {"modulo_id": m.modulo_id, "codigo": m.codigo, "nombre": m.nombre, "descripcion": m.descripcion, "activo": m.activo}
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"nombre": m.nombre})
        return m

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

    def save_delegacion(self, usuario_id: Optional[int], sesion_id: Optional[int], data: Dict[str, Any]) -> Delegacion:
        modulo = "ADMIN_CATALOGOS"
        action = "CREAR_REGISTRO"
        old_val = None

        if data.get("delegacion_id"):
            d = self.session.get(Delegacion, data["delegacion_id"])
            action = "ACTUALIZAR_REGISTRO"
            old_val = {"codigo_portal": d.codigo_portal, "nombre": d.nombre, "municipio_id": d.municipio_id, "activo": d.activo}
            
            d.codigo_portal = data.get("codigo_portal", d.codigo_portal)
            d.nombre = data.get("nombre", d.nombre)
            d.municipio_id = data.get("municipio_id", d.municipio_id)
            if "activo" in data:
                d.activo = data["activo"]
        else:
            d = Delegacion(
                codigo_portal=data.get("codigo_portal"),
                nombre=data["nombre"],
                municipio_id=data["municipio_id"],
                activo=data.get("activo", True)
            )

        self.cat_repo.save_delegacion(d)
        new_val = {"delegacion_id": d.delegacion_id, "nombre": d.nombre, "municipio_id": d.municipio_id, "activo": d.activo}
        self._log_audit(usuario_id, sesion_id, modulo, action, old_val, new_val, {"nombre": d.nombre})
        return d
