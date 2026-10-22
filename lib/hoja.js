// Talks to the Google Sheet through its Apps Script web app (hoja/Codigo.gs).
// HOJA_URL is the web app's /exec URL and HOJA_TOKEN the TOKEN script property.

async function llamar(res) {
  if (!res.ok) throw new Error(`hoja: HTTP ${res.status}`);
  const json = await res.json();
  if (!json.ok) throw new Error(`hoja: ${json.error}`);
  return json;
}

function url(params) {
  const u = new URL(process.env.HOJA_URL);
  for (const [k, v] of Object.entries({ ...params, token: process.env.HOJA_TOKEN })) u.searchParams.set(k, v);
  return u;
}

export const leerInventario = () => fetch(url({ accion: 'inventario' })).then(llamar);

export const leerChat = tel => fetch(url({ accion: 'chat', tel })).then(llamar);

// Apps Script answers a POST with a redirect; fetch follows it to read the result
export const escribir = (accion, datos) =>
  fetch(process.env.HOJA_URL, {
    method: 'POST',
    headers: { 'content-type': 'text/plain' },
    body: JSON.stringify({ ...datos, accion, token: process.env.HOJA_TOKEN })
  }).then(llamar);
