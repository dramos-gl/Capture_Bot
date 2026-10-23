# SATC-STD-002: Estándar Multidisciplinario para la Extracción Parametrizada de Datos, Validación de Regex y Gobernanza en Base de Datos y JSON (Metadata-Driven Engine)

**Código Documental:** SATC-STD-002  
**Versión:** 1.0  
**Fecha de Emisión:** 2026-10-22  
**Clasificación:** Normativo / Estándar Técnico de Ingeniería  
**Estado:** Aprobado para Producción  
**Autoría:** Equipo Multidisciplinario de Ingeniería SATC  
- Arquitecto de Software & Diseñador de Sistemas (Líder Técnico)
- Ingeniero de Datos & DBA (PostgreSQL & Sincronización)
- Ingeniero Backend & Automatización (Python / Apps Script / OCR Engine)
- Ingeniero de Calidad y Pruebas (QA / Test Automation)
- Analista de Negocio / Procesos Inmobiliarios y Fiscales (Contexto Quintana Roo)

---

## 1. Política Arquitectónica de Cero Código Duro (Lead Architect)

### 1.1. Declaración de Principios y Prohibición Absoluta
Queda **estrictamente prohibido en todo el ecosistema SATC/SAR**:
1. Incrustar expresiones regulares (`re.compile(r'...')`, RegExp) hardcodeadas en controladores, vistas, scripts de automatización o workers de backend.
2. Definir ventanas deslizantes (sliding windows), offsets numéricos, longitudes de caracteres o patrones de sustitución dentro de archivos ejecutables Python o Google Apps Script.
3. Asumir estructuras fijas por municipio o delegación directamente en el código de producción.

### 1.2. Principio Rector: Metadata-Driven Architecture
Toda lógica de extracción, anclaje documental, validación sintáctica y saneamiento de cadenas se desacopla en metadatos gobernados por base de datos y serializados en un contrato JSON declarativo. 

El código de los motores OCR y Parsers opera exclusivamente como un **intérprete ciego**: recibe texto crudo, consulta las reglas activas de la base de datos (con caché en memoria L1) y ejecuta la cascada definida por configuración.

```
       [ Archivo Maestro ]
     reglas_extraccion.json
               │
               ▼ (Sincronización Idempotente)
  [ Tablas satc_configuracion ]
  ├── campo_canonico
  ├── campo_etiqueta_ancla
  └── campo_formato_municipio
               │
               ▼ (Carga / Invalidador de Caché)
 [ MetadataExtractionService ]  ◄── (Cero Regex en código)
               │
               ▼
[ Pipeline OCR / Importador ]
```

### 1.3. Ciclo de Vida y Gobierno de Cambios
Cualquier modificación o adición de formatos (ej. un nuevo municipio o una variante en Cédulas Catastrales):
1. Se especifica primero en el contrato JSON normativo.
2. Se sincroniza hacia la base de datos mediante scripts idempotentes (`ON CONFLICT DO UPDATE`).
3. El motor backend refresca su caché en caliente sin requerir despliegue (redeploy) ni recompilación de ejecutables.

---

## 2. Especificación del Contrato JSON Estándar (Ingeniero de Datos & Backend)

