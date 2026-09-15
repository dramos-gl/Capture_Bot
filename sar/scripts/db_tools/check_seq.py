from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

db = DatabaseConnector()
with db.get_session() as session:
    max_id = session.execute(text('SELECT MAX(referencia_id) FROM sar_produccion.referencia')).scalar()
    seq_name = session.execute(text("SELECT pg_get_serial_sequence('sar_produccion.referencia', 'referencia_id')")).scalar()
    
    print("Max ID:", max_id)
    print("Sequence Name:", seq_name)
    
    if seq_name:
        curr_val = session.execute(text(f"SELECT last_value, is_called FROM {seq_name}")).first()
        print("Sequence current state (last_value, is_called):", curr_val)
