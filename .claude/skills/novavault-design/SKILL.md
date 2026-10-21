---
name: novavault-design
description: Design system and house rules for the NOVAVAULT perfume site (static index.html + img/, no build step). Use whenever editing, reviewing or extending the NOVAVAULT site — adding or removing a perfume, marking one sold out / back in stock ("agotado", "ya hay"), changing copy or translations (EN/ES), styling, layout, motion, the WhatsApp/Instagram order links, or any new page or section for NOVAVAULT.
---

# NOVAVAULT design system (v2: editorial gallery)

**Idea:** black, gold and white from the logo. The hero belongs to the featured perfume (its colour fills the whole hero); the rest of the site is a calm bone-coloured gallery with white product cards, and ink sections carry the proof (why us, wholesale). Full token table in `DESIGN.md`.

## Tokens

| Token | Value |
|---|---|
| Bone (page) / paper (product) | `#f4f0e8` / `#ffffff` |
| Ink / muted / hairline | `#0b0b0b` / `#635b51` / `#e2dace` |
| Gold (logo) / dark gold text on bone | `#d4af37` / `#7a5f10` |
| Logo | `img/logo.webp` round black-and-gold badge; tagline "Exclusive finds. Premium quality. Trusted by you." |
| Cream (text on dark) | `#f6efe4` |
| Display / body | Instrument Serif (400 + italic) / Manrope 400-500-600 |
| Type scale | 12 / 14 / 16 / 20 / 28 px, fluid 36-56 px, fluid 48-92 px |
| Space | 8pt grid, section padding 72 px / 120 px (768+), gutter 24 / 40 px |
| Shape | Pills for buttons and chips, 12 px cards, 1 px hairlines, shadows only on hover (<8% alpha), no glass, no glow |
| Buttons | 48 px high. Solid = ink (cream inside the hero). Line = 1 px outline |

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
- Banned: glassmorphism / `backdrop-filter`, rainbow or multi-hue CTAs, glow stacks, cartoon art, prices.

## Layout and behaviour

- Sections in order: hero (featured perfume picker), houses ribbon, scent finder (`#scents`), why us (`#why`, ink), how to order (`#order`), wholesale (`#wholesale`, dark band), contact (`#contact`), footer.
- Breakpoints: 375, 768, 960 (nav links show; below it a Menu control), 1280.
- Product page `#p=<id>` is a white overlay: the site underneath is `inert`, Tab stays inside, Esc closes it, focus returns to the card. Old links `#c=arab|designer|most` set the finder's collection filter.
- Motion: UI transitions 200 / 300 ms ease-out; sections fade up once on scroll. Hero motion (bottle entrance, cursor tilt, flakes pushed by the pointer, spin-and-swap on pick, colour morph) uses Motion from jsDelivr and is off under `prefers-reduced-motion`.

## Product data (in `index.html`)

Perfumes live in two arrays: `AR` (Arab) and `DE` (Designer). Entry shape:

```js
{id:'khamrah-dukhan',n:'Khamrah Dukhan',b:'Lattafa',m:['dark','warm'],sold:true,d:'English description…',es:'Descripción en español…'}
```

- `id` must match the image file `img/<id>.webp`.
- **Mark sold out:** add `sold:true`. **Back in stock:** remove it.
- **Add a perfume:** add an entry to `AR` or `DE` with `d`, `es` and `m` (moods: `warm`, `fresh`, `floral`, `dark`), add a WebP photo at `img/<id>.webp`, and its size to `IMG`.
- **Most wanted** is the `MOST` list of ids. **Hero featured perfumes** (Arab only, Supremacy Collector's Edition first) are in `FEAT` (id, colours `h1`/`h2`/`ha`, notes in EN/ES); each needs a background-free photo at `img/hero-<id>.webp`.

## Before finishing any change

1. No prices introduced; the WhatsApp number and Instagram link are unchanged.
2. Every new string has its Spanish version.
3. Colours, type sizes and weights come from the tokens above.
4. Check at 375 px wide: no horizontal scroll, targets ≥ 44 px.
