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
import logging
from typing import List, Dict, Any, Optional
import pypdf

logger = logging.getLogger(__name__)


class RppResolutionExtractor:
    """Extrae folios electrónicos reales de Constancias de Resolución de Condominios del RPP."""

    @staticmethod
    def extract_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
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
        for page in reader.pages:
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

        # Tokenizado determinista por: '<N> UNIDAD DE PROPIEDAD EXCLUSIVA'
        tokens = re.split(r'\n\s*(\d+)\s+UNIDAD DE PROPIEDAD EXCLUSIVA\s+', sec, flags=re.IGNORECASE)

        results = []
        for i in range(1, len(tokens), 2):
            num_fraccion = int(tokens[i])
            body = tokens[i + 1]

            # 1. Folio Real Electrónico (secuencia de 15 a 25 dígitos, normalmente 20)
            m_folio = re.search(r'(\d{15,25})', body)
            folio = m_folio.group(1).strip() if m_folio else ""

            # 2. Interior / UPE (primera línea del bloque, sanitizada de folios pegados y comas)
            lines = [l.strip() for l in body.split('\n') if l.strip()]
            interior_raw = lines[0] if lines else ""
            interior_raw = re.sub(r'\b\d{15,25}\b', '', interior_raw)
            interior = re.sub(r'^[,\.\s;:-]+|[,\.\s;:-]+$', '', interior_raw).strip().upper()

            # 3. Edificio / Torre
            m_ed = re.search(r'(EDIFICIO\s+[A-Z0-9]+|\bTORRE\s+[A-Z0-9]+)', body, re.IGNORECASE)
            edificio = m_ed.group(1).strip().upper() if m_ed else ""

            # 4. Número oficial (tolerante a erratas de OCR/PDF ej. NUMEO, NUMEORO)
            m_nof = re.search(r'N[ÚU\ufffd]?M[EEO]*R?O?\s+OFICIAL\s*(\d+)', body, re.IGNORECASE)
            no_oficial = m_nof.group(1).strip() if m_nof else ""
            # Si no viene explícito "NUMERO OFICIAL <N>" en el cuerpo, la columna "No." (num_fraccion) es su equivalente oficial
            if not no_oficial and num_fraccion:
                no_oficial = str(num_fraccion)

            # 5. Nivel / Planta (tolerante a puntos como NIVEL .3)
            m_niv = re.search(r'(PLANTA BAJA|NIVEL[\s\.]*\d+|PISO[\s\.]*\d+)', body, re.IGNORECASE)
            nivel = m_niv.group(1).strip().upper() if m_niv else ""
            if nivel:
                nivel = re.sub(r'\s*\.\s*', ' ', nivel)

            if folio and interior:
                results.append({
                    "numero_fraccion": num_fraccion,
                    "interior": interior,
                    "edificio": edificio,
                    "numero_oficial": no_oficial,
                    "nivel": nivel,
                    "folio_electronico": folio
                })
            else:
                logger.warning(f"Entrada omitida por falta de folio o interior en fraccion #{num_fraccion}")

        logger.info(f"RppResolutionExtractor: Se extrajeron con éxito {len(results)} folios del PDF {pdf_path}")
        return results
