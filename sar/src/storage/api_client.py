import os
import json
import requests
import keyring
from typing import Optional

class APIClient:
    """Secure HTTP client wrapper for PySide6 to consume the SAR FastAPI backend."""

    def __init__(self):
        # 1. Cargar configuraciones locales del settings.json
        import sys
        
        # Resolver ruta robusta de settings.json (soporte para PyInstaller)
        from sar.src.paths import get_settings_path
        settings_path = get_settings_path()
            
        self.settings_data = {}
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    self.settings_data = json.load(f)
            except Exception as e:
                print(f"Error al abrir settings.json en APIClient: {e}")

        self.api_url = self.settings_data.get("API_URL", "http://localhost:8000")
        self.connect_via_api = self.settings_data.get("CONNECT_VIA_API", False)
        
        # Almacén en memoria ram local por si el OS bloquea el Keyring de Windows
        self._token_fallback = None

    def save_token(self, username: str, token: str) -> None:
        """Guarda el token JWT usando keyring (OS) o el fallback en memoria ram."""
        try:
            keyring.set_password("sistema_sar_token", username, token)
        except Exception as e:
            print(f"Advertencia: Keyring bloqueado por OS, usando fallback en memoria: {e}")
            self._token_fallback = token

    def get_token(self, username: str) -> Optional[str]:
        """Obtiene el token JWT desde el OS o el fallback en memoria."""
        try:
            token = keyring.get_password("sistema_sar_token", username)
            if token:
                return token
        except Exception:
            pass
        return self._token_fallback

    def delete_token(self, username: str) -> None:
        """Remueve el token de sesión guardado."""
        try:
            keyring.delete_password("sistema_sar_token", username)
        except Exception:
            pass
        self._token_fallback = None

    def _get_headers(self, username: Optional[str] = None) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if username:
            token = self.get_token(username)
            if token:
                headers["Authorization"] = f"Bearer {token}"
        return headers

    def request(
        self,
        method: str,
        endpoint: str,
        data: dict = None,
        json: dict = None,
        params: dict = None,
        username: str = None,
        timeout: int = 15,
        **kwargs
    ) -> dict:
        """Realiza peticiones HTTP genéricas con manejo de errores centralizado."""
        url = f"{self.api_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = self._get_headers(username)
        
        # Resolver payloads de forma flexible y retrocompatible
        method_upper = method.upper()
        payload_json = json if json is not None else (data if method_upper in ("POST", "PUT", "DELETE", "PATCH") else None)
        query_params = params if params is not None else (data if method_upper == "GET" else None)
        
        try:
            response = requests.request(
                method=method_upper,
                url=url,
                headers=headers,
                json=payload_json,
                params=query_params,
                timeout=timeout,
                **kwargs
            )

            # Lanzar excepción si hay código de error HTTP
            if response.status_code >= 400:
                try:
                    err_detail = response.json().get("detail", "Error en el servidor")
                except Exception:
                    err_detail = response.text
                raise Exception(f"{response.status_code}: {err_detail}")

            return response.json() if response.content else {}
            
        except requests.exceptions.ConnectionError:
            raise Exception("No se pudo establecer conexión con el Servidor Central API. Verifique su red.")
        except requests.exceptions.Timeout:
            raise Exception("La petición al servidor API excedió el tiempo límite de espera.")
        except Exception as e:
            raise e

