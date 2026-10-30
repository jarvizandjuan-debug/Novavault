---
name: detector-setups
description: Analiza a fondo la gráfica de una acción (tendencia diaria, EMAs, ATR, soportes y resistencias, máximos/mínimos de ayer, VWAP, rango de apertura) y detecta setups intradía como ORB, VWAP reclaim, bandera alcista y mínimos crecientes, con gatillo, stop y target sugeridos. Úsala cuando el usuario pregunte "analiza NVDA", "¿hay setup en TSLA?", "niveles clave de AMD", "dónde entro", "lee la gráfica de...".
---

# Detector de setups

## Ejecutar

```bash
~/mesa-trading/py ~/.claude/skills/detector-setups/scripts/analizar.py NVDA
~/mesa-trading/py ~/.claude/skills/detector-setups/scripts/analizar.py TSLA --r 2.5 --json
```

(Python de la mesa: `~/mesa-trading/py`; si no existe, `python3`.)

## Qué devuelve

- Tendencia diaria (alineación de EMAs 9/20/50) y ATR diario.
- Niveles: máximo/mínimo/cierre de ayer, máx/mín de 20 días, máximo de 52 semanas, 3 resistencias y 3 soportes (pivotes agrupados en zonas).
- Sesión de hoy (velas de 5m): apertura, VWAP y lado del precio, rango de los primeros 15 minutos, máximo/mínimo del día.
- Setups: ORB 15m, VWAP reclaim, bandera alcista 5m, mínimos crecientes, cada uno con gatillo, stop y target (R configurable).

## Cómo presentar

1. Resume en 2–3 frases la "historia" de la gráfica (tendencia + dónde está el precio respecto a VWAP y niveles).
2. Lista los setups activos con gatillo / stop / target y la resistencia siguiente (si el target pasa por encima de una resistencia cercana, adviértelo).
3. Si no hay setup claro, dilo: "no hay setup" también es una respuesta válida.
4. Siguiente paso sugerido: **stop-y-target** para calcular el tamaño de la posición con el gatillo y el stop elegidos.

## Reglas

- Los niveles son referencias técnicas, no predicciones. Educativo, paper trading, no es asesoría financiera.
- Fuera de horario de mercado, la "sesión de hoy" es la última sesión disponible: indícalo.
