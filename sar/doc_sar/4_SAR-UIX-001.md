# SAR-UIX-001: Especificación UX/UI
**Categoría:** Experiencia de Usuario  
**Versión:** 1.0  
**Estado:** Baseline Inicial  
**Metodología:** Business-First Architecture (BFA)  
Dependencias:

SAR-BLUEPRINT-001 v1.3
SAR-DAT-001 v1.0
SAR-OPS-001 v1.1
1. Objetivo

Definir la experiencia operativa completa del Sistema de Administración de Referencias (SAR), incluyendo:

Navegación.
Pantallas.
Permisos.
Flujos operativos.
Componentes funcionales.
Dashboards.
Interacción entre Administradores y Usuarios Operativos.
2. Principios de Diseño
UIX-001

SAR es un sistema operativo empresarial, no un sitio web comercial.

UIX-002

La prioridad es productividad.

UIX-003

Reducir clics.

UIX-004

Toda información relevante debe visualizarse sin navegar múltiples pantallas.

UIX-005

La trazabilidad debe estar disponible en cualquier momento.

UIX-006

La experiencia debe ser similar a:

ERP
CRM
Sistemas de Mesa de Control

UIX-007

Responsividad y Adaptabilidad de Pantalla:
Toda ventana, formulario modal y diálogo del sistema debe adaptarse de forma fluida a resoluciones desde 1366×768 (laptops estándar) hasta monitores 4K y diferentes escalas de DPI (100% a 150%). Ningún formulario debe desbordar los límites físicos de la pantalla ni ocultar botones de acción críticos; los formularios extensos deben estructurarse obligatoriamente en 3 niveles: Cabecera de contexto fija, Cuerpo central desplazable (`QScrollArea`) y Pie fijo con botones de confirmación (`[Guardar]`, `[Cancelar]`).
3. Roles
Administrador

Acceso total.

Permisos
Crear órdenes.
Importar solicitudes.
Asignar solicitudes.
Reasignar solicitudes.
Consultar referencias.
Consultar auditoría.
Gestionar catálogos.
Monitorear sesiones.
Usuario Operativo

Acceso limitado.

Permisos
Ver solicitudes asignadas.
Procesar solicitudes.
Consultar progreso.
Consultar referencias generadas por sus procesos.
4. Mapa General de Navegación

El sistema SAR implementa un modelo de **ventanas independientes por módulo**. Al iniciar sesión, el usuario debe seleccionar el módulo al que desea acceder. Según el módulo seleccionado, el sistema abre una ventana independiente (`QMainWindow`) con su propia interfaz y permisos.

```
LOGIN (Ventana única de autenticación)
  │
  ├── [Selector de Módulo] ← ComboBox cargado dinámicamente desde BD
  ├── [Usuario]
  ├── [Contraseña]
  └── [Iniciar Sesión]
         │
         ├── ADMIN          → Ventana: Administración del Sistema
         │     ├── Seguridad (Usuarios, Roles, Permisos, Módulos, Acciones)
         │     ├── Catálogos (Conceptos, Geografía, RFCs, Estados)
         │     └── Configuración (Parámetros, Localizadores)
         │
         ├── CTRL_REF       → Ventana: Control de Referencias (maximizada)
         │     ├── Dashboard
         │     ├── Órdenes
         │     ├── Solicitudes
         │     └── Referencias
         │
         ├── BOT_FACE_A     → Ventana: Bot Face A - Automatización (Fase A)
         │
         └── BOT_C          → Ventana: Bot Face C - Facturación y Timbrado (Fase C)
```

**Notas de implementación:**
- Los módulos disponibles en el ComboBox se cargan dinámicamente desde la base de datos (`get_all_app_modulos()`).
- Cada módulo abre su propia `QMainWindow` independiente; la ventana de login se oculta (`hide()`) durante la sesión activa.
- Al cerrar sesión (`logout`), la ventana del módulo activo se cierra y la ventana de login vuelve a mostrarse (`show()`).
- Los módulos `BOT_FACE_A` y `BOT_C` se abren en tamaño normal (1100×750); los módulos `ADMIN` y `CTRL_REF` se abren maximizados.
5. Login
Objetivo

Autenticar usuarios y dirigirlos al módulo de trabajo correspondiente.

