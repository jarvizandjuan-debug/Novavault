"""TIME MACHINE: simula el resto del día miles de veces (10,000 por defecto) para estimar la
probabilidad de tocar el target antes que el stop.

Método: bootstrap por bloques de velas reales de 5 minutos de los últimos 60 días del propio
ticker (mantiene volatilidad, colas gordas y algo de inercia), reescalado a la volatilidad
reciente y sin deriva direccional. En cada vela simulada se revisan máximo y mínimo: si en la misma vela se tocan stop
y target, cuenta como stop (criterio conservador).

Ejemplos:
  time_machine.py --plan                         # usa el último plan de stop-y-target
  time_machine.py NVDA --entrada 214 --stop 211.5 --target 219
  time_machine.py TSLA --entrada 450 --stop 444 --target 462 --barras 40 --sims 20000
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "configurar-mesa" / "scripts"))
from mesa_comun import (AVISO, barras_restantes, cargar_plan, descargar_intradia, dinero, json_out,  # noqa: E402
                        mercado_abierto, precio_actual, requiere, salir, sesiones)


def preparar_velas(df, np):
    """Por sesión: log-retorno de cierre y excursiones de máximo/mínimo respecto al cierre previo."""
    bloques = []
    for s in sesiones(df):
        if len(s) < 12:
            continue
        o, h, l, c = (s[k].values.astype(float) for k in ("Open", "High", "Low", "Close"))
        previo = np.concatenate([[o[0]], c[:-1]])
        ok = (previo > 0) & (h > 0) & (l > 0) & (c > 0)
        if not ok.all():
            continue
        rc = np.log(c / previo)
        rh = np.maximum(np.log(h / previo), np.maximum(rc, 0))
        rl = np.minimum(np.log(l / previo), np.minimum(rc, 0))
        bloques.append(np.stack([rc, rh, rl], axis=1))
    return bloques


def simular(bloques, n_barras, n_sims, bloque, escala, entrada, stop, target, largo, np, semilla=None):
    rng = np.random.default_rng(semilla)
    plano = np.concatenate(bloques)
    # índices válidos de inicio de bloque (sin cruzar de un día a otro)
    inicios, off = [], 0
    for b in bloques:
        if len(b) >= bloque:
            inicios.extend(range(off, off + len(b) - bloque + 1))
        off += len(b)
    inicios = np.array(inicios)
    k = -(-n_barras // bloque)
    sel = inicios[rng.integers(0, len(inicios), size=(n_sims, k))]
    idx = (sel[:, :, None] + np.arange(bloque)[None, None, :]).reshape(n_sims, -1)[:, :n_barras]
    r = plano[idx] * escala  # (sims, barras, 3)
    logp_prev = np.log(entrada) + np.concatenate([np.zeros((n_sims, 1)), np.cumsum(r[:, :-1, 0], axis=1)], axis=1)
    alto = np.exp(logp_prev + r[:, :, 1])
    bajo = np.exp(logp_prev + r[:, :, 2])
    cierre_final = np.exp(logp_prev[:, -1] + r[:, -1, 0])
    if largo:
        toca_t, toca_s = alto >= target, bajo <= stop
    else:
        toca_t, toca_s = bajo <= target, alto >= stop
    nunca = n_barras + 1
    primer_t = np.where(toca_t.any(1), toca_t.argmax(1), nunca)
    primer_s = np.where(toca_s.any(1), toca_s.argmax(1), nunca)
    gana = primer_t < primer_s
    pierde = (primer_s <= primer_t) & (primer_s < nunca)
    ninguno = ~gana & ~pierde
    return gana, pierde, ninguno, primer_t, primer_s, cierre_final


def main():
    p = argparse.ArgumentParser(description="Time Machine: simula el día miles de veces")
    p.add_argument("ticker", nargs="?")
    p.add_argument("--plan", action="store_true", help="Usa el último plan guardado por stop-y-target")
    p.add_argument("--lado", choices=["largo", "corto"], default="largo")
    p.add_argument("--entrada", type=float)
    p.add_argument("--stop", type=float)
    p.add_argument("--target", type=float)
    p.add_argument("--acciones", type=int)
    p.add_argument("--sims", type=int, default=10000)
    p.add_argument("--barras", type=int, help="Velas de 5m a simular (por defecto: hasta el cierre)")
    p.add_argument("--bloque", type=int, default=6, help="Velas por bloque del bootstrap (6 = 30 min)")
    p.add_argument("--sin-escala", action="store_true", help="No reescalar a la volatilidad reciente")
    p.add_argument("--con-tendencia", action="store_true",
                   help="Conserva la deriva de los últimos 60 días (por defecto se neutraliza)")
    p.add_argument("--semilla", type=int)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    np, pd, yf = requiere()

    if a.plan:
        pl = cargar_plan()
        tk, lado, entrada, stop, target = pl["ticker"], pl["lado"], pl["entrada"], pl["stop"], pl["target"]
        acciones = a.acciones or pl.get("acciones")
    else:
        if not a.ticker or a.stop is None or a.target is None:
            p.error("indica TICKER --stop y --target (o usa --plan)")
        tk, lado, stop, target, acciones = a.ticker.upper(), a.lado, a.stop, a.target, a.acciones
        entrada = a.entrada if a.entrada else precio_actual(tk)[0]
    largo = lado == "largo"
    if largo and not (stop < entrada < target):
        salir("Para un largo se necesita stop < entrada < target.")
    if not largo and not (target < entrada < stop):
        salir("Para un corto se necesita target < entrada < stop.")

    df = descargar_intradia(tk, periodo="60d", intervalo="5m")
    bloques = preparar_velas(df, np)
    if len(bloques) < 5:
        salir("Hacen falta al menos 5 sesiones de historia intradía.")
    n_barras = a.barras or barras_restantes(5)
    n_barras = max(1, min(n_barras, 78))
    bloque = max(1, min(a.bloque, n_barras))

    # sin sesgo direccional: se quita la deriva media para no "regalar" la tendencia pasada
    if not a.con_tendencia:
        mu = float(np.concatenate(bloques)[:, 0].mean())
        bloques = [b - mu for b in bloques]
    # volatilidad reciente (últimas 5 sesiones) frente a la de 60 días
    vol_total = float(np.concatenate(bloques)[:, 0].std())
    vol_rec = float(np.concatenate(bloques[-5:])[:, 0].std())
    escala = 1.0 if a.sin_escala or vol_total == 0 else float(np.clip(vol_rec / vol_total, 0.5, 2.5))

    gana, pierde, ninguno, pt, ps, cierre = simular(bloques, n_barras, a.sims, bloque, escala, entrada, stop,
                                                    target, largo, np, a.semilla)
    riesgo = abs(entrada - stop)
    r_target = abs(target - entrada) / riesgo
    r_cierre = ((cierre - entrada) if largo else (entrada - cierre)) / riesgo
    r_final = np.where(gana, r_target, np.where(pierde, -1.0, r_cierre))
    p_t, p_s, p_n = gana.mean(), pierde.mean(), ninguno.mean()
    ev = float(r_final.mean())
    res = {
        "ticker": tk, "lado": lado, "entrada": entrada, "stop": stop, "target": target,
        "simulaciones": a.sims, "barras_5m": n_barras, "sesiones_historia": len(bloques),
        "escala_volatilidad": round(escala, 2), "con_tendencia": a.con_tendencia,
        "prob_target": round(float(p_t), 4), "prob_stop": round(float(p_s), 4), "prob_ninguno": round(float(p_n), 4),
        "r_target": round(r_target, 2), "esperanza_R": round(ev, 3),
        "breakeven_winrate": round(1 / (1 + r_target), 4),
        "min_mediana_a_target": int(np.median(pt[gana]) * 5 + 5) if gana.any() else None,
        "min_mediana_a_stop": int(np.median(ps[pierde]) * 5 + 5) if pierde.any() else None,
        "percentiles_R": {q: round(float(np.percentile(r_final, q)), 2) for q in (5, 25, 50, 75, 95)},
    }
    if acciones:
        res["acciones"] = acciones
        res["esperanza_usd"] = round(ev * riesgo * acciones, 2)
    if a.json:
        json_out(res)
        return

    print("🌀 TIME MACHINE " + "·" * 30)
    print(f"{tk} {'LARGO' if largo else 'CORTO'} · entrada {entrada:.2f} · stop {stop:.2f} · target {target:.2f} ({r_target:.2f}R)")
    momento = "hasta el cierre" if mercado_abierto() else "sesión completa: mercado cerrado"
    print(f"Simulando {a.sims:,} veces {n_barras} velas de 5m ({momento}) con {len(bloques)} días reales "
          f"· volatilidad x{escala:.2f}")
    print()
    barra = lambda x: "█" * int(round(x * 40))  # noqa: E731
    print(f"  ★ TARGET primero  {p_t * 100:5.1f}%  {barra(p_t)}")
    print(f"  ♥ STOP primero    {p_s * 100:5.1f}%  {barra(p_s)}")
    print(f"  · Ninguno (cierre){p_n * 100:5.1f}%  {barra(p_n)}")
    print()
    print(f"  Esperanza: {ev:+.2f}R por trade" + (f"  ({dinero(res['esperanza_usd'])} con {acciones} acciones)" if acciones else ""))
    print(f"  Win rate necesario para no perder con {r_target:.2f}R: {res['breakeven_winrate'] * 100:.0f}%")
    if res["min_mediana_a_target"]:
        print(f"  Tiempo mediano hasta el target: ~{res['min_mediana_a_target']} min")
    if res["min_mediana_a_stop"]:
        print(f"  Tiempo mediano hasta el stop:   ~{res['min_mediana_a_stop']} min")
    pr = res["percentiles_R"]
    print(f"  Resultado en R (p5/p25/p50/p75/p95): {pr[5]:+.2f} / {pr[25]:+.2f} / {pr[50]:+.2f} / {pr[75]:+.2f} / {pr[95]:+.2f}")
    print()
    if ev > 0.1:
        print("  Lectura: con la volatilidad real de este ticker, el plan tiene esperanza positiva.")
    elif ev > -0.1:
        print("  Lectura: esperanza cercana a cero; el plan depende de que tu setup tenga ventaja real.")
    else:
        print("  Lectura: esperanza negativa con movimientos aleatorios: ajusta stop/target o espera mejor precio.")
    print("  Ojo: la simulación no conoce tu setup ni las noticias; mide si stop y target son razonables "
          "para cómo se mueve esta acción.")
    print(f"\n{AVISO}")


if __name__ == "__main__":
    main()
