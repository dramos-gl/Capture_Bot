import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

def migrate_cancelaciones():
    print("Iniciando migración de base de datos para Conceptos de Cancelación y Órdenes Anuales...")
    db = DatabaseConnector()
    
    with db.get_session() as session:
        # 1. Agregar columna es_cancelacion en sar_catalogo.concepto
        session.execute(text("""
            ALTER TABLE sar_catalogo.concepto 
            ADD COLUMN IF NOT EXISTS es_cancelacion BOOLEAN NOT NULL DEFAULT FALSE;
        """))
        session.execute(text("""
            COMMENT ON COLUMN sar_catalogo.concepto.es_cancelacion IS 'Indica si el concepto es de tipo Cancelación';
        """))
        print("Columna sar_catalogo.concepto.es_cancelacion verificada/creada.")

        # 2. Agregar columna tipo_orden en sar_produccion.orden_generacion
        session.execute(text("""
            ALTER TABLE sar_produccion.orden_generacion 
            ADD COLUMN IF NOT EXISTS tipo_orden VARCHAR(30) NOT NULL DEFAULT 'ESTANDAR';
        """))
        session.execute(text("""
            COMMENT ON COLUMN sar_produccion.orden_generacion.tipo_orden IS 'Tipo de orden: ESTANDAR, CANCELACION, etc.';
        """))
        print("Columna sar_produccion.orden_generacion.tipo_orden verificada/creada.")

        # 3. Crear índice para acelerar consultas por tipo_orden
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_orden_generacion_tipo_orden 
            ON sar_produccion.orden_generacion(tipo_orden);
        """))
        print("Índice idx_orden_generacion_tipo_orden verificado/creado.")

        # 4. Insertar concepto de ejemplo para Cancelación si no existe
        session.execute(text("""
            INSERT INTO sar_catalogo.concepto (codigo_portal, nombre, alias, activo, es_cancelacion)
            SELECT 'PORTAL-CNC-01', 'Derecho de Cancelación de Registro', 'CANCELACION', TRUE, TRUE
            WHERE NOT EXISTS (
                SELECT 1 FROM sar_catalogo.concepto WHERE es_cancelacion = TRUE
            );
        """))
        print("Concepto de Cancelación inicial verificado/insertado.")

        session.commit()
        print("¡MIGRACIÓN DE CONCEPTOS DE CANCELACIÓN FINALIZADA CON ÉXITO!")

if __name__ == "__main__":
    migrate_cancelaciones()
