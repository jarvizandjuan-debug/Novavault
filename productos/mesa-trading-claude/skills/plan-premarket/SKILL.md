---
name: plan-premarket
description: Arma el plan de trading del día antes de la apertura combinando escáner, noticias, niveles y riesgo; deja 1 a 3 operaciones candidatas con gatillo, stop, target y tamaño, y guarda el plan en ~/mesa-trading/planes/. Úsala cuando el usuario diga "prepara mi día", "plan premarket", "game plan", "qué opero hoy" o "plan de trading de hoy".
---

# Plan premarket

Orquesta las demás skills. No necesita script propio: ejecuta los de las otras skills, que están en las carpetas
hermanas (`~/.claude/skills/<skill>/scripts/`), con el Python de la mesa `~/mesa-trading/py` (o `python3`).

## Pasos

1. **Contexto de mercado**: `detector-setups` sobre SPY y QQQ (tendencia y dónde está el precio respecto a niveles).
2. **Escaneo**: `escaner-graficas` con `--setup gap` y luego `--setup todos` sobre el universo de la config. Quédate con 5–8 nombres.
3. **Catalizadores**: `radar-noticias --escaneo`. Descarta los que no tengan catalizador claro o tengan dilución.
4. **Setups**: `detector-setups` en los 3 mejores. Elige gatillo y stop lógicos (rango de apertura, máximo previo, VWAP).
5. **Riesgo**: `stop-y-target` para cada candidato (`--entrada` = gatillo, `--stop` = stop técnico). Descarta los `NO OPERAR`.
6. **Opcional**: `time-machine` en el mejor candidato para ver la probabilidad de target antes que stop.
7. **Escribe el plan** con la plantilla `plantilla.md` de esta skill en `~/mesa-trading/planes/AAAA-MM-DD.md` y muéstralo.

## El plan debe incluir

- Sesgo del mercado (alcista / bajista / lateral) en una línea.
- 1–3 operaciones: ticker, catalizador, setup, gatillo, stop, target, acciones, riesgo en $, R:R y condición de invalidación.
- Reglas del día: pérdida máxima diaria (de la config), número máximo de operaciones (sugiere 3) y hora límite de entradas (sugiere 11:30 NY).
- Lista "no tocar": nombres que se mueven pero sin setup o con riesgo de dilución.

## Reglas

- Menos es más: si nada cumple, el plan es "hoy no se opera" y está bien.
- Educativo, paper trading, no es asesoría financiera.
