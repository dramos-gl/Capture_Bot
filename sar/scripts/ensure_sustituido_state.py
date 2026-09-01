import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import sar.src.storage.db_connector as dbc
from sqlalchemy import text

def ensure_sustituido_state():
    db = dbc.DatabaseConnector()
    with db.get_session() as s:
        res = s.execute(text("SELECT estado_id, entidad, codigo, descripcion FROM sar_catalogo.estado_sistema WHERE codigo = 'SUSTITUIDO'")).fetchall()
        print('Current SUSTITUIDO entries:', res)
        if not res:
            max_id = s.execute(text("SELECT COALESCE(MAX(estado_id), 90) FROM sar_catalogo.estado_sistema")).scalar()
            new_id = max_id + 1
            print(f"Creating SUSTITUIDO with ID {new_id}...")
            s.execute(
                text("INSERT INTO sar_catalogo.estado_sistema (estado_id, entidad, codigo, descripcion) VALUES (:id, :entidad, :codigo, :desc)"),
                {"id": new_id, "entidad": "asignacion_referencia", "codigo": "SUSTITUIDO", "desc": "Asignación sustituida por un nuevo intento para la misma ubicación"}
            )
            s.commit()
            print("Successfully inserted SUSTITUIDO!")
        else:
            print("State SUSTITUIDO already exists.")

if __name__ == "__main__":
    ensure_sustituido_state()