Flujo de Autenticación
1. El usuario selecciona el **módulo al que desea acceder** desde el ComboBox.
2. Ingresa su **usuario** y **contraseña**.
3. Presiona **[Iniciar Sesión]**.
4. El sistema valida que los tres campos estén completos antes de emitir la solicitud.
5. Las credenciales se verifican contra la base de datos física mediante `SecurityService.login()`.
6. Si son válidas, la ventana de login se oculta y se abre la ventana del módulo seleccionado.
7. Si son inválidas, se muestra el mensaje de error en el campo de contraseña.

Componentes
+----------------------------------+

          🔒 SAR Login

   Sistema Administración
        Referencias

  Módulo de Acceso

  [  Seleccionar un módulo  ▼]

  Usuario
  [________________________]

  Contraseña
  [························]

  [Iniciar Sesión]  [Cancelar]

+----------------------------------+

Detalle de Componentes

| Componente | Tipo | Comportamiento |
|---|---|---|
| **Selector de Módulo** | `CustomComboBox` | Cargado dinámicamente desde BD. Campo requerido. |
| **Usuario** | `LabeledInput` (icono user) | Campo requerido. Muestra error inline si vacío. |
| **Contraseña** | `LabeledInput` (icono lock, enmascarado) | Campo requerido. Muestra error general de login. |
| **[Iniciar Sesión]** | `CustomButton` (primario) | Valida campos y emite señal `login_requested`. |
| **[Cancelar]** | `CustomButton` (peligro) | Ejecuta `QApplication.quit()`, cierra la app. |

Navegación por Teclado
- `Tab`: Módulo → Usuario → Contraseña → Iniciar Sesión → Cancelar
- `Enter` en campo Usuario: mueve foco a Contraseña.
- `Enter` en campo Contraseña: dispara acción de login.

Recuperar Contraseña

Reservado para futuras versiones.

6. Dashboard Principal
Administrador
Indicadores
Órdenes Activas

Solicitudes Pendientes

Solicitudes Procesando

Referencias Generadas

Referencias Expiradas

Usuarios Conectados

Sesiones Activas
Diseño Conceptual
+------------------------------------------------+

 ÓRDENES ACTIVAS

 15

 REFERENCIAS GENERADAS

 12,540

 REFERENCIAS EXPIRADAS

 150

 SESIONES ACTIVAS

 6

+------------------------------------------------+
Gráficas
Producción Diaria
Día vs Referencias
Producción por Empresa
RFC vs Referencias
Producción por Concepto
Análisis
Aviso
CLG
7. Módulo Órdenes
Objetivo

Administrar requerimientos masivos.

Pantalla
ÓRDENES

Folio

Fecha

Estado

Solicitadas

Generadas

Acciones
Acciones
Nueva Orden
Consultar
Cerrar
Cancelar
8. Nueva Orden
Objetivo

Crear e importar requerimientos masivos en el sistema.

Métodos de Captura

### Opción 1: Formulario de Captura Dinámico (En Pantalla - Primario)
Habilita la captura rápida en vivo agregando renglones en una grilla interactiva.

Componentes del Formulario:
*   **Descripción de la Orden**: Input de texto general.
*   **Tabla de Captura Dinámica (Grilla)**:
    *   Columnas:
        1.  `RFC` (Dropdown filtrable conectado a CAT_RFC)
        2.  `Concepto` (Dropdown conectado a CAT_CONCEPTO)
        3.  `Delegación` (Dropdown conectado a CAT_DELEGACION)
        4.  `Cantidad` (Input numérico)
        5.  `Acciones` (Botón "Eliminar Renglón")
*   **Controles**:
    *   `[ + Agregar Renglón ]` (Añade una nueva fila vacía a la grilla)
    *   `[ Guardar Orden ]` (Registra la orden completa y genera grupos/solicitudes de forma transaccional)

### Opción 2: Importar desde Excel (Archivo - Secundario)
Carga masiva para configuraciones muy grandes de referencias mediante archivo externo.

Componentes:
*   **Descripción de la Orden**: Input de texto general.
*   **Archivo Excel**: Botón `[Seleccionar Archivo .xlsx]`.
*   **Controles**:
    *   `[ Importar Excel ]`

