# Flujo de AutoFacturación (Benito Juárez)

Este documento detalla el proceso lineal de 5 pasos implementado en **CancunBot** para la automatización de la expedición de facturas en el portal del municipio de Benito Juárez.

## Principios Técnicos (Playwright)
- **Cero Hardcodeo**: Todos los selectores están almacenados en la tabla `localizador_portal` (SAR).
- **Esperas Explícitas**: Se utilizan validaciones visuales (`is_visible()`) y esperas dinámicas para garantizar que los elementos de Angular se hidraten antes de interactuar con ellos.
- **Simulación Humana**: Se utiliza `press_sequentially` para los campos de captura que requieren disparar eventos `ng-change`/`onkeyup` en el framework AngularJS del portal.

## Paso 1: Acceso Inicial
- **Acción:** Llenado del formulario base del ticket.
- **Campos:** RFC, Correo electrónico, Folio del ticket, Importe total.
- **Validación Bot:** Si el portal despliega el mensaje *"El ticket se encuentra facturado"*, el flujo se interrumpe y se reporta estado `ERROR_FACTURA`.

## Paso 2: Datos del Receptor
- **Acción:** Continuar en la pantalla de receptor.
- **Contexto:** El portal precarga los datos fiscales del contribuyente basados en el RFC y valida contra el SAT.

## Paso 3: Datos de Factura
- **Acción:** Selección del Uso del CFDI (Por defecto: *Adquisición de mercancías*).
- **Validación Visual:** El bot detiene su ejecución e inyecta un *overlay* en el navegador pidiendo la confirmación humana de los datos antes de continuar.

## Paso 4: Detalle de Producto y Generación
- **Acción:** Se presenta el resumen de los conceptos (claves SAT, cantidades, IVA). Al presionar *Continuar*, el portal procede inmediatamente al timbrado.
- **Resultado:** El portal ejecuta la generación del CFDI de inmediato.

## Paso 5: Confirmación de Éxito y Descarga
- **Acción:** Aparece un modal emergente de éxito que el bot debe cerrar haciendo clic en el botón "OK".
- **Descarga:** Tras cerrar el modal, el bot localiza los botones de descarga (XML y PDF) y extrae los archivos en el disco local.
