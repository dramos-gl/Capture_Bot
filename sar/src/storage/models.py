"""SQLAlchemy 2.0 ORM models mapping the physical database schema of SAR."""

from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import (
    ForeignKey,
    String,
    Text,
    Integer,
    Numeric,
    Boolean,
    Date,
    DateTime,
    JSON,
    Table,
    Column
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ===========================================================================
# TABLAS INTERMEDIAS (MANY-TO-MANY RELATIONSHIP ASSOC TABLES)
# ===========================================================================

usuario_rol = Table(
    "usuario_rol",
    Base.metadata,
    Column("usuario_id", ForeignKey("sar_seguridad.usuario.usuario_id", ondelete="CASCADE"), primary_key=True),
    Column("rol_id", ForeignKey("sar_seguridad.rol.rol_id", ondelete="CASCADE"), primary_key=True),
    schema="sar_seguridad"
)

rol_permiso = Table(
    "rol_permiso",
    Base.metadata,
    Column("rol_id", ForeignKey("sar_seguridad.rol.rol_id", ondelete="CASCADE"), primary_key=True),
    Column("permiso_id", ForeignKey("sar_seguridad.permiso.permiso_id", ondelete="CASCADE"), primary_key=True),
    schema="sar_seguridad"
)

rol_app_modulo = Table(
    "rol_app_modulo",
    Base.metadata,
    Column("rol_id", ForeignKey("sar_seguridad.rol.rol_id", ondelete="CASCADE"), primary_key=True),
    Column("app_modulo_id", ForeignKey("sar_seguridad.app_modulo.app_modulo_id", ondelete="CASCADE"), primary_key=True),
    schema="sar_seguridad"
)


# ===========================================================================
# ESQUEMA: sar_seguridad
# ===========================================================================

class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = {"schema": "sar_seguridad"}

    usuario_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    correo: Mapped[Optional[str]] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relaciones
    roles: Mapped[List["Rol"]] = relationship(secondary=usuario_rol, back_populates="usuarios")
    sesiones: Mapped[List["Sesion"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")


class Rol(Base):
    __tablename__ = "rol"
    __table_args__ = {"schema": "sar_seguridad"}

    rol_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relaciones
    usuarios: Mapped[List["Usuario"]] = relationship(secondary=usuario_rol, back_populates="roles")
    permisos: Mapped[List["Permiso"]] = relationship(secondary=rol_permiso, back_populates="roles")
    app_modulos: Mapped[List["AppModulo"]] = relationship(secondary=rol_app_modulo, back_populates="roles")


class Modulo(Base):
    __tablename__ = "modulo"
    __table_args__ = {"schema": "sar_seguridad"}

    modulo_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relaciones
    permisos: Mapped[List["Permiso"]] = relationship(back_populates="modulo")


class AppModulo(Base):
    """Módulos Maestros (Aplicaciones) del Sistema SAR."""
    __tablename__ = "app_modulo"
    __table_args__ = {"schema": "sar_seguridad"}

    app_modulo_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relaciones
    roles: Mapped[List["Rol"]] = relationship(secondary=rol_app_modulo, back_populates="app_modulos")


class Accion(Base):
    __tablename__ = "accion"
    __table_args__ = {"schema": "sar_seguridad"}

    accion_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relaciones
    permisos: Mapped[List["Permiso"]] = relationship(back_populates="accion")


class Permiso(Base):
    __tablename__ = "permiso"
    __table_args__ = {"schema": "sar_seguridad"}

    permiso_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    modulo_id: Mapped[int] = mapped_column(ForeignKey("sar_seguridad.modulo.modulo_id", ondelete="CASCADE"), nullable=False)
    accion_id: Mapped[int] = mapped_column(ForeignKey("sar_seguridad.accion.accion_id", ondelete="CASCADE"), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relaciones
    modulo: Mapped["Modulo"] = relationship(back_populates="permisos")
    accion: Mapped["Accion"] = relationship(back_populates="permisos")
    roles: Mapped[List["Rol"]] = relationship(secondary=rol_permiso, back_populates="permisos")


class Sesion(Base):
    __tablename__ = "sesion"
    __table_args__ = {"schema": "sar_seguridad"}

    sesion_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("sar_seguridad.usuario.usuario_id", ondelete="CASCADE"), nullable=False)
    equipo_nombre: Mapped[Optional[str]] = mapped_column(String(200))
    equipo_uuid: Mapped[Optional[str]] = mapped_column(String(200))
    ip_equipo: Mapped[Optional[str]] = mapped_column(String(100))
    version_cliente: Mapped[Optional[str]] = mapped_column(String(50))
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    ultimo_heartbeat: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    estado: Mapped[Optional[str]] = mapped_column(String(30))

    # Relaciones
    usuario: Mapped["Usuario"] = relationship(back_populates="sesiones")


# ===========================================================================
# ESQUEMA: sar_catalogo
# ===========================================================================

class Municipio(Base):
    __tablename__ = "municipio"
    __table_args__ = {"schema": "sar_catalogo"}

    municipio_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo_portal: Mapped[Optional[str]] = mapped_column(String(50))
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    activo: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)

    # Relaciones
    delegaciones: Mapped[List["Delegacion"]] = relationship(back_populates="municipio")


class Delegacion(Base):
    __tablename__ = "delegacion"
    __table_args__ = {"schema": "sar_catalogo"}

    delegacion_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    municipio_id: Mapped[int] = mapped_column(ForeignKey("sar_catalogo.municipio.municipio_id", ondelete="RESTRICT"), nullable=False)
    codigo_portal: Mapped[Optional[str]] = mapped_column(String(300))
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    activo: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)

    # Relaciones
    municipio: Mapped["Municipio"] = relationship(back_populates="delegaciones")
    solicitudes: Mapped[List["Solicitud"]] = relationship(back_populates="delegacion")


class Concepto(Base):
    __tablename__ = "concepto"
    __table_args__ = {"schema": "sar_catalogo"}

    concepto_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo_portal: Mapped[Optional[str]] = mapped_column(String(300))
    nombre: Mapped[str] = mapped_column(String(300), nullable=False)
    alias: Mapped[Optional[str]] = mapped_column(String(20))
    activo: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)

    # Relaciones
    grupos_referencia: Mapped[List["GrupoReferencia"]] = relationship(back_populates="concepto")


