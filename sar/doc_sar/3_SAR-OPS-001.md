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
7. Ciclo de Vida de un Grupo
Estados:
•	PENDIENTE
•	GENERANDO
•	COMPLETADO
•	CERRADO
________________________________________
8. Ciclo de Vida de una Solicitud
Estados:
•	PENDIENTE
•	ASIGNADA
•	PROCESANDO
•	COMPLETADA
•	ERROR
•	CANCELADA
Flujo:
PENDIENTE → ASIGNADA → PROCESANDO → COMPLETADA
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
10. Bandeja de Trabajo
Cada usuario visualizará únicamente:
•	Solicitudes asignadas.
•	Cantidad solicitada.
•	Cantidad generada.
•	Estado.
•	Progreso.
Ejemplo:
EMPRESA1 ANALISIS CANCUN 1000
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
12. Automatización Tributanet
Secuencia:
1.	Acceso al portal.
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
