# 📕 Manual Técnico y de Administración — Sistema SAR (SAR-ADM)
**Versión:** 1.0  
**Fecha de Emisión:** Marzo 2026  
**Sistema:** SAR (Sistema de Administración de Referencias)  
**Audiencia:** Administradores de Sistemas, DBAs, Ingenieros de TI y Soporte N2/N3  

---

## 📌 Control del Documento y Notas de Edición

> [!NOTE]
> **Para el administrador/editor técnico:**  
> Este documento contiene marcadores visuales `> 📸 [Captura de Pantalla: ...]` para vistas administrativas de la aplicación y herramientas de TI (pgAdmin, Visor de Eventos, Diálogos de Administración). Reemplázalos con las imágenes del entorno operativo real.

---

# 1. Arquitectura del Sistema e Infraestructura

## 1.1 Diagrama de Topología y Comunicación (Red LAN)
Conforme al estándar [12_SAR-NET-001.md](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/12_SAR-NET-001.md):

```mermaid
graph TD
    subgraph Estaciones de Trabajo (Clientes)
        C1[Cliente 1: SAR_Cliente.exe]
        C2[Cliente 2: SAR_Cliente.exe]
        CN[Cliente N: SAR_Cliente.exe]
    end

    subgraph Servidor Central LAN
        DB[(PostgreSQL 16\nPuerto 5432)]
        FS[Servidor de Archivos SMB/UNC\n\\SRV-SAR\Comprobantes$]
    end

    subgraph Servicios Externos
        EXT[Portal Tributanet / Facturación]
    end

    C1 -->|TCP 5432 / TLS| DB
    C2 -->|TCP 5432 / TLS| DB
    CN -->|TCP 5432 / TLS| DB

    C1 -->|SMB 445| FS
    C2 -->|SMB 445| FS

    C1 -.->|HTTPS 443 / Playwright| EXT
    C2 -.->|HTTPS 443 / Playwright| EXT
```

## 1.2 Requisitos y Puertos de Red

| Servicio | Protocolo / Puerto | Dirección | Propósito |
| :--- | :---: | :---: | :--- |
| **Base de Datos** | TCP / `5432` | Cliente → Servidor | Acceso a PostgreSQL (Pool psycopg2/SQLAlchemy) |
| **Recurso Compartido** | TCP / `445` (SMB) | Cliente → Servidor | Almacenamiento centralizado de PDFs y XMLs |
| **Automatización Externa**| TCP / `443` (HTTPS)| Cliente → WAN | Conexión con portales externos (Playwright) |

---

# 2. Despliegue y Empaquetado del Cliente (`SAR_Cliente.exe`)

## 2.1 Especificaciones de Compilación
El cliente de escritorio está construido en **PySide6 (Qt for Python)** y empaquetado mediante **PyInstaller**.

### Comando Oficial de Empaquetado:
```powershell
pyinstaller --noconfirm --onedir --windowed --paths=. `
    --add-data "sar/src/ui/assets;sar/src/ui/assets" `
    --name="SAR_Cliente" `
    sar/main.py
```

## 2.2 Estructura del Paquete en Producción (`dist/SAR_Cliente/`)
```text
SAR_Cliente/
│
├── SAR_Cliente.exe         # Ejecutable principal
├── .env                    # Configuración de entorno local/red
├── sar/
│   └── src/ui/assets/      # Iconos, estilos QSS y recursos gráficos
└── _internal/              # Librerías dinámicas y runtime Python
```

## 2.3 Variables de Entorno (`.env`)
```ini
# Configuración de Conexión a Base de Datos Central
SAR_DB_HOST=192.168.1.100
SAR_DB_PORT=5432
SAR_DB_NAME=sar_db
SAR_DB_USER=sar_app_user
SAR_DB_PASS=PasswordSeguro2026!

