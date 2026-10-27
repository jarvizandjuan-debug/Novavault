# Carrusel · Mis 6 agentes de IA

9 láminas de 1080x1350 para Instagram, en `png/` (01.png es la portada).

Concepto: cada agente es un empleado con su credencial colgada del cuello. Clawd, el
muñequito de Claude Code, aparece en pixel art vestido según el oficio de cada agente.

| # | Lámina | Clawd lleva |
|---|--------|-------------|
| 1 | Portada · 6 empleados. Ninguno es humano. | Foto del equipo completo |
| 2 | 01 El Rastreador | Binoculares y flecha de tendencia |
| 3 | 02 El Anzuelo | Sombrero de pescador y caña |
| 4 | 03 La Pluma | Pluma y tintero |
| 5 | 04 El Artista | Boina, pincel y paleta |
| 6 | 05 El Cartero | Gorra y sobre |
| 7 | 06 El Detective | Gorro de detective y lupa |
| 8 | El ciclo (la lámina para captura) | Los 6 en fila |
| 9 | Comenta AGENTES | Clawd con la mano arriba |

## Caption

```
Mi equipo de contenido tiene 6 empleados. Ninguno es humano.

Son 6 agentes de IA que monté con Claude Code y cada uno tiene un solo trabajo:

01 El Rastreador busca los formatos que ya están pegando
02 El Anzuelo escribe los primeros 3 segundos
03 La Pluma escribe guiones y captions con mi voz
04 El Artista diseña carruseles y portadas
05 El Cartero publica a diario en Instagram y TikTok
06 El Detective lee las métricas y decide qué repetir

Así saco contenido para Instagram todos los días sin depender de la inspiración. Yo solo apruebo. Si algo no suena a mí, no sale.

Comenta AGENTES y te mando la guía con la instrucción exacta de cada uno, lista para copiar y pegar.

#claudecode #agentesdeia #inteligenciaartificial #creadordecontenido
```

## Texto alternativo (portada)

Seis muñequitos pixelados de Claude Code, cada uno con un accesorio de su oficio
(binoculares, sombrero de pescador, pluma, boina, gorra de cartero y gorro de detective),
bajo el título "6 empleados. Ninguno es humano."

## Editar y volver a generar

Todo el texto está en el arreglo `AG` de `carrusel.html`. Después de editar:

```bash
node render.js   # necesita Playwright; vuelve a escribir png/01.png ... png/09.png
```