Plantilla Oficial del Excel:
*   Columnas: RFC, Concepto, Delegación, Cantidad

Resultado de Generación (Ambas Opciones)

SAR generará de forma automática:
*   Órdenes
*   Grupos
*   Solicitudes (con pre-asignación de rangos)
*   Índices de Producción
9. Detalle de Orden
Información General
Folio

Descripción

Fecha

Estado
Resumen
Solicitadas

Generadas

Expiradas

Pendientes
Grid
RFC

Concepto

Delegación

Cantidad

Generadas

Estado
10. Asignación de Solicitudes
Pantalla Crítica

Esta es la pantalla más importante del sistema.

Grid
RFC

Concepto

Delegación

Cantidad

Usuario Asignado

Estado
Acciones
Asignar
[Usuario ▼]
Reasignar
Guardar

10.1 Asignación de Referencias y Facturas
Objetivo

Permitir al Administrador o usuarios con acceso asignar referencias en estado FACTURADA (con su respectiva factura XML/PDF descargada) a los colaboradores finales, tanto de forma individual como masiva.

Filtros de Búsqueda
*   **RFC** (Dropdown filtrable conectado a CAT_RFC - Requerido)
*   **Concepto** (Dropdown conectado a CAT_CONCEPTO - Requerido)
*   **Delegación** (Dropdown conectado a CAT_DELEGACION - Opcional)

Grid de Referencias Facturadas
Muestra las referencias que cumplen con los filtros y cuyo estado actual es FACTURADA.
*   `[Seleccionar Checkbox]` (Columna para selección múltiple)
*   `Consecutivo`
*   `Referencia Portal`
*   `Importe`
*   `Folio Factura`
*   `Delegación`

Flujos de Asignación

### Opción A: Asignación Individual
1. El usuario localiza la referencia deseada en el Grid.
2. Hace clic en el botón `[Asignar]` en la columna de Acciones de dicha fila.
3. Se despliega un panel lateral o modal para seleccionar:
   *   `Usuario Destino` (Colaborador)
   *   `Tipo Asignación` (Física / Digital)
   *   `Observaciones` (Texto libre)
4. Presiona `[Confirmar Asignación]`. La referencia cambia a `ASIGNADA` y se crea su registro en la tabla `ASIGNACION`.

### Opción B: Asignación Masiva
1. El usuario utiliza la casilla "Seleccionar Todos" o marca individualmente varias referencias en el Grid.
2. En la sección superior del panel de control de asignación masiva, completa los campos:
   *   `Usuario Destino` (Colaborador)
   *   `Tipo Asignación` (Física / Digital)
   *   `Observaciones` (Texto común para todo el lote)
3. Hace clic en el botón `[Asignar Selección Masiva]`.
4. El sistema actualiza en una sola transacción todas las referencias seleccionadas al estado `ASIGNADA` y crea sus registros correspondientes en la tabla `ASIGNACION`.

11. Mis Solicitudes
Usuario Operativo

Visualiza únicamente trabajo asignado. Por defecto, se excluyen las solicitudes con estado COMPLETADA, COMPLETADO o CANCELADA para mantener limpio el panel de trabajo activo.

Filtros de Búsqueda
*   **Mostrar completadas y canceladas**: `CustomCheckBox` atómico con borde interactivo y fondo transparente ubicado a un lado del botón Actualizar que permite alternar la visualización de todo el historial.

Grid de Solicitudes Asignadas
Muestra la lista de solicitudes asignadas al operador actual.
*   `ID Solicitud`
*   `Folio Orden`
*   `RFC`
*   `Razón Social`
*   `Concepto`
*   `Solicitadas`
*   `Generadas`
*   `Estado`

Interacciones y Acciones
*   **Doble Clic sobre fila**: Carga automáticamente el contexto de la solicitud seleccionada para su ejecución (bloqueado de forma segura mientras el Bot esté en proceso).
*   **Botón [Actualizar]**: Actualiza la consulta en base de datos en tiempo real considerando la configuración del checkbox.
*   **Bloqueo en Ejecución**: Al iniciar la secuencia RPA, se desactivan automáticamente el checkbox de filtrado, la tabla (incluyendo doble clic), el botón de cargar solicitud y la selección de ruta de descargas para evitar conflictos de concurrencia.
12. Procesamiento en Vivo
Objetivo