### 2.1. JSON Schema Canónico
El archivo de configuración maestro `reglas_extraccion.json` reside formalmente en `satc/src/config/reglas_extraccion.json` y se rige por el siguiente contrato de datos:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SATC_Metadata_Extraction_Rules",
  "type": "object",
  "required": ["version", "campos"],
  "properties": {
    "version": { "type": "string" },
    "descripcion": { "type": "string" },
    "campos": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["slug", "nombre", "descripcion", "tipo_dato", "etiquetas_ancla", "variantes_municipio"],
        "properties": {
          "slug": { "type": "string" },
          "nombre": { "type": "string" },
          "descripcion": { "type": "string" },
          "tipo_dato": { "type": "string", "enum": ["STRING", "INTEGER", "DATE"] },
          "etiquetas_ancla": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["etiqueta", "regex_ancla", "prioridad"],
              "properties": {
                "etiqueta": { "type": "string" },
                "regex_ancla": { "type": "string" },
                "prioridad": { "type": "integer" }
              }
            }
          },
          "variantes_municipio": {
            "type": "array",
            "items": {
              "type": "object",
              "required": [
                "jurisdiccion",
                "nombre_variante",
                "prioridad",
                "regex_extraccion",
                "regex_validacion",
                "longitud_min",
                "longitud_max",
                "remover_caracteres",
                "permite_sliding_window",
                "descripcion_error"
              ],
              "properties": {
                "jurisdiccion": { "type": "string", "enum": ["CANCUN", "PLAYA", "TULUM", "GLOBAL"] },
                "nombre_variante": { "type": "string" },
                "prioridad": { "type": "integer" },
                "regex_extraccion": { "type": "string" },
                "regex_validacion": { "type": "string" },
                "longitud_min": { "type": ["integer", "null"] },
                "longitud_max": { "type": ["integer", "null"] },
                "remover_caracteres": { "type": "string" },
                "permite_sliding_window": { "type": "boolean" },
                "descripcion_error": { "type": "string" }
              }
            }
          }
        }
      }
    }
  }
}
```

### 2.2. Archivo Maestro de Producción (`reglas_extraccion.json`)
A continuación se detalla la configuración productiva para los campos **`clave_catastral`**, **`folio_electronico`** y **`padron`**:

```json
{
  "version": "1.0.0",
  "descripcion": "Configuración maestra de extracción gobernada por metadatos para trámites de vivienda SATC",
  "campos": [
    {
      "slug": "clave_catastral",
      "nombre": "Clave Catastral",
      "descripcion": "Identificador catastral municipal único del predio o UPE",
      "tipo_dato": "STRING",
      "etiquetas_ancla": [
        {
          "etiqueta": "CLAVE CATASTRAL",
          "regex_ancla": "(?:c(?:lave)?\\.?\\s*cat(?:astral)?\\.?|c\\.?c\\.?)[\\s:]*([A-Z0-9\\-]+)",
          "prioridad": 1
        },
        {
          "etiqueta": "DATOS DEL PREDIO / CC",
          "regex_ancla": "datos\\s+del\\s+predio[\\s\\S]*?(?:c(?:lave)?\\.?\\s*cat(?:astral)?\\.?)[\\s:]*([A-Z0-9\\-]+)",
          "prioridad": 2
        },
        {
          "etiqueta": "CVE CATASTRO",
          "regex_ancla": "(?:cve\\.?|clave)\\s*catastro[\\s:]*([A-Z0-9\\-]+)",
          "prioridad": 3
        }
      ],
      "variantes_municipio": [
        {
          "jurisdiccion": "CANCUN",
          "nombre_variante": "Cancún 18 Caracteres (18 Números o 17 Números + 1 Letra)",
          "prioridad": 1,
          "regex_extraccion": "(?:[1-9]\\d{17}|[1-9]\\d{16}[A-Z])",
          "regex_validacion": "^[1-9](?:\\d{17}|\\d{16}[A-Z])$",
          "longitud_min": 18,
          "longitud_max": 18,
          "remover_caracteres": " -/",
          "permite_sliding_window": true,
          "descripcion_error": "La clave catastral de Cancún (18 chars) debe iniciar con 1-9 y contener 18 números o 17 números y 1 letra."
        },
        {
          "jurisdiccion": "CANCUN",
          "nombre_variante": "Cancún 17 Caracteres (16 Números + 1 Letra)",
          "prioridad": 2,
          "regex_extraccion": "(?:[1-9]\\d{15}[A-Z])",
          "regex_validacion": "^[1-9]\\d{15}[A-Z]$",
          "longitud_min": 17,
          "longitud_max": 17,
          "remover_caracteres": " -/",
          "permite_sliding_window": true,
          "descripcion_error": "La clave catastral de Cancún (17 chars) debe iniciar con 1-9 y contener exactamente 16 números y 1 letra."
        },
        {
          "jurisdiccion": "PLAYA",
          "nombre_variante": "Playa del Carmen (Con Guión 16 a 19 caracteres)",
          "prioridad": 1,
          "regex_extraccion": "(?:[1-9]\\d{14}-\\d{1,3})",
          "regex_validacion": "^[1-9]\\d{14}-\\d{1,3}$",
          "longitud_min": 16,
          "longitud_max": 19,
          "remover_caracteres": " ",
          "permite_sliding_window": false,
          "descripcion_error": "La clave de Solidaridad/Playa con guión debe tener base de 15 dígitos numéricos seguidos de un guión y de 1 a 3 dígitos."
        },
        {
          "jurisdiccion": "PLAYA",
          "nombre_variante": "Playa del Carmen (Sin Guión 15 Dígitos Continuos)",
          "prioridad": 2,
          "regex_extraccion": "(?:[1-9]\\d{14})",
          "regex_validacion": "^[1-9]\\d{14}$",
          "longitud_min": 15,
          "longitud_max": 15,
          "remover_caracteres": " -/",
          "permite_sliding_window": false,
          "descripcion_error": "La clave de Solidaridad/Playa continua debe contener exactamente 15 dígitos numéricos sin letras."
        },
        {
          "jurisdiccion": "TULUM",
          "nombre_variante": "Tulum (Con Guión 16 a 19 caracteres)",
          "prioridad": 1,
          "regex_extraccion": "(?:[1-9]\\d{14}-\\d{1,3})",
          "regex_validacion": "^[1-9]\\d{14}-\\d{1,3}$",
          "longitud_min": 16,
          "longitud_max": 19,
          "remover_caracteres": " ",
          "permite_sliding_window": false,
          "descripcion_error": "La clave de Tulum con guión debe tener base de 15 dígitos numéricos seguidos de un guión y de 1 a 3 dígitos."
        },
        {
          "jurisdiccion": "TULUM",
          "nombre_variante": "Tulum (Sin Guión 15 Dígitos Continuos)",
          "prioridad": 2,
          "regex_extraccion": "(?:[1-9]\\d{14})",
          "regex_validacion": "^[1-9]\\d{14}$",
          "longitud_min": 15,
          "longitud_max": 15,
          "remover_caracteres": " -/",
          "permite_sliding_window": false,
          "descripcion_error": "La clave de Tulum continua debe contener exactamente 15 dígitos numéricos sin letras."
        }
      ]
    },
    {
      "slug": "folio_electronico",
      "nombre": "Folio Electrónico RPP",
      "descripcion": "Folio de inscripción del Registro Público de la Propiedad (RPP)",
      "tipo_dato": "STRING",
      "etiquetas_ancla": [
        {
          "etiqueta": "FOLIO ELECTRONICO",
          "regex_ancla": "(?:folio\\s*electr[oó]nico|folio\\s*real|f\\.e\\.)[\\s:]*(\\d{1,20})",
          "prioridad": 1
        },
        {
          "etiqueta": "FOLIO INSCRIPCION",
          "regex_ancla": "(?:no\\.?\\s*folio|folio)[\\s:]*(\\d{1,20})",
          "prioridad": 2
        }
      ],
      "variantes_municipio": [
        {
          "jurisdiccion": "GLOBAL",
          "nombre_variante": "Folio Electrónico RPP 20 Dígitos (Quintana Roo)",
          "prioridad": 1,
          "regex_extraccion": "(?:\\b20\\d{18}\\b|\\b\\d{20}\\b)",
          "regex_validacion": "^\\d{20}$",
          "longitud_min": 20,
          "longitud_max": 20,
          "remover_caracteres": " -/",
          "permite_sliding_window": true,
          "descripcion_error": "El folio electrónico RPP debe contener exactamente 20 dígitos numéricos (comenzando habitualmente con el código 20)."
        },
        {
          "jurisdiccion": "GLOBAL",
          "nombre_variante": "Folio Numérico Breve / Histórico",
          "prioridad": 2,
          "regex_extraccion": "(?:\\b[1-9]\\d{3,9}\\b)",
          "regex_validacion": "^[1-9]\\d{3,9}$",
          "longitud_min": 4,
          "longitud_max": 10,
          "remover_caracteres": " -/",
          "permite_sliding_window": false,
          "descripcion_error": "El folio numérico general debe tener entre 4 y 10 dígitos numéricos sin ceros iniciales."
        }
      ]
    },
    {
      "slug": "padron",
      "nombre": "Padrón Catastral / Número de Cuenta",
      "descripcion": "Número de padrón municipal o cuenta predial asignada",
      "tipo_dato": "STRING",
      "etiquetas_ancla": [
        {
          "etiqueta": "PADRON",
          "regex_ancla": "(?:padr[oó]n|num(?:ero)?\\.?\\s*padr[oó]n|cta\\.?\\s*predial)[\\s:]*([A-Z0-9\\-]+)",
          "prioridad": 1
        }
      ],
      "variantes_municipio": [
        {
          "jurisdiccion": "GLOBAL",
          "nombre_variante": "Padrón Alfanumérico Municipal",
          "prioridad": 1,
          "regex_extraccion": "(?:[A-Z0-9]{4,15})",
          "regex_validacion": "^[A-Z0-9]{4,15}$",
          "longitud_min": 4,
          "longitud_max": 15,
          "remover_caracteres": " -/",
          "permite_sliding_window": false,
          "descripcion_error": "El número de padrón debe ser alfanumérico entre 4 y 15 caracteres."
        }
      ]
    }
  ]
}
```

---

## 3. Procedimiento de Migración y Persistencia SQL (DBA)

### 3.1. Mapeo Entidad-Relación y Tablas
La estructura física normalizada en el esquema `satc_configuracion` refleja 1:1 el contrato JSON:
1. `satc_configuracion.campo_canonico`: Almacena el `slug`, `nombre`, `descripcion` y `tipo_dato`.
2. `satc_configuracion.campo_etiqueta_ancla`: Almacena los alias y expresiones regulares de captura asociados a un `campo_id`.
3. `satc_configuracion.campo_formato_municipio`: Almacena las variantes estructurales, longitudes, limpieza y prioridad vinculadas a `sar_catalogo.municipio` (o `municipio_id = NULL / GLOBAL`).

### 3.2. Script SQL de Sincronización Idempotente
El siguiente script se ejecuta sin riesgo de duplicar registros, alterar IDs autoincrementales ni causar bloqueos (`Deadlocks`):

```sql
-- =============================================================================
-- SINCRONIZACIÓN IDEMPOTENTE DE REGLAS METADATA-DRIVEN
-- Esquema: satc_configuracion
-- =============================================================================

