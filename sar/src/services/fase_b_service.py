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
            elif self.action_type == "facturas":
                res = self.service.export_facturas_individuales(self.sol_ids, self.dest_dir)
            else:
                res = self.service.generate_pdf_only(self.sol_ids, self.dest_dir)
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(e)


class FaseBService:
    """Service class to orchestrate the generation of Excel, merged PDF batches, and individual invoices export."""

    def __init__(self, db_connector):
        self.db_connector = db_connector

    def get_facturas_exportables(self, solicitud_ids: List[int]) -> List[Any]:
        """Obtiene las facturas que cuentan con pdf_path y xml_path para las solicitudes dadas."""
        if not solicitud_ids:
            return []
            
        from sar.src.storage.api_client import APIClient
        api_client = APIClient()
        if api_client.connect_via_api:
            from types import SimpleNamespace
            sol_ids_str = ",".join([str(x) for x in solicitud_ids])
            payload = {"solicitud_ids": sol_ids_str}
            data = api_client.request("GET", "/api/docs/solicitudes/facturas-exportables", data=payload)
            return [SimpleNamespace(**item) for item in data]
            
        with self.db_connector.get_session() as session:
            query = text("""
                SELECT 
                    r.referencia_id,
                    r.referencia_portal,
                    r.solicitud_id,
                    r.consecutivo_grupo,
                    f.factura_id,
                    f.nombre_archivo,
                    f.pdf_path,
                    f.pdf2_path,
                    f.xml_path,
                    rfc.rfc,
                    c.alias AS concepto_alias
                FROM sar_produccion.referencia r
                JOIN sar_archivo.factura f ON r.referencia_id = f.referencia_id
                JOIN sar_produccion.grupo_referencia gr ON r.grupo_id = gr.grupo_id
                JOIN sar_catalogo.rfc rfc ON gr.rfc_id = rfc.rfc_id
                JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
                WHERE r.solicitud_id IN :sol_ids
                  AND f.pdf_path IS NOT NULL 
                  AND f.xml_path IS NOT NULL
                ORDER BY r.consecutivo_grupo ASC
            """)
            rows = session.execute(query, {"sol_ids": tuple(solicitud_ids)}).all()
        return rows

    def _get_references_and_metadata(self, solicitud_ids: List[int]) -> List[Any]:
        """Helper to fetch references and metadata for a list of solicitudes."""
        if not solicitud_ids:
            return []
            
        from sar.src.storage.api_client import APIClient
        api_client = APIClient()
        if api_client.connect_via_api:
            from types import SimpleNamespace
            sol_ids_str = ",".join([str(x) for x in solicitud_ids])
            payload = {"solicitud_ids": sol_ids_str}
            data = api_client.request("GET", "/api/docs/solicitudes/references-metadata", data=payload)
            return [SimpleNamespace(**item) for item in data]
            
        with self.db_connector.get_session() as session:
            query = text("""
                SELECT 
                    r.consecutivo_grupo,
                    r.referencia_portal,
                    r.importe,
                    r.cantidad,
                    r.porcentaje,
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

    @staticmethod
    def _extract_serie_folio(xml_path: str, pdf_path: str = None) -> str:
        """Extrae la Serie y Folio de la factura. Prioriza el XML (CFDI) y cuenta con fallback al PDF."""
        import xml.etree.ElementTree as ET
        if xml_path and os.path.exists(xml_path):
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                serie = root.attrib.get("Serie", "").strip()
                folio = root.attrib.get("Folio", "").strip()
                if serie and folio:
                    return f"{serie}-{folio}"
                elif folio:
                    return folio
            except Exception:
                pass

        if pdf_path and os.path.exists(pdf_path):
            try:
                from pypdf import PdfReader
                reader = PdfReader(pdf_path)
                if reader.pages:
                    text = reader.pages[0].extract_text()
                    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
                    for i, line in enumerate(lines):
                        if "SERIE Y FOLIO" in line.upper():
                            # Puede venir en la misma línea "SERIE Y FOLIO: LBA-12345" o en la siguiente
                            parts = line.split(":")
                            if len(parts) > 1 and parts[1].strip():
                                return parts[1].strip()
                            elif i + 1 < len(lines):
                                return lines[i + 1].strip()
            except Exception:
                pass
        return ""

    def check_conflicting_files(self, solicitud_ids: List[int], dest_dir: str, action_type: str = "excel") -> List[str]:
        """Checks if target files already exist in the destination directory.
        
        Returns:
            A list of filenames that would conflict/be overwritten.
        """
        if not os.path.exists(dest_dir):
            return []
            
        if action_type == "facturas":
            facturas = self.get_facturas_exportables(solicitud_ids)
            conflicts = []
            for f in facturas:
                ref_portal = getattr(f, "referencia_portal", "") or f"REF_{getattr(f, 'referencia_id', '')}"
                nom_base = getattr(f, "nombre_archivo", None) or ref_portal
                xml_p = getattr(f, "xml_path", None)
                pdf1 = getattr(f, "pdf_path", None)
                
                serie_folio = self._extract_serie_folio(xml_p, pdf1)
                if serie_folio:
                    clean_serie_folio = "".join(c for c in serie_folio if c.isalnum() or c in ("-", "_")).strip("_")
                    base_name = f"{ref_portal}_{clean_serie_folio}"
                else:
                    base_name = nom_base

                clean_base = "".join(c for c in base_name if c.isalnum() or c in ("-", "_", ".")).strip("_")
                for ext in (".pdf", ".xml"):
                    fname = f"{clean_base}{ext}"
                    if os.path.exists(os.path.join(dest_dir, fname)):
                        conflicts.append(fname)
            return conflicts

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
                        "cantidad": row.cantidad,
                        "importe": float(row.importe) if row.importe is not None else 0.0,
                        "porcentaje": row.porcentaje
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
                missing_refs = []
                for row in batch_rows:
                    if not row.ruta_archivo or not os.path.exists(row.ruta_archivo):
                        missing_refs.append(
                            f"- Consecutivo: {row.consecutivo_grupo} | Referencia: {row.referencia_portal or 'N/A'}"
                        )
                    else:
                        pdf_paths_to_merge.append(row.ruta_archivo)
                
                if missing_refs:
                    missing_str = "\n".join(missing_refs)
                    raise FileNotFoundError(
                        f"Hacen falta archivos PDF de boletas para las siguientes referencias en {pdf_filename}:\n\n{missing_str}"
                    )
                
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

    def export_facturas_individuales(self, solicitud_ids: List[int], dest_dir: str) -> Dict[str, Any]:
        """Exporta de forma individual las facturas (PDF y XML) de los derechos que cuenten con ambos archivos."""
        import shutil
        if not os.path.exists(dest_dir):
            raise ValueError(f"El directorio de destino no existe: {dest_dir}")

        facturas = self.get_facturas_exportables(solicitud_ids)
        if not facturas:
            return {
                "success": False,
                "message": "No se encontraron derechos que cuenten con ambos archivos (PDF y XML) en las solicitudes seleccionadas."
            }

        archivos_exportados = []
        derechos_procesados = 0
        faltantes = 0
        errores = 0

        for f in facturas:
            ref_portal = getattr(f, "referencia_portal", "") or f"REF_{getattr(f, 'referencia_id', '')}"
            nom_base = getattr(f, "nombre_archivo", None) or ref_portal
            pdf1 = getattr(f, "pdf_path", None)
            pdf2 = getattr(f, "pdf2_path", None)
            xml_p = getattr(f, "xml_path", None)

            # Extraer Serie y Folio para nomenclatura enriquecida
            serie_folio = self._extract_serie_folio(xml_p, pdf1)
            if serie_folio:
                clean_serie_folio = "".join(c for c in serie_folio if c.isalnum() or c in ("-", "_")).strip("_")
                base_name = f"{ref_portal}_{clean_serie_folio}"
            else:
                base_name = nom_base

            # Limpiar nombre de archivo para evitar caracteres inválidos
            clean_base = "".join(c for c in base_name if c.isalnum() or c in ("-", "_", ".")).strip("_")
            if not clean_base:
                clean_base = ref_portal

            # Verificar existencia física de archivos
            if not pdf1 or not os.path.exists(pdf1) or not xml_p or not os.path.exists(xml_p):
                faltantes += 1
                continue

            try:
                # 1. Exportar PDF individual (unificar si tiene pdf2_path, o copiar directamente)
                dest_pdf = os.path.join(dest_dir, f"{clean_base}.pdf")
                valid_pdfs = [p for p in [pdf1, pdf2] if p and os.path.exists(p)]
                
                if len(valid_pdfs) > 1:
                    merge_pdfs(valid_pdfs, dest_pdf)
                else:
                    shutil.copy2(pdf1, dest_pdf)
                archivos_exportados.append(os.path.basename(dest_pdf))

                # 2. Exportar XML individual
                dest_xml = os.path.join(dest_dir, f"{clean_base}.xml")
                shutil.copy2(xml_p, dest_xml)
                archivos_exportados.append(os.path.basename(dest_xml))

                derechos_procesados += 1

            except Exception as e:
                errores += 1

        return {
            "success": derechos_procesados > 0,
            "total_referencias": derechos_procesados,
            "total_archivos": len(archivos_exportados),
            "archivos": archivos_exportados,
            "faltantes": faltantes,
            "errores": errores,
            "message": f"Se exportaron {derechos_procesados} facturas ({len(archivos_exportados)} archivos PDF y XML)."
        }

