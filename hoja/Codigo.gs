// NOVAVAULT: puente entre la hoja de Google, la página y el bot de WhatsApp.
// Pégalo en Extensiones > Apps Script de la hoja e impleméntalo como aplicación web (ver hoja/LEEME.md).
// Propiedades del script: TOKEN (la misma clave que HOJA_TOKEN en Vercel) y CORREO (a dónde llegan los avisos).

const PESTANAS = {
  Pedidos: ['fecha', 'telefono', 'nombre', 'articulos', 'tipo', 'entrega', 'ciudad', 'zip', 'notas', 'estado'],
  Chats: ['telefono', 'nombre', 'bot', 'ultimo_mensaje', 'motivo'],
  Mensajes: ['fecha', 'telefono', 'rol', 'texto', 'contenido', 'wa_id']
};
// una conversación termina tras 24 h sin mensajes; la siguiente empieza de cero
const SESION_MS = 24 * 60 * 60 * 1000;
const MAX_TURNOS = 200;

function doGet(e) {
  return responder_(() => {
    autorizar_(e.parameter.token);
    if (e.parameter.accion === 'inventario') return { productos: filas_('Inventario'), datos: datos_() };
    if (e.parameter.accion === 'chat') return chat_(String(e.parameter.tel));
    throw new Error('accion desconocida');
  });
}

function doPost(e) {
  return responder_(() => {
    const p = JSON.parse(e.postData.contents);
    autorizar_(p.token);
    const lock = LockService.getScriptLock();
    lock.waitLock(20000);
    try {
      if (p.accion === 'mensajes') return guardarMensajes_(p);
      if (p.accion === 'pedido') return guardarPedido_(p);
      if (p.accion === 'pausar') return pausar_(p.tel, p.nombre, p.motivo);
      throw new Error('accion desconocida');
    } finally {
      lock.releaseLock();
    }
  });
}

// Ejecútala una vez desde el editor: crea las pestañas Pedidos, Chats y Mensajes y pide los permisos de correo.
function configurar() {
  Object.keys(PESTANAS).forEach(hoja_);
  MailApp.getRemainingDailyQuota();
}

// Solo la primera vez: llena Inventario y Datos con la plantilla de hoja/*.csv del repositorio.
// Todo queda como texto, así "9pm" o "23.00" no se vuelven horas ni fechas. No toca pestañas que ya tienen datos.
const PLANTILLA = 'https://raw.githubusercontent.com/jarvizandjuan-debug/Novavault/sistema-inventario/hoja/';
function cargarPlantilla() {
  ['Inventario', 'Datos'].forEach(nombre => {
    const libro = SpreadsheetApp.getActive();
    const h = libro.getSheetByName(nombre) || libro.insertSheet(nombre);
    if (h.getLastRow() > 0) throw new Error(`La pestaña ${nombre} ya tiene datos; bórrala primero si quieres recargarla.`);
    const filas = Utilities.parseCsv(UrlFetchApp.fetch(PLANTILLA + nombre + '.csv').getContentText('UTF-8'));
    h.getRange(1, 1, filas.length, filas[0].length).setNumberFormat('@').setValues(filas);
    h.setFrozenRows(1);
  });
}

function responder_(fn) {
  let salida;
  try {
    salida = { ok: true, ...fn() };
  } catch (err) {
    salida = { ok: false, error: String(err.message || err) };
  }
  return ContentService.createTextOutput(JSON.stringify(salida)).setMimeType(ContentService.MimeType.JSON);
}

function autorizar_(token) {
  const esperado = PropertiesService.getScriptProperties().getProperty('TOKEN');
  if (!esperado || token !== esperado) throw new Error('token invalido');
}

function hoja_(nombre) {
  const libro = SpreadsheetApp.getActive();
  let h = libro.getSheetByName(nombre);
  if (!h) {
    h = libro.insertSheet(nombre);
    h.appendRow(PESTANAS[nombre]);
    h.setFrozenRows(1);
  }
  return h;
}

// filas como objetos, con los encabezados en minúsculas
function filas_(nombre) {
  const h = SpreadsheetApp.getActive().getSheetByName(nombre);
  if (!h) return [];
  const [enc, ...resto] = h.getDataRange().getDisplayValues();
  const claves = enc.map(c => String(c).trim().toLowerCase());
  return resto.filter(f => f.some(v => v !== '')).map(f => Object.fromEntries(claves.map((c, i) => [c, f[i]])));
}