BEGIN;

-- 1. Sincronizar Campos Canónicos
INSERT INTO satc_configuracion.campo_canonico (codigo, nombre, descripcion, activo)
VALUES
    ('clave_catastral', 'Clave Catastral', 'Identificador catastral municipal único del predio o UPE', true),
    ('folio_electronico', 'Folio Electrónico RPP', 'Folio de inscripción del Registro Público de la Propiedad (RPP)', true),
    ('padron', 'Padrón Catastral', 'Número de padrón municipal o cuenta predial asignada', true)
ON CONFLICT (codigo) DO UPDATE 
SET nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion,
    activo = EXCLUDED.activo,
    updated_at = CURRENT_TIMESTAMP;

-- 2. Sincronizar Etiquetas Ancla (Por campo_id y etiqueta)
WITH campos AS (
    SELECT campo_id, codigo FROM satc_configuracion.campo_canonico
)
INSERT INTO satc_configuracion.campo_etiqueta_ancla (campo_id, etiqueta, regex_ancla, prioridad, activo)
VALUES
    ((SELECT campo_id FROM campos WHERE codigo = 'clave_catastral'), 'CLAVE CATASTRAL', '(?:c(?:lave)?\.?\s*cat(?:astral)?\.?|c\.?c\.?)[\s:]*([A-Z0-9\-]+)', 1, true),
    ((SELECT campo_id FROM campos WHERE codigo = 'clave_catastral'), 'DATOS DEL PREDIO / CC', 'datos\s+del\s+predio[\s\S]*?(?:c(?:lave)?\.?\s*cat(?:astral)?\.?)[\s:]*([A-Z0-9\-]+)', 2, true),
    ((SELECT campo_id FROM campos WHERE codigo = 'clave_catastral'), 'CVE CATASTRO', '(?:cve\.?|clave)\s*catastro[\s:]*([A-Z0-9\-]+)', 3, true),
    ((SELECT campo_id FROM campos WHERE codigo = 'folio_electronico'), 'FOLIO ELECTRONICO', '(?:folio\s*electr[oó]nico|folio\s*real|f\.e\.)[\s:]*(\d{1,20})', 1, true),
    ((SELECT campo_id FROM campos WHERE codigo = 'folio_electronico'), 'FOLIO INSCRIPCION', '(?:no\.?\s*folio|folio)[\s:]*(\d{1,20})', 2, true),
    ((SELECT campo_id FROM campos WHERE codigo = 'padron'), 'PADRON', '(?:padr[oó]n|num(?:ero)?\.?\s*padr[oó]n|cta\.?\s*predial)[\s:]*([A-Z0-9\-]+)', 1, true)
