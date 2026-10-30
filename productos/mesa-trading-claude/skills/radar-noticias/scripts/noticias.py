"""Radar de noticias: titulares recientes por ticker, clasificados por tipo de catalizador,
sesgo (+/-) e impacto probable.

Ejemplos:
  noticias.py NVDA
  noticias.py NCLH,CVNA,TXT --horas 24
  noticias.py --escaneo          # tickers del último escaneo
  noticias.py --watchlist --json
"""
import argparse
import datetime as dt
import email.utils
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "configurar-mesa" / "scripts"))
from mesa_comun import AVISO, HOME, cargar_config, json_out, requiere  # noqa: E402

# (categoría, impacto, patrones)
CATEGORIAS = [
    ("RESULTADOS", "ALTO", r"earnings|quarterly results|\bq[1-4]\b|eps|revenue|beats?|miss(es|ed)?|resultados|ganancias"),
    ("GUÍA", "ALTO", r"guidance|outlook|(raises?|lifts?|cuts?|lowers?).{0,25}(view|forecast)|previsi"),
    ("FDA / CLÍNICO", "ALTO", r"\bfda\b|approval|approved|phase [123]|trial|clinical|ensayo"),
    ("FUSIÓN / COMPRA", "ALTO", r"acquir|merger|buyout|takeover|agrees? to buy|deal to buy|adquisici|fusi[oó]n"),
    ("CONTRATO", "ALTO", r"contract|awarded|partnership|agreement|order from|contrato|alianza"),
    ("DILUCIÓN", "ALTO", r"offering|dilut|priced .{0,30}shares|at-the-market|private placement|emisi[oó]n"),
    ("LEGAL / REGULADOR", "ALTO", r"sec (probe|charges|investigation)|investigation|probe|lawsuit|subpoena|antitrust|recall|demanda|investigaci"),
    ("QUIEBRA", "ALTO", r"bankrupt|chapter 11|delist|going concern|quiebra"),
    ("ANALISTAS", "MEDIO", r"upgrade|downgrade|price target|initiat|overweight|underweight|outperform|rating"),
    ("DIRECTIVOS", "MEDIO", r"\bceo\b|\bcfo\b|resign|steps down|appoint|director"),
    ("RECOMPRA / DIVIDENDO", "MEDIO", r"buyback|repurchase|dividend|split|recompra|dividendo"),
    ("SECTOR / MACRO", "BAJO", r"fed\b|inflation|tariff|rates|sector|market|stocks to|wall street"),
]
POSITIVAS = r"beat|raises?|record|approv|award|wins?|surge|soar|jump|rall(y|ies)|upgrade|strong|tops|exceed|boost|bullish|sube|dispara"
NEGATIVAS = r"miss|cuts?|lower|reject|downgrade|offering|dilut|plunge|tumble|falls?|drop|sink|slump|lawsuit|probe|recall|bankrupt|weak|warn|bearish|cae|desplom"


def clasificar(titulo):
    t = titulo.lower()
    cat, imp = "GENERAL", "BAJO"
    for c, i, pat in CATEGORIAS:
        if re.search(pat, t):
            cat, imp = c, i
            break
    pos = len(re.findall(POSITIVAS, t))
    neg = len(re.findall(NEGATIVAS, t))
    sesgo = "+" if pos > neg else ("-" if neg > pos else "=")
    return cat, imp, sesgo


