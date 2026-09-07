# 🛡️ Guía de Aplicación de la Matriz de Permisos (RBAC) - Sistema SAR

**Documento:** `SAR-SEC-003` — Estándar de Control de Acceso y Permisos Granulares  
**Proyecto:** Sistema de Administración de Referencias (SAR)  
**Metodología:** [SAR-AI-PROMPTS-001](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/SAR-AI-PROMPTS-001.md)  

---

## 1. Definición Funcional del Catálogo de Acciones (`sar_seguridad.accion`)

En el esquema de seguridad relacional del sistema SAR, los permisos se constituyen mediante la intersección de un **Módulo (`sar_seguridad.modulo`)** y una **Acción (`sar_seguridad.accion`)**. 

A continuación se define la matriz estándar de las 6 acciones registradas en el catálogo del sistema:

| Código Acción | Nombre | Definición Funcional | Aplicación en la Interfaz (PySide6 UI) | Operación Backend / Base de Datos |
| :--- | :--- | :--- | :--- | :--- |
| **`LEER`** | Leer / Consultar | Permiso de acceso base y lectura visual. | Visualización de pestañas en el sidebar, acceso a la vista, carga de tablas dinámicas y filtros. | Queries `SELECT` sin mutación. |
| **`CREAR`** | Crear / Registrar | Alta de nuevas entidades o registros. | Visibilidad de botones *"Capturar Orden"*, *"+ Agregar Renglón"*, *"Guardar Lote"*. | Sentencias `INSERT` o endpoints `POST`. |
| **`EDITAR`** | Editar / Modificar | Cambio de datos o actualización parcial. | Habilitación del botón *"Editar Orden"*, *"Editar Cantidad"*, *"Marcar Visibles"* y edición de celdas. | Sentencias `UPDATE` o endpoints `PUT`/`PATCH`. |
| **`ELIMINAR`** | Eliminar / Cancelar | Operaciones destructivas o bajas lógicas. | Visibilidad y activación de botones *"Cancelar Orden"*, *"Rechazar"*, *"Cancelar Solicitud"*. | Updates con estado `CANCELADA`/`RECHAZADA` o `DELETE`. |
| **`ASIGNAR`** | Asignar / Reservar | Vinculación de recursos y reserva de derechos. | Habilitación de menú *"Asignar Usuario"*, *"Asignar Seleccionados"*, *"Reservar Derechos"*, *"Confirmar Apartados"*. | Transacciones relacionales con bloqueos `FOR UPDATE`. |
| **`EJECUTAR`** | Procesos / Exportar | Disparo de procesos masivos y reportes. | Botones de *"Autorizar Orden Completa"*, *"Generar Excel"*, *"Generar PDF"*, *"Procesar Derechos"*. | Ejecución de funciones PL/pgSQL o pipelines de generación de archivos. |

---

## 2. Aplicación Granular por Módulo y Sub-Módulo

### 📊 Módulo 1: Tablero Principal (`DASHBOARD`)
* **Código en Base de Datos:** `DASHBOARD`
* **Vistas Impactadas:** [`dashboard_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/dashboard_view.py) (`DashboardView`).

| Sub-Sección / Componente | Acción Requerida | Efecto en la Interfaz y Control de Acceso |
| :--- | :--- | :--- |
| **Vista General Dashboard** | `DASHBOARD` + `LEER` | Muestra el item *"Tablero Principal"* en el Sidebar. Permite ver métricas operativas generales, filtros de fechas y búsquedas. |
| **Filtros y Búsqueda Avanzada** | `DASHBOARD` + `LEER` | Permite interactuar con los inputs de búsqueda por folio/derecho y actualizar la tabla de resumen. |
| **Métricas de Producción (Doble Clic / StatCards)** | `DASHBOARD` + `EJECUTAR` | Habilita el evento del doble clic en las StatCards y la apertura del diálogo de Analítica BI (`metrics_dashboard_dialog.py`). |

---

### 📋 Módulo 2: Órdenes de Generación (`ORDENES`)
* **Código en Base de Datos:** `ORDENES`
* **Vistas Impactadas:** [`orders_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/orders_view.py) (`OrdersView`).

