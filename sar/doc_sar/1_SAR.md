SAR - Sistema de Administración de Referencias
Blueprint Empresarial v1.3 (Baseline Congelada)
Versión: 1.3
Estado: Congelada
Metodología: Business-First Architecture (BFA)
Fecha: 2026
________________________________________
1. Resumen Ejecutivo
1.1 Propósito
El Sistema de Administración de Referencias (SAR) es una plataforma interna diseñada para automatizar, administrar, controlar y auditar el ciclo completo de vida de las referencias generadas mediante Tributanet.
SAR elimina procesos manuales relacionados con:
•	Generación de referencias
•	Descarga de PDFs
•	Captura manual de referencias
•	Elaboración manual de Excel
•	Integración manual de PDFs
•	Seguimiento de autorizaciones
•	Control documental
________________________________________
1.2 Problema Actual
Actualmente el proceso requiere:
1.	Acceder manualmente a Tributanet.
2.	Seleccionar municipio (Benito Juares)
3.	Capturar RFC.
4.	Seleccionar Delegación (Cancún o Playa).
5.	Actualizar datos de dirección
6.	Seleccionar conceptos.
7.	Generar boletas individualmente.
8.	Descargar PDFs.
9.	Imprimir documentos.
10.	Leer referencias mediante lector.
11.	Capturar referencias en Excel.
12.	Integrar PDF unificados.
13.	Gestionar autorizaciones.
14.	Gestionar facturación posterior.
Lo anterior genera:
•	Alto tiempo operativo.
•	Errores humanos.
•	Falta de trazabilidad.
•	Dependencia de personal operativo.
•	Retrabajo.
________________________________________
1.3 Objetivo Estratégico
Maximizar la generación de referencias útiles y minimizar la pérdida de referencias por rechazo o expiración.
________________________________________
2. Alcance de SAR
Alcance Incluido
Planeación
•	Órdenes de Generación
•	Grupos de Referencias
•	Solicitudes
Generación
•	Automatización Tributanet
•	Descarga PDF
•	Extracción de datos
•	Generación de consecutivos
Administración
•	Referencias
•	Autorizaciones
•	Lotes
•	Exportaciones Excel
•	Gestión documental PDF
Facturación
•	Integración con proceso de facturación
Trazabilidad
•	Asignación de facturas
•	Seguimiento histórico
Auditoría
•	Bitácoras
•	Eventos
•	Historial
________________________________________
Alcance Excluido
•	ERP
•	Contabilidad
•	CRM
•	Inteligencia Artificial
•	Integraciones externas adicionales
________________________________________
3. Principios Fundamentales
PF-001
La referencia es la entidad principal del negocio.
________________________________________
PF-002
Toda referencia es única.
________________________________________
PF-003
Toda referencia tiene vigencia limitada mientras se encuentre pendiente de autorización.
________________________________________
PF-004
Una referencia nunca podrá reutilizarse.
________________________________________
PF-005
Una referencia rechazada se considera obsoleta.
________________________________________
PF-006
Una referencia expirada se considera obsoleta.
________________________________________
PF-007
Toda operación debe ser auditable.
________________________________________
PF-008
Toda asignación debe ser trazable.
________________________________________
PF-009
La unidad documental del negocio es el Grupo de Referencias.
________________________________________
4. Arquitectura Conceptual
ORDEN_GENERACION
        │
        ▼
GRUPO_REFERENCIA
(RFC + CONCEPTO)
        │
        ▼
SOLICITUD
(RFC + CONCEPTO + DELEGACION)
        │
        ▼
REFERENCIA
        │
        ▼
AUTORIZACION
        │
 ┌──────┼──────┐
 ▼      ▼      ▼
AUT.  RECH.  EXP.
 │
 ▼
FACTURA
 │
 ▼
ASIGNACION
________________________________________
5. Dominio de Negocio
Orden de Generación
Representa una necesidad operativa completa.
Ejemplo:
“Necesito generar 15,300 referencias.”
________________________________________
Grupo de Referencias
Representa:
RFC + Concepto
Es la unidad documental sobre la que se construyen:
•	Consecutivos
•	Lotes
•	Archivos Excel
•	PDFs individuales
•	PDFs unificados
•	Métricas operativas
Ejemplo:
Empresa A + Tipo 1
________________________________________
Solicitud
Representa:
RFC + Concepto + Delegación
Es la unidad operativa utilizada por los workers para generar referencias.
Ejemplo:
Empresa A + Tipo 1 + Cancún + 1000
________________________________________
Referencia
Resultado generado por Tributanet.
Es la entidad principal del sistema.
Cada referencia pertenece a:
•	Un Grupo de Referencias
•	Una Solicitud
________________________________________
Autorización
Resultado de evaluación de una referencia.
________________________________________
Factura
Documento generado a partir de una referencia autorizada.
________________________________________
Asignación
Registro de entrega física o digital de una factura.
________________________________________
6. Flujo Operativo Oficial
Orden de Generación
        ↓
