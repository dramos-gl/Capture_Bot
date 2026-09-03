import os
from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.tokens.typography import Typography
from sar.src.ui.design_system.tokens.spacing import Spacing

class ThemeManager:
    """Manages global application theme state and QSS loading."""
    _is_dark: bool = False

    @classmethod
    def is_dark_active(cls) -> bool:
        """Returns whether the active application theme is dark."""
        return cls._is_dark

    @staticmethod
    def get_qss(is_dark: bool = False) -> str:
        """Generates dynamic QSS by interpolating tokens."""
        # Theme specific colors
        bg = Colors.BG_DARK if is_dark else Colors.BG_LIGHT
        surf = Colors.SURFACE_DARK if is_dark else Colors.SURFACE_LIGHT
        border = Colors.BORDER_DARK if is_dark else Colors.BORDER_LIGHT
        
        txt_primary = Colors.TEXT_DARK_PRIMARY if is_dark else Colors.TEXT_LIGHT_PRIMARY
        txt_secondary = Colors.TEXT_DARK_SECONDARY if is_dark else Colors.TEXT_LIGHT_SECONDARY
        txt_muted = Colors.TEXT_DARK_MUTED if is_dark else Colors.TEXT_LIGHT_MUTED

        # Resolve asset paths for QSS
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icons_dir = os.path.abspath(os.path.join(base_dir, "..", "assets", "icons"))
        check_path = os.path.join(icons_dir, "check.svg").replace("\\", "/")
        chevron_down_path = os.path.join(icons_dir, "chevron_down_dark.svg" if is_dark else "chevron_down.svg").replace("\\", "/")
        chevron_up_path = os.path.join(icons_dir, "chevron_up_dark.svg" if is_dark else "chevron_up.svg").replace("\\", "/")
        calendar_path = os.path.join(icons_dir, "calendar.svg").replace("\\", "/")

        qss = f"""
        /* Global Defaults */
        QWidget {{
            background-color: {bg};
            color: {txt_primary};
            font-family: {Typography.FONT_FAMILY};
            font-size: {Typography.SIZE_MD};
        }}
        
        /* Premium Card / Container */
        QFrame#cardFrame {{
            background-color: {surf};
            border: {Spacing.BORDER_WIDTH_SM} solid {border};
            border-radius: {Spacing.RADIUS_LG};
        }}
        
        /* Sidebar Styling */
        QFrame#sidebarFrame {{
            background-color: {surf};
            border-right: {Spacing.BORDER_WIDTH_SM} solid {border};
        }}
        
        /* Floating Label Container */
        QFrame#floatingInputFrame {{
            background-color: {surf};
            border: {Spacing.BORDER_WIDTH_SM} solid {border};
            border-radius: {Spacing.RADIUS_MD};
        }}
        
        /* Inner LineEdit for Floating Label */
        QLineEdit#floatingInput {{
            background-color: transparent;
            border: none;
            padding: 0px 4px;
            color: {txt_primary};
        }}
        QLineEdit#floatingInput:focus {{
            border: none;
        }}
        
        /* Dialog Container */
        QWidget#dialogMainFrame {{
            background-color: {surf};
            border: 1px solid {border};
            border-radius: {Spacing.RADIUS_MD};
        }}
        QWidget#dialogHeader {{
            background-color: {Colors.PRIMARY};
            border-top-left-radius: {Spacing.RADIUS_MD};
            border-top-right-radius: {Spacing.RADIUS_MD};
        }}
        QWidget#dialogFooter {{
            background-color: {bg};
            border-bottom-left-radius: {Spacing.RADIUS_MD};
            border-bottom-right-radius: {Spacing.RADIUS_MD};
            border-top: 1px solid {border};
        }}
        QPushButton#dialogHeaderBtn {{
            background-color: transparent;
            border: none;
            color: white;
        }}
        QPushButton#dialogHeaderBtn:hover {{
            background-color: {Colors.PRIMARY_HOVER};
            border-radius: 4px;
        }}
        
        /* Atoms: Inputs */
        QLineEdit {{
            background-color: {surf};
            border: 1px solid {border};
            border-radius: {Spacing.RADIUS_MD};
            padding: 3px 8px;
            min-height: 28px;
            max-height: 28px;
            color: {txt_primary};
            font-size: 13px;
        }}
        QLineEdit:focus {{
            border: 1.5px solid {Colors.ACCENT};
        }}
        
        /* ComboBoxes */
        QComboBox {{
            background-color: {surf};
            border: 1px solid {border};
            border-radius: {Spacing.RADIUS_MD};
            padding: 3px 10px;
            min-height: 28px;
            max-height: 28px;
            color: {txt_primary};
            font-size: 13px;
        }}
        QComboBox:focus, QComboBox:on {{
            border: 1.5px solid {Colors.ACCENT};
        }}
        QComboBox::drop-down {{
            border: none;
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 30px;
        }}
        QComboBox::down-arrow {{
            image: url({chevron_down_path});
            width: 16px;
            height: 16px;
            margin-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid {border};
            border-radius: 6px;
            background-color: {surf};
            alternate-background-color: {surf};
            color: {txt_primary};
            selection-background-color: {Colors.ACCENT_BG if not is_dark else Colors.ACCENT_DARK_BG};
            selection-color: {Colors.TEXT_LIGHT_PRIMARY if not is_dark else Colors.TEXT_DARK_PRIMARY};
            padding: 4px;
            outline: 0px;
        }}
        QComboBox QAbstractItemView::viewport {{
            background-color: {surf};
        }}
        QComboBox QAbstractItemView::item {{
            min-height: 28px;
            padding: 4px 8px;
            border-radius: 4px;
            background-color: {surf};
            color: {txt_primary};
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {Colors.ACCENT_BG if not is_dark else Colors.ACCENT_DARK_BG};
            color: {Colors.TEXT_LIGHT_PRIMARY if not is_dark else Colors.TEXT_DARK_PRIMARY};
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {Colors.NEUTRAL_BG if not is_dark else Colors.NEUTRAL_DARK_BG};
            color: {txt_primary};
        }}

        /* Labeled Groupbox Molecule (Fieldset style for Combos & Dates) */
        QGroupBox#labeledGroup {{
            background-color: {surf};
            border: 1px solid {border};
            border-radius: 8px;
            margin-top: 8px;
            font-weight: bold;
            color: {"#2563EB" if not is_dark else "#60A5FA"};
            font-size: 11px;
        }}
        QGroupBox#labeledGroup::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 8px;
            padding: 0 4px;
            background-color: transparent;
        }}
        QGroupBox#labeledGroup QComboBox {{
            border: none;
            background-color: transparent;
            min-width: 130px;
            height: 35px;
            min-height: 35px;
            max-height: 35px;
            padding: 2px 10px;
            font-size: 13px;
        }}
        QGroupBox#labeledGroup QDateEdit {{
            border: none;
            background-color: transparent;
            min-width: 120px;
            height: 35px;
            min-height: 35px;
            max-height: 35px;
            padding: 2px 6px 2px 10px;
            font-size: 13px;
            color: {txt_primary};
        }}

        /* Date Editors */
        QDateEdit {{
            background-color: {surf};
            border: 1px solid {border};
            border-radius: {Spacing.RADIUS_MD};
            padding: 3px 10px;
            min-height: 28px;
            max-height: 28px;
            color: {txt_primary};
            font-size: 13px;
        }}
        QDateEdit:focus {{
            border: 1.5px solid {Colors.ACCENT};
        }}
        QDateEdit::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 28px;
            border: none;
        }}
        QDateEdit::down-arrow {{
            image: url({calendar_path});
            width: 16px;
            height: 16px;
            margin-right: 8px;
        }}
        
        /* Calendar Widget */
        QCalendarWidget {{
            background-color: {surf};
            color: {txt_primary};
        }}
        QCalendarWidget QWidget#qt_datetimedit_calendar {{
            background-color: {surf};
        }}
        QCalendarWidget QAbstractItemView:enabled {{
            background-color: {surf};
            color: {txt_primary};
            selection-background-color: {Colors.ACCENT};
            selection-color: #FFFFFF;
            alternate-background-color: {bg};
            outline: 0px;
        }}
        QCalendarWidget QToolButton {{
            color: {txt_primary};
            background-color: {surf};
            font-weight: bold;
            border-radius: 4px;
            padding: 4px;
        }}
        QCalendarWidget QToolButton:hover {{
            background-color: {border};
        }}
        QCalendarWidget QMenu {{
            background-color: {surf};
            color: {txt_primary};
            border: 1px solid {border};
        }}
        QCalendarWidget QSpinBox {{
            background-color: {surf};
            color: {txt_primary};
            border: 1px solid {border};
        }}
        QCalendarWidget QWidget#qt_calendar_navigationbar {{
            background-color: {surf};
            border-bottom: 1px solid {border};
        }}

        /* SpinBoxes */
        QSpinBox, QDoubleSpinBox {{
            background-color: {surf};
            border: 1px solid {border};
            border-radius: {Spacing.RADIUS_MD};
            padding: 3px 26px 3px 10px;
            min-height: 28px;
            max-height: 28px;
            color: {txt_primary};
            font-size: 13px;
        }}
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 1.5px solid {Colors.ACCENT};
        }}
        QSpinBox::up-button, QDoubleSpinBox::up-button {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 22px;
            border-left: 1px solid {border};
            border-bottom: 0.5px solid {border};
            background-color: transparent;
            margin: 1px 1px 0px 0px;
        }}
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
            background-color: {"rgba(255, 255, 255, 0.08)" if is_dark else "#F1F5F9"};
        }}
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
            image: url("{chevron_up_path}");
            width: 10px;
            height: 10px;
        }}
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            subcontrol-origin: padding;
            subcontrol-position: bottom right;
            width: 22px;
            border-left: 1px solid {border};
            border-top: 0.5px solid {border};
            background-color: transparent;
            margin: 0px 1px 1px 0px;
        }}
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
            background-color: {"rgba(255, 255, 255, 0.08)" if is_dark else "#F1F5F9"};
        }}
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
            image: url("{chevron_down_path}");
            width: 10px;
            height: 10px;
        }}
        
        /* Buttons */
        QPushButton {{
            background-color: #E6E6E6;
            color: #000000;
            font-weight: {Typography.WEIGHT_BOLD};
            border: 1px solid {Colors.PRIMARY};
            border-radius: {Spacing.RADIUS_MD};
            padding: 8px 16px;
            outline: 0;
        }}
        QPushButton:hover {{
            background-color: #D4D4D4;
        }}
        QPushButton:pressed {{
            background-color: #C0C0C0;
        }}
        QPushButton:disabled {{
            background-color: {surf};
            border: 1px solid {border};
            color: {txt_muted};
        }}
        
        /* Primary Action Buttons */
        QPushButton#primaryBtn {{
            background-color: {Colors.ACCENT};
            color: #FFFFFF;
            border: none;
        }}
        QPushButton#primaryBtn:hover {{
            background-color: {Colors.ACCENT_HOVER};
        }}
        
        /* Danger Action Buttons */
        QPushButton#dangerBtn {{
            background-color: {Colors.ERROR};
            color: #FFFFFF;
            border: none;
        }}
        QPushButton#dangerBtn:hover {{
            background-color: #DC2626;
        }}
        
        /* Secondary Action Buttons */
        QPushButton#secondaryBtn {{
            background-color: transparent;
            color: {txt_secondary};
            border: {Spacing.BORDER_WIDTH_SM} solid {border};
        }}
        QPushButton#secondaryBtn:hover {{
            background-color: {surf};
            border-color: {Colors.PRIMARY};
            color: {txt_primary};
        }}
        
        /* Styled Headers */
        QLabel {{
            background-color: transparent;
        }}
        
        QLabel#headerLabel {{
            font-size: {Typography.SIZE_XL};
            font-weight: {Typography.WEIGHT_BOLD};
            color: {txt_primary};
        }}
        
        QLabel#subheaderLabel {{
            font-size: {Typography.SIZE_LG};
            font-weight: {Typography.WEIGHT_SEMI_BOLD};
            color: {txt_secondary};
        }}
        
        QLabel#mutedLabel {{
            font-size: {Typography.SIZE_SM};
            color: {txt_muted};
        }}
        
        /* Configuración de la Orden / Header Labels */
        QLabel#orderViewTitle {{
            font-size: {Typography.SIZE_XL};
            font-weight: {Typography.WEIGHT_BOLD};
            color: {txt_primary};
        }}
        
        QLabel#cardHeaderTitle {{
            font-weight: {Typography.WEIGHT_BOLD};
            color: {Colors.ACCENT};
            font-size: {Typography.SIZE_LG};
        }}
        
        QLabel#cardHeaderSubtitle {{
            color: {txt_muted};
            font-size: {Typography.SIZE_SM};
        }}
        
        /* Total General Frame & Labels */
        QFrame#totalGeneralFrame {{
            border: 1px solid {border};
            border-radius: {Spacing.RADIUS_MD};
            padding: 6px 16px;
            background-color: {surf};
        }}
        
        QLabel#totalGeneralTitle {{
            font-weight: {Typography.WEIGHT_BOLD};
            font-size: {Typography.SIZE_MD};
            color: {txt_primary};
        }}
        
        QLabel#totalGeneralValue {{
            font-size: {Typography.SIZE_XL};
            font-weight: {Typography.WEIGHT_BOLD};
            color: {Colors.ACCENT};
        }}
        
        /* Status Badges */
        QFrame#statusBadge, QFrame[badge_variant] {{
            border-radius: 10px;
            border: none;
        }}
        QFrame[badge_variant="success"] {{
            background-color: {Colors.SUCCESS_DARK_BG if is_dark else Colors.SUCCESS_BG};
        }}
        QFrame[badge_variant="success"] QLabel {{
            color: {Colors.SUCCESS_DARK_TEXT if is_dark else Colors.SUCCESS};
            font-weight: bold;
            font-size: 10px;
            background: transparent;
            border: none;
        }}
        QFrame[badge_variant="accent"] {{
            background-color: {Colors.ACCENT_DARK_BG if is_dark else Colors.ACCENT_BG};
        }}
        QFrame[badge_variant="accent"] QLabel {{
            color: {Colors.ACCENT_DARK_TEXT if is_dark else Colors.ACCENT};
            font-weight: bold;
            font-size: 10px;
            background: transparent;
            border: none;
        }}
        QFrame[badge_variant="warning"] {{
            background-color: {Colors.WARNING_DARK_BG if is_dark else Colors.WARNING_BG};
        }}
        QFrame[badge_variant="warning"] QLabel {{
            color: {Colors.WARNING_DARK_TEXT if is_dark else Colors.WARNING};
            font-weight: bold;
            font-size: 10px;
            background: transparent;
            border: none;
        }}
        QFrame[badge_variant="error"] {{
            background-color: {Colors.ERROR_DARK_BG if is_dark else Colors.ERROR_BG};
        }}
        QFrame[badge_variant="error"] QLabel {{
            color: {Colors.ERROR_DARK_TEXT if is_dark else Colors.ERROR};
            font-weight: bold;
            font-size: 10px;
            background: transparent;
            border: none;
        }}
        QFrame[badge_variant="assigned"] {{
            background-color: {Colors.ASSIGNED_DARK_BG if is_dark else Colors.ASSIGNED_BG};
        }}
        QFrame[badge_variant="assigned"] QLabel {{
            color: {Colors.ASSIGNED_DARK_TEXT if is_dark else Colors.ASSIGNED};
            font-weight: bold;
            font-size: 10px;
            background: transparent;
            border: none;
        }}
        QFrame[badge_variant="reserved"] {{
            background-color: {Colors.RESERVED_DARK_BG if is_dark else Colors.RESERVED_BG};
        }}
        QFrame[badge_variant="reserved"] QLabel {{
            color: {Colors.RESERVED_DARK_TEXT if is_dark else Colors.RESERVED};
            font-weight: bold;
            font-size: 10px;
            background: transparent;
            border: none;
        }}
        QFrame[badge_variant="neutral"] {{
            background-color: {Colors.NEUTRAL_DARK_BG if is_dark else Colors.NEUTRAL_BG};
        }}
        QFrame[badge_variant="neutral"] QLabel {{
            color: {Colors.NEUTRAL_DARK_TEXT if is_dark else Colors.SLATE_500};
            font-weight: bold;
            font-size: 10px;
            background: transparent;
            border: none;
        }}

        /* Interactive Grid elements */
        QLabel#gridBadge {{
            background-color: {"#EFF6FF" if not is_dark else Colors.PRIMARY_HOVER};
            color: {"#2563EB" if not is_dark else "#FFFFFF"};
            border-radius: 6px;
            padding: 2px 8px;
            font-weight: {Typography.WEIGHT_BOLD};
            font-size: {Typography.SIZE_SM};
            margin-left: 4px;
        }}
        
        QFrame#interactiveGridRow {{
            background-color: {surf};
            border: 1px solid {border};
            border-radius: {Spacing.RADIUS_MD};
        }}
        
        /* Divider line */
        QFrame#dividerLine {{
            background-color: {border};
            max-height: 1px;
        }}
        
        /* FilterBar Styling */
        QFrame#filterBarFrame {{
            background-color: {surf};
            border-radius: {Spacing.RADIUS_MD};
            border: {Spacing.BORDER_WIDTH_SM} solid {border};
        }}
        
        QLineEdit#filterBarSearch {{
            padding: 10px 16px;
            border: {Spacing.BORDER_WIDTH_SM} solid {border};
            border-radius: {Spacing.RADIUS_MD};
            background-color: {surf};
            font-size: {Typography.SIZE_MD};
            color: {txt_primary};
        }}
        QLineEdit#filterBarSearch:focus {{
            border: {Spacing.BORDER_WIDTH_SM} solid {Colors.PRIMARY};
        }}
        
        QPushButton#filterBarActionBtn {{
            background-color: {Colors.ACCENT};
            color: #FFFFFF;
            border-radius: 8px;
            font-size: 24px;
            font-weight: {Typography.WEIGHT_BOLD};
            border: none;
            padding: 0px;
        }}
        QPushButton#filterBarActionBtn:hover {{
            background-color: {Colors.ACCENT_HOVER};
        }}
        
        /* OrderProcessingDialog Styling */
        QDialog#orderProcessingDialog {{
            background-color: {bg};
        }}
        
        QLabel#orderProcessingSubtitle {{
            color: {txt_secondary};
            font-weight: {Typography.WEIGHT_MEDIUM};
        }}
        
        QPushButton#orderProcessingCloseBtn {{
            font-size: 16px;
            font-weight: {Typography.WEIGHT_BOLD};
            border-radius: 4px;
            background-color: transparent;
            color: {txt_secondary};
            border: {Spacing.BORDER_WIDTH_SM} solid {border};
        }}
        QPushButton#orderProcessingCloseBtn:hover {{
            background-color: {surf};
            color: {txt_primary};
        }}
        
        QFrame#orderProcessingBanner {{
            background-color: {"#EFF6FF" if not is_dark else Colors.PRIMARY_HOVER};
            border: 1px solid {"#BFDBFE" if not is_dark else Colors.PRIMARY_LIGHT};
            border-radius: {Spacing.RADIUS_MD};
            padding: 12px;
        }}
        
        QLabel#orderProcessingBannerText {{
            color: {"#1E3A8A" if not is_dark else "#FFFFFF"};
            font-weight: {Typography.WEIGHT_MEDIUM};
            font-size: {Typography.SIZE_SM};
        }}
        
        QFrame#orderProcessingMetricBar {{
            background-color: {surf};
            border: 1px solid {border};
            border-radius: {Spacing.RADIUS_MD};
            padding: 10px;
        }}
        
        QLabel#orderProcessingMetricPending {{
            color: {txt_primary};
            font-weight: {Typography.WEIGHT_BOLD};
        }}
        
        QLabel#orderProcessingMetricAuth {{
            color: {txt_primary};
            font-weight: {Typography.WEIGHT_BOLD};
        }}
        
        QLabel#orderProcessingMetricRej {{
            color: {txt_primary};
            font-weight: {Typography.WEIGHT_BOLD};
        }}
        
        /* Table contour/border styling inside dialog */
        QDialog#orderProcessingDialog QTableWidget {{
            border: {Spacing.BORDER_WIDTH_SM} solid {border};
            border-radius: {Spacing.RADIUS_MD};
        }}
        
        QPushButton#orderProcessingRejectBtn {{
            background-color: transparent;
            color: {Colors.ERROR};
            border: {Spacing.BORDER_WIDTH_SM} solid {"#FCA5A5" if not is_dark else Colors.ERROR};
            padding: 8px 16px;
            border-radius: {Spacing.RADIUS_MD};
            font-weight: {Typography.WEIGHT_BOLD};
        }}
        QPushButton#orderProcessingRejectBtn:hover {{
            background-color: {"#FEF2F2" if not is_dark else Colors.PRIMARY_HOVER};
        }}
        
        QPushButton#orderProcessingAuthBtn {{
            background-color: {Colors.ACCENT};
            color: #FFFFFF;
            border: none;
            padding: 8px 16px;
            border-radius: {Spacing.RADIUS_MD};
            font-weight: {Typography.WEIGHT_BOLD};
        }}
        QPushButton#orderProcessingAuthBtn:hover {{
            background-color: {Colors.ACCENT_HOVER};
        }}
        
        /* Dashboard Styling */
        QFrame#dashboardIndicatorBar {{
            background-color: {Colors.ACCENT};
            border-radius: 2px;
        }}
        QLabel#dashboardTitle {{
            font-size: 20px;
            font-weight: {Typography.WEIGHT_BOLD};
            color: {txt_primary};
        }}
        QLabel#dashboardSubtitle {{
            font-size: {Typography.SIZE_SM};
            color: {txt_muted};
        }}
        QLabel#dashboardDatetime {{
            font-size: {Typography.SIZE_SM};
            color: {txt_secondary};
            font-weight: {Typography.WEIGHT_BOLD};
        }}
        QLabel#dashboardTableTitle {{
            font-size: {Typography.SIZE_MD};
            font-weight: {Typography.WEIGHT_BOLD};
            color: {txt_primary};
        }}
        QLabel#dashboardPaginationInfo {{
            font-size: {Typography.SIZE_SM};
            color: {txt_muted};
        }}
        
        /* Pagination Buttons */
        QPushButton#paginationPageBtn {{
            background-color: {surf};
            color: {txt_secondary};
            border: 1px solid {border};
            border-radius: 6px;
            font-weight: {Typography.WEIGHT_BOLD};
            font-size: {Typography.SIZE_SM};
            padding: 4px 8px;
            min-width: 28px;
            max-width: 28px;
            min-height: 28px;
            max-height: 28px;
        }}
        QPushButton#paginationPageBtn:hover {{
            background-color: {bg};
            color: {Colors.PRIMARY};
        }}
        
        QPushButton#paginationActivePageBtn {{
            background-color: {Colors.ACCENT};
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            font-weight: {Typography.WEIGHT_BOLD};
            font-size: {Typography.SIZE_SM};
            padding: 4px 8px;
            min-width: 28px;
            max-width: 28px;
            min-height: 28px;
            max-height: 28px;
        }}
        
        QPushButton#paginationNavBtn {{
            background-color: {surf};
            color: {txt_secondary};
            border: 1px solid {border};
            border-radius: 6px;
            font-weight: {Typography.WEIGHT_BOLD};
            font-size: {Typography.SIZE_SM};
            padding: 4px 8px;
            min-width: 28px;
            max-width: 28px;
            min-height: 28px;
            max-height: 28px;
        }}
        QPushButton#paginationNavBtn:hover {{
            background-color: {bg};
            color: {Colors.PRIMARY};
        }}
        QPushButton#paginationNavBtn:disabled {{
            background-color: {surf};
            color: {txt_muted};
            border: 1px solid {border};
        }}
        
        /* StatCard Labels */
        QLabel#statCardTitle {{
            font-weight: {Typography.WEIGHT_BOLD};
            color: {txt_secondary};
            font-size: {Typography.SIZE_SM};
        }}
        QLabel#statCardSub {{
            font-size: 11px;
            color: {txt_muted};
        }}
        
        /* Sidebar Brand & Logo */
        QLabel#sidebarLogo {{
            background-color: {Colors.ACCENT};
            border-radius: 10px;
        }}
        QLabel#sidebarBrandTitle {{
            font-size: 24px;
            font-weight: {Typography.WEIGHT_BOLD};
            color: {txt_primary};
        }}
        QLabel#sidebarBrandSubtitle {{
            font-size: {Typography.SIZE_SM};
            color: {txt_muted};
        }}
        
        /* Sidebar User Profile */
        QLabel#sidebarProfileUser {{
            font-size: {Typography.SIZE_SM};
            font-weight: {Typography.WEIGHT_BOLD};
            color: {txt_primary};
        }}
        QLabel#sidebarProfileStatus {{
            font-size: 11px;
            color: {Colors.SUCCESS};
            font-weight: {Typography.WEIGHT_BOLD};
        }}
        
        /* Sidebar Navigation Buttons */
        QPushButton#navBtn {{
            background-color: transparent;
            color: {txt_secondary};
            text-align: left;
            padding: 12px 20px;
            border-radius: {Spacing.RADIUS_MD};
            font-weight: {Typography.WEIGHT_MEDIUM};
            border: none;
        }}
        QPushButton#navBtn:hover {{
            background-color: {bg};
            color: {Colors.PRIMARY};
        }}
        QPushButton#navBtn:checked {{
            background-color: {"#EFF6FF" if not is_dark else Colors.PRIMARY_HOVER};
            color: {"#2563EB" if not is_dark else "#FFFFFF"};
            font-weight: {Typography.WEIGHT_BOLD};
            border: none;
        }}
        
        /* Sidebar Sub-Navigation Buttons */
        QPushButton#subNavBtn {{
            background-color: transparent;
            color: {txt_secondary};
            text-align: left;
            padding: 8px 12px 8px 24px;
            border-radius: {Spacing.RADIUS_MD};
            font-weight: {Typography.WEIGHT_MEDIUM};
            border: none;
        }}
        QPushButton#subNavBtn:hover {{
            background-color: {bg};
            color: {Colors.PRIMARY};
        }}
        QPushButton#subNavBtn:checked {{
            background-color: {"#EFF6FF" if not is_dark else Colors.PRIMARY_HOVER};
            color: {"#2563EB" if not is_dark else "#FFFFFF"};
            font-weight: {Typography.WEIGHT_BOLD};
            border: none;
        }}
        
        /* Tables */
        QTableWidget {{
            border: none;
            gridline-color: {border};
            background-color: {surf};
            alternate-background-color: {bg};
            outline: 0;
        }}
        QHeaderView::section {{
            background-color: {surf};
            border: none;
            border-bottom: 1px solid {border};
            border-right: 1px solid {border};
            padding: 8px;
            font-weight: {Typography.WEIGHT_SEMI_BOLD};
            color: {txt_secondary};
        }}
        QTableWidget::item {{
            padding: 8px;
            border-bottom: 1px solid {border};
        }}
        QTableWidget::item:selected {{
            background-color: {"#EFF6FF" if not is_dark else "#1E293B"};
            color: {"#2563EB" if not is_dark else "#60A5FA"};
            font-weight: bold;
        }}

        /* Table Corner Button (Top-Left corner) */
        QTableCornerButton::section {{
            background-color: {surf};
            border: none;
            border-bottom: 1px solid {border};
            border-right: 1px solid {border};
        }}

        /* Tabs */
        QTabWidget::pane {{
            border: 1px solid {border};
            background-color: {surf};
            border-radius: {Spacing.RADIUS_MD};
            padding: 16px;
        }}
        QTabBar::tab {{
            background-color: {bg};
            color: {txt_secondary};
            padding: 8px 16px;
            border: 1px solid {border};
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            margin-right: 2px;
            font-weight: bold;
        }}
        QTabBar::tab:selected {{
            background-color: {surf};
            color: {"#2563EB" if not is_dark else "#60A5FA"};
            border-bottom: 2px solid {"#2563EB" if not is_dark else "#60A5FA"};
        }}
        QTabBar::tab:hover:!selected {{
            background-color: {border};
            color: {txt_primary};
        }}
        
        /* CheckBoxes */
        QCheckBox {{
            background-color: transparent;
            color: {txt_primary};
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1.5px solid {border};
            border-radius: 4px;
            background-color: {surf};
        }}
        QCheckBox::indicator:hover {{
            border-color: {Colors.ACCENT};
        }}
        QCheckBox::indicator:checked {{
            background-color: {Colors.ACCENT};
            border-color: {Colors.ACCENT};
            image: url({check_path});
        }}
        QCheckBox::indicator:disabled {{
            border-color: {border};
            background-color: {bg};
        }}
        
        /* Menu Bar and Menus Dropdowns */
        QMenuBar {{
            background-color: {surf};
            color: {txt_primary};
            border-bottom: 1px solid {border};
            font-size: 13px;
            font-weight: 500;
            padding: 2px 6px;
        }}
        QMenuBar::item {{
            background-color: transparent;
            color: {txt_primary};
            padding: 6px 12px;
            margin: 2px;
            border-radius: 6px;
        }}
        QMenuBar::item:selected {{
            background-color: {border};
            color: {Colors.ACCENT};
        }}
        QMenuBar::item:pressed {{
            background-color: {"#CBD5E1" if not is_dark else "#475569"};
        }}
        QMenu {{
            background-color: {surf};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 6px 4px;
        }}
        QMenu::item {{
            padding: 6px 24px 6px 12px;
            background-color: transparent;
            color: {txt_primary};
            border-radius: 4px;
            font-size: 12px;
        }}
        QMenu::item:selected {{
            background-color: {"#EFF6FF" if not is_dark else Colors.PRIMARY_HOVER};
            color: {"#2563EB" if not is_dark else "#FFFFFF"};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {border};
            margin: 4px 6px;
        }}
        
        /* ScrollBars */
        QScrollBar:vertical {{
            border: none;
            background-color: transparent;
            width: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {"#CBD5E1" if not is_dark else "#475569"};
            min-height: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {"#94A3B8" if not is_dark else "#64748B"};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: transparent;
            height: 0px;
        }}
        QScrollBar:horizontal {{
            border: none;
            background-color: transparent;
            height: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {"#CBD5E1" if not is_dark else "#475569"};
            min-width: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {"#94A3B8" if not is_dark else "#64748B"};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            border: none;
            background: transparent;
            width: 0px;
        }}

        /* ToolTips */
        QToolTip {{
            background-color: {"#1E293B" if not is_dark else "#0F172A"};
            color: #FFFFFF;
            border: 1px solid {"#334155" if not is_dark else "#475569"};
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
        }}

        /* Message and Loading Dialog Floating Cards */
        QWidget#messageDialogCard, GLLoadingDialog {{
            background-color: {surf};
            border: 1px solid {border};
            border-radius: 12px;
        }}
        
        /* Logged In User Widget on Menu Bar */
        QWidget#menuUserWidget {{
            background-color: transparent;
            margin: 2px;
            border-radius: 0px;
        }}
        QWidget#menuUserWidget:hover {{
            background-color: {border};
        }}
        
        /* Sidebar Action Buttons styling */
        QPushButton#themeToggleBtn {{
            background-color: transparent;
            color: {txt_secondary};
            text-align: left;
            padding: 10px 16px;
            border: 1px solid {border};
            border-radius: 10px;
            font-size: 13px;
            font-weight: bold;
        }}
        QPushButton#themeToggleBtn:hover {{
            background-color: {bg};
        }}
        QPushButton#logoutBtn {{
            background-color: transparent;
            color: #DC2626;
            text-align: left;
            padding: 10px 16px;
            border: 1px solid #FCA5A5;
            border-radius: 10px;
            font-size: 13px;
            font-weight: bold;
        }}
        QPushButton#logoutBtn:hover {{
            background-color: #FEF2F2;
            border-color: #EF4444;
        }}

        /* Bot Face A and Face C Specific Styles (Forced Light Look) */
        BotView, BillingBotView, R2FCancunView {{
            background-color: #f3f4f6;
            color: #1f2937;
            font-family: 'Segoe UI', sans-serif;
        }}
        BotView QFrame#card, BillingBotView QFrame#card, R2FCancunView QFrame#card {{
            background-color: #ffffff;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
        }}
        BotView QLabel, BillingBotView QLabel, R2FCancunView QLabel {{
            background: transparent;
        }}
        BotView QPushButton#primaryBtn {{
            background-color: #1e293b;
            color: white;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }}
        BotView QPushButton#primaryBtn:hover {{
            background-color: #334155;
        }}
        BillingBotView QPushButton#primaryBtn, R2FCancunView QPushButton#primaryBtn {{
            background-color: #1e293b;
            color: white;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }}
        BillingBotView QPushButton#primaryBtn:hover, R2FCancunView QPushButton#primaryBtn:hover {{
            background-color: #334155;
        }}
        BotView QPushButton#secondaryBtn, BillingBotView QPushButton#secondaryBtn, R2FCancunView QPushButton#secondaryBtn {{
            background-color: #ffffff;
            color: #4b5563;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            padding: 8px 16px;
        }}
        BotView QPushButton#secondaryBtn:hover, BillingBotView QPushButton#secondaryBtn:hover, R2FCancunView QPushButton#secondaryBtn:hover {{
            background-color: #f9fafb;
        }}
        BotView QPushButton#iconHeaderBtn {{
            background-color: transparent;
            border: none;
            color: white;
            font-size: 16px;
            padding: 4px;
        }}
        BotView QPushButton#iconHeaderBtn:hover {{
            background-color: #334155;
            border-radius: 4px;
        }}
        BillingBotView QPushButton#iconHeaderBtn, R2FCancunView QPushButton#iconHeaderBtn {{
            background-color: transparent;
            border: none;
            color: white;
            font-size: 16px;
            padding: 4px;
        }}
        BillingBotView QPushButton#iconHeaderBtn:hover, R2FCancunView QPushButton#iconHeaderBtn:hover {{
            background-color: #334155;
            border-radius: 4px;
        }}
        BotView QTextEdit#console {{
            background-color: #111827;
            color: #10b981;
            font-family: 'Consolas', monospace;
            border-radius: 4px;
            padding: 8px;
        }}
        BillingBotView QTextEdit#console, R2FCancunView QTextEdit#console {{
            background-color: #111827;
            color: #10b981;
            font-family: 'Consolas', monospace;
            border-radius: 4px;
            padding: 8px;
        }}
        BotView QProgressBar, BillingBotView QProgressBar, R2FCancunView QProgressBar {{
            border: 1px solid #d1d5db;
            border-radius: 4px;
            text-align: center;
            background-color: #f3f4f6;
            color: #111827;
            font-weight: bold;
        }}
        BotView QProgressBar::chunk {{
            background-color: #3b82f6;
            border-radius: 3px;
        }}
        BillingBotView QProgressBar::chunk, R2FCancunView QProgressBar::chunk {{
            background-color: #3b82f6;
            border-radius: 3px;
        }}
        QFrame#botHeaderFaceA {{
            background-color: #1e293b;
            border-radius: 8px;
            padding: 10px 20px;
        }}
        QFrame#botHeaderFaceA QLabel {{
            color: white;
            font-size: 16px;
            font-weight: bold;
        }}
        QFrame#botHeaderFaceC {{
            background-color: #1e293b;
            border-radius: 8px;
            padding: 10px 20px;
        }}
        QFrame#botHeaderFaceC QLabel {{
            color: white;
            font-size: 16px;
            font-weight: bold;
        }}
        
        /* Table Styles inside Bots */
        BotView QTableWidget#botTable, BillingBotView QTableWidget#botTable, R2FCancunView QTableWidget#botTable {{
            background-color: white;
            color: #374151;
            gridline-color: #e5e7eb;
            border: 1px solid #e5e7eb;
        }}
        BotView QTableWidget#botTable QHeaderView::section, BillingBotView QTableWidget#botTable QHeaderView::section, R2FCancunView QTableWidget#botTable QHeaderView::section {{
            background-color: #f9fafb;
            color: #374151;
            font-weight: bold;
            border: none;
            border-bottom: 1px solid #e5e7eb;
            padding: 4px;
        }}
        
        /* Dropdown menus for Bots (forces light style) */
        QMenu#botMenu {{
            background-color: #ffffff;
            color: #1f2937;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            padding: 4px;
        }}
        QMenu#botMenu::item {{
            padding: 6px 12px;
            border-radius: 2px;
        }}
        QMenu#botMenu::item:selected {{
            background-color: #f3f4f6;
        }}
        """
        return qss

    @classmethod
    def apply_theme(cls, widget=None, is_dark: bool = False):
        """Applies the computed QSS theme stylesheet globally and to the given widget."""
        cls._is_dark = is_dark
        qss = cls.get_qss(is_dark)
        
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.setStyleSheet(qss)
            
        if widget and widget is not app:
            widget.setStyleSheet(qss)
