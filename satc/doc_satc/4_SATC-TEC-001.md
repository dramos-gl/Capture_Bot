# SATC-TEC-001: Arquitectura Técnica de Solución
**Categoría:** Arquitectura de Solución  
**Versión:** 1.0  
**Estado:** Vigor / Producción  
**Metodología:** Business-First Architecture (BFA)  
**Fecha:** 2026  

---

## 1. Resumen Ejecutivo y Alcance

**SATC (Sistema de Automatización de Trámites Cancún)** es el subsistema especializado en la automatización del ciclo de descarga de recibos y facturación de la Tesorería Municipal de Cancún y el portal de facturación Benito Juárez.

Este documento define la **Arquitectura Técnica de Solución (SATC-TEC-001)**, detallando la interacción entre la interfaz gráfica (PySide6), el motor de procesamiento asíncrono/hilos (QThread + Playwright), la capa de persistencia en PostgreSQL (`db_satc`), la verificación de disponibilidad en red de la ruta `CANCUN_PDF_BASE_PATH` y la resiliencia en modo de contingencia local.

---

## 2. Diagrama de Arquitectura Técnica

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        GUI PySide6 (Thread Principal)                  │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                 R2FCancunView (r2f_cancun_view.py)             │   │
│   │  - Selector de Ruta (CANCUN_PDF_BASE_PATH / custom)             │   │
│   │  - GLStatusIndicator [CONECTADO | NO CONECTADO]                │   │
│   │  - Switch de Modo (RECIBOS / FACTURAS)                         │   │
│   │  - Alertas Preventivas de Desconexión de Red                    │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
└───────────────────────────────────┼────────────────────────────────────┘
                                    │ (Inicia Worker)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Worker Hilo Secundario (QThread)                     │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │               BotReciboCunWorker (bot_recibo_worker.py)         │   │
│   │  - Executa Playwright (sync_api) stealth mode                  │   │
│   │  - Consulta portal recibo.tesoreriacancun.com                   │   │
│   │  - Extrae metadatos y valida folios pase de caja/electrónicos │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
└───────────────────────────────────┼────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    Almacenamiento y Persistencia                       │
│                                                                        │
│  ┌───────────────────────────────┐     ┌────────────────────────────┐  │
│  │ Base de Datos PostgreSQL      │     │ Repositorio de Archivos    │  │
│  │ (db_satc)                │     │ (Red LAN / Local)          │  │
│  │ - satc_configuracion     │     │ - CANCUN_PDF_BASE_PATH     │  │
│  │ - satc_produccion        │     │ - Contingencia local       │  │
│  │ - satc_auditoria         │     │   (storage/contingencia)   │  │
│  └───────────────────────────────┘     └────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Patrones Técnicos Fundamentales

### 3.1 Desacoplamiento Hilo Principal (UI) vs Hilo Secundario (RPA Worker)
Para prevenir el congelamiento (*UI freezing*) durante operaciones intensivas I/O de Playwright (navegación web, descargas de PDFs, esperas de selectores), toda la lógica del robot se ejecuta dentro de **`BotReciboCunWorker`** derivido de `QThread`.

Los eventos y progresos se notifican hacia la vista únicamente mediante **Señales de Qt (`PySide6.QtCore.Signal`)**:
- `status_changed(str)`: Transmite mensajes de log hacia la consola visual.
- `metric_updated(str, int)`: Actualiza las tarjetas de métricas (pendientes, exitosos, errores).
- `progress_changed(int, int)`: Controla la barra de progreso.
- `folio_status_changed(dict)`: Muestra en tiempo real el folio y estado en procesamiento.
- `finished_processing(bool, str)`: Restablece los botones y controles de la interfaz al terminar.

---

### 3.2 Estrategia Anti-Hardcodeo de Selectores
Ningún selector CSS, XPath o identificador del portal web vive hardcodeado en el código fuente de Python.
Todos los selectores se gestionan dinámicamente mediante el patrón **Page Object Model (POM)** cargando la definición desde la tabla:
`satc_configuracion.localizador_portal` (`CANCUN_RECIBO` / `CANCUN_FACTURA`).

