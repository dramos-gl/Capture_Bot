"""
CancunBot — Worker Asíncrono de Análisis de PDF (QThread)
Procesa archivos PDF multipágina en segundo plano sin congelar la GUI.
"""
import logging
from typing import List, Dict, Any
from PySide6.QtCore import QThread, Signal

import pdfplumber
from cancunbot.src.services.paq_pdf_extractor import PaqPdfExtractor, FolioPaqData

logger = logging.getLogger(__name__)


class PdfAnalysisWorker(QThread):
    """
    Worker asíncrono que escanea múltiples archivos PDF en segundo plano.
    """
    progress_updated = Signal(int, int, str)   # current_page, total_pages, current_file_name
    page_extracted = Signal(dict)               # dict representa 1 página analizada
    metric_updated = Signal(str, object)        # metric_name, value
    finished_analysis = Signal(bool, str, list) # success, message, list of all dicts

    def __init__(self, pdf_paths: List[str], parent=None):
        super().__init__(parent)
        self.pdf_paths = pdf_paths
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def run(self):
        if not self.pdf_paths:
            self.finished_analysis.emit(False, "No se seleccionaron archivos PDF para analizar.", [])
            return

        extractor = PaqPdfExtractor()
        all_results: List[Dict[str, Any]] = []

        # 1. Calcular total de páginas
        total_pages = 0
        file_page_counts = []
        for path_str in self.pdf_paths:
            try:
                with pdfplumber.open(path_str) as pdf:
                    count = len(pdf.pages)
                    file_page_counts.append((path_str, count))
                    total_pages += count
            except Exception as e:
                logger.error(f"Error contando páginas de {path_str}: {e}")
                file_page_counts.append((path_str, 0))

        if total_pages == 0:
            self.finished_analysis.emit(False, "No se encontraron páginas legibles en los archivos seleccionados.", [])
            return

        self.metric_updated.emit("total_paginas", total_pages)
        self.metric_updated.emit("total_archivos", len(self.pdf_paths))

        current_page_index = 0
        validos_count = 0
        alertas_count = 0
        monto_acumulado = 0.0
        seen_folios = set()

        for path_str, page_count in file_page_counts:
            if self._stop_requested:
                break

            if page_count == 0:
                continue

            from pathlib import Path
            filename = Path(path_str).name

            try:
                with pdfplumber.open(path_str) as pdf:
                    for i, page in enumerate(pdf.pages):
                        if self._stop_requested:
                            break

                        current_page_index += 1
                        page_num = i + 1

                        self.progress_updated.emit(current_page_index, total_pages, filename)

                        text = page.extract_text() or ""
                        if not text.strip():
                            record = FolioPaqData(
                                archivo_pdf=filename,
                                pagina=page_num,
                                es_valido=False,
                                observacion="Página vacía o sin texto reconocible"
                            )
                        else:
                            record = extractor._parse_page_text(text, filename, page_num)

                        folio_val = record.folio_pase_caja if record.folio_pase_caja else record.folio_electronico
                        if folio_val:
                            if folio_val in seen_folios:
                                record.es_valido = False
                                record.observacion = f"Duplicado en el mismo lote ({folio_val})"
                            else:
                                seen_folios.add(folio_val)

                        rec_dict = record.to_dict()
                        all_results.append(rec_dict)

                        if record.es_valido:
                            validos_count += 1
                            monto_acumulado += record.total
                        else:
                            alertas_count += 1

                        self.page_extracted.emit(rec_dict)
                        self.metric_updated.emit("validos", validos_count)
                        self.metric_updated.emit("alertas", alertas_count)
                        self.metric_updated.emit("monto_total", monto_acumulado)

            except Exception as file_err:
                logger.error(f"Error analizando {filename}: {file_err}")

        if self._stop_requested:
            self.finished_analysis.emit(False, "Análisis cancelado por el usuario.", all_results)
        else:
            msg = f"Análisis finalizado: {validos_count} folios válidos detectados en {total_pages} páginas."
            self.finished_analysis.emit(True, msg, all_results)
