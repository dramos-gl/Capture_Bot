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

## 3. Fase 1: Configuración de PostgreSQL (Pruebas / Conexión Externa)

Para permitir que los equipos clientes de la red local puedan comunicarse con la base de datos alojada en el servidor:

1. **`postgresql.conf`**: Configure PostgreSQL para escuchar en todas las interfaces de red del servidor (`10.11.8.151`):
   ```ini
   listen_addresses = '*'
   ```
2. **`pg_hba.conf`**: Autorice explícitamente el acceso remoto al cliente de pruebas (`10.11.8.108`) y mantenga las conexiones locales:
   ```text
   # TYPE  DATABASE        USER            ADDRESS                 METHOD
   # Conexiones locales del servidor (127.0.0.1 y localhost)
   local   all             all                                     scram-sha-256
   host    all             all             127.0.0.1/32            scram-sha-256
   host    all             all             ::1/128                 scram-sha-256
   
   # Conexiones remotas desde el cliente de pruebas
   host    db_sar          postgres        10.11.8.108/32          scram-sha-256
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
  * **Path:** `C:\SAR_System\.venv\Scripts\python.exe`
  * **Startup directory:** `C:\SAR_System`
  * **Arguments:** `-m uvicorn sar.main_api:app --host 0.0.0.0 --port 8000 --workers 4`
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
netstat -ano | findstr :8000 #Revisar si esta en modo LISTENING
Test-NetConnection -ComputerName 10.11.8.151 -Port 8000 #Verificar la conexión al servidor desde el cliente de pruebas
```

### 4.4. Inicio Manual del Servidor (Modo Desarrollo/Pruebas)
Para realizar pruebas rápidas, depurar o ejecutar el servidor de la API sin instalarlo como servicio de Windows, ejecute el siguiente comando desde la raíz del proyecto con el entorno virtual activo:
```powershell
.venv_sar\Scripts\activate
python -m uvicorn sar.main_api:app --host 0.0.0.0 --port 8000 --reload
```
* **`--host 0.0.0.0`**: Permite recibir conexiones desde cualquier IP (localhost y subred local).
* **`--port 8000`**: Puerto de escucha del servidor.
* **`--reload`**: Reinicia automáticamente el servidor al detectar cambios en el código de Python.

### 4.5. Administrador del Servidor (SAR_Servidor)
El administrador del sistema puede controlar el estatus del servicio, consultar las sesiones activas, modificar parámetros y visualizar logs en tiempo real mediante el módulo del Administrador del Servidor.

#### 1. Mediante Script de Python:
```powershell
.venv_sar\Scripts\python sar/main_server_manager.py
```

#### 2. Compilar a .exe independiente:
```powershell
# Asegúrese de cerrar cualquier instancia previa de SAR_Servidor.exe antes de compilar
Get-Process | Where-Object { $_.ProcessName -eq "SAR_Servidor" } | Stop-Process -Force -ErrorAction SilentlyContinue

.venv_sar\Scripts\pyinstaller --noconfirm --onedir --windowed --paths=. --icon="sar/src/ui/assets/sar_logo.png" --add-data "sar/src/ui/assets;sar/src/ui/assets" --name="SAR_Servidor" sar/main_server_manager.py
```

---


## 5. Fase 3: Configuración del Firewall de Windows (Servidor)

El Firewall de Windows Defender en la máquina Servidor (`10.11.8.151`) debe permitir tráfico entrante desde el cliente (`10.11.8.108`) tanto para la API como para PostgreSQL en los perfiles de Dominio y Privado.

### 5.1. Regla de Entrada para la API (Puerto 8000)
Autorice al equipo cliente (`10.11.8.108`) a conectarse a la API de FastAPI en los perfiles `Domain,Private`:
```powershell
New-NetFirewallRule -DisplayName "API SAR - Solo Clientes Autorizados" `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 8000 `
    -RemoteAddress "10.11.9.19", "10.11.4.2"

#Revisar la lista del centro firewall y busca cualquier regla que se llame "python" y desactivarlo

### 5.2. Regla de Entrada para PostgreSQL (Puerto 5432)
Autorice al equipo cliente (`10.11.8.108`) a conectarse directamente a la Base de Datos PostgreSQL en los perfiles `Domain,Private`:
```powershell
New-NetFirewallRule -DisplayName "SAR - Base de Datos (Cliente 10.11.8.108)" `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 5432 `
    -Profile Domain,Private `
    -RemoteAddress 10.11.8.108
```

---

## 6. Fase 4: Despliegue y Distribución del Cliente

### 6.1. Archivo de Configuración del Cliente (`settings.json`)
En la carpeta de instalación de cada cliente de escritorio (junto al ejecutable compilado `SAR_Cliente.exe`), se creará un archivo de configuración dinámico para controlar la conexión:

```json
{
  "CONNECT_VIA_API": false,
  "API_URL": "http://127.0.0.1:8000",
  "DB_USER": "postgres",
  "DB_PASSWORD": "",
  "DB_HOST": "127.0.0.1",
  "DB_PORT": "5432",
  "DB_NAME": "db_sar"
}
```
* **`CONNECT_VIA_API`**: Interruptor de seguridad. Si se establece en `false`, el cliente se conecta de forma directa a la base de datos local (comportamiento legacy). Si se cambia a `true`, la autenticación se conmuta automáticamente a la API REST.

---

### 6.2. Compilación del Cliente
Utilice PyInstaller desde el entorno virtual para compilar la aplicación de escritorio especificando la ruta de búsqueda de módulos, el icono del ejecutable `--icon` e incluyendo la carpeta de recursos visuales (iconos/imágenes):
```powershell
.venv_sar\Scripts\pyinstaller --noconfirm --onedir --windowed --paths=. --icon="sar/src/ui/assets/sar_logo.png" --add-data "sar/src/ui/assets;sar/src/ui/assets" --name="SAR_Cliente" sar/main.py
```
Distribuya la carpeta de salida `dist/SAR_Cliente/` (que incluye el ejecutable `SAR_Cliente.exe`, el archivo `settings.json` y los assets empaquetados) a los operadores de la red local.
