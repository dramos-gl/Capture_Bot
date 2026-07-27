"""
CancunBot — Servicio de Importación de Folios desde Excel
Lee una hoja de cálculo y retorna la lista de folios a procesar.
"""
import logging
from pathlib import Path
from typing import Optional

import openpyxl

from src.storage.repositories import ParametroRepository

logger = logging.getLogger(__name__)


class ExcelImporter:
    """
    Importa folios desde un archivo Excel.
    
    Estructura esperada del Excel:
        - Columna 'FOLIO' (o el nombre configurado en BD): Folio electrónico
        - Columna 'FOLIO_PASE_CAJA' (opcional): Folio de pase de caja
    
    Los nombres de columna son configurables via parámetros de sistema:
        - EXCEL_COLUMNA_FOLIO_ELECTRONICO
        - EXCEL_COLUMNA_FOLIO_PASE_CAJA
    """

    def __init__(self):
        params = ParametroRepository()
        self._col_electronico = params.obtener(
            "EXCEL_COLUMNA_FOLIO_ELECTRONICO", "FOLIO"
        )
        self._col_pase_caja = params.obtener(
            "EXCEL_COLUMNA_FOLIO_PASE_CAJA", "FOLIO_PASE_CAJA"
        )

    def importar(self, ruta_excel: str) -> list[dict]:
        """
        Lee el archivo Excel y retorna la lista de folios.
        
        Args:
            ruta_excel: Ruta al archivo .xlsx
        
        Returns:
            Lista de dicts con claves: folio_electronico, folio_pase_caja, tipo_folio
        
        Raises:
            FileNotFoundError: Si el archivo no existe
            ValueError: Si el archivo no tiene las columnas requeridas
        """
        ruta = Path(ruta_excel)
        if not ruta.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {ruta_excel}")

        logger.info(f"Importando folios desde: {ruta_excel}")

        wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
        ws = wb.active

        # Leer encabezados de la primera fila
        headers = [str(cell.value).strip().upper() if cell.value else "" 
                   for cell in next(ws.iter_rows(min_row=1, max_row=1))]

        col_elec = self._col_electronico.upper()
        col_pase = self._col_pase_caja.upper()

        if col_elec not in headers and col_pase not in headers:
            raise ValueError(
                f"El Excel no tiene las columnas esperadas. "
                f"Se requiere al menos '{col_elec}' o '{col_pase}'. "
                f"Columnas encontradas: {headers}"
            )

        idx_elec: Optional[int] = headers.index(col_elec) if col_elec in headers else None
        idx_pase: Optional[int] = headers.index(col_pase) if col_pase in headers else None

        folios: list[dict] = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            folio_elec = str(row[idx_elec]).strip() if idx_elec is not None and row[idx_elec] else None
            folio_pase = str(row[idx_pase]).strip() if idx_pase is not None and row[idx_pase] else None

            # Saltar filas vacías
            if not folio_elec and not folio_pase:
                continue

            # Determinar tipo de folio
            if folio_elec:
                tipo = "ELECTRONICO"
            else:
                tipo = "PASE_CAJA"

            folios.append({
                "folio_electronico": folio_elec,
                "folio_pase_caja": folio_pase,
                "tipo_folio": tipo
            })

        wb.close()
        logger.info(f"Importados {len(folios)} folios desde el Excel.")
        return folios

    def validar_estructura(self, ruta_excel: str) -> tuple[bool, str]:
        """
        Valida que el archivo Excel tenga la estructura correcta sin importar datos.
        
        Returns:
            Tuple (es_valido, mensaje)
        """
        try:
            ruta = Path(ruta_excel)
            if not ruta.exists():
                return False, f"Archivo no encontrado: {ruta_excel}"
            if ruta.suffix.lower() not in [".xlsx", ".xls"]:
                return False, "El archivo debe ser formato Excel (.xlsx o .xls)"
            self.importar(ruta_excel)  # Prueba de importación
            return True, "Estructura válida"
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Error al validar: {e}"
