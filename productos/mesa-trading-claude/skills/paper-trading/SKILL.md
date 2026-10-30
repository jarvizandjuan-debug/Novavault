---
name: paper-trading
description: Ejecuta operaciones en paper trading (sin dinero real) siempre con stop y target (orden bracket). Modo local con cuenta simulada o modo Alpaca Paper. Abre, revisa, cierra posiciones, muestra la cuenta y el historial, y bloquea nuevas entradas al llegar a la pérdida diaria máxima. Úsala cuando el usuario diga "entra en paper", "compra 20 NVDA en paper", "mis posiciones", "cierra TSLA", "cómo va mi cuenta", "historial de operaciones".
---

# Paper trading

Todo es simulado. El modo `alpaca` usa exclusivamente `https://paper-api.alpaca.markets` (cuenta de práctica).

## Ejecutar

```bash
~/mesa-trading/py ~/.claude/skills/paper-trading/scripts/paper.py cuenta
~/mesa-trading/py ~/.claude/skills/paper-trading/scripts/paper.py abrir --plan
~/mesa-trading/py ~/.claude/skills/paper-trading/scripts/paper.py abrir NVDA --acciones 20 --stop 211.5 --target 219 --setup ORB
~/mesa-trading/py ~/.claude/skills/paper-trading/scripts/paper.py abrir AMD --lado corto --acciones 10 --stop 152.2 --target 146
~/mesa-trading/py ~/.claude/skills/paper-trading/scripts/paper.py posiciones      # revisa stops/targets y P&L
~/mesa-trading/py ~/.claude/skills/paper-trading/scripts/paper.py cerrar NVDA
~/mesa-trading/py ~/.claude/skills/paper-trading/scripts/paper.py historial
~/mesa-trading/py ~/.claude/skills/paper-trading/scripts/paper.py reiniciar --confirmar
```

## Cómo funciona el modo local

- Entra al último precio disponible (+ deslizamiento de la config). Fuera de horario avisa de que es precio pre/post-market.
- `posiciones`, `cuenta` y `cerrar` revisan vela a vela desde la entrada si se tocó el stop o el target
  (si ambos en la misma vela: stop) y cierran solas esas posiciones.
- Cada operación cerrada se anota sola en el diario (`~/mesa-trading/diario/operaciones.csv`).
- Rechaza la entrada si el precio ya no está entre stop y target, si no hay efectivo, o si se alcanzó la pérdida diaria máxima.

## Reglas

- Sin stop y target no se abre nada. Prefiere siempre `abrir --plan` (sale de stop-y-target).
- Confirma con el usuario antes de abrir o cerrar una posición, mostrando ticker, acciones, stop, target y riesgo.
- Educativo, paper trading, no es asesoría financiera.
