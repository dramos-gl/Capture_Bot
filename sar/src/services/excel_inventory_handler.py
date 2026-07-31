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
        
        def get_idx(*names):
            for name in names:
                name_upper = name.strip().upper()
                if name_upper in headers:
                    return headers.index(name_upper)
            return -1

        idx_cliente = get_idx("CLIENTE", "NOMBRE CLIENTE", "NOMBRE")
        idx_desarrollo = get_idx("DESARROLLO")
        idx_empresa = get_idx("EMPRESA", "RFC", "EMPRESA FACTURADORA")
        idx_fecha_sol = get_idx("FECHA_SOLICITUD", "FECHA SOLICITUD", "FECHA")
        idx_ubicacion = get_idx("UBICACION", "UBICACIÓN")
        idx_mz = get_idx("MZ", "MANZANA")
        idx_lote = get_idx("LOTE", "LT")
        idx_edif = get_idx("EDIF", "EDIFICIO")
        idx_viv = get_idx("VIV", "VIVIENDA")
        idx_folio = get_idx("FOLIO")
        idx_estatus_aviso = get_idx("ESTATUS_PRIMER_AVISO", "ESTATUS RPP")
        idx_credito_titular = get_idx("CREDITO_TITULAR", "CREDITO TITULAR", "CREDITO", "TITULAR", "CREDITO_O_TITULAR")
        idx_pa = get_idx("PA", "PADRON", "PADRÓN")
        idx_delegacion = get_idx("DELEGACION", "DELEGACIÓN")
        
        # Concept reference columns (resilient to accents, spaces, and abbreviations)
        concept_cols = {
            "ANALISIS": get_idx("ANALISIS", "ANÁLISIS", "ANALIS"),
            "AVISO": get_idx("AVISO", "1ER_AVISO", "1ER _AVISO", "AVISO_RPP", "PRIMER AVISO", "AVISO PREVENTIVO"),
            "CLG": get_idx("CLG", "CERTIFICADO", "CLG_RPP"),
            "CANC_1ER _AVISO": get_idx("CANC_1ER _AVISO", "CANC_1ER_AVISO", "CANCELACION_1ER_AVISO", "CANCELACIÓN 1ER AVISO", "CANCELACION 1ER AVISO"),
            "CANC_2DO_AVISO": get_idx("CANC_2DO_AVISO", "CANCELACION_2DO_AVISO", "CANCELACIÓN 2DO AVISO", "CANCELACION 2DO AVISO"),
            "NUEVO_DERECHO_AVISO": get_idx("NUEVO_DERECHO_AVISO", "NUEVO_AVISO", "NUEVO DERECHO AVISO"),
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
            empresa = str(row[idx_empresa]).strip().upper() if idx_empresa != -1 and row[idx_empresa] is not None else ""
            
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
            
            raw_ubicacion = str(row[idx_ubicacion]).strip() if idx_ubicacion != -1 and row[idx_ubicacion] is not None else ""

            # Parse fallback from UBICACION text column if mz/lote are empty
            if (not mz and not lote) and idx_ubicacion != -1 and row[idx_ubicacion] is not None:
                # Try parsing e.g. "MZ 38 LT 2 VIV 35"
                import re
                txt = raw_ubicacion.upper()
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
            credito_titular = str(row[idx_credito_titular]).strip() if idx_credito_titular != -1 and row[idx_credito_titular] is not None else ""
            pa = str(row[idx_pa]).strip() if idx_pa != -1 and row[idx_pa] is not None else ""
            delegacion = str(row[idx_delegacion]).strip() if idx_delegacion != -1 and row[idx_delegacion] is not None else ""

            # Check each concept reference column
            for concept_name, col_idx in concept_cols.items():
                if col_idx != -1 and row[col_idx] is not None:
                    ref_val = str(row[col_idx]).strip()
                    # Skip empty/None references or headers accidentally repeated
                    if not ref_val or ref_val.upper() in ("NONE", "NULL", "-", ""):
                        continue
                    
                    is_indicator = False
                    if len(ref_val) <= 4 or ref_val.upper() in ("X", "SI", "S", "1", "YES", "OK", "X/"):
                        is_indicator = True
                    
                    # Store record
                    parsed_records.append({
                        "excel_row": row_num,
                        "cliente": cliente,
                        "desarrollo": desarrollo,
                        "empresa": empresa,
                        "fecha_solicitud": fecha_sol,
                        "ubicacion": raw_ubicacion,
                        "mz": mz,
                        "lote": lote,
                        "edif": edif,
                        "viv": viv,
                        "folio_electronico": folio,
                        "estatus_primer_aviso": estatus_aviso,
                        "credito_titular": credito_titular,
                        "pa": pa,
                        "delegacion": delegacion,
                        "concepto_solicitado": concept_name,
                        "referencia_asignada": "" if is_indicator else ref_val,
                        "requiere_autovincular": is_indicator
                    })

        return parsed_records

    @staticmethod
    def validate_parsed_rows(session, parsed_rows: List[Dict[str, Any]], default_rfc_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Validates parsed rows against the database, enforcing:
        1. Reference exists and is FACTURADA (or auto-assigns an available one if empty).
        2. Reference is not already assigned.
        3. Concept matching (CLG, AVISO, etc.).
        4. Geolocation match (desarrollo delegation == reference delegation).
        5. Company (RFC) matching for autolink and validation.
        """
        from sar.src.storage.models import Referencia, EstadoSistema, Desarrollo, Delegacion, GrupoReferencia, Concepto, Solicitud, Rfc, LoteDetalle
        from sqlalchemy import select
        
        # Cache concepts mapping
        concepto_stmt = select(Concepto)
        concepts = session.execute(concepto_stmt).scalars().all()
        concept_alias_map = {c.alias: c for c in concepts if c.alias}

        # Cache RFCs mapping (razon_social and rfc strings to id)
        rfcs_stmt = select(Rfc).where(Rfc.activo == True)
        rfcs = session.execute(rfcs_stmt).scalars().all()
        rfcs_map = {r.razon_social.strip().upper(): r.rfc_id for r in rfcs}
        rfcs_map.update({r.rfc.strip().upper(): r.rfc_id for r in rfcs})
        
        validated_rows = []
        allocated_ref_ids = set()

        for row in parsed_rows:
            ref_str = row["referencia_asignada"]
            concept_req = row["concepto_solicitado"]
            desarrollo_name = row["desarrollo"]
            row_empresa = row.get("empresa", "").strip().upper()
            req_autolink = row.get("requiere_autovincular", False)
            
            row_result = dict(row)
            row_result["status"] = "PENDIENTE" # default
            row_result["error_message"] = ""
            row_result["referencia_id"] = None
            row_result["desarrollo_id"] = None
            row_result["delegacion_nombre"] = ""
            row_result["rfc_id"] = None
            
            # Resolve Company (RFC)
            resolved_rfc_id = None
            if row_empresa:
                resolved_rfc_id = rfcs_map.get(row_empresa)
                if not resolved_rfc_id:
                    row_result["status"] = "ERROR"
                    row_result["error_message"] = f"La empresa '{row_empresa}' no está registrada o no está activa."
                    validated_rows.append(row_result)
                    continue
            else:
                resolved_rfc_id = default_rfc_id

            row_result["rfc_id"] = resolved_rfc_id
            
            # 1. Lookup/register Desarrollo first
            des_stmt = select(Desarrollo).where(Desarrollo.nombre == desarrollo_name)
            desarrollo = session.execute(des_stmt).scalars().first()
            
            if not desarrollo:
                deleg_id = 2 # default Cancun
                if "PLAYA" in desarrollo_name or "TULUM" in desarrollo_name:
                    deleg_id = 3 # Playa del Carmen
                
                desarrollo = Desarrollo(nombre=desarrollo_name, delegacion_id=deleg_id, activo=True)
                session.add(desarrollo)
                session.flush()
            
            row_result["desarrollo_id"] = desarrollo.desarrollo_id
            
            # Fetch delegation details for development
            deleg_stmt = select(Delegacion.nombre).where(Delegacion.delegacion_id == desarrollo.delegacion_id)
            deleg_name = session.execute(deleg_stmt).scalar()
            row_result["delegacion_nombre"] = deleg_name

            # Check if this client already has an assignment for the same concept at this exact location
            dup_stmt = select(LoteDetalle).where(
                LoteDetalle.cliente == cliente,
                LoteDetalle.desarrollo_id == desarrollo.desarrollo_id,
                LoteDetalle.mz == mz,
                LoteDetalle.lote == lote,
                LoteDetalle.edif == edif,
                LoteDetalle.viv == viv,
                LoteDetalle.concepto_solicitado == concept_req
            )
            dup_check = session.execute(dup_stmt).scalars().first()
            has_dup = dup_check is not None
            dup_ref = dup_check.referencia_asignada if dup_check else None

            # Handle automatic reference assignment
            if req_autolink or not ref_str:
                if not resolved_rfc_id:
                    row_result["status"] = "ERROR"
                    row_result["error_message"] = "Debe especificar la Empresa en el Excel o seleccionar una Empresa por Defecto en la pantalla."
                    validated_rows.append(row_result)
                    continue

                expected_aliases = []
                if concept_req == "CLG": expected_aliases = ["CLG"]
                elif concept_req in ("AVISO", "NUEVO_DERECHO_AVISO"): expected_aliases = ["AVISO PREVENTIVO"]
                elif concept_req == "ANALISIS": expected_aliases = ["ANALISIS"]
                else: expected_aliases = [concept_req]

                # Find a reference in FACTURADA state for this concept, delegation, and company
                available_stmt = (
                    select(Referencia)
                    .join(EstadoSistema, Referencia.estado_id == EstadoSistema.estado_id)
                    .join(GrupoReferencia, Referencia.grupo_id == GrupoReferencia.grupo_id)
                    .join(Concepto, GrupoReferencia.concepto_id == Concepto.concepto_id)
                    .join(Solicitud, Referencia.solicitud_id == Solicitud.solicitud_id)
                    .where(
                        EstadoSistema.entidad == 'referencia',
                        EstadoSistema.codigo == 'FACTURADA',
                        Concepto.alias.in_(expected_aliases),
                        Solicitud.delegacion_id == desarrollo.delegacion_id,
                        GrupoReferencia.rfc_id == resolved_rfc_id
                    )
                )
                if allocated_ref_ids:
                    available_stmt = available_stmt.where(Referencia.referencia_id.not_in(list(allocated_ref_ids)))

                ref_obj = session.execute(available_stmt).scalars().first()
                if not ref_obj:
                    row_result["status"] = "ERROR"
                    row_result["error_message"] = f"No hay facturas disponibles ('FACTURADA') para '{concept_req}' de la empresa seleccionada en '{deleg_name}'."
                    validated_rows.append(row_result)
                    continue

                row_result["referencia_id"] = ref_obj.referencia_id
                row_result["referencia_asignada"] = ref_obj.referencia_portal
                allocated_ref_ids.add(ref_obj.referencia_id)
                if has_dup:
                    row_result["status"] = "WARNING"
                    row_result["error_message"] = f"El cliente ya tiene una asignación de {concept_req} para esta ubicación en un lote anterior (Ref: {dup_ref})."
                else:
                    row_result["status"] = "CORRECTO"
                validated_rows.append(row_result)
                continue

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
            if has_dup:
                row_result["status"] = "WARNING"
                row_result["error_message"] = f"El cliente ya tiene una asignación de {concept_req} para esta ubicación en un lote anterior (Ref: {dup_ref})."
            else:
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

    @staticmethod
    def generate_blank_template(dest_path: str):
        """Generates a blank styled Excel sheet containing the correct columns for bulk import."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Hoja1"

        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        
        font_header = Font(name="Calibri", size=10, bold=True, color="000000")
        fill_header = PatternFill(start_color="86C232", end_color="86C232", fill_type="solid") # Sleek green
        border_thin = Side(border_style="thin", color="D3D3D3")

        headers = [
            "CLIENTE", "DESARROLLO", "EMPRESA", "FECHA_SOLICITUD", "UBICACION", "MZ", "LOTE", "EDIF", "VIV", 
            "FOLIO", "ESTATUS_PRIMER_AVISO", "CREDITO_TITULAR", "PA", "DELEGACION", "ANALISIS", "AVISO", "CLG", "CANC_1ER _AVISO", "CANC_2DO_AVISO", "NUEVO_DERECHO_AVISO"
        ]
        
        ws.row_dimensions[1].height = 25
        for col_idx, text_header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=text_header)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=Side(border_style="medium", color="000000"))

        # Add a mock row as a reference example for users
        ws.row_dimensions[2].height = 18
        mock_data = [
            "JUAN PEREZ", "ALDEA TULUM", "PROMOTORA RESIDENCIAL", "2026-07-21", "MZ 10 LT 5 VIV 3", "10", "5", "", "3",
            "123456", "NUEVO INGRESO", "123456789", "PA-ALDEA", "TULUM", "", "70028350819888101", "", "", "", ""
        ]
        for col_idx, val in enumerate(mock_data, start=1):
            cell = ws.cell(row=2, column=col_idx, value=val)
            cell.font = Font(name="Calibri", size=10, italic=True)
            cell.border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)

        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        wb.save(dest_path)

