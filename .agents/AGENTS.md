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

## 3. Principio de Transparencia de Transporte (CONNECT_VIA_API / Modo Híbrido)

Cualquier ajuste en la lógica de negocio, servicios, catálogos o interfaz de usuario debe ser **100% transparente y simétrico** tanto para la conexión directa a base de datos (`CONNECT_VIA_API: false`) como para la conexión vía API REST (`CONNECT_VIA_API: true`):
- **Capa de Servicios de UI (`*UIService`)**: Toda vista debe interactuar con servicios desacoplados que soporten ambas vías. Si se agrega un nuevo campo o método, este debe implementarse de forma idéntica en la rama directa (SQLAlchemy/Repositorios) y en la rama REST (`APIClient`).
- **Simetría en API Central (FastAPI)**: Todo endpoint en `sar/src/api/routers/` debe exponer y recibir los mismos contratos de datos (JSON) que los repositorios locales.
- **Cero Divergencia**: Ninguna funcionalidad o vista puede asumir conexión directa exclusiva ni depender únicamente de HTTP; el conmutador de `settings.json` debe operar sin fricción ni discrepancias funcionales.

## 4. Principio de Atomic Design y Cero Hardcodeo de UI (design_system)

Toda modificación o extensión de la interfaz gráfica en PySide6 debe regirse estrictamente por la arquitectura de **Atomic Design** (`sar/src/ui/design_system/`):
- **Cero Estilos Hardcodeados en Vistas**: Queda estrictamente prohibido incrustar reglas CSS/QSS inline ad-hoc en las vistas (`sar/src/ui/views/`). Toda regla visual, espaciado y paleta de colores debe originarse a través de los tokens (`tokens/colors.py`, `tokens/spacing.py`, `tokens/typography.py`) y del `ThemeManager`.
- **Integración Formal de Nuevos Componentes**: Si un requerimiento visual necesita un nuevo tipo de control (átomo, molécula u organismo), este debe crearse formalmente en el subdirectorio correspondiente dentro de `sar/src/ui/design_system/components/` (ej. `atoms/gl_spin_box.py`, `molecules/gl_info_banner.py`) y registrarse para exportación pública en `sar/src/ui/design_system/components/__init__.py`.
- **Compatibilidad con Temas (Light / Dark)**: Todo componente debe reaccionar adecuadamente a los cambios de tema claro y oscuro a través de `ThemeManager.is_dark_active()`.

## 5. Comportamiento en Planning Mode y Modificación de Código

- Siempre que se modifique o cree código, se debe verificar el impacto en el orquestador y la interfaz de usuario en PySide6.
- Preservar los comentarios e integridad del código no relacionado.
- Al final de cada iteración, proporcionar un resumen conciso y hacer referencia a los archivos modificados mediante enlaces válidos de formato file:///.
