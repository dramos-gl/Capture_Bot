"""Migration script to create missing Foreign Key performance indexes in SAR PostgreSQL Database."""

import sys
from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

INDEX_STATEMENTS = [
    # 1. sar_produccion.referencia -> usuario_asignado (57K+ filas, índice parcial para no indexar nulos)
    (
        "idx_referencia_usuario_asignado",
        "sar_produccion.referencia",
        """
        CREATE INDEX IF NOT EXISTS idx_referencia_usuario_asignado 
        ON sar_produccion.referencia (usuario_asignado) 
        WHERE usuario_asignado IS NOT NULL;
        """
    ),
    # 2. sar_archivo.asignacion_referencia -> usuario_confirmacion (11K+ filas, índice parcial)
    (
        "idx_asignacion_referencia_usuario_confirmacion",
        "sar_archivo.asignacion_referencia",
        """
        CREATE INDEX IF NOT EXISTS idx_asignacion_referencia_usuario_confirmacion 
        ON sar_archivo.asignacion_referencia (usuario_confirmacion) 
        WHERE usuario_confirmacion IS NOT NULL;
        """
    ),
    # 3. sar_produccion.solicitud -> delegacion_id
    (
        "idx_solicitud_delegacion_id",
        "sar_produccion.solicitud",
        """
        CREATE INDEX IF NOT EXISTS idx_solicitud_delegacion_id 
        ON sar_produccion.solicitud (delegacion_id);
        """
    ),
    # 4. sar_produccion.orden_generacion -> municipio_id
    (
        "idx_orden_generacion_municipio_id",
        "sar_produccion.orden_generacion",
        """
        CREATE INDEX IF NOT EXISTS idx_orden_generacion_municipio_id 
        ON sar_produccion.orden_generacion (municipio_id);
        """
    ),
    # 5. sar_produccion.orden_generacion -> estado_id
    (
        "idx_orden_generacion_estado_id",
        "sar_produccion.orden_generacion",
        """
        CREATE INDEX IF NOT EXISTS idx_orden_generacion_estado_id 
        ON sar_produccion.orden_generacion (estado_id);
        """
    ),
    # 6. sar_produccion.orden_generacion -> usuario_id
    (
        "idx_orden_generacion_usuario_id",
        "sar_produccion.orden_generacion",
        """
        CREATE INDEX IF NOT EXISTS idx_orden_generacion_usuario_id 
        ON sar_produccion.orden_generacion (usuario_id);
        """
    ),
    # 7. sar_catalogo.desarrollo_empresa -> delegacion_id
    (
        "idx_desarrollo_empresa_delegacion_id",
        "sar_catalogo.desarrollo_empresa",
        """
        CREATE INDEX IF NOT EXISTS idx_desarrollo_empresa_delegacion_id 
        ON sar_catalogo.desarrollo_empresa (delegacion_id);
        """
    ),
    # 8. sar_seguridad.rol_app_modulo -> app_modulo_id
    (
        "idx_rol_app_modulo_app_modulo_id",
        "sar_seguridad.rol_app_modulo",
        """
        CREATE INDEX IF NOT EXISTS idx_rol_app_modulo_app_modulo_id 
        ON sar_seguridad.rol_app_modulo (app_modulo_id);
        """
    )
]

def run_migration():
    print("Iniciando migración de índices de optimización FK en SAR...")
    db = DatabaseConnector()
    created_count = 0
    with db.get_session() as session:
        for idx_name, table_name, sql in INDEX_STATEMENTS:
            try:
                print(f"Creando índice '{idx_name}' en {table_name}...")
                session.execute(text(sql))
                session.commit()
                created_count += 1
                print(f"  -> Índice '{idx_name}' integrado exitosamente.")
            except Exception as e:
                session.rollback()
                print(f"  -> Error al crear '{idx_name}': {e}", file=sys.stderr)
                raise e
    print(f"\nMigración finalizada. Se integraron {created_count} índices correctamente.")

if __name__ == "__main__":
    run_migration()