ON CONFLICT (campo_id, etiqueta) DO UPDATE
SET regex_ancla = EXCLUDED.regex_ancla,
    prioridad = EXCLUDED.prioridad,
    activo = EXCLUDED.activo;

-- 3. Sincronizar Formatos y Variantes por Municipio
WITH campos AS (
    SELECT campo_id, codigo FROM satc_configuracion.campo_canonico
)
INSERT INTO satc_configuracion.campo_formato_municipio (
    campo_id, municipio_id, nombre_variante, prioridad, regex_extraccion, 
    regex_validacion, longitud_min, longitud_max, remover_caracteres, 
    permite_sliding_window, descripcion_error, activo
)
VALUES
    -- Cancún (Benito Juárez ID 2)
    ((SELECT campo_id FROM campos WHERE codigo = 'clave_catastral'), 2, 'Cancún 18 Caracteres (18 Números o 17 Números + 1 Letra)', 1, 
     '(?:[1-9]\d{17}|[1-9]\d{16}[A-Z])', '^[1-9](?:\d{17}|\d{16}[A-Z])$', 18, 18, ' -/', true, 
     'La clave catastral de Cancún (18 chars) debe iniciar con 1-9 y contener 18 números o 17 números y 1 letra.', true),
    
    ((SELECT campo_id FROM campos WHERE codigo = 'clave_catastral'), 2, 'Cancún 17 Caracteres (16 Números + 1 Letra)', 2, 
     '(?:[1-9]\d{15}[A-Z])', '^[1-9]\d{15}[A-Z]$', 17, 17, ' -/', true, 
     'La clave catastral de Cancún (17 chars) debe iniciar con 1-9 y contener exactamente 16 números y 1 letra.', true),

    -- Playa del Carmen / Solidaridad (ID 8)
    ((SELECT campo_id FROM campos WHERE codigo = 'clave_catastral'), 8, 'Playa del Carmen (Con Guión 16 a 19 caracteres)', 1, 
     '(?:[1-9]\d{14}-\d{1,3})', '^[1-9]\d{14}-\d{1,3}$', 16, 19, ' ', false, 
     'La clave de Solidaridad/Playa con guión debe tener base de 15 dígitos numéricos seguidos de un guión y de 1 a 3 dígitos.', true),

    ((SELECT campo_id FROM campos WHERE codigo = 'clave_catastral'), 8, 'Playa del Carmen (Sin Guión 15 Dígitos Continuos)', 2, 
     '(?:[1-9]\d{14})', '^[1-9]\d{14}$', 15, 15, ' -/', false, 
     'La clave de Solidaridad/Playa continua debe contener exactamente 15 dígitos numéricos sin letras.', true),

    -- Tulum (ID 9)
    ((SELECT campo_id FROM campos WHERE codigo = 'clave_catastral'), 9, 'Tulum (Con Guión 16 a 19 caracteres)', 1, 
     '(?:[1-9]\d{14}-\d{1,3})', '^[1-9]\d{14}-\d{1,3}$', 16, 19, ' ', false, 
     'La clave de Tulum con guión debe tener base de 15 dígitos numéricos seguidos de un guión y de 1 a 3 dígitos.', true),

    ((SELECT campo_id FROM campos WHERE codigo = 'clave_catastral'), 9, 'Tulum (Sin Guión 15 Dígitos Continuos)', 2, 
     '(?:[1-9]\d{14})', '^[1-9]\d{14}$', 15, 15, ' -/', false, 
     'La clave de Tulum continua debe contener exactamente 15 dígitos numéricos sin letras.', true),

    -- Folio RPP 20 Dígitos (Aplica a Cancún ID 2, Playa ID 8, Tulum ID 9)
    ((SELECT campo_id FROM campos WHERE codigo = 'folio_electronico'), 2, 'Folio RPP 20 Dígitos (Cancún)', 1, 
     '(?:\b20\d{18}\b|\b\d{20}\b)', '^\d{20}$', 20, 20, ' -/', true, 
     'El folio electrónico RPP debe contener exactamente 20 dígitos numéricos.', true),

    ((SELECT campo_id FROM campos WHERE codigo = 'folio_electronico'), 8, 'Folio RPP 20 Dígitos (Playa)', 1, 
     '(?:\b20\d{18}\b|\b\d{20}\b)', '^\d{20}$', 20, 20, ' -/', true, 
     'El folio electrónico RPP debe contener exactamente 20 dígitos numéricos.', true),

    ((SELECT campo_id FROM campos WHERE codigo = 'folio_electronico'), 9, 'Folio RPP 20 Dígitos (Tulum)', 1, 
     '(?:\b20\d{18}\b|\b\d{20}\b)', '^\d{20}$', 20, 20, ' -/', true, 
     'El folio electrónico RPP debe contener exactamente 20 dígitos numéricos.', true)

