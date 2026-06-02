# 📖 Manual de Usuario — Optima Capture Bot
### Versión 1.1.0 | DR 2026

---

## 1. Introducción

**Optima Capture Bot** es una aplicación de escritorio local que automatiza la consulta de referencias en el portal SATQ, la generación / timbrado de CFDI y la descarga de documentos en PDF.

La aplicación combina:
* **CustomTkinter** para la interfaz gráfica.
* **Playwright** para la automatización del navegador.
* **openpyxl** para leer y escribir el archivo Excel de control.
* **JSON** para persistir configuración de usuario.

---

## 2. Qué hace el bot hoy

### Funcionalidades implementadas
* Carga un archivo Excel de control y valida su estructura.
* Valida el RFC de la empresa y la referencia para cada registro.
* Detecta duplicados internos en el lote antes de procesar.
* Abre un navegador visible con un perfil persistente de Chrome/Edge.
* Navega al portal SATQ y consulta cada referencia.
* Genera CFDI si la referencia no está timbrada.
* Descarga los documentos PDF en carpetas organizadas por lote.
* Actualiza el estado de cada fila en Excel.
* Guarda logs de actividad en `logs/optima_capture_bot.log`.
* Registra decisiones de timbrado en `logs/auditoria_timbrado.csv`.

### Comportamiento actual
* El bot usa por defecto `Optima_Capture_Bot.xlsx` en la raíz del proyecto.
* Si el archivo no existe, el operador debe seleccionarlo desde la GUI.
* El modo de timbrado puede ser `asistido` o `autonomo`.
* El panel de errores y botones de reintento son mayoritariamente visuales, pero el flujo principal no respalda todas las acciones manuales hoy.
* La funcionalidad de captura de pantalla existe en el código, pero no se ejecuta automáticamente en el flujo actual.

---

## 3. Requisitos de archivo Excel

### 3.1 Hoja `Catalogo_RFC`
El archivo Excel debe contener la hoja llamada exacta:
* `Catalogo_RFC`

En la fila 2:
* Columna A: RFC de la empresa.
* Columna B: Razón Social.
* Columna C: Código Postal (CP).

### 3.2 Hoja `Control_Referencias`
El bot lee los registros desde la hoja exacta:
* `Control_Referencias`

Columnas obligatorias:
* Columna A: `ID` (número secuencial o identificador interno).
* Columna B: `Referencia` (valor buscado en SATQ).
* Columna C: `RFC` (puede estar vacío y se escribe desde el catálogo).
* Columna D: `Estado_Proceso` (el bot actualiza este campo).
* Columna E: `Lote_Asignado` (el bot usa `Lote_1`, `Lote_2`, ...).
* Columna F: `Fecha_Hora_Ejecucion` (actualizado por el bot).
* Columna G: `Detalle_Error` (mensaje de error o control).

Columnas adicionales leídas opcionalmente:
* Columna H: `Cantidad`.
* Columna I: `Importe`.
* Columna J: `Porcentaje`.

### 3.3 Estados admitidos
El bot utiliza los siguientes estados para las filas:
* `PENDIENTE` — aún no procesado.
* `VALIDADO` — referencia aceptada y lista para consulta.
* `EN_PROCESO` — actualmente en ejecución.
* `EXITOSO` — procesado y descargado correctamente.
* `OK-GENERADA` — se generó un CFDI nuevo.
* `OK-YA GENERADA` — ya existía factura en SATQ.
* `ERROR_VALIDACION` — validación local previa fallida.
* `ERROR_REINTENTABLE` — error de portal que necesita atención.
* `ERROR_LOCAL` — fallo al guardar o error crítico.
* `DUPLICADO` — referencia repetida dentro del mismo lote.
* `OMITIDO-YA GENERADA` — se omitió una referencia ya generada cuando se pidió no procesar duplicados.
* `REQUIERE_REVISION` — estado que se reserva para revisión manual.

---

## 4. Preparación previa a la ejecución

### 4.1 Archivos y carpetas
La aplicación genera automáticamente al primer inicio:
* `logs/`
* `downloads/`
* `screenshots/`
* `temp/`

### 4.2 Ajustes persistidos
La configuración se guarda en:
* `settings.json`

Valores importantes:
* `excel_path` — ruta al archivo Excel.
* `download_dir` — carpeta de destino para descargas.
* `satq_url` — URL del portal SATQ.
* `modo_timbrado` — `asistido` o `autonomo`.
* `max_timbrado_retries` — número máximo de reintentos por error de portal.
* `reintento_automatico` — si el bot debe recargar y volver a intentar.

---

## 5. Uso de la interfaz gráfica

### 5.1 Panel de controles operativos
* **Omitir 'Ya Generadas'**: Si está activo, el bot no procesa referencias que ya existan como generadas en el portal.
* **Modo Autónomo**: Si está activo, el bot timbra automáticamente sin pedir confirmación previa.
* **Iniciar Bot**: Inicia el proceso completo.
* **Pausar / Reanudar**: Detiene la ejecución al finalizar la fila actual y puede reanudarla.
* **Detener Seguro**: Finaliza la ejecución al cerrar el ciclo de procesamiento.
* **Seleccionar Excel**: Cambia el archivo de entrada.
* **Carpeta Descargas**: Cambia el directorio donde se guardan los PDF.
* **Configurar URL SATQ**: Permite modificar la URL del portal en caso de cambios del sitio.

### 5.2 Panel de métricas
El sistema muestra en tiempo real:
* pendientes,
* exitosos,
* errores,
* omitidos,
* revisiones,
* total de registros.

### 5.3 Monitoreo en tiempo real
Muestra:
* referencia actual,
* RFC usado,
* estado de la fila,
* acción en curso,
* lote activo,
* progreso porcentual.

