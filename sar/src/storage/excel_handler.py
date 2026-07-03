"""Excel handler for lot generations using openpyxl."""

import openpyxl
from typing import List, Dict, Any

def generate_excel_batch(filepath: str, data: List[Dict[str, Any]]) -> None:
    """Generates an Excel file with columns: id, Referencia, importe.
    
    Args:
        filepath: The destination file path.
        data: A list of dictionaries with keys 'id', 'Referencia', 'importe'.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lote"
    
    # Headers
    headers = ["id", "Referencia", "importe"]
    ws.append(headers)
    
    # Data rows
    for row in data:
        ws.append([
            row.get("id"),
            row.get("Referencia"),
            row.get("importe")
        ])
        
    wb.save(filepath)
