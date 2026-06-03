import os
from collections import defaultdict
from pathlib import Path

class PDFValidator:
    """Utility to validate downloaded PDF files against reference IDs.

    The validator scans a root download directory (including all sub‑folders) and
    counts how many PDF files start with each reference identifier (the part
    before the first underscore "_").

    The public ``run`` method receives a list of reference strings and returns:
        - ``resultados``: dict mapping reference → state ("COMPLETO", "INCOMPLETO", "NO_DESCARGADO")
        - ``totales``: tuple (total_refs, completos, incompletos, sin_descarga, cobertura_percent)
        - ``archivos_extras``: list of PDF file paths not matching the list of references
    """

    def __init__(self, download_dir: str | Path):
        self.root = Path(download_dir).expanduser().resolve()
        if not self.root.is_dir():
            raise ValueError(f"Download directory does not exist or is not a folder: {self.root}")

    def _index_files_and_detect_extras(self, referencias_set: set[str]) -> tuple[dict[str, int], list[str]]:
        """Walk the download directory, count PDFs per reference, and detect extra files.

        Returns a tuple: (counts dict, list of extra filename paths)
        """
        counts = defaultdict(int)
        extras = []
        for pdf_path in self.root.rglob("*.pdf"):
            filename = pdf_path.name
            if "_" in filename:
                ref = filename.split("_", 1)[0]
                if ref in referencias_set:
                    counts[ref] += 1
                else:
                    extras.append(filename)
            else:
                extras.append(filename)
        return counts, extras

    @staticmethod
    def _classify(count: int) -> str:
        if count == 2:
            return "COMPLETO"
        elif count == 1:
            return "INCOMPLETO"
        else:
            return "NO_DESCARGADO"

    def run(self, referencias: list[str]):
        """Validate the given list of references.

        Parameters
        ----------
        referencias: list of reference strings (without trailing underscores)

        Returns
        -------
        resultados: dict mapping each reference to its validation state.
        totales: tuple(total, completos, incompletos, sin_descarga, cobertura_percent)
        extras: list of filenames not matching references
        """
        referencias_set = set(referencias)
        index, extras = self._index_files_and_detect_extras(referencias_set)
        resultados = {}
        completos = incompletos = sin_descarga = 0
        for ref in referencias:
            cnt = index.get(ref, 0)
            estado = self._classify(cnt)
            resultados[ref] = estado
            if estado == "COMPLETO":
                completos += 1
            elif estado == "INCOMPLETO":
                incompletos += 1
            else:
                sin_descarga += 1
        total = len(referencias)
        cobertura = (completos * 2) / (total * 2) * 100 if total > 0 else 0.0
        return resultados, (total, completos, incompletos, sin_descarga, cobertura), extras
