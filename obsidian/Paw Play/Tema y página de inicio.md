---
tags: [paw-play, shopify, tema]
---
# 🎨 Tema y página de inicio

## Problema que encontramos
El tema (Horizon, "Gorrion Cazador") tenía la landing del pajarito **escrita dentro de `layout/theme.liquid`**, probablemente por la app Store Launch. Por eso:
- en la página de inicio siempre salía el gato con el pajarito, sin importar lo que se pusiera;
- el menú y el pie de página no aparecían en el inicio.

**Arreglo:** en `layout/theme.liquid` se cambiaron las 3 condiciones `{%- unless template.name == 'index' -%}` por `{%- unless false -%}`. Hay una copia del archivo original.

## Versiones del tema
| Tema | ID | Estado |
|---|---|---|
| Horizon - Gorrion Cazador | 186978173143 | Tema anterior (respaldo) |
| Paw Play - Inicio con todos los productos | 187098104023 | Publicado, pero con el problema del layout |
| **Paw Play - Inicio v2 (con todos los productos)** | **187098530007** | ✅ **Este es el que hay que publicar** |

Editor de la v2: https://admin.shopify.com/store/pawplay-5118/themes/187098530007/editor

## Nuevo inicio (sección `paw-play-home`)
1. **Banner llamativo:** etiqueta roja "🎄 Regalos de Navidad para tu gato", título "Juguetes que tu gato *sí* va a usar" y huellitas animadas.
2. **Franja amarilla animada:** Enviado desde EE. UU. · Devoluciones gratis en 30 días · Pago seguro · Solo productos para gatos · El regalo perfecto.
3. **Todos los productos** de la colección "Juguetes para gatos":
   - el pajarito lleva la etiqueta "⭐ El favorito";
   - 2 por fila en celular.
4. **Ventana al hacer clic en un producto:**
   - fotos con miniaturas;
   - precio y selector de opción;
   - botón "Agregar al carrito";
   - descripción y link a la página completa.
5. **Más abajo:** por qué comprar con nosotros, la sección del pajarito y el cierre "Un gato que juega es un gato feliz" con link al Instagram.

Es bilingüe: cambia sola al inglés en `/en`. Si agregas productos a la colección, aparecen solos.

## Archivos (repositorio Novavault, rama `ccr-6bd8489b-rbzmzb`)
- `paw-play/theme/paw-play-home.liquid`: sección del inicio
- `paw-play/theme/theme.liquid`: layout arreglado
- `paw-play/theme/theme.liquid.backup`: layout original

> [!warning] Barra de "Oferta del día"
> En las páginas de producto hay una barra con cuenta regresiva hasta la medianoche ("El día termina en…"). Es urgencia falsa y conviene quitarla o cambiarla. Ver [[Reglas de la marca]].
