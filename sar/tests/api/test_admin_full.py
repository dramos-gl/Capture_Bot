# -*- coding: utf-8 -*-
"""
Prueba completa del Modulo de Administracion via API REST.
Valida todos los endpoints: GET /data/{entity}, POST /save/{entity},
y consultas de permisos/roles.
"""
import sys
import requests

BASE = "http://localhost:8000/api/admin"
AUTH = "http://localhost:8000/api/auth"

results = []

def check(name, expr, expected=True):
    ok = bool(expr) == expected
    tag = "[PASS]" if ok else "[FAIL]"
    results.append((ok, f"{tag} | {name}"))
    return ok

def run_tests():
    print("=" * 60)
    print("  AUDITORIA: Modulo Administracion - CONNECT_VIA_API")
    print("=" * 60)

    # --- AUTENTICACION ---
    print("\n[1] Autenticacion")
    r = requests.post(f"{AUTH}/login", json={
        "username": "admin", "password": "admin123",
        "ip_equipo": "127.0.0.1", "equipo_nombre": "AUDIT_TEST"
    })
    check("POST /auth/login devuelve 200", r.status_code == 200)
    if r.status_code != 200:
        print(f"    ERROR: {r.text}")
        print("    No se puede continuar sin sesion activa.")
        return
    d = r.json()
    uid = d["usuario_id"]
    sid = d["sesion_id"]
    check("Login retorna usuario_id > 0", uid > 0)
    check("Login retorna sesion_id > 0", sid > 0)

    # --- GET /data/{entity} ---
    print("\n[2] GET /data/{entity} - Todas las entidades")
    entities = [
        "usuarios", "roles", "modulos", "acciones", "app_modulos",
        "conceptos", "municipios", "delegaciones", "rfcs",
        "estados", "parametros", "localizadores"
    ]
    for entity in entities:
        r = requests.get(f"{BASE}/data/{entity}")
        ok = check(f"GET /data/{entity} -> 200", r.status_code == 200)
        if ok:
            data = r.json()
            check(f"  /data/{entity} retorna lista", isinstance(data, list))
        else:
            print(f"    ERROR: {r.text[:200]}")

    # --- PERMISOS ---
    print("\n[3] Endpoints de permisos y roles")
    r = requests.get(f"{BASE}/permissions-for-user/{uid}")
    check("GET /permissions-for-user/{uid} -> 200", r.status_code == 200)
    if r.status_code == 200:
        perms = r.json()
        check("Permisos es lista no vacia", isinstance(perms, list) and len(perms) > 0)
        if perms:
            check("Permiso formato [modulo, accion]", isinstance(perms[0], list) and len(perms[0]) == 2)

    r = requests.get(f"{BASE}/roles-for-user/{uid}")
    check("GET /roles-for-user/{uid} -> 200", r.status_code == 200)

    r_roles = requests.get(f"{BASE}/data/roles")
    if r_roles.status_code == 200 and r_roles.json():
        rol_id = r_roles.json()[0]["rol_id"]
        r = requests.get(f"{BASE}/permisos-for-rol/{rol_id}")
        check(f"GET /permisos-for-rol/{rol_id} -> 200", r.status_code == 200)

    # --- CAMPOS DE RESPUESTA ---
    print("\n[4] Validacion de campos en respuestas")
    r = requests.get(f"{BASE}/data/usuarios")
    if r.status_code == 200 and r.json():
        u = r.json()[0]
        check("Usuario tiene 'usuario_id'", "usuario_id" in u)
        check("Usuario tiene 'username'", "username" in u)
        check("Usuario tiene 'activo'", "activo" in u)

    r = requests.get(f"{BASE}/data/roles")
    if r.status_code == 200 and r.json():
        rol = r.json()[0]
        check("Rol tiene 'rol_id'", "rol_id" in rol)
        check("Rol tiene 'codigo'", "codigo" in rol)
        check("Rol tiene 'activo'", "activo" in rol)

    r = requests.get(f"{BASE}/data/modulos")
    if r.status_code == 200 and r.json():
        mod = r.json()[0]
        check("Modulo tiene 'id'", "id" in mod)
        check("Modulo tiene 'codigo'", "codigo" in mod)
        check("Modulo tiene 'activo'", "activo" in mod)

    r = requests.get(f"{BASE}/data/acciones")
    if r.status_code == 200 and r.json():
        acc = r.json()[0]
        check("Accion tiene 'id'", "id" in acc)
        check("Accion tiene 'codigo'", "codigo" in acc)
        check("Accion tiene 'activo'", "activo" in acc)

    r = requests.get(f"{BASE}/data/localizadores")
    if r.status_code == 200 and r.json():
        loc = r.json()[0]
        check("Localizador tiene 'localizador_id'", "localizador_id" in loc)
        check("Localizador tiene 'nombre_clave'", "nombre_clave" in loc)
        check("Localizador tiene 'estrategia_selector'", "estrategia_selector" in loc)
        check("Localizador tiene 'valor_selector'", "valor_selector" in loc)

    r = requests.get(f"{BASE}/data/delegaciones")
    if r.status_code == 200 and r.json():
        delg = r.json()[0]
        check("Delegacion tiene 'delegacion_id'", "delegacion_id" in delg)
        check("Delegacion tiene 'municipio_id'", "municipio_id" in delg)

    # --- CRUD PARAMETRO ---
    import time
    test_codigo = f"TEST_AUDIT_{int(time.time())}"
    print("\n[5] POST /save/parametros (ciclo CRUD)")
    payload = {
        "usuario_id": uid, "sesion_id": sid,
        "data": {"parametro_id": None, "codigo": test_codigo, "valor": "V1", "activo": True}
    }
    r = requests.post(f"{BASE}/save/parametros", json=payload)
    check("POST /save/parametros (crear) -> 200", r.status_code == 200)
    if r.status_code == 200:
        created_id = r.json().get("id")
        check("Respuesta incluye 'id' del nuevo registro", created_id is not None)

        # Verify in GET
        r2 = requests.get(f"{BASE}/data/parametros")
        if r2.status_code == 200:
            found = any(p.get("codigo") == "TEST_AUDIT_2026" for p in r2.json())
            check("Parametro creado aparece en GET /data/parametros", found)

        # Update
        payload["data"]["parametro_id"] = created_id
        payload["data"]["valor"] = "V2"
        r3 = requests.post(f"{BASE}/save/parametros", json=payload)
        check("POST /save/parametros (actualizar) -> 200", r3.status_code == 200)

        # Cleanup
        payload["data"]["activo"] = False
        requests.post(f"{BASE}/save/parametros", json=payload)

    # --- CRUD CONCEPTO ---
    print("\n[6] POST /save/conceptos")
    r = requests.post(f"{BASE}/save/conceptos", json={
        "usuario_id": uid, "sesion_id": sid,
        "data": {"concepto_id": None, "codigo_portal": "TST", "nombre": "Concepto Audit Test", "alias": "CAT", "activo": True}
    })
    check("POST /save/conceptos -> 200", r.status_code == 200)

    # --- CRUD MUNICIPIO ---
    print("\n[7] POST /save/municipios")
    r = requests.post(f"{BASE}/save/municipios", json={
        "usuario_id": uid, "sesion_id": sid,
        "data": {"municipio_id": None, "codigo_portal": "MX99", "nombre": "Municipio Test Audit", "activo": True}
    })
    check("POST /save/municipios -> 200", r.status_code == 200)

    # --- LOGOUT ---
    print("\n[8] Logout")
    r = requests.post(f"{AUTH}/logout", json={"sesion_id": sid})
    check("POST /auth/logout -> 200", r.status_code == 200)

    # --- RESUMEN ---
    print("\n" + "=" * 60)
    print("  RESUMEN")
    print("=" * 60)
    passed = sum(1 for ok, _ in results if ok)
    total = len(results)
    for ok, msg in results:
        print(msg)
    print(f"\n  Resultado: {passed}/{total} pruebas exitosas")
    if passed == total:
        print("  STATUS: TODOS LOS CHECKS PASARON - Admin 100% OK en modo API")
    else:
        fails = total - passed
        print(f"  STATUS: {fails} prueba(s) fallaron - Revisar arriba")
    return passed == total

if __name__ == "__main__":
    ok = run_tests()
    sys.exit(0 if ok else 1)
