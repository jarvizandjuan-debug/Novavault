# Mesa de Trading para Claude Code · 11 skills

Convierte a Claude Code en tu mesa de day trading: escanea miles de gráficas, sigue las noticias, calcula
stop, target y tamaño antes de entrar, espera el momento exacto de entrada, simula el día 10,000 veces y
lleva tu diario. **Todo en paper trading, sin dinero real.**

Versión 1.0

---

## Las 11 skills

| # | Skill | Qué hace | Pídele a Claude... |
|---|---|---|---|
| 1 | `configurar-mesa` | Capital simulado, riesgo por operación, R:R mínimo, pérdida diaria máxima, watchlist | "configura mi mesa de trading" |
| 2 | `escaner-graficas` | Escanea el S&P 500 o todo el mercado de EE. UU. (miles de gráficas): gaps, volumen relativo, rupturas, banderas | "escanea el mercado y dame los 10 mejores setups" |
| 3 | `detector-setups` | Lee la gráfica de un ticker: tendencia, niveles, VWAP, ORB, bandera, con gatillo/stop/target | "analiza NVDA, ¿hay setup?" |
| 4 | `radar-noticias` | Titulares recientes clasificados por catalizador, sesgo e impacto | "¿por qué se mueve CVNA hoy?" |
| 5 | `plan-premarket` | Plan del día con 1–3 operaciones candidatas, guardado en un archivo | "prepara mi plan de hoy" |
| 6 | `stop-y-target` | Stop, target y número de acciones según tu riesgo, con veredicto OPERABLE / NO OPERAR | "pon stop y target para TSLA en 452" |
| 7 | `gatillo-entrada` | Vigila el precio y avisa (o entra en paper) en el momento exacto; modo replay para practicar | "avísame cuando NVDA rompa 215 con volumen" |
| 8 | `time-machine` | Simula el resto del día 10,000 veces con velas reales: probabilidad de target vs. stop | "simula esta operación 10,000 veces" |
| 9 | `backtest-setup` | Prueba ORB, primera vela tras gap y VWAP reclaim con 60 días de velas de 5 min | "¿funciona el ORB en AMD?" |
| 10 | `paper-trading` | Opera sin dinero real (cuenta local o Alpaca Paper), siempre con stop y target | "entra en paper con el plan" |
| 11 | `diario-trading` | Win rate, esperanza en R, profit factor, drawdown, por setup y hora; revisión semanal | "¿cómo voy esta semana?" |

## Requisitos

- [Claude Code](https://claude.com/claude-code) instalado.
- Python 3.9 o superior ([descarga](https://www.python.org/downloads/)).
- Conexión a internet (datos de mercado de Yahoo Finance y titulares de Google News).
- Opcional: cuenta gratuita de **Alpaca Paper Trading** si quieres ejecutar en un bróker simulado.

## Instalación

Descomprime el ZIP y, dentro de la carpeta:

**macOS / Linux**
```bash
bash instalar.sh
```

**Windows** (PowerShell)
```powershell
powershell -ExecutionPolicy Bypass -File instalar.ps1
```

El instalador:
1. Copia las 11 skills a `~/.claude/skills/` (tus skills personales de Claude Code).
2. Crea `~/mesa-trading/` con un entorno de Python propio (`.venv`) y las librerías necesarias.
3. Crea la configuración por defecto y comprueba que llegan datos de mercado.

Después abre Claude Code (o reinícialo) y escribe: **configura mi mesa de trading**.

> ¿Prefieres instalarlas solo en un proyecto? Copia la carpeta `skills/` a `.claude/skills/` de ese proyecto.
> Igualmente necesitas ejecutar el instalador una vez para crear `~/mesa-trading/`.

## Un día típico

1. **Antes de la apertura**: "prepara mi plan de hoy" → escaneo + noticias + niveles + riesgo → `~/mesa-trading/planes/AAAA-MM-DD.md`.
2. **Antes de entrar**: "pon stop y target para NCLH, entrada 18.10, stop bajo el rango de apertura" → ficha con acciones y riesgo.
3. **Simulación**: "time machine con el plan" → probabilidad de target antes que stop y esperanza en R.
4. **Entrada**: "vigila la entrada del plan y entra en paper cuando se active".
5. **Durante el día**: "mis posiciones" → revisa stops y targets.
6. **Al cierre**: "revisión de mi diario" → estadísticas y una mejora concreta para mañana.

Fuera de horario puedes practicar con días pasados: "haz un replay del plan con el día de ayer".

## Dónde se guarda todo

```
~/mesa-trading/
├── config.json          tu configuración
├── py                   lanzador del Python de la mesa
├── planes/              planes diarios y ultimo_plan.json
├── paper/cuenta.json    cuenta paper local
├── diario/              operaciones.csv y revisiones semanales
├── backtests/           resultados de backtests
└── cache/               listas de tickers y último escaneo
```

## Datos y limitaciones

- Datos de **Yahoo Finance** (vía la librería `yfinance`) y titulares de **Google News**, para uso personal.
  Pueden llevar unos segundos o minutos de retraso y a veces fallar: no son datos de nivel profesional.
- Velas de 1 minuto: últimos ~7 días. Velas de 5 minutos: últimos 60 días.
- Mercado de acciones de EE. UU. (horario 9:30–16:00 de Nueva York; no contempla festivos).
- El escaneo de todo el mercado (`todo-usa`) descarga miles de gráficas y tarda varios minutos.
- Backtests y simulaciones no incluyen comisiones; el modo paper local aplica un deslizamiento configurable.

## Seguridad

- Ninguna skill opera con dinero real. El modo Alpaca usa **solo** `paper-api.alpaca.markets`.
- Tus claves de Alpaca se leen de variables de entorno (`APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`); no se envían a ningún otro sitio.
- Todo corre en tu ordenador. No hay servidores intermedios.

## Desinstalar

Borra las carpetas de las 11 skills en `~/.claude/skills/` y, si quieres eliminar tus datos, `~/mesa-trading/`.

## Aviso importante

Este producto es **educativo**. No es asesoría financiera, de inversión ni recomendación de compra o venta de
ningún valor. Las simulaciones, backtests y probabilidades se basan en datos pasados y no garantizan resultados
futuros. El day trading con dinero real implica un alto riesgo de pérdida. Practica en paper trading y, si algún
día operas con dinero real, hazlo bajo tu propia responsabilidad.
