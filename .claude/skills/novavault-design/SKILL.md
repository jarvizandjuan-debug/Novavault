---
name: novavault-design
description: Design system and house rules for the NOVAVAULT perfume site (static index.html + img/, no build step). Use whenever editing, reviewing or extending the NOVAVAULT site — adding or removing a perfume, marking one sold out / back in stock ("agotado", "ya hay"), changing copy or translations (EN/ES), styling, layout, motion, the WhatsApp/Instagram order links, or any new page or section for NOVAVAULT.
---

# NOVAVAULT design system

**Idea:** dark = brand, navigation and proof; white = product. The landing is black with white category tiles; the three collection views (Most Wanted / Arab / Designer) and every product page are white galleries.

## Tokens

| Token | Value |
|---|---|
| Matte black | `#0a0a0a` |
| Vault gold | `#d4af37` (highlight `#f3d98b`, text on white `#7a5f10`) |
| Paper / ink | `#ffffff` / `#14110a` |
| Display / body | Marcellus / Jost |
| Type scale | 12 / 14 / 16 / 22 px, fluid 32-48 px, fluid 40-100 px. Weights 300 / 400 / 500 only |
| Space | 8pt / 4pt grid, section padding 72 px (narrow) / 120 px (768+), gutter 24 px |
| Shape | 2 px radius, 1 px hairline on every raised surface, shadows only on hover and always below 8% alpha, no glass, no glow |
| Buttons | 48 px high. Primary = gold fill. Secondary = outline (gold on black, ink on white) |

## Fixed owner rules (never change without the owner asking)

- English by default, with an EN/ES toggle. Every visible string needs a Spanish version (`data-es="..."` on elements, `es:` on product entries).
- **No prices anywhere.**
- Sold-out items stay visible with a "Sold out" badge and disabled order buttons.
- WhatsApp **+1 510 978 8240** (`wa.me/15109788240`) with a pre-filled message per perfume.
- Instagram DM via `https://ig.me/m/novavaultcolognes`.

## Accessibility and tone

- Target WCAG 2.1 AA: 4.5:1 text contrast, 44×44 px hit targets.
- Tone: opinionated and direct, sentence case, verb-first buttons ("Order on WhatsApp", "Shop the collection").
- No icon library; the back chevron is CSS.
- Banned: glassmorphism / `backdrop-filter`, rainbow or multi-hue CTAs, glow stacks, cartoon art, decorative pills around static text, prices.

## Layout and behaviour

- Breakpoints: 375 (narrow), 768 (medium), 1280 (wide). On narrow the nav collapses to a Menu control.
- Both page overlays (collection view, product page) make the site underneath `inert`, keep Tab inside, close with Esc and return focus to the tile or card that opened them.
- Page patterns: landing = marketing home; collection views = product listing; product page = detail.
- Motion: UI transitions 200 / 300 ms ease-out. Ambient brand motion (hero intro, one-time logo glint, floating bottles, gold dust, light beam, ribbon ticker) is intentional, uses transform/opacity only (the glint animates background-position once), and switches off under `prefers-reduced-motion`.

## Product data (in `index.html`)

Perfumes live in two arrays: `AR` (Arab) and `DE` (Designer). Entry shape:

```js
{id:'khamrah-dukhan',n:'Khamrah Dukhan',b:'Lattafa',sold:true,d:'English description…',es:'Descripción en español…'}
```

- `id` must match the image file `img/<id>.webp`.
- **Mark sold out:** add `sold:true`. **Back in stock:** remove it.
- **Add a perfume:** add an entry to `AR` or `DE` with both `d` and `es`, and add a WebP photo at `img/<id>.webp`.
- **Most Wanted** is a list of ids in the collections config (`most:{ids:[...]}`); add or remove ids there. Landing tile thumbnails come from `data-ph="id1,id2,id3"` on each `.cat` tile.

## Before finishing any change

1. No prices introduced; the WhatsApp number and Instagram link are unchanged.
2. Every new string has its Spanish version.
3. Colours, type sizes and weights come from the tokens above.
4. Check at 375 px wide: no horizontal scroll, targets ≥ 44 px.
