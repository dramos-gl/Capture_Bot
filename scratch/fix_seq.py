import os
import sys

# Ensure the root dir is in Python path when run from scratch/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

def fix_sequences():
    db = DatabaseConnector()
    queries = [
        "SELECT setval('sar_seguridad.usuario_usuario_id_seq', COALESCE((SELECT MAX(usuario_id) FROM sar_seguridad.usuario), 1), true);",
        "SELECT setval('sar_seguridad.rol_rol_id_seq', COALESCE((SELECT MAX(rol_id) FROM sar_seguridad.rol), 1), true);",
        "SELECT setval('sar_seguridad.modulo_modulo_id_seq', COALESCE((SELECT MAX(modulo_id) FROM sar_seguridad.modulo), 1), true);",
        "SELECT setval('sar_seguridad.accion_accion_id_seq', COALESCE((SELECT MAX(accion_id) FROM sar_seguridad.accion), 1), true);",
        "SELECT setval('sar_catalogo.rfc_rfc_id_seq', COALESCE((SELECT MAX(rfc_id) FROM sar_catalogo.rfc), 1), true);",
        "SELECT setval('sar_catalogo.concepto_concepto_id_seq', COALESCE((SELECT MAX(concepto_id) FROM sar_catalogo.concepto), 1), true);",
        "SELECT setval('sar_catalogo.municipio_municipio_id_seq', COALESCE((SELECT MAX(municipio_id) FROM sar_catalogo.municipio), 1), true);",
        "SELECT setval('sar_catalogo.delegacion_delegacion_id_seq', COALESCE((SELECT MAX(delegacion_id) FROM sar_catalogo.delegacion), 1), true);"
    ]
    for q in queries:
        with db.get_session() as session:
            try:
                session.execute(text(q))
                session.commit()
            except Exception as e:
                print(f"Failed to execute: {q} \nError: {e}")
                session.rollback()
    print("Sequences fixed.")

if __name__ == '__main__':
    fix_sequences()
