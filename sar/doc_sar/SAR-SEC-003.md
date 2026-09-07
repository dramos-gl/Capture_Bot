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

## 2. Aplicación Granular por Módulo y Sub-Módulo (Con Jerarquía de Orden)

La tabla de módulos internos `sar_seguridad.modulo` incluye la columna **`orden NUMERIC(4,1)`** que rige tanto la secuencia de navegación en el Sidebar como el rotulado en la Matriz de Permisos (`[orden] Nombre`):

| Orden | Código Módulo (`sar_seguridad.modulo`) | Nombre en Pantalla | Vista PySide6 Impactada | Acciones Soportadas |
| :---: | :--- | :--- | :--- | :--- |
| **1.0** | `DASHBOARD` | Inicio | [`dashboard_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/dashboard_view.py) | `LEER`, `EJECUTAR` |
| **2.0** | `DERECHOS` | Derechos (Producción) | [`referencias_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/referencias_view.py) | `LEER`, `EDITAR` |
| **3.0** | `CONTROL_DERECHOS` | Control de Derechos | [`inventory_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/inventory_view.py) | `LEER` |
| **3.1** | `CTRL:INVENTARIO` | Inventario | [`inventory_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/inventory_view.py) (Sub-tab Visor) | `LEER`, `ASIGNAR`, `EJECUTAR` |
| **3.2** | `CTRL:ASIGNAR_DERECHO` | Asignar Derecho | [`inventory_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/inventory_view.py) (Sub-tab Asignación) | `LEER`, `ASIGNAR` |
| **3.3** | `CTRL:ASIGNAR_VALIDAR` | Asignar/Validar por Lotes | [`inventory_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/inventory_view.py) (Sub-tab Masivo) | `LEER`, `CREAR`, `ASIGNAR` |
| **3.4** | `CTRL:RESERVA_DERECHO` | Reservar Derecho (Apartados) | [`inventory_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/inventory_view.py) (Sub-tab Apartar) | `LEER`, `ASIGNAR` |
| **3.5** | `CTRL:GESTION_LOTES` | Gestión de asignaciones | [`inventory_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/inventory_view.py) (Sub-tab Lotes) | `LEER`, `EJECUTAR` |
| **--** | `ORDENES` | Órdenes de Generación | [`orders_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/orders_view.py) | `LEER`, `CREAR`, `EDITAR`, `ELIMINAR`, `EJECUTAR` |
| **--** | `SOLICITUDES` | Solicitudes del Bot | [`requests_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/requests_view.py) | `LEER`, `ASIGNAR`, `EDITAR`, `ELIMINAR` |
| **--** | `CATALOGOS` | Catálogos del Sistema | [`admin_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/admin_view.py) | `LEER`, `CREAR`, `EDITAR`, `ELIMINAR` |
| **--** | `SEGURIDAD` | Control de Acceso (RBAC) | [`admin_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/admin_view.py) | `LEER`, `CREAR`, `EDITAR`, `ELIMINAR`, `ASIGNAR` |
| **--** | `CONFIGURACION` | Configuración General | [`admin_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/src/ui/views/admin_view.py) | `LEER`, `EDITAR` |

---

### 📊 Detalle por Componente Visual

#### 📊 Módulo [1] Inicio (`DASHBOARD`)
* `LEER`: Acceso al tablero principal, búsqueda, filtros de fecha/orden y lectura de indicadores KPI.
* `EJECUTAR`: Habilita la acción de **doble clic** en las StatCards de KPI (*Total Generadas*, *Pendientes*, *Autorizadas*, *Rechazadas*) para aperturar el módulo de *Métricas y Analítica Operativa (BI)*.
* **Detalle de Errores e Invalidadas:** El **doble clic** en las StatCards de *Con Error* o *Invalidadas* requiere permisos de consulta de detalle (`DASHBOARD:LEER` o `DERECHOS:LEER`). En caso de falta de permisos, el sistema aplica la política de fallo seguro denegando el acceso e informando mediante `GLMessageBox.warning`.

#### 📑 Módulo [2] Derechos (`DERECHOS`)
* `LEER`: Visualización del listado general de referencias/facturas emitidas, paginación y activación de los botones **"Ver Detalle"** (`_on_ver_detalle`) y **"Ver PDF"** (`_on_ver_pdf`).
* `EDITAR`: Habilita la ejecución de las acciones de modificación masiva: botones **"Marcar Visibles"** (`_on_marcar_visibles`) y **"Cambiar Estado"** (`_on_cambiar_estado`). En ausencia de este permiso, la acción se bloquea e informa mediante `QMessageBox.warning`.

#### 🔑 Módulo [3] Control de Derechos y Submódulos

##### [3.1] Inventario (`CTRL:INVENTARIO`)
* `LEER`: Búsqueda de derechos en inventario, filtros por empresa/concepto, y apertura con **doble clic** del diálogo modal de detalle desde las StatCards KPI (`_open_kpi_detail` $\rightarrow$ `InventoryKPIDetailDialog`).
* `ASIGNAR`: Habilita el botón **"Asignar Seleccionados"** (`_on_asignar_seleccionados`) y la acción de **doble clic** sobre las filas de la tabla (`_on_table_cell_double_clicked`) para aperturar el formulario de asignación a Notaría/Colaborador (`ManualAssignmentDialog`).
* `EJECUTAR`: Habilita el botón de redirección **"Ver Métricas y Analítica de Producción"** (`_on_open_metrics_requested`) y el botón **"Exportar a Excel"** (`_on_export_excel`) dentro del diálogo de detalle KPI. En caso de ausencia de permiso, el sistema aplica el fallo seguro denegando el acceso vía `QMessageBox.warning`.

##### [3.2] Asignar Derecho (`CTRL:ASIGNAR_DERECHO`)
* `LEER`: Visibilidad de la pestaña *"Asignar Derechos"* y habilitación de la acción **"Buscar Derechos"** (`_on_buscar_referencias_ind`) para consultar disponibilidades físicas de referencias facturadas según los criterios de empresa, concepto y delegación.
* `ASIGNAR`: Habilita el botón **"Continuar Asignación"** (`_on_confirmar_asignacion_ind`) para aperturar el diálogo de asignación manual (`ManualAssignmentDialog`) y transferir formalmente las referencias seleccionadas a la Notaría o Colaborador de destino. En caso de ausencia de permiso, el sistema aplica la política de fallo seguro denegando la acción vía `QMessageBox.warning`.

##### [3.3] Asignar/Validar por Lotes (`CTRL:ASIGNAR_VALIDAR`)
* `LEER`: Visibilidad de la pestaña *"Asignar & Validar por lotes"* y habilitación del botón **"Descargar Plantilla"** (`_on_download_template`).
* `CREAR`: Habilita la acción **"Seleccionar Excel"** (`_on_pick_excel_masivo`) para cargar, parsear y previsualizar en segundo plano el archivo Excel de lote.
* `ASIGNAR`: Habilita la selección de las casillas **"Completar Lote Reservado"** (`_on_completar_reserva_changed`) y **"Reservar Derechos"** (`_on_solo_reservar_changed`), así como la ejecución del botón **"Confirmar"** (`_on_confirmar_masivo`) para aplicar y consolidar en la base de datos el lote de asignaciones masivas. En caso de ausencia de permiso, el sistema aplica el patrón de fallo seguro informando vía `QMessageBox.warning`.

##### [3.4] Reservar Derecho (`CTRL:RESERVA_DERECHO`)
* `LEER`: Visibilidad de la pestaña *"Reserva de Derechos"*, filtros dinámicos por empresa/desarrollo y cálculo de disponibilidades.
* `ASIGNAR`: Habilita la acción del botón **"Confirmar Apartados"** (`_on_save_apartar`) para reservar y apartar folios físicamente en favor de una Notaría seleccionada. En caso de ausencia de permiso, el sistema aplica la política de fallo seguro denegando la acción e informando vía `QMessageBox.warning`.

##### [3.5] Gestión de asignaciones (`CTRL:GESTION_LOTES`)
* `LEER`: Consulta del historial de lotes asignados, filtros dinámicos, activación del botón **"Ver Detalle"** (`_on_ver_detalle_lote`) y apertura por **doble clic** (`_on_table_cell_double_clicked_lotes`) del diálogo modal de desglose (`LoteProcessingDialog`).
* `EJECUTAR`: Habilita la acción del botón **"Exportar Asignación Seleccionada"** (`_on_exportar_lote_seleccionado`), así como las acciones internas del diálogo de detalle: **"Generar Excel"** (`_on_generate_excel`) y **"Generar PDF"** (`_on_generate_pdf`) para la expedición formal de documentos. En caso de ausencia de permiso, el sistema deniega el acceso e informa mediante `QMessageBox.warning`.

#### 📦 Módulo Órdenes de Generación (`ORDENES`)
* `LEER`: Consulta del historial de órdenes capturadas (`tab_historial`), búsqueda por folio, apertura con **doble clic** del módulo interactivo *Procesar Derechos* (`OrderProcessingDialog`), y habilitación del botón **"! Validar Domicilio Fiscal"** (`_on_abrir_validador_fiscal` $\rightarrow$ `CompanyFiscalValidationDialog`) para consultar de solo lectura el domicilio fiscal de las empresas registradas antes de generar órdenes.
* `CREAR`: Habilita la acción de **Guardar Orden** (`_on_guardar_orden`) en modo de creación para registrar nuevas órdenes con sus partidas.
* `EDITAR`: Habilita la carga de una orden para modificación (`load_order_for_editing`) y la acción **Actualizar Orden**.
* `ELIMINAR`: Permite la acción **Cancelar Orden** (`_on_cancelar_orden`) para dar de baja órdenes y sus solicitudes asociadas.
* `EJECUTAR`: Permite la ejecución masiva desde el historial de **Autorizar Orden Completa** (`_on_autorizar_orden`) / **Rechazar Orden Completa** (`_on_rechazar_orden`), así como las acciones internas del diálogo *Procesar Derechos*: **Generar Excel** (`_on_generar_excel_lotes`), **Generar PDF** (`_on_generar_pdf_unificado`), **Autorizar seleccionadas** (`_on_authorize_selected`) y **Rechazar seleccionadas** (`_on_reject_selected`). En caso de ausencia del permiso `EJECUTAR`, el sistema aplica la política de fallo seguro denegando el procesamiento e informando mediante `QMessageBox.warning`.

#### 🤖 Módulo Solicitudes del Bot (`SOLICITUDES`)
* `LEER`: Consulta de la bandeja de solicitudes de trabajo, filtros y búsqueda. Habilita el **doble clic** en la columna *Folio Orden* para aperturar el diálogo interactivo *Procesar Derechos* (`OrderProcessingDialog`).
* `ASIGNAR`: Habilita el botón **Asignar Usuario** (`_on_asignar`) para reasignar solicitudes a operadores específicos.
* `EDITAR`: Habilita el botón **Editar Cantidad** (`_on_editar`) para ajustar la cantidad solicitada de la orden de trabajo.
* `ELIMINAR`: Habilita el botón **Cancelar Solicitud** (`_on_cancelar`) para dar de baja una solicitud de trabajo en la cola del bot. En ausencia de permisos, el sistema aplica la política de fallo seguro informando vía `QMessageBox.warning`.

---

## 3. Matriz de Roles Estándar de Fábrica

### 🛡️ Rol `ADMINISTRADOR` (Rol ID 1)
* **Ámbito:** Acceso total y global.
* **Permisos:** Posee **TODAS** las intersecciones Módulo x Acción en la base de datos.

### 👷 Rol `OPERADOR` (Rol ID 2)
* **Ámbito:** Operación cotidiana de generación y scrapers.
* **Permisos:** `DASHBOARD:LEER`, `ORDENES:LEER,CREAR`, `SOLICITUDES:LEER,EDITAR,EJECUTAR`, `DERECHOS:LEER`, `CTRL:INVENTARIO:LEER,ASIGNAR,EJECUTAR`.

### 👤 Rol `OPERADOR DE ASIGNACIONES Y BOTS` (Rol ID 4)
* **Ámbito:** Operación sin restricciones en bots y gestión controlada de asignación de derechos.
* **1. Módulos de Aplicación (`sar_seguridad.app_modulo`):**
  * `BOT_FACE_A` ("Bot-Pago de derechos"): **Acceso Completo Operativo**
  * `BOT_C` ("Bot-Facturación"): **Acceso Completo Operativo**
  * `CTRL_REF` ("Control de Referencias"): **Acceso Habilitado**
* **2. Permisos Granulares RBAC Otorgados en BD:**
  * `DASHBOARD`: `LEER`
  * `DERECHOS`: `LEER` *(Lectura de tabla de derechos. Botones "Marcar Visibles" y "Cambiar Estado" deshabilitados al no tener EDITAR)*.
  * `CTRL:INVENTARIO`: `LEER` *(Lectura y filtros. Botón "Asignar Seleccionados" deshabilitado y doble clic inactivo al no tener ASIGNAR)*.
  * `CTRL:ASIGNAR_DERECHO`: `LEER`, `ASIGNAR` *(Pestaña y asignación directa habilitada)*.
  * `CTRL:GESTION_LOTES`: `LEER`, `EJECUTAR` *(Pestaña y exportación a Excel/PDF de asignaciones habilitada)*.
* **3. Submódulos Restringidos en Sidebar y UI:**
  * 🛑 `CTRL:ASIGNAR_VALIDAR` ("Asignar/Validar por Lote"): **Oculto / Deshabilitado**.
  * 🛑 `CTRL:RESERVA_DERECHO` ("Reserva de Derechos"): **Oculto / Deshabilitado**.

---

## 4. Política de Fallo Seguro (*Fail-Closed Pattern*)

```python
# Ejemplo de implementación atómica en componentes PySide6 (DashboardView)
def _check_permission(self, modulo_codigo: str, accion_codigo: str) -> bool:
    """Verifica permisos antes de ejecutar acciones en Dashboard."""
    parent_window = self.window()
    usuario_id = getattr(parent_window, 'current_usuario_id', None)
    if not usuario_id:
        return True # Fallback para pruebas/instanciación independiente
    
    try:
        with self.db_connector.get_session() as session:
            from sar.src.services.security_service import SecurityService
            sec_service = SecurityService(session)
            return sec_service.has_permission(usuario_id, modulo_codigo, accion_codigo)
    except Exception as e:
        print(f"Error checking permission {modulo_codigo}:{accion_codigo}: {e}")
        return False

def _on_card_double_clicked(self, event):
    if not self._check_permission("DASHBOARD", "EJECUTAR"):
        from sar.src.ui.design_system.components import GLMessageBox as QMessageBox
        QMessageBox.warning(
            self,
            "Acceso Denegado",
            "No tiene permisos para acceder al módulo de Métricas y Analítica Operativa (DASHBOARD:EJECUTAR)."
        )
        return
    self.show_metrics_requested.emit(list(self.selected_orden_ids))
```

Si ocurre cualquier excepción de red o base de datos durante la verificación de permisos, la interfaz **asume permisos nulos (`False`)**, previniendo que un usuario no autorizado realice acciones destructivas o administrativas.
