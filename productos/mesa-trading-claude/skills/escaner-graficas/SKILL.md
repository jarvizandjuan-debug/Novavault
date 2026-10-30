---
name: escaner-graficas
description: Escanea cientos o miles de gráficas de acciones de EE. UU. (S&P 500, todo el mercado o la watchlist) y ordena las mejores candidatas por gap, volumen relativo, momentum, rupturas de máximos, banderas alcistas y rebotes en EMA. Úsala cuando el usuario pida "escanea el mercado", "busca setups", "qué acciones se mueven hoy", "gappers", "acciones con volumen", "rupturas" o "candidatas para operar".
---

# Escáner de gráficas

## Ejecutar

Python de la mesa: `~/mesa-trading/py` (si no existe, `python3`). Script: `scripts/escanear.py` de esta skill.

```bash
~/mesa-trading/py ~/.claude/skills/escaner-graficas/scripts/escanear.py                       # universo de la config (S&P 500)
~/mesa-trading/py ~/.claude/skills/escaner-graficas/scripts/escanear.py --setup gap --top 15
~/mesa-trading/py ~/.claude/skills/escaner-graficas/scripts/escanear.py --universo todo-usa --top 30   # miles de gráficas, tarda varios minutos
~/mesa-trading/py ~/.claude/skills/escaner-graficas/scripts/escanear.py --universo watchlist --json
```

Opciones: `--universo sp500|todo-usa|watchlist|"AAPL,MSFT"|ruta.txt`, `--setup todos|gap|momentum|ruptura|bandera|rebote-ema|volumen`, `--top N`, `--precio-min`, `--vol-min`, `--csv archivo.csv`, `--json`.

`todo-usa` descarga unas 5,000–6,000 gráficas: ejecútalo en segundo plano o avisa de que tardará.

## Qué mide cada señal

- **GAP↑ / GAP↓**: apertura vs. cierre anterior (≥ 2%).
- **RVOL**: volumen de hoy / media de 20 días (≥ 1.5x). Parcial si el mercado sigue abierto.
- **RUPTURA20**: cierre por encima del máximo de los 20 días anteriores.
- **BANDERA**: mástil ≥ 3 ATR en ≤ 6 velas y consolidación estrecha que retrocede ≤ 50%.
- **REBOTE-EMA20**: tendencia alcista y el mínimo de hoy tocó la EMA20.
- **TENDENCIA**: precio > EMA9 > EMA20 > EMA50. **MAX52**: a menos del 3% del máximo de 52 semanas. **INSIDE**: vela interior.

## Cómo presentar los resultados

1. Di cuántas gráficas se escanearon y en cuánto tiempo.
2. Muestra el top en una tabla y destaca 3–5 nombres con una frase sobre por qué destacan.
3. Separa ideas alcistas (gap↑, ruptura, bandera) de bajistas (gap↓ con volumen).
4. El escaneo guarda el top en `~/mesa-trading/cache/ultimo_escaneo.txt`: propone seguir con
   **radar-noticias** (`--escaneo`) para ver qué catalizador hay detrás y con **detector-setups** para el mejor candidato.

## Reglas

- Un escáner encuentra candidatas, no operaciones: nunca digas "compra X".
- Datos de Yahoo Finance (pueden llevar retraso). Educativo, paper trading, no es asesoría financiera.
