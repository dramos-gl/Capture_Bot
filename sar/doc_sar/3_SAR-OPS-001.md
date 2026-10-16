# SAR-OPS-001: Modelo Operativo y Procesos
**Categoría:** Operación y Negocio  
**Versión:** 1.1  
**Estado:** Baseline Congelada  
**Metodología:** Business-First Architecture (BFA)  
Dependencias:
•	SAR-BLUEPRINT-001 v1.3
•	SAR-DAT-001 v1.0
________________________________________
1. Objetivo
Definir la operación completa del Sistema de Administración de Referencias (SAR), estableciendo la forma en que los usuarios interactúan con el sistema, cómo se distribuye el trabajo y cómo se ejecuta la automatización de generación de referencias mediante Tributanet.
________________________________________
2. Principios Operativos
OP-001
El Usuario es el actor principal del sistema.
OP-002
Toda actividad deberá estar asociada a un usuario autenticado.
OP-003
La Sesión Activa representa una instancia operativa temporal.
OP-004
La Referencia es la unidad principal de producción.
OP-005
Toda operación deberá quedar auditada.
OP-006
El sistema deberá soportar procesamiento concurrente.
OP-007
La asignación de trabajo será controlada por el Administrador.
________________________________________
3. Actores
Administrador
Responsable de:
•	Crear órdenes de generación.
•	Importar solicitudes.
•	Asignar solicitudes.
•	Reasignar solicitudes.
•	Monitorear producción.
•	Consultar métricas.
•	Gestionar catálogos.
________________________________________
Usuario Operativo
Responsable de:
•	Iniciar sesión.
•	Consultar bandeja de trabajo.
•	Ejecutar solicitudes asignadas.
•	Supervisar ejecución.
•	Reportar incidencias.
________________________________________
Sistema SAR
Responsable de:
•	Controlar estados.
•	Mantener trazabilidad.
•	Gestionar consecutivos.
•	Registrar referencias.
•	Auditar operaciones.
•	Monitorear sesiones activas.
________________________________________
Tributanet
Sistema externo responsable de:
•	Generar referencias.
•	Generar boletas PDF.
•	Asignar vigencias.
________________________________________
4. Arquitectura Operativa
Administrador
      │
      ▼
Orden de Generación
      │
      ▼
Solicitudes
      │
      ▼
Asignación Manual
      │
 ┌────┼────┐
 ▼    ▼    ▼
Usuario Usuario Usuario
Sesión Sesión Sesión
 ▼      ▼      ▼
Playwright
 ▼
Tributanet
 ▼
Referencias
________________________________________
5. Gestión de Usuarios y Sesiones
Definición
Usuario
Representa a una persona dentro de la organización.
Sesión Activa
Representa una instancia operativa temporal asociada a un Usuario.
________________________________________
Regla Operativa RO-001
Un usuario podrá iniciar sesión desde múltiples equipos simultáneamente.
________________________________________
Regla Operativa RO-002
La concurrencia crítica se controla a nivel de SOLICITUD, no a nivel de usuario.
•	Múltiples instancias del mismo usuario pueden coexistir procesando diferentes solicitudes.
•	Cada sesión activa reportará su propio heartbeat de forma independiente.
________________________________________
Beneficios
•	Flexibilidad operativa para operadores con múltiples terminales de ejecución.
•	Protección contra fallos distribuidos.
•	Monitoreo detallado de rendimiento por equipo físico.
________________________________________
6. Ciclo de Vida de una Orden
Estados:
•	BORRADOR
•	ABIERTA
•	PROCESANDO
•	FINALIZADA
•	CANCELADA
Flujo:
BORRADOR → ABIERTA → PROCESANDO → FINALIZADA
________________________________________
6.1 Tipos de Órdenes y Modos Operativos
Las órdenes se clasifican en cinco tipos, definiendo el comportamiento del sistema y la automatización:

•	ESTANDAR: Órdenes de cobro y subsidios procesadas por lotes discretos (Ej. ORD-SUB-YYYYMMDD, con sufijo incremental -2, -3 si hay múltiples el mismo día). Cada referencia equivale a 1 acto.
•	PAGADA: Orden anual para Derechos Pagados (Ej. ORD-PAGADA-YYYY). Reutiliza el folio padre anual para acumular partidas a lo largo de todo el ejercicio fiscal.
•	CANCELACION: Orden anual para cancelaciones hipotecarias y de avisos (Ej. ORD-CLX-AV-YYYY). Las referencias se agrupan sobre el mismo folio padre anual.
•	FOJAS: Orden anual para Derechos de Fojas (Ej. ORD-FOJAS-YYYY). Requiere que el usuario defina la `cantidad_actos` durante la captura, lo cual modifica el multiplicador en el portal.
•	TESTIMONIO: Orden anual para Expedición de Testimonios (Ej. ORD-TESTIMONIO-YYYY). Genera las referencias en un grupo y portal distinto (Grupo=71).
________________________________________
6.2 Ciclo de Vida y Reglas Operativas de una Orden (orden_generacion)

