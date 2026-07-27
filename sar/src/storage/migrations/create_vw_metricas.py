"""Script para crear/actualizar la vista vw_metricas_referencias en la base de datos."""
import sys
import os

# Asegurar que el proyecto esté en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

SQL_CREATE_VIEW = """
CREATE OR REPLACE VIEW sar_produccion.vw_metricas_referencias AS
SELECT
    r.referencia_id,
    r.grupo_id,
    r.solicitud_id,
    r.importe,
    r.fecha_generacion,
    gr.orden_id,
    og.folio                    AS folio_orden,
    gr.rfc_id,
    rfc.rfc                     AS rfc_nombre,
    rfc.razon_social            AS rfc_razon_social,
    gr.concepto_id,
    c.nombre                    AS concepto_nombre,
    s.delegacion_id,
    d.nombre                    AS delegacion_nombre,
    es.codigo                   AS estado_codigo,
    es.descripcion              AS estado_descripcion
FROM sar_produccion.referencia r
JOIN sar_produccion.grupo_referencia gr  ON r.grupo_id       = gr.grupo_id
JOIN sar_produccion.orden_generacion og  ON gr.orden_id      = og.orden_id
JOIN sar_produccion.solicitud s          ON r.solicitud_id   = s.solicitud_id
JOIN sar_catalogo.rfc rfc                ON gr.rfc_id        = rfc.rfc_id
JOIN sar_catalogo.concepto c             ON gr.concepto_id   = c.concepto_id
LEFT JOIN sar_catalogo.delegacion d      ON s.delegacion_id  = d.delegacion_id
JOIN sar_catalogo.estado_sistema es      ON r.estado_id      = es.estado_id;
"""

def main():
    print("Conectando a la base de datos...")
    try:
        connector = DatabaseConnector()
        with connector.engine.connect() as conn:
            conn.execute(text(SQL_CREATE_VIEW))
            conn.commit()
        print("[OK] Vista 'sar_produccion.vw_metricas_referencias' creada/actualizada correctamente.")
    except Exception as e:
        print(f"[ERROR] Al crear la vista: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
