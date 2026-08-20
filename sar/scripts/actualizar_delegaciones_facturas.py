#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de ejecución manual para actualizar el campo 'delegacion' en la tabla sar_archivo.factura.
Analiza registros que tengan el campo 'delegacion' vacío (nulo o cadena vacía), examina los PDFs
asociados (pdf_path y pdf2_path) usando pypdf, y extrae la delegación correspondiente (Cancun o Playa del Carmen).
"""

import sys
import os
from sqlalchemy import text

# Asegurar que el directorio raíz del proyecto esté en el path
# Desde /sar/scripts/actualizar_delegaciones_facturas.py, ir dos niveles hacia atrás nos da la raíz del proyecto
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


from sar.src.storage.db_connector import DatabaseConnector

def extract_delegacion_from_pdf(pdf_path: str) -> str:
    """Intenta extraer la delegación del texto de un PDF."""
    if not pdf_path or not os.path.exists(pdf_path):
        return None
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            text_content = page.extract_text()
            if text_content:
                text_lower = text_content.lower()
                if "delegación cancun" in text_lower or "delegacion cancun" in text_lower:
                    return "Cancun"
                elif "delegación playa del carmen" in text_lower or "delegacion playa del carmen" in text_lower:
                    return "Playa del Carmen"
                elif "delegación chetumal" in text_lower or "delegacion chetumal" in text_lower:
                    return "Chetumal"
    except Exception as e:
        print(f"  [Advertencia] Error al leer {pdf_path}: {e}")
    return None

def main():
    print("=== Iniciando Actualización Manual de Delegaciones en Facturas ===")
    db = DatabaseConnector()
    
    try:
        with db.get_session() as session:
            # Obtener todas las facturas con delegación vacía o nula
            query = text("""
                SELECT factura_id, pdf_path, pdf2_path, uuid, folio
                FROM sar_archivo.factura
                WHERE delegacion IS NULL OR delegacion = ''
            """)
            
            facturas = session.execute(query).all()
            total_facturas = len(facturas)
            print(f"Se encontraron {total_facturas} facturas con el campo 'delegacion' vacío.")
            
            if total_facturas == 0:
                print("No hay facturas pendientes por actualizar.")
                return

            actualizados = 0
            no_encontrados = 0
            no_legibles = 0

            for i, row in enumerate(facturas, 1):
                factura_id = row.factura_id
                pdf_path = row.pdf_path
                pdf2_path = row.pdf2_path
                folio = row.folio or row.uuid
                
                print(f"[{i}/{total_facturas}] Procesando Factura ID: {factura_id} (Folio/UUID: {folio})")
                
                delegacion = None
                
                # Intentar primero con pdf_path
                if pdf_path:
                    delegacion = extract_delegacion_from_pdf(pdf_path)
                    if delegacion:
                        print(f"  -> Encontrada delegación '{delegacion}' en pdf_path: {pdf_path}")
                
                # Si no se encontró, intentar con pdf2_path
                if not delegacion and pdf2_path:
                    delegacion = extract_delegacion_from_pdf(pdf2_path)
                    if delegacion:
                        print(f"  -> Encontrada delegación '{delegacion}' en pdf2_path: {pdf2_path}")
                
                if delegacion:
                    # Actualizar en la base de datos
                    update_query = text("""
                        UPDATE sar_archivo.factura
                        SET delegacion = :delegacion
                        WHERE factura_id = :factura_id
                    """)
                    session.execute(update_query, {"delegacion": delegacion, "factura_id": factura_id})
                    actualizados += 1
                else:
                    # Reportar por qué falló
                    path_exists_1 = os.path.exists(pdf_path) if pdf_path else False
                    path_exists_2 = os.path.exists(pdf2_path) if pdf2_path else False
                    
                    if not path_exists_1 and not path_exists_2:
                        print(f"  [Error] Los archivos PDF no existen físicamente en las rutas indicadas.")
                        no_encontrados += 1
                    else:
                        print(f"  [Error] No se encontró el texto de delegación en los archivos PDF existentes.")
                        no_legibles += 1
            
            # Guardar cambios
            session.commit()
            print("\n=== Resumen del Proceso ===")
            print(f"Total procesadas: {total_facturas}")
            print(f"Actualizadas exitosamente: {actualizados}")
            print(f"Error: PDFs no existen físicamente: {no_encontrados}")
            print(f"Error: Texto de delegación no encontrado en el PDF: {no_legibles}")
            
    except Exception as e:
        print(f"Ocurrió un error general durante el proceso: {e}")

if __name__ == "__main__":
    main()