class Rfc(Base):
    __tablename__ = "rfc"
    __table_args__ = {"schema": "sar_catalogo"}

    rfc_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rfc: Mapped[str] = mapped_column(String(13), unique=True, nullable=False)
    razon_social: Mapped[str] = mapped_column(String(500), nullable=False)
    calle: Mapped[Optional[str]] = mapped_column(String(500))
    no_exterior: Mapped[Optional[str]] = mapped_column(String(50))
    no_interior: Mapped[Optional[str]] = mapped_column(String(50))
    colonia: Mapped[Optional[str]] = mapped_column(String(300))
    codigo_postal: Mapped[Optional[str]] = mapped_column(String(10))
    localidad: Mapped[Optional[str]] = mapped_column(String(300))
    municipio: Mapped[Optional[str]] = mapped_column(String(300))
    estado: Mapped[Optional[str]] = mapped_column(String(300))
    activo: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relaciones
    grupos_referencia: Mapped[List["GrupoReferencia"]] = relationship(back_populates="rfc")


class EstadoSistema(Base):
    __tablename__ = "estado_sistema"
    __table_args__ = {"schema": "sar_catalogo"}

    estado_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    entidad: Mapped[str] = mapped_column(String(100), nullable=False)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(200))


class EventoSistema(Base):
    __tablename__ = "evento_sistema"
    __table_args__ = {"schema": "sar_catalogo"}

    evento_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(300))


# ===========================================================================
# ESQUEMA: sar_produccion
# ===========================================================================

