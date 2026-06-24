# SAR-DEV-001: Guía de Desarrollo y Estándares
**Categoría:** Ingeniería de Software  
**Versión:** 1.0  
**Estado:** Baseline Inicial  
**Metodología:** Business-First Architecture (BFA)  
________________________________________
1. Objetivo
Definir el plan oficial de construcción del Sistema de Administración de Referencias (SAR), incluyendo:
•	Estrategia de desarrollo.
•	Estructura del proyecto.
•	Roadmap de implementación.
•	Entregables por fase.
•	Dependencias técnicas.
•	Criterios de aceptación.
________________________________________
2. Alcance de la Versión 1.0
La versión 1.0 incluye exclusivamente:
FASE A
Generación y administración de referencias.
Incluye:
•	Órdenes.
•	Solicitudes.
•	Referencias.
•	Automatización Tributanet.
•	Descarga PDF.
•	Catálogos.
•	Usuarios.
•	Sesiones.
•	Auditoría.
•	Dashboard operativo.
________________________________________
3. Tecnologías Congeladas
Cliente
Python 3.13
PySide6
________________________________________
Automatización
Playwright
________________________________________
Backend
FastAPI
________________________________________
ORM
SQLAlchemy 2.x
________________________________________
Migraciones
Alembic
________________________________________
Base de Datos
PostgreSQL
________________________________________
Reportes
Pandas
OpenPyXL
________________________________________
PDF
pypdf
________________________________________
4. Estructura General del Proyecto
SAR/

├── client/
│
├── server/
│
├── database/
│
├── automation/
│
├── reports/
│
├── docs/
│
├── tests/
│
└── deployment/
________________________________________
5. Cliente Desktop
client/

├── ui/
├── views/
├── dialogs/
├── widgets/
├── services/
├── models/
├── resources/
└── main.py
________________________________________
6. API Central
server/

├── api/
├── core/
├── security/
├── services/
├── repositories/
├── schemas/
├── models/
├── audit/
└── main.py
________________________________________
7. Automatización
automation/

├── playwright/
│
├── tributanet/
│
├── downloads/
│
├── checkpoints/
│
└── workers/
________________________________________
8. Base de Datos
database/

├── migrations/
├── ddl/
├── seed/
└── diagrams/
________________________________________
9. Fases de Construcción
FASE DEV-01
Fundación
________________________________________
Objetivo
Construir la base técnica.
________________________________________
Entregables
•	PostgreSQL.
•	FastAPI.
•	SQLAlchemy.
•	Alembic.
•	Seguridad.
•	Usuarios.
•	Roles.
•	Auditoría básica.
________________________________________
Criterio de aceptación
Login funcional.
________________________________________
FASE DEV-02
Catálogos
________________________________________
Entregables
•	RFC.
•	Municipios.
•	Delegaciones.
•	Conceptos.
________________________________________
Criterio de aceptación
ABM completo.
________________________________________
FASE DEV-03
Órdenes
________________________________________
Entregables
•	Crear Orden.
•	Importar Excel.
•	Generar Solicitudes.
•	Validaciones.
________________________________________
Criterio de aceptación
Carga masiva funcional.
________________________________________
FASE DEV-04
Solicitudes
________________________________________
Entregables
•	Asignación.
•	Reasignación.
•	Estados.
•	Bandeja de trabajo.
________________________________________
Criterio de aceptación
Flujo operativo completo.
________________________________________
FASE DEV-05
Referencias
________________________________________
Entregables
•	Generación de índices.
•	Consecutivos.
•	Registro de referencias.
•	Historial.
________________________________________
Criterio de aceptación
Integridad transaccional validada.
________________________________________
FASE DEV-06
Playwright
________________________________________
Entregables
•	Login Tributanet.
•	Consulta RFC.
•	Generación referencia.
•	Descarga PDF.
________________________________________
Criterio de aceptación
Generación automática exitosa.
________________________________________
FASE DEV-07
Procesamiento Distribuido
________________________________________
Entregables
•	Sesiones.
•	Heartbeat.
•	Recuperación.
•	Monitoreo.
________________________________________
Criterio de aceptación
Múltiples usuarios simultáneos.
________________________________________
FASE DEV-08
Dashboard
________________________________________
Entregables
•	KPIs.
•	Producción.
•	Errores.
•	Usuarios conectados.
________________________________________
Criterio de aceptación
Indicadores en tiempo real.
________________________________________
FASE DEV-09
Auditoría Completa
________________________________________
Entregables
•	Bitácora.
•	Cambios.
•	Trazabilidad.
________________________________________
Criterio de aceptación
Auditoría extremo a extremo.
________________________________________
FASE DEV-10
Estabilización
________________________________________
Entregables
•	Optimización.
•	Corrección de errores.
•	Hardening.
________________________________________
Criterio de aceptación
Release Candidate.
________________________________________
10. Estrategia de Desarrollo
Enfoque
Vertical Slice.
________________________________________
Cada módulo deberá construirse completo:
BD

