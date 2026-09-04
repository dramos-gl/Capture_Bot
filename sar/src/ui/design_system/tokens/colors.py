"""Color design tokens for UI components."""

class Colors:
    # --- Primary Brand Colors ---
    PRIMARY = "#2C3E50"        # Dark Navy / Charcoal (from image border)
    PRIMARY_HOVER = "#1A252F"  # Darker Navy
    PRIMARY_LIGHT = "#34495E"  # Lighter Navy
    
    # --- Secondary brand / UI Colors ---
    ACCENT = "#2563EB"         # Blue Accent (Revisión manual)
    ACCENT_HOVER = "#1D4ED8"
    
    # --- Dark Theme Backgrounds & Surfaces ---
    BG_DARK = "#0F172A"        # Deep Slate (900)
    SURFACE_DARK = "#1E293B"   # Slate Blue (800)
    BORDER_DARK = "#334155"    # Slate Gray (700)
    
    # --- Light Theme Backgrounds & Surfaces ---
    BG_LIGHT = "#E8EEF5"       # Light soft blue (from image)
    SURFACE_LIGHT = "#FFFFFF"  # Pure White
    BORDER_LIGHT = "#A9A9A9"   # Darker gray for flat borders
    
    # --- Text Colors (Dark Theme) ---
    TEXT_DARK_PRIMARY = "#F8FAFC"
    TEXT_DARK_SECONDARY = "#94A3B8"
    TEXT_DARK_MUTED = "#64748B"
    
    # --- Text Colors (Light Theme) ---
    TEXT_LIGHT_PRIMARY = "#1E293B"
    TEXT_LIGHT_SECONDARY = "#475569"
    TEXT_LIGHT_MUTED = "#64748B"
    
    # --- Status / Feedback Colors ---
    SUCCESS = "#16A34A"
    WARNING = "#D97706"
    ERROR = "#EF4444"
    INFO = "#3B82F6"
    ASSIGNED = "#6366F1"
    RESERVED = "#0D9488"
    
    # --- Status Background Colors (Light Theme Badges) ---
    SUCCESS_BG = "#DCFCE7"
    WARNING_BG = "#FEF3C7"
    ERROR_BG = "#FEE2E2"
    ACCENT_BG = "#DBEAFE"
    NEUTRAL_BG = "#F1F5F9"
    ASSIGNED_BG = "#EEF2FF"
    RESERVED_BG = "#CCFBF1"

    # --- Status Colors (Dark Theme Badges) ---
    SUCCESS_DARK_BG = "rgba(22, 163, 74, 0.20)"
    SUCCESS_DARK_TEXT = "#4ADE80"
    WARNING_DARK_BG = "rgba(217, 119, 6, 0.22)"
    WARNING_DARK_TEXT = "#FBBF24"
    ERROR_DARK_BG = "rgba(239, 68, 68, 0.20)"
    ERROR_DARK_TEXT = "#F87171"
    ACCENT_DARK_BG = "rgba(37, 99, 235, 0.22)"
    ACCENT_DARK_TEXT = "#60A5FA"
    NEUTRAL_DARK_BG = "rgba(100, 116, 139, 0.20)"
    NEUTRAL_DARK_TEXT = "#94A3B8"
    ASSIGNED_DARK_BG = "rgba(99, 102, 241, 0.22)"
    ASSIGNED_DARK_TEXT = "#818CF8"
    RESERVED_DARK_BG = "rgba(13, 148, 136, 0.22)"
    RESERVED_DARK_TEXT = "#2DD4BF"

    # --- Modern Neutrals (Slate from Flet System) ---
    SLATE_50        = "#F8FAFC"
    SLATE_100       = "#F1F5F9"
    SLATE_200       = "#E2E8F0"
    SLATE_500       = "#64748B"
    SLATE_900       = "#0F172A"

    # --- Flet Semantic Colors ---
    GREEN_400       = "#66BB6A"
    RED_400         = "#EF5350"
    AMBER_600       = "#FFB300"
    BLUE_400        = "#42A5F5"

    # --- Module Accent Colors (Vivid Series from Flet) ---
    ACCENT_CYAN     = "#06B6D4"
    ACCENT_PINK     = "#D946EF"
    ACCENT_VIOLET   = "#8B5CF6"
    ACCENT_ROSE     = "#F43F5E"
    ACCENT_EMERALD  = "#10B981"
    ACCENT_AMBER    = "#F59E0B"
    ACCENT_BLUE     = "#3B82F6"
    ACCENT_INDIGO   = "#6366F1"
    ACCENT_RED      = "#EF4444"
    ACCENT_TEAL     = "#2DD4BF"
    ACCENT_BLUE_DEEP = "#1D4ED8"

    # --- Analytics & Vivid Chart Palette (Inspirada en dashboards modernos) ---
    CHART_EMERALD_DARK = "#2E7D32"  # Verde esmeralda profundo / boscoso (Generadas / Completadas)
    CHART_AMBER        = "#F59E0B"  # Ámbar cálido / Mostaza brillante (Pendiente / Low)
    CHART_PURPLE       = "#9333EA"  # Púrpura vivo / Violeta (Medium / Asignadas)
    CHART_CORAL        = "#F43F5E"  # Coral / Rojo vivo (Rechazadas / Critical)
    CHART_BLUE         = "#0284C7"  # Azul cian / Océano (General / High)
    CHART_INDIGO       = "#6366F1"  # Índigo brillante
    CHART_TEAL         = "#14B8A6"  # Verde azulado vibrante
    CHART_SLATE        = "#64748B"  # Slate neutro

    CHART_VIVID_PALETTE = [
        CHART_EMERALD_DARK,
        CHART_AMBER,
        CHART_PURPLE,
        CHART_CORAL,
        CHART_BLUE,
        CHART_INDIGO,
        CHART_TEAL,
        CHART_SLATE
    ]
