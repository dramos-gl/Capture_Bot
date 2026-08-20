"""
Script de Migración Transaccional Avanzada — Orden 4 → Orden 5
===============================================================
Miga TODAS las referencias de la Orden 4 hacia la Orden 5.
- Si la delegacion_id de una referencia en el CSV cambió, la asocia a una solicitud con la nueva delegación.
- Si la delegacion_id es la misma, la migra a la nueva orden manteniendo la delegación original.
- Si un grupo tiene referencias asignadas a múltiples delegaciones en el CSV (ej. CANCUN y CHETUMAL),
  crea dinámicamente múltiples solicitudes (una por cada delegación bajo ese mismo grupo) en Orden 5
  y asocia cada referencia a la solicitud que le corresponde según el CSV individual.
"""
import sys
import os
import csv
import shutil
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sar.src.storage.db_connector import DatabaseConnector
from sqlalchemy import text

ORDEN_4_ID          = 4
CSV_PATH            = os.path.abspath(os.path.join(os.path.dirname(__file__), 'plantilla_migracion_orden5.csv'))
DESCRIPCION_ORDEN_5 = "Subsidios 2026 Manual - Corrección Delegación"

def get_del_prefix(delegacion_nombre: str) -> str:
    """Calcula el prefijo DEL (3 letras mayúsculas) del nombre de la delegación."""
    nombre_limpio = delegacion_nombre.upper().replace(' ', '').replace('_', '')
    return nombre_limpio[:3]

def build_new_filename(referencia_portal: str, del_prefix: str, grupo_id: int, n: int) -> str:
    """Construye el nombre de archivo según el patrón: [ref]_[DEL][grupo_id]_[n].pdf"""
    return f"{referencia_portal}_{del_prefix}{grupo_id}_{n}.pdf"

def build_new_dir(base_ruta: str, anio: str, folio_orden: str, rfc: str, alias_concepto: str) -> str:
    """Construye la ruta de directorio destino."""
    return os.path.join(base_ruta, anio, folio_orden, rfc, alias_concepto)

def extract_base_ruta(pdf_path: str, anio: str, folio_orden_4: str) -> str:
    """Extrae la ruta base del storage a partir de un pdf_path existente."""
    idx = pdf_path.find(anio + os.sep + folio_orden_4)
    if idx == -1:
        idx = pdf_path.find(anio + '\\' + folio_orden_4)
    if idx == -1:
        idx = pdf_path.find(anio + '/' + folio_orden_4)
    if idx == -1:
        raise ValueError(f"No se puede extraer la ruta base de: {pdf_path}")
    return pdf_path[:idx].rstrip('/\\')

