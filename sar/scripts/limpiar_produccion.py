"""Script para limpiar los datos transaccionales, auditoría y archivos PDF de la base de datos de producción de SAR.
Conserva catálogos (municipio, delegación, concepto, rfc, estado_sistema, evento_sistema), seguridad (usuario, rol, permisos, etc.) y configuración (parametros, localizadores).
"""

import sys
import os
from sqlalchemy import text

# Asegurar que el módulo principal esté en el path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sar.src.storage.db_connector import DatabaseConnector

def limpiar_produccion():
    print("Conectando a la base de datos PostgreSQL...")
    db = DatabaseConnector()
    
    # Lista de tablas a truncar y reiniciar sus llaves primarias seriales
    tablas_limpiar = [
        "sar_archivo.lote_detalle",
        "sar_archivo.lote_asignacion",
        "sar_archivo.factura",
        "sar_archivo.archivo_pdf",
        "sar_produccion.referencia",
        "sar_produccion.solicitud",
        "sar_produccion.grupo_referencia",
        "sar_produccion.orden_generacion",
        "sar_auditoria.auditoria_error",
        "sar_auditoria.auditoria_evento",
        "sar_auditoria.auditoria_login",
        "sar_seguridad.sesion"
    ]
    
    # Verificar si se pasó el argumento --yes o -y para saltar la confirmación
    bypass_confirm = len(sys.argv) > 1 and sys.argv[1] in ['--yes', '-y']
    
    try:
        with db.get_session() as session:
            print("\nTablas que se van a limpiar (se reiniciarán los contadores de ID):")
            for tabla in tablas_limpiar:
                print(f" - {tabla}")
                
            if not bypass_confirm:
                confirmacion = input("\n¿Está seguro de que desea limpiar estas tablas? (s/N): ").strip().lower()
                if confirmacion != 's':
                    print("Operación cancelada por el usuario.")
                    return
            else:
                print("\n[Bypass] Ejecutando sin confirmación manual (--yes)...")
            
            print("\nEjecutando limpieza en la base de datos...")
            
            # Construir y ejecutar consulta de truncado
            tablas_str = ", ".join(tablas_limpiar)
            query = text(f"TRUNCATE TABLE {tablas_str} RESTART IDENTITY CASCADE;")
            session.execute(query)
            
            # Confirmar transacción
            session.commit()
            print("¡Éxito! El esquema de producción y las tablas de archivos/auditoría han sido limpiados y reiniciados.")
            
    except Exception as e:
        print(f"\nError al ejecutar la limpieza: {e}")

if __name__ == "__main__":
    limpiar_produccion()
