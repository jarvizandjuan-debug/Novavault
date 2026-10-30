"""Backtest de setups intradía con velas reales de 5 minutos (hasta 60 días, límite de Yahoo).

Setups:
  orb           Ruptura del rango de apertura (por defecto 15 min). Stop: mínimo del rango (o la mitad).
  primera-vela  Gap >= X%: entrada al romper el máximo de la primera vela de 5m. Stop: su mínimo.
  vwap-reclaim  Tras 3+ velas bajo el VWAP, cierre por encima: entrada al cierre. Stop: mínimo de 3 velas.

Una operación por día y ticker, salida en stop, target (múltiplo R) o a la hora límite.
Si stop y target caen en la misma vela, cuenta como stop (conservador). Sin comisiones.

Ejemplos:
  backtest.py --setup orb --tickers NVDA,TSLA,AMD
  backtest.py --setup primera-vela --gap 3 --tickers watchlist --r 2
  backtest.py --setup vwap-reclaim --tickers SPY,QQQ --r 1.5 --json
"""
import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "configurar-mesa" / "scripts"))
from mesa_comun import (AVISO, HOME, cargar_config, descargar_intradia, json_out, requiere, sesiones,  # noqa: E402
                        tabla, universo, vwap)


def salida(s, i0, entrada, stop, target, hasta):
    """Recorre desde la vela i0 (inclusive) hasta la hora límite."""
    for j in range(i0, len(s)):
        t = s.index[j]
        if t.time() >= hasta:
            return float(s["Open"].iloc[j]), "hora", t
        lo, hi, op = float(s["Low"].iloc[j]), float(s["High"].iloc[j]), float(s["Open"].iloc[j])
        if lo <= stop:
            return (min(op, stop) if j > i0 else stop), "stop", t
        if hi >= target:
            return (max(op, target) if j > i0 else target), "target", t
    return float(s["Close"].iloc[-1]), "cierre", s.index[-1]


