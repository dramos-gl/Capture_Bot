# 🚀 Optima Capture Bot — Documentación Operativa y Arquitectura de Fases B y C

Este documento consolida el funcionamiento completo, las reglas de negocio, la arquitectura y el flujo de control de las **Fases B y C** de la plataforma **Optima Capture Bot** (v1.2.0). 
Este documento sirve como base de análisis para la futura planificación de la **FASE A**.

---

## 🗺️ Mapa de Flujo General del Sistema

```mermaid
graph TD
    subgraph FASE B: Ingesta y Preparación (Automatizado)
        A[Carpeta con PDFs de Pago] --> B(Extractor PhaseBExtractor)
        B --> C{Extraer RFC, Referencia, Razón Social, CP, Importe y Fecha Límite}
        C -->|Válidos| D[Organizar por RFC en Carpetas]
        C -->|Errores/Incompletos| Err[Carpetas Errores/Incompletos]
        D --> E[Ordenar por Fecha de Alta ASC]
        E --> F[Renombrar PDFs: Ref_RFC_ID.pdf]
        E --> G[Particionar registros: Max 300 por Excel]
        G --> H[Generar Excels: RFC_OCB_Particion.xlsx]
    end

    subgraph FASE C: Orquestación y Operación (Playwright)
        H --> I[Cargar Excel Generado]
        I --> J[Iniciar Bot]
        J --> K[Orquestador: BotOrchestrator]
        K --> L[Leer fila de Control_Referencias]
        L --> M[Buscar Referencia en SATQ]
        M --> N{¿Ya Generada?}
        N -->|No / Pendiente| O[Frenar en Modo Asistido o Timbrar en Modo Autónomo]
        N -->|Sí y Omitir Activado| P[Marcar OMITIDO-YA GENERADA]
        N -->|Sí y Omitir Desactivado| Q[Descargar los 2 PDFs de la Factura]
        O --> R[Descargar los 2 PDFs y marcar OK-GENERADA]
        R --> S[Guardar en Carpeta Descargas/Lote_N]
        S --> T[Actualizar Fila en Caliente en Excel]
    end
```

---

## 📥 FASE B — Automatización de Entradas (Ingesta y Preparación)

El objetivo de la **FASE B** es digitalizar y formatear los datos de los pagos de derechos en formato PDF, eliminando la captura manual y preparando lotes organizados listos para ser consumidos por el motor de timbrado (FASE C).

### 1. Extracción de Datos desde PDF
Mediante la librería `pypdf`, el sistema escanea recursivamente el directorio de origen seleccionado y procesa cada archivo PDF aplicando los siguientes patrones de expresiones regulares:

* **Fecha de Alta:** Ubica el patrón `Fecha alta:` y extrae el valor temporal de la siguiente línea (p. ej., `2026-06-03 13:23:43`).
* **Referencia:** Busca la cadena `REFERENCIA:\s*(\d{17})` correspondiente al código de barras. Tiene un fallback genérico para cualquier bloque numérico de 17 dígitos (`\b\d{17}\b`).
* **RFC del Contribuyente:** Extrae la clave del SAT mediante `[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}`.
* **Razón Social:** Identifica el texto posterior al campo `Apellido Paterno, Materno, Nombres(s):`.
* **Código Postal (CP):** Extraer los 5 dígitos numéricos tras `Codigo Postal:`.
* **Importe:** Extrae el valor numérico tras el término `IMPORTE:` (p. ej., `1,408` o `1,408.00`).
* **Fecha Límite:** Extrae exactamente 10 caracteres con el formato de fecha `YYYY-MM-DD` después del patrón `FECHA LIMITE:`.