Visualizar ejecución del bot.

Información
RFC

Concepto

Delegación

Estado
Progreso
450 / 1000
Última Referencia
000450
Tiempo
00:15:20
Botones
[Pausar]

[Detener]
13. Módulo Referencias
Objetivo

Consultar producción.

Filtros
RFC

Concepto

Delegación

Estado

Fecha
Grid
Consecutivo

Referencia

Importe

Fecha Generación

Vigencia

Estado
Estados
GENERADA

AUTORIZADA

RECHAZADA

EXPIRADA
14. Detalle de Referencia
Información
Referencia

Consecutivo

RFC

Concepto

Delegación

Importe

Vigencia

Estado
PDF
[Ver PDF]
Auditoría
Fecha Creación

Usuario

Sesión
15. Módulo RFC
Objetivo

Administrar contribuyentes.

Grid
RFC

Razón Social

Código Postal

Activo
Información Completa
RFC

Razón Social

Calle

No Exterior

No Interior

Colonia

Código Postal

Localidad

Municipio

Estado
Acciones
Nuevo
Editar
Desactivar
16. Catálogo Conceptos
Grid
Concepto

Descripción

Activo
Ejemplos Iniciales
Análisis y Calificación

Aviso Preventivo

CLG
17. Catálogo Delegaciones
Grid
Delegación

Municipio

Activo
Ejemplos Iniciales
Cancún

Playa del Carmen

Chetumal
18. Catálogo Municipios
Grid
Municipio

Activo
Ejemplos
Benito Juárez

Solidaridad

Othón P. Blanco

Tulum
19. Usuarios
Grid
Usuario

Nombre

Rol

Activo
Roles
Administrador

Operador
20. Sesiones Activas
Objetivo

Monitorear operación.

Grid
Usuario

Equipo

Versión

Inicio Sesión

Último Heartbeat

Estado
Acciones
Finalizar Sesión
Ver Actividad
21. Auditoría
Objetivo

Trazabilidad total.

Filtros
Fecha

Usuario

Entidad

Acción
Grid
Fecha

Usuario

Acción

Descripción
22. Dashboard Operativo
Producción
Referencias Hoy

Referencias Mes

Promedio Diario
Productividad
Referencias por Usuario

Tiempo Promedio por Referencia

Tiempo Promedio por Solicitud
Calidad
Errores

Reintentos

Expiradas
23. Dashboard Ejecutivo
Indicadores Estratégicos
Referencias Generadas

Referencias Autorizadas

Referencias Rechazadas

Referencias Expiradas
Tendencias
Producción Mensual

Producción por Empresa

Producción por Concepto
24. Configuración
Parámetros Generales
Heartbeat
60 segundos
Ruta PDF
\\Servidor\Referencias
Tamaño de Lote
299
Reintentos Automáticos
3
25. Decisiones UI/UX Congeladas
UX-001

Dashboard único para Administrador.

UX-002

Bandeja de trabajo individual para Operadores.

UX-003

Asignación manual de solicitudes.

UX-004

Monitoreo en tiempo real de sesiones.

UX-005

Consulta centralizada de referencias.

UX-006

Trazabilidad completa desde Orden → Solicitud → Referencia.

---

## 26. Control de Inventario y Asignación de Derechos (Fase B)

### 26.1 Visor de Inventario con Filas Ancladas (Pinned Selected Rows)
* **Cuadrícula Paginada Asíncrona**: Carga eficiente mediante `InventoryLoadWorker` en segundo plano con límites seleccionables (50, 100, 200 por página) y filtros dinámicos por Estado (`Disponible`, `Asignada`, `Reservada`), Concepto, Empresa y búsqueda por texto.
* **Selección Múltiple Persistente**: La selección de derechos en memoria (`selected_ref_map`) se conserva intacta a través de cambios de filtros, páginas o búsquedas.
* **Anclaje Superior de Filas Seleccionadas**: Todas las referencias marcadas por el usuario se posicionan y fijan automáticamente en las filas superiores de la tabla (`visible_table_data`), resaltadas con un fondo suave distintivo (`#EFF6FF`). Esto garantiza que el usuario nunca pierda de vista su carrito/cola de asignación al navegar o cambiar filtros.
* **Bloqueo de Derechos Asignados**: Los derechos en estado `ASIGNADA` tienen su checkbox permanentemente deshabilitado y bloqueado con tooltip explicativo. El doble clic en derechos asignados está restringido.
* **Barra de Acciones Dinámica**:
  - **`Asignar Seleccionados ({N})`**: Botón principal que se activa con $\ge 1$ derechos seleccionados y abre el asistente secuencial de asignación.
  - **`Limpiar Selección`**: Botón auxiliar para desmarcar y desanclar todas las filas acumuladas en un solo clic.
  - **Badge de Conteo**: Indicador visual dinámico con el total de derechos seleccionados.

