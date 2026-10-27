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

La estructura espacial y catastral del SATC opera bajo una jerarquía territorial unificada normalizada:
$$\text{Desarrollo} \longrightarrow \text{Régimen (Macro-Lote: SM, MZ, LT)} \longrightarrow \text{Edificio / Torre} \longrightarrow \text{Vivienda / Espacio Privativo (Interior)}$$

### 2.1 Régimen (`satc_catalogo.regimen`)
En el ecosistema inmobiliario formalizado:
* **Relación Soberana:** `1 Desarrollo = N Regímenes`. Cada régimen representa un polígono físico o macro-lote fiduciario (`SM`, `MZ`, `LT`) con un número total de UPEs autorizadas (`total_upes`).
* **Subdivisión Espacial:** Las viviendas se vinculan directamente al régimen matriz mediante `regimen_id`. Se agrupan opcionalmente por **Edificio o Torre** (`edificio`), nivel (`nivel`), número oficial (`numero_oficial`) e **interior** (`interior`).
* **Ejemplo Operativo:**
  * **Desarrollo:** `AURA NOVA PLAYA`
  * **Régimen:** `REGIMEN AURA NOVA PLAYA MZ1 LT1` (`SM 10, MZ 1, LT 1`)
  * **UPEs Declaradas / Autorizadas:** `577 UPEs`
  * **Distribución:** 577 unidades distribuidas en Torres (ej. *Torre A - Depto 101*).
* **Nivel de Granularidad de los Trámites:**
  1. **Nivel Régimen (Macro-Trámite Matriz):** 
     * Licencia de Construcción Matriz del Régimen.
     * Constitución y Autorización del Régimen en Condominio.
     * Dictámenes Generales de Protección Civil y Servicios Urbanos.
  2. **Nivel Vivienda / Espacio (Micro-Trámite Individualizado):**
     * Importación inicial de unidades (Estado: `PROYECTADA`).
     * Asignación e importación de Folios Electrónicos del RPP (`folio_electronico`).
     * Individualización y alta de Cédula Catastral (`clave_catastral` y `padron`).
     * Recibo de Derechos Catastrales por UPE (Descargado por Bot A).
     * Facturación CFDI (Timbrado por Bot C).
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

### 3.1.1 Individualización RPP (Constancia de Resolución)
* **Disparador:** Emisión del documento oficial del Registro Público de la Propiedad (RPP) por individualización del Régimen en Condominio (ej. *Constancia de Resolución*).
* **Extracción Automatizada (`RppResolutionExtractor`):** Procesamiento de la sección *FOLIOS GENERADOS*, extrayendo el número de fracción, interior, nivel, edificio, número oficial y los 20 dígitos del folio electrónico real con reporte de avance por página vía callback.
* **Regla de Vinculación para Unidades de Servicio (`destino = SERVICIO`):** En las áreas comunes o unidades de servicio donde el campo `edificio` es `null` o `'-'`, el enlace no exige torre/edificio y se concilia de manera unívoca y prioritaria mediante la tupla **`(interior, numero_oficial)`**.
* **Transición de Estado:** Al asignar el folio electrónico, la vivienda transiciona de `PROYECTADA` a `EN_INDIVIDUALIZACION`.

### 3.1.2 Individualización Catastral (Oficio de Alta de Predio de Catastro)
* **Disparador:** Emisión del oficio municipal de alta de predios y asignación de claves catastrales por régimen de condominio.
* **Extracción Automatizada (`CatastroOficioExtractor`):** 
  * **Aislamiento Cromático por Canal Rojo (R):** Segmentación que atenúa sellos y tintas azules institucionales de Catastro para recuperar con máxima nitidez los 20 dígitos del folio electrónico y los 18 dígitos de la clave catastral (`tessedit_char_whitelist=0123456789`).
  * **Procesamiento Concurrente Multi-Core (`ProcessPoolExecutor`):** Renderizado y extracción OCR en paralelo por página a 300 DPI con reporte de progreso en tiempo real (`progress_callback`).
  * **Heurística de Validación Primaria y Erratas Tipográficas:** La conciliación vincula primariamente mediante `folio_electronico` (identificador soberano). Cuando se detecta discrepancia entre los dígitos del folio y la descripción textual del oficio (ej. *Folio termina en 36 pero el texto dice NO OFICIAL 33*), el sistema vincula exitosamente la vivienda correcta e inyecta una advertencia formal clasificada para auditoría.
* **Experiencia de Usuario Homologada (UX / UI):**
  * **Spinner Circular con Porcentaje en Tiempo Real:** El componente `CircularSpinner` calcula y proyecta en el centro exacto el porcentaje de avance (`11% ... 100%`) con tipografía institucional, manteniendo la animación circular de 50 ms.
  * **Cronómetro y Desglose Final:** Al concluir el análisis y la vinculación en BD, se despliega el tiempo exacto transcurrido (`XX seg` o `X min Y seg`).
  * **KPI Dinámico de Alertas:** Indicador interactivo tipo toggle (`Con Advertencia: X`) que filtra al instante los registros con erratas detectadas en el documento oficial sin requerir recargar la vista.

### 3.2 Flujo Integral Post-Claves Catastrales (Preliminar / Pendiente de Confirmación)

> [!NOTE]
> **Estado del Flujo:** Propuesta conceptual preliminar sujeta a confirmación formal de negocio. No se han aplicado cambios a nivel de esquema físico ni migraciones de base de datos hasta que el flujo operativo definitivo sea ratificado.

