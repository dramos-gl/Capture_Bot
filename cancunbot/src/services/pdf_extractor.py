"""
CancunBot — Extractor de Datos de PDF de Recibo Electrónico
Extrae los campos estructurados del PDF usando pdfplumber y expresiones regulares.
"""
import re
import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pdfplumber

logger = logging.getLogger(__name__)


@dataclass
class DatosRecibo:
    """
    Estructura de datos extraídos del PDF del recibo electrónico.
    Todos los campos son opcionales para tolerancia ante variaciones del formato.
    """
    folio_pase_caja: Optional[str] = None
    folio_electronico: Optional[str] = None
    fecha_expedicion: Optional[str] = None      # Formato: YYYY-MM-DD
    hora_expedicion: Optional[str] = None       # Formato: HH:MM:SS
    lugar_expedicion: Optional[str] = None
    rfc: Optional[str] = None
    contribucion: Optional[str] = None
    nombre_contribuyente: Optional[str] = None
    concepto: Optional[str] = None
    total: Optional[float] = None
    forma_pago: Optional[str] = None
    padron: Optional[str] = None
    clave_catastral: Optional[str] = None
    sm: Optional[str] = None
    mz: Optional[str] = None
    l: Optional[str] = None
    datos_adicionales: dict = field(default_factory=dict)


