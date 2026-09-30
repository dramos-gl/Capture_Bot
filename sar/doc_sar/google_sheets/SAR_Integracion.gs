/**
 * ============================================================================
 * SISTEMA INTEGRAL: CONTROL DE DUPLICADOS, FORMATO Y CONTROL DE DERECHOS
 * Hoja Operativa: 'Ctrl_Derechos'
 * Arquitectura: Business-First / Apps Script Enterprise
 * Versión: 2.4.0 - Almacenamiento Técnico Independiente (CTRL_Derechos_BackUP)
 * ============================================================================
 */

// ============================================================================
// 1. CONFIGURACIN Y CONSTANTES DEL SISTEMA
// ============================================================================
const CONFIG = Object.freeze({
  SEGURIDAD: {
    // Dominio corporativo con acceso exclusivo a menús y funciones de SAR
    DOMINIO_AUTORIZADO: "@caduinmobiliaria.com",
    // Correo(s) específicos adicionales si fuera necesario
    ADMINS_EXPLICITOS: [
      "domingo.ramos@caduinmobiliaria.com"
    ],
    HABILITAR_RESTRICCION: true
  },
  SHEETS: {
    OPERATIVA: "Ctrl_Derechos",
    CONTROL: "CONTROL_D",
    LOG: "LOG_D",
    REPORTE: "Reporte_Duplicados"
  },
  COLUMNS: {
    // 1-based index para APIs de Google Sheets
    COL_ESTADO: 1,                  // Columna A: ESTADO (Protegida)
    COL_D: 4,                       // CLIENTE (Texto con espacios normalizados)
    COL_E_MIN: 5,                   // Inicio bloque E:I sin espacios internos
    COL_I_MAX: 9,                   // Fin bloque E:I
    // Bloque E:H (Duplicados compuestos en tiempo real)
    BLOQUE_EH_INICIO: 5,            // Col E
    BLOQUE_EH_COLS: 4,              // E, F, G, H
    // Bloque N:Q (Universo compartido de duplicados en tiempo real)
    BLOQUE_NQ_INICIO: 14,           // Col N
    BLOQUE_NQ_COLS: 4               // N, O, P, Q
  },
  EXPORT: {
    COL_INICIO: 2,                  // Columna B
    NUM_COLS: 18,                   // B a S (18 columnas)
    // Desplazamiento relativo en matriz B:S (0-indexed: B=0, C=1, D=2, E=3, F=4, G=5)
    IDX_D: 2,                       // CLIENTE
    IDX_E: 3,                       // MZA
    IDX_F: 4,                       // LOTE
    IDX_G: 5,                       // EXT
    IDX_AVISO: 12,                  // Col N (AVISO) en base a B=0
    IDX_CLG: 13                     // Col O (CLG) en base a B=0
  },
  DRIVE: {
    FOLDER_ID_RESPALDOS: "1taIDE3ou9enSY5pUE-V-FYYMcpVi1Nx-",
    NOMBRE_ARCHIVO_BACKUP: "CTRL_Derechos_BackUP",
    CARPETA_LOTES: "Derechos_Lotes_Exportacion",
    CARPETA_BACKUPS: "Derechos_Backups_JSON"
  },
  COLORS: {
    DUPLICADO_EH: "#F4CCCC",        // Rojo pastel suave
    DUPLICADO_NQ: "#FF6B6B",        // Rojo alerta vivo
    BLANCO: null,
    HEADER_CONTROL: "#D9EAD3",
    HEADER_LOG: "#CFE2F3"
  },
  LOCK_TIMEOUT_MS: 30000            // 30 segundos
});

// ============================================================================
// 2. CONTROL DE ACCESO Y SEGURIDAD POR DOMINIO
// ============================================================================

/**
 * Valida si el usuario actual pertenece al dominio corporativo autorizado.
 * @return {boolean}
 */
function usuarioEstaAutorizado() {
  if (!CONFIG.SEGURIDAD.HABILITAR_RESTRICCION) return true;

  const email = (Session.getActiveUser().getEmail() || "").trim().toLowerCase();
  if (!email) return false;

  // Validación 1: Lista explícita de correos administradores
  const admins = CONFIG.SEGURIDAD.ADMINS_EXPLICITOS.map(a => a.toLowerCase());
  if (admins.includes(email)) return true;

  // Validación 2: Dominio corporativo @caduinmobiliaria.com
  const dominio = CONFIG.SEGURIDAD.DOMINIO_AUTORIZADO.toLowerCase();
  if (email.endsWith(dominio)) {
    return true;
  }

  return false;
}

// ============================================================================
// 3. MENÚ PRINCIPAL Y DISPARADORES
// ============================================================================
function onOpen() {
  const autorizado = usuarioEstaAutorizado();

  // Si no es del dominio corporativo, NO se construye el menú
  if (!autorizado) {
    return;
  }

  const ui = SpreadsheetApp.getUi();
  ui.createMenu('Control de Derechos')
    .addItem('1. Exportar Excel', 'menuGenerarLoteSAR')
    .addItem('2. Confirmar Lote Completo', 'menuConfirmarLoteCompleto')
    .addItem('3. Confirmar Parcial (Lista Derechos)', 'menuConfirmarParcialSAR')
    .addSeparator()
    .addItem('📄 Extraer duplicados de (E:H)', 'generarReporteEH')
    .addItem('📄 Extraer duplicados de (E:I)', 'generarReporteEI')
    .addSeparator()
    .addItem('🧹 Limpiar hoja operativa completa', 'limpiarArchivoCompleto')
    .addItem('🎨 Refrescar coloreado de duplicados', 'refrescarColoreadoManual')
    .addSeparator()
    .addItem('🔒 Proteger Columna ESTADO (A:A)', 'menuProtegerColumnaEstado')
    .addToUi();
}

function menuProtegerColumnaEstado() {
  if (!usuarioEstaAutorizado()) return;
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const hojaOp = ss.getSheetByName(CONFIG.SHEETS.OPERATIVA);
  if (hojaOp) {
    TechnicalStorage.protegerColumnaEstado(hojaOp);
    SpreadsheetApp.getUi().alert('Columna A (ESTADO) protegida exitosamente para edición exclusiva de administradores.');
  }
}

function generarReporteEH() {
  if (!usuarioEstaAutorizado()) {
    SpreadsheetApp.getUi().alert('⛔ Acceso denegado: Función exclusiva para @caduinmobiliaria.com');
    return;
  }
  ReportEngine.generar(4, 'E:H');
}

function generarReporteEI() {
  if (!usuarioEstaAutorizado()) {
    SpreadsheetApp.getUi().alert(' Acceso denegado: Función exclusiva para @caduinmobiliaria.com');
    return;
  }
  ReportEngine.generar(5, 'E:I');
}

/**
 * Disparador onEdit en tiempo real optimizado.
 * Opera para cualquier usuario (notaría o interno) para mantener la integridad de los datos
 * y el coloreado en tiempo real sin requerir privilegios de menú.
 * @param {GoogleAppsScript.Events.SheetsOnEdit} e
 */
