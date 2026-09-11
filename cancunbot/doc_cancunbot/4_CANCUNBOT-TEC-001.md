# CANCUNBOT-TEC-001: Arquitectura Técnica de Solución
**Categoría:** Arquitectura de Solución  
**Versión:** 1.0  
**Estado:** Vigor / Producción  
**Metodología:** Business-First Architecture (BFA)  
**Fecha:** 2026  

---

## 1. Resumen Ejecutivo y Alcance

**CancunBot** es el subsistema especializado en la automatización del ciclo de descarga de recibos y facturación de la Tesorería Municipal de Cancún y el portal de facturación Benito Juárez.

Este documento define la **Arquitectura Técnica de Solución (CANCUNBOT-TEC-001)**, detallando la interacción entre la interfaz gráfica (PySide6), el motor de procesamiento asíncrono/hilos (QThread + Playwright), la capa de persistencia en PostgreSQL (`db_cancunbot`), la verificación de disponibilidad en red de la ruta `CANCUN_PDF_BASE_PATH` y la resiliencia en modo de contingencia local.

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
│  │ (db_cancunbot)                │     │ (Red LAN / Local)          │  │
│  │ - cancunbot_configuracion     │     │ - CANCUN_PDF_BASE_PATH     │  │
│  │ - cancunbot_produccion        │     │ - Contingencia local       │  │
│  │ - cancunbot_auditoria         │     │   (storage/contingencia)   │  │
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
`cancunbot_configuracion.localizador_portal` (`CANCUN_RECIBO` / `CANCUN_FACTURA`).

---

### 3.3 Verificación de Conectividad a la Unidad de Red (`CANCUN_PDF_BASE_PATH`)

La arquitectura integra un sistema asíncrono de comprobación de almacenamiento mediante **`PathVerifyThread`**:

1. **Consulta de Configuración**: La vista recupera el parámetro **`CANCUN_PDF_BASE_PATH`** desde la tabla `cancunbot_configuracion.parametro_sistema`.
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

## 4. Parámetros Principales del Sistema

| Parámetro | Clave BD / Código | Valor Predeterminado / Descripción |
| :--- | :--- | :--- |
| **Ruta Repositorio PDF** | `CANCUN_PDF_BASE_PATH` | `T:\CANCUN` (Ruta o unidad de red compartida) |
| **URL Portal Recibos** | `CANCUN_PORTAL_RECIBO_URL` | `https://recibo.tesoreriacancun.com` |
| **URL Portal Facturas** | `CANCUN_PORTAL_FACTURA_URL` | `https://benitojuarez.expidefactura.com/` |
| **Reintentos Máximos** | `CANCUN_MAX_REINTENTOS` | `3` (Intentos automáticos por folio en error) |
| **Timeout Transacción** | `CANCUN_BOT_TIMEOUT_MS` | `30000` (Tiempo de espera en ms) |
