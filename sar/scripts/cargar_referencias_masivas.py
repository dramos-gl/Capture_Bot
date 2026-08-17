"""
Script de Carga Masiva Transaccional para la Orden 4 (SAR)
Procesa un archivo CSV plano con todas las referencias, calcula consecutivos y mapea
a grupo_id y solicitud_id correspondientes usando la Orden 4 en la base de datos PostgreSQL.
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

ORDEN_ID = 4
CSV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'referencias_carga_orden_4.csv'))

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
    print(" INICIANDO PROCESO DE CARGA MASIVA - ORDEN 4")
    print("=" * 80)
    
    if not os.path.exists(CSV_PATH):
        # Crear una plantilla vacia en caso de que no exista
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
        print("\n Validando estructura de la Orden 4 en la Base de Datos...")
        
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

        # Cargar grupos de referencia de la Orden 4
        grupos_db = session.execute(text("""
            SELECT gr.grupo_id, gr.rfc_id, r.rfc, gr.concepto_id, c.alias AS concepto_alias, gr.cantidad_solicitada
            FROM sar_produccion.grupo_referencia gr
            JOIN sar_catalogo.rfc r ON gr.rfc_id = r.rfc_id
            JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
            WHERE gr.orden_id = :oid
        """), {"oid": ORDEN_ID}).mappings().all()

        map_grupos = {}  # (rfc_id/rfc_code, concepto_id/concepto_alias) -> grupo_db
        for g in grupos_db:
            # Soportar busqueda tanto por ID numerico como por codigo de negocio
            map_grupos[(str(g['rfc_id']), str(g['concepto_id']))] = g
            map_grupos[(g['rfc'].upper(), g['concepto_alias'].upper())] = g

        # Cargar solicitudes de la Orden 4
        solicitudes_db = session.execute(text("""
            SELECT s.solicitud_id, s.grupo_id, s.delegacion_id, d.nombre AS delegacion, s.cantidad_solicitada,
                   s.consecutivo_inicio, s.consecutivo_fin
            FROM sar_produccion.solicitud s
            JOIN sar_catalogo.delegacion d ON s.delegacion_id = d.delegacion_id
            WHERE s.grupo_id IN (
                SELECT grupo_id FROM sar_produccion.grupo_referencia WHERE orden_id = :oid
            )
            ORDER BY s.consecutivo_inicio
        """), {"oid": ORDEN_ID}).mappings().all()

        map_solicitudes = {}  # grupo_id -> lista de solicitudes sorted by consecutivo_inicio
        for s in solicitudes_db:
            gid = s['grupo_id']
            if gid not in map_solicitudes:
                map_solicitudes[gid] = []
            map_solicitudes[gid].append(s)

        # 2. Asignacion y Validaciones Previas
        print("\n Mapeando referencias a grupos y solicitudes...")
        
        # Estructura temporal para llevar el consecutivo de insercion
        consecutivos_actuales = {}
        for gid, sols in map_solicitudes.items():
            consecutivos_actuales[gid] = min(s['consecutivo_inicio'] for s in sols)

        # Mapeo de que solicitud le toca a cada registro por delegacion
        conteo_solicitudes = {} # solicitud_id -> cantidad_asignada
        conteo_grupos = {}      # grupo_id -> cantidad_asignada

        referencias_finales = []
        referencias_set = set()

        for reg in registros:
            rfc_val = reg['rfc'].upper()
            concepto_val = reg['concepto'].upper()
            deleg_val = reg['delegacion'].upper()
            ref_portal = reg['referencia_portal']

            # Evitar duplicados en el mismo CSV
            if ref_portal in referencias_set:
                print(f" Error: La referencia portal '{ref_portal}' esta duplicada en el CSV (linea {reg['linea']}).")
                return
            referencias_set.add(ref_portal)

            # Buscar grupo_id probando por valor exacto del CSV (pueden ser IDs como '2' o codigos)
            g_key = (rfc_val, concepto_val)
            if g_key not in map_grupos:
                print(f" Error: El grupo con RFC '{rfc_val}' y Concepto '{concepto_val}' no pertenece a la Orden 4 (linea {reg['linea']}).")
                return
            grupo = map_grupos[g_key]
            gid = grupo['grupo_id']

            # Buscar solicitudes de este grupo
            sols_grupo = map_solicitudes.get(gid, [])
            solicitud_destino = None
            
            # Buscamos la primera solicitud de este grupo que tenga espacio disponible,
            # sin obligar a que coincida estrictamente la delegacion por fila si esta viene
            # desalineada con las cuotas asignadas en la UI (distribucion secuencial por grupo).
            for s in sols_grupo:
                asignadas = conteo_solicitudes.get(s['solicitud_id'], 0)
                if asignadas < s['cantidad_solicitada']:
                    solicitud_destino = s
                    break

            if not solicitud_destino:
                print(f" Error: No hay solicitudes disponibles (todas estan llenas) bajo el grupo ID {gid} (linea {reg['linea']}).")
                return

            sid = solicitud_destino['solicitud_id']
            conteo_solicitudes[sid] = conteo_solicitudes.get(sid, 0) + 1
            conteo_grupos[gid] = conteo_grupos.get(gid, 0) + 1

            # Calcular consecutivo para esta referencia dentro del grupo
            # Usaremos los consecutivos del grupo ordenadamente
            consecutivo = consecutivos_actuales[gid]
            consecutivos_actuales[gid] += 1

            referencias_finales.append({
                'grupo_id': gid,
                'solicitud_id': sid,
                'consecutivo_grupo': consecutivo,
                'referencia_portal': ref_portal,
                'importe': reg['importe'],
                'fecha_generacion': reg['fecha_generacion'],
                'fecha_vigencia': reg['fecha_vigencia'],
                'estado_id': estado_ref_autorizada,
                'cantidad': 1,
                'porcentaje': 100
            })

        # Validar si las cantidades en el archivo no exceden o descuadran con los totales solicitados
        print("\n Validando integridad de totales por grupo...")
        for gid, g in map_grupos.items():
            db_id = g['grupo_id']
            solicitadas = g['cantidad_solicitada']
            cargadas = conteo_grupos.get(db_id, 0)
            if cargadas != solicitadas:
                print(f" Advertencia: El grupo ID {db_id} ({gid[0]} - {gid[1]}) tiene {solicitadas} solicitadas, pero se estan cargando {cargadas} referencias.")

        # Verificar si alguna referencia ya existe en la base de datos
        print("\n Verificando duplicados contra la base de datos...")
        chunk_size = 1000
        for i in range(0, len(referencias_finales), chunk_size):
            chunk = referencias_finales[i:i+chunk_size]
            portal_refs = [r['referencia_portal'] for r in chunk]
            duplicados_db = session.execute(
                text("SELECT referencia_portal FROM sar_produccion.referencia WHERE referencia_portal = ANY(:refs)"),
                {"refs": portal_refs}
            ).scalars().all()
            if duplicados_db:
                print(f" Error: Las siguientes referencias ya existen en la base de datos: {duplicados_db}")
                return

        # 3. Proceder con el Insert Masivo
        print("\n Todo validado. Insertando referencias en la base de datos...")
        
        session.bulk_insert_mappings(Referencia, referencias_finales)
        session.flush()
        print(f" {len(referencias_finales)} referencias insertadas exitosamente.")

        # 4. Actualizar contadores y estados
        print("\n Actualizando contadores de Solicitudes y Grupos...")
        
        for sid, count in conteo_solicitudes.items():
            session.execute(text("""
                UPDATE sar_produccion.solicitud
                SET cantidad_generada = :c, cantidad_autorizada = :c,
                    estado_id = :eid, ultimo_consecutivo = consecutivo_fin
                WHERE solicitud_id = :sid
            """), {"c": count, "eid": estado_sol_autorizada, "sid": sid})

        for gid, count in conteo_grupos.items():
            session.execute(text("""
                UPDATE sar_produccion.grupo_referencia
                SET cantidad_generada = :c, cantidad_autorizada = :c,
                    estado_id = :eid, ultimo_consecutivo = cantidad_solicitada
                WHERE grupo_id = :gid
            """), {"c": count, "eid": estado_grp_autorizado, "gid": gid})

        # Actualizar la Orden completa a AUTORIZADA
        session.execute(text("""
            UPDATE sar_produccion.orden_generacion
            SET estado_id = :eid
            WHERE orden_id = :oid
        """), {"eid": estado_ord_autorizada, "oid": ORDEN_ID})

        # 5. Retro-fechado automatico
        print("\n Aplicando retro-fechado a la Orden y Solicitudes...")
        # Obtenemos la menor fecha de generacion de las referencias insertadas para retro-fechar
        min_fecha_gen = min(r['fecha_generacion'] for r in referencias_finales)
        min_fecha_dt = datetime.combine(min_fecha_gen, datetime.min.time())
        
        session.execute(text("""
            UPDATE sar_produccion.orden_generacion
            SET fecha_creacion = :f
            WHERE orden_id = :oid
        """), {"f": min_fecha_dt, "oid": ORDEN_ID})

        session.execute(text("""
            UPDATE sar_produccion.grupo_referencia
            SET created_at = :f
            WHERE orden_id = :oid
        """), {"f": min_fecha_dt, "oid": ORDEN_ID})

        session.execute(text("""
            UPDATE sar_produccion.solicitud
            SET fecha_inicio = :f, fecha_fin = :f, fecha_asignacion = :f
            WHERE grupo_id IN (SELECT grupo_id FROM sar_produccion.grupo_referencia WHERE orden_id = :oid)
        """), {"f": min_fecha_dt, "oid": ORDEN_ID})

        print(f" Se aplico el retro-fechado a la fecha minima encontrada: {min_fecha_gen}")
        print("\n ¡Proceso completado exitosamente y con total consistencia transaccional!")

if __name__ == "__main__":
    main()
