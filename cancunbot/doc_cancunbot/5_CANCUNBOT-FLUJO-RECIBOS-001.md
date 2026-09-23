# Flujo de Descarga de Recibos (Benito Juárez)

Este documento detalla el proceso implementado en **CancunBot** para la automatización de la consulta y descarga de recibos en el portal `https://recibo.tesoreriacancun.com`.

## Principios Técnicos (Playwright)
- **Cero Hardcodeo**: Todos los selectores están almacenados en la tabla `localizador_portal` (SAR).
- **Manejo Dinámico de reCAPTCHA v3**: Se interactúa directamente con la capa de Javascript del portal para ejecutar la validación invisible del captcha.
- **Inyección de Código (Anti-Rate-Limiting)**: El bot inyecta reglas CSS y parches en Javascript para silenciar modales de error de validación e intercepta fallos para enfriar la conexión en caso de estrangulamiento (Rate Limiting).

## Paso 1: Inicialización y Navegación
- **Acción:** El bot navega al portal de recibos.
- **Parcheo de UI:** Se inyectan reglas CSS personalizadas en el DOM para ocultar cualquier ventana emergente de error (`SweetAlert2`) que pudiera interrumpir el flujo visual o la interacción de Playwright.

## Paso 2: Llenado de Datos
- **Formato Inteligente:** Si el folio es electrónico (ej. `F-12345`), el bot elimina automáticamente el prefijo `F-` y utiliza el identificador `CANCUN_RECIBO_INPUT_FOLIO`. Si es pase de caja, utiliza `CANCUN_RECIBO_INPUT_PASE_CAJA`.
- **Eventos:** Se dispara un evento `change` mediante jQuery inyectado para garantizar que los frameworks del portal detecten la escritura.

## Paso 3: Superar reCAPTCHA y Consultar
- **Acción:** En lugar de dar un simple clic, el bot invoca directamente la función nativa `validarCaptcha()` del portal.
- **Manejo de Errores (Reintentos):** Si la consulta falla (debido a demasiados intentos o validación de captcha), el bot ejecuta hasta 3 reintentos progresivos, recargando la página y aplicando tiempos de espera incrementales (Enfriamiento) para renovar el token de sesión.

## Paso 4: Carga de Tabla de Resultados
- **Acción:** El sistema espera de forma asíncrona (AJAX) hasta detectar la renderización de la tabla de resultados (`table.stacktable`) o la disponibilidad de los botones de descarga (`button:has-text('PDF')`).
- **Validación Final:** Si aparece un modal explícito de *Folio no encontrado*, se marca el recibo con estado de error en la base de datos de SAR.

## Paso 5: Descarga de Archivos
- **Acción:** Una vez localizada la tabla, el bot extrae la información y procede a descargar el PDF del recibo, moviéndolo a la carpeta de salida configurada en la sesión del usuario.
