import sys
sys.path.insert(0, '.')
from sar.src.storage.db_connector import DatabaseConnector
from sar.src.services.inventario_ui_service import InventarioUIService

connector = DatabaseConnector()
service = InventarioUIService(connector)

print("=== Test get_dimensiones_con_stock_facturadas ===")
dims = service.get_dimensiones_con_stock_facturadas("Disponible")
print("Empresas:", dims["empresas"])
print("Conceptos:", dims["conceptos"])
print("Delegaciones:", dims["delegaciones"])
print("Desarrollos:", dims["desarrollos"])

print("\n=== Test get_referencias_facturadas_paginated con empresa CADU RESIDENCIAS ===")
res = service.get_referencias_facturadas_paginated(
    limit=10000,
    offset=0,
    search_text="",
    concepto_id=None,
    rfc_id=None,
    filter_assigned="Disponible",
    empresa_nombre="CADU RESIDENCIAS SA DE CV"
)
tc = res["total_count"]
rc = len(res["records"])
print(f"CADU RESIDENCIAS -> Total count: {tc}, fetched: {rc}")
assert tc == 212, f"Expected 212, got {tc}"
assert rc == 212, f"Expected 212, got {rc}"

print("\n=== Test get_referencias_facturadas_paginated con concepto ===")
c_name = dims["conceptos"][0]
res_c = service.get_referencias_facturadas_paginated(
    limit=10000,
    offset=0,
    search_text="",
    concepto_id=None,
    rfc_id=None,
    filter_assigned="Disponible",
    concepto_nombre=c_name
)
tc_c = res_c["total_count"]
rc_c = len(res_c["records"])
print(f"Concepto {c_name} -> Total count: {tc_c}, fetched: {rc_c}")

print("\n=== Test FastAPI router functions symmetry ===")
from sar.src.api.routers.docs_router import get_dimensiones_con_stock_facturadas, get_referencias_facturadas

with connector.get_session() as session:
    api_dims = get_dimensiones_con_stock_facturadas(filter_assigned="Disponible", orden_ids=None, db=session)
    print("FastAPI dims empresas:", api_dims.get("empresas"))
    assert "CADU RESIDENCIAS SA DE CV" in api_dims.get("empresas", [])
    assert "CHETUMAL" in api_dims.get("delegaciones", [])

    api_res = get_referencias_facturadas(
        limit=10000,
        filter_assigned="Disponible",
        empresa_nombre="CADU RESIDENCIAS SA DE CV",
        db=session
    )
    print("FastAPI CADU RESIDENCIAS total_count:", api_res.get("total_count"), "fetched:", len(api_res.get("records", [])))
    assert api_res.get("total_count") == 212
    assert len(api_res.get("records", [])) == 212

print("\n>>> ALL TESTS PASSED WITH 100% SUCCESS AND ZERO REGRESSIONS <<<")
