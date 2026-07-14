# SAR-NET-001: Guía de Configuración de Red, Seguridad y Despliegue con NSSM
**Categoría:** Infraestructura, Seguridad y Despliegue  
**Versión:** 2.0  
**Estado:** Propuesto  
**Metodología:** Business-First Architecture (BFA)

---

## 1. Objetivo
Esta guía proporciona las instrucciones detalladas y las mejores prácticas de seguridad informática para realizar el despliegue del sistema SAR en un entorno distribuido local (LAN). Describe la configuración de PostgreSQL, el despliegue de la API FastAPI como servicio de Windows utilizando **NSSM (Non-Sucking Service Manager)**, las políticas de Firewall de Windows y la distribución cliente.

---

## 2. Topología de Red Propuesta (3-Tier)

La arquitectura de 3 capas aísla la base de datos de las estaciones de trabajo de los operadores, utilizando el servidor de API como la única pasarela de conexión:

```
[ EQUIPOS OPERADORES (Clientes) ]
 ├── Ejecutan: SAR_App.exe (GUI compiled via PyInstaller)
 └── Leen: settings.json (Apunta a http://<IP_SERVIDOR>:8000)
       │
       ▼ (Peticiones HTTP/JSON por Puerto 8000)
[ SERVIDOR CENTRAL ]
 ├── Firewall de Windows (Bloquea puerto 5432 a la LAN; permite puerto 8000)
 ├── Servicio Windows: SAR_API (FastAPI + Uvicorn gestionado por NSSM)
 └── PostgreSQL (Servicio escuchando en Localhost/Puerto 5432)
```

---

## 3. Fase 1: Configuración de PostgreSQL (Aislamiento)

En producción, la base de datos PostgreSQL **no debe** aceptar conexiones directas desde los equipos clientes.

1. **`postgresql.conf`**: Configure PostgreSQL para escuchar en la interfaz local del servidor:
   ```ini
   listen_addresses = 'localhost'
   ```
2. **`pg_hba.conf`**: Restrinja el acceso de red local solo para conexiones locales desde el propio servidor donde corre la API:
   ```text
   # TYPE  DATABASE        USER            ADDRESS                 METHOD
   host    db_sar          postgres        127.0.0.1/32            scram-sha-256
   host    db_sar          sar_api_user    127.0.0.1/32            scram-sha-256
   ```

---

## 4. Fase 2: Servidor API & Configuración de NSSM

Para asegurar que la API de FastAPI esté activa de manera ininterrumpida (24/7), se desplegará como un **Servicio de Windows** utilizando la herramienta **NSSM**.

### 4.1. Requisitos Previos en el Servidor
1. Descargue y extraiga **NSSM** (versión recomendada 2.24 o superior) en una ruta del sistema (ejemplo: `C:\tools\nssm.exe`).
2. Copie el código fuente del backend SAR a su ubicación definitiva (ejemplo: `C:\SAR_System`).
3. Inicialice el entorno virtual e instale las dependencias de producción:
   ```powershell
   cd C:\SAR_System
   python -m venv .venv
   .\.venv\Scripts\pip install -r requirements.txt
   ```

### 4.2. Registro del Servicio con NSSM
Abra una terminal de **PowerShell** como **Administrador** y ejecute:

```powershell
# Lanzar la GUI de instalación de NSSM
C:\tools\nssm.exe install SAR_API
```

Esto abrirá la interfaz gráfica de NSSM. Configure los siguientes parámetros:

* **Tab: Application**
  * **Path:** `C:\SAR_System\.venv\Scripts\uvicorn.exe`
  * **Startup directory:** `C:\SAR_System`
  * **Arguments:** `sar.main_api:app --host 0.0.0.0 --port 8000 --workers 4`
* **Tab: Details**
  * **Display name:** Sistema SAR - Servidor API
  * **Description:** Backend API REST en FastAPI para la gestión de referencias y control de accesos del robot SAR.
  * **Startup type:** Automatic
* **Tab: Shutdown**
  * Deje los valores predeterminados (envía señales de terminación seguras a los procesos de Uvicorn).

Haga clic en **Install service**.

### 4.3. Arrancar el Servicio
Desde la misma terminal de PowerShell, inicialice el servicio:
```powershell
Start-Service SAR_API
# Verificar el estado del servicio
Get-Service SAR_API
```

---

## 5. Fase 3: Configuración del Firewall de Windows

El Firewall de Windows debe cerrarse para la base de datos pero abrirse de manera controlada para el puerto de la API.

### 5.1. Regla de Entrada para la API (Puerto 8000)
Autorice a los equipos de la subred local (`192.168.1.0/24`) a conectarse a la API de FastAPI:

```powershell
New-NetFirewallRule -DisplayName "SAR - Servidor API (Producción)" `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 8000 `
    -Profile Private `
    -RemoteAddress 192.168.1.0/24
```

### 5.2. Bloqueo del Puerto PostgreSQL (Puerto 5432)
Asegúrese de que no existan reglas entrantes que permitan tráfico a PostgreSQL desde fuera del servidor:
```powershell
Disable-NetFirewallRule -DisplayName "PostgreSQL*"
```

---

## 6. Fase 4: Despliegue y Distribución del Cliente

### 6.1. Archivo de Configuración del Cliente (`settings.json`)
En la carpeta de instalación de cada cliente de escritorio (junto al ejecutable compilado), se creará un archivo de configuración dinámico:

```json
{
  "api_url": "http://192.168.1.15:8000"
}
```

### 6.2. Compilación del Cliente
Utilice PyInstaller para compilar la aplicación de escritorio a partir del archivo `.spec` existente en el workspace:
```powershell
pyinstaller main.spec --noconfirm
```
Distribuya la carpeta de salida `dist/main/` (que incluye el ejecutable `main.exe` y el archivo `settings.json`) a los operadores de la red local.
