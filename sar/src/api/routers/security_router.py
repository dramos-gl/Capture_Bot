import jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sar.src.storage.db_connector import DatabaseConnector
from sar.src.services.security_service import SecurityService

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Inicializar un conector de BD local para la dependencia de sesión
db_connector = DatabaseConnector()

# Configuración básica de JWT
SECRET_KEY = "sar_api_secure_fallback_secret_key_2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 horas según recomendación SEC-001

class LoginRequest(BaseModel):
    username: str
    password: str
    ip_equipo: Optional[str] = "127.0.0.1"
    equipo_nombre: Optional[str] = "Cliente LAN"
    equipo_uuid: Optional[str] = "lan-uuid"

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    usuario_id: int
    username: str
    sesion_id: int
    roles: list[str]

class LogoutRequest(BaseModel):
    sesion_id: int

class ModuleInfo(BaseModel):
    nombre: str
    codigo: str

def get_db():
    """Dependencia para inyectar la sesión de base de datos transaccional."""
    with db_connector.get_session() as session:
        yield session

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Genera un token JWT firmado de corta duración."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.get("/modules", response_model=list[ModuleInfo])
def get_active_modules(db: Session = Depends(get_db)):
    """Retorna los módulos de aplicación activos del sistema."""
    from sar.src.storage.repositories import UsuarioRepository
    repo = UsuarioRepository(db)
    modulos = repo.get_all_app_modulos()
    return [{"nombre": mod.nombre, "codigo": mod.codigo} for mod in modulos]

@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Verifica credenciales del usuario, crea sesión y retorna el JWT token."""
    security_service = SecurityService(db)
    
    # Autenticar mediante el servicio actual
    sesion_obj = security_service.login(
        username=request.username,
        password_raw=request.password,
        ip_equipo=request.ip_equipo,
        equipo_nombre=request.equipo_nombre,
        equipo_uuid=request.equipo_uuid
    )
    
    if not sesion_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas o usuario inactivo",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Obtener roles del usuario
    user = sesion_obj.usuario
    roles_list = [rol.codigo for rol in user.roles]
    
    # Crear token JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {
        "sub": user.username,
        "usuario_id": user.usuario_id,
        "sesion_id": sesion_obj.sesion_id,
        "roles": roles_list
    }
    
    token = create_access_token(data=token_data, expires_delta=access_token_expires)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario_id": user.usuario_id,
        "username": user.username,
        "sesion_id": sesion_obj.sesion_id,
        "roles": roles_list
    }

@router.post("/logout")
def logout(request: LogoutRequest, db: Session = Depends(get_db)):
    """Cierra la sesión del usuario en la base de datos."""
    security_service = SecurityService(db)
    try:
        security_service.logout(request.sesion_id)
        return {"detail": "Sesión cerrada correctamente"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al cerrar la sesión: {str(e)}"
        )

@router.get("/module-access/{usuario_id}/{module_code}")
def check_module_access(usuario_id: int, module_code: str, db: Session = Depends(get_db)):
    """Verifica si el usuario tiene acceso al módulo de aplicación especificado."""
    security_service = SecurityService(db)
    has_access = security_service.has_app_module_access(usuario_id, module_code)
    return {"has_access": bool(has_access)}