class PdfExtractor:
    """
    Extrae datos estructurados del PDF de recibo electrónico de la Tesorería de Cancún.
    
    Estrategia de extracción:
    1. Extrae el texto completo del PDF con pdfplumber.
    2. Aplica expresiones regulares para cada campo esperado.
    3. Los campos no encontrados quedan como None.
    4. Los campos no reconocidos se capturan en datos_adicionales.
    
    NOTA: Los patrones regex deberán ajustarse al formato real del PDF
    tras obtener una muestra del documento durante la fase DEV-04.
    """

    # Patrones de extracción (se ajustan tras inspeccionar PDF real)
    _PATRONES: dict[str, str] = {
        "folio_pase_caja":      r"FOLIO\s+PASE\s+DE\s+CAJA[:\s]+([A-Z0-9\-]+)",
        "folio_electronico":    r"FOLIO\s+ELECTR[ÓO]NICO[:\s]+([A-Z0-9\-]+)",
        "fecha_expedicion":     r"FECHA\s+DE\s+EXPEDICI[ÓO]N[:\s]+(\d{2}/\d{2}/\d{4})",
        "hora_expedicion":      r"HORA\s+DE\s+EXPEDICI[ÓO]N[:\s]+(\d{2}:\d{2}(?::\d{2})?)",
        "lugar_expedicion":     r"LUGAR\s+DE\s+EXPEDICI[ÓO]N[:\s]+(.+?)(?:\n|RFC)",
        "rfc":                  r"\bRFC[:\s]+([A-Z&]{3,4}\d{6}[A-Z0-9]{3})\b",
        "contribucion":         r"CONTRIBUCI[ÓO]N[:\s]+(.+?)(?:\n|DATOS)",
        "nombre_contribuyente": r"NOMBRE[:\s]+(.+?)(?:\n|FOLIO|RFC)",
        "concepto":             r"CONCEPTO[:\s]+(.+?)(?:\n|TOTAL|FORMA)",
        "total":                r"TOTAL[:\s]+\$?\s*([\d,]+\.?\d*)",
        "forma_pago":           r"FORMA\s+DE\s+PAGO[:\s]+(.+?)(?:\n|$)",
        "padron":               r"PADR[OÓ]N[:\s]+([A-Z0-9\-]+)",
        "clave_catastral":      r"CLAVE\s+CATASTRAL[:\s]+([A-Z0-9\-]+)",
    }

    def extraer(self, ruta_pdf: str, db_session=None) -> DatosRecibo:
        """
        Extrae los datos del PDF de recibo.
        
        Args:
            ruta_pdf: Ruta al archivo PDF descargado
            db_session: Sesión activa de base de datos para recuperar parámetros
        """
        ruta = Path(ruta_pdf)
        if not ruta.exists():
            raise FileNotFoundError(f"PDF no encontrado: {ruta_pdf}")

        logger.info(f"Extrayendo datos del PDF: {ruta.name}")

        # Extrae todo el texto del PDF
        texto_completo = self._extraer_texto(ruta_pdf)
        if not texto_completo:
            logger.warning(f"No se pudo extraer texto del PDF: {ruta.name}")
            return DatosRecibo()

        datos = DatosRecibo()

        # Aplica cada patrón
        for campo, patron in self._PATRONES.items():
            valor = self._aplicar_patron(texto_completo, patron)
            if valor:
                setattr(datos, campo, valor)
                logger.debug(f"Campo '{campo}': '{valor}'")
            else:
                logger.debug(f"Campo '{campo}': no encontrado")

        # Post-procesamiento
        if datos.nombre_contribuyente:
            datos.nombre_contribuyente = self.clean_nombre_contribuyente(datos.nombre_contribuyente)
        if datos.fecha_expedicion:
            datos.fecha_expedicion = self._normalizar_fecha(datos.fecha_expedicion)
        if datos.total:
            try:
                datos.total = float(str(datos.total).replace(",", ""))
            except ValueError:
                logger.warning(f"No se pudo convertir total a float: '{datos.total}'")
                datos.total = None

        # 1. Extraer y aislar la sección "DETALLE CONCEPTO DE COBRO:" del texto completo
        detalle_cobro_seccion = ""
        detalle_match = re.search(
            r"DETALLE\s+CONCEPTO\s+DE\s+COBRO:\s*(.+?)(?=\n(?:CONCEPTOS|Aviso|TOTAL|$))", 
            texto_completo, 
            re.IGNORECASE | re.DOTALL
        )
        if detalle_match:
            detalle_cobro_seccion = detalle_match.group(1).strip()
            # Guardamos el detalle crudo en datos adicionales con la clave sugerida para evitar confusión
            datos.datos_adicionales["detalle_concepto"] = detalle_cobro_seccion
            logger.debug(f"Sección Detalle Concepto de Cobro aislada: '{detalle_cobro_seccion}'")

        # 2. Extraer SM, MZ, L, Padrón y Clave Catastral ÚNICAMENTE de la sección DETALLE CONCEPTO DE COBRO
        if detalle_cobro_seccion:
            # Buscar SM (Super Manzana o SM)
            sm_match = re.search(r"\b(?:SUPER\s*MANZANA|SM)[\s\-]*([A-Z0-9\-]+)\b", detalle_cobro_seccion, re.IGNORECASE)
            if sm_match:
                datos.sm = sm_match.group(1).strip()
            else:
                datos.sm = None
            
            # Buscar MZ (Manzana, Mz, M, Lote)
            mz_match = re.search(r"\b(?:MANZANA|MZ|M)[\s\-\.]*([A-Z0-9\-]+)\b", detalle_cobro_seccion, re.IGNORECASE)
            if mz_match:
                datos.mz = mz_match.group(1).strip()
            else:
                datos.mz = None

            # Buscar L (Lote, Lt, L. con delimitadores opcionales)
            l_match = re.search(r"\b(?:LOTE|LT|L)[\s\-\.]*([A-Z0-9\-]+)\b", detalle_cobro_seccion, re.IGNORECASE)
            if l_match:
                datos.l = l_match.group(1).strip()
            else:
                datos.l = None

            # Padrón (Padron o Padrón)
            padron_match = re.search(r"\b(?:PADR[OÓ]N)[\s\-:]*([A-Z0-9\-]+)\b", detalle_cobro_seccion, re.IGNORECASE)
            if padron_match:
                datos.padron = padron_match.group(1).strip()
            else:
                datos.padron = None

            # Clave Catastral
            clave_match = re.search(r"\b(?:CLAVE\s+CATASTRAL|CLAVE)[\s\-:]*([A-Z0-9\-]+)\b", detalle_cobro_seccion, re.IGNORECASE)
            if clave_match:
                datos.clave_catastral = clave_match.group(1).strip()
            else:
                datos.clave_catastral = None

            # Validación de clave catastral
            if datos.clave_catastral:
                municipio_context = "CANCUN"
                lugar = (datos.lugar_expedicion or "").upper()
                if "SOLIDARIDAD" in lugar or "PLAYA" in lugar or "TULUM" in lugar:
                    municipio_context = "PLAYA"
                datos.clave_catastral = self.validar_clave_catastral(datos.clave_catastral, municipio_context, db_session)
        else:
            # Si no viene la sección de detalle de cobro, forzamos valores nulos
            datos.sm = None
            datos.mz = None
            datos.l = None
            datos.padron = None
            datos.clave_catastral = None

        # 3. Extraer e inteligenciar la sección de CONCEPTOS (Evitar duplicidades o códigos y dejar el concepto limpio y resumido)
        # Extrae la tabla desde CONCEPTOS hasta el TOTAL del final
        conceptos_tabla_match = re.search(
            r"CONCEPTOS\s+CANTIDAD\s+IMPORTE\s*(.+?)(?=\n(?:TOTAL|$))", 
            texto_completo, 
            re.IGNORECASE | re.DOTALL
        )
        if conceptos_tabla_match:
            lineas_conceptos = [linea.strip() for linea in conceptos_tabla_match.group(1).split("\n") if linea.strip()]
            conceptos_limpios = []
            
            for linea in lineas_conceptos:
                # Ejemplo linea: 1801010019 - I.A.D.S.10% DE IMPUESTO PREDIAL 1 $44.00
                # Removemos código numérico inicial, guiones iniciales, cantidades e importes finales
                # Regex limpia código inicial (ej: 1801010019 -)
                linea_sin_codigo = re.sub(r"^\d+\s*[-–]\s*", "", linea).strip()
                # Regex limpia cantidad e importe final (ej: 1 $44.00)
                linea_sin_importes = re.sub(r"\s+\d+\s+\$?\s*[\d,]+\.?\d*$", "", linea_sin_codigo).strip()
                
                # Normalizar redundancias usando un diccionario dinámico cargado de concept_mapping.json
                mapped_value = None
                try:
                    import json
                    # Usamos la clase Path importada a nivel de módulo
                    mapping_path = Path(__file__).parents[2] / "concept_mapping.json"
                    
                    if mapping_path.exists():
                        with open(mapping_path, "r", encoding="utf-8") as f:
                            config_map = json.load(f).get("MAP_CONCEPTOS", {})
                            for keyword, replacement in config_map.items():
                                if keyword.upper() in linea_sin_importes.upper():
                                    mapped_value = replacement
                                    break
                except Exception as json_err:
                    logger.warning(f"No se pudo leer concept_mapping.json ({json_err}). Usando fallbacks de seguridad.")

                if mapped_value:
                    conceptos_limpios.append(mapped_value)
                elif "PREDIAL" in linea_sin_importes:
                    conceptos_limpios.append("IMPUESTO PREDIAL")
                elif "OBRA PUBLICA" in linea_sin_importes:
                    conceptos_limpios.append("CONSTANCIA DE COOPERACION POR OBRA")
                elif linea_sin_importes:
                    conceptos_limpios.append(linea_sin_importes)
            
            # Unir sin duplicados (set preservando orden)
            conceptos_unicos = []
            for c in conceptos_limpios:
                if c not in conceptos_unicos:
                    conceptos_unicos.append(c)
            
            # Guardar el concepto resultante e inteligenciado
            if conceptos_unicos:
                datos.concepto = " / ".join(conceptos_unicos)
                logger.info(f"Concepto de cobro inteligenciado resultante: '{datos.concepto}'")
            else:
                datos.concepto = datos.concepto or "PREDIAL"
        else:
            # Fallback si no logra aislar la sección de conceptos
            if datos.concepto:
                val_concepto = datos.concepto.upper()
                if "PREDIAL" in val_concepto:
                    datos.concepto = "IMPUESTO PREDIAL"
                elif "OBRA PUBLICA" in val_concepto:
                    datos.concepto = "CONSTANCIA DE COOPERACION POR OBRA"

        # Buscar e inyectar Referencia Bancaria/Identificador en datos adicionales
        if texto_completo:
            ref_bancaria = self.extract_bancaria_ref(texto_completo)
            if ref_bancaria:
                datos.datos_adicionales["referencia_bancaria"] = ref_bancaria
                logger.info(f"Referencia bancaria de pago detectada: {ref_bancaria}")

        logger.info(
            f"Extracción completada: RFC={datos.rfc}, "
            f"Folio={datos.folio_electronico}, Total={datos.total}, "
            f"SM={datos.sm}, MZ={datos.mz}, L={datos.l}, "
            f"Clave Catastral={datos.clave_catastral}"
        )
        return datos

    def calcular_hash(self, ruta_pdf: str) -> str:
        """Calcula el hash SHA256 del archivo PDF para verificación de integridad."""
        sha256 = hashlib.sha256()
        with open(ruta_pdf, "rb") as f:
            for bloque in iter(lambda: f.read(4096), b""):
                sha256.update(bloque)
        return sha256.hexdigest()

    def _extraer_texto(self, ruta_pdf: str) -> str:
        """Extrae el texto completo de todas las páginas del PDF."""
        try:
            with pdfplumber.open(ruta_pdf) as pdf:
                texto = "\n".join(
                    pagina.extract_text() or ""
                    for pagina in pdf.pages
                )
            return texto.upper()  # Normaliza a mayúsculas para facilitar matching
        except Exception as e:
            logger.error(f"Error al abrir PDF con pdfplumber: {e}")
            return ""

    def _aplicar_patron(self, texto: str, patron: str) -> Optional[str]:
        """Aplica un patrón regex al texto y retorna el primer grupo capturado."""
        try:
            match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        except re.error as e:
            logger.error(f"Error en patrón regex '{patron}': {e}")
        return None

    def validar_clave_catastral(self, clave: str, municipio: str = "CANCUN", db_session=None) -> Optional[str]:
        """
        Valida de forma estricta la clave catastral extraída por municipio.
        Si se pasa db_session, busca patrones dinámicos en los parámetros de la base de datos:
          - CATASTRO_PATRON_CANCUN (separados por comas)
          - CATASTRO_PATRON_PLAYA (separados por comas)
        Si no se define o falla, utiliza las expresiones regulares por defecto en código.
        """
        if not clave:
            return None
        
        # Limpieza básica de espacios y guiones
        val = clave.strip().upper()
        
        # Regla general: no puede iniciar con '0'
        if val.startswith("0"):
            logger.warning(f"Clave catastral rechazada: Inicia con cero ({val})")
            return None

        # Intentar cargar patrones desde la base de datos para no dejar hardcoded las reglas
        patrones_db = None
        if db_session:
            try:
                param_name = f"CATASTRO_PATRON_{municipio.upper()}"
                # Evitar colisión o dependencias circulares importando de forma tardía
                from sqlalchemy import text
                res = db_session.execute(
                    text("SELECT valor FROM sar_configuracion.parametro_sistema WHERE codigo = :c AND activo = true"),
                    {"c": param_name}
                ).fetchone()
                if res and res[0]:
                    # Patrones guardados separados por comas
                    patrones_db = [p.strip() for p in res[0].split(",") if p.strip()]
                    logger.info(f"Cargados {len(patrones_db)} patrones dinámicos desde BD para {municipio}")
            except Exception as db_err:
                logger.warning(f"No se pudieron consultar patrones dinámicos en BD ({db_err}). Usando fallbacks locales.")

        if municipio.upper() == "CANCUN":
            # Cancún soporta 3 variantes exactas por defecto en código
            patrones_cancun = patrones_db if patrones_db else [
                r"^[1-9][0-9]{17}$",         # 18 dígitos
                r"^[1-9][0-9]{6}[A-Z][0-9]{10}$", # 18 caracteres (1 letra en posición 8)
                r"^[1-9][0-9]{5}[A-Z][0-9]{10}$", # 17 caracteres (1 letra en posición 7)
            ]
            
            # Buscar coincidencia
            for pat in patrones_cancun:
                try:
                    if re.match(pat, val):
                        return val
                except re.error as e:
                    logger.error(f"Patrón regex inválido cargado desde BD: '{pat}' ({e})")
            
            # Intento de rescate si el patrón tiene una letra en otra posición intermedia
            if len(val) in (17, 18) and re.match(r"^[1-9][A-Z0-9]+$", val):
                if len(re.findall(r"\d", val)) >= 15:
                    logger.info(f"Clave catastral de Cancún aceptada con variante especial: {val}")
                    return val

            logger.warning(f"Clave catastral de Cancún no cumple formato estricto: {val}")
            return None

        elif municipio.upper() in ("PLAYA_DEL_CARMEN", "PLAYA", "TULUM", "SOLIDARIDAD"):
            # Playa del Carmen / Tulum soporta 2 variantes exactas (no admite letras) por defecto en código:
            # 1. Base de 15 dígitos con guion y sufijo opcional de 1 a 3 dígitos
            # 2. 15 dígitos numéricos exactos sin guion
            patrones_playa = patrones_db if patrones_db else [
                r"^[1-9][0-9]{14}-\d{1,3}$",
                r"^[1-9][0-9]{14}$"
            ]
            
            # Buscar coincidencia
            for pat in patrones_playa:
                try:
                    if re.match(pat, val):
                        return val
                except re.error as e:
                    logger.error(f"Patrón regex inválido cargado desde BD para Playa: '{pat}' ({e})")
                
            logger.warning(f"Clave catastral de Playa/Tulum no cumple formato estricto: {val}")
            return None

        return val # Retorno general si es otro municipio

    def clean_nombre_contribuyente(self, nombre: str) -> Optional[str]:
        """
        Limpia el nombre del contribuyente eliminando las denominaciones legales comunes,
        removiendo comas y puntos excedentes, y normalizando erratas comunes.
        
        Ejemplos:
          - CADU INMOBILIARIA, S.A. DE C.V.  -> CADU INMOBILIARIA
          - CADU RECIDENCIAS, S.A. DE C.V.   -> CADU RESIDENCIAS
          - CADURMA, S.A. DE C.V.            -> CADURMA
        """
        if not nombre:
            return None
        
        # Pasar a mayúsculas y limpiar espacios iniciales/finales
        val = nombre.strip().upper()
        
        # 1. Correcciones de erratas comunes solicitadas
        val = val.replace("RECIDENCIAS", "RESIDENCIAS")
        
        # 2. Remover denominaciones comerciales y sociedades (con/sin puntos y comas)
        patrones_legales = [
            r"\bS\.?\s*A\.?\s+DE\s+C\.?\s*V\.?\b",  # S.A. DE C.V.
            r"\bS\.?\s*DE\s+R\.?\s*L\.?\s+DE\s+C\.?\s*V\.?\b", # S. DE R.L. DE C.V.
            r"\bS\.?\s*A\.?\s*P\.?\s*I\.?\s+DE\s+C\.?\s*V\.?\b", # S.A.P.I. DE C.V.
            r"\bS\.?\s*C\.?\b", # S.C.
            r"\bS\.?\s*A\.?\b", # S.A.
            r"\bA\.?\s*C\.?\b", # A.C.
            r"\bS\.?\s*R\.?\s*L\.?\b", # S.R.L.
            r"\bFIDEICOMISO\b" # Limpiar duplicaciones si las hubiera (opcional)
        ]
        
        for pat in patrones_legales:
            val = re.sub(pat, "", val, flags=re.IGNORECASE)
            
        # 3. Remover caracteres de puntuación colgados al final de las palabras (como comas o puntos remanentes)
        val = re.sub(r"[\.,\s]+$", "", val)
        val = re.sub(r"^[\.,\s]+", "", val)
        
        # 4. Remover dobles espacios intermedios
        val = re.sub(r"\s+", " ", val).strip()
        
        return val if val else None

    def extract_bancaria_ref(self, texto: str) -> Optional[str]:
        """
        Extrae la referencia bancaria o identificador del recibo de pago relacionado.
        Ej. F-2026-659-9915
        """
        if not texto:
            return None
        # Patrón típico de folio bancario electrónico emitido por el portal de Cancún
        match = re.search(r"\b(F-\d{4}-\d{3,4}-\d{4,7})\b", texto, re.IGNORECASE)
        if match:
            return match.group(1).strip().upper()
        return None

    def _normalizar_fecha(self, fecha_str: str) -> str:
        """
        Normaliza la fecha al formato YYYY-MM-DD.
        Acepta: DD/MM/YYYY, D/M/YYYY
        """
        try:
            from datetime import datetime
            for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(fecha_str.strip(), fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        except Exception:
            pass
        return fecha_str  # Retorna tal cual si no puede normalizar
