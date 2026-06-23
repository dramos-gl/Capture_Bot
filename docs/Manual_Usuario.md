# 📖 Manual de Operación — Optima Capture Bot
### Versión 1.1.0 | Guía de Operación para Usuarios Finales

Bienvenido al manual operativo de **Optima Capture Bot**. Este manual ha sido redactado desde la perspectiva de Product Owner y Analista de Negocio para proveerte de una guía clara, sencilla y libre de tecnicismos complejos para la operación diaria del bot.

---

## 1. Consideraciones Antes de Iniciar el Bot

Para asegurar una ejecución fluida y evitar interrupciones operativas, asegúrate de cumplir con los siguientes puntos antes de hacer clic en **"Iniciar Bot"**:

* **Cerrar el Archivo Excel:** El bot leerá y actualizará el archivo `Optima_Capture_Bot.xlsx` en tiempo real. **Mantén el archivo cerrado** durante la ejecución. Si está abierto, el bot se pausará e indicará una advertencia de bloqueo.
* **Verificar las Rutas en la Barra de Estado:** Pasa el cursor del mouse sobre la barra inferior de la aplicación (los indicadores de ruta de Excel y carpeta de descargas). Los *tooltips* emergentes te mostrarán la ruta completa seleccionada para que confirmes que estás usando el archivo y la carpeta correctos.
* **Instalación de Navegadores:** El bot requiere tener Google Chrome o Microsoft Edge instalado en el sistema. Utiliza un perfil persistente (`perfil_bot`) para recordar sesiones previas del portal SATQ.

---

## 2. Guía de Botones e Interruptores (Switches)

La interfaz gráfica contiene controles diseñados para dar flexibilidad en caliente (en tiempo real):

### 2.1 Interruptores Clave
* **Modo Autónomo (Switch):**
  * **Desactivado (Modo Asistido):** El bot buscará el registro y rellenará los datos en el portal, pero **se detendrá y te pedirá confirmación visual** (mediante un panel en la app) antes de pulsar "Timbrar". Ideal para verificar datos de nuevos clientes.
  * **Activado (Modo Autónomo - RECOMENDADO):** El bot rellenará los datos y procesará la generación de la factura de forma 100% automática y veloz sin interrumpir. *Se puede cambiar en caliente (mientras el bot trabaja).*
* **Omitir 'Ya Generadas' (Switch):**
  * **Activado:** Si la factura ya está timbrada en el portal, el bot **no descargará los PDFs** y pasará directamente al siguiente registro. Ahorra tiempo y ancho de banda.
  * **Desactivado:** Si la factura ya está timbrada, el bot la abrirá y **descargará sus respectivos archivos PDF**.

### 2.2 Botones de Control Operativo
* **Iniciar Bot:** Comienza el proceso de validación previa y abre el portal.
* **Pausar / Reanudar:** Detiene de forma segura la ejecución al finalizar la fila que se esté procesando en ese momento. Al hacer clic en Reanudar, continuará justo donde se quedó.
* **Detener Seguro:** Detiene permanentemente el lote al concluir la fila actual.
* **Validar PDFs:** Ejecuta una auditoría rápida de tus descargas físicas contra lo que dice el Excel, marcando con colores las filas inconsistentes.

---

## 3. ¿Cuándo Aplicar "Omitir Ya Generadas"?

Esta opción determina si deseas guardar los PDFs físicos de facturas que ya fueron timbradas con anterioridad en el portal de SATQ.

### Escenario A: Activar "Omitir 'Ya Generadas'" (Recomendado para Lotes Nuevos / Procesamientos Grandes)
* **Cuándo usarlo:** Cuando deseas procesar un archivo Excel grande donde la prioridad es únicamente timbrar y generar los CFDI **nuevos** (pendientes) y no te interesa descargar las facturas que ya se timbraron en el pasado.
* **Resultado:** Las referencias previamente timbradas se marcan en tu Excel con el estado `OMITIDO-YA GENERADA` de forma instantánea sin perder tiempo en descargas.

