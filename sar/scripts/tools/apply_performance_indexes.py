"""Script de aplicación segura e idempotente de índices de rendimiento para SAR.
Ejecuta los 6 índices B-Tree propuestos y verifica su existencia en pg_indexes.
"""

import sys
from sqlalchemy import text
from sar.src.storage.db_connector import DatabaseConnector

INDEXES_TO_APPLY = [
    (
        "idx_orden_generacion_fecha",
        "sar_produccion",
        "orden_generacion",
        "CREATE INDEX IF NOT EXISTS idx_orden_generacion_fecha ON sar_produccion.orden_generacion (fecha_creacion DESC);"
    ),
    (
        "idx_grupo_referencia_rfc_id",
        "sar_produccion",
        "grupo_referencia",
        "CREATE INDEX IF NOT EXISTS idx_grupo_referencia_rfc_id ON sar_produccion.grupo_referencia (rfc_id);"
    ),
    (
        "idx_grupo_referencia_concepto_id",
        "sar_produccion",
        "grupo_referencia",
        "CREATE INDEX IF NOT EXISTS idx_grupo_referencia_concepto_id ON sar_produccion.grupo_referencia (concepto_id);"
    ),
    (
        "idx_referencia_estado_fecha",
        "sar_produccion",
        "referencia",
        "CREATE INDEX IF NOT EXISTS idx_referencia_estado_fecha ON sar_produccion.referencia (estado_id, fecha_generacion DESC, referencia_id DESC);"
    ),
    (
        "idx_lote_asignacion_destino_fecha",
        "sar_archivo",
        "lote_asignacion",
        "CREATE INDEX IF NOT EXISTS idx_lote_asignacion_destino_fecha ON sar_archivo.lote_asignacion (tipo_destino, fecha DESC);"
    ),
    (
        "idx_lote_detalle_concepto_id",
        "sar_archivo",
        "lote_detalle",
        "CREATE INDEX IF NOT EXISTS idx_lote_detalle_concepto_id ON sar_archivo.lote_detalle (concepto_id);"
    ),
]


def apply_indexes():
    print("Iniciando conexión a PostgreSQL...")
    connector = DatabaseConnector()
    
    with connector.engine.connect() as conn:
        trans = conn.begin()
        try:
            for idx_name, schema, table, ddl in INDEXES_TO_APPLY:
                print(f"Aplicando índice: {idx_name} en {schema}.{table}...")
                conn.execute(text(ddl))
            trans.commit()
            print("Todos los índices fueron procesados exitosamente.")
        except Exception as e:
            trans.rollback()
            print(f"Error al aplicar índices: {e}")
            sys.exit(1)

    # Verificación en catálogo del sistema
    print("\n--- Verificación en pg_indexes ---")
    with connector.engine.connect() as conn:
        for idx_name, schema, table, _ in INDEXES_TO_APPLY:
            query = text("""
                SELECT schemaname, tablename, indexname 
                FROM pg_indexes 
                WHERE schemaname = :schema AND indexname = :idx_name;
            """)
            row = conn.execute(query, {"schema": schema, "idx_name": idx_name}).first()
            if row:
                print(f"  [OK] {row.schemaname}.{row.tablename} -> {row.indexname}")
            else:
                print(f"  [AVISO] No se encontró {schema}.{idx_name} en pg_indexes.")


if __name__ == "__main__":
    apply_indexes()