API

UI

Pruebas
antes de pasar al siguiente.
________________________________________
11. Estrategia de Base de Datos
Todas las modificaciones deberán realizarse mediante:
Alembic
________________________________________
Prohibido:
Cambios manuales
en Producción
________________________________________
12. Estrategia de Código
Convenciones
PEP8
Type Hints
Docstrings
________________________________________
Cobertura mínima
70%
________________________________________
13. Estrategia de Pruebas
Unitarias
Servicios.
________________________________________
Integración
API + PostgreSQL.
________________________________________
Operativas
Playwright.
________________________________________
Aceptación
Casos de negocio.
________________________________________
14. Gestión de Configuración
Variables:
DATABASE_URL

PDF_PATH

HEARTBEAT_INTERVAL

PLAYWRIGHT_TIMEOUT
________________________________________
Archivo:
.env
________________________________________
15. Gestión de Errores
Clasificación:
Crítico
Detiene operación.
________________________________________
Medio
Permite continuar.
________________________________________
Informativo
Registro únicamente.
________________________________________
16. Estrategia de Versionamiento
v1.0.0
Release Inicial.
________________________________________
v1.1.0
Mejoras funcionales.
________________________________________
v2.0.0
Cambios estructurales.
________________________________________
17. Estrategia de Despliegue
Servidor
FastAPI
PostgreSQL
Repositorio PDF
________________________________________
Cliente
SAR Desktop
PySide6
Playwright
________________________________________
18. Riesgos Técnicos
RT-001
Cambios en Tributanet.
________________________________________
RT-002
Bloqueos del portal.
________________________________________
RT-003
Interrupciones de Internet.
________________________________________
RT-004
Fallas eléctricas.
________________________________________
RT-005
Corrupción de PDFs.
________________________________________
19. Mitigaciones
Checkpoints.
________________________________________
Reintentos automáticos.
________________________________________
Auditoría.
________________________________________
Recuperación de sesión.
________________________________________
Respaldo diario.
________________________________________
20. Criterio de Go-Live
SAR podrá liberarse cuando:
•	Todos los módulos estén terminados.
•	Auditoría validada.
•	Recuperación validada.
•	Procesamiento concurrente validado.
•	Generación de referencias validada.
•	Descarga PDF validada.
•	Dashboard operativo validado.
________________________________________
Estado Documental
Documento | Nombre Formal | Categoría | Estado
--- | --- | --- | ---
SAR-BLUEPRINT-001 | Blueprint Empresarial SAR | Arquitectura Empresarial | Congelado
SAR-DAT-001 | Modelo de Datos de Negocio | Análisis de Datos | Congelado
SAR-OPS-001 | Modelo Operativo y Procesos | Operación y Negocio | Congelado
SAR-UIX-001 | Especificación UX/UI | Experiencia de Usuario | Congelado
SAR-TEC-001 | Arquitectura Técnica | Arquitectura de Solución | Congelado
SAR-DEV-001 | Guía de Desarrollo y Estándares | Ingeniería de Software | Congelado
SAR-SEC-001 | Arquitectura de Seguridad y Auditoría | Seguridad | Congelado
SAR-DB-001 | Diseño Físico de Base de Datos | Ingeniería de Datos | Congelado
________________________________________
Próximo Artefacto
SAR-DB-001
Diseño Físico de Base de Datos
Incluye:
•	DDL PostgreSQL.
•	Índices.
•	Constraints.
•	Secuencias.
•	Relaciones.
•	Estrategia de concurrencia.
•	Auditoría física.
•	Modelo de rendimiento.
