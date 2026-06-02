# 🚀 Optima Capture Bot — Plan Maestro Operativo (MVP v1.1)

## 1. Visión del Producto

### Objetivo Estratégico

Crear una herramienta local que automatice consultas SATQ, timbrado CFDI y descarga de documentos desde un archivo de control.

El producto está diseñado para:
* reducir intervención manual,
* conservar trazabilidad,
* evitar duplicados,
* permitir control de pausas y detenciones seguras.

---

## 2. Estado actual del MVP

### Funcionalidades implementadas
* Carga de Excel configurable.
* Validación de RFC y referencias.
* Detección de duplicados internos en el lote.
* Automatización de navegador con Playwright.
* Consulta de referencias en SATQ.
* Timbrado de CFDI y descarga de PDFs.
* Persistencia de estados en Excel.
* Logs y auditoría en CSV.

### Funcionalidades previstas en desarrollo
* Gestión de errores en UI con efecto real en el flujo.
* Capturas automáticas de evidencia en fallos.
* Login manual real como control de inicio de sesión.
* Exportación integrada de carpetas de lote.

---

## 3. Arquitectura actual

```plaintext
main.py
  └─ inicializa entorno y logging
  └─ carga settings y Excel
  └─ crea cola de eventos
  └─ inicia UI

app/
  ├─ gui.py             # Interface operativa del bot
  ├─ orchestrator.py    # Flujo de procesamiento y coordinación
  ├─ scraper.py         # Interacción con portal SATQ via Playwright
  ├─ excel_handler.py   # Lectura/escritura segura de Excel
  ├─ validator.py       # Validación de RFC, referencia y duplicados
  ├─ settings.py        # Configuración persistente en JSON
  ├─ paths.py           # Rutas de carpetas y directorios de soporte
```

---

## 4. Flujo funcional principal

1. `main.py` crea carpetas y configura logging.
2. Se carga la ruta de Excel desde `settings.json` o `Optima_Capture_Bot.xlsx`.
3. Se crea un hilo de trabajo para mantener la UI responsiva.
4. `BotOrchestrator` carga el catálogo y los registros del Excel.
5. Se ejecuta la validación previa:
   * RFC de la empresa,
   * formato de referencia,
   * duplicados internos.
6. Se abre un navegador visible con perfil persistente.
7. Se procesa cada referencia:
   * busca en SATQ,
   * detecta si está generada,
   * genera CFDI si es necesario,
   * descarga PDFs,
   * actualiza Excel.
8. El estado final de cada fila se escribe en el archivo Excel.

---

## 5. Componentes clave

### 5.1 `app/gui.py`
* Construye la UI con CustomTkinter.
* Envía comandos de usuario al orquestador.
* Consume eventos de la cola para actualizar métricas, logs y estado.
* Permite seleccionar Excel, carpeta de descargas y cambiar la URL SATQ.

### 5.2 `app/orchestrator.py`
* Coordina el proceso completo.
* Gestiona estados de ejecución, pausar, reanudar y detener.
* Ejecuta validaciones previas y la lógica por fila.
* Usa un callback para decidir timbrado en modo asistido.

### 5.3 `app/scraper.py`
* Inicializa Playwright con Chrome o Edge real.
* Navega al portal SATQ.
* Rellena referencias, RFC, razón social y código postal.
* Decide los escenarios: no generada, ya generada, inválida o desconocida.
* Descarga los PDFs generados.

### 5.4 `app/excel_handler.py`
* Lee hojas `Catalogo_RFC` y `Control_Referencias`.
* Actualiza filas de Excel de forma atómica.
* Crea copias de seguridad temporales antes de guardar.

### 5.5 `app/validator.py`
* Valida formato de RFC.
* Valida sintaxis de referencia.
* Detecta duplicados locales en el lote.

### 5.6 `app/settings.py`
* Persiste configuración en `settings.json`.
* Devuelve rutas y modo de operación.

---

## 6. Limitaciones actuales (QA)

### 6.1 Inconsistencias entre UI y flujo real
* El bot muestra controles de gestión de errores avanzados, pero esas acciones no están completamente enlazadas al proceso.
* Los botones `Reintentar Registro`, `Omitir Registro` y `Revisión Manual` no realizan cambios automáticos en Excel.

### 6.2 Funcionalidad de captura de pantalla
* La clase `SatqScraper` define `capturar_pantalla()`.
* Sin embargo, no existe una llamada a esa función en el flujo principal de `procesar_registro()`.

### 6.3 Login manual no utilizado
* El código contiene lógica para esperar login manual.
* En el flujo actual, el orquestador asume que no se requiere autenticación y continúa directamente.

### 6.4 Dependencias técnicas
* Playwright requiere Chrome o Edge instalados en Windows.
* El archivo Excel debe permanecer cerrado durante los guardados.

---

## 7. Principales mejoras recomendadas

1. Vincular las acciones de error de la UI a cambios concretos en el Excel.
2. Activar capturas de pantalla automáticas en cada fallo crítico.
3. Implementar un flujo de login/manual cuando el portal lo demande.
4. Añadir un botón para abrir la carpeta de lote activa directamente desde la UI.
5. Mejorar la documentación de la estructura de Excel con ejemplos de plantilla.

---

## 8. Recomendaciones de operación para el Product Owner

* Mantener `Modo Autónomo` para lotes grandes cuando los datos sean confiables.
* Usar `Modo Asistido` para pruebas o lotes nuevos.
* Revisar `logs/optima_capture_bot.log` antes de ejecutar el bot en producción.
* No editar manualmente los archivos de configuración sin respaldo.

---

## 9. Estado de despliegue

La aplicación está en estado de **MVP funcional**, con el núcleo de automatización operativo y una interfaz usable.
Faltan mejoras de robustez en la gestión de errores y soporte pleno para intervenciones manuales.
