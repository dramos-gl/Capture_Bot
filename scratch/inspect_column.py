from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

db = DatabaseConnector()
with db.get_session() as session:
    res = session.execute(text("""
        SELECT column_name, column_default, is_identity, identity_generation, identity_start
        FROM information_schema.columns 
        WHERE table_schema = 'sar_produccion' 
          AND table_name = 'referencia' 
          AND column_name = 'referencia_id';
    """)).first()
    print("Column definition:", res)
    
    # Check what seq pg_get_serial_sequence returns
    seq_name = session.execute(text("SELECT pg_get_serial_sequence('sar_produccion.referencia', 'referencia_id')")).scalar()
    print("pg_get_serial_sequence returns:", seq_name)
    
    # Check all sequences in schema sar_produccion
    seqs = session.execute(text("""
        SELECT sequence_name 
        FROM information_schema.sequences 
        WHERE sequence_schema = 'sar_produccion';
    """)).fetchall()
    print("Sequences in sar_produccion:", seqs)
