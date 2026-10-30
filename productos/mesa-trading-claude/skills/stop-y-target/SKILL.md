---
name: stop-y-target
description: Calcula el stop loss, el target y el tamaño de la posición ANTES de entrar, según el riesgo por operación de la config (por defecto 1% del capital), con stop manual, por ATR o por estructura; valida el R:R mínimo y avisa de stops dentro del ruido. Guarda el plan para gatillo, time-machine y paper. Úsala cuando el usuario diga "dónde pongo el stop", "cuántas acciones compro", "calcula mi riesgo", "pon stop y target", "R:R de esta operación", o antes de cualquier entrada.
---

# Stop y target antes de entrar

Regla de la mesa: **no hay entrada sin stop y target definidos antes**.

## Ejecutar

```bash
~/mesa-trading/py ~/.claude/skills/stop-y-target/scripts/riesgo.py NVDA --entrada 214.50 --stop 211.80 --r 2.5 --setup ORB --guardar
~/mesa-trading/py ~/.claude/skills/stop-y-target/scripts/riesgo.py NCLH --entrada 18.10 --stop-atr 1 --guardar
~/mesa-trading/py ~/.claude/skills/stop-y-target/scripts/riesgo.py TSLA --stop-estructura --target 455 --guardar     # entrada = precio actual
~/mesa-trading/py ~/.claude/skills/stop-y-target/scripts/riesgo.py AMD --lado corto --entrada 150 --stop 152.2 --r 2
```

- Stop: `--stop PRECIO` | `--stop-atr N` (N veces el ATR de 5 minutos) | `--stop-estructura` (último pivote de 5m + colchón).
- Target: `--target PRECIO` | `--r N` (múltiplo del riesgo; por defecto `rr_minimo` de la config).
- `--guardar` deja el plan en `~/mesa-trading/planes/ultimo_plan.json` (solo si es OPERABLE).

## Cómo presentar

Muestra el bloque del plan (entrada, stop, target, R:R, acciones, riesgo en $, ganancia si toca target) como una
"ficha" clara y el **veredicto**:
- `OPERABLE`: cumple las reglas.
- `NO OPERAR`: R:R por debajo del mínimo, stop dentro del ruido (< 0.25 ATR de 5m) o no alcanza para 1 acción.

Explica cada aviso en lenguaje simple. Si el target pasa por encima de una resistencia cercana (puedes verla con
detector-setups), sugiere un target más conservador.

Siguiente paso: **time-machine --plan** para simular el día, y **gatillo-entrada --plan** para esperar la entrada.

## Reglas

- Nunca sugieras mover el stop más lejos para "aguantar" una operación.
- Educativo, paper trading, no es asesoría financiera.
