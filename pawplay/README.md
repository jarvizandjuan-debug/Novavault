# PawPlay · portada del Gorrión Cazador

Copia de la portada de la tienda Shopify PawPlay (tema "Horizon - Gorrion Cazador").

- En la tienda, este diseño vive dentro de `layout/theme.liquid` y solo se muestra en la página de inicio
  (`template.name == 'index'`). En el resto de páginas se ve el tema normal.
- `portada-pawplay.liquid` es la versión legible del mismo código.
- Las reseñas salen de los metaobjetos `pawplay_review` (Shopify > Contenido > Metaobjetos > Reseña de cliente).
  La nota media y el número de reseñas se calculan solos; si no hay ninguna, no se muestra ninguna cifra.
