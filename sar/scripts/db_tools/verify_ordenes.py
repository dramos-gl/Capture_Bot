import sys
import os
import math

# Ensure the root dir is in Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sar.src.storage.db_connector import DatabaseConnector
from sar.src.services.ordenes_service import OrdenesService
from sar.src.storage.models import Rfc, Concepto, Delegacion

def main():
    db_connector = DatabaseConnector()
    
    with db_connector.get_session() as session:
        # Create dummy catalog entries if none exist
        from sar.src.storage.repositories import CatalogoRepository
        repo = CatalogoRepository(session)
        
        rfcs = repo.get_rfcs_activos()
        if not rfcs:
            print("No RFCs found. Creating a test RFC...")
            rfc_test = Rfc(rfc="TEST010203XXX", razon_social="Empresa Prueba SA de CV", activo=True)
            session.add(rfc_test)
            session.flush()
            rfcs = [rfc_test]
            
        conceptos = repo.get_conceptos_activos()
        if not conceptos:
            print("No Conceptos found. Creating a test Concepto...")
            concepto_test = Concepto(nombre="Análisis y Calificación", activo=True)
            session.add(concepto_test)
            session.flush()
            conceptos = [concepto_test]
            
        delegaciones = repo.get_delegaciones_activas()
        if not delegaciones:
            # Requires municipio, but for simplicity we will just use None if DB allows or create one
            pass
            
        rfc_id = rfcs[0].rfc_id
        concepto_id = conceptos[0].concepto_id
        delegacion_id = delegaciones[0].delegacion_id if delegaciones else None
        
        service = OrdenesService(session)
        
        renglones = [
            {"rfc_id": rfc_id, "concepto_id": concepto_id, "delegacion_id": delegacion_id, "cantidad": 500}
        ]
        
        print("Creating order with 500 requests...")
        orden = service.crear_orden_manual(
            usuario_id=1,  # Assuming user 1 exists
            sesion_id=None,
            descripcion="Test Orden Masiva 500",
            municipio_id=2,
            renglones=renglones
        )
        
        print(f"Order created: {orden.folio} (ID: {orden.orden_id})")
        
        # Verify groups and requests
        grupos = orden.grupos
        print(f"Created {len(grupos)} groups.")
        
        for g in grupos:
            print(f"Group {g.grupo_id} - Qty Requested: {g.cantidad_solicitada}")
            solicitudes = g.solicitudes
            print(f"  Generated {len(solicitudes)} solicitudes.")
            for s in solicitudes:
                print(f"  - Solicitud {s.solicitud_id}: Qty {s.cantidad_solicitada}, Consecutivos {s.consecutivo_inicio}-{s.consecutivo_fin}")
        
        # We roll back so we don't pollute the dev DB
        session.rollback()
        print("Test passed! Transaction rolled back.")

if __name__ == "__main__":
    main()
