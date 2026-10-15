# SATC-CICLO-VIDA-001: Ciclo de Vida de Trámites por Vivienda, Fraccionamientos y Regímenes de Condominio

**Categoría:** Arquitectura Empresarial & Gobernanza de Negocio  
**Versión:** 1.0  
**Ecosistema:** Proyecto_CapturaBot  
**Subsistema:** SATC (Sistema de Automatización y Control de Trámites Cancún)  
**Fecha:** 2026  
**Metodología:** Business-First Architecture (BFA)  

---

## 1. Propósito y Alcance

Este documento establece el marco normativo, conceptual y funcional para la **administración del ciclo de vida de los trámites de vivienda**, desde la detección de la necesidad hasta la comprobación final de pagos y facturación en el ERP corporativo.

El objetivo central es erradicar omisiones operativas, garantizar la trazabilidad física-jurídica-financiera y automatizar las tareas repetitivas considerando las diferencias operativas entre:
1. **Fraccionamientos** (Lotes individuales tradicionales).
2. **Regímenes de Condominio** (Macro-lotes con Unidades de Propiedad Exclusiva - UPEs).

---

## 2. Modelos de Proyecto y Estructura Territorial

La estructura espacial y catastral del SATC opera bajo una jerarquía territorial unificada de 6 niveles:
$$\text{Desarrollo} \longrightarrow \text{SM (Supermanzana)} \longrightarrow \text{MZ (Manzana)} \longrightarrow \text{Lote} \longrightarrow \text{Edificio} \longrightarrow \text{Vivienda / UPE}$$

### 2.1 Fraccionamiento (Modelo Lote a Lote Horizontal)
En un desarrollo de tipo Fraccionamiento:
* **Relación:** `1 Lote = 1 Vivienda` (`edificio` permanece NULL).
* **Identificación:** `Desarrollo + SM + MZ + Lote + Vivienda (Casa)`.
* **Dinámica de Trámites:** Cada lote se gestiona y apertura de forma individualizada para trámites de alineamiento, número oficial, cédula catastral, predial individual y permisos de construcción/terminación.

### 2.2 Régimen de Condominio (Modelo Macro-Lote + UPEs Vertical o Mixto)
En un desarrollo constituido bajo Régimen de Condominio:
* **Relación:** `1 Macro-Lote (SM, MZ, Lote) = N UPEs (Unidades de Propiedad Exclusiva / Viviendas)`.
* **Subdivisión Espacial:** Las UPEs pueden agruparse en **Edificios o Torres** (`edificio`) conteniendo múltiples departamentos o interiores (`vivienda`).
* **Ejemplo Operativo:**
  * **Desarrollo:** `AURA NOVA PLAYA`
  * **Ubicación Fiduciaria:** `SM 10, MZ 1, LT 1`
  * **UPEs Declaradas / Solicitadas:** `577 UPEs`
  * **Distribución:** 577 viviendas distribuidas en Edificios/Torres o clusters (ej. *Torre A - Depto 101* = UPE-001).
* **Nivel de Granularidad de los Trámites:**
  1. **Nivel Régimen (Macro-Trámite):** 
     * Licencia de Construcción Matriz del Régimen.
     * Constitución y Autorización del Régimen en Condominio.
     * Dictámenes Generales de Protección Civil y Servicios Urbanos.
  2. **Nivel Vivienda / UPE (Micro-Trámite Individualizado):**
     * Solicitud de Individualización Catastral por UPE.
     * Asignación de Clave Catastral y Padrón Municipal individual (577 registros).
     * Recibo de Derechos Catastrales por UPE.
     * Cédula Catastral Individual.
     * Certificado de No Adeudo Municipal para Venta / Escrituración.

---

## 3. Matriz de Eventos del Ciclo de Vida de la Vivienda

El ciclo de vida de cada vivienda (o UPE) está ligado a tres grandes hitos de negocio:

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ 1. CONSTRUCCIÓN │  ───> │    2. VENTA     │  ───> │ 3. ESCRITURACIÓN│
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                         │
         ▼                         ▼                         ▼
  • Alineamiento/Número     • Individualización       • No Adeudo Predial
  • Licencia Construcción   • Clave Catastral UPE     • No Adeudo Servicios
  • Terminación de Obra     • Alta Padrón Municipal   • Finiquito Municipal
