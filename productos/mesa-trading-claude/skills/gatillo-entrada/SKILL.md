---
name: gatillo-entrada
description: Espera el momento exacto de entrada. Vigila el precio en vivo (velas de 1 minuto) y avisa cuando se cumple la condición del setup (cruce o cierre de vela de 5m por encima/debajo de un nivel, con confirmación de volumen opcional); cancela si antes toca el stop; no persigue precios ya rotos. Con --ejecutar abre la operación en paper con su stop y target. Incluye modo replay para practicar con días pasados. Úsala cuando el usuario diga "avísame cuando rompa", "espera la entrada", "vigila NVDA", "entra cuando cruce 215", "practica con el día de ayer".
---

# Gatillo de entrada

## Ejecutar

```bash
~/mesa-trading/py ~/.claude/skills/gatillo-entrada/scripts/gatillo.py --plan                      # vigila la entrada del último plan
~/mesa-trading/py ~/.claude/skills/gatillo-entrada/scripts/gatillo.py --plan --ejecutar           # y entra en paper al activarse
~/mesa-trading/py ~/.claude/skills/gatillo-entrada/scripts/gatillo.py NVDA --nivel 215.20 --condicion cierre-arriba --volumen 1.5
~/mesa-trading/py ~/.claude/skills/gatillo-entrada/scripts/gatillo.py --plan --replay 2026-10-28 --desde 09:45   # práctica
```

- `--condicion`: `cruce-arriba` (por defecto en largos), `cruce-abajo`, `cierre-arriba`, `cierre-abajo` (cierre de vela de 5m).
- `--volumen N`: exige que el volumen de la vela sea ≥ N veces la media reciente.
- `--invalidacion PRECIO`: cancela si lo toca antes (con `--plan`, es el stop).
- `--cada S` segundos entre revisiones (20 por defecto) y `--max-min` minutos máximos de espera (60).

## Importante al ejecutarlo

- En vivo es un proceso largo: **ejecútalo en segundo plano** (o con `--max-min` corto) y revisa su salida.
- Solo funciona con el mercado abierto (9:30–16:00 NY). Fuera de horario, sale con código 3 y sugiere `--replay`.
- El gatillo se "arma" solo cuando el precio está entre el stop y el nivel: si ya rompió, avisa y no persigue.
- Códigos de salida: 0 activado, 2 invalidado o tiempo agotado, 3 mercado cerrado.

## Replay (práctica)

`--replay AAAA-MM-DD` repite un día de los últimos ~7 vela a vela y, con `--plan`, cuenta el desenlace
(stop, target o cierre, en R). Úsalo para entrenar la paciencia y validar planes sin esperar al mercado.

## Reglas

- `--ejecutar` exige `--plan`: nunca se entra sin stop y target.
- Los datos de Yahoo pueden tener unos segundos de retraso. Educativo, paper trading, no es asesoría financiera.