| Sub-Sección / Componente | Acción Requerida | Efecto en la Interfaz y Control de Acceso |
| :--- | :--- | :--- |
| **Órdenes Capturadas (Historial)** | `ORDENES` + `LEER` | Muestra el listado del historial de órdenes, barra de estado, tabla de resultados y permite doble clic para consultar el detalle. |
| **Capturar Nueva Orden** | `ORDENES` + `CREAR` | Habilita la pestaña *"Capturar Nueva Orden"*, el selector de cliente/municipio y el botón **"Guardar Orden"**. |
| **Editar Orden Existente** | `ORDENES` + `EDITAR` | Permite seleccionar una orden capturada no procesada y cargarla en modo edición para modificar renglones. |
| **Autorizar Orden Completa** | `ORDENES` + `EJECUTAR` | Habilita el botón **"Autorizar orden completa"** (cambia masivamente el estado de la orden a `AUTORIZADA`). |
| **Rechazar Orden Completa** | `ORDENES` + `ELIMINAR` | Habilita el botón **"Rechazar orden completa"** (marca la orden como `RECHAZADA`). |
| **Cancelar Orden** | `ORDENES` + `ELIMINAR` | Habilita el botón **"Cancelar Orden"** (recursivamente marca la orden y sus solicitudes como `CANCELADA`). |
| **Procesar Derechos por Solicitudes** | `ORDENES` + `EDITAR` | Abre el diálogo `OrderProcessingDialog` para seleccionar solicitudes específicas dentro de una orden. |
| **Acciones en Lote (Procesar Solicitudes)** | `ORDENES` + `EJECUTAR` | Permite usar **"Autorizar seleccionados"**, **"Generar Excel"** y **"Generar PDF"** desde el diálogo de procesamiento. |

---

### 📥 Módulo 3: Solicitudes del Bot (`SOLICITUDES`)
* **Código en Base de Datos:** `SOLICITUDES`
* **Vistas Impactadas:** [`requests_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/requests_view.py) (`RequestsView`).

| Sub-Sección / Componente | Acción Requerida | Efecto en la Interfaz y Control de Acceso |
| :--- | :--- | :--- |
| **Bandeja de Solicitudes** | `SOLICITUDES` + `LEER` | Muestra el listado de solicitudes pendientes/procesadas y la acción doble clic para ver metadatos. |
| **Asignar Usuario Operador** | `SOLICITUDES` + `ASIGNAR` | Habilita la opción **"Asignar usuario"** en el menú contextual de la tabla para delegar la solicitud a un operador. |
| **Editar Cantidad de Derechos** | `SOLICITUDES` + `EDITAR` | Permite abrir el diálogo `EditQuantityDialog` y actualizar la cantidad solicitada. |
| **Cancelar Solicitud Individual** | `SOLICITUDES` + `ELIMINAR` | Habilita la opción **"Cancelar Solicitud"** en el menú contextual de la tabla. |

---

### 📑 Módulo 4: Referencias / Producción de Derechos (`REFERENCIAS`)
* **Código en Base de Datos:** `REFERENCIAS`
* **Vistas Impactadas:** [`referencias_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/referencias_view.py) (`ReferenciasView`).

| Sub-Sección / Componente | Acción Requerida | Efecto en la Interfaz y Control de Acceso |
| :--- | :--- | :--- |
| **Visor de Producción de Derechos** | `REFERENCIAS` + `LEER` | Visualización del listado general de referencias/facturas emitidas, paginación, ver detalle y visor interno de PDF. |
| **Marcar Visibles / Cambiar Estado** | `REFERENCIAS` + `EDITAR` | Habilita las acciones de cambio manual de estado visual (`GENERADA`, `AUTORIZADA`, `EXPIRADA`). |