```

### 3.1 Etapa de Construcción / Urbanización
* **Disparador:** Alta del paquete o inicio de edificación de manzana/régimen.
* **Trámites Clave:** Constancia de Uso de Suelo, Número Oficial, Derechos de Aportación, Terminación de Obra.
* **Control SATC:** Validación de que ningún lote/UPE inicie venta sin contar con la terminación de obra o prórroga de licencia respectiva.

### 3.2 Etapa de Venta (Comercialización)
* **Disparador:** Asignación comercial de la vivienda a un cliente.
* **Trámites Clave:** Asignación definitiva de Clave Catastral de la UPE, Alta en Padrón de Impuesto Predial del Municipio de Benito Juárez (Cancún).
* **Control SATC:** Verificación de que las 577 UPEs cuenten con su clave catastral homologada antes de integrar el expediente notarial.

### 3.3 Etapa de Escrituración y Entrega
* **Disparador:** Firma de contrato de compraventa y llamado a Notaría.
* **Trámites Clave:** Certificado de No Adeudo Predial, Impuesto Sobre Adquisición de Bienes Inmuebles (ISABI), Constancia de No Adeudo de Agua/Drenaje, Verificación de Finiquito de Derechos.
* **Control SATC:** Auditoría documental estricta. Ninguna vivienda pasa a "Escriturada" si presenta adeudos fiscales o trámites en estado pendiente.

### 3.4 Obligaciones Post-Venta
* **Obligaciones Remanentes:**
  * Notificación de traslado de dominio al contribuyente final.
  * Finiquito de garantías fiduciarias y cancelación de gravámenes del régimen matriz.
  * Cierre y resguardo de expediente digital con sellos SHA-256.

---

## 4. Cadena de Control Financiero y Documental

Cada trámite debe mantener una conciliación trilateral obligatoria:

```
┌────────────────────────────────────────────────────────┐
│                   TRÁMITE DE VIVIENDA                  │
└───────────────────────────┬────────────────────────────┘
                            │
       ┌────────────────────┼────────────────────┐
       ▼                    ▼                    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  PAGO / OC   │     │    RECIBO    │     │   FACTURA    │
│  (ERP Cadena)│     │  (Tesorería) │     │ (CFDI SAT)   │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────────────┴────────────────────┘
                            │
                            ▼
              CONCILIACIÓN Y COMPROBACIÓN ERP
---

## 4. Máquina de Estados: Vivienda y Trámite Individual

Para gobernar el flujo sin ambigüedad operativa ni vacíos de control, el sistema opera con dos dimensiones de estados fuertemente acopladas mediante reglas de transición:

### 4.1 Estados de la Vivienda / UPE (`satc_catalogo.vivienda`)

Representa la situación física, comercial y jurídica de la unidad privativa:

```
┌─────────────────┐       ┌───────────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ EN_CONSTRUCCION │  ───> │ EN_INDIVIDUALIZACION  │  ───> │ LISTA_PARA_VENTA│  ───> │ EN_ESCRITURACION│
└─────────────────┘       └───────────────────────┘       └─────────────────┘       └────────┬────────┘
                                                                                             │
                                                                                             ▼
                                                                                    ┌─────────────────┐
                                                                                    │   ESCRITURADA   │
                                                                                    └─────────────────┘
```

| Código de Estado | Nombre Legible | Descripción y Regla de Negocio | Candado de Transición |
| :--- | :--- | :--- | :--- |
| `PROYECTADA` | Proyectada / En Plano | UPE dada de alta en el régimen (ej. UPE-001 de 577). Aún no inicia obra. | Licencia de construcción matriz autorizada. |
| `EN_CONSTRUCCION` | En Construcción | Edificación activa de la manzana o torre. | Trámites de urbanización y terminación de obra concluidos. |
| `EN_INDIVIDUALIZACION` | En Individualización | Gestión catastral para segregar la UPE del macro-lote base. | Generación de Clave Catastral y Padrón Municipal individual. |
| `LISTA_PARA_VENTA` | Lista para Venta | Cuenta con clave catastral individual y puede asignarse comercialmente. | Apartado o contrato de compraventa firmado. |
| `EN_ESCRITURACION` | En Notaría / Escrituración | Expediente en notaría. **Candado crítico:** no puede escriturarse con adeudos. | Certificados de No Adeudo vigentes, recibo pagado y factura emitida. |
| `ESCRITURADA` | Escriturada | Título de propiedad formalmente protocolizado. | Trámites de traslado de dominio concluidos. |
| `EN_GARANTIA` | En Garantía / Post-Venta | Obligaciones remanentes de finiquito y seguimiento de garantías. | Finiquito de gravámenes del régimen matriz. |
| `CONCLUIDA` | Ciclo Concluido | Vivienda con expediente digital 100% cerrado, auditado y comprobado en ERP. | Cero obligaciones pendientes. |