### 2. Reglas de Limpieza y Normalización
* **Limpieza de Razón Social (Contribuyente):** Para asegurar la coincidencia exacta de datos, se remueven comas, puntos y sufijos societarios comunes (`S.A. DE C.V.`, `S.A.`, `S. DE R.L.`, `S.C.`, etc.) mediante expresiones regulares tolerantes a espacios intermedios. Se conserva únicamente el nombre base del contribuyente (p. ej. `CADURMA, S.A. DE C.V .` $\rightarrow$ `CADURMA`; `INMOCCIDENTE S.A. DE C.V.` $\rightarrow$ `INMOCCIDENTE`).
* **Fecha de Alta y Ordenamiento:** La fecha de alta es el criterio principal de ordenamiento. Los registros de cada RFC se ordenan cronológicamente de forma ascendente. El correlativo de la columna `id` (1, 2, 3...) de Excel sigue este orden exacto.
* **Importe:** Se eliminan caracteres especiales e interrogantes de formato, transformándolo en un float de precisión (p. ej. `1,408` $\rightarrow$ `1408.0`).

### 3. Estructura de Salida y Particionado por RFC
El sistema agrupa los registros según su RFC y crea subcarpetas organizadas en la ruta de destino (`Destino/[RFC]/`):

* **Particionado (Lotes de 300):** Si un RFC tiene más de 300 registros, el sistema genera de forma automática archivos Excel particionados nombrados como `{RFC}_OCB_{particion}.xlsx`.
* **Continuidad:** La asignación del `id` se mantiene de forma continua a lo largo de las particiones (p. ej. partición 1 del 1 al 300; partición 2 del 301 al 600).
* **Nomenclatura de PDFs Renombrados:** Cada PDF de entrada se copia y renombra dentro de su respectiva subcarpeta como:
  `Destino/[RFC]/{Referencia}_{RFC}_{id}.pdf`  *(p. ej., terminación `_1.pdf` para `id=1`)*.
* **Manejo de Incidencias:** Los archivos corruptos o ilegibles se aíslan en la carpeta `Destino/Errores_Lectura/`, y aquellos con datos incompletos en `Destino/Incompletos_o_Invalidos/`.

---

## ⚙️ FASE C — Automatización de Salidas (Consulta y Timbrado)

La **FASE C** toma los archivos Excel generados en la Fase B y automatiza las interacciones con el portal tributario SATQ mediante el motor de Playwright.

### 1. Carga del Catálogo y Lote
El orquestador carga el archivo de referencias y lee:
* **Fila 2 de `Catalogo_RFC`:** Obtiene el RFC emisor, Razón Social y CP para configurar la sesión.
* **Filas de `Control_Referencias`:** Lee las referencias con estado `PENDIENTE`.

### 2. Flujo Operativo en el Portal SATQ
El bot inicializa un navegador Chrome o Edge con perfil persistente para retener las sesiones y navega al portal:
1. **Búsqueda:** Escribe la Referencia en el campo de texto y hace clic en Buscar.
2. **Detección de Estado:**
   * **Caso 1: Factura ya Timbrada (Ya Generada):**
     * Si `Omitir Ya Generadas` está activado: Marca la fila como `OMITIDO-YA GENERADA` en Excel y continúa.
     * Si `Omitir Ya Generadas` está desactivado: Abre la factura, hace clic en el botón de PDF, descarga los 2 PDFs fiscales y actualiza la fila a `OK-YA GENERADA`.
   * **Caso 2: Nueva Factura (Pendiente):**
     * Llena los datos fiscales (Razón Social y CP) obtenidos de `Catalogo_RFC`.
     * **Modo Asistido:** El bot se detiene antes de pulsar "Timbrar", y despliega un aviso visual en la app para aprobación humana.
     * **Modo Autónomo:** El bot pulsa "Timbrar" directamente, emitiendo el registro de auditoría.

