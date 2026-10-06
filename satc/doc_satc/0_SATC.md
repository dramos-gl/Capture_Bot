# Registro de Documentos del Sistema — SATC (Sistema de Automatización de Trámites Cancún)

**Ecosistema:** Proyecto_CapturaBot  
**Metodología:** Business-First Architecture (BFA)  
**Nombre del Sistema:** Sistema ATC / SATC (Sistema de Automatización de Trámites Cancún)  
**Versión:** 2.0  
**Fecha:** 2026

---

## Índice de Documentación Oficial

| Código | Nombre Formal | Categoría | Archivo |
| :--- | :--- | :--- | :--- |
| **SATC-BLUEPRINT-001** | Blueprint Empresarial SATC | Arquitectura Empresarial | [1_SATC-BLUEPRINT-001.md](1_SATC-BLUEPRINT-001.md) |
| **SATC-DB-001** | Diseño Físico de Base de Datos | Ingeniería de Datos | [2_SATC-DB-001.md](2_SATC-DB-001.md) |
| **SATC-DEV-001** | Guía de Desarrollo y Estándares | Ingeniería de Software | [3_SATC-DEV-001.md](3_SATC-DEV-001.md) |
| **SATC-TEC-001** | Arquitectura Técnica | Arquitectura de Solución | [4_SATC-TEC-001.md](4_SATC-TEC-001.md) |
| **SATC-RPA-001** | Resiliencia, Captcha & UX Portal Cancún | Automatización & RPA | [5_SATC-RPA-001.md](5_SATC-RPA-001.md) |
| **SATC-AISLAMIENTO-001** | Principio de Aislamiento Estricto | Arquitectura y Coexistencia | [6_SATC-AISLAMIENTO-001.md](6_SATC-AISLAMIENTO-001.md) |

---

## Visión General del Sistema

El **SATC (Sistema de Automatización de Trámites Cancún)** es la plataforma empresarial encargada de la gestión, orquestación y automatización (RPA) de trámites administrativos y fiscales de Cancún. Agrupa un módulo de **Control y Orquestación** junto a módulos bot especializados:

### 🎛️ Módulo de Control y Orquestación
Gestión de lotes de entrada (Excel/PDF/Manual), validación de RFCs, asignación a ordenes de trabajo y monitoreo de estado en tiempo real.

### 🤖 Bot A — Descarga de Recibos Electrónicos
Automatiza la consulta y descarga de recibos electrónicos desde el portal **recibo.tesoreriacancun.com**, a partir de folios electrónicos o folios pase de caja. Extrae los datos del PDF descargado y los registra en el esquema `satc_produccion`.

### 🤖 Bot C — Facturación Electrónica
A partir de los datos capturados en la fase del Bot A, automatiza el proceso de facturación en el portal **benitojuarez.expidefactura.com**, completando el ciclo: Recibo → Factura.

---

## Relación con el Ecosistema SAR

SATC es un subsistema **hermano** de SAR, que hereda y mantiene simetría en sus patrones de diseño:

| Patrón | SAR | SATC |
| :--- | :--- | :--- |
| Page Object Model (POM) | `sar/src/pages/` | `satc/src/pages/` |
| Anti-hardcodeo selectores | `sar_configuracion.localizador_portal` | `satc_configuracion.localizador_portal` |
| Repository Pattern | `sar/src/storage/repositories.py` | `satc/src/storage/satc_repos.py` |
| Parámetros configurables | `sar_configuracion.parametro_sistema` | `satc_configuracion.parametro_sistema` |
| UI Desktop (PySide6) | `sar/src/ui/` | `satc/src/ui/` |
| Automatización | Playwright | Playwright |
| Base de datos | PostgreSQL (`sar_db`) | PostgreSQL (`satc_produccion` en `db_sar`) |

> **Ambos proyectos comparten el entorno virtual `.venv_sar`** ubicado en la raíz de `Proyecto_CapturaBot`.

---

## Directivas Obligatorias de Coexistencia e Impacto

1. **Aislamiento y No-Afectación al Ecosistema SAR**:
   - Bajo ninguna circunstancia las modificaciones, mejoras o refactorizaciones realizadas en **SATC** deben alterar, romper o degradar la funcionalidad existente del **SAR** (modelos, servicios, endpoints REST o vistas de PySide6).
   - SATC debe consumir los componentes del Atomic Design (`sar/src/ui/design_system/`) en modo **solo lectura / extensión limpia**, sin modificar los contratos ni los tokens base del SAR.

2. **Gestión de Nuevas Dependencias y Esquemas de Base de Datos**:
   - Cualquier requerimiento que implique nuevas dependencias de base de datos (nuevas tablas, migraciones SQL, modificaciones al esquema `satc_produccion`) **debe ser explícitamente documentado y detallado en los Planes de Trabajo (Implementation Plans)** antes de su ejecución.
   - Las migraciones DDL deben estar aisladas en `satc/src/storage/migrations/` y no deben afectar las tablas del núcleo SAR salvo aprobación explícita del **Equipo de Arquitectura de Datos**.
