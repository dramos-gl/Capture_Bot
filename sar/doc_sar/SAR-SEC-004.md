# 🛡️ Guía de Aplicación de la Matriz de Permisos (RBAC) - Módulo CTRL_R2F (Recibos & Facturas)

**Documento:** `SAR-SEC-004` — Estándar de Control de Acceso y Permisos Granulares para Control de Recibos y Facturas (R2F CancúnBot)  
**Proyecto:** Sistema de Administración de Referencias (SAR) — Sub-sistema R2F Cancún  
**Metodología:** [SAR-AI-PROMPTS-001](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/SAR-AI-PROMPTS-001.md) | **Ref:** [SAR-SEC-003](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/SAR-SEC-003.md)  

---

## 1. Definición Funcional de Acciones para R2F (`sar_seguridad.accion`)

En el módulo **Control de Recibos & Facturas (R2F)**, la seguridad relacional se rige mediante la intersección del Módulo (`sar_seguridad.app_modulo` / `sar_seguridad.modulo`) y las Acciones Granulares (`sar_seguridad.accion`):

| Código Acción | Nombre | Aplicación en el Módulo CTRL_R2F (PySide6 UI) | Operación Backend / Base de Datos |
| :--- | :--- | :--- | :--- |
| **`LEER`** | Consultar / Lectura | Acceso visual a las pestañas del sidebar (*"Capturar Orden"*, *"Órdenes Capturadas"*, *"Control de Recibos"*), consulta del listado de recibos, filtros por RFC/Estado y lectura de StatCards KPI. | Consultas `SELECT` sobre `cancunbot_produccion.orden_cancun`, `lote_folio`, `folio_cancun` y `recibo_cancun`. |
| **`CREAR`** | Crear / Importar | Visibilidad y ejecución de los botones *"📁 Importar Plantilla Excel"*, *"📄 Importar Boletas / PDF(s)"* y alta de nuevas órdenes `OrdenCancun`. | Inserts transaccionales en `orden_cancun`, `lote_folio` y `folio_cancun` (o endpoints `POST`). |
| **`EDITAR`** | Modificar / Seleccionar | Habilitación de la acción masiva *"Marcar Visibles"* (`_on_marcar_visibles`) y edición/actualización de lotes. | Modificación de registros y actualización de contadores. |
| **`ELIMINAR`** | Liberar / Revertir | Habilitación del botón *"Liberar para Factura"* (`_on_liberar_factura`) para regresar recibos a estado `PENDIENTE_FACTURAR`. | Updates de estado en `cancunbot_produccion.recibo_cancun`. |
| **`ASIGNAR`** | Catalogación / Vinculación | Resolución de catálogos maestros de RFC (`sar_catalogo.rfc`) y Desarrollo (`sar_catalogo.desarrollo`) durante la importación. | Consultas y mapeo de IDs de catálogo relacional. |
| **`EJECUTAR`** | Bot / Exportar / PDF | Habilitación del botón *"🤖 Abrir Bot R2F Cancún"*, *"Ver PDF Recibo"* (`_on_ver_pdf`) y *"⬇ Descargar Plantilla Excel"*. | Disparo del worker Playwright `BotReciboCunWorker`, apertura de visores PDF del sistema operativo y generación de plantillas. |

---

## 2. Jerarquía de Módulos y Sub-Módulos (`sar_seguridad.modulo`)

