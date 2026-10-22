"""
CancunBot — Modelos ORM de SQLAlchemy 2.0
Mapea el esquema satc_produccion en la base de datos sar_db.
"""
from datetime import datetime, date, time
from typing import List, Optional
from sqlalchemy import (
    ForeignKey,
    String,
    Text,
    Integer,
    Numeric,
    Boolean,
    Date,
    Time,
    DateTime,
    JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Reutilizar la clase Base del SAR para compartir el mismo Metadata
from sar.src.storage.models import Base, Usuario, EstadoSistema


class OrdenCancun(Base):
    """Mapea la tabla orden_cancun que agrupa N lotes de folios."""
    __tablename__ = "orden_cancun"
    __table_args__ = {"schema": "satc_produccion"}

    orden_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    folio_orden: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    total_lotes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_folios: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    folios_procesados: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    folios_error: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    folios_facturados: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estado_id: Mapped[int] = mapped_column(ForeignKey("sar_catalogo.estado_sistema.estado_id"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("sar_seguridad.usuario.usuario_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relaciones
    estado: Mapped[EstadoSistema] = relationship()
    usuario: Mapped[Usuario] = relationship()
    lotes: Mapped[List["LoteFolio"]] = relationship(back_populates="orden", cascade="all, delete-orphan")


class LoteFolio(Base):
    """Mapea la tabla lote_folio que agrupa folios de entrada."""
    __tablename__ = "lote_folio"
    __table_args__ = {"schema": "satc_produccion"}

    lote_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    orden_id: Mapped[Optional[int]] = mapped_column(ForeignKey("satc_produccion.orden_cancun.orden_id", ondelete="SET NULL"), nullable=True)
    folio_lote: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    origen: Mapped[str] = mapped_column(String(20), default="EXCEL", nullable=False)
    total_folios: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    folios_procesados: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    folios_error: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    folios_facturados: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    archivo_excel: Mapped[Optional[str]] = mapped_column(String(500))
    estado_id: Mapped[int] = mapped_column(ForeignKey("sar_catalogo.estado_sistema.estado_id"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("sar_seguridad.usuario.usuario_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relaciones
    orden: Mapped[Optional[OrdenCancun]] = relationship(back_populates="lotes")
    estado: Mapped[EstadoSistema] = relationship()
    usuario: Mapped[Usuario] = relationship()
    folios: Mapped[List["FolioCancun"]] = relationship(back_populates="lote", cascade="all, delete-orphan")


class FolioCancun(Base):
    """Mapea un folio individual a descargar."""
    __tablename__ = "folio_cancun"
    __table_args__ = {"schema": "satc_produccion"}

    folio_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("satc_produccion.lote_folio.lote_id", ondelete="CASCADE"), nullable=False)
    folio_electronico: Mapped[Optional[str]] = mapped_column(String(100))
    folio_pase_caja: Mapped[Optional[str]] = mapped_column(String(100))
    tipo_folio: Mapped[str] = mapped_column(String(20), default="ELECTRONICO", nullable=False)
    intentos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ultimo_error: Mapped[Optional[str]] = mapped_column(Text)
    estado_id: Mapped[int] = mapped_column(ForeignKey("sar_catalogo.estado_sistema.estado_id"), nullable=False)
    rfc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sar_catalogo.rfc.rfc_id", ondelete="SET NULL"))
    desarrollo_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sar_catalogo.desarrollo.desarrollo_id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relaciones
    lote: Mapped[LoteFolio] = relationship(back_populates="folios")
    estado: Mapped[EstadoSistema] = relationship()
    recibo: Mapped[Optional["ReciboCancun"]] = relationship(back_populates="folio", cascade="all, delete-orphan")
    
    # Importar relaciones del SAR dinámicamente o por cadena
    rfc_asoc = relationship("Rfc", foreign_keys=[rfc_id])
    desarrollo_asoc = relationship("Desarrollo", foreign_keys=[desarrollo_id])


class ReciboCancun(Base):
    """Mapea los datos extraídos del PDF del recibo."""
    __tablename__ = "recibo_cancun"
    __table_args__ = {"schema": "satc_produccion"}

    recibo_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    folio_id: Mapped[int] = mapped_column(ForeignKey("satc_produccion.folio_cancun.folio_id", ondelete="CASCADE"), unique=True, nullable=False)
    folio_pase_caja: Mapped[Optional[str]] = mapped_column(String(100))
    folio_electronico: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    fecha_expedicion: Mapped[Optional[date]] = mapped_column(Date)
    hora_expedicion: Mapped[Optional[time]] = mapped_column(Time)
    lugar_expedicion: Mapped[Optional[str]] = mapped_column(String(300))
    rfc: Mapped[Optional[str]] = mapped_column(String(13))
    contribucion: Mapped[Optional[str]] = mapped_column(String(300))
    nombre_contribuyente: Mapped[Optional[str]] = mapped_column(String(500))
    concepto: Mapped[Optional[str]] = mapped_column(Text)
    total: Mapped[Optional[float]] = mapped_column(Numeric(14, 2))
    forma_pago: Mapped[Optional[str]] = mapped_column(String(100))
    detalle_concepto: Mapped[Optional[dict]] = mapped_column(JSON)
    pdf_nombre: Mapped[Optional[str]] = mapped_column(String(500))
    pdf_ruta: Mapped[Optional[str]] = mapped_column(String(1000))
    hash_sha256: Mapped[Optional[str]] = mapped_column(String(64))
    correo_factura: Mapped[Optional[str]] = mapped_column(String(200))
    padron: Mapped[Optional[str]] = mapped_column(String(100))
    clave_catastral: Mapped[Optional[str]] = mapped_column(String(100))
    sm: Mapped[Optional[str]] = mapped_column(String(50))
    mz: Mapped[Optional[str]] = mapped_column(String(50))
    l: Mapped[Optional[str]] = mapped_column(String(50))
    estado_id: Mapped[int] = mapped_column(ForeignKey("sar_catalogo.estado_sistema.estado_id"), nullable=False)
    rfc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sar_catalogo.rfc.rfc_id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relaciones
    folio: Mapped[FolioCancun] = relationship(back_populates="recibo")
    estado: Mapped[EstadoSistema] = relationship()
    factura: Mapped[Optional["FacturaCancun"]] = relationship(back_populates="recibo", cascade="all, delete-orphan")
    rfc_asoc = relationship("Rfc", foreign_keys=[rfc_id])


class FacturaCancun(Base):
    """Mapea los datos del CFDI / Factura generada."""
    __tablename__ = "factura_cancun"
    __table_args__ = {"schema": "satc_produccion"}

    factura_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    recibo_id: Mapped[int] = mapped_column(ForeignKey("satc_produccion.recibo_cancun.recibo_id", ondelete="RESTRICT"), unique=True, nullable=False)
    uuid_cfdi: Mapped[Optional[str]] = mapped_column(String(36), unique=True)
    folio_fiscal: Mapped[Optional[str]] = mapped_column(String(100))
    rfc_emisor: Mapped[Optional[str]] = mapped_column(String(13))
    rfc_receptor: Mapped[Optional[str]] = mapped_column(String(13))
    razon_social_receptor: Mapped[Optional[str]] = mapped_column(String(500))
    cp_receptor: Mapped[Optional[str]] = mapped_column(String(10))
    fecha_timbrado: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    pdf_path: Mapped[Optional[str]] = mapped_column(String(1000))
    xml_path: Mapped[Optional[str]] = mapped_column(String(1000))
    datos_adicionales: Mapped[Optional[dict]] = mapped_column(JSON)
    estado: Mapped[str] = mapped_column(String(30), default="PENDIENTE", nullable=False)
    mensaje_error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relaciones
    recibo: Mapped[ReciboCancun] = relationship(back_populates="factura")


# =============================================================================
# MODELOS DE GOBERNANZA DEL CICLO DE VIDA DE VIVIENDAS Y TRÁMITES (SATC)
# =============================================================================

class TipoTramite(Base):
    """Mapea el catálogo de trámites municipales y derechos."""
    __tablename__ = "tipo_tramite"
    __table_args__ = {"schema": "satc_catalogo"}

    tipo_tramite_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    aplica_a: Mapped[str] = mapped_column(String(30), default="AMBOS", nullable=False)
    etapa_disparador: Mapped[str] = mapped_column(String(30), nullable=False)
    dias_vigencia: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    es_obligatorio: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class EstadoVivienda(Base):
    """Mapea el catálogo de estados del ciclo de vida físico-comercial de la vivienda."""
    __tablename__ = "estado_vivienda"
    __table_args__ = {"schema": "satc_catalogo"}

    estado_vivienda_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(250))
    orden_flujo: Mapped[int] = mapped_column(Integer, nullable=False)
    permite_venta: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    permite_escrituracion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class EstadoTramite(Base):
    """Mapea el catálogo de estados operativos y financieros del trámite."""
    __tablename__ = "estado_tramite"
    __table_args__ = {"schema": "satc_catalogo"}

    estado_tramite_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    fase: Mapped[str] = mapped_column(String(50), nullable=False)
    es_bloqueante: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    es_terminal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RegimenCondominio(Base):
    """Mapea el macro-lote fiduciario del régimen en condominio."""
    __tablename__ = "regimen"
    __table_args__ = {"schema": "satc_catalogo"}

    regimen_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    desarrollo_id: Mapped[int] = mapped_column(ForeignKey("sar_catalogo.desarrollo.desarrollo_id"), nullable=False)
    nombre_regimen: Mapped[str] = mapped_column(String(200), nullable=False)
    sm: Mapped[Optional[str]] = mapped_column(String(50))
    mz: Mapped[str] = mapped_column(String(50), nullable=False)
    lt: Mapped[str] = mapped_column(String(50), nullable=False)
    total_upes: Mapped[int] = mapped_column(Integer, nullable=False)
    upes_generadas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    licencia_construccion_matriz: Mapped[Optional[str]] = mapped_column(String(100))
    clave_catastral_matriz: Mapped[Optional[str]] = mapped_column(String(100))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relaciones
    desarrollo = relationship("Desarrollo", foreign_keys=[desarrollo_id])
    viviendas: Mapped[List["Vivienda"]] = relationship(back_populates="regimen")


class Vivienda(Base):
    """Mapea cada unidad privativa o espacio bajo Régimen de Condominio (Normalizado)."""
    __tablename__ = "vivienda"
    __table_args__ = {"schema": "satc_catalogo"}

    vivienda_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    regimen_id: Mapped[int] = mapped_column(ForeignKey("satc_catalogo.regimen.regimen_id", ondelete="RESTRICT"), nullable=False)
    
    # Identificación Urbana y Física
    numero_oficial: Mapped[Optional[str]] = mapped_column(String(50))
    interior: Mapped[str] = mapped_column(String(50), nullable=False)
    edificio: Mapped[Optional[str]] = mapped_column(String(50))
    nivel: Mapped[Optional[str]] = mapped_column(String(30))
    calle: Mapped[Optional[str]] = mapped_column(String(200))
    
    # Vocación y Régimen
    destino: Mapped[str] = mapped_column(String(30), default="HABITACIONAL", nullable=False)
    espacio: Mapped[str] = mapped_column(String(30), default="VIVIENDA", nullable=False)
    
    # Identidad Jurídica (RPP) y Catastral
    folio_electronico: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    fecha_alta_folio: Mapped[Optional[date]] = mapped_column(Date)
    clave_catastral: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    fecha_alta_cc: Mapped[Optional[date]] = mapped_column(Date)
    padron: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    
    # Ciclo y Auditoría
    estado_vivienda_id: Mapped[int] = mapped_column(ForeignKey("satc_catalogo.estado_vivienda.estado_vivienda_id"), nullable=False)
    fecha_escrituracion: Mapped[Optional[date]] = mapped_column(Date)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relaciones Soberanas
    regimen: Mapped["RegimenCondominio"] = relationship(back_populates="viviendas")
    estado: Mapped[EstadoVivienda] = relationship()
    tramites: Mapped[List["TramiteVivienda"]] = relationship(back_populates="vivienda", cascade="all, delete-orphan")

    @property
    def desarrollo(self):
        """Propiedad delegada: el desarrollo se resuelve a través del régimen matriz sin redundancia en BD."""
        return self.regimen.desarrollo if self.regimen else None

    @property
    def ubicacion_macro(self) -> str:
        """Formatea SM, MZ y LT heredados del régimen matriz."""
        if not self.regimen:
            return ""
        return f"SM {self.regimen.sm or '-'}, MZ {self.regimen.mz}, LT {self.regimen.lt}"


class TramiteVivienda(Base):
    """Mapea el expediente del ciclo de vida de un trámite por vivienda o régimen."""
    __tablename__ = "tramite_vivienda"
    __table_args__ = {"schema": "satc_produccion"}

    tramite_vivienda_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    solicitud_tramite_id: Mapped[Optional[int]] = mapped_column(ForeignKey("satc_produccion.solicitud_tramite.solicitud_tramite_id", ondelete="SET NULL"))
    vivienda_id: Mapped[Optional[int]] = mapped_column(ForeignKey("satc_catalogo.vivienda.vivienda_id", ondelete="CASCADE"))
    regimen_id: Mapped[Optional[int]] = mapped_column(ForeignKey("satc_catalogo.regimen.regimen_id", ondelete="CASCADE"))
    tipo_tramite_id: Mapped[int] = mapped_column(ForeignKey("satc_catalogo.tipo_tramite.tipo_tramite_id"), nullable=False)
    estado_tramite_id: Mapped[int] = mapped_column(ForeignKey("satc_catalogo.estado_tramite.estado_tramite_id"), nullable=False)
    folio_pase_caja: Mapped[Optional[str]] = mapped_column(String(100))
    folio_electronico: Mapped[Optional[str]] = mapped_column(String(100))
    recibo_id: Mapped[Optional[int]] = mapped_column(ForeignKey("satc_produccion.recibo_cancun.recibo_id", ondelete="SET NULL"))
    factura_id: Mapped[Optional[int]] = mapped_column(ForeignKey("satc_produccion.factura_cancun.factura_id", ondelete="SET NULL"))
    orden_compra_erp: Mapped[Optional[str]] = mapped_column(String(50))
    poliza_comprobacion_erp: Mapped[Optional[str]] = mapped_column(String(50))
    comprobado_erp: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    fecha_conclusion: Mapped[Optional[date]] = mapped_column(Date)
    usuario_responsable_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sar_seguridad.usuario.usuario_id", ondelete="SET NULL"))
    observaciones: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relaciones
    solicitud_tramite: Mapped[Optional["SolicitudTramite"]] = relationship(back_populates="tramites")
    vivienda: Mapped[Optional[Vivienda]] = relationship(back_populates="tramites")
    regimen: Mapped[Optional[RegimenCondominio]] = relationship()
    tipo_tramite: Mapped[TipoTramite] = relationship()
    estado: Mapped[EstadoTramite] = relationship()
    recibo: Mapped[Optional[ReciboCancun]] = relationship()
    factura: Mapped[Optional[FacturaCancun]] = relationship()
    usuario_responsable = relationship("Usuario", foreign_keys=[usuario_responsable_id])
    requisitos: Mapped[List["RequisitoDocumento"]] = relationship(back_populates="tramite", cascade="all, delete-orphan")


class OrdenTramite(Base):
    """Mapea la macro-orden ejecutiva de trámites (Vía B paralela a orden_cancun)."""
    __tablename__ = "orden_tramite"
    __table_args__ = {"schema": "satc_produccion"}

    orden_tramite_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    folio_orden: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    desarrollo_id: Mapped[int] = mapped_column(ForeignKey("sar_catalogo.desarrollo.desarrollo_id"), nullable=False)
    regimen_id: Mapped[Optional[int]] = mapped_column(ForeignKey("satc_catalogo.regimen.regimen_id", ondelete="SET NULL"))
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    total_solicitudes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_viviendas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_concluidos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_comprobados_erp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estado_id: Mapped[int] = mapped_column(ForeignKey("satc_catalogo.estado_tramite.estado_tramite_id"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("sar_seguridad.usuario.usuario_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relaciones
    desarrollo = relationship("Desarrollo", foreign_keys=[desarrollo_id])
    regimen = relationship("RegimenCondominio", foreign_keys=[regimen_id])
    estado: Mapped[EstadoTramite] = relationship()
    usuario = relationship("Usuario", foreign_keys=[usuario_id])
    solicitudes: Mapped[List["SolicitudTramite"]] = relationship(back_populates="orden", cascade="all, delete-orphan")


class SolicitudTramite(Base):
    """Mapea el paquete de radicación de trámites ante el municipio (Vía B paralela a lote_folio)."""
    __tablename__ = "solicitud_tramite"
    __table_args__ = {"schema": "satc_produccion"}

    solicitud_tramite_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    orden_tramite_id: Mapped[int] = mapped_column(ForeignKey("satc_produccion.orden_tramite.orden_tramite_id", ondelete="CASCADE"), nullable=False)
    folio_solicitud: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    tipo_tramite_id: Mapped[int] = mapped_column(ForeignKey("satc_catalogo.tipo_tramite.tipo_tramite_id"), nullable=False)
    expediente_municipal: Mapped[Optional[str]] = mapped_column(String(100))
    fecha_ingreso_municipio: Mapped[Optional[date]] = mapped_column(Date)
    total_viviendas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    viviendas_procesadas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    viviendas_facturadas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    viviendas_concluidas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    archivo_origen: Mapped[Optional[str]] = mapped_column(String(500))
    estado_id: Mapped[int] = mapped_column(ForeignKey("satc_catalogo.estado_tramite.estado_tramite_id"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("sar_seguridad.usuario.usuario_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relaciones
    orden: Mapped[OrdenTramite] = relationship(back_populates="solicitudes")
    tipo_tramite: Mapped[TipoTramite] = relationship()
    estado: Mapped[EstadoTramite] = relationship()
    usuario = relationship("Usuario", foreign_keys=[usuario_id])
    tramites: Mapped[List["TramiteVivienda"]] = relationship(back_populates="solicitud_tramite")


class RequisitoDocumento(Base):
    """Mapea las evidencias documentales de un trámite resguardadas con hash SHA-256."""
    __tablename__ = "requisito_documento"
    __table_args__ = {"schema": "satc_produccion"}

    documento_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tramite_vivienda_id: Mapped[int] = mapped_column(ForeignKey("satc_produccion.tramite_vivienda.tramite_vivienda_id", ondelete="CASCADE"), nullable=False)
    tipo_documento: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    ruta_archivo: Mapped[str] = mapped_column(String(1000), nullable=False)
    hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    tamano_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_emision: Mapped[Optional[date]] = mapped_column(Date)
    fecha_vencimiento: Mapped[Optional[date]] = mapped_column(Date)
    vigente: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relaciones
    tramite: Mapped[TramiteVivienda] = relationship(back_populates="requisitos")


# =============================================================================
# MODELOS DE CONFIGURACIÓN Y EXTRACCIÓN METADATA-DRIVEN (satc_configuracion)
# =============================================================================

class CampoCanonico(Base):
    """Mapea el catálogo de campos canónicos de negocio para extracción documental."""
    __tablename__ = "campo_canonico"
    __table_args__ = {"schema": "satc_configuracion"}

    campo_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relaciones
    anclas: Mapped[List["CampoEtiquetaAncla"]] = relationship(back_populates="campo", cascade="all, delete-orphan")
    formatos: Mapped[List["CampoFormatoMunicipio"]] = relationship(back_populates="campo", cascade="all, delete-orphan")


class CampoEtiquetaAncla(Base):
    """Mapea variaciones de escritura y anclas OCR para localizar campos en documentos."""
    __tablename__ = "campo_etiqueta_ancla"
    __table_args__ = {"schema": "satc_configuracion"}

    etiqueta_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    campo_id: Mapped[int] = mapped_column(ForeignKey("satc_configuracion.campo_canonico.campo_id", ondelete="CASCADE"), nullable=False)
    etiqueta: Mapped[str] = mapped_column(String(100), nullable=False)
    regex_ancla: Mapped[str] = mapped_column(Text, nullable=False)
    prioridad: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relaciones
    campo: Mapped[CampoCanonico] = relationship(back_populates="anclas")


class CampoFormatoMunicipio(Base):
    """Mapea reglas de validación y extracción estructural por jurisdicción municipal."""
    __tablename__ = "campo_formato_municipio"
    __table_args__ = {"schema": "satc_configuracion"}

    formato_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    campo_id: Mapped[int] = mapped_column(ForeignKey("satc_configuracion.campo_canonico.campo_id", ondelete="CASCADE"), nullable=False)
    municipio_id: Mapped[int] = mapped_column(ForeignKey("sar_catalogo.municipio.municipio_id", ondelete="RESTRICT"), nullable=False)
    nombre_variante: Mapped[str] = mapped_column(String(100), nullable=False)
    prioridad: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    regex_extraccion: Mapped[str] = mapped_column(Text, nullable=False)
    regex_validacion: Mapped[str] = mapped_column(Text, nullable=False)
    longitud_min: Mapped[Optional[int]] = mapped_column(Integer)
    longitud_max: Mapped[Optional[int]] = mapped_column(Integer)
    remover_caracteres: Mapped[Optional[str]] = mapped_column(String(50), default=" -/")
    permite_sliding_window: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    descripcion_error: Mapped[Optional[str]] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relaciones
    campo: Mapped[CampoCanonico] = relationship(back_populates="formatos")
    municipio = relationship("Municipio", foreign_keys=[municipio_id])


