"""
SATC — Metadata Extraction & Validation Service (Metadata-Driven Engine)
Provee el motor centralizado de extracción documental, validación estructural,
cascada de prioridad y ventanas deslizantes (sliding windows) desacoplado del código fuente.
"""
import re
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("SATC_METADATA_ENGINE")


class MetadataExtractionService:
    """
    Motor inteligente de validación y extracción gobernado por parámetros de base de datos
    (satc_configuracion.campo_canonico, campo_etiqueta_ancla, campo_formato_municipio).
    
    Implementa:
    1. Reglas Globales: No inicia con 0, solo alfanumérico y guiones.
    2. Cascada de Búsqueda:
       - Intento 1: Por Etiqueta / Ancla indicadora.
       - Intento 2: Caída Estructural Cancún (Observaciones + Ventanas Deslizantes en bloques fusionados).
       - Intento 3: Caída Estructural Playa / Tulum (Patrón numérico directo).
       - Intento 4: Patrón Segmentado con Guiones Múltiples.
    3. Caché de compilación regex en memoria para alto rendimiento.
    """

    _cache_formatos_mun: Dict[int, List[Dict[str, Any]]] = {}
    _cache_anclas_campo: Dict[str, List[re.Pattern]] = {}
    _cache_compiled_rules: Dict[int, List[Dict[str, Any]]] = {}

    def __init__(self, session=None):
        self.session = session

    @classmethod
    def clear_cache(cls):
        """Invalida la caché para forzar recarga en caliente tras cambios en la BD."""
        cls._cache_formatos_mun.clear()
        cls._cache_anclas_campo.clear()
        cls._cache_compiled_rules.clear()
        logger.info("MetadataExtractionService: Caché de patrones de extracción invalidada.")

    def _ensure_cache_loaded(self, municipio_id: Optional[int] = None):
        """Carga y compila en memoria las reglas desde satc_configuracion."""
        if not self.session:
            return

        from satc.src.storage.satc_repos import MetadataRulesRepository
        repo = MetadataRulesRepository(self.session)

        # Cargar anclas si están vacías
        if not self._cache_anclas_campo:
            campos = repo.list_campos(solo_activos=True)
            for c in campos:
                patterns = []
                for a in sorted(c.anclas, key=lambda x: x.prioridad):
                    if a.activo:
                        try:
                            patterns.append(re.compile(a.regex_ancla, re.IGNORECASE))
                        except Exception as e:
                            logger.error(f"Error compilando regex ancla '{a.etiqueta}': {e}")
                self._cache_anclas_campo[c.codigo] = patterns

        # Cargar formatos del municipio
        if municipio_id and municipio_id not in self._cache_compiled_rules:
            formatos = repo.list_formatos_by_municipio(municipio_id, solo_activos=True)
            compiled_list = []
            for f in formatos:
                try:
                    compiled_list.append({
                        "formato_id": f.formato_id,
                        "codigo_campo": f.campo.codigo,
                        "nombre_variante": f.nombre_variante,
                        "prioridad": f.prioridad,
                        "regex_extraccion": re.compile(f.regex_extraccion, re.IGNORECASE),
                        "regex_validacion": re.compile(f.regex_validacion),
                        "longitud_min": f.longitud_min,
                        "longitud_max": f.longitud_max,
                        "remover_caracteres": f.remover_caracteres or " -/",
                        "permite_sliding_window": f.permite_sliding_window,
                        "descripcion_error": f.descripcion_error or "Formato no válido"
                    })
                except Exception as e:
                    logger.error(f"Error compilando formato municipal '{f.nombre_variante}': {e}")
            self._cache_compiled_rules[municipio_id] = compiled_list

    def es_clave_catastral_valida(self, valor_raw: str, municipio_id: Optional[int] = None) -> Tuple[bool, str, str]:
        """
        Valida exhaustivamente una clave catastral según las reglas globales y las
        variantes estructurales del municipio.
        Retorna: (es_valido: bool, valor_limpio: str, mensaje_error: str)
        """
        if not valor_raw:
            return False, "", "Clave catastral vacía."

        # Limpieza básica
        val = str(valor_raw).strip().upper()

        # Regla Global 1: Nunca inicia con 0
        if val.startswith("0"):
            return False, val, "La clave catastral nunca debe iniciar con el dígito 0."

        # Regla Global 2: Solo caracteres alfanuméricos y guiones
        if not re.match(r'^[A-Z0-9\-]+$', val):
            return False, val, "La clave catastral solo permite caracteres alfanuméricos y guiones."

        if not municipio_id:
            # Fallback genérico si no se especificó municipio: validar longitud mínima típica (15)
            clean_digits = re.sub(r'[\s\-]+', '', val)
            if len(clean_digits) >= 15:
                return True, val, ""
            return False, val, "Longitud insuficiente para clave catastral."

        self._ensure_cache_loaded(municipio_id)
        rules = self._cache_compiled_rules.get(municipio_id, [])
        catastro_rules = [r for r in rules if r["codigo_campo"] == "clave_catastral"]

        if not catastro_rules:
            # Si no hay reglas configuradas para ese municipio, aceptar formato estándar
            return True, val, ""

        # Evaluar variantes en cascada por prioridad
        errores = []
        for rule in catastro_rules:
            # Limpiar caracteres declarados en remover_caracteres si aplica
            chars_to_strip = rule["remover_caracteres"]
            val_to_check = val
            if chars_to_strip:
                for c in chars_to_strip:
                    val_to_check = val_to_check.replace(c, '')

            # Validar longitud
            l_val = len(val)
            if rule["longitud_min"] is not None and l_val < rule["longitud_min"]:
                errores.append(rule["descripcion_error"])
                continue
            if rule["longitud_max"] is not None and l_val > rule["longitud_max"]:
                errores.append(rule["descripcion_error"])
                continue

            # Validar con regex_validacion (probar con val o val_to_check según el patrón)
            if rule["regex_validacion"].match(val) or rule["regex_validacion"].match(val_to_check):
                return True, val, ""
            else:
                errores.append(rule["descripcion_error"])

        return False, val, errores[0] if errores else "No coincide con ningún formato catastral autorizado."

    def extraer_clave_catastral_de_texto(self, texto: str, municipio_id: int = 2) -> Optional[str]:
        """
        Aplica la estrategia de 4 intentos en cascada descrita en la especificación técnica:
        - Intento 1: Por Etiqueta / Ancla indicadora.
        - Intento 2: Caída Estructural Cancún (Observaciones + Ventanas Deslizantes de 18 y 17 caracteres).
        - Intento 3: Caída Estructural Playa / Tulum (Patrón numérico directo).
        - Intento 4: Patrón Estructural con Guiones Múltiples.
        """
        if not texto:
            return None

        self._ensure_cache_loaded(municipio_id)
        rules = self._cache_compiled_rules.get(municipio_id, [])
        catastro_rules = [r for r in rules if r["codigo_campo"] == "clave_catastral"]

        # ---------------------------------------------------------------------
        # INTENTO 1: Por Etiqueta / Ancla indicadora
        # ---------------------------------------------------------------------
        anclas = self._cache_anclas_campo.get("clave_catastral", [])
        for ancla_rx in anclas:
            for match in ancla_rx.finditer(texto):
                candidato = match.group(1).strip()
                valido, limpio, _ = self.es_clave_catastral_valida(candidato, municipio_id)
                if valido:
                    return limpio

        # ---------------------------------------------------------------------
        # INTENTO 2: Caída Estructural Cancún (Tolerancia a OCR y Ventana Deslizante)
        # ---------------------------------------------------------------------
        # Priorizar a partir de la palabra observacion / observaciones
        obs_match = re.search(r'observaci[oó]n(?:es)?[:\s\S]*', texto, re.IGNORECASE)
        segmentos_a_evaluar = [obs_match.group(0), texto] if obs_match else [texto]

        cancun_sliding_rules = [r for r in catastro_rules if r["permite_sliding_window"]]
        if cancun_sliding_rules:
            for seg in segmentos_a_evaluar:
                # Buscar palabras/bloques fusionados entre 17 y 39 caracteres
                cadenas = re.findall(r'[A-Z0-9\-]{17,39}', seg.upper())
                for cad in cadenas:
                    # Ventana deslizante para longitudes 18 y 17
                    for w_len in (18, 17):
                        if len(cad) >= w_len:
                            for start_i in range(len(cad) - w_len + 1):
                                sub = cad[start_i:start_i + w_len]
                                valido, limpio, _ = self.es_clave_catastral_valida(sub, municipio_id)
                                if valido:
                                    return limpio

        # ---------------------------------------------------------------------
        # INTENTO 3: Caída Estructural Playa / Tulum (Patrón numérico directo)
        # ---------------------------------------------------------------------
        if municipio_id in (8, 9):  # Playa del Carmen / Tulum
            direct_matches = re.findall(r'\b([1-9]\d{14}(?:-\d{1,3})?)\b', texto)
            for dm in direct_matches:
                valido, limpio, _ = self.es_clave_catastral_valida(dm, municipio_id)
                if valido:
                    return limpio

        # ---------------------------------------------------------------------
        # INTENTO 4: Patrón Estructural con Guiones Múltiples (Formato segmentado)
        # ---------------------------------------------------------------------
        segmentados = re.findall(r'\b([1-9]\d{2,}-\d{2,}-\d{2,}-\d{2,}[A-Z0-9\-]*)\b', texto)
        for seg_cand in segmentados:
            valido, limpio, _ = self.es_clave_catastral_valida(seg_cand, municipio_id)
            if valido:
                return limpio

        return None
