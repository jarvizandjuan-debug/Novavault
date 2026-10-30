"""Utilidades compartidas por las skills de la Mesa de Trading.

Todas las skills leen la configuración de ~/mesa-trading/config.json
(o de la carpeta indicada en la variable de entorno MESA_TRADING_HOME).
"""
import datetime as dt
import json
import logging
import math
import os
import sys
import time
import urllib.request
import warnings
from pathlib import Path

# Salida en UTF-8 también en Windows (símbolos como ★ ♥ █ en consolas cp1252)
for _flujo in (sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

HOME = Path(os.environ.get("MESA_TRADING_HOME", str(Path.home() / "mesa-trading"))).expanduser()
CONFIG = HOME / "config.json"
CACHE = HOME / "cache"
PLANES = HOME / "planes"
ULTIMO_PLAN = PLANES / "ultimo_plan.json"
SKILLS_DIR = Path(__file__).resolve().parents[2]

DEFAULTS = {
    "capital_paper": 25000.0,
    "riesgo_por_trade_pct": 1.0,
    "rr_minimo": 2.0,
    "max_posicion_pct": 25.0,
    "max_perdida_diaria_pct": 3.0,
    "modo_paper": "local",
    "universo": "sp500",
    "watchlist": ["SPY", "QQQ", "AAPL", "NVDA", "TSLA", "AMD", "META", "MSFT", "AMZN", "GOOGL"],
    "precio_min": 5.0,
    "volumen_medio_min": 1000000,
    "deslizamiento_pct": 0.02,
}

AVISO = "Solo educativo. No es asesoría financiera. Opera en paper trading."


# ---------------------------------------------------------------- config
def cargar_config():
    cfg = dict(DEFAULTS)
    if CONFIG.exists():
        try:
            cfg.update(json.loads(CONFIG.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            print(f"Aviso: {CONFIG} no es JSON válido; uso valores por defecto.", file=sys.stderr)
    return cfg


def guardar_config(cfg):
    HOME.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def guardar_plan(plan):
    PLANES.mkdir(parents=True, exist_ok=True)
    plan = dict(plan, guardado=dt.datetime.now().isoformat(timespec="seconds"))
    ULTIMO_PLAN.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    return ULTIMO_PLAN


def cargar_plan():
    if not ULTIMO_PLAN.exists():
        salir("No hay plan guardado. Primero usa la skill stop-y-target con --guardar.")
    return json.loads(ULTIMO_PLAN.read_text(encoding="utf-8"))


def salir(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


# ---------------------------------------------------------------- deps
def requiere():
    """Importa pandas, numpy y yfinance o explica cómo instalarlos."""
    try:
        import numpy  # noqa: F401
        import pandas  # noqa: F401
        import yfinance  # noqa: F401
    except ImportError as e:
        salir(f"Falta una librería ({e.name}). Instala con:  python3 -m pip install -r requirements.txt  "
              "(o vuelve a ejecutar el instalador de la Mesa de Trading).")
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    warnings.filterwarnings("ignore", module="yfinance")
    warnings.filterwarnings("ignore", category=FutureWarning)
    import numpy as np
    import pandas as pd
    import yfinance as yf
    return np, pd, yf


# ---------------------------------------------------------------- tiempo
def ny_tz():
    from zoneinfo import ZoneInfo
    return ZoneInfo("America/New_York")


def ahora_ny():
    return dt.datetime.now(ny_tz())


def mercado_abierto(t=None):
    t = t or ahora_ny()
    if t.weekday() >= 5:
        return False
    return dt.time(9, 30) <= t.time() < dt.time(16, 0)


def barras_restantes(intervalo_min=5, t=None):
    """Barras que quedan hasta el cierre (16:00 NY). Si el mercado está cerrado: sesión completa."""
    t = t or ahora_ny()
    if not mercado_abierto(t):
        return int(390 / intervalo_min)
    cierre = t.replace(hour=16, minute=0, second=0, microsecond=0)
    return max(1, int((cierre - t).total_seconds() // (intervalo_min * 60)))


# ---------------------------------------------------------------- datos
def _yf_download(yf, tickers, **kw):
    for intento in range(3):
        try:
            return yf.download(tickers, progress=False, threads=True, auto_adjust=True, **kw)
        except Exception as e:  # red inestable o límite de Yahoo
            if intento == 2:
                print(f"Aviso: fallo descargando {len(tickers)} tickers: {e}", file=sys.stderr)
                return None
            time.sleep(2 * (intento + 1))


def descargar_diario(tickers, periodo="1y", lote=150, progreso=True):
    """Velas diarias de muchos tickers. Devuelve {ticker: DataFrame(Open, High, Low, Close, Volume)}."""
    np, pd, yf = requiere()
    out = {}
    tickers = list(dict.fromkeys(tickers))
    for i in range(0, len(tickers), lote):
        chunk = tickers[i:i + lote]
        data = _yf_download(yf, chunk, period=periodo, interval="1d", group_by="ticker")
        if data is not None and not data.empty:
            if isinstance(data.columns, pd.MultiIndex):
                nivel0 = set(data.columns.get_level_values(0))
                for t in chunk:
                    if t in nivel0:
                        df = data[t].dropna(how="all")
                        if len(df):
                            out[t] = df[["Open", "High", "Low", "Close", "Volume"]]
            else:
                df = data.dropna(how="all")
                if len(df):
                    out[chunk[0]] = df[["Open", "High", "Low", "Close", "Volume"]]
        if progreso and len(tickers) > lote:
            print(f"  ...descargadas {min(i + lote, len(tickers))}/{len(tickers)}", file=sys.stderr, flush=True)
    return out


def descargar_intradia(ticker, periodo="5d", intervalo="5m", prepost=False):
    """Velas intradía (hora de Nueva York). 1m: máx. 7 días; 5m: máx. 60 días."""
    np, pd, yf = requiere()
    for intento in range(3):
        try:
            df = yf.Ticker(ticker).history(period=periodo, interval=intervalo, prepost=prepost, auto_adjust=False)
            break
        except Exception as e:
            if intento == 2:
                salir(f"No pude descargar datos de {ticker}: {e}")
            time.sleep(2 * (intento + 1))
    if df is None or df.empty:
        salir(f"Sin datos intradía para {ticker}. ¿El ticker es correcto?")
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.index = df.index.tz_convert("America/New_York")
    return df


def precio_actual(ticker):
    """Último precio disponible (incluye pre/post-market). Devuelve (precio, timestamp)."""
    df = descargar_intradia(ticker, periodo="2d", intervalo="1m", prepost=True)
    return float(df["Close"].iloc[-1]), df.index[-1]


def sesiones(df):
    """Agrupa velas intradía por día de mercado."""
    return [g for _, g in df.groupby(df.index.date)]


def atr(df, n=14):
    import pandas as pd
    pc = df["Close"].shift(1)
    tr = pd.concat([df["High"] - df["Low"], (df["High"] - pc).abs(), (df["Low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=max(2, n // 2)).mean()


def ema(serie, n):
    return serie.ewm(span=n, adjust=False).mean()


def vwap(sesion):
    tp = (sesion["High"] + sesion["Low"] + sesion["Close"]) / 3
    vol = sesion["Volume"].replace(0, float("nan")).fillna(0)
    acum = vol.cumsum().replace(0, float("nan"))
    return (tp * vol).cumsum() / acum


def pivotes(df, ventana=3):
    """Máximos y mínimos locales: listas de (timestamp, precio)."""
    h, l = df["High"].values, df["Low"].values
    altos, bajos = [], []
    for i in range(ventana, len(df) - ventana):
        if h[i] == max(h[i - ventana:i + ventana + 1]):
            altos.append((df.index[i], float(h[i])))
        if l[i] == min(l[i - ventana:i + ventana + 1]):
            bajos.append((df.index[i], float(l[i])))
    return altos, bajos


# ---------------------------------------------------------------- universos
def _descargar_texto(url, destino, max_horas):
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and time.time() - destino.stat().st_mtime < max_horas * 3600:
        return destino.read_text(encoding="utf-8")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 mesa-trading"})
    with urllib.request.urlopen(req, timeout=30) as r:
        txt = r.read().decode("utf-8", "replace")
    destino.write_text(txt, encoding="utf-8")
    return txt


def universo(nombre, cfg=None):
    """sp500 | todo-usa | watchlist | lista separada por comas | ruta a un .txt (un ticker por línea)."""
    cfg = cfg or cargar_config()
    nombre = (nombre or cfg.get("universo", "sp500")).strip()
    base = SKILLS_DIR / "escaner-graficas" / "universos"
    if nombre == "watchlist":
        return [t.upper() for t in cfg.get("watchlist", [])]
    if nombre == "sp500":
        try:
            txt = _descargar_texto("https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv",
                                   CACHE / "sp500.csv", 24 * 7)
            filas = [l.split(",")[0].strip() for l in txt.splitlines()[1:] if l.strip()]
            tick = [f.replace(".", "-") for f in filas if f]
            if len(tick) > 400:
                return tick
        except Exception:
            pass
        return [l.strip() for l in (base / "sp500.txt").read_text().splitlines() if l.strip()]
    if nombre in ("todo-usa", "todo", "usa"):
        tick = []
        for url, col, etf_col, test_col in (
            ("https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt", "Symbol", "ETF", "Test Issue"),
            ("https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt", "ACT Symbol", "ETF", "Test Issue"),
        ):
            try:
                txt = _descargar_texto(url, CACHE / url.rsplit("/", 1)[1], 24)
            except Exception as e:
                print(f"Aviso: no pude bajar {url}: {e}", file=sys.stderr)
                continue
            lineas = [l for l in txt.splitlines() if l and not l.startswith("File Creation")]
            cab = lineas[0].split("|")
            for l in lineas[1:]:
                c = dict(zip(cab, l.split("|")))
                s = c.get(col, "")
                if c.get(test_col) == "Y" or c.get(etf_col) == "Y":
                    continue
                if not s or any(ch in s for ch in "$^+=") or len(s) > 5:
                    continue
                tick.append(s.replace(".", "-"))
        if not tick:
            salir("No pude obtener la lista de todas las acciones de EE. UU.; usa --universo sp500.")
        return sorted(set(tick))
    p = Path(nombre).expanduser()
    if p.exists():
        return [l.strip().upper() for l in p.read_text().splitlines() if l.strip() and not l.startswith("#")]
    return [t.strip().upper() for t in nombre.split(",") if t.strip()]


# ---------------------------------------------------------------- salida
def tabla(filas, columnas, anchos=None):
    """Imprime una tabla de ancho fijo. filas: lista de dicts."""
    anchos = anchos or {c: max(len(c), *(len(str(f.get(c, ""))) for f in filas)) if filas else len(c) for c in columnas}
    print("  ".join(c.ljust(anchos[c]) for c in columnas))
    print("  ".join("-" * anchos[c] for c in columnas))
    for f in filas:
        print("  ".join(str(f.get(c, "")).ljust(anchos[c]) for c in columnas))


def pct(x, dec=1):
    return f"{x * 100:+.{dec}f}%"


def dinero(x):
    return f"${x:,.2f}"


def json_out(obj):
    def conv(o):
        if hasattr(o, "isoformat"):
            return o.isoformat()
        if hasattr(o, "item"):
            return o.item()
        return str(o)
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=conv))


def redondear_precio(p):
    """Centavos para precios >= $1, 4 decimales por debajo (como exigen los brókers)."""
    return round(p, 2) if p >= 1 else round(p, 4)


def es_nan(x):
    return x is None or (isinstance(x, float) and math.isnan(x))