Grupos de Referencias
        ↓
Solicitudes
        ↓
Workers
        ↓
Tributanet
        ↓
Referencias
        ↓
Autorización
        ↓
Facturación
        ↓
Asignación
        ↓
Cierre
________________________________________
7. Ejemplo Operativo
Requerimiento
EMPRESA1
•	ANALISIS: 2000
•	AVISO: 3000
•	CLG: 2400
EMPRESA2
•	ANALISIS: 1800
•	AVISO: 2200
•	CLG: 1200
EMPRESA3
•	ANALISIS: 900
•	AVISO: 1000
•	CLG: 800
Total:
15,300 referencias
________________________________________
Orden Generada
OG-2026-0001
________________________________________
Grupos Generados
EMPRESA1 - ANALISIS
EMPRESA1 - AVISO
EMPRESA1 - CLG
EMPRESA2 - ANALISIS
EMPRESA2 - AVISO
EMPRESA2 - CLG
EMPRESA3 - ANALISIS
EMPRESA3 - AVISO
EMPRESA3 - CLG
________________________________________
Total:
9 grupos
________________________________________
Solicitudes Generadas
•	EMPRESA1 - ANALISIS - Cancún - Cantidad: 1000 (Rango: Consecutivo 1 al 1000)
•	EMPRESA1 - ANALISIS - Playa del Carmen - Cantidad: 1000 (Rango: Consecutivo 1001 al 2000)
•	EMPRESA1 - AVISO - Cancún - Cantidad: 1200 (Rango: Consecutivo 1 al 1200)
•	EMPRESA1 - AVISO - Playa del Carmen - Cantidad: 1800 (Rango: Consecutivo 1201 al 3000)
…
________________________________________
8. Ciclo de Vida de Referencia
GENERANDO
      ↓
GENERADA
      ↓
PENDIENTE_AUTORIZACION
      ↓
 ┌──────────────┬──────────────┬──────────────┐
 ↓              ↓              ↓
AUTORIZADA   RECHAZADA    EXPIRADA
      ↓
FACTURADA
      ↓
ASIGNADA
________________________________________
Autorizada
La vigencia deja de ser relevante.
Continúa hacia facturación (generación y descarga de factura).
________________________________________
Facturada
La factura ha sido emitida y descargada físicamente.
Disponible para su asignación.
________________________________________
Asignada
Fin del ciclo activo. La factura fue entregada física o digitalmente al colaborador.
Únicamente útil para reportes, estadísticas e historial.
________________________________________
Rechazada
Fin del ciclo.
Referencia obsoleta.
________________________________________
Expirada
Fin del ciclo.
Referencia obsoleta.
________________________________________
9. Reglas de Negocio Congeladas
RN-001
Una Solicitud representa:
RFC + Concepto + Delegación + Cantidad
________________________________________
RN-002
Una Orden de Generación puede contener múltiples Grupos de Referencias.
________________________________________
RN-003
Un Grupo de Referencias representa:
RFC + Concepto
________________________________________
RN-004
Un Grupo de Referencias puede contener múltiples Solicitudes.
________________________________________
RN-005
Toda referencia generada por Tributanet es única.
________________________________________
RN-006
Una referencia nunca podrá reutilizarse.
________________________________________
RN-007
La vigencia aplica únicamente mientras la referencia se encuentre pendiente de autorización.
________________________________________
RN-008
Una referencia autorizada conserva su validez operativa aunque posteriormente se alcance su fecha original de vencimiento.
________________________________________
RN-009
Una referencia sin resolución al llegar su fecha límite pasará automáticamente a estado EXPIRADA.
________________________________________
RN-010
Una referencia expirada requerirá una nueva generación.
________________________________________
RN-011
Las aprobaciones podrán ser totales o parciales.
________________________________________
RN-012
Toda referencia autorizada podrá generar una factura asociada.
________________________________________
RN-013
La asignación de facturas (referencias en estado FACTURADA) podrá realizarse de forma individual o masiva por el Administrador SAR u otros usuarios con acceso, permitiendo filtrar por RFC, Concepto y, opcionalmente, Delegación.
________________________________________
RN-014
Toda asignación individual o masiva deberá registrar una o más entidades ASIGNACION y cambiar el estado de la referencia a ASIGNADA, conservando trazabilidad histórica permanente.
________________________________________
RN-015
Una aprobación parcial consume únicamente las referencias autorizadas.
________________________________________
RN-016
Las referencias autorizadas continúan hacia facturación.
________________________________________
RN-017
Toda referencia deberá poseer un consecutivo secuencial dentro de su Grupo de Referencias.
________________________________________
RN-018
El consecutivo deberá reiniciarse por cada combinación RFC + Concepto.
________________________________________
RN-019
Los lotes deberán construirse utilizando el consecutivo del Grupo de Referencias.
________________________________________
RN-020
Los archivos Excel deberán generarse por Grupo de Referencias.
________________________________________
RN-021
Los PDFs individuales y PDFs unificados deberán organizarse por Grupo de Referencias.
________________________________________
RN-022
Las referencias rechazadas o expiradas finalizan su ciclo de vida.
________________________________________
RN-023
Optimización de captura por coincidencia: El bot deberá leer el valor actual de los campos autocompletados (Nombre, Calle, Colonia, CP, etc.). Si coinciden exactamente con los registros de la base de datos (tras normalización a mayúsculas y recorte de espacios), omitirá la escritura en el portal para maximizar la velocidad del proceso.
________________________________________
10. Estrategia de Workers
Modelo inicial:
1 Equipo = 1 Worker
________________________________________
Características:
•	Escalable
•	Distribuido
•	Parametrizable
•	Concurrente
________________________________________
Funciones:
•	Tomar solicitudes
•	Ejecutar automatización
•	Descargar PDFs
•	Registrar referencias
•	Reportar resultados
________________________________________
Concurrencia
Los workers podrán procesar simultáneamente solicitudes pertenecientes al mismo Grupo de Referencias.
Por lo tanto:
•	No se permitirá el uso de MAX(CONSECUTIVO)+1.
•	El consecutivo se pre-asignará en rangos de inicio y fin a nivel de Solicitud en la planeación.
•	El consecutivo se incrementará de forma transaccional en la Solicitud, garantizando que sea único y ordenado dentro de su rango asignado.
________________________________________
11. Gestión de Lotes
Configuración inicial:
299 referencias por lote
________________________________________
Debe ser parametrizable.
No debe estar codificado.
________________________________________
Ejemplo
Grupo:
EMPRESA1 - ANALISIS
2000 referencias
________________________________________
Lote 1
1 - 299
________________________________________
Lote 2
300 - 598
________________________________________
Lote 3
599 - 897
________________________________________
…
________________________________________
Lote 7
1795 - 2000
________________________________________
12. Gestión Documental
Excel
Los archivos Excel se generan por Grupo de Referencias.
Ejemplo:
EMPRESA1_ANALISIS_LOTE_001.xlsx
Contenido:
•	Consecutivo
•	Referencia
•	Importe
•	Vigencia
________________________________________
PDFs Individuales
Estructura:
EMPRESA1
 └── ANALISIS
      ├── 000001.pdf
      ├── 000002.pdf
      ├── 000003.pdf
      └── ...
