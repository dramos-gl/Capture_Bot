"""
Migración Segura e Idempotente para Soporte de XML en Facturas de BOT_FACE_C.
1. Agrega columna 'xml_path' (VARCHAR 1000) en 'sar_archivo.factura' si no existe.
2. Agrega o actualiza el localizador 'btn_xml' en 'sar_configuracion.localizador_portal'.
Tolerancia de error: 0. Idempotente y no destructivo.
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

# Forzar usuario postgres (owner de las tablas) para migraciones DDL
os.environ["DB_USER"] = "postgres"
if "DB_PASSWORD" not in os.environ:
    os.environ["DB_PASSWORD"] = "postgres"

from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

def migrate_facturacion_xml():
    print("Iniciando migración segura para soporte de XML en BOT_FACE_C...")
    db = DatabaseConnector()
    
    with db.get_session() as session:
        # 1. Agregar columna xml_path en sar_archivo.factura si no existe
        session.execute(text("""
            ALTER TABLE sar_archivo.factura 
            ADD COLUMN IF NOT EXISTS xml_path VARCHAR(1000);
        """))
        session.execute(text("""
            COMMENT ON COLUMN sar_archivo.factura.xml_path IS 'Ruta absoluta o UNC del archivo XML CFDI timbrado';
        """))
        print(" -> Columna sar_archivo.factura.xml_path verificada/creada.")

        # 2. Insertar / Actualizar localizador dinámico para botón XML en sar_configuracion.localizador_portal
        session.execute(text("""
            INSERT INTO sar_configuracion.localizador_portal (
                nombre_clave,
                label_visible,
                estrategia_selector,
                valor_selector,
                descripcion,
                portal
            ) VALUES (
                'btn_xml',
                'Botón Descargar XML Factura',
                'CSS',
                'a:has-text("XML"), a[href*="tipo=xml"]',
                'Enlace para descargar el archivo XML del CFDI timbrado en el portal SATQ',
                'SAR'
            )
            ON CONFLICT (nombre_clave) DO UPDATE 
            SET valor_selector = EXCLUDED.valor_selector,
                descripcion    = EXCLUDED.descripcion;
        """))
        print(" -> Localizador 'btn_xml' en sar_configuracion.localizador_portal verificado/actualizado.")

        session.commit()
        print("¡MIGRACIÓN DE SOPORTE XML FINALIZADA CON ÉXITO Y CERO IMPACTO EN DATOS EXISTENTES!")

if __name__ == "__main__":
    migrate_facturacion_xml()
