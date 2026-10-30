---
name: radar-noticias
description: Sigue las noticias que mueven una acción. Trae titulares recientes por ticker (Yahoo Finance y Google News), los clasifica por tipo de catalizador (resultados, guía, FDA, fusiones, contratos, dilución, legal, analistas...), sesgo positivo/negativo e impacto. Úsala cuando el usuario pregunte "¿por qué se mueve X?", "noticias de NVDA", "catalizadores de hoy", "¿hay noticia detrás de este gap?" o después de un escaneo.
---

# Radar de noticias

## Ejecutar

```bash
~/mesa-trading/py ~/.claude/skills/radar-noticias/scripts/noticias.py NVDA
~/mesa-trading/py ~/.claude/skills/radar-noticias/scripts/noticias.py NCLH,CVNA --horas 24 --max 6
~/mesa-trading/py ~/.claude/skills/radar-noticias/scripts/noticias.py --escaneo        # top del último escaneo
~/mesa-trading/py ~/.claude/skills/radar-noticias/scripts/noticias.py --watchlist --json
```

## Cómo presentar

1. Por cada ticker: el catalizador principal en una frase (qué pasó y si es de impacto ALTO).
2. Distingue catalizadores "de verdad" (resultados con guía elevada, FDA, contrato grande, adquisición) de ruido (artículos de opinión, "stock forecast", listas).
3. Señala riesgos: **DILUCIÓN** (ofertas de acciones) o **LEGAL** suelen frenar subidas.
4. Si tienes herramienta de búsqueda web, úsala para confirmar la noticia más importante antes de concluir.
5. Siguiente paso: **detector-setups** en el ticker con el mejor catalizador.

## Reglas

- La clasificación es automática por palabras clave: confirma leyendo el titular completo.
- No inventes noticias ni cifras que no aparezcan en los resultados.
- Educativo, paper trading, no es asesoría financiera.