### 3. Políticas de Mitigación y Tolerancia a Fallos
* **Monitoreo de 35s post-timbrado:** El bot monitorea la página tras timbrar buscando el botón de descarga del PDF.
* **Mitigación HTTP 500 (FastCGI Timeout):** Si el servidor lanza un código de error HTTP 500, el bot toma captura de pantalla, cierra la sesión del navegador y fuerza un reinicio de navegador desde cero para limpiar conexiones huérfanas.
* **Spinner colgado:** Si la transacción queda en "Esperando..." por más de 15 segundos pero el botón "Salir" está activo, hace clic en Salir para cancelar y evitar el bloqueo de la referencia en el portal.
* **Reintentos:** Permite hasta 2 reintentos automáticos por referencia antes de marcar la fila como `ERROR_REINTENTABLE` y pausar de forma segura la ejecución.

---

## 📊 Estructura de Datos de Excel (Especificación Técnica)

Cada libro generado por el bot se ajusta a la siguiente especificación exacta:

### Hoja 1: `Catalogo_RFC`
Contiene la configuración de emisor aplicable a todas las referencias del libro en una única fila de datos.

| Fila | Columna A (RFC) | Columna B (Razon_Social_Correcta) | Columna C (CP_Correcto) |
|---|---|---|---|
| **Fila 1** | RFC | Razon_Social_Correcta | CP_Correcto |
| **Fila 2** | `CAD1001263P4` | `CADURMA` | `77503` |

### Hoja 2: `Control_Referencias`
Registro de referencias a procesar por el bot y bitácora del estado físico del lote.

| Columna | Nombre del Encabezado | Tipo de Dato | Origen de Ingesta (Fase B) | Comportamiento en Timbrado (Fase C) |
|---|---|---|---|---|
| **Col A** | **id** | Entero | Asignado secuencialmente por fecha alta (1, 2, 3...) | Leído por orquestador |
| **Col B** | **Referencia** | String | Extraído del PDF (17 dígitos) | Leído para búsqueda en SATQ |
| **Col C** | **RFC** | None | Se deja vacío (`None`) | Ignorado (usa el de Catalogo_RFC) |
| **Col D** | **Estado_Proceso** | String | Inicializado en `'PENDIENTE'` | Actualizado a `OK-GENERADA`, `OK-YA GENERADA`, etc. |
| **Col E** | **Lote_Asignado** | String | Vacío | El bot escribe el lote físico (`Lote_1`, `Lote_2`...) |
| **Col F** | **Fecha_Hora_Ejecucion** | String/Fecha | Vacío | El bot estampa la fecha/hora de timbrado |
| **Col G** | **Detalle_Error** | String | Vacío | Detalle técnico detallado si ocurre fallo |
| **Col H** | **CANTIDAD** | Entero | Escrito por defecto con valor `1` | Reservado para portal |
| **Col I** | **IMPORTE** | Float/Entero | Extraído del PDF (p. ej., `1408.0`) | Reservado para validaciones |
| **Col J** | **PORCENTAJE** | None | Vacío | Sin cambios |
| **Col K** | **FECHA LIMITE** | String/Fecha | Extraído del PDF (p. ej., `2026-06-30`) | Columna agregada al final para trazabilidad |

---

## 🛡️ Trazabilidad, Auditoría y QA

El bot mantiene una infraestructura robusta de auditoría paralela para garantizar la integridad operativa:

1. **Auditoría de Descargas (Botón "Validar PDFs"):** Esta utilidad lee el Excel y escanea físicamente la carpeta de descargas buscando la existencia de exactamente 2 PDFs por cada referencia marcada como exitosa. Colorea de **Azul Claro (`#93C5FD`)** si está incompleta (1 PDF) o de **Amarillo Claro (`#FEF08A`)** si no tiene descargas (0 PDFs).
2. **Capturas de Evidencia:** En caso de errores visuales en el portal, Playwright captura la pantalla en la carpeta `/screenshots` para que el operador analice el panel de incidencias en caliente.
3. **Logs Técnicos Rotativos:** Registro continuo de actividad en la consola y en el archivo `/logs/app.log` con rotación automática a los 5 MB para evitar saturación de disco.
