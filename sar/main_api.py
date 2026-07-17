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

# Configurar middleware de CORS para permitir conexiones desde la red local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_api:app", host="0.0.0.0", port=8000, reload=True)
