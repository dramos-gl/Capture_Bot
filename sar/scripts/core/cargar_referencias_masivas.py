"""
Script de Carga Masiva Transaccional Incremental para la Orden de Referencias (SAR)
Permite subir un listado adicional de referencias a una orden y solicitudes ya existentes,
incrementando dinámicamente las cuotas o agregando nuevas solicitudes si la delegación no existía.
"""
import sys
import os
import csv
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sar.src.storage.db_connector import DatabaseConnector
from sar.src.storage.models import Referencia
from sqlalchemy import text

ORDEN_ID = 5
CSV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'referencias_carga_orden_5.csv'))

def parse_date(date_str):
    """Parsea fecha en formatos comunes YYYY-MM-DD o DD/MM/YYYY. Retorna None si es vacio."""
    if not date_str or not date_str.strip():
        return None
    date_str = date_str.strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Formato de fecha invalido: '{date_str}'")

def main():
    print("=" * 80)
    print(f" INICIANDO PROCESO DE CARGA MASIVA INCREMENTAL - ORDEN ID: {ORDEN_ID}")
    print("=" * 80)
    
    if not os.path.exists(CSV_PATH):
        print(f" No se encontro el archivo CSV en: {CSV_PATH}")
        print(" Generando una plantilla vacia para ti...")
        with open(CSV_PATH, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['rfc', 'concepto_alias', 'delegacion', 'referencia_portal', 'importe', 'fecha_generacion', 'fecha_vigencia'])
        print(f" Plantilla creada. Por favor llenala en: {CSV_PATH}")
        return

    db = DatabaseConnector()
    
    # 1. Leer y analizar el CSV completo
    registros = []
    print(f" Leyendo datos desde {CSV_PATH}...")
    try:
        with open(CSV_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=2):
                ref = row.get('referencia_portal', '').strip()
                if not ref:
                    continue
                
                try:
                    importe = float(row.get('importe') or 0.0)
                    fecha_gen = parse_date(row.get('fecha_generacion'))
                    fecha_vig = parse_date(row.get('fecha_vigencia'))
                except ValueError as e:
                    print(f" Error en la linea {idx} del CSV: {e}")
                    return

                registros.append({
                    'linea': idx,
                    'rfc': row.get('rfc', '').strip(),
                    'concepto': row.get('concepto_alias', '').strip(),
                    'delegacion': row.get('delegacion', '').strip(),
                    'referencia_portal': ref,
                    'importe': importe,
                    'fecha_generacion': fecha_gen,
                    'fecha_vigencia': fecha_vig
                })
    except Exception as e:
        print(f" Error al abrir o leer el archivo CSV: {e}")
        return

    total_registros = len(registros)
    print(f" Se leyeron {total_registros} registros del CSV.")
    if total_registros == 0:
        print(" No hay registros para procesar.")
        return

    # Iniciar la conexion y transaccion
    with db.get_session() as session:
        print(f"\n Validando estructura de la Orden {ORDEN_ID} en la Base de Datos...")
        
        # Obtener los ids de estado requeridos
        estado_ref_autorizada = session.execute(
            text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad='referencia' AND codigo='AUTORIZADA'")
        ).scalar()
        estado_sol_autorizada = session.execute(
            text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad='solicitud' AND codigo='AUTORIZADA'")
        ).scalar()
        estado_grp_autorizado = session.execute(
            text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad='grupo_referencia' AND codigo='AUTORIZADO'")
        ).scalar()
        estado_ord_autorizada = session.execute(
            text("SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad='orden_generacion' AND codigo='AUTORIZADA'")
        ).scalar()

        if not all([estado_ref_autorizada, estado_sol_autorizada, estado_grp_autorizado, estado_ord_autorizada]):
            print(" Error: No se encontraron todos los catalogos de estados requeridos en sar_catalogo.estado_sistema.")
            return

        # Cargar catálogo de delegaciones
        delegaciones_db = session.execute(text("SELECT delegacion_id, nombre FROM sar_catalogo.delegacion")).mappings().all()
        map_delegaciones = {d['nombre'].upper(): d['delegacion_id'] for d in delegaciones_db}

        # Cargar grupos de referencia de la Orden
        grupos_db = session.execute(text("""
            SELECT gr.grupo_id, gr.rfc_id, r.rfc, gr.concepto_id, c.alias AS concepto_alias, gr.cantidad_solicitada, gr.cantidad_generada
            FROM sar_produccion.grupo_referencia gr
            JOIN sar_catalogo.rfc r ON gr.rfc_id = r.rfc_id
            JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
            WHERE gr.orden_id = :oid
        """), {"oid": ORDEN_ID}).mappings().all()

        map_grupos = {}
        for g in grupos_db:
            map_grupos[(g['rfc'].upper(), g['concepto_alias'].upper())] = g

        # Cargar solicitudes de la Orden
        solicitudes_db = session.execute(text("""
            SELECT s.solicitud_id, s.grupo_id, s.delegacion_id, d.nombre AS delegacion, s.cantidad_solicitada, s.cantidad_generada,
                   s.consecutivo_inicio, s.consecutivo_fin
            FROM sar_produccion.solicitud s
            JOIN sar_catalogo.delegacion d ON s.delegacion_id = d.delegacion_id
            WHERE s.grupo_id IN (
                SELECT grupo_id FROM sar_produccion.grupo_referencia WHERE orden_id = :oid
            )
            ORDER BY s.consecutivo_inicio
        """), {"oid": ORDEN_ID}).mappings().all()

        # Mapeamos solicitudes existentes por (grupo_id, delegacion_id)
        map_solicitudes = {}
        for s in solicitudes_db:
            map_solicitudes[(s['grupo_id'], s['delegacion_id'])] = dict(s)

        # Mapeamos también la lista de solicitudes por grupo_id para saber cuál es el máximo consecutivo actual
        solicitudes_por_grupo = {}
        for s in solicitudes_db:
            gid = s['grupo_id']
            if gid not in solicitudes_por_grupo:
                solicitudes_por_grupo[gid] = []
            solicitudes_por_grupo[gid].append(s)

        # Verificar si alguna referencia ya existe en la base de datos
        print("\n Verificando duplicados contra la base de datos...")
        portal_refs_csv = [r['referencia_portal'] for r in registros]
        chunk_size = 1000
        for i in range(0, len(portal_refs_csv), chunk_size):
            chunk = portal_refs_csv[i:i+chunk_size]
            duplicados_db = session.execute(
                text("SELECT referencia_portal FROM sar_produccion.referencia WHERE referencia_portal = ANY(:refs)"),
                {"refs": chunk}
            ).scalars().all()
            if duplicados_db:
                print(f" Error: Las siguientes referencias ya existen en la base de datos: {duplicados_db}")
                return

        # 2. Mapeo incremental
        print("\n Procesando asignación incremental...")
        referencias_finales = []
        
        # Diccionario para rastrear cuántas referencias adicionales sumamos a cada solicitud/grupo en esta ejecución
        nuevas_referencias_por_solicitud = {} # solicitud_id -> count
        nuevas_referencias_por_grupo = {}     # grupo_id -> count
        
        # Rastrear consecutivos por grupo de forma secuencial
        consecutivos_siguiente = {}
        for gid, sols in solicitudes_por_grupo.items():
            # El siguiente consecutivo del grupo será el MAX consecutivo_fin de sus solicitudes + 1
            max_consec = max(s['consecutivo_fin'] for s in sols)
            consecutivos_siguiente[gid] = max_consec + 1

        for reg in registros:
            rfc_val = reg['rfc'].upper()
            concepto_val = reg['concepto'].upper()
            deleg_val = reg['delegacion'].upper()
            ref_portal = reg['referencia_portal']

            # Validar grupo
            g_key = (rfc_val, concepto_val)
            if g_key not in map_grupos:
                print(f" Error: El grupo con RFC '{rfc_val}' y Concepto '{concepto_val}' no pertenece a la Orden {ORDEN_ID} (linea {reg['linea']}).")
                return
            grupo = map_grupos[g_key]
            gid = grupo['grupo_id']

            # Validar delegación
            if deleg_val not in map_delegaciones:
                print(f" Error: La delegación '{deleg_val}' no existe en el catálogo base (linea {reg['linea']}).")
                return
            deleg_id = map_delegaciones[deleg_val]

            # Buscar si ya existe una solicitud para este grupo y delegación
            sol_key = (gid, deleg_id)
            if sol_key in map_solicitudes:
                solicitud = map_solicitudes[sol_key]
                sid = solicitud['solicitud_id']
            else:
                # Si la delegación no tiene solicitud en este grupo, creamos una nueva solicitud
                print(f" -> Detectada nueva delegación '{deleg_val}' en grupo {gid}. Creando solicitud...")
                
                # consecutivo_inicio de la nueva solicitud será el máximo actual del grupo
                c_inicio = consecutivos_siguiente.get(gid, 1)
                
                res_insert_sol = session.execute(text("""
                    INSERT INTO sar_produccion.solicitud 
                    (grupo_id, delegacion_id, cantidad_solicitada, cantidad_generada, cantidad_autorizada,
                     consecutivo_inicio, consecutivo_fin, ultimo_consecutivo, estado_id, 
                     fecha_inicio, fecha_fin, fecha_asignacion)
                    VALUES 
                    (:gid, :del_id, 0, 0, 0, :c_ini, :c_ini, :c_ini, :eid, :now, :now, :now)
                    RETURNING solicitud_id
                """), {
                    "gid": gid, "del_id": deleg_id, "c_ini": c_inicio, "eid": estado_sol_autorizada, "now": datetime.now()
                })
                sid = res_insert_sol.scalar()
                
                # Registrar en la estructura temporal
                nueva_sol = {
                    'solicitud_id': sid,
                    'grupo_id': gid,
                    'delegacion_id': deleg_id,
                    'cantidad_solicitada': 0,
                    'cantidad_generada': 0,
                    'consecutivo_inicio': c_inicio,
                    'consecutivo_fin': c_inicio - 1
                }
                map_solicitudes[sol_key] = nueva_sol
                if gid not in solicitudes_por_grupo:
                    solicitudes_por_grupo[gid] = []
                solicitudes_por_grupo[gid].append(nueva_sol)
                
            # Calcular consecutivo único para esta referencia en el grupo
            consecutivo_actual = consecutivos_siguiente.get(gid, 1)
            consecutivos_siguiente[gid] = consecutivo_actual + 1

            referencias_finales.append({
                'grupo_id': gid,
                'solicitud_id': sid,
                'consecutivo_grupo': consecutivo_actual,
                'referencia_portal': ref_portal,
                'importe': reg['importe'],
                'fecha_generacion': reg['fecha_generacion'],
                'fecha_vigencia': reg['fecha_vigencia'],
                'estado_id': estado_ref_autorizada,
                'cantidad': 1,
                'porcentaje': 100
            })

            nuevas_referencias_por_solicitud[sid] = nuevas_referencias_por_solicitud.get(sid, 0) + 1
            nuevas_referencias_por_grupo[gid] = nuevas_referencias_por_grupo.get(gid, 0) + 1

        # 3. Proceder con la inserción de las referencias adicionales
        print("\n Insertando referencias adicionales...")
        session.bulk_insert_mappings(Referencia, referencias_finales)
        session.flush()
        print(f" {len(referencias_finales)} referencias insertadas exitosamente.")

        # 4. Actualizar contadores, límites y consecutivos
        print("\n Actualizando contadores, cuotas de solicitudes y consecutivos...")
        
        # Actualizar solicitudes
        for sid, count in nuevas_referencias_por_solicitud.items():
            # Obtener datos anteriores de la solicitud
            sol = next(s for s_list in solicitudes_por_grupo.values() for s in s_list if s['solicitud_id'] == sid)
            
            nueva_cantidad_gen = sol['cantidad_generada'] + count
            nueva_cantidad_sol = sol['cantidad_solicitada'] + count # Aumentar cantidad solicitada para dar cabida
            nuevo_consecutivo_fin = sol['consecutivo_inicio'] + nueva_cantidad_sol - 1
            
            session.execute(text("""
                UPDATE sar_produccion.solicitud
                SET cantidad_solicitada = :cs, cantidad_generada = :cg, cantidad_autorizada = :cg,
                    consecutivo_fin = :cfin, ultimo_consecutivo = :cfin
                WHERE solicitud_id = :sid
            """), {
                "cs": nueva_cantidad_sol, "cg": nueva_cantidad_gen, "cfin": nuevo_consecutivo_fin, "sid": sid
            })

        # Actualizar grupos
        for gid, count in nuevas_referencias_por_grupo.items():
            # Obtener cuota anterior del grupo
            g_db = next(g for g in grupos_db if g['grupo_id'] == gid)
            nueva_cant_sol = g_db['cantidad_solicitada'] + count
            nueva_cant_gen = g_db['cantidad_generada'] + count
            
            session.execute(text("""
                UPDATE sar_produccion.grupo_referencia
                SET cantidad_solicitada = :cs, cantidad_generada = :cg, cantidad_autorizada = :cg,
                    ultimo_consecutivo = :cs
                WHERE grupo_id = :gid
            """), {
                "cs": nueva_cant_sol, "cg": nueva_cant_gen, "gid": gid
            })

        # Sincronizar estados
        session.execute(text("UPDATE sar_produccion.orden_generacion SET estado_id = :eid WHERE orden_id = :oid"), {"eid": estado_ord_autorizada, "oid": ORDEN_ID})

        print("\n ¡Referencias integradas al lote masivo con total consistencia y actualización de cuotas!")

if __name__ == "__main__":
    main()
