"""Gatillo de entrada: vigila el precio y avisa (o entra en paper) en el momento exacto en que
se cumple la condición del setup. Nunca entra sin stop y target.

Ejemplos:
  gatillo.py --plan                               # vigila la entrada del último plan
  gatillo.py --plan --ejecutar                    # y abre la operación en paper al activarse
  gatillo.py NVDA --nivel 215.20 --condicion cierre-arriba --volumen 1.5
  gatillo.py --plan --replay 2026-10-29           # práctica: repite un día pasado vela a vela
"""
import argparse
import datetime as dt
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "configurar-mesa" / "scripts"))
from mesa_comun import (AVISO, SKILLS_DIR, ahora_ny, cargar_plan, descargar_intradia, mercado_abierto,  # noqa: E402
                        requiere, salir)


def evaluar(barras, cond, nivel, vol_min, invalid):
    """Recorre las velas de 1m desde que empezó la vigilancia.

    Devuelve (estado, índice, rvol) con estado en: activado, invalidado, esperando, ya_cruzado, fuera_de_zona.
    El gatillo solo se arma cuando el precio está entre el stop y el nivel: no persigue precios ya rotos.
    """
    arriba = cond.endswith("arriba")
    c, h, l, v = (barras[k].values for k in ("Close", "High", "Low", "Volume"))
    # zona de armado: entre la invalidación (stop) y el gatillo
    zona = c < nivel if arriba else c > nivel
    if invalid is not None:
        zona &= (c > invalid) if arriba else (c < invalid)
    if not zona.any():
        mas_alla = (c >= nivel) if arriba else (c <= nivel)
        return ("ya_cruzado" if mas_alla.all() else "fuera_de_zona"), None, None
    i0 = int(zona.argmax())
    rvol = None
    for i in range(i0 + 1, len(barras)):
        if invalid is not None and ((arriba and l[i] <= invalid) or (not arriba and h[i] >= invalid)):
            return "invalidado", i, None
        if cond.startswith("cruce"):
            ok = h[i] >= nivel if arriba else l[i] <= nivel
            vol_act = v[i]
            base = v[max(0, i - 20):i]
        else:  # cierre de vela de 5 minutos
            if (barras.index[i].minute + 1) % 5:
                continue
            ok = c[i] > nivel if arriba else c[i] < nivel
            vol_act = v[max(0, i - 4):i + 1].mean()
            base = v[max(0, i - 24):max(0, i - 4)]
        rvol = float(vol_act / base.mean()) if len(base) >= 5 and base.mean() > 0 else None
        if ok and (not vol_min or (rvol is not None and rvol >= vol_min)):
            return "activado", i, rvol
    return "esperando", None, rvol


def linea(t, tk, precio, nivel, rvol):
    falta = nivel - precio
    v = f" · vol {rvol:.1f}x" if rvol else ""
    return f"[{t}] {tk} {precio:.2f} · gatillo {nivel:.2f} · faltan {falta:+.2f} ({falta / precio * 100:+.2f}%){v}"


def resultado_plan(dia, desde, plan):
    largo = plan["lado"] == "largo"
    for j in range(desde, len(dia)):
        b = dia.iloc[j]
        hora = dia.index[j].strftime("%H:%M")
        if (b["Low"] <= plan["stop"]) if largo else (b["High"] >= plan["stop"]):
            print(f"[{hora}] ♥ STOP {plan['stop']:.2f} · -1.00R")
            return
        if (b["High"] >= plan["target"]) if largo else (b["Low"] <= plan["target"]):
            print(f"[{hora}] ★ TARGET {plan['target']:.2f} · +{plan['rr']:.2f}R")
            return
    cierre = float(dia["Close"].iloc[-1])
    r = ((cierre - plan["entrada"]) if largo else (plan["entrada"] - cierre)) / plan["riesgo_por_accion"]
    print(f"[16:00] Cierre sin tocar stop ni target: {cierre:.2f} · {r:+.2f}R")


def replay(tk, fecha, cond, nivel, vol_min, invalid, plan, desde):
    df = descargar_intradia(tk, periodo="7d", intervalo="1m")
    dia = df[df.index.date == fecha]
    if desde:
        dia = dia[dia.index.time >= dt.time.fromisoformat(desde)]
    if dia.empty:
        salir(f"No hay velas de 1 minuto para {fecha} (Yahoo guarda solo ~7 días).")
    print(f"⏪ REPLAY {tk} {fecha} desde {dia.index[0]:%H:%M} · condición {cond} {nivel:.2f}"
          + (f" · invalidación {invalid:.2f}" if invalid is not None else ""))
    estado, i, rvol = evaluar(dia, cond, nivel, vol_min, invalid)
    if estado == "ya_cruzado":
        print("El precio nunca estuvo del lado previo al gatillo: no hay ruptura que esperar (no persigas).")
        return
    if estado == "fuera_de_zona":
        print("El precio nunca entró en la zona entre el stop y el gatillo: el plan no aplicó ese día.")
        return
    if estado == "invalidado":
        print(f"[{dia.index[i]:%H:%M}] ✗ Setup INVALIDADO: tocó {invalid:.2f} antes de activarse.")
        return
    if estado == "esperando":
        print("Fin del día: el gatillo no se activó (sin entrada = sin pérdida).")
        return
    print(f"[{dia.index[i]:%H:%M}] 🚀 GATILLO ACTIVADO · {tk} {dia['Close'].iloc[i]:.2f}"
          + (f" · vol {rvol:.1f}x" if rvol else ""))
    if plan:
        resultado_plan(dia, i, plan)


