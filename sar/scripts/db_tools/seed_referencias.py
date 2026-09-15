"""Mock Data Seeder for Referencias."""

import sys
import os
import random
import uuid
from datetime import datetime, timedelta

# Asegurar que el modulo principal esta en el path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sar.src.storage.db_connector import DatabaseConnector
from sar.src.storage.models import Solicitud, GrupoReferencia, Referencia, EstadoSistema

def seed_referencias():
    db = DatabaseConnector()
    print("Conectando a la base de datos...")
    
    try:
        with db.get_session() as session:
            # 1. Obtener estados de prueba
            estados = session.query(EstadoSistema).filter(EstadoSistema.entidad == 'REFERENCIA').all()
            if not estados:
                # Insertar estados base si no existen
                e1 = EstadoSistema(entidad='REFERENCIA', codigo='GENERADA', descripcion='GENERADA')
                e2 = EstadoSistema(entidad='REFERENCIA', codigo='AUTORIZADA', descripcion='AUTORIZADA')
                e3 = EstadoSistema(entidad='REFERENCIA', codigo='RECHAZADA', descripcion='RECHAZADA')
                e4 = EstadoSistema(entidad='REFERENCIA', codigo='EXPIRADA', descripcion='EXPIRADA')
                session.add_all([e1, e2, e3, e4])
                session.flush()
                estados = [e1, e2, e3, e4]
            
            # 2. Buscar alguna solicitud existente
            solicitud = session.query(Solicitud).first()
            if not solicitud:
                print("Error: No hay solicitudes en la BD. Por favor, crea una Orden y Solicitud primero desde la app.")
                return
                
            grupo = session.get(GrupoReferencia, solicitud.grupo_id)
            if not grupo:
                print("Error: Grupo no encontrado.")
                return
                
            print(f"Usando Solicitud ID: {solicitud.solicitud_id} y Grupo ID: {grupo.grupo_id}")
            
            # 3. Generar 20 referencias simuladas
            nuevas_referencias = []
            now = datetime.utcnow()
            
            for i in range(1, 21):
                estado_random = random.choice(estados)
                
                # Simular diferentes fechas de generacion en el último mes
                dias_restar = random.randint(0, 30)
                fecha_gen = now - timedelta(days=dias_restar)
                
                ref = Referencia(
                    grupo_id=grupo.grupo_id,
                    solicitud_id=solicitud.solicitud_id,
                    consecutivo_grupo=i,
                    referencia_portal=f"REF-{uuid.uuid4().hex[:8].upper()}",
                    importe=round(random.uniform(100.0, 5000.0), 2),
                    fecha_generacion=fecha_gen,
                    fecha_vigencia=(fecha_gen + timedelta(days=30)).date(),
                    estado_id=estado_random.estado_id,
                    usuario_asignado=None # Por defecto sin asignar
                )
                nuevas_referencias.append(ref)
                
            session.add_all(nuevas_referencias)
            
            # Actualizar conteos del grupo y solicitud
            solicitud.cantidad_generada = (solicitud.cantidad_generada or 0) + 20
            grupo.cantidad_generada = (grupo.cantidad_generada or 0) + 20
            
            print(f"Exito: Se insertaron {len(nuevas_referencias)} referencias simuladas exitosamente.")
            
    except Exception as e:
        print(f"Error al sembrar datos: {e}")

if __name__ == "__main__":
    seed_referencias()
