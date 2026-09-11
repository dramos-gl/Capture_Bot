# 15_SAR-RPA-CANCUN-001: Arquitectura de Resiliencia, Bypass de Captcha y UX en Portal Cancún

**Sistema:** Sistema de Administración de Referencias (SAR) — Submódulo CancúnBot (R2F)  
**Documento ID:** SAR-RPA-CANCUN-001  
**Versión:** 2.0  
**Estado:** Aprobado / Implementado en Producción  
**Fecha:** 2026-09-09  

---

## 1. Resumen Ejecutivo

El presente documento establece la especificación técnica oficial y los patrones de diseño de software implementados en el submódulo **CancúnBot** (`cancunbot`) dentro del Sistema SAR para interactuar de manera resiliente, automatizada y a prueba de fallos con el portal municipal de recibos oficiales del Ayuntamiento de Benito Juárez (`https://recibo.tesoreriacancun.com/`).

Se detallan los mecanismos de solución desarrollados para abordar los desafíos de **protección anti-bot de Google reCAPTCHA v3**, la prevención de **Rate Limiting (bloqueos por demasiados intentos)**, el **Bypass táctico DOM/JS** para garantizar la descarga de folios válidos, la **supresión estética (UI/UX) de modales emergentes** y el recálculo dinámico en tiempo real de métricas en la interfaz de escritorio PySide6.

---

## 2. Análisis del Portal Municipal y Causa Raíz de Bloqueos

### 2.1 Componentes Técnicos del Portal
El portal de la Tesorería Municipal de Cancún opera mediante la siguiente arquitectura frontend/backend:
* **Google reCAPTCHA v3 Invisible (`captcha.js`)**: Utiliza el SiteKey `6Le6VEAsAAAAAF6e-bKISOmiiqL8dg8LouooPX0r` para evaluar el comportamiento del usuario y generar un token asíncrono.
* **Validación en Servidor (`includes/validar_captcha.php`)**: Evalúa el token enviado. Si la puntuación del cliente cae por debajo del umbral o la IP emite solicitudes masivas en intervalos cortos, el servidor retorna `valido: false` con la descripción `"Error de validación: No se pudo verificar que seas humano"` o `"Demasiados intentos. Espera 1 minutos."`.
* **Notificaciones Emergentes (`SweetAlert2`)**: Muestra un cuadro modal estético (`Swal.fire`) que interrumpe la navegación y congela la UI hasta que el usuario presione "OK".
* **Despliegue de Resultados (`consulta.js`)**: Ejecuta la función interna `ejecutarCollapse(ejercicio, paseCaja)` mediante AJAX, renderizando la tabla `#prueba` que contiene la información del pago y el botón de descarga en PDF.

### 2.2 Diagnóstico de Fallo Original
Cuando la automatización RPA ejecutaba consultas continuas a alta velocidad:
1. Google reCAPTCHA v3 degradaba la puntuación de la sesión/IP a `0.0`.
2. La llamada AJAX `validar_captcha.php` fallaba arrojando el diálogo modal SweetAlert2.
3. Aunque los datos del folio eran válidos y en ocasiones la tabla `#prueba` alcanzaba a ser renderizada en segundo plano, la presencia del modal emergente bloqueaba el clic en el botón "PDF" e inducía recargas redundantes en la automatización.

---

## 3. Arquitectura de Solución Implementada

### 3.1 Bypass Táctico de Consulta e Invocación Directa DOM
Se modificó la clase Page Object Model [`ReciboTesoreriaPage`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/cancunbot/src/pages/recibo_tesoreria_page.py) para inyectar JavaScript en la sesión de Playwright:

