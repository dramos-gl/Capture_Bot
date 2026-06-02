# 📖 Manual de Usuario — Optima Capture Bot
### Versión 1.1.0 | DR 2026

---

## 1. Introducción y Arquitectura

**Optima Capture Bot** es una aplicación de escritorio diseñada para la automatización del proceso de consulta, timbrado de CFDI y descarga de facturas en el portal del SATQ (Servicio de Administración Tributaria de Quintana Roo). 

El sistema combina el poder de **Playwright** (para interactuar de forma segura con el navegador) y **CustomTkinter** (para ofrecer una interfaz gráfica de usuario moderna, limpia y de nivel premium).

### Características Clave:
*   **Gestión por Lotes:** Genera carpetas de descarga ordenadas cada 100 referencias (`Lote_1`, `Lote_2`, etc.).
*   **Modo Dual (Autónomo / Asistido):** Cambia entre timbrado desatendido de alta velocidad o verificación previa guiada.
*   **Trazabilidad y Auditoría:** Reportes en caliente en el archivo maestro de Excel y log inmutable de timbrados en CSV.
*   **Resiliencia:** Manejo robusto de errores de red y prevención de bloqueos de archivos Excel en ejecución.

---

## 2. Configuración Inicial del Sistema

### 2.1. Estructura de Carpetas del Proyecto
Al ejecutarse por primera vez, el bot crea de manera automática la estructura modular necesaria para su funcionamiento:
*   📂 `/downloads`: Almacenamiento raíz de los archivos PDF/XML descargados organizados por subcarpetas de lotes.
*   📂 `/logs`: Contiene la bitácora técnica de actividad del sistema (`optima_capture_bot.log`) y el archivo clave de auditoría (`auditoria_timbrado.csv`).
*   📂 `/screenshots`: Capturas de pantalla tomadas de forma automática en caso de incidencias en el portal para su posterior análisis.
*   📂 `/temp`: Archivos temporales y el perfil persistente de Chrome.

### 2.2. Preparación del Archivo de Control (Excel)
El bot requiere de un archivo Excel maestro llamado por defecto `Optima_Capture_Bot.xlsx` en la raíz del proyecto. El archivo debe contener la siguiente estructura:

1.  **Pestaña `DATOS_EMPRESA` (Catálogo):**
    *   Debe registrar el **RFC**, la **Razón Social** y el **Código Postal (CP)** del receptor fiscal que se utilizarán para la facturación.
2.  **Pestaña `CONTROL_PROCESO` (Lote):**
    *   **Columna A (Referencia):** Clave o número único de la factura/documento a buscar.
    *   **Columna B (Lote):** Reservada para que el bot asigne la carpeta física de salida (ej. `Lote_1`).
    *   **Columna C (Estado):** El estado del registro (`PENDIENTE`, `EN_PROCESO`, `EXITOSO`, `REQUIERE_REVISION`, `DUPLICADO`, etc.).
    *   **Columna D (Error):** Detalle textual de por qué falló un registro si ocurre un error.

---

## 3. Guía de Uso de la Interfaz Gráfica (GUI)

La interfaz se divide en 4 secciones funcionales clave de fácil lectura:

```
┌────────────────────────────────────────────────────────────────────────────┐
│  🚀 OPTIMA CAPTURE BOT — MVP v1.1                     [ Portal: ACTIVO ] ⚙  │
├───────────────────────┬──────────────────────────┬─────────────────────────┤
│ ⚙️ CONTROLES          │ 📊 MÉTRICAS DEL LOTE     │ 🛒 MONITOREO EN VIVO    │
│ [x] Modo Autónomo     │ ⏰ Pendientes: 12        │ Referencia: 450912A     │
│ [x] Omitir Generadas  │ ✅ Exitosos:   45        │ RFC:         AAA010101  │
│                       │ ⚠️ Errores:     2        │ Progreso: [██████░░] 75%│
│ [ ▶ Iniciar Bot ]     ├──────────────────────────┴─────────────────────────┤
│ [ ⏸ Pausar      ]     │ ⚙️ CONSOLA DE LOGS DE ACTIVIDAD                    │
│ [ ■ Detener     ]     │ [12:04:12] [INFO] Buscando referencia 450912A...   │
│                       │ [12:04:15] [SUCCESS] Descarga completada.          │
├───────────────────────┴────────────────────────────────────────────────────┤
│ ⚠️ GESTIÓN DE INCIDENCIAS: Sin fallos registrados.    [Reintentar] [Omitir] │
├────────────────────────────────────────────────────────────────────────────┤
│ OPTIMA CAPTURE BOT  |  Versión: 1.1.0  |  DR 2026          🔋 Sistema listo │
└────────────────────────────────────────────────────────────────────────────┘
```

