# Claude Code destruyó el day trading — video 9:16

Video vertical de 35 s en pixel art de 16 bits (1080×1920, 30 fps, H.264 + AAC).

- `claude-code-day-trading.mp4`: el video final.
- `cover.png`: portada (fotograma del hook).

## Escenas

| Tiempo | Escena | Texto en pantalla |
|---|---|---|
| 0–3 s | Terminal retro, el texto se escribe solo | CLAUDE CODE DESTRUYÓ EL DAY TRADING / 11 SKILLS GRATIS |
| 3–10 s | Trader frente a monitores CRT y luego escaneo de miles de gráficas | ESCANEA MILES DE GRÁFICAS |
| 10–17 s | Cursor de selección sobre el setup, ventana emergente con la noticia | DETECTA EL SETUP + LA NOTICIA |
| 17–24 s | Barras de vida: stop (rojo) y target (verde), cuenta atrás 3-2-1 y entrada | STOP Y TARGET ANTES DE ENTRAR |
| 24–31 s | TIME MACHINE: vórtice, 10,000 simulaciones, 64% / 36% | SIMULA EL DÍA 10,000 VECES |
| 31–35 s | Sello PAPER TRADING — SIN DINERO REAL y CTA | COMENTA TRADE Y TE LO MANDO |

El ticker (PXL16), la noticia y los porcentajes son ficticios e ilustrativos.

## Cómo regenerarlo

Requiere Python 3 con `numpy` y `Pillow`, y `ffmpeg`.

```bash
python3 audio.py          # música chiptune + efectos + voz -> mix.wav (-14 LUFS)
python3 render.py video   # fotogramas -> out.mp4
python3 render.py stills 2.5 12.6   # fotogramas sueltos en stills/ para revisar
```

- `timeline.py`: tiempos compartidos por audio y video. La música va a 137 BPM, así que cada escena de 7 s dura exactamente 4 compases.
- `vo/`: locución en español (voz neural es-MX). Algunas palabras en inglés van escritas de forma fonética en el guion de la locución ("déi tréiding", "eskils", "tárguet", "treid") para que se pronuncien en inglés.
- Fuente: Press Start 2P (SIL Open Font License, ver `OFL.txt`).
