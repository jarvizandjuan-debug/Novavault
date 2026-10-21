# NOVAVAULT design system (v2: editorial gallery)

**Idea:** black, gold and white from the logo. The hero belongs to the featured perfume (its colour fills the whole hero); the rest of the site is a calm bone-coloured gallery with white product cards, and ink sections carry the proof (why us, wholesale).

| Token | Value |
|---|---|
| Bone (page) | `#f4f0e8` |
| Paper (product) | `#ffffff` |
| Ink / muted | `#0b0b0b` / `#635b51` |
| Hairline | `#e2dace` |
| Gold (logo) / dark gold text on bone | `#d4af37` / `#7a5f10` |
| Cream (text on dark) | `#f6efe4` |
| Logo | `img/logo.webp` (round badge, black + gold), favicon `img/favicon.png` |
| Display / body | Instrument Serif (400 + italic) / Manrope 400-500-600 |
| Type scale | 12 / 14 / 16 / 20 / 28 px, fluid 36-56 px, fluid 48-92 px |
| Space | 8pt grid, section padding 72 px (narrow) / 120 px (768+), gutter 24 / 40 px |
| Shape | Pills for buttons and chips, 12 px cards, 1 px hairlines, shadows only on hover and below 8% alpha, no glass, no glow |
| Buttons | 48 px high. Solid = ink (cream inside the hero). Line = 1 px outline |

Hero featured perfumes (colours `h1` base, `h2` light, `ha` accent) live in `FEAT` in `index.html`: Tobacco Vanille, Eclaire, Lost Cherry, Sauvage. Each needs a background-free photo at `img/hero-<id>.webp`.

Rules that never change: English by default (EN/ES toggle), no prices, sold-out items stay visible with a badge and disabled order buttons (they are listed after available ones), WhatsApp +1 510 978 8240 with a pre-filled message per perfume, Instagram DM via ig.me/m/novavaultcolognes.

Mark a perfume sold out: add `sold:true` to its entry in `AR` or `DE` in `index.html`. Each entry also has `m`, its moods for the scent finder: `warm`, `fresh`, `floral`, `dark`.

Breakpoints: 375 (narrow), 768 (medium), 960 (nav shows links), 1280 (wide). The product page is a white overlay: the site underneath is `inert`, Tab stays inside, Esc closes it and focus returns to the card that opened it.

Motion: UI transitions 200 / 300 ms ease-out; sections fade up once on scroll. Hero motion (bottle entrance, cursor tilt, floating flakes pushed away by the pointer, spin-and-swap when a featured perfume is picked, colour morph) uses Motion from the jsDelivr CDN and switches off under `prefers-reduced-motion`.