________________________________________
PDF Unificado
Ejemplo:
EMPRESA1_ANALISIS_LOTE_001.pdf
Contiene todas las referencias del lote correspondiente.
________________________________________
13. KPIs Estratégicos
Producción
•	Referencias Generadas
•	Referencias Autorizadas
•	Referencias Rechazadas
•	Referencias Expiradas
________________________________________
Eficiencia
Tasa de Aprovechamiento
Autorizadas / Generadas
________________________________________
Tasa de Desperdicio
(Rechazadas + Expiradas) / Generadas
________________________________________
Tiempo Promedio de Autorización
Fecha Autorización - Fecha Generación
________________________________________
Infraestructura
•	Workers Activos
•	Workers en Error
•	Tiempo Promedio por Referencia
________________________________________
Operación
•	Referencias por Grupo
•	Referencias por RFC
•	Referencias por Concepto
•	Referencias por Delegación
________________________________________
14. Entidades Empresariales Congeladas
Catálogos
•	CAT_RFC
•	CAT_CONCEPTO
•	CAT_DELEGACION
•	CAT_MUNICIPIO
•	CAT_ENTIDAD
________________________________________
Operación
•	ORDEN_GENERACION
•	GRUPO_REFERENCIA
•	SOLICITUD
•	REFERENCIA
•	AUTORIZACION
________________________________________
Documental
•	FACTURA
•	ASIGNACION
________________________________________
Infraestructura
•	WORKER
•	AUDITORIA
________________________________________
15. Estado del Proyecto
Descubrimiento
100%
________________________________________
Dominio de Negocio
100%
________________________________________
Modelo Conceptual
100%
________________________________________
Reglas de Negocio
100%
________________________________________
Modelo de Datos
100% (Congelado mediante [SAR-DB-001 v2.0](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/docs/SAR/9_SAR-DB-001%20v2.0.md))
________________________________________
Arquitectura Operativa
85%
________________________________________
UX Operativa
10%
________________________________________
Arquitectura Técnica
20%
________________________________________
Desarrollo
0%
________________________________________
16. Conclusión
SAR es una plataforma empresarial orientada a la administración integral del ciclo de vida de referencias, desde la planeación de su generación hasta la asignación final de la factura resultante.
La referencia continúa siendo la entidad principal del negocio; sin embargo, el descubrimiento más importante de esta versión es que la unidad documental y organizacional del sistema es el Grupo de Referencias, definido por la combinación RFC + Concepto.
Sobre esta entidad se construyen:
•	Consecutivos
•	Lotes
•	Archivos Excel
•	PDFs individuales
•	PDFs unificados
•	Métricas operativas
•	Control documental
