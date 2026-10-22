# NOVAVAULT

One-page site (HTML + CSS + JS, no build step) plus two Vercel functions.

- `index.html`: the whole site (landing, scent finder, product pages)
- `img/`: product photos (WebP)
- `api/inventario.js`: the catalogue from the Google Sheet, for the site
- `api/whatsapp.js`: the WhatsApp sales assistant (WhatsApp Cloud API + Claude)
- `lib/`: sheet access, catalogue parsing and the assistant's prompt and tools
- `hoja/`: the sheet template, its Apps Script and the setup guide (`hoja/LEEME.md`, in Spanish)

Stock, prices and business facts live in the Google Sheet. To mark a perfume as sold out, set its `estado` to `agotado` there; the site and the assistant pick it up within a minute. The `AR` and `DE` arrays in `index.html` are only the fallback when the sheet can't be reached.