function onEdit(e) {
  try {
    if (!e || !e.range) return;

    const range = e.range;
    const sheet = range.getSheet();

    // Solo actuar en la hoja operativa 'Ctrl_Derechos'
    if (sheet.getName() !== CONFIG.SHEETS.OPERATIVA) return;

    const startRow = range.getRow();
    const startCol = range.getColumn();
    const numRows = range.getNumRows();
    const numCols = range.getNumColumns();
    const endCol = startCol + numCols - 1;

    // ------------------------------------------------------------------------
    // PASO 1: FORMATEO Y LIMPIEZA DE ESPACIOS / MAYSCULAS
    // ------------------------------------------------------------------------
    const values = range.getValues();
    let huboCambio = false;

    for (let r = 0; r < numRows; r++) {
      if (startRow + r === 1) continue; // Omitir encabezado

      for (let c = 0; c < numCols; c++) {
        const celda = values[r][c];
        const numColumnaActual = startCol + c;
        const textoLimpio = DataFormatter.formatearCelda(celda, numColumnaActual);

        if (textoLimpio !== celda) {
          values[r][c] = textoLimpio;
          huboCambio = true;
        }
      }
    }

    if (huboCambio) {
      range.setValues(values);
    }

    const lastRow = sheet.getLastRow();
    if (lastRow < 2) return;
    const totalFilas = lastRow - 1;

    // ------------------------------------------------------------------------
    // PASO 2: COLOREADO DIFERENCIAL EN BLOQUE E:H (Cols 5 a 8)
    // ------------------------------------------------------------------------
    const tocoBloqueEH = !(endCol < CONFIG.COLUMNS.BLOQUE_EH_INICIO || startCol > (CONFIG.COLUMNS.BLOQUE_EH_INICIO + CONFIG.COLUMNS.BLOQUE_EH_COLS - 1));
    if (tocoBloqueEH) {
      DuplicateColorEngine.actualizarBloqueEH(sheet, totalFilas);
    }

    // ------------------------------------------------------------------------
    // PASO 3: COLOREADO DIFERENCIAL EN BLOQUE N:Q (Cols 14 a 17)
    // ------------------------------------------------------------------------
    const tocoBloqueNQ = !(endCol < CONFIG.COLUMNS.BLOQUE_NQ_INICIO || startCol > (CONFIG.COLUMNS.BLOQUE_NQ_INICIO + CONFIG.COLUMNS.BLOQUE_NQ_COLS - 1));
    if (tocoBloqueNQ) {
      DuplicateColorEngine.actualizarBloqueNQ(sheet, totalFilas);
    }

  } catch (err) {
    console.error("[onEdit] Error: " + err.message);
  }
}

/**
 * Permite al usuario re-evaluar y pintar duplicados bajo demanda.
 */
function refrescarColoreadoManual() {
  if (!usuarioEstaAutorizado()) {
    SpreadsheetApp.getUi().alert(' Acceso denegado.');
    return;
  }

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.SHEETS.OPERATIVA);
  if (!sheet) return;

  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return;

  const totalFilas = lastRow - 1;
  DuplicateColorEngine.actualizarBloqueEH(sheet, totalFilas);
  DuplicateColorEngine.actualizarBloqueNQ(sheet, totalFilas);
  SpreadsheetApp.getUi().alert('Coloreado de duplicados actualizado.');
}

// ============================================================================
// 4. MDULO DE FORMATEO Y NORMALIZACIN DE DATOS
// ============================================================================
const DataFormatter = {
  formatearCelda(texto, numColumna) {
    if (typeof texto !== 'string') return texto;
    if (texto.trim() === '') return '';

    // Columnas 5 a 9 (E, F, G, H, I): Sin espacios y todo a MAYSCULAS
    if (numColumna >= CONFIG.COLUMNS.COL_E_MIN && numColumna <= CONFIG.COLUMNS.COL_I_MAX) {
      return texto.replace(/\s+/g, '').toUpperCase();
    }

    // Columna 4 (D): MAYSCULAS, limpia extremos y colapsa dobles espacios
    if (numColumna === CONFIG.COLUMNS.COL_D) {
      return texto.trim().replace(/\s+/g, ' ').toUpperCase();
    }

    // Demás columnas: limpia extremos y colapsa dobles espacios
    return texto.trim().replace(/\s+/g, ' ');
  }
};

/**
 * Limpieza masiva de toda la hoja operativa.
 */
function limpiarArchivoCompleto() {
  if (!usuarioEstaAutorizado()) {
    SpreadsheetApp.getUi().alert(' Acceso denegado: Función exclusiva para @caduinmobiliaria.com');
    return;
  }

  const ui = SpreadsheetApp.getUi();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.SHEETS.OPERATIVA);

  if (!sheet) {
    ui.alert(`No se encontró la hoja "${CONFIG.SHEETS.OPERATIVA}".`);
    return;
  }

  const lastRow = sheet.getLastRow();
  const lastCol = sheet.getLastColumn();
  if (lastRow < 2 || lastCol < 1) {
    ui.alert('No hay datos suficientes para limpiar.');
    return;
  }

  const totalFilas = lastRow - 1;
  const range = sheet.getRange(2, 1, totalFilas, lastCol);
  const values = range.getValues();
  let celdasModificadas = 0;

  for (let f = 0; f < totalFilas; f++) {
    for (let c = 0; c < lastCol; c++) {
      const celda = values[f][c];
      const numColumna = c + 1;
      const textoLimpio = DataFormatter.formatearCelda(celda, numColumna);

      if (textoLimpio !== celda) {
        values[f][c] = textoLimpio;
        celdasModificadas++;
      }
    }
  }

  if (celdasModificadas > 0) {
    range.setValues(values);
    ui.alert(`Limpieza completada: se formatearon y corrigieron ${celdasModificadas} celdas.`);
  } else {
    ui.alert('La hoja ya cuenta con el formato correcto.');
  }
}

