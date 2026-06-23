SAR-TEC-001
Arquitectura Técnica
Sistema de Administración de Referencias (SAR)
Documento: SAR-TEC-001
Versión: 1.0
Estado: Baseline Inicial
Metodología: Business-First Architecture (BFA)
________________________________________
1. Objetivo
Definir la arquitectura técnica oficial para la implementación del Sistema de Administración de Referencias (SAR).
La arquitectura deberá garantizar:
•	Trazabilidad completa.
•	Escalabilidad controlada.
•	Operación distribuida.
•	Recuperación ante fallos.
•	Mantenimiento simplificado.
•	Integración con Tributanet mediante automatización web.
________________________________________
2. Principios Arquitectónicos
TEC-001
Business First.
La tecnología se adapta al negocio.
________________________________________
TEC-002
Monolito Modular.
Se evitarán microservicios en la versión inicial.
________________________________________
TEC-003
Base de datos centralizada.
La fuente única de verdad será la base de datos SAR.
________________________________________
TEC-004
Operación distribuida.
Cada usuario podrá ejecutar procesos desde su equipo.
________________________________________
TEC-005
Automatización desacoplada.
La automatización Playwright será independiente de la interfaz gráfica.
________________________________________
TEC-006
Trazabilidad total.
Toda operación deberá quedar registrada.
________________________________________
3. Arquitectura General
                USUARIOS

                     │

                     ▼

             APLICACIÓN SAR

                     │

         ┌───────────┼───────────┐

         ▼                       ▼

      API SAR              PLAYWRIGHT

         │                       │

         ▼                       ▼

     POSTGRESQL            TRIBUTANET

         │

         ▼

   REPOSITORIO PDF
________________________________________
4. Arquitectura Física
Servidor Central
Responsable de:
•	API SAR
•	Base de Datos
•	Repositorio PDF
•	Auditoría
•	Reportes
________________________________________
Equipos Operativos
Responsables de:
•	Interfaz SAR
•	Playwright
•	Procesamiento
________________________________________
5. Arquitectura Lógica
Módulo Seguridad
Responsable de:
•	Usuarios
•	Roles
•	Sesiones
•	Auditoría
________________________________________
Módulo Catálogos
Responsable de:
•	RFC
•	Conceptos
•	Delegaciones
•	Municipios
________________________________________
Módulo Producción
Responsable de:
•	Órdenes
•	Solicitudes
•	Referencias
________________________________________
Módulo Automatización
Responsable de:
•	Playwright
•	Descarga PDF
•	Recuperación
________________________________________
Módulo Reportes
Responsable de:
•	Dashboards
•	Indicadores
•	Exportaciones
________________________________________
6. Frontend
Tecnología Recomendada
Opción Oficial
React
+
TypeScript
+
Vite
________________________________________
Justificación
•	Alta mantenibilidad.
•	Interfaz moderna.
•	Escalable.
•	Amplio soporte comunitario.
________________________________________
7. Backend
Tecnología Recomendada
Python
+
FastAPI
________________________________________
Justificación
•	Ya existe experiencia interna.
•	Integración natural con Playwright.
•	Excelente rendimiento.
•	Documentación automática.
________________________________________
8. Automatización
Tecnología Oficial
Playwright
________________________________________
Razones
•	Más estable que Selenium.
•	Mejor manejo de sesiones.
•	Mejor manejo de descargas.
•	Mejor soporte para sitios modernos.
________________________________________
9. Base de Datos
Recomendación Oficial
PostgreSQL
________________________________________
Razones
•	Gratuito.
•	Robusto.
•	Transaccional.
•	Excelente concurrencia.
•	Escalable.
________________________________________
10. Evaluación SQL Anywhere
Estado
Aprobado únicamente como alternativa.
________________________________________
Ventajas
•	Administración sencilla.
•	Curva de aprendizaje baja.
________________________________________
Desventajas
•	Menor ecosistema.
•	Menor comunidad.
•	Dependencia comercial futura.
________________________________________
Decisión
PostgreSQL = Oficial

SQL Anywhere = Contingencia
________________________________________
11. Repositorio de PDFs
Estrategia
Los PDFs no deberán almacenarse dentro de la base de datos.
________________________________________
Ubicación
Servidor Central
________________________________________
Ejemplo
PDF/

 ├── 2026

 │    ├── EMPRESA_A

 │    ├── EMPRESA_B

 │    └── EMPRESA_C
________________________________________
12. Convención de Archivos
Formato:
REFERENCIA.pdf
Ejemplo:
123456789012.pdf
________________________________________
13. Concurrencia
Requisito
Soportar múltiples usuarios operando simultáneamente.
________________________________________
Estrategia
PostgreSQL gestionará:
•	Bloqueos.
•	Transacciones.
•	Secuencias.
________________________________________
14. Control de Consecutivos
Estrategia Oficial
Base de datos.
________________________________________
Nunca:
Variables en memoria

Archivos TXT

Excel
________________________________________
Mecanismo
NEXTVAL()
o secuencia equivalente.
________________________________________
15. Recuperación
Escenario
Falla eléctrica.
________________________________________
Requisito
La solicitud deberá continuar desde la última referencia confirmada.
________________________________________
Estrategia
Checkpoint automático.
________________________________________
16. Auditoría
Toda operación deberá registrar:
•	Fecha
•	Hora
•	Usuario
•	Sesión
•	Equipo
•	Acción
•	Entidad afectada
________________________________________
17. Seguridad
Autenticación
Usuario y contraseña.
________________________________________
Futuro
Integración Active Directory.
________________________________________
18. Roles
Administrador
Acceso total.
________________________________________
Operador
Procesamiento únicamente.
________________________________________
19. Respaldos
Base de Datos
Diario.
________________________________________
PDFs
Diario.
________________________________________
Auditoría
Diario.
________________________________________
20. Monitoreo
Indicadores:
•	Usuarios conectados.
•	Sesiones activas.
•	Solicitudes procesando.
•	Errores.
•	Producción diaria.
________________________________________
21. Decisiones Técnicas Congeladas
DT-001
Arquitectura Monolítica Modular.
________________________________________
DT-002
Backend Python + FastAPI.
________________________________________
DT-003
Frontend React + TypeScript.
________________________________________
DT-004
Automatización Playwright.
________________________________________
DT-005
Base de Datos PostgreSQL.
________________________________________
DT-006
Repositorio PDF en sistema de archivos.
________________________________________
DT-007
Operación distribuida mediante usuarios autenticados.
________________________________________
DT-008
Consecutivos administrados por base de datos.
________________________________________
22. Roadmap Técnico
Fase 1
Fundación
•	Base de datos.
•	Seguridad.
•	Catálogos.
________________________________________
Fase 2
Producción
•	Órdenes.
•	Solicitudes.
•	Referencias.
________________________________________
Fase 3
Automatización
•	Playwright.
•	Descargas.
•	Recuperación.
________________________________________
Fase 4
Reportes
•	Dashboard.
•	KPIs.
•	Exportaciones.
________________________________________
Estado del Proyecto
Documento	Estado
SAR-BLUEPRINT-001	Congelado
SAR-DAT-001	Congelado
SAR-OPS-001	Congelado
SAR-UIX-001	Congelado
SAR-TEC-001	Congelado
SAR-DEV-001	Pendiente
________________________________________
Próximo Documento
SAR-DEV-001
Plan Maestro de Construcción y Ejecución.
