"""
Extractor especializado para Constancias de Resolución del RPP (Registro Público de la Propiedad).
Extrae la sección 'FOLIOS GENERADOS' y parsea de manera determinista cada UPE:
- No. Fracción
- Interior / UPE
- Número Oficial
- Nivel
- Edificio
- Folio Real Electrónico (20 dígitos)
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
import pypdf

from satc.src.paths import RPP_PATTERNS_FILE

logger = logging.getLogger(__name__)


class RppResolutionExtractor:
    """Extrae folios electrónicos reales de Constancias de Resolución de Condominios del RPP."""

    # Fallback embebido en memoria en caso de ausencia o error en archivo de configuración JSON
    DEFAULT_PATTERNS = {
        "upe_header_patterns": [
            r"UNIDAD(?:ES)?\s+DE\s+PROPIEDAD\s+EXCLUSIVA",
            r"UNIDA(?:DES)?\s+DE\s+PROPIEDAD\s+EXCLUSIVA",
            r"UNIDAD(?:ES)?\s+DE\s+PO?RPIEDAD\s+EXCLUSIVA",
            r"UNIDA(?:DES)?\s+DE\s+PO?RPIEDAD\s+EXCLUSIVA",
            r"UNID[AÁ]D(?:ES)?\s+DE\s+PROPIED[AÁ]D\s+EXCLUSIVA",
            r"UPE"
        ],
        "numero_oficial_patterns": [
            r"N[ÚU\ufffd]?M[EEO]*R?O?\s*OF[IÍ]?C[IÍ]?AL\s*(\d+)",
            r"N[ÚU\ufffd]?M[EEO]*R?O?\s*(\d+)\s*OF[IÍ]?C[IÍ]?AL",
            r"NO\.?\s*OF[IÍ]?C[IÍ]?AL\s*(\d+)",
            r"NUM\.?\s*OF[IÍ]?C[IÍ]?AL\s*(\d+)"
        ],
        "edificio_patterns": [
            r"(EDIFICIO\s*[A-Z0-9]+|\bTORRE\s*[A-Z0-9]+|\bEDIF\.?\s*[A-Z0-9]+)"
        ],
        "nivel_patterns": [
            r"(\bPLANTA\s+BAJA\b|\bNIVEL[\s\.]*\d+|\bPISO[\s\.]*\d+|\bPB\b|\bN[1-9]\d*\b)"
        ]
    }

    _cached_patterns: Optional[Dict[str, Any]] = None

    @classmethod
    def get_patterns(cls) -> Dict[str, Any]:
        """Carga y almacena en caché los patrones de extracción desde el archivo de configuración JSON."""
        if cls._cached_patterns is not None:
            return cls._cached_patterns

        patterns = dict(cls.DEFAULT_PATTERNS)
        try:
            if RPP_PATTERNS_FILE.exists():
                with open(RPP_PATTERNS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k in ("upe_header_patterns", "numero_oficial_patterns", "edificio_patterns", "nivel_patterns"):
                        if k in data and isinstance(data[k], list) and data[k]:
                            patterns[k] = data[k]
                logger.debug(f"RppResolutionExtractor: Patrones OCR cargados exitosamente desde {RPP_PATTERNS_FILE}")
            else:
                logger.warning(f"RppResolutionExtractor: Archivo {RPP_PATTERNS_FILE} no encontrado. Usando fallback en memoria.")
        except Exception as e:
            logger.error(f"RppResolutionExtractor: Error al leer {RPP_PATTERNS_FILE}: {e}. Usando fallback en memoria.")

        cls._cached_patterns = patterns
        return patterns

    @classmethod
    def extract_from_pdf(cls, pdf_path: str, progress_callback: Optional[Any] = None) -> List[Dict[str, Any]]:
        """
        Lee el archivo PDF del RPP y extrae todos los folios generados para cada vivienda/UPE.
        Retorna lista de diccionarios normalizados:
        [{
            'numero_fraccion': int,
            'interior': str,
            'edificio': str,
            'numero_oficial': str,
            'nivel': str,
            'folio_electronico': str
        }, ...]
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"El archivo PDF no existe: {pdf_path}")

        reader = pypdf.PdfReader(pdf_path)
        pages_clean = []
        tot_pages = len(reader.pages)
        for idx, page in enumerate(reader.pages):
            if progress_callback:
                try:
                    progress_callback(idx + 1, tot_pages)
                except Exception:
                    pass
            txt = page.extract_text() or ""
            # Remover encabezados de certificación digital que se insertan en los saltos de página
            txt = re.sub(r'CERTIFICADO DIGITAL[\s\S]*?P[\w\W]{1,10}gina \d+ de \d+\s*', '', txt)
            pages_clean.append(txt)

        full_text = "\n".join(pages_clean)

        if "FOLIOS GENERADOS" not in full_text.upper():
            raise ValueError(
                "El documento PDF no contiene la sección 'FOLIOS GENERADOS' característica "
                "de las Constancias de Resolución del RPP."
            )

        # Localizar el inicio de la sección FOLIOS GENERADOS
        idx_start = full_text.find("FOLIOS GENERADOS")
        sec = full_text[idx_start:]

        # Cargar patrones parametrizados
        patterns = cls.get_patterns()
        upe_headers = patterns.get("upe_header_patterns", cls.DEFAULT_PATTERNS["upe_header_patterns"])
        upe_union = "|".join(f"(?:{p})" for p in upe_headers)

        # Mapear página física/documental para cada fracción
        regex_frac_page = rf'(?:^|\n)\s*(\d+)\s+(?:{upe_union})\b'
        frac_to_page = {}
        for p_idx, p_obj in enumerate(reader.pages):
            p_text = p_obj.extract_text() or ""
            p_matches = re.findall(regex_frac_page, p_text, re.IGNORECASE)
            for m in p_matches:
                frac_to_page[int(m)] = p_idx + 1

        # Tokenizado tolerante a erratas de cabecera capturando también el encabezado para reconstrucción
        regex_split = rf'\n\s*(\d+)\s+({upe_union})\s+'
        tokens = re.split(regex_split, sec, flags=re.IGNORECASE)

        results = []
        nof_patterns = patterns.get("numero_oficial_patterns", cls.DEFAULT_PATTERNS["numero_oficial_patterns"])
        ed_patterns = patterns.get("edificio_patterns", cls.DEFAULT_PATTERNS["edificio_patterns"])
        niv_patterns = patterns.get("nivel_patterns", cls.DEFAULT_PATTERNS["nivel_patterns"])

        for i in range(1, len(tokens), 3):
            num_fraccion = int(tokens[i])
            header_matched = tokens[i + 1].strip()
            body = tokens[i + 2]

            # 1. Folio Real Electrónico (secuencia de 15 a 25 dígitos, comúnmente 20)
            m_folio = re.search(r'(\d{15,25})', body)
            folio = m_folio.group(1).strip() if m_folio else ""

            # Reconstrucción de la extracción textual completa limpia (sin el folio ni firmas electrónicas)
            body_clean = ' '.join(body.split())
            body_clean = re.sub(r'\b\d{15,25}\b', '', body_clean).strip()
            body_clean = re.sub(r'\s+FIRMA\s+ELECTR[OÓ\ufffd]?NICA.*$', '', body_clean, flags=re.IGNORECASE).strip()
            texto_extraccion = f"{header_matched} {body_clean}".strip()
            pagina_doc = frac_to_page.get(num_fraccion, 1)

            # 2. Interior / UPE (primera línea del bloque, sanitizada de folios pegados y comas)
            lines = [l.strip() for l in body.split('\n') if l.strip()]
            interior_raw = lines[0] if lines else ""
            interior_raw = re.sub(r'\b\d{15,25}\b', '', interior_raw)
            # Limpiar palabras clave que queden pegadas al final de la línea por cortes tipográficos (ej. '201 NUMERO')
            interior_raw = re.sub(
                r'\s+(?:N[ÚU\ufffd]?M[EEO]*R?O?|OFIC?IAL|PLANTA|NIVEL|EDIFICIO|TORRE|DEPTO|DEPARTAMENTO)\b.*$',
                '',
                interior_raw,
                flags=re.IGNORECASE
            )
            interior = re.sub(r'^[,\.\s;:-]+|[,\.\s;:-]+$', '', interior_raw).strip().upper()

            # 3. Edificio / Torre
            edificio = ""
            for ep in ed_patterns:
                m_ed = re.search(ep, body, re.IGNORECASE)
                if m_ed:
                    edificio = m_ed.group(1).strip().upper()
                    break

            # 4. Número oficial (tolerante a erratas de OCR/PDF ej. NUMEO, OFCIAL, trasposiciones)
            no_oficial = ""
            for np in nof_patterns:
                m_nof = re.search(np, body, re.IGNORECASE)
                if m_nof:
                    no_oficial = m_nof.group(1).strip()
                    break

            # Si no viene explícito "NUMERO OFICIAL <N>" en el cuerpo, la columna "No." (num_fraccion) es su equivalente oficial
            if not no_oficial and num_fraccion:
                no_oficial = str(num_fraccion)

            # 5. Nivel / Planta (tolerante a PB, N1, N2, N3, NIVEL .3, etc.)
            nivel = ""
            for niv_p in niv_patterns:
                m_niv = re.search(niv_p, body, re.IGNORECASE)
                if m_niv:
                    raw_niv = m_niv.group(1).strip().upper()
                    raw_niv = re.sub(r'\s*\.\s*', ' ', raw_niv)
                    # Normalizar a estándar BD: PB, 1, 2, 3...
                    if raw_niv in ("PB", "PLANTA BAJA"):
                        nivel = "PB"
                    elif raw_niv.startswith("N") and raw_niv[1:].isdigit():
                        nivel = raw_niv[1:]
                    elif "NIVEL" in raw_niv or "PISO" in raw_niv:
                        m_dig = re.search(r'\d+', raw_niv)
                        nivel = m_dig.group(0) if m_dig else raw_niv
                    else:
                        nivel = raw_niv
                    break

            # 6. Desacoplamiento y Sanitización Rigurosa de Interior / Nivel:
            # En formatos condensados (ej. '101 PB', '201 N1', 'A PB'), remover sufijos de nivel del interior
            interior_clean = re.sub(
                r'\b(PB|PLANTA\s+BAJA|N[1-9]\d*|NIVEL[\s\.]*\d+|PISO[\s\.]*\d+)\b',
                '',
                interior,
                flags=re.IGNORECASE
            )
            interior_clean = re.sub(r'^[,\.\s;:-]+|[,\.\s;:-]+$', '', interior_clean).strip().upper()
            if interior_clean:
                interior = interior_clean

            if folio and interior:
                results.append({
                    "numero_fraccion": num_fraccion,
                    "interior": interior,
                    "edificio": edificio,
                    "numero_oficial": no_oficial,
                    "nivel": nivel,
                    "folio_electronico": folio,
                    "pagina": pagina_doc,
                    "texto_completo": texto_extraccion
                })
            else:
                logger.warning(f"Entrada omitida por falta de folio o interior en fraccion #{num_fraccion}")

        logger.info(f"RppResolutionExtractor: Se extrajeron con éxito {len(results)} folios del PDF {pdf_path}")
        return results
