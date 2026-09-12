import os
import sys
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

# Asegurar que el directorio raíz está en el path de Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sar.src.storage.db_connector import DatabaseConnector
from sar.src.api.routers.security_router import router as security_router
from sar.src.api.routers.ops_router import router as ops_router
from sar.src.api.routers.docs_router import router as docs_router
from sar.src.api.routers.admin_router import router as admin_router

app = FastAPI(
    title="SAR - Servidor API",
    description="Backend API REST en FastAPI para el Sistema de Administración de Referencias",
    version="1.0.0"
)

# Configurar middleware de CORS permitiendo orígenes configurables o toda la red local
from sar.src.paths import get_settings_path
import json

cors_origins = ["*"]
try:
    settings_path = get_settings_path()
    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            custom_origins = cfg.get("CORS_ORIGINS")
            if custom_origins and isinstance(custom_origins, list):
                cors_origins = custom_origins
except Exception:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers de endpoints
app.include_router(security_router)
app.include_router(ops_router)
app.include_router(docs_router)
app.include_router(admin_router)

# Inicializar conector de base de datos del servidor
db_connector = DatabaseConnector()

@app.get("/")
def read_root():
    """Endpoint de estado básico para verificar que la API está en línea."""
    return {
        "status": "online",
        "app": "SAR - Servidor API",
        "version": "1.0.0"
    }

@app.get("/health")
def read_health():
    """Endpoint de diagnóstico profundo para validar conectividad con PostgreSQL."""
    import time
    from sqlalchemy import text
    
    t_start = time.perf_counter()
    db_status = "connected"
    db_error = None
    latency_ms = 0.0
    
    try:
        with db_connector.get_session() as session:
            session.execute(text("SELECT 1")).scalar()
        latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
    except Exception as e:
        db_status = "disconnected"
        db_error = str(e)
        latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
        
    return {
        "status": "online" if db_status == "connected" else "degraded",
        "app": "SAR - Servidor API",
        "version": "1.0.0",
        "database": db_status,
        "db_latency_ms": latency_ms,
        "db_error": db_error
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_api:app", host="0.0.0.0", port=8000, reload=True)
