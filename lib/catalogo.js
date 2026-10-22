// Turns the Inventario tab (written by hand, in Spanish) into clean product records.

const plano = s => String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').trim().toLowerCase();
const si = s => ['si', 'yes', 'x', 'true', '1'].includes(plano(s));

const ESTILOS = { calido: 'warm', dulce: 'warm', warm: 'warm', fresco: 'fresh', fresh: 'fresh', floral: 'floral', intenso: 'dark', ahumado: 'dark', dark: 'dark' };

function estado(s) {
  const e = plano(s);
  if (e.startsWith('disponible') || e === 'available' || e === 'si') return 'available';
  if (e.startsWith('agotado') || e === 'sold out' || e === 'no') return 'sold';
  return 'ask'; // "consultar" or blank: the owner has to confirm
}

export function productos(filas) {
  return filas
    .filter(f => f.id && f.nombre)
    .map(f => {
      // "54.99", "$54.99" or, from a Spanish-locale sheet, "54,99"
      let p = String(f.precio ?? '').replace(/[$\s]/g, '');
      p = /,\d{1,2}$/.test(p) ? p.replace(/\./g, '').replace(',', '.') : p.replace(/,/g, '');
      const precio = parseFloat(p);
      return {
        id: plano(f.id),
        n: String(f.nombre).trim(),
        b: String(f.casa).trim(),
        c: plano(f.coleccion).startsWith('arab') ? 'arab' : 'designer',
        m: [...new Set(String(f.estilos).split(/[,/]/).map(x => ESTILOS[plano(x)]).filter(Boolean))],
        most: si(f.mas_buscado),
        stock: estado(f.estado),
        price: Number.isFinite(precio) ? precio : null,
        web: si(f.en_pagina),
        d: String(f.descripcion_en ?? '').trim(),
        es: String(f.descripcion_es ?? '').trim()
      };
    });
}
