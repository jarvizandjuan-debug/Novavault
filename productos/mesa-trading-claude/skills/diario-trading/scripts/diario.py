"""Diario de trading: registra operaciones y mide lo que importa (win rate, R medio,
esperanza, profit factor, drawdown) por setup, día y hora.

Las operaciones de paper-trading (modo local) se anotan solas en ~/mesa-trading/diario/operaciones.csv.

Ejemplos:
  diario.py stats
  diario.py stats --desde 2026-10-01 --setup ORB
  diario.py agregar NVDA --entrada 214 --salida 219 --stop 211.5 --acciones 20 --setup ORB --notas "esperé confirmación"
  diario.py revision          # informe semanal en Markdown
"""
import argparse
import csv
import datetime as dt
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "configurar-mesa" / "scripts"))
from mesa_comun import AVISO, HOME, ahora_ny, dinero, salir, tabla  # noqa: E402

DIARIO = HOME / "diario" / "operaciones.csv"
CAMPOS = ["fecha", "ticker", "lado", "setup", "entrada", "salida", "stop", "target", "acciones", "pnl", "r",
          "motivo", "notas", "origen"]
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


def leer(desde=None, hasta=None, setup=None):
    if not DIARIO.exists():
        return []
    ops = []
    with open(DIARIO, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                row["pnl"] = float(row["pnl"])
                row["r"] = float(row["r"]) if row.get("r") not in ("", None) else 0.0
                row["dt"] = dt.datetime.fromisoformat(row["fecha"])
            except (ValueError, KeyError):
                continue
            if desde and row["dt"].date() < desde:
                continue
            if hasta and row["dt"].date() > hasta:
                continue
            if setup and row.get("setup", "").lower() != setup.lower():
                continue
            ops.append(row)
    ops.sort(key=lambda o: o["dt"].replace(tzinfo=None))
    return ops


def metricas(ops):
    n = len(ops)
    if not n:
        return None
    gan = [o for o in ops if o["pnl"] > 0]
    per = [o for o in ops if o["pnl"] < 0]
    bruto_g = sum(o["pnl"] for o in gan)
    bruto_p = -sum(o["pnl"] for o in per)
    curva, pico, dd = 0.0, 0.0, 0.0
    for o in ops:
        curva += o["pnl"]
        pico = max(pico, curva)
        dd = max(dd, pico - curva)
    racha, peor_racha = 0, 0
    for o in ops:
        racha = racha + 1 if o["pnl"] < 0 else 0
        peor_racha = max(peor_racha, racha)
    return {
        "operaciones": n,
        "win_rate": len(gan) / n,
        "r_medio_ganadoras": sum(o["r"] for o in gan) / len(gan) if gan else 0.0,
        "r_medio_perdedoras": sum(o["r"] for o in per) / len(per) if per else 0.0,
        "esperanza_r": sum(o["r"] for o in ops) / n,
        "profit_factor": bruto_g / bruto_p if bruto_p else float("inf"),
        "pnl_total": sum(o["pnl"] for o in ops),
        "max_drawdown": dd,
        "peor_racha": peor_racha,
        "mejor": max(ops, key=lambda o: o["pnl"]),
        "peor": min(ops, key=lambda o: o["pnl"]),
    }


def por(ops, clave):
    grupos = defaultdict(list)
    for o in ops:
        grupos[clave(o)].append(o)
    filas = []
    for k, g in sorted(grupos.items(), key=lambda kv: str(kv[0])):
        m = metricas(g)
        filas.append({"GRUPO": k or "(sin setup)", "OPS": m["operaciones"], "WIN%": f"{m['win_rate'] * 100:.0f}%",
                      "ESPERANZA": f"{m['esperanza_r']:+.2f}R", "P&L": dinero(m["pnl_total"])})
    return filas


def imprimir(m, titulo):
    pf = "∞" if m["profit_factor"] == float("inf") else f"{m['profit_factor']:.2f}"
    print(f"=== {titulo} ===")
    print(f"  Operaciones     {m['operaciones']}")
    print(f"  Win rate        {m['win_rate'] * 100:.1f}%")
    print(f"  R medio         ganadoras {m['r_medio_ganadoras']:+.2f}R · perdedoras {m['r_medio_perdedoras']:+.2f}R")
    print(f"  Esperanza       {m['esperanza_r']:+.2f}R por operación")
    print(f"  Profit factor   {pf}")
    print(f"  P&L total       {dinero(m['pnl_total'])}")
    print(f"  Máx. drawdown   {dinero(m['max_drawdown'])} · peor racha {m['peor_racha']} pérdidas seguidas")


def cmd_stats(a):
    ops = leer(a.desde, a.hasta, a.setup)
    m = metricas(ops)
    if not m:
        print("Aún no hay operaciones en el diario.")
        return
    imprimir(m, "DIARIO DE TRADING")
    print("\nPor setup:")
    tabla(por(ops, lambda o: o.get("setup", "")), ["GRUPO", "OPS", "WIN%", "ESPERANZA", "P&L"])
    print("\nPor hora de entrada (NY):")
    tabla(por(ops, lambda o: f"{o['dt'].hour:02d}h"), ["GRUPO", "OPS", "WIN%", "ESPERANZA", "P&L"])


def cmd_agregar(a):
    largo = a.lado == "largo"
    if a.stop is None:
        salir("Indica --stop: sin stop no se puede medir el riesgo (R).")
    riesgo = abs(a.entrada - a.stop) * a.acciones
    pnl = (a.salida - a.entrada) * a.acciones * (1 if largo else -1)
    op = {"fecha": (dt.datetime.fromisoformat(a.fecha) if a.fecha else ahora_ny()).isoformat(timespec="seconds"),
          "ticker": a.ticker.upper(), "lado": a.lado, "setup": a.setup, "entrada": a.entrada, "salida": a.salida,
          "stop": a.stop, "target": a.target or "", "acciones": a.acciones, "pnl": round(pnl, 2),
          "r": round(pnl / riesgo, 2) if riesgo else 0, "motivo": a.motivo, "notas": a.notas, "origen": "manual"}
    DIARIO.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not DIARIO.exists()
    with open(DIARIO, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if nuevo:
            w.writeheader()
        w.writerow(op)
    print(f"✓ Anotado: {op['ticker']} {dinero(op['pnl'])} ({op['r']:+.2f}R)")


def cmd_revision(a):
    hoy = ahora_ny().date()
    desde = a.desde or hoy - dt.timedelta(days=7)
    ops = leer(desde, hoy)
    m = metricas(ops)
    destino = HOME / "diario" / f"revision-{hoy.isoformat()}.md"
    lineas = [f"# Revisión de trading · {desde} → {hoy}", ""]
    if not m:
        lineas.append("Sin operaciones en el periodo.")
    else:
        pf = "∞" if m["profit_factor"] == float("inf") else f"{m['profit_factor']:.2f}"
        lineas += [
            "| Métrica | Valor |", "|---|---|",
            f"| Operaciones | {m['operaciones']} |",
            f"| Win rate | {m['win_rate'] * 100:.1f}% |",
            f"| Esperanza | {m['esperanza_r']:+.2f}R |",
            f"| Profit factor | {pf} |",
            f"| P&L | {dinero(m['pnl_total'])} |",
            f"| Máx. drawdown | {dinero(m['max_drawdown'])} |",
            "", "## Por setup", "", "| Setup | Ops | Win% | Esperanza | P&L |", "|---|---|---|---|---|",
        ]
        for f_ in por(ops, lambda o: o.get("setup", "")):
            lineas.append(f"| {f_['GRUPO']} | {f_['OPS']} | {f_['WIN%']} | {f_['ESPERANZA']} | {f_['P&L']} |")
        lineas += ["", "## Por día", "", "| Día | Ops | Win% | Esperanza | P&L |", "|---|---|---|---|---|"]
        for f_ in por(ops, lambda o: f"{o['dt'].weekday()}-{DIAS[o['dt'].weekday()]}"):
            lineas.append(f"| {f_['GRUPO'][2:]} | {f_['OPS']} | {f_['WIN%']} | {f_['ESPERANZA']} | {f_['P&L']} |")
        mej, pe = m["mejor"], m["peor"]
        lineas += ["", "## Extremos", "",
                   f"- Mejor: {mej['ticker']} {mej['fecha'][:10]} {dinero(mej['pnl'])} ({mej['r']:+.2f}R) — {mej.get('notas') or 'sin notas'}",
                   f"- Peor: {pe['ticker']} {pe['fecha'][:10]} {dinero(pe['pnl'])} ({pe['r']:+.2f}R) — {pe.get('notas') or 'sin notas'}",
                   "", "## Operaciones", "", "| Fecha | Ticker | Setup | R | P&L | Motivo |", "|---|---|---|---|---|---|"]
        for o in ops:
            lineas.append(f"| {o['fecha'][:16]} | {o['ticker']} | {o.get('setup', '')} | {o['r']:+.2f} | {dinero(o['pnl'])} | {o.get('motivo', '')} |")
        manuales = [o for o in ops if o.get("motivo") == "manual"]
        lineas += ["", "## Preguntas para la revisión", "",
                   f"- {len(manuales)} de {len(ops)} salidas fueron manuales (ni stop ni target). ¿Seguiste el plan?",
                   "- ¿Qué setup tiene esperanza positiva con al menos 20 operaciones? Ese es tu foco.",
                   "- ¿Hay una hora del día en la que pierdes de forma sistemática? Considera no operar en ella."]
    lineas += ["", f"_{AVISO}_", ""]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(lineas), encoding="utf-8")
    print("\n".join(lineas))
    print(f"\nGuardado en {destino}")


def main():
    p = argparse.ArgumentParser(description="Diario de trading")
    sub = p.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("stats")
    st.add_argument("--desde", type=dt.date.fromisoformat)
    st.add_argument("--hasta", type=dt.date.fromisoformat)
    st.add_argument("--setup")
    ag = sub.add_parser("agregar")
    ag.add_argument("ticker")
    ag.add_argument("--lado", choices=["largo", "corto"], default="largo")
    ag.add_argument("--entrada", type=float, required=True)
    ag.add_argument("--salida", type=float, required=True)
    ag.add_argument("--stop", type=float)
    ag.add_argument("--target", type=float)
    ag.add_argument("--acciones", type=int, required=True)
    ag.add_argument("--setup", default="")
    ag.add_argument("--motivo", default="manual", choices=["stop", "target", "manual"])
    ag.add_argument("--notas", default="")
    ag.add_argument("--fecha", help="AAAA-MM-DDTHH:MM (por defecto ahora)")
    rv = sub.add_parser("revision")
    rv.add_argument("--desde", type=dt.date.fromisoformat)
    a = p.parse_args()
    {"stats": cmd_stats, "agregar": cmd_agregar, "revision": cmd_revision}[a.cmd](a)


if __name__ == "__main__":
    main()