### 4.2 Estados del Trámite de Vivienda (`satc_produccion.tramite_vivienda`)

Gobierna el estado operativo, documental, automatizado (Bots) y financiero (ERP) de cada obligación:

```
┌──────────────┐     ┌─────────────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│  NO_INICIADO │ ──> │REQUISITOS_PENDIENTES│ ──> │INGRESADO_MUNICIPIO───> │    PAGO_EMITIDO      │
└──────────────┘     └─────────────────────┘     └────────┬─────────┘     └──────────┬───────────┘
                                                          │                          │
                                                          ▼                          ▼
                                                    ┌───────────┐         ┌──────────────────────┐
                                                    │ OBSERVADO │         │RECIBO_DESCARGADO(Bot)│
                                                    └───────────┘         └──────────┬───────────┘
                                                                                     │
                                                                                     ▼
                                                                          ┌──────────────────────┐
                                                                          │  FACTURADO (Bot CFDI)│
                                                                          └──────────┬───────────┘
                                                                                     │
                                                                                     ▼
                                                                          ┌──────────────────────┐
                                                                          │ COMPROBADO_ERP/CONCL.│
                                                                          └──────────────────────┘
```

| Código de Estado | Fase | Descripción y Evidencia | Automatización Asociada |
| :--- | :--- | :--- | :--- |
| `NO_INICIADO` | Preventiva | El trámite corresponde por matriz a la vivienda, pero aún no se dispara el hito. | Semáforo preventivo. |
| `REQUISITOS_PENDIENTES`| Documental | Falta integrar documentación técnica previa (planos, memoria, acuses). | Matriz de faltantes documentales. |
| `INGRESADO_MUNICIPIO` | Operativa | Solicitud formalmente radicada ante Tesorería o Catastro Cancún. | Registro de folio de expediente. |
| `OBSERVADO` | Incidencia | Municipio emite prevención o rechazo técnico. Requiere subsanación. | Notificación al gestor con plazo límite. |
| `ORDEN_COMPRA_ERP` | Financiera | Autorización del gasto y generación de OC en el ERP corporativo. | Registro de `orden_compra_erp`. |
| `PAGO_EMITIDO` | Financiera | Generado el folio de pase de caja o comprobante de pago bancario. | Pasa a cola de procesamiento de bots. |
| `RECIBO_DESCARGADO` | Automatizada | **Bot A** descargó el PDF oficial, extrajo datos y selló con SHA-256. | Dispara inmediatamente la tarea para Bot C. |
| `FACTURADO` | Automatizada | **Bot C** timbró el CFDI (PDF y XML) en *ExpideFactura*. | Listo para comprobación contable. |
| `COMPROBADO_ERP` | Contable | Póliza de egreso comprobada en ERP con XML y PDF vinculados. | Cierre financiero del trámite. |
| `CONCLUIDO` | Cierre | Documento oficial final resguardado (ej. Cédula catastral definitiva). | Marca el trámite como 100% cumplido para la vivienda. |

---

## 5. Arquitectura de Coexistencia y Cadena de Control Financiero

### 5.1 Jerarquía Operativa de Doble Vía (Strangler Fig Pattern)
Para garantizar **cero interrupción** del sistema en producción mientras se evoluciona al control por vivienda, el sistema implementa dos vías paralelas:

```
┌────────────────────────────────────────────────────────┐     ┌────────────────────────────────────────────────────────┐
│            VÍA A: OPERACIÓN ACTUAL (R2F)               │     │        VÍA B: GOBERNANZA INTEGRAL (NUEVO FLUJO)        │
│            (Operación reactiva por folios)             │     │      (Control de ciclo de vida por vivienda / UPE)     │
└───────────────────────────┬────────────────────────────┘     └───────────────────────────┬────────────────────────────┘
                            │                                                              │
                            ▼                                                              ▼
                   satc_produccion.                                               satc_produccion.
                     orden_cancun                                                   orden_tramite
                            │                                                              │
                            ▼                                                              ▼
                   satc_produccion.                                               satc_produccion.
                      lote_folio                                                 solicitud_tramite
                            │                                                              │
                            ▼                                                              ▼
                   satc_produccion.                                               satc_produccion.
                     folio_cancun                                                 tramite_vivienda
                            │                                                              │
                            └───────────────────────────────┬──────────────────────────────┘
                                                            │
                                                            ▼
                                                   satc_produccion.recibo_cancun (Bot A)
                                                            │
                                                            ▼
                                                   satc_produccion.factura_cancun (Bot C)
```

