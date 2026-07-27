"""
CancunBot — Conector de Base de Datos
Gestiona la conexión a PostgreSQL usando SQLAlchemy 2.x.
"""
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

from src.services.settings import get_db_url

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def get_engine() -> Engine:
    """Retorna (y cachea) el engine de SQLAlchemy."""
    global _engine
    if _engine is None:
        db_url = get_db_url()
        _engine = create_engine(
            db_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # Verifica conexión antes de usarla
            echo=False
        )
        logger.info("Engine de base de datos inicializado.")
    return _engine


def get_session_factory() -> sessionmaker:
    """Retorna (y cachea) la fábrica de sesiones."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False
        )
    return _SessionLocal


def get_session() -> Session:
    """Crea y retorna una nueva sesión de base de datos.
    
    Uso recomendado:
        with get_session() as session:
            ...
    """
    factory = get_session_factory()
    return factory()


def verificar_conexion() -> bool:
    """Verifica que la conexión a la base de datos esté disponible."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Conexión a db_cancunbot verificada correctamente.")
        return True
    except Exception as e:
        logger.error(f"Error al conectar a db_cancunbot: {e}")
        return False