### 26.2 Formulario "Asignar Derechos" (Manual / Individual)
* **Diferenciación de Destino**:
  - **`COLABORADOR`**: Muestra exclusivamente los campos de selección de colaborador y observaciones (para trámites y gestiones externas sin desarrollo ni cliente).
  - **`NOTARIA`**: Habilita la captura completa de Notaría, Cliente, Desarrollo, Coordenadas físicas, Folio/Crédito/PA y fechas notariales/RPP.

### 26.3 Asignación Masiva por Lotes
* Plantilla estándar descargable de **19 columnas** (`Plantilla_Control_Inventario.xlsx`) sin delegación redundante.
* Modos de Operación con exclusión mutua:
  1. **Asignación Directa** (Por defecto, obligatoriedad de ubicación física y cliente).
  2. **Reservar Derechos** (Apartado temporal de referencias, omite ubicación física).
  3. **Completar Lote Reservado** (Consolida apartados previos en `RESERVADA` hacia `ASIGNADA` con cliente y vivienda).

### 26.4 Asignación Manual con Wizard Secuencial y Borradores
* **Estructura Responsiva en 3 Niveles (Soporte 1366x768)**:
  1. **Cabecera Fija**: Banner de referencia, controles del paginador secuencial (`◀ Anterior` / `Siguiente ▶`), checkbox de replicación (`chk_replicar`) y selector de tipo de destino (`NOTARIA` / `COLABORADOR`).
  2. **Cuerpo Central Desplazable (`QScrollArea`)**: Contenedores dinámicos con scroll suave e integrado visualmente al tema para visualizar y editar todos los campos notariales, ubicación física, clientes y fechas sin importar la resolución o escala DPI.
  3. **Pie Fijo Pinned**: Botones **[Cancelar]** y **[Guardar]** anclados permanentemente en la parte inferior, garantizando accesibilidad y confirmación visual inmediata en todo momento.
* **Paginador / Wizard Secuencial**: Navegación interactiva por derecho (`Derecho X de N`) con controles `◀ Anterior` / `Siguiente ▶` y banner informativo enriquecido con alias de concepto (`CLG`, `AVISO`, etc.), delegación (`CAN`, `PLA`, etc.) y empresa.
* **Borradores Independientes**: Cada partida seleccionada mantiene su propio borrador en memoria (`_derechos_data`) con validación secuencial previa a la persistencia.
* **Opción de Replicación**: Checkbox opcional (`chk_replicar`) para replicar datos notariales, fechas u observaciones capturadas a las siguientes partidas del lote.
* **Búsqueda Predictiva Multi-criterio**: Detección inteligente con debounce de 350 ms capaz de resolver inmuebles por:
  - Número de Crédito Titular
  - P.A. (Paquete)
  - Folio Electrónico
  - Coordenadas tradicionales (Desarrollo + Mz + Lote + Edif + Viv)
* **Guardado y Confirmación**: Botón de acción **`Guardar`** con cuadro de diálogo de confirmación de seguridad antes de procesar el lote en base de datos.

### 26.5 Detalle de Asignación y Generación de Documentos (PDF y Excel)
* **Exportación Excel**: Generación de reportes tabulares consolidados con métricas de asignación.
* **Exportación de PDFs Unificados (`PdfWorker`)**: Estándar de nomenclatura con **prefijo consecutivo de 3 dígitos** (`{consec}_{...}.pdf`) para ordenamiento cronológico natural:
  - **`ASIGNADA`**: `{consec}_{cliente}_{concepto}.pdf` (Ej: `001_JUAN_PEREZ_Aviso.pdf`)
  - **`RESERVADA` (Notaría)**: `{consec}_{referencia}_{notaria}_{concepto}_{deleg}.pdf` (Ej: `001_1020304050_Not4_Aviso_CUN.pdf`)
  - **`COLABORADOR`**: `{consec}_{referencia}_{concepto}_{deleg}.pdf` (Ej: `001_1020304050_Aviso_CUN.pdf`)

