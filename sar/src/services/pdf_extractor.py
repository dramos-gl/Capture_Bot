"""PDF info extraction and merging services."""

import os
from typing import List

# Safe imports for maximum compatibility across different versions of pypdf/PyPDF2
try:
    from pypdf import PdfMerger as PDFMergerClass
except ImportError:
    try:
        from pypdf import PdfWriter as PDFMergerClass
    except ImportError:
        try:
            from PyPDF2 import PdfMerger as PDFMergerClass
        except ImportError:
            try:
                from PyPDF2 import PdfFileMerger as PDFMergerClass
            except ImportError:
                # Fallback to a dummy class that raises an error on use
                class PDFMergerClass:
                    def __init__(self):
                        raise ImportError("No se pudo importar PdfMerger ni PdfWriter de pypdf o PyPDF2.")

def merge_pdfs(pdf_paths: List[str], output_path: str) -> None:
    """Merges multiple PDF files into a single PDF unificado using pypdf.
    
    Args:
        pdf_paths: List of absolute file paths to the PDF files to merge.
        output_path: The destination path of the merged PDF.
    """
    merger = PDFMergerClass()
    for path in pdf_paths:
        if os.path.exists(path):
            merger.append(path)
        else:
            raise FileNotFoundError(f"No se encontró el archivo de boleta: {path}")
    merger.write(output_path)
    merger.close()
