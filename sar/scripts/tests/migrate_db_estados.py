from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

db = DatabaseConnector()

# Definir la matriz de estados deseada
ESTADOS_DESEADOS = [
    # orden_generacion (Femenino)
    ("orden_generacion", "ABIERTA", "Orden abierta para edición"),
    ("orden_generacion", "COMPLETADA", "Orden con todas las referencias generadas"),
    ("orden_generacion", "AUTORIZADA", "Orden con todas las referencias autorizadas"),
    ("orden_generacion", "CANCELADA", "Orden cancelada"),
    
    # grupo_referencia (Masculino)
    ("grupo_referencia", "PENDIENTE", "Grupo pendiente de procesamiento"),
    ("grupo_referencia", "COMPLETADO", "Grupo completamente generado"),
    ("grupo_referencia", "AUTORIZADO", "Grupo completamente autorizado"),
    ("grupo_referencia", "CANCELADO", "Grupo cancelado"),
    
    # solicitud (Femenino)
    ("solicitud", "PENDIENTE", "Solicitud pendiente de procesamiento por bot"),
    ("solicitud", "PROCESANDO", "Solicitud siendo procesada por bot"),
    ("solicitud", "ASIGNADA", "Solicitud asignada a operador/bot"),
    ("solicitud", "COMPLETADA", "Solicitud completada con éxito"),
    ("solicitud", "AUTORIZADA", "Solicitud autorizada de pago"),
    ("solicitud", "CANCELADA", "Solicitud cancelada"),
    ("solicitud", "ERROR", "Solicitud finalizada con error en bot"),
    ("solicitud", "FACTURADA", "Solicitud completamente facturada"),
    ("solicitud", "FACTURADA_PARCIAL", "Solicitud parcialmente facturada"),
    
    # referencia (Femenino)
    ("referencia", "PENDIENTE", "Referencia pendiente"),
    ("referencia", "GENERADA", "Referencia generada en Tributanet"),
    ("referencia", "ASIGNADA", "Referencia asignada a operador"),
    ("referencia", "PENDIENTE_AUTORIZACION", "Referencia pendiente de validación de pago"),
    ("referencia", "AUTORIZADA", "Referencia con pago verificado"),
    ("referencia", "RECHAZADA", "Referencia rechazada de pago"),
    ("referencia", "EXPIRADA", "Referencia vencida sin pago"),
    ("referencia", "FACTURADA", "Referencia facturada en SATQ"),
    ("referencia", "ERROR", "Referencia con error en proceso"),
    ("referencia", "ERROR_VALIDACION", "Referencia con error de validación"),
    
    # general
    ("general", "CANCELADO", "Estado general cancelado"),
]

def migrate_states():
    print("Iniciando migración y unificación de estados del sistema (Búsqueda por valor exacto de case)...")
    
    with db.get_session() as session:
        # 1. Asegurar la existencia de todos los estados deseados con valor EXACTO de case
        estados_map = {} # (entidad, codigo) -> estado_id
        
        for entidad, codigo, desc in ESTADOS_DESEADOS:
            # Buscar existencia exacta (respetando mayúsculas y minúsculas)
            stmt = text("""
                SELECT estado_id FROM sar_catalogo.estado_sistema 
                WHERE entidad = :entidad AND codigo = :codigo
                LIMIT 1
            """)
            row = session.execute(stmt, {"entidad": entidad, "codigo": codigo}).fetchone()
            
            if row:
                # Si existe exactamente, solo actualizamos descripción por si acaso
                session.execute(text("""
                    UPDATE sar_catalogo.estado_sistema 
                    SET descripcion = :desc 
                    WHERE estado_id = :id
                """), {"desc": desc, "id": row.estado_id})
                estados_map[(entidad, codigo)] = row.estado_id
            else:
                # Si no existe exactamente, lo creamos
                ins_stmt = text("""
                    INSERT INTO sar_catalogo.estado_sistema (entidad, codigo, descripcion) 
                    VALUES (:entidad, :codigo, :desc) 
                    RETURNING estado_id
                """)
                new_id = session.execute(ins_stmt, {"entidad": entidad, "codigo": codigo, "desc": desc}).scalar()
                estados_map[(entidad, codigo)] = new_id
                print(f"Creado estado estándar: {entidad} -> {codigo} (ID: {new_id})")
        
        session.flush()
        
        # 2. Obtener la lista actual de todos los estados en la base de datos
        all_estados = session.execute(text("SELECT estado_id, entidad, codigo FROM sar_catalogo.estado_sistema")).fetchall()
        
        # Mapeo de redirección: id_viejo -> id_nuevo
        redirecciones = {}
        
        for row in all_estados:
            est_id, ent, cod = row.estado_id, row.entidad, row.codigo
            
            # Normalizar nombres según las reglas de negocio
            ent_norm = ent.lower()
            cod_norm = cod.upper()
            
            if ent_norm == "grupo_referencia":
                if cod_norm == "CANCELADA": cod_norm = "CANCELADO"
                if cod_norm == "AUTORIZADA": cod_norm = "AUTORIZADO"
            elif ent_norm == "orden_generacion":
                if cod_norm == "COMPLETADO": cod_norm = "COMPLETADA"
            elif ent_norm == "solicitud":
                if cod_norm == "ASIGNADO": cod_norm = "ASIGNADA"
            elif ent_norm == "general":
                ent_norm = "general"
                cod_norm = "CANCELADO"
            
            # Buscar cuál es el ID del estado estándar correspondiente en el mapa que creamos en el paso 1
            target_id = estados_map.get((ent_norm, cod_norm))
            
            if target_id and target_id != est_id:
                redirecciones[est_id] = target_id
                
        # 3. Aplicar las redirecciones a las tablas reales
        for old_id, new_id in sorted(redirecciones.items()):
            print(f"Redirigiendo FKs del estado viejo {old_id} al estándar {new_id}...")
            session.execute(text("UPDATE sar_produccion.referencia SET estado_id = :target WHERE estado_id = :old"), {"target": new_id, "old": old_id})
            session.execute(text("UPDATE sar_produccion.solicitud SET estado_id = :target WHERE estado_id = :old"), {"target": new_id, "old": old_id})
            session.execute(text("UPDATE sar_produccion.grupo_referencia SET estado_id = :target WHERE estado_id = :old"), {"target": new_id, "old": old_id})
            session.execute(text("UPDATE sar_produccion.orden_generacion SET estado_id = :target WHERE estado_id = :old"), {"target": new_id, "old": old_id})
            
        session.flush()
        
        # 4. Eliminar los estados obsoletos (aquellos cuyos IDs no pertenecen al mapa estándar)
        valid_ids = list(estados_map.values())
        print(f"Eliminando registros obsoletos de sar_catalogo.estado_sistema...")
        session.execute(text("DELETE FROM sar_catalogo.estado_sistema WHERE estado_id NOT IN :valid_ids"), {"valid_ids": tuple(valid_ids)})
        
        session.commit()
        print("¡MIGRACIÓN Y UNIFICACIÓN FINALIZADA CON ÉXITO!")

if __name__ == "__main__":
    migrate_states()