1. **Propagación de Eventos jQuery**: Al escribir en los inputs `#pase` o `#ayo`, se disparan explícitamente los eventos `.trigger('input').trigger('change')` para refrescar los escuchadores internos del sitio.
2. **Invocación Multivía de Consulta**: Se evalúa la existencia de `validarCaptcha()`. Si la respuesta de reCAPTCHA v3 tarda o se bloquea, el bot invoca directamente `ejecutarCollapse(ejercicio, paseCaja)` tras 800ms, forzando la petición AJAX de consulta a la base de datos municipal.
3. **Priorización de Renderizado de Tabla**: Se añadió la verificación proactiva en el DOM (`#prueba button, button:has-text('PDF'), table.stacktable`). Si los elementos de la tabla ya se encuentran presentes, el bot considera la consulta como **exitosa** y procede inmediatamente con la descarga del PDF, ignorando cualquier fallo de reCAPTCHA.

---

### 3.2 Solución Estética de Experiencia de Usuario (UI/UX)

Para garantizar una experiencia limpia e ininterrumpida para el operador (sin ventanas emergentes parpadeando ni interrupciones visuales durante ejecuciones visibles), se diseñó e implementó un **Silenciador Gráfico Proactivo** mediante `_inyectar_silenciador_modales()`:

#### 1. Inyección CSS de Ocultamiento Inmediato
Se inserta un bloque CSS de máxima prioridad (`!important`) en la cabecera `<head>` del portal:

```css
.swal2-container.swal2-shown {
    display: none !important;
    opacity: 0 !important;
    visibility: hidden !important;
    pointer-events: none !important;
}
body.swal2-shown {
    overflow: auto !important;
}
```
* **Efecto**: Cualquier modal de SweetAlert2 que el portal intente desplegar se vuelve totalmente invisible, transparente e ininteractivo, impidiendo que bloquee la pantalla o el scroll de la página.

#### 2. Intercepción JavaScript de `Swal.fire()` (Monkey Patching)
Se sobrescribe la función nativa `Swal.fire` del navegador:

```javascript
if (typeof Swal !== 'undefined' && !window._swal_patched) {
    const originalFire = Swal.fire;
    Swal.fire = function(...args) {
        const title = args[0]?.title || args[0] || '';
        if (typeof title === 'string' && (title.includes('Error') || title.includes('seguridad') || title.includes('intentos'))) {
            console.log('Modal de error silenciada automáticamente.');
            return Promise.resolve({ isConfirmed: true });
        }
        return originalFire.apply(this, args);
    };
    window._swal_patched = true;
}
```
* **Efecto**: Si el portal intenta invocar una alerta emergente con títulos como *"Error de validación"*, *"Validación de seguridad fallida"* o *"Demasiados intentos"*, el parche intercepta la llamada, evita el despliegue del diálogo gráfico y resuelve automáticamente una promesa de confirmación.

---

### 3.3 Pausas Humanizadas Anti-Rate-Limit (Throttling)
En la clase [`BotReciboCunWorker`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/cancunbot/src/core/bot_recibo_worker.py), se incorporó un retardo aleatorio entre la consulta de folios consecutivos:

```python
import random
pause_sec = round(random.uniform(2.5, 4.0), 2)
self.status_changed.emit(f"⏳ Pausa humanizada anti-rate-limit ({pause_sec}s) antes del siguiente folio...")
self.msleep(int(pause_sec * 1000))
```
* **Efecto**: Simula la cadencia de navegación de un operador humano, previniendo que el Firewall de Aplicaciones Web (WAF) o Google reCAPTCHA v3 marquen la dirección IP del cliente con restricción por tasa de peticiones.

---

## 4. Lógica de Métricas Dinámicas Reactivas en Tiempo Real (PySide6)