---

## 27. Sistema de Diseño Atómico, Temas y Badges de Estado

### 27.1 Normalización del Box Model (Simetría 36px)
* Todos los controles de entrada (`QLineEdit`, `CustomComboBox`, `QDateEdit`, `QSpinBox`) y botones de acción en grillas interactivas están normalizados a una altura exterior uniforme de **36px** (`min-height: 28px; max-height: 28px; padding: 3px; border: 1px solid;`).
* En grillas y formularios, se aplica alineación vertical centrada (`Qt.AlignVCenter`) para garantizar que todos los controles compartan la misma línea de base y cotas visuales (`y`, `h`).

### 27.2 Variantes de Badges de Estado (`StatusBadge`)
Los estados operativos del sistema se diferencian semántica y cromáticamente mediante propiedades dinámicas declarativas (`badge_variant`):

| Estado del Sistema | Variante | Ícono | Modo Claro (Fondo / Texto) | Modo Oscuro (Fondo / Texto) |
| :--- | :--- | :---: | :---: | :---: |
| **`ASIGNADA`** | `assigned` | 🕒 Reloj | `#EEF2FF` / `#6366F1` (Índigo) | `rgba(99, 102, 241, 0.22)` / `#818CF8` |
| **`PENDIENTE_AUTORIZACION`** | `warning` | 🕒 Reloj | `#FEF3C7` / `#D97706` (Ámbar) | `rgba(217, 119, 6, 0.22)` / `#FBBF24` |
| **`RESERVADA`** | `reserved` | 🕒 Reloj | `#CCFBF1` / `#0D9488` (Teal) | `rgba(13, 148, 136, 0.22)` / `#2DD4BF` |
| **`AUTORIZADA` / `DISPONIBLE`** | `success` | ✔️ Check | `#DCFCE7` / `#16A34A` (Verde) | `rgba(22, 163, 74, 0.20)` / `#4ADE80` |
| **`GENERADA` / `ABIERTA`** | `accent` | 🕒 Reloj | `#DBEAFE` / `#2563EB` (Azul) | `rgba(37, 99, 235, 0.22)` / `#60A5FA` |
| **`RECHAZADA` / `ERROR`** | `error` | ⚠️ Alerta | `#FEE2E2` / `#EF4444` (Rojo) | `rgba(239, 68, 68, 0.20)` / `#F87171` |
| **`SUSTITUIDO` / `BORRADOR`** | `neutral` | 🕒 Reloj | `#F1F5F9` / `#64748B` (Gris) | `rgba(100, 116, 139, 0.20)` / `#94A3B8` |

### 27.3 Controles de Entrada Interactivos (`QSpinBox`)
* Botones de incremento y decremento configurados con `subcontrol-origin: padding` para preservar intacto el contorno exterior perimetral.
* Vectores SVG dedicados (`chevron_up.svg`, `chevron_down.svg`, `chevron_up_dark.svg`, `chevron_down_dark.svg`) con retroalimentación en `:hover` para temas Claro y Oscuro.

---

## 28. Módulos Adicionales y Servicios Centralizados

### 28.1 Módulo R2F-Cancún (`r2f_control_view.py`)
* Control de carga masiva de lotes de folios electrónicos y pases a caja para la Tesorería de Cancún.
* Visualización en tiempo real del ciclo de procesamiento: Folio → Recibo Oficial → Factura SATQ Timbrada.
* Integración con bot scraper autónomo para consulta y descarga de recibos PDF y extracción de metadatos catastrales (`SM`, `MZ`, `Lote`).

### 28.2 Módulo de Control de Servidor API REST (`api_server_view.py`)
* Panel de administración para el servidor LAN FastAPI.
* Monitoreo en vivo de estado (`Activo` / `Detenido`), puerto de red (8000), consumo de endpoints, métricas de latencia y visor de logs en tiempo real.


