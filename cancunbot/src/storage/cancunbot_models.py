"""
CancunBot — Modelos ORM de SQLAlchemy 2.0
Mapea el esquema cancunbot_produccion en la base de datos sar_db.
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


class LoteFolio(Base):
    """Mapea la tabla lote_folio que agrupa folios de entrada."""
    __tablename__ = "lote_folio"
    __table_args__ = {"schema": "cancunbot_produccion"}

    lote_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
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
    estado: Mapped[EstadoSistema] = relationship()
    usuario: Mapped[Usuario] = relationship()
    folios: Mapped[List["FolioCancun"]] = relationship(back_populates="lote", cascade="all, delete-orphan")


class FolioCancun(Base):
    """Mapea un folio individual a descargar."""
    __tablename__ = "folio_cancun"
    __table_args__ = {"schema": "cancunbot_produccion"}

    folio_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("cancunbot_produccion.lote_folio.lote_id", ondelete="CASCADE"), nullable=False)
    folio_electronico: Mapped[Optional[str]] = mapped_column(String(100))
    folio_pase_caja: Mapped[Optional[str]] = mapped_column(String(100))
    tipo_folio: Mapped[str] = mapped_column(String(20), default="ELECTRONICO", nullable=False)
    intentos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ultimo_error: Mapped[Optional[str]] = mapped_column(Text)
    estado_id: Mapped[int] = mapped_column(ForeignKey("sar_catalogo.estado_sistema.estado_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relaciones
    lote: Mapped[LoteFolio] = relationship(back_populates="folios")
    estado: Mapped[EstadoSistema] = relationship()
    recibo: Mapped[Optional["ReciboCancun"]] = relationship(back_populates="folio", cascade="all, delete-orphan")


class ReciboCancun(Base):
    """Mapea los datos extraídos del PDF del recibo."""
    __tablename__ = "recibo_cancun"
    __table_args__ = {"schema": "cancunbot_produccion"}

    recibo_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    folio_id: Mapped[int] = mapped_column(ForeignKey("cancunbot_produccion.folio_cancun.folio_id", ondelete="CASCADE"), unique=True, nullable=False)
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
    datos_adicionales: Mapped[Optional[dict]] = mapped_column(JSON)
    pdf_nombre: Mapped[Optional[str]] = mapped_column(String(500))
    pdf_ruta: Mapped[Optional[str]] = mapped_column(String(1000))
    hash_sha256: Mapped[Optional[str]] = mapped_column(String(64))
    correo_factura: Mapped[Optional[str]] = mapped_column(String(200))
    padron: Mapped[Optional[str]] = mapped_column(String(100))
    clave_catastral: Mapped[Optional[str]] = mapped_column(String(100))
    estado_id: Mapped[int] = mapped_column(ForeignKey("sar_catalogo.estado_sistema.estado_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relaciones
    folio: Mapped[FolioCancun] = relationship(back_populates="recibo")
    estado: Mapped[EstadoSistema] = relationship()
    factura: Mapped[Optional["FacturaCancun"]] = relationship(back_populates="recibo", cascade="all, delete-orphan")


class FacturaCancun(Base):
    """Mapea los datos del CFDI / Factura generada."""
    __tablename__ = "factura_cancun"
    __table_args__ = {"schema": "cancunbot_produccion"}

    factura_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    recibo_id: Mapped[int] = mapped_column(ForeignKey("cancunbot_produccion.recibo_cancun.recibo_id", ondelete="RESTRICT"), unique=True, nullable=False)
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
