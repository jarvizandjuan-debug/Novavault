// GET /api/inventario: the catalogue the website shows, read from the Google Sheet.
// Vercel's CDN keeps it for a minute, so a change in the sheet reaches the site within about a minute.
import { leerInventario } from '../lib/hoja.js';
import { productos } from '../lib/catalogo.js';

export async function GET() {
  try {
    const { productos: filas } = await leerInventario();
    const lista = productos(filas)
      .filter(p => p.web)
      .map(({ id, n, b, c, m, most, stock, d, es }) => ({ id, n, b, c, m, most, sold: stock === 'sold', d, es }));
    return Response.json(
      { productos: lista },
      { headers: { 'cache-control': 'public, s-maxage=60, stale-while-revalidate=600' } }
    );
  } catch (err) {
    console.error(err);
    // the page falls back to the catalogue built into index.html
    return Response.json({ error: 'inventario no disponible' }, { status: 502, headers: { 'cache-control': 'no-store' } });
  }
}
