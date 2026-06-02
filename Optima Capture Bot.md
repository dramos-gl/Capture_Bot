# 🚀 Optima Capture Bot — Plan Maestro Operativo (MVP v1.1)

## 📌 Visión del Producto

### Objetivo Estratégico

Desarrollar una plataforma local de automatización operativa capaz de:

* capturar referencias,
* consultar información en SATQ,
* descargar facturas automáticamente,
* organizar archivos por lotes,
* mantener trazabilidad total,
* recuperar procesos interrumpidos,
* y ofrecer monitoreo visual en tiempo real mediante una interfaz gráfica moderna.

---

# 🎯 Objetivo del MVP

El MVP NO busca:

* escalamiento masivo,
* multiusuario,
* procesamiento distribuido,
* arquitectura enterprise.

El MVP busca:

> Automatización estable, auditable y controlada para un único operador local.

---

# 🧠 Principios del Producto

## 1. Resiliencia Operativa

El sistema debe poder:

* recuperarse de errores,
* continuar tras apagones,
* evitar duplicados,
* registrar evidencia.

---

## 2. Observabilidad Total

El operador nunca debe quedarse “a ciegas”.

El sistema mostrará:

* avance,
* estado actual,
* logs,
* errores,
* screenshots,
* métricas básicas.

---

## 3. Control Humano

El operador conserva control operativo:

* pausar,
* reanudar,
* detener,
* revisar errores.

---

## 4. Arquitectura Evolutiva

Aunque el MVP será local:

* la arquitectura se diseñará preparada para crecer.

---

# 🏗️ Arquitectura General MVP

```plaintext
┌──────────────────────────────┐
│      CustomTkinter UI        │
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│      Orquestador Bot         │
└──────────────┬───────────────┘
               │
     ┌─────────┴─────────┐
     │                   │
┌────▼─────┐      ┌──────▼──────┐
│ Validator│      │ Playwright  │
└────┬─────┘      └──────┬──────┘
     │                   │
┌────▼─────────┐  ┌──────▼──────┐
│ SQLite/Excel │  │ Descargador │
└────┬─────────┘  └──────┬──────┘
     │                   │
┌────▼───────────────────▼──────┐
│ Logs + Screenshots + Auditoría│
└───────────────────────────────┘
```

---

# 🖥️ Interfaz Gráfica (CustomTkinter)

## Objetivo de la UI

La interfaz NO será decorativa.

Su propósito será:

* control operativo,
* monitoreo,
* diagnóstico,
* confianza operacional.

---

# 🎛️ Componentes Principales UI

---

## 1. Panel Estado General

### Mostrará:

* Estado sistema
* SATQ conectado/desconectado
* Sesión activa
* Operador actual
* Tiempo ejecución

### Ejemplo:

```plaintext
Estado Sistema: EN EJECUCIÓN
Sesión SATQ: ACTIVA
Tiempo Total: 00:21:33
```

---

## 2. Panel Métricas Operativas

### KPIs visibles:

| Métrica     | Descripción            |
| ----------- | ---------------------- |
| Pendientes  | Registros sin procesar |
| Procesados  | Total completados      |
| Exitosos    | Descargas correctas    |
| Errores     | Registros fallidos     |
| Reintentos  | Intentos automáticos   |
| Lote Actual | Carpeta activa         |

---

## 3. Panel Registro Actual

### Información:

* referencia actual,
* RFC,
* estado,
* tiempo individual,
* acción actual.

### Ejemplo:

```plaintext
Referencia: REF-000245
RFC: XAXX010101000
Estado: EN_PROCESO
Acción: Descargando PDF
```

---

## 4. Consola Log Tiempo Real

## Objetivo

Mostrar trazabilidad operativa viva.

### Ejemplo:

```plaintext
[10:31:02] Sistema iniciado
[10:31:05] SATQ disponible
[10:31:08] Procesando REF-000245
[10:31:15] Factura localizada
[10:31:18] PDF descargado
[10:31:19] Estado EXITOSO
```

---

# ⚠️ Gestión Visual de Errores

## Reglas

Los errores:

* NO se ocultan,
* NO se silencian,
* NO se resumen ambiguamente.

---

## Ejemplo:

```plaintext
ERROR_VALIDACION
Referencia: REF-000381
Motivo: RFC inválido
```

---

## Funcionalidades:

* abrir screenshot,
* abrir log detallado,
* reintentar registro,
* marcar revisión manual.

---

# 🧩 Controles Operativos

| Acción             | Obligatorio |
| ------------------ | ----------- |
| Iniciar            | Sí          |
| Pausar             | Sí          |
| Reanudar           | Sí          |
| Detener seguro     | Sí          |
| Reintentar errores | Sí          |
| Abrir carpeta lote | Sí          |
| Exportar logs      | Sí          |

---

# 🛡️ Máquina de Estados Oficial