// ============================================================================
// 5. MOTOR DIFERENCIAL DE COLOREADO DE DUPLICADOS (CDIGO PURO)
// ============================================================================
const DuplicateColorEngine = {
  /**
   * Actualiza el bloque E:H (Duplicados por clave compuesta de fila).
   * Solo envía escritura a Google Sheets si detecta diferencias con los colores actuales.
   * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet
   * @param {number} totalFilas
   */
  actualizarBloqueEH(sheet, totalFilas) {
    const rangeEH = sheet.getRange(2, CONFIG.COLUMNS.BLOQUE_EH_INICIO, totalFilas, CONFIG.COLUMNS.BLOQUE_EH_COLS);
    const matrixEH = rangeEH.getValues();
    const currentBackgrounds = rangeEH.getBackgrounds();

    const counts = Object.create(null);
    const keys = new Array(totalFilas);

    for (let f = 0; f < totalFilas; f++) {
      const row = matrixEH[f];
      const colE = row[0];

      if (colE === "" || colE === null || colE === undefined) {
        keys[f] = null;
        continue;
      }

      // Clave compuesta E:H
      const key = `${String(colE).trim().toLowerCase()}|||${String(row[1] || "").trim().toLowerCase()}|||${String(row[2] || "").trim().toLowerCase()}|||${String(row[3] || "").trim().toLowerCase()}`;
      keys[f] = key;
      counts[key] = (counts[key] || 0) + 1;
    }

    let diffDetected = false;
    const targetBackgrounds = new Array(totalFilas);

    for (let f = 0; f < totalFilas; f++) {
      const key = keys[f];
      const isDuplicate = key && counts[key] > 1;
      const targetNull = isDuplicate ? CONFIG.COLORS.DUPLICADO_EH : null;

      const rowColors = new Array(CONFIG.COLUMNS.BLOQUE_EH_COLS);
      const curRow = currentBackgrounds[f];

      for (let c = 0; c < CONFIG.COLUMNS.BLOQUE_EH_COLS; c++) {
        rowColors[c] = targetNull;
        const curColor = curRow[c];
        const isCurrentlyMarked = (curColor && curColor.toLowerCase() === CONFIG.COLORS.DUPLICADO_EH.toLowerCase());
        
        if (isDuplicate !== isCurrentlyMarked) {
          diffDetected = true;
        }
      }
      targetBackgrounds[f] = rowColors;
    }

    // DIFFING: Solo escribir si hay discrepancia real de colores
    if (diffDetected) {
      rangeEH.setBackgrounds(targetBackgrounds);
    }
  },

  /**
   * Actualiza el bloque N:Q (Universo compartido de duplicados en tiempo real).
   * Alerta con rojo vivo `#FF6B6B` si cualquier celda se repite dentro de N:Q.
   * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet
   * @param {number} totalFilas
   */
  actualizarBloqueNQ(sheet, totalFilas) {
    const rangeNQ = sheet.getRange(2, CONFIG.COLUMNS.BLOQUE_NQ_INICIO, totalFilas, CONFIG.COLUMNS.BLOQUE_NQ_COLS);
    const matrixNQ = rangeNQ.getValues();
    const currentBackgrounds = rangeNQ.getBackgrounds();

    const globalCounts = Object.create(null);

    // Conteo en el universo de las 4 columnas
    for (let f = 0; f < totalFilas; f++) {
      const row = matrixNQ[f];
      for (let c = 0; c < CONFIG.COLUMNS.BLOQUE_NQ_COLS; c++) {
        const val = row[c];
        if (val !== "" && val !== null && val !== undefined) {
          const key = String(val).trim().toLowerCase();
          globalCounts[key] = (globalCounts[key] || 0) + 1;
        }
      }
    }

    let diffDetected = false;
    const targetBackgrounds = new Array(totalFilas);

    for (let f = 0; f < totalFilas; f++) {
      const rowColors = new Array(CONFIG.COLUMNS.BLOQUE_NQ_COLS);
      const rowValues = matrixNQ[f];
      const curRow = currentBackgrounds[f];

      for (let c = 0; c < CONFIG.COLUMNS.BLOQUE_NQ_COLS; c++) {
        const val = rowValues[c];
        let isDuplicate = false;

        if (val !== "" && val !== null && val !== undefined) {
          const key = String(val).trim().toLowerCase();
          if (globalCounts[key] > 1) {
            isDuplicate = true;
          }
        }

        rowColors[c] = isDuplicate ? CONFIG.COLORS.DUPLICADO_NQ : null;

        const curColor = curRow[c];
        const isCurrentlyMarked = (curColor && curColor.toLowerCase() === CONFIG.COLORS.DUPLICADO_NQ.toLowerCase());

        if (isDuplicate !== isCurrentlyMarked) {
          diffDetected = true;
        }
      }
      targetBackgrounds[f] = rowColors;
    }

    // DIFFING: Solo escribir si hay discrepancia real de colores
    if (diffDetected) {
      rangeNQ.setBackgrounds(targetBackgrounds);
    }
  }
};

// ============================================================================
// 6. MOTOR DE EXPORTACIN Y GESTIN DE LOTES SAR
// ============================================================================

/**
 * Menú 1: Exporta registros completos (D:G) a un archivo Excel y actualiza estados de forma atómica.
 */
function menuGenerarLoteSAR() {
  if (!usuarioEstaAutorizado()) {
    SpreadsheetApp.getUi().alert(' Acceso denegado: Esta función requiere pertenecer a @caduinmobiliaria.com.');
    return;
  }

  const lock = LockService.getDocumentLock();
  if (!lock.tryLock(CONFIG.LOCK_TIMEOUT_MS)) {
    SpreadsheetApp.getUi().alert('Otra operación está en curso. Por favor espere.');
    return;
  }

  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const hojaOp = ss.getSheetByName(CONFIG.SHEETS.OPERATIVA);
    if (!hojaOp) throw new Error(`No se encontró la hoja ${CONFIG.SHEETS.OPERATIVA}`);

    const controlMap = TechnicalStorage.cargarMapaControl(ss);

    const ultimaFila = hojaOp.getLastRow();
    if (ultimaFila < 2) {
      SpreadsheetApp.getUi().alert('No hay datos en la hoja operativa.');
      return;
    }

    const numFilas = ultimaFila - 1;
    const totalColsOp = hojaOp.getLastColumn();
    // Leemos las filas completas de la hoja operativa (Col 1 a totalColsOp)
    const matrizFilasCompletas = hojaOp.getRange(2, 1, numFilas, totalColsOp).getValues();
    // Leemos el bloque de exportación B:S
    const datosOp = hojaOp.getRange(2, CONFIG.EXPORT.COL_INICIO, numFilas, CONFIG.EXPORT.NUM_COLS).getValues();
    const encabezados = hojaOp.getRange(1, CONFIG.EXPORT.COL_INICIO, 1, CONFIG.EXPORT.NUM_COLS).getValues()[0];

    const loteId = TechnicalStorage.generarLoteID();
    const timestamp = new Date();
    const usuario = Session.getActiveUser().getEmail() || "usuario_sheets";

    const filasParaExportar = [];
    const registrosAExportar = [];

    for (let i = 0; i < datosOp.length; i++) {
      const fila = datosOp[i];
      const filaCompletaOriginal = matrizFilasCompletas[i];

      const colD = String(fila[CONFIG.EXPORT.IDX_D] || "").trim();
      const colE = String(fila[CONFIG.EXPORT.IDX_E] || "").trim();
      const colF = String(fila[CONFIG.EXPORT.IDX_F] || "").trim();
      const colG = String(fila[CONFIG.EXPORT.IDX_G] || "").trim();

      // REGLA OBLIGATORIA: D, E, F y G deben contener datos válidos
      const obligatoriosCompletos = (colD !== "" && colE !== "" && colF !== "" && colG !== "");
      if (!obligatoriosCompletos) continue;

      // OBTENCIN DE REFERENCIA OFICIAL: Se extrae de Columna N (AVISO) o en su defecto Columna O (CLG)
      const colAviso = String(fila[CONFIG.EXPORT.IDX_AVISO] || "").trim().toUpperCase();
      const colClg = String(fila[CONFIG.EXPORT.IDX_CLG] || "").trim().toUpperCase();
      const referencia = colAviso || colClg;

      // Si no tiene folio de Aviso ni de CLG, no puede conciliarse en SAR
      if (!referencia) continue;

      const meta = controlMap.get(referencia);
      const estadoActual = meta ? meta.estado : "PENDIENTE";

      // Solo exportar registros en estado PENDIENTE
      if (estadoActual === "PENDIENTE") {
        filasParaExportar.push(fila);
        registrosAExportar.push({
          referencia: referencia,
          estadoAnterior: estadoActual,
          estadoNuevo: "EXPORTADO",
          lote: loteId,
          detalle: `Fila ${i + 2} | CLG: ${colClg || 'N/A'}`,
          filaOperativaCompleta: filaCompletaOriginal
        });
      }
    }

    if (filasParaExportar.length === 0) {
      SpreadsheetApp.getUi().alert('No se encontraron registros completos (D:G) en estado PENDIENTE para exportar.');
      return;
    }

    // PASO 1: Generación del archivo Excel físico en Drive (Si falla, aborta sin tocar base técnica)
    const archivoInfo = TechnicalStorage.generarArchivoExcelSAR(loteId, encabezados, filasParaExportar);

    // PASO 2: Persistencia atómica de transacciones en CONTROL_D y LOG_D
    TechnicalStorage.actualizarEstadoControlYLog(ss, registrosAExportar, loteId, usuario, timestamp);

    // PASO 3: Respaldo JSON de auditoría
    TechnicalStorage.generarBackupJSON(loteId, timestamp, usuario, registrosAExportar);

    // PASO 4: Presentar ventana modal con descarga local inmediata al navegador
    TechnicalStorage.mostrarDialogoDescargaLocal(loteId, filasParaExportar.length, archivoInfo.downloadUrl, archivoInfo.viewUrl);

  } catch (err) {
    console.error(`[menuGenerarLoteSAR] Error: ${err.message}`, err.stack);
    SpreadsheetApp.getUi().alert(` Error al generar lote: ${err.message}`);
  } finally {
    lock.releaseLock();
  }
}