def main():
    print("=" * 90)
    print("  MIGRACIÓN TRANSACCIONAL ORDEN 4 → ORDEN 5 (CON SOPORTE MULTI-DELEGACIÓN)")
    print("=" * 90)

    print(f"\n[1/7] Leyendo CSV de mapeo: {CSV_PATH}")
    if not os.path.exists(CSV_PATH):
        print(f"  ERROR: No se encontró el archivo CSV en {CSV_PATH}")
        return

    # Leer el CSV mapeando referencia_portal -> delegacion_id_correcta
    # y agrupar por grupo_id_ord4 -> {referencia_portal: delegacion_id_correcta}
    mapeo_referencias = defaultdict(dict)
    with open(CSV_PATH, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ref_portal = row['referencia_portal'].strip()
            gid_ord4   = int(row['grupo_id_ord4'].strip())
            del_id_v   = int(row['delegacion_id'].strip())
            mapeo_referencias[gid_ord4][ref_portal] = del_id_v

    total_refs_csv = sum(len(v) for v in mapeo_referencias.values())
    print(f"  Total referencias cargadas desde CSV: {total_refs_csv}")

    db = DatabaseConnector()
    with db.get_session() as session:
        # Cargar Catálogos
        print("\n[2/7] Cargando catálogos de la BD...")
        delegaciones = {
            r['delegacion_id']: {'nombre': r['nombre'], 'del': get_del_prefix(r['nombre'])}
            for r in session.execute(text("SELECT delegacion_id, nombre FROM sar_catalogo.delegacion")).mappings().all()
        }
        
        # Cargar grupos de Orden 4
        grupos_ord4 = {
            r['grupo_id']: dict(r)
            for r in session.execute(text("""
                SELECT gr.grupo_id, gr.rfc_id, r.rfc, gr.concepto_id, c.alias AS concepto_alias,
                       gr.cantidad_solicitada, gr.cantidad_generada, gr.cantidad_autorizada,
                       gr.cantidad_facturada, gr.ultimo_consecutivo
                FROM sar_produccion.grupo_referencia gr
                JOIN sar_catalogo.rfc r ON gr.rfc_id = r.rfc_id
                JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
                WHERE gr.orden_id = :oid
            """), {"oid": ORDEN_4_ID}).mappings().all()
        }

        orden4 = session.execute(text(
            "SELECT folio, fecha_creacion, municipio_id FROM sar_produccion.orden_generacion WHERE orden_id=:oid"
        ), {"oid": ORDEN_4_ID}).mappings().one()
        folio_orden4 = orden4['folio']
        anio_str = str(orden4['fecha_creacion'].year)

        # Estados
        def get_estado(entidad, codigo):
            return session.execute(text(
                "SELECT estado_id FROM sar_catalogo.estado_sistema WHERE entidad=:e AND codigo=:c"
            ), {"e": entidad, "c": codigo}).scalar()

        estado_ord_autorizada  = get_estado('orden_generacion', 'AUTORIZADA')
        estado_grp_facturado   = get_estado('grupo_referencia', 'AUTORIZADO')
        estado_grp_cancelado   = get_estado('grupo_referencia', 'CANCELADO')
        estado_sol_facturada   = get_estado('solicitud', 'FACTURADA')
        estado_sol_cancelada   = get_estado('solicitud', 'CANCELADA')
        usuario_sistema        = session.execute(text(
            "SELECT usuario_id FROM sar_seguridad.usuario WHERE username='admin' LIMIT 1"
        )).scalar()

        # ── 3. Crear Orden 5 ──────────────────────────────────────────────
        print("\n[3/7] Creando/Recuperando Orden 5...")
        orden5_existente = session.execute(text(
            "SELECT orden_id, folio FROM sar_produccion.orden_generacion WHERE descripcion=:desc LIMIT 1"
        ), {"desc": DESCRIPCION_ORDEN_5}).mappings().one_or_none()

        if orden5_existente:
            orden5_id = orden5_existente['orden_id']
            folio_orden5 = orden5_existente['folio']
            print(f"  Orden 5 ya existe: ID={orden5_id} | Folio={folio_orden5}")
        else:
            fecha_ahora = datetime.now()
            folio_orden5 = f"ORD-{fecha_ahora.strftime('%Y%m%d-%H%M%S')}-MIG"
            orden5_id = session.execute(text("""
                INSERT INTO sar_produccion.orden_generacion
                    (folio, descripcion, estado_id, usuario_id, fecha_creacion, municipio_id)
                VALUES (:folio, :desc, :estado, :uid, :fecha, :mun)
                RETURNING orden_id
            """), {
                "folio": folio_orden5, "desc": DESCRIPCION_ORDEN_5, "estado": estado_ord_autorizada,
                "uid": usuario_sistema, "fecha": orden4['fecha_creacion'], "mun": orden4['municipio_id']
            }).scalar()
            print(f"  Orden 5 creada: ID={orden5_id} | Folio={folio_orden5}")

        # ── 4. Procesar Grupos y Solicitudes dinámicamente ────────────────
        print("\n[4/7] Creando grupos y segmentando solicitudes por delegación real...")
        
        mapa_grupos_nuevos = {}
        # Estructura: {(new_grupo_id, delegacion_id): new_solicitud_id}
        mapa_solicitudes_nuevas = {}

        for old_gid, g in grupos_ord4.items():
            # Crear Grupo en Orden 5
            new_gid = session.execute(text(
                "SELECT grupo_id FROM sar_produccion.grupo_referencia WHERE orden_id=:oid AND rfc_id=:rfc AND concepto_id=:con"
            ), {"oid": orden5_id, "rfc": g['rfc_id'], "con": g['concepto_id']}).scalar()

            if not new_gid:
                new_gid = session.execute(text("""
                    INSERT INTO sar_produccion.grupo_referencia
                        (orden_id, rfc_id, concepto_id, estado_id, cantidad_solicitada,
                         cantidad_generada, cantidad_autorizada, cantidad_facturada,
                         ultimo_consecutivo, created_at)
                    VALUES (:oid, :rfc, :con, :est, :cant, :cant, :cant, :cant, :ult, :fecha)
                    RETURNING grupo_id
                """), {
                    "oid": orden5_id, "rfc": g['rfc_id'], "con": g['concepto_id'], "est": estado_grp_facturado,
                    "cant": g['cantidad_solicitada'], "ult": g['ultimo_consecutivo'], "fecha": orden4['fecha_creacion']
                }).scalar()
            mapa_grupos_nuevos[old_gid] = new_gid

            # Identificar qué delegaciones reales se usan en este grupo en el CSV
            delegaciones_del_grupo = set(mapeo_referencias[old_gid].values())
            
            # Obtener consecutivos mínimos/máximos del grupo original para prorratear rangos
            rango_original = session.execute(text(
                "SELECT MIN(consecutivo_grupo), MAX(consecutivo_grupo) FROM sar_produccion.referencia WHERE grupo_id=:gid"
            ), {"gid": old_gid}).fetchone()
            min_c = rango_original[0] if rango_original and rango_original[0] is not None else 1
            max_c = rango_original[1] if rango_original and rango_original[1] is not None else 1

            # Crear una solicitud para cada delegación mapeada bajo este grupo
            for del_id in delegaciones_del_grupo:
                new_sid = session.execute(text(
                    "SELECT solicitud_id FROM sar_produccion.solicitud WHERE grupo_id=:gid AND delegacion_id=:del"
                ), {"gid": new_gid, "del": del_id}).scalar()

                if not new_sid:
                    new_sid = session.execute(text("""
                        INSERT INTO sar_produccion.solicitud
                            (grupo_id, delegacion_id, cantidad_solicitada, cantidad_generada,
                             cantidad_autorizada, cantidad_facturada, consecutivo_inicio,
                             consecutivo_fin, ultimo_consecutivo, estado_id,
                             fecha_inicio, fecha_fin, fecha_asignacion)
                        VALUES (:gid, :del, 0, 0, 0, 0, :ini, :fin, :ult, :est, :fi, :ff, :fa)
                        RETURNING solicitud_id
                    """), {
                        "gid": new_gid, "del": del_id, "ini": min_c, "fin": max_c, "ult": max_c,
                        "est": estado_sol_facturada, "fi": orden4['fecha_creacion'], "ff": orden4['fecha_creacion'],
                        "fa": orden4['fecha_creacion']
                    }).scalar()
                    print(f"    Solicitud creada: grupo_id={new_gid} | delegacion_id={del_id} (ID={new_sid})")
                mapa_solicitudes_nuevas[(new_gid, del_id)] = new_sid

        # ── 5. Migrar referencias una a una a su solicitud correcta ───────
        print("\n[5/7] Migrando referencias a sus nuevas solicitudes...")
        total_migradas = 0

        # Traer todas las referencias a migrar de la BD
        referencias_bd = session.execute(text("""
            SELECT referencia_id, referencia_portal, grupo_id, solicitud_id 
            FROM sar_produccion.referencia 
            WHERE grupo_id IN :gids
        """), {"gids": tuple(grupos_ord4.keys())}).mappings().all()

        for ref in referencias_bd:
            old_gid = ref['grupo_id']
            ref_portal = ref['referencia_portal']
            
            # Obtener delegación destino desde el CSV
            dest_del_id = mapeo_referencias[old_gid].get(ref_portal)
            if dest_del_id is None:
                # Si no está en el CSV, mantiene la original
                dest_del_id = session.execute(text(
                    "SELECT delegacion_id FROM sar_produccion.solicitud WHERE solicitud_id=:sid"
                ), {"sid": ref['solicitud_id']}).scalar()

            new_gid = mapa_grupos_nuevos[old_gid]
            new_sid = mapa_solicitudes_nuevas[(new_gid, dest_del_id)]

            # UPDATE referencia
            session.execute(text("""
                UPDATE sar_produccion.referencia
                SET grupo_id = :new_gid, solicitud_id = :new_sid
                WHERE referencia_id = :rid
            """), {"new_gid": new_gid, "new_sid": new_sid, "rid": ref['referencia_id']})
            total_migradas += 1

        print(f"  Referencias asociadas correctamente: {total_migradas}")

        # ── 6. Actualizar contadores y estados ──────────────────────────────
        print("\n[6/7] Actualizando contadores e inactivando Orden 4...")
        
        # Vaciar y Cancelar grupos y solicitudes de Orden 4
        for old_gid in grupos_ord4:
            session.execute(text("""
                UPDATE sar_produccion.grupo_referencia
                SET cantidad_generada=0, cantidad_autorizada=0, cantidad_facturada=0,
                    ultimo_consecutivo=0, estado_id=:est
                WHERE grupo_id=:gid
            """), {"est": estado_grp_cancelado, "gid": old_gid})

            session.execute(text("""
                UPDATE sar_produccion.solicitud
                SET cantidad_generada=0, cantidad_autorizada=0, cantidad_facturada=0, estado_id=:est
                WHERE grupo_id=:gid
            """), {"est": estado_sol_cancelada, "gid": old_gid})

        # Recalcular contadores reales de Orden 5
        print("  Recalculando contadores en Orden 5...")
        for old_gid, new_gid in mapa_grupos_nuevos.items():
            cnt_ref = session.execute(text("SELECT COUNT(*) FROM sar_produccion.referencia WHERE grupo_id=:gid"), {"gid": new_gid}).scalar()
            cnt_fac = session.execute(text("""
                SELECT COUNT(*) FROM sar_archivo.factura f 
                JOIN sar_produccion.referencia r ON f.referencia_id=r.referencia_id WHERE r.grupo_id=:gid
            """), {"gid": new_gid}).scalar()

            session.execute(text("""
                UPDATE sar_produccion.grupo_referencia
                SET cantidad_solicitada=:cnt_r, cantidad_generada=:cnt_r, cantidad_autorizada=:cnt_r, cantidad_facturada=:cnt_f
                WHERE grupo_id=:gid
            """), {"cnt_r": cnt_ref, "cnt_f": cnt_fac, "gid": new_gid})

            # Actualizar solicitudes
            sols_de_grupo = session.execute(text("SELECT solicitud_id FROM sar_produccion.solicitud WHERE grupo_id=:gid"), {"gid": new_gid}).scalars().all()
            for sid in sols_de_grupo:
                cnt_sol_ref = session.execute(text("SELECT COUNT(*) FROM sar_produccion.referencia WHERE solicitud_id=:sid"), {"sid": sid}).scalar()
                cnt_sol_fac = session.execute(text("""
                    SELECT COUNT(*) FROM sar_archivo.factura f 
                    JOIN sar_produccion.referencia r ON f.referencia_id=r.referencia_id WHERE r.solicitud_id=:sid
                """), {"sid": sid}).scalar()

                session.execute(text("""
                    UPDATE sar_produccion.solicitud
                    SET cantidad_solicitada=:cnt_r, cantidad_generada=:cnt_r, cantidad_autorizada=:cnt_r, cantidad_facturada=:cnt_f
                    WHERE solicitud_id=:sid
                """), {"cnt_r": cnt_sol_ref, "cnt_f": cnt_sol_fac, "sid": sid})

        # No hay contadores globales a nivel de la tabla orden_generacion.

        session.flush()

        # ── 7. Mover y renombrar archivos PDF en disco ──────────────────────
        print("\n[7/7] Renombrando y organizando archivos PDF en disco...")
        muestra_path = session.execute(text("SELECT pdf_path FROM sar_archivo.factura WHERE pdf_path IS NOT NULL LIMIT 1")).scalar()
        
        if not muestra_path:
            print("  ADVERTENCIA: No se encontraron facturas con PDF. Omitiendo movimiento de archivos.")
        else:
            base_storage = extract_base_ruta(muestra_path, anio_str, folio_orden4)
            
            facturas = session.execute(text("""
                SELECT f.factura_id, f.referencia_id, f.pdf_path, f.pdf2_path,
                       ref.grupo_id, r.rfc, c.alias AS concepto_alias, sol.delegacion_id
                FROM sar_archivo.factura f
                JOIN sar_produccion.referencia ref ON f.referencia_id = ref.referencia_id
                JOIN sar_produccion.grupo_referencia gr ON ref.grupo_id = gr.grupo_id
                JOIN sar_catalogo.rfc r ON gr.rfc_id = r.rfc_id
                JOIN sar_catalogo.concepto c ON gr.concepto_id = c.concepto_id
                JOIN sar_produccion.solicitud sol ON ref.solicitud_id = sol.solicitud_id
                WHERE gr.orden_id = :oid
            """), {"oid": orden5_id}).mappings().all()

            archivos_movidos = 0
            for f in facturas:
                del_id = f['delegacion_id']
                del_info = delegaciones.get(del_id, {'nombre': 'CANCUN', 'del': 'CAN'})
                nueva_dir = build_new_dir(base_storage, anio_str, folio_orden5, f['rfc'], f['concepto_alias'])
                os.makedirs(nueva_dir, exist_ok=True)

                ref_portal = session.execute(text("SELECT referencia_portal FROM sar_produccion.referencia WHERE referencia_id=:rid"), {"rid": f['referencia_id']}).scalar()

                nuevos_paths = {}
                for idx, path_key in [(1, 'pdf_path'), (2, 'pdf2_path')]:
                    old_path = f[path_key]
                    if not old_path:
                        nuevos_paths[path_key] = None
                        continue

                    nuevo_nombre = build_new_filename(ref_portal, del_info['del'], f['grupo_id'], idx)
                    nuevo_path = os.path.join(nueva_dir, nuevo_nombre)

                    if os.path.exists(old_path):
                        shutil.move(old_path, nuevo_path)
                        archivos_movidos += 1
                    nuevos_paths[path_key] = nuevo_path

                session.execute(text("""
                    UPDATE sar_archivo.factura
                    SET pdf_path=:pdf, pdf2_path=:pdf2, delegacion=:del
                    WHERE factura_id=:fid
                """), {"pdf": nuevos_paths['pdf_path'], "pdf2": nuevos_paths['pdf2_path'], "del": del_info['nombre'], "fid": f['factura_id']})

            print(f"  Proceso de archivos completado. Movidos en disco: {archivos_movidos}")

    print("\n" + "=" * 90)
    print("  MIGRACIÓN GLOBAL DE ORDEN 4 A ORDEN 5 COMPLETADA CON ÉXITO")
    print("=" * 90)

if __name__ == "__main__":
    main()
