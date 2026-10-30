---
name: diario-trading
description: Diario de trading con estadísticas reales — win rate, R medio de ganadoras y perdedoras, esperanza, profit factor, drawdown y peor racha, por setup, hora y día — y revisión semanal en Markdown. Las operaciones de paper-trading se anotan solas. Úsala cuando el usuario diga "mis estadísticas", "cómo voy", "anota esta operación", "revisión semanal", "qué setup me funciona", "diario de trading".
---

# Diario de trading

## Ejecutar

```bash
~/mesa-trading/py ~/.claude/skills/diario-trading/scripts/diario.py stats
~/mesa-trading/py ~/.claude/skills/diario-trading/scripts/diario.py stats --desde 2026-10-01 --setup ORB
~/mesa-trading/py ~/.claude/skills/diario-trading/scripts/diario.py agregar NVDA --entrada 214 --salida 219 --stop 211.5 --acciones 20 --setup ORB --motivo target --notas "esperé el cierre de 5m"
~/mesa-trading/py ~/.claude/skills/diario-trading/scripts/diario.py revision          # informe de los últimos 7 días
```

Archivo: `~/mesa-trading/diario/operaciones.csv` (se puede abrir en Excel o Google Sheets).

## Cómo presentar

1. Las 4 cifras clave: operaciones, win rate, esperanza en R y profit factor.
2. Qué setup y qué hora funcionan mejor y peor (con cuidado si hay pocas operaciones).
3. Disciplina: cuántas salidas fueron manuales en lugar de stop/target.
4. Una sola acción concreta para la próxima semana (por ejemplo: "solo ORB antes de las 11:00").

## Reglas

- Sé honesto con los números aunque sean malos: el diario sirve para mejorar, no para sentirse bien.
- Educativo, paper trading, no es asesoría financiera.
