import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

# Force postgres owner user for DDL migrations
os.environ["DB_USER"] = "postgres"
if "DB_PASSWORD" not in os.environ:
    os.environ["DB_PASSWORD"] = "postgres"

from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

def migrate_fojas_testimonios():
    print("Iniciando migración para Fojas y Testimonios...")
    db = DatabaseConnector()
    with db.get_session() as session:
        # 1. Agregar columna tipo_modulo a sar_catalogo.concepto
        try:
            session.execute(text("""
                ALTER TABLE sar_catalogo.concepto 
                ADD COLUMN IF NOT EXISTS tipo_modulo VARCHAR(30) NOT NULL DEFAULT 'ESTANDAR';
            """))
            session.commit()
            print("Columna sar_catalogo.concepto.tipo_modulo verificada/creada.")
        except Exception as e:
            session.rollback()
            print(f"Aviso DDL tipo_modulo (requiere superusuario o ya existe): {e}")

        # 2. Agregar columna cantidad_actos a sar_produccion.solicitud
        try:
            session.execute(text("""
                ALTER TABLE sar_produccion.solicitud 
                ADD COLUMN IF NOT EXISTS cantidad_actos INTEGER NOT NULL DEFAULT 1;
            """))
            session.commit()
            print("Columna sar_produccion.solicitud.cantidad_actos verificada/creada.")
        except Exception as e:
            session.rollback()
            print(f"Aviso DDL cantidad_actos (requiere superusuario o ya existe): {e}")

        # 3. Actualizar conceptos 4, 5 y 6 con sus respectivos tipos de módulo y asegurar activo = TRUE
        session.execute(text("""
            UPDATE sar_catalogo.concepto SET tipo_modulo = 'ESTANDAR' WHERE concepto_id IN (1, 2, 3);
            UPDATE sar_catalogo.concepto SET tipo_modulo = 'CANCELACION' WHERE concepto_id = 4;
            
            -- Asegurar existencia y activación de concepto 5 (Fojas)
            INSERT INTO sar_catalogo.concepto (concepto_id, codigo_portal, nombre, alias, activo, es_cancelacion, tipo_modulo)
            VALUES (5, 'PORTAL-FOJAS-01', '5. Derechos de Fojas', 'FOJAS', TRUE, FALSE, 'FOJAS')
            ON CONFLICT (concepto_id) DO UPDATE SET 
                activo = TRUE, 
                tipo_modulo = 'FOJAS',
                nombre = '5. Derechos de Fojas';

            -- Asegurar existencia y activación de concepto 6 (Testimonios)
            INSERT INTO sar_catalogo.concepto (concepto_id, codigo_portal, nombre, alias, activo, es_cancelacion, tipo_modulo)
            VALUES (6, 'PORTAL-TESTIMONIO-01', '6. Expedición de Testimonios', 'TESTIMONIO', TRUE, FALSE, 'TESTIMONIO')
            ON CONFLICT (concepto_id) DO UPDATE SET 
                activo = TRUE, 
                tipo_modulo = 'TESTIMONIO',
                nombre = '6. Expedición de Testimonios';
        """))
        print("Conceptos 5 y 6 actualizados/insertados y activos.")

        # 4. Insertar semilla en localizador_portal para el campo multiplicar136
        session.execute(text("""
            INSERT INTO sar_configuracion.localizador_portal 
            (nombre_clave, label_visible, estrategia_selector, valor_selector, descripcion, portal) 
            VALUES
            ('txtCantidadMultiplicar136', 'Cantidad Multiplicador (Detalle 136)', 'CSS', 'input.multiplicar136', 'Campo de cantidad multiplicadora para conceptos en Tributanet', 'SAR')
            ON CONFLICT (nombre_clave) DO NOTHING;
        """))
        print("Semilla localizador_portal 'txtCantidadMultiplicar136' verificada/insertada.")

        # 5. Insertar semilla en parametro_sistema para la URL del Grupo 71
        session.execute(text("""
            INSERT INTO sar_configuracion.parametro_sistema 
            (codigo, valor, descripcion) 
            VALUES
            ('TRIBUTANET_GRUPO71_URL', 'https://shacienda.qroo.gob.mx/tributanet/contribucion/dec_contribucion_control.php?Grupo=71', 'URL directa al formulario de contribuciones Grupo 71 de Tributanet (Fase A)')
            ON CONFLICT (codigo) DO NOTHING;
        """))
        print("Semilla parametro_sistema 'TRIBUTANET_GRUPO71_URL' verificada/insertada.")

        session.commit()
        print("¡MIGRACIÓN DE FOJAS Y TESTIMONIOS FINALIZADA CON ÉXITO!")

if __name__ == "__main__":
    migrate_fojas_testimonios()