class OrdenGeneracion(Base):
    __tablename__ = "orden_generacion"
    __table_args__ = {"schema": "sar_produccion"}

    orden_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    folio: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    municipio_id: Mapped[int] = mapped_column(ForeignKey("sar_catalogo.municipio.municipio_id"), nullable=False, default=2)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    estado_id: Mapped[int] = mapped_column(ForeignKey("sar_catalogo.estado_sistema.estado_id"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("sar_seguridad.usuario.usuario_id"), nullable=False)

    # Relaciones
    municipio: Mapped["Municipio"] = relationship()
    grupos: Mapped[List["GrupoReferencia"]] = relationship(back_populates="orden", cascade="all, delete-orphan")


class GrupoReferencia(Base):
    __tablename__ = "grupo_referencia"
    __table_args__ = {"schema": "sar_produccion"}

    grupo_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    orden_id: Mapped[int] = mapped_column(ForeignKey("sar_produccion.orden_generacion.orden_id", ondelete="CASCADE"), nullable=False)
    rfc_id: Mapped[int] = mapped_column(ForeignKey("sar_catalogo.rfc.rfc_id"), nullable=False)
    concepto_id: Mapped[int] = mapped_column(ForeignKey("sar_catalogo.concepto.concepto_id"), nullable=False)
    cantidad_solicitada: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad_generada: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    cantidad_autorizada: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    cantidad_rechazada: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    cantidad_expirada: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    cantidad_facturada: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    ultimo_consecutivo: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    estado_id: Mapped[int] = mapped_column(ForeignKey("sar_catalogo.estado_sistema.estado_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relaciones
    orden: Mapped["OrdenGeneracion"] = relationship(back_populates="grupos")
    rfc: Mapped["Rfc"] = relationship(back_populates="grupos_referencia")
    concepto: Mapped["Concepto"] = relationship(back_populates="grupos_referencia")
    solicitudes: Mapped[List["Solicitud"]] = relationship(back_populates="grupo", cascade="all, delete-orphan")
    referencias: Mapped[List["Referencia"]] = relationship(back_populates="grupo", cascade="all, delete-orphan")


class Solicitud(Base):
    __tablename__ = "solicitud"
    __table_args__ = {"schema": "sar_produccion"}

    solicitud_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    grupo_id: Mapped[int] = mapped_column(ForeignKey("sar_produccion.grupo_referencia.grupo_id", ondelete="CASCADE"), nullable=False)
    delegacion_id: Mapped[int] = mapped_column(ForeignKey("sar_catalogo.delegacion.delegacion_id"), nullable=False)
    cantidad_solicitada: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad_generada: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    cantidad_autorizada: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    cantidad_facturada: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    consecutivo_inicio: Mapped[int] = mapped_column(Integer, nullable=False)
    consecutivo_fin: Mapped[int] = mapped_column(Integer, nullable=False)
    ultimo_consecutivo: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    usuario_asignado: Mapped[Optional[int]] = mapped_column(ForeignKey("sar_seguridad.usuario.usuario_id"))
    estado_id: Mapped[int] = mapped_column(ForeignKey("sar_catalogo.estado_sistema.estado_id"), nullable=False)
    fecha_asignacion: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    fecha_inicio: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    fecha_fin: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relaciones
    grupo: Mapped["GrupoReferencia"] = relationship(back_populates="solicitudes")
    delegacion: Mapped["Delegacion"] = relationship(back_populates="solicitudes")
    referencias: Mapped[List["Referencia"]] = relationship(back_populates="solicitud", cascade="all, delete-orphan")


class Referencia(Base):
    __tablename__ = "referencia"
    __table_args__ = {"schema": "sar_produccion"}

    referencia_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    grupo_id: Mapped[int] = mapped_column(ForeignKey("sar_produccion.grupo_referencia.grupo_id", ondelete="CASCADE"), nullable=False)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("sar_produccion.solicitud.solicitud_id", ondelete="CASCADE"), nullable=False)
    consecutivo_grupo: Mapped[int] = mapped_column(Integer, nullable=False)
    referencia_portal: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    importe: Mapped[Optional[float]] = mapped_column(Numeric(14, 2))
    fecha_generacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_vigencia: Mapped[Optional[date]] = mapped_column(Date)
    usuario_asignado: Mapped[Optional[int]] = mapped_column(ForeignKey("sar_seguridad.usuario.usuario_id"))
    estado_id: Mapped[int] = mapped_column(ForeignKey("sar_catalogo.estado_sistema.estado_id"), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    porcentaje: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relaciones
    grupo: Mapped["GrupoReferencia"] = relationship(back_populates="referencias")
    solicitud: Mapped["Solicitud"] = relationship(back_populates="referencias")
    archivos_pdf: Mapped[List["ArchivoPDF"]] = relationship(back_populates="referencia", cascade="all, delete-orphan")
    facturas: Mapped[List["Factura"]] = relationship(back_populates="referencia", cascade="all, delete-orphan")


# ===========================================================================
# ESQUEMA: sar_archivo
# ===========================================================================

class ArchivoPDF(Base):
    __tablename__ = "archivo_pdf"
    __table_args__ = {"schema": "sar_archivo"}

    archivo_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    referencia_id: Mapped[int] = mapped_column(ForeignKey("sar_produccion.referencia.referencia_id", ondelete="CASCADE"), nullable=False)
    tipo_archivo: Mapped[str] = mapped_column(String(50), nullable=False)
    estado_archivo: Mapped[str] = mapped_column(String(30), nullable=False)
    nombre_archivo: Mapped[str] = mapped_column(String(500), nullable=False)
    ruta_archivo: Mapped[str] = mapped_column(String(1000), nullable=False)
    hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    tamano_bytes: Mapped[int] = mapped_column(nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relaciones
    referencia: Mapped["Referencia"] = relationship(back_populates="archivos_pdf")


class Factura(Base):
    __tablename__ = "factura"
    __table_args__ = {"schema": "sar_archivo"}

    factura_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    referencia_id: Mapped[int] = mapped_column(ForeignKey("sar_produccion.referencia.referencia_id", ondelete="RESTRICT"), nullable=False)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    folio: Mapped[Optional[str]] = mapped_column(String(100))
    rfc_emisor: Mapped[str] = mapped_column(String(13), nullable=False)
    fecha_factura: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(1000))
    xml_path: Mapped[Optional[str]] = mapped_column(String(1000))
    estado: Mapped[str] = mapped_column(String(30), nullable=False)

    # Relaciones
    referencia: Mapped["Referencia"] = relationship(back_populates="facturas")
    asignaciones: Mapped[List["Asignacion"]] = relationship(back_populates="factura", cascade="all, delete-orphan")


class Asignacion(Base):
    __tablename__ = "asignacion"
    __table_args__ = {"schema": "sar_archivo"}

    asignacion_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    factura_id: Mapped[int] = mapped_column(ForeignKey("sar_archivo.factura.factura_id", ondelete="CASCADE"), nullable=False)
    usuario_destino: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo_asignacion: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha_asignacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    observaciones: Mapped[Optional[str]] = mapped_column(Text)

    # Relaciones
    factura: Mapped["Factura"] = relationship(back_populates="asignaciones")


# ===========================================================================
# ESQUEMA: sar_auditoria
# ===========================================================================

class AuditoriaLogin(Base):
    __tablename__ = "auditoria_login"
    __table_args__ = {"schema": "sar_auditoria"}

    login_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usuario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sar_seguridad.usuario.usuario_id", ondelete="SET NULL"))
    sesion_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sar_seguridad.sesion.sesion_id", ondelete="SET NULL"))
    fecha_login: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    fecha_logout: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ip: Mapped[Optional[str]] = mapped_column(String(100))
    equipo: Mapped[Optional[str]] = mapped_column(String(200))


class AuditoriaEvento(Base):
    __tablename__ = "auditoria_evento"
    __table_args__ = {"schema": "sar_auditoria"}

    evento_auditoria_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    evento_id: Mapped[int] = mapped_column(ForeignKey("sar_catalogo.evento_sistema.evento_id", ondelete="RESTRICT"), nullable=False)
    usuario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sar_seguridad.usuario.usuario_id", ondelete="SET NULL"))
    sesion_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sar_seguridad.sesion.sesion_id", ondelete="SET NULL"))
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    modulo: Mapped[str] = mapped_column(String(100), nullable=False)
    valor_anterior: Mapped[Optional[dict]] = mapped_column(JSON)
    valor_nuevo: Mapped[Optional[dict]] = mapped_column(JSON)
    detalle: Mapped[Optional[dict]] = mapped_column(JSON)


class AuditoriaError(Base):
    __tablename__ = "auditoria_error"
    __table_args__ = {"schema": "sar_auditoria"}

    error_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usuario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sar_seguridad.usuario.usuario_id", ondelete="SET NULL"))
    sesion_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sar_seguridad.sesion.sesion_id", ondelete="SET NULL"))
    modulo: Mapped[str] = mapped_column(String(100), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


# ===========================================================================
# ESQUEMA: sar_configuracion
# ===========================================================================

class ParametroSistema(Base):
    __tablename__ = "parametro_sistema"
    __table_args__ = {"schema": "sar_configuracion"}

    parametro_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    valor: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class LocalizadorPortal(Base):
    __tablename__ = "localizador_portal"
    __table_args__ = {"schema": "sar_configuracion"}

    localizador_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre_clave: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    label_visible: Mapped[str] = mapped_column(String(200), nullable=False)
    estrategia_selector: Mapped[str] = mapped_column(String(50), nullable=False)
    valor_selector: Mapped[str] = mapped_column(String(500), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(500))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