| Estado             | Descripción         |
| ------------------ | ------------------- |
| PENDIENTE          | Sin procesar        |
| VALIDADO           | Validación correcta |
| EN_PROCESO         | Ejecutándose        |
| EXITOSO            | Descarga correcta   |
| ERROR_REINTENTABLE | Timeout/red         |
| ERROR_VALIDACION   | Datos inválidos     |
| ERROR_PORTAL       | Fallo SATQ          |
| DUPLICADO          | Ya existente        |
| REQUIERE_REVISION  | Ambiguo/manual      |
| OMITIDO            | Ignorado            |

---

# 🔎 Módulo Validación Previa

## Objetivo

Evitar automatizar datos defectuosos.

---

## Validaciones Obligatorias

| Validación           | Prioridad |
| -------------------- | --------- |
| RFC válido           | Alta      |
| Referencia vacía     | Alta      |
| Longitud referencia  | Alta      |
| Caracteres inválidos | Alta      |
| Duplicados internos  | Alta      |
| CP válido            | Media     |

---

# 🧠 Sistema Anti-Duplicados

## Estrategia

Generar hash:

```plaintext
RFC + REFERENCIA + FECHA
```

---

## Validaciones:

* antes procesamiento,
* antes descarga,
* antes escritura.

---

# 📂 Estructura Directorios

```plaintext
Optima_Capture_Bot/
│
├── app/
├── data/
├── logs/
├── screenshots/
├── downloads/
│    ├── Lote_1/
│    ├── Lote_2/
│
├── config/
├── exports/
└── temp/
```

---

# 📸 Evidencia Automática

## Capturas automáticas:

| Evento           | Screenshot |
| ---------------- | ---------- |
| Error SATQ       | Sí         |
| Timeout          | Sí         |
| Error descarga   | Sí         |
| Error validación | Sí         |

---

# 🧾 Sistema Logs

## Formato:

```plaintext
[Timestamp] [Nivel] [Referencia] Mensaje
```

## Ejemplo:

```plaintext
[10:31:18] [INFO] [REF-000245] PDF descargado
```

---

# 🧱 Persistencia de Datos

# MVP Inicial

## Recomendación:

SQLite + exportación Excel.

---

# Razón

Excel:

* NO es transaccional,
* puede corromperse,
* tiene locking deficiente.

SQLite:

* ligero,
* local,
* estable,
* idempotente.

---

# 📦 Gestión de Lotes

## Regla Operativa

Máximo:

* 50 registros por lote.

---

## Resultado:

```plaintext
downloads/
 ├── Lote_1/
 ├── Lote_2/
 ├── Lote_3/
```

---

# 🔄 Recuperación Automática

## Objetivo

Recuperar operación tras:

* apagón,
* cierre,
* error red,
* crash.

---

## Estrategia

Al iniciar:

* ignorar EXITOSOS,
* reanudar PENDIENTES,
* detectar EN_PROCESO interrumpidos.

---

# 🌐 Motor Automatización

## Tecnología:

### Python + Playwright

---

# Estrategias:

| Función    | Estrategia   |
| ---------- | ------------ |
| Login      | Humano       |
| Captcha    | Humano       |
| Navegación | Automatizada |
| Delays     | Aleatorios   |
| Selectores | Robustos     |
| Reintentos | Inteligentes |

---

# ⚙️ Estrategia Anti-Bloqueo

## Implementar:

* delays aleatorios,
* navegación humana parcial,
* perfiles persistentes,
* viewport dinámico.

---

# 📈 KPIs MVP

| KPI                 | Objetivo |
| ------------------- | -------- |
| Éxito automático    | >95%     |
| Tiempo promedio     | <20s     |
| Recuperación fallos | 100%     |
| Duplicados          | 0        |
| Errores críticos    | <2%      |

---

# 📅 Roadmap Oficial

# Sprint 1 — Base Operativa

## Objetivo

Infraestructura mínima estable.

### Entregables

* estructura carpetas,
* SQLite,
* UI base,
* logs,
* validaciones.

---

# Sprint 2 — Automatización SATQ

## Entregables

* Playwright,
* login manual,
* navegación,
* procesamiento secuencial.

---

# Sprint 3 — Descargas y Lotes

## Entregables

* PDFs,
* batching,
* screenshots,
* control errores.

---

# Sprint 4 — Resiliencia

## Entregables

* recuperación automática,
* chaos testing,
* métricas,
* estabilización.

---

# 🚫 Fuera del Alcance MVP

## NO incluir inicialmente:

* multiusuario,
* PostgreSQL,
* cloud,
* OCR,
* IA,
* dashboards ejecutivos,
* paralelismo masivo.

---

# ✅ Criterios Go-Live

El sistema se considerará listo cuando:

* procese lotes completos sin duplicados,
* recupere interrupciones,
* mantenga logs auditables,
* genere lotes correctamente,
* muestre trazabilidad completa en UI.

---

# 🎯 Conclusión Estratégica

El éxito del proyecto NO dependerá únicamente de Playwright.

Dependerá de:

* resiliencia,
* observabilidad,
* control operativo,
* y confianza del operador.

El MVP debe priorizar:

> estabilidad operativa antes que sofisticación tecnológica.
