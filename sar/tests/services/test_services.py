"""Integration test to verify SecurityService and OrderService logic."""

import sys
import os

# Añadir el directorio raíz de Proyecto_CapturaBot al path de Python para resolver importaciones
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from sar.src.storage.db_connector import DatabaseConnector
from sar.src.services.security_service import SecurityService
from sar.src.services.order_service import OrderService
from sar.src.storage.models import OrdenGeneracion, GrupoReferencia, Solicitud, Rfc


def run_integration_test():
    print("Iniciando prueba de servicios de Seguridad y Órdenes...")
    
    # Configurar parámetros locales
    os.environ["DB_NAME"] = "db_sar"
    os.environ["DB_USER"] = "postgres"
    os.environ["DB_PASSWORD"] = ""  # Password en blanco según los ajustes del usuario

    connector = DatabaseConnector()

    try:
        with connector.get_session() as session:
            # 1. Instanciar Servicios
            security_svc = SecurityService(session)
            order_svc = OrderService(session)

            # 2. Probar Inicio de Sesión (Login)
            print("\nProbando autenticación con usuario 'admin'...")
            sesion = security_svc.login(
                username="admin",
                password_raw="admin123",
                ip_equipo="127.0.0.1",
                equipo_nombre="Estación de Pruebas"
            )

            if not sesion:
                print("[!] ERROR: No se pudo autenticar al usuario admin.")
                return

            print(f"¡Login Exitoso! ID de Sesión: {sesion.sesion_id}")
            print(f"Estado de la Sesión: {sesion.estado}")

            # 3. Probar Verificación de Permisos (RBAC)
            print("\nVerificando permisos para el usuario admin...")
            tiene_permiso_ordenes = security_svc.has_permission(sesion.usuario_id, "ORDENES", "CREAR")
            tiene_permiso_seguridad = security_svc.has_permission(sesion.usuario_id, "SEGURIDAD", "ELIMINAR")
            
            print(f"¿Tiene permiso para CREAR ORDENES?: {tiene_permiso_ordenes}")
            print(f"¿Tiene permiso para ELIMINAR SEGURIDAD?: {tiene_permiso_seguridad}")

            # 4. Probar Orquestación de Órdenes y Consecutivos
            print("\nAsegurando existencia de RFC para pruebas...")
            rfc_test = session.get(Rfc, 1)
            if not rfc_test:
                rfc_test = Rfc(
                    rfc_id=1,
                    rfc="XAXX010101000",
                    razon_social="EMPRESA DE PRUEBAS S.A. DE C.V.",
                    activo=True
                )
                session.add(rfc_test)
                session.flush()

            print("Creando una Orden de Generación de prueba...")
            
            # Definimos un requerimiento masivo de prueba:
            # Para la empresa 1 (supongamos rfc_id=1, concepto_id=1, delegacion Cancún (id=2) solicita 1000 y Playa (id=3) solicita 1000)
            items_prueba = [
                {"rfc_id": 1, "concepto_id": 1, "delegacion_id": 2, "cantidad": 1000},
                {"rfc_id": 1, "concepto_id": 1, "delegacion_id": 3, "cantidad": 1000}
            ]

            orden = order_svc.create_order(
                descripcion="Orden de prueba de integración de servicios y rangos",
                usuario_id=sesion.usuario_id,
                sesion_id=sesion.sesion_id,
                items=items_prueba
            )

            print(f"¡Orden Creada Exitosamente!")
            print(f"Folio Generado: {orden.folio}")
            print(f"ID de Orden: {orden.orden_id}")

            # 5. Validar que la pre-asignación de consecutivos sea correcta
            # Cancún debe iniciar del 1 al 1000, y Playa del 1001 al 2000
            print("\nValidando asignación de rangos consecutivos para Solicitudes:")
            for grupo in orden.grupos:
                print(f"-> Grupo ID: {grupo.grupo_id} | Cantidad Solicitada en Grupo: {grupo.cantidad_solicitada}")
                for sol in grupo.solicitudes:
                    print(
                        f"   * Solicitud ID: {sol.solicitud_id} | "
                        f"Delegación ID: {sol.delegacion_id} | "
                        f"Cantidad: {sol.cantidad_solicitada} | "
                        f"Rango Asignado: Consecutivo {sol.consecutivo_inicio} al {sol.consecutivo_fin} | "
                        f"Último Consecutivo Inicial: {sol.ultimo_consecutivo}"
                    )

            # Confirmar que los rangos estén correctos
            assert len(orden.grupos) == 1, "Debería crearse un solo grupo para el mismo RFC+Concepto"
            solicitudes = orden.grupos[0].solicitudes
            assert len(solicitudes) == 2, "Deberían crearse dos solicitudes por delegación"
            
            sol1, sol2 = solicitudes[0], solicitudes[1]
            assert sol1.consecutivo_inicio == 1 and sol1.consecutivo_fin == 1000
            assert sol2.consecutivo_inicio == 1001 and sol2.consecutivo_fin == 2000
            print("\n¡ASERTIVIDAD DE RANGOS VERIFICADA CON ÉXITO (1-1000 y 1001-2000)!")

            # 6. Probar Cierre de Sesión (Logout)
            print("\nProbando cierre de sesión...")
            security_svc.logout(sesion.sesion_id)
            
            # Recargar sesión para verificar que esté cerrada
            session.refresh(sesion)
            print(f"Estado de la Sesión después de logout: {sesion.estado}")

    except Exception as e:
        print(f"\n[ERROR] Falló la prueba de integración de servicios.")
        print(f"Detalle: {str(e)}")


if __name__ == "__main__":
    run_integration_test()
