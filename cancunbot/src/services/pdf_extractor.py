"""
CancunBot — Extractor de Datos de PDF de Recibo Electrónico
Extrae los campos estructurados del PDF usando pdfplumber y expresiones regulares.
"""
import re
import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pdfplumber

logger = logging.getLogger(__name__)


@dataclass
class DatosRecibo:
    """
    Estructura de datos extraídos del PDF del recibo electrónico.
    Todos los campos son opcionales para tolerancia ante variaciones del formato.
    """
    folio_pase_caja: Optional[str] = None
    folio_electronico: Optional[str] = None
    fecha_expedicion: Optional[str] = None      # Formato: YYYY-MM-DD
    hora_expedicion: Optional[str] = None       # Formato: HH:MM:SS
    lugar_expedicion: Optional[str] = None
    rfc: Optional[str] = None
    contribucion: Optional[str] = None
    nombre_contribuyente: Optional[str] = None
    concepto: Optional[str] = None
    total: Optional[float] = None
    forma_pago: Optional[str] = None
    padron: Optional[str] = None
    clave_catastral: Optional[str] = None
    datos_adicionales: dict = field(default_factory=dict)


class PdfExtractor:
    """
    Extrae datos estructurados del PDF de recibo electrónico de la Tesorería de Cancún.
    
    Estrategia de extracción:
    1. Extrae el texto completo del PDF con pdfplumber.
    2. Aplica expresiones regulares para cada campo esperado.
    3. Los campos no encontrados quedan como None.
    4. Los campos no reconocidos se capturan en datos_adicionales.
    
    NOTA: Los patrones regex deberán ajustarse al formato real del PDF
    tras obtener una muestra del documento durante la fase DEV-04.
    """

    # Patrones de extracción (se ajustan tras inspeccionar PDF real)
    _PATRONES: dict[str, str] = {
        "folio_pase_caja":      r"FOLIO\s+PASE\s+DE\s+CAJA[:\s]+([A-Z0-9\-]+)",
        "folio_electronico":    r"FOLIO\s+ELECTR[ÓO]NICO[:\s]+([A-Z0-9\-]+)",
        "fecha_expedicion":     r"FECHA\s+DE\s+EXPEDICI[ÓO]N[:\s]+(\d{2}/\d{2}/\d{4})",
        "hora_expedicion":      r"HORA\s+DE\s+EXPEDICI[ÓO]N[:\s]+(\d{2}:\d{2}(?::\d{2})?)",
        "lugar_expedicion":     r"LUGAR\s+DE\s+EXPEDICI[ÓO]N[:\s]+(.+?)(?:\n|RFC)",
        "rfc":                  r"\bRFC[:\s]+([A-Z&]{3,4}\d{6}[A-Z0-9]{3})\b",
        "contribucion":         r"CONTRIBUCI[ÓO]N[:\s]+(.+?)(?:\n|DATOS)",
        "nombre_contribuyente": r"NOMBRE[:\s]+(.+?)(?:\n|FOLIO|RFC)",
        "concepto":             r"CONCEPTO[:\s]+(.+?)(?:\n|TOTAL|FORMA)",
        "total":                r"TOTAL[:\s]+\$?\s*([\d,]+\.?\d*)",
        "forma_pago":           r"FORMA\s+DE\s+PAGO[:\s]+(.+?)(?:\n|$)",
        "padron":               r"PADR[OÓ]N[:\s]+([A-Z0-9\-]+)",
        "clave_catastral":      r"CLAVE\s+CATASTRAL[:\s]+([A-Z0-9\-]+)",
    }

    def extraer(self, ruta_pdf: str) -> DatosRecibo:
        """
        Extrae los datos del PDF de recibo.
        
        Args:
            ruta_pdf: Ruta al archivo PDF descargado
        
        Returns:
            DatosRecibo con los campos extraídos (None si no se encontraron)
        
        Raises:
            FileNotFoundError: Si el archivo no existe
        """
        ruta = Path(ruta_pdf)
        if not ruta.exists():
            raise FileNotFoundError(f"PDF no encontrado: {ruta_pdf}")

        logger.info(f"Extrayendo datos del PDF: {ruta.name}")

        # Extrae todo el texto del PDF
        texto_completo = self._extraer_texto(ruta_pdf)
        if not texto_completo:
            logger.warning(f"No se pudo extraer texto del PDF: {ruta.name}")
            return DatosRecibo()

        datos = DatosRecibo()

        # Aplica cada patrón
        for campo, patron in self._PATRONES.items():
            valor = self._aplicar_patron(texto_completo, patron)
            if valor:
                setattr(datos, campo, valor)
                logger.debug(f"Campo '{campo}': '{valor}'")
            else:
                logger.debug(f"Campo '{campo}': no encontrado")

        # Post-procesamiento
        if datos.fecha_expedicion:
            datos.fecha_expedicion = self._normalizar_fecha(datos.fecha_expedicion)
        if datos.total:
            try:
                datos.total = float(str(datos.total).replace(",", ""))
            except ValueError:
                logger.warning(f"No se pudo convertir total a float: '{datos.total}'")
                datos.total = None

        logger.info(
            f"Extracción completada: RFC={datos.rfc}, "
            f"Folio={datos.folio_electronico}, Total={datos.total}"
        )
        return datos

    def calcular_hash(self, ruta_pdf: str) -> str:
        """Calcula el hash SHA256 del archivo PDF para verificación de integridad."""
        sha256 = hashlib.sha256()
        with open(ruta_pdf, "rb") as f:
            for bloque in iter(lambda: f.read(4096), b""):
                sha256.update(bloque)
        return sha256.hexdigest()

    def _extraer_texto(self, ruta_pdf: str) -> str:
        """Extrae el texto completo de todas las páginas del PDF."""
        try:
            with pdfplumber.open(ruta_pdf) as pdf:
                texto = "\n".join(
                    pagina.extract_text() or ""
                    for pagina in pdf.pages
                )
            return texto.upper()  # Normaliza a mayúsculas para facilitar matching
        except Exception as e:
            logger.error(f"Error al abrir PDF con pdfplumber: {e}")
            return ""

    def _aplicar_patron(self, texto: str, patron: str) -> Optional[str]:
        """Aplica un patrón regex al texto y retorna el primer grupo capturado."""
        try:
            match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        except re.error as e:
            logger.error(f"Error en patrón regex '{patron}': {e}")
        return None

    def _normalizar_fecha(self, fecha_str: str) -> str:
        """
        Normaliza la fecha al formato YYYY-MM-DD.
        Acepta: DD/MM/YYYY, D/M/YYYY
        """
        try:
            from datetime import datetime
            for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(fecha_str.strip(), fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        except Exception:
            pass
        return fecha_str  # Retorna tal cual si no puede normalizar