def _fecha(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return dt.datetime.fromtimestamp(x, dt.timezone.utc)
    try:
        return dt.datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    except ValueError:
        try:
            return email.utils.parsedate_to_datetime(str(x))
        except (TypeError, ValueError):
            return None


def de_yahoo(ticker):
    np, pd, yf = requiere()
    items = []
    try:
        crudos = yf.Ticker(ticker).news or []
    except Exception:
        crudos = []
    if not crudos:
        try:
            crudos = [n for n in yf.Search(ticker, news_count=15).news
                      if not n.get("relatedTickers") or ticker in n.get("relatedTickers", [])]
        except Exception:
            crudos = []
    for n in crudos:
        c = n.get("content", n)
        titulo = c.get("title")
        if not titulo:
            continue
        prov = c.get("provider", {}).get("displayName") if isinstance(c.get("provider"), dict) else c.get("publisher")
        url = (c.get("canonicalUrl") or {}).get("url") if isinstance(c.get("canonicalUrl"), dict) else c.get("link")
        items.append({"titulo": titulo, "fuente": prov or "Yahoo Finance", "url": url,
                      "fecha": _fecha(c.get("pubDate") or c.get("providerPublishTime"))})
    return items


def de_google(ticker):
    q = urllib.parse.quote(f"{ticker} stock")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 mesa-trading"})
        with urllib.request.urlopen(req, timeout=20) as r:
            root = ET.fromstring(r.read())
    except Exception:
        return []
    items = []
    for it in root.iter("item"):
        titulo = (it.findtext("title") or "").strip()
        fuente = it.findtext("source") or ""
        if fuente and titulo.endswith(" - " + fuente):
            titulo = titulo[: -len(fuente) - 3]
        items.append({"titulo": titulo, "fuente": fuente or "Google News", "url": it.findtext("link"),
                      "fecha": _fecha(it.findtext("pubDate"))})
    return items


def radar(ticker, horas, maximo):
    vistos, items = set(), []
    for n in de_yahoo(ticker) + de_google(ticker):
        clave = re.sub(r"\W+", "", n["titulo"].lower())[:60]
        if clave in vistos:
            continue
        vistos.add(clave)
        items.append(n)
    ahora = dt.datetime.now(dt.timezone.utc)
    limite = ahora - dt.timedelta(hours=horas)
    items = [n for n in items if n["fecha"] is None or n["fecha"] >= limite]
    for n in items:
        n["categoria"], n["impacto"], n["sesgo"] = clasificar(n["titulo"])
        n["hace"] = f"{(ahora - n['fecha']).total_seconds() / 3600:.0f}h" if n["fecha"] else "?"
    orden = {"ALTO": 0, "MEDIO": 1, "BAJO": 2}
    items.sort(key=lambda n: (orden[n["impacto"]], -(n["fecha"].timestamp() if n["fecha"] else 0)))
    return items[:maximo]


def main():
    p = argparse.ArgumentParser(description="Radar de noticias y catalizadores")
    p.add_argument("tickers", nargs="?", help="Tickers separados por comas")
    p.add_argument("--watchlist", action="store_true")
    p.add_argument("--escaneo", action="store_true", help="Usa los tickers del último escaneo")
    p.add_argument("--horas", type=float, default=36)
    p.add_argument("--max", type=int, default=8)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    if a.watchlist:
        tickers = cargar_config()["watchlist"]
    elif a.escaneo:
        f = HOME / "cache" / "ultimo_escaneo.txt"
        if not f.exists():
            print("ERROR: no hay escaneo previo; usa la skill escaner-graficas primero.", file=sys.stderr)
            sys.exit(1)
        tickers = f.read_text().split()[:10]
    elif a.tickers:
        tickers = [t.strip().upper() for t in a.tickers.split(",") if t.strip()]
    else:
        p.error("indica tickers, --watchlist o --escaneo")
    salida = {}
    for t in tickers:
        salida[t] = radar(t, a.horas, a.max)
    if a.json:
        json_out(salida)
        return
    for t, items in salida.items():
        altos = [n for n in items if n["impacto"] == "ALTO"]
        print(f"\n=== {t} · {len(items)} titulares en {a.horas:g}h · {len(altos)} de impacto ALTO ===")
        if not items:
            print("  Sin noticias recientes: el movimiento (si lo hay) puede ser técnico o sectorial.")
        for n in items:
            print(f"  [{n['impacto']:<5}] ({n['sesgo']}) {n['categoria']:<18} hace {n['hace']:>4} · {n['fuente']}")
            print(f"           {n['titulo']}")
    print(f"\nLa clasificación es automática por palabras clave: confirma leyendo la noticia. {AVISO}")


if __name__ == "__main__":
    main()
