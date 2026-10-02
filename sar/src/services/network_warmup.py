"""Network Warmup Worker to pre-establish TCP connections in background without blocking UI."""

from PySide6.QtCore import QThread, Signal

class NetworkWarmupWorker(QThread):
    """Background worker thread that quietly warms TCP connection / Connection Pools for API or Postgres DB.
    Guaranteed Fail-Safe: any network timeouts or errors are swallowed silently.
    """
    finished_signal = Signal(bool)

    def __init__(self, db_connector=None, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector

    def run(self):
        try:
            from sar.src.storage.api_client import APIClient
            api_client = APIClient()

            if api_client.connect_via_api:
                # Pre-warm HTTP Keep-Alive connection pool to FastAPI backend
                api_client.request("GET", "/api/auth/modules", timeout=3)
            else:
                # Pre-warm PostgreSQL TCP connection pool
                if self.db_connector:
                    with self.db_connector.get_session() as session:
                        from sqlalchemy import text
                        session.execute(text("SELECT 1")).scalar()
            self.finished_signal.emit(True)
        except Exception as e:
            # Quiet Fail-Safe: Never bubble errors to user if background warmup fails
            self.finished_signal.emit(False)
