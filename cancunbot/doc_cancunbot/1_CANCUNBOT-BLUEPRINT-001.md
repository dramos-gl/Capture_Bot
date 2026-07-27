# CANCUNBOT-BLUEPRINT-001: Blueprint Empresarial CancunBot
**Categoría:** Arquitectura Empresarial  
**Versión:** 1.0  
**Estado:** Baseline Congelada  
**Metodología:** Business-First Architecture (BFA)  
**Fecha:** 2026

---

## 1. Resumen Ejecutivo

### 1.1 Propósito

**CancunBot** es un sistema de automatización interno diseñado para eliminar el trabajo manual en el proceso de descarga de recibos electrónicos de la Tesorería Municipal de Cancún y la posterior generación de facturas electrónicas (CFDI).

CancunBot automatiza:
- Consulta de recibos por folio electrónico o folio pase de caja en `recibo.tesoreriacancun.com`.
- Descarga, renombrado y organización de archivos PDF de recibos.
- Extracción de datos estructurados del PDF hacia la base de datos.
- Facturación electrónica automática en `benitojuarez.expidefactura.com`.

### 1.2 Problema Actual

El proceso requiere actualmente:
1. Recolectar folios impresos en recibos físicos.
2. Acceder manualmente al portal de Tesorería Cancún.
3. Capturar el folio uno por uno.
4. Descargar el PDF de cada recibo.
5. Renombrar y organizar los archivos manualmente.
6. Capturar datos del recibo en hojas de cálculo.
7. Acceder al portal de facturación con los datos capturados.
8. Generar cada factura manualmente.

Lo anterior genera:
- Alto tiempo operativo.
- Errores humanos en captura.
- Falta de trazabilidad.
- Dependencia de personal operativo.

### 1.3 Objetivo Estratégico

Automatizar completamente el ciclo: **Folio Recibo → PDF Descargado → Datos Capturados → Factura Generada**.

---

## 2. Principios Fundamentales

**PF-001** — El folio electrónico es la entidad de ingreso del sistema.

**PF-002** — El recibo es la entidad principal de negocio.

**PF-003** — Toda operación debe ser auditable.

**PF-004** — Ningún selector de portal debe estar hardcodeado en el código fuente. Todos viven en la base de datos (`localizador_portal`).

**PF-005** — La ruta y convención de renombrado de PDFs debe ser configurable, no hardcodeada.

**PF-006** — El correo electrónico del contribuyente vive en el catálogo de contribuyentes, asociado a su RFC.

**PF-007** — Una solicitud agrupa N folios. Puede originarse desde importación Excel o captura manual.

---

## 3. Arquitectura Conceptual

```
SOLICITUD
(lote de folios: Excel o Manual)
    │
    ▼
FOLIO
(unidad de trabajo de los Bots)
    │
    ▼
RECIBO
(datos extraídos del PDF descargado)
    │
    ▼
FACTURA
(CFDI generado en portal de facturación)
```

---

## 4. Dominio de Negocio

### Solicitud
Agrupa un conjunto de folios a procesar.  
Puede originarse de:
- **Importación Excel**: El operador importa una hoja de cálculo con N folios.
- **Captura manual**: El operador teclea uno o más folios directamente en la UI.

Cada importación/captura crea una `solicitud` registrada en la base de datos.

### Folio
Unidad de trabajo individual asignada a los Bots.  
Contiene el folio electrónico o folio pase de caja a consultar.

### Recibo
Datos estructurados extraídos del PDF de recibo descargado.  
Campos capturados:
- Folio Pase de Caja
- Fecha de Expedición
- Lugar de Expedición
- Hora de Expedición
- RFC
- Contribución
- Nombre del Contribuyente
- Folio Electrónico
- Detalle Concepto de Cobro
- Concepto
- Total
- Forma de Pago *(opcional)*

### Contribuyente
Catálogo de contribuyentes registrados.  
Almacena el correo electrónico asociado al RFC para su uso en facturación.

### Factura
Comprobante fiscal digital (CFDI) generado a partir de un recibo.  
Requiere: RFC, correo electrónico, folio electrónico e importe.

---

## 5. Flujo Operativo Oficial

```
[INGESTA DE FOLIOS]
  ├── Importación Excel → Solicitud (N folios)
  └── Captura Manual → Solicitud (1..N folios)
         │
         ▼
[BOT A: DESCARGA DE RECIBOS]
  Por cada folio en estado PENDIENTE:
  ├── Consulta portal recibo.tesoreriacancun.com
  ├── Descarga PDF
  ├── Renombra y organiza archivo
  ├── Extrae datos del PDF
  └── Guarda en BD (tabla recibo)
         │
         ▼
[REVISIÓN / APROBACIÓN] *(opcional)*
         │
         ▼
[BOT C: FACTURACIÓN]
  Por cada recibo en estado PENDIENTE_FACTURAR:
  ├── Lee RFC, correo (catálogo), folio e importe
  ├── Accede a benitojuarez.expidefactura.com
  ├── Llena formulario y timbra
  ├── Descarga factura PDF/XML
  └── Actualiza estado → FACTURADO
```

---

## 6. Ciclo de Vida de un Folio

```
PENDIENTE
    ↓
DESCARGANDO
    ↓
DESCARGADO ──────────────────────────────→ ERROR_DESCARGA
    ↓
(datos extraídos → recibo creado)
```

## Ciclo de Vida de un Recibo

```
CAPTURADO
    ↓
PENDIENTE_FACTURAR
    ↓
FACTURANDO
    ↓
FACTURADO ───────────────────────────────→ ERROR_FACTURA
```

---

## 7. Reglas de Negocio

**RN-001** — Un folio electrónico es único. No puede procesarse dos veces.

**RN-002** — Un folio pase de caja puede complementar a un folio electrónico.

**RN-003** — Una solicitud puede contener de 1 a N folios.

**RN-004** — El correo electrónico para facturación se obtiene del catálogo de contribuyentes mediante el RFC del recibo.

**RN-005** — Si un folio no se encuentra en el portal, se registra como `ERROR_DESCARGA` y continúa con el siguiente.

**RN-006** — Si la facturación falla, el recibo queda en `ERROR_FACTURA` y puede reintentarse.

**RN-007** — El importe para facturación se toma del campo `total` extraído del PDF del recibo.

**RN-008** — Todo selector de portal es configurable desde la tabla `localizador_portal`. El código nunca contiene selectores CSS/XPath hardcodeados.

**RN-009** — La estructura de carpetas y convención de renombrado de PDFs es configurable mediante parámetros de sistema.

---

## 8. KPIs del Sistema

- Folios procesados por día.
- Tasa de éxito de descarga de recibos.
- Tasa de éxito de facturación.
- Tiempo promedio por folio.
- Errores por portal.

---

## 9. Estado del Proyecto

| Documento | Categoría | Estado |
| :--- | :--- | :--- |
| CANCUNBOT-BLUEPRINT-001 | Arquitectura Empresarial | **Baseline Congelada** |
| CANCUNBOT-DB-001 | Ingeniería de Datos | **Baseline Congelada** |
| CANCUNBOT-DEV-001 | Ingeniería de Software | **Baseline Inicial** |
| Desarrollo | — | **Pendiente de Inicio** |
