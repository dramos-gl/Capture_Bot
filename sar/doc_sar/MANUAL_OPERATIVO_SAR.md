# 📘 MANUAL DE USUARIO SAR
**Sistema de Administración de Referencias / Derechos**  
**Versión:** 1.0  
**Fecha de Emisión:** Marzo 2026  
**Audiencia:** Operadores de Captura, Asistentes Administrativos, Facturación y Supervisores  

---

## Contenido

1. [Introducción al sistema SAR](#1-introducción-al-sistema-sar)  
   1.1 [¿Qué es SAR?](#11-qué-es-sar)  
   1.2 [Objetivos principales](#12-objetivos-principales)  
   1.3 [Conceptos básicos](#13-conceptos-básicos)  
   1.4 [Flujo general de trabajo](#14-flujo-general-de-trabajo)  
       1.4.1 [Flujo manual de operación de derechos](#141-flujo-manual-de-operación-de-derechos)  
       1.4.2 [Flujo actual automatizado mediante el sistema SAR](#142-flujo-actual-automatizado-mediante-el-sistema-sar)  
2. [Acceso al sistema](#2-acceso-al-sistema)  
   2.1 [Inicio de sesión](#21-inicio-de-sesión)  
   2.2 [Qué hacer ante credenciales incorrectas](#22-qué-hacer-ante-credenciales-incorrectas)  
   2.3 [Cierre de sesión seguro](#23-cierre-de-sesión-seguro)  
3. [Navegación principal y módulos operativos](#3-navegación-principal-y-módulos-operativos)  
   3.1 [Guía Rápida de Módulos](#31-guía-rápida-de-módulos)  
   3.2 [Mapa de navegación visual](#32-mapa-de-navegación-visual)  
   3.3 [Vistas de módulos — Interfaz gráfica del sistema SAR](#33-vistas-de-módulos--interfaz-gráfica-del-sistema-sar)  
       3.3.1 [Interfaz principal y Dashboard](#331-interfaz-principal-y-dashboard)  
       3.3.2 [Opciones del menú lateral](#332-opciones-del-menú-lateral)  
4. [Módulo 1: Control de derechos y órdenes](#4-módulo-1-control-de-derechos-y-órdenes)  
   4.1 [Creación de una Nueva Orden (Paso a Paso)](#41-creación-de-una-nueva-orden-paso-a-paso)  
   4.2 [Consulta de Solicitudes por Orden](#42-consulta-de-solicitudes-por-orden)  
   4.3 [Asignación de Solicitudes a un Usuario Operador](#43-asignación-de-solicitudes-a-un-usuario-operador)  
   4.4 [Ciclo de Vida y Estados de una Orden](#44-ciclo-de-vida-y-estados-de-una-orden)  
       4.4.1 [Edición o Cancelación de Órdenes](#441-edición-o-cancelación-de-órdenes)  
   4.5 [Autorización o Rechazo desde "Procesar Derechos"](#45-autorización-o-rechazo-desde-procesar-derechos)  
   4.6 [Generar Lote de archivos 'Excel y PDF de 299'](#46-generar-lote-de-archivos-excel-y-pdf-de-299)  
5. [Módulo 2: Bot Fase A — AutoGeneración de Derechos](#5-módulo-2-bot-fase-a--autogeneración-de-derechos)  
   5.1 [Ejecución del Bot (Paso a Paso)](#51-ejecución-del-bot-paso-a-paso)  
   5.2 [Supervisión y Monitoreo](#52-supervisión-y-monitoreo)  
   5.3 [Diagnóstico y Solución de Incidencias](#53-diagnóstico-y-solución-de-incidencias)  
6. [Módulo 3: Bot Fase C — AutoFacturación de Derechos](#6-módulo-3-bot-fase-c--autofacturación-de-derechos)  
   6.1 [Ejecución del Bot (Paso a Paso)](#61-ejecución-del-bot-paso-a-paso)  
   6.2 [Supervisión y Monitoreo](#62-supervisión-y-monitoreo)  
   6.3 [Diagnóstico y Solución de Incidencias](#63-diagnóstico-y-solución-de-incidencias)  
7. [Verificación de Archivos y Comprobantes](#7-verificación-de-archivos-y-comprobantes)  
   7.1 [Convención de Nombres y Extensiones](#71-convención-de-nombres-y-extensiones)  
   7.2 [Checklist de Verificación de Archivos](#72-checklist-de-verificación-de-archivos)  
8. [Control de inventario](#8-control-de-inventario)  
   8.1 [Introducción y Estructura por Sub-Pestañas](#81-introducción-y-estructura-por-sub-pestañas)  
   8.2 [Sub-módulo 1: Visor de Inventario de Derechos (`📋 Inventario`)](#82-sub-módulo-1-visor-de-inventario-de-derechos-inventario)  
   8.3 [Sub-módulo 2: Asignación y Validación por Lotes (`⚡ Asignar & Validar por lotes`)](#83-sub-módulo-2-asignación-y-validación-por-lotes-asignar--validar-por-lotes)  
   8.4 [Sub-módulo 3: Reserva de Derechos (`🔑 Reserva de Derechos`)](#84-sub-módulo-3-reserva-de-derechos-reserva-de-derechos)  
   8.5 [Sub-módulo 4: Asignación Individual (`👤 Asignar Derechos`)](#85-sub-módulo-4-asignación-individual-asignar-derechos)  
   8.6 [Sub-módulo 5: Gestión de Lotes y Empaquetado (`📋 Gestión de Asignaciones`)](#86-sub-módulo-5-gestión-de-lotes-y-empaquetado-gestión-de-asignaciones)  
   8.7 [Control de Accesos por Permisos (Fail-Closed)](#87-control-de-accesos-por-permisos-fail-closed)  
9. [Solución de Problemas y Errores Frecuentes](#9-solución-de-problemas-y-errores-frecuentes)  
10. [Las 7 Reglas de Oro del Operador SAR](#10-las-7-reglas-de-oro-del-operador-sar)  

---

# 1. Introducción al sistema SAR

## 1.1 ¿Qué es SAR?
**SAR (Sistema de Administración de Referencias/Derechos)** es una herramienta centralizada de escritorio diseñada para gestionar de forma integral el ciclo de vida de los derechos solicitados.

El sistema permite realizar la captura, control, asignación, procesamiento, generación y facturación automatizada de derechos, manteniendo la trazabilidad de las órdenes, solicitudes y referencias durante todo el proceso.

## 1.2 Objetivos principales
* **Prevención de errores:** Reducir errores de captura, asignación y procesamiento, así como impresiones innecesarias.
* **Automatización confiable:** Automatizar la generación, procesamiento y facturación de derechos, minimizando la intervención manual.
* **Trazabilidad total:** Mantener un control detallado del ciclo de vida de cada orden y derecho, desde su creación hasta su asignación.
* **Control operativo:** Centralizar la administración de referencias y facilitar el seguimiento de su estado.
* **Eficiencia:** Reducir tareas repetitivas y tiempos de operación mediante procesos automatizados.

## 1.3 Conceptos básicos

| Término | Definición Operativa |
| :--- | :--- |
| **Orden / solicitud** | Solicitud principal que agrupa uno o varios derechos/conceptos para una empresa determinada. |
| **Referencia** | Cadena alfanumérica única emitida por el portal externo (Tributanet) que identifica la línea de pago. |
| **Derecho / concepto** | Trámite específico para solicitar (ej. Análisis, Avisos, CLG, etc.). |
| **Lote / folio** | Unidad de inventario asignada a una orden para control interno. |
| **Auto generación / Auto facturación** | Proceso automatizado de generación y timbrado de derechos. |

## 1.4 Flujo general de trabajo

```
Acceso al Sistema ➔ Crear Orden ➔ Bot Fase A: Genera derechos ➔ Control de derechos Genera lotes Excel y PDF (299) ➔ Autorización ➔ Bot Fase C: Auto facturación ➔ Inventario ➔ Reservas y asignación de derechos ➔ Fin
```

### 1.4.1 Flujo manual de operación de derechos
*(Véase diagrama comparativo de proceso tradicional)*

### 1.4.2 Flujo actual automatizado mediante el sistema SAR
*(Véase arquitectura de automatización SAR)*

---

# 2. Acceso al sistema

## 2.1 Inicio de sesión
Abre el sistema ejecutando el acceso directo **SAR_Cliente** desde tu escritorio o la ruta asignada por TI, y sigue estos pasos:
1. Selecciona el módulo al que deseas ingresar.
2. Ingresa tus credenciales: escribe tu **Nombre de Usuario** y **Contraseña**.
3. Inicia sesión: haz clic en el botón **Iniciar sesión**.
*(Opcional: Si deseas salir antes de entrar, haz clic en Cancelar para cerrar la aplicación).*

> 📸 **[Imagen 1: ventana de inicio de sesión ‘SAR Login’]**  
> 📸 **[Imagen 2: ventana de inicio de sesión con módulos desplegados ‘SAR Login’]**

## 2.2 Qué hacer ante credenciales incorrectas
Si aparece el mensaje: *"Credenciales inválidas o usuario inactivo"*:
* **Verifica tus datos:** Asegúrate de que el usuario y la contraseña estén bien escritos (revisa mayúsculas, minúsculas y bloqueos de teclado).
* **Contacta a soporte:** Si el error persiste tras 3 intentos, solicita el restablecimiento de tu contraseña con el Administrador de TI.

## 2.3 Cierre de sesión seguro
Al terminar tus actividades en cualquier módulo, cierra tu sesión para liberar los bloqueos temporales del sistema. Puedes hacerlo de tres formas:
1. Haz clic directo en el botón **Cerrar sesión**.
2. Haz clic en tu nombre de usuario (esquina superior derecha) y selecciona **Cerrar sesión**.
3. Cierra la ventana principal de la aplicación.

> [!IMPORTANT]
> Salir correctamente garantiza que los registros queden desbloqueados y listos para otros usuarios.

---

# 3. Navegación principal y módulos operativos

La pantalla principal de SAR se organiza en tres áreas:
1. **Barra superior:** métricas en tiempo real.
2. **Menú lateral:** navegación entre los distintos módulos del sistema.
3. **Área central:** espacio de trabajo donde se gestionan los datos y formularios.

## 3.1 Guía Rápida de Módulos
Localiza rápidamente el módulo correspondiente a la operación que necesitas ejecutar:

| ¿Qué tarea necesitas realizar? | Módulo correspondiente |
| :--- | :--- |
| Crear órdenes nuevas, consultar estatus, autorizar o asignar derechos y generar reportes | 📁 **Control de derechos** |
| Ejecutar la generación automática de derechos en Tributanet | 🤖 **Bot Fase A — AutoGeneración de Derechos** |
| Timbrar y descargar facturas de derechos autorizados | 🤖 **Bot Fase C — AutoFacturación de Derechos** |
| Administrar inventario de derechos facturados, reservas y asignaciones masivas | 📦 **Control de inventario** |

## 3.2 Mapa de navegación visual
Diagrama panorámico de la aplicación para ubicar los módulos y herramientas automatizadas según su función en el flujo de trabajo.

## 3.3 Vistas de módulos — Interfaz gráfica del sistema SAR
Al ingresar, el sistema despliega por defecto el Tablero de Control Operativo (Dashboard) con las métricas clave y los registros recientes. En el costado izquierdo se encuentra el menú lateral permanente para navegar entre las secciones del sistema.

### 3.3.1 Figura: Interfaz principal y Dashboard del módulo Control de Derechos.

### 3.3.2 Opciones del menú lateral

| Sección | Descripción y funciones principales |
| :--- | :--- |
| **Dashboard** | Resumen operativo general: tarjetas de métricas en tiempo real (generados, pendientes, autorizados, errores) y tabla de últimos derechos generados. |
| **Órdenes** | Gestión del ciclo de vida de órdenes: captura, consulta, edición, autorización/rechazo, asignación a responsables y exportación de archivos (Excel/PDF). |
| **Derechos** | Consulta y seguimiento individual de los derechos procesados: detalle, validación de estatus y cambios de estado según reglas de negocio. |
| **Control de Derechos** | Administración del inventario de derechos: consulta de disponibilidad, asignaciones individuales o masivas, apartados (notarías/colaboradores) y reportes. |
| **Cambiar Tema** | Alterna la apariencia visual de la interfaz entre Modo claro y Modo oscuro sin alterar datos ni operaciones. |
| **Cerrar Sesión** | Finaliza la sesión de trabajo liberando los bloqueos temporales del usuario activo. |

---

# 4. Módulo 1: Control de derechos y órdenes

El módulo **SAR – Control de Derechos** es el centro operativo del sistema para registrar, administrar, supervisar y controlar todo el ciclo de vida de las órdenes y derechos.

## 4.1 Creación de una Nueva Orden (Paso a Paso)

> [!CAUTION]
> **REGLA DE ORO (Validación Previa Obligatoria):**  
> Antes de registrar una orden, confirma que los datos fiscales de cada empresa sean 100% correctos. Los bots de automatización (Bot Fase A y Bot Fase C) generarán y facturarán los derechos tomando exactamente la información registrada en el sistema.

### Lista de Chequeo Previo:
* [ ] La empresa está registrada en el sistema y activa.
* [ ] El RFC coincide carácter por carácter con la Cédula Fiscal.
* [ ] El domicilio registrado en el sistema es idéntico a la cédula fiscal.

### Procedimiento de captura:
1. Iniciar sesión en el módulo **Control de Derechos**.
2. En el menú lateral, ve a: **Órdenes ➔ Capturar Nueva Orden**.
3. **Municipio:** Selecciona el municipio disponible (por defecto: `BENITO JUAREZ`).
4. **Descripción:** Escribe una referencia clara para la orden (ejemplo: *Subsidios septiembre 2026*).
5. **Agregar renglones (solicitudes):**
   * Selecciona: **Empresa ➔ Delegación ➔ Concepto**.
   * Escribe la cantidad de derechos a tramitar.
   * Agrega los renglones necesarios según tu trámite.
6. **Guardar:** Haz clic en **Guardar** y confirma en el cuadro de diálogo para registrar la orden.

> 📌 **Reglas de captura:**  
> * 1 renglón = 1 solicitud. Una orden puede contener una o múltiples solicitudes.  
> * Se debe registrar un renglón por cada combinación de Empresa + Delegación + Concepto. No se permiten renglones duplicados.  
> * Cada solicitud creada deberá asignarse a un usuario operador (worker) para su posterior procesamiento automático.

## 4.2 Consulta de Solicitudes por Orden
1. En el menú lateral, selecciona: **Órdenes ➔ Solicitudes**.
2. Por defecto, la pantalla carga las solicitudes correspondientes a la última orden registrada.
3. Para consultar solicitudes de una orden anterior, haz clic en el icono de **Filtro** y selecciona la orden deseada.

## 4.3 Asignación de Solicitudes a un Usuario Operador
Para que el **Bot Fase A — AutoGeneración de Derechos** pueda tramitar los derechos ante Tributanet, la solicitud debe estar asignada a un usuario.
1. Identifica la solicitud en estado `PENDIENTE` (indica que sus derechos aún no se han generado).
2. Haz clic en el botón **Asignar Usuario**.
3. Elige al usuario responsable (worker) de la lista desplegable y pulsa **OK / Aceptar**.
4. La solicitud cambiará a estado `ASIGNADA`.

> 💡 **Transición automática:**  
> En cuanto el Bot Fase A finalice con éxito la generación de la totalidad de derechos de la solicitud, cada derecho generado pasará automáticamente al estado `PENDIENTE_AUTORIZACION`.

## 4.4 Ciclo de Vida y Estados de una Orden

Las órdenes transitan por los siguientes estados dentro del flujo operativo:

```
[ PENDIENTE ] ──▶ [ ABIERTA ] ──▶ [ PENDIENTE_AUTORIZACION ] ──▶ [ AUTORIZADA ] ──▶ (Bot Fase C: Timbrado) 
                                                               └──▶ [ RECHAZADA ]  ──▶ (Fin de ciclo)
```

| Estado | Significado y Acciones Permitidas |
| :--- | :--- |
| **PENDIENTE** | Orden recién capturada. Sus solicitudes aún no han sido asignadas. |
| **ABIERTA** | Al menos una de sus solicitudes ya fue asignada a un usuario operador. |
| **PENDIENTE_AUTORIZACION** | El Bot Fase A terminó de generar todos los derechos. La orden queda a la espera del dictamen de la Autoridad Externa. |
| **AUTORIZADA** | La autoridad externa aprobó la totalidad de los derechos. Queda lista para timbrado y descarga mediante el Bot Fase C — AutoFacturación. |
| **RECHAZADA** | La autoridad externa no autorizó los derechos dentro de su vigencia (último día del mes de generación). Los derechos expiran y el trámite debe reiniciarse desde una nueva orden. |

### 4.4.1 ✏️ Edición o Cancelación de Órdenes:
Solo se pueden editar o cancelar órdenes que se encuentren en estado `PENDIENTE` o `ABIERTA`, siempre y cuando no tengan derechos descargados. Editar una orden permite ampliar la cantidad de derechos solicitados.

## 4.5 Autorización o Rechazo desde "Procesar Derechos"
Para autorizar o rechazar solicitudes específicas de una orden:
1. **Acceso:** Puedes ingresar por cualquiera de estas dos vías:
   * Hacer doble clic sobre una orden en la ventana general de órdenes.
   * Hacer doble clic sobre la columna **Folio Orden** en la vista de solicitudes.
2. Se abrirá la ventana emergente **Procesar Derechos**.
3. Selecciona las solicitudes deseadas y utiliza los botones **Autorizar** o **Rechazar** según la respuesta oficial recibida.

## 4.6 Generar Lote de archivos ‘Excel y PDF de 299’
Esta herramienta genera los paquetes documentales requeridos para el expediente de solicitud ante la autoridad externa.

> [!IMPORTANT]
> **Requisito indispensable:** TODOS los derechos vinculados a la orden deben estar generados y en estado `PENDIENTE_AUTORIZACION`.

### Procedimiento:
1. Dentro de la ventana **Procesar Derechos**, haz clic en el botón **Generar Excel y PDF**.
2. Confirma la acción en el cuadro de diálogo emergente.
3. Selecciona la carpeta de destino donde se guardarán los paquetes organizados en bloques de hasta 299 registros.

> ⏳ **Nota sobre rendimiento:**  
> La compilación y armado de los archivos PDF requiere mayor tiempo de procesamiento debido al volumen y consolidación de documentos. Evita cerrar la ventana hasta que el sistema confirme la finalización.

---

# 5. Módulo 2: Bot Fase A — AutoGeneración de Derechos

El **Bot Fase A (AutoGeneración de Derechos)** es el componente automatizado encargado de interactuar con la plataforma externa Tributanet de forma autónoma y controlada: captura los datos de la solicitud, tramita la referencia oficial de pago y descarga el comprobante del derecho en formato PDF.

## 5.1 Ejecución del Bot (Paso a Paso)

> [!CAUTION]
> **Validación Previa Obligatoria:**  
> Antes de arrancar la ejecución, confirma en el apartado ‘CONTROLES OPERATIVOS’ que la ruta de almacenamiento predefinida muestre el estado **CONECTADO**. Si aparece desconectada o en error, repórtalo de inmediato al Administrador del Sistema.

### Procedimiento de arranque:
1. **Ingreso:** Accede al módulo **Bot Fase A — AutoGeneración de Derechos**.
2. **Seleccionar solicitud:** La pantalla mostrará las solicitudes en estado `ASIGNADA` listas para trámite. Carga la solicitud correspondiente mediante cualquiera de estas vías:
   * Selecciona el registro y haz clic en **Cargar Solicitud Seleccionada**.
   * Haz doble clic directo sobre la solicitud deseada.
3. **Iniciar proceso:** Haz clic en el botón **▶️ Iniciar Bot**.
4. **Confirmación:** Confirma la acción en el cuadro de diálogo emergente.
5. **Procesamiento autónomo:** Al iniciar, el bot opera de forma 100% autónoma sobre la solicitud seleccionada. El proceso concluye cuando se genera la totalidad de los derechos solicitados, momento en el cual el sistema actualiza de manera automática:
   * El estado de la solicitud a `PENDIENTE_AUTORIZACIÓN`.
   * El estado individual de cada una de las referencias/derechos vinculados a `PENDIENTE_AUTORIZACIÓN`.

> 🔒 **Bloqueo operativo durante la ejecución:**  
> Una vez iniciado, el bot trabaja de manera 100% autónoma. Por seguridad operativa, todas las funciones de la ventana se deshabilitarán temporalmente, quedando activo únicamente el botón **⏹️ Detener Bot**, el cual permite pausar o cancelar el proceso de forma segura.

## 5.2 Supervisión y Monitoreo
Durante la operación automática, el operador debe vigilar los indicadores de avance:
* **Barra de Progreso:** Indica visualmente el avance respecto al total de derechos de la solicitud cargada.
* **Bitácora de Eventos (Consola de Logs):** Despliega en la parte inferior el registro en tiempo real de cada acción efectuada en el portal externo (inicio de trámite, captura, obtención de folio y guardado de archivo).
* **Estado de actividad:** No cierres ni minimices forzadamente la aplicación mientras el indicador de estado muestre `Procesando...`.

## 5.3 Diagnóstico y Solución de Incidencias

> ⚠️ **Interrupciones en el servicio:**  
> Durante el procesamiento pueden presentarse desconexiones o fallas de comunicación con la plataforma externa. Si el bot se detiene por un error de conexión, valida primero el acceso al portal de forma manual desde un navegador web y, una vez restablecido el servicio, vuelve a iniciar el bot más tarde para continuar el proceso desde donde se pausó.

| Situación / Incidencia | Causa probable | Acción correctiva |
| :--- | :--- | :--- |
| **Lentitud o tiempo de espera (Timeout)** | Sobrecarga en los servidores de Tributanet. | El sistema ejecutará automáticamente hasta 3 intentos de reconexión antes de suspender la tarea. |
| **Detención en color rojo (Error crítico)** | Bloqueo o rechazo en la plataforma externa. | Revisa la Bitácora de Eventos. Ejemplos habituales:<br>• *"Portal Tributanet no disponible"*: Suspende y reintenta más tarde.<br>• *"RFC registrada de forma incorrecta"* |
| **Interrupción manual voluntaria** | Necesidad de pausar la tarea por parte del usuario. | Haz clic en **⏹️ Detener Bot**. El sistema esperará a concluir el derecho que esté procesando en ese instante para evitar inconsistencias y guardará el avance obtenido. |

---

# 6. Módulo 3: Bot Fase C — AutoFacturación de Derechos

El **Bot Fase C (AutoFacturación de Derechos)** procesa de forma automatizada las solicitudes `AUTORIZADAS`, ejecutando el timbrado fiscal y descargando los comprobantes digitales correspondientes (archivos PDF).

## 6.1 Ejecución del Bot (Paso a Paso)

> [!CAUTION]
> **Validación Previa Obligatoria:**  
> Antes de arrancar la ejecución, confirma en el apartado ‘CONTROLES OPERATIVOS’ que la ruta de almacenamiento predefinida muestre el estado **CONECTADO**. Si aparece desconectada o en error, repórtalo de inmediato al Administrador del Sistema.

1. **Ingreso:** Entra al módulo **Bot Fase C — AutoFacturación de Derechos**.
2. **Seleccionar solicitud:** La pantalla mostrará las solicitudes en estado `AUTORIZADA`, listas para procesar. Carga la solicitud correspondiente mediante cualquiera de estas vías:
   * Selecciona una solicitud para facturación y haz clic en **Cargar Solicitud Seleccionada**.
   * Haz doble clic directo sobre la solicitud deseada.
3. **Iniciar proceso:** Haz clic en el botón **▶️ Iniciar Bot**.
4. **Confirmación:** Confirma la acción en el cuadro de diálogo emergente.
5. **Procesamiento autónomo:** Al iniciar, el bot opera de forma 100% autónoma sobre la solicitud seleccionada. El proceso concluye cuando se genera la totalidad de los derechos AUTORIZADOS, momento en el cual el sistema actualiza de manera automática:
   * El estado de la solicitud a `FACTURADA`.
   * El estado individual de cada una de las referencias/derechos vinculados a `FACTURADA`. Los derechos/referencias timbrados y descargados al cambiar al estado `FACTURADA` automáticamente pasan a ser parte del **INVENTARIO**.

> 🔒 **Bloqueo operativo durante la ejecución:**  
> Una vez iniciado, el bot trabaja de manera 100% autónoma. Por seguridad operativa, todas las funciones de la ventana se deshabilitarán temporalmente, quedando activo únicamente el botón **⏹️ Detener Bot**, el cual permite pausar o cancelar el proceso de forma segura.

## 6.2 Supervisión y Monitoreo
Durante la operación automática, el operador debe vigilar los indicadores de avance:
* **Barra de Progreso:** Indica visualmente el avance respecto al total de derechos de la solicitud cargada.
* **Bitácora de Eventos (Consola de Logs):** Despliega en la parte inferior el registro en tiempo real de cada acción efectuada en el portal externo (inicio de trámite, captura, obtención de folio y guardado de archivo).
* **Estado de actividad:** No cierres ni minimices forzadamente la aplicación mientras el indicador de estado muestre `Procesando...`.

## 6.3 Diagnóstico y Solución de Incidencias

| Situación / Incidencia | Causa probable | Acción correctiva |
| :--- | :--- | :--- |
| **Lentitud o tiempo de espera (Timeout)** | Sobrecarga en los servidores de Tributanet. | El sistema ejecutará automáticamente hasta 3 intentos de reconexión antes de suspender la tarea. |
| **Detención en color rojo (Error crítico)** | Bloqueo o rechazo en la plataforma externa. | Revisa la Bitácora de Eventos. Ejemplos habituales:<br>• *"Portal Tributanet no disponible"*: Suspende y reintenta más tarde.<br>• *"RFC registrado de forma incorrecta"* |
| **Interrupción manual voluntaria** | Necesidad de pausar la tarea por parte del usuario. | Haz clic en **⏹️ Detener Bot**. El sistema esperará a concluir el derecho que esté procesando en ese instante para evitar inconsistencias y guardará el avance obtenido. |
| **ERROR DE VALIDACION DERECHO NO AUTORIZADO** | El portal rechaza el derecho por vigencia o validación externa. | Los derechos procesados NO AUTORIZADOS en el portal cambiarán de estado a `ERROR_VALIDACION`. |

---

# 7. Verificación de Archivos y Comprobantes

> [!IMPORTANT]
> **Regla de cierre de órdenes/solicitudes/referencias:**  
> Ninguna orden debe darse por finalizada sin haber comprobado físicamente en disco la existencia, integridad y legibilidad de sus archivos generados.  
> Esta validación es obligatoria para ambos procesos de automatización:  
> * **AutoGeneración de Derechos (Bot Fase A):** verificación de boletas de pago en PDF.  
> * **AutoFacturación de Derechos (Bot Fase C):** verificación de facturas timbradas en PDF.

## 7.1 Convención de Nombres y Extensiones
Verificar la estructura del orden de los archivos descargados y el renombrado correcto:

| Tipo de Archivo | Formato | Ejemplo de Nombre | Ubicación Recomendada |
| :--- | :---: | :--- | :--- |
| **Boleta de Pago** | `.pdf` | `BOLETA_ORD142_REF88392.pdf` | `Q:\BOT\Boletas\` |
| **Factura Fiscal** | `.pdf` | `FACTURA_F29384.pdf` | `Q:\BOT\Facturas\` |

## 7.2 Checklist de Verificación de Archivos
Antes de dar por concluida la automatización, valida la siguiente lista de verificación:
- [ ] **Descarga física:** El archivo se encuentra guardado en la carpeta de destino designada.
- [ ] **Integridad técnica:** El tamaño del archivo es superior a 0 KB (sin descargas incompletas ni archivos dañados).
- [ ] **Consistencia fiscal:** El RFC y la Razón Social impresos en el PDF coinciden carácter por carácter con la orden capturada.
- [ ] **Validación de importes:** El importe total reflejado en el comprobante coincide con el desglose autorizado.

---

# 8. Control de inventario

El módulo **Control de Derechos e Inventario** es el centro operativo para administrar, consultar, reservar, asignación por lotes o individual y empaquetar las referencias que se encuentran en estado `FACTURADA`.

> 📸 **[Captura de Pantalla recomendada: Vista principal del Módulo Control de Derechos e Inventario mostrando las 5 sub-pestañas operativas y la barra de herramientas]**

---

## 8.1 Estructura del Módulo y Navegación por Sub-Pestañas

El módulo se compone de **5 sub-pestañas operativas especializadas**:

| Sub-Pestaña | Descripción Funcional | Perfil Principal |
| :--- | :--- | :--- |
| 📋 **Inventario (Visor)** | Consulta general de referencias facturadas, filtrado multidimensional, tarjetas KPI, asignación en bloque y exportación. | Operador / Supervisor |
| ⚡ **Asignar & Validar por lotes** | Carga masiva en Excel con validación previa de folios electrónicos y 3 modalidades operativas (Asignar, Completar o Reservar). | Coordinador / Admin |
| 🔑 **Reserva de Derechos** | Bloqueo o apartado formal de bloques de folios por Notaría/Desarrollo sin cliente final inicial. | Administrador |
| 👤 **Asignar Derechos** | Asignación individual y puntual de referencias a Notaría, Colaborador o Cliente. | Operador / Supervisor |
| 📋 **Gestión de Asignaciones** | Auditoría histórica de lotes creados, edición de expedientes y descarga empaquetada de archivos Excel y PDF unificados. | Supervisor / Admin |

---

## 8.2 Sub-módulo 1: Visor de Inventario (`📋 Inventario`)

Permite examinar el inventario global de referencias timbradas y realizar búsquedas o asignaciones inmediatas.

### 8.2.1 Filtros y Búsqueda Multidimensional
* **Filtro de Estado:** Opciones desplegables para filtrar por `Todos`, `Disponible`, `Asignada` o `Reservadas`.
* **Filtro de Empresa / RFC:** Selección por cédula fiscal de la empresa titular.
* **Filtro de Concepto / Derecho:** Selección del trámite (*Análisis*, *Primer Aviso*, *CLG*, etc.).
* **Filtros de Fechas y Orden:** Rango de fechas de facturación y acotamiento por folios de orden específicos.
* **Campo de Búsqueda de Texto & Botón 🔍 Buscar:** Búsqueda en tiempo real por número de referencia o folio.
* **Botón 🔄 Actualizar:** Refresca los registros de la tabla y recalcula los contadores de inventario.

### 8.2.2 Tarjetas de Métricas KPI y Diálogo Analítico
* **Contadores KPI Superiores:** Visualización inmediata de *Total Inventario*, *Disponibles*, *Reservadas* y *Asignadas*.
* **Botón 📊 Métricas & Producción:** Al hacer clic, abre la ventana emergente analítica (*Metrics Dashboard Dialog*) con gráficas acumuladas por empresa, concepto y delegación.

### 8.2.3 Interacción con la Tabla de Datos y Acciones
* **Selección Múltiple (Checkboxes):** Marca las casillas de verificación en las filas deseadas y haz clic en el botón **👤 Asignar Seleccionados** para abrir el flujo de asignación en bloque.
* **Doble Clic en Fila (Detalle del Derecho):** Al hacer doble clic sobre cualquier referencia, el sistema abre la ventana emergente de **Detalle del Derecho**, mostrando los datos de facturación, folio de orden, comprobante XML/PDF vinculado e historial de estados.
* **Exportar a Excel:** Haz clic en **📊 Exportar Excel** para descargar la relación filtrada en formato `.xlsx`.

---

## 8.3 Sub-módulo 2: Asignación y Validación por Lotes (`⚡ Asignar & Validar por lotes`)

Esta herramienta procesa archivos Excel para cruzar folios electrónicos y acreditar referencias masivamente de forma asíncrona (`BatchValidationWorker`).

### 8.3.1 Modalidades Operativas (Casillas de Verificación / Checks)
Antes de cargar el archivo, define el modo de operación seleccionando o desmarcando las casillas superiores:

1. **Modo 1: Asignación Directa por Lote (Sin seleccionar ningún check)**
   * **Uso:** Crea un nuevo lote asignado directamente a una Notaría o Colaborador vinculando clientes y folios electrónicos finales.
2. **Modo 2: Check `Completar lote reservado` [ ☑ ]**
   * **Uso:** Selecciona este check cuando vayas a cargar un Excel para completar los datos definitivos de acreditados/escrituras de un lote que fue reservado con anterioridad.
3. **Modo 3: Check `Reservar derechos` [ ☑ ]**
   * **Uso:** Selecciona este check para cargar un Excel y apartar/reservar derechos en bloque para una Notaría o Desarrollo sin asignar nombres de clientes finales aún.

### 8.3.2 Formulario de Datos del Lote (2 Columnas Simétricas)
* **Fila 1:**
  * **Tipo Destino \*:** Selección entre `NOTARIA` o `COLABORADOR`.
  * **Destinatario \*:** Selector desplegable de la Notaría o Colaborador según el tipo elegido.
* **Fila 2:**
  * **Solicitante Externo (Persona):** Captura opcional del responsable o contacto externo.
  * **Observaciones del Lote:** Notas y justificaciones adicionales para el expediente del lote.

*(Nota: La empresa/RFC se resuelve de forma automática y transparente a partir de la columna del Excel o del número de referencia física, por lo que no requiere selección manual previa).*

### 8.3.3 Barra de Acciones Estandarizada
Los botones de operación se ubican alineados en una sola barra horizontal en el siguiente orden secuencial:

$$\mathbf{Importar\ Excel} \longrightarrow \mathbf{Descargar\ Plantilla} \longrightarrow \mathbf{Confirmar} \longrightarrow \mathbf{Limpiar} \longrightarrow \mathbf{Filtrar\ \acute{O}rdenes\ (\nabla)}$$

1. **Botón 📊 Importar Excel:** Abre el explorador para cargar el archivo `.xlsx`. Al seleccionarlo, se ejecuta la validación asíncrona automática (`BatchValidationWorker`) con diálogo de progreso circular (`GLLoadingDialog`).
2. **Botón 📄 Descargar Plantilla:** Descarga el formato oficial estructurado (`Plantilla_Control_Inventario.xlsx`).
3. **Botón 💾 Confirmar:** Procesa formalmente la asignación masiva en base de datos tras verificar la previsualización.
4. **Botón 🧹 Limpiar:** Limpia la tabla de previsualización y reinicia el archivo seleccionado.
5. **Botón 🔍 Filtrar Órdenes ($\nabla$):** Menú persistente desplegable para acotar la asignación a una o más órdenes específicas.

### 8.3.4 Previsualización y Diagnóstico
* La tabla inferior muestra el semáforo de validación en tiempo real:
  * **Verde (🟢 CORRECTO):** Folio existente, disponible y datos válidos.
  * **Rojo (🔴 ERROR):** Folio no encontrado, ya asignado o discrepancia de datos.
  * **Amarillo (🟡 WARNING):** Advertencias no bloqueantes.

---

## 8.4 Sub-módulo 3: Reserva de Derechos (`🔑 Reserva de Derechos`)

Permite apartar formalmente bloques de folios para Notarías o Desarrollos Inmobiliarios sin asignar nombres de acreditados finales.

### 8.4.1 Formulario y Barra de Acciones Estandarizada
1. Ve a la pestaña **🔑 Reserva de Derechos**.
2. **Formulario Superior (2 Columnas Simétricas - Altura 36px):**
   * **Columna 1:** Notaría Destino \*, Desarrollo Inmobiliario.
   * **Columna 2:** Solicitante Externo (Persona), Observaciones.
3. **Barra de Acciones en la Cabecera de Partidas:**
   $$\mathbf{Agregar} \longrightarrow \mathbf{Confirmar} \longrightarrow \mathbf{Limpiar} \longrightarrow \mathbf{Filtrar\ \acute{O}rdenes\ (\nabla)}$$
   * **➕ Agregar:** Inserta una nueva fila de partida (Empresa, Delegación, Concepto, Cantidad a Reservar).
   * **💾 Confirmar:** Aplica la reserva en base de datos marcando los folios como `RESERVADA`.
   * **🧹 Limpiar:** Limpia las partidas agregadas y reinicia el formulario.
   * **🔍 Filtrar Órdenes ($\nabla$):** Acota la reserva a órdenes seleccionadas.

---

## 8.5 Sub-módulo 4: Asignación Individual (`👤 Asignar Derechos`)

Permite gestionar asignaciones directas de derechos mediante captura interactiva de partidas.

### 8.5.1 Formulario y Barra de Acciones Estandarizada
1. Ingresa a **👤 Asignar Derechos**.
2. **Formulario Superior (2 Columnas Simétricas - Altura 36px):**
   * **Columna 1:** Tipo Destino \*, Destinatario (Notaría / Colaborador) \*.
   * **Columna 2:** Solicitante Externo (Persona), Observaciones.
3. **Barra de Acciones en la Cabecera de Partidas:**
   $$\mathbf{Agregar} \longrightarrow \mathbf{Buscar} \longrightarrow \mathbf{Continuar} \longrightarrow \mathbf{Limpiar} \longrightarrow \mathbf{Filtrar\ \acute{O}rdenes\ (\nabla)}$$
   * **➕ Agregar:** Inserta una partida interactiva.
   * **🔍 Buscar:** Valida existencias y disponibilidad en tiempo real.
   * **➡️ Continuar:** Despliega el formulario de ubicación (Mz, Lote, Edif, Viv) y cliente.
   * **🧹 Limpiar:** Restablece las partidas y campos.
   * **🔍 Filtrar Órdenes ($\nabla$):** Filtra por órdenes de generación.

---

## 8.6 Sub-módulo 5: Gestión de Lotes y Empaquetado (`📋 Gestión de Asignaciones`)

Permite consultar el historial completo de lotes de asignación creados, editar expedientes y descargar los paquetes documentales finales.

### 8.6.1 Filtros y Tabla de Lotes Históricos
* Filtra la lista por **Rango de Fechas**, **Notaría / Colaborador Destino**, **Solicitante** o **Estatus del Lote**.
* Visualiza en la tabla el ID del Lote, fecha de creación, usuario responsable, total de referencias y estado.

### 8.6.2 Detalle de Asignación (Edición de Expedientes)
* Selecciona un lote y haz clic en **👁️ Detalle de Asignación**.
* Se abrirá la ventana emergente mostrando la lista completa de referencias del lote, permitiendo editar datos de escrituras, folios electrónicos o comentarios individuales.

### 8.6.3 Generación de Excel y Paquete de PDFs
* **Botón 📊 Generar Excel:** Crea la hoja de relación del lote en formato `.xlsx` estructurado para envío a la notaría o cliente.
* **Botón 📄 Generar PDF (Motor `PdfWorker`):**  
  Al presionar este botón, el motor asíncrono en segundo plano unifica y consolida los comprobantes PDF por desarrollo y concepto, renombrando cada archivo bajo la regla oficial de notaría:  
  `[Consecutivo]_[Referencia]_[Notaría]_[Concepto]_[Delegación].pdf`  
  *(Ejemplo: `001_REF88392_Not14_Aviso_CUN.pdf`)*.

---

## 8.7 Control de Accesos por Permisos (Fail-Closed)

> [!CAUTION]
> El acceso a las pestañas y acciones de este módulo está regulado de forma atómica por el motor de seguridad SAR bajo el principio **Fail-Closed**:
> * `CTRL:INVENTARIO:ASIGNAR`: Habilita el botón *Asignar Seleccionados* y asignaciones directas.
> * `CTRL:ASIGNAR_VALIDAR:LEER`: Habilita la pestaña *⚡ Asignar & Validar por lotes*.
> * `CTRL:RESERVA_DERECHO:LEER`: Habilita la pestaña *🔑 Reserva de Derechos*.  
> Si tu usuario no tiene estos permisos concedidos, los botones y pestañas se mostrarán inhabilitados (en gris). Solicita la asignación de roles al Administrador de TI.

---

# 9. Solución de Problemas y Errores Frecuentes

| Caso | Causa probable | Solución |
| :--- | :--- | :--- |
| **Caso 1: "RFC o Domicilio Fiscal no coincide"** | Datos capturados diferentes a la Cédula de Identificación Fiscal. | Cancela la captura actual, verifica la Cédula Fiscal física o solicita al Administrador actualizar el catálogo de empresas antes de volver a crear la orden. |
| **Caso 2: "Sin inventario / folios disponibles para el concepto"** | Se agotaron los paquetes de folios precargados para ese tipo de derecho. | Monitoreo constante del inventario para anticipar nuevas solicitudes y notificar al Administrador. |
| **Caso 3: "Error de Conexión con Tributanet en Bot Fase A"** | Caída temporal del portal gubernamental o interrupción de internet. | Esperar y realizar monitoreo manual mediante *Reintentar*. Si el portal externo sigue caído, pausa la cola de trabajo y notifica a supervisión. |
| **Caso 4: "Comprobante / PDF no aparece en la carpeta"** | La ruta de red no está disponible o no se tienen permisos de escritura. | Verifica que la unidad de red esté conectada en Windows (`Q:\` o ruta UNC). Vuelve a ejecutar la descarga individual desde la tabla de órdenes. |

---

# 10. Las 7 Reglas de Oro del Operador SAR

1. 🔍 **Verifica siempre el RFC y la Empresa** antes de hacer clic en Guardar.
2. 🚫 **No repitas clics en "Iniciar Bot"** si la barra de progreso ya está en marcha.
3. 👁️ **Revisa las referencias generadas** antes de proceder a la Autorización.
4. 📝 **Registra siempre un motivo claro** cuando tengas que rechazar una orden.
5. 📂 **Comprueba que los archivos PDF existan físicamente** y no pesen 0 KB.
6. 🔒 **Cierra tu sesión** al retirarte de tu equipo de cómputo.
7. ⚠️ **Ante cualquier comportamiento anómalo**, no intentes forzar procesos; avisa de inmediato a soporte.