### 5.4 Consola de logs
Registra mensajes del bot en pantalla, en formato de hora y nivel.

### 5.5 Panel de gestión de incidencias
Los botones disponibles hoy son:
* **Ver Captura** — abre la última captura de pantalla disponible en `screenshots/`.
* **Reintentar Registro** — botón informativo, no reinicia automáticamente el flujo actual.
* **Omitir Registro** — botón de soporte visual que indica omisión.
* **Revisión Manual** — marca la intención de revisar luego.

> Nota: en la versión actual, estas acciones son mayormente de soporte visual y no siempre impactan el motor de procesamiento principal.

---

## 6. Qué sucede durante la ejecución

1. El bot carga los datos del catálogo y las referencias desde Excel.
2. Valida el RFC de la empresa y cada referencia.
3. Detecta duplicados locales y marca las filas repetidas como `DUPLICADO`.
4. Inicia Playwright con un navegador visible y perfil persistente.
5. Navega al portal SATQ.
6. Procesa cada registro válido:
   * consulta la referencia,
   * determina si el CFDI ya está generado,
   * genera el CFDI si es necesario,
   * descarga los PDFs,
   * actualiza el estado en Excel.
7. Crea carpetas físicas de descarga por lotes de 100 filas (`Lote_1`, `Lote_2`, ...).

---

## 7. Auditoría y trazabilidad

### Archivos de auditoría
* `logs/optima_capture_bot.log`: registro de todo el flujo de sistema.
* `logs/auditoria_timbrado.csv`: registro de cada aprobación o cancelación de timbrado.

### Formato de auditoría
```csv
timestamp,razon_social,cp,aprobado,modo
2026-06-02T15:18:22,EMPRESA S.A. DE C.V.,77500,SI,autonomo
2026-06-02T15:20:10,EMPRESA S.A. DE C.V.,77500,NO,asistido
```

---

## 8. Problemas comunes y recomendaciones

### 8.1 Excel bloqueado
* Causa: el archivo `Optima_Capture_Bot.xlsx` está abierto en Excel.
* Solución: ciérrelo y espere a que el bot continue automáticamente.

### 8.2 No aparece el botón Iniciar Bot
* Compruebe que:
  * exista el archivo Excel seleccionado,
  * exista la carpeta de descargas configurada.

### 8.3 Error de referencia inválida
* El campo `Referencia` debe tener al menos 6 caracteres.
* No debe incluir comillas, asteriscos, barras invertidas ni signos `<>|`.

### 8.4 Duplicados internos
* Si la misma referencia aparece varias veces en `Control_Referencias`, el bot marcará las filas repetidas como `DUPLICADO`.

### 8.5 Descargar PDFs en lotes
* El directorio `downloads/` se organiza por subcarpetas `Lote_1`, `Lote_2`, etc.
* Si la carpeta de descargas no existe, el bot la crea automáticamente.

---

## 9. Limitaciones conocidas

* La espera de login manual no se activa en el flujo actual, porque el bot asume que el portal no requiere autenticación automatizada.
* El panel de errores muestra opciones, pero las acciones `Reintentar Registro`, `Omitir Registro` y `Revisión Manual` no modifican el registro de Excel automáticamente.
* La captura de pantalla de errores está implementada en `app/scraper.py`, pero actualmente no hay una llamada automática a `capturar_pantalla()` en el proceso principal.
* El bot usa selectores específicos del portal en `app/scraper.py` para localizar los campos y botones de búsqueda y timbrado.
* El modo de validación previa al timbrado funciona solo si el modo es `asistido` y el proceso llega a la generación de CFDI.

### 9.1 Mantenimiento de selectores del portal
* Los selectores actuales se basan en los identificadores internos del sitio:
  * `input#Referencia`
  * `input#RFC`
  * `button[type='submit']` para Buscar
  * `button:has-text('Generar CFDI'), a:has-text('Generar CFDI')`
  * `input#NombreReceptor`
  * `input#DomicilioFiscalReceptor`
  * `button#btnTimbrar`
* Si el portal actualiza los identificadores o agrega nuevos campos, se debe revisar `app/scraper.py` y ajustar los selectores en esa función para que el bot localice los elementos correctos.
* El bot descarga los archivos PDF generados tras el timbrado usando el método `_descargar_pdfs()` en `app/scraper.py`.
  * Los PDFs se guardan en el directorio `downloads/` dentro de una subcarpeta por lote (`Lote_1`, `Lote_2`, etc.).
  * El nombre de archivo se construye con `referencia`, `RFC` e índice: `REFERENCIA_RFC_1.pdf`, `REFERENCIA_RFC_2.pdf`.
* Para futuras actualizaciones, use la consola del navegador (DevTools) y verifique si el elemento cambió a un nuevo `id`, `name`, `data-*` o etiqueta visible.
* Si se agregan nuevos campos obligatorios en el portal, el bot necesitará extender la función `_generar_cfdi()` para completar esos datos antes de pulsar `Timbrar`.

---

## 10. Recomendaciones de operación

* Mantenga el archivo Excel cerrado mientras el bot esté procesando registros.
* Utilice `Modo Autónomo` para lotes grandes cuando confíe en los datos del catálogo.
* Si hay errores múltiples, revise primero el archivo `logs/optima_capture_bot.log`.
* No elimine manualmente `settings.json`; ese archivo guarda la ruta de Excel y la carpeta de descargas.

---

## 11. Análisis QA rápido

* El flujo actual es funcional, pero existen áreas de mejora:
  * consolidar la gestión de errores desde la UI con cambios reales en Excel,
  * activar capturas automáticas en fallos del portal,
  * soportar login manual de forma real cuando el portal lo requiera.
