# SAR-SEC-002: Guía de Aplicación de la Matriz de Permisos (RBAC)
**Categoría:** Seguridad  
**Versión:** 1.0  
**Estado:** Baseline  
**Metodología:** Business-First Architecture (BFA)

---

## 1. Introducción
Esta guía define las directrices y el alcance operativo para la aplicación de la matriz de seguridad basada en roles (RBAC) en el Sistema de Administración de Referencias (SAR). Establece el comportamiento esperado a nivel de interfaz de usuario y base de datos para cada interacción.

---

## 2. Nivel 1: Módulos de Aplicación (Macronivel - Control de Acceso)
Determina en qué puntos de entrada de la aplicación se permite el inicio de sesión. Si el rol del usuario no tiene la relación en `sar_seguridad.rol_app_modulo`, el sistema rechaza la autenticación.

| Código de Módulo | Nombre Comercial | Criterio de Acceso | Vistas Habilitadas |
| :--- | :--- | :--- | :--- |
| **`ADMIN`** | Administración | Exclusivo para administradores del sistema y personal de TI/Seguridad. | Panel completo de configuración de base de datos, auditoría, geografía, catálogos y gestión de usuarios/roles. |
| **`CTRL_REF`** | Control de Referencias | Diseñado para supervisores operativos y analistas de control de cobro. | Tablero de control (Dashboard), creación y consulta de órdenes, asignación de solicitudes, visor de referencias y descargas de PDFs/XMLs. |
| **`BOT_FACE_A`** | Bot - Pago de derechos | Diseñado para los workers de automatización (Robots) y operadores dedicados a la generación de boletas. | Interfaz de ejecución del bot de Playwright para generación de referencias en Tributanet. |
| **`BOT_C`** | Bot - Facturación | Diseñado para los workers de automatización (Robots) y operadores dedicados al timbrado. | Interfaz de ejecución del bot de consulta y descarga de CFDI en el portal SATQ. |

---

## 3. Nivel 2: Módulos Funcionales y Acciones (Micronivel - Autorización Granular)
Una vez dentro de un Módulo de Aplicación, las acciones individuales de los usuarios se rigen por la combinación de **Módulo Funcional** y **Acción**.

Las acciones estándar se definen como:
- **`CREAR`**: Registrar nuevos registros en la base de datos o iniciar nuevas estructuras.
- **`LEER`**: Consultar, filtrar y visualizar información en tablas o formularios de solo lectura.
- **`EDITAR`**: Modificar valores de registros existentes que se encuentren en estados modificables.
- **`ELIMINAR`**: Cancelar, desactivar o realizar borrado lógico (soft-delete) sobre elementos.
- **`ASIGNAR`**: Vincular una entidad operativa a un usuario/operador específico para su procesamiento.
- **`EJECUTAR`**: Disparar scripts, workers o robots de Playwright para procesos automáticos de scraping.

---

## 4. Guía Detallada de Operaciones por Módulo Funcional

### 4.1. DASHBOARD (Tablero Principal)
Módulo enfocado en la visualización general de la salud del sistema, estadísticas de cobro y avance de órdenes.

- **`LEER`**: 
  - Visualizar gráficas de referencias generadas vs. autorizadas.
  - Ver indicadores en tiempo real de errores y solicitudes en proceso.
  - Consultar resúmenes financieros mensuales.
- *Otras Acciones*: No aplican sobre este módulo.

### 4.2. ORDENES (Órdenes de Generación Masiva)
Gestión de requerimientos solicitados por la administración para procesar lotes de referencias.

- **`CREAR`**: Registrar una nueva Orden de Generación con su folio y descripción.
- **`LEER`**: Consultar el listado histórico de órdenes, filtrar por folio y exportar reportes resumidos.
- **`EDITAR`**: Modificar el folio o descripción de una orden (solo si su estado es `BORRADOR`).
- **`ELIMINAR`**: Cancelar de forma definitiva una orden completa (cambia su estado a `CANCELADA` y cancela sus grupos dependientes).
- *Otras Acciones*: No aplican.

### 4.3. SOLICITUDES (Distribución Operativa de Scraping)
Fraccionamiento y asignación de lotes para su ejecución por los bots.

- **`CREAR`**: Generar o fraccionar grupos de referencias en solicitudes detalladas asociando delegaciones y rangos de consecutivos.
- **`LEER`**: Ver el visor de solicitudes, su porcentaje de avance, estado actual (`PROCESANDO`, `ERROR`, `COMPLETADA`) y logs del robot.
- **`EDITAR`**: Modificar la cantidad solicitada de un lote antes de ser procesado (estado `PENDIENTE`).
- **`ELIMINAR`**: Cancelar una solicitud individual (libera el rango de consecutivos asignados).
- **`ASIGNAR`**: Asignar/reasignar una solicitud específica a un operador o robot (`usuario_asignado`).
- **`EJECUTAR`**: Iniciar el scraper automático (Face A) para capturar las boletas en Tributanet.

### 4.4. REFERENCIAS (Referencias Emitidas y Facturas)
Control documental y verificación fiscal de los pagos.

- **`LEER`**: 
  - Consultar la grilla paginada de referencias y facturas timbradas.
  - Descargar los archivos físicos PDF/XML.
- **`EDITAR`**: Corregir información auxiliar de cobro o cambiar el estado del pago ante discrepancias.
- **`ELIMINAR`**: *Bloqueado por política SEC-004*. Ninguna referencia o factura puede ser eliminada físicamente de la base de datos para mantener integridad fiscal.
- **`ASIGNAR`**: Vincular facturas a colaboradores específicos para envío de correos o entregas.
- **`EJECUTAR`**: Disparar el Bot Face C para consultar Tributanet/SATQ y validar si los folios han sido cobrados o requieren facturación.

