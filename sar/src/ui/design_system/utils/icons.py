"""SVG Icon generator for Design System."""

import base64
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtSvg import QSvgRenderer

class Icons:
    """Provides standard QIcons rendered from SVG paths."""

    # Estructura organizada por las categorías reales del sistema administrativo
    CATEGORIES = {
        "Acción Principal": {
            "guardar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>''',
            "guardar_nuevo": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15.2 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v5.5"></path><path d="M16 19h6M19 16v6"></path><path d="M7 3v5h8V3"></path></svg>''',
            "editar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"></path></svg>''',
            "eliminar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2M10 11v6M14 11v6"></path></svg>''',
            "cancelar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="m15 9-6 6M9 9l6 6"></path></svg>''',
            "salir": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"></path></svg>''',
            "volver": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"></path></svg>''',
            "siguiente": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M12 5l7 7-7 7"></path></svg>''',
            "aceptar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="m9 12 2 2 4-4"></path></svg>''',
            "rechazar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="m4.93 4.93 14.14 14.14"></path></svg>''',
            "cerrar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18M6 6l12 12"></path></svg>''',
            "limpiar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 21 1.9-5.7a8.5 8.5 0 1 1 3.8 3.8L3 21M5 16l3.5 3.5M11.5 11.5 16 7M10 13l4-4M13 14.5l4-4"></path></svg>''',
            "actualizar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"></path><path d="M16 16h5v5"></path></svg>''',
            "deshacer": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7v6h6"></path><path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"></path></svg>''',
            "rehacer": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 7v6h-6"></path><path d="M3 17a9 9 0 0 1 9-9 9 9 0 0 1 6 2.3l3 2.7"></path></svg>'''
        },
        "Navegación": {
            "inicio": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>''',
            "dashboard": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="9" x="3" y="3" rx="1"></rect><rect width="7" height="5" x="14" y="3" rx="1"></rect><rect width="7" height="9" x="14" y="10" rx="1"></rect><rect width="7" height="5" x="3" y="14" rx="1"></rect></svg>''',
            "modulos": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="3" width="7" height="7" rx="1"></rect><rect x="3" y="14" width="7" height="7" rx="1"></rect><rect x="14" y="14" width="7" height="7" rx="1"></rect></svg>''',
            "menu": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" x2="20" y1="12" y2="12"></line><line x1="4" x2="20" y1="6" y2="6"></line><line x1="4" x2="20" y1="18" y2="18"></line></svg>''',
            "submenu": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6h16M10 12h10M10 18h10M4 10v8h3"></path></svg>''',
            "arriba": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m18 15-6-6-6 6"></path></svg>''',
            "abajo": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"></path></svg>''',
            "izquierda": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"></path></svg>''',
            "derecha": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"></path></svg>''',
            "ir_a": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14 21 3"></path></svg>''',
            "anterior": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m17 18-6-6 6-6M6 6v12"></path></svg>''',
            "siguiente_skip": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m7 6 6 6-6 6M18 6v12"></path></svg>''',
            "ultimo": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m5 4 8 8-8 8M19 5v14"></path></svg>''',
            "expandir": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"></path></svg>''',
            "colapsar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 14h6v6M20 10h-6V4M14 10l7-7M10 14l-7 7"></path></svg>'''
        },
        "Búsqueda y Filtros": {
            "buscar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>''',
            "busqueda_avanzada": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><path d="M8 8h6M9 14h4"></path></svg>''',
            "filtrar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z"></path></svg>''',
            "quitar_filtro": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 3H2l8 9.46V19l4 2v-8.54L18 3M22 6l-4 4M18 6l4 4"></path></svg>''',
            "ordenar_az": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5h10M11 9h7M11 13h4M3 17l3 3 3-3M6 18V4"></path></svg>''',
            "ordenar_za": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5h4M11 9h7M11 13h10M3 17l3 3 3-3M6 18V4"></path></svg>''',
            "columnas": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3h18v18H3zM12 3v18"></path></svg>''',
            "agrupar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="6" height="6" rx="1"></rect><rect x="15" y="3" width="6" height="6" rx="1"></rect><rect x="9" y="14" width="6" height="6" rx="1"></rect><path d="M9 6h6M6 14v-2h12v2"></path></svg>''',
            "desagrupar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 9h14M5 15h14M9 5v14M15 5v14"></path></svg>''',
            "vista_lista": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>''',
            "vista_cuadricula": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="14" width="7" height="7" rx="1"></rect><rect x="3" y="14" width="7" height="7" rx="1"></rect></svg>''',
            "vista_tarjetas": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="7" rx="1"></rect><rect x="3" y="14" width="18" height="7" rx="1"></rect></svg>''',
            "exportar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8M16 6l-4-4-4 4M12 2v13"></path></svg>''',
            "importar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8M12 15V2M8 11l4 4 4-4"></path></svg>'''
        },
        "Visualización": {
            "visualizar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>''',
            "detalles": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="9" y1="9" x2="15" y2="9"></line><line x1="9" y1="13" x2="15" y2="13"></line><line x1="9" y1="17" x2="13" y2="17"></line></svg>''',
            "informacion": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>''',
            "vista_previa": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><path d="M6 12c2.5-3 5.5-3 8 0M10 12a1 1 0 1 0 0-2 1 1 0 0 0 0 2z"></path></svg>''',
            "pantalla_completa": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3"></path></svg>''',
            "minimizar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line></svg>''',
            "zoom_in": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="11" y1="8" x2="11" y2="14"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>''',
            "zoom_out": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>''',
            "acercar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 15-6-6M9 15v-6h6M4 20l5-5"></path></svg>''',
            "alejar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 9 6 6M15 9h-6v6M20 4l-5 5"></path></svg>''',
            "ajustar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h18M12 3v18M8 8l4-4 4 4M8 16l4 4 4-4"></path></svg>''',
            "ocultar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>''',
            "mostrar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>''',
            "reordenar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8h16M4 16h16M8 5l4-4 4 4M16 19l-4 4-4-4M12 2v20"></path></svg>''',
            "mas_opciones": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"></circle><circle cx="12" cy="5" r="1"></circle><circle cx="12" cy="19" r="1"></circle></svg>'''
        },
        "Documentos": {
            "documento_nuevo": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"></path><path d="M14 2v4a2 2 0 0 0 2 2h4M9 15h6M12 12v6"></path></svg>''',
            "documento_abrir": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 14h12M6 10h12M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>''',
            "documento_guardar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>''',
            "documento_guardar_como": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><path d="m8 14 3 3 5-5"></path></svg>''',
            "documento_duplicar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>''',
            "documento_eliminar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"></path><path d="M14 2v4a2 2 0 0 0 2 2h4M9 13h6M10 16h4"></path></svg>''',
            "documento_imprimir": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 6 2 18 2 18 9"></polyline><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path><rect x="6" y="14" width="12" height="8"></rect></svg>''',
            "documento_vista_previa": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"></path><path d="M14 2v4a2 2 0 0 0 2 2h4"></path><circle cx="11" cy="14" r="3"></circle></svg>''',
            "documento_descargar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"></path><path d="M14 2v4a2 2 0 0 0 2 2h4M12 11v6M9 14l3 3 3-3"></path></svg>''',
            "documento_cargar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"></path><path d="M14 2v4a2 2 0 0 0 2 2h4M12 17v-6M9 14l3-3 3 3"></path></svg>''',
            "documento_adjuntar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>''',
            "documento_desadjuntar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21 21-9-9M9 5l4-4a4 4 0 0 1 5.66 5.66l-3 3M5.5 12.5a6 6 0 0 0 8.49 8.49l3-3M3 3l18 18"></path></svg>''',
            "documento_plantilla": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"></path><path d="M14 2v4a2 2 0 0 0 2 2h4M12 11l1 2h2l-1.5 1.5.5 2-2-1-2 1 .5-2L9 13h2z"></path></svg>''',
            "documento_historial": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"></path><path d="M14 2v4a2 2 0 0 0 2 2h4M12 12v4l3 1"></path></svg>''',
            "documento_versiones": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"></path></svg>'''
        },
        "Datos y Tablas": {
            "nuevo_registro": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3h18v18H3zM3 9h18M3 15h18M12 9v12M15 6h2M16 5v2"></path></svg>''',
            "editar_registro": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3h18v18H3zM3 9h18M3 15h18M12 9v12M14 5l4 4"></path></svg>''',
            "eliminar_registro": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3h18v18H3zM3 9h18M3 15h18M12 9v12M14 6h4"></path></svg>''',
            "duplicar_registro": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="9" width="12" height="12" rx="1"></rect><rect x="9" y="3" width="12" height="12" rx="1"></rect></svg>''',
            "exportar_datos": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path><path d="M19 14h6M22 11l3 3-3 3"></path></svg>''',
            "importar_datos": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path><path d="M25 14h-6M22 11l-3 3 3 3"></path></svg>''',
            "resumen": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="7" y1="8" x2="17" y2="8"></line><line x1="7" y1="12" x2="13" y2="12"></line><line x1="7" y1="16" x2="15" y2="16"></line></svg>''',
            "grafico": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>''',
            "tabla": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3h18v18H3zM21 9H3M21 15H3M12 3v18"></path></svg>''',
            "campos": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"></rect><path d="M21 9H3M21 15H3M12 3v18"></path></svg>''',
            "configuracion_tabla": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.1a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"></path><circle cx="12" cy="12" r="3"></circle></svg>''',
            "validar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10zM9 11l2 2 4-4"></path></svg>''',
            "advertencia": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>''',
            "error": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>''',
            "exito": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="m9 12 2 2 4-4"></path></svg>'''
        },
        "Usuarios y Seguridad": {
            "usuario": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>''',
            "usuarios": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"></path></svg>''',
            "grupo": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-3-3.87M9 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="10" cy="7" r="4"></circle><circle cx="18" cy="11" r="3"></circle></svg>''',
            "roles": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm10-5h3m-3 4h3m-3 4h3"></path></svg>''',
            "permisos": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21 2-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0 3 3L22 7l-3-3m-3.5 3.5 3-3"></path></svg>''',
            "bloquear": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>''',
            "desbloquear": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 9.9-1"></path></svg>''',
            "cambiar_contrasenia": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4M12 14v4M10 16h4"></path></svg>''',
            "perfil": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"></rect><circle cx="12" cy="10" r="3"></circle><path d="M6 20v-1a3 3 0 0 1 3-3h6a3 3 0 0 1 3 3v1"></path></svg>''',
            "sesion": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M10 17l5-5-5-5M15 12H3"></path></svg>''',
            "actividad": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>''',
            "auditoria": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><circle cx="12" cy="14" r="3"></circle></svg>''',
            "seguridad": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.5 3.8 17 5 19 5a1 1 0 0 1 1 1z"></path><rect width="8" height="5" x="8" y="11" rx="1"></rect><path d="M9 11V9a3 3 0 0 1 6 0v2"></path></svg>''',
            "notificacion": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0"></path></svg>''',
            "mensajes": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>'''
        },
        "Configuración": {
            "configuracion": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.1a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"></path><circle cx="12" cy="12" r="3"></circle></svg>''',
            "preferencias": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14"></line><line x1="4" y1="10" x2="4" y2="3"></line><line x1="12" y1="21" x2="12" y2="12"></line><line x1="12" y1="8" x2="12" y2="3"></line><line x1="20" y1="21" x2="20" y2="16"></line><line x1="20" y1="12" x2="20" y2="3"></line><line x1="2" y1="14" x2="6" y2="14"></line><line x1="10" y1="8" x2="14" y2="8"></line><line x1="18" y1="16" x2="22" y2="16"></line></svg>''',
            "parametros": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 5h10M17 5h4M3 12h4M11 12h10M3 19h14M21 19h0M15 3v4M9 10v4M15 17v4"></path></svg>''',
            "opciones": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9M3 20h4M3 12h9M16 12h5M3 4h5M12 4h9"></path><circle cx="9" cy="4" r="1"></circle><circle cx="14" cy="12" r="1"></circle><circle cx="9" cy="20" r="1"></circle></svg>''',
            "idioma": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>''',
            "tema": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 14.7255 3.09032 17.1962 4.85857 19C5.03345 19.1749 5.27552 19.2612 5.51836 19.2318C5.99125 19.1744 6.46328 19.2555 6.89315 19.468C7.5414 19.7885 8 20.463 8 21.2C8 21.6418 8.35817 22 8.8 22H12ZM12 20V20ZM12 20H8.8C8.5 19.5 8 18 6.5 17.5C5.5 17.2 4.5 17.5 4 18C3 16.5 2.5 14.8 2.5 13"></path><circle cx="7.5" cy="10.5" r="1.5"></circle><circle cx="11.5" cy="7.5" r="1.5"></circle><circle cx="16.5" cy="9.5" r="1.5"></circle></svg>''',
            "notificaciones_config": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0M19 2v6M16 5h6"></path></svg>''',
            "integraciones": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10zM12 6V2M12 22v-4M6 12H2M22 12h-4"></path></svg>''',
            "api": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>''',
            "webhooks": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.5" y1="10.5" x2="15.5" y2="6.5"></line><line x1="8.5" y1="13.5" x2="15.5" y2="17.5"></line></svg>''',
            "sincronizar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l.73-.73"></path></svg>''',
            "respaldar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"></path><path d="M12 11v6M9 14l3-3 3 3"></path></svg>''',
            "restaurar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"></path><path d="M12 17v-6M9 14l3 3 3-3"></path></svg>''',
            "mantenimiento": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path></svg>''',
            "soporte": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18v-6a9 9 0 0 1 18 0v6M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3M3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3"></path></svg>'''
        },
        "Comunicación": {
            "correo": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>''',
            "enviar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>''',
            "responder": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 17 4 12 9 7"></polyline><path d="M20 18v-2a4 4 0 0 0-4-4H4"></path></svg>''',
            "responder_todos": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="17 17 12 12 17 7M9 17l-5-5 5-5"></polyline><path d="M20 18v-2a4 4 0 0 0-4-4H12"></path></svg>''',
            "reenviar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 17 20 12 15 7"></polyline><path d="M4 18v-2a4 4 0 0 1 4-4h12"></path></svg>''',
            "marcar_leido": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><path d="M2 6l10 7 10-7M4 18h16"></path></svg>''',
            "marcar_no_leido": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><circle cx="18" cy="8" r="2" fill="currentColor"></circle></svg>''',
            "importante": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>''',
            "favorito": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>''',
            "comentario": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg>''',
            "chat": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>''',
            "llamada": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>''',
            "videollamada": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m23 7-7 5 7 5V7z"></path><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>''',
            "anuncio": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5L6 9H2v6h4l5 4V5zM15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>''',
            "rss": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 11a9 9 0 0 1 9 9M4 4a16 16 0 0 1 16 16"></path><circle cx="5" cy="19" r="1"></circle></svg>'''
        },
        "Interfaz y Otros": {
            "switch_toggle": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="5" width="22" height="14" rx="7" ry="7"></rect><circle cx="16" cy="12" r="4"></circle></svg>''',
            "checkbox": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><polyline points="9 11 11 13 15 9"></polyline></svg>''',
            "radio_button": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="4" fill="currentColor"></circle></svg>''',
            "calendario": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>''',
            "fecha": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line><rect x="7" y="14" width="2" height="2"></rect><rect x="11" y="14" width="2" height="2"></rect></svg>''',
            "hora": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>''',
            "etiqueta": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"></path><line x1="7" y1="7" x2="7.01" y2="7"></line></svg>''',
            "archivo": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path><polyline points="13 2 13 9 20 9"></polyline></svg>''',
            "carpeta": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>''',
            "enlace": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>''',
            "copiar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>''',
            "cortar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="6" r="3"></circle><circle cx="6" cy="18" r="3"></circle><line x1="9.8" y1="8.2" x2="20" y2="18.4"></line><line x1="9.8" y1="15.8" x2="20" y2="5.6"></line></svg>''',
            "pegar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>''',
            "arrastrar": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m5 9-3 3 3 3M9 5l3-3 3 3M15 19l-3 3-3-3M19 9l3 3-3 3M2 12h20M12 2v20"></path></svg>''',
            "ayuda": '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'''
        }
    }

    # Flat map building
    MAP = {}
    for cat_name, icon_dict in CATEGORIES.items():
        for icon_name, svg in icon_dict.items():
            MAP[icon_name] = svg

    # Custom/Special icons keeping backwards compatibility
    _SHIELD_LOCK_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#2C3E50" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><rect x="9" y="11" width="6" height="4" rx="1"></rect><path d="M10 11V9a2 2 0 1 1 4 0v2"></path></svg>'''
    _EXCEL_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path><polyline points="14 2 14 8 20 8"></polyline><path d="M8 13h2v5H8z"></path><path d="M12 15h2v3h-2z"></path><path d="M16 12h2v6h-2z"></path></svg>'''
    _PDF_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path><polyline points="14 2 14 8 20 8"></polyline><path d="M9 15h1.5a1.5 1.5 0 0 0 0-3H9v6"></path><path d="M12 12v6h1.5a3 3 0 0 0 0-6H12z"></path><path d="M16 18V12h3"></path><path d="M16 15h2.5"></path></svg>'''
    _DOT_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="5" fill="currentColor"/></svg>'''
    _HOLLOW_DOT_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/></svg>'''

    # Legacy mapping for backwards compatibility with exact SVG paths if necessary
    _LEGACY_MAP = {
        "shield_lock_legacy": _SHIELD_LOCK_SVG,
        "excel_legacy": _EXCEL_SVG,
        "pdf_legacy": _PDF_SVG,
        "dot_legacy": _DOT_SVG,
        "hollow_dot_legacy": _HOLLOW_DOT_SVG
    }

    @classmethod
    def _create_icon(cls, svg_string: str, color: str = None) -> QIcon:
        if color:
            svg_string = svg_string.replace('currentColor', color)
        pixmap = QPixmap()
        pixmap.loadFromData(QByteArray(svg_string.encode('utf-8')), "SVG")
        return QIcon(pixmap)

    @classmethod
    def get_pixmap(cls, name: str, size: int = 24, color: str = "#475569") -> QPixmap:
        """Renderiza el icono SVG directamente a un QPixmap con calidad vectorial limpia."""
        if color is None:
            color = "#475569"
        svg_string = cls.MAP.get(name)
        if not svg_string:
            svg_string = cls._LEGACY_MAP.get(name, cls.MAP["ayuda"])
        
        # Replace color
        svg_string = svg_string.replace('currentColor', color)
        
        # Render
        renderer = QSvgRenderer(QByteArray(svg_string.encode('utf-8')))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        renderer.render(painter)
        painter.end()
        
        return pixmap

    @classmethod
    def get_icon(cls, name: str, size: int = 24, color: str = "#475569") -> QIcon:
        """Genera un QIcon de PySide6 para su uso en botones o elementos UI."""
        if color is None:
            color = "#475569"
        return QIcon(cls.get_pixmap(name, size, color))

    # --- LEGACY & CONVENIENCE METHODS (Backward Compatible) ---
    @classmethod
    def user(cls, color: str = None) -> QIcon:
        return cls.get_icon("usuario", color=color)

    @classmethod
    def lock(cls) -> QIcon:
        return cls.get_icon("bloquear")

    @classmethod
    def eye(cls) -> QIcon:
        return cls.get_icon("visualizar")
        
    @classmethod
    def eye_off(cls) -> QIcon:
        return cls.get_icon("ocultar")

    @classmethod
    def save(cls) -> QIcon:
        return cls.get_icon("guardar")

    @classmethod
    def close(cls) -> QIcon:
        return cls.get_icon("cerrar")

    @classmethod
    def minimize(cls) -> QIcon:
        return cls.get_icon("minimizar")

    @classmethod
    def shield_lock(cls, color: str = None) -> QIcon:
        # Keep custom layout
        return cls._create_icon(cls._SHIELD_LOCK_SVG, color)
        
    @classmethod
    def trash(cls, color: str = None) -> QIcon:
        return cls.get_icon("eliminar", color=color)

    @classmethod
    def edit(cls, color: str = None) -> QIcon:
        return cls.get_icon("editar", color=color)

    @classmethod
    def calendar(cls, color: str = None) -> QIcon:
        return cls.get_icon("calendario", color=color)

    @classmethod
    def refresh(cls, color: str = None) -> QIcon:
        return cls.get_icon("actualizar", color=color)

    @classmethod
    def dashboard(cls, color: str = None) -> QIcon:
        return cls.get_icon("dashboard", color=color)
        
    @classmethod
    def list_icon(cls, color: str = None) -> QIcon:
        return cls.get_icon("vista_lista", color=color)
        
    @classmethod
    def file_text(cls, color: str = None) -> QIcon:
        return cls.get_icon("detalles", color=color)
        
    @classmethod
    def database(cls, color: str = None) -> QIcon:
        return cls.get_icon("tabla", color=color)
        
    @classmethod
    def clock(cls, color: str = None) -> QIcon:
        return cls.get_icon("hora", color=color)
        
    @classmethod
    def shield_check(cls, color: str = None) -> QIcon:
        return cls.get_icon("validar", color=color)
        
    @classmethod
    def alert_triangle(cls, color: str = None) -> QIcon:
        return cls.get_icon("advertencia", color=color)
        
    @classmethod
    def power(cls, color: str = None) -> QIcon:
        return cls.get_icon("salir", color=color)
        
    @classmethod
    def search(cls, color: str = None) -> QIcon:
        return cls.get_icon("buscar", color=color)
        
    @classmethod
    def filter_icon(cls, color: str = None) -> QIcon:
        return cls.get_icon("filtrar", color=color)
        
    @classmethod
    def more_vertical(cls, color: str = None) -> QIcon:
        return cls.get_icon("mas_opciones", color=color)

    @classmethod
    def check(cls, color: str = None) -> QIcon:
        return cls.get_icon("exito", color=color)

    @classmethod
    def hollow_dot(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._HOLLOW_DOT_SVG, color)

    @classmethod
    def help_circle(cls, color: str = None) -> QIcon:
        return cls.get_icon("ayuda", color=color)

    @classmethod
    def chevron_down(cls, color: str = None) -> QIcon:
        return cls.get_icon("abajo", color=color)

    @classmethod
    def chevron_up(cls, color: str = None) -> QIcon:
        return cls.get_icon("arriba", color=color)

    @classmethod
    def dot(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._DOT_SVG, color)

    @classmethod
    def file_excel(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._EXCEL_SVG, color)

    @classmethod
    def file_pdf(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._PDF_SVG, color)


    # --- NEW CONVENIENCE CLASSMETHODS (Generated dynamically/statically for ease of use) ---
    # Acción Principal
    @classmethod
    def guardar_nuevo(cls, color: str = None) -> QIcon: return cls.get_icon("guardar_nuevo", color=color)
    @classmethod
    def cancelar(cls, color: str = None) -> QIcon: return cls.get_icon("cancelar", color=color)
    @classmethod
    def salir(cls, color: str = None) -> QIcon: return cls.get_icon("salir", color=color)
    @classmethod
    def volver(cls, color: str = None) -> QIcon: return cls.get_icon("volver", color=color)
    @classmethod
    def siguiente(cls, color: str = None) -> QIcon: return cls.get_icon("siguiente", color=color)
    @classmethod
    def aceptar(cls, color: str = None) -> QIcon: return cls.get_icon("aceptar", color=color)
    @classmethod
    def rechazar(cls, color: str = None) -> QIcon: return cls.get_icon("rechazar", color=color)
    @classmethod
    def cerrar(cls, color: str = None) -> QIcon: return cls.get_icon("cerrar", color=color)
    @classmethod
    def limpiar(cls, color: str = None) -> QIcon: return cls.get_icon("limpiar", color=color)
    @classmethod
    def actualizar(cls, color: str = None) -> QIcon: return cls.get_icon("actualizar", color=color)
    @classmethod
    def deshacer(cls, color: str = None) -> QIcon: return cls.get_icon("deshacer", color=color)
    @classmethod
    def rehacer(cls, color: str = None) -> QIcon: return cls.get_icon("rehacer", color=color)

    # Navegación
    @classmethod
    def inicio(cls, color: str = None) -> QIcon: return cls.get_icon("inicio", color=color)
    @classmethod
    def modulos(cls, color: str = None) -> QIcon: return cls.get_icon("modulos", color=color)
    @classmethod
    def menu(cls, color: str = None) -> QIcon: return cls.get_icon("menu", color=color)
    @classmethod
    def submenu(cls, color: str = None) -> QIcon: return cls.get_icon("submenu", color=color)
    @classmethod
    def arriba(cls, color: str = None) -> QIcon: return cls.get_icon("arriba", color=color)
    @classmethod
    def abajo(cls, color: str = None) -> QIcon: return cls.get_icon("abajo", color=color)
    @classmethod
    def izquierda(cls, color: str = None) -> QIcon: return cls.get_icon("izquierda", color=color)
    @classmethod
    def derecha(cls, color: str = None) -> QIcon: return cls.get_icon("derecha", color=color)
    @classmethod
    def ir_a(cls, color: str = None) -> QIcon: return cls.get_icon("ir_a", color=color)
    @classmethod
    def anterior(cls, color: str = None) -> QIcon: return cls.get_icon("anterior", color=color)
    @classmethod
    def siguiente_skip(cls, color: str = None) -> QIcon: return cls.get_icon("siguiente_skip", color=color)
    @classmethod
    def ultimo(cls, color: str = None) -> QIcon: return cls.get_icon("ultimo", color=color)
    @classmethod
    def expandir(cls, color: str = None) -> QIcon: return cls.get_icon("expandir", color=color)
    @classmethod
    def colapsar(cls, color: str = None) -> QIcon: return cls.get_icon("colapsar", color=color)

    # Búsqueda y Filtros
    @classmethod
    def buscar(cls, color: str = None) -> QIcon: return cls.get_icon("buscar", color=color)
    @classmethod
    def busqueda_avanzada(cls, color: str = None) -> QIcon: return cls.get_icon("busqueda_avanzada", color=color)
    @classmethod
    def filtrar(cls, color: str = None) -> QIcon: return cls.get_icon("filtrar", color=color)
    @classmethod
    def quitar_filtro(cls, color: str = None) -> QIcon: return cls.get_icon("quitar_filtro", color=color)
    @classmethod
    def ordenar_az(cls, color: str = None) -> QIcon: return cls.get_icon("ordenar_az", color=color)
    @classmethod
    def ordenar_za(cls, color: str = None) -> QIcon: return cls.get_icon("ordenar_za", color=color)
    @classmethod
    def columnas(cls, color: str = None) -> QIcon: return cls.get_icon("columnas", color=color)
    @classmethod
    def agrupar(cls, color: str = None) -> QIcon: return cls.get_icon("agrupar", color=color)
    @classmethod
    def desagrupar(cls, color: str = None) -> QIcon: return cls.get_icon("desagrupar", color=color)
    @classmethod
    def vista_lista(cls, color: str = None) -> QIcon: return cls.get_icon("vista_lista", color=color)
    @classmethod
    def vista_cuadricula(cls, color: str = None) -> QIcon: return cls.get_icon("vista_cuadricula", color=color)
    @classmethod
    def vista_tarjetas(cls, color: str = None) -> QIcon: return cls.get_icon("vista_tarjetas", color=color)
    @classmethod
    def exportar(cls, color: str = None) -> QIcon: return cls.get_icon("exportar", color=color)
    @classmethod
    def importar(cls, color: str = None) -> QIcon: return cls.get_icon("importar", color=color)

    # Visualización
    @classmethod
    def visualizar(cls, color: str = None) -> QIcon: return cls.get_icon("visualizar", color=color)
    @classmethod
    def detalles(cls, color: str = None) -> QIcon: return cls.get_icon("detalles", color=color)
    @classmethod
    def informacion(cls, color: str = None) -> QIcon: return cls.get_icon("informacion", color=color)
    @classmethod
    def vista_previa(cls, color: str = None) -> QIcon: return cls.get_icon("vista_previa", color=color)
    @classmethod
    def pantalla_completa(cls, color: str = None) -> QIcon: return cls.get_icon("pantalla_completa", color=color)
    @classmethod
    def zoom_in(cls, color: str = None) -> QIcon: return cls.get_icon("zoom_in", color=color)
    @classmethod
    def zoom_out(cls, color: str = None) -> QIcon: return cls.get_icon("zoom_out", color=color)
    @classmethod
    def acercar(cls, color: str = None) -> QIcon: return cls.get_icon("acercar", color=color)
    @classmethod
    def alejar(cls, color: str = None) -> QIcon: return cls.get_icon("alejar", color=color)
    @classmethod
    def ajustar(cls, color: str = None) -> QIcon: return cls.get_icon("ajustar", color=color)
    @classmethod
    def ocultar(cls, color: str = None) -> QIcon: return cls.get_icon("ocultar", color=color)
    @classmethod
    def mostrar(cls, color: str = None) -> QIcon: return cls.get_icon("mostrar", color=color)
    @classmethod
    def reordenar(cls, color: str = None) -> QIcon: return cls.get_icon("reordenar", color=color)
    @classmethod
    def mas_opciones(cls, color: str = None) -> QIcon: return cls.get_icon("mas_opciones", color=color)

    # Documentos
    @classmethod
    def documento_nuevo(cls, color: str = None) -> QIcon: return cls.get_icon("documento_nuevo", color=color)
    @classmethod
    def documento_abrir(cls, color: str = None) -> QIcon: return cls.get_icon("documento_abrir", color=color)
    @classmethod
    def documento_guardar(cls, color: str = None) -> QIcon: return cls.get_icon("documento_guardar", color=color)
    @classmethod
    def documento_guardar_como(cls, color: str = None) -> QIcon: return cls.get_icon("documento_guardar_como", color=color)
    @classmethod
    def documento_duplicar(cls, color: str = None) -> QIcon: return cls.get_icon("documento_duplicar", color=color)
    @classmethod
    def documento_eliminar(cls, color: str = None) -> QIcon: return cls.get_icon("documento_eliminar", color=color)
    @classmethod
    def documento_imprimir(cls, color: str = None) -> QIcon: return cls.get_icon("documento_imprimir", color=color)
    @classmethod
    def documento_vista_previa(cls, color: str = None) -> QIcon: return cls.get_icon("documento_vista_previa", color=color)
    @classmethod
    def documento_descargar(cls, color: str = None) -> QIcon: return cls.get_icon("documento_descargar", color=color)
    @classmethod
    def documento_cargar(cls, color: str = None) -> QIcon: return cls.get_icon("documento_cargar", color=color)
    @classmethod
    def documento_adjuntar(cls, color: str = None) -> QIcon: return cls.get_icon("documento_adjuntar", color=color)
    @classmethod
    def documento_desadjuntar(cls, color: str = None) -> QIcon: return cls.get_icon("documento_desadjuntar", color=color)
    @classmethod
    def documento_plantilla(cls, color: str = None) -> QIcon: return cls.get_icon("documento_plantilla", color=color)
    @classmethod
    def documento_historial(cls, color: str = None) -> QIcon: return cls.get_icon("documento_historial", color=color)
    @classmethod
    def documento_versiones(cls, color: str = None) -> QIcon: return cls.get_icon("documento_versiones", color=color)

    # Datos y Tablas
    @classmethod
    def nuevo_registro(cls, color: str = None) -> QIcon: return cls.get_icon("nuevo_registro", color=color)
    @classmethod
    def editar_registro(cls, color: str = None) -> QIcon: return cls.get_icon("editar_registro", color=color)
    @classmethod
    def eliminar_registro(cls, color: str = None) -> QIcon: return cls.get_icon("eliminar_registro", color=color)
    @classmethod
    def duplicar_registro(cls, color: str = None) -> QIcon: return cls.get_icon("duplicar_registro", color=color)
    @classmethod
    def exportar_datos(cls, color: str = None) -> QIcon: return cls.get_icon("exportar_datos", color=color)
    @classmethod
    def importar_datos(cls, color: str = None) -> QIcon: return cls.get_icon("importar_datos", color=color)
    @classmethod
    def resumen(cls, color: str = None) -> QIcon: return cls.get_icon("resumen", color=color)
    @classmethod
    def grafico(cls, color: str = None) -> QIcon: return cls.get_icon("grafico", color=color)
    @classmethod
    def tabla(cls, color: str = None) -> QIcon: return cls.get_icon("tabla", color=color)
    @classmethod
    def campos(cls, color: str = None) -> QIcon: return cls.get_icon("campos", color=color)
    @classmethod
    def configuracion_tabla(cls, color: str = None) -> QIcon: return cls.get_icon("configuracion_tabla", color=color)
    @classmethod
    def validar(cls, color: str = None) -> QIcon: return cls.get_icon("validar", color=color)
    @classmethod
    def advertencia(cls, color: str = None) -> QIcon: return cls.get_icon("advertencia", color=color)
    @classmethod
    def error(cls, color: str = None) -> QIcon: return cls.get_icon("error", color=color)
    @classmethod
    def exito(cls, color: str = None) -> QIcon: return cls.get_icon("exito", color=color)

    # Usuarios y Seguridad
    @classmethod
    def usuario(cls, color: str = None) -> QIcon: return cls.get_icon("usuario", color=color)
    @classmethod
    def usuarios(cls, color: str = None) -> QIcon: return cls.get_icon("usuarios", color=color)
    @classmethod
    def grupo(cls, color: str = None) -> QIcon: return cls.get_icon("grupo", color=color)
    @classmethod
    def roles(cls, color: str = None) -> QIcon: return cls.get_icon("roles", color=color)
    @classmethod
    def permisos(cls, color: str = None) -> QIcon: return cls.get_icon("permisos", color=color)
    @classmethod
    def bloquear(cls, color: str = None) -> QIcon: return cls.get_icon("bloquear", color=color)
    @classmethod
    def desbloquear(cls, color: str = None) -> QIcon: return cls.get_icon("desbloquear", color=color)
    @classmethod
    def cambiar_contrasenia(cls, color: str = None) -> QIcon: return cls.get_icon("cambiar_contrasenia", color=color)
    @classmethod
    def perfil(cls, color: str = None) -> QIcon: return cls.get_icon("perfil", color=color)
    @classmethod
    def sesion(cls, color: str = None) -> QIcon: return cls.get_icon("sesion", color=color)
    @classmethod
    def actividad(cls, color: str = None) -> QIcon: return cls.get_icon("actividad", color=color)
    @classmethod
    def auditoria(cls, color: str = None) -> QIcon: return cls.get_icon("auditoria", color=color)
    @classmethod
    def seguridad(cls, color: str = None) -> QIcon: return cls.get_icon("seguridad", color=color)
    @classmethod
    def notificacion(cls, color: str = None) -> QIcon: return cls.get_icon("notificacion", color=color)
    @classmethod
    def mensajes(cls, color: str = None) -> QIcon: return cls.get_icon("mensajes", color=color)

    # Configuración
    @classmethod
    def configuracion(cls, color: str = None) -> QIcon: return cls.get_icon("configuracion", color=color)
    @classmethod
    def preferencias(cls, color: str = None) -> QIcon: return cls.get_icon("preferencias", color=color)
    @classmethod
    def parametros(cls, color: str = None) -> QIcon: return cls.get_icon("parametros", color=color)
    @classmethod
    def opciones(cls, color: str = None) -> QIcon: return cls.get_icon("opciones", color=color)
    @classmethod
    def idioma(cls, color: str = None) -> QIcon: return cls.get_icon("idioma", color=color)
    @classmethod
    def tema(cls, color: str = None) -> QIcon: return cls.get_icon("tema", color=color)
    @classmethod
    def notificaciones_config(cls, color: str = None) -> QIcon: return cls.get_icon("notificaciones_config", color=color)
    @classmethod
    def integraciones(cls, color: str = None) -> QIcon: return cls.get_icon("integraciones", color=color)
    @classmethod
    def api(cls, color: str = None) -> QIcon: return cls.get_icon("api", color=color)
    @classmethod
    def webhooks(cls, color: str = None) -> QIcon: return cls.get_icon("webhooks", color=color)
    @classmethod
    def sincronizar(cls, color: str = None) -> QIcon: return cls.get_icon("sincronizar", color=color)
    @classmethod
    def respaldar(cls, color: str = None) -> QIcon: return cls.get_icon("respaldar", color=color)
    @classmethod
    def restaurar(cls, color: str = None) -> QIcon: return cls.get_icon("restaurar", color=color)
    @classmethod
    def mantenimiento(cls, color: str = None) -> QIcon: return cls.get_icon("mantenimiento", color=color)
    @classmethod
    def soporte(cls, color: str = None) -> QIcon: return cls.get_icon("soporte", color=color)

    # Comunicación
    @classmethod
    def correo(cls, color: str = None) -> QIcon: return cls.get_icon("correo", color=color)
    @classmethod
    def enviar(cls, color: str = None) -> QIcon: return cls.get_icon("enviar", color=color)
    @classmethod
    def responder(cls, color: str = None) -> QIcon: return cls.get_icon("responder", color=color)
    @classmethod
    def responder_todos(cls, color: str = None) -> QIcon: return cls.get_icon("responder_todos", color=color)
    @classmethod
    def reenviar(cls, color: str = None) -> QIcon: return cls.get_icon("reenviar", color=color)
    @classmethod
    def marcar_leido(cls, color: str = None) -> QIcon: return cls.get_icon("marcar_leido", color=color)
    @classmethod
    def marcar_no_leido(cls, color: str = None) -> QIcon: return cls.get_icon("marcar_no_leido", color=color)
    @classmethod
    def importante(cls, color: str = None) -> QIcon: return cls.get_icon("importante", color=color)
    @classmethod
    def favorito(cls, color: str = None) -> QIcon: return cls.get_icon("favorito", color=color)
    @classmethod
    def comentario(cls, color: str = None) -> QIcon: return cls.get_icon("comentario", color=color)
    @classmethod
    def chat(cls, color: str = None) -> QIcon: return cls.get_icon("chat", color=color)
    @classmethod
    def llamada(cls, color: str = None) -> QIcon: return cls.get_icon("llamada", color=color)
    @classmethod
    def videollamada(cls, color: str = None) -> QIcon: return cls.get_icon("videollamada", color=color)
    @classmethod
    def anuncio(cls, color: str = None) -> QIcon: return cls.get_icon("anuncio", color=color)
    @classmethod
    def rss(cls, color: str = None) -> QIcon: return cls.get_icon("rss", color=color)

    # Interfaz y Otros
    @classmethod
    def switch_toggle(cls, color: str = None) -> QIcon: return cls.get_icon("switch_toggle", color=color)
    @classmethod
    def checkbox(cls, color: str = None) -> QIcon: return cls.get_icon("checkbox", color=color)
    @classmethod
    def radio_button(cls, color: str = None) -> QIcon: return cls.get_icon("radio_button", color=color)
    @classmethod
    def calendario(cls, color: str = None) -> QIcon: return cls.get_icon("calendario", color=color)
    @classmethod
    def fecha(cls, color: str = None) -> QIcon: return cls.get_icon("fecha", color=color)
    @classmethod
    def hora(cls, color: str = None) -> QIcon: return cls.get_icon("hora", color=color)
    @classmethod
    def etiqueta(cls, color: str = None) -> QIcon: return cls.get_icon("etiqueta", color=color)
    @classmethod
    def archivo(cls, color: str = None) -> QIcon: return cls.get_icon("archivo", color=color)
    @classmethod
    def carpeta(cls, color: str = None) -> QIcon: return cls.get_icon("carpeta", color=color)
    @classmethod
    def enlace(cls, color: str = None) -> QIcon: return cls.get_icon("enlace", color=color)
    @classmethod
    def copiar(cls, color: str = None) -> QIcon: return cls.get_icon("copiar", color=color)
    @classmethod
    def cortar(cls, color: str = None) -> QIcon: return cls.get_icon("cortar", color=color)
    @classmethod
    def pegar(cls, color: str = None) -> QIcon: return cls.get_icon("pegar", color=color)
    @classmethod
    def arrastrar(cls, color: str = None) -> QIcon: return cls.get_icon("arrastrar", color=color)
    @classmethod
    def ayuda(cls, color: str = None) -> QIcon: return cls.get_icon("ayuda", color=color)
