"""
CancunBot — Extractor de Boletas y Pases de Caja desde PDF (PAQ.pdf)
Analiza archivos PDF multipágina extraídos de la Tesorería Municipal de Benito Juárez (Cancún).
"""
import re
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

import pdfplumber

logger = logging.getLogger(__name__)


@dataclass
class FolioPaqData:
    archivo_pdf: str
    pagina: int
    folio_pase_caja: Optional[str] = None
    folio_electronico: Optional[str] = None
    rfc: Optional[str] = None
    nombre_contribuyente: Optional[str] = None
    fecha_emision: Optional[str] = None
    padron: Optional[str] = None
    clave_catastral: Optional[str] = None
    total: float = 0.0
    domicilio: Optional[str] = None
    es_valido: bool = True
    observacion: str = "OK"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PaqPdfExtractor:
    """
    Parsea documentos PDF de Pases de Caja / Predial de Cancún y extrae los campos clave por página.
    """

    _RE_ASTERISK_FOLIO = re.compile(r"\*([0-9\-]{5,25})\*")
    _RE_LINEA_CAPTURA = re.compile(r"LINEA\s+DE\s+CAPTURA\s+([0-9\s]+)\$")
    _RE_RFC = re.compile(r"\bRFC[:\s]+([A-Z&]{3,4}\d{6}[A-Z0-9]{3})\b", re.IGNORECASE)
    _RE_NOMBRE = re.compile(r"Nombre[:\s]+(.+?)(?:\nRFC|\nFecha|\nContrib)", re.IGNORECASE)
    _RE_FECHA = re.compile(r"Fecha\s+emisi[oó]n[:\s]+(\d{2}/\d{2}/\d{2,4})", re.IGNORECASE)
    _RE_PADRON = re.compile(r"Padron[:\s]+(\d+)", re.IGNORECASE)
    _RE_CATASTRAL = re.compile(r"Clave\s+Catastral[:\s]+([0-9]+)", re.IGNORECASE)
    _RE_TOTAL = re.compile(r"Total[:\s]+\$?\s*([\d,]+\.?\d*)", re.IGNORECASE)
    _RE_DOMICILIO = re.compile(r"domicilio\s+(.+?)(?:\nLINEA|\nTOTAL|\n$)", re.IGNORECASE | re.DOTALL)

    def extraer_archivo(self, ruta_pdf: str) -> List[FolioPaqData]:
        """
        Extrae todos los registros de cada página del archivo PDF.
        """
        path = Path(ruta_pdf)
        if not path.exists():
            raise FileNotFoundError(f"No se encontró el archivo: {ruta_pdf}")

        resultados: List[FolioPaqData] = []
        nombre_archivo = path.name

        try:
            with pdfplumber.open(path) as pdf:
                for idx, page in enumerate(pdf.pages):
                    num_pagina = idx + 1
                    text = page.extract_text() or ""
                    
                    if not text.strip():
                        resultados.append(FolioPaqData(
                            archivo_pdf=nombre_archivo,
                            pagina=num_pagina,
                            es_valido=False,
                            observacion="Página vacía o sin texto reconocible (escaneada)"
                        ))
                        continue

                    data = self._parse_page_text(text, nombre_archivo, num_pagina)
                    resultados.append(data)

        except Exception as e:
            logger.error(f"Error procesando PDF {ruta_pdf}: {e}")
            resultados.append(FolioPaqData(
                archivo_pdf=nombre_archivo,
                pagina=1,
                es_valido=False,
                observacion=f"Error leyendo PDF: {str(e)}"
            ))

        return resultados

    def _parse_page_text(self, text: str, nombre_archivo: str, num_pagina: int) -> FolioPaqData:
        data = FolioPaqData(archivo_pdf=nombre_archivo, pagina=num_pagina)

        # 1. Folio Pase de Caja (entre asteriscos *4-24-22308409*)
        m_ast = self._RE_ASTERISK_FOLIO.search(text)
        if m_ast:
            data.folio_pase_caja = m_ast.group(1).strip()
        else:
            # Fallback linea de captura
            m_lc = self._RE_LINEA_CAPTURA.search(text)
            if m_lc:
                data.folio_pase_caja = m_lc.group(1).replace(" ", "").strip()

        # 2. RFC
        m_rfc = self._RE_RFC.search(text)
        if m_rfc:
            data.rfc = m_rfc.group(1).strip().upper()

        # 3. Nombre del Contribuyente
        m_nom = self._RE_NOMBRE.search(text)
        if m_nom:
            data.nombre_contribuyente = m_nom.group(1).strip()

        # 4. Fecha emisión
        m_fec = self._RE_FECHA.search(text)
        if m_fec:
            data.fecha_emision = m_fec.group(1).strip()

        # 5. Padrón
        m_pad = self._RE_PADRON.search(text)
        if m_pad:
            data.padron = m_pad.group(1).strip()

        # 6. Clave Catastral
        m_cat = self._RE_CATASTRAL.search(text)
        if m_cat:
            data.clave_catastral = m_cat.group(1).strip()

        # 7. Total
        m_tot = self._RE_TOTAL.search(text)
        if m_tot:
            try:
                raw_tot = m_tot.group(1).replace(",", "").strip()
                data.total = float(raw_tot)
            except ValueError:
                data.total = 0.0

        # 8. Domicilio
        m_dom = self._RE_DOMICILIO.search(text)
        if m_dom:
            data.domicilio = " ".join(m_dom.group(1).split())

        # Validaciones de integridad
        if not data.folio_pase_caja and not data.folio_electronico:
            data.es_valido = False
            data.observacion = "No se detectó folio entre asteriscos ni línea de captura"

        return data
