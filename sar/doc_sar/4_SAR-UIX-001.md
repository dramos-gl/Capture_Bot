SAR-UIX-001
Diseño Funcional de Experiencia de Usuario (UI/UX)
Sistema de Administración de Referencias (SAR)

Documento: SAR-UIX-001
Versión: 1.0
Estado: Baseline Inicial
Metodología: Business-First Architecture (BFA)
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
LOGIN

│

▼

DASHBOARD

├── Órdenes
│
├── Solicitudes
│
├── Referencias
│
├── RFC
│
├── Conceptos
│
├── Delegaciones
│
├── Usuarios
│
├── Sesiones
│
├── Auditoría
│
├── Reportes
│
└── Configuración
5. Login
Objetivo

Autenticar usuarios.

Componentes
+----------------------------------+

          SAR

 Sistema Administración
      Referencias

 Usuario

 [________________]

 Contraseña

 [________________]

       [Entrar]

+----------------------------------+
Acciones
Entrar

Valida credenciales.

Recuperar Contraseña

Opcional para futuras versiones.

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

