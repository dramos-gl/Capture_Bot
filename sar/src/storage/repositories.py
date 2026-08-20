"""Repository classes for encapsulated database CRUD and queries."""

from typing import List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from sar.src.storage.models import (
    Usuario,
    Rol,
    Modulo,
    Accion,
    Permiso,
    Sesion,
    OrdenGeneracion,
    GrupoReferencia,
    Solicitud,
    Referencia,
    AuditoriaLogin,
    AuditoriaEvento,
    AuditoriaError,
    EventoSistema,
    ParametroSistema,
    LocalizadorPortal,
    usuario_rol,
    rol_permiso,
    Rfc,
    Concepto,
    Delegacion,
    Municipio,
    AppModulo,
    EstadoSistema
)


class BaseRepository:
    """Base repository class providing session access."""
    def __init__(self, session: Session):
        self.session = session


class UsuarioRepository(BaseRepository):
    """Handles query operations for Usuario and authorization schema."""

    def get_by_id(self, usuario_id: int) -> Optional[Usuario]:
        return self.session.get(Usuario, usuario_id)

    def get_by_username(self, username: str) -> Optional[Usuario]:
        stmt = select(Usuario).where(Usuario.username == username)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_all_usuarios(self) -> List[Usuario]:
        stmt = select(Usuario).order_by(Usuario.username)
        return list(self.session.execute(stmt).scalars().all())

    def save(self, usuario: Usuario) -> Usuario:
        self.session.add(usuario)
        self.session.flush()
        return usuario

    def get_all_roles(self) -> List[Rol]:
        stmt = select(Rol).order_by(Rol.nombre)
        return list(self.session.execute(stmt).scalars().all())

    def get_roles_for_user(self, usuario_id: int) -> List[int]:
        stmt = select(usuario_rol.c.rol_id).where(usuario_rol.c.usuario_id == usuario_id)
        return list(self.session.execute(stmt).scalars().all())
        
    def get_all_app_modulos(self) -> List[AppModulo]:
        stmt = select(AppModulo).where(AppModulo.activo == True).order_by(AppModulo.nombre)
        return list(self.session.execute(stmt).scalars().all())

    def get_all_modulos(self) -> List[Modulo]:
        stmt = select(Modulo).where(Modulo.activo == True).order_by(Modulo.nombre)
        return list(self.session.execute(stmt).scalars().all())
        
    def get_all_acciones(self) -> List[Accion]:
        stmt = select(Accion).where(Accion.activo == True).order_by(Accion.nombre)
        return list(self.session.execute(stmt).scalars().all())
        
    def get_permisos_for_rol(self, rol_id: int) -> List[tuple[int, int]]:
        stmt = (
            select(Permiso.modulo_id, Permiso.accion_id)
            .join(rol_permiso, Permiso.permiso_id == rol_permiso.c.permiso_id)
            .where(rol_permiso.c.rol_id == rol_id)
        )
        return list(self.session.execute(stmt).all())

    def get_app_modulos_for_rol(self, rol_id: int) -> List[int]:
        from sar.src.storage.models import rol_app_modulo
        stmt = select(rol_app_modulo.c.app_modulo_id).where(rol_app_modulo.c.rol_id == rol_id)
        return list(self.session.execute(stmt).scalars().all())

    def save_rol(self, rol: Rol) -> Rol:
        self.session.add(rol)
        self.session.flush()
        return rol

    def get_user_permissions(self, usuario_id: int) -> List[tuple[str, str]]:
        """Fetches distinct modulo and accion code pairs representing the user's permissions."""
        stmt = (
            select(Modulo.codigo, Accion.codigo)
            .select_from(Usuario)
            .join(usuario_rol, Usuario.usuario_id == usuario_rol.c.usuario_id)
            .join(Rol, usuario_rol.c.rol_id == Rol.rol_id)
            .join(rol_permiso, Rol.rol_id == rol_permiso.c.rol_id)
            .join(Permiso, rol_permiso.c.permiso_id == Permiso.permiso_id)
            .join(Modulo, Permiso.modulo_id == Modulo.modulo_id)
            .join(Accion, Permiso.accion_id == Accion.accion_id)
            .where(and_(Usuario.usuario_id == usuario_id, Permiso.activo == True))
        )
        return self.session.execute(stmt).all()

    def get_authorized_app_modules(self, usuario_id: int) -> List[str]:
        """Fetches distinct application module codes that the user is authorized to access."""
        from sar.src.storage.models import rol_app_modulo, AppModulo
        stmt = (
            select(AppModulo.codigo)
            .select_from(Usuario)
            .join(usuario_rol, Usuario.usuario_id == usuario_rol.c.usuario_id)
            .join(Rol, usuario_rol.c.rol_id == Rol.rol_id)
            .join(rol_app_modulo, Rol.rol_id == rol_app_modulo.c.rol_id)
            .join(AppModulo, rol_app_modulo.c.app_modulo_id == AppModulo.app_modulo_id)
            .where(and_(Usuario.usuario_id == usuario_id, AppModulo.activo == True))
            .distinct()
        )
        return list(self.session.execute(stmt).scalars().all())


class OrdenRepository(BaseRepository):
    """Handles persistence operations for orders and nested groups/solicitudes."""

    def create(self, orden: OrdenGeneracion) -> OrdenGeneracion:
        self.session.add(orden)
        self.session.flush()  # Generar ID sin confirmar transacción
        return orden

    def get_by_id(self, orden_id: int) -> Optional[OrdenGeneracion]:
        return self.session.get(OrdenGeneracion, orden_id)

    def get_by_folio(self, folio: str) -> Optional[OrdenGeneracion]:
        stmt = select(OrdenGeneracion).where(OrdenGeneracion.folio == folio)
        return self.session.execute(stmt).scalar_one_or_none()


class SolicitudRepository(BaseRepository):
    """Handles worker query operations and locks on Solicitud."""

    def get_by_id(self, solicitud_id: int) -> Optional[Solicitud]:
        return self.session.get(Solicitud, solicitud_id)

    def claim_solicitud_with_lock(self, solicitud_id: int) -> Optional[Solicitud]:
        """Locks a specific Solicitud row using SELECT ... FOR UPDATE."""
        stmt = (
            select(Solicitud)
            .where(Solicitud.solicitud_id == solicitud_id)
            .with_for_update()
        )
        return self.session.execute(stmt).scalar_one_or_none()


class ReferenciaRepository(BaseRepository):
    """Handles saving and checking Tributanet reference records."""

    def create(self, referencia: Referencia) -> Referencia:
        self.session.add(referencia)
        self.session.flush()
        return referencia

    def exists_by_portal_ref(self, ref_portal: str) -> bool:
        stmt = select(Referencia.referencia_id).where(Referencia.referencia_portal == ref_portal)
        return self.session.execute(stmt).scalar_one_or_none() is not None


class AuditRepository(BaseRepository):
    """Handles recording session logs, transational event logs, and bot errors."""

    def create_session(self, usuario_id: int, equipo_nombre: str, equipo_uuid: str, ip_equipo: str) -> Sesion:
        sesion = Sesion(
            usuario_id=usuario_id,
            equipo_nombre=equipo_nombre,
            equipo_uuid=equipo_uuid,
            ip_equipo=ip_equipo,
            estado="ACTIVA"
        )
        self.session.add(sesion)
        self.session.flush()
        return sesion

    def close_session(self, sesion_id: int) -> None:
        sesion = self.session.get(Sesion, sesion_id)
        if sesion:
            sesion.estado = "FINALIZADA"
            # Usar fecha nativa
            from datetime import datetime
            sesion.ultimo_heartbeat = datetime.utcnow()

    def log_login(self, usuario_id: int, sesion_id: int, ip: str, equipo: str) -> None:
        log = AuditoriaLogin(
            usuario_id=usuario_id,
            sesion_id=sesion_id,
            ip=ip,
            equipo=equipo
        )
        self.session.add(log)

    def log_logout(self, usuario_id: int, sesion_id: int) -> None:
        stmt = select(AuditoriaLogin).where(
            and_(AuditoriaLogin.usuario_id == usuario_id, AuditoriaLogin.sesion_id == sesion_id)
        ).order_by(AuditoriaLogin.login_id.desc())
        log = self.session.execute(stmt).scalars().first()
        if log:
            from datetime import datetime
            log.fecha_logout = datetime.utcnow()

    def log_evento(
        self,
        evento_codigo: str,
        modulo: str,
        usuario_id: Optional[int],
        sesion_id: Optional[int],
        valor_anterior: Optional[dict] = None,
        valor_nuevo: Optional[dict] = None,
        detalle: Optional[dict] = None
    ) -> None:
        # Buscar el ID del evento por su código
        evt_stmt = select(EventoSistema.evento_id).where(EventoSistema.codigo == evento_codigo)
        evento_id = self.session.execute(evt_stmt).scalar_one()

        log = AuditoriaEvento(
            evento_id=evento_id,
            usuario_id=usuario_id,
            sesion_id=sesion_id,
            modulo=modulo,
            valor_anterior=valor_anterior,
            valor_nuevo=valor_nuevo,
            detalle=detalle
        )
        self.session.add(log)

    def log_error(
        self,
        usuario_id: Optional[int],
        sesion_id: Optional[int],
        modulo: str,
        mensaje: str,
        stack_trace: Optional[str] = None
    ) -> None:
        log = AuditoriaError(
            usuario_id=usuario_id,
            sesion_id=sesion_id,
            modulo=modulo,
            mensaje=mensaje,
            stack_trace=stack_trace
        )
        self.session.add(log)


