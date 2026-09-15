from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

db = DatabaseConnector()
with db.get_session() as session:
    # Query pg_depend to see what sequence is owned by the column
    res = session.execute(text("""
        SELECT d.refobjid::regclass AS table_name, a.attname AS column_name, c.relname AS sequence_name
        FROM pg_depend d
        JOIN pg_attribute a ON a.attrelid = d.refobjid AND a.attnum = d.refobjsubid
        JOIN pg_class c ON c.oid = d.objid
        WHERE d.refclassid = 'pg_class'::regclass
          AND d.classid = 'pg_class'::regclass
          AND c.relkind = 'S'
          AND d.refobjid = 'sar_produccion.referencia'::regclass;
    """)).fetchall()
    print("Dependencies for sar_produccion.referencia:")
    for row in res:
        print(row)
        
    # Check the nextval of the sequence directly
    try:
        next_val_direct = session.execute(text("SELECT nextval('sar_produccion.referencia_referencia_id_seq')")).scalar()
        print("nextval('sar_produccion.referencia_referencia_id_seq') directly returned:", next_val_direct)
    except Exception as e:
        print("Error getting nextval:", e)
