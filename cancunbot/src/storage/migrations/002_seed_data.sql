-- =============================================================================
-- CANCUNBOT: Seed Data - Datos Iniciales del Sistema
-- Versión: 1.0 | Fecha: 2026
-- Ejecutar DESPUÉS de 001_initial_schema.sql
-- =============================================================================


-- =============================================================================
-- ESTADOS DEL SISTEMA
-- =============================================================================

INSERT INTO cancunbot_catalogo.estado_sistema (entidad, codigo, descripcion) VALUES

-- Estados de SOLICITUD
('SOLICITUD', 'NUEVA',         'Solicitud recién creada, sin procesar'),
('SOLICITUD', 'EN_PROCESO',    'Bot procesando los folios de la solicitud'),
('SOLICITUD', 'COMPLETADA',    'Todos los folios fueron procesados exitosamente'),
('SOLICITUD', 'CON_ERRORES',   'Procesada con errores en algunos folios'),

-- Estados de FOLIO
('FOLIO', 'PENDIENTE',         'Folio en espera de descarga por Bot A'),
('FOLIO', 'DESCARGANDO',       'Bot A descargando el recibo del portal'),
('FOLIO', 'DESCARGADO',        'Recibo descargado y datos extraídos correctamente'),
('FOLIO', 'ERROR_DESCARGA',    'Error al consultar o descargar el recibo del portal'),

-- Estados de RECIBO
('RECIBO', 'CAPTURADO',        'Datos del recibo extraídos y guardados en BD'),
('RECIBO', 'PENDIENTE_FACTURAR', 'Recibo listo para proceso de facturación'),
('RECIBO', 'FACTURANDO',       'Bot C generando la factura en el portal'),
('RECIBO', 'FACTURADO',        'Factura generada y descargada exitosamente'),
('RECIBO', 'ERROR_FACTURA',    'Error al generar la factura en el portal');


-- =============================================================================
-- PARÁMETROS DE SISTEMA
-- =============================================================================

INSERT INTO cancunbot_configuracion.parametro_sistema (codigo, valor, descripcion) VALUES

('PORTAL_RECIBO_URL',
 'https://recibo.tesoreriacancun.com',
 'URL base del portal de recibos electrónicos de Tesorería Cancún'),

('PORTAL_FACTURA_URL',
 'https://benitojuarez.expidefactura.com/',
 'URL base del portal de facturación electrónica Benito Juárez'),

('PDF_BASE_PATH',
 'PDF_Recibos',
 'Ruta base (relativa al proyecto) para almacenar PDFs de recibos'),

('PDF_NAMING_PATTERN',
 '{folio_electronico}',
 'Patrón de renombrado del PDF. Tokens: {folio_electronico}, {folio_pase_caja}, {fecha}, {rfc}'),

('SOLICITUD_FOLIO_PREFIX',
 'SOL',
 'Prefijo para el folio de solicitud (ej: SOL-2026-001)'),

('BOT_A_TIMEOUT_MS',
 '30000',
 'Timeout en milisegundos para operaciones de Playwright en Bot A'),

('BOT_C_TIMEOUT_MS',
 '30000',
 'Timeout en milisegundos para operaciones de Playwright en Bot C'),

('MAX_REINTENTOS_FOLIO',
 '3',
 'Número máximo de reintentos para descargar un recibo fallido'),

('EXCEL_COLUMNA_FOLIO_ELECTRONICO',
 'FOLIO',
 'Nombre del encabezado de columna en Excel para el folio electrónico'),

('EXCEL_COLUMNA_FOLIO_PASE_CAJA',
 'FOLIO_PASE_CAJA',
 'Nombre del encabezado de columna en Excel para el folio de pase de caja');


-- =============================================================================
-- LOCALIZADORES DE PORTAL — RECIBO
-- (Los valores de selector se actualizan tras inspección del portal)
-- =============================================================================

INSERT INTO cancunbot_configuracion.localizador_portal
    (portal, nombre_clave, label_visible, estrategia_selector, valor_selector, descripcion)
VALUES

('RECIBO', 'RECIBO_INPUT_FOLIO',
 'Campo de texto para ingresar el folio',
 'CSS', '[PENDIENTE_INSPECCION]',
 'Input principal donde se ingresa el folio electrónico o pase de caja'),

('RECIBO', 'RECIBO_BTN_CONSULTAR',
 'Botón Consultar',
 'CSS', '[PENDIENTE_INSPECCION]',
 'Botón que ejecuta la consulta del folio en el portal'),

('RECIBO', 'RECIBO_BTN_DESCARGAR',
 'Botón Descargar PDF',
 'CSS', '[PENDIENTE_INSPECCION]',
 'Botón que inicia la descarga del PDF del recibo'),

('RECIBO', 'RECIBO_MSG_NO_ENCONTRADO',
 'Mensaje de folio no encontrado',
 'CSS', '[PENDIENTE_INSPECCION]',
 'Elemento visible cuando el folio no existe en el portal');


-- =============================================================================
-- LOCALIZADORES DE PORTAL — FACTURA
-- (Los valores de selector se actualizan tras inspección del portal)
-- =============================================================================

INSERT INTO cancunbot_configuracion.localizador_portal
    (portal, nombre_clave, label_visible, estrategia_selector, valor_selector, descripcion)
VALUES

('FACTURA', 'FACTURA_INPUT_RFC',
 'Campo RFC del contribuyente',
 'CSS', '[PENDIENTE_INSPECCION]',
 'Input donde se ingresa el RFC para generar la factura'),

('FACTURA', 'FACTURA_INPUT_CORREO',
 'Campo correo electrónico',
 'CSS', '[PENDIENTE_INSPECCION]',
 'Input donde se ingresa el correo del contribuyente'),

('FACTURA', 'FACTURA_INPUT_FOLIO',
 'Campo folio electrónico',
 'CSS', '[PENDIENTE_INSPECCION]',
 'Input donde se ingresa el folio electrónico del recibo'),

('FACTURA', 'FACTURA_INPUT_IMPORTE',
 'Campo importe',
 'CSS', '[PENDIENTE_INSPECCION]',
 'Input donde se ingresa el importe total del recibo'),

('FACTURA', 'FACTURA_BTN_GENERAR',
 'Botón Generar / Timbrar',
 'CSS', '[PENDIENTE_INSPECCION]',
 'Botón que ejecuta el timbrado de la factura'),

('FACTURA', 'FACTURA_BTN_DESCARGAR_PDF',
 'Botón Descargar PDF de factura',
 'CSS', '[PENDIENTE_INSPECCION]',
 'Botón para descargar el PDF de la factura generada'),

('FACTURA', 'FACTURA_BTN_DESCARGAR_XML',
 'Botón Descargar XML de factura',
 'CSS', '[PENDIENTE_INSPECCION]',
 'Botón para descargar el XML de la factura generada'),

('FACTURA', 'FACTURA_MSG_EXITO',
 'Mensaje de factura generada exitosamente',
 'CSS', '[PENDIENTE_INSPECCION]',
 'Elemento visible cuando la factura fue generada con éxito'),

('FACTURA', 'FACTURA_MSG_ERROR',
 'Mensaje de error en facturación',
 'CSS', '[PENDIENTE_INSPECCION]',
 'Elemento visible cuando ocurre un error en el proceso de facturación');