def main():
    p = argparse.ArgumentParser(description="Gatillo de entrada")
    p.add_argument("ticker", nargs="?")
    p.add_argument("--plan", action="store_true", help="Usa el último plan de stop-y-target")
    p.add_argument("--nivel", type=float, help="Precio que activa la entrada")
    p.add_argument("--condicion", choices=["cruce-arriba", "cruce-abajo", "cierre-arriba", "cierre-abajo"])
    p.add_argument("--volumen", type=float, default=0, help="Exige volumen de la vela >= N veces la media (ej. 1.5)")
    p.add_argument("--invalidacion", type=float, help="Si toca este precio antes, se cancela (por defecto, el stop del plan)")
    p.add_argument("--cada", type=int, default=20, help="Segundos entre revisiones (en vivo)")
    p.add_argument("--max-min", type=float, default=60, help="Minutos máximos de espera")
    p.add_argument("--ejecutar", action="store_true", help="Abre la operación en paper al activarse (requiere --plan)")
    p.add_argument("--replay", help="Fecha AAAA-MM-DD para practicar con un día pasado")
    p.add_argument("--desde", help="Hora HH:MM desde la que empieza el replay (por defecto 09:30)")
    a = p.parse_args()
    requiere()

    plan = cargar_plan() if a.plan else None
    if plan:
        tk = plan["ticker"]
        nivel = a.nivel or plan["entrada"]
        cond = a.condicion or ("cruce-arriba" if plan["lado"] == "largo" else "cruce-abajo")
        invalid = a.invalidacion if a.invalidacion is not None else plan["stop"]
    else:
        if not a.ticker or a.nivel is None:
            p.error("indica TICKER y --nivel (o usa --plan)")
        if a.ejecutar:
            p.error("--ejecutar necesita --plan: no se entra sin stop y target")
        tk, nivel, invalid = a.ticker.upper(), a.nivel, a.invalidacion
        cond = a.condicion or "cruce-arriba"

    if a.replay:
        replay(tk, dt.date.fromisoformat(a.replay), cond, nivel, a.volumen, invalid, plan, a.desde)
        print(f"\n{AVISO}")
        return

    if not mercado_abierto():
        print(f"Mercado cerrado ({ahora_ny():%a %H:%M} NY). El gatillo funciona de 9:30 a 16:00 NY.")
        print("Para practicar ahora usa --replay AAAA-MM-DD con un día de los últimos 7.")
        sys.exit(3)

    inicio = ahora_ny() - dt.timedelta(minutes=1)
    fin = time.time() + a.max_min * 60
    print(f"⏳ Vigilando {tk}: {cond} {nivel:.2f}" + (f" con volumen >= {a.volumen:g}x" if a.volumen else "")
          + (f" · invalidación {invalid:.2f}" if invalid is not None else "") + f" · máx {a.max_min:g} min", flush=True)
    avisado = False
    while time.time() < fin:
        barras = descargar_intradia(tk, periodo="1d", intervalo="1m")
        barras = barras[barras.index >= inicio.replace(second=0, microsecond=0)]
        hora = ahora_ny().strftime("%H:%M:%S")
        if len(barras):
            estado, i, rvol = evaluar(barras, cond, nivel, a.volumen, invalid)
            print(linea(hora, tk, float(barras["Close"].iloc[-1]), nivel, rvol), flush=True)
            if estado == "ya_cruzado" and not avisado:
                print("  El precio ya está más allá del gatillo: no persigas. Espero a que vuelva y rompa de nuevo.", flush=True)
                avisado = True
            elif estado == "fuera_de_zona" and not avisado:
                print("  El precio está más allá del stop: espero a que entre en la zona stop–gatillo.", flush=True)
                avisado = True
            elif estado == "invalidado":
                print(f"[{hora}] ✗ Setup INVALIDADO: tocó {invalid:.2f}. No hay entrada.", flush=True)
                sys.exit(2)
            elif estado == "activado":
                print(f"[{hora}] 🚀 GATILLO ACTIVADO · {tk} {float(barras['Close'].iloc[i]):.2f}", flush=True)
                if a.ejecutar:
                    paper = SKILLS_DIR / "paper-trading" / "scripts" / "paper.py"
                    subprocess.run([sys.executable, str(paper), "abrir", "--plan"], check=False)
                print(f"\n{AVISO}")
                return
        if not mercado_abierto():
            break
        time.sleep(max(5, a.cada))
    print("Tiempo agotado sin activarse el gatillo (sin entrada = sin pérdida).")
    sys.exit(2)


if __name__ == "__main__":
    main()
