import sys
import os
from sqlalchemy import text

# Ensure root dir is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sar.src.storage.db_connector import DatabaseConnector

def run_migration():
    print("Iniciando migración de localizadores...")
    db = DatabaseConnector()
    
    try:
        with db.get_session() as session:
            insert_query = text("""
                INSERT INTO sar_configuracion.localizador_portal (nombre_clave, label_visible, estrategia_selector, valor_selector, descripcion) VALUES
                ('txtMunicipioRfc', 'Municipio del RFC', 'CSS', 'input#mun', 'Campo para el municipio del RFC en el formulario principal RPP'),
                ('txtEstadoRfc', 'Estado del RFC', 'CSS', 'input#Estado', 'Campo para la entidad federativa / estado del RFC en el formulario principal RPP')
                ON CONFLICT (nombre_clave) DO UPDATE SET
                    valor_selector = EXCLUDED.valor_selector,
                    descripcion = EXCLUDED.descripcion;
            """)
            session.execute(insert_query)
            session.commit()
            print("¡Localizadores txtMunicipioRfc y txtEstadoRfc registrados exitosamente!")
    except Exception as e:
        print(f"Error ejecutando migración: {str(e)}")

if __name__ == "__main__":
    run_migration()