---

### 3.3 Verificación de Conectividad a la Unidad de Red (`CANCUN_PDF_BASE_PATH`)

La arquitectura integra un sistema asíncrono de comprobación de almacenamiento mediante **`PathVerifyThread`**:

1. **Consulta de Configuración**: La vista recupera el parámetro **`CANCUN_PDF_BASE_PATH`** desde la tabla `satc_configuracion.parametro_sistema`.
2. **Prueba de Accesibilidad**: `PathVerifyThread` intenta validar permisos de lectura y escritura en la ruta de red o directorio configurado.
3. **Indicador Visual de Estado (`GLStatusIndicator`)**:
   - **`CONECTADO` (Verde)**: La unidad de red está accesible y lista para producción.
   - **`NO CONECTADO` (Rojo)**: La unidad de red no está accesible o se encuentra desmontada.
4. **Respuesta Preventiva**: Si el estado es `NO CONECTADO` y el operador presiona `▶ Iniciar Bot`, se bloquea la ejecución directa y se despliega una advertencia modal (`QMessageBox.warning`) solicitando al operador verificar la red o reportar la falla a soporte de TI.

---

### 3.4 Resiliencia y Modo de Contingencia Local

Si por razones operativas el usuario decide continuar con el procesamiento mientras la unidad de red está en estado `NO CONECTADO`:
1. **Descarga Temporal**: Los PDFs descargados se almacenan en el directorio local de contingencia: `storage/contingencia/recibos/[Año]/[RFC]/[Concepto]/`.
2. **Sincronización Diferida**: Cuando la conexión a la unidad de red por defecto (`CANCUN_PDF_BASE_PATH`) se restablece, el hilo secundario **`SyncContingencyThread`** detecta los archivos locales, los migra hacia la unidad de red compartida y actualiza en la base de datos la ubicación física real (`ruta_archivo`).

---

---

### 3.5 Subsistema de Extracción OCR y Vinculación RPP Parametrizado

Para la vinculación masiva y automática de Folios Reales Electrónicos de Resoluciones de Régimen de Propiedad en Condominio emitidas por el RPP y el Catastro:
1. **Extractor Desacoplado (`RppResolutionExtractor`)**:
   - Lee documentos PDF de resoluciones, detecta la sección `'FOLIOS GENERADOS'` y segmenta las Unidades de Propiedad Exclusiva (UPE).
   - Extrae de forma estructurada: `numero_fraccion`, `interior`, `edificio`, `nivel`, `numero_oficial` y `folio_electronico`.
2. **Cero Hardcodeo de Patrones Regex (`rpp_ocr_patterns.json`)**:
   - Los patrones regulares y variaciones ortográficas se parametrizan en `satc/config/rpp_ocr_patterns.json`.
   - Soporta erratas mecanográficas y OCR habituales en los oficios (ej. `UNIDA DE PORPIEDAD`, `OFCIAL`, `NUMEO`, `NÚMERO`, `EDIFCIO`).
   - Implementa un mecanismo de fallback seguro (`DEFAULT_PATTERNS`) en caso de ausencia temporal del archivo de configuración.
3. **Criterios de Vinculación y Blindaje de Datos**:
   - Vinculación Primaria: Coincidencia por `Fracción / UPE` o `Interior`.
   - Vinculación Secundaria: Coincidencia por `Número Oficial` (columna `'No.'` del oficio RPP / Catastro).
   - Filtros Interactivos en KPIs: La interfaz (`SatcCatalogsView`) permite filtrar registros con un solo clic sobre los indicadores (ej. faltantes, no vinculables o huérfanos).

---

### 3.6 Reglas de Integridad Empresarial para Carga Inicial de Viviendas

Para garantizar la rigurosidad y exactitud contable/catastral de un sistema de grado empresarial:
1. **Bloqueo Preventivo ante Régimen Completo (Fast-Fail)**:
   - Si un régimen ya cuenta con el 100% de sus viviendas físicas en BD (`viviendas_en_bd >= total_upes`), la interfaz bloquea la Carga Inicial, alerta al usuario y conmuta automáticamente a la etapa operativa siguiente: `'2. Vincular Folios RPP'`.
   - Se prohíbe explícitamente seleccionar archivos en modo Carga Inicial si la capacidad está agotada.
