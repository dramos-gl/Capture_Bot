# Registro de Documentos del Sistema — CancunBot

**Ecosistema:** Proyecto_CapturaBot  
**Metodología:** Business-First Architecture (BFA)  
**Versión:** 1.0  
**Fecha:** 2026

---

## Índice de Documentación Oficial

| Código | Nombre Formal | Categoría | Archivo |
| :--- | :--- | :--- | :--- |
| **CANCUNBOT-BLUEPRINT-001** | Blueprint Empresarial CancunBot | Arquitectura Empresarial | [1_CANCUNBOT-BLUEPRINT-001.md](1_CANCUNBOT-BLUEPRINT-001.md) |
| **CANCUNBOT-DB-001** | Diseño Físico de Base de Datos | Ingeniería de Datos | [2_CANCUNBOT-DB-001.md](2_CANCUNBOT-DB-001.md) |
| **CANCUNBOT-DEV-001** | Guía de Desarrollo y Estándares | Ingeniería de Software | [3_CANCUNBOT-DEV-001.md](3_CANCUNBOT-DEV-001.md) |
| **CANCUNBOT-TEC-001** | Arquitectura Técnica | Arquitectura de Solución | [4_CANCUNBOT-TEC-001.md](4_CANCUNBOT-TEC-001.md) |
| **CANCUNBOT-RPA-001** | Resiliencia, Captcha & UX Portal Cancún | Automatización & RPA | [5_CANCUNBOT-RPA-001.md](5_CANCUNBOT-RPA-001.md) |

---

## Visión General del Sistema

**CancunBot** automatiza dos flujos críticos vinculados a la **Tesorería Municipal de Cancún**:

### Bot A — Descarga de Recibos Electrónicos
Automatiza la consulta y descarga de recibos electrónicos desde el portal **recibo.tesoreriacancun.com**, a partir de folios electrónicos o folios pase de caja. Extrae los datos del PDF descargado y los registra en la base de datos.

### Bot C — Facturación Electrónica
A partir de los datos capturados en la fase del Bot A, automatiza el proceso de facturación en el portal **benitojuarez.expidefactura.com**, completando el ciclo: Recibo → Factura.

---

## Relación con el Ecosistema SAR

CancunBot es un proyecto **hermano** del SAR, que hereda sus patrones de diseño:

| Patrón | SAR | CancunBot |
| :--- | :--- | :--- |
| Page Object Model (POM) | `sar/src/pages/` | `cancunbot/src/pages/` |
| Anti-hardcodeo selectores | `sar_configuracion.localizador_portal` | `cancunbot_configuracion.localizador_portal` |
| Repository Pattern | `sar/src/storage/repositories.py` | `cancunbot/src/storage/repositories.py` |
| Parámetros configurables | `sar_configuracion.parametro_sistema` | `cancunbot_configuracion.parametro_sistema` |
| UI Desktop (PySide6) | `sar/src/ui/` | `cancunbot/src/ui/` |
| Automatización | Playwright | Playwright |
| Base de datos | PostgreSQL (`sar_db`) | PostgreSQL (`db_cancunbot`) |

> **Ambos proyectos comparten el entorno virtual `.venv_sar`** ubicado en la raíz de `Proyecto_CapturaBot`.

---

## Directivas Obligatorias de Coexistencia e Impacto

1. **Aislamiento y No-Afectación al Ecosistema SAR**:
   - Bajo ninguna circunstancia las modificaciones, mejoras o refactorizaciones realizadas en **CancunBot** deben alterar, romper o degradar la funcionalidad existente del **SAR** (modelos, servicios, endpoints REST o vistas de PySide6).
   - CancunBot debe consumir los componentes del Atomic Design (`sar/src/ui/design_system/`) en modo **solo lectura / extensión limpia**, sin modificar los contratos ni los tokens base del SAR.

2. **Gestión de Nuevas Dependencias y Esquemas de Base de Datos**:
   - Cualquier requerimiento que implique nuevas dependencias de base de datos (nuevas tablas, migraciones SQL, modificaciones a `db_cancunbot` o `sar_db`) **debe ser explícitamente documentado y detallado en los Planes de Trabajo (Implementation Plans)** antes de su ejecución.
   - Las migraciones DDL deben estar aisladas en `cancunbot/src/storage/migrations/` y no deben afectar las tablas del núcleo SAR (`sar_db`) salvo aprobación explícita del **Equipo de Arquitectura de Datos**.