Una vez formalizada la asignación de las **Claves Catastrales Individuales** de cada vivienda o UPE (mediante el Oficio de Alta de Predio o Cédula Catastral matriz), la secuencia operativa proyectada contempla cuatro etapas:

```
[Claves Catastrales Individuales]
               │
               ▼
   [Etapa 1: Cédula Catastral]
   ├── Emisión: Documento Oficial Cédula Catastral (PDF)
   └── Captura: Folio de Cédula, Fecha de Emisión y Vigencia
               │
               ▼
   [Etapa 2: Determinación y Apertura Predial]
   ├── Generación de Periodo Fiscal (Año / Bimestres)
   └── Vinculación de Cuenta Predial Individual
               │
               ▼
   [Etapa 3: Pago de Impuesto Predial]
   ├── Emisión/Descarga de Recibo Oficial de Pago (Tesorería)
   └── Facturación CFDI (si aplica)
               │
               ▼
   [Etapa 4: Padrón y Constancia Catastral]
   ├── Integración del Padrón Municipal de la Vivienda
   └── Habilitación para Constancia de No Adeudo Predial (NAP)
```

#### Detalle Operativo por Etapa:

1. **Etapa 1: Cédula Catastral Individual**
   * **Emisión Documental:** Generación/Recepción del documento oficial en PDF de la Cédula Catastral individualizada por UPE.
   * **Captura de Metadatos:** Registro y validación del `folio_cedula`, `fecha_emision` y `fecha_vigencia` de la cédula catastral.
   * **Control de Vigencia:** Alerta temprana si la cédula excede su periodo de validez oficial antes de escrituración.

2. **Etapa 2: Determinación y Apertura Predial**
   * **Determinación Fiscal:** Generación y cálculo del periodo fiscal aplicable (ejercicio anual y bimestres gravables correspondientes).
   * **Cuenta Predial Individual:** Vinculación definitiva de la cuenta o clave predial individualizada (`padron`), segregándola del macro-lote base.

3. **Etapa 3: Pago de Impuesto Predial**
   * **Pase de Caja y Tesorería:** Generación del pase a caja municipal y pago de la contribución predial.
   * **Descarga Automatizada (Bot A):** Recuperación del Recibo Oficial de Pago de Tesorería Municipal con extracción de datos e inyección de hash SHA-256.
   * **Timbrado CFDI (Bot C):** Facturación electrónica en el portal municipal (si aplica para acreditamiento o comprobación fiscal empresarial).

4. **Etapa 4: Padrón y Constancia Catastral (NAP)**
   * **Integración al Padrón Municipal:** Consolidación de la vivienda como unidad tributaria independiente en el padrón activo de Benito Juárez (Cancún).
   * **Habilitación Notarial:** Cumplimiento de pre-requisitos y expedición de la **Constancia de No Adeudo Predial (NAP)**, habilitando la vivienda para su pase formal a Notaría (Estado: `EN_ESCRITURACION`).

### 3.3 Etapa de Venta (Comercialización)
* **Disparador:** Asignación comercial de la vivienda a un cliente.
* **Trámites Clave:** Asignación definitiva de Clave Catastral de la UPE, Cédula Catastral Vigente y Apertura en Padrón de Impuesto Predial.
* **Control SATC:** Verificación de que las UPEs cuenten con su clave catastral homologada antes de integrar el expediente notarial.

### 3.4 Etapa de Escrituración y Entrega
* **Disparador:** Firma de contrato de compraventa y llamado a Notaría.
* **Trámites Clave:** Certificado de No Adeudo Predial, Impuesto Sobre Adquisición de Bienes Inmuebles (ISABI), Constancia de No Adeudo de Agua/Drenaje, Verificación de Finiquito de Derechos.
* **Control SATC:** Auditoría documental estricta. Ninguna vivienda pasa a "Escriturada" si presenta adeudos fiscales o trámites en estado pendiente.

### 3.5 Obligaciones Post-Venta
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

### 4.1.1 Bitácora Inmutable de Historial de Estados (`satc_catalogo.vivienda_historial_estado`)
Para satisfacer los requisitos de auditoría notarial, fiscal y de seguridad operativa, **toda transición de estado queda registrada de manera inmutable** en la tabla histórica:
* **Entidad:** `satc_catalogo.vivienda_historial_estado`.
* **Datos Auditados:**
  - `vivienda_id`: Clave primaria de la vivienda.
  - `estado_anterior_id`: Estado previo (o `NULL` en creación).
  - `estado_nuevo_id`: Nuevo estado asignado.
  - `usuario_id`: Usuario responsable que ejecutó la operación (vía UI o API REST).
  - `sesion_id`: Sesión activa de auditoría.
  - `origen_cambio`: Clasificador del disparador (`CARGA_INICIAL`, `VINCULAR_RPP`, `VINCULAR_CATASTRO`, `MANUAL`, `API`).
  - `motivo`: Explicación textual del evento (ej. *Vinculación de Folio RPP: 2026...* o *Vinculación Catastral (CC: 6016...)*).
  - `metadata_adicional`: Objeto JSONB con los datos contextuales procesados en ese momento.
  - `created_at`: Sello temporal con zona horaria (`TIMESTAMPTZ`).
* **Salvaguarda Soberana vía Trigger (`trg_vivienda_historial_estado`)**: Se implementó una función y trigger nativo en PostgreSQL (`AFTER UPDATE OF estado_vivienda_id ON satc_catalogo.vivienda`) que captura cualquier transición manual o externa en base de datos previniendo registros huérfanos sin bitácora.

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

