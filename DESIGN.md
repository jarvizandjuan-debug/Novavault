# NOVAVAULT design system

**Idea:** dark = brand, navigation and proof; white = product. The landing is black with white category tiles; the three collection views (Most Wanted / Arab / Designer) and every product page are white galleries.

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

Rules that never change: English by default (EN/ES toggle), no prices, sold-out items stay visible with a badge and disabled order buttons, WhatsApp +1 510 978 8240 with a pre-filled message per perfume, Instagram DM via ig.me/m/novavaultcolognes.

Mark a perfume sold out: add `sold:true` to its entry in `AR` or `DE` in `index.html`.

Breakpoints: 375 (narrow), 768 (medium), 1280 (wide). On narrow the nav collapses to a Menu control; both page overlays make the site underneath `inert`, keep Tab inside, close with Esc and return focus to the tile or card that opened them.

Motion: UI transitions use 200 / 300 ms ease-out. Ambient brand motion (hero intro, one-time logo glint, floating bottles, gold dust, ribbon) is intentional and switches off under `prefers-reduced-motion`.
