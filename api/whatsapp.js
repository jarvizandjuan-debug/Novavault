// /api/whatsapp: webhook for the WhatsApp Business Cloud API (Meta).
// GET answers Meta's verification; POST receives customer messages, answers with the agent and logs to the sheet.
import { createHmac, timingSafeEqual } from 'node:crypto';
import { waitUntil } from '@vercel/functions';
import { leerChat, leerInventario, escribir } from '../lib/hoja.js';
import { responder, HANDOFF } from '../lib/agente.js';

// sheet reads, the Claude call and the reply run after the 200, inside this budget
export const maxDuration = 60;

const GRAPH =`https://graph.facebook.com/${process.env.WHATSAPP_API_VERSION || 'v23.0'}`;

export function GET(request) {
  const q = new URL(request.url).searchParams;
  if (q.get('hub.mode') === 'subscribe' && q.get('hub.verify_token') === process.env.WHATSAPP_VERIFY_TOKEN) {
    return new Response(q.get('hub.challenge'));
  }
  return new Response('forbidden', { status: 403 });
}

function firmaValida(cuerpo, firma) {
  if (!firma?.startsWith('sha256=')) return false;
  const esperada = createHmac('sha256', process.env.WHATSAPP_APP_SECRET).update(cuerpo).digest();
  const recibida = Buffer.from(firma.slice(7), 'hex');
  return recibida.length === esperada.length && timingSafeEqual(recibida, esperada);
}

export async function POST(request) {
  const cuerpo = await request.text();
  if (!firmaValida(cuerpo, request.headers.get('x-hub-signature-256'))) {
    return new Response('bad signature', { status: 401 });
  }
  const evento = JSON.parse(cuerpo);
  for (const entry of evento.entry ?? []) {
    for (const change of entry.changes ?? []) {
      const v = change.value ?? {};
      for (const msg of v.messages ?? []) {
        const nombre = v.contacts?.find(c => c.wa_id === msg.from)?.profile?.name ?? '';
        // answer Meta right away (it retries slow webhooks) and do the work after
        waitUntil(atender(msg, nombre).catch(err => console.error('whatsapp', msg.id, err)));
      }
    }
  }
  return new Response('ok');
}

function textoDe(msg) {
  if (msg.type === 'text') return msg.text.body;
  if (msg.type === 'button') return msg.button.text;
  if (msg.type === 'interactive') return msg.interactive.button_reply?.title ?? msg.interactive.list_reply?.title ?? '';
  const tipo = { audio: 'a voice note', image: 'a photo', video: 'a video', sticker: 'a sticker', document: 'a document', location: 'a location' }[msg.type] ?? 'a message';
  const pie = msg.image?.caption || msg.video?.caption;
  return `[The customer sent ${tipo}, which you cannot see or hear${pie ? `, with the caption: "${pie}"` : ''}. Ask them to write it as text.]`;
}

async function atender(msg, nombre) {
  const tel = msg.from;
  const [chat, inventario] = await Promise.all([leerChat(tel), leerInventario()]);
  if (chat.ids.includes(msg.id)) return; // Meta delivered this message twice
  const entrada = textoDe(msg);
  const cliente = { rol: 'cliente', texto: entrada, contenido: { role: 'user', content: entrada }, wa_id: msg.id };

  if (chat.bot === 'pausado') {
    // the owner is handling this chat: keep the message for context, stay quiet
    await escribir('mensajes', { tel, nombre, filas: [cliente] });
    return;
  }

  let r;
  try {
    r = await responder({ inventario, historial: chat.mensajes, entrada, chat: { tel, nombre } });
  } catch (err) {
    console.error(err);
    await escribir('mensajes', { tel, nombre, filas: [cliente] });
    await escribir('pausar', { tel, nombre, motivo: 'el bot tuvo un error al responder' });
    await enviar(tel, `${HANDOFF.es}\n\n${HANDOFF.en}`);
    return;
  }

  const [, ...resto] = r.nuevos;
  const filas = [
    cliente,
    ...resto.map(m => ({
      rol: m.role === 'assistant' ? 'bot' : 'herramienta',
      texto: Array.isArray(m.content) ? m.content.filter(b => b.type === 'text').map(b => b.text).join('\n') : '',
      contenido: m
    }))
  ];
  await escribir('mensajes', { tel, nombre, filas });
  if (r.texto) await enviar(tel, r.texto);
}

async function enviar(tel, texto) {
  const res = await fetch(`${GRAPH}/${process.env.WHATSAPP_PHONE_ID}/messages`, {
    method: 'POST',
    headers: { authorization: `Bearer ${process.env.WHATSAPP_TOKEN}`, 'content-type': 'application/json' },
    body: JSON.stringify({ messaging_product: 'whatsapp', to: tel, type: 'text', text: { body: texto.slice(0, 4096) } })
  });
  if (!res.ok) throw new Error(`whatsapp send ${res.status}: ${await res.text()}`);
}