### Escenario B: Desactivar "Omitir 'Ya Generadas'" (Recomendado para Auditorías de Entregables)
* **Cuándo usarlo:** Cuando requieres tener en tu carpeta de descargas los archivos PDF de absolutamente todas las referencias del Excel, sin importar si son facturas nuevas o timbradas previamente.
* **Resultado:** Para cada referencia ya timbrada, el bot la ubicará, descargará sus 2 archivos PDF y marcará el estado en Excel como `OK-YA GENERADA`.

---

## 4. Proceso de Descarga Selectiva de Referencias "Ya Generadas"

Si procesaste un lote con la opción de omitir activada y ahora deseas descargar **únicamente** los PDF de referencias específicas (por ejemplo, las que quedaron como `OMITIDO-YA GENERADA`), sigue este sencillo procedimiento:

1. **Abre tu archivo Excel** (`Control_Referencias`).
2. Localiza las filas específicas que deseas descargar (ej. las que dicen `OMITIDO-YA GENERADA`).
3. **Limpia la celda** de la columna `Estado_Proceso` de esas filas (o escribe la palabra **`PENDIENTE`**).
4. Deja las demás filas (las exitosas `OK-GENERADA`) **exactamente como están**.
5. **Cierra el archivo Excel**.
6. Abre la aplicación del Bot y **DESACTIVA** el interruptor **"Omitir 'Ya Generadas'"**.
7. Haz clic en **"Iniciar Bot"**.

El bot **saltará automáticamente** todas las filas que conserven el estado `OK-GENERADA` y procesará únicamente las filas que dejaste vacías, descargando sus PDFs físicos y actualizando su estado a `OK-YA GENERADA`.

---

## 5. Gestión Operativa de Incidencias

Si el bot se detiene o detecta un problema con un registro, la aplicación te proporciona un panel de incidencias en el extremo inferior derecho:

* **Ver Captura:** Si una referencia falló por error de portal, haz clic aquí para ver una imagen exacta de cómo se veía la pantalla del portal en el momento del fallo (guardada en `screenshots/`).
* **Reintentar Registro:** Si el portal falló temporalmente, haz clic para volver a consultar ese registro específico inmediatamente.
* **Omitir Registro:** Si la referencia tiene un dato erróneo que no puedes corregir al momento, haz clic para saltarla y continuar con el lote.
* **Revisión Manual:** Cambia el estado del registro a `REQUIERE_REVISION` para que puedas analizarlo manualmente después.

---

## 6. Clasificación de Carpetas de Descarga (Lotes)

Para facilitar la organización fiscal y evitar que tu carpeta de descargas se sature con miles de archivos sueltos, el bot organiza de forma automática las descargas físicas en carpetas de **lotes de 100 registros**:

* Registros de la fila **2 a 101** de Excel $\rightarrow$ se guardan en la subcarpeta `Lote_1`.
* Registros de la fila **102 a 201** de Excel $\rightarrow$ se guardan en la subcarpeta `Lote_2`.
* Registros de la fila **202 a 301** de Excel $\rightarrow$ se guardan en la subcarpeta `Lote_3`.

*(El bot creará estas subcarpetas de manera transparente sin que tengas que intervenir)*.

---

## 7. Herramienta de Auditoría "Validar PDFs"

Si en algún momento deseas comprobar que las descargas en tu disco coinciden exactamente con la información de tu archivo Excel, haz clic en el botón **"Validar PDFs"**. Esta herramienta asíncrona realizará lo siguiente:

1. Escaneará tu carpeta de descargas de forma inteligente.
2. Comparará la cantidad física de PDFs encontrados para cada referencia en el Excel (debe haber exactamente 2 archivos PDF por referencia).
3. **Pintará las celdas en tu Excel** para darte un reporte visual instantáneo:
   * 🟦 **Azul Claro (`#93C5FD`):** Referencia **Incompleta** (solo se descargó 1 PDF en disco).
   * 🟨 **Amarillo Claro (`#FEF08A`):** Referencia **Sin descargas** (0 PDFs en disco).
   * ⬜ **Sin Relleno:** Descarga **Completa** (los 2 PDFs están a salvo en disco).
4. Listará en la consola de logs de la aplicación cualquier archivo extra o no identificado que se haya guardado manualmente en la carpeta de descargas.
