from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

db = DatabaseConnector()
with db.get_session() as session:
    # Let's find all dependencies in pg_depend where refobjid is a table and objid is a sequence
    # and see if there are multiple sequences for the same column.
    query = text("""
        SELECT 
            ns.nspname AS schema_name,
            t.relname AS table_name,
            a.attname AS column_name,
            s.relname AS sequence_name,
            d.deptype
        FROM pg_depend d
        JOIN pg_class t ON t.oid = d.refobjid
        JOIN pg_namespace ns ON ns.oid = t.relnamespace
        JOIN pg_attribute a ON a.attrelid = d.refobjid AND a.attnum = d.refobjsubid
        JOIN pg_class s ON s.oid = d.objid
        WHERE d.refclassid = 'pg_class'::regclass
          AND d.classid = 'pg_class'::regclass
          AND s.relkind = 'S'
          AND ns.nspname IN ('sar_seguridad', 'sar_catalogo', 'sar_produccion', 'sar_archivo', 'sar_auditoria', 'sar_configuracion');
    """)
    
    dependencies = session.execute(query).fetchall()
    
    # We will group sequences by table + column
    grouped = {}
    for row in dependencies:
        key = (row.schema_name, row.table_name, row.column_name)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append((row.sequence_name, row.deptype))
        
    print("Found dependencies:")
    for key, seqs in grouped.items():
        print(f"{key[0]}.{key[1]} ({key[2]}): {seqs}")
        if len(seqs) > 1:
            # We have duplicates! Let's find which one is the IDENTITY sequence.
            # In PostgreSQL, the identity column sequence is internally dependent ('i').
            # The old serial sequence is usually auto ('a') or has another dependency.
            # Let's inspect which one is 'i'.
            identity_seq = None
            old_seqs = []
            for seq_name, deptype in seqs:
                if deptype == 'i':
                    identity_seq = seq_name
                else:
                    old_seqs.append(seq_name)
            
            print(f"  -> IDENTITY Sequence: {identity_seq}")
            print(f"  -> Old Sequence(s) to drop: {old_seqs}")
            
            # If we have an identity sequence, we should:
            # 1. Update the identity sequence to the correct value (MAX + 1)
            # 2. Drop the old sequence(s)
            if identity_seq:
                table_fullname = f"{key[0]}.{key[1]}"
                col_name = key[2]
                
                # Get max val
                max_val = session.execute(text(f"SELECT COALESCE(MAX({col_name}), 0) FROM {table_fullname}")).scalar()
                print(f"  -> Syncing {key[0]}.{identity_seq} to MAX({col_name}) = {max_val}...")
                session.execute(text(f"SELECT setval('{key[0]}.{identity_seq}', {max_val + 1}, false)"))
                
                for old_seq in old_seqs:
                    print(f"  -> Dropping old sequence {key[0]}.{old_seq}...")
                    session.execute(text(f"DROP SEQUENCE IF EXISTS {key[0]}.{old_seq} CASCADE"))
            print("-" * 50)
        else:
            # Only one sequence. Let's make sure it's synced.
            table_fullname = f"{key[0]}.{key[1]}"
            col_name = key[2]
            seq_name = seqs[0][0]
            max_val = session.execute(text(f"SELECT COALESCE(MAX({col_name}), 0) FROM {table_fullname}")).scalar()
            print(f"  -> Syncing {key[0]}.{seq_name} to MAX({col_name}) = {max_val}...")
            session.execute(text(f"SELECT setval('{key[0]}.{seq_name}', {max_val + 1}, false)"))
            print("-" * 50)
            
    session.commit()
    print("Cleanup and synchronization completed successfully!")
