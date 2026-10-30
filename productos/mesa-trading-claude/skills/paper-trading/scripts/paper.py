"""Paper trading (sin dinero real). Toda operación nace con stop y target (orden bracket).

Modos (config "modo_paper"):
  local  - cuenta simulada en ~/mesa-trading/paper/cuenta.json (no requiere registro)
  alpaca - cuenta PAPER de Alpaca (https://paper-api.alpaca.markets). Nunca usa la API real.

Ejemplos:
  paper.py cuenta
  paper.py abrir --plan                                   # usa el último plan de stop-y-target
  paper.py abrir NVDA --acciones 20 --stop 211.5 --target 219
  paper.py posiciones                                     # revisa stops/targets y muestra P&L
  paper.py cerrar NVDA
  paper.py historial
  paper.py reiniciar --confirmar
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "configurar-mesa" / "scripts"))
from mesa_comun import (AVISO, HOME, ahora_ny, cargar_config, cargar_plan, descargar_intradia, dinero,  # noqa: E402
                        mercado_abierto, precio_actual, redondear_precio, requiere, salir, tabla)

ALPACA_PAPER = "https://paper-api.alpaca.markets"  # fijo: este script nunca opera con dinero real
CUENTA = HOME / "paper" / "cuenta.json"
DIARIO = HOME / "diario" / "operaciones.csv"
CAMPOS_DIARIO = ["fecha", "ticker", "lado", "setup", "entrada", "salida", "stop", "target", "acciones", "pnl", "r",
                 "motivo", "notas", "origen"]


# ---------------------------------------------------------------- diario
def anotar_diario(op):
    import csv
    DIARIO.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not DIARIO.exists()
    with open(DIARIO, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS_DIARIO)
        if nuevo:
            w.writeheader()
        w.writerow({k: op.get(k, "") for k in CAMPOS_DIARIO})


# ---------------------------------------------------------------- modo local
def cargar_cuenta(cfg):
    if CUENTA.exists():
        return json.loads(CUENTA.read_text(encoding="utf-8"))
    return {"capital_inicial": cfg["capital_paper"], "efectivo": cfg["capital_paper"], "posiciones": [], "cerradas": []}


def guardar_cuenta(c):
    CUENTA.parent.mkdir(parents=True, exist_ok=True)
    CUENTA.write_text(json.dumps(c, indent=2, ensure_ascii=False), encoding="utf-8")


def perdida_hoy(c):
    hoy = ahora_ny().date().isoformat()
    return -sum(op["pnl"] for op in c["cerradas"] if op["fecha"].startswith(hoy) and op["pnl"] < 0)


def cerrar_local(c, pos, precio, motivo, cuando):
    largo = pos["lado"] == "largo"
    pnl = (precio - pos["entrada"]) * pos["acciones"] * (1 if largo else -1)
    riesgo = abs(pos["entrada"] - pos["stop"]) * pos["acciones"]
    op = dict(pos, salida=round(precio, 4), pnl=round(pnl, 2), r=round(pnl / riesgo, 2) if riesgo else 0,
              motivo=motivo, cerrada_en=cuando, fecha=pos["abierta_en"], origen="paper-local")
    c["efectivo"] += pos["acciones"] * pos["entrada"] + pnl  # se libera lo invertido (o la garantía del corto)
    c["posiciones"].remove(pos)
    c["cerradas"].append(op)
    anotar_diario(op)
    return op


def revisar_local(c):
    """Recorre las velas desde la entrada para ver si se tocó el stop o el target (bracket simulado)."""
    cerradas = []
    for pos in list(c["posiciones"]):
        desde = dt.datetime.fromisoformat(pos["abierta_en"])
        dias = (ahora_ny() - desde).days
        df = descargar_intradia(pos["ticker"], periodo="7d" if dias < 6 else "60d", intervalo="1m" if dias < 6 else "5m")
        df = df[df.index > desde]
        largo = pos["lado"] == "largo"
        for t, b in df.iterrows():
            s_hit = b["Low"] <= pos["stop"] if largo else b["High"] >= pos["stop"]
            t_hit = b["High"] >= pos["target"] if largo else b["Low"] <= pos["target"]
            if s_hit:  # si ambos en la misma vela: stop (conservador); con gap, al precio de apertura
                precio = min(b["Open"], pos["stop"]) if largo else max(b["Open"], pos["stop"])
                cerradas.append(cerrar_local(c, pos, float(precio), "stop", t.isoformat()))
                break
            if t_hit:
                precio = max(b["Open"], pos["target"]) if largo else min(b["Open"], pos["target"])
                cerradas.append(cerrar_local(c, pos, float(precio), "target", t.isoformat()))
                break
    return cerradas


# ---------------------------------------------------------------- modo alpaca
def alpaca(metodo, ruta, cuerpo=None):
    cfg = cargar_config()
    key = os.environ.get("APCA_API_KEY_ID") or cfg.get("alpaca_key_id")
    sec = os.environ.get("APCA_API_SECRET_KEY") or cfg.get("alpaca_secret_key")
    if not key or not sec:
        salir("Faltan las claves de Alpaca PAPER: exporta APCA_API_KEY_ID y APCA_API_SECRET_KEY.")
    req = urllib.request.Request(ALPACA_PAPER + ruta, method=metodo,
                                 data=json.dumps(cuerpo).encode() if cuerpo is not None else None,
                                 headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec,
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            txt = r.read()
            return json.loads(txt) if txt else {}
    except urllib.error.HTTPError as e:
        salir(f"Alpaca respondió {e.code}: {e.read().decode(errors='replace')}")


# ---------------------------------------------------------------- comandos
def datos_orden(a):
    if a.plan:
        pl = cargar_plan()
        if pl.get("veredicto") != "OPERABLE":
            salir("El último plan no es OPERABLE.")
        return (pl["ticker"], pl["lado"], int(a.acciones or pl["acciones"]), pl["stop"], pl["target"],
                pl.get("setup", ""), pl.get("entrada"))
    if not a.ticker or a.stop is None or a.target is None or not a.acciones:
        salir("Para abrir sin --plan indica TICKER --acciones --stop y --target. Sin stop no se entra.")
    return a.ticker.upper(), a.lado, a.acciones, a.stop, a.target, a.setup, None


def cmd_abrir(a, cfg):
    tk, lado, acciones, stop, target, setup, entrada_plan = datos_orden(a)
    largo = lado == "largo"
    if acciones < 1:
        salir("Acciones debe ser al menos 1.")
    precio, ts = precio_actual(tk)
    if not mercado_abierto():
        print(f"⚠ Mercado cerrado: uso el último precio disponible ({precio:.2f}, {ts:%d/%m %H:%M} NY, puede ser pre/post-market).")
    if largo and not (stop < precio < target) or not largo and not (target < precio < stop):
        salir(f"El precio actual ({precio:.2f}) no está entre stop ({stop}) y target ({target}). "
              "El setup ya no es válido: recalcula con stop-y-target.")
    if cfg["modo_paper"] == "alpaca":
        orden = {"symbol": tk, "qty": str(acciones), "side": "buy" if largo else "sell", "type": "market",
                 "time_in_force": "day", "order_class": "bracket",
                 "take_profit": {"limit_price": str(redondear_precio(target))},
                 "stop_loss": {"stop_price": str(redondear_precio(stop))},
                 "client_order_id": f"mesa-{uuid.uuid4().hex[:12]}"}
        r = alpaca("POST", "/v2/orders", orden)
        print(f"Orden bracket enviada a Alpaca PAPER: {r.get('id')} · estado {r.get('status')}")
        print(f"  {'COMPRA' if largo else 'VENTA CORTA'} {acciones} {tk} a mercado · stop {stop} · target {target}")
        return
    c = cargar_cuenta(cfg)
    limite = c["capital_inicial"] * cfg["max_perdida_diaria_pct"] / 100
    if perdida_hoy(c) >= limite:
        salir(f"Bloqueado: hoy ya perdiste {dinero(perdida_hoy(c))} (límite diario {dinero(limite)}). Mañana será otro día.")
    desl = precio * cfg.get("deslizamiento_pct", 0) / 100
    fill = precio + desl if largo else precio - desl
    coste = acciones * fill
    if coste > c["efectivo"]:
        salir(f"Efectivo insuficiente: necesitas {dinero(coste)} y tienes {dinero(c['efectivo'])}.")
    pos = {"id": uuid.uuid4().hex[:8], "ticker": tk, "lado": lado, "acciones": acciones, "entrada": round(fill, 4),
           "stop": stop, "target": target, "setup": setup, "abierta_en": ahora_ny().isoformat(timespec="seconds")}
    c["efectivo"] -= coste
    c["posiciones"].append(pos)
    guardar_cuenta(c)
    riesgo = abs(fill - stop) * acciones
    print(f"✓ PAPER {'COMPRA' if largo else 'CORTO'} {acciones} {tk} @ {fill:.2f} (precio {precio:.2f} + deslizamiento)")
    print(f"  ♥ stop {stop} · ★ target {target} · riesgo {dinero(riesgo)} · id {pos['id']}")
    if entrada_plan and abs(fill / entrada_plan - 1) > 0.003:
        print(f"  ⚠ Entraste a {fill:.2f}, lejos de la entrada planeada {entrada_plan:.2f}: el R:R real cambia.")


def cmd_posiciones(a, cfg):
    if cfg["modo_paper"] == "alpaca":
        pos = alpaca("GET", "/v2/positions")
        if not pos:
            print("Sin posiciones abiertas en Alpaca PAPER.")
            return
        tabla([{"TICKER": p["symbol"], "ACCIONES": p["qty"], "ENTRADA": f"{float(p['avg_entry_price']):.2f}",
                "PRECIO": f"{float(p['current_price']):.2f}", "P&L": dinero(float(p["unrealized_pl"]))} for p in pos],
              ["TICKER", "ACCIONES", "ENTRADA", "PRECIO", "P&L"])
        return
    c = cargar_cuenta(cfg)
    for op in revisar_local(c):
        print(f"{'★' if op['motivo'] == 'target' else '♥'} {op['ticker']} cerrada por {op['motivo'].upper()} a "
              f"{op['salida']:.2f} · {dinero(op['pnl'])} ({op['r']:+.2f}R)")
    guardar_cuenta(c)
    if not c["posiciones"]:
        print("Sin posiciones abiertas.")
        return
    filas = []
    for p in c["posiciones"]:
        precio = precio_actual(p["ticker"])[0]
        largo = p["lado"] == "largo"
        pnl = (precio - p["entrada"]) * p["acciones"] * (1 if largo else -1)
        r = pnl / (abs(p["entrada"] - p["stop"]) * p["acciones"])
        filas.append({"TICKER": p["ticker"], "LADO": p["lado"], "ACC": p["acciones"], "ENTRADA": f"{p['entrada']:.2f}",
                      "PRECIO": f"{precio:.2f}", "STOP": p["stop"], "TARGET": p["target"], "P&L": dinero(pnl),
                      "R": f"{r:+.2f}"})
    tabla(filas, ["TICKER", "LADO", "ACC", "ENTRADA", "PRECIO", "STOP", "TARGET", "P&L", "R"])


def cmd_cerrar(a, cfg):
    tk = a.ticker.upper()
    if cfg["modo_paper"] == "alpaca":
        for o in alpaca("GET", f"/v2/orders?status=open&symbols={tk}&nested=true") or []:
            alpaca("DELETE", f"/v2/orders/{o['id']}")
        r = alpaca("DELETE", f"/v2/positions/{tk}")
        print(f"Cierre enviado a Alpaca PAPER: {r.get('id', '')} {tk}")
        return
    c = cargar_cuenta(cfg)
    revisar_local(c)
    pos = [p for p in c["posiciones"] if p["ticker"] == tk]
    if not pos:
        guardar_cuenta(c)
        salir(f"No hay posición abierta en {tk} (puede que ya la cerrara el stop o el target: mira historial).")
    precio = precio_actual(tk)[0]
    for p in pos:
        op = cerrar_local(c, p, precio, "manual", ahora_ny().isoformat(timespec="seconds"))
        print(f"✓ {tk} cerrada a {precio:.2f} · {dinero(op['pnl'])} ({op['r']:+.2f}R)")
    guardar_cuenta(c)


def cmd_cuenta(a, cfg):
    if cfg["modo_paper"] == "alpaca":
        acc = alpaca("GET", "/v2/account")
        print(f"Alpaca PAPER · equity {dinero(float(acc['equity']))} · efectivo {dinero(float(acc['cash']))} "
              f"· poder de compra {dinero(float(acc['buying_power']))}")
        return
    c = cargar_cuenta(cfg)
    revisar_local(c)
    guardar_cuenta(c)
    invertido = 0.0
    for p in c["posiciones"]:
        precio = precio_actual(p["ticker"])[0]
        largo = p["lado"] == "largo"
        invertido += p["acciones"] * p["entrada"] + (precio - p["entrada"]) * p["acciones"] * (1 if largo else -1)
    equity = c["efectivo"] + invertido
    realizado = sum(op["pnl"] for op in c["cerradas"])
    print(f"Cuenta PAPER local · equity {dinero(equity)} · efectivo {dinero(c['efectivo'])}")
    print(f"  Capital inicial {dinero(c['capital_inicial'])} · P&L realizado {dinero(realizado)} "
          f"· {len(c['posiciones'])} abiertas · {len(c['cerradas'])} cerradas · pérdida hoy {dinero(perdida_hoy(c))}")


def cmd_historial(a, cfg):
    if cfg["modo_paper"] == "alpaca":
        ords = alpaca("GET", "/v2/orders?status=closed&limit=50&nested=true")
        tabla([{"FECHA": (o.get("filled_at") or "")[:16], "TICKER": o["symbol"], "LADO": o["side"], "ACC": o["qty"],
                "PRECIO": o.get("filled_avg_price") or "-", "ESTADO": o["status"]} for o in ords],
              ["FECHA", "TICKER", "LADO", "ACC", "PRECIO", "ESTADO"])
        return
    c = cargar_cuenta(cfg)
    if not c["cerradas"]:
        print("Todavía no hay operaciones cerradas.")
        return
    tabla([{"FECHA": op["fecha"][:16], "TICKER": op["ticker"], "LADO": op["lado"], "ENTRADA": f"{op['entrada']:.2f}",
            "SALIDA": f"{op['salida']:.2f}", "MOTIVO": op["motivo"], "P&L": dinero(op["pnl"]), "R": f"{op['r']:+.2f}"}
           for op in sorted(c["cerradas"], key=lambda o: o["fecha"])[-30:]],
          ["FECHA", "TICKER", "LADO", "ENTRADA", "SALIDA", "MOTIVO", "P&L", "R"])


def cmd_reiniciar(a, cfg):
    if cfg["modo_paper"] == "alpaca":
        salir("La cuenta de Alpaca se reinicia desde su web (Paper Trading > Reset).")
    if not a.confirmar:
        salir("Esto borra la cuenta paper local. Repite con --confirmar.")
    if CUENTA.exists():
        CUENTA.rename(CUENTA.with_name(f"cuenta-{dt.datetime.now():%Y%m%d-%H%M%S}.json"))
    guardar_cuenta(cargar_cuenta(cfg))
    print(f"Cuenta paper reiniciada con {dinero(cfg['capital_paper'])} (la anterior quedó como copia).")


def main():
    p = argparse.ArgumentParser(description="Paper trading con stop y target obligatorios")
    sub = p.add_subparsers(dest="cmd", required=True)
    ab = sub.add_parser("abrir")
    ab.add_argument("ticker", nargs="?")
    ab.add_argument("--plan", action="store_true")
    ab.add_argument("--lado", choices=["largo", "corto"], default="largo")
    ab.add_argument("--acciones", type=int)
    ab.add_argument("--stop", type=float)
    ab.add_argument("--target", type=float)
    ab.add_argument("--setup", default="")
    sub.add_parser("posiciones")
    ce = sub.add_parser("cerrar")
    ce.add_argument("ticker")
    sub.add_parser("cuenta")
    sub.add_parser("historial")
    re_ = sub.add_parser("reiniciar")
    re_.add_argument("--confirmar", action="store_true")
    a = p.parse_args()
    requiere()
    cfg = cargar_config()
    {"abrir": cmd_abrir, "posiciones": cmd_posiciones, "cerrar": cmd_cerrar, "cuenta": cmd_cuenta,
     "historial": cmd_historial, "reiniciar": cmd_reiniciar}[a.cmd](a, cfg)
    print(f"\n[{cfg['modo_paper'].upper()}] {AVISO}")


if __name__ == "__main__":
    main()
