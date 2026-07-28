"""
CancunBot — Repositorios de Base de Datos (SQLAlchemy 2.0)
Encapsula el acceso y manipulación de datos para las entidades de R2F-Cancún.
"""
import logging
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, update, and_, func
from sqlalchemy.orm import Session

from sar.src.storage.models import EstadoSistema, Usuario
from cancunbot.src.storage.cancunbot_models import LoteFolio, FolioCancun, ReciboCancun, FacturaCancun

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

    def create(self, usuario_id: int, origen: str = "EXCEL", descripcion: Optional[str] = None, archivo_excel: Optional[str] = None) -> LoteFolio:
        """Creates a new folio batch."""
        estado_id = self._get_estado_id("lote_folio", "NUEVO")
        folio_lote = self.generate_next_folio()
        
        lote = LoteFolio(
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

    def create_bulk(self, lote_id: int, folios_list: List[Tuple[str, str]]) -> int:
        """
        Inserts multiple folios into a batch.
        
        Args:
            lote_id: ID of the batch
            folios_list: List of tuples (folio_text, tipo_folio)
        """
        estado_id = self._get_estado_id("folio_cancun", "PENDIENTE")
        count = 0
        for folio_text, tipo in folios_list:
            clean_text = folio_text.strip() if folio_text else ""
            if not clean_text:
                continue

            folio = FolioCancun(
                lote_id=lote_id,
                tipo_folio=tipo,
                estado_id=estado_id,
                intentos=0
            )
            if tipo == "ELECTRONICO":
                folio.folio_electronico = clean_text
            else:
                folio.folio_pase_caja = clean_text
            
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
