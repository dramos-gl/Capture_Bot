"""
Formatters utility module for SAR UI.
Provides consistent formatting helpers across the application.
"""
from typing import Optional


def format_orden_filter_label(folio: str, descripcion: Optional[str] = None, max_desc_len: int = 50) -> str:
    """
    Formats order folio and description for UI filters and dropdown menus.
    
    Transforms technical folios such as:
        'ORD-20260709-234440' with description 'Subsidios Julio 2026'
    Into human-readable operational labels:
        'ORD-20260709 - Subsidios Julio 2026'
    
    Handles:
        - Prefixes: Takes 'ORD-YYYYMMDD' from 'ORD-YYYYMMDD-HHMMSS[-SUFFIX]'
        - Empty or missing descriptions
        - Truncation of excessively long descriptions
    """
    if not folio:
        return ""

    parts = str(folio).strip().split("-")
    if len(parts) >= 2:
        prefix = f"{parts[0]}-{parts[1]}"
    else:
        prefix = str(folio).strip()

    desc = (descripcion or "").strip()
    if desc:
        if len(desc) > max_desc_len:
            desc = desc[:max_desc_len].rstrip() + "..."
        return f"{prefix} - {desc}"

    return prefix
