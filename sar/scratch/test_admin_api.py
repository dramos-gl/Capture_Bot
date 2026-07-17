import requests
import json

BASE_URL = "http://localhost:8000/api/admin"

def run_tests():
    print("=== PROBANDO API REST DE ADMINISTRACIÓN ===")
    
    # 1. Test get entity data
    print("\n1. Probando GET /data/parametros...")
    try:
        r = requests.get(f"{BASE_URL}/data/parametros")
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            params = r.json()
            print(f"Total parámetros encontrados: {len(params)}")
            if params:
                print(f"Primer parámetro: {params[0]}")
        else:
            print(f"Error: {r.text}")
    except Exception as e:
        print(f"Excepción: {e}")
        
    print("\n2. Probando GET /data/usuarios...")
    try:
        r = requests.get(f"{BASE_URL}/data/usuarios")
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            users = r.json()
            print(f"Total usuarios: {len(users)}")
            if users:
                print(f"Primer usuario: {users[0]}")
    except Exception as e:
        print(f"Excepción: {e}")

    print("\n3. Probando GET /permissions-for-user/1...")
    try:
        r = requests.get(f"{BASE_URL}/permissions-for-user/1")
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            perms = r.json()
            print(f"Total permisos para usuario 1: {len(perms)}")
            if perms:
                print(f"Muestras de permisos: {perms[:3]}")
    except Exception as e:
        print(f"Excepción: {e}")

    # 4. Save test parametro
    print("\n4. Probando POST /save/parametros...")
    payload = {
        "usuario_id": 1,
        "sesion_id": 1,
        "data": {
            "parametro_id": None,
            "codigo": "TEST_AUDIT_PARAM",
            "valor": "VALOR_PRUEBA_API",
            "activo": True
        }
    }
    try:
        # We need an active session to save.
        # Since session 1 might not be active, let's create a test login first or override check.
        # Let's see if login works:
        login_payload = {
            "username": "admin",
            "password": "admin123",
            "ip_equipo": "127.0.0.1",
            "equipo_nombre": "Cliente Test"
        }
        login_r = requests.post("http://localhost:8000/api/auth/login", json=login_payload)
        if login_r.status_code == 200:
            login_data = login_r.json()
            print("Login exitoso para test de guardado!")
            payload["usuario_id"] = login_data["usuario_id"]
            payload["sesion_id"] = login_data["sesion_id"]
            
            r = requests.post(f"{BASE_URL}/save/parametros", json=payload)
            print(f"Save Status: {r.status_code}")
            print(f"Response: {r.text}")
        else:
            print(f"Login falló (Status {login_r.status_code}): {login_r.text}")
    except Exception as e:
        print(f"Excepción en guardado: {e}")

if __name__ == "__main__":
    run_tests()