A. Órdenes ESTANDAR (Lotes Discretos):
•	ABIERTA: Orden creada por el operador en fase de captura y edición de partidas.
•	COMPLETADA: El Bot SAR concluyó la generación de todas las líneas de captura y referencias bancarias del lote (listas para validación directiva).
•	AUTORIZADA: La dirección aprobó las referencias del lote.
•	RECHAZADA: La dirección rechazó las referencias del lote.
•	CANCELADA: La orden fue anulada administrativamente antes de generar derechos.
Flujo: ABIERTA → COMPLETADA → AUTORIZADA / RECHAZADA (o CANCELADA).

B. Órdenes Anuales (PAGADA, CANCELACION, FOJAS, TESTIMONIO):
•	ABIERTA: La cabecera permanece abierta de manera continua durante los 365 días del año calendario para permitir la inyección acumulativa de trámites esporádicos.
•	CERRADA: Transición ejecutada automáticamente al inicio del siguiente ejercicio fiscal al crearse la nueva orden anual.
*(Nota: Las solicitudes y referencias hijas de una orden anual fluyen normalmente en su ciclo de vida individual: PENDIENTE → COMPLETADA → PENDIENTE_AUTORIZACION → AUTORIZADA / RECHAZADA).*

C. Matriz de Acciones de Cabecera (Módulo Órdenes Capturadas):
•	Editar Orden: Permitido para órdenes en estado ABIERTA. En partidas con derechos ya generados (`cantidad_generada > 0`), no se permite reducir la cantidad ni eliminar la partida.
•	Autorizar / Rechazar en Bloque: Permitido exclusivamente para órdenes ESTANDAR completas (`total_pendientes == total_solicitadas`). Para órdenes Anuales, está bloqueado en bloque; el usuario debe ingresar con doble clic para autorizar o rechazar partidas individuales.
•	Cancelar Orden: Permitido únicamente si la orden no cuenta con referencias generadas (`generadas == 0`). Las órdenes Anuales no pueden cancelarse en bloque por ser contenedores del ejercicio fiscal.
________________________________________
7. Ciclo de Vida de un Grupo
Estados:
•	PENDIENTE
•	GENERANDO
•	COMPLETADO
•	CERRADO
________________________________________
8. Ciclo de Vida y Reglas de Solicitudes (sar_produccion.solicitud)
Estados:
•	PENDIENTE
•	ASIGNADA
•	PROCESANDO
•	COMPLETADA
•	ERROR
•	CANCELADA
Flujo: PENDIENTE → ASIGNADA → PROCESANDO → COMPLETADA

Reglas de Negocio para Solicitudes:
•	Edición de Cantidad: Únicamente permitida en estado PENDIENTE con cero referencias generadas. Protege los rangos de consecutivos precalculados y evita condiciones de carrera con el Bot SAR.
•	Cancelación de Solicitud: Únicamente permitida en estado PENDIENTE con cero referencias generadas. Descuenta automáticamente la cantidad del grupo padre y asigna formalmente el estado `CANCELADA` (`estado_id = 36`). Es la vía oficial para anular trámites específicos dentro de órdenes anuales sin afectar el folio contenedor.
________________________________________
9. Asignación de Solicitudes
Estrategia Oficial
La asignación será realizada por el Administrador.
________________________________________
Ejemplo
EMPRESA1 | ANALISIS | CANCUN | 1000
Asignado a:
Juan Pérez
________________________________________
EMPRESA1 | ANALISIS | PLAYA | 1000
Asignado a:
Pedro Gómez
________________________________________
10. Bandeja de Trabajo (Módulo Solicitudes)
Cada usuario visualizará en la tabla de solicitudes:
•	ID Solicitud, Grupo, Folio Orden.
•	Empresa (con formato Alias Comercial + RFC entre paréntesis).
•	Concepto, Delegación, Solicitadas, Generadas, Facturadas, Estado y Asignado a.

Reglas Operativas de Filtrado y UX:
•	**Regla de Selección de Orden por Defecto**: Al acceder a la bandeja, el sistema preselecciona automáticamente la **orden más reciente** que contenga solicitudes en estado `PENDIENTE` o `COMPLETADA`. Si ninguna orden activa tiene solicitudes en dicho estado, selecciona la orden más reciente activa del catálogo.
•	**Filtro de Estado**: Por defecto se aplica `'Todas'`, omitiendo estados combinados y filtrando en memoria con ultra-baja latencia sobre la(s) orden(es) activa(s).
•	**Botón de Filtro de Órdenes**: Permite selección granular múltiple o conmutación hacia "Todas las órdenes".

