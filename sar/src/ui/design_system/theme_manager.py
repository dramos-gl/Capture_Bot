"""Theme manager utilizing design tokens to apply premium Dark/Light modes."""

from sar.src.ui.design_system.tokens.colors import Colors
from sar.src.ui.design_system.tokens.typography import Typography
from sar.src.ui.design_system.tokens.spacing import Spacing

class ThemeManager:
    """Manages global application theme state and QSS loading."""

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
            border: {Spacing.BORDER_WIDTH_SM} solid {border};
            border-radius: {Spacing.RADIUS_MD};
            padding: 4px 8px;
            color: {txt_primary};
        }}
        QLineEdit:focus {{
            border: {Spacing.BORDER_WIDTH_SM} solid {Colors.PRIMARY};
        }}
        
        /* ComboBoxes */
        QComboBox {{
            background-color: {surf};
            border: {Spacing.BORDER_WIDTH_SM} solid {border};
            border-radius: {Spacing.RADIUS_MD};
            padding: 4px 8px;
            color: {txt_primary};
        }}
        QComboBox:on {{
            border-color: {Colors.PRIMARY};
        }}
        QComboBox::drop-down {{
            border: none;
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 30px;
        }}
        QComboBox::down-arrow {{
            image: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='none' stroke='%23475569' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
            width: 16px;
            height: 16px;
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
            border-radius: 20px;
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
            border-radius: 16px;
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
            color: {Colors.WARNING};
            font-weight: {Typography.WEIGHT_BOLD};
        }}
        
        QLabel#orderProcessingMetricAuth {{
            color: {Colors.SUCCESS};
            font-weight: {Typography.WEIGHT_BOLD};
        }}
        
        QLabel#orderProcessingMetricRej {{
            color: {Colors.ERROR};
            font-weight: {Typography.WEIGHT_BOLD};
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
            background: {surf};
            border-radius: {Spacing.RADIUS_MD};
        }}
        QTabBar::tab {{
            background: {bg};
            color: {txt_secondary};
            padding: 8px 16px;
            border: 1px solid {border};
            border-bottom-color: {border};
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            background: {surf};
            color: {Colors.PRIMARY};
            border-bottom-color: {surf};
            font-weight: bold;
        }}
        QTabBar::tab:hover:!selected {{
            background: {border};
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
            image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='4' stroke-linecap='round' stroke-linejoin='round'><polyline points='20 6 9 17 4 12'/></svg>");
        }}
        QCheckBox::indicator:disabled {{
            border-color: {border};
            background-color: {bg};
        }}
        
        /* Menu Bar and Menus Dropdowns */
        QMenuBar {{
            background-color: {surf};
            border-bottom: 1px solid {border};
        }}
        QMenuBar::item {{
            background-color: transparent;
            padding: 6px 10px;
            margin: 2px;
            border-radius: 0px;
        }}
        QMenuBar::item:selected {{
            background-color: {border};
            color: {Colors.PRIMARY};
        }}
        QMenu {{
            background-color: {surf};
            border: 1px solid {border};
            border-radius: 0px;
            padding: 4px 0px;
        }}
        QMenu::item {{
            padding: 6px 24px;
            background-color: transparent;
            border-radius: 0px;
        }}
        QMenu::item:selected {{
            background-color: {Colors.PRIMARY if not is_dark else Colors.PRIMARY_HOVER};
            color: #FFFFFF;
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {border};
            margin: 4px 0px;
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
        """
        return qss

    @classmethod
    def apply_theme(cls, widget, is_dark: bool = False):
        """Applies the computed QSS theme stylesheet to the given widget/app."""
        qss = cls.get_qss(is_dark)
        widget.setStyleSheet(qss)