### 3.1. Panel de Controles Operativos (Izquierda)
*   **Interruptor Modo Autónomo:**
    *   *Desactivado (Modo Asistido):* El bot pausa el flujo antes de timbrar cada factura no generada y le solicita confirmación al usuario mediante los botones `Aprobar` / `Cancelar` en la GUI.
    *   *Activado (Modo Autónomo):* El bot realiza el timbrado del CFDI de forma directa, rápida e ininterrumpida. **Recomendado para corridas nocturnas o masivas.**
*   **Switch Omitir "Ya Generadas":** Si está activo, el bot no vuelve a descargar facturas que en el portal del SATQ ya figuren con estado emitido/timbrado.
*   **Botón Seleccionar Excel:** Permite al operador cambiar el archivo de entrada dinámicamente si no desea usar el predeterminado en la raíz.
*   **Botón Carpeta Descargas:** Permite cambiar la ruta física de destino de los PDF descargados.

### 3.2. Panel de Métricas (Centro)
Muestra un recuento visual en tiempo real de registros procesados, clasificados por:
*   **Pendientes (Azul):** Listos para procesarse.
*   **Exitosos (Verde):** Timbrados y descargados correctamente.
*   **Errores (Rojo):** Registros que fallaron por problemas del portal, datos o red.
*   **Revisión (Gris):** Casos donde la referencia es inválida o no existe.

### 3.3. Monitoreo en Tiempo Real (Derecha)
Muestra la referencia exacta que el bot está procesando en ese instante, el RFC y la acción actual del navegador, acompañado de una barra de progreso porcentual del lote.

---

## 4. Modos de Operación: Autónomo vs. Asistido

El bot tiene una lógica de negocio robusta que previene errores humanos y fiscales. 

### 4.1. Flujo en Modo Asistido (Manual)
1. El bot detecta que una referencia **no está generada** en el portal del SATQ.
2. Ingresa los datos fiscales (Razón Social y Código Postal).
3. Hace una pausa de seguridad en el hilo de ejecución y muestra los botones de validación en pantalla:
   *   **Aprobar Timbrado:** El bot hace clic en timbrar y continúa.
   *   **Cancelar Timbrado:** El bot cancela el proceso de esa fila, la marca como `REQUIERE_REVISION` en el Excel y pasa a la siguiente.
4. Si el operador no responde en 5 minutos, el bot cancela el registro por seguridad para evitar colgar indefinidamente la ejecución.

### 4.2. Flujo en Modo Autónomo (100% Desatendido)
1. El bot detecta que una referencia **no está generada**.
2. Rellena los datos de Razón Social y Código Postal del Catálogo.
3. **Capa de Seguridad (Verificación Post-Fill):** El bot lee el valor físico depositado en los campos del portal web. Si no coincide exactamente con el valor del Catálogo (o está vacío), el bot **aborta el timbrado inmediatamente**, registra la alerta de integridad y clasifica la fila con error para proteger al contribuyente.
4. Si los valores coinciden, el bot timbra de forma inmediata.
5. El evento es reportado automáticamente en el archivo `logs/auditoria_timbrado.csv`.

---

## 5. Auditoría y Trazabilidad

Para garantizar el cumplimiento contable, cada decisión de timbrado (manual o automática) se escribe de manera inmutable en el archivo `logs/auditoria_timbrado.csv`.

**Formato del Archivo de Auditoría:**
```csv
timestamp,razon_social,cp,aprobado,modo
2026-05-30T12:04:15,MI EMPRESA SA DE CV,77500,SI,AUTONOMO
2026-05-30T12:05:22,CLIENTE PRUEBA SA,06000,NO,ASISTIDO
```

---

## 6. Resolución de Problemas Frecuentes

### 6.1. Alerta de Archivo Excel Bloqueado
*   **Problema:** Aparece una ventana emergente en el bot indicando que el archivo Excel está bloqueado.
*   **Causa:** El operador tiene abierto el archivo `Optima_Capture_Bot.xlsx` en Microsoft Excel.
*   **Solución:** Cierre el programa de Excel en Windows. El bot detectará de forma automática la liberación del archivo y continuará con la ejecución de inmediato.

### 6.2. Registro marcado como "ERROR_PORTAL"
*   **Problema:** Una fila se tiñe de color rojo y el bot continúa con el siguiente registro.
*   **Causa:** Falló la carga del elemento web, el portal del SATQ se ralentizó o el PAC demoró más de 30 segundos en responder.
*   **Acción:**
    1. Vaya al panel flotante de fallos al pie de la GUI.
    2. Haga clic en **📷 Ver Captura** para abrir la imagen de evidencia de lo que veía el navegador en el momento exacto del error.
    3. Si el problema fue temporal (red), puede presionar **Reintentar Registro** para devolverlo a estado `PENDIENTE`.

### 6.3. Registro marcado como "DUPLICADO"
*   **Causa:** La misma referencia está escrita más de una vez en el Excel maestro de entrada.
*   **Acción:** El bot autodetecta la duplicidad y marca de forma preventiva el segundo registro para no gastar recursos ni procesar referencias redundantes. No requiere acción correctiva.
