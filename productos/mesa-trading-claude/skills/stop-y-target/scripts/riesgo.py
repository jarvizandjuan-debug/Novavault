"""Calcula stop, target y tamaño de posición ANTES de entrar, según tus reglas de riesgo.

Ejemplos:
  riesgo.py NVDA --entrada 214.50 --stop 211.80 --r 2.5
  riesgo.py NCLH --entrada 18.10 --stop-atr 1 --r 2 --guardar
  riesgo.py TSLA --stop-estructura --target 455 --guardar     # entrada = precio actual
  riesgo.py AMD --lado corto --entrada 150 --stop 152.2 --r 2
"""
import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "configurar-mesa" / "scripts"))
from mesa_comun import (AVISO, atr, cargar_config, descargar_intradia, dinero, guardar_plan, json_out,  # noqa: E402
                        pivotes, precio_actual, redondear_precio, requiere, salir, sesiones)


def main():
    p = argparse.ArgumentParser(description="Stop, target y tamaño de posición")
    p.add_argument("ticker")
    p.add_argument("--lado", choices=["largo", "corto"], default="largo")
    p.add_argument("--entrada", type=float, help="Precio de entrada (por defecto, el actual)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--stop", type=float, help="Stop en precio")
    g.add_argument("--stop-atr", type=float, help="Stop a N ATR de 5 minutos de la entrada")
    g.add_argument("--stop-estructura", action="store_true", help="Stop bajo el último mínimo (o sobre el último máximo)")
    t = p.add_mutually_exclusive_group()
    t.add_argument("--target", type=float, help="Target en precio")
    t.add_argument("--r", type=float, help="Target como múltiplo del riesgo (por defecto: rr_minimo de la config)")
    p.add_argument("--capital", type=float)
    p.add_argument("--riesgo-pct", type=float)
    p.add_argument("--setup", default="", help="Nombre del setup (para el diario)")
    p.add_argument("--guardar", action="store_true", help="Guarda el plan para gatillo, time-machine y paper")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()

    requiere()
    cfg = cargar_config()
    tk = a.ticker.upper()
    capital = a.capital or cfg["capital_paper"]
    riesgo_pct = a.riesgo_pct or cfg["riesgo_por_trade_pct"]
    largo = a.lado == "largo"

    intr = descargar_intradia(tk, periodo="5d", intervalo="5m")
    atr5 = float(atr(intr, 14).iloc[-1])
    entrada = a.entrada if a.entrada else precio_actual(tk)[0]

    if a.stop is not None:
        stop = a.stop
        metodo = "manual"
    elif a.stop_atr:
        stop = entrada - a.stop_atr * atr5 if largo else entrada + a.stop_atr * atr5
        metodo = f"{a.stop_atr:g} ATR(5m)"
    else:
        hoy = sesiones(intr)[-1]
        altos, bajos = pivotes(hoy if len(hoy) >= 10 else intr.iloc[-40:], ventana=2)
        colchon = 0.1 * atr5
        if largo:
            cand = [pr for _, pr in bajos if pr < entrada - 0.3 * atr5]
            stop = (cand[-1] if cand else float(intr["Low"].iloc[-12:].min())) - colchon
        else:
            cand = [pr for _, pr in altos if pr > entrada + 0.3 * atr5]
            stop = (cand[-1] if cand else float(intr["High"].iloc[-12:].max())) + colchon
        metodo = "estructura (último pivote 5m + colchón)"
    stop = redondear_precio(stop)
    riesgo_acc = (entrada - stop) if largo else (stop - entrada)
    if riesgo_acc <= 0:
        salir(f"El stop ({stop}) debe estar {'por debajo' if largo else 'por encima'} de la entrada ({entrada}).")

    if a.target is not None:
        target = a.target
    else:
        r = a.r or cfg["rr_minimo"]
        target = entrada + r * riesgo_acc if largo else entrada - r * riesgo_acc
    target = redondear_precio(target)
    beneficio_acc = (target - entrada) if largo else (entrada - target)
    if beneficio_acc <= 0:
        salir("El target debe estar del lado de la ganancia.")
    rr = beneficio_acc / riesgo_acc

    riesgo_usd = capital * riesgo_pct / 100
    acciones = math.floor(riesgo_usd / riesgo_acc)
    max_valor = capital * cfg["max_posicion_pct"] / 100
    limitado = False
    if acciones * entrada > max_valor:
        acciones = math.floor(max_valor / entrada)
        limitado = True

    avisos = []
    veredicto = "OPERABLE"
    if round(rr, 2) < cfg["rr_minimo"]:
        veredicto = "NO OPERAR"
        avisos.append(f"R:R {rr:.2f} menor que tu mínimo ({cfg['rr_minimo']:g}).")
    if riesgo_acc < 0.25 * atr5:
        veredicto = "NO OPERAR"
    if riesgo_acc < 0.5 * atr5:
        avisos.append(f"Stop muy ajustado: {riesgo_acc:.2f} < 0.5 ATR(5m) ({atr5:.2f}). El ruido normal puede sacarte.")
    if acciones < 1:
        veredicto = "NO OPERAR"
        avisos.append("Con tu riesgo por trade no alcanza ni para 1 acción.")
    if limitado:
        avisos.append(f"Posición limitada al {cfg['max_posicion_pct']:g}% del capital ({dinero(max_valor)}).")

    plan = {
        "ticker": tk, "lado": a.lado, "entrada": redondear_precio(entrada), "stop": stop, "target": target,
        "acciones": acciones, "riesgo_por_accion": round(riesgo_acc, 4), "rr": round(rr, 2),
        "riesgo_usd": round(acciones * riesgo_acc, 2), "beneficio_usd": round(acciones * beneficio_acc, 2),
        "valor_posicion": round(acciones * entrada, 2), "metodo_stop": metodo, "atr5m": round(atr5, 4),
        "setup": a.setup, "veredicto": veredicto, "avisos": avisos,
    }
    if a.guardar and veredicto == "OPERABLE":
        ruta = guardar_plan(plan)
        plan["guardado_en"] = str(ruta)
    if a.json:
        json_out(plan)
        return
    flecha = "▲ LARGO" if largo else "▼ CORTO"
    print(f"=== PLAN {tk} {flecha} ===")
    print(f"  Entrada  {plan['entrada']:>10.2f}")
    print(f"  ♥ Stop   {stop:>10.2f}   ({metodo}; riesgo {riesgo_acc:.2f}/acción)")
    print(f"  ★ Target {target:>10.2f}   (beneficio {beneficio_acc:.2f}/acción)")
    print(f"  R:R      {'1:' + format(rr, '.2f'):>10}")
    print(f"  Acciones {acciones:>10}   (valor {dinero(plan['valor_posicion'])})")
    print(f"  Riesgo   {dinero(plan['riesgo_usd']):>10}   ({riesgo_pct:g}% de {dinero(capital)})")
    print(f"  Ganancia {dinero(plan['beneficio_usd']):>10}   si toca el target")
    print(f"  ATR(5m)  {atr5:>10.2f}")
    print(f"\n  VEREDICTO: {veredicto}")
    for w in avisos:
        print(f"  ⚠ {w}")
    if plan.get("guardado_en"):
        print(f"\n  Plan guardado en {plan['guardado_en']} (úsalo con --plan en gatillo, time-machine y paper).")
    elif a.guardar:
        print("\n  No guardé el plan porque el veredicto es NO OPERAR.")
    print(f"\n{AVISO}")


if __name__ == "__main__":
    main()
