# Reporte de Auditoría Multidisciplinaria: Optima Capture Bot (v1.1.0)

Este documento presenta los hallazgos y evaluaciones emitidos por el comité de auditoría multidisciplinario respecto al estado actual, robustez, usabilidad y control operativo del robot.

---

## 1. Product Owner Senior (Objetivos de Negocio y Flujo de Procesos)
### Evaluación
* El sistema cumple satisfactoriamente con el MVP y la iteración v1.1.0. Se han cubierto las metas de automatización del portal SATQ.
* **Integridad de Datos:** La sugerencia de condicionar el estado `OK-GENERADA` a la descarga exitosa de los 2 archivos PDF reduce a cero las falsas confirmaciones, garantizando que el Excel refleje la existencia de los entregables físicos.
* **Mitigación de Errores Humanos:** La validación estricta de RFCs basada en una lista blanca (`Allowlist`) de 4 empresas autorizadas asegura que el bot no procese lotes de entidades ajenas a la organización.

### Recomendaciones de Negocio
* **Escalabilidad del Catálogo:** Actualmente, los RFCs válidos están en código duro en `validator.py`. A largo plazo, se aconseja parametrizar esta lista en `settings.json` o leerla de una base de datos segura para evitar modificar código fuente al dar de alta nuevos clientes.

---

## 2. QA Lead (Calidad de Software y Escenarios de Prueba)
### Evaluación
* **Detección de Anomalías:** El sistema cuenta con mecanismos de control para anomalías complejas como bloqueos de archivos en caliente (`PermissionError`), e inestabilidad del servidor (HTTP 500 FastCGI).
* **Validación de PDFs:** El nuevo módulo `PDFValidator` mitiga escenarios de regresión donde las facturas quedaban a medias, validando de forma interactiva y asíncrona la integridad del lote en disco.

### Estrategia de Pruebas Recomendada
* **Prueba de Estrés de Red:** Simular micro-cortes de internet durante el clic de Timbrar para asegurar que el reintento vía recarga total de Playwright se ejecuta en menos de 35 segundos sin corromper el Excel.
* **Pruebas de Regresión en Portal:** Dado que el portal SATQ no posee un entorno de staging/QA, cualquier cambio en sus selectores (ej: `button#btnTimbrar`) romperá el bot. Se requiere monitoreo constante de la estructura DOM.

---

## 3. Arquitecto de Automatización / RPA Senior (Robustez y Escalabilidad)
### Evaluación
* **Manejo de Errores y Excepciones:** Se destaca el desacoplamiento mediante una cola de eventos thread-safe (`queue.Queue`) entre el hilo del orquestador y la interfaz de usuario. Esto previene cuelgues del hilo principal (GUI) de Tkinter.
* **Gestión del Estado del Navegador:** El uso de un perfil de usuario persistente (`perfil_bot`) de Chromium real en Windows mitiga la detección de bots y conserva las sesiones activas de manera óptima.
* **Mantenimiento y Logs:** El uso de `RotatingFileHandler` con un límite de 5 MB de tamaño y 3 respaldos previene el consumo de almacenamiento y asegura la autogestión de logs de forma indefinida.

### Recomendaciones Arquitectónicas
* **Refactorización de Selectores:** Mapear los selectores de Playwright (`button#btnTimbrar`, `a.btn.btn-default[href="./"]`, etc.) a un archivo de configuración JSON separado para que el bot sea mantenible sin compilar de nuevo el código ante actualizaciones del portal web.

---

## 4. Especialista UX/UI (Experiencia de Usuario e Interfaz)
### Evaluación
* **Facilidad de Confirmación:** La incorporación de Tooltips interactivos y visuales en la barra de estado para mostrar la ruta completa de Excel y Descargas en hover responde de forma óptima a las necesidades de seguridad del operador.
* **Bloqueo Inteligente de Controles:** La desactivación temporal de controles al dar clic en "Validar PDFs" o "Iniciar Bot" evita interferencias, garantizando una interacción ordenada.
* **Modo Autónomo Flexible:** Dejar habilitado el switch de Modo Autónomo en caliente permite al usuario "asistir" al bot sin necesidad de pausar la automatización, incrementando la productividad operativa significativamente.

---

## 5. Auditor de Riesgos Operativos (Continuidad y Seguridad Fiscal)
### Evaluación
* **Continuidad del Negocio:** El sistema maneja de forma segura las interrupciones del operador (Pausa, Detención segura, y modal de bloqueo de Excel).
* **Riesgo Fiscal:** Cada decisión tomada por el bot en modo autónomo o asistido se escribe de forma paralela e histórica en `logs/auditoria_timbrado.csv`. Esto proporciona evidencia legal en caso de auditorías externas.

### Riesgos Identificados
* **Expiración de Sesión del SATQ:** Si el portal implementa sesiones más cortas o captchas intermedios en el timbrado, el modo autónomo fallará. La mitigación actual (pausa y cambio a modo asistido con alarma visual) es adecuada, pero requiere atención constante del operador.

---

## Conclusión del Comité
El robot **Optima Capture Bot (v1.1.0)** se encuentra en un estado **Altamente Maduro, Seguro y Auditable**. Los controles preventivos de error humano (lista de RFCs) y recuperación técnica (FastCGI 500 y cuelgues) mitigan los principales riesgos operativos del proceso. 

Se autoriza su promoción/uso continuo bajo la recomendación de archivar periódicamente el log de auditoría.
