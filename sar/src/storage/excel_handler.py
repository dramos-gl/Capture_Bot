"""Excel handler for lot generations using openpyxl."""

import openpyxl
from typing import List, Dict, Any

def generate_excel_batch(filepath: str, data: List[Dict[str, Any]]) -> None:
    """Generates an Excel file with columns: Id, Referencia, Cantidad, Importe, Porcentaje.
    
    Args:
        filepath: The destination file path.
        data: A list of dictionaries with keys 'id', 'Referencia', 'cantidad', 'importe', 'porcentaje'.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lote"
    
    # Headers
    headers = ["Id", "Referencia", "Cantidad", "Importe", "Porcentaje"]
    ws.append(headers)
    
    # Data rows
    for row in data:
        ws.append([
            row.get("id"),
            row.get("Referencia"),
            row.get("cantidad"),
            row.get("importe"),
            row.get("porcentaje")
        ])
        
    # Auto-fit column widths to prevent text clipping
    for col in ws.columns:
        max_len = 0
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or '')
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)
        
    wb.save(filepath)