---

### 🔑 Módulo 5: Control de Derechos e Inventarios (`REFERENCIAS` / Sub-módulo Inventario)
* **Código en Base de Datos:** `REFERENCIAS`
* **Vistas Impactadas:** [`inventory_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/inventory_view.py) (`InventoryView`).

#### 5.1. Sub-tab: Inventario de Facturas/Derechos
* `REFERENCIAS` + `LEER`: Búsqueda de derechos en inventario, doble clic para ver detalle, consulta de tarjetas de métricas (`StatCards`) y apertura de *Analítica de Producción*.
* `REFERENCIAS` + `ASIGNAR`: Habilita la selección múltiple y los botones **"Asignar Seleccionados"** y **"Continuar Asignación"**.
* `REFERENCIAS` + `EJECUTAR`: Habilita el botón **"Exportar a Excel"** para el inventario filtrado.

#### 5.2. Sub-tab: Asignar Derechos (Asignación Directa)
* `REFERENCIAS` + `ASIGNAR`: Permite seleccionar Notaría/Colaborador, asociar cliente y confirmar la asignación directa de referencias reservadas.

#### 5.3. Sub-tab: Asignar & Validar por Lotes
* `REFERENCIAS` + `CREAR`: Carga y lectura del archivo Excel de lote.
* `REFERENCIAS` + `ASIGNAR`: Habilita la acción **"Completar Lote Reservado"**, **"Reservar Derechos"** y el botón final **"Confirmar Lote"**.

#### 5.4. Sub-tab: Reserva de Derechos (Apartados)
* `REFERENCIAS` + `ASIGNAR`: Habilita la confirmación de apartado de números de folio de derechos sin cliente asignado.

#### 5.5. Sub-tab: Gestión de Asignaciones
* `REFERENCIAS` + `LEER`: Consulta del historial de lotes asignados, tabla de control y doble clic para ver desglose de detalle.
* `REFERENCIAS` + `EJECUTAR`: Habilita las acciones **"Exportar Asignación"**, **"Generar Excel"** y **"Generar PDF"** de los expedientes de lote.

---

### ⚙️ Módulos de Administración y Seguridad (`CATALOGOS`, `SEGURIDAD`, `CONFIGURACION`)
* **Código en Base de Datos:** `CATALOGOS`, `SEGURIDAD`, `CONFIGURACION`
* **Vistas Impactadas:** [`admin_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/admin_view.py) (`AdminWindow`) y subvistas asociadas.

| Módulo | Acción | Función Protegida |
| :--- | :--- | :--- |
| `CATALOGOS` | `LEER` / `EDITAR` | Consulta y mantenimiento de catálogos de RFCs, Conceptos, Municipios y Delegaciones. |
| `SEGURIDAD` | `LEER` / `EDITAR` / `ASIGNAR` | Administración de Usuarios, Creación de Roles y Matriz de Permisos RBAC. |
| `CONFIGURACION` | `LEER` / `EDITAR` | Parámetros del sistema, localizadores de portales y procesos especiales de migración/carga masiva. |

---