* **Vía A (Operativa R2F):** `orden_cancun` ──> `lote_folio` ──> `folio_cancun`. Permite a los operadores procesar lotes rápidos en Excel sin vincular previamente la vivienda.
* **Vía B (Gobernanza Ciclo de Vida):** `orden_tramite` ──> `solicitud_tramite` ──> `tramite_vivienda`. Permite gobernar los macro-proyectos, radicar paquetes ante Catastro/Tesorería y controlar el semáforo de escrituración por vivienda/UPE.
* **Convergencia:** Ambos flujos reutilizan el mismo motor de automatización: **Bot A** (descarga y lectura de recibos) y **Bot C** (timbrado CFDI).

### 5.2 Cadena de Conciliación Trilateral ERP

Cada trámite de vivienda mantiene una conciliación trilateral obligatoria:

```
┌────────────────────────────────────────────────────────┐
│                   TRÁMITE DE VIVIENDA                  │
└───────────────────────────┬────────────────────────────┘
                            │
       ┌────────────────────┼────────────────────┐
       ▼                    ▼                    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  PAGO / OC   │     │    RECIBO    │     │   FACTURA    │
│  (ERP Cadena)│     │  (Tesorería) │     │ (CFDI SAT)   │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────────────┴────────────────────┘
                            │
                            ▼
              CONCILIACIÓN Y COMPROBACIÓN ERP
              (Póliza Contable / Cierre Financiero)
```

1. **Orden de Compra / Estimación ERP:** Registra el compromiso financiero y el número de orden de compra asignado por el ERP.
2. **Folio de Pase de Caja / Pago Municipal:** Registro del comprobante bancario o folio de caja de la Tesorería.
3. **Recibo Oficial Descargado (Bot A):** Extracción automatizada del PDF oficial (`recibo_cancun`), capturando importe, contribuyente, concepto y clave catastral.
4. **Factura CFDI (Bot C):** Generación automática del CFDI en el portal con descarga de PDF/XML (`factura_cancun`).
5. **Comprobación ERP:** Vinculación de la factura y recibo contra la Orden de Compra original, registrando el número de comprobación/póliza en el ERP para cerrar el ciclo financiero.

---

## 6. Prevención Proactiva de Errores y Omisiones

El sistema SATC implementa las siguientes reglas de control preventivo:

* **CO-001 (Control de Integridad de UPEs):** Si un Régimen declara $N$ UPEs (ej. 577), el sistema no permite el cierre del macro-trámite hasta que existan exactamente 577 registros de UPEs con sus claves catastrales generadas o validadas.
* **CO-002 (Alerta de Factura Huérfana):** Todo recibo oficial descargado que exceda 48 horas sin factura generada emite una alerta roja en el tablero de control.
* **CO-003 (Alerta de Pago no Comprobado en ERP):** Toda factura timbrada que no tenga asociada una Orden de Compra comprobada dentro de los 15 días posteriores a su emisión se clasifica como pasivo fiscal pendiente de comprobación.
* **CO-004 (Bloqueo de Duplicidad):** No se permite ingresar o tramitar dos veces el mismo tipo de trámite para una misma vivienda y ejercicio fiscal, a menos que se trate de un alcance complementario debidamente autorizado.
* **CO-005 (Semáforo de Bloqueo a Escrituración):** El sistema bloquea el expediente notarial de una UPE si falta alguno de los 3 documentos obligatorios: (a) Cédula Catastral, (b) Certificado de No Adeudo, (c) Factura de derechos correspondiente.

---

## 7. Indicadores de Éxito y Tablero de Control (KPIs)

El éxito operativo se mide en tiempo real a través de las siguientes métricas:

| Métrica | Definición | Meta Operativa |
| :--- | :--- | :--- |
| **Índice de Cobertura de UPEs** | $\frac{\text{UPEs con trámites completos}}{\text{Total UPEs del Régimen}} \times 100$ | $100\%$ previo a escrituración |
| **Tiempo Ciclo Recibo → Factura** | Horas transcurridas desde la descarga del recibo hasta el timbrado de la factura | $< 4\text{ horas}$ |
| **Tasa de Conciliación ERP** | $\frac{\text{Facturas comprobadas en ERP}}{\text{Total facturas emitidas}} \times 100$ | $> 98\%$ mensual |
| **Omisiones Detectadas** | Número de viviendas en venta sin expediente de individualización iniciado | $0\text{ al cierre de mes}$ |
| **Ahorro de Carga Operativa** | Horas-hombre ahorradas mediante descarga RPA y extracción automática | $> 85\%$ vs proceso manual |

