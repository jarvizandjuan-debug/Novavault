---
name: time-machine
description: TIME MACHINE. Simula el resto del día de trading miles de veces (10,000 por defecto) con un bootstrap de velas reales de 5 minutos del propio ticker para estimar la probabilidad de tocar el target antes que el stop, la esperanza en R y el tiempo típico hasta cada salida, antes de arriesgar un dólar. Úsala cuando el usuario diga "simula el día", "time machine", "qué probabilidad tiene esta operación", "simula 10,000 veces", "¿vale la pena este trade?".
---

# Time Machine

## Ejecutar

```bash
~/mesa-trading/py ~/.claude/skills/time-machine/scripts/time_machine.py --plan                    # usa el último plan de stop-y-target
~/mesa-trading/py ~/.claude/skills/time-machine/scripts/time_machine.py NVDA --entrada 214 --stop 211.5 --target 219
~/mesa-trading/py ~/.claude/skills/time-machine/scripts/time_machine.py TSLA --entrada 450 --stop 444 --target 462 --barras 40 --sims 20000 --json
```

Opciones: `--sims` (10000), `--barras` velas de 5m a simular (por defecto, las que quedan hasta el cierre; sesión completa
si el mercado está cerrado), `--bloque` (6 velas = 30 min por bloque), `--sin-escala`, `--con-tendencia`, `--semilla`.

## Cómo funciona (explícalo si lo preguntan)

1. Descarga 60 días de velas de 5 minutos del ticker.
2. Construye miles de "días alternativos" encadenando bloques de 30 minutos reales elegidos al azar
   (mantiene la volatilidad, las colas gordas y algo de inercia de esa acción).
3. Reescala a la volatilidad de los últimos 5 días y quita la deriva (sin sesgo alcista ni bajista, salvo `--con-tendencia`).
4. En cada vela revisa máximo y mínimo: si toca stop y target en la misma vela cuenta como stop (conservador).

## Cómo presentar

- Probabilidades: ★ target primero / ♥ stop primero / sin tocar ninguno al cierre.
- Esperanza en R (y en $ si hay número de acciones) frente al win rate necesario para no perder.
- Tiempo mediano hasta target y hasta stop.
- Lectura honesta: la simulación mide si stop y target son razonables para cómo se mueve la acción. No conoce el
  setup ni las noticias: la ventaja tiene que venir del setup (compruébalo con **backtest-setup**).

## Reglas

- Nunca presentes las probabilidades como garantía. Educativo, paper trading, no es asesoría financiera.