### 🏝️ Módulos Especiales Cancún (`FOLIOS_CANCUN`, `RECIBOS_CANCUN`, `FACTURAS_CANCUN`)
* **Código en Base de Datos:** `FOLIOS_CANCUN`, `RECIBOS_CANCUN`, `FACTURAS_CANCUN`
* **Vistas Impactadas:** [`r2f_control_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/r2f_control_view.py) (`R2FControlView`).

| Módulo | Acción | Función Protegida |
| :--- | :--- | :--- |
| `FOLIOS_CANCUN` | `LEER` / `EDITAR` | Carga y gestión de folios de capturas en el portal de Cancún. |
| `RECIBOS_CANCUN` | `LEER` / `EJECUTAR` | Consulta y descarga masiva de recibos de pago en Cancún. |
| `FACTURAS_CANCUN` | `LEER` / `EJECUTAR` | Proceso de facturación automatizado y vinculación con R2F. |

---

## 3. Matriz de Roles Estándar de Fábrica

### 🛡️ Rol `ADMINISTRADOR`
* **Ámbito:** Acceso total y global.
* **Asignación de Permisos:** Posee **TODAS** las intersecciones Módulo x Acción (`DASHBOARD`, `ORDENES`, `SOLICITUDES`, `REFERENCIAS`, `CATALOGOS`, `SEGURIDAD`, `CONFIGURACION`, etc., cruzados con las 6 acciones).

### 👷 Rol `OPERADOR` (Rol ID 2)
* **Ámbito:** Operación cotidiana y seguimiento.
* **Permisos Otorgados:**
  * `DASHBOARD`: `LEER`
  * `ORDENES`: `LEER`, `CREAR`
  * `SOLICITUDES`: `LEER`, `EDITAR`, `EJECUTAR`
  * `REFERENCIAS`: `LEER`, `ASIGNAR`, `EJECUTAR`
  * `FOLIOS_CANCUN` / `RECIBOS_CANCUN` / `FACTURAS_CANCUN`: `LEER`, `EJECUTAR`

### 👤 Rol `OPERADOR DE ASIGNACIONES Y BOTS` (Rol ID 4)
* **Ámbito:** Operación sin restricciones en bots de captura/facturación y gestión controlada de inventarios y asignación de derechos.
* **1. Módulos de Aplicación (`sar_seguridad.app_modulo`):**
  * `BOT_FACE_A` ("Bot-Pago de derechos"): **Acceso Completo Operativo**
  * `BOT_C` ("Bot-Facturación"): **Acceso Completo Operativo**
  * `CTRL_REF` ("Control de Referencias"): **Acceso Habilitado**
* **2. Matriz Granular de Permisos RBAC (`sar_seguridad.modulo` x `sar_seguridad.accion`):**
  * **`DASHBOARD`**: `LEER` *(Acceso visual al tablero principal).*
  * **`REFERENCIAS`**: `LEER` *(Lectura de inventario y consulta de asignaciones sin permiso de asignación masiva por lote ni doble clic).*
  * **`REFERENCIAS`**: `ASIGNAR` *(Habilitado exclusivamente para las pestañas de "Asignar Derechos", "Reserva de Derechos" y "Gestión de Asignaciones").*
* **3. Comportamiento Restrictivo en PySide6 UI (`InventoryView`):**
  * 🛑 **Botón "Asignar Seleccionados" (Sub-tab Inventario):** Deshabilitado/Oculto para `rol_id=4`.
  * 🛑 **Acción Doble Clic en Filas de Inventario:** Inactiva (no abre detalle ni modal de asignación rápida).
  * ✅ **Pestaña "Asignar Derechos":** Habilitada para continuar asignaciones de derechos reservadas.
  * ✅ **Pestaña "Gestión de Asignaciones":** Habilitada para consultar, exportar a Excel/PDF y verificar detalle de lotes asignados.

---

## 4. Política de Fallo Seguro (*Fail-Closed Pattern*)

```python
# Ejemplo de implementación atómica en componentes PySide6
def apply_rbac_security(self, usuario_id: int):
    # Por defecto, deshabilitar acciones críticas (Fail-Closed)
    self.btn_guardar.setEnabled(False)
    self.btn_cancelar.setEnabled(False)
    
    # Evaluar permisos vía API REST o SecurityService
    has_crear = self.security_service.has_permission(usuario_id, "ORDENES", "CREAR")
    has_eliminar = self.security_service.has_permission(usuario_id, "ORDENES", "ELIMINAR")
    
    self.btn_guardar.setEnabled(has_crear)
    self.btn_cancelar.setEnabled(has_eliminar)
```

Si ocurre cualquier excepción de red o base de datos durante la verificación de permisos, la interfaz **asume permisos nulos (`False`)**, previniendo que un usuario no autorizado realice acciones destructivas o administrativas.