/**
 * Menú 2: Confirmación de Lote Completo.
 */
function menuConfirmarLoteCompleto() {
  if (!usuarioEstaAutorizado()) {
    SpreadsheetApp.getUi().alert(' Acceso denegado: Esta función requiere pertenecer a @caduinmobiliaria.com.');
    return;
  }

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const ultimoLoteSugerido = TechnicalStorage.obtenerUltimoLoteExportado(ss);

  const ui = SpreadsheetApp.getUi();
  const mensajePrompt = ultimoLoteSugerido
    ? `Lote pendiente detectado: "${ultimoLoteSugerido}".\nPresione OK para confirmar este lote o escriba otro:`
    : 'Ingrese el Lote ID a confirmar (ej. D-20260928-113000):';

  const respuesta = ui.prompt(
    'Confirmación de Importación en Derechos',
    mensajePrompt,
    ui.ButtonSet.OK_CANCEL
  );

  if (respuesta.getSelectedButton() !== ui.Button.OK) return;
  let loteId = respuesta.getResponseText().trim();
  if (!loteId && ultimoLoteSugerido) {
    loteId = ultimoLoteSugerido;
  }
  if (!loteId) {
    ui.alert('Debe ingresar un Lote ID válido.');
    return;
  }

  const lock = LockService.getDocumentLock();
  if (!lock.tryLock(CONFIG.LOCK_TIMEOUT_MS)) {
    ui.alert('Otra operación está en curso. Por favor espere.');
    return;
  }

  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const controlMap = TechnicalStorage.cargarMapaControl(ss);
    const usuario = Session.getActiveUser().getEmail() || "usuario_sheets";
    const timestamp = new Date();

    const registrosAConfirmar = [];
    for (const [ref, meta] of controlMap.entries()) {
      if (meta.lote === loteId && (meta.estado === "EXPORTADO" || meta.estado === "EXPORTADA")) {
        registrosAConfirmar.push({
          referencia: ref,
          estadoAnterior: meta.estado,
          estadoNuevo: "ASIGNADO",
          lote: loteId,
          detalle: "Confirmación completa de lote"
        });
      }
    }

    if (registrosAConfirmar.length === 0) {
      ui.alert(`No se encontraron registros pendientes de confirmar para el lote: ${loteId}.`);
      return;
    }

    TechnicalStorage.actualizarEstadoControlYLog(ss, registrosAConfirmar, loteId, usuario, timestamp);
    TechnicalStorage.generarBackupJSON(`${loteId}_CONFIRMACION`, timestamp, usuario, registrosAConfirmar);

    ui.alert(` Lote ${loteId} confirmado: Se marcaron ${registrosAConfirmar.length} referencias como ASIGNADO.`);

  } catch (err) {
    ui.alert(` Error en confirmación: ${err.message}`);
  } finally {
    lock.releaseLock();
  }
}

/**
 * Menú 3: Confirmación Parcial pegando la lista desde SAR.
 */
function menuConfirmarParcialSAR() {
  if (!usuarioEstaAutorizado()) {
    SpreadsheetApp.getUi().alert(' Acceso denegado: Esta función requiere pertenecer a @caduinmobiliaria.com.');
    return;
  }

  const ui = SpreadsheetApp.getUi();
  const respuesta = ui.prompt(
    'Confirmación Parcial de Referencias',
    'Pegue las referencias procesadas exitosamente en Derechos (separadas por salto de línea o coma):',
    ui.ButtonSet.OK_CANCEL
  );

  if (respuesta.getSelectedButton() !== ui.Button.OK) return;
  const textoEntrada = respuesta.getResponseText();
  if (!textoEntrada) return;

  const refsExitosas = new Set(
    textoEntrada.split(/[\n,]/).map(r => r.trim().toUpperCase()).filter(r => r.length > 0)
  );

  if (refsExitosas.size === 0) {
    ui.alert('No se ingresaron referencias válidas.');
    return;
  }

  const lock = LockService.getDocumentLock();
  if (!lock.tryLock(CONFIG.LOCK_TIMEOUT_MS)) {
    ui.alert('Bloqueo activo. Intente en unos momentos.');
    return;
  }

  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const controlMap = TechnicalStorage.cargarMapaControl(ss);
    const usuario = Session.getActiveUser().getEmail() || "usuario_sheets";
    const timestamp = new Date();

    const transacciones = [];
    let exitosas = 0;
    let devueltasAPendiente = 0;

    for (const [ref, meta] of controlMap.entries()) {
      if (meta.estado === "EXPORTADO" || meta.estado === "EXPORTADA") {
        if (refsExitosas.has(ref)) {
          transacciones.push({
            referencia: ref,
            estadoAnterior: meta.estado,
            estadoNuevo: "ASIGNADO",
            lote: meta.lote,
            detalle: "Confirmación parcial Derechos"
          });
          exitosas++;
        } else {
          transacciones.push({
            referencia: ref,
            estadoAnterior: meta.estado,
            estadoNuevo: "PENDIENTE",
            lote: meta.lote,
            detalle: "Revertida a PENDIENTE (Omitida por Derechos)"
          });
          devueltasAPendiente++;
        }
      }
    }

    if (transacciones.length === 0) {
      ui.alert('No hay referencias con estado EXPORTADO para conciliar.');
      return;
    }

    TechnicalStorage.actualizarEstadoControlYLog(ss, transacciones, "CONCILIACION_PARCIAL", usuario, timestamp);
    ui.alert(` Conciliación finalizada:\n- Confirmadas (ASIGNADO): ${exitosas}\n- Devueltas a PENDIENTE: ${devueltasAPendiente}`);

  } catch (err) {
    ui.alert(` Error en conciliación: ${err.message}`);
  } finally {
    lock.releaseLock();
  }
}

