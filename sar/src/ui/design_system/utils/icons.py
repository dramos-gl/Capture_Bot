"""SVG Icon generator for Design System."""

import base64
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QByteArray

class Icons:
    """Provides standard QIcons rendered from SVG paths."""

    _USER_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>'''
    _LOCK_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>'''
    _EYE_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>'''
    _EYE_OFF_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>'''
    _SAVE_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>'''
    _X_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>'''
    _MINIMIZE_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line></svg>'''
    _SHIELD_LOCK_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#2C3E50" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><rect x="9" y="11" width="6" height="4" rx="1"></rect><path d="M10 11V9a2 2 0 1 1 4 0v2"></path></svg>'''
    _TRASH_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>'''
    _EDIT_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>'''
    _CALENDAR_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>'''
    _REFRESH_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>'''
    _DASHBOARD_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>'''
    _LIST_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>'''
    _FILE_TEXT_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>'''
    _DATABASE_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path><path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"></path></svg>'''
    _CLOCK_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>'''
    _SHIELD_CHECK_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><polyline points="9 11 11 13 15 9"></polyline></svg>'''
    _ALERT_TRIANGLE_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'''
    _POWER_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18.36 6.64a9 9 0 1 1-12.73 0"></path><line x1="12" y1="2" x2="12" y2="12"></line></svg>'''
    _SEARCH_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>'''
    _FILTER_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polyline></svg>'''
    _MORE_VERTICAL_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"></circle><circle cx="12" cy="5" r="1"></circle><circle cx="12" cy="19" r="1"></circle></svg>'''
    _CHECK_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>'''

    @classmethod
    def _create_icon(cls, svg_string: str, color: str = None) -> QIcon:
        # If color is requested, replace "currentColor" with the specific hex code
        if color:
            svg_string = svg_string.replace('currentColor', color)
        pixmap = QPixmap()
        pixmap.loadFromData(QByteArray(svg_string.encode('utf-8')), "SVG")
        return QIcon(pixmap)

    @classmethod
    def user(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._USER_SVG, color)

    @classmethod
    def lock(cls) -> QIcon:
        return cls._create_icon(cls._LOCK_SVG)

    @classmethod
    def eye(cls) -> QIcon:
        return cls._create_icon(cls._EYE_SVG)
        
    @classmethod
    def eye_off(cls) -> QIcon:
        return cls._create_icon(cls._EYE_OFF_SVG)

    @classmethod
    def save(cls) -> QIcon:
        return cls._create_icon(cls._SAVE_SVG)

    @classmethod
    def close(cls) -> QIcon:
        return cls._create_icon(cls._X_SVG)

    @classmethod
    def minimize(cls) -> QIcon:
        return cls._create_icon(cls._MINIMIZE_SVG)

    @classmethod
    def shield_lock(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._SHIELD_LOCK_SVG, color)
        
    @classmethod
    def trash(cls) -> QIcon:
        return cls._create_icon(cls._TRASH_SVG)

    @classmethod
    def edit(cls) -> QIcon:
        return cls._create_icon(cls._EDIT_SVG)

    @classmethod
    def calendar(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._CALENDAR_SVG, color)

    @classmethod
    def refresh(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._REFRESH_SVG, color)

    @classmethod
    def dashboard(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._DASHBOARD_SVG, color)
        
    @classmethod
    def list_icon(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._LIST_SVG, color)
        
    @classmethod
    def file_text(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._FILE_TEXT_SVG, color)
        
    @classmethod
    def database(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._DATABASE_SVG, color)
        
    @classmethod
    def clock(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._CLOCK_SVG, color)
        
    @classmethod
    def shield_check(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._SHIELD_CHECK_SVG, color)
        
    @classmethod
    def alert_triangle(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._ALERT_TRIANGLE_SVG, color)
        
    @classmethod
    def power(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._POWER_SVG, color)
        
    @classmethod
    def search(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._SEARCH_SVG, color)
        
    @classmethod
    def filter_icon(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._FILTER_SVG, color)
        
    @classmethod
    def more_vertical(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._MORE_VERTICAL_SVG, color)
        
    _CHEVRON_DOWN_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>'''
    _CHEVRON_UP_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>'''
    _DOT_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="5" fill="currentColor"/></svg>'''

    _HELP_CIRCLE_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'''

    _HOLLOW_DOT_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/></svg>'''

    @classmethod
    def check(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._CHECK_SVG, color)

    @classmethod
    def hollow_dot(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._HOLLOW_DOT_SVG, color)

    @classmethod
    def help_circle(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._HELP_CIRCLE_SVG, color)

    @classmethod
    def chevron_down(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._CHEVRON_DOWN_SVG, color)

    @classmethod
    def chevron_up(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._CHEVRON_UP_SVG, color)

    @classmethod
    def dot(cls, color: str = None) -> QIcon:
        return cls._create_icon(cls._DOT_SVG, color)
