import sys
import os
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sar.src.storage.db_connector import DatabaseConnector
from sar.src.storage.repositories import CatalogoRepository, ProduccionRepository
from sar.src.services.ordenes_service import OrdenesService
from sar.src.services.ordenes_ui_service import OrdenesUIService

def test_cancelaciones_y_orden_anual():
    print("\n=== TEST: Conceptos de Cancelación y Orden Anual ===")
    db = DatabaseConnector()
    
    with db.get_session() as session:
        cat_repo = CatalogoRepository(session)
        
        # 1. Probar filtrado de conceptos habituales vs cancelaciones
        habituales = cat_repo.get_conceptos_activos(es_cancelacion=False)
        cancelaciones = cat_repo.get_conceptos_activos(es_cancelacion=True)
        
        print(f"Conceptos Habituales encontrados: {len(habituales)}")
        print(f"Conceptos de Cancelación encontrados: {len(cancelaciones)}")
        
        assert len(cancelaciones) > 0, "Debe existir al menos 1 concepto de cancelación"
        
        # Obtener IDs necesarios para la prueba
        rfc = cat_repo.get_rfcs_activos()[0]
        delegacion = cat_repo.get_delegaciones_activas()[0]
        concepto_cancelacion = cancelaciones[0]
        
        # 2. Probar creación/asociación a la Orden Anual de Cancelaciones
        ordenes_service = OrdenesService(session)
        renglones = [
            {
                "rfc_id": rfc.rfc_id,
                "concepto_id": concepto_cancelacion.concepto_id,
                "delegacion_id": delegacion.delegacion_id,
                "cantidad": 5
            }
        ]
        
        current_year = datetime.utcnow().year
        orden_cancel = ordenes_service.crear_orden_manual(
            usuario_id=1,
            sesion_id=None,
            descripcion=f"Orden Anual de Cancelaciones {current_year}",
            municipio_id=1,
            renglones=renglones,
            tipo_orden="CANCELACION"
        )
        session.commit()
        
        expected_folio = f"ORD-CANCEL-{current_year}"
        print(f"Folio de Orden Anual generado: {orden_cancel.folio}")
        assert orden_cancel.folio == expected_folio, f"El folio debe ser {expected_folio}"
        assert orden_cancel.tipo_orden == "CANCELACION", "El tipo_orden debe ser CANCELACION"
        
        # 3. Probar acumulación de una segunda solicitud en la misma orden anual
        renglones_segunda = [
            {
                "rfc_id": rfc.rfc_id,
                "concepto_id": concepto_cancelacion.concepto_id,
                "delegacion_id": delegacion.delegacion_id,
                "cantidad": 10
            }
        ]
        orden_segunda = ordenes_service.crear_orden_manual(
            usuario_id=1,
            sesion_id=None,
            descripcion=f"Orden Anual de Cancelaciones {current_year}",
            municipio_id=1,
            renglones=renglones_segunda,
            tipo_orden="CANCELACION"
        )
        session.commit()
        
        assert orden_segunda.orden_id == orden_cancel.orden_id, "Debe reutilizar la misma Orden Anual"
        print(f"Acumulativo de Orden Anual exitoso. ID de orden reutilizado: {orden_segunda.orden_id}")
        
    print("¡TODAS LAS PRUEBAS DE CANCELACIONES Y ORDEN ANUAL PASARON EXITOSAMENTE!")

if __name__ == "__main__":
    test_cancelaciones_y_orden_anual()
