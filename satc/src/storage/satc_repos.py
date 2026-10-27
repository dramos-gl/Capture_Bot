"""
CancunBot — Repositorios de Base de Datos (SQLAlchemy 2.0)
Encapsula el acceso y manipulación de datos para las entidades de R2F-Cancún.
"""
import re
import logging
from datetime import datetime, date
from typing import List, Optional, Tuple, Any

from sqlalchemy import select, update, and_, func
from sqlalchemy.orm import Session, selectinload

from sar.src.storage.models import EstadoSistema, Usuario
from satc.src.storage.satc_models import OrdenCancun, LoteFolio, FolioCancun, ReciboCancun, FacturaCancun

logger = logging.getLogger(__name__)


class BaseCancunRepository:
    """Base repository class providing session access."""
    def __init__(self, session: Session):
        self.session = session

    def _get_estado_id(self, entidad: str, codigo: str) -> int:
        """Helper to fetch the primary key ID of a system status."""
        stmt = select(EstadoSistema.estado_id).where(
            and_(EstadoSistema.entidad == entidad, EstadoSistema.codigo == codigo)
        )
        result = self.session.execute(stmt).scalar_one_or_none()
        if not result:
            raise ValueError(f"Estado '{codigo}' para la entidad '{entidad}' no existe en el catálogo.")
        return result


