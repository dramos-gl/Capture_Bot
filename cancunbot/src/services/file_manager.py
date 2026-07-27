"""
CancunBot — Servicio de Gestión de Archivos PDF
Renombra y organiza los PDFs descargados en el repositorio.
"""
import hashlib
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from src.storage.repositories import ParametroRepository

logger = logging.getLogger(__name__)


class FileManager:
    """
    Gestiona el renombrado y organización de archivos PDF descargados.
    
    La ruta base y el patrón de renombrado son configurables via parámetros:
        - PDF_BASE_PATH       → Carpeta raíz del repositorio
        - PDF_NAMING_PATTERN  → Patrón del nombre de archivo
    
    Tokens disponibles en el patrón:
        {folio_electronico}  → Folio electrónico del recibo
        {folio_pase_caja}    → Folio de pase de caja
        {rfc}                → RFC del contribuyente
        {fecha}              → Fecha de expedición (YYYYMMDD)
        {anio}               → Año de expedición
    """

    def __init__(self, base_dir: Optional[Path] = None):
        params = ParametroRepository()
        if base_dir:
            self._base_dir = base_dir
        else:
            base_path_str = params.obtener("PDF_BASE_PATH", "PDF_Recibos")
            # Si es ruta relativa, la hace relativa al proyecto
            base_path = Path(base_path_str)
            if not base_path.is_absolute():
                from src.paths import ROOT_DIR
                base_path = ROOT_DIR / base_path
            self._base_dir = base_path

        self._patron = params.obtener("PDF_NAMING_PATTERN", "{folio_electronico}")

    def organizar(self, ruta_temp: str, datos_recibo: dict) -> str:
        """
        Mueve y renombra el PDF temporal a su ubicación definitiva.
        
        Args:
            ruta_temp: Ruta del PDF temporal (recién descargado)
            datos_recibo: Dict con datos extraídos del PDF
        
        Returns:
            Ruta definitiva del PDF organizado
        """
        # Construye el nombre del archivo
        nombre = self._construir_nombre(datos_recibo)
        if not nombre.endswith(".pdf"):
            nombre += ".pdf"

        # Carpeta destino (pendiente: estructura definida en OQ-003)
        carpeta_destino = self._construir_carpeta(datos_recibo)
        carpeta_destino.mkdir(parents=True, exist_ok=True)

        ruta_destino = carpeta_destino / nombre

        # Si ya existe, agrega sufijo numérico
        if ruta_destino.exists():
            base = ruta_destino.stem
            ext = ruta_destino.suffix
            contador = 1
            while ruta_destino.exists():
                ruta_destino = carpeta_destino / f"{base}_{contador}{ext}"
                contador += 1

        shutil.move(str(ruta_temp), str(ruta_destino))
        logger.info(f"PDF organizado: {ruta_destino}")
        return str(ruta_destino)

    def _construir_nombre(self, datos: dict) -> str:
        """Construye el nombre del archivo aplicando el patrón configurado."""
        fecha_raw = datos.get("fecha_expedicion") or datetime.now().strftime("%Y-%m-%d")
        fecha_fmt = fecha_raw.replace("-", "") if fecha_raw else ""
        anio = fecha_fmt[:4] if len(fecha_fmt) >= 4 else str(datetime.now().year)

        tokens = {
            "folio_electronico": datos.get("folio_electronico") or "SIN_FOLIO",
            "folio_pase_caja":   datos.get("folio_pase_caja") or "",
            "rfc":               datos.get("rfc") or "SIN_RFC",
            "fecha":             fecha_fmt,
            "anio":              anio,
        }

        nombre = self._patron
        for token, valor in tokens.items():
            nombre = nombre.replace(f"{{{token}}}", self._limpiar(valor))

        return nombre

    def _construir_carpeta(self, datos: dict) -> Path:
        """
        Construye la ruta de carpeta destino.
        PENDIENTE (OQ-003): La estructura se definirá en fases posteriores.
        Por ahora organiza por año.
        """
        anio = str(datetime.now().year)
        return self._base_dir / anio

    @staticmethod
    def _limpiar(valor: str) -> str:
        """Limpia caracteres no válidos para nombres de archivo."""
        import re
        return re.sub(r'[<>:"/\\|?*]', '_', valor).strip()
