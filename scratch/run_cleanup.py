import sys
import os
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sar.src.storage.db_connector import DatabaseConnector

def run_cleanup():
    sql_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../sar/scripts/limpiar_produccion.sql"))
    print(f"Reading SQL script from: {sql_path}")
    
    if not os.path.exists(sql_path):
        print("SQL script file not found!")
        return

    with open(sql_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    db = DatabaseConnector()
    print(f"Connecting to database: {db.db_name} on {db.db_host}...")
    
    # We will run the raw SQL query. Since SQLAlchemy expects text, we can execute the script.
    # Note: postgresql doesn't always support executing multiple statements via a single execute block
    # unless using the raw connection, or we can execute the commands within a transaction block.
    try:
        with db.engine.connect() as connection:
            with connection.begin() as transaction:
                # We can execute the raw SQL text
                connection.execute(text(sql_content))
                print("Database tables truncated successfully!")
    except Exception as e:
        print(f"An error occurred while executing the SQL script: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_cleanup()