ON CONFLICT (campo_id, municipio_id, nombre_variante) DO UPDATE
SET prioridad = EXCLUDED.prioridad,
    regex_extraccion = EXCLUDED.regex_extraccion,
    regex_validacion = EXCLUDED.regex_validacion,
    longitud_min = EXCLUDED.longitud_min,
    longitud_max = EXCLUDED.longitud_max,
    remover_caracteres = EXCLUDED.remover_caracteres,
    permite_sliding_window = EXCLUDED.permite_sliding_window,
    descripcion_error = EXCLUDED.descripcion_error,
    activo = EXCLUDED.activo,
    updated_at = CURRENT_TIMESTAMP;

COMMIT;
```

---

## 4. Lineamientos de Implementación del Motor de Extracción (Backend Engineer)

### 4.1. Algoritmo de Cascada en 4 Fases
El servicio [MetadataExtractionService](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/satc/src/services/metadata_extraction_service.py) ejecuta la resolución de valores mediante una cascada estricta:

```
[ Texto Crudo OCR ]
        │
        ▼
┌──────────────────────────────────────────────┐
│ FASE 1: Búsqueda por Ancla                   │
│ (Etiquetas predefinidas con grupo de captura)│
└──────────────────────┬───────────────────────┘
                       │ ¿Encontrado y Válido?
                       ├────────────────────────► [ RETORNAR VALOR ]
                       ▼ NO
