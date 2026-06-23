SAR-SEC-001
Arquitectura de Seguridad y Auditoría
Sistema de Administración de Referencias (SAR)

Documento: SAR-SEC-001
Versión: 1.0
Estado: CONGELADO
Metodología: Business First Architecture (BFA)

1. Objetivo

Definir la arquitectura de seguridad, control de acceso, auditoría y trazabilidad del Sistema de Administración de Referencias (SAR).

El objetivo principal es garantizar:

Integridad
Trazabilidad
Disponibilidad
No repudio
Recuperación operativa
2. Principios de Seguridad
SEC-001

Toda operación debe estar asociada a un usuario autenticado.

SEC-002

Toda acción relevante debe quedar auditada.

SEC-003

Ningún usuario tendrá acceso directo a PostgreSQL.

Acceso exclusivamente mediante:

SAR Desktop
      ↓
FastAPI
      ↓
PostgreSQL
SEC-004

Las referencias generadas nunca podrán eliminarse físicamente.

SEC-005

Toda modificación crítica deberá conservar historial.

3. Modelo de Autenticación
Método Oficial
Usuario
+
Contraseña
Futura Evolución

Preparar compatibilidad para:

LDAP
Active Directory
Azure AD
4. Gestión de Sesiones
Regla Oficial

Un usuario puede iniciar sesión desde múltiples equipos.

Motivo:

En SAR el recurso crítico es la:

SOLICITUD

No la sesión.

Ejemplo:

Juan

Equipo A
Equipo B
Equipo C

Permitido.

5. Identidad Operativa

Diferenciar:

USUARIO

de

SESIÓN ACTIVA

Usuario:

Persona

Sesión:

Instancia de trabajo

Ejemplo:

Usuario:
Juan Pérez

Sesiones:

PC-01

PC-02

Laptop
6. Roles Oficiales
Administrador

Control total.

Permisos:

Usuarios

Roles

Configuración

Órdenes

Solicitudes

Reportes

Auditoría
Supervisor

Control operativo.

Permisos:

Órdenes

Asignaciones

Monitoreo

Reportes
Operador

Producción.

Permisos:

Tomar solicitudes

Procesar solicitudes

Consultar historial propio
Consulta

Solo lectura.

Permisos:

Dashboards

Reportes
7. Matriz RBAC
Recurso	Admin	Supervisor	Operador	Consulta
Usuarios	Sí	No	No	No
Roles	Sí	No	No	No
Configuración	Sí	No	No	No
RFC	Sí	Sí	Lectura	Lectura
Órdenes	Sí	Sí	Lectura	Lectura
Solicitudes	Sí	Sí	Sí	Lectura
Referencias	Sí	Sí	Sí	Lectura
Dashboard	Sí	Sí	Sí	Sí
Auditoría	Sí	Sí	No	No
8. Seguridad de Contraseñas
Hash
Argon2

No almacenar:

Texto plano
MD5
SHA1
9. Seguridad de API
Token
JWT

Tiempo recomendado:

8 horas

Refresh:

24 horas
10. Auditoría Obligatoria

Toda acción deberá registrarse.

Eventos Auditables
Login
LOGIN
Logout
LOGOUT
Crear Orden
ORDEN_CREATE
Modificar Orden
ORDEN_UPDATE
Asignar Solicitud
SOLICITUD_ASSIGN
Generar Referencia
REFERENCIA_CREATE
Cambio Estado
REFERENCIA_STATUS
Reproceso
REFERENCIA_REPROCESS
11. No Repudio

Toda auditoría deberá almacenar:

Usuario

Equipo

IP

Fecha

Hora

Acción

Detalle

Ejemplo:

{
  "usuario":"jperez",
  "equipo":"PC-OPER-01",
  "accion":"REFERENCIA_CREATE",
  "referencia":"123456789",
  "fecha":"2026-07-01 14:32:10"
}
12. Auditoría de Producción
Tabla
auditoria_evento

Objetivo:

Qué hizo
Quién lo hizo
Cuándo lo hizo
Dónde lo hizo
13. Auditoría de Acceso
Tabla
auditoria_login

Registrar:

Inicio

Cierre

Sesión

IP

Equipo
14. Auditoría de Errores
Tabla
auditoria_error

Registrar:

Excepción

Stack Trace

Usuario

Módulo

Fecha
15. Seguridad de PDFs

Los PDFs representan evidencia operativa.

Política

Prohibido eliminar.

Estados permitidos:

Activo

Archivado
16. Integridad de Archivos

Cada PDF almacenará:

SHA256

Objetivo:

Detectar:

Corrupción

Manipulación

Sustitución
17. Recuperación Operativa
Checkpoints

Obligatorios.

Permiten continuar:

Solicitud
↓
Referencia 850
↓
Falla eléctrica
↓
Reanudar desde 851
18. Seguridad de Concurrencia

Problema:

5 usuarios
10 usuarios
20 usuarios

trabajando simultáneamente.

Solución:

SELECT ... FOR UPDATE

sobre:

grupo_referencia

Garantía:

Cero duplicados

en consecutivos.

19. Respaldo
Base de Datos

Diario.

PDFs

Diario.

Auditoría

Diaria.

Retención:

5 años
20. Monitoreo

Indicadores:

Usuarios Activos
Sesiones Activas
Solicitudes Procesándose
Referencias Generadas
Errores por Hora
21. Riesgos Identificados
R-001

Cambio de estructura Tributanet.

R-002

Bloqueo temporal portal.

R-003

Falla eléctrica.

R-004

Falla de red.

R-005

Manipulación de archivos.

R-006

Acceso indebido.

22. Controles Mitigantes
Riesgo	Mitigación
Duplicidad	FOR UPDATE
Manipulación PDF	SHA256
Falla eléctrica	Checkpoint
Usuario indebido	RBAC
Cambio portal	Versionado Bot
Eliminación accidental	Archivado
Decisiones Congeladas
SEC-001

RBAC obligatorio.

SEC-002

JWT obligatorio.

SEC-003

Argon2 obligatorio.

SEC-004

Auditoría obligatoria.

SEC-005

PDFs no eliminables.

SEC-006

Checkpoints obligatorios.

SEC-007

Múltiples sesiones por usuario permitidas.

SEC-008

Consecutivos protegidos mediante bloqueo transaccional.