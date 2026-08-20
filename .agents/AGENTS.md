# Reglas del Proyecto SAR (Sistema de Administración de Referencias)

Este archivo define las reglas de comportamiento y desarrollo obligatorias que los agentes de IA deben seguir al trabajar en esta base de código.

## 1. Cumplimiento de Prompts Estructurados (SAR-AI-PROMPTS-001)

Cualquier cambio, análisis técnico, refactorización o propuesta de código debe seguir estrictamente la metodología y el marco de trabajo multidisciplinario detallado en [SAR-AI-PROMPTS-001.md](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/SAR-AI-PROMPTS-001.md). 
- **No codificar antes de analizar**: Todo requerimiento debe pasar primero por un análisis formal simulando los roles del **Equipo de Diseño y Arquitectura**.
- **Desarrollo Consensuado**: Considerar y documentar los pros/contras de las alternativas antes de proponer código final.
- **Auditoría de QA**: Antes de dar por finalizada una tarea, realizar el análisis de casos borde, riesgos y rendimiento bajo la perspectiva del **Equipo de Calidad**.
- **Hardening e Infraestructura**: Considerar el impacto de red, seguridad, respaldos y robustez (especialmente en entornos de red LAN con PostgreSQL y Windows) bajo la guía del **Equipo de Infraestructura**.

## 2. Alineación con el Blueprint y Estándares Técnicos

Todas las modificaciones deben estar completamente alineadas con la arquitectura formal de SAR definida en la carpeta doc_sar/:
- **Estándar de Desarrollo**: Seguir la guía de desarrollo y convenciones descritas en [7_SAR-DEV-001.md](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/7_SAR-DEV-001.md).
- **Estándar de Código**: Adherirse a los estándares y calidad de código descritos en [9_SAR-CODE-001.md](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/9_SAR-CODE-001.md).
- **Esquema de Base de Datos**: Respetar el diseño físico de PostgreSQL detallado en [10_SAR-DB-001 v3.0.md](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/10_SAR-DB-001%20v3.0.md) e implementar control transaccional estricto con bloqueos a nivel de fila (FOR UPDATE) cuando se gestionen folios/consecutivos concurrentes.
- **Seguridad**: Respetar las directrices de seguridad física, lógica y de red descritas en [8_SAR-SEC-001.md](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/8_SAR-SEC-001.md) e [11_SAR-SEC-002.md](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/11_SAR-SEC-002.md).

## 3. Comportamiento en Planning Mode y Modificación de Código

- Siempre que se modifique o cree código, se debe verificar el impacto en el orquestador y la interfaz de usuario en PySide6.
- Preservar los comentarios e integridad del código no relacionado.
- Al final de cada iteración, proporcionar un resumen conciso y hacer referencia a los archivos modificados mediante enlaces válidos de formato ile:///.
