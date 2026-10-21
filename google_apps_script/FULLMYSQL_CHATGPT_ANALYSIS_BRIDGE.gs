/**
 * FULL MYSQL -> Google Sheet bridge for FULL_MYSQL_CHATGPT_ANALYSIS.
 *
 * Deploy this standalone Apps Script as a Web App:
 *   Execute as: Me (the deploying Google account)
 *   Who has access: Anyone
 *
 * Configure two Script Properties in Project Settings:
 *   FULLMYSQL_SHEET_ID
 *   FULLMYSQL_WEBHOOK_SECRET
 *
 * The DigitalOcean FULL MYSQL service calls this endpoint over HTTPS.
 * The endpoint is intentionally narrow: it can only read/write the configured
 * spreadsheet and only the approved MYSQL_* / BRIDGE_STATUS tabs.
 */

const FULLMYSQL_BRIDGE_VERSION = '1.1.0-upload-history';

const ALLOWED_TABS = new Set([
  'MYSQL_SOURCE_STATUS',
  'MYSQL_LOOKUP_INDEX',
  'MYSQL_QUICK_CHECK_CURRENT',
  'MYSQL_FAMILY_CURRENT',
  'MYSQL_ANALYSIS_CURRENT',
  'MYSQL_QA_HOLD',
  'MYSQL_NEGATIVE_STOCK',
  'MYSQL_COST_BACKFILL',
  'BRIDGE_STATUS',
  'ANALYSIS_STATUS',
  'ANALYSIS_PRICE_EPISODES',
  'ANALYSIS_PRICE_TRACKING',
  'ANALYSIS_UPC_DAILY',
  'ANALYSIS_ITEM_REFERENCE',
  'ANALYSIS_PRICE_EVENTS',
  'ANALYSIS_COST_HISTORY',
  'ANALYSIS_COVERAGE',
  'ANALYSIS_SOURCES',
  'ANALYSIS_DEPT_DAILY',
  'ANALYSIS_FAMILY_REFERENCE',
  'ANALYSIS_RULES',
]);

function _json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function _properties_() {
  return PropertiesService.getScriptProperties();
}

function _configuredSheetId_() {
  const value = String(_properties_().getProperty('FULLMYSQL_SHEET_ID') || '').trim();
  if (!value) {
    throw new Error('FULLMYSQL_SHEET_ID Script Property is not configured.');
  }
  return value;
}

function _configuredSecret_() {
  const value = String(_properties_().getProperty('FULLMYSQL_WEBHOOK_SECRET') || '');
  if (value.length < 24) {
    throw new Error('FULLMYSQL_WEBHOOK_SECRET must be at least 24 characters.');
  }
  return value;
}

function _assertAuthorized_(payload) {
  if (!payload || typeof payload !== 'object') {
    throw new Error('JSON object body required.');
  }
  const supplied = String(payload.secret || '');
  const expected = _configuredSecret_();
  if (!supplied || supplied !== expected) {
    throw new Error('UNAUTHORIZED');
  }

  const configuredSheetId = _configuredSheetId_();
  const suppliedSheetId = String(payload.spreadsheet_id || '');
  if (!suppliedSheetId || suppliedSheetId !== configuredSheetId) {
    throw new Error('SPREADSHEET_ID_MISMATCH');
  }
  return configuredSheetId;
}

function _assertTab_(tab) {
  const name = String(tab || '');
  if (!ALLOWED_TABS.has(name)) {
    throw new Error('TAB_NOT_ALLOWED: ' + name);
  }
  return name;
}

function _ensureTab_(ss, title) {
  let sheet = ss.getSheetByName(title);
  if (!sheet) {
    sheet = ss.insertSheet(title);
  }
  return sheet;
}

function _normalizeMatrix_(values) {
  if (!Array.isArray(values) || values.length === 0) {
    throw new Error('VALUES_REQUIRED');
  }
  let width = 0;
  values.forEach(row => {
    if (!Array.isArray(row)) {
      throw new Error('ROW_MUST_BE_ARRAY');
    }
    width = Math.max(width, row.length);
  });
  if (width < 1) {
    throw new Error('VALUES_WIDTH_REQUIRED');
  }
  const cells = values.length * width;
  if (cells > 50000) {
    throw new Error('CHUNK_TOO_LARGE');
  }
  return values.map(row => {
    const out = row.slice();
    while (out.length < width) out.push('');
    return out;
  });
}

