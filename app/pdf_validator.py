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
    """

    def __init__(self, download_dir: str | Path):
        self.root = Path(download_dir).expanduser().resolve()
        if not self.root.is_dir():
            raise ValueError(f"Download directory does not exist or is not a folder: {self.root}")

    def _index_files(self) -> dict[str, int]:
        """Walk the download directory and count PDFs per reference.

        Returns a dictionary ``{reference: pdf_count}``.
        """
        counts = defaultdict(int)
        for pdf_path in self.root.rglob("*.pdf"):
            # Ensure we only work with file names, not full paths
            filename = pdf_path.name
            # Reference is the substring before the first underscore
            if "_" in filename:
                ref = filename.split("_", 1)[0]
                counts[ref] += 1
        return counts

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
        """
        index = self._index_files()
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
        # Each reference should have exactly 2 PDFs to be complete
        cobertura = (completos * 2) / (total * 2) * 100 if total > 0 else 0.0
        return resultados, (total, completos, incompletos, sin_descarga, cobertura)
