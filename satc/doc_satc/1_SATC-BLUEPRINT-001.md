# SATC-BLUEPRINT-001: Blueprint Empresarial SATC (Sistema de Automatización de Trámites Cancún)
**Categoría:** Arquitectura Empresarial  
**Versión:** 1.0  
**Estado:** Baseline Congelada  
**Metodología:** Business-First Architecture (BFA)  
**Fecha:** 2026

---

## 1. Resumen Ejecutivo

### 1.1 Propósito

**SATC (Sistema de Automatización y Control de Trámites Cancún)** es la plataforma empresarial de gobernanza y automatización encargada de controlar el ciclo de vida completo de los trámites de cada vivienda —en desarrollos tipo **Fraccionamiento** y bajo **Régimen de Condominio (UPEs)**—, desde la detección de la necesidad administrativa/fiscal hasta la obtención de recibos, emisión de facturas CFDI y su debida comprobación contable contra el ERP corporativo.

SATC automatiza y gobierna:
- Inventario y control de trámites por desarrollo, manzana, lote y Unidad de Propiedad Exclusiva (UPE).
- Identificación proactiva de trámites faltantes y prevención de omisiones en etapas de construcción, venta y escrituración.
- Consulta y descarga desasistida de recibos oficiales de Tesorería (`recibo.tesoreriacancun.com`).
- Extracción estructurada y renombrado estandarizado de comprobantes PDF con sellos de integridad SHA-256.
- Facturación electrónica CFDI automática en el portal fiscal (`benitojuarez.expidefactura.com`).
- Conciliación trilateral entre Solicitud/Pago, Recibo Oficial, Factura SAT y Órdenes de Compra del ERP.

### 1.2 Problema que Resuelve

La operación inmobiliaria y fiscal enfrentaba los siguientes cuellos de botella:
1. **Falta de Control Integral por Vivienda:** No existía visibilidad de qué trámites correspondían a cada lote o UPE en un régimen de condominio (ej. desarrollos con cientos de viviendas en un solo macro-lote).
2. **Riesgo Crítico de Omisiones:** Omisiones en la individualización catastral o pago de derechos que retrasaban la escrituración y entrega a clientes.
3. **Desconexión con el ERP:** Pagos municipales y facturas timbradas sin comprobación oportuna contra órdenes de compra o pólizas contables.
4. **Carga Operativa Manual:** Consulta, descarga, extracción y facturación manual folio por folio en portales web municipales.

### 1.3 Objetivo Estratégico

Asegurar que el 100% de las viviendas cuenten con sus trámites controlados, sus evidencias documentales blindadas y sus obligaciones financieras conciliadas, reduciendo en más de un 85% la intervención manual mediante automatización robótica (RPA).

---

## 2. Principios Fundamentales

**PF-001** — La entidad soberana del negocio es la **VIVIENDA / UPE**, vinculada a su desarrollo, manzana, lote o régimen de condominio.

**PF-002** — Todo desarrollo bajo Régimen de Condominio debe declarar su macro-lote (MZ/LT) y su total de Unidades de Propiedad Exclusiva (UPEs) autorizadas.

**PF-003** — El sistema debe prevenir proactivamente omisiones: no se permite avanzar a la fase de escrituración si existen trámites obligatorios incompletos o sin recibo oficial.

**PF-004** — Toda operación crítica, descarga o facturación debe ser auditable y conservar evidencia digital con sellos SHA-256.

**PF-005** — Ningún selector de portal debe estar hardcodeado en el código fuente (`satc_configuracion.localizador_portal`).

**PF-006** — La ruta y convención de renombrado de documentos PDF/XML debe ser configurable y organizada por jerarquía física (`Desarrollo/Manzana/Lote_o_UPE/Tramite`).

**PF-007** — Todo recibo y factura timbrada debe mantener trazabilidad financiera con la Orden de Compra del ERP y su respectiva póliza contable de comprobación.

---

## 3. Arquitectura Conceptual

```
DESARROLLO (Fraccionamiento o Régimen de Condominio)
    │
    ├── Régimen de Condominio (MZ / LT / Total UPEs)
    │        │
    │        ▼
    └── VIVIENDA / UPE (Unidad individual de control)
             │
             ▼
        TRÁMITE DE VIVIENDA (Catálogo y Matriz de Obligaciones)
             │
             ├── [1] Solicitud / Pago / Orden de Compra ERP
             │        │
             │        ▼
             ├── [2] Bot A: Descarga de Recibo Oficial (PDF + SHA256)
             │        │
             │        ▼
             ├── [3] Bot C: Timbrado de Factura CFDI (PDF + XML)
             │        │
             │        ▼
             └── [4] Comprobación Contable y Conciliación ERP (Póliza)
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
| SATC-BLUEPRINT-001 | Arquitectura Empresarial | **Baseline Congelada** |
| SATC-DB-001 | Ingeniería de Datos | **Baseline Congelada** |
| SATC-DEV-001 | Ingeniería de Software | **Baseline Inicial** |
| Desarrollo | — | **Pendiente de Inicio** |
