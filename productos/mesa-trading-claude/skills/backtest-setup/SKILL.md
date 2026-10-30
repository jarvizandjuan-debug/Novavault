---
name: backtest-setup
description: Prueba setups intradía (ORB rango de apertura, primera vela tras gap, VWAP reclaim) con velas reales de 5 minutos de hasta 60 días y mide win rate, esperanza en R, profit factor y drawdown por ticker. Úsala cuando el usuario pregunte "¿funciona el ORB en NVDA?", "backtest de este setup", "¿qué setup funciona mejor?", "pruébalo con datos históricos".
---

# Backtest de setups

## Ejecutar

```bash
~/mesa-trading/py ~/.claude/skills/backtest-setup/scripts/backtest.py --setup orb --tickers NVDA,TSLA,AMD
~/mesa-trading/py ~/.claude/skills/backtest-setup/scripts/backtest.py --setup orb --or-min 30 --stop mitad --r 1.5 --tickers watchlist
~/mesa-trading/py ~/.claude/skills/backtest-setup/scripts/backtest.py --setup primera-vela --gap 3 --tickers watchlist
~/mesa-trading/py ~/.claude/skills/backtest-setup/scripts/backtest.py --setup vwap-reclaim --tickers SPY,QQQ --r 1.5 --json
```

Parámetros: `--r` (target en R), `--dias` (máx. 60), `--or-min` (minutos del rango de apertura), `--stop rango|mitad` (ORB),
`--gap` (% mínimo para primera-vela), `--ultima-entrada HH:MM` (11:30), `--hasta HH:MM` (salida forzada, 15:55).

El detalle de cada operación se guarda en `~/mesa-trading/backtests/`.

## Cómo presentar

1. Resultado global: operaciones, win rate, esperanza (R por operación), total R, profit factor, drawdown máximo en R.
2. Tabla por ticker, destacando dónde el setup tiene esperanza positiva y dónde no.
3. Si se pide, compara variantes (por ejemplo `--r 1.5` vs `--r 2`, `--stop mitad`) y resume cuál fue mejor.
4. Conclusión honesta: con menos de 30 operaciones la muestra no es fiable; 60 días son un solo régimen de mercado.

## Reglas

- Resultados pasados no garantizan resultados futuros. Sin comisiones ni deslizamiento.
- Educativo, paper trading, no es asesoría financiera.
