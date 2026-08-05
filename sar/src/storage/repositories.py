"""Repository classes for encapsulated database CRUD and queries."""

from typing import List, Optional
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
        if orden_ids:
            stmt = text("""
                SELECT * FROM sar_produccion.vw_solicitudes_detalle 
                WHERE grupo_id IN (SELECT g_ref.grupo_id FROM sar_produccion.grupo_referencia g_ref WHERE g_ref.orden_id IN :orden_ids_param)
                ORDER BY grupo_id ASC, solicitud_id ASC
            """)
            result = self.session.execute(stmt, {"orden_ids_param": tuple(orden_ids)})
        else:
            stmt = text("SELECT * FROM sar_produccion.vw_solicitudes_detalle ORDER BY grupo_id ASC, solicitud_id ASC")
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
                   c.nombre as concepto, d.nombre as delegacion, 
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
                   c.nombre as concepto, d.nombre as delegacion, 
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
            query_str += " AND es.codigo IN ('AUTORIZADA', 'AUTORIZACION_PARCIAL', 'FACTURADA', 'FACTURADA_PARCIAL', 'ERROR_VALIDACION')"
        else:
            query_str += " AND es.codigo IN ('AUTORIZADA', 'AUTORIZACION_PARCIAL')"
            
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
                rfc.colonia, rfc.no_exterior, rfc.no_interior, rfc.localidad,
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
            "rfc_municipio": row.rfc_municipio,
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
            pdte_codes = ["GENERADA", "ASIGNADA", "PENDIENTE"]
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
                    
            err_codes = ["ERROR", "RECHAZADA", "FALLIDO"]
            err_ids = []
            for code in err_codes:
                try:
                    err_ids.append(self._get_estado_id("referencia", code))
                except ValueError:
                    pass
            
            query_pdte = select(func.count(Referencia.referencia_id)).where(Referencia.estado_id.in_(pdte_ids))
            query_aut = select(func.count(Referencia.referencia_id)).where(Referencia.estado_id.in_(aut_ids))
            query_err = select(func.count(Referencia.referencia_id)).where(Referencia.estado_id.in_(err_ids))
            
            if orden_ids:
                query_pdte = query_pdte.join(GrupoReferencia).where(GrupoReferencia.orden_id.in_(orden_ids))
                query_aut = query_aut.join(GrupoReferencia).where(GrupoReferencia.orden_id.in_(orden_ids))
                query_err = query_err.join(GrupoReferencia).where(GrupoReferencia.orden_id.in_(orden_ids))
                
            pendientes = self.session.execute(query_pdte).scalar_one() if pdte_ids else 0
            autorizadas = self.session.execute(query_aut).scalar_one() if aut_ids else 0
            con_error = self.session.execute(query_err).scalar_one() if err_ids else 0
        except Exception:
            pendientes = 0
            autorizadas = 0
            con_error = 0
            
        return {
            "total_generadas": total_generadas,
            "pendientes": pendientes,
            "autorizadas": autorizadas,
            "con_error": con_error
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
        from sar.src.storage.models import Desarrollo, Delegacion
        stmt = select(Desarrollo, Delegacion.nombre).join(Delegacion).where(Desarrollo.activo == True).order_by(Desarrollo.nombre)
        results = self.session.execute(stmt).all()
        return [
            {
                "desarrollo_id": d[0].desarrollo_id,
                "nombre": d[0].nombre,
                "delegacion_id": d[0].delegacion_id,
                "delegacion_nombre": d[1]
            }
            for d in results
        ]

    def save_desarrollo(self, nombre: str, delegacion_id: int) -> dict:
        from sar.src.storage.models import Desarrollo
        d = Desarrollo(nombre=nombre.strip().upper(), delegacion_id=delegacion_id, activo=True)
        self.session.add(d)
        self.session.flush()
        return {"desarrollo_id": d.desarrollo_id, "nombre": d.nombre, "delegacion_id": d.delegacion_id}

    def get_referencias_facturadas_paginated(
        self, limit: int = 200, offset: int = 0, search_text: str = "", concepto_id: int = None, rfc_id: int = None, filter_assigned: str = "Todos"
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
            
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        # We need a view or a direct query that has the fields we need.
        # Let's write the query to select the fields from vw_referencias_detalle.
        # We also need concept_id. Wait! Does vw_referencias_detalle have concept_id?
        # Let's check vw_referencias_detalle definition:
        # og.folio AS folio_orden, r.grupo_id, rfc.razon_social AS rfc_razon_social,
        # c.nombre AS concepto_nombre, d.nombre AS delegacion_nombre, ...
        # c.nombre is the concept name. It doesn't have concepto_id, but we can join with grupo_referencia to get it.
        # Let's write the query selecting directly from tables or join with grupo_referencia:
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
            LEFT JOIN sar_archivo.lote_detalle ld ON r.referencia_id = ld.referencia_id
            LEFT JOIN sar_archivo.lote_asignacion la ON ld.lote_asignacion_id = la.lote_asignacion_id
            LEFT JOIN sar_catalogo.notaria n ON la.notaria_id = n.notaria_id
            LEFT JOIN sar_catalogo.colaborador col ON la.colaborador_id = col.colaborador_id
            LEFT JOIN sar_catalogo.desarrollo des ON ld.desarrollo_id = des.desarrollo_id
        """
        
        # Modify conditions to use table aliases
        conditions_sql = []
        if filter_assigned == "Disponible":
            conditions_sql.append("es.codigo = 'FACTURADA'")
            conditions_sql.append("ld.lote_detalle_id IS NULL")
        elif filter_assigned == "Asignada":
            conditions_sql.append("es.codigo = 'ASIGNADA'")
        else: # Todos
            conditions_sql.append("es.codigo IN ('FACTURADA', 'ASIGNADA')")
            
        if concepto_id:
            conditions_sql.append("gr.concepto_id = :concepto_id")
        if rfc_id:
            conditions_sql.append("gr.rfc_id = :rfc_id")
            
        if search_text:
            search_conds = [
                "r.referencia_portal ILIKE :search",
                "rfc.razon_social ILIKE :search",
                "c.nombre ILIKE :search",
                "d.nombre ILIKE :search",
                "u.nombre ILIKE :search",
                "ld.cliente ILIKE :search"
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
                ld.lote_detalle_id IS NOT NULL AS asignada,
                COALESCE(n.nombre, col.nombre, '') AS asignado_a,
                la.tipo_destino AS tipo_asignacion,
                la.solicitante_externo AS solicitante_externo,
                la.fecha AS fecha_asignacion,
                des.nombre AS desarrollo_nombre,
                ld.cliente AS cliente_nombre,
                ld.mz, ld.lote, ld.edif, ld.viv, ld.folio_electronico
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
                "folio_electronico": row.folio_electronico or ""
            })
            
        return res, total_count

    def crear_lote_asignacion(
        self, tipo_destino: str, notaria_id: Optional[int], colaborador_id: Optional[int],
        solicitante_externo: Optional[str], observaciones: Optional[str], usuario_creacion: int,
        detalles_list: List[dict]
    ) -> int:
        from sar.src.storage.models import LoteAsignacion, LoteDetalle, Referencia
        
        lote = LoteAsignacion(
            tipo_destino=tipo_destino,
            notaria_id=notaria_id,
            colaborador_id=colaborador_id,
            solicitante_externo=solicitante_externo.strip() if solicitante_externo else None,
            observaciones=observaciones,
            usuario_creacion=usuario_creacion
        )
        self.session.add(lote)
        self.session.flush() # Generate lote_asignacion_id

        estado_asignada_id = self._get_estado_id("referencia", "ASIGNADA")

        for d in detalles_list:
            det = LoteDetalle(
                lote_asignacion_id=lote.lote_asignacion_id,
                cliente=d["cliente"].strip().upper(),
                desarrollo_id=d["desarrollo_id"],
                fecha_solicitud=d.get("fecha_solicitud"),
                ubicacion=d.get("ubicacion"),
                mz=d.get("mz"),
                lote=d.get("lote"),
                edif=d.get("edif"),
                viv=d.get("viv"),
                folio_electronico=d.get("folio_electronico"),
                estatus_primer_aviso=d.get("estatus_primer_aviso"),
                credito_titular=d.get("credito_titular"),
                pa=d.get("pa"),
                delegacion=d.get("delegacion"),
                concepto_solicitado=d["concepto_solicitado"],
                referencia_id=d.get("referencia_id"),
                referencia_asignada=d["referencia_asignada"]
            )
            self.session.add(det)
            
            # If reference exists in DB, update status to ASIGNADA
            if d.get("referencia_id"):
                ref = self.session.get(Referencia, d["referencia_id"])
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
                (SELECT COUNT(*) FROM sar_archivo.lote_detalle ld WHERE ld.lote_asignacion_id = la.lote_asignacion_id) AS total_referencias
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

    def get_lote_detalles(self, lote_asignacion_id: int) -> List[dict]:
        from sqlalchemy import text
        stmt = text("""
            SELECT 
                ld.lote_detalle_id,
                ld.cliente,
                des.nombre AS desarrollo_nombre,
                ld.fecha_solicitud,
                ld.ubicacion,
                ld.mz,
                ld.lote,
                ld.edif,
                ld.viv,
                ld.folio_electronico,
                ld.estatus_primer_aviso,
                ld.credito_titular,
                ld.pa,
                ld.delegacion,
                ld.concepto_solicitado,
                ld.referencia_asignada,
                d.nombre AS delegacion_nombre
            FROM sar_archivo.lote_detalle ld
            JOIN sar_catalogo.desarrollo des ON ld.desarrollo_id = des.desarrollo_id
            JOIN sar_catalogo.delegacion d ON des.delegacion_id = d.delegacion_id
            WHERE ld.lote_asignacion_id = :lote_id
            ORDER BY ld.lote_detalle_id ASC
        """)
        results = self.session.execute(stmt, {"lote_id": lote_asignacion_id}).all()
        return [
            {
                "lote_detalle_id": row.lote_detalle_id,
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
                "estatus_primer_aviso": row.estatus_primer_aviso or "",
                "credito_titular": row.credito_titular or "",
                "pa": row.pa or "",
                "delegacion_original": row.delegacion or "",
                "concepto": row.concepto_solicitado,
                "referencia": row.referencia_asignada
            }
            for row in results
        ]

