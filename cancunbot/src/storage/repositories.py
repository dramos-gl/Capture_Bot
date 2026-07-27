"""
CancunBot — Repositorios de Base de Datos
Patrón Repository: toda interacción con PostgreSQL pasa por aquí.
Nunca SQL directo fuera de este módulo.
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.storage.db_connector import get_session

logger = logging.getLogger(__name__)


# =============================================================================
# REPOSITORIO: Localizador
# Carga los selectores de portales desde BD (anti-hardcodeo)
# =============================================================================
class LocalizadorRepository:
    """Gestiona la carga de localizadores de portal desde la BD."""

    def cargar_por_portal(self, portal: str) -> dict:
        """
        Carga todos los localizadores activos de un portal.
        
        Returns:
            dict: {nombre_clave: {estrategia_selector, valor_selector, label_visible}}
        """
        with get_session() as session:
            rows = session.execute(
                text("""
                    SELECT nombre_clave, estrategia_selector, valor_selector, label_visible
                    FROM cancunbot_configuracion.localizador_portal
                    WHERE portal = :portal AND activo = TRUE
                """),
                {"portal": portal}
            ).fetchall()

            resultado = {
                row.nombre_clave: {
                    "estrategia_selector": row.estrategia_selector,
                    "valor_selector": row.valor_selector,
                    "label_visible": row.label_visible
                }
                for row in rows
            }
            logger.info(f"Cargados {len(resultado)} localizadores para portal '{portal}'.")
            return resultado


# =============================================================================
# REPOSITORIO: Parámetro de Sistema
# =============================================================================
class ParametroRepository:
    """Gestiona los parámetros configurables del sistema."""

    def obtener(self, codigo: str, default: str = "") -> str:
        """Obtiene el valor de un parámetro por su código."""
        with get_session() as session:
            row = session.execute(
                text("""
                    SELECT valor
                    FROM cancunbot_configuracion.parametro_sistema
                    WHERE codigo = :codigo AND activo = TRUE
                """),
                {"codigo": codigo}
            ).fetchone()
            return row.valor if row else default

    def obtener_todos(self) -> dict:
        """Retorna todos los parámetros activos como diccionario."""
        with get_session() as session:
            rows = session.execute(
                text("""
                    SELECT codigo, valor
                    FROM cancunbot_configuracion.parametro_sistema
                    WHERE activo = TRUE
                """)
            ).fetchall()
            return {row.codigo: row.valor for row in rows}


# =============================================================================
# REPOSITORIO: Solicitud
# =============================================================================
class SolicitudRepository:
    """Gestiona las solicitudes (lotes de folios a procesar)."""

    def _obtener_estado_id(self, session: Session, entidad: str, codigo: str) -> int:
        """Obtiene el ID de un estado del catálogo."""
        row = session.execute(
            text("""
                SELECT estado_id FROM cancunbot_catalogo.estado_sistema
                WHERE entidad = :entidad AND codigo = :codigo
            """),
            {"entidad": entidad, "codigo": codigo}
        ).fetchone()
        if not row:
            raise ValueError(f"Estado '{codigo}' para entidad '{entidad}' no encontrado.")
        return row.estado_id

    def _generar_folio(self, session: Session) -> str:
        """Genera el siguiente folio de solicitud (ej: SOL-2026-001)."""
        row = session.execute(
            text("""
                SELECT COALESCE(MAX(
                    CAST(SPLIT_PART(folio_solicitud, '-', 3) AS INTEGER)
                ), 0) + 1 AS siguiente
                FROM cancunbot_produccion.solicitud
                WHERE folio_solicitud LIKE 'SOL-%'
            """)
        ).fetchone()
        anio = datetime.now().year
        consecutivo = str(row.siguiente).zfill(3)
        return f"SOL-{anio}-{consecutivo}"

    def crear(self, origen: str, descripcion: str = "",
              archivo_excel: Optional[str] = None) -> int:
        """
        Crea una nueva solicitud vacía.
        
        Args:
            origen: 'EXCEL' o 'MANUAL'
            descripcion: Nota descriptiva del lote
            archivo_excel: Ruta del Excel (solo si origen='EXCEL')
        
        Returns:
            solicitud_id del registro creado
        """
        with get_session() as session:
            estado_id = self._obtener_estado_id(session, "SOLICITUD", "NUEVA")
            folio = self._generar_folio(session)
            result = session.execute(
                text("""
                    INSERT INTO cancunbot_produccion.solicitud
                        (folio_solicitud, origen, descripcion, archivo_excel, estado_id)
                    VALUES (:folio, :origen, :descripcion, :archivo_excel, :estado_id)
                    RETURNING solicitud_id
                """),
                {
                    "folio": folio,
                    "origen": origen,
                    "descripcion": descripcion,
                    "archivo_excel": archivo_excel,
                    "estado_id": estado_id
                }
            )
            solicitud_id = result.fetchone().solicitud_id
            session.commit()
            logger.info(f"Solicitud creada: {folio} (ID={solicitud_id}, origen={origen})")
            return solicitud_id

    def listar_todas(self) -> list[dict]:
        """Retorna todas las solicitudes con su estado."""
        with get_session() as session:
            rows = session.execute(text("""
                SELECT s.solicitud_id, s.folio_solicitud, s.origen, s.descripcion,
                       s.total_folios, s.folios_procesados, s.folios_facturados,
                       s.folios_error, s.created_at, e.codigo as estado
                FROM cancunbot_produccion.solicitud s
                JOIN cancunbot_catalogo.estado_sistema e ON s.estado_id = e.estado_id
                ORDER BY s.created_at DESC
            """)).fetchall()
            return [dict(r._mapping) for r in rows]

    def actualizar_contadores(self, solicitud_id: int) -> None:
        """Recalcula y actualiza los contadores de la solicitud desde BD."""
        with get_session() as session:
            session.execute(text("""
                UPDATE cancunbot_produccion.solicitud s
                SET
                    folios_procesados = (
                        SELECT COUNT(*) FROM cancunbot_produccion.folio f
                        JOIN cancunbot_catalogo.estado_sistema e ON f.estado_id = e.estado_id
                        WHERE f.solicitud_id = s.solicitud_id AND e.codigo = 'DESCARGADO'
                    ),
                    folios_error = (
                        SELECT COUNT(*) FROM cancunbot_produccion.folio f
                        JOIN cancunbot_catalogo.estado_sistema e ON f.estado_id = e.estado_id
                        WHERE f.solicitud_id = s.solicitud_id AND e.codigo = 'ERROR_DESCARGA'
                    ),
                    updated_at = NOW()
                WHERE solicitud_id = :solicitud_id
            """), {"solicitud_id": solicitud_id})
            session.commit()


# =============================================================================
# REPOSITORIO: Folio
# =============================================================================
class FolioRepository:
    """Gestiona los folios individuales dentro de una solicitud."""

    def _obtener_estado_id(self, session: Session, codigo: str) -> int:
        row = session.execute(
            text("""
                SELECT estado_id FROM cancunbot_catalogo.estado_sistema
                WHERE entidad = 'FOLIO' AND codigo = :codigo
            """),
            {"codigo": codigo}
        ).fetchone()
        if not row:
            raise ValueError(f"Estado de folio '{codigo}' no encontrado.")
        return row.estado_id

    def crear_lote(self, solicitud_id: int, folios: list[dict]) -> int:
        """
        Inserta un lote de folios para una solicitud.
        
        Args:
            solicitud_id: ID de la solicitud
            folios: Lista de dicts con claves: folio_electronico, folio_pase_caja, tipo_folio
        
        Returns:
            Número de folios insertados
        """
        with get_session() as session:
            estado_id = self._obtener_estado_id(session, "PENDIENTE")
            count = 0
            for folio in folios:
                session.execute(text("""
                    INSERT INTO cancunbot_produccion.folio
                        (solicitud_id, folio_electronico, folio_pase_caja, tipo_folio, estado_id)
                    VALUES (:solicitud_id, :folio_electronico, :folio_pase_caja,
                            :tipo_folio, :estado_id)
                """), {
                    "solicitud_id": solicitud_id,
                    "folio_electronico": folio.get("folio_electronico"),
                    "folio_pase_caja": folio.get("folio_pase_caja"),
                    "tipo_folio": folio.get("tipo_folio", "ELECTRONICO"),
                    "estado_id": estado_id
                })
                count += 1

            # Actualiza contador total en solicitud
            session.execute(text("""
                UPDATE cancunbot_produccion.solicitud
                SET total_folios = total_folios + :count, updated_at = NOW()
                WHERE solicitud_id = :solicitud_id
            """), {"count": count, "solicitud_id": solicitud_id})

            session.commit()
            logger.info(f"Insertados {count} folios en solicitud ID={solicitud_id}")
            return count

    def obtener_pendientes(self) -> list[dict]:
        """Retorna todos los folios en estado PENDIENTE, listos para Bot A."""
        with get_session() as session:
            rows = session.execute(text("""
                SELECT f.folio_id, f.solicitud_id, f.folio_electronico,
                       f.folio_pase_caja, f.tipo_folio, f.intentos
                FROM cancunbot_produccion.folio f
                JOIN cancunbot_catalogo.estado_sistema e ON f.estado_id = e.estado_id
                WHERE e.entidad = 'FOLIO' AND e.codigo = 'PENDIENTE'
                ORDER BY f.solicitud_id, f.folio_id
            """)).fetchall()
            return [dict(r._mapping) for r in rows]

    def actualizar_estado(self, folio_id: int, codigo_estado: str,
                          error: Optional[str] = None) -> None:
        """Actualiza el estado de un folio."""
        with get_session() as session:
            row = session.execute(text("""
                SELECT estado_id FROM cancunbot_catalogo.estado_sistema
                WHERE entidad = 'FOLIO' AND codigo = :codigo
            """), {"codigo": codigo_estado}).fetchone()
            if not row:
                raise ValueError(f"Estado '{codigo_estado}' no existe.")

            session.execute(text("""
                UPDATE cancunbot_produccion.folio
                SET estado_id = :estado_id,
                    intentos = intentos + 1,
                    ultimo_error = :error,
                    updated_at = NOW()
                WHERE folio_id = :folio_id
            """), {"estado_id": row.estado_id, "error": error, "folio_id": folio_id})
            session.commit()


# =============================================================================
# REPOSITORIO: Recibo
# =============================================================================
class ReciboRepository:
    """Gestiona los recibos extraídos del PDF."""

    def crear(self, folio_id: int, datos: dict) -> int:
        """
        Inserta un nuevo registro de recibo con los datos extraídos del PDF.
        
        Args:
            folio_id: ID del folio que generó este recibo
            datos: Diccionario con los campos del recibo
        
        Returns:
            recibo_id del registro creado
        """
        import json
        with get_session() as session:
            row_estado = session.execute(text("""
                SELECT estado_id FROM cancunbot_catalogo.estado_sistema
                WHERE entidad = 'RECIBO' AND codigo = 'CAPTURADO'
            """)).fetchone()
            if not row_estado:
                raise ValueError("Estado 'CAPTURADO' para RECIBO no encontrado.")

            result = session.execute(text("""
                INSERT INTO cancunbot_produccion.recibo (
                    folio_id, folio_pase_caja, folio_electronico, fecha_expedicion,
                    hora_expedicion, lugar_expedicion, rfc, contribucion,
                    nombre_contribuyente, concepto, total, forma_pago,
                    datos_adicionales, pdf_nombre, pdf_ruta, hash_sha256, estado_id
                ) VALUES (
                    :folio_id, :folio_pase_caja, :folio_electronico, :fecha_expedicion,
                    :hora_expedicion, :lugar_expedicion, :rfc, :contribucion,
                    :nombre_contribuyente, :concepto, :total, :forma_pago,
                    :datos_adicionales::jsonb, :pdf_nombre, :pdf_ruta, :hash_sha256,
                    :estado_id
                )
                RETURNING recibo_id
            """), {
                "folio_id": folio_id,
                "folio_pase_caja": datos.get("folio_pase_caja"),
                "folio_electronico": datos.get("folio_electronico"),
                "fecha_expedicion": datos.get("fecha_expedicion"),
                "hora_expedicion": datos.get("hora_expedicion"),
                "lugar_expedicion": datos.get("lugar_expedicion"),
                "rfc": datos.get("rfc"),
                "contribucion": datos.get("contribucion"),
                "nombre_contribuyente": datos.get("nombre_contribuyente"),
                "concepto": datos.get("concepto"),
                "total": datos.get("total"),
                "forma_pago": datos.get("forma_pago"),
                "datos_adicionales": json.dumps(datos.get("datos_adicionales", {})),
                "pdf_nombre": datos.get("pdf_nombre"),
                "pdf_ruta": datos.get("pdf_ruta"),
                "hash_sha256": datos.get("hash_sha256"),
                "estado_id": row_estado.estado_id
            })
            recibo_id = result.fetchone().recibo_id
            session.commit()
            logger.info(f"Recibo creado: ID={recibo_id} (folio_id={folio_id})")
            return recibo_id

    def obtener_pendientes_facturar(self) -> list[dict]:
        """Retorna recibos en estado PENDIENTE_FACTURAR con datos del contribuyente."""
        with get_session() as session:
            rows = session.execute(text("""
                SELECT r.recibo_id, r.folio_electronico, r.rfc, r.total,
                       r.nombre_contribuyente,
                       c.correo_electronico
                FROM cancunbot_produccion.recibo r
                JOIN cancunbot_catalogo.estado_sistema e ON r.estado_id = e.estado_id
                LEFT JOIN cancunbot_catalogo.contribuyente c ON r.rfc = c.rfc
                WHERE e.entidad = 'RECIBO' AND e.codigo = 'PENDIENTE_FACTURAR'
                ORDER BY r.recibo_id
            """)).fetchall()
            return [dict(r._mapping) for r in rows]

    def actualizar_estado(self, recibo_id: int, codigo_estado: str) -> None:
        """Actualiza el estado de un recibo."""
        with get_session() as session:
            row = session.execute(text("""
                SELECT estado_id FROM cancunbot_catalogo.estado_sistema
                WHERE entidad = 'RECIBO' AND codigo = :codigo
            """), {"codigo": codigo_estado}).fetchone()
            if not row:
                raise ValueError(f"Estado de recibo '{codigo_estado}' no existe.")
            session.execute(text("""
                UPDATE cancunbot_produccion.recibo
                SET estado_id = :estado_id, updated_at = NOW()
                WHERE recibo_id = :recibo_id
            """), {"estado_id": row.estado_id, "recibo_id": recibo_id})
            session.commit()


# =============================================================================
# REPOSITORIO: Auditoría
# =============================================================================
class AuditoriaRepository:
    """Gestiona el registro de eventos y errores en auditoría."""

    def registrar_evento(self, modulo: str, accion: str,
                         entidad: Optional[str] = None,
                         entidad_id: Optional[int] = None,
                         detalle: Optional[dict] = None) -> None:
        """Registra un evento en la bitácora de auditoría."""
        import json
        try:
            with get_session() as session:
                session.execute(text("""
                    INSERT INTO cancunbot_auditoria.auditoria_evento
                        (modulo, accion, entidad, entidad_id, detalle)
                    VALUES (:modulo, :accion, :entidad, :entidad_id, :detalle::jsonb)
                """), {
                    "modulo": modulo,
                    "accion": accion,
                    "entidad": entidad,
                    "entidad_id": entidad_id,
                    "detalle": json.dumps(detalle or {})
                })
                session.commit()
        except Exception as e:
            logger.error(f"Error registrando evento de auditoría: {e}")

    def registrar_error(self, modulo: str, mensaje: str,
                        entidad: Optional[str] = None,
                        entidad_id: Optional[int] = None,
                        stack_trace: Optional[str] = None) -> None:
        """Registra un error en la bitácora de auditoría."""
        try:
            with get_session() as session:
                session.execute(text("""
                    INSERT INTO cancunbot_auditoria.auditoria_error
                        (modulo, entidad, entidad_id, mensaje, stack_trace)
                    VALUES (:modulo, :entidad, :entidad_id, :mensaje, :stack_trace)
                """), {
                    "modulo": modulo,
                    "entidad": entidad,
                    "entidad_id": entidad_id,
                    "mensaje": mensaje,
                    "stack_trace": stack_trace
                })
                session.commit()
        except Exception as e:
            logger.error(f"Error registrando error de auditoría: {e}")
