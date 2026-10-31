import openpyxl
import xlrd
from datetime import datetime
from typing import List, Dict, Any

def parse_reporte_ubicaciones_erp(file_path: str) -> List[Dict[str, Any]]:
    """
    Lee y normaliza el reporte de ubicaciones del ERP (compatible con .xls nativo OLE2 y .xlsx).
    Maneja el formato nativo del ERP con fila de título en fila 0 y cabeceras en fila 1.
    """
    records = []
    
    if file_path.lower().endswith(".xls"):
        wb = xlrd.open_workbook(file_path)
        sh = wb.sheet_by_index(0)
        
        # Buscar la fila de cabeceras en las primeras 5 filas
        header_row = 1
        for r in range(min(5, sh.nrows)):
            row_vals = [str(v or "").strip().upper() for v in sh.row_values(r)]
            if any("STATUS LOTE" in v or "MZNA" in v or "LOTE" in v for v in row_vals):
                header_row = r
                break

        headers = [str(v or "").strip().upper() for v in sh.row_values(header_row)]

        def get_idx(*names):
            for name in names:
                for idx, h in enumerate(headers):
                    if h == name.upper() or h.startswith(name.upper()):
                        return idx
            return -1

        c_des = get_idx("DESAR.", "DESARROLLO")
        c_mz = get_idx("MZNA.", "MZNA", "MANZANA", "MZ")
        c_lt = get_idx("LOTE", "LT")
        c_ext = get_idx("EXTERIOR", "EXT", "NO. OFICIAL")
        c_int = get_idx("INTERIOR", "INT", "DEPTO", "UPE")
        c_st = get_idx("STATUS LOTE", "ESTATUS LOTE", "STATUS")
        c_fst = get_idx("FECHA STATUS LOTE", "FECHA ESTATUS LOTE", "FECHA STATUS")
        c_cli = get_idx("CLIENTE")
        c_nss = get_idx("NSS", "NNS")
        c_eta = get_idx("ETAPA")
        c_niv = get_idx("NIVEL")

        # La columna con el nombre del cliente suele ser la contigua al ID numérico de cliente
        c_nom = c_cli + 1 if (c_cli != -1 and c_cli + 1 < len(headers) and headers[c_cli + 1] == "") else c_cli

        for r_idx in range(header_row + 1, sh.nrows):
            row = sh.row_values(r_idx)
            
            # Formatear fecha status si es número de fecha Excel
            f_val = row[c_fst] if c_fst != -1 else ""
            f_str = ""
            if isinstance(f_val, float) and f_val > 0:
                try:
                    f_tuple = xlrd.xldate_as_tuple(f_val, wb.datemode)
                    f_str = datetime(*f_tuple).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    f_str = str(f_val)
            else:
                f_str = str(f_val or "").strip()

            cli_nombre = str(row[c_nom] if c_nom != -1 else "").strip()
            if not cli_nombre and c_cli != -1:
                cli_nombre = str(row[c_cli] or "").strip()

            records.append({
                "desarrollo": str(row[c_des] if c_des != -1 else "").strip(),
                "mz": str(row[c_mz] if c_mz != -1 else "").strip(),
                "lote": str(row[c_lt] if c_lt != -1 else "").strip(),
                "exterior": str(row[c_ext] if c_ext != -1 else "").strip(),
                "interior": str(row[c_int] if c_int != -1 else "").strip(),
                "nivel": str(row[c_niv] if c_niv != -1 else "").strip(),
                "status_lote": str(row[c_st] if c_st != -1 else "").strip(),
                "fecha_estatus_lote": f_str,
                "cliente": cli_nombre,
                "nss": str(row[c_nss] if c_nss != -1 else "").strip(),
                "etapa": str(row[c_eta] if c_eta != -1 else "").strip()
            })
    else:
        # Formato .xlsx con openpyxl
        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) > 1:
            header_row = 1
            for r_idx in range(min(5, len(rows))):
                row_vals = [str(v or "").strip().upper() for v in rows[r_idx]]
                if any("STATUS LOTE" in v or "MZNA" in v or "LOTE" in v for v in row_vals):
                    header_row = r_idx
                    break
            
            headers = [str(v or "").strip().upper() for v in rows[header_row]]
            
            def get_idx_xlsx(*names):
                for name in names:
                    for idx, h in enumerate(headers):
                        if h == name.upper() or h.startswith(name.upper()):
                            return idx
                return -1

            c_des = get_idx_xlsx("DESAR.", "DESARROLLO")
            c_mz = get_idx_xlsx("MZNA.", "MZNA", "MANZANA", "MZ")
            c_lt = get_idx_xlsx("LOTE", "LT")
            c_ext = get_idx_xlsx("EXTERIOR", "EXT", "NO. OFICIAL")
            c_int = get_idx_xlsx("INTERIOR", "INT", "DEPTO", "UPE")
            c_st = get_idx_xlsx("STATUS LOTE", "ESTATUS LOTE", "STATUS")
            c_fst = get_idx_xlsx("FECHA STATUS LOTE", "FECHA ESTATUS LOTE", "FECHA STATUS")
            c_cli = get_idx_xlsx("CLIENTE")
            c_nss = get_idx_xlsx("NSS", "NNS")
            c_eta = get_idx_xlsx("ETAPA")
            c_niv = get_idx_xlsx("NIVEL")

            c_nom = c_cli + 1 if (c_cli != -1 and c_cli + 1 < len(headers) and headers[c_cli + 1] == "") else c_cli

            for row in rows[header_row + 1:]:
                f_val = row[c_fst] if c_fst != -1 else ""
                f_str = f_val.strftime("%Y-%m-%d %H:%M") if hasattr(f_val, "strftime") else str(f_val or "").strip()
                cli_nombre = str(row[c_nom] if c_nom != -1 else "").strip()
                if not cli_nombre and c_cli != -1:
                    cli_nombre = str(row[c_cli] or "").strip()

                records.append({
                    "desarrollo": str(row[c_des] if c_des != -1 else "").strip(),
                    "mz": str(row[c_mz] if c_mz != -1 else "").strip(),
                    "lote": str(row[c_lt] if c_lt != -1 else "").strip(),
                    "exterior": str(row[c_ext] if c_ext != -1 else "").strip(),
                    "interior": str(row[c_int] if c_int != -1 else "").strip(),
                    "nivel": str(row[c_niv] if c_niv != -1 else "").strip(),
                    "status_lote": str(row[c_st] if c_st != -1 else "").strip(),
                    "fecha_estatus_lote": f_str,
                    "cliente": cli_nombre,
                    "nss": str(row[c_nss] if c_nss != -1 else "").strip(),
                    "etapa": str(row[c_eta] if c_eta != -1 else "").strip()
                })

    return records