2. **Validación Estricta de Capacidad Restante y Desduplicación Interna**:
   - **Excedente**: Si `len(archivo) > total_upes`, el análisis asíncrono rechaza la carga inmediatamente.
   - **Duplicados Internos en Archivo**: Si el archivo Excel contiene filas repetidas para la misma clave `(Edificio, Interior)`, se rechaza la carga indicando los ejemplos conflictivos para su corrección previa.
   - **Alerta de Carga Parcial**: Si `len(archivo) < total_upes`, el sistema notifica de forma destacada al operador la cantidad faltante antes de confirmar la inserción, previniendo cargas incompletas por descuido humano.
3. **Coherencia de Destino vs Espacio**:
   - `DESTINO = 'SERVICIO'` asigna forzosamente por defecto `ESPACIO = 'AREAS_COMUNES'` (impidiendo que se registre erróneamente como `'VIVIENDA'`).
4. **Validaciones en Botón "Cargar Archivo" y Cambio de Operación**:
   - **Precondiciones Obligatorias**: El botón `'Cargar Archivo'` exige estrictamente la selección previa de un **Desarrollo**, un **Régimen en Condominio** y una **Operación** antes de abrir el explorador de archivos.
   - **Reactividad de la Tabla en Conmutación de Operación**: Al cambiar de operación, el sistema limpia el staging de análisis anterior y recarga automáticamente la tabla de viviendas directamente desde la base de datos para ese régimen, garantizando una vista limpia y consistente del padrón registrado sin residuos de previsualizaciones previas.
5. **Exportación Dual Inteligente (Excel)**:
   - **Modo Padrón en BD**: Al seleccionar un régimen con viviendas existentes en BD, el botón `'Exportar Datos'` se activa inmediatamente permitiendo descargar el padrón completo registrado (`Padron_Viviendas_[Desarrollo]_[Regimen].xlsx`).
   - **Modo Análisis de Archivo**: Si se carga un archivo (Excel o PDF de resolución), el botón `'Exportar Datos'` prioriza la exportación de los datos extraídos/analizados (`Datos_Extraidos_[Modo]_[Desarrollo].xlsx`), conservando ambas funcionalidades de forma complementaria y sin fricción.
6. **Lógica de Refresco y Preservación de Estado (`Refrescar`)**:
   - **Recarga Integral Asíncrona**: Al presionar `'Refrescar'` en la Toolbar superior, el sistema consulta los datos frescos desde la base de datos o API.
   - **Preservación de Selección**: Si el operador ya tenía un régimen seleccionado, el refresco recarga los catálogos y re-selecciona automáticamente el mismo régimen, actualizando los registros de viviendas, contadores de avance y métricas sin obligar al usuario a volver a seleccionar el régimen.
   - **Limpieza de Residuos**: Si había un archivo en staging no aplicado, el refresco lo descarta y regresa la tabla al padrón fidedigno de la base de datos.

---

## 4. Parámetros Principales del Sistema

| Parámetro | Clave BD / Código | Valor Predeterminado / Descripción |
| :--- | :--- | :--- |
| **Ruta Repositorio PDF** | `CANCUN_PDF_BASE_PATH` | `T:\CANCUN` (Ruta o unidad de red compartida) |
| **URL Portal Recibos** | `CANCUN_PORTAL_RECIBO_URL` | `https://recibo.tesoreriacancun.com` |
| **URL Portal Facturas** | `CANCUN_PORTAL_FACTURA_URL` | `https://benitojuarez.expidefactura.com/` |
| **Reintentos Máximos** | `CANCUN_MAX_REINTENTOS` | `3` (Intentos automáticos por folio en error) |
| **Timeout Transacción** | `CANCUN_BOT_TIMEOUT_MS` | `30000` (Tiempo de espera en ms) |
| **Configuración OCR RPP** | `RPP_PATTERNS_FILE` | `satc/config/rpp_ocr_patterns.json` (Patrones regex y erratas toleradas) |

