import os
import sys
from PySide6.QtWidgets import QApplication

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Ensure single QApplication instance
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from sar.src.ui.design_system.components.organisms.gl_sidebar import NavigationSidebar
from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

def test_sidebar_menu_structure():
    sidebar = NavigationSidebar()
    
    # 1. Main menu items must have 4 top-level items
    menu_keys = [item[1] for item in sidebar.menu_items]
    assert menu_keys == ["dashboard", "ordenes", "inventario", "configuracion"], (
        f"Esperados 4 menús principales, encontrados: {menu_keys}"
    )
    
    # 2. Órdenes submenu must have 4 items in strict sequence
    orden_buttons = [
        sidebar.btn_capturar_nueva,
        sidebar.btn_ordenes_capturadas,
        sidebar.btn_solicitudes,
        sidebar.btn_derechos
    ]
    assert [btn.text() for btn in orden_buttons] == [
        "Capturar Nueva Orden",
        "Órdenes Capturadas",
        "Solicitudes",
        "Derechos"
    ]
    
    # 3. Button dictionary bindings
    assert "referencias" in sidebar.buttons
    assert sidebar.buttons["referencias"] == sidebar.btn_derechos
    assert sidebar.buttons["capturar_orden"] == sidebar.btn_capturar_nueva
    assert sidebar.buttons["ordenes_capturadas"] == sidebar.btn_ordenes_capturadas
    assert sidebar.buttons["solicitudes"] == sidebar.btn_solicitudes

def test_sidebar_signals_and_navigation():
    sidebar = NavigationSidebar()
    selected_keys = []
    sidebar.nav_selected.connect(lambda k: selected_keys.append(k))
    
    # Authorize items
    for k in ["capturar_orden", "ordenes_capturadas", "solicitudes", "referencias"]:
        sidebar.show_item(k)
        
    # Click on "Derechos"
    sidebar.btn_derechos.click()
    assert selected_keys[-1] == "referencias"
    assert sidebar.btn_derechos.isChecked() is True
    assert sidebar.btn_capturar_nueva.isChecked() is False
    assert sidebar.buttons["ordenes"].isChecked() is True
    
    # Click on "Solicitudes"
    sidebar.btn_solicitudes.click()
    assert selected_keys[-1] == "solicitudes"
    assert sidebar.btn_solicitudes.isChecked() is True
    assert sidebar.btn_derechos.isChecked() is False

def test_sidebar_collapse_retention_security():
    sidebar = NavigationSidebar()
    # Authorize only "referencias" and "dashboard" (Simulating CONSULTA role)
    sidebar.show_item("dashboard")
    sidebar.show_item("ordenes")
    sidebar.show_item("referencias")
    
    # capturar_orden should NOT be in authorized items
    assert "capturar_orden" not in sidebar._authorized_items
    assert "referencias" in sidebar._authorized_items
    
    # Toggle collapse to 70px
    sidebar.toggle_collapse()
    assert sidebar.is_collapsed is True
    assert sidebar.width() == 70
    
    # Toggle collapse back to 250px
    sidebar.toggle_collapse()
    assert sidebar.is_collapsed is False
    assert sidebar.width() == 250
    
    # Verify that un-authorized buttons remain hidden and NOT revived
    assert sidebar.btn_capturar_nueva.isVisible() is False
    assert sidebar.btn_ordenes_capturadas.isVisible() is False
    assert sidebar.btn_solicitudes.isVisible() is False

def test_modulos_db_order():
    db = DatabaseConnector()
    with db.get_session() as session:
        rows = session.execute(text("""
            SELECT codigo, orden FROM sar_seguridad.modulo 
            WHERE codigo IN ('DASHBOARD', 'ORDENES', 'SOLICITUDES', 'DERECHOS', 'CONTROL_DERECHOS')
            ORDER BY orden
        """)).fetchall()
        
        order_dict = {r.codigo: float(r.orden) for r in rows}
        assert order_dict["DASHBOARD"] == 1.0
        assert order_dict["ORDENES"] == 2.0
        assert order_dict["SOLICITUDES"] == 2.3
        assert order_dict["DERECHOS"] == 2.4
        assert order_dict["CONTROL_DERECHOS"] == 3.0

if __name__ == "__main__":
    print("Ejecutando test_sidebar_menu_structure()...")
    test_sidebar_menu_structure()
    print("OK!")
    
    print("Ejecutando test_sidebar_signals_and_navigation()...")
    test_sidebar_signals_and_navigation()
    print("OK!")
    
    print("Ejecutando test_sidebar_collapse_retention_security()...")
    test_sidebar_collapse_retention_security()
    print("OK!")
    
    print("Ejecutando test_modulos_db_order()...")
    test_modulos_db_order()
    print("OK!")
    
    print("\n[SUCCESS] TODAS LAS PRUEBAS DE SIDEBAR Y NAVEGACION PASARON CON EXITO.")