┌──────────────────────────────────────────────┐
│ FASE 2: Caída Estructural Cancún             │
│ (Sección Observaciones + Ventana Deslizante) │
└──────────────────────┬───────────────────────┘
                       │ ¿Encontrado y Válido?
                       ├────────────────────────► [ RETORNAR VALOR ]
                       ▼ NO
┌──────────────────────────────────────────────┐
│ FASE 3: Caída Estructural Playa / Tulum      │
│ (Patrón numérico 15d o 15d con guión)        │
└──────────────────────┬───────────────────────┘
                       │ ¿Encontrado y Válido?
                       ├────────────────────────► [ RETORNAR VALOR ]
                       ▼ NO
┌──────────────────────────────────────────────┐
│ FASE 4: Patrón Segmentado Multiparte         │
│ (Formatos históricos con guiones múltiples)  │
└──────────────────────┬───────────────────────┘
                       │ ¿Encontrado y Válido?
                       ├────────────────────────► [ RETORNAR VALOR ]
                       ▼ NO
               [ RETORNAR NULL ]
```

### 4.2. Tolerancia a Ruido OCR y Ventana Deslizante (Sliding Window)
1. **Problema**: Los motores OCR frecuentemente fusionan la clave con texto adyacente (ej. `LOTE_102030405060708901_EN_TRAMITE`).
2. **Solución Normativa**:
   - Extraer todos los tokens alfanuméricos entre 17 y 39 caracteres.
   - Para longitudes fijas de 18 y 17 caracteres, aplicar ventana deslizante:
     ```python
     for w_len in (18, 17):
         if len(token) >= w_len:
             for start_i in range(len(token) - w_len + 1):
                 candidate = token[start_i:start_i + w_len]
                 is_valid, clean_val, _ = self.es_clave_catastral_valida(candidate, municipio_id)
                 if is_valid:
                     return clean_val
     ```

### 4.3. Reglas de Descarte Global (Falsos Positivos)
Toda extracción queda descartada de inmediato si incumple cualquiera de las dos reglas soberanas:
1. **Inicio con Cero**: Si `candidate.startswith("0")` -> Descarte inmediato.
2. **Caracteres Prohibidos**: Si contiene símbolos distintos a `[A-Z0-9\-]` -> Descarte inmediato.

---

## 5. Matriz de Aseguramiento de Calidad y Pruebas Unitarias (QA Lead)

### 5.1. Matriz de Casos de Prueba Oficiales

| ID | Input de Texto OCR | Municipio | Resultado Esperado | Variante / Regla Disparada | Tipo Caso |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-01** | `CLAVE CATASTRAL: 1020304050607089A` | Cancún (2) | `1020304050607089A` | Intento 1: Ancla + Cancún 17 chars | Positivo |
| **TC-02** | `DATOS PREDIO: CC 102030405060708901 FOLIO 77` | Cancún (2) | `102030405060708901` | Intento 1: Ancla + Cancún 18 chars (num) | Positivo |
| **TC-03** | `OBSERVACIONES: REF_10203040506070890A_MIGRADO` | Cancún (2) | `10203040506070890A` | Intento 2: Sliding Window 18 chars | Positivo |
| **TC-04** | `CEDULA CLAVE: 102030405060708-1 EDIF B` | Playa (8) | `102030405060708-1` | Intento 1: Ancla + Playa con guión | Positivo |
| **TC-05** | `MUNICIPIO SOLIDARIDAD CC 102030405060708 VIV` | Playa (8) | `102030405060708` | Intento 1: Ancla + Playa 15 dígitos | Positivo |
| **TC-06** | `TULUM CONSTANCIA 102030405060708-102 SM 1` | Tulum (9) | `102030405060708-102` | Intento 3: Caída directa Tulum guión | Positivo |
| **TC-07** | `INSCRIPCION RPP FOLIO: 20260200000000127466` | Cancún (2) | `20260200000000127466`| Intento 1: Ancla Folio RPP 20d | Positivo |
| **TC-NEG-01** | `CLAVE CATASTRAL: 01020304050607089A` | Cancún (2) | `NULL` (Rechazado) | Regla Global: Inicia con 0 | Negativo |
| **TC-NEG-02** | `CLAVE: 10203040506070` *(14 caracteres)* | Cancún (2) | `NULL` (Rechazado) | Longitud truncada (< 17 chars) | Negativo |
| **TC-NEG-03** | `CC: 102030405060708-` *(Guión sin sufijo)* | Playa (8) | `NULL` (Rechazado) | Formato con guión incompleto | Negativo |
| **TC-NEG-04** | `FOLIO ELECTRONICO: 2026020000000012746` *(19d)*| Cancún (2) | `NULL` (Rechazado) | Folio RPP truncado (< 20d) | Negativo |

### 5.2. Checklist Obligatorio para Code Review (PR Quality Gate)
Antes de aprobar cualquier Pull Request que interactúe con el motor de extracción o sus tablas:
- [ ] **Cero Hardcodeo**: Se verificó mediante búsqueda en el PR que no existan expresiones regulares ni literales de máscara en archivos `.py` o `.gs`.
- [ ] **Contrato JSON Actualizado**: Si se introdujo un nuevo campo o variante, `reglas_extraccion.json` refleja el cambio validado contra el schema.
- [ ] **Idempotencia SQL**: La migración correspondiente utiliza sentencias `ON CONFLICT DO UPDATE`.
- [ ] **Aislamiento de Dominios**: Ninguna regla de `satc_configuracion` altera ni toca el esquema de referencias `sar_*`.
- [ ] **Simetría Dual de Transporte**: La consulta y guardado funcionan de forma simétrica tanto en conexión directa como a través de `APIClient` (`CONNECT_VIA_API: true`).
- [ ] **Cobertura de Pruebas**: Los tests unitarios en `satc/tests/` pasan al 100%, cubriendo al menos un caso positivo y uno negativo por cada variante nueva.