Ejemplo de Registro:
EMPRESA1 (RFC123456) | ANALISIS | CANCUN | 1000 Solicitadas
[INICIAR]
________________________________________
11. Inicio de Procesamiento
Cuando el usuario selecciona “Iniciar”:
SAR ejecutará:
1.	Validar sesión.
2.	Bloquear solicitud.
3.	Registrar auditoría.
4.	Iniciar Playwright.
5.	Actualizar estado a PROCESANDO.
________________________________________
12. Automatización Tributanet (Bot Face A)
Secuencia Estándar:
1.	Acceso al portal principal.
2.	Selección de municipio.
3.	Captura RFC.
4.	Apertura de formulario.
5.	Validación de datos fiscales.
6.	Selección de Delegación.
7.	Selección de Concepto.
8.	Generación de referencia.
9.	Descarga PDF.
10.	Registro en SAR.
11.	Continuar siguiente referencia.

Excepciones Operativas:
•	Flujo Fojas: En el paso 7, el sistema inyecta automáticamente la `cantidad_actos` en el campo multiplicador de Tributanet (utilizando selectores estrictos tipo `[type='number']` para evitar colisiones con campos de lectura).
•	Flujo Testimonios: 
    - El paso 1 navega a una URL específica de Grupo Especial (Grupo=71).
    - El paso 6 (Delegación) se omite automáticamente al no existir en dicho portal.
    - El paso 7 (Concepto) se selecciona procesando el `codigo_portal` mediante Expresiones Regulares (extrayendo el prefijo numérico) para blindar el bot contra caracteres especiales y discrepancias de codificación.
________________________________________
13. Control de Consecutivos
Regla Operativa RO-010
Los consecutivos pertenecen al Grupo de Referencias.
Definición:
RFC + CONCEPTO
________________________________________
Ejemplo:
EMPRESA1 ANALISIS
1 - 2000
________________________________________
EMPRESA1 AVISO
1 - 3000
________________________________________
Restricción:
No podrán existir dos referencias con el mismo:
•	GRUPO_ID
•	CONSECUTIVO_GRUPO
________________________________________
14. Recuperación ante Fallos
Falla de Playwright
Estado:
ERROR
________________________________________
Falla de Internet
Estado:
PAUSADA
________________________________________
Cierre inesperado
Al reiniciar:
SAR deberá recuperar el último punto procesado.
________________________________________
15. Heartbeat
Cada sesión enviará señal periódica.
Frecuencia inicial:
60 segundos
________________________________________
Sin Heartbeat:
Estado:
INACTIVA
________________________________________
16. Monitoreo Operativo
Dashboard del Administrador:
•	Usuarios conectados.
•	Sesiones activas.
•	Solicitudes pendientes.
•	Solicitudes procesando.
•	Solicitudes completadas.
•	Solicitudes con error.
________________________________________
17. Métricas Operativas
Producción
•	Referencias generadas por día.
•	Referencias por RFC.
•	Referencias por concepto.
•	Referencias por delegación.
________________________________________
Productividad
•	Referencias por usuario.
•	Tiempo promedio por referencia.
•	Tiempo promedio por solicitud.
________________________________________
18. Recuperación Operativa
Regla RO-020
Si una sesión desaparece:
La solicitud permanecerá asignada.
________________________________________
El Administrador podrá:
•	Reasignar.
•	Reanudar.
•	Cancelar.
________________________________________
19. Decisiones Arquitectónicas Congeladas
DA-001
Usuario = Actor Empresarial
________________________________________
DA-002
Sesión Activa = Actor Operativo
________________________________________
DA-003
Múltiples sesiones activas simultáneas permitidas por usuario (control a nivel de solicitud).
________________________________________
DA-004
Asignación manual de solicitudes.
________________________________________
DA-005
Procesamiento distribuido mediante usuarios operativos.
________________________________________
20. Estado del Proyecto
Documento | Nombre Formal | Categoría | Estado
--- | --- | --- | ---
SAR-BLUEPRINT-001 | Blueprint Empresarial SAR | Arquitectura Empresarial | Congelado
SAR-DAT-001 | Modelo de Datos de Negocio | Análisis de Datos | Congelado
SAR-OPS-001 | Modelo Operativo y Procesos | Operación y Negocio | Congelado
SAR-UIX-001 | Especificación UX/UI | Experiencia de Usuario | Pendiente
SAR-TEC-001 | Arquitectura Técnica | Arquitectura de Solución | Pendiente
SAR-DEV-001 | Guía de Desarrollo y Estándares | Ingeniería de Software | Pendiente
SAR-SEC-001 | Arquitectura de Seguridad y Auditoría | Seguridad | Pendiente
SAR-DB-001 | Diseño Físico de Base de Datos | Ingeniería de Datos | Pendiente
________________________________________
Próximo Documento
SAR-UIX-001
Diseño Funcional de Pantallas.
