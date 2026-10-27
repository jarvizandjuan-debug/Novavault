# NOVAVAULT

Static one-page site (HTML + CSS + JS, no build step).

- `index.html`: the whole site (landing, Most Wanted / Arab / Designer views, product pages)
- `img/`: product photos (WebP)

To mark a perfume as sold out, add `sold:true` to its entry in the `AR` or `DE` array in `index.html` (and remove it again when it is back in stock).

## Reels Vault sales page

- `reels/index.html`: sales page for the Instagram skills kit (the 13 `ig-*` skills in `.claude/skills/`, MIT licence, © Jake Schincariol). Same design system, EN/ES toggle.
- Price and payment link live in `OFFER` at the bottom of the file. With both empty the page shows no price and every "Get Reels Vault" button opens WhatsApp with the order message written. Paste a Stripe, Hotmart, Gumroad or Shopify link into `checkout` to send buyers there instead.
