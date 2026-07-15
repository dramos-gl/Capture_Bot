import os
import openpyxl
from datetime import datetime, date
from typing import List, Dict, Any
from sqlalchemy import select, and_

class ExcelInventoryHandler:
    """Service to parse and validate Excel files for reference inventory control."""

    @staticmethod
    def parse_excel_inventory(file_path: str) -> List[Dict[str, Any]]:
        """Parses the Excel file and normalizes it into a list of detail dictionaries.
        
        One row in Excel with multiple reference columns (ANALISIS, AVISO, CLG)
        will be split into multiple detail records.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"El archivo no existe: {file_path}")

        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb.active # Use the active sheet (typically Hoja1)
        
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []

        # Find header indices
        headers = [str(h).strip().upper() for h in rows[0]]
        
        def get_idx(name):
            try:
                return headers.index(name)
            except ValueError:
                return -1

        idx_cliente = get_idx("CLIENTE")
        idx_desarrollo = get_idx("DESARROLLO")
        idx_fecha_sol = get_idx("FECHA_SOLICITUD")
        idx_ubicacion = get_idx("UBICACION")
        idx_mz = get_idx("MZ")
        idx_lote = get_idx("LOTE")
        idx_edif = get_idx("EDIF")
        idx_viv = get_idx("VIV")
        idx_folio = get_idx("FOLIO")
        idx_estatus_aviso = get_idx("ESTATUS_PRIMER_AVISO")
        
        # Concept reference columns
        concept_cols = {
            "ANALISIS": get_idx("ANALISIS"),
            "AVISO": get_idx("AVISO"),
            "CLG": get_idx("CLG"),
            "CANC_1ER _AVISO": get_idx("CANC_1ER _AVISO"),
            "CANC_2DO_AVISO": get_idx("CANC_2DO_AVISO"),
            "NUEVO_DERECHO_AVISO": get_idx("NUEVO_DERECHO_AVISO"),
        }

        parsed_records = []

        # Process data rows
        for row_num, row in enumerate(rows[1:], start=2):
            # Skip empty rows
            if not row or all(v is None for v in row):
                continue
                
            cliente = str(row[idx_cliente]).strip() if idx_cliente != -1 and row[idx_cliente] is not None else ""
            if not cliente:
                continue # Skip rows without client name

            desarrollo = str(row[idx_desarrollo]).strip().upper() if idx_desarrollo != -1 and row[idx_desarrollo] is not None else "GENERICO"
            
            # Format date
            fecha_sol = None
            if idx_fecha_sol != -1 and row[idx_fecha_sol] is not None:
                val = row[idx_fecha_sol]
                if isinstance(val, (datetime, date)):
                    fecha_sol = val
                else:
                    try:
                        fecha_sol = datetime.strptime(str(val).split()[0], "%Y-%m-%d").date()
                    except Exception:
                        pass
            
            # Location fields
            mz = str(row[idx_mz]).strip() if idx_mz != -1 and row[idx_mz] is not None else ""
            lote = str(row[idx_lote]).strip() if idx_lote != -1 and row[idx_lote] is not None else ""
            edif = str(row[idx_edif]).strip() if idx_edif != -1 and row[idx_edif] is not None else ""
            viv = str(row[idx_viv]).strip() if idx_viv != -1 and row[idx_viv] is not None else ""
            
            # Parse fallback from UBICACION text column if mz/lote are empty
            if (not mz and not lote) and idx_ubicacion != -1 and row[idx_ubicacion] is not None:
                # Try parsing e.g. "MZ 38 LT 2 VIV 35"
                import re
                txt = str(row[idx_ubicacion]).upper()
                m_mz = re.search(r"MZ\s*(\d+)", txt)
                m_lt = re.search(r"L?T\s*(\d+)", txt)
                m_ed = re.search(r"EDIF\s*([A-Z0-9\-]+)", txt)
                m_vv = re.search(r"VIV\s*([A-Z0-9\-]+)", txt)
                if m_mz: mz = m_mz.group(1)
                if m_lt: lote = m_lt.group(1)
                if m_ed: edif = m_ed.group(1)
                if m_vv: viv = m_vv.group(1)

            folio = str(row[idx_folio]).strip() if idx_folio != -1 and row[idx_folio] is not None else ""
            estatus_aviso = str(row[idx_estatus_aviso]).strip() if idx_estatus_aviso != -1 and row[idx_estatus_aviso] is not None else ""

            # Check each concept reference column
            for concept_name, col_idx in concept_cols.items():
                if col_idx != -1 and row[col_idx] is not None:
                    ref_val = str(row[col_idx]).strip()
                    # Skip empty/None references or headers accidentally repeated
                    if not ref_val or ref_val.upper() in ("NONE", "NULL", "-"):
                        continue
                    
                    # Store record
                    parsed_records.append({
                        "excel_row": row_num,
                        "cliente": cliente,
                        "desarrollo": desarrollo,
                        "fecha_solicitud": fecha_sol,
                        "mz": mz,
                        "lote": lote,
                        "edif": edif,
                        "viv": viv,
                        "folio_electronico": folio,
                        "estatus_primer_aviso": estatus_aviso,
                        "concepto_solicitado": concept_name,
                        "referencia_asignada": ref_val
                    })

        return parsed_records

    @staticmethod
    def validate_parsed_rows(session, parsed_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validates parsed rows against the database, enforcing:
        1. Reference exists and is FACTURADA.
        2. Reference is not already assigned.
        3. Concept matching (CLG, AVISO, etc.).
        4. Geolocation match (desarrollo delegation == reference delegation).
        """
        from sar.src.storage.models import Referencia, EstadoSistema, Desarrollo, Delegacion, GrupoReferencia, Concepto, Solicitud
        
        # Cache concepts mapping
        concepto_stmt = select(Concepto)
        concepts = session.execute(concepto_stmt).scalars().all()
        # Map aliases: 'CLG' -> Concepto(alias='CLG')
        concept_alias_map = {c.alias: c for c in concepts if c.alias}
        
        validated_rows = []

        for row in parsed_rows:
            ref_str = row["referencia_asignada"]
            concept_req = row["concepto_solicitado"]
            desarrollo_name = row["desarrollo"]
            
            row_result = dict(row)
            row_result["status"] = "PENDIENTE" # default
            row_result["error_message"] = ""
            row_result["referencia_id"] = None
            row_result["desarrollo_id"] = None
            row_result["delegacion_nombre"] = ""
            
            # 1. Lookup/register Desarrollo first
            des_stmt = select(Desarrollo).where(Desarrollo.nombre == desarrollo_name)
            desarrollo = session.execute(des_stmt).scalars().first()
            
            if not desarrollo:
                # Try fallback: register it temporarily under CANCUN (delegacion_id=2) or PLAYA (delegacion_id=3)
                # Let's infer based on name:
                deleg_id = 2 # default Cancun
                if "PLAYA" in desarrollo_name or "TULUM" in desarrollo_name:
                    deleg_id = 3 # Playa del Carmen
                
                # We can dynamically register the development
                desarrollo = Desarrollo(nombre=desarrollo_name, delegacion_id=deleg_id, activo=True)
                session.add(desarrollo)
                session.flush()
            
            row_result["desarrollo_id"] = desarrollo.desarrollo_id
            
            # Fetch delegation details for development
            deleg_stmt = select(Delegacion.nombre).where(Delegacion.delegacion_id == desarrollo.delegacion_id)
            deleg_name = session.execute(deleg_stmt).scalar()
            row_result["delegacion_nombre"] = deleg_name

            # 2. Query reference details
            ref_stmt = (
                select(Referencia, EstadoSistema.codigo, Concepto.alias, Delegacion.nombre, Delegacion.delegacion_id)
                .join(EstadoSistema, Referencia.estado_id == EstadoSistema.estado_id)
                .join(GrupoReferencia, Referencia.grupo_id == GrupoReferencia.grupo_id)
                .join(Concepto, GrupoReferencia.concepto_id == Concepto.concepto_id)
                .join(Solicitud, Referencia.solicitud_id == Solicitud.solicitud_id)
                .join(Delegacion, Solicitud.delegacion_id == Delegacion.delegacion_id)
                .where(Referencia.referencia_portal == ref_str)
            )
            ref_res = session.execute(ref_stmt).first()

            if not ref_res:
                row_result["status"] = "ERROR"
                row_result["error_message"] = f"La referencia '{ref_str}' no existe en el sistema."
                validated_rows.append(row_result)
                continue
                
            ref_obj, estado_cod, concept_alias, ref_deleg_name, ref_deleg_id = ref_res
            row_result["referencia_id"] = ref_obj.referencia_id

            # 3. Check if reference is in FACTURADA state
            if estado_cod != "FACTURADA":
                # Wait, if it is already ASIGNADA, let's check if it is assigned to the SAME client in this lote or another
                from sar.src.storage.models import LoteDetalle
                ld_check = session.execute(select(LoteDetalle).where(LoteDetalle.referencia_id == ref_obj.referencia_id)).scalars().first()
                if ld_check:
                    row_result["status"] = "ERROR"
                    row_result["error_message"] = f"La referencia ya está asignada al cliente '{ld_check.cliente}'."
                else:
                    row_result["status"] = "WARNING"
                    row_result["error_message"] = f"Advertencia: La referencia está en estado '{estado_cod}' (se esperaba 'FACTURADA')."
                validated_rows.append(row_result)
                continue

            # 4. Check Concept Match
            # Maps column names to DB concept aliases: e.g. column 'AVISO' matches alias 'AVISO PREVENTIVO'
            expected_aliases = []
            if concept_req == "CLG": expected_aliases = ["CLG"]
            elif concept_req in ("AVISO", "NUEVO_DERECHO_AVISO"): expected_aliases = ["AVISO PREVENTIVO"]
            elif concept_req == "ANALISIS": expected_aliases = ["ANALISIS"]

            if expected_aliases and concept_alias not in expected_aliases:
                row_result["status"] = "ERROR"
                row_result["error_message"] = f"Concepto incorrecto: Referencia es de tipo '{concept_alias}' pero se solicitó '{concept_req}'."
                validated_rows.append(row_result)
                continue

            # 5. Check Geolocation Match
            if ref_deleg_id != desarrollo.delegacion_id:
                row_result["status"] = "ERROR"
                row_result["error_message"] = f"Error geográfico: Referencia pertenece a '{ref_deleg_name}' pero el desarrollo '{desarrollo_name}' pertenece a '{deleg_name}'."
                validated_rows.append(row_result)
                continue

            # Valid reference!
            row_result["status"] = "CORRECTO"
            validated_rows.append(row_result)

        return validated_rows

    @staticmethod
    def generate_excel_inventory_file(dest_path: str, title: str, subtitle: str, date_range: str, data_rows: List[Dict[str, Any]]):
        """Generates a styled Excel sheet mapping the structure shown in Image 1."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Hoja1"

        # Styles
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        
        font_title = Font(name="Calibri", size=16, bold=True)
        font_subtitle = Font(name="Calibri", size=12, bold=True)
        font_header = Font(name="Calibri", size=10, bold=True, color="000000")
        font_data = Font(name="Calibri", size=10)
        
        fill_header = PatternFill(start_color="86C232", end_color="86C232", fill_type="solid") # Sleek green
        
        border_thin = Side(border_style="thin", color="D3D3D3")
        border_double = Side(border_style="double", color="000000")
        border_data = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)

        # 1. Header block
        ws.merge_cells("A2:P2")
        ws["A2"] = title.upper()
        ws["A2"].font = font_title
        ws["A2"].alignment = Alignment(horizontal="center")
        
        ws.merge_cells("A3:P3")
        ws["A3"] = subtitle.upper()
        ws["A3"].font = font_subtitle
        ws["A3"].alignment = Alignment(horizontal="center")

        ws.merge_cells("A4:P4")
        ws["A4"] = f"FECHA CORTE: {date_range.upper()}"
        ws["A4"].font = Font(name="Calibri", size=11, bold=True, italic=True)
        ws["A4"].alignment = Alignment(horizontal="center")

        # Column headers matching Control_Inventario.xlsx format
        headers = [
            "CLIENTE", "DESARROLLO", "FECHA_SOLICITUD", "UBICACION", "MZ", "LOTE", "EDIF", "VIV", 
            "FOLIO", "ESTATUS_PRIMER_AVISO", "ANALISIS", "AVISO", "CLG", "CANC_1ER _AVISO", "CANC_2DO_AVISO", "NUEVO_DERECHO_AVISO"
        ]
        
        ws.row_dimensions[6].height = 25
        for col_idx, text_header in enumerate(headers, start=1):
            cell = ws.cell(row=6, column=col_idx, value=text_header)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=Side(border_style="medium", color="000000"))

        # We need to pivot data_rows (which are normalized in details) back to a single row per client
        # to generate a clean sheet similar to Control_Inventario.xlsx
        pivot_data = {}
        for r in data_rows:
            # Group key by client and location coordinates
            key = (r["cliente"], r["desarrollo"], r["mz"], r["lote"], r["edif"], r["viv"], r["folio_electronico"])
            if key not in pivot_data:
                pivot_data[key] = {
                    "cliente": r["cliente"],
                    "desarrollo": r["desarrollo"],
                    "fecha_solicitud": r.get("fecha_solicitud", ""),
                    "mz": r["mz"],
                    "lote": r["lote"],
                    "edif": r["edif"],
                    "viv": r["viv"],
                    "folio": r["folio_electronico"],
                    "estatus": r.get("estatus_primer_aviso", ""),
                    "references": {}
                }
            concept = r["concepto"]
            pivot_data[key]["references"][concept] = r["referencia"]

        row_num = 7
        for key, p in pivot_data.items():
            ws.row_dimensions[row_num].height = 18
            
            # Build location string
            loc_str = ""
            if p["mz"]: loc_str += f"MZ {p['mz']} "
            if p["lote"]: loc_str += f"LT {p['lote']} "
            if p["edif"]: loc_str += f"EDIF {p['edif']} "
            if p["viv"]: loc_str += f"VIV {p['viv']} "
            loc_str = loc_str.strip()

            ws.cell(row=row_num, column=1, value=p["cliente"])
            ws.cell(row=row_num, column=2, value=p["desarrollo"])
            ws.cell(row=row_num, column=3, value=p["fecha_solicitud"])
            ws.cell(row=row_num, column=4, value=loc_str)
            ws.cell(row=row_num, column=5, value=p["mz"])
            ws.cell(row=row_num, column=6, value=p["lote"])
            ws.cell(row=row_num, column=7, value=p["edif"] or None)
            ws.cell(row=row_num, column=8, value=p["viv"])
            ws.cell(row=row_num, column=9, value=p["folio"])
            ws.cell(row=row_num, column=10, value=p["estatus"])
            
            # Concept references columns mapping
            ws.cell(row=row_num, column=11, value=p["references"].get("ANALISIS", ""))
            ws.cell(row=row_num, column=12, value=p["references"].get("AVISO", ""))
            ws.cell(row=row_num, column=13, value=p["references"].get("CLG", ""))
            ws.cell(row=row_num, column=14, value=p["references"].get("CANC_1ER _AVISO", ""))
            ws.cell(row=row_num, column=15, value=p["references"].get("CANC_2DO_AVISO", ""))
            ws.cell(row=row_num, column=16, value=p["references"].get("NUEVO_DERECHO_AVISO", ""))
            
            for c in range(1, 17):
                cell = ws.cell(row=row_num, column=c)
                cell.font = font_data
                cell.border = border_data
                if c in (3, 5, 6, 7, 8, 9, 10):
                    cell.alignment = Alignment(horizontal="center")
                    
            row_num += 1

        # Adjust column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 10)

        wb.save(dest_path)
