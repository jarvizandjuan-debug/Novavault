"""Analiza a fondo la gráfica de un ticker: tendencia, niveles clave y setups intradía,
con gatillo, stop y target sugeridos.

Ejemplos:
  analizar.py NVDA
  analizar.py TSLA --json
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "configurar-mesa" / "scripts"))
from mesa_comun import (AVISO, atr, descargar_diario, descargar_intradia, ema, json_out, pivotes,  # noqa: E402
                        requiere, sesiones, vwap)


def agrupar(niveles, tol=0.006):
    """Une niveles a menos de 0.6% entre sí (zonas, no líneas)."""
    out = []
    for p in niveles:
        if not out or abs(p / out[-1] - 1) > tol:
            out.append(round(p, 2))
    return out


def niveles_diarios(d):
    c = d["Close"]
    precio = float(c.iloc[-1])
    altos, bajos = pivotes(d.iloc[-120:], ventana=3)
    res = agrupar(sorted(p for _, p in altos if p > precio * 1.002))[:3]
    sop = agrupar(sorted((p for _, p in bajos if p < precio * 0.998), reverse=True))[:3]
    return {
        "precio": precio,
        "ema9": float(ema(c, 9).iloc[-1]),
        "ema20": float(ema(c, 20).iloc[-1]),
        "ema50": float(ema(c, 50).iloc[-1]),
        "ema200": float(ema(c, 200).iloc[-1]) if len(d) >= 200 else None,
        "atr": float(atr(d).iloc[-1]),
        "max_ayer": float(d["High"].iloc[-2]),
        "min_ayer": float(d["Low"].iloc[-2]),
        "cierre_ayer": float(c.iloc[-2]),
        "max20": float(d["High"].iloc[-21:-1].max()),
        "min20": float(d["Low"].iloc[-21:-1].min()),
        "max52": float(d["High"].iloc[-252:].max()),
        "resistencias": res,
        "soportes": sop,
    }


def tendencia(n):
    p, e9, e20, e50 = n["precio"], n["ema9"], n["ema20"], n["ema50"]
    if p > e9 > e20 > e50:
        return "ALCISTA fuerte (precio > EMA9 > EMA20 > EMA50)"
    if p > e20 > e50:
        return "ALCISTA"
    if p < e9 < e20 < e50:
        return "BAJISTA fuerte (precio < EMA9 < EMA20 < EMA50)"
    if p < e20 < e50:
        return "BAJISTA"
    return "LATERAL / mixta"


def setups_intradia(s, n_or=3):
    """Busca setups en la última sesión de velas de 5 minutos."""
    out = []
    if len(s) < n_or + 2:
        return out, {}
    vw = vwap(s)
    precio = float(s["Close"].iloc[-1])
    rango = (s["High"] - s["Low"]).rolling(12, min_periods=3).mean()
    rango_med = float(rango.iloc[-1]) or float((s["High"] - s["Low"]).mean())
    or_h = float(s["High"].iloc[:n_or].max())
    or_l = float(s["Low"].iloc[:n_or].min())
    info = {"apertura": float(s["Open"].iloc[0]), "precio": precio, "vwap": float(vw.iloc[-1]),
            "or_alto": or_h, "or_bajo": or_l, "max_dia": float(s["High"].max()), "min_dia": float(s["Low"].min()),
            "velas": len(s), "hora": s.index[-1].strftime("%H:%M")}

    # Opening Range Breakout (15 min)
    despues = s.iloc[n_or:]
    if len(despues) and float(despues["High"].max()) > or_h:
        estado = "ROTO al alza" if precio > or_h else "roto y perdido"
    else:
        estado = "pendiente (dentro del rango)" if precio <= or_h else "ROTO al alza"
    out.append({"setup": "ORB 15m", "estado": estado, "gatillo": or_h, "stop": or_l,
                "nota": "Entrada al romper el máximo de los primeros 15 min; stop bajo el mínimo del rango."})

    # VWAP
    lado = "ENCIMA" if precio > vw.iloc[-1] else "DEBAJO"
    cruces = (s["Close"] > vw).astype(int).diff().fillna(0)
    ult = s.index[cruces != 0]
    reclaim = len(s) >= 8 and cruces.iloc[-6:].max() > 0 and (s["Close"].iloc[-10:-5] < vw.iloc[-10:-5]).sum() >= 3
    if reclaim and lado == "ENCIMA":
        stop = float(s["Low"].iloc[-6:].min())
        out.append({"setup": "VWAP reclaim", "estado": "ACTIVO", "gatillo": float(s["High"].iloc[-1]), "stop": stop,
                    "nota": "Recuperó el VWAP tras estar debajo; entrada sobre el máximo de la vela actual."})
    info["vwap_lado"] = lado
    info["ultimo_cruce_vwap"] = ult[-1].strftime("%H:%M") if len(ult) else None

    # Bandera alcista intradía: mástil >= 3 velas promedio en <= 6 velas, consolidación de 3-8 velas
    h, l, c = s["High"].values, s["Low"].values, s["Close"].values
    for cons in range(3, 9):
        fin = len(s) - 1 - cons
        if fin < 6:
            break
        subida = h[fin] - min(l[fin - 6:fin + 1])
        if subida < 3 * rango_med:
            continue
        ch, cl = max(h[fin + 1:]), min(l[fin + 1:])
        if (h[fin] - cl) / subida <= 0.5 and (ch - cl) <= 0.6 * subida and c[-1] >= cl + 0.4 * (ch - cl):
            out.append({"setup": "Bandera alcista 5m", "estado": "FORMÁNDOSE", "gatillo": float(ch), "stop": float(cl),
                        "nota": f"Mástil de {subida:.2f} y {cons} velas de bandera; entrada al romper el techo."})
            break

    # Mínimos crecientes
    _, bajos = pivotes(s, ventana=2)
    if len(bajos) >= 3 and bajos[-3][1] < bajos[-2][1] < bajos[-1][1]:
        out.append({"setup": "Mínimos crecientes", "estado": "tendencia intradía alcista",
                    "gatillo": float(s["High"].iloc[-6:].max()), "stop": float(bajos[-1][1]),
                    "nota": "Tres mínimos más altos seguidos; stop bajo el último mínimo."})
    return out, info


def main():
    p = argparse.ArgumentParser(description="Detector de setups")
    p.add_argument("ticker")
    p.add_argument("--r", type=float, default=2.0, help="Múltiplo R para el target sugerido")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    requiere()
    t = a.ticker.upper()
    d = descargar_diario([t], periodo="1y", progreso=False).get(t)
    if d is None or len(d) < 30:
        print(f"ERROR: sin datos diarios suficientes para {t}.", file=sys.stderr)
        sys.exit(1)
    n = niveles_diarios(d.dropna())
    intr = descargar_intradia(t, periodo="5d", intervalo="5m")
    ses = sesiones(intr)
    hoy = ses[-1]
    setups, info = setups_intradia(hoy)
    for s in setups:
        riesgo = s["gatillo"] - s["stop"]
        if riesgo > 0:
            s["target"] = s["gatillo"] + a.r * riesgo
            arriba = [r for r in n["resistencias"] if r > s["gatillo"]]
            s["resistencia_siguiente"] = arriba[0] if arriba else None
            s["riesgo_por_accion"] = riesgo
        else:
            s["target"] = None
    tend = tendencia(n)
    if a.json:
        json_out({"ticker": t, "tendencia": tend, "diario": n, "sesion": info, "setups": setups,
                  "fecha_sesion": str(hoy.index[-1].date())})
        return
    print(f"=== {t} · sesión {hoy.index[-1].date()} (hasta {info.get('hora')}) ===")
    print(f"Precio {n['precio']:.2f} · Tendencia diaria: {tend}")
    print(f"ATR diario {n['atr']:.2f} ({n['atr'] / n['precio'] * 100:.1f}%) · EMA9 {n['ema9']:.2f} · EMA20 {n['ema20']:.2f} · EMA50 {n['ema50']:.2f}")
    print(f"Ayer: máx {n['max_ayer']:.2f} · mín {n['min_ayer']:.2f} · cierre {n['cierre_ayer']:.2f}")
    print(f"Máx 20d {n['max20']:.2f} · Mín 20d {n['min20']:.2f} · Máx 52s {n['max52']:.2f}")
    print(f"Resistencias: {', '.join(f'{x:.2f}' for x in n['resistencias']) or '—'}")
    print(f"Soportes:     {', '.join(f'{x:.2f}' for x in n['soportes']) or '—'}")
    if info:
        print(f"\nIntradía: apertura {info['apertura']:.2f} · VWAP {info['vwap']:.2f} ({info['vwap_lado']}) · "
              f"rango 15m {info['or_bajo']:.2f}–{info['or_alto']:.2f} · máx/mín día {info['max_dia']:.2f}/{info['min_dia']:.2f}")
    print("\nSetups detectados:")
    for s in setups:
        linea = f"  • {s['setup']}: {s['estado']} · gatillo {s['gatillo']:.2f} · stop {s['stop']:.2f}"
        if s.get("target"):
            linea += f" · target {a.r:g}R {s['target']:.2f}"
        print(linea)
        print(f"    {s['nota']}")
    print(f"\n{AVISO}")


if __name__ == "__main__":
    main()
