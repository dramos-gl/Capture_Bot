import requests
import json
import sys

def test_api():
    base_url = "http://127.0.0.1:8000"
    print("=== INICIANDO PRUEBAS DE API (FastAPI) ===")
    
    # 1. Probar Ping al Servidor
    print("\n1. Probando ping al servidor...")
    try:
        res = requests.get(f"{base_url}/")
        print(f"Status Code: {res.status_code}")
        print(f"Respuesta: {json.dumps(res.json(), indent=2)}")
    except Exception as e:
        print(f"ERROR al conectar al servidor: {e}")
        sys.exit(1)
        
    # 2. Probar Inicio de Sesión (Login)
    print("\n2. Probando inicio de sesión (/api/auth/login)...")
    login_payload = {
        "username": "admin",
        "password": "admin123",
        "ip_equipo": "127.0.0.1",
        "equipo_nombre": "Test Runner",
        "equipo_uuid": "test-uuid-1234"
    }
    try:
        res = requests.post(f"{base_url}/api/auth/login", json=login_payload)
        print(f"Status Code: {res.status_code}")
        if res.status_code == 200:
            login_data = res.json()
            print(f"Respuesta: {json.dumps(login_data, indent=2)}")
            token = login_data["access_token"]
            usuario_id = login_data["usuario_id"]
            sesion_id = login_data["sesion_id"]
            print("¡LOGIN EXITOSO!")
        else:
            print(f"Fallo de login: {res.text}")
            print("Nota: Asegúrese de tener el usuario 'admin' registrado en la base de datos.")
            return
    except Exception as e:
        print(f"ERROR en login: {e}")
        return

    # 3. Probar Acceso a Módulos (Nivel 1)
    print(f"\n3. Probando verificación de acceso al módulo CTRL_REF para usuario {usuario_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(f"{base_url}/api/auth/module-access/{usuario_id}/CTRL_REF", headers=headers)
        print(f"Status Code: {res.status_code}")
        print(f"Respuesta: {json.dumps(res.json(), indent=2)}")
    except Exception as e:
        print(f"ERROR en verificación de módulo: {e}")

    # 4. Probar Obtención de Catálogos
    print("\n4. Probando obtención de catálogos activos (/api/ops/catalogos)...")
    try:
        res = requests.get(f"{base_url}/api/ops/catalogos", headers=headers)
        print(f"Status Code: {res.status_code}")
        if res.status_code == 200:
            catalogs = res.json()
            print(f"RFCs encontrados: {len(catalogs.get('rfcs', []))}")
            print(f"Conceptos encontrados: {len(catalogs.get('conceptos', []))}")
            print(f"Delegaciones encontradas: {len(catalogs.get('delegaciones', []))}")
            print(f"Municipios encontrados: {len(catalogs.get('municipios', []))}")
        else:
            print(f"Error: {res.text}")
    except Exception as e:
        print(f"ERROR al traer catálogos: {e}")

    # 5. Probar Listado de Órdenes
    print("\n5. Probando obtención de órdenes (/api/ops/ordenes)...")
    try:
        res = requests.get(f"{base_url}/api/ops/ordenes", headers=headers)
        print(f"Status Code: {res.status_code}")
        if res.status_code == 200:
            ordenes = res.json()
            print(f"Órdenes encontradas en BD: {len(ordenes)}")
            if ordenes:
                print(f"Ejemplo de primer orden: {json.dumps(ordenes[0], indent=2)}")
        else:
            print(f"Error: {res.text}")
    except Exception as e:
        print(f"ERROR al listar órdenes: {e}")

    # 6. Probar Cierre de Sesión (Logout)
    print("\n6. Probando cierre de sesión (/api/auth/logout)...")
    try:
        logout_payload = {"sesion_id": sesion_id}
        res = requests.post(f"{base_url}/api/auth/logout", json=logout_payload, headers=headers)
        print(f"Status Code: {res.status_code}")
        print(f"Respuesta: {json.dumps(res.json(), indent=2)}")
        print("=== PRUEBAS CONCLUIDAS CON ÉXITO ===")
    except Exception as e:
        print(f"ERROR en logout: {e}")

if __name__ == "__main__":
    test_api()