class OrdenCancunRepository(BaseCancunRepository):
    """Encapsulates CRUD and query logic for OrdenCancun."""

    def get_by_id(self, orden_id: int) -> Optional[OrdenCancun]:
        return self.session.get(OrdenCancun, orden_id)

    def generate_next_folio(self) -> str:
        """Generates the next sequential order folio (e.g. ORD-CUN-2026-001)."""
        year = datetime.now().year
        prefix = f"ORD-CUN-{year}-"
        stmt = select(OrdenCancun.folio_orden).where(
            OrdenCancun.folio_orden.like(f"{prefix}%")
        )
        folios = self.session.execute(stmt).scalars().all()
        
        max_seq = 0
        for f in folios:
            try:
                seq = int(f.split("-")[-1])
                if seq > max_seq:
                    max_seq = seq
            except ValueError:
                continue
        return f"{prefix}{str(max_seq + 1).zfill(3)}"

    def create(self, usuario_id: int, descripcion: Optional[str] = None) -> OrdenCancun:
        """Creates a new Cancún order."""
        # Se asigna estado EN_PROCESO o NUEVO usando la entidad genérica del catálogo
        try:
            estado_id = self._get_estado_id("orden_trabajo", "ABIERTA")
        except ValueError:
            estado_id = self._get_estado_id("lote_folio", "NUEVO")

        folio_orden = self.generate_next_folio()
        orden = OrdenCancun(
            folio_orden=folio_orden,
            descripcion=descripcion or f"Orden de procesamiento R2F Cancún {folio_orden}",
            estado_id=estado_id,
            usuario_id=usuario_id,
            total_lotes=0,
            total_folios=0,
            folios_procesados=0,
            folios_error=0,
            folios_facturados=0
        )
        self.session.add(orden)
        self.session.flush()
        return orden

    def list_all(self) -> List[OrdenCancun]:
        stmt = (
            select(OrdenCancun)
            .options(selectinload(OrdenCancun.estado))
            .order_by(OrdenCancun.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def update_metrics_and_status(self, orden_id: int) -> None:
        """Recalcula las métricas agregadas de la orden en base a todos sus lotes asociados."""
        orden = self.session.get(OrdenCancun, orden_id)
        if not orden:
            return

        tot_lotes = self.session.scalar(
            select(func.count(LoteFolio.lote_id)).where(LoteFolio.orden_id == orden_id)
        ) or 0
        tot_folios = self.session.scalar(
            select(func.coalesce(func.sum(LoteFolio.total_folios), 0)).where(LoteFolio.orden_id == orden_id)
        ) or 0
        tot_proc = self.session.scalar(
            select(func.coalesce(func.sum(LoteFolio.folios_procesados), 0)).where(LoteFolio.orden_id == orden_id)
        ) or 0
        tot_err = self.session.scalar(
            select(func.coalesce(func.sum(LoteFolio.folios_error), 0)).where(LoteFolio.orden_id == orden_id)
        ) or 0
        tot_fact = self.session.scalar(
            select(func.coalesce(func.sum(LoteFolio.folios_facturados), 0)).where(LoteFolio.orden_id == orden_id)
        ) or 0

        orden.total_lotes = tot_lotes
        orden.total_folios = tot_folios
        orden.folios_procesados = tot_proc
        orden.folios_error = tot_err
        orden.folios_facturados = tot_fact
        orden.updated_at = datetime.utcnow()
        self.session.flush()


class LoteFolioRepository(BaseCancunRepository):
    """Encapsulates CRUD and query logic for LoteFolio."""

    def get_by_id(self, lote_id: int) -> Optional[LoteFolio]:
        return self.session.get(LoteFolio, lote_id)

    def get_by_folio(self, folio_lote: str) -> Optional[LoteFolio]:
        stmt = select(LoteFolio).where(LoteFolio.folio_lote == folio_lote)
        return self.session.execute(stmt).scalar_one_or_none()

    def generate_next_folio(self) -> str:
        """Generates the next sequential batch folio (e.g. LOT-2026-001)."""
        year = datetime.now().year
        prefix = f"LOT-{year}-"
        stmt = select(LoteFolio.folio_lote).where(
            LoteFolio.folio_lote.like(f"{prefix}%")
        )
        folios = self.session.execute(stmt).scalars().all()
        
        max_seq = 0
        for f in folios:
            try:
                seq = int(f.split("-")[-1])
                if seq > max_seq:
                    max_seq = seq
            except ValueError:
                continue
        return f"{prefix}{str(max_seq + 1).zfill(3)}"

    def create(self, usuario_id: int, origen: str = "EXCEL", descripcion: Optional[str] = None, archivo_excel: Optional[str] = None, orden_id: Optional[int] = None) -> LoteFolio:
        """Creates a new folio batch associated optional to an order."""
        estado_id = self._get_estado_id("lote_folio", "NUEVO")
        folio_lote = self.generate_next_folio()
        
        lote = LoteFolio(
            orden_id=orden_id,
            folio_lote=folio_lote,
            descripcion=descripcion,
            origen=origen,
            archivo_excel=archivo_excel,
            estado_id=estado_id,
            usuario_id=usuario_id,
            total_folios=0,
            folios_procesados=0,
            folios_error=0,
            folios_facturados=0
        )
        self.session.add(lote)
        self.session.flush()

        # Actualizar contadores de la orden si aplica
        if orden_id:
            orden = self.session.get(OrdenCancun, orden_id)
            if orden:
                orden.total_lotes = self.session.scalar(
                    select(func.count(LoteFolio.lote_id)).where(LoteFolio.orden_id == orden_id)
                ) or 0
                self.session.flush()

        return lote

    def list_all(self) -> List[LoteFolio]:
        stmt = select(LoteFolio).order_by(LoteFolio.created_at.desc())
        return list(self.session.execute(stmt).scalars().all())

    def update_metrics_and_status(self, lote_id: int) -> None:
        """Recalculates counts and advances batch status."""
        lote = self.session.get(LoteFolio, lote_id)
        if not lote:
            return

        # Fetch status IDs once
        st_pending = self._get_estado_id("folio_cancun", "PENDIENTE")
        st_error = self._get_estado_id("folio_cancun", "ERROR_DESCARGA")
        st_recibo_ok = self._get_estado_id("folio_cancun", "RECIBO_OK")
        st_facturado = self._get_estado_id("folio_cancun", "FACTURADO")

        # Counts
        total = self.session.scalar(
            select(func.count(FolioCancun.folio_id)).where(FolioCancun.lote_id == lote_id)
        ) or 0
        procesados = self.session.scalar(
            select(func.count(FolioCancun.folio_id)).where(
                and_(FolioCancun.lote_id == lote_id, FolioCancun.estado_id == st_recibo_ok)
            )
        ) or 0
        errores = self.session.scalar(
            select(func.count(FolioCancun.folio_id)).where(
                and_(FolioCancun.lote_id == lote_id, FolioCancun.estado_id == st_error)
            )
        ) or 0
        facturados = self.session.scalar(
            select(func.count(FolioCancun.folio_id)).where(
                and_(FolioCancun.lote_id == lote_id, FolioCancun.estado_id == st_facturado)
            )
        ) or 0

        lote.total_folios = total
        lote.folios_procesados = procesados
        lote.folios_error = errores
        lote.folios_facturados = facturados
        lote.updated_at = datetime.utcnow()

        # Update status
        if total > 0:
            if facturados == total or (procesados + facturados) == total:
                lote.estado_id = self._get_estado_id("lote_folio", "COMPLETADO")
            elif errores > 0 and (procesados + errores + facturados) == total:
                lote.estado_id = self._get_estado_id("lote_folio", "COMPLETADO_PARCIAL")
            else:
                lote.estado_id = self._get_estado_id("lote_folio", "EN_PROCESO")
        self.session.flush()


class FolioCancunRepository(BaseCancunRepository):
    """Encapsulates CRUD and query logic for FolioCancun."""

    def get_by_id(self, folio_id: int) -> Optional[FolioCancun]:
        return self.session.get(FolioCancun, folio_id)

    def create_bulk(self, lote_id: int, folios_list: List[dict]) -> int:
        """
        Inserts multiple folios into a batch.
        
        Args:
            lote_id: ID of the batch
            folios_list: List of dicts representing imported excel records
        """
        estado_id = self._get_estado_id("folio_cancun", "PENDIENTE")
        count = 0
        for item in folios_list:
            tipo = item["tipo_folio"]
            folio_elec = item.get("folio_electronico")
            folio_pase = item.get("folio_pase_caja")
            
            folio = FolioCancun(
                lote_id=lote_id,
                tipo_folio=tipo,
                estado_id=estado_id,
                rfc_id=item.get("rfc_id"),
                desarrollo_id=item.get("desarrollo_id"),
                intentos=0
            )
            if folio_elec:
                folio.folio_electronico = folio_elec.strip()
            if folio_pase:
                folio.folio_pase_caja = folio_pase.strip()
            
            self.session.add(folio)
            count += 1
        
        self.session.flush()
        return count

    def get_pending_downloads(self) -> List[FolioCancun]:
        """Returns all folios pending download for Bot Recibos."""
        estado_id = self._get_estado_id("folio_cancun", "PENDIENTE")
        stmt = select(FolioCancun).where(
            FolioCancun.estado_id == estado_id
        ).order_by(FolioCancun.lote_id, FolioCancun.folio_id)
        return list(self.session.execute(stmt).scalars().all())

    def update_status(self, folio_id: int, status_code: str, error_msg: Optional[str] = None) -> None:
        """Updates the status and error tracking of a folio."""
        folio = self.session.get(FolioCancun, folio_id)
        if folio:
            folio.estado_id = self._get_estado_id("folio_cancun", status_code)
            if status_code == "DESCARGANDO":
                folio.intentos += 1
            if error_msg is not None:
                folio.ultimo_error = error_msg
            folio.updated_at = datetime.utcnow()
            self.session.flush()


class ReciboCancunRepository(BaseCancunRepository):
    """Encapsulates CRUD and query logic for ReciboCancun."""

    def get_by_id(self, recibo_id: int) -> Optional[ReciboCancun]:
        return self.session.get(ReciboCancun, recibo_id)

    def get_by_folio_id(self, folio_id: int) -> Optional[ReciboCancun]:
        stmt = select(ReciboCancun).where(ReciboCancun.folio_id == folio_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def save_extracted_receipt(self, folio_id: int, data: dict) -> ReciboCancun:
        """Stores extracted fields from a downloaded PDF recibo."""
        estado_id = self._get_estado_id("recibo_cancun", "CAPTURADO")
        
        # Check if already exists to overwrite/update
        recibo = self.get_by_folio_id(folio_id)
        if not recibo:
            recibo = ReciboCancun(folio_id=folio_id)
            self.session.add(recibo)

        recibo.folio_pase_caja = data.get("folio_pase_caja")
        recibo.folio_electronico = data.get("folio_electronico")
        recibo.fecha_expedicion = data.get("fecha_expedicion")
        recibo.hora_expedicion = data.get("hora_expedicion")
        recibo.lugar_expedicion = data.get("lugar_expedicion")
        recibo.rfc = data.get("rfc")
        recibo.contribucion = data.get("contribucion")
        recibo.nombre_contribuyente = data.get("nombre_contribuyente")
        recibo.concepto = data.get("concepto")
        recibo.total = data.get("total")
        recibo.forma_pago = data.get("forma_pago")
        recibo.pdf_nombre = data.get("pdf_nombre")
        recibo.pdf_ruta = data.get("pdf_ruta")
        recibo.hash_sha256 = data.get("hash_sha256")
        recibo.correo_factura = data.get("correo_factura")
        recibo.padron = data.get("padron")
        recibo.clave_catastral = data.get("clave_catastral")
        recibo.rfc_id = data.get("rfc_id")
        recibo.sm = data.get("sm")
        recibo.mz = data.get("mz")
        recibo.l = data.get("l")
        recibo.detalle_concepto = data.get("datos_adicionales")
        recibo.estado_id = estado_id
        recibo.updated_at = datetime.utcnow()
        
        self.session.flush()
        return recibo

    def get_pending_billing(self) -> List[ReciboCancun]:
        """Returns recibos ready for billing bot processing."""
        estado_id = self._get_estado_id("recibo_cancun", "PENDIENTE_FACTURAR")
        stmt = select(ReciboCancun).where(
            ReciboCancun.estado_id == estado_id
        ).order_by(ReciboCancun.recibo_id)
        return list(self.session.execute(stmt).scalars().all())

    def get_recibos_paginated(self, limit: int, offset: int, search_text: str = "", estado_filter: str = "Todos") -> Tuple[List[ReciboCancun], int]:
        """Fetches paginated receipts matching search criteria and optional status filters."""
        stmt = select(ReciboCancun)
        
        # Apply filters
        filters = []
        if search_text:
            s_like = f"%{search_text.strip()}%"
            filters.append(
                (ReciboCancun.folio_electronico.like(s_like)) |
                (ReciboCancun.folio_pase_caja.like(s_like)) |
                (ReciboCancun.nombre_contribuyente.like(s_like)) |
                (ReciboCancun.rfc.like(s_like))
            )
            
        if estado_filter and estado_filter != "Todos":
            status_id = self._get_estado_id("recibo_cancun", estado_filter)
            filters.append(ReciboCancun.estado_id == status_id)
            
        if filters:
            stmt = stmt.where(and_(*filters))
            
        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = self.session.execute(count_stmt).scalar() or 0
        
        # Pagination & Ordering
        stmt = stmt.order_by(ReciboCancun.recibo_id.desc()).limit(limit).offset(offset)
        results = list(self.session.execute(stmt).scalars().all())
        
        return results, total_count

    def update_status(self, recibo_id: int, status_code: str) -> None:
        recibo = self.session.get(ReciboCancun, recibo_id)
        if recibo:
            recibo.estado_id = self._get_estado_id("recibo_cancun", status_code)
            recibo.updated_at = datetime.utcnow()
            self.session.flush()


class FacturaCancunRepository(BaseCancunRepository):
    """Encapsulates CRUD and query logic for FacturaCancun."""

    def get_by_id(self, factura_id: int) -> Optional[FacturaCancun]:
        return self.session.get(FacturaCancun, factura_id)

    def get_by_recibo_id(self, recibo_id: int) -> Optional[FacturaCancun]:
        stmt = select(FacturaCancun).where(FacturaCancun.recibo_id == recibo_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def register_billing_attempt(self, recibo_id: int, status: str = "PROCESANDO", error_msg: Optional[str] = None) -> FacturaCancun:
        factura = self.get_by_recibo_id(recibo_id)
        if not factura:
            factura = FacturaCancun(recibo_id=recibo_id)
            self.session.add(factura)
        
        factura.estado = status
        factura.mensaje_error = error_msg
        factura.updated_at = datetime.utcnow()
        self.session.flush()
        return factura

    def register_success(self, recibo_id: int, uuid_cfdi: str, folio_fiscal: str, rfc_emisor: str, rfc_receptor: str, cp_receptor: str, pdf_path: str, xml_path: str) -> FacturaCancun:
        factura = self.get_by_recibo_id(recibo_id)
        if not factura:
            factura = FacturaCancun(recibo_id=recibo_id)
            self.session.add(factura)

        factura.uuid_cfdi = uuid_cfdi
        factura.folio_fiscal = folio_fiscal
        factura.rfc_emisor = rfc_emisor
        factura.rfc_receptor = rfc_receptor
        factura.cp_receptor = cp_receptor
        factura.pdf_path = pdf_path
        factura.xml_path = xml_path
        factura.estado = "FACTURADO"
        factura.mensaje_error = None
        factura.fecha_timbrado = datetime.utcnow()
        factura.updated_at = datetime.utcnow()
        self.session.flush()
        return factura


# =============================================================================
# REPOSITORIOS DEL CICLO DE VIDA DE VIVIENDAS Y TRÁMITES (SATC)
# =============================================================================

from satc.src.storage.satc_models import (
    TipoTramite, EstadoVivienda, EstadoTramite, 
    RegimenCondominio, Vivienda, ViviendaHistorialEstado, TramiteVivienda, RequisitoDocumento,
    CampoCanonico, CampoEtiquetaAncla, CampoFormatoMunicipio
)


class TipoTramiteRepository(BaseCancunRepository):
    """Encapsula operaciones para el catálogo de tipos de trámite."""

    def get_by_id(self, tipo_tramite_id: int) -> Optional[TipoTramite]:
        return self.session.get(TipoTramite, tipo_tramite_id)

    def list_all(self) -> List[TipoTramite]:
        stmt = select(TipoTramite).order_by(TipoTramite.tipo_tramite_id.asc())
        return list(self.session.execute(stmt).scalars().all())

    def save(self, tipo: TipoTramite) -> TipoTramite:
        self.session.add(tipo)
        self.session.flush()
        return tipo


class EstadoViviendaRepository(BaseCancunRepository):
    """Encapsula operaciones para el catálogo de estados del ciclo de vida de la vivienda."""

    def get_by_id(self, estado_vivienda_id: int) -> Optional[EstadoVivienda]:
        return self.session.get(EstadoVivienda, estado_vivienda_id)

    def list_all(self) -> List[EstadoVivienda]:
        stmt = select(EstadoVivienda).order_by(EstadoVivienda.orden_flujo.asc(), EstadoVivienda.estado_vivienda_id.asc())
        return list(self.session.execute(stmt).scalars().all())

    def save(self, estado: EstadoVivienda) -> EstadoVivienda:
        self.session.add(estado)
        self.session.flush()
        return estado


class EstadoTramiteRepository(BaseCancunRepository):
    """Encapsula operaciones para el catálogo de estados operativos de trámites."""

    def get_by_id(self, estado_tramite_id: int) -> Optional[EstadoTramite]:
        return self.session.get(EstadoTramite, estado_tramite_id)

    def list_all(self) -> List[EstadoTramite]:
        stmt = select(EstadoTramite).order_by(EstadoTramite.estado_tramite_id.asc())
        return list(self.session.execute(stmt).scalars().all())

    def save(self, estado: EstadoTramite) -> EstadoTramite:
        self.session.add(estado)
        self.session.flush()
        return estado


class RegimenCondominioRepository(BaseCancunRepository):
    """Encapsula el acceso y manipulación de Regímenes de Condominio (Macro-Lotes)."""

    def get_by_id(self, regimen_id: int) -> Optional[RegimenCondominio]:
        return self.session.get(RegimenCondominio, regimen_id)

    def get_by_desarrollo(self, desarrollo_id: int) -> List[RegimenCondominio]:
        stmt = (
            select(RegimenCondominio)
            .where(RegimenCondominio.desarrollo_id == desarrollo_id)
            .order_by(RegimenCondominio.nombre_regimen.asc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def create(
        self,
        desarrollo_id: int,
        nombre_regimen: str,
        mz: str,
        lt: str,
        total_upes: int,
        sm: Optional[str] = None,
        licencia_matriz: Optional[str] = None,
        clave_catastral_matriz: Optional[str] = None,
    ) -> RegimenCondominio:
        regimen = RegimenCondominio(
            desarrollo_id=desarrollo_id,
            nombre_regimen=nombre_regimen,
            sm=sm,
            mz=mz,
            lt=lt,
            total_upes=total_upes,
            upes_generadas=0,
            licencia_construccion_matriz=licencia_matriz,
            clave_catastral_matriz=clave_catastral_matriz,
            activo=True,
            created_at=datetime.utcnow()
        )
        self.session.add(regimen)
        self.session.flush()
        return regimen

    def list_all(self) -> List[RegimenCondominio]:
        stmt = (
            select(RegimenCondominio)
            .options(selectinload(RegimenCondominio.desarrollo))
            .order_by(RegimenCondominio.regimen_id.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def save(self, regimen: RegimenCondominio) -> RegimenCondominio:
        self.session.add(regimen)
        self.session.flush()
        return regimen

    def increment_upes_generadas(self, regimen_id: int, count: int) -> None:
        regimen = self.get_by_id(regimen_id)
        if regimen:
            regimen.upes_generadas += count
            regimen.updated_at = datetime.utcnow()
            self.session.flush()


class ViviendaRepository(BaseCancunRepository):
    """Encapsula operaciones para Viviendas individuales y UPEs."""

    def get_by_id(self, vivienda_id: int) -> Optional[Vivienda]:
        return self.session.get(Vivienda, vivienda_id)

    def _get_estado_vivienda_id(self, codigo: str) -> int:
        stmt = select(EstadoVivienda.estado_vivienda_id).where(EstadoVivienda.codigo == codigo)
        result = self.session.execute(stmt).scalar_one_or_none()
        if not result:
            raise ValueError(f"Estado de vivienda '{codigo}' no existe en el catálogo.")
        return result

    def _parse_safe_date(self, val: Any) -> Optional[date]:
        """Sanitiza y convierte de forma segura cualquier cadena u objeto a datetime.date."""
        if not val:
            return None
        if hasattr(val, "strftime") and hasattr(val, "day"):
            return val if isinstance(val, date) else val.date()
        val_str = str(val).strip()
        if not val_str or val_str.upper() in ("NONE", "NULL", "-", "N/A", ""):
            return None
        # Formato ISO: YYYY-MM-DD
        m_iso = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})", val_str)
        if m_iso:
            y, m, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
            try:
                return date(y, m, d)
            except ValueError:
                return None
        # Formato Latam: DD/MM/YYYY
        m_lat = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})", val_str)
        if m_lat:
            d, m, y = int(m_lat.group(1)), int(m_lat.group(2)), int(m_lat.group(3))
            try:
                return date(y, m, d)
            except ValueError:
                return None
        return None

    def create_upe(
        self,
        regimen_id: int,
        interior: str,
        numero_oficial: Optional[str] = None,
        edificio: Optional[str] = None,
        nivel: Optional[str] = None,
        calle: Optional[str] = None,
        destino: str = "HABITACIONAL",
        espacio: str = "VIVIENDA",
        folio_electronico: Optional[str] = None,
        clave_catastral: Optional[str] = None,
        padron: Optional[str] = None,
        descripcion: Optional[str] = None,
        fecha_escrituracion: Optional[date] = None,
        estado_codigo: str = "PROYECTADA"
    ) -> Vivienda:
        estado_id = self._get_estado_vivienda_id(estado_codigo)
        viv = Vivienda(
            regimen_id=regimen_id,
            numero_oficial=numero_oficial,
            interior=interior,
            edificio=edificio,
            nivel=nivel,
            calle=calle,
            destino=destino,
            espacio=espacio,
            folio_electronico=folio_electronico,
            clave_catastral=clave_catastral,
            padron=padron,
            descripcion=descripcion,
            fecha_escrituracion=fecha_escrituracion,
            estado_vivienda_id=estado_id,
            activo=True,
            created_at=datetime.utcnow()
        )
        self.session.add(viv)
        self.session.flush()
        return viv

    def list_by_regimen(self, regimen_id: int) -> List[Vivienda]:
        stmt = (
            select(Vivienda)
            .options(
                selectinload(Vivienda.estado),
                selectinload(Vivienda.regimen).selectinload(RegimenCondominio.desarrollo)
            )
            .where(Vivienda.regimen_id == regimen_id)
            .order_by(Vivienda.vivienda_id.asc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_by_desarrollo(self, desarrollo_id: int) -> List[Vivienda]:
        """Consulta viviendas de un desarrollo resolviéndolas a través de su régimen matriz."""
        stmt = (
            select(Vivienda)
            .join(Vivienda.regimen)
            .options(
                selectinload(Vivienda.estado),
                selectinload(Vivienda.regimen).selectinload(RegimenCondominio.desarrollo)
            )
            .where(RegimenCondominio.desarrollo_id == desarrollo_id)
            .order_by(Vivienda.vivienda_id.asc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def count_by_regimen(self, regimen_id: int) -> int:
        stmt = select(func.count(Vivienda.vivienda_id)).where(Vivienda.regimen_id == regimen_id)
        return self.session.execute(stmt).scalar_one() or 0

    def get_by_folio_electronico(self, folio_electronico: str) -> Optional[Vivienda]:
        """Búsqueda directa por folio electrónico inmobiliario del RPP."""
        stmt = select(Vivienda).where(Vivienda.folio_electronico == folio_electronico)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_clave_catastral(self, clave_catastral: str) -> Optional[Vivienda]:
        """Búsqueda directa por clave catastral individualizada."""
        stmt = select(Vivienda).where(Vivienda.clave_catastral == clave_catastral)
        return self.session.execute(stmt).scalar_one_or_none()

    def update_estado(self, vivienda_id: int, nuevo_estado_codigo: str) -> None:
        viv = self.get_by_id(vivienda_id)
        if viv:
            viv.estado_vivienda_id = self._get_estado_vivienda_id(nuevo_estado_codigo)
            viv.updated_at = datetime.utcnow()
            self.session.flush()

    def bulk_update_folios_rpp(self, regimen_id: int, updates: List[Dict[str, Any]], usuario_id: Optional[int] = None, sesion_id: Optional[int] = None) -> Dict[str, int]:
        """
        Asocia masivamente folios electrónicos del RPP a viviendas de un régimen
        usando (edificio, interior) o interior como clave de enlace flexible.
        Transiciona el estado de la vivienda a 'EN_INDIVIDUALIZACION' y registra bitácora.
        """
        st_indiv_id = self._get_estado_vivienda_id("EN_INDIVIDUALIZACION")
        viviendas = self.list_by_regimen(regimen_id)
        
        # Mapeo estricto por (edificio normalizado, interior normalizado)
        vivienda_map = {}
        # Mapeo de respaldo por interior exclusivo (si es único en el régimen)
        interior_map = {}
        interior_counts = {}
        # Mapeo de respaldo por número oficial exclusivo (si es único en el régimen)
        nof_map = {}
        nof_counts = {}
        # Mapeo específico para SERVICIO / Áreas Comunes: (interior, numero_oficial) sin edificio
        servicio_map = {}

        for v in viviendas:
            dest_v = str(v.destino or "").strip().upper()
            ed_norm = re.sub(r'^(EDIFICIO|TORRE)\s*', '', (v.edificio or "").strip().upper()).strip()
            if ed_norm in ("-", "N/A", "NONE"):
                ed_norm = ""
            int_norm = (v.interior or "").strip().upper()
            vivienda_map[(ed_norm, int_norm)] = v
            # También guardar con edificio completo original
            raw_ed_v = (v.edificio or "").strip().upper()
            if raw_ed_v not in ("-", "N/A", "NONE"):
                vivienda_map[(raw_ed_v, int_norm)] = v
            interior_counts[int_norm] = interior_counts.get(int_norm, 0) + 1
            interior_map[int_norm] = v

            # Indexar por Número Oficial (Prioridad Primaria)
            nof_raw = str(v.numero_oficial or "").strip().upper()
            if nof_raw and nof_raw not in ("-", "N/A", "NONE"):
                nof_map[nof_raw] = v
                nof_counts[nof_raw] = nof_counts.get(nof_raw, 0) + 1
                digits_match = re.search(r'\b(\d+)\b', nof_raw)
                if digits_match:
                    d_val = digits_match.group(1).lstrip("0") or "0"
                    if d_val != nof_raw:
                        if d_val not in nof_map:
                            nof_map[d_val] = v
                        nof_counts[d_val] = nof_counts.get(d_val, 0) + 1
                    # Si es SERVICIO o edificio vacío, indexar por (interior, nof)
                    if dest_v == "SERVICIO" or not ed_norm:
                        servicio_map[(int_norm, d_val)] = v
                        servicio_map[(int_norm, nof_raw)] = v
                else:
                    if dest_v == "SERVICIO" or not ed_norm:
                        servicio_map[(int_norm, nof_raw)] = v

        actualizados = 0
        no_encontrados = 0

        for item in updates:
            raw_edif = (item.get("edificio") or "").strip().upper()
            ed_norm = re.sub(r'^(EDIFICIO|TORRE)\s*', '', raw_edif).strip()
            if ed_norm in ("-", "N/A", "NONE"):
                ed_norm = ""
            inter = str(item.get("interior") or "").strip().upper()
            folio = str(item.get("folio_electronico") or "").strip()
            raw_nof = str(item.get("numero_oficial") or "").strip().upper()
            digits_nof = re.search(r'\b(\d+)\b', raw_nof)
            d_clean = digits_nof.group(1).lstrip("0") or "0" if digits_nof else raw_nof

            if not inter or not folio:
                continue

            target = None
            # 1. Prioridad para registros de SERVICIO / sin edificio: validar mediante (interior, número oficial)
            if inter and raw_nof and (not ed_norm or raw_edif in ("-", "N/A", "NONE", "")):
                target = servicio_map.get((inter, d_clean)) or servicio_map.get((inter, raw_nof))

            # 2. Prioridad Primaria: Coincidencia por Número Oficial unívoco en el régimen (NO OFICIAL)
            if not target and raw_nof:
                if nof_counts.get(raw_nof) == 1:
                    target = nof_map.get(raw_nof)
                elif d_clean and nof_counts.get(d_clean) == 1:
                    target = nof_map.get(d_clean)

            # 3. Prioridad Secundaria: Búsqueda física directa exacta por combinación (Edificio, Interior/UPE)
            if not target and (raw_edif or ed_norm):
                target = vivienda_map.get((raw_edif, inter)) or vivienda_map.get((ed_norm, inter))

            # 4. Respaldo por (interior, número oficial) general
            if not target and inter and raw_nof:
                target = servicio_map.get((inter, d_clean)) or servicio_map.get((inter, raw_nof))

            # 5. Respaldo exclusivo para áreas comunes sin edificio asignado si el interior es único
            if not target and not raw_edif and not ed_norm and interior_counts.get(inter) == 1:
                target = interior_map.get(inter)

            if target:
                target.folio_electronico = folio
                fecha_folio = self._parse_safe_date(item.get("fecha_alta_folio") or item.get("fecha"))
                if fecha_folio:
                    target.fecha_alta_folio = fecha_folio
                # Solo avanza estado si estaba en PROYECTADA
                if target.estado and target.estado.codigo == "PROYECTADA":
                    est_ant_id = target.estado_vivienda_id
                    target.estado_vivienda_id = st_indiv_id
                    # Registrar bitácora histórica
                    hist = ViviendaHistorialEstado(
                        vivienda_id=target.vivienda_id,
                        estado_anterior_id=est_ant_id,
                        estado_nuevo_id=st_indiv_id,
                        usuario_id=usuario_id,
                        sesion_id=sesion_id,
                        origen_cambio="VINCULAR_RPP",
                        motivo=f"Vinculación de Folio RPP: {folio}",
                        metadata_adicional={
                            "folio_electronico": folio,
                            "interior": inter,
                            "numero_oficial": raw_nof
                        },
                        created_at=datetime.utcnow()
                    )
                    self.session.add(hist)

                target.updated_at = datetime.utcnow()
                actualizados += 1
            else:
                no_encontrados += 1

        self.session.flush()
        return {"actualizados": actualizados, "no_encontrados": no_encontrados}

    def bulk_update_catastro(self, regimen_id: int, updates: List[Dict[str, Any]], usuario_id: Optional[int] = None, sesion_id: Optional[int] = None) -> Dict[str, int]:
        """
        Asocia masivamente Clave Catastral y Padrón municipal a viviendas de un régimen
        usando prioritariamente folio_electronico, o secundariamente (edificio, interior) o número oficial.
        Transiciona el estado de la vivienda a 'LISTA_PARA_VENTA' y registra bitácora.
        """
        st_venta_id = self._get_estado_vivienda_id("LISTA_PARA_VENTA")
        viviendas = self.list_by_regimen(regimen_id)
        
        vivienda_by_interior = {}
        interior_map = {}
        interior_counts = {}
        nof_map = {}
        nof_counts = {}

        tupla_completa_map = {}
        servicio_map = {}
        for v in viviendas:
            dest_v = str(v.destino or "").strip().upper()
            raw_ed = (v.edificio or "").strip().upper()
            ed_clean = "" if raw_ed in ("-", "N/A", "NONE", "") else re.sub(r'^(EDIFICIO|TORRE)\s*', '', raw_ed).strip()
            inter = (v.interior or "").strip().upper()
            nof_raw = str(v.numero_oficial or "").strip().upper()
            digits_match = re.search(r'\b(\d+)\b', nof_raw)
            nof_clean = digits_match.group(1).lstrip("0") or "0" if digits_match else nof_raw

            if inter:
                tupla_completa_map[(ed_clean, inter, nof_clean)] = v
                tupla_completa_map[(raw_ed if raw_ed != "-" else "", inter, nof_clean)] = v
                if dest_v == "SERVICIO" or not ed_clean:
                    servicio_map[(inter, nof_clean)] = v
                    servicio_map[(inter, nof_raw)] = v
            
            vivienda_by_interior[(raw_ed, inter)] = v
            vivienda_by_interior[(ed_clean, inter)] = v
            interior_counts[inter] = interior_counts.get(inter, 0) + 1
            interior_map[inter] = v

            if nof_raw and nof_raw not in ("-", "N/A", "NONE"):
                nof_map[nof_raw] = v
                nof_counts[nof_raw] = nof_counts.get(nof_raw, 0) + 1
                if nof_clean != nof_raw:
                    if nof_clean not in nof_map:
                        nof_map[nof_clean] = v
                    nof_counts[nof_clean] = nof_counts.get(nof_clean, 0) + 1

        vivienda_by_rpp = {
            v.folio_electronico.strip().upper(): v
            for v in viviendas if v.folio_electronico
        }

        actualizados = 0
        no_encontrados = 0

        for item in updates:
            raw_ed = (item.get("edificio") or "").strip().upper()
            ed_clean = "" if raw_ed in ("-", "N/A", "NONE", "") else re.sub(r'^(EDIFICIO|TORRE)\s*', '', raw_ed).strip()
            inter = str(item.get("interior") or "").strip().upper()
            folio_rpp = str(item.get("folio_electronico") or "").strip().upper()
            clave_cat = str(item.get("clave_catastral") or "").strip()
            padron = str(item.get("padron") or "").strip()
            raw_nof = str(item.get("numero_oficial") or "").strip().upper()
            digits_nof = re.search(r'\b(\d+)\b', raw_nof)
            nof_clean = digits_nof.group(1).lstrip("0") or "0" if digits_nof else raw_nof

            if not clave_cat and not padron:
                continue

            target = None
            # 1. Prioridad Primaria Soberana: Búsqueda unívoca por folio RPP
            if folio_rpp and folio_rpp in vivienda_by_rpp:
                target = vivienda_by_rpp[folio_rpp]

            # 2. Prioridad para unidades de SERVICIO / sin edificio: validar mediante (interior, número oficial)
            if not target and inter and raw_nof and (not ed_clean or raw_ed in ("-", "N/A", "NONE", "")):
                target = servicio_map.get((inter, nof_clean)) or servicio_map.get((inter, raw_nof))

            # 3. Prioridad Secundaria: Coincidencia conjunta por (Edificio, UPE/Interior, Número Oficial)
            if not target and inter and nof_clean:
                target = tupla_completa_map.get((ed_clean, inter, nof_clean)) or tupla_completa_map.get((raw_ed, inter, nof_clean))

            # 4. Prioridad Terciaria: Coincidencia física exacta por (edificio, interior/UPE)
            if not target:
                if (raw_ed, inter) in vivienda_by_interior:
                    target = vivienda_by_interior[(raw_ed, inter)]
                elif (ed_clean, inter) in vivienda_by_interior:
                    target = vivienda_by_interior[(ed_clean, inter)]

            # 5. Respaldo por (interior, número oficial) general
            if not target and inter and raw_nof:
                target = servicio_map.get((inter, nof_clean)) or servicio_map.get((inter, raw_nof))

            # 6. Respaldo para áreas comunes sin edificio asignado con interior unívoco
            if not target and not raw_ed and not ed_clean and interior_counts.get(inter) == 1:
                target = interior_map.get(inter)

            # 5. Inferencia Catastral: Sufijo de Clave Catastral
            if not target and clave_cat.startswith("60") and len(clave_cat) == 18:
                cc_nof = clave_cat[-4:].lstrip("0") or "0"
                if nof_counts.get(cc_nof) == 1:
                    target = nof_map.get(cc_nof)

            if target:
                if clave_cat:
                    target.clave_catastral = clave_cat
                if padron:
                    target.padron = padron
                fecha_cc = self._parse_safe_date(item.get("fecha_alta_cc") or item.get("fecha"))
                if fecha_cc:
                    target.fecha_alta_cc = fecha_cc
                if target.estado.codigo in ["PROYECTADA", "EN_INDIVIDUALIZACION"]:
                    est_ant_id = target.estado_vivienda_id
                    target.estado_vivienda_id = st_venta_id
                    # Registrar bitácora histórica
                    hist = ViviendaHistorialEstado(
                        vivienda_id=target.vivienda_id,
                        estado_anterior_id=est_ant_id,
                        estado_nuevo_id=st_venta_id,
                        usuario_id=usuario_id,
                        sesion_id=sesion_id,
                        origen_cambio="VINCULAR_CATASTRO",
                        motivo=f"Vinculación Catastral (CC: {clave_cat or '-'}, Padrón: {padron or '-'})",
                        metadata_adicional={
                            "clave_catastral": clave_cat,
                            "padron": padron,
                            "interior": inter,
                            "numero_oficial": raw_nof
                        },
                        created_at=datetime.utcnow()
                    )
                    self.session.add(hist)

                target.updated_at = datetime.utcnow()
                actualizados += 1
            else:
                no_encontrados += 1

        self.session.flush()
        return {"actualizados": actualizados, "no_encontrados": no_encontrados}


class TramiteViviendaRepository(BaseCancunRepository):
    """Encapsula el ciclo de vida y trazabilidad de los trámites de vivienda."""

    def get_by_id(self, tramite_vivienda_id: int) -> Optional[TramiteVivienda]:
        return self.session.get(TramiteVivienda, tramite_vivienda_id)

    def _get_estado_tramite_id(self, codigo: str) -> int:
        stmt = select(EstadoTramite.estado_tramite_id).where(EstadoTramite.codigo == codigo)
        result = self.session.execute(stmt).scalar_one_or_none()
        if not result:
            raise ValueError(f"Estado de trámite '{codigo}' no existe en el catálogo.")
        return result

    def create(
        self,
        tipo_tramite_id: int,
        vivienda_id: Optional[int] = None,
        regimen_id: Optional[int] = None,
        solicitud_tramite_id: Optional[int] = None,
        estado_codigo: str = "NO_INICIADO",
        folio_pase_caja: Optional[str] = None,
        orden_compra_erp: Optional[str] = None,
        usuario_responsable_id: Optional[int] = None,
        observaciones: Optional[str] = None
    ) -> TramiteVivienda:
        estado_id = self._get_estado_tramite_id(estado_codigo)
        tramite = TramiteVivienda(
            vivienda_id=vivienda_id,
            regimen_id=regimen_id,
            solicitud_tramite_id=solicitud_tramite_id,
            tipo_tramite_id=tipo_tramite_id,
            estado_tramite_id=estado_id,
            folio_pase_caja=folio_pase_caja,
            orden_compra_erp=orden_compra_erp,
            comprobado_erp=False,
            usuario_responsable_id=usuario_responsable_id,
            observaciones=observaciones,
            created_at=datetime.utcnow()
        )
        self.session.add(tramite)
        self.session.flush()
        return tramite

    def list_by_vivienda(self, vivienda_id: int) -> List[TramiteVivienda]:
        stmt = (
            select(TramiteVivienda)
            .options(
                selectinload(TramiteVivienda.tipo_tramite),
                selectinload(TramiteVivienda.estado),
                selectinload(TramiteVivienda.recibo),
                selectinload(TramiteVivienda.factura),
            )
            .where(TramiteVivienda.vivienda_id == vivienda_id)
            .order_by(TramiteVivienda.tramite_vivienda_id.asc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def update_estado(self, tramite_vivienda_id: int, estado_codigo: str) -> None:
        tramite = self.get_by_id(tramite_vivienda_id)
        if tramite:
            tramite.estado_tramite_id = self._get_estado_tramite_id(estado_codigo)
            tramite.updated_at = datetime.utcnow()
            self.session.flush()

    def conciliar_erp(self, tramite_vivienda_id: int, poliza_comprobacion: str) -> None:
        tramite = self.get_by_id(tramite_vivienda_id)
        if tramite:
            tramite.poliza_comprobacion_erp = poliza_comprobacion
            tramite.comprobado_erp = True
            tramite.estado_tramite_id = self._get_estado_tramite_id("COMPROBADO_ERP")
            tramite.updated_at = datetime.utcnow()
            self.session.flush()


from satc.src.storage.satc_models import OrdenTramite, SolicitudTramite


class OrdenTramiteRepository(BaseCancunRepository):
    """Encapsula operaciones para OrdenTramite (Macro-Orden ejecutiva)."""

    def get_by_id(self, orden_tramite_id: int) -> Optional[OrdenTramite]:
        return self.session.get(OrdenTramite, orden_tramite_id)

    def generate_next_folio(self) -> str:
        year = datetime.now().year
        prefix = f"TRM-ORD-{year}-"
        stmt = select(OrdenTramite.folio_orden).where(OrdenTramite.folio_orden.like(f"{prefix}%"))
        folios = self.session.execute(stmt).scalars().all()
        max_seq = 0
        for f in folios:
            try:
                seq = int(f.split("-")[-1])
                if seq > max_seq:
                    max_seq = seq
            except ValueError:
                continue
        return f"{prefix}{str(max_seq + 1).zfill(3)}"

    def create(
        self,
        desarrollo_id: int,
        usuario_id: int,
        regimen_id: Optional[int] = None,
        descripcion: Optional[str] = None
    ) -> OrdenTramite:
        folio = self.generate_next_folio()
        # Estado inicial: NO_INICIADO
        stmt_est = select(EstadoTramite.estado_tramite_id).where(EstadoTramite.codigo == "NO_INICIADO")
        estado_id = self.session.execute(stmt_est).scalar_one()

        orden = OrdenTramite(
            folio_orden=folio,
            desarrollo_id=desarrollo_id,
            regimen_id=regimen_id,
            descripcion=descripcion,
            total_solicitudes=0,
            total_viviendas=0,
            total_concluidos=0,
            total_comprobados_erp=0,
            estado_id=estado_id,
            usuario_id=usuario_id,
            created_at=datetime.utcnow()
        )
        self.session.add(orden)
        self.session.flush()
        return orden

    def list_all(self) -> List[OrdenTramite]:
        stmt = (
            select(OrdenTramite)
            .options(
                selectinload(OrdenTramite.desarrollo),
                selectinload(OrdenTramite.regimen),
                selectinload(OrdenTramite.estado),
                selectinload(OrdenTramite.solicitudes),
            )
            .order_by(OrdenTramite.orden_tramite_id.desc())
        )
        return list(self.session.execute(stmt).scalars().all())


class SolicitudTramiteRepository(BaseCancunRepository):
    """Encapsula operaciones para SolicitudTramite (Renglón por Tipo de Trámite)."""

    def get_by_id(self, solicitud_tramite_id: int) -> Optional[SolicitudTramite]:
        return self.session.get(SolicitudTramite, solicitud_tramite_id)

    def list_by_orden(self, orden_tramite_id: int) -> List[SolicitudTramite]:
        stmt = (
            select(SolicitudTramite)
            .options(
                selectinload(SolicitudTramite.tipo_tramite),
                selectinload(SolicitudTramite.estado),
                selectinload(SolicitudTramite.tramites),
            )
            .where(SolicitudTramite.orden_tramite_id == orden_tramite_id)
            .order_by(SolicitudTramite.solicitud_tramite_id.asc())
        )
        return list(self.session.execute(stmt).scalars().all())


class MetadataRulesRepository(BaseCancunRepository):
    """Encapsula operaciones de consulta y administración para reglas de extracción metadata-driven."""

    def list_campos(self, solo_activos: bool = True) -> List[CampoCanonico]:
        stmt = select(CampoCanonico).options(
            selectinload(CampoCanonico.anclas),
            selectinload(CampoCanonico.formatos).selectinload(CampoFormatoMunicipio.municipio)
        ).order_by(CampoCanonico.campo_id.asc())
        if solo_activos:
            stmt = stmt.where(CampoCanonico.activo == True)
        return list(self.session.execute(stmt).scalars().all())

    def get_campo_by_codigo(self, codigo: str) -> Optional[CampoCanonico]:
        stmt = select(CampoCanonico).options(
            selectinload(CampoCanonico.anclas),
            selectinload(CampoCanonico.formatos).selectinload(CampoFormatoMunicipio.municipio)
        ).where(CampoCanonico.codigo == codigo)
        return self.session.execute(stmt).scalars().first()

    def list_formatos_by_municipio(self, municipio_id: int, solo_activos: bool = True) -> List[CampoFormatoMunicipio]:
        stmt = (
            select(CampoFormatoMunicipio)
            .options(
                selectinload(CampoFormatoMunicipio.campo),
                selectinload(CampoFormatoMunicipio.municipio)
            )
            .where(CampoFormatoMunicipio.municipio_id == municipio_id)
            .order_by(CampoFormatoMunicipio.prioridad.asc())
        )
        if solo_activos:
            stmt = stmt.where(CampoFormatoMunicipio.activo == True)
        return list(self.session.execute(stmt).scalars().all())

    def list_anclas_by_campo(self, campo_id: int, solo_activos: bool = True) -> List[CampoEtiquetaAncla]:
        stmt = (
            select(CampoEtiquetaAncla)
            .where(CampoEtiquetaAncla.campo_id == campo_id)
            .order_by(CampoEtiquetaAncla.prioridad.asc())
        )
        if solo_activos:
            stmt = stmt.where(CampoEtiquetaAncla.activo == True)
        return list(self.session.execute(stmt).scalars().all())

    def list_all_formatos(self, solo_activos: bool = False) -> List[CampoFormatoMunicipio]:
        stmt = (
            select(CampoFormatoMunicipio)
            .options(
                selectinload(CampoFormatoMunicipio.campo),
                selectinload(CampoFormatoMunicipio.municipio)
            )
            .order_by(CampoFormatoMunicipio.municipio_id.asc(), CampoFormatoMunicipio.prioridad.asc())
        )
        if solo_activos:
            stmt = stmt.where(CampoFormatoMunicipio.activo == True)
        return list(self.session.execute(stmt).scalars().all())

    def get_formato_by_id(self, formato_id: int) -> Optional[CampoFormatoMunicipio]:
        stmt = (
            select(CampoFormatoMunicipio)
            .options(
                selectinload(CampoFormatoMunicipio.campo),
                selectinload(CampoFormatoMunicipio.municipio)
            )
            .where(CampoFormatoMunicipio.formato_id == formato_id)
        )
        return self.session.execute(stmt).scalars().first()

    def save_formato(self, data: Dict[str, Any]) -> CampoFormatoMunicipio:
        fid = data.get("formato_id")
        if fid:
            obj = self.get_formato_by_id(int(fid))
            if not obj:
                raise ValueError(f"Formato municipal con ID {fid} no existe.")
            obj.campo_id = int(data.get("campo_id", obj.campo_id))
            obj.municipio_id = int(data.get("municipio_id", obj.municipio_id))
            obj.nombre_variante = str(data.get("nombre_variante", obj.nombre_variante)).strip()
            obj.prioridad = int(data.get("prioridad", obj.prioridad) or 1)
            obj.regex_extraccion = str(data.get("regex_extraccion", obj.regex_extraccion)).strip()
            obj.regex_validacion = str(data.get("regex_validacion", obj.regex_validacion)).strip()
            obj.longitud_min = int(data["longitud_min"]) if data.get("longitud_min") is not None and str(data["longitud_min"]).strip() != "" else None
            obj.longitud_max = int(data["longitud_max"]) if data.get("longitud_max") is not None and str(data["longitud_max"]).strip() != "" else None
            obj.remover_caracteres = data.get("remover_caracteres", obj.remover_caracteres)
            obj.permite_sliding_window = bool(data.get("permite_sliding_window", obj.permite_sliding_window))
            obj.descripcion_error = data.get("descripcion_error", obj.descripcion_error)
            obj.activo = bool(data.get("activo", obj.activo))
            obj.updated_at = datetime.utcnow()
        else:
            obj = CampoFormatoMunicipio(
                campo_id=int(data["campo_id"]),
                municipio_id=int(data["municipio_id"]),
                nombre_variante=str(data["nombre_variante"]).strip(),
                prioridad=int(data.get("prioridad", 1) or 1),
                regex_extraccion=str(data["regex_extraccion"]).strip(),
                regex_validacion=str(data["regex_validacion"]).strip(),
                longitud_min=int(data["longitud_min"]) if data.get("longitud_min") is not None and str(data["longitud_min"]).strip() != "" else None,
                longitud_max=int(data["longitud_max"]) if data.get("longitud_max") is not None and str(data["longitud_max"]).strip() != "" else None,
                remover_caracteres=data.get("remover_caracteres", " -/"),
                permite_sliding_window=bool(data.get("permite_sliding_window", False)),
                descripcion_error=data.get("descripcion_error"),
                activo=bool(data.get("activo", True)),
                created_at=datetime.utcnow()
            )
            self.session.add(obj)
        self.session.flush()
        return obj



