"""
Formatters utility module for SAR UI.
Provides consistent formatting helpers across the application.
"""
from typing import Optional


def format_orden_filter_label(folio: str, descripcion: Optional[str] = None, max_desc_len: int = 50) -> str:
    """
    Formats order description for UI filters and dropdown menus.
    
    Prioritizes the human-readable description (e.g. 'Subsidios Agosto 2026')
    to provide a clean, non-repetitive operational UX.
    
    Fallback:
        If description is missing or empty, returns the clean folio prefix.
    """
    desc = (descripcion or "").strip()
    if desc:
        if len(desc) > max_desc_len:
            return desc[:max_desc_len].rstrip() + "..."
        return desc

    # Fallback si no tiene descripción capturada
    if not folio:
        return ""

    parts = str(folio).strip().split("-")
    if len(parts) >= 2:
        return f"{parts[0]}-{parts[1]}"
    return str(folio).strip()