function _parseAllowedA1_(a1) {
  const text = String(a1 || '').trim();
  const match = text.match(/^'([^']+)'!([A-Z]+\d+:[A-Z]+\d+)$/i);
  if (!match) {
    throw new Error('INVALID_A1');
  }
  const tab = _assertTab_(match[1]);
  return { tab: tab, range: match[2] };
}

function _handleWriteChunk_(ss, payload) {
  const title = _assertTab_(payload.tab);
  const startRow = Number(payload.start_row || 0);
  if (!Number.isInteger(startRow) || startRow < 1 || startRow > 1000000) {
    throw new Error('INVALID_START_ROW');
  }

  const values = _normalizeMatrix_(payload.values);
  const width = values[0].length;
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    const sheet = _ensureTab_(ss, title);
    if (payload.clear === true) {
      sheet.clearContents();
    }
    const neededRows = startRow + values.length - 1;
    if (sheet.getMaxRows() < neededRows) {
      sheet.insertRowsAfter(sheet.getMaxRows(), neededRows - sheet.getMaxRows());
    }
    if (sheet.getMaxColumns() < width) {
      sheet.insertColumnsAfter(sheet.getMaxColumns(), width - sheet.getMaxColumns());
    }
    sheet.getRange(startRow, 1, values.length, width).setValues(values);
    SpreadsheetApp.flush();
  } finally {
    lock.releaseLock();
  }

  return {
    ok: true,
    action: 'write_tab_chunk',
    tab: title,
    start_row: startRow,
    rows_written: values.length,
    columns_written: width,
  };
}

function _handleClearTab_(ss, payload) {
  const title = _assertTab_(payload.tab);
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    const sheet = _ensureTab_(ss, title);
    sheet.clearContents();
    SpreadsheetApp.flush();
  } finally {
    lock.releaseLock();
  }
  return { ok: true, action: 'clear_tab', tab: title };
}

function _handleReadRange_(ss, payload) {
  const parsed = _parseAllowedA1_(payload.a1);
  const sheet = ss.getSheetByName(parsed.tab);
  if (!sheet) {
    return { ok: true, action: 'read_range', a1: payload.a1, values: [] };
  }
  const match = parsed.range.match(/^([A-Z]+)(\d+):([A-Z]+)(\d+)$/i);
  const column = text => text.toUpperCase().split('').reduce((n,c) => n*26+c.charCodeAt(0)-64,0);
  const firstRow=Number(match[2]),lastRow=Math.min(Number(match[4]),sheet.getLastRow());
  const firstCol=column(match[1]),lastCol=Math.min(column(match[3]),sheet.getMaxColumns());
  if(firstRow>lastRow||firstCol>lastCol)return {ok:true,action:'read_range',a1:payload.a1,values:[]};
  if((lastRow-firstRow+1)*(lastCol-firstCol+1)>50000)throw new Error('READ_TOO_LARGE');
  const values = sheet.getRange(firstRow,firstCol,lastRow-firstRow+1,lastCol-firstCol+1).getValues();
  return { ok: true, action: 'read_range', a1: payload.a1, values: values };
}

function doGet() {
  return _json_({
    ok: true,
    service: 'FULL_MYSQL_APPS_SCRIPT_BRIDGE',
    version: FULLMYSQL_BRIDGE_VERSION,
  });
}

function doPost(e) {
  try {
    const raw = e && e.postData ? e.postData.contents : '';
    const payload = JSON.parse(raw || '{}');
    const spreadsheetId = _assertAuthorized_(payload);
    const ss = SpreadsheetApp.openById(spreadsheetId);
    const action = String(payload.action || '');

    if (action === 'write_tab_chunk') {
      return _json_(_handleWriteChunk_(ss, payload));
    }
    if (action === 'clear_tab') {
      return _json_(_handleClearTab_(ss, payload));
    }
    if (action === 'read_range') {
      return _json_(_handleReadRange_(ss, payload));
    }
    throw new Error('ACTION_NOT_ALLOWED');
  } catch (err) {
    return _json_({
      ok: false,
      error: String(err && err.message ? err.message : err),
      version: FULLMYSQL_BRIDGE_VERSION,
    });
  }
}

