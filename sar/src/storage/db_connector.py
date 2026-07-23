"""Database connector for PostgreSQL using SQLAlchemy."""

import os
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sar.src.storage.models import Base


class DatabaseConnector:
    """Manages the database connection and session lifecycle."""

    def __init__(self):
        # Intentar cargar variables desde settings.json si existe
        import json
        from sar.src.paths import get_settings_path
        
        settings_path = get_settings_path()
        settings_data = {}
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings_data = json.load(f)
            except Exception as e:
                print(f"Advertencia: No se pudo cargar settings.json: {e}")

        self.db_user = os.getenv("DB_USER") or settings_data.get("DB_USER", "postgres")
        self.db_password = os.getenv("DB_PASSWORD") or settings_data.get("DB_PASSWORD", "")
        self.db_host = os.getenv("DB_HOST") or settings_data.get("DB_HOST", "localhost")
        self.db_port = os.getenv("DB_PORT") or settings_data.get("DB_PORT", "5432")
        self.db_name = os.getenv("DB_NAME") or settings_data.get("DB_NAME", "db_sar")

        # Construir URL de conexión para PostgreSQL usando psycopg2
        self.database_url = (
            f"postgresql://{self.db_user}:{self.db_password}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )

        # Crear el motor de base de datos
        # pool_pre_ping=True verifica que la conexión siga viva antes de usarla
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,
            echo=False  # Cambiar a True para debuguear SQL generado en desarrollo
        )

        # Crear fábrica de sesiones
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False
        )

    def create_tables(self) -> None:
        """Utility method to create tables if they do not exist (mainly for dev/tests)."""
        Base.metadata.create_all(bind=self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Provides a transactional scope around a series of operations."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