function datos_() {
  return Object.fromEntries(filas_('Datos').filter(f => f.clave).map(f => [f.clave.trim(), f.valor]));
}

function filaChat_(tel) {
  const h = hoja_('Chats');
  const tels = h.getRange(1, 1, h.getLastRow(), 1).getDisplayValues().map(f => f[0]);
  const i = tels.indexOf(tel);
  return { h, fila: i > 0 ? i + 1 : 0 };
}

function chat_(tel) {
  const { h, fila } = filaChat_(tel);
  const bot = fila ? String(h.getRange(fila, 3).getValue()).trim().toLowerCase() : 'activo';
  const todos = hoja_('Mensajes').getDataRange().getValues().slice(1).filter(f => String(f[1]) === tel);
  // la conversación actual: los mensajes desde el último silencio de más de 24 h
  let inicio = todos.length;
  while (inicio > 0) {
    const sig = inicio < todos.length ? todos[inicio][0] : new Date();
    if (sig - todos[inicio - 1][0] > SESION_MS) break;
    inicio--;
  }
  const sesion = todos.slice(inicio);
  return {
    bot: bot === 'pausado' ? 'pausado' : 'activo',
    ids: todos.map(f => String(f[5])).filter(Boolean),
    mensajes: sesion.length > MAX_TURNOS ? [] : sesion.filter(f => f[4]).map(f => JSON.parse(f[4]))
  };
}

// texto de clientes o del bot: si empieza con = + - @ la hoja lo tomaría como fórmula
function texto_(s) {
  s = String(s == null ? '' : s);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function guardarMensajes_(p) {
  const ahora = new Date();
  const h = hoja_('Mensajes');
  p.filas.forEach(m => h.appendRow([ahora, "'" + p.tel, m.rol, texto_(m.texto), m.contenido ? JSON.stringify(m.contenido) : '', m.wa_id || '']));
  const { h: hc, fila } = filaChat_(p.tel);
  if (fila) {
    if (p.nombre) hc.getRange(fila, 2).setValue(texto_(p.nombre));
    hc.getRange(fila, 4).setValue(ahora);
  } else {
    hc.appendRow(["'" + p.tel, texto_(p.nombre), 'activo', ahora, '']);
  }
  return {};
}

function guardarPedido_(p) {
  const d = p.pedido;
  const articulos = d.articulos.map(a => `${a.cantidad} x ${a.perfume}`).join(', ');
  hoja_('Pedidos').appendRow([new Date(), "'" + p.tel, texto_(d.nombre), texto_(articulos), d.tipo, d.entrega, texto_(d.ciudad), "'" + d.zip, texto_(d.notas), 'nuevo']);
  avisar_(`Nuevo pedido de ${d.nombre}`, [
    `Cliente: ${d.nombre} (+${p.tel})`,
    `Artículos: ${articulos}`,
    `Tipo: ${d.tipo} · Entrega: ${d.entrega} · ${d.ciudad} ${d.zip}`,
    d.notas ? `Notas: ${d.notas}` : '',
    '',
    'El bot quedó en pausa en este chat. Responde por WhatsApp para cerrar el pago y la entrega.',
    `Chat: https://wa.me/${p.tel}`
  ]);
  return pausar_(p.tel, d.nombre, 'pedido confirmado', true);
}

function pausar_(tel, nombre, motivo, sinAviso) {
  const { h, fila } = filaChat_(tel);
  if (fila) {
    h.getRange(fila, 3).setValue('pausado');
    h.getRange(fila, 5).setValue(texto_(motivo));
  } else {
    h.appendRow(["'" + tel, texto_(nombre), 'pausado', new Date(), texto_(motivo)]);
  }
  if (!sinAviso) {
    avisar_(`Un cliente te necesita en WhatsApp`, [
      `Cliente: ${nombre || 'sin nombre'} (+${tel})`,
      `Motivo: ${motivo}`,
      '',
      'El bot quedó en pausa en este chat. Cuando termines, escribe "activo" en la columna bot de la pestaña Chats.',
      `Chat: https://wa.me/${tel}`
    ]);
  }
  return {};
}

function avisar_(asunto, lineas) {
  const correo = PropertiesService.getScriptProperties().getProperty('CORREO') || Session.getEffectiveUser().getEmail();
  MailApp.sendEmail(correo, `NOVAVAULT: ${asunto}`, lineas.filter(l => l !== null).join('\n'));
}
