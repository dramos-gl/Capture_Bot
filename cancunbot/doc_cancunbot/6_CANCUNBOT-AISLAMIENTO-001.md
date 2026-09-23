# CANCUNBOT-AISLAMIENTO-001: Propuesta de Aislamiento de Recursos (Futuro)
**Categoría:** Infraestructura y Base de Datos  
**Estado:** Propuesta a Futuro  
**Módulo:** R2F Cancún (`cancunbot`)  

---

## 1. Contexto

Durante la integración y evaluación del módulo `cancunbot` en el sistema SAR, se planteó la posibilidad de **separar cancunbot en una base de datos independiente** para evitar que los procesos automatizados (scraping, facturación, descargas masivas) impactaran negativamente la integridad y el rendimiento del sistema principal `SAR`.

Tras un análisis del Equipo Multidisciplinario (Arquitectura, Base de Datos e Infraestructura), se dictaminó que la separación física de la base de datos **NO es recomendable** por las siguientes razones:
- Rompería la integridad referencial con los catálogos base compartidos (`estado_sistema`, `usuario`, `rfc`, etc.).
- Requeriría implementar sincronización de catálogos o transacciones distribuidas, añadiendo una complejidad técnica innecesaria.

La alternativa validada por el comité es aplicar un **Aislamiento Híbrido (Cómputo + Conexión)** dentro de la misma base de datos `db_sar`. Este documento detalla esa alternativa para su implementación en el futuro, cuando la carga del robot lo justifique.

---

## 2. Aislamiento Lógico y de Base de Datos (DBA)

El enfoque principal es restringir el consumo de recursos de PostgreSQL para evitar que el bot monopolice el pool de conexiones o genere cuellos de botella (locks).

### 2.1. Usuario de Base de Datos Dedicado
Se recomienda la creación de un rol exclusivo en PostgreSQL para el módulo Cancún: `cancunbot_user`.

*   **Límite de Conexiones:** Asignar un máximo estricto (ej. `CONNECTION LIMIT 5`). Si el bot entra en un bucle o abre múltiples hilos, no podrá saturar PostgreSQL; solo el propio bot se verá frenado, mientras `sar_app_user` (operadores humanos) continuará trabajando sin interrupciones.
*   **Permisos (Principio de Mínimo Privilegio):**
    *   **Solo Lectura (`SELECT`):** A los esquemas `sar_catalogo`, `sar_seguridad`, y `sar_configuracion`.
    *   **Lectura y Escritura (`SELECT, INSERT, UPDATE`):** Únicamente al esquema `cancunbot_produccion`.

---

## 3. Aislamiento de Cómputo (Backend / UI)

Los procesos de automatización de navegadores (Playwright / Chromium) consumen una cantidad intensiva de memoria RAM y CPU. Ejecutarlos en la máquina de un operador junto a la GUI del SAR podría causar congelamientos.

### 3.1. Extracción a un Worker Dedicado
*   **Desacoplar el módulo UI:** A futuro, en lugar de invocar `BotReciboCunWorker` o `BotFacturaCunWorker` desde la GUI en la máquina del operador, se recomienda compilar un ejecutable secundario (e.g., `CancunBot_Worker.exe` o script `.py` como daemon).
*   **Ejecución Centralizada:** Este worker puede ejecutarse en un servidor secundario de bajo costo (o máquina virtual independiente).
*   **Dinámica de Operación:** La GUI del sistema SAR funcionará únicamente para **crear lotes y monitorear** (`LoteFolio`), pero el procesamiento pesado lo realizará de forma autónoma el worker aislado.

---

## 4. Pasos para la Implementación (Cuando se requiera)

1.  **DML en PostgreSQL:**
    ```sql
    CREATE ROLE cancunbot_user WITH LOGIN PASSWORD '***' CONNECTION LIMIT 5;
    GRANT CONNECT ON DATABASE db_sar TO cancunbot_user;
    
    -- Permisos de lectura
    GRANT USAGE ON SCHEMA sar_catalogo TO cancunbot_user;
    GRANT SELECT ON ALL TABLES IN SCHEMA sar_catalogo TO cancunbot_user;
    
    -- Permisos completos en su esquema
    GRANT USAGE, CREATE ON SCHEMA cancunbot_produccion TO cancunbot_user;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA cancunbot_produccion TO cancunbot_user;
    GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA cancunbot_produccion TO cancunbot_user;
    ```
2.  **Ajustar `settings.json` o variables de entorno:**
    Incluir las credenciales de base de datos exclusivas del bot.
3.  **Ajuste de Conector en Código:**
    Modificar la forma en que los workers obtienen la sesión, instanciando `DatabaseConnector` con las credenciales específicas del bot.
