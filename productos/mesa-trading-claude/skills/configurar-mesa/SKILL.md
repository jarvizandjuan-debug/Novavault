---
name: configurar-mesa
description: Configura la Mesa de Trading de Claude Code (capital de paper trading, riesgo por operación, R:R mínimo, pérdida diaria máxima, watchlist, universo del escáner y modo paper local o Alpaca) y verifica que todo funciona. Úsala la primera vez, o cuando el usuario diga "configura mi mesa de trading", "cambia mi riesgo", "mi watchlist", "conecta Alpaca", "verifica la instalación".
---

# Configurar la Mesa de Trading

Esta skill prepara la carpeta `~/mesa-trading/` y el archivo `config.json` que usan las otras 10 skills.

## Cómo ejecutar los scripts

Usa el Python de la mesa: `~/mesa-trading/py` (lo crea el instalador; si no existe, usa `python3`).
El script está en la carpeta `scripts/` de esta skill (normalmente `~/.claude/skills/configurar-mesa/scripts/`).

```bash
~/mesa-trading/py ~/.claude/skills/configurar-mesa/scripts/configurar.py ver
~/mesa-trading/py ~/.claude/skills/configurar-mesa/scripts/configurar.py inicializar --capital 25000 --riesgo-pct 1 --rr-min 2 --watchlist "SPY,QQQ,NVDA,TSLA,AMD"
~/mesa-trading/py ~/.claude/skills/configurar-mesa/scripts/configurar.py set max_perdida_diaria_pct 3
~/mesa-trading/py ~/.claude/skills/configurar-mesa/scripts/configurar.py verificar
```

## Flujo recomendado (primera vez)

1. Ejecuta `verificar`. Si falta algo, explica cómo arreglarlo (normalmente volver a correr el instalador).
2. Pregunta al usuario, en un solo mensaje y con valores por defecto sugeridos:
   - Capital simulado (por defecto 25,000).
   - Riesgo por operación en % (por defecto 1%; recomienda 0.5–1%).
   - R:R mínimo (por defecto 2).
   - Pérdida diaria máxima en % (por defecto 3%): al alcanzarla, paper-trading bloquea nuevas entradas ese día.
   - Watchlist (tickers que sigue a diario).
   - Modo paper: `local` (no requiere cuenta) o `alpaca` (cuenta PAPER gratuita de Alpaca).
3. Ejecuta `inicializar` con sus respuestas y muestra el resultado.

## Claves (config.json)

| Clave | Qué es |
|---|---|
| capital_paper | Capital de la cuenta simulada |
| riesgo_por_trade_pct | % del capital que se arriesga por operación (define el tamaño) |
| rr_minimo | Relación beneficio/riesgo mínima para aceptar un plan |
| max_posicion_pct | Tamaño máximo de una posición, en % del capital |
| max_perdida_diaria_pct | Pérdida diaria que bloquea nuevas entradas |
| modo_paper | `local` o `alpaca` |
| universo | `sp500`, `todo-usa`, `watchlist`, lista o ruta a .txt |
| watchlist | Lista de tickers |
| precio_min / volumen_medio_min | Filtros del escáner |
| deslizamiento_pct | Deslizamiento simulado en las entradas paper (local) |

## Alpaca (opcional)

1. Crea una cuenta en alpaca.markets y entra en **Paper Trading** (no la cuenta real).
2. Genera claves de API de paper.
3. El usuario debe exportarlas en su terminal (no las pegues en el chat si puedes evitarlo):
   `export APCA_API_KEY_ID=...` y `export APCA_API_SECRET_KEY=...`
4. `configurar.py set modo_paper alpaca` y luego `verificar`.

Los scripts solo hablan con `https://paper-api.alpaca.markets`. Nunca con la API de dinero real.

## Reglas

- Recuerda siempre que es una herramienta educativa en paper trading, no asesoría financiera.
- No subas el riesgo por operación por encima del 2% sin advertir claramente del peligro.
