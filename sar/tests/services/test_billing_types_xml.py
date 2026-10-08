"""
Prueba Unitaria y de Integración para Validar el Soporte de Tipos de Orden y XML en Facturas.
Regla SAR-AI-PROMPTS-001 / SAR-TEST-001: Ubicado en sar/tests/services/.
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from sar.src.storage.db_connector import DatabaseConnector
from sar.src.storage.models import Factura, Referencia, Solicitud
from sar.src.storage.repositories import OperacionRepository
from sar.src.api.routers.docs_router import RegistrarFacturaBotRequest, registrar_factura_bot
from sqlalchemy import text
import uuid
import datetime

def test_facturacion_types_and_xml():
    print("Iniciando prueba de consistencia: Tipos de orden, xml_path y simetría API...")
    db = DatabaseConnector()
    
    with db.get_session() as session:
        # 1. Verificar existencia de la columna xml_path en el modelo SQLAlchemy
        assert hasattr(Factura, "xml_path"), "El modelo Factura debe tener el atributo xml_path"
        print(" -> [OK] Atributo Factura.xml_path validado en SQLAlchemy.")
        
        # 2. Verificar existencia de un registro de referencia para probar la inserción/actualización
        ref = session.query(Referencia).first()
        if not ref:
            print(" -> [SKIP] No hay referencias en la base de datos para prueba de persistencia end-to-end.")
            return

        ref_id = ref.referencia_id
        sol_id = ref.solicitud_id
        
        # 3. Probar get_solicitud_bot_context
        repo = OperacionRepository(session)
        ctx = repo.get_solicitud_bot_context(sol_id)
        assert "tipo_orden" in ctx, "El contexto del bot debe incluir la clave 'tipo_orden'"
        print(f" -> [OK] get_solicitud_bot_context retorna tipo_orden: '{ctx['tipo_orden']}'.")
        
        # 4. Probar persistencia de factura con xml_path (Simulando llamada de Bot / API)
        # Verificar o crear registro de prueba
        test_pdf = "storage/facturas/2026/ORD_TEST/RFC123/CONCEPTO/12345_CAN1_1.pdf"
        test_xml = "storage/facturas/2026/ORD_TEST/RFC123/CONCEPTO/12345_CAN1.xml"
        
        req = RegistrarFacturaBotRequest(
            referencia_id=ref_id,
            pdf_paths=[test_pdf],
            xml_path=test_xml,
            rfc_emisor="XAXX010101000",
            consecutivo=1,
            solicitud_id=sol_id,
            grupo_id=ctx.get("grupo_id", 1),
            delegacion="Cancun"
        )
        
        # Ejecutar función de router (mismo código que atiende POST /api/docs/facturas/bot)
        registrar_factura_bot(req, db=session)
        session.commit()
        
        # Verificar que el registro en BD tenga xml_path asignado
        factura_db = session.query(Factura).filter(Factura.referencia_id == ref_id).first()
        assert factura_db is not None, "La factura debe existir en sar_archivo.factura"
        assert factura_db.xml_path == test_xml, f"xml_path esperado '{test_xml}', obtenido '{factura_db.xml_path}'"
        print(f" -> [OK] Factura persistida con éxito en BD. xml_path={factura_db.xml_path}")
        
        # Probar caso ESTANDAR (sin xml_path, 2 PDFs) para garantizar CERO REGRESIÓN
        test_pdf_2 = "storage/facturas/2026/ORD_TEST/RFC123/CONCEPTO/12345_CAN1_2.pdf"
        req_estandar = RegistrarFacturaBotRequest(
            referencia_id=ref_id,
            pdf_paths=[test_pdf, test_pdf_2],
            xml_path=None,
            rfc_emisor="XAXX010101000",
            consecutivo=1,
            solicitud_id=sol_id,
            grupo_id=ctx.get("grupo_id", 1),
            delegacion="Cancun"
        )
        registrar_factura_bot(req_estandar, db=session)
        session.commit()
        
        session.refresh(factura_db)
        assert factura_db.pdf2_path == test_pdf_2, "El segundo PDF debe actualizarse correctamente para órdenes estándar"
        print(f" -> [OK] Comportamiento ESTANDAR preservado sin regresión. pdf2_path={factura_db.pdf2_path}")

    print("\n¡TODAS LAS VALIDACIONES DE CONSISTENCIA Y SIMETRÍA PASARON EXITOSAMENTE (0 ERRORES)!")

if __name__ == "__main__":
    test_facturacion_types_and_xml()