# Rutas de Descargas y Archivos
SAR_STORAGE_PATH=\\SRV-SAR\Comprobantes$
SAR_LOG_LEVEL=INFO
```

---

# 3. Módulo de Administración del Sistema (SAR-ADM)

> 📸 **[Captura de Pantalla recomendada: Menú Administrativo de SAR con catálogos de empresas, conceptos y usuarios]**

## 3.1 Gestión de Catálogos Maestros
* **Empresas y RFCs:** Alta, baja lógica y modificación de razones sociales, identificadores fiscales y sucursales.
* **Conceptos y Tarifas:** Catálogo de trámites, importes vigentes y claves gubernamentales.

## 3.2 Inyección y Control de Folios / Derechos (Inventario)
1. Ingresa a **Administración → Control de Folios**.
2. Haz clic en **📥 Inyectar Nuevo Paquete**.
3. Selecciona el concepto y carga el rango de folios o archivo CSV provisto.
4. Confirma la carga para habilitar la disponibilidad inmediata a los operadores.

> 📸 **[Captura de Pantalla recomendada: Diálogo de carga e inyección de nuevos paquetes de folios]**

## 3.3 Gestión de Usuarios y Roles de Seguridad

| Rol | Permisos Otorgados |
| :--- | :--- |
| `ROLE_OPERADOR` | Captura de órdenes, ejecución de Bot Fase A (AutoGeneración de Derechos) y Bot Fase C (AutoFacturación de Derechos), consultas básicas. |
| `ROLE_SUPERVISOR` | Todo lo de operador + Autorización y Rechazo de órdenes de cualquier usuario. |
| `ROLE_ADMIN` | Acceso total: Configuración, catálogos, inyección de folios, desbloqueo y auditoría. |

---

# 4. Base de Datos PostgreSQL y Transaccionalidad

Conforme a [10_SAR-DB-001 v3.0.md](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/10_SAR-DB-001%20v3.0.md):

## 4.1 Control de Concurrencia Estricto
Para evitar condiciones de carrera (*Race Conditions*) o asignaciones duplicadas de folios entre clientes simultáneos, el sistema implementa bloqueo pesimista a nivel de fila:

```sql
-- Ejemplo del mecanismo de reserva transaccional
BEGIN;
SELECT id, numero_folio 
FROM sar_folios_inventario 
WHERE concepto_id = 12 AND estado = 'DISPONIBLE' 
ORDER BY id ASC 
LIMIT 1 
FOR UPDATE SKIP LOCKED;

UPDATE sar_folios_inventario 
SET estado = 'RESERVADO', orden_id = 142 
WHERE id = :id_obtenido;
COMMIT;
```

## 4.2 Estrategia de Respaldos (`pg_dump`)
Ejecutar diariamente mediante tarea programada en el servidor:
```bash
pg_dump -U postgres -h localhost -F c -b -v -f "D:\Backups_SAR\sar_db_%DATE%.dump" sar_db
```

---

# 5. Soporte Nivel 2/3 y Mantenimiento Correctivo

## 5.1 Desbloqueo y Purga de Órdenes Inconsistentes
Conforme al protocolo [14_SAR-DB-DELETE-ORDER.md](file:///c:/Users/dramos/Documents/Proyecto_CapturaBot/sar/doc_sar/14_SAR-DB-DELETE-ORDER.md):

Si una orden queda corrupta por fallo eléctrico o cierre forzado durante la generación:
```sql
-- Procedimiento seguro: Liberar folios antes de purgar la orden
UPDATE sar_folios_inventario 
SET estado = 'DISPONIBLE', orden_id = NULL 
WHERE orden_id = 142;

UPDATE sar_ordenes 
SET estado = 'RECHAZADA', observaciones = 'Cancelada por soporte técnico debido a inconsistencia' 
WHERE id = 142;
```

## 5.2 Ubicación de Archivos de Log del Cliente
* **Ruta de logs local:** `%APPDATA%\SAR\logs\sar_client.log`
* **Nivel de detalle:** Configurable en `.env` mediante `SAR_LOG_LEVEL=DEBUG`.
