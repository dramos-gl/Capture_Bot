import sys
import os
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sar.src.storage.db_connector import DatabaseConnector
from sar.src.storage.repositories import CatalogoRepository
from sar.src.services.ordenes_service import OrdenesService
from sar.src.services.admin_service import AdminService

def test_carga_masiva_cancelacion_nueva_solicitud():
    print("\n=== TEST: Carga Masiva - Nueva Solicitud en Órdenes No-ESTANDAR ===")
    db = DatabaseConnector()
    
    with db.get_session() as session:
        cat_repo = CatalogoRepository(session)
        cancelaciones = cat_repo.get_conceptos_activos(es_cancelacion=True)
        assert len(cancelaciones) > 0, "Debe existir al menos un concepto de cancelación"
        
        rfc = cat_repo.get_rfcs_activos()[0]
        delegacion = cat_repo.get_delegaciones_activas()[0]
        concepto = cancelaciones[0]
        
        # 1. Obtener o crear orden de cancelación
        ordenes_svc = OrdenesService(session)
        current_year = datetime.now().year
        orden = ordenes_svc.crear_orden_manual(
            usuario_id=1,
            sesion_id=None,
            descripcion=f"Orden Anual de Cancelaciones {current_year}",
            municipio_id=1,
            renglones=[{
                "rfc_id": rfc.rfc_id,
                "concepto_id": concepto.concepto_id,
                "delegacion_id": delegacion.delegacion_id,
                "cantidad": 1
            }],
            tipo_orden="CANCELACION"
        )
        session.commit()
        
        admin_svc = AdminService(session)
        
        # Obtener cuántas solicitudes existen antes de la carga masiva
        from sqlalchemy import text
        sols_previas = session.execute(text("""
            SELECT s.solicitud_id, s.consecutivo_inicio, s.consecutivo_fin
            FROM sar_produccion.solicitud s
            JOIN sar_produccion.grupo_referencia gr ON s.grupo_id = gr.grupo_id
            WHERE gr.orden_id = :oid
        """), {"oid": orden.orden_id}).mappings().all()
        count_sols_previas = len(sols_previas)
        max_consec_previo = max([s['consecutivo_fin'] for s in sols_previas] or [0])
        
        # 2. Simular registros para carga masiva
        dummy_ref = f"TSTCAN{datetime.now().strftime('%M%S%f')}"
        registros = [{
            "rfc": rfc.rfc,
            "concepto_alias": concepto.alias or concepto.nombre,
            "delegacion": delegacion.nombre,
            "referencia_portal": dummy_ref,
            "importe": 1500.0,
            "fecha_generacion": None,
            "fecha_vigencia": None
        }]
        
        # 3. Probar método de preview
        preview_res = admin_svc.preview_carga_masiva_referencias(orden.orden_id, registros)
        print(f"Preview resultado: es_valido={preview_res['es_valido']}, nuevas_solicitudes={preview_res['nuevas_solicitudes_estimadas']}")
        assert preview_res["es_valido"] is True
        assert preview_res["nuevas_solicitudes_estimadas"] == 1
        
        # 4. Probar método de ejecución
        exec_res = admin_svc.ejecutar_carga_masiva_referencias(
            orden_id=orden.orden_id,
            registros=registros,
            usuario_id=1
        )
        session.commit()
        print(f"Ejecución resultado: {exec_res}")
        assert exec_res["solicitudes_creadas"] == 1
        assert exec_res["total_referencias_cargadas"] == 1
        
        # 5. Validar en BD que se creó una NUEVA solicitud y que el consecutivo es correlativo continuo
        sols_posteriores = session.execute(text("""
            SELECT s.solicitud_id, s.consecutivo_inicio, s.consecutivo_fin, s.cantidad_generada
            FROM sar_produccion.solicitud s
            JOIN sar_produccion.grupo_referencia gr ON s.grupo_id = gr.grupo_id
            WHERE gr.orden_id = :oid
            ORDER BY s.solicitud_id DESC
        """), {"oid": orden.orden_id}).mappings().all()
        
        assert len(sols_posteriores) == count_sols_previas + 1, "Debe haberse sumado exactamente 1 nueva solicitud"
        nueva_sol = sols_posteriores[0]
        print(f"Nueva solicitud creada: ID={nueva_sol['solicitud_id']}, inicio={nueva_sol['consecutivo_inicio']}, fin={nueva_sol['consecutivo_fin']}")
        assert nueva_sol['consecutivo_inicio'] == max_consec_previo + 1, f"El consecutivo de inicio debe ser {max_consec_previo + 1}"
        assert nueva_sol['consecutivo_fin'] == max_consec_previo + 1
        
    print("¡TEST DE CARGA MASIVA CON NUEVA SOLICITUD COMPLETADO CON ÉXITO!")

if __name__ == "__main__":
    test_carga_masiva_cancelacion_nueva_solicitud()
