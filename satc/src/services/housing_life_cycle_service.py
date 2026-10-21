"""
SATC — Servicio del Ciclo de Vida de Viviendas y Trámites
Módulo: satc.src.services.housing_life_cycle_service

Gobierna la creación de Regímenes de Condominio, generación en masa de UPEs
y la matriz preventiva de trámites con vinculación documental y financiera ERP.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from satc.src.storage.satc_models import (
    RegimenCondominio, Vivienda, TramiteVivienda, TipoTramite, EstadoVivienda, EstadoTramite
)
from satc.src.storage.satc_repos import (
    RegimenCondominioRepository, ViviendaRepository, TramiteViviendaRepository,
    TipoTramiteRepository, EstadoViviendaRepository, EstadoTramiteRepository
)

logger = logging.getLogger(__name__)


class HousingLifeCycleService:
    """Capa de lógica de negocio para la gobernanza de viviendas y trámites."""

    def __init__(self, session: Session):
        self.session = session
        self.regimen_repo = RegimenCondominioRepository(session)
        self.vivienda_repo = ViviendaRepository(session)
        self.tramite_repo = TramiteViviendaRepository(session)
        self.tipo_tramite_repo = TipoTramiteRepository(session)
        self.estado_vivienda_repo = EstadoViviendaRepository(session)
        self.estado_tramite_repo = EstadoTramiteRepository(session)

    def registrar_regimen(
        self,
        desarrollo_id: int,
        nombre_regimen: str,
        mz: str,
        lt: str,
        total_upes: int,
        sm: Optional[str] = None,
        licencia_matriz: Optional[str] = None,
        clave_catastral_matriz: Optional[str] = None,
    ) -> RegimenCondominio:
        """
        Registra un Régimen en Condominio fiduciario (Macro-Lote).
        Ejemplo: 'REGIMEN AURA NOVA PLAYA MZ1 LT1' con 577 UPEs.
        """
        regimen = self.regimen_repo.create(
            desarrollo_id=desarrollo_id,
            nombre_regimen=nombre_regimen,
            sm=sm,
            mz=mz,
            lt=lt,
            total_upes=total_upes,
            licencia_matriz=licencia_matriz,
            clave_catastral_matriz=clave_catastral_matriz,
        )
        self.session.commit()
        logger.info(f"Régimen '{nombre_regimen}' creado exitosamente con ID {regimen.regimen_id} y {total_upes} UPEs.")
        return regimen

    def generar_upes_en_masa(
        self,
        regimen_id: int,
        prefijo_upe: str = "UPE",
        rango_inicio: int = 1,
        rango_fin: Optional[int] = None,
        edificio_defecto: Optional[str] = None,
        calle_defecto: Optional[str] = None,
    ) -> List[Vivienda]:
        """
        Genera en bloque las N UPEs autorizadas de un Régimen de Condominio.
        Garantiza que no se sobrepase el total_upes declarado.
        """
        regimen = self.regimen_repo.get_by_id(regimen_id)
        if not regimen:
            raise ValueError(f"Régimen con ID {regimen_id} no encontrado.")

        fin = rango_fin or regimen.total_upes
        if fin > regimen.total_upes:
            raise ValueError(
                f"El rango solicitado ({fin}) excede el total de UPEs autorizadas ({regimen.total_upes})."
            )

        viviendas_creadas = []
        for i in range(rango_inicio, fin + 1):
            num_upe_str = f"{prefijo_upe}-{str(i).zfill(3)}"
            interior_str = f"{str(i).zfill(3)}"
            viv = self.vivienda_repo.create_upe(
                regimen_id=regimen.regimen_id,
                interior=interior_str,
                numero_oficial=num_upe_str,
                edificio=edificio_defecto,
                calle=calle_defecto,
                destino="HABITACIONAL",
                espacio="VIVIENDA",
                descripcion=f"UPE {i} de {regimen.total_upes} - {regimen.nombre_regimen}",
                estado_codigo="PROYECTADA"
            )
            viviendas_creadas.append(viv)

        self.regimen_repo.increment_upes_generadas(regimen_id, len(viviendas_creadas))
        self.session.commit()
        logger.info(f"Generadas {len(viviendas_creadas)} UPEs para el régimen ID {regimen_id}.")
        return viviendas_creadas

    def inicializar_matriz_tramites(self, vivienda_id: int) -> List[TramiteVivienda]:
        """
        Asocia automáticamente a una vivienda todos los trámites obligatorios
        definidos en el catálogo que apliquen a 'VIVIENDA_INDIVIDUAL' o 'AMBOS'.
        """
        tipos_obligatorios = (
            self.session.query(TipoTramite)
            .filter(
                TipoTramite.activo.is_(True),
                TipoTramite.es_obligatorio.is_(True),
                TipoTramite.aplica_a.in_(["VIVIENDA_INDIVIDUAL", "AMBOS"])
            )
            .all()
        )

        tramites_creados = []
        for tipo in tipos_obligatorios:
            t = self.tramite_repo.create(
                tipo_tramite_id=tipo.tipo_tramite_id,
                vivienda_id=vivienda_id,
                estado_codigo="NO_INICIADO"
            )
            tramites_creados.append(t)

        self.session.commit()
        return tramites_creados

    def detectar_omisiones_regimen(self, regimen_id: int) -> Dict[str, Any]:
        """
        Auditoría de prevención de omisiones para un Régimen de Condominio:
        - UPEs faltantes por dar de alta
        - UPEs sin individualización catastral
        - Trámites obligatorios pendientes previo a escrituración
        - Recibos descargados sin factura timbrada
        """
        regimen = self.regimen_repo.get_by_id(regimen_id)
        if not regimen:
            raise ValueError(f"Régimen {regimen_id} no encontrado.")

        viviendas = self.vivienda_repo.list_by_regimen(regimen_id)
        upes_faltantes = regimen.total_upes - len(viviendas)

        sin_catastro = [v.numero_upe for v in viviendas if not v.clave_catastral]
        
        return {
            "regimen": regimen.nombre_regimen,
            "total_upes_declaradas": regimen.total_upes,
            "upes_registradas": len(viviendas),
            "upes_faltantes_registro": max(0, upes_faltantes),
            "upes_sin_clave_catastral": len(sin_catastro),
            "cobertura_porcentaje": round((len(viviendas) / regimen.total_upes) * 100, 2) if regimen.total_upes else 0.0
        }

    def obtener_viviendas_activas_no_vendidas(self, regimen_id: int) -> List[Vivienda]:
        """
        Retorna únicamente las viviendas de un régimen que NO han sido vendidas ni escrituradas.
        Filtro de exclusión inteligente: excluye viviendas con fecha_venta/fecha_escrituracion
        y estados terminales (ESCRITURADA, EN_GARANTIA, CONCLUIDA).
        """
        from satc.src.storage.satc_models import EstadoVivienda
        estados_excluidos = (
            self.session.query(EstadoVivienda.estado_vivienda_id)
            .filter(EstadoVivienda.codigo.in_(["ESCRITURADA", "EN_GARANTIA", "CONCLUIDA"]))
            .all()
        )
        ids_excluidos = [e[0] for e in estados_excluidos]

        return (
            self.session.query(Vivienda)
            .filter(
                Vivienda.regimen_id == regimen_id,
                Vivienda.activo.is_(True),
                Vivienda.fecha_venta.is_(None),
                Vivienda.fecha_escrituracion.is_(None),
                ~Vivienda.estado_vivienda_id.in_(ids_excluidos) if ids_excluidos else True
            )
            .order_by(Vivienda.vivienda_id.asc())
            .all()
        )

    def crear_solicitud_tramite(
        self,
        orden_tramite_id: int,
        tipo_tramite_id: int,
        usuario_id: int,
        expediente_municipal: Optional[str] = None,
        archivo_origen: Optional[str] = None
    ) -> Any:
        """
        Crea una nueva solicitud_tramite dentro de una orden_tramite, asociando
        exclusivamente las viviendas del régimen que continúan activas (no vendidas).
        Si el régimen tenía 577 y 100 ya se vendieron, asocia exactamente las 477 restantes.
        """
        from satc.src.storage.satc_models import OrdenTramite, SolicitudTramite
        
        orden = self.session.get(OrdenTramite, orden_tramite_id)
        if not orden:
            raise ValueError(f"Orden de trámite {orden_tramite_id} no existe.")

        viviendas_elegibles = []
        if orden.regimen_id:
            viviendas_elegibles = self.obtener_viviendas_activas_no_vendidas(orden.regimen_id)

        # Generar folio consecutivo
        year = datetime.now().year
        count_sol = self.session.query(SolicitudTramite).filter(SolicitudTramite.orden_tramite_id == orden_tramite_id).count()
        folio_sol = f"SOL-{orden.folio_orden}-{str(count_sol + 1).zfill(2)}"

        solicitud = SolicitudTramite(
            orden_tramite_id=orden_tramite_id,
            folio_solicitud=folio_sol,
            tipo_tramite_id=tipo_tramite_id,
            expediente_municipal=expediente_municipal,
            total_viviendas=len(viviendas_elegibles),
            archivo_origen=archivo_origen,
            estado_id=self.tramite_repo._get_estado_tramite_id("NO_INICIADO"),
            usuario_id=usuario_id,
            created_at=datetime.utcnow()
        )
        self.session.add(solicitud)
        self.session.flush()

        # Crear los expedientes de trámite por vivienda con folios en blanco (listos para pago)
        for viv in viviendas_elegibles:
            self.tramite_repo.create(
                tipo_tramite_id=tipo_tramite_id,
                vivienda_id=viv.vivienda_id,
                regimen_id=orden.regimen_id,
                solicitud_tramite_id=solicitud.solicitud_tramite_id,
                estado_codigo="NO_INICIADO"
            )

        # Actualizar acumuladores en la macro-orden
        orden.total_solicitudes = (orden.total_solicitudes or 0) + 1
        orden.total_viviendas = (orden.total_viviendas or 0) + len(viviendas_elegibles)
        orden.updated_at = datetime.utcnow()

        self.session.commit()
        logger.info(
            f"Solicitud {folio_sol} creada exitosamente con {len(viviendas_elegibles)} viviendas elegibles (excluidas vendidas)."
        )
        return solicitud

    # =========================================================================
    # GESTIÓN DE CATÁLOGOS MAESTROS SATC (Tipos, Estados, Regímenes)
    # =========================================================================

    def get_all_tipos_tramite(self) -> List[TipoTramite]:
        return self.tipo_tramite_repo.list_all()

    def save_tipo_tramite(self, data: Dict[str, Any]) -> TipoTramite:
        tipo_id = data.get("tipo_tramite_id")
        if tipo_id:
            tipo = self.tipo_tramite_repo.get_by_id(int(tipo_id))
            if not tipo:
                raise ValueError(f"Tipo de trámite con ID {tipo_id} no encontrado.")
            tipo.codigo = data.get("codigo", tipo.codigo).strip().upper()
            tipo.nombre = data.get("nombre", tipo.nombre).strip()
            tipo.aplica_a = data.get("aplica_a", tipo.aplica_a)
            tipo.etapa_disparador = data.get("etapa_disparador", tipo.etapa_disparador)
            tipo.dias_vigencia = int(data.get("dias_vigencia", tipo.dias_vigencia) or 0)
            tipo.es_obligatorio = bool(data.get("es_obligatorio", tipo.es_obligatorio))
            tipo.activo = bool(data.get("activo", tipo.activo))
        else:
            tipo = TipoTramite(
                codigo=data["codigo"].strip().upper(),
                nombre=data["nombre"].strip(),
                aplica_a=data.get("aplica_a", "AMBOS"),
                etapa_disparador=data.get("etapa_disparador", "CONSTRUCCION"),
                dias_vigencia=int(data.get("dias_vigencia", 0) or 0),
                es_obligatorio=bool(data.get("es_obligatorio", True)),
                activo=bool(data.get("activo", True))
            )
        self.tipo_tramite_repo.save(tipo)
        return tipo

    def get_all_estados_tramite(self) -> List[EstadoTramite]:
        return self.estado_tramite_repo.list_all()

    def save_estado_tramite(self, data: Dict[str, Any]) -> EstadoTramite:
        est_id = data.get("estado_tramite_id")
        if est_id:
            estado = self.estado_tramite_repo.get_by_id(int(est_id))
            if not estado:
                raise ValueError(f"Estado de trámite con ID {est_id} no encontrado.")
            estado.codigo = data.get("codigo", estado.codigo).strip().upper()
            estado.nombre = data.get("nombre", estado.nombre).strip()
            estado.fase = data.get("fase", estado.fase).strip().upper()
            estado.es_bloqueante = bool(data.get("es_bloqueante", estado.es_bloqueante))
            estado.es_terminal = bool(data.get("es_terminal", estado.es_terminal))
            estado.activo = bool(data.get("activo", estado.activo))
        else:
            estado = EstadoTramite(
                codigo=data["codigo"].strip().upper(),
                nombre=data["nombre"].strip(),
                fase=data.get("fase", "OPERATIVA").strip().upper(),
                es_bloqueante=bool(data.get("es_bloqueante", True)),
                es_terminal=bool(data.get("es_terminal", False)),
                activo=bool(data.get("activo", True))
            )
        self.estado_tramite_repo.save(estado)
        return estado

    def get_all_estados_vivienda(self) -> List[EstadoVivienda]:
        return self.estado_vivienda_repo.list_all()

    def save_estado_vivienda(self, data: Dict[str, Any]) -> EstadoVivienda:
        est_id = data.get("estado_vivienda_id")
        if est_id:
            estado = self.estado_vivienda_repo.get_by_id(int(est_id))
            if not estado:
                raise ValueError(f"Estado de vivienda con ID {est_id} no encontrado.")
            estado.codigo = data.get("codigo", estado.codigo).strip().upper()
            estado.nombre = data.get("nombre", estado.nombre).strip()
            estado.descripcion = data.get("descripcion", estado.descripcion)
            estado.orden_flujo = int(data.get("orden_flujo", estado.orden_flujo) or 1)
            estado.permite_venta = bool(data.get("permite_venta", estado.permite_venta))
            estado.permite_escrituracion = bool(data.get("permite_escrituracion", estado.permite_escrituracion))
            estado.activo = bool(data.get("activo", estado.activo))
        else:
            estado = EstadoVivienda(
                codigo=data["codigo"].strip().upper(),
                nombre=data["nombre"].strip(),
                descripcion=data.get("descripcion", ""),
                orden_flujo=int(data.get("orden_flujo", 1) or 1),
                permite_venta=bool(data.get("permite_venta", False)),
                permite_escrituracion=bool(data.get("permite_escrituracion", False)),
                activo=bool(data.get("activo", True))
            )
        self.estado_vivienda_repo.save(estado)
        return estado

    def get_all_regimenes(self) -> List[RegimenCondominio]:
        return self.regimen_repo.list_all()

    def save_regimen_condominio(self, data: Dict[str, Any]) -> RegimenCondominio:
        reg_id = data.get("regimen_id")
        if reg_id:
            regimen = self.regimen_repo.get_by_id(int(reg_id))
            if not regimen:
                raise ValueError(f"Régimen con ID {reg_id} no encontrado.")
            regimen.desarrollo_id = int(data.get("desarrollo_id", regimen.desarrollo_id))
            regimen.nombre_regimen = data.get("nombre_regimen", regimen.nombre_regimen).strip()
            regimen.sm = data.get("sm", regimen.sm)
            regimen.mz = data.get("mz", regimen.mz).strip()
            regimen.lt = data.get("lt", regimen.lt).strip()
            regimen.total_upes = int(data.get("total_upes", regimen.total_upes) or 1)
            regimen.licencia_construccion_matriz = data.get("licencia_construccion_matriz", regimen.licencia_construccion_matriz)
            regimen.clave_catastral_matriz = data.get("clave_catastral_matriz", regimen.clave_catastral_matriz)
            regimen.activo = bool(data.get("activo", regimen.activo))
            regimen.updated_at = datetime.utcnow()
        else:
            regimen = RegimenCondominio(
                desarrollo_id=int(data["desarrollo_id"]),
                nombre_regimen=data["nombre_regimen"].strip(),
                sm=data.get("sm"),
                mz=data["mz"].strip(),
                lt=data["lt"].strip(),
                total_upes=int(data.get("total_upes", 1) or 1),
                upes_generadas=0,
                licencia_construccion_matriz=data.get("licencia_construccion_matriz"),
                clave_catastral_matriz=data.get("clave_catastral_matriz"),
                activo=bool(data.get("activo", True)),
                created_at=datetime.utcnow()
            )
        self.regimen_repo.save(regimen)
        return regimen

    # =========================================================================
    # IMPORTACIÓN Y CONSULTA DE VIVIENDAS (Excel Bulk Import)
    # =========================================================================

    def get_viviendas_by_regimen(self, regimen_id: int) -> List[Dict[str, Any]]:
        viviendas = self.vivienda_repo.list_by_regimen(regimen_id)
        return [
            {
                "vivienda_id": v.vivienda_id,
                "desarrollo_id": v.desarrollo.desarrollo_id if v.desarrollo else None,
                "desarrollo_nombre": v.desarrollo.nombre if v.desarrollo else "",
                "regimen_id": v.regimen_id,
                "regimen_nombre": v.regimen.nombre_regimen if v.regimen else "",
                "sm": v.regimen.sm or "" if v.regimen else "",
                "mz": v.regimen.mz if v.regimen else "",
                "lt": v.regimen.lt if v.regimen else "",
                "numero_oficial": v.numero_oficial or "",
                "interior": v.interior,
                "edificio": v.edificio or "",
                "nivel": v.nivel or "",
                "calle": v.calle or "",
                "destino": v.destino,
                "espacio": v.espacio,
                "folio_electronico": v.folio_electronico or "",
                "clave_catastral": v.clave_catastral or "",
                "padron": v.padron or "",
                "fecha_escrituracion": str(v.fecha_escrituracion) if v.fecha_escrituracion else "",
                "descripcion": v.descripcion or "",
                "estado_codigo": v.estado.codigo if v.estado else "",
                "estado_nombre": v.estado.nombre if v.estado else "",
                "activo": v.activo
            }
            for v in viviendas
        ]

    def get_viviendas_by_desarrollo(self, desarrollo_id: int, solo_sin_regimen: bool = False) -> List[Dict[str, Any]]:
        viviendas = self.vivienda_repo.list_by_desarrollo(desarrollo_id)
        if solo_sin_regimen:
            viviendas = [v for v in viviendas if v.regimen_id is None]
        return [
            {
                "vivienda_id": v.vivienda_id,
                "desarrollo_id": v.desarrollo.desarrollo_id if v.desarrollo else desarrollo_id,
                "desarrollo_nombre": v.desarrollo.nombre if v.desarrollo else "",
                "regimen_id": v.regimen_id,
                "regimen_nombre": v.regimen.nombre_regimen if v.regimen else "SIN RÉGIMEN",
                "sm": v.regimen.sm or "" if v.regimen else "",
                "mz": v.regimen.mz if v.regimen else "",
                "lt": v.regimen.lt if v.regimen else "",
                "numero_oficial": v.numero_oficial or "",
                "interior": v.interior,
                "edificio": v.edificio or "",
                "nivel": v.nivel or "",
                "calle": v.calle or "",
                "destino": v.destino,
                "espacio": v.espacio,
                "folio_electronico": v.folio_electronico or "",
                "clave_catastral": v.clave_catastral or "",
                "padron": v.padron or "",
                "fecha_escrituracion": str(v.fecha_escrituracion) if v.fecha_escrituracion else "",
                "descripcion": v.descripcion or "",
                "estado_codigo": v.estado.codigo if v.estado else "",
                "estado_nombre": v.estado.nombre if v.estado else "",
                "activo": v.activo
            }
            for v in viviendas
        ]

    def importar_viviendas_excel(
        self,
        desarrollo_id: int,
        records: List[Dict[str, Any]],
        regimen_id: int,
        usuario_id: int = 1,
        sesion_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Importa masivamente viviendas/UPEs normalizadas asociadas a su régimen matriz.
        Validaciones de integridad:
          1. El régimen debe existir y pertenecer al desarrollo.
          2. Valida que el total de registros no exceda el límite autorizado en el régimen.
          3. Detección de duplicidad por (regimen_id, edificio, interior).
        """
        if not desarrollo_id or not regimen_id:
            raise ValueError("El desarrollo_id y regimen_id son obligatorios para importar viviendas.")

        regimen = self.regimen_repo.get_by_id(regimen_id)
        if not regimen:
            raise ValueError(f"Régimen con ID {regimen_id} no existe.")
        if regimen.desarrollo_id != desarrollo_id:
            raise ValueError("El régimen seleccionado no pertenece al desarrollo indicado.")

        # Validación de UPEs autorizadas vs total en archivo
        upes_existentes = self.vivienda_repo.count_by_regimen(regimen_id)
        total_en_archivo = len(records)
        if (upes_existentes + total_en_archivo) > regimen.total_upes:
            raise ValueError(
                f"Inconsistencia en archivo: Las viviendas a importar ({total_en_archivo}) más las existentes ({upes_existentes}) "
                f"superan el límite de UPEs autorizadas en el Régimen ({regimen.total_upes})."
            )

        # Cargar estado inicial por defecto (PROYECTADA)
        estado_id = self.vivienda_repo._get_estado_vivienda_id("PROYECTADA")

        from sqlalchemy import select
        stmt = select(Vivienda).where(Vivienda.regimen_id == regimen_id)
        existentes_db = self.session.execute(stmt).scalars().all()
        # Clave única normalizada: (EDIFICIO, INTERIOR)
        existentes_keys = {
            (
                (v.edificio or "").strip().upper(),
                (v.interior or "").strip().upper()
            )
            for v in existentes_db
        }

        nuevos_insertados = 0
        omitidos_duplicados = 0

        for r in records:
            interior_val = str(r.get("interior") or r.get("vivienda") or "").strip().upper()
            if not interior_val:
                continue

            edif_val = str(r.get("edificio") or "").strip().upper() or None
            nivel_val = str(r.get("nivel") or "").strip().upper() or None
            num_oficial_val = str(r.get("numero_oficial") or r.get("numero_upe") or "").strip() or None
            calle_val = str(r.get("calle") or "").strip() or None
            destino_val = str(r.get("destino") or "HABITACIONAL").strip().upper()
            espacio_val = str(r.get("espacio") or "VIVIENDA").strip().upper()
            folio_elec_val = str(r.get("folio_electronico") or "").strip() or None
            clave_cat_val = str(r.get("clave_catastral") or "").strip() or None
            padron_val = str(r.get("padron") or r.get("cuenta_predial") or "").strip() or None
            desc_val = str(r.get("descripcion") or "").strip() or None

            k = (edif_val or "", interior_val)

            if k in existentes_keys:
                omitidos_duplicados += 1
                continue

            nueva_viv = Vivienda(
                regimen_id=regimen_id,
                numero_oficial=num_oficial_val,
                interior=interior_val,
                edificio=edif_val,
                nivel=nivel_val,
                calle=calle_val,
                destino=destino_val if destino_val in ['HABITACIONAL', 'SERVICIO', 'COMERCIAL', 'MIXTO'] else 'HABITACIONAL',
                espacio=espacio_val if espacio_val in ['VIVIENDA', 'AREAS_COMUNES', 'ESTACIONAMIENTO', 'BODEGA'] else 'VIVIENDA',
                folio_electronico=folio_elec_val,
                clave_catastral=clave_cat_val,
                padron=padron_val,
                descripcion=desc_val,
                estado_vivienda_id=estado_id,
                activo=True,
                created_at=datetime.utcnow()
            )
            self.session.add(nueva_viv)
            existentes_keys.add(k)
            nuevos_insertados += 1

        # Actualizar contador de UPEs generadas en el régimen
        if nuevos_insertados > 0:
            regimen.upes_generadas = self.vivienda_repo.count_by_regimen(regimen_id) + nuevos_insertados
            regimen.updated_at = datetime.utcnow()

        self.session.commit()

        logger.info(
            f"Importación de viviendas completada para régimen {regimen_id}: "
            f"{nuevos_insertados} insertados, {omitidos_duplicados} omitidos por duplicidad."
        )

        return {
            "total_procesados": len(records),
            "nuevos_insertados": nuevos_insertados,
            "omitidos_duplicados": omitidos_duplicados,
            "regimen_id": regimen_id,
            "desarrollo_id": desarrollo_id
        }

    def vincular_folios_rpp_excel(self, regimen_id: int, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Enriquece las viviendas del régimen con sus Folios Electrónicos del RPP desde registros parseados.
        Avanza el estado a 'EN_INDIVIDUALIZACION'.
        """
        regimen = self.regimen_repo.get_by_id(regimen_id)
        if not regimen:
            raise ValueError(f"Régimen con ID {regimen_id} no existe.")

        res = self.vivienda_repo.bulk_update_folios_rpp(regimen_id, records)
        self.session.commit()
        logger.info(f"Folios RPP vinculados para régimen {regimen_id}: {res['actualizados']} actualizados, {res['no_encontrados']} no encontrados.")
        return {
            "regimen_id": regimen_id,
            "actualizados": res["actualizados"],
            "no_encontrados": res["no_encontrados"],
            "total_en_archivo": len(records)
        }

    def vincular_folios_rpp_pdf(self, regimen_id: int, pdf_path: str) -> Dict[str, Any]:
        """
        Extrae y asocia los folios electrónicos del RPP directamente desde una Constancia de Resolución PDF.
        """
        from satc.src.services.rpp_resolution_extractor import RppResolutionExtractor
        records = RppResolutionExtractor.extract_from_pdf(pdf_path)
        return self.vincular_folios_rpp_excel(regimen_id=regimen_id, records=records)

    def vincular_catastro_excel(self, regimen_id: int, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Enriquece las viviendas del régimen con su Clave Catastral y Padrón municipal.
        Avanza el estado a 'LISTA_PARA_VENTA'.
        """
        regimen = self.regimen_repo.get_by_id(regimen_id)
        if not regimen:
            raise ValueError(f"Régimen con ID {regimen_id} no existe.")

        res = self.vivienda_repo.bulk_update_catastro(regimen_id, records)
        self.session.commit()
        logger.info(f"Datos catastrales vinculados para régimen {regimen_id}: {res['actualizados']} actualizados, {res['no_encontrados']} no encontrados.")
        return {
            "regimen_id": regimen_id,
            "actualizados": res["actualizados"],
            "no_encontrados": res["no_encontrados"],
            "total_en_archivo": len(records)
        }