// ============================================================================
// 7. CAPA TCNICA DE PERSISTENCIA, DRIVE Y AUDITORÍA
// ============================================================================
const TechnicalStorage = {
  generarLoteID() {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    return `D-${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
  },

  obtenerCarpetaBase() {
    if (CONFIG.DRIVE.FOLDER_ID_RESPALDOS && CONFIG.DRIVE.FOLDER_ID_RESPALDOS.trim() !== "") {
      try {
        return DriveApp.getFolderById(CONFIG.DRIVE.FOLDER_ID_RESPALDOS.trim());
      } catch (err) {
        console.warn(`[Drive] No se pudo acceder a la carpeta por ID (${CONFIG.DRIVE.FOLDER_ID_RESPALDOS}): ${err.message}. Se usará la raíz de Drive.`);
      }
    }
    return DriveApp.getRootFolder();
  },

  obtenerOCrearCarpeta(nombreCarpeta) {
    const carpetaBase = this.obtenerCarpetaBase();
    const carpetas = carpetaBase.getFoldersByName(nombreCarpeta);
    return carpetas.hasNext() ? carpetas.next() : carpetaBase.createFolder(nombreCarpeta);
  },

  /**
   * Obtiene o crea el archivo maestro independiente de respaldo en Google Drive: 'CTRL_Derechos_BackUP'
   * Ubicado exclusivamente en la carpeta designada de respaldos para blindar la seguridad contra externos.
   * @return {GoogleAppsScript.Spreadsheet.Spreadsheet}
   */
  obtenerOLibroControlExterno() {
    const carpetaBase = this.obtenerCarpetaBase();
    const nombreArchivo = CONFIG.DRIVE.NOMBRE_ARCHIVO_BACKUP || "CTRL_Derechos_BackUP";
    const archivos = carpetaBase.getFilesByName(nombreArchivo);

    let ssControl = null;
    if (archivos.hasNext()) {
      const archivo = archivos.next();
      ssControl = SpreadsheetApp.openById(archivo.getId());
    } else {
      // Creación del archivo maestro independiente en Google Drive
      ssControl = SpreadsheetApp.create(nombreArchivo);
      const archivoDrive = DriveApp.getFileById(ssControl.getId());
      carpetaBase.addFile(archivoDrive);
      DriveApp.getRootFolder().removeFile(archivoDrive);
    }

    this.inicializarEstructurasEnLibroExterno(ssControl);
    return ssControl;
  },

  /**
   * Inicializa las pestañas CONTROL_D y LOG_D dentro del libro externo independiente.
   * @param {GoogleAppsScript.Spreadsheet.Spreadsheet} ssControl
   */
  inicializarEstructurasEnLibroExterno(ssControl) {
    const ssOp = SpreadsheetApp.getActiveSpreadsheet();
    const hojaOp = ssOp.getSheetByName(CONFIG.SHEETS.OPERATIVA);

    let hojaControl = ssControl.getSheetByName(CONFIG.SHEETS.CONTROL);
    if (!hojaControl) {
      hojaControl = ssControl.insertSheet(CONFIG.SHEETS.CONTROL);
      const totalColsOp = hojaOp ? hojaOp.getLastColumn() : 19;
      const encabezadosOp = hojaOp
        ? hojaOp.getRange(1, 1, 1, totalColsOp).getValues()[0]
        : ["#", "DESARROLLO", "P.A.", "CLIENTE", "MZA", "LOTE", "EXT", "INT", "No.OFICIAL", "FECHA_NOTARIA", "FECHA_RPP", "FECHA_ESCRITURA", "FECHA_TITULACION", "AVISO", "CLG", "CANC_1", "CANC_2", "COMENTARIOS", "MES STOCK"];

      const encabezadosControl = [
        ...encabezadosOp,
        "LOTE_DERECHOS",
        "FECHA_EXPORTACION",
        "FECHA_CONFIRMACION",
        "USUARIO_DERECHOS",
        "ESTADO_DERECHOS",
        "REFERENCIA_CLAVE"
      ];
      hojaControl.getRange(1, 1, 1, encabezadosControl.length)
        .setValues([encabezadosControl])
        .setFontWeight("bold")
        .setBackground(CONFIG.COLORS.HEADER_CONTROL);
    }

    let hojaLog = ssControl.getSheetByName(CONFIG.SHEETS.LOG);
    if (!hojaLog) {
      hojaLog = ssControl.insertSheet(CONFIG.SHEETS.LOG);
      hojaLog.getRange(1, 1, 1, 8).setValues([[
        "Timestamp", "Operacion", "Lote_ID", "Referencia", "Estado_Anterior", "Estado_Nuevo", "Usuario", "Detalle"
      ]]).setFontWeight("bold").setBackground(CONFIG.COLORS.HEADER_LOG);
    }

    // Eliminar la hoja por defecto 'Hoja 1' / 'Sheet1' generada al crear el libro nuevo
    const hojaDefault = ssControl.getSheetByName("Hoja 1") || ssControl.getSheetByName("Sheet1");
    if (hojaDefault && ssControl.getSheets().length > 1) {
      try {
        ssControl.deleteSheet(hojaDefault);
      } catch (e) {
        // Ignorar si no se puede eliminar
      }
    }
  },

  protegerHojaTecnica(hoja) {
    // Las hojas en el archivo independiente heredan los permisos de la carpeta de Drive del administrador
  },

  /**
   * Obtiene los índices (1-based) de las columnas técnicas de CONTROL_D inspeccionando los encabezados.
   * Proporciona resiliencia total frente a inserciones, ordenamientos o cambios de columnas.
   */
  obtenerIndicesColumnasControl(hojaControl) {
    const totalCols = hojaControl.getLastColumn();
    const encabezados = hojaControl.getRange(1, 1, 1, totalCols).getValues()[0];

    const indices = {
      lote: -1,
      fechaExp: -1,
      fechaConf: -1,
      usuario: -1,
      estado: -1,
      refClave: -1
    };

    for (let c = 0; c < encabezados.length; c++) {
      const h = String(encabezados[c] || "").trim().toUpperCase();
      if (h === "LOTE_DERECHOS" || h === "LOTE_SAR") indices.lote = c + 1;
      else if (h === "FECHA_EXPORTACION") indices.fechaExp = c + 1;
      else if (h === "FECHA_CONFIRMACION") indices.fechaConf = c + 1;
      else if (h === "USUARIO_DERECHOS" || h === "USUARIO_SAR") indices.usuario = c + 1;
      else if (h === "ESTADO_DERECHOS" || h === "ESTADO_SAR") indices.estado = c + 1;
      else if (h === "REFERENCIA_CLAVE") indices.refClave = c + 1;
    }

    // Fallback retrocompatible por posición relativa final si no coincidieran por nombre
    if (indices.refClave === -1) indices.refClave = totalCols;
    if (indices.estado === -1) indices.estado = totalCols - 1;
    if (indices.usuario === -1) indices.usuario = totalCols - 2;
    if (indices.fechaConf === -1) indices.fechaConf = totalCols - 3;
    if (indices.fechaExp === -1) indices.fechaExp = totalCols - 4;
    if (indices.lote === -1) indices.lote = totalCols - 5;

    return indices;
  },

  cargarMapaControl(ss) {
    // Si no se pasa o si se pasa el activo, obtenemos el libro de control independiente
    const ssControl = this.obtenerOLibroControlExterno();
    const hojaControl = ssControl.getSheetByName(CONFIG.SHEETS.CONTROL);
    const mapa = new Map();
    if (!hojaControl) return mapa;

    const ultimaFila = hojaControl.getLastRow();
    const ultimaCol = hojaControl.getLastColumn();
    if (ultimaFila < 2 || ultimaCol < 6) return mapa;

    const idx = this.obtenerIndicesColumnasControl(hojaControl);
    const valores = hojaControl.getRange(2, 1, ultimaFila - 1, ultimaCol).getValues();

    for (let i = 0; i < valores.length; i++) {
      const fila = valores[i];
      const ref = String(fila[idx.refClave - 1] || fila[CONFIG.COLUMNS.BLOQUE_NQ_INICIO - 1] || "").trim().toUpperCase();
      if (ref) {
        mapa.set(ref, {
          filaIndice: i, // 0-based relativo a los datos
          lote: fila[idx.lote - 1],
          fechaExp: fila[idx.fechaExp - 1],
          fechaConf: fila[idx.fechaConf - 1],
          usuario: fila[idx.usuario - 1],
          estado: fila[idx.estado - 1],
          referencia: ref
        });
      }
    }
    return mapa;
  },

  /**
   * Obtiene el ID del último lote exportado que tenga referencias pendientes de confirmación.
   * @param {GoogleAppsScript.Spreadsheet.Spreadsheet} ss
   * @return {string}
   */
  obtenerUltimoLoteExportado(ss) {
    const controlMap = this.cargarMapaControl(ss);
    let ultimoLote = "";
    for (const [_, meta] of controlMap.entries()) {
      if (meta.estado === "EXPORTADO" || meta.estado === "EXPORTADA") {
        if (meta.lote) ultimoLote = meta.lote;
      }
    }
    return ultimoLote;
  },

  /**
   * Actualización transaccional y atómica en lote en el archivo independiente 'CTRL_Derechos_BackUP'.
   * CONTROL_D almacena una copia exacta e histórica de cada fila de Ctrl_Derechos
   * junto con los metadatos de lote, fecha, usuario y estado.
   */
  actualizarEstadoControlYLog(ssOperativa, transacciones, loteId, usuario, timestamp) {
    const ssControl = this.obtenerOLibroControlExterno();
    const hojaControl = ssControl.getSheetByName(CONFIG.SHEETS.CONTROL);
    const hojaLog = ssControl.getSheetByName(CONFIG.SHEETS.LOG);
    const hojaOp = ssOperativa.getSheetByName(CONFIG.SHEETS.OPERATIVA);

    const controlMap = this.cargarMapaControl(ssControl);
    const totalControlFilas = hojaControl.getLastRow() > 1 ? hojaControl.getLastRow() - 1 : 0;
    const totalControlCols = hojaControl.getLastColumn();

    let matrizControl = (totalControlFilas > 0 && totalControlCols > 0)
      ? hojaControl.getRange(2, 1, totalControlFilas, totalControlCols).getValues()
      : [];

    const idxControl = this.obtenerIndicesColumnasControl(hojaControl);
    const idxLote = idxControl.lote;             // 1-based
    const idxFechaExp = idxControl.fechaExp;
    const idxFechaConf = idxControl.fechaConf;
    const idxUsuario = idxControl.usuario;
    const idxEstado = idxControl.estado;
    const idxRefClave = idxControl.refClave;

    // Lógica para LOG_D: 1 solo registro por referencia que se actualiza in-place
    const totalLogFilas = hojaLog.getLastRow() > 1 ? hojaLog.getLastRow() - 1 : 0;
    let matrizLog = totalLogFilas > 0
      ? hojaLog.getRange(2, 1, totalLogFilas, 8).getValues()
      : [];

    // Mapeo de referencia -> índice de fila en matrizLog
    const mapaLog = new Map();
    for (let i = 0; i < matrizLog.length; i++) {
      const refLog = String(matrizLog[i][3] || "").trim().toUpperCase(); // Columna 4: Referencia
      if (refLog) {
        mapaLog.set(refLog, i);
      }
    }

    const nuevasFilasControl = [];
    const nuevasFilasLog = [];

    transacciones.forEach(t => {
      const existeControl = controlMap.get(t.referencia);

      if (existeControl && existeControl.filaIndice < matrizControl.length) {
        const idx = existeControl.filaIndice;
        matrizControl[idx][idxEstado - 1] = t.estadoNuevo;
        matrizControl[idx][idxUsuario - 1] = usuario;

        if (t.estadoNuevo === "ASIGNADO") {
          matrizControl[idx][idxFechaConf - 1] = timestamp;
        } else {
          matrizControl[idx][idxLote - 1] = t.lote;
          matrizControl[idx][idxFechaExp - 1] = timestamp;
        }
      } else {
        // Nueva inserción en CONTROL_D: Copia EXACTA de la fila operativa + metadatos
        let baseFila = [];
        if (t.filaOperativaCompleta && Array.isArray(t.filaOperativaCompleta)) {
          baseFila = [...t.filaOperativaCompleta];
        } else {
          const totalColsOp = hojaOp ? hojaOp.getLastColumn() : (totalControlCols - 6);
          baseFila = new Array(totalColsOp).fill("");
        }

        const colsOpEsperadas = totalControlCols - 6;
        while (baseFila.length < colsOpEsperadas) baseFila.push("");
        if (baseFila.length > colsOpEsperadas) baseFila = baseFila.slice(0, colsOpEsperadas);

        const nuevaFila = [
          ...baseFila,
          t.lote,
          timestamp,
          t.estadoNuevo === "ASIGNADO" ? timestamp : "",
          usuario,
          t.estadoNuevo,
          t.referencia
        ];

        nuevasFilasControl.push(nuevaFila);
      }

      // Actualización de LOG_D (1 solo registro único por referencia)
      const operacionTexto = t.estadoNuevo === "ASIGNADO" ? "CONFIRMACION" : "EXPORTACION";
      const refClave = t.referencia.toUpperCase();

      if (mapaLog.has(refClave)) {
        // Si ya existe la referencia en LOG_D, se actualiza en su lugar
        const logIdx = mapaLog.get(refClave);
        matrizLog[logIdx][0] = timestamp;        // Timestamp más reciente
        matrizLog[logIdx][1] = operacionTexto;   // Operacion
        matrizLog[logIdx][2] = t.lote;           // Lote_ID
        matrizLog[logIdx][4] = t.estadoAnterior; // Estado_Anterior
        matrizLog[logIdx][5] = t.estadoNuevo;    // Estado_Nuevo (actualizado a ASIGNADO o PENDIENTE)
        matrizLog[logIdx][6] = usuario;          // Usuario
        matrizLog[logIdx][7] = t.detalle || "OK";// Detalle
      } else {
        // Si no existía previamente, se inserta su registro inicial
        nuevasFilasLog.push([
          timestamp,
          operacionTexto,
          t.lote,
          t.referencia,
          t.estadoAnterior,
          t.estadoNuevo,
          usuario,
          t.detalle || "OK"
        ]);
      }
    });

    // 1. Escritura en lote de actualizaciones existentes en CONTROL_D
    if (matrizControl.length > 0) {
      hojaControl.getRange(2, 1, matrizControl.length, totalControlCols).setValues(matrizControl);
    }
    // 2. Inserción de copias exactas nuevas en CONTROL_D
    if (nuevasFilasControl.length > 0) {
      hojaControl.getRange(hojaControl.getLastRow() + 1, 1, nuevasFilasControl.length, totalControlCols).setValues(nuevasFilasControl);
    }

    // 3. LOG_D: Actualización in-place y nuevas inserciones (sin duplicar referencias)
    if (matrizLog.length > 0) {
      hojaLog.getRange(2, 1, matrizLog.length, 8).setValues(matrizLog);
    }
    if (nuevasFilasLog.length > 0) {
      hojaLog.getRange(hojaLog.getLastRow() + 1, 1, nuevasFilasLog.length, 8).setValues(nuevasFilasLog);
    }

    // 4. Sincronización automática de estados en Columna A de Ctrl_Derechos
    this.sincronizarColumnaEstado(ssOperativa, transacciones);
  },

  /**
   * Sincroniza los estados en la Columna A de la hoja operativa 'Ctrl_Derechos'.
   * Se ejecuta en bloque (batch) para alta velocidad y aplica color visual.
   * @param {GoogleAppsScript.Spreadsheet.Spreadsheet} ss
   * @param {Array<Object>} transacciones
   */
  sincronizarColumnaEstado(ss, transacciones) {
    const hojaOp = ss.getSheetByName(CONFIG.SHEETS.OPERATIVA);
    if (!hojaOp) return;

    const ultimaFila = hojaOp.getLastRow();
    if (ultimaFila < 2) return;

    const totalFilas = ultimaFila - 1;
    // Mapa rápido de referencia -> estadoNuevo
    const mapaTransacciones = new Map();
    transacciones.forEach(t => {
      if (t.referencia) {
        mapaTransacciones.set(t.referencia.toUpperCase(), t.estadoNuevo);
      }
    });

    if (mapaTransacciones.size === 0) return;

    // Leemos el bloque de Referencias N:O (Columnas 14 y 15) y Columna A (Estado actual) en bloque
    const rangoRefsNO = hojaOp.getRange(2, CONFIG.COLUMNS.BLOQUE_NQ_INICIO, totalFilas, 2);
    const valoresRefsNO = rangoRefsNO.getValues();

    const rangoEstados = hojaOp.getRange(2, CONFIG.COLUMNS.COL_ESTADO, totalFilas, 1);
    const valoresEstados = rangoEstados.getValues();

    let huboModificacion = false;

    for (let i = 0; i < totalFilas; i++) {
      const aviso = String(valoresRefsNO[i][0] || "").trim().toUpperCase(); // Columna N
      const clg = String(valoresRefsNO[i][1] || "").trim().toUpperCase();   // Columna O
      
      // La referencia puede coincidir con AVISO o con CLG
      let nuevoEstado = null;
      if (aviso && mapaTransacciones.has(aviso)) {
        nuevoEstado = mapaTransacciones.get(aviso);
      } else if (clg && mapaTransacciones.has(clg)) {
        nuevoEstado = mapaTransacciones.get(clg);
      }

      if (nuevoEstado && valoresEstados[i][0] !== nuevoEstado) {
        valoresEstados[i][0] = nuevoEstado;
        huboModificacion = true;
      }
    }

    if (huboModificacion) {
      rangoEstados.setValues(valoresEstados);
    }

    // Asegurar que la columna A permanezca protegida contra edición de usuarios
    this.protegerColumnaEstado(hojaOp);
  },

  /**
   * Bloquea la Columna A de la hoja operativa para que solo los administradores
   * (@caduinmobiliaria.com / propietarios) puedan editarla, restringiendo a la notaría.
   * @param {GoogleAppsScript.Spreadsheet.Sheet} hojaOp
   */
  protegerColumnaEstado(hojaOp) {
    try {
      const rangoA = hojaOp.getRange("A:A");
      const proteccionesExistentes = hojaOp.getProtections(SpreadsheetApp.ProtectionType.RANGE);
      
      const yaProtegida = proteccionesExistentes.some(p => {
        const rng = p.getRange();
        return rng && rng.getA1Notation().includes("A:A") || (rng.getColumn() === 1 && rng.getNumColumns() === 1);
      });

      if (!yaProtegida) {
        const proteccion = rangoA.protect().setDescription("Protección de Columna ESTADO SAR");
        proteccion.removeEditors(proteccion.getEditors());
        if (proteccion.canDomainEdit()) proteccion.setDomainEdit(false);
      }
    } catch (err) {
      console.warn(`[Seguridad] No se pudo proteger Columna A: ${err.message}`);
    }
  },

  generarArchivoExcelSAR(loteId, encabezados, filas) {
    const tempSS = SpreadsheetApp.create(`EXPORT_DERECHOS_${loteId}`);
    try {
      const sheet = tempSS.getActiveSheet();
      sheet.setName("DERECHOS_DATA");

      // 1. Determinar si existe la columna "MES STOCK" (normalmente la última columna, índice 17 en B:S)
      let indiceMesStock = -1;
      for (let i = 0; i < encabezados.length; i++) {
        const tit = String(encabezados[i] || "").trim().toUpperCase();
        if (tit === "MES STOCK" || tit.includes("STOCK")) {
          indiceMesStock = i;
          break;
        }
      }

      // 2. Filtrar encabezados: Omitir "MES STOCK" y anteponer Columna A vacía con título '#'
      const encabezadosFiltrados = [];
      const indicesAExportar = [];
      for (let i = 0; i < encabezados.length; i++) {
        if (i === indiceMesStock) continue;
        encabezadosFiltrados.push(encabezados[i]);
        indicesAExportar.push(i);
      }
      const encabezadosFinales = ["#", ...encabezadosFiltrados];

      // 3. Filtrar filas de datos: Anteponer celda vacía ("") para Columna A y omitir "MES STOCK"
      const filasFinales = filas.map(f => {
        const filaFiltrada = indicesAExportar.map(idx => f[idx]);
        return ["", ...filaFiltrada];
      });

      sheet.getRange(1, 1, 1, encabezadosFinales.length).setValues([encabezadosFinales]).setFontWeight("bold");
      sheet.getRange(2, 1, filasFinales.length, encabezadosFinales.length).setValues(filasFinales);
      SpreadsheetApp.flush();

      // Descarga binaria con política de reintento resiliente (Retry Backoff)
      const url = `https://docs.google.com/feeds/download/spreadsheets/Export?key=${tempSS.getId()}&exportFormat=xlsx`;
      let blob = null;
      let intentos = 0;
      const maxIntentos = 3;

      while (intentos < maxIntentos) {
        try {
          intentos++;
          const response = UrlFetchApp.fetch(url, {
            headers: { Authorization: "Bearer " + ScriptApp.getOAuthToken() },
            muteHttpExceptions: false
          });
          blob = response.getBlob().setName(`${loteId}.xlsx`);
          if (blob && blob.getBytes().length > 0) {
            break;
          }
        } catch (fetchErr) {
          if (intentos >= maxIntentos) throw fetchErr;
          Utilities.sleep(500 * intentos);
        }
      }

      const carpeta = this.obtenerOCrearCarpeta(CONFIG.DRIVE.CARPETA_LOTES);
      const archivoFinal = carpeta.createFile(blob);

      // URL de descarga directa que fuerza el diálogo "Guardar como..." del navegador
      const downloadUrl = `https://drive.google.com/uc?export=download&id=${archivoFinal.getId()}`;
      const viewUrl = archivoFinal.getUrl();

      return {
        downloadUrl: downloadUrl,
        viewUrl: viewUrl,
        fileId: archivoFinal.getId()
      };
    } finally {
      // Garantizar eliminación del documento temporal de Google Drive
      try {
        DriveApp.getFileById(tempSS.getId()).setTrashed(true);
      } catch (cleanErr) {
        console.warn(`[Drive] No se pudo enviar temporal a papelera: ${cleanErr.message}`);
      }
    }
  },

  /**
   * Muestra un diálogo emergente interactivo que descarga automáticamente el archivo
   * en la máquina del usuario (abriendo el explorador de Windows para elegir carpeta: Descargas, Documentos, etc.)
   */
  mostrarDialogoDescargaLocal(loteId, totalRegistros, downloadUrl, viewUrl) {
    const htmlContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <base target="_blank">
        <link href="https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
          body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8fafc;
            color: #1e293b;
          }
          .card {
            background: #ffffff;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
            text-align: center;
          }
          .badge {
            display: inline-block;
            background: #dcfce7;
            color: #166534;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 12px;
          }
          h2 {
            margin: 0 0 8px 0;
            font-size: 20px;
            color: #0f172a;
          }
          p {
            font-size: 14px;
            color: #64748b;
            margin: 0 0 20px 0;
          }
          .stats {
            background: #f1f5f9;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 20px;
            font-size: 13px;
            text-align: left;
          }
          .stats-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
          }
          .stats-row:last-child {
            margin-bottom: 0;
          }
          .btn-download {
            display: block;
            width: 100%;
            box-sizing: border-box;
            background: #0284c7;
            color: #ffffff;
            text-decoration: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            border: none;
            transition: background 0.2s;
            margin-bottom: 10px;
          }
          .btn-download:hover {
            background: #0369a1;
          }
          .btn-secondary {
            display: inline-block;
            color: #64748b;
            text-decoration: underline;
            font-size: 12px;
            cursor: pointer;
          }
          .footer-note {
            margin-top: 14px;
            font-size: 11px;
            color: #94a3b8;
          }
        </style>
        <script>
          window.onload = function() {
            // Disparo automático de descarga local en el navegador
            const link = document.createElement('a');
            link.href = "${downloadUrl}";
            link.download = "${loteId}.xlsx";
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
          };
        </script>
      </head>
      <body>
        <div class="card">
          <span class="badge">Exportación Exitosa</span>
          <h2>Lote ${loteId}</h2>
          <p>Tu archivo Excel ha sido generado y preparado para tu computadora.</p>
          
          <div class="stats">
            <div class="stats-row"><span>Registros (D:G):</span> <strong>${totalRegistros}</strong></div>
            <div class="stats-row"><span>Formato:</span> <strong>Microsoft Excel (.xlsx)</strong></div>
            <div class="stats-row"><span>Almacenamiento:</span> <strong>Google Drive + Copia Local</strong></div>
          </div>

          <a href="${downloadUrl}" class="btn-download" download="${loteId}.xlsx">
            ️ Guardar en mi Computadora
          </a>

          <a href="${viewUrl}" class="btn-secondary" target="_blank">
            Ver copia de respaldo en Google Drive
          </a>

          <div class="footer-note">
             Si tu navegador tiene activada la opción <em>"Preguntar dónde guardar cada archivo"</em>, podrás seleccionar Documentos, Descargas o cualquier carpeta.
          </div>
        </div>
      </body>
      </html>
    `;

    const htmlOutput = HtmlService.createHtmlOutput(htmlContent)
      .setWidth(450)
      .setHeight(400);

    SpreadsheetApp.getUi().showModalDialog(htmlOutput, 'Descarga de Archivo Excel Derechos');
  },

  generarBackupJSON(loteId, timestamp, usuario, registros) {
    const payload = {
      version: "2.2.0",
      loteId: loteId,
      timestamp: timestamp.toISOString(),
      usuario: usuario,
      totalRegistros: registros.length,
      registros: registros
    };

    const carpeta = this.obtenerOCrearCarpeta(CONFIG.DRIVE.CARPETA_BACKUPS);
    carpeta.createFile(`${loteId}_BACKUP.json`, JSON.stringify(payload, null, 2), MimeType.PLAIN_TEXT);
  }
};

// ============================================================================
// 8. MOTOR DE EXTRACCIN Y REPORTE DE DUPLICADOS (B:K + N:S)
// ============================================================================
const ReportEngine = {
  generar(colsEvaluar, etiquetaTexto) {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const hojaOrigen = ss.getActiveSheet();
    const ui = SpreadsheetApp.getUi();

    if (hojaOrigen.getName() === CONFIG.SHEETS.REPORTE) {
      ui.alert(`Debes situarte en la hoja "${CONFIG.SHEETS.OPERATIVA}" para extraer el reporte.`);
      return;
    }

    const filaInicio = 2;
    const ultimaFila = hojaOrigen.getLastRow();

    if (ultimaFila < filaInicio) {
      ui.alert('No hay filas de datos suficientes en la hoja actual.');
      return;
    }

    const colInicioLectura = CONFIG.EXPORT.COL_INICIO; // B
    const totalColsLectura = CONFIG.EXPORT.NUM_COLS;   // 18 columnas (B a S)
    const filaTitulosCompleta = hojaOrigen.getRange(1, colInicioLectura, 1, totalColsLectura).getValues()[0];

    // Columnas a mostrar: B a K (0..9) y N a S (12..17) [omite L=10 y M=11]
    const indicesColumnas = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 13, 14, 15, 16, 17];
    const encabezadosExtraidos = indicesColumnas.map(idx => filaTitulosCompleta[idx] || `Columna ${idx + 2}`);
    const encabezados = [
      'Fila Original',
      ...encabezadosExtraidos,
      'Total Repeticiones'
    ];

    const totalFilas = ultimaFila - filaInicio + 1;
    const matrizDatos = hojaOrigen.getRange(filaInicio, colInicioLectura, totalFilas, totalColsLectura).getValues();

    const conteoClaves = Object.create(null);
    const filasMapeadas = [];

    for (let i = 0; i < matrizDatos.length; i++) {
      const numFilaReal = filaInicio + i;
      const fila = matrizDatos[i];

      // E=3, F=4, G=5, H=6, I=7 (relativo a B=0)
      const columnasComparacion = fila.slice(3, 3 + colsEvaluar);
      const estaVacia = columnasComparacion.every(val => val === "" || val === null || val === undefined);
      if (estaVacia || columnasComparacion[0] === "") continue;

      const clave = columnasComparacion
        .map(val => String(val).trim().toLowerCase())
        .join("|||");

      conteoClaves[clave] = (conteoClaves[clave] || 0) + 1;

      filasMapeadas.push({
        numFilaReal: numFilaReal,
        clave: clave,
        valoresReporte: indicesColumnas.map(idx => fila[idx])
      });
    }

    const duplicados = filasMapeadas.filter(item => conteoClaves[item.clave] > 1);

    if (duplicados.length === 0) {
      ui.alert(`No se encontraron duplicados evaluando (${etiquetaTexto}).`);
      return;
    }

    duplicados.sort((a, b) => a.clave.localeCompare(b.clave) || (a.numFilaReal - b.numFilaReal));

    let hojaReporte = ss.getSheetByName(CONFIG.SHEETS.REPORTE);
    if (!hojaReporte) {
      hojaReporte = ss.insertSheet(CONFIG.SHEETS.REPORTE);
    } else {
      hojaReporte.clear();
    }

    const salida = [encabezados];
    duplicados.forEach(item => {
      salida.push([
        item.numFilaReal,
        ...item.valoresReporte,
        conteoClaves[item.clave]
      ]);
    });

    hojaReporte.getRange(1, 1, salida.length, encabezados.length).setValues(salida);

    const headerRange = hojaReporte.getRange(1, 1, 1, encabezados.length);
    headerRange.setFontWeight('bold').setBackground(CONFIG.COLORS.HEADER_CONTROL);

    // Optimización de rendimiento: 1 sola llamada RPC nativa para ajustar el ancho de todas las columnas
    try {
      hojaReporte.autoResizeColumns(1, encabezados.length);
    } catch (e) {
      // Fallback retrocompatible
      for (let c = 1; c <= encabezados.length; c++) {
        hojaReporte.autoResizeColumn(c);
      }
    }

    ss.setActiveSheet(hojaReporte);
    ui.alert(`Reporte generado: ${duplicados.length} registros duplicados extraídos evaluando (${etiquetaTexto}).`);
  }
};
