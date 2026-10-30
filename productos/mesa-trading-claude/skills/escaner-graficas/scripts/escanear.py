"""Escanea cientos o miles de gráficas diarias y ordena las acciones con mejores setups.

Ejemplos:
  escanear.py                              # universo de la config (S&P 500 por defecto)
  escanear.py --universo todo-usa --top 30 # todas las acciones de EE. UU. (tarda unos minutos)
  escanear.py --universo watchlist --setup gap
  escanear.py --universo "AAPL,NVDA,TSLA" --json
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "configurar-mesa" / "scripts"))
from mesa_comun import (AVISO, HOME, atr, cargar_config, descargar_diario, ema, json_out,  # noqa: E402
                        requiere, tabla, universo)

SETUPS = ["todos", "gap", "momentum", "ruptura", "bandera", "rebote-ema", "volumen"]


def bandera_diaria(df, a):
    """Mástil fuerte (>= 3 ATR en <= 6 velas) seguido de 3-10 velas de consolidación estrecha."""
    h, l, c = df["High"].values, df["Low"].values, df["Close"].values
    n = len(df)
    mejor = None
    for fin_mastil in range(n - 11, n - 3):
        if fin_mastil < 8:
            continue
        ini = fin_mastil - 6
        subida = h[fin_mastil] - min(l[ini:fin_mastil + 1])
        if subida < 3 * a:
            continue
        cons_h = max(h[fin_mastil + 1:])
        cons_l = min(l[fin_mastil + 1:])
        retroceso = (h[fin_mastil] - cons_l) / subida
        rango = (cons_h - cons_l) / a
        if retroceso <= 0.5 and rango <= 2.5 and c[-1] >= cons_l + 0.5 * (cons_h - cons_l):
            calidad = (1 - retroceso) * min(subida / a / 6, 1)
            if not mejor or calidad > mejor["calidad"]:
                mejor = {"calidad": calidad, "techo": float(cons_h), "suelo": float(cons_l)}
    return mejor


def analizar(t, df):
    if len(df) < 60:
        return None
    df = df.dropna()
    c, o, h, l, v = df["Close"], df["Open"], df["High"], df["Low"], df["Volume"]
    precio, previo = float(c.iloc[-1]), float(c.iloc[-2])
    if previo <= 0 or precio <= 0:
        return None
    a = float(atr(df).iloc[-1])
    vol_medio = float(v.iloc[-21:-1].mean())
    e9, e20, e50 = (float(ema(c, n).iloc[-1]) for n in (9, 20, 50))
    max20 = float(h.iloc[-21:-1].max())
    max52 = float(h.iloc[-252:].max())
    r = {
        "ticker": t,
        "precio": precio,
        "cambio": precio / previo - 1,
        "gap": float(o.iloc[-1]) / previo - 1,
        "rvol": float(v.iloc[-1]) / vol_medio if vol_medio > 0 else 0.0,
        "atr_pct": a / precio,
        "vol_medio": vol_medio,
        "tendencia": precio > e9 > e20 > e50,
        "ruptura20": precio > max20,
        "cerca_max52": precio >= 0.97 * max52,
        "rebote_ema": precio > e20 > e50 and float(l.iloc[-1]) <= e20 * 1.005 and precio > e20,
        "inside": float(h.iloc[-1]) < float(h.iloc[-2]) and float(l.iloc[-1]) > float(l.iloc[-2]),
        "bandera": bandera_diaria(df, a) if a > 0 else None,
        "fecha": str(df.index[-1].date()),
    }
    senales = []
    if abs(r["gap"]) >= 0.02:
        senales.append("GAP" + ("↑" if r["gap"] > 0 else "↓"))
    if r["rvol"] >= 1.5:
        senales.append(f"RVOL{r['rvol']:.1f}")
    if r["ruptura20"]:
        senales.append("RUPTURA20")
    if r["bandera"]:
        senales.append("BANDERA")
    if r["rebote_ema"]:
        senales.append("REBOTE-EMA20")
    if r["tendencia"]:
        senales.append("TENDENCIA")
    if r["cerca_max52"]:
        senales.append("MAX52")
    if r["inside"]:
        senales.append("INSIDE")
    r["senales"] = senales
    return r


def puntaje(r, setup):
    rv = min(r["rvol"] / 3, 1.0)
    mom = min(abs(r["cambio"]) / 0.06, 1.0)
    gap = min(abs(r["gap"]) / 0.05, 1.0)
    if setup == "gap":
        return 60 * gap + 40 * rv if abs(r["gap"]) >= 0.02 else 0
    if setup == "momentum":
        return 50 * mom + 30 * rv + 20 * r["tendencia"] if r["cambio"] > 0 else 0
    if setup == "ruptura":
        return 50 * r["ruptura20"] + 30 * rv + 20 * r["cerca_max52"] if r["ruptura20"] else 0
    if setup == "bandera":
        return 70 * r["bandera"]["calidad"] + 30 * r["tendencia"] if r["bandera"] else 0
    if setup == "rebote-ema":
        return 60 * r["rebote_ema"] + 40 * rv if r["rebote_ema"] else 0
    if setup == "volumen":
        return 100 * rv if r["rvol"] >= 1.5 else 0
    return (25 * rv + 20 * mom + 15 * gap + 12 * r["ruptura20"] + 12 * bool(r["bandera"])
            + 8 * r["tendencia"] + 4 * r["rebote_ema"] + 4 * r["cerca_max52"])


def main():
    p = argparse.ArgumentParser(description="Escáner de gráficas")
    p.add_argument("--universo", help="sp500 | todo-usa | watchlist | 'AAPL,MSFT' | ruta.txt")
    p.add_argument("--setup", default="todos", choices=SETUPS)
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--precio-min", type=float)
    p.add_argument("--vol-min", type=float, help="Volumen medio diario mínimo (acciones)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--csv", help="Guarda todos los resultados en este CSV")
    a = p.parse_args()

    requiere()
    cfg = cargar_config()
    tickers = universo(a.universo, cfg)
    pmin = a.precio_min if a.precio_min is not None else cfg["precio_min"]
    vmin = a.vol_min if a.vol_min is not None else cfg["volumen_medio_min"]
    if not a.json:
        print(f"Escaneando {len(tickers):,} gráficas (setup: {a.setup})...", file=sys.stderr, flush=True)
    t0 = time.time()
    datos = descargar_diario(tickers, periodo="1y")
    res = []
    for t, df in datos.items():
        try:
            r = analizar(t, df)
        except Exception:
            continue
        if not r or r["precio"] < pmin or r["vol_medio"] < vmin:
            continue
        r["puntaje"] = round(puntaje(r, a.setup), 1)
        if r["puntaje"] > 0:
            res.append(r)
    res.sort(key=lambda r: r["puntaje"], reverse=True)
    dur = time.time() - t0

    if a.csv:
        import csv
        with open(a.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["ticker", "puntaje", "precio", "cambio", "gap", "rvol", "atr_pct", "senales", "fecha"])
            for r in res:
                w.writerow([r["ticker"], r["puntaje"], round(r["precio"], 2), round(r["cambio"], 4), round(r["gap"], 4),
                            round(r["rvol"], 2), round(r["atr_pct"], 4), " ".join(r["senales"]), r["fecha"]])
    top = res[:a.top]
    (HOME / "cache").mkdir(parents=True, exist_ok=True)
    (HOME / "cache" / "ultimo_escaneo.txt").write_text("\n".join(r["ticker"] for r in top), encoding="utf-8")
    if a.json:
        json_out({"escaneadas": len(datos), "solicitadas": len(tickers), "candidatas": len(res), "segundos": round(dur, 1),
                  "setup": a.setup, "top": [{k: v for k, v in r.items() if k != "bandera"} | {"bandera": bool(r["bandera"])}
                                             for r in top]})
        return
    print(f"\nEscaneadas {len(datos):,} gráficas en {dur:.0f}s · {len(res)} candidatas · setup: {a.setup}")
    if not top:
        print("Ninguna acción cumple los filtros. Prueba otro setup o baja --precio-min/--vol-min.")
        return
    filas = [{"#": i + 1, "TICKER": r["ticker"], "PUNTAJE": r["puntaje"], "PRECIO": f"{r['precio']:.2f}",
              "CAMBIO": f"{r['cambio'] * 100:+.1f}%", "GAP": f"{r['gap'] * 100:+.1f}%", "RVOL": f"{r['rvol']:.1f}x",
              "ATR%": f"{r['atr_pct'] * 100:.1f}%", "SEÑALES": " ".join(r["senales"])} for i, r in enumerate(top)]
    tabla(filas, ["#", "TICKER", "PUNTAJE", "PRECIO", "CAMBIO", "GAP", "RVOL", "ATR%", "SEÑALES"])
    print(f"\nDatos diarios hasta {top[0]['fecha']} (RVOL parcial si el mercado sigue abierto). {AVISO}")


if __name__ == "__main__":
    main()