| Orden | Código Módulo (`sar_seguridad.modulo`) | Nombre en Pantalla | Vista PySide6 / Componente | Acciones Soportadas |
| :---: | :--- | :--- | :--- | :--- |
| **8.0** | `CTRL_R2F` | Control de Recibos & Facturas (R2F) | [`r2f_control_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/cancunbot/src/ui/views/r2f_control_view.py) | `LEER`, `CREAR`, `EDITAR`, `ELIMINAR`, `ASIGNAR`, `EJECUTAR` |
| **8.1** | `R2F:CAPTURAR_ORDEN` | Capturar Orden / Importar | `R2FControlView._build_capturar_orden_page()` (Pestaña 1) | `LEER`, `CREAR`, `EJECUTAR` |
| **8.2** | `R2F:ORDENES_CAPTURADAS` | Órdenes Capturadas | `R2FControlView._build_ordenes_capturadas_page()` (Pestaña 2) | `LEER`, `EDITAR` |
| **8.3** | `R2F:BANDEJA_CONTROL` | Bandeja de Control R2F | `R2FControlView._build_bandeja_control_page()` (Pestaña 3) | `LEER`, `EDITAR`, `ELIMINAR`, `EJECUTAR` |
| **8.4** | `BOT_R2F` | Bot R2F Cancún (Ejecución) | [`r2f_cancun_view.py`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/cancunbot/src/ui/views/r2f_cancun_view.py) | `LEER`, `EJECUTAR` |

---

## 3. Matriz de Permisos por Perfil de Usuario (RBAC)

| Módulo / Sub-módulo | Acción | ADMINISTRADOR | OPERADOR | CONSULTOR |
| :--- | :---: | :---: | :---: | :---: |
| `CTRL_R2F` (Acceso al Módulo) | `LEER` | ✅ Autorizado | ✅ Autorizado | ✅ Autorizado |
| `R2F:CAPTURAR_ORDEN` (Importar Excel/PDF) | `CREAR` | ✅ Autorizado | ✅ Autorizado | ❌ Bloqueado |
| `R2F:CAPTURAR_ORDEN` (Descargar Plantilla) | `EJECUTAR` | ✅ Autorizado | ✅ Autorizado | ✅ Autorizado |
| `R2F:ORDENES_CAPTURADAS` (Historial de Órdenes) | `LEER` | ✅ Autorizado | ✅ Autorizado | ✅ Autorizado |
| `R2F:BANDEJA_CONTROL` (Bandeja y Filtros) | `LEER` | ✅ Autorizado | ✅ Autorizado | ✅ Autorizado |
| `R2F:BANDEJA_CONTROL` (Liberar para Factura) | `ELIMINAR` | ✅ Autorizado | ✅ Autorizado | ❌ Bloqueado |
| `R2F:BANDEJA_CONTROL` (Ver PDF Recibo) | `EJECUTAR` | ✅ Autorizado | ✅ Autorizado | ✅ Autorizado |
| `BOT_R2F` (Ejecutar Bot Cancún) | `EJECUTAR` | ✅ Autorizado | ✅ Autorizado | ❌ Bloqueado |

---

## 4. Política de Fallo Seguro (Fail-Closed) en la Interfaz

Siguiendo el estándar de seguridad SAR (`SAR-SEC-001` y `SAR-SEC-003`):

1. **Ocultación/Deshabilitación Visual**:
   - Si el usuario carece de la acción `CREAR` en `CTRL_R2F`, los botones *"📁 Importar Plantilla Excel"* y *"📄 Importar Boletas / PDF(s)"* se deshabilitan o se ocultan visualmente.
   - Si el usuario carece de la acción `EJECUTAR`, el botón *"🤖 Abrir Bot R2F Cancún"* deniega la apertura.

2. **Interceptación de Intentos No Autorizados**:
   - Al invocar cualquier acción de mutación sin los privilegios requeridos, el sistema bloquea la transacción e informa al usuario mediante el componente estándar del Design System:
     ```python
     GLMessageBox.warning(self, "Acceso Denegado", "No cuentas con los privilegios requeridos para ejecutar esta acción.")
     ```

---

## 5. Script DDL de Integración en Base de Datos

El registro formal en las tablas del esquema `sar_seguridad` se ejecuta mediante la migración:
- [`005_register_ctrl_r2f_app_modulo.sql`](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/cancunbot/src/storage/migrations/005_register_ctrl_r2f_app_modulo.sql)

```sql
-- Registrar módulo CTRL_R2F en sar_seguridad.app_modulo
INSERT INTO sar_seguridad.app_modulo (codigo, nombre, activo)
VALUES ('CTRL_R2F', 'Control de Recibos & Facturas (R2F)', TRUE)
ON CONFLICT (codigo) DO UPDATE 
SET nombre = EXCLUDED.nombre, activo = TRUE;

-- Otorgar accesos a roles
INSERT INTO sar_seguridad.rol_app_modulo (rol_id, app_modulo_id)
SELECT r.rol_id, am.app_modulo_id
FROM sar_seguridad.rol r
CROSS JOIN sar_seguridad.app_modulo am
WHERE r.codigo IN ('ADMINISTRADOR', 'OPERADOR')
  AND am.codigo = 'CTRL_R2F'
ON CONFLICT (rol_id, app_modulo_id) DO NOTHING;
```

---
*Documento formal generado según el estándar de arquitectura de seguridad SAR.*