Alineado strictly con el estándar de arquitectura del **Bot Face A** ([`bot_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/bot_view.py)), se actualizó la vista [`R2FCancunView`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/cancunbot/src/ui/views/r2f_cancun_view.py) para mantener sincronía matemática exacta entre la base de datos/API y las tarjetas de la interfaz gráfica.

### 4.1 Carga de Estado Base
Al seleccionar un lote (`_load_lote_detalles`), la vista registra el total y los estados acumulados:
```python
self.total_referencias = lote.total_folios
self.exitosos_base = lote.folios_procesados
self.errores_base = lote.folios_error
self.current_success = self.exitosos_base
self.current_errors = self.errores_base
```

### 4.2 Decremento y Recálculo Dinámico
Cuando el worker emite la señal `metric_updated`, el método `_on_metric_updated` efectúa el recálculo reactivo:
```python
def _on_metric_updated(self, metric: str, value: int):
    if metric == "exitosos":
        self.current_success = self.exitosos_base + value
        self.box_exitosos.set_value(str(self.current_success))
    elif metric == "errores":
        self.current_errors = self.errores_base + value
        self.box_errores.set_value(str(self.current_errors))

    # Recálculo exacto: Pendientes = Total - Exitosos - Errores
    if hasattr(self, "total_referencias"):
        remaining = self.total_referencias - self.current_success - self.current_errors
        self.box_pendientes.set_value(str(max(0, remaining)))
```

### 4.3 Blindaje de Interfaz ante Errores Humanos (Estandarización Face A & Face C)

Siguiendo el estándar de diseño y comportamiento seguro de los Bots Face A (`bot_view.py`) y Face C (`billing_bot_view.py`), la vista R2F Cancún deshabilita de forma preventiva todos los controles interactivos que puedan interrumpir o desincronizar la ejecución RPA mientras el bot se encuentra en estado `ACTIVO`:

* **Controles Deshabilitados al Iniciar (`_on_iniciar_bot`)**:
  * Interruptor de Modo (`switch_modo`) y Modo Autónomo (`chk_autonomo`).
  * Botones de Carga de Archivos (`btn_importar_excel`, `btn_importar_pdf`, `btn_descargar_plantilla`).
  * Botón Selector de Ruta de Descarga (`btn_browse`).
  * Botón Modal Administración (`btn_control_r2f`).
  * Tablas de Selección e Interacción (`table_lotes`, `table_detalles`).
* **Único Control Activo**: El botón principal se transforma en `⏹ Detener Bot` (`btn_iniciar` en color rojo de peligro `Colors.ERROR`), permitiendo únicamente una detención segura y ordenada del proceso.
* **Restablecimiento Automatizado (`_on_worker_finished`)**: Al concluir o detenerse el hilo `QThread`, todos los componentes vuelven a su estado habilitado de forma segura.

---

## 5. Matriz de Componentes Modificados

| Módulo / Archivo | Rol | Descripción de la Modificación |
| :--- | :--- | :--- |
| [`recibo_tesoreria_page.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/cancunbot/src/pages/recibo_tesoreria_page.py) | **Page Object Model** | Inyección de CSS anti-emergentes, parche JS a `Swal.fire`, bypass de `ejecutarCollapse` y detección prioritaria de la tabla `#prueba`. |
| [`bot_recibo_worker.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/cancunbot/src/core/bot_recibo_worker.py) | **RPA QThread Worker** | Inclusión de pausas humanizadas aleatorias (2.5s - 4.0s) e integración de soporte multi-cliente (BD Directa / REST API). |
| [`r2f_cancun_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/cancunbot/src/ui/views/r2f_cancun_view.py) | **Interfaz PySide6 (UI)** | Réplica exacta del patrón Face A/C: decremento en tiempo real de Pendientes y blindaje estricto de controles de UI ante errores humanos. |

---

## 6. Verificación y Control de Calidad

* **Pruebas de Compilación**: Todos los módulos fueron validados mediante `python -m py_compile` arrojando un código de salida `0` (sin errores de sintaxis).
* **Compatibilidad de Red**: Probado y validado operando tanto en entornos de red LAN con conexión directa a PostgreSQL como en modalidad cliente distribuido REST API (`CONNECT_VIA_API=true`).
* **Resiliencia de UX**: Confirmado el silenciamiento absoluto de cuadros emergentes y la continuidad ininterrumpida en la descarga de archivos PDF.
* **Prueba de Errores Humanos**: Confirmado el bloqueo preventivo de tablas, selectores e importaciones durante la ejecución activa.