def orb(s, a, cierre_previo):
    n = max(1, a.or_min // 5)
    if len(s) <= n + 1:
        return None
    h, l = float(s["High"].iloc[:n].max()), float(s["Low"].iloc[:n].min())
    stop = l if a.stop == "rango" else (h + l) / 2
    for i in range(n, len(s)):
        if s.index[i].time() >= a.ultima_entrada:
            return None
        if float(s["High"].iloc[i]) > h:
            entrada = max(h, float(s["Open"].iloc[i]))
            return i, entrada, stop
    return None


def primera_vela(s, a, cierre_previo):
    if cierre_previo is None or len(s) < 3:
        return None
    gap = float(s["Open"].iloc[0]) / cierre_previo - 1
    if gap < a.gap / 100:
        return None
    h, l = float(s["High"].iloc[0]), float(s["Low"].iloc[0])
    for i in range(1, len(s)):
        if s.index[i].time() >= a.ultima_entrada:
            return None
        if float(s["Low"].iloc[i]) < l:
            return None  # perdió el mínimo antes de romper: setup fallido
        if float(s["High"].iloc[i]) > h:
            return i, max(h, float(s["Open"].iloc[i])), l
    return None


def vwap_reclaim(s, a, cierre_previo):
    vw = vwap(s).values
    c = s["Close"].values
    debajo = 0
    for i in range(1, len(s) - 1):
        t = s.index[i].time()
        if t >= a.ultima_entrada:
            return None
        if c[i] < vw[i]:
            debajo += 1
            continue
        if debajo >= 3 and t >= dt.time(10, 0):
            stop = float(s["Low"].iloc[max(0, i - 2):i + 1].min())
            if stop < c[i]:
                return i + 1, float(c[i]), stop  # entrada al cierre de la vela i, se gestiona desde i+1
        debajo = 0
    return None


SETUPS = {"orb": orb, "primera-vela": primera_vela, "vwap-reclaim": vwap_reclaim}


def backtest_ticker(tk, a):
    df = descargar_intradia(tk, periodo=f"{a.dias}d", intervalo="5m")
    ops = []
    previo = None
    for s in sesiones(df):
        señal = SETUPS[a.setup](s, a, previo)
        previo = float(s["Close"].iloc[-1])
        if not señal:
            continue
        i, entrada, stop = señal
        riesgo = entrada - stop
        if riesgo <= 0 or riesgo / entrada < 0.0005:
            continue
        target = entrada + a.r * riesgo
        px, motivo, t_sal = salida(s, i, entrada, stop, target, a.hasta)
        ops.append({"ticker": tk, "fecha": str(s.index[0].date()), "entrada_hora": s.index[min(i, len(s) - 1)].strftime("%H:%M"),
                    "entrada": round(entrada, 2), "stop": round(stop, 2), "target": round(target, 2),
                    "salida": round(px, 2), "motivo": motivo, "r": round((px - entrada) / riesgo, 2)})
    return ops


def resumen(ops):
    n = len(ops)
    if not n:
        return None
    rs = [o["r"] for o in ops]
    gan = [r for r in rs if r > 0]
    per = [r for r in rs if r <= 0]
    curva, pico, dd = 0.0, 0.0, 0.0
    for r in rs:
        curva += r
        pico = max(pico, curva)
        dd = max(dd, pico - curva)
    return {"operaciones": n, "win_rate": len(gan) / n, "esperanza_r": sum(rs) / n, "total_r": sum(rs),
            "profit_factor": (sum(gan) / -sum(per)) if per and sum(per) < 0 else float("inf"),
            "max_drawdown_r": dd, "por_motivo": {m: sum(1 for o in ops if o["motivo"] == m) for m in
                                                  ("target", "stop", "hora", "cierre")}}


def main():
    p = argparse.ArgumentParser(description="Backtest de setups intradía")
    p.add_argument("--setup", choices=list(SETUPS), default="orb")
    p.add_argument("--tickers", default="watchlist", help="'NVDA,TSLA' | watchlist | ruta.txt")
    p.add_argument("--dias", type=int, default=60)
    p.add_argument("--r", type=float, default=2.0)
    p.add_argument("--or-min", type=int, default=15, help="Minutos del rango de apertura (ORB)")
    p.add_argument("--stop", choices=["rango", "mitad"], default="rango", help="Stop del ORB")
    p.add_argument("--gap", type=float, default=2.0, help="Gap mínimo %% (primera-vela)")
    p.add_argument("--ultima-entrada", type=dt.time.fromisoformat, default=dt.time(11, 30))
    p.add_argument("--hasta", type=dt.time.fromisoformat, default=dt.time(15, 55), help="Hora de salida forzada")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    requiere()
    a.dias = max(1, min(a.dias, 60))
    tickers = universo(a.tickers, cargar_config())
    if len(tickers) > 40:
        tickers = tickers[:40]
        print("Aviso: limito el backtest a 40 tickers.", file=sys.stderr)
    ops, por_ticker = [], []
    for tk in tickers:
        try:
            o = backtest_ticker(tk, a)
        except SystemExit:
            continue
        ops += o
        m = resumen(o)
        if m:
            por_ticker.append({"TICKER": tk, "OPS": m["operaciones"], "WIN%": f"{m['win_rate'] * 100:.0f}%",
                               "ESPERANZA": f"{m['esperanza_r']:+.2f}R", "TOTAL": f"{m['total_r']:+.1f}R"})
    m = resumen(ops)
    (HOME / "backtests").mkdir(parents=True, exist_ok=True)
    destino = HOME / "backtests" / f"{a.setup}-{dt.date.today().isoformat()}.csv"
    if ops:
        import csv
        with open(destino, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(ops[0]))
            w.writeheader()
            w.writerows(ops)
    if a.json:
        json_out({"setup": a.setup, "parametros": {"r": a.r, "dias": a.dias, "or_min": a.or_min, "gap": a.gap},
                  "resumen": m, "operaciones": ops})
        return
    print(f"=== BACKTEST {a.setup.upper()} · {len(tickers)} tickers · {a.dias} días · target {a.r:g}R ===")
    if not m:
        print("El setup no se activó en el periodo. Prueba otros tickers o parámetros.")
        return
    pf = "∞" if m["profit_factor"] == float("inf") else f"{m['profit_factor']:.2f}"
    print(f"  Operaciones {m['operaciones']} · win rate {m['win_rate'] * 100:.1f}% · esperanza {m['esperanza_r']:+.2f}R "
          f"· total {m['total_r']:+.1f}R · profit factor {pf} · máx. drawdown {m['max_drawdown_r']:.1f}R")
    pm = m["por_motivo"]
    print(f"  Salidas: {pm['target']} target · {pm['stop']} stop · {pm['hora'] + pm['cierre']} por hora")
    print()
    tabla(por_ticker, ["TICKER", "OPS", "WIN%", "ESPERANZA", "TOTAL"])
    print(f"\nDetalle guardado en {destino}")
    print("Limitaciones: 60 días como máximo, sin comisiones ni deslizamiento, una entrada por día. "
          "Menos de 30 operaciones no es una muestra fiable.")
    print(AVISO)


if __name__ == "__main__":
    main()
