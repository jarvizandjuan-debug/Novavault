"""Configura la Mesa de Trading: capital paper, reglas de riesgo, watchlist y modo de ejecución.

Uso:
  configurar.py ver
  configurar.py inicializar [--capital 25000 --riesgo-pct 1 --rr-min 2 ...]
  configurar.py set CLAVE VALOR
  configurar.py verificar
"""
import argparse
import json
import os
import platform
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mesa_comun import AVISO, CONFIG, DEFAULTS, HOME, cargar_config, guardar_config, salir  # noqa: E402

CAMPOS = {
    "capital": ("capital_paper", float),
    "riesgo_pct": ("riesgo_por_trade_pct", float),
    "rr_min": ("rr_minimo", float),
    "max_posicion_pct": ("max_posicion_pct", float),
    "max_perdida_diaria_pct": ("max_perdida_diaria_pct", float),
    "modo_paper": ("modo_paper", str),
    "universo": ("universo", str),
    "precio_min": ("precio_min", float),
    "volumen_min": ("volumen_medio_min", int),
}


def validar(cfg):
    errores = []
    if cfg["modo_paper"] not in ("local", "alpaca"):
        errores.append("modo_paper debe ser 'local' o 'alpaca'.")
    if not 0 < cfg["riesgo_por_trade_pct"] <= 5:
        errores.append("riesgo_por_trade_pct debe estar entre 0 y 5 (recomendado 0.5–1).")
    if cfg["rr_minimo"] < 1:
        errores.append("rr_minimo debe ser al menos 1.")
    if cfg["capital_paper"] <= 0:
        errores.append("capital_paper debe ser positivo.")
    if not 0 < cfg["max_posicion_pct"] <= 100:
        errores.append("max_posicion_pct debe estar entre 0 y 100.")
    return errores


def mostrar(cfg):
    print(f"Configuración ({CONFIG}):")
    for k, v in cfg.items():
        if "secret" in k or "key" in k:
            v = "********"
        print(f"  {k}: {v}")
    print(f"\n{AVISO}")


def cmd_inicializar(a):
    cfg = cargar_config()
    for arg, (clave, tipo) in CAMPOS.items():
        v = getattr(a, arg)
        if v is not None:
            cfg[clave] = tipo(v)
    if a.watchlist:
        cfg["watchlist"] = [t.strip().upper() for t in a.watchlist.split(",") if t.strip()]
    errores = validar(cfg)
    if errores:
        salir(" ".join(errores))
    guardar_config(cfg)
    for sub in ("planes", "paper", "diario", "cache", "backtests"):
        (HOME / sub).mkdir(parents=True, exist_ok=True)
    print("Mesa de Trading lista.\n")
    mostrar(cfg)


def cmd_set(a):
    cfg = cargar_config()
    clave = a.clave
    if clave not in cfg and clave not in DEFAULTS:
        salir(f"Clave desconocida: {clave}. Claves válidas: {', '.join(DEFAULTS)}")
    actual = DEFAULTS.get(clave, cfg.get(clave))
    if isinstance(actual, list):
        valor = [t.strip().upper() for t in a.valor.split(",") if t.strip()]
    elif isinstance(actual, bool):
        valor = a.valor.lower() in ("1", "true", "si", "sí", "yes")
    elif isinstance(actual, int):
        valor = int(float(a.valor))
    elif isinstance(actual, float):
        valor = float(a.valor)
    else:
        valor = a.valor
    cfg[clave] = valor
    errores = validar(cfg)
    if errores:
        salir(" ".join(errores))
    guardar_config(cfg)
    print(f"{clave} = {valor}")


def cmd_verificar(a):
    ok = True
    print(f"Python {platform.python_version()} ({sys.executable})")
    if sys.version_info < (3, 9):
        print("  ✗ Necesitas Python 3.9 o superior.")
        ok = False
    for mod in ("numpy", "pandas", "yfinance"):
        try:
            m = __import__(mod)
            print(f"  ✓ {mod} {getattr(m, '__version__', '')}")
        except ImportError:
            print(f"  ✗ falta {mod}  →  python3 -m pip install -r requirements.txt")
            ok = False
    print(f"  {'✓' if CONFIG.exists() else '✗'} config: {CONFIG}")
    if ok:
        from mesa_comun import descargar_diario
        d = descargar_diario(["SPY"], periodo="5d", progreso=False)
        if "SPY" in d:
            print(f"  ✓ datos de mercado: SPY cierre {d['SPY']['Close'].iloc[-1]:.2f}")
        else:
            print("  ✗ no pude descargar datos de Yahoo Finance (¿sin internet?)")
            ok = False
    cfg = cargar_config()
    if cfg["modo_paper"] == "alpaca":
        key = os.environ.get("APCA_API_KEY_ID") or cfg.get("alpaca_key_id")
        sec = os.environ.get("APCA_API_SECRET_KEY") or cfg.get("alpaca_secret_key")
        if not key or not sec:
            print("  ✗ modo alpaca sin claves: exporta APCA_API_KEY_ID y APCA_API_SECRET_KEY (cuenta PAPER).")
            ok = False
        else:
            req = urllib.request.Request("https://paper-api.alpaca.markets/v2/account",
                                         headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec})
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    acc = json.loads(r.read())
                print(f"  ✓ Alpaca PAPER conectado: equity ${float(acc['equity']):,.2f}")
            except Exception as e:
                print(f"  ✗ Alpaca PAPER no responde o claves inválidas: {e}")
                ok = False
    print("\nTodo listo." if ok else "\nHay cosas por arreglar (ver arriba).")
    sys.exit(0 if ok else 1)


def main():
    p = argparse.ArgumentParser(description="Configura la Mesa de Trading")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ver")
    i = sub.add_parser("inicializar")
    i.add_argument("--capital", type=float)
    i.add_argument("--riesgo-pct", dest="riesgo_pct", type=float)
    i.add_argument("--rr-min", dest="rr_min", type=float)
    i.add_argument("--max-posicion-pct", dest="max_posicion_pct", type=float)
    i.add_argument("--max-perdida-diaria-pct", dest="max_perdida_diaria_pct", type=float)
    i.add_argument("--modo-paper", dest="modo_paper", choices=["local", "alpaca"])
    i.add_argument("--universo")
    i.add_argument("--precio-min", dest="precio_min", type=float)
    i.add_argument("--volumen-min", dest="volumen_min", type=int)
    i.add_argument("--watchlist", help="Tickers separados por comas")
    s = sub.add_parser("set")
    s.add_argument("clave")
    s.add_argument("valor")
    sub.add_parser("verificar")
    a = p.parse_args()
    if a.cmd == "ver":
        mostrar(cargar_config())
    elif a.cmd == "inicializar":
        cmd_inicializar(a)
    elif a.cmd == "set":
        cmd_set(a)
    else:
        cmd_verificar(a)


if __name__ == "__main__":
    main()
