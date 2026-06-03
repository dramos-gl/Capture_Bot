# 🚀 Optima Capture Bot — Plan Maestro Operativo (v1.1.0)

## 1. Visión del Producto

### Objetivo Estratégico

Crear una herramienta local que automatice consultas SATQ, timbrado CFDI y descarga de documentos desde un archivo de control.

El producto está diseñado para:
* reducir intervención manual,
* conservar trazabilidad,
* evitar duplicados,
* permitir control de pausas y detenciones seguras.

---

## 2. Estado actual de la v1.1.0

### Funcionalidades implementadas
* Carga de Excel con validación de estructura de hojas.
* Validación de RFC contra una **lista blanca corporativa** configurada dinámicamente.
* Detección de duplicados internos en el lote.
* Automatización de navegador con Playwright.
* Consulta de referencias en SATQ.
* **Mitigación de Cuelgues post-Timbrado:** Monitoreo de 35 segundos con autodetección de errores **HTTP 500 (FastCGI Timeout)** o botón de espera colgado, aplicando botón de Salir o recarga de pestaña.
* **Integridad de Descargas:** Asignación condicional de estado de éxito (`OK-GENERADA`) a la presencia real de PDFs físicos.
* **Herramienta Validar PDFs:** Escaneo asíncrono de PDFs del lote, pintado de celdas en el Excel (**Azul** para incompleto, **Amarillo** para no descargado) y logs de archivos extras.
* Persistencia de estados en Excel.
* Logs técnicos rotativos a 5 MB y auditoría de decisiones en CSV.
* Visualización persistente y interactiva de rutas completas en la barra de estado mediante Tooltips.
* **Configuración Externa (settings.json):** Parametrización de RFCs permitidos y selectores DOM de Playwright para facilitar el mantenimiento del bot ante cambios en el portal SATQ.

---

## 3. Arquitectura actual

```plaintext
main.py
  └─ inicializa entorno y logging (RotatingFileHandler 5MB)
  └─ carga settings y Excel
  └─ crea cola de eventos
  └─ inicia UI

app/
  ├─ gui.py             # Interface operativa y tooltips interactivos
  ├─ orchestrator.py    # Flujo de procesamiento y callback de timbrado
  ├─ scraper.py         # Playwright headed, timeouts, mitigaciones 500 y selectores dinámicos
  ├─ excel_handler.py   # openpyxl, guardados atómicos y coloreado de celdas
  ├─ validator.py       # Expresiones regulares SAT, duplicados y validación dinámica de RFC
  ├─ settings.py        # Configuración persistente en JSON (RFCs y selectores)
  ├─ paths.py           # Rutas absolutas del proyecto
  ├─ pdf_validator.py   # Utilidad de validación asíncrona de PDFs
```

---

## 4. Flujo funcional principal

1. `main.py` crea carpetas y configura logging.
2. Se carga la ruta de Excel desde `settings.json` o `Optima_Capture_Bot.xlsx`.
3. Se crea un hilo de trabajo para mantener la UI responsiva.
4. `BotOrchestrator` carga el catálogo y los registros del Excel.
5. Se ejecuta la validación previa:
   * RFC de la empresa (validado contra la lista dinámica en settings.json),
   * formato de referencia,
   * duplicados internos.
6. Se abre un navegador visible con perfil persistente.
7. Se procesa cada referencia:
   * busca en SATQ usando los selectores configurados dinámicamente,
   * detecta si está generada,
   * genera CFDI si es necesario (con mitigación de cuelgues),
   * descarga PDFs,
   * actualiza Excel tras verificar que la descarga se completó.
8. El estado final de cada fila se escribe en el archivo Excel.

---

## 5. Componentes clave

### 5.1 `app/gui.py`
* Construye la UI con CustomTkinter.
* Envía comandos de usuario al orquestador.
* Deshabilita botones de interacción al iniciar el bot o validar PDFs para evitar interferencias.
* Consume eventos de la cola para actualizar métricas, logs y estado.
* Permite seleccionar Excel, carpeta de descargas, configurar URL SATQ y ejecutar la auditoría de descargas.

### 5.2 `app/orchestrator.py`
* Coordina el proceso completo.
* Gestiona estados de ejecución, pausar, reanudar y detener.
* Ejecuta validaciones previas y la lógica por fila.
* Usa un callback para decidir timbrado en modo asistido.

### 5.3 `app/scraper.py`
* Inicializa Playwright con Chrome o Edge real.
* Navega al portal SATQ.
* Monitorea cuelgues y errores de servidor de forma proactiva.
* Carga dinámicamente los selectores DOM de SATQ desde la configuración.
* Descarga los PDFs generados.

### 5.4 `app/excel_handler.py`
* Lee hojas `Catalogo_RFC` y `Control_Referencias`.
* Actualiza filas y colorea celdas de referencias según el estado físico del PDF.
* Crea copias de seguridad temporales antes de guardar.

### 5.5 `app/validator.py`
* Valida formato de RFC y pertenencia a la lista blanca autorizada en `settings.json`.
* Valida sintaxis de referencia.
* Detecta duplicados locales en el lote.

### 5.6 `app/pdf_validator.py`
* Escanea la carpeta de descargas.
* Compara cantidad de PDFs físicos contra referencias del Excel y localiza archivos extras.

---

## 6. Limitaciones actuales (QA)

### 6.1 Dependencias técnicas
* Playwright requiere Chrome o Edge instalados en Windows.
* El archivo Excel debe permanecer cerrado durante los guardados y la validación de celdas para evitar bloqueos por permisos.

---

## 7. Recomendaciones de operación para el Product Owner

* Mantener `Modo Autónomo` para lotes grandes cuando los datos sean confiables.
* Usar `Modo Asistido` para pruebas o lotes nuevos.
* Archivar anualmente el log de auditoría `auditoria_timbrado.csv`.

---

## 8. Estado de despliegue

La aplicación se encuentra en estado **Estable de Producción (v1.1.0)**, con todas las características de mitigación, robustez, herramientas de control y configuración dinámica de selectores/RFCs completamente enlazadas al proceso.