class ConfigRepository(BaseRepository):
    """Handles query operations for system parameters and portal selectors configuration."""

    def get_parametro(self, codigo: str) -> Optional[str]:
        """Gets the value of a system parameter by its code."""
        stmt = select(ParametroSistema.valor).where(
            and_(ParametroSistema.codigo == codigo, ParametroSistema.activo == True)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_localizadores(self) -> dict[str, LocalizadorPortal]:
        """Gets all active locators mapped by their nombre_clave."""
        stmt = select(LocalizadorPortal).where(LocalizadorPortal.activo == True)
        results = self.session.execute(stmt).scalars().all()
        return {loc.nombre_clave: loc for loc in results}

    def get_localizadores_portal(self, portal: str) -> dict[str, LocalizadorPortal]:
        """Gets all active locators for a specific portal, mapped by their nombre_clave."""
        stmt = select(LocalizadorPortal).where(
            and_(LocalizadorPortal.activo == True, LocalizadorPortal.portal == portal)
        )
        results = self.session.execute(stmt).scalars().all()
        return {loc.nombre_clave: loc for loc in results}

    def get_lote_size(self, default_size: int = 299) -> int:
        """Helper to get TAMANO_LOTE parameter or return default."""
        val = self.get_parametro("TAMANO_LOTE")
        if val is not None and val.isdigit():
            return int(val)
        return default_size

    def get_lote_solicitud_size(self, default_size: int = 2000) -> int:
        """Helper to get TAMANO_LOTE_SOLICITUD parameter or return default."""
        val = self.get_parametro("TAMANO_LOTE_SOLICITUD")
        if val is not None and val.isdigit():
            return int(val)
        return default_size

    def get_all_parametros(self) -> List[ParametroSistema]:
        stmt = select(ParametroSistema).order_by(ParametroSistema.codigo)
        return list(self.session.execute(stmt).scalars().all())

    def save_parametro(self, parametro: ParametroSistema) -> ParametroSistema:
        self.session.add(parametro)
        self.session.flush()
        return parametro

    def get_all_localizadores_list(self) -> List[LocalizadorPortal]:
        stmt = select(LocalizadorPortal).order_by(LocalizadorPortal.nombre_clave)
        return list(self.session.execute(stmt).scalars().all())

    def save_localizador(self, loc: LocalizadorPortal) -> LocalizadorPortal:
        self.session.add(loc)
        self.session.flush()
        return loc


class CatalogoRepository(BaseRepository):
    """Handles query operations for static and semi-static catalogs."""

    def get_rfcs_activos(self) -> List[Rfc]:
        stmt = select(Rfc).where(Rfc.activo == True).order_by(Rfc.razon_social)
        return list(self.session.execute(stmt).scalars().all())

    def get_conceptos_activos(self) -> List[Concepto]:
        stmt = select(Concepto).where(Concepto.activo == True).order_by(Concepto.nombre)
        return list(self.session.execute(stmt).scalars().all())

    def get_delegaciones_activas(self) -> List[Delegacion]:
        stmt = select(Delegacion).where(Delegacion.activo == True).order_by(Delegacion.nombre)
        return list(self.session.execute(stmt).scalars().all())

    def get_all_rfcs(self) -> List[Rfc]:
        stmt = select(Rfc).order_by(Rfc.razon_social)
        return list(self.session.execute(stmt).scalars().all())

    def save_rfc(self, rfc: Rfc) -> Rfc:
        self.session.add(rfc)
        self.session.flush()
        return rfc

    def get_all_conceptos(self) -> List[Concepto]:
        stmt = select(Concepto).order_by(Concepto.nombre)
        return list(self.session.execute(stmt).scalars().all())

    def save_concepto(self, concepto: Concepto) -> Concepto:
        self.session.add(concepto)
        self.session.flush()
        return concepto

    def get_all_municipios(self) -> List[Municipio]:
        stmt = select(Municipio).order_by(Municipio.nombre)
        return list(self.session.execute(stmt).scalars().all())

    def save_municipio(self, mun: Municipio) -> Municipio:
        self.session.add(mun)
        self.session.flush()
        return mun

    def get_all_delegaciones_list(self) -> List[Delegacion]:
        stmt = select(Delegacion).order_by(Delegacion.nombre)
        return list(self.session.execute(stmt).scalars().all())

    def get_delegaciones_por_municipio(self, municipio_id: int) -> List[Delegacion]:
        stmt = select(Delegacion).where(Delegacion.municipio_id == municipio_id).order_by(Delegacion.nombre)
        return list(self.session.execute(stmt).scalars().all())

    def save_delegacion(self, d: Delegacion) -> Delegacion:
        self.session.add(d)
        self.session.flush()
        return d

    def get_all_estados_sistema(self) -> List[EstadoSistema]:
        stmt = select(EstadoSistema).order_by(EstadoSistema.entidad, EstadoSistema.codigo)
        return list(self.session.execute(stmt).scalars().all())

    def save_estado_sistema(self, est: EstadoSistema) -> EstadoSistema:
        self.session.add(est)
        self.session.flush()
        return est

    def get_all_notarias(self) -> List[Any]:
        from sar.src.storage.models import Notaria
        stmt = select(Notaria).order_by(Notaria.nombre)
        return list(self.session.execute(stmt).scalars().all())

    def save_notaria(self, n: Any) -> Any:
        self.session.add(n)
        self.session.flush()
        return n

    def get_all_colaboradores(self) -> List[Any]:
        from sar.src.storage.models import Colaborador
        stmt = select(Colaborador).order_by(Colaborador.nombre)
        return list(self.session.execute(stmt).scalars().all())

    def save_colaborador(self, c: Any) -> Any:
        self.session.add(c)
        self.session.flush()
        return c

    def get_all_desarrollos(self) -> List[Any]:
        from sar.src.storage.models import Desarrollo
        stmt = select(Desarrollo).order_by(Desarrollo.nombre)
        return list(self.session.execute(stmt).scalars().all())

    def save_desarrollo(self, d: Any) -> Any:
        self.session.add(d)
        self.session.flush()
        return d

    def get_desarrollo_empresas(self, desarrollo_id: int) -> List[Any]:
        from sar.src.storage.models import DesarrolloEmpresa
        from sqlalchemy.orm import selectinload
        stmt = select(DesarrolloEmpresa).where(DesarrolloEmpresa.desarrollo_id == desarrollo_id)\
            .options(selectinload(DesarrolloEmpresa.rfc), selectinload(DesarrolloEmpresa.delegacion))\
            .order_by(DesarrolloEmpresa.desarrollo_empresa_id)
        return list(self.session.execute(stmt).scalars().all())

    def save_desarrollo_empresa(self, de: Any) -> Any:
        self.session.add(de)
        self.session.flush()
        return de



class OperacionRepository(BaseRepository):
    def _get_estado_id(self, codigo: str) -> int:
        from sqlalchemy import select
        estado = self.session.execute(select(EstadoSistema).where(EstadoSistema.codigo == codigo)).scalars().first()
        if not estado:
            raise ValueError(f"Estado no encontrado: {codigo}")
        return estado.estado_id

    def get_all_ordenes(self) -> List[dict]:
        from sqlalchemy import select
        stmt = select(OrdenGeneracion).order_by(OrdenGeneracion.fecha_creacion.desc())
        ordenes = self.session.scalars(stmt).all()
        
        result = []
        for o in ordenes:
            estado_codigo = self.session.execute(select(EstadoSistema.codigo).where(EstadoSistema.estado_id == o.estado_id)).scalar_one()
            result.append({
                "orden_id": o.orden_id,
                "folio": o.folio,
                "descripcion": o.descripcion,
                "fecha_creacion": o.fecha_creacion.strftime("%Y-%m-%d %H:%M"),
                "estado": estado_codigo,
                "usuario_id": o.usuario_id
            })
        return result
        
    def create_orden(self, folio: str, descripcion: str, usuario_id: int) -> OrdenGeneracion:
        estado_borrador = self._get_estado_id("BORRADOR")
        orden = OrdenGeneracion(
            folio=folio,
            descripcion=descripcion,
            estado_id=estado_borrador,
            usuario_id=usuario_id
        )
        self.session.add(orden)
        self.session.flush()
        return orden
        
    def update_orden_estado(self, orden_id: int, nuevo_estado_codigo: str):
        orden = self.session.get(OrdenGeneracion, orden_id)
        if orden:
            orden.estado_id = self._get_estado_id(nuevo_estado_codigo)
            self.session.flush()

    def create_grupo_referencia(self, orden_id: int, rfc_id: int, concepto_id: int, cantidad: int) -> GrupoReferencia:
        estado_pdte = self._get_estado_id("PENDIENTE")
        grupo = GrupoReferencia(
            orden_id=orden_id,
            rfc_id=rfc_id,
            concepto_id=concepto_id,
            cantidad_solicitada=cantidad,
            estado_id=estado_pdte
        )
        self.session.add(grupo)
        self.session.flush()
        return grupo

    def create_solicitud(self, grupo_id: int, delegacion_id: int, cantidad: int, consecutivo_inicio: int, consecutivo_fin: int) -> Solicitud:
        estado_pdte = self._get_estado_id("PENDIENTE")
        solicitud = Solicitud(
            grupo_id=grupo_id,
            delegacion_id=delegacion_id,
            cantidad_solicitada=cantidad,
            consecutivo_inicio=consecutivo_inicio,
            consecutivo_fin=consecutivo_fin,
            estado_id=estado_pdte
        )
        self.session.add(solicitud)
        self.session.flush()
        return solicitud
        
    def get_solicitudes(self, orden_ids: list = None) -> List[dict]:
        from sqlalchemy import text
        from sar.src.storage.models import EstadoSistema
        from sqlalchemy import select
        
        # Get the ID of the 'FACTURADA' state for references precisely
        try:
            facturada_state_id = self.session.execute(
                select(EstadoSistema.estado_id).where(
                    EstadoSistema.entidad == "referencia",
                    EstadoSistema.codigo == "FACTURADA"
                )
            ).scalar()
        except Exception:
            facturada_state_id = None

        if facturada_state_id:
            subquery_count = f"""
                COALESCE((
                    SELECT COUNT(*) 
                    FROM sar_produccion.referencia 
                    WHERE solicitud_id = v.solicitud_id AND estado_id = {facturada_state_id}
                ), 0)
            """
        else:
            subquery_count = """
                COALESCE((
                    SELECT COUNT(*) 
                    FROM sar_produccion.referencia r 
                    JOIN sar_catalogo.estado_sistema esr ON r.estado_id = esr.estado_id 
                    WHERE r.solicitud_id = v.solicitud_id AND esr.codigo = 'FACTURADA'
                ), 0)
            """

        if orden_ids:
            stmt = text(f"""
                SELECT v.*, {subquery_count} AS cantidad_facturada
                FROM sar_produccion.vw_solicitudes_detalle v
                JOIN sar_produccion.grupo_referencia gr ON v.grupo_id = gr.grupo_id
                WHERE gr.orden_id IN :orden_ids_param
                ORDER BY v.grupo_id ASC, v.solicitud_id ASC
            """)
            result = self.session.execute(stmt, {"orden_ids_param": tuple(orden_ids)})
        else:
            stmt = text(f"""
                SELECT v.*, {subquery_count} AS cantidad_facturada
                FROM sar_produccion.vw_solicitudes_detalle v
                ORDER BY v.grupo_id ASC, v.solicitud_id ASC
            """)
            result = self.session.execute(stmt)
        res = []
        for row in result:
            res.append({
                "solicitud_id": row.solicitud_id,
                "grupo_id": row.grupo_id,
                "folio": row.folio,
                "rfc": row.rfc_razon_social,
                "concepto": row.concepto_nombre,
                "delegacion": row.delegacion_nombre or "Sin Delegación",
                "cantidad_solicitada": row.cantidad_solicitada,
                "cantidad_generada": row.cantidad_generada,
                "cantidad_facturada": getattr(row, "cantidad_facturada", 0),
                "estado": row.estado_codigo,
                "usuario_asignado": row.usuario_asignado_nombre or "Sin Asignar"
            })
        return res
        
    def asignar_solicitud(self, solicitud_id: int, usuario_id: int) -> bool:
        from sqlalchemy import select
        solicitud = self.session.get(Solicitud, solicitud_id)
        if not solicitud:
            return False
            
        estado_codigo = self.session.execute(select(EstadoSistema.codigo).where(EstadoSistema.estado_id == solicitud.estado_id)).scalar_one()
        
        # Asignar el nuevo usuario siempre
        solicitud.usuario_asignado = usuario_id
        
        # Solo actualizar el estado a ASIGNADO si el estado actual es PENDIENTE
        if estado_codigo == 'PENDIENTE':
            from sqlalchemy import and_
            estado_asignado = self.session.execute(
                select(EstadoSistema).where(
                    and_(EstadoSistema.entidad == 'solicitud', EstadoSistema.codigo == 'ASIGNADA')
                )
            ).scalars().first()
            if not estado_asignado:
                estado_asignado = EstadoSistema(entidad='solicitud', codigo='ASIGNADA', descripcion='Estado ASIGNADA de solicitud')
                self.session.add(estado_asignado)
                self.session.flush()
            solicitud.estado_id = estado_asignado.estado_id
        
        # Actualizar la orden a 'ABIERTA' si su estado actual es 'PENDIENTE'
        if solicitud.grupo and solicitud.grupo.orden:
            from sqlalchemy import and_
            orden = solicitud.grupo.orden
            estado_orden = self.session.execute(select(EstadoSistema.codigo).where(EstadoSistema.estado_id == orden.estado_id)).scalar_one()
            if estado_orden == 'PENDIENTE':
                estado_abierta = self.session.execute(
                    select(EstadoSistema).where(
                        and_(EstadoSistema.entidad == 'orden_generacion', EstadoSistema.codigo == 'ABIERTA')
                    )
                ).scalars().first()
                if not estado_abierta:
                    estado_abierta = EstadoSistema(entidad='orden_generacion', codigo='ABIERTA', descripcion='Estado ABIERTA de orden_generacion')
                    self.session.add(estado_abierta)
                    self.session.flush()
                orden.estado_id = estado_abierta.estado_id
                
        self.session.flush()
        return True

    def cancelar_solicitud(self, solicitud_id: int) -> bool:
        from sqlalchemy import text
        stmt = text("SELECT sar_produccion.fn_cancelar_solicitud(:solicitud_id)")
        result = self.session.execute(stmt, {"solicitud_id": solicitud_id}).scalar()
        self.session.flush()
        return result

    def editar_cantidad_solicitud(self, solicitud_id: int, nueva_cantidad: int) -> bool:
        from sqlalchemy import text
        stmt = text("SELECT sar_produccion.fn_editar_cantidad_solicitud(:solicitud_id, :nueva_cantidad)")
        result = self.session.execute(stmt, {"solicitud_id": solicitud_id, "nueva_cantidad": nueva_cantidad}).scalar()
        self.session.flush()
        return result


    def get_solicitudes_asignadas(self, usuario_id: int, ver_todas: bool = False) -> List[dict]:
        """Fetch only solicitudes assigned to a specific user and pending."""
        from sqlalchemy import text
        query_str = """
            SELECT s.solicitud_id, s.grupo_id, o.folio, rfc.rfc, rfc.razon_social, 
                   c.alias as concepto, d.nombre as delegacion, 
                   s.cantidad_solicitada, s.cantidad_generada, es.codigo as estado
            FROM sar_produccion.solicitud s
            JOIN sar_produccion.grupo_referencia gr ON s.grupo_id = gr.grupo_id
            JOIN sar_produccion.orden_generacion o ON gr.orden_id = o.orden_id
            JOIN sar_catalogo.rfc rfc ON gr.rfc_id = rfc.rfc_id
            JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
            JOIN sar_catalogo.delegacion d ON s.delegacion_id = d.delegacion_id
            JOIN sar_catalogo.estado_sistema es ON s.estado_id = es.estado_id
            WHERE s.usuario_asignado = :usuario_id
        """
        if not ver_todas:
            query_str += " AND es.codigo IN ('ASIGNADO', 'ASIGNADA', 'PROCESANDO', 'ERROR')"
        else:
            query_str += " AND es.codigo IN ('ASIGNADO', 'ASIGNADA', 'PROCESANDO', 'ERROR', 'COMPLETADA', 'COMPLETADO', 'CANCELADA')"
            
        query_str += " ORDER BY s.solicitud_id ASC"
        
        stmt = text(query_str)
        result = self.session.execute(stmt, {"usuario_id": usuario_id})
        res = []
        for row in result:
            res.append({
                "solicitud_id": row.solicitud_id,
                "grupo_id": row.grupo_id,
                "folio": row.folio,
                "rfc": row.rfc,
                "razon_social": row.razon_social,
                "concepto": row.concepto,
                "delegacion": row.delegacion,
                "cantidad_solicitada": row.cantidad_solicitada,
                "cantidad_generada": row.cantidad_generada,
                "estado": row.estado
            })
        return res
    def get_solicitudes_facturacion(self, usuario_id: int, ver_facturadas: bool = False) -> List[dict]:
        """Fetch only solicitudes assigned to a specific user for billing."""
        from sqlalchemy import text
        query_str = """
            SELECT s.solicitud_id, s.grupo_id, o.folio, rfc.rfc, rfc.razon_social, 
                   c.alias as concepto, d.nombre as delegacion, 
                   s.cantidad_solicitada,
                   COALESCE((
                       SELECT COUNT(*)
                       FROM sar_produccion.referencia r
                       JOIN sar_catalogo.estado_sistema es_ref ON r.estado_id = es_ref.estado_id
                       WHERE r.solicitud_id = s.solicitud_id AND es_ref.codigo = 'AUTORIZADA'
                   ), 0) AS cantidad_autorizada,
                   COALESCE((
                       SELECT COUNT(*)
                       FROM sar_produccion.referencia r
                       JOIN sar_catalogo.estado_sistema es_ref ON r.estado_id = es_ref.estado_id
                       WHERE r.solicitud_id = s.solicitud_id AND es_ref.codigo = 'FACTURADA'
                   ), 0) AS cantidad_facturada,
                   es.codigo as estado
            FROM sar_produccion.solicitud s
            JOIN sar_produccion.grupo_referencia gr ON s.grupo_id = gr.grupo_id
            JOIN sar_produccion.orden_generacion o ON gr.orden_id = o.orden_id
            JOIN sar_catalogo.rfc rfc ON gr.rfc_id = rfc.rfc_id
            JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
            JOIN sar_catalogo.delegacion d ON s.delegacion_id = d.delegacion_id
            JOIN sar_catalogo.estado_sistema es ON s.estado_id = es.estado_id
            WHERE s.usuario_asignado = :usuario_id
        """
        if ver_facturadas:
            query_str += " AND es.codigo IN ('AUTORIZADA', 'AUTORIZACION_PARCIAL', 'FACTURADA', 'FACTURADA_PARCIAL', 'ERROR_VALIDACION', 'ERROR', 'PROCESANDO')"
        else:
            query_str += " AND es.codigo IN ('AUTORIZADA', 'AUTORIZACION_PARCIAL', 'FACTURADA_PARCIAL', 'ERROR_VALIDACION', 'ERROR', 'PROCESANDO')"
            
        query_str += " ORDER BY s.solicitud_id ASC"
        
        stmt = text(query_str)
        result = self.session.execute(stmt, {"usuario_id": usuario_id})
        res = []
        for row in result:
            res.append({
                "solicitud_id": row.solicitud_id,
                "grupo_id": row.grupo_id,
                "folio": row.folio,
                "rfc": row.rfc,
                "razon_social": row.razon_social,
                "concepto": row.concepto,
                "delegacion": row.delegacion,
                "cantidad_solicitada": row.cantidad_solicitada,
                "cantidad_autorizada": row.cantidad_autorizada,
                "cantidad_facturada": row.cantidad_facturada,
                "estado": row.estado
            })
        return res

    def get_solicitud_bot_context(self, solicitud_id: int) -> dict:
        """Fetches the deep context needed for the Bot to process a Solicitud.
        
        NOTA DE DISEÑO: El campo `ultimo_consecutivo` en la tabla solicitud es propiedad
        de Face A (Generación de Referencias en Tributanet). Cuando Face A termina,
        este valor queda igual a `consecutivo_fin`. Face C (Facturación) NO debe usar
        `ultimo_consecutivo` como indicador de progreso propio; en su lugar se usa
        `facturas_procesadas`, que cuenta las facturas reales registradas en sar_archivo.factura.
        """
        from sqlalchemy import text
        stmt = text("""
            SELECT 
                s.solicitud_id, s.consecutivo_inicio, s.consecutivo_fin, s.ultimo_consecutivo,
                s.grupo_id,
                rfc.rfc, rfc.razon_social, rfc.calle, rfc.codigo_postal, rfc.municipio as rfc_municipio,
                rfc.colonia, rfc.no_exterior, rfc.no_interior, rfc.localidad, rfc.estado as rfc_estado,
                m.codigo_portal as municipio_codigo_portal, m.nombre as municipio_nombre,
                c.nombre as concepto_nombre, c.alias as concepto_alias, c.codigo_portal as concepto_codigo_portal,
                d.nombre as delegacion_nombre,
                o.folio as orden_folio,
                -- Conteo real de referencias ya timbradas por Face C (fuente de verdad para reanudación)
                COALESCE((
                    SELECT COUNT(DISTINCT f.factura_id)
                    FROM sar_produccion.referencia r
                    JOIN sar_archivo.factura f ON f.referencia_id = r.referencia_id
                    WHERE r.solicitud_id = s.solicitud_id
                ), 0) AS facturas_procesadas,
                -- Conteo de referencias con error para predictibilidad visual en UI
                COALESCE((
                    SELECT COUNT(r.referencia_id)
                    FROM sar_produccion.referencia r
                    JOIN sar_catalogo.estado_sistema es ON r.estado_id = es.estado_id
                    WHERE r.solicitud_id = s.solicitud_id AND es.codigo IN ('ERROR', 'ERROR_VALIDACION')
                ), 0) AS referencias_con_error
            FROM sar_produccion.solicitud s
            JOIN sar_produccion.grupo_referencia gr ON s.grupo_id = gr.grupo_id
            JOIN sar_produccion.orden_generacion o ON gr.orden_id = o.orden_id
            JOIN sar_catalogo.municipio m ON o.municipio_id = m.municipio_id
            JOIN sar_catalogo.rfc rfc ON gr.rfc_id = rfc.rfc_id
            JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
            JOIN sar_catalogo.delegacion d ON s.delegacion_id = d.delegacion_id
            WHERE s.solicitud_id = :solicitud_id
        """)
        row = self.session.execute(stmt, {"solicitud_id": solicitud_id}).fetchone()
        if not row:
            raise ValueError(f"Solicitud {solicitud_id} no encontrada o sin datos asociados.")
        return {
            "solicitud_id": row.solicitud_id,
            "grupo_id": row.grupo_id,
            "consecutivo_inicio": row.consecutivo_inicio,
            "consecutivo_fin": row.consecutivo_fin,
            "ultimo_consecutivo": row.ultimo_consecutivo,
            "facturas_procesadas": row.facturas_procesadas,
            "referencias_con_error": row.referencias_con_error,
            "rfc": row.rfc,
            "razon_social": row.razon_social,
            "calle": row.calle,
            "codigo_postal": row.codigo_postal,
            "rfc_municipio": row.rfc_municipio or "",
            "rfc_estado": row.rfc_estado or "",
            "municipio_nombre": row.municipio_nombre,
            "municipio_codigo_portal": row.municipio_codigo_portal,
            "no_exterior": row.no_exterior or "",
            "no_interior": row.no_interior or "",
            "colonia": row.colonia or "",
            "localidad": row.localidad or "",
            "codigo_postal": row.codigo_postal,
            "municipio": row.municipio_codigo_portal,  # Maps directly to the code (e.g. '02') for the portal drop-down
            "concepto_nombre": row.concepto_nombre,
            "concepto_alias": row.concepto_alias or "UNK",
            "concepto_codigo_portal": row.concepto_codigo_portal,
            "delegacion_nombre": row.delegacion_nombre,
            "orden_folio": row.orden_folio
        }

class ProduccionRepository(BaseRepository):
    def _get_estado_id(self, entidad: str, codigo: str) -> int:
        from sqlalchemy import select, and_
        estado = self.session.execute(
            select(EstadoSistema).where(
                and_(EstadoSistema.entidad == entidad, EstadoSistema.codigo == codigo)
            )
        ).scalars().first()
        if not estado:
            raise ValueError(f"Estado no encontrado: {entidad} -> {codigo}")
        return estado.estado_id

    def get_referencias(self, limit: int = 500) -> List[dict]:
        from sqlalchemy import text
        stmt = text("SELECT * FROM sar_produccion.vw_referencias_detalle ORDER BY folio_orden ASC, grupo_id ASC LIMIT :lim")
        result = self.session.execute(stmt, {"lim": limit})
        res = []
        for row in result:
            res.append({
                "referencia_id": row.referencia_id,
                "referencia_portal": row.referencia_portal,
                "importe": str(row.importe) if row.importe else "",
                "consecutivo_grupo": row.consecutivo_grupo,
                "fecha_generacion": row.fecha_generacion.strftime("%Y-%m-%d"),
                "fecha_vigencia": row.fecha_vigencia.strftime("%Y-%m-%d") if row.fecha_vigencia else "",
                "estado": row.estado_codigo,
                "folio_orden": row.folio_orden,
                "grupo_id": row.grupo_id,
                "empresa": row.rfc_razon_social,
                "concepto": row.concepto_nombre,
                "delegacion": row.delegacion_nombre or "Sin Delegación",
                "procesado_por": row.usuario_asignado_nombre or "Sin Asignar"
            })
        return res

    def get_referencias_paginated(self, limit: int = 200, offset: int = 0, search_text: str = "", estado_filter: str = "Todos", orden_ids: list = None) -> tuple:
        """
        Returns a paginated list of references and the total count matching the filters.
        """
        from sqlalchemy import text
        
        # Build base WHERE clause
        conditions = []
        params = {"lim": limit, "off": offset}
        
        if orden_ids:
            conditions.append("grupo_id IN (SELECT g_ref.grupo_id FROM sar_produccion.grupo_referencia g_ref WHERE g_ref.orden_id IN :orden_ids_param)")
            params["orden_ids_param"] = tuple(orden_ids)
            
        if estado_filter and estado_filter != "Todos":
            conditions.append("estado_codigo = :estado")
            params["estado"] = estado_filter
            
        if search_text:
            if search_text.isdigit():
                search_conds = [
                    "referencia_id = :search_int",
                    "consecutivo_grupo = :search_int",
                    "referencia_portal ILIKE :search"
                ]
                params["search_int"] = int(search_text)
            else:
                search_conds = [
                    "referencia_portal ILIKE :search",
                    "folio_orden ILIKE :search",
                    "rfc_razon_social ILIKE :search",
                    "concepto_nombre ILIKE :search",
                    "delegacion_nombre ILIKE :search",
                    "estado_codigo ILIKE :search",
                    "usuario_asignado_nombre ILIKE :search"
                ]
            conditions.append(f"({' OR '.join(search_conds)})")
            params["search"] = f"%{search_text}%"
            
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        # Query total count
        count_stmt = text(f"SELECT COUNT(*) FROM sar_produccion.vw_referencias_detalle {where_clause}")
        total_count = self.session.execute(count_stmt, params).scalar()
        
        # Query page records
        query_stmt = text(f"""
            SELECT * FROM sar_produccion.vw_referencias_detalle 
            {where_clause} 
            ORDER BY fecha_generacion DESC, referencia_id DESC
            LIMIT :lim OFFSET :off
        """)
        result = self.session.execute(query_stmt, params)
        
        res = []
        for row in result:
            res.append({
                "referencia_id": row.referencia_id,
                "referencia_portal": row.referencia_portal,
                "importe": str(row.importe) if row.importe else "",
                "consecutivo_grupo": row.consecutivo_grupo,
                "fecha_generacion": row.fecha_generacion.strftime("%Y-%m-%d") if row.fecha_generacion else "",
                "fecha_vigencia": row.fecha_vigencia.strftime("%Y-%m-%d") if row.fecha_vigencia else "",
                "estado": row.estado_codigo,
                "folio_orden": row.folio_orden,
                "grupo_id": row.grupo_id,
                "empresa": row.rfc_razon_social,
                "concepto": row.concepto_nombre,
                "delegacion": row.delegacion_nombre or "Sin Delegación",
                "procesado_por": row.usuario_asignado_nombre or "Sin Asignar"
            })
        return res, total_count
        
    def get_ordenes(self) -> List[dict]:
        from sqlalchemy import text
        stmt = text("""
            SELECT 
                r.*, 
                es.codigo AS estado_codigo
            FROM sar_produccion.vw_ordenes_resumen r
            JOIN sar_produccion.orden_generacion o ON r.orden_id = o.orden_id
            JOIN sar_catalogo.estado_sistema es ON o.estado_id = es.estado_id
            ORDER BY r.fecha_creacion DESC
        """)
        result = self.session.execute(stmt)
        res = []
        for row in result:
            res.append({
                "orden_id": row.orden_id,
                "folio": row.folio,
                "descripcion": row.descripcion,
                "fecha_creacion": row.fecha_creacion.strftime("%Y-%m-%d %H:%M"),
                "creador": row.creador,
                "total_solicitadas": row.total_solicitadas,
                "total_generadas": row.total_generadas,
                "estado": row.estado_codigo
            })
        return res

    def _get_or_create_estado_id(self, entidad: str, codigo: str) -> int:
        from sqlalchemy import select, and_
        estado = self.session.execute(
            select(EstadoSistema).where(
                and_(EstadoSistema.entidad == entidad, EstadoSistema.codigo == codigo)
            )
        ).scalars().first()
        if not estado:
            estado = EstadoSistema(entidad=entidad, codigo=codigo, descripcion=f"Estado {codigo} de {entidad}")
            self.session.add(estado)
            self.session.flush()
        return estado.estado_id

    def get_orden_estado(self, orden_id: int) -> str:
        from sqlalchemy import text
        stmt = text("""
            SELECT es.codigo 
            FROM sar_produccion.orden_generacion o
            JOIN sar_catalogo.estado_sistema es ON o.estado_id = es.estado_id
            WHERE o.orden_id = :orden_id
        """)
        res = self.session.execute(stmt, {"orden_id": orden_id}).scalar()
        return res if res else ""

    def get_solicitudes_detalle_by_orden(self, orden_id: int) -> List[dict]:
        from sqlalchemy import text
        stmt = text("""
            SELECT 
                s.solicitud_id,
                o.folio as folio_orden,
                rfc.razon_social as empresa_nombre,
                c.nombre as concepto_nombre,
                d.nombre as delegacion_nombre,
                s.cantidad_solicitada,
                s.cantidad_generada,
                es.codigo as solicitud_estado_codigo,
                COALESCE((SELECT COUNT(*) FROM sar_produccion.referencia r JOIN sar_catalogo.estado_sistema esr ON r.estado_id = esr.estado_id WHERE r.solicitud_id = s.solicitud_id AND esr.codigo = 'PENDIENTE_AUTORIZACION'), 0) as count_pendiente,
                COALESCE((SELECT COUNT(*) FROM sar_produccion.referencia r JOIN sar_catalogo.estado_sistema esr ON r.estado_id = esr.estado_id WHERE r.solicitud_id = s.solicitud_id AND esr.codigo = 'AUTORIZADA'), 0) as count_autorizada,
                COALESCE((SELECT COUNT(*) FROM sar_produccion.referencia r JOIN sar_catalogo.estado_sistema esr ON r.estado_id = esr.estado_id WHERE r.solicitud_id = s.solicitud_id AND esr.codigo = 'RECHAZADA'), 0) as count_rechazada,
                COALESCE((SELECT COUNT(*) FROM sar_produccion.referencia r JOIN sar_catalogo.estado_sistema esr ON r.estado_id = esr.estado_id WHERE r.solicitud_id = s.solicitud_id AND esr.codigo = 'FACTURADA'), 0) as count_facturada
            FROM sar_produccion.solicitud s
            JOIN sar_produccion.grupo_referencia gr ON s.grupo_id = gr.grupo_id
            JOIN sar_produccion.orden_generacion o ON gr.orden_id = o.orden_id
            JOIN sar_catalogo.rfc rfc ON gr.rfc_id = rfc.rfc_id
            JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
            JOIN sar_catalogo.delegacion d ON s.delegacion_id = d.delegacion_id
            JOIN sar_catalogo.estado_sistema es ON s.estado_id = es.estado_id
            WHERE o.orden_id = :orden_id
            ORDER BY s.solicitud_id ASC
        """)
        
        result = self.session.execute(stmt, {"orden_id": orden_id})
        res = []
        for row in result:
            if row.solicitud_estado_codigo == "COMPLETADA":
                if row.count_pendiente > 0:
                    estado_visual = "PENDIENTE_AUTORIZACION"
                elif row.count_autorizada > 0 and row.count_pendiente == 0:
                    estado_visual = "AUTORIZADA"
                elif row.count_rechazada > 0 and row.count_pendiente == 0:
                    estado_visual = "RECHAZADA"
                else:
                    estado_visual = "COMPLETADA"
            else:
                estado_visual = row.solicitud_estado_codigo
                
            res.append({
                "solicitud_id": row.solicitud_id,
                "folio_orden": row.folio_orden,
                "empresa": row.empresa_nombre,
                "concepto": row.concepto_nombre,
                "delegacion": row.delegacion_nombre,
                "cantidad_solicitada": row.cantidad_solicitada,
                "cantidad_generada": row.cantidad_generada,
                "estado": estado_visual,
                "count_pendiente": row.count_pendiente,
                "count_autorizada": row.count_autorizada,
                "count_rechazada": row.count_rechazada,
                "count_facturada": row.count_facturada
            })
        return res

    def procesar_estado_solicitudes_seleccionadas(self, solicitud_ids: List[int], nuevo_estado: str) -> dict:
        from sqlalchemy import text
        from sar.src.storage.models import OrdenGeneracion
        
        new_state_id = self._get_or_create_estado_id("referencia", nuevo_estado)
        pending_state_id = self._get_or_create_estado_id("referencia", "PENDIENTE_AUTORIZACION")
        
        upd_stmt = text("""
            UPDATE sar_produccion.referencia
            SET estado_id = :new_state_id
            WHERE solicitud_id IN :sol_ids AND estado_id = :pending_state_id
        """)
        result = self.session.execute(upd_stmt, {
            "new_state_id": new_state_id,
            "sol_ids": tuple(solicitud_ids),
            "pending_state_id": pending_state_id
        })
        rows_updated = result.rowcount
        self.session.flush()
        
        if solicitud_ids:
            # Actualizar el estado físico de las solicitudes mismas
            sol_state_id = self._get_or_create_estado_id("solicitud", nuevo_estado)
            upd_sol_stmt = text("""
                UPDATE sar_produccion.solicitud
                SET estado_id = :sol_state_id
                WHERE solicitud_id IN :sol_ids
            """)
            self.session.execute(upd_sol_stmt, {"sol_state_id": sol_state_id, "sol_ids": tuple(solicitud_ids)})
            self.session.flush()

            grp_stmt = text("""
                SELECT DISTINCT s.grupo_id, gr.orden_id 
                FROM sar_produccion.solicitud s
                JOIN sar_produccion.grupo_referencia gr ON s.grupo_id = gr.grupo_id
                WHERE s.solicitud_id IN :sol_ids
            """)
            affected = self.session.execute(grp_stmt, {"sol_ids": tuple(solicitud_ids)}).fetchall()
            
            for grp_id, ord_id in affected:
                # Actualizar el estado físico del grupo si todas sus solicitudes están resueltas
                check_grp_stmt = text("""
                    SELECT 
                        COALESCE(SUM(CASE WHEN es.codigo = 'AUTORIZADA' THEN 1 ELSE 0 END), 0) as aut,
                        COALESCE(SUM(CASE WHEN es.codigo = 'RECHAZADA' THEN 1 ELSE 0 END), 0) as rech,
                        COUNT(*) as total
                    FROM sar_produccion.solicitud s
                    JOIN sar_catalogo.estado_sistema es ON s.estado_id = es.estado_id
                    WHERE s.grupo_id = :grp_id
                """)
                grp_counts = self.session.execute(check_grp_stmt, {"grp_id": grp_id}).fetchone()
                if grp_counts and grp_counts.total > 0:
                    from sar.src.storage.models import GrupoReferencia
                    grupo = self.session.get(GrupoReferencia, grp_id)
                    if grupo:
                        if grp_counts.aut == grp_counts.total:
                            grupo.estado_id = self._get_or_create_estado_id("grupo_referencia", "AUTORIZADA")
                        elif grp_counts.rech == grp_counts.total:
                            grupo.estado_id = self._get_or_create_estado_id("grupo_referencia", "RECHAZADA")
                        elif grp_counts.aut + grp_counts.rech == grp_counts.total:
                            grupo.estado_id = self._get_or_create_estado_id("grupo_referencia", "AUTORIZADA")
                    self.session.flush()

                # Actualizar el estado de la orden
                check_ord_ref_stmt = text("""
                    SELECT 
                        COALESCE(SUM(CASE WHEN es.codigo = 'PENDIENTE_AUTORIZACION' THEN 1 ELSE 0 END), 0) as pdte,
                        COALESCE(SUM(CASE WHEN es.codigo = 'AUTORIZADA' THEN 1 ELSE 0 END), 0) as aut,
                        COALESCE(SUM(CASE WHEN es.codigo = 'RECHAZADA' THEN 1 ELSE 0 END), 0) as rech,
                        COUNT(*) as total
                    FROM sar_produccion.referencia r
                    JOIN sar_catalogo.estado_sistema es ON r.estado_id = es.estado_id
                    WHERE r.grupo_id IN (SELECT grupo_id FROM sar_produccion.grupo_referencia WHERE orden_id = :orden_id)
                """)
                counts = self.session.execute(check_ord_ref_stmt, {"orden_id": ord_id}).fetchone()
                
                if counts and counts.total > 0:
                    orden = self.session.get(OrdenGeneracion, ord_id)
                    if orden:
                        if counts.pdte == 0:
                            if counts.aut == counts.total:
                                orden.estado_id = self._get_or_create_estado_id("orden_generacion", "AUTORIZADA")
                            elif counts.rech == counts.total:
                                orden.estado_id = self._get_or_create_estado_id("orden_generacion", "RECHAZADA")
                            else:
                                if counts.aut > 0 and counts.aut + counts.rech == counts.total:
                                    orden.estado_id = self._get_or_create_estado_id("orden_generacion", "AUTORIZADA")
                            self.session.flush()
        
        return {"rows_updated": rows_updated}

    def cancelar_orden_transaccional(self, orden_id: int, usuario_id: int = None, sesion_id: int = None) -> dict:
        from sqlalchemy import text
        from sar.src.storage.models import OrdenGeneracion
        
        # 1. Verificar si existen referencias asociadas a la orden
        check_stmt = text("""
            SELECT COUNT(*) FROM sar_produccion.referencia r
            JOIN sar_produccion.grupo_referencia gr ON r.grupo_id = gr.grupo_id
            WHERE gr.orden_id = :orden_id
        """)
        ref_count = self.session.execute(check_stmt, {"orden_id": orden_id}).scalar()
        if ref_count and ref_count > 0:
            raise ValueError("No se puede cancelar una orden que ya tiene referencias generadas.")
            
        ord_cancel_id = self._get_or_create_estado_id("orden_generacion", "CANCELADA")
        grp_cancel_id = self._get_or_create_estado_id("grupo_referencia", "CANCELADO")
        sol_cancel_id = self._get_or_create_estado_id("solicitud", "CANCELADA")
        
        # 3. Cancelar solicitudes asociadas
        upd_sol_stmt = text("""
            UPDATE sar_produccion.solicitud
            SET estado_id = :state_id
            WHERE grupo_id IN (
                SELECT grupo_id FROM sar_produccion.grupo_referencia WHERE orden_id = :orden_id
            )
        """)
        self.session.execute(upd_sol_stmt, {"state_id": sol_cancel_id, "orden_id": orden_id})
        
        # 4. Cancelar grupos asociados
        upd_grp_stmt = text("""
            UPDATE sar_produccion.grupo_referencia
            SET estado_id = :state_id
            WHERE orden_id = :orden_id
        """)
        self.session.execute(upd_grp_stmt, {"state_id": grp_cancel_id, "orden_id": orden_id})
        
        # 5. Cancelar la orden principal
        orden = self.session.get(OrdenGeneracion, orden_id)
        if orden:
            orden.estado_id = ord_cancel_id
            
        self.session.flush()

        # Registro de Auditoría
        try:
            from sar.src.storage.models import EventoSistema, AuditoriaEvento
            import datetime
            stmt_ev = select(EventoSistema.evento_id).where(EventoSistema.codigo == 'MODIFICAR_CATALOGO')
            evento_id = self.session.execute(stmt_ev).scalar() or 1
            
            log = AuditoriaEvento(
                evento_id=evento_id,
                usuario_id=usuario_id,
                sesion_id=sesion_id,
                fecha=datetime.datetime.now(datetime.timezone.utc),
                modulo="CTRL_REF",
                detalle={"orden_id": orden_id, "action": "cancelar_orden_transaccional", "status": "CANCELADA"}
            )
            self.session.add(log)
            self.session.flush()
        except Exception as e:
            print("Error logging audit event for cancel_orden:", e)

        return {"success": True}

    def check_orden_ready_for_masivo(self, orden_id: int) -> dict:
        from sqlalchemy import text
        
        # 1. Validar si la orden está cancelada
        stmt_est = text("""
            SELECT es.codigo 
            FROM sar_produccion.orden_generacion o
            JOIN sar_catalogo.estado_sistema es ON o.estado_id = es.estado_id
            WHERE o.orden_id = :orden_id
        """)
        est_cod = self.session.execute(stmt_est, {"orden_id": orden_id}).scalar()
        if est_cod == "CANCELADA":
            return {"ready": False, "reason": "No se puede autorizar o rechazar una orden cancelada."}

        # 2. Obtener la cantidad de referencias solicitadas en total para la orden
        stmt_sol = text("""
            SELECT COALESCE(SUM(s.cantidad_solicitada), 0)
            FROM sar_produccion.solicitud s
            JOIN sar_produccion.grupo_referencia gr ON s.grupo_id = gr.grupo_id
            WHERE gr.orden_id = :orden_id
        """)
        total_solicitadas = self.session.execute(stmt_sol, {"orden_id": orden_id}).scalar()
        
        # 3. Obtener la cantidad de referencias actualmente en estado PENDIENTE_AUTORIZACION
        stmt_pdte = text("""
            SELECT COUNT(*) 
            FROM sar_produccion.referencia r
            JOIN sar_catalogo.estado_sistema es ON r.estado_id = es.estado_id
            WHERE r.grupo_id IN (SELECT grupo_id FROM sar_produccion.grupo_referencia WHERE orden_id = :orden_id)
              AND es.codigo = 'PENDIENTE_AUTORIZACION'
        """)
        total_pendientes = self.session.execute(stmt_pdte, {"orden_id": orden_id}).scalar()
        
        if total_solicitadas == 0:
            return {"ready": False, "reason": "La orden no tiene solicitudes registradas."}
            
        if total_pendientes != total_solicitadas:
            return {
                "ready": False,
                "reason": (
                    f"No todas las referencias están listas para autorizar de forma masiva.\n\n"
                    f"- Referencias Solicitadas: {total_solicitadas}\n"
                    f"- Referencias Pendientes de Autorización: {total_pendientes}"
                )
            }
            
        return {"ready": True, "total_referencias": total_solicitadas}

    def update_orden_estado_masivo(self, orden_id: int, nuevo_estado_codigo: str, usuario_id: int = None, sesion_id: int = None):
        from sqlalchemy import text
        from sar.src.storage.models import OrdenGeneracion

        # 1. Obtener la cantidad de referencias solicitadas en total para la orden
        stmt_sol = text("""
            SELECT COALESCE(SUM(s.cantidad_solicitada), 0)
            FROM sar_produccion.solicitud s
            JOIN sar_produccion.grupo_referencia gr ON s.grupo_id = gr.grupo_id
            WHERE gr.orden_id = :orden_id
        """)
        total_solicitadas = self.session.execute(stmt_sol, {"orden_id": orden_id}).scalar()
        
        # 2. Obtener la cantidad de referencias actualmente en estado PENDIENTE_AUTORIZACION
        stmt_pdte = text("""
            SELECT COUNT(*) 
            FROM sar_produccion.referencia r
            JOIN sar_catalogo.estado_sistema es ON r.estado_id = es.estado_id
            WHERE r.grupo_id IN (SELECT grupo_id FROM sar_produccion.grupo_referencia WHERE orden_id = :orden_id)
              AND es.codigo = 'PENDIENTE_AUTORIZACION'
        """)
        total_pendientes = self.session.execute(stmt_pdte, {"orden_id": orden_id}).scalar()
        
        if total_solicitadas == 0:
            raise ValueError("La orden no tiene solicitudes registradas.")
            
        if total_pendientes != total_solicitadas:
            raise ValueError(
                f"No se puede procesar la orden completa de forma masiva porque no todas las referencias están listas para autorizar.\n\n"
                f"- Referencias Solicitadas: {total_solicitadas}\n"
                f"- Referencias Pendientes de Autorización: {total_pendientes}\n\n"
                "Para autorizaciones parciales, por favor use el módulo individual dando doble clic sobre la orden."
            )

        # 3. Validar si la orden está cancelada
        stmt_est = text("""
            SELECT es.codigo 
            FROM sar_produccion.orden_generacion o
            JOIN sar_catalogo.estado_sistema es ON o.estado_id = es.estado_id
            WHERE o.orden_id = :orden_id
        """)
        est_cod = self.session.execute(stmt_est, {"orden_id": orden_id}).scalar()
        if est_cod == "CANCELADA":
            raise ValueError("No se puede autorizar o rechazar una orden cancelada.")

        # 4. Actualizar todas las referencias de la orden al nuevo estado
        estado_id = self._get_estado_id("referencia", nuevo_estado_codigo)
        stmt_upd = text("""
            UPDATE sar_produccion.referencia 
            SET estado_id = :estado_id 
            WHERE grupo_id IN (
                SELECT grupo_id FROM sar_produccion.grupo_referencia WHERE orden_id = :orden_id
            )
        """)
        self.session.execute(stmt_upd, {"estado_id": estado_id, "orden_id": orden_id})
        
        # 4.5. Actualizar todas las solicitudes al nuevo estado en cascada
        sol_estado_codigo = "AUTORIZADA" if nuevo_estado_codigo == "AUTORIZADA" else "CANCELADA"
        sol_estado_id = self._get_or_create_estado_id("solicitud", sol_estado_codigo)
        stmt_sol_upd = text("""
            UPDATE sar_produccion.solicitud
            SET estado_id = :estado_id
            WHERE grupo_id IN (
                SELECT grupo_id FROM sar_produccion.grupo_referencia WHERE orden_id = :orden_id
            )
        """)
        self.session.execute(stmt_sol_upd, {"estado_id": sol_estado_id, "orden_id": orden_id})

        # 4.6. Actualizar todos los grupos de referencia al nuevo estado en cascada
        grp_estado_codigo = "AUTORIZADO" if nuevo_estado_codigo == "AUTORIZADA" else "CANCELADO"
        grp_estado_id = self._get_or_create_estado_id("grupo_referencia", grp_estado_codigo)
        stmt_grp_upd = text("""
            UPDATE sar_produccion.grupo_referencia
            SET estado_id = :estado_id
            WHERE orden_id = :orden_id
        """)
        self.session.execute(stmt_grp_upd, {"estado_id": grp_estado_id, "orden_id": orden_id})
        
        # 5. Actualizar el estado de la orden principal
        orden = self.session.get(OrdenGeneracion, orden_id)
        if orden:
            ord_estado_id = self._get_or_create_estado_id("orden_generacion", nuevo_estado_codigo)
            orden.estado_id = ord_estado_id

        self.session.flush()

        # Registro de Auditoría
        try:
            from sar.src.storage.models import EventoSistema, AuditoriaEvento
            import datetime
            stmt_ev = select(EventoSistema.evento_id).where(EventoSistema.codigo == 'AUTORIZAR_REFERENCIA')
            evento_id = self.session.execute(stmt_ev).scalar() or 1
            
            log = AuditoriaEvento(
                evento_id=evento_id,
                usuario_id=usuario_id,
                sesion_id=sesion_id,
                fecha=datetime.datetime.now(datetime.timezone.utc),
                modulo="CTRL_REF",
                detalle={"orden_id": orden_id, "action": "update_orden_estado_masivo", "status": nuevo_estado_codigo}
            )
            self.session.add(log)
            self.session.flush()
        except Exception as e:
            print("Error logging audit event for update_orden_masivo:", e)

    def update_referencia_estado(self, referencia_id: int, nuevo_estado_codigo: str):
        ref = self.session.get(Referencia, referencia_id)
        if ref:
            ref.estado_id = self._get_estado_id("referencia", nuevo_estado_codigo)
            self.session.flush()

    def update_referencias_estado_masivo(self, referencia_ids: List[int], nuevo_estado_codigo: str, rechazar_restantes: bool = False):
        from sqlalchemy import text
        from sar.src.storage.models import Referencia, Solicitud, GrupoReferencia, OrdenGeneracion
        
        estado_id = self._get_estado_id("referencia", nuevo_estado_codigo)
        pending_id = self._get_estado_id("referencia", "PENDIENTE_AUTORIZACION")
        rechazada_id = self._get_estado_id("referencia", "RECHAZADA")
        
        # 1. Validar que todas las referencias seleccionadas estén en PENDIENTE_AUTORIZACION
        stmt_check = text("""
            SELECT COUNT(*) FROM sar_produccion.referencia r
            JOIN sar_catalogo.estado_sistema es ON r.estado_id = es.estado_id
            WHERE r.referencia_id IN :ref_ids AND es.codigo != 'PENDIENTE_AUTORIZACION'
        """)
        not_pending = self.session.execute(stmt_check, {"ref_ids": tuple(referencia_ids)}).scalar()
        if not_pending and not_pending > 0:
            raise ValueError("Solo se pueden procesar referencias que estén en estado PENDIENTE_AUTORIZACION.")
            
        # 2. Obtener las solicitudes vinculadas
        stmt_sols = text("""
            SELECT DISTINCT solicitud_id FROM sar_produccion.referencia
            WHERE referencia_id IN :ref_ids
        """)
        sol_rows = self.session.execute(stmt_sols, {"ref_ids": tuple(referencia_ids)}).fetchall()
        sol_ids = [r[0] for r in sol_rows if r[0]]
        
        # 3. Si se solicita rechazar las restantes
        if rechazar_restantes and sol_ids:
            stmt_restantes = text("""
                UPDATE sar_produccion.referencia
                SET estado_id = :rechazada_id
                WHERE solicitud_id IN :sol_ids 
                  AND referencia_id NOT IN :selected_ids 
                  AND estado_id = :pending_id
            """)
            self.session.execute(stmt_restantes, {
                "rechazada_id": rechazada_id,
                "sol_ids": tuple(sol_ids),
                "selected_ids": tuple(referencia_ids),
                "pending_id": pending_id
            })
            
        # 4. Actualizar las referencias seleccionadas
        for ref_id in referencia_ids:
            ref = self.session.get(Referencia, ref_id)
            if ref:
                ref.estado_id = estado_id
                
        self.session.flush()
        
        # 5. Recalcular estados de solicitudes, grupos y órdenes vinculadas
        if sol_ids:
            for sol_id in sol_ids:
                stmt_counts = text("""
                    SELECT 
                        COALESCE(SUM(CASE WHEN es.codigo = 'AUTORIZADA' THEN 1 ELSE 0 END), 0) as aut,
                        COALESCE(SUM(CASE WHEN es.codigo = 'RECHAZADA' THEN 1 ELSE 0 END), 0) as rech,
                        COALESCE(SUM(CASE WHEN es.codigo = 'PENDIENTE_AUTORIZACION' THEN 1 ELSE 0 END), 0) as pdte,
                        COUNT(*) as total
                    FROM sar_produccion.referencia r
                    JOIN sar_catalogo.estado_sistema es ON r.estado_id = es.estado_id
                    WHERE r.solicitud_id = :sol_id
                """)
                counts = self.session.execute(stmt_counts, {"sol_id": sol_id}).fetchone()
                if counts and counts.total > 0:
                    solicitud = self.session.get(Solicitud, sol_id)
                    if solicitud:
                        if counts.pdte > 0:
                            pass
                        elif counts.aut == counts.total:
                            solicitud.estado_id = self._get_or_create_estado_id("solicitud", "AUTORIZADA")
                        elif counts.rech == counts.total:
                            solicitud.estado_id = self._get_or_create_estado_id("solicitud", "RECHAZADA")
                        else:
                            solicitud.estado_id = self._get_or_create_estado_id("solicitud", "AUTORIZACION_PARCIAL")
                            
            stmt_grps = text("""
                SELECT DISTINCT s.grupo_id, gr.orden_id 
                FROM sar_produccion.solicitud s
                JOIN sar_produccion.grupo_referencia gr ON s.grupo_id = gr.grupo_id
                WHERE s.solicitud_id IN :sol_ids
            """)
            affected = self.session.execute(stmt_grps, {"sol_ids": tuple(sol_ids)}).fetchall()
            
            for grp_id, ord_id in affected:
                check_grp_stmt = text("""
                    SELECT 
                        COALESCE(SUM(CASE WHEN es.codigo = 'AUTORIZADA' THEN 1 ELSE 0 END), 0) as aut,
                        COALESCE(SUM(CASE WHEN es.codigo = 'RECHAZADA' THEN 1 ELSE 0 END), 0) as rech,
                        COALESCE(SUM(CASE WHEN es.codigo = 'AUTORIZACION_PARCIAL' THEN 1 ELSE 0 END), 0) as part,
                        COUNT(*) as total
                    FROM sar_produccion.solicitud s
                    JOIN sar_catalogo.estado_sistema es ON s.estado_id = es.estado_id
                    WHERE s.grupo_id = :grp_id
                """)
                grp_counts = self.session.execute(check_grp_stmt, {"grp_id": grp_id}).fetchone()
                if grp_counts and grp_counts.total > 0:
                    grupo = self.session.get(GrupoReferencia, grp_id)
                    if grupo:
                        if grp_counts.aut == grp_counts.total:
                            grupo.estado_id = self._get_or_create_estado_id("grupo_referencia", "AUTORIZADA")
                        elif grp_counts.rech == grp_counts.total:
                            grupo.estado_id = self._get_or_create_estado_id("grupo_referencia", "RECHAZADA")
                        else:
                            grupo.estado_id = self._get_or_create_estado_id("grupo_referencia", "AUTORIZACION_PARCIAL")
                            
                check_ord_ref_stmt = text("""
                    SELECT 
                        COALESCE(SUM(CASE WHEN es.codigo = 'PENDIENTE_AUTORIZACION' THEN 1 ELSE 0 END), 0) as pdte,
                        COALESCE(SUM(CASE WHEN es.codigo = 'AUTORIZADA' THEN 1 ELSE 0 END), 0) as aut,
                        COALESCE(SUM(CASE WHEN es.codigo = 'RECHAZADA' THEN 1 ELSE 0 END), 0) as rech,
                        COUNT(*) as total
                    FROM sar_produccion.referencia r
                    JOIN sar_catalogo.estado_sistema es ON r.estado_id = es.estado_id
                    WHERE r.grupo_id IN (SELECT grupo_id FROM sar_produccion.grupo_referencia WHERE orden_id = :orden_id)
                """)
                counts = self.session.execute(check_ord_ref_stmt, {"orden_id": ord_id}).fetchone()
                if counts and counts.total > 0:
                    orden = self.session.get(OrdenGeneracion, ord_id)
                    if orden:
                        if counts.pdte == 0:
                            if counts.aut == counts.total:
                                orden.estado_id = self._get_or_create_estado_id("orden_generacion", "AUTORIZADA")
                            elif counts.rech == counts.total:
                                orden.estado_id = self._get_or_create_estado_id("orden_generacion", "RECHAZADA")
                            else:
                                if counts.aut > 0 and counts.aut + counts.rech == counts.total:
                                    orden.estado_id = self._get_or_create_estado_id("orden_generacion", "AUTORIZADA")
                                    
        self.session.flush()

    def asignar_referencias(self, referencia_ids: List[int], usuario_id: int) -> bool:
        from sqlalchemy import select
        
        # Obtener o crear estado ASIGNADA
        from sqlalchemy import and_
        estado_asignada = self.session.execute(
            select(EstadoSistema).where(
                and_(EstadoSistema.entidad == 'referencia', EstadoSistema.codigo == 'ASIGNADA')
            )
        ).scalars().first()
        if not estado_asignada:
            estado_asignada = EstadoSistema(entidad='referencia', codigo='ASIGNADA', descripcion='Estado ASIGNADA de referencia')
            self.session.add(estado_asignada)
            self.session.flush()
            
        referencias = self.session.execute(select(Referencia).where(Referencia.referencia_id.in_(referencia_ids))).scalars().all()
        for ref in referencias:
            ref.usuario_asignado = usuario_id
            ref.estado_id = estado_asignada.estado_id
            
        self.session.flush()
        return True

    def get_dashboard_kpis(self, orden_ids: list = None) -> dict:
        from sqlalchemy import select, func
        from sar.src.storage.models import GrupoReferencia
        
        query_total = select(func.count(Referencia.referencia_id))
        if orden_ids:
            query_total = query_total.join(GrupoReferencia).where(GrupoReferencia.orden_id.in_(orden_ids))
            
        total_generadas = self.session.execute(query_total).scalar_one()
        
        try:
            pdte_codes = ["GENERADA", "ASIGNADA", "PENDIENTE", "PENDIENTE_AUTORIZACION"]
            pdte_ids = []
            for code in pdte_codes:
                try:
                    pdte_ids.append(self._get_estado_id("referencia", code))
                except ValueError:
                    pass
                    
            aut_codes = ["AUTORIZADA", "COMPLETA", "COMPLETADA"]
            aut_ids = []
            for code in aut_codes:
                try:
                    aut_ids.append(self._get_estado_id("referencia", code))
                except ValueError:
                    pass
                    
            err_codes = ["ERROR", "FALLIDO"]
            err_ids = []
            for code in err_codes:
                try:
                    err_ids.append(self._get_estado_id("referencia", code))
                except ValueError:
                    pass
            
            rech_codes = ["RECHAZADA"]
            rech_ids = []
            for code in rech_codes:
                try:
                    rech_ids.append(self._get_estado_id("referencia", code))
                except ValueError:
                    pass
            
            invalid_codes = ["ERROR_VALIDACION"]
            invalid_ids = []
            for code in invalid_codes:
                try:
                    invalid_ids.append(self._get_estado_id("referencia", code))
                except ValueError:
                    pass
            
            query_pdte = select(func.count(Referencia.referencia_id)).where(Referencia.estado_id.in_(pdte_ids))
            query_aut = select(func.count(Referencia.referencia_id)).where(Referencia.estado_id.in_(aut_ids))
            query_err = select(func.count(Referencia.referencia_id)).where(Referencia.estado_id.in_(err_ids))
            query_rech = select(func.count(Referencia.referencia_id)).where(Referencia.estado_id.in_(rech_ids))
            query_invalid = select(func.count(Referencia.referencia_id)).where(Referencia.estado_id.in_(invalid_ids)) if invalid_ids else None
            
            if orden_ids:
                query_pdte = query_pdte.join(GrupoReferencia).where(GrupoReferencia.orden_id.in_(orden_ids))
                query_aut = query_aut.join(GrupoReferencia).where(GrupoReferencia.orden_id.in_(orden_ids))
                query_err = query_err.join(GrupoReferencia).where(GrupoReferencia.orden_id.in_(orden_ids))
                query_rech = query_rech.join(GrupoReferencia).where(GrupoReferencia.orden_id.in_(orden_ids))
                if query_invalid is not None:
                    query_invalid = query_invalid.join(GrupoReferencia).where(GrupoReferencia.orden_id.in_(orden_ids))
                
            pendientes = self.session.execute(query_pdte).scalar_one() if pdte_ids else 0
            autorizadas = self.session.execute(query_aut).scalar_one() if aut_ids else 0
            con_error = self.session.execute(query_err).scalar_one() if err_ids else 0
            rechazadas = self.session.execute(query_rech).scalar_one() if rech_ids else 0
            invalidas = self.session.execute(query_invalid).scalar_one() if (query_invalid is not None and invalid_ids) else 0
        except Exception:
            pendientes = 0
            autorizadas = 0
            con_error = 0
            rechazadas = 0
            invalidas = 0
            
        return {
            "total_generadas": total_generadas,
            "pendientes": pendientes,
            "autorizadas": autorizadas,
            "con_error": con_error,
            "rechazadas": rechazadas,
            "invalidas": invalidas
        }

    def get_orden_detalle_edicion(self, orden_id: int) -> dict:
        from sqlalchemy import text
        from sar.src.storage.models import OrdenGeneracion
        
        orden = self.session.get(OrdenGeneracion, orden_id)
        if not orden:
            raise ValueError(f"No se encontró la orden con ID {orden_id}")
            
        estado_codigo = self.get_orden_estado(orden_id)
        
        stmt = text("""
            SELECT 
                gr.rfc_id, 
                gr.concepto_id, 
                s.delegacion_id, 
                SUM(s.cantidad_solicitada) as cantidad,
                COALESCE(SUM(s.cantidad_generada), 0) as cantidad_generada
            FROM sar_produccion.grupo_referencia gr
            JOIN sar_produccion.solicitud s ON gr.grupo_id = s.grupo_id
            WHERE gr.orden_id = :orden_id
            GROUP BY gr.rfc_id, gr.concepto_id, s.delegacion_id
            ORDER BY gr.rfc_id ASC, gr.concepto_id ASC, s.delegacion_id ASC
        """)
        
        result = self.session.execute(stmt, {"orden_id": orden_id})
        renglones = []
        for row in result:
            renglones.append({
                "rfc_id": row.rfc_id,
                "concepto_id": row.concepto_id,
                "delegacion_id": row.delegacion_id,
                "cantidad": int(row.cantidad),
                "cantidad_generada": int(row.cantidad_generada)
            })
            
        # Check if all solicitudes are in state PENDIENTE, ASIGNADA, or COMPLETADA
        stmt_states = text("""
            SELECT es.codigo, COUNT(*)
            FROM sar_produccion.solicitud s
            JOIN sar_produccion.grupo_referencia gr ON s.grupo_id = gr.grupo_id
            JOIN sar_catalogo.estado_sistema es ON s.estado_id = es.estado_id
            WHERE gr.orden_id = :orden_id
            GROUP BY es.codigo
        """)
        states_result = self.session.execute(stmt_states, {"orden_id": orden_id}).fetchall()
        
        # Valid states for editing
        allowed_states = {"PENDIENTE", "ASIGNADA", "COMPLETADA", "COMPLETADO"}
        editable = True
        for state_code, count in states_result:
            if state_code not in allowed_states:
                editable = False
                break
                
        # Also check if order itself is already cancelled
        if estado_codigo == "CANCELADA":
            editable = False
            
        return {
            "orden_id": orden.orden_id,
            "folio": orden.folio,
            "descripcion": orden.descripcion,
            "municipio_id": orden.municipio_id,
            "estado": estado_codigo,
            "editable": editable,
            "renglones": renglones
        }


class InventarioRepository(BaseRepository):
    """Handles persistence operations for notary/collaborator catalogs and assignments."""

    def _get_estado_id(self, entidad: str, codigo: str) -> int:
        from sqlalchemy import select, and_
        from sar.src.storage.models import EstadoSistema
        estado = self.session.execute(
            select(EstadoSistema).where(
                and_(EstadoSistema.entidad == entidad, EstadoSistema.codigo == codigo)
            )
        ).scalars().first()
        if not estado:
            raise ValueError(f"Estado no encontrado: {entidad} -> {codigo}")
        return estado.estado_id

    def get_notarias(self) -> List[dict]:
        from sqlalchemy import select
        from sar.src.storage.models import Notaria
        stmt = select(Notaria).where(Notaria.activo == True).order_by(Notaria.nombre)
        results = self.session.execute(stmt).scalars().all()
        return [{"notaria_id": n.notaria_id, "nombre": n.nombre} for n in results]

    def save_notaria(self, nombre: str) -> dict:
        from sar.src.storage.models import Notaria
        n = Notaria(nombre=nombre.strip().upper(), activo=True)
        self.session.add(n)
        self.session.flush()
        return {"notaria_id": n.notaria_id, "nombre": n.nombre}

    def get_colaboradores(self) -> List[dict]:
        from sqlalchemy import select
        from sar.src.storage.models import Colaborador
        stmt = select(Colaborador).where(Colaborador.activo == True).order_by(Colaborador.nombre)
        results = self.session.execute(stmt).scalars().all()
        return [{"colaborador_id": c.colaborador_id, "nombre": c.nombre} for c in results]

    def save_colaborador(self, nombre: str) -> dict:
        from sar.src.storage.models import Colaborador
        c = Colaborador(nombre=nombre.strip().upper(), activo=True)
        self.session.add(c)
        self.session.flush()
        return {"colaborador_id": c.colaborador_id, "nombre": c.nombre}

    def get_desarrollos(self) -> List[dict]:
        from sqlalchemy import select
        from sar.src.storage.models import Desarrollo, DesarrolloEmpresa, Delegacion
        stmt = (
            select(Desarrollo, DesarrolloEmpresa, Delegacion)
            .join(DesarrolloEmpresa, Desarrollo.desarrollo_id == DesarrolloEmpresa.desarrollo_id)
            .join(Delegacion, DesarrolloEmpresa.delegacion_id == Delegacion.delegacion_id)
            .where(Desarrollo.activo == True, DesarrolloEmpresa.activo == True)
            .order_by(DesarrolloEmpresa.es_default.desc(), Desarrollo.nombre)  # defaults first
        )
        results = self.session.execute(stmt).all()
        # Evitar duplicados: si un desarrollo tiene varias empresas/delegaciones,
        # conservamos el registro marcado como es_default (que viene primero por el ORDER BY).
        seen_ids = set()
        desarrollos_list = []
        for row in results:
            d_obj, de_obj, del_obj = row[0], row[1], row[2]
            if d_obj.desarrollo_id not in seen_ids:
                seen_ids.add(d_obj.desarrollo_id)
                desarrollos_list.append({
                    "desarrollo_id": d_obj.desarrollo_id,
                    "nombre": d_obj.nombre,
                    "delegacion_id": del_obj.delegacion_id,
                    "delegacion_nombre": del_obj.nombre,
                    "es_default": de_obj.es_default,
                })
        return desarrollos_list

    def save_desarrollo(self, nombre: str, delegacion_id: int) -> dict:
        from sar.src.storage.models import Desarrollo
        d = Desarrollo(nombre=nombre.strip().upper(), activo=True)
        self.session.add(d)
        self.session.flush()
        return {"desarrollo_id": d.desarrollo_id, "nombre": d.nombre, "delegacion_id": delegacion_id}

    def get_rfcs_con_stock_facturadas(self) -> List[dict]:
        """Returns active RFCs that have at least one reference in 'FACTURADA' state."""
        from sqlalchemy import text
        stmt = text("""
            SELECT DISTINCT rfc.rfc_id, rfc.razon_social
            FROM sar_catalogo.rfc rfc
            JOIN sar_produccion.grupo_referencia gr ON rfc.rfc_id = gr.rfc_id
            JOIN sar_produccion.referencia r ON gr.grupo_id = r.grupo_id
            JOIN sar_catalogo.estado_sistema es ON r.estado_id = es.estado_id
            WHERE rfc.activo = TRUE
              AND es.entidad = 'referencia'
              AND es.codigo = 'FACTURADA'
              AND r.referencia_id NOT IN (
                  SELECT ar.referencia_id FROM sar_archivo.asignacion_referencia ar
                  WHERE ar.referencia_id IS NOT NULL
              )
            ORDER BY rfc.razon_social
        """)
        results = self.session.execute(stmt).all()
        return [{"rfc_id": row.rfc_id, "razon_social": row.razon_social} for row in results]


    def get_desarrollos_activos_para_apartar(self) -> List[dict]:
        """Returns all active desarrollo_empresa records with their rfc and delegacion data.
        Each record represents a valid (desarrollo, rfc, delegacion) combination.
        Used to populate the Desarrollo combo in the Apartar tab with smart cascade defaults.
        """
        from sqlalchemy import select
        from sar.src.storage.models import Desarrollo, DesarrolloEmpresa, Delegacion, Rfc
        stmt = (
            select(Desarrollo, DesarrolloEmpresa, Delegacion, Rfc)
            .join(DesarrolloEmpresa, Desarrollo.desarrollo_id == DesarrolloEmpresa.desarrollo_id)
            .join(Delegacion, DesarrolloEmpresa.delegacion_id == Delegacion.delegacion_id)
            .join(Rfc, DesarrolloEmpresa.rfc_id == Rfc.rfc_id)
            .where(Desarrollo.activo == True, DesarrolloEmpresa.activo == True)
            .order_by(DesarrolloEmpresa.es_default.desc(), Desarrollo.nombre)
        )
        results = self.session.execute(stmt).all()
        return [
            {
                "desarrollo_id": row[0].desarrollo_id,
                "nombre": row[0].nombre,
                "rfc_id": row[1].rfc_id,
                "delegacion_id": row[1].delegacion_id,
                "es_default": row[1].es_default,
                "rfc_razon_social": row[3].razon_social,
                "delegacion_nombre": row[2].nombre,
            }
            for row in results
        ]

    def get_rfcs_por_desarrollo(self, desarrollo_id: int) -> List[dict]:
        """Returns all RFCs linked to a desarrollo via desarrollo_empresa (active only)."""
        from sqlalchemy import select
        from sar.src.storage.models import DesarrolloEmpresa, Rfc
        stmt = (
            select(Rfc, DesarrolloEmpresa.es_default)
            .join(DesarrolloEmpresa, Rfc.rfc_id == DesarrolloEmpresa.rfc_id)
            .where(
                DesarrolloEmpresa.desarrollo_id == desarrollo_id,
                DesarrolloEmpresa.activo == True
            )
            .order_by(DesarrolloEmpresa.es_default.desc(), Rfc.razon_social)
        )
        results = self.session.execute(stmt).all()
        # Deduplicate by rfc_id, keeping es_default=True info
        seen = set()
        out = []
        for rfc_obj, es_default in results:
            if rfc_obj.rfc_id not in seen:
                seen.add(rfc_obj.rfc_id)
                out.append({
                    "rfc_id": rfc_obj.rfc_id,
                    "razon_social": rfc_obj.razon_social,
                    "es_default": es_default
                })
        return out

    def get_delegaciones_por_desarrollo_rfc(self, desarrollo_id: int, rfc_id: int) -> List[dict]:
        """Returns all delegaciones for a given (desarrollo, rfc) combination (active only)."""
        from sqlalchemy import select
        from sar.src.storage.models import DesarrolloEmpresa, Delegacion
        stmt = (
            select(Delegacion, DesarrolloEmpresa.es_default)
            .join(DesarrolloEmpresa, Delegacion.delegacion_id == DesarrolloEmpresa.delegacion_id)
            .where(
                DesarrolloEmpresa.desarrollo_id == desarrollo_id,
                DesarrolloEmpresa.rfc_id == rfc_id,
                DesarrolloEmpresa.activo == True
            )
            .order_by(DesarrolloEmpresa.es_default.desc(), Delegacion.nombre)
        )
        results = self.session.execute(stmt).all()
        seen = set()
        out = []
        for del_obj, es_default in results:
            if del_obj.delegacion_id not in seen:
                seen.add(del_obj.delegacion_id)
                out.append({
                    "delegacion_id": del_obj.delegacion_id,
                    "nombre": del_obj.nombre,
                    "es_default": es_default
                })
        return out

    def get_conceptos_con_stock(self, rfc_id: int, delegacion_id: int) -> List[dict]:
        """Returns concepts (IDs 2=AVISO, 3=CLG only) that have at least one FACTURADA
        reference available (not yet in asignacion_referencia) for the given rfc + delegacion.
        """
        from sqlalchemy import text
        stmt = text("""
            SELECT DISTINCT c.concepto_id, c.nombre
            FROM sar_produccion.referencia r
            JOIN sar_produccion.grupo_referencia gr ON r.grupo_id = gr.grupo_id
            JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
            JOIN sar_produccion.solicitud s ON r.solicitud_id = s.solicitud_id
            JOIN sar_catalogo.estado_sistema es ON r.estado_id = es.estado_id
            WHERE es.entidad = 'referencia'
              AND es.codigo = 'FACTURADA'
              AND gr.rfc_id = :rfc_id
              AND s.delegacion_id = :delegacion_id
              AND c.concepto_id IN (2, 3)
              AND r.referencia_id NOT IN (
                  SELECT ar.referencia_id FROM sar_archivo.asignacion_referencia ar
                  WHERE ar.referencia_id IS NOT NULL
              )
            ORDER BY c.concepto_id
        """)
        results = self.session.execute(stmt, {"rfc_id": rfc_id, "delegacion_id": delegacion_id}).all()
        return [{"concepto_id": row.concepto_id, "nombre": row.nombre} for row in results]



    def get_referencias_facturadas_paginated(
        self, limit: int = 200, offset: int = 0, search_text: str = "", concepto_id: int = None, rfc_id: int = None, filter_assigned: str = "Todos", start_date: str = None, end_date: str = None, orden_ids: list = None
    ) -> tuple[List[dict], int]:
        from sqlalchemy import text
        
        conditions = []
        params = {"lim": limit, "off": offset}
        
        # Only references in 'FACTURADA' state
        conditions.append("estado_codigo = 'FACTURADA'")
        
        if concepto_id:
            conditions.append("concepto_id = :concepto_id")
            params["concepto_id"] = concepto_id

        if rfc_id:
            params["rfc_id"] = rfc_id
            
        if filter_assigned == "Disponible":
            conditions.append("referencia_id NOT IN (SELECT ld.referencia_id FROM sar_archivo.lote_detalle ld WHERE ld.referencia_id IS NOT NULL)")
        elif filter_assigned == "Asignada":
            conditions.append("referencia_id IN (SELECT ld.referencia_id FROM sar_archivo.lote_detalle ld WHERE ld.referencia_id IS NOT NULL)")

        if search_text:
            search_conds = [
                "referencia_portal ILIKE :search",
                "rfc_razon_social ILIKE :search",
                "concepto_nombre ILIKE :search",
                "delegacion_nombre ILIKE :search",
                "usuario_asignado_nombre ILIKE :search"
            ]
            conditions.append(f"({' OR '.join(search_conds)})")
            params["search"] = f"%{search_text}%"
            
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
            
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        # We need a view or a direct query that has the fields we need.
        # Let's write the query to select the fields from vw_referencias_detalle.
        # We also need concept_id. Wait! Does vw_referencias_detalle have concept_id?
        # Let's check vw_referencias_detalle definition:
        # og.folio AS folio_orden, r.grupo_id, rfc.razon_social AS rfc_razon_social,
        # c.nombre AS concepto_nombre, d.nombre AS delegacion_nombre, ...
        # c.nombre is the concept name. It doesn't have concepto_id, but we can join with grupo_referencia to get it.
        sql_base = """
            FROM sar_produccion.referencia r
            JOIN sar_produccion.grupo_referencia gr ON r.grupo_id = gr.grupo_id
            JOIN sar_produccion.orden_generacion og ON gr.orden_id = og.orden_id
            JOIN sar_catalogo.rfc rfc ON gr.rfc_id = rfc.rfc_id
            JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
            JOIN sar_produccion.solicitud s ON r.solicitud_id = s.solicitud_id
            LEFT JOIN sar_catalogo.delegacion d ON s.delegacion_id = d.delegacion_id
            JOIN sar_catalogo.estado_sistema es ON r.estado_id = es.estado_id
            LEFT JOIN sar_seguridad.usuario u ON r.usuario_asignado = u.usuario_id
            LEFT JOIN sar_archivo.asignacion_referencia ar ON r.referencia_id = ar.referencia_id
            LEFT JOIN sar_archivo.lote_detalle ld ON ar.lote_detalle_id = ld.lote_detalle_id
            LEFT JOIN sar_archivo.lote_asignacion la ON ld.lote_asignacion_id = la.lote_asignacion_id
            LEFT JOIN sar_catalogo.notaria n ON la.notaria_id = n.notaria_id
            LEFT JOIN sar_catalogo.colaborador col ON la.colaborador_id = col.colaborador_id
            LEFT JOIN sar_catalogo.desarrollo des ON ld.desarrollo_id = des.desarrollo_id
            LEFT JOIN sar_archivo.ubicacion ubi ON ar.ubicacion_id = ubi.ubicacion_id
        """
        
        # Modify conditions to use table aliases
        conditions_sql = []
        if filter_assigned == "Disponible":
            conditions_sql.append("es.codigo = 'FACTURADA'")
            conditions_sql.append("ar.referencia_id IS NULL")
        elif filter_assigned == "Asignada":
            conditions_sql.append("es.codigo = 'ASIGNADA'")
        elif filter_assigned == "Reservada":
            conditions_sql.append("es.codigo = 'RESERVADA'")
        elif filter_assigned == "LotesControl":
            conditions_sql.append("es.codigo IN ('ASIGNADA', 'RESERVADA')")
        else: # Todos
            conditions_sql.append("es.codigo IN ('FACTURADA', 'ASIGNADA', 'RESERVADA')")

            
        if concepto_id:
            conditions_sql.append("gr.concepto_id = :concepto_id")
        if rfc_id:
            conditions_sql.append("gr.rfc_id = :rfc_id")
            
        if start_date:
            conditions_sql.append("la.fecha::date >= :start_date")
        if end_date:
            conditions_sql.append("la.fecha::date <= :end_date")
        if orden_ids:
            conditions_sql.append("og.orden_id IN :orden_ids_param")
            params["orden_ids_param"] = tuple(orden_ids)
            
        if search_text:
            search_conds = [
                "r.referencia_portal ILIKE :search",
                "rfc.razon_social ILIKE :search",
                "c.nombre ILIKE :search",
                "d.nombre ILIKE :search",
                "u.nombre ILIKE :search",
                "ubi.cliente ILIKE :search",
                "la.lote_asignacion_id::text ILIKE :search",
                "n.nombre ILIKE :search",
                "col.nombre ILIKE :search"
            ]
            conditions_sql.append(f"({' OR '.join(search_conds)})")
            
        where_clause = f"WHERE {' AND '.join(conditions_sql)}"

        
        count_stmt = text(f"SELECT COUNT(DISTINCT r.referencia_id) {sql_base} {where_clause}")
        total_count = self.session.execute(count_stmt, params).scalar()
        
        query_stmt = text(f"""
            SELECT DISTINCT
                r.referencia_id,
                r.referencia_portal,
                r.importe,
                r.fecha_generacion,
                og.folio AS folio_orden,
                rfc.razon_social AS empresa,
                c.nombre AS concepto_nombre,
                c.concepto_id AS concepto_id,
                d.nombre AS delegacion_nombre,
                d.delegacion_id AS delegacion_id,
                u.nombre AS procesado_por,
                ar.referencia_id IS NOT NULL AS asignada,
                COALESCE(n.nombre, col.nombre, '') AS asignado_a,
                la.tipo_destino AS tipo_asignacion,
                la.solicitante_externo AS solicitante_externo,
                la.fecha AS fecha_asignacion,
                des.nombre AS desarrollo_nombre,
                ubi.cliente AS cliente_nombre,
                ubi.mz, ubi.lote, ubi.edif, ubi.viv, ubi.lote_id_erp AS folio_electronico,
                la.lote_asignacion_id AS lote_asignacion_id,
                es.codigo AS estado_codigo
            {sql_base}
            {where_clause}
            ORDER BY r.fecha_generacion DESC, r.referencia_id DESC
            LIMIT :lim OFFSET :off
        """)
        
        result = self.session.execute(query_stmt, params)
        res = []
        for row in result:
            res.append({
                "referencia_id": row.referencia_id,
                "referencia_portal": row.referencia_portal,
                "importe": str(row.importe) if row.importe else "",
                "fecha_generacion": row.fecha_generacion.strftime("%Y-%m-%d") if row.fecha_generacion else "",
                "folio_orden": row.folio_orden,
                "empresa": row.empresa,
                "concepto": row.concepto_nombre,
                "concepto_id": row.concepto_id,
                "delegacion": row.delegacion_nombre,
                "delegacion_id": row.delegacion_id,
                "procesado_por": row.procesado_por or "Sin Asignar",
                "asignada": row.asignada,
                "asignado_a": row.asignado_a,
                "tipo_asignacion": row.tipo_asignacion or "",
                "solicitante_externo": row.solicitante_externo or "",
                "fecha_asignacion": row.fecha_asignacion.strftime("%Y-%m-%d %H:%M") if row.fecha_asignacion else "",
                "desarrollo": row.desarrollo_nombre or "",
                "cliente": row.cliente_nombre or "",
                "mz": row.mz or "",
                "lote": row.lote or "",
                "edif": row.edif or "",
                "viv": row.viv or "",
                "folio_electronico": row.folio_electronico or "",
                "lote_asignacion_id": row.lote_asignacion_id,
                "estado_codigo": row.estado_codigo
            })
            
        return res, total_count

    def get_inventario_summary(
        self, search_text: str = "", concepto_id: int = None, rfc_id: int = None, start_date: str = None, end_date: str = None, orden_ids: list = None
    ) -> dict:
        from sqlalchemy import text
        
        params = {}
        if search_text:
            params["search"] = f"%{search_text}%"
        if concepto_id:
            params["concepto_id"] = concepto_id
        if rfc_id:
            params["rfc_id"] = rfc_id
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if orden_ids:
            params["orden_ids_param"] = tuple(orden_ids)
            
        sql_base = """
            FROM sar_produccion.referencia r
            JOIN sar_produccion.grupo_referencia gr ON r.grupo_id = gr.grupo_id
            JOIN sar_produccion.orden_generacion og ON gr.orden_id = og.orden_id
            JOIN sar_catalogo.rfc rfc ON gr.rfc_id = rfc.rfc_id
            JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
            JOIN sar_produccion.solicitud s ON r.solicitud_id = s.solicitud_id
            LEFT JOIN sar_catalogo.delegacion d ON s.delegacion_id = d.delegacion_id
            JOIN sar_catalogo.estado_sistema es ON r.estado_id = es.estado_id
            LEFT JOIN sar_seguridad.usuario u ON r.usuario_asignado = u.usuario_id
            LEFT JOIN sar_archivo.asignacion_referencia ar ON r.referencia_id = ar.referencia_id
            LEFT JOIN sar_archivo.lote_detalle ld ON ar.lote_detalle_id = ld.lote_detalle_id
            LEFT JOIN sar_archivo.lote_asignacion la ON ld.lote_asignacion_id = la.lote_asignacion_id
            LEFT JOIN sar_archivo.ubicacion ubi ON ar.ubicacion_id = ubi.ubicacion_id
        """
        
        base_conditions = []
        if concepto_id:
            base_conditions.append("gr.concepto_id = :concepto_id")
        if rfc_id:
            base_conditions.append("gr.rfc_id = :rfc_id")
        if start_date:
            base_conditions.append("la.fecha::date >= :start_date")
        if end_date:
            base_conditions.append("la.fecha::date <= :end_date")
        if orden_ids:
            base_conditions.append("og.orden_id IN :orden_ids_param")
        if search_text:
            search_conds = [
                "r.referencia_portal ILIKE :search",
                "rfc.razon_social ILIKE :search",
                "c.nombre ILIKE :search",
                "d.nombre ILIKE :search",
                "u.nombre ILIKE :search",
                "ubi.cliente ILIKE :search"
            ]
            base_conditions.append(f"({' OR '.join(search_conds)})")
            
        # Available condition
        conds_disp = list(base_conditions)
        conds_disp.append("es.codigo = 'FACTURADA'")
        conds_disp.append("ar.referencia_id IS NULL")
        where_disp = f"WHERE {' AND '.join(conds_disp)}"
        
        # Assigned condition
        conds_asig = list(base_conditions)
        conds_asig.append("es.codigo = 'ASIGNADA'")
        where_asig = f"WHERE {' AND '.join(conds_asig)}"
        
        # Reservada condition
        conds_res = list(base_conditions)
        conds_res.append("es.codigo = 'RESERVADA'")
        where_res = f"WHERE {' AND '.join(conds_res)}"
        
        query_disp = text(f"SELECT COUNT(DISTINCT r.referencia_id) {sql_base} {where_disp}")
        query_asig = text(f"SELECT COUNT(DISTINCT r.referencia_id) {sql_base} {where_asig}")
        query_res = text(f"SELECT COUNT(DISTINCT r.referencia_id) {sql_base} {where_res}")
        
        disponibles = self.session.execute(query_disp, params).scalar() or 0
        asignadas = self.session.execute(query_asig, params).scalar() or 0
        reservadas = self.session.execute(query_res, params).scalar() or 0
        
        return {"disponibles": disponibles, "asignadas": asignadas, "reservadas": reservadas}

    def crear_lote_asignacion(
        self, tipo_destino: str, notaria_id: Optional[int], colaborador_id: Optional[int],
        solicitante_externo: Optional[str], observaciones: Optional[str], usuario_creacion: int,
        detalles_list: List[dict]
    ) -> int:
        from sar.src.storage.models import LoteAsignacion, LoteDetalle, Ubicacion, AsignacionReferencia, Referencia, Concepto
        from sqlalchemy import select
        
        lote = LoteAsignacion(
            tipo_destino=tipo_destino,
            notaria_id=notaria_id,
            colaborador_id=colaborador_id,
            solicitante_externo=solicitante_externo.strip() if solicitante_externo else None,
            observaciones=observaciones,
            usuario_creacion=usuario_creacion
        )
        self.session.add(lote)
        self.session.flush()

        estado_asignada_id = self._get_estado_id("referencia", "ASIGNADA")

        # Load concepts map
        concepto_stmt = select(Concepto)
        concepts = self.session.execute(concepto_stmt).scalars().all()
        concepts_map = {c.alias: c.concepto_id for c in concepts if c.alias}

        # We will group references by (rfc_id, concepto_id, desarrollo_id) to create the LoteDetalle entries
        grouped_details = {}

        for d in detalles_list:
            ref = None
            if d.get("referencia_id"):
                ref = self.session.get(Referencia, d["referencia_id"])
            
            # Resolve keys
            rfc_id = ref.grupo.rfc_id if (ref and ref.grupo) else 1
            concepto_id = ref.grupo.concepto_id if (ref and ref.grupo) else concepts_map.get(d["concepto_solicitado"], 3)
            desarrollo_id = d["desarrollo_id"]

            key = (rfc_id, concepto_id, desarrollo_id)
            if key not in grouped_details:
                ld = LoteDetalle(
                    lote_asignacion_id=lote.lote_asignacion_id,
                    rfc_id=rfc_id,
                    concepto_id=concepto_id,
                    desarrollo_id=desarrollo_id,
                    cantidad_solicitada=0,
                    cantidad_confirmada=0
                )
                self.session.add(ld)
                self.session.flush()
                grouped_details[key] = ld

            # Increment count
            ld_parent = grouped_details[key]
            ld_parent.cantidad_solicitada += 1
            ld_parent.cantidad_confirmada += 1

            # Create Ubicacion record
            ubi = Ubicacion(
                cliente=d["cliente"].strip().upper(),
                desarrollo_id=desarrollo_id,
                fecha_solicitud=d.get("fecha_solicitud"),
                mz=d.get("mz"),
                lote=d.get("lote"),
                edif=d.get("edif"),
                viv=d.get("viv"),
                credito_titular=d.get("credito_titular"),
                delegacion=d.get("delegacion"),
                comentarios=d.get("pa"),
                lote_id_erp=d.get("folio_electronico")
            )
            self.session.add(ubi)
            self.session.flush()

            # Create AsignacionReferencia record
            asig = AsignacionReferencia(
                lote_detalle_id=ld_parent.lote_detalle_id,
                referencia_id=d["referencia_id"],
                ubicacion_id=ubi.ubicacion_id,
                intento=1,
                estado_id=estado_asignada_id,
                usuario_asignacion=usuario_creacion,
                observaciones=d.get("pa")
            )
            self.session.add(asig)
            
            if ref:
                ref.estado_id = estado_asignada_id

        self.session.flush()
        return lote.lote_asignacion_id

    def get_lotes_asignacion(self) -> List[dict]:
        from sqlalchemy import text
        stmt = text("""
            SELECT 
                la.lote_asignacion_id,
                la.tipo_destino,
                COALESCE(n.nombre, col.nombre, '') AS asignado_a,
                la.solicitante_externo,
                la.fecha,
                la.observaciones,
                u.nombre AS creador,
                (
                    SELECT COUNT(*) 
                    FROM sar_archivo.asignacion_referencia ar 
                    JOIN sar_archivo.lote_detalle ld ON ar.lote_detalle_id = ld.lote_detalle_id
                    WHERE ld.lote_asignacion_id = la.lote_asignacion_id
                ) AS total_referencias
            FROM sar_archivo.lote_asignacion la
            LEFT JOIN sar_catalogo.notaria n ON la.notaria_id = n.notaria_id
            LEFT JOIN sar_catalogo.colaborador col ON la.colaborador_id = col.colaborador_id
            JOIN sar_seguridad.usuario u ON la.usuario_creacion = u.usuario_id
            ORDER BY la.fecha DESC
        """)
        results = self.session.execute(stmt).all()
        return [
            {
                "lote_asignacion_id": row.lote_asignacion_id,
                "tipo_destino": row.tipo_destino,
                "asignado_a": row.asignado_a,
                "solicitante_externo": row.solicitante_externo or "",
                "fecha": row.fecha.strftime("%Y-%m-%d %H:%M"),
                "observaciones": row.observaciones or "",
                "creador": row.creador,
                "total_referencias": row.total_referencias
            }
            for row in results
        ]

    def get_lotes_asignacion_filtered(
        self,
        search: str = None,
        tipo_destino: str = None,
        limit: int = 50,
        offset: int = 0,
        start_date: str = None,
        end_date: str = None,
        orden_ids: list = None
    ):
        """Returns paginated lotes with optional filters including date range. Returns (list_of_dicts, total_count)."""
        from sqlalchemy import text

        where_clauses = []
        params = {"limit": limit, "offset": offset}

        if tipo_destino:
            where_clauses.append("la.tipo_destino = :tipo_destino")
            params["tipo_destino"] = tipo_destino

        if start_date:
            where_clauses.append("la.fecha >= :start_date")
            params["start_date"] = start_date

        if end_date:
            where_clauses.append("la.fecha <= :end_date")
            params["end_date"] = f"{end_date} 23:59:59"

        if orden_ids:
            where_clauses.append("""
                la.lote_asignacion_id IN (
                    SELECT DISTINCT ld.lote_asignacion_id 
                    FROM sar_archivo.lote_detalle ld
                    JOIN sar_archivo.asignacion_referencia ar ON ld.lote_detalle_id = ar.lote_detalle_id
                    JOIN sar_produccion.referencia r ON ar.referencia_id = r.referencia_id
                    JOIN sar_produccion.grupo_referencia gr ON r.grupo_id = gr.grupo_id
                    WHERE gr.orden_id IN :orden_ids_param
                )
            """)
            params["orden_ids_param"] = tuple(orden_ids)

        if search:
            where_clauses.append("""
                (
                    la.lote_asignacion_id::text ILIKE :search
                    OR n.nombre ILIKE :search
                    OR col.nombre ILIKE :search
                    OR la.solicitante_externo ILIKE :search
                    OR la.observaciones ILIKE :search
                    OR u.nombre ILIKE :search
                )
            """)
            params["search"] = f"%{search}%"

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        stmt_count = text(f"""
            SELECT COUNT(*) FROM sar_archivo.lote_asignacion la
            LEFT JOIN sar_catalogo.notaria n ON la.notaria_id = n.notaria_id
            LEFT JOIN sar_catalogo.colaborador col ON la.colaborador_id = col.colaborador_id
            JOIN sar_seguridad.usuario u ON la.usuario_creacion = u.usuario_id
            {where_sql}
        """)
        total = self.session.execute(stmt_count, params).scalar() or 0

        stmt = text(f"""
            SELECT
                la.lote_asignacion_id,
                la.tipo_destino,
                COALESCE(n.nombre, col.nombre, '') AS asignado_a,
                la.solicitante_externo,
                la.fecha,
                la.observaciones,
                u.nombre AS creador,
                (
                    SELECT COUNT(*)
                    FROM sar_archivo.asignacion_referencia ar
                    JOIN sar_archivo.lote_detalle ld ON ar.lote_detalle_id = ld.lote_detalle_id
                    WHERE ld.lote_asignacion_id = la.lote_asignacion_id
                ) AS total_referencias
            FROM sar_archivo.lote_asignacion la
            LEFT JOIN sar_catalogo.notaria n ON la.notaria_id = n.notaria_id
            LEFT JOIN sar_catalogo.colaborador col ON la.colaborador_id = col.colaborador_id
            JOIN sar_seguridad.usuario u ON la.usuario_creacion = u.usuario_id
            {where_sql}
            ORDER BY la.fecha DESC
            LIMIT :limit OFFSET :offset
        """)
        results = self.session.execute(stmt, params).all()

        lotes = [
            {
                "lote_asignacion_id": row.lote_asignacion_id,
                "tipo_destino": row.tipo_destino,
                "asignado_a": row.asignado_a,
                "solicitante_externo": row.solicitante_externo or "",
                "fecha": row.fecha.strftime("%Y-%m-%d %H:%M"),
                "observaciones": row.observaciones or "",
                "creador": row.creador,
                "total_referencias": row.total_referencias,
            }
            for row in results
        ]
        return lotes, int(total)


    def get_lote_asignacion_header(self, lote_asignacion_id: int) -> dict:
        """Returns rich header info for a single lote_asignacion."""
        from sqlalchemy import text
        stmt = text("""
            SELECT
                la.lote_asignacion_id,
                la.tipo_destino,
                COALESCE(n.nombre, col.nombre, '') AS asignado_a,
                la.solicitante_externo,
                la.fecha,
                la.observaciones,
                u.nombre AS creador,
                COALESCE(r_emp.razon_social, '') AS empresa,
                (
                    SELECT es.codigo
                    FROM sar_archivo.asignacion_referencia ar2
                    JOIN sar_catalogo.estado_sistema es ON ar2.estado_id = es.estado_id
                    WHERE ar2.lote_detalle_id IN (
                        SELECT ld2.lote_detalle_id
                        FROM sar_archivo.lote_detalle ld2
                        WHERE ld2.lote_asignacion_id = la.lote_asignacion_id
                    )
                    LIMIT 1
                ) AS estado_muestra
            FROM sar_archivo.lote_asignacion la
            LEFT JOIN sar_catalogo.notaria n ON la.notaria_id = n.notaria_id
            LEFT JOIN sar_catalogo.colaborador col ON la.colaborador_id = col.colaborador_id
            JOIN sar_seguridad.usuario u ON la.usuario_creacion = u.usuario_id
            LEFT JOIN (
                SELECT ld_e.lote_asignacion_id, MIN(ld_e.rfc_id) AS rfc_id
                FROM sar_archivo.lote_detalle ld_e
                GROUP BY ld_e.lote_asignacion_id
            ) first_rfc ON first_rfc.lote_asignacion_id = la.lote_asignacion_id
            LEFT JOIN sar_catalogo.rfc r_emp ON r_emp.rfc_id = first_rfc.rfc_id
            WHERE la.lote_asignacion_id = :lote_id
        """)
        row = self.session.execute(stmt, {"lote_id": lote_asignacion_id}).first()
        if not row:
            return {}
        return {
            "lote_asignacion_id": row.lote_asignacion_id,
            "tipo_destino": row.tipo_destino,
            "asignado_a": row.asignado_a,
            "solicitante_externo": row.solicitante_externo or "",
            "fecha": row.fecha.strftime("%d/%m/%Y %H:%M") if row.fecha else "",
            "observaciones": row.observaciones or "",
            "creador": row.creador,
            "empresa": row.empresa,
            "estado_refs": row.estado_muestra or "—",
        }

    def get_lote_detalles(self, lote_asignacion_id: int) -> List[dict]:

        from sqlalchemy import text
        stmt = text("""
            SELECT
                ar.asignacion_referencia_id AS lote_detalle_id,
                ar.referencia_id,
                COALESCE(ubi.cliente, 'RESERVA PENDIENTE DE COMPLETAR') AS cliente,
                des.nombre AS desarrollo_nombre,
                ubi.fecha_solicitud,
                COALESCE(ubi.mz, '') || ' ' || COALESCE(ubi.lote, '') AS ubicacion,
                ubi.mz,
                ubi.lote,
                ubi.edif,
                ubi.viv,
                ubi.lote_id_erp AS folio_electronico,
                ubi.credito_titular,
                ubi.comentarios AS pa,
                ubi.delegacion,
                c.alias AS concepto_solicitado,
                ref.referencia_portal AS referencia_asignada,
                d.nombre AS delegacion_nombre,
                es.codigo AS estado_ref,
                r.razon_social AS empresa
            FROM sar_archivo.asignacion_referencia ar
            JOIN sar_archivo.lote_detalle ld ON ar.lote_detalle_id = ld.lote_detalle_id
            JOIN sar_produccion.referencia ref ON ar.referencia_id = ref.referencia_id
            JOIN sar_catalogo.concepto c ON ld.concepto_id = c.concepto_id
            JOIN sar_catalogo.desarrollo des ON ld.desarrollo_id = des.desarrollo_id
            JOIN sar_catalogo.delegacion d ON des.delegacion_id = d.delegacion_id
            JOIN sar_catalogo.estado_sistema es ON ar.estado_id = es.estado_id
            JOIN sar_catalogo.rfc r ON ld.rfc_id = r.rfc_id
            LEFT JOIN sar_archivo.ubicacion ubi ON ar.ubicacion_id = ubi.ubicacion_id
            WHERE ld.lote_asignacion_id = :lote_id
            ORDER BY ar.asignacion_referencia_id ASC
        """)
        results = self.session.execute(stmt, {"lote_id": lote_asignacion_id}).all()
        return [
            {
                "lote_detalle_id": row.lote_detalle_id,
                "referencia_id": row.referencia_id,
                "cliente": row.cliente,
                "desarrollo": row.desarrollo_nombre,
                "delegacion": row.delegacion_nombre,
                "fecha_solicitud": row.fecha_solicitud.strftime("%Y-%m-%d") if row.fecha_solicitud else "",
                "ubicacion": row.ubicacion or "",
                "mz": row.mz or "",
                "lote": row.lote or "",
                "edif": row.edif or "",
                "viv": row.viv or "",
                "folio_electronico": row.folio_electronico or "",
                "credito_titular": row.credito_titular or "",
                "pa": row.pa or "",
                "delegacion_original": row.delegacion or "",
                "concepto": row.concepto_solicitado,
                "referencia": row.referencia_asignada,
                "estado": row.estado_ref,
                "empresa": row.empresa,
            }
            for row in results
        ]

    def get_facturas_by_referencia_id(self, referencia_id: int) -> List[dict]:
        from sqlalchemy import text
        stmt = text("""
            SELECT factura_id, pdf_path, pdf2_path, uuid, nombre_archivo, estado, delegacion
            FROM sar_archivo.factura
            WHERE referencia_id = :referencia_id
        """)
        results = self.session.execute(stmt, {"referencia_id": referencia_id}).all()
        return [
            {
                "factura_id": row.factura_id,
                "pdf_path": row.pdf_path,
                "pdf2_path": row.pdf2_path,
                "uuid": row.uuid,
                "nombre_archivo": row.nombre_archivo,
                "estado": row.estado,
                "delegacion": row.delegacion
            }
            for row in results
        ]

    def count_referencias_disponibles(self, rfc_id: int, concepto_id: int, delegacion_id: int, orden_ids: list = None) -> int:
        """Returns the count of FACTURADA references available for the given combination.
        Used for real-time UI feedback without side effects.
        """
        from sar.src.storage.models import Referencia, EstadoSistema, GrupoReferencia, AsignacionReferencia, Solicitud, Concepto
        from sqlalchemy import select, func

        conc = self.session.get(Concepto, concepto_id)
        if not conc:
            return 0

        expected_aliases = []
        if conc.alias == "CLG":
            expected_aliases = ["CLG"]
        elif conc.alias in ("AVISO", "NUEVO_DERECHO_AVISO", "AVISO PREVENTIVO"):
            expected_aliases = ["AVISO PREVENTIVO"]
        elif conc.alias == "ANALISIS":
            expected_aliases = ["ANALISIS"]
        else:
            expected_aliases = [conc.alias]

        count_stmt = (
            select(func.count(Referencia.referencia_id))
            .join(EstadoSistema, Referencia.estado_id == EstadoSistema.estado_id)
            .join(GrupoReferencia, Referencia.grupo_id == GrupoReferencia.grupo_id)
            .join(Concepto, GrupoReferencia.concepto_id == Concepto.concepto_id)
            .join(Solicitud, Referencia.solicitud_id == Solicitud.solicitud_id)
            .where(
                EstadoSistema.entidad == 'referencia',
                EstadoSistema.codigo == 'FACTURADA',
                GrupoReferencia.rfc_id == rfc_id,
                Concepto.alias.in_(expected_aliases),
                Solicitud.delegacion_id == delegacion_id,
                ~Referencia.referencia_id.in_(
                    select(AsignacionReferencia.referencia_id)
                )
            )
        )
        if orden_ids:
            count_stmt = count_stmt.where(GrupoReferencia.orden_id.in_(orden_ids))
        result = self.session.execute(count_stmt).scalar()
        return result if result is not None else 0

    def apartar_referencias(
        self, notaria_id: int, rfc_id: int, concepto_id: int, delegacion_id: int, cantidad: int, usuario_id: int, desarrollo_id: Optional[int] = None, observaciones: Optional[str] = None, orden_ids: Optional[list] = None
    ) -> int:
        from sar.src.storage.models import LoteAsignacion, LoteDetalle, AsignacionReferencia, Referencia, EstadoSistema, Desarrollo, GrupoReferencia, Solicitud, Concepto
        from sqlalchemy import select

        # If desarrollo_id is not specified (e.g. "Cualquier Desarrollo"), we find fallback development
        from sar.src.storage.models import DesarrolloEmpresa
        if not desarrollo_id:
            des_emp = (
                self.session.query(DesarrolloEmpresa)
                .filter(
                    DesarrolloEmpresa.rfc_id == rfc_id,
                    DesarrolloEmpresa.delegacion_id == delegacion_id,
                    DesarrolloEmpresa.activo == True
                )
                .order_by(DesarrolloEmpresa.es_default.desc())
                .first()
            )
            if not des_emp:
                # Fallback to any active development for this delegation
                des_emp = (
                    self.session.query(DesarrolloEmpresa)
                    .filter(
                        DesarrolloEmpresa.delegacion_id == delegacion_id,
                        DesarrolloEmpresa.activo == True
                    )
                    .first()
                )
            if not des_emp:
                raise ValueError("No se encontró ningún desarrollo activo asociado a la delegación seleccionada.")
            desarrollo_id = des_emp.desarrollo_id

        estado_facturada_id = self._get_estado_id("referencia", "FACTURADA")
        estado_reservada_id = self._get_estado_id("referencia", "RESERVADA")

        conc = self.session.get(Concepto, concepto_id)
        if not conc:
            raise ValueError("El concepto seleccionado no existe.")
        
        expected_aliases = []
        if conc.alias == "CLG": expected_aliases = ["CLG"]
        elif conc.alias in ("AVISO", "NUEVO_DERECHO_AVISO"): expected_aliases = ["AVISO PREVENTIVO"]
        elif conc.alias == "ANALISIS": expected_aliases = ["ANALISIS"]
        else: expected_aliases = [conc.alias]

        available_stmt = (
            select(Referencia)
            .join(EstadoSistema, Referencia.estado_id == EstadoSistema.estado_id)
            .join(GrupoReferencia, Referencia.grupo_id == GrupoReferencia.grupo_id)
            .join(Concepto, GrupoReferencia.concepto_id == Concepto.concepto_id)
            .join(Solicitud, Referencia.solicitud_id == Solicitud.solicitud_id)
            .where(
                EstadoSistema.entidad == 'referencia',
                EstadoSistema.codigo == 'FACTURADA',
                GrupoReferencia.rfc_id == rfc_id,
                Concepto.alias.in_(expected_aliases),
                Solicitud.delegacion_id == delegacion_id,
                ~Referencia.referencia_id.in_(
                    select(AsignacionReferencia.referencia_id)
                )
            )
        )
        if orden_ids:
            available_stmt = available_stmt.where(GrupoReferencia.orden_id.in_(orden_ids))
            
        available_stmt = available_stmt.limit(cantidad)
        available_refs = self.session.execute(available_stmt).scalars().all()
        
        if len(available_refs) < cantidad:
            raise ValueError(f"No hay suficientes facturas disponibles en estado FACTURADA. Solicitadas: {cantidad}, Disponibles: {len(available_refs)}")

        lote = LoteAsignacion(
            tipo_destino="NOTARIA",
            notaria_id=notaria_id,
            colaborador_id=None,
            solicitante_externo=None,
            observaciones=observaciones if observaciones else f"Apartado/Reserva de referencias (Cant: {cantidad})",
            usuario_creacion=usuario_id
        )
        self.session.add(lote)
        self.session.flush()

        # Create LoteDetalle representing the Captured Row
        ld = LoteDetalle(
            lote_asignacion_id=lote.lote_asignacion_id,
            rfc_id=rfc_id,
            concepto_id=concepto_id,
            desarrollo_id=desarrollo_id,
            cantidad_solicitada=cantidad,
            cantidad_confirmada=0
        )
        self.session.add(ld)
        self.session.flush()

        for ref in available_refs:
            asig = AsignacionReferencia(
                lote_detalle_id=ld.lote_detalle_id,
                referencia_id=ref.referencia_id,
                ubicacion_id=None,
                intento=1,
                estado_id=estado_reservada_id,
                usuario_asignacion=usuario_id,
                observaciones="Reservada"
            )
            self.session.add(asig)
            ref.estado_id = estado_reservada_id

        return lote.lote_asignacion_id

    def apartar_referencias_lote(
        self, notaria_id: int, usuario_id: int, partidas: List[dict], observaciones: Optional[str] = None, orden_ids: Optional[list] = None
    ) -> int:
        """
        Reserva referencias para múltiples partidas bajo un único lote_asignacion.
        Cada partida en 'partidas' debe ser un diccionario con:
        - rfc_id, concepto_id, delegacion_id, cantidad, desarrollo_id (opcional)
        """
        from sar.src.storage.models import LoteAsignacion, LoteDetalle, AsignacionReferencia, Referencia, EstadoSistema, Desarrollo, GrupoReferencia, Solicitud, Concepto, DesarrolloEmpresa
        from sqlalchemy import select

        estado_facturada_id = self._get_estado_id("referencia", "FACTURADA")
        estado_reservada_id = self._get_estado_id("referencia", "RESERVADA")

        # 1. Crear el lote global de asignación (cabecera única)
        lote = LoteAsignacion(
            tipo_destino="NOTARIA",
            notaria_id=notaria_id,
            colaborador_id=None,
            solicitante_externo=None,
            observaciones=observaciones if observaciones else "Apartado/Reserva de referencias múltiple",
            usuario_creacion=usuario_id
        )
        self.session.add(lote)
        self.session.flush()

        # 2. Iterar y procesar cada renglón/partida
        for partida in partidas:
            rfc_id = partida["rfc_id"]
            concepto_id = partida["concepto_id"]
            delegacion_id = partida["delegacion_id"]
            cantidad = partida["cantidad"]
            desarrollo_id = partida.get("desarrollo_id")

            # Buscar desarrollo default si no se especifica
            if not desarrollo_id:
                des_emp = (
                    self.session.query(DesarrolloEmpresa)
                    .filter(
                        DesarrolloEmpresa.rfc_id == rfc_id,
                        DesarrolloEmpresa.delegacion_id == delegacion_id,
                        DesarrolloEmpresa.activo == True
                    )
                    .order_by(DesarrolloEmpresa.es_default.desc())
                    .first()
                )
                if not des_emp:
                    des_emp = (
                        self.session.query(DesarrolloEmpresa)
                        .filter(
                            DesarrolloEmpresa.delegacion_id == delegacion_id,
                            DesarrolloEmpresa.activo == True
                        )
                        .first()
                    )
                if not des_emp:
                    raise ValueError("No se encontró ningún desarrollo activo asociado a la delegación seleccionada.")
                desarrollo_id = des_emp.desarrollo_id

            conc = self.session.get(Concepto, concepto_id)
            if not conc:
                raise ValueError("El concepto seleccionado no existe.")
            
            expected_aliases = []
            if conc.alias == "CLG": expected_aliases = ["CLG"]
            elif conc.alias in ("AVISO", "NUEVO_DERECHO_AVISO"): expected_aliases = ["AVISO PREVENTIVO"]
            elif conc.alias == "ANALISIS": expected_aliases = ["ANALISIS"]
            else: expected_aliases = [conc.alias]

            available_stmt = (
                select(Referencia)
                .join(EstadoSistema, Referencia.estado_id == EstadoSistema.estado_id)
                .join(GrupoReferencia, Referencia.grupo_id == GrupoReferencia.grupo_id)
                .join(Concepto, GrupoReferencia.concepto_id == Concepto.concepto_id)
                .join(Solicitud, Referencia.solicitud_id == Solicitud.solicitud_id)
                .where(
                    EstadoSistema.entidad == 'referencia',
                    EstadoSistema.codigo == 'FACTURADA',
                    GrupoReferencia.rfc_id == rfc_id,
                    Concepto.alias.in_(expected_aliases),
                    Solicitud.delegacion_id == delegacion_id,
                    ~Referencia.referencia_id.in_(
                        select(AsignacionReferencia.referencia_id)
                    )
                )
            )
            if orden_ids:
                available_stmt = available_stmt.where(GrupoReferencia.orden_id.in_(orden_ids))
                
            available_stmt = available_stmt.limit(cantidad)
            available_refs = self.session.execute(available_stmt).scalars().all()
            
            if len(available_refs) < cantidad:
                raise ValueError(f"No hay suficientes facturas disponibles en estado FACTURADA. Solicitadas: {cantidad}, Disponibles: {len(available_refs)}")

            # Crear el LoteDetalle correspondiente a este renglón
            ld = LoteDetalle(
                lote_asignacion_id=lote.lote_asignacion_id,
                rfc_id=rfc_id,
                concepto_id=concepto_id,
                desarrollo_id=desarrollo_id,
                cantidad_solicitada=cantidad,
                cantidad_confirmada=0
            )
            self.session.add(ld)
            self.session.flush()

            # Vincular referencias
            for ref in available_refs:
                asig = AsignacionReferencia(
                    lote_detalle_id=ld.lote_detalle_id,
                    referencia_id=ref.referencia_id,
                    ubicacion_id=None,
                    intento=1,
                    estado_id=estado_reservada_id,
                    usuario_asignacion=usuario_id,
                    observaciones="Reservada"
                )
                self.session.add(asig)
                ref.estado_id = estado_reservada_id

        self.session.flush()
        return lote.lote_asignacion_id

    def get_lotes_reservados_by_notaria(self, notaria_id: int) -> List[dict]:
        from sqlalchemy import text
        stmt = text("""
            SELECT 
                la.lote_asignacion_id,
                la.fecha,
                (
                    SELECT COUNT(*) 
                    FROM sar_archivo.asignacion_referencia ar 
                    JOIN sar_archivo.lote_detalle ld ON ar.lote_detalle_id = ld.lote_detalle_id
                    WHERE ld.lote_asignacion_id = la.lote_asignacion_id 
                      AND ar.ubicacion_id IS NULL
                ) AS total_pendientes
            FROM sar_archivo.lote_asignacion la
            WHERE la.notaria_id = :notaria_id
              AND EXISTS (
                  SELECT 1 
                  FROM sar_archivo.asignacion_referencia ar 
                  JOIN sar_archivo.lote_detalle ld ON ar.lote_detalle_id = ld.lote_detalle_id
                  WHERE ld.lote_asignacion_id = la.lote_asignacion_id 
                    AND ar.ubicacion_id IS NULL
              )
            ORDER BY la.fecha ASC
        """)
        results = self.session.execute(stmt, {"notaria_id": notaria_id}).all()
        return [
            {
                "lote_asignacion_id": row.lote_asignacion_id,
                "fecha": row.fecha.strftime("%Y-%m-%d %H:%M"),
                "total_pendientes": row.total_pendientes
            }
            for row in results
        ]

    def completar_reservaciones(self, detalles_completados: List[dict], usuario_id: Optional[int] = None) -> None:
        from sar.src.storage.models import AsignacionReferencia, Referencia, Ubicacion
        import datetime
        estado_asignada_id = self._get_estado_id("referencia", "ASIGNADA")
        
        for d in detalles_completados:
            ar_id = d.get("lote_detalle_id") # Note: mapped in get_lote_detalles as lote_detalle_id
            if not ar_id:
                continue
            
            ar = self.session.get(AsignacionReferencia, ar_id)
            if ar:
                # Convert string date to datetime.date object for fecha_solicitud
                f_sol = d.get("fecha_solicitud")
                fecha_sol = None
                if f_sol:
                    if isinstance(f_sol, str):
                        try:
                            if "-" in f_sol:
                                fecha_sol = datetime.datetime.strptime(f_sol.split()[0], "%Y-%m-%d").date()
                            else:
                                fecha_sol = datetime.datetime.strptime(f_sol.split()[0], "%d/%m/%Y").date()
                        except:
                            fecha_sol = None
                    else:
                        fecha_sol = f_sol

                # Convert string date for fecha_ingreso_rpp
                f_rpp = d.get("estatus_primer_aviso")
                fecha_rpp = None
                if f_rpp:
                    if isinstance(f_rpp, str):
                        try:
                            # Try yyyy-mm-dd first, then dd/mm/yyyy
                            if "-" in f_rpp:
                                fecha_rpp = datetime.datetime.strptime(f_rpp.split()[0], "%Y-%m-%d").date()
                            else:
                                fecha_rpp = datetime.datetime.strptime(f_rpp.split()[0], "%d/%m/%Y").date()
                        except:
                            fecha_rpp = None
                    else:
                        fecha_rpp = f_rpp

                # Check if an Ubicacion with this exact address/client already exists in this transaction/database to avoid duplication
                from sqlalchemy import select
                cliente_upper = d["cliente"].strip().upper()
                desarrollo_id = ar.lote_detalle.desarrollo_id
                mz = d.get("mz")
                lote = d.get("lote")
                edif = d.get("edif")
                viv = d.get("viv")
                
                dup_ubi_stmt = select(Ubicacion).where(
                    Ubicacion.cliente == cliente_upper,
                    Ubicacion.desarrollo_id == desarrollo_id,
                    Ubicacion.mz == mz,
                    Ubicacion.lote == lote,
                    Ubicacion.edif == edif,
                    Ubicacion.viv == viv
                )
                ubi = self.session.execute(dup_ubi_stmt).scalars().first()

                # Get correct 'pa' field from Excel payload
                pa_val = d.get("pa")

                if not ubi:
                    # Create new Ubicacion mapping to the new database columns if not exists
                    ubi = Ubicacion(
                        cliente=cliente_upper,
                        desarrollo_id=desarrollo_id,
                        fecha_solicitud=fecha_sol,
                        mz=mz,
                        lote=lote,
                        edif=edif, # ext
                        viv=viv,   # int
                        credito_titular=d.get("credito_titular"),
                        delegacion=d.get("delegacion"),
                        comentarios=d.get("comentarios"), # default comments
                        pa=pa_val, # new column pa
                        no_oficial=d.get("folio_electronico"), # new column no_oficial
                        fecha_ingreso_rpp=fecha_rpp # new column fecha_ingreso_rpp
                    )
                    self.session.add(ubi)
                    self.session.flush()
                else:
                    # If it exists, update the missing fields (pa, no_oficial, fecha_ingreso_rpp) if they are provided in Excel
                    if pa_val and not ubi.pa:
                        ubi.pa = pa_val
                    if d.get("folio_electronico") and not ubi.no_oficial:
                        ubi.no_oficial = d.get("folio_electronico")
                    if fecha_rpp and not ubi.fecha_ingreso_rpp:
                        ubi.fecha_ingreso_rpp = fecha_rpp
                    self.session.flush()

                # Link to AsignacionReferencia and set status to ASIGNADA
                ar.ubicacion_id = ubi.ubicacion_id
                ar.estado_id = estado_asignada_id
                
                # Calculate consecutive attempt number (intento) for this location AND concept
                from sar.src.storage.models import LoteDetalle
                intento_stmt = (
                    select(AsignacionReferencia.intento)
                    .join(LoteDetalle, AsignacionReferencia.lote_detalle_id == LoteDetalle.lote_detalle_id)
                    .where(
                        AsignacionReferencia.ubicacion_id == ubi.ubicacion_id,
                        AsignacionReferencia.asignacion_referencia_id != ar.asignacion_referencia_id,
                        LoteDetalle.concepto_id == ar.lote_detalle.concepto_id
                    )
                    .order_by(AsignacionReferencia.intento.desc())
                )
                prev_intentos = self.session.execute(intento_stmt).scalars().all()
                if prev_intentos:
                    ar.intento = prev_intentos[0] + 1
                else:
                    ar.intento = 1
                
                # Register confirmation date and confirming user
                ar.fecha_confirmacion = datetime.datetime.now()
                if usuario_id:
                    ar.usuario_confirmacion = usuario_id
                
                # Increment confirmed count in lote_detalle
                ar.lote_detalle.cantidad_confirmada += 1
                
                # Update reference status to ASIGNADA
                if ar.referencia_id:
                    ref = self.session.get(Referencia, ar.referencia_id)
                    if ref:
                        ref.estado_id = estado_asignada_id
        self.session.flush()

    def get_referencias_disponibles_filtro(
        self, rfc_id: int, concepto_id: int, delegacion_id: int, cantidad: int, orden_ids: list = None
    ) -> List[dict]:
        """Fetches available references matching criteria using FIFO order, returning lightweight dicts."""
        from sar.src.storage.models import Referencia, EstadoSistema, GrupoReferencia, AsignacionReferencia, Solicitud, Concepto
        from sqlalchemy import select

        conc = self.session.get(Concepto, concepto_id)
        if not conc:
            return []

        expected_aliases = []
        if conc.alias == "CLG": expected_aliases = ["CLG"]
        elif conc.alias in ("AVISO", "NUEVO_DERECHO_AVISO", "AVISO PREVENTIVO"): expected_aliases = ["AVISO PREVENTIVO"]
        elif conc.alias == "ANALISIS": expected_aliases = ["ANALISIS"]
        else: expected_aliases = [conc.alias]

        from sar.src.storage.models import Rfc
        stmt = (
            select(
                Referencia.referencia_id,
                Referencia.referencia_portal,
                Referencia.importe,
                Concepto.nombre,
                Rfc.razon_social
            )
            .join(EstadoSistema, Referencia.estado_id == EstadoSistema.estado_id)
            .join(GrupoReferencia, Referencia.grupo_id == GrupoReferencia.grupo_id)
            .join(Concepto, GrupoReferencia.concepto_id == Concepto.concepto_id)
            .join(Rfc, GrupoReferencia.rfc_id == Rfc.rfc_id)
            .join(Solicitud, Referencia.solicitud_id == Solicitud.solicitud_id)
            .where(
                EstadoSistema.entidad == 'referencia',
                EstadoSistema.codigo == 'FACTURADA',
                GrupoReferencia.rfc_id == rfc_id,
                Concepto.alias.in_(expected_aliases),
                Solicitud.delegacion_id == delegacion_id,
                ~Referencia.referencia_id.in_(
                    select(AsignacionReferencia.referencia_id)
                )
            )
            .order_by(Referencia.fecha_generacion.asc(), Referencia.referencia_id.asc())
            .limit(cantidad)
        )
        if orden_ids:
            stmt = stmt.where(GrupoReferencia.orden_id.in_(orden_ids))
        rows = self.session.execute(stmt).all()
        return [
            {
                "referencia_id": r[0],
                "referencia_portal": r[1],
                "importe": str(r[2]) if r[2] else "0.00",
                "concepto_nombre": r[3] or "",
                "empresa_nombre": r[4] or ""
            }
            for r in rows
        ]

    def asignar_referencias_directo(
        self, tipo_destino: str, destino_id: int, usuario_id: int, referencias_data: List[dict],
        solicitante_externo: Optional[str] = None, observaciones: Optional[str] = None
    ) -> int:
        """Assigns references directly (individual selection style) to Notaria/Colaborador."""
        from sar.src.storage.models import LoteAsignacion, LoteDetalle, AsignacionReferencia, Referencia, Concepto, Desarrollo
        from sqlalchemy import select
        import datetime

        notaria_id = destino_id if tipo_destino == "NOTARIA" else None
        colaborador_id = destino_id if tipo_destino == "COLABORADOR" else None

        lote = LoteAsignacion(
            tipo_destino=tipo_destino,
            notaria_id=notaria_id,
            colaborador_id=colaborador_id,
            solicitante_externo=solicitante_externo.strip() if solicitante_externo else None,
            observaciones=observaciones.strip() if observaciones else "Asignación Individual Directa",
            usuario_creacion=usuario_id
        )
        self.session.add(lote)
        self.session.flush()

        estado_asignada_id = self._get_estado_id("referencia", "ASIGNADA")

        # Agrupar referencias por (rfc_id, concepto_id, desarrollo_id)
        for item in referencias_data:
            ref_id = item["referencia_id"]
            delegacion_id = item["delegacion_id"]

            ref = self.session.get(Referencia, ref_id)
            if not ref:
                continue

            # Obtener el desarrollo_id correspondiente a esa delegación y al RFC del grupo de la referencia
            from sar.src.storage.models import DesarrolloEmpresa
            de_stmt = select(DesarrolloEmpresa.desarrollo_id).where(
                DesarrolloEmpresa.delegacion_id == delegacion_id,
                DesarrolloEmpresa.rfc_id == ref.grupo.rfc_id,
                DesarrolloEmpresa.activo == True
            )
            desarrollo_id = self.session.execute(de_stmt).scalar()
            if not desarrollo_id:
                # Fallback to any development matching this delegation
                from sar.src.storage.models import Desarrollo
                des_stmt = select(Desarrollo.desarrollo_id).where(Desarrollo.nombre == "GENERAL")
                desarrollo_id = self.session.execute(des_stmt).scalar() or 1

            ld = LoteDetalle(
                lote_asignacion_id=lote.lote_asignacion_id,
                rfc_id=ref.grupo.rfc_id,
                concepto_id=ref.grupo.concepto_id,
                desarrollo_id=desarrollo_id,
                cantidad_solicitada=1,
                cantidad_confirmada=1
            )
            self.session.add(ld)
            self.session.flush()

            # Registrar asignación
            asig = AsignacionReferencia(
                lote_detalle_id=ld.lote_detalle_id,
                referencia_id=ref.referencia_id,
                ubicacion_id=None,
                intento=1,
                estado_id=estado_asignada_id,
                usuario_asignacion=usuario_id,
                observaciones="Asignado Individualmente"
            )
            self.session.add(asig)
            ref.estado_id = estado_asignada_id

        self.session.flush()
        return lote.lote_asignacion_id


