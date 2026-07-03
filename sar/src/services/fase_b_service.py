"""Service to handle FASE B operations: batching, Excel generation, and PDF merging."""

import os
from typing import Dict, Any, List
from sqlalchemy import text
from PySide6.QtCore import QThread, Signal
from sar.src.storage.excel_handler import generate_excel_batch
from sar.src.services.pdf_extractor import merge_pdfs

class FaseBWorker(QThread):
    """Background worker thread to process Fase B generation without freezing UI."""
    finished = Signal(dict)
    error = Signal(Exception)

    def __init__(self, service, sol_ids, dest_dir, action_type="excel"):
        super().__init__()
        self.service = service
        self.sol_ids = sol_ids
        self.dest_dir = dest_dir
        self.action_type = action_type

    def run(self):
        try:
            if self.action_type == "excel":
                res = self.service.generate_excel_only(self.sol_ids, self.dest_dir)
            else:
                res = self.service.generate_pdf_only(self.sol_ids, self.dest_dir)
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(e)


class FaseBService:
    """Service class to orchestrate the generation of Excel and merged PDF batches for multiple Solicitudes."""

    def __init__(self, db_connector):
        self.db_connector = db_connector

    def _get_references_and_metadata(self, solicitud_ids: List[int]) -> List[Any]:
        """Helper to fetch references and metadata for a list of solicitudes."""
        if not solicitud_ids:
            return []
            
        with self.db_connector.get_session() as session:
            query = text("""
                SELECT 
                    r.consecutivo_grupo,
                    r.referencia_portal,
                    r.importe,
                    pdf.ruta_archivo,
                    rfc.rfc,
                    c.alias AS concepto_alias
                FROM sar_produccion.referencia r
                LEFT JOIN sar_archivo.archivo_pdf pdf ON r.referencia_id = pdf.referencia_id
                JOIN sar_produccion.grupo_referencia gr ON r.grupo_id = gr.grupo_id
                JOIN sar_catalogo.rfc rfc ON gr.rfc_id = rfc.rfc_id
                JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
                WHERE r.solicitud_id IN :sol_ids
                ORDER BY r.consecutivo_grupo ASC
            """)
            rows = session.execute(query, {"sol_ids": tuple(solicitud_ids)}).all()
        return rows

    def _group_by_company_concept_and_lote(self, rows: List[Any]) -> Dict[str, Dict[int, List[Any]]]:
        """Groups references first by group key (RFC_CONCEPTO) and then by global lote number.
        
        Returns:
            A nested dictionary: { "RFC_CONCEPTO": { 1: [rows], 2: [rows] } }
        """
        grouped = {}
        for row in rows:
            rfc_clean = "".join(c for c in row.rfc if c.isalnum())
            concepto_alias = row.concepto_alias or "CONCEPTO"
            concepto_clean = "".join(c for c in concepto_alias if c.isalnum() or c in ("-", "_")).upper()
            
            group_key = f"{rfc_clean}_{concepto_clean}"
            if group_key not in grouped:
                grouped[group_key] = {}
                
            lote_num = ((row.consecutivo_grupo - 1) // 299) + 1
            if lote_num not in grouped[group_key]:
                grouped[group_key][lote_num] = []
                
            grouped[group_key][lote_num].append(row)
        return grouped

    def check_conflicting_files(self, solicitud_ids: List[int], dest_dir: str, action_type: str = "excel") -> List[str]:
        """Checks if target files already exist in the destination directory.
        
        Returns:
            A list of filenames that would conflict/be overwritten.
        """
        if not os.path.exists(dest_dir):
            return []
            
        rows = self._get_references_and_metadata(solicitud_ids)
        if not rows:
            return []
            
        grouped_data = self._group_by_company_concept_and_lote(rows)
        conflicts = []
        
        for group_key, lotes in grouped_data.items():
            for lote_num in lotes.keys():
                batch_str = f"{lote_num:03d}"
                ext = ".xlsx" if action_type == "excel" else ".pdf"
                filename = f"{group_key}_LOTE_{batch_str}{ext}"
                full_path = os.path.join(dest_dir, filename)
                if os.path.exists(full_path):
                    conflicts.append(filename)
                    
        return conflicts

    def generate_excel_only(self, solicitud_ids: List[int], dest_dir: str) -> Dict[str, Any]:
        """Generates Excel files grouped by RFC+Concepto and their global lote number."""
        if not os.path.exists(dest_dir):
            raise ValueError(f"El directorio de destino no existe: {dest_dir}")

        rows = self._get_references_and_metadata(solicitud_ids)
        if not rows:
            return {"success": False, "message": "No se encontraron referencias para las solicitudes seleccionadas."}

        grouped_data = self._group_by_company_concept_and_lote(rows)
        generated_files = []
        total_referencias = len(rows)

        for group_key, lotes in grouped_data.items():
            for lote_num in sorted(lotes.keys()):
                batch_rows = lotes[lote_num]
                batch_str = f"{lote_num:03d}"

                excel_filename = f"{group_key}_LOTE_{batch_str}.xlsx"
                excel_path = os.path.join(dest_dir, excel_filename)
                
                excel_data = [
                    {
                        "id": row.consecutivo_grupo,
                        "Referencia": row.referencia_portal,
                        "importe": float(row.importe) if row.importe is not None else 0.0
                    }
                    for row in batch_rows
                ]
                generate_excel_batch(excel_path, excel_data)
                generated_files.append(excel_filename)

        return {
            "success": True,
            "total_referencias": total_referencias,
            "lotes_generados": len(generated_files),
            "archivos": generated_files
        }

    def generate_pdf_only(self, solicitud_ids: List[int], dest_dir: str) -> Dict[str, Any]:
        """Generates merged PDF files grouped by RFC+Concepto and their global lote number."""
        if not os.path.exists(dest_dir):
            raise ValueError(f"El directorio de destino no existe: {dest_dir}")

        rows = self._get_references_and_metadata(solicitud_ids)
        if not rows:
            return {"success": False, "message": "No se encontraron referencias para las solicitudes seleccionadas."}

        grouped_data = self._group_by_company_concept_and_lote(rows)
        generated_files = []
        total_referencias = len(rows)

        for group_key, lotes in grouped_data.items():
            for lote_num in sorted(lotes.keys()):
                batch_rows = lotes[lote_num]
                batch_str = f"{lote_num:03d}"

                pdf_filename = f"{group_key}_LOTE_{batch_str}.pdf"
                pdf_path = os.path.join(dest_dir, pdf_filename)
                
                pdf_paths_to_merge = []
                for row in batch_rows:
                    if row.ruta_archivo:
                        pdf_paths_to_merge.append(row.ruta_archivo)
                
                if pdf_paths_to_merge:
                    merge_pdfs(pdf_paths_to_merge, pdf_path)
                    generated_files.append(pdf_filename)
                else:
                    generated_files.append(f"{pdf_filename} (Omitido: Sin PDFs de boletas)")

        return {
            "success": True,
            "total_referencias": total_referencias,
            "lotes_generados": len(generated_files),
            "archivos": generated_files
        }