### 4.5. CATALOGOS (Catálogos Maestros de Operación)
Administración de datos del entorno del bot.

- **`CREAR`**: Agregar nuevos RFCs (empresas), conceptos de cobro o delegaciones del RPP.
- **`LEER`**: Listar datos de RFCs, ver aliases de conceptos de cobro y geografía municipal.
- **`EDITAR`**: Modificar domicilios fiscales, cambiar nombres comerciales o actualizar el alias de un concepto.
- **`ELIMINAR`**: Desactivar registros del catálogo (cambia el atributo `activo` a `FALSE` para evitar que sigan usándose en nuevos procesos, sin borrar historial transaccional).

### 4.6. SEGURIDAD (Control de Acceso y RBAC)
Gestión administrativa de los accesos al sistema.

- **`CREAR`**: Registrar nuevos usuarios o perfiles/roles en la plataforma.
- **`LEER`**: Consultar las bitácoras de auditoría de eventos (`auditoria_evento`), inicios de sesión (`auditoria_login`), historial de sesiones activas e historial de errores.
- **`EDITAR`**: 
  - Asignar roles a usuarios.
  - Cambiar contraseñas (generando el hash Argon2id).
  - Modificar la matriz de permisos de un Rol o asignar sus módulos autorizados (`rol_app_modulo`).
- **`ELIMINAR`**: Desactivar la cuenta de un usuario (`activo = FALSE`) o dar de baja lógica un rol.

### 4.7. CONFIGURACION (Parámetros y Localizadores de Portal)
Ajuste de variables de comportamiento de la aplicación y del navegador automatizado.

- **`CREAR`**: Agregar nuevos parámetros operativos o selectores XPath/CSS para nuevos campos de los portales gubernamentales.
- **`LEER`**: Ver el listado de configuraciones activas.
- **`EDITAR`**: Modificar el valor de un parámetro (ej. cambiar el tiempo del `HEARTBEAT` o el `TAMANO_LOTE`) o actualizar un selector web por cambios en el diseño de Tributanet/SATQ.
- **`ELIMINAR`**: Desactivar un parámetro o localizador en desuso.

---

## 5. Configuración de Roles Típicos (Ejemplo de Aplicación)

### 5.1. Rol: Trabajador de Automatización (BOT_WORKER)
Diseñado exclusivamente para que los procesos autónomos (Scrapers Face A y Face C) realicen consultas y escrituras sin intervención humana ni acceso a consolas administrativas.

#### A. Acceso a Módulos de Aplicación (Nivel 1)
- [x] **`BOT_FACE_A`** (Bot - Pago de derechos)
- [x] **`BOT_C`** (Bot - Facturación)
- [ ] **`ADMIN`** (Administración) - *Deshabilitado*
- [ ] **`CTRL_REF`** (Control de Referencias) - *Deshabilitado*

#### B. Permisos en la Matriz Operativa (Nivel 2)
1. **SOLICITUDES**:
   - `LEER`: Consultar la cola de solicitudes pendientes.
   - `EDITAR`: Actualizar reintentos y estados intermedios.
   - `EJECUTAR`: Habilitar la ejecución automatizada de Playwright.
2. **REFERENCIAS**:
   - `LEER`: Consultar referencias generadas.
   - `CREAR`: Registrar nuevos registros de referencia y boletas PDF generadas.
   - `EJECUTAR`: Ejecutar el proceso de timbrado en SATQ.
3. **CONFIGURACION**:
   - `LEER`: Cargar variables del sistema (HEARTBEAT, timeouts) y selectores XPath de los localizadores.
4. **CATALOGOS**:
   - `LEER`: Validar RFCs y conceptos asignados.

### 5.2. Rol: Operador del Sistema (OPERADOR)
Diseñado para el personal operativo (usuarios humanos) que supervisa la generación, administra la cola de solicitudes, dispara ejecuciones de bots manualmente y visualiza los reportes/referencias generadas.

#### A. Acceso a Módulos de Aplicación (Nivel 1)
- [x] **`CTRL_REF`** (Control de Referencias) - *Habilitado para interfaz visual principal*
- [x] **`BOT_FACE_A`** (Bot - Pago de derechos) - *Habilitado para disparos interactivos*
- [x] **`BOT_C`** (Bot - Facturación) - *Habilitado para timbrado interactivo*
- [ ] **`ADMIN`** (Administración) - *Deshabilitado (Seguridad Macronivel)*

#### B. Permisos en la Matriz Operativa (Nivel 2)
1. **DASHBOARD**:
   - `LEER`: Visualizar métricas generales y de rendimiento operativo.
2. **ORDENES**:
   - `LEER`: Consultar el listado histórico de órdenes y su progreso.
3. **SOLICITUDES**:
   - `LEER`: Consultar el avance detallado de las delegaciones.
   - `EJECUTAR`: Disparar manualmente los scrapers automáticos para solicitudes específicas.
4. **REFERENCIAS**:
   - `LEER`: Listar boletas generadas y descargar archivos PDF/XML.
   - `EJECUTAR`: Forzar manualmente el timbrado o validación en SATQ de referencias pendientes.
5. **CATALOGOS**:
   - `LEER`: Consultar RFCs y conceptos activos en modo de solo lectura.
6. **CONFIGURACION**:
   - `LEER`: Visualizar localizadores activos en modo de solo lectura para soporte básico.


