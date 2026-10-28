"""C3 (28/10/2026): ¿cuándo y por qué pierde 迪亚马特 (91 % de aciertos), y qué preventiva evita esas pérdidas?

Pedido de Nicolás: «mira cuándo perdió y por qué perdió, pon una preventiva para cuando pierde y apuesta solo cuando sí funciona».

Para cada una de sus posiciones (historial público, datos/copy/historial-<id>.json) se bajan las velas de 5 m de Binance futuros
de las 24 h anteriores a la entrada y de toda la operación. Se mide:
- antes de entrar, en su lado: cuánto se movió la moneda en 1 h, 4 h y 24 h; distancia al máximo (o mínimo) de 24 h; volumen
  de la última hora frente a la media de 24 h;
- durante la operación: lo máximo que fue en contra (MAE) y a favor (MFE), en % del precio.
Preventivas probadas (elegidas en la PRIMERA mitad de su historial y comprobadas en la SEGUNDA):
- filtro de entrada: no entrar si la medida que más separa perdedoras de ganadoras pasa del umbral fijado en la primera mitad;
- stop: cortar cuando el precio va X % en contra (con las velas de 5 m; si en una vela se tocan el stop y el cierre real, cuenta el stop).
Copia en papel con 40.000 COP y 10 % de margen por copia, con y sin preventiva.
Uso: python -I c3_perdidas_diamat.py > c3_perdidas_diamat.txt"""
import json
import os
import sys
import time
import urllib.request

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(os.environ.get("TRADER_DATOS") or os.path.join(AQUI, "..", "..", "datos"), "copy")
PID = "5240448882690502145"
H = {"User-Agent": "Mozilla/5.0"}
COP = 3177.85


def velas(simbolo, ini_ms, fin_ms):
    ruta = os.path.join(DATOS, "velas5m", f"{simbolo}-{ini_ms}-{fin_ms}.json")
    if os.path.exists(ruta):
        return json.load(open(ruta, encoding="utf-8"))
    out, t = [], ini_ms
    while t < fin_ms:
        u = f"https://fapi.binance.com/fapi/v1/klines?symbol={simbolo}&interval=5m&startTime={t}&endTime={fin_ms}&limit=1500"
        try:
            x = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=20).read())
        except Exception:
            return None
        if not x:
            break
        out += [[int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])] for k in x]
        t = int(x[-1][0]) + 300000
        time.sleep(0.15)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    json.dump(out, open(ruta, "w"))
    return out


def medir(p):
    lado = 1 if p.get("side") == "Long" else -1
    ab, ce = int(p["opened"]), int(p["closed"])
    v = velas(p["symbol"], ab - 25 * 3600000, ce + 300000)
    if not v or len(v) < 60:
        return None
    t = np.array([x[0] for x in v])
    o, h, l, c, vol = (np.array([x[k] for x in v]) for k in (1, 2, 3, 4, 5))
    i = int(np.searchsorted(t, ab, side="right")) - 1  # vela de la entrada
    if i < 289:
        return None
    e = float(p.get("avgCost") or c[i])
    mov = lambda n: lado * (c[i - 1] / c[i - 1 - n] - 1) * 100  # noqa: E731  (n velas de 5 m)
    hi24, lo24 = h[i - 288:i].max(), l[i - 288:i].min()
    dist = (hi24 / e - 1) * 100 if lado < 0 else (e / lo24 - 1) * 100  # cuánto le falta al máximo (corto) o al mínimo (largo)
    vr = vol[i - 12:i].mean() / max(1e-12, vol[i - 288:i].mean())
    j = int(np.searchsorted(t, ce, side="right"))
    dentro_h, dentro_l = h[i:j + 1], l[i:j + 1]
    mae = ((dentro_h.max() / e - 1) * 100 if lado < 0 else (1 - dentro_l.min() / e) * 100) if len(dentro_h) else 0.0
    mfe = ((1 - dentro_l.min() / e) * 100 if lado < 0 else (dentro_h.max() / e - 1) * 100) if len(dentro_h) else 0.0
    # camino para el stop: lo máximo en contra vela a vela
    camino = [((hh / e - 1) * 100 if lado < 0 else (1 - ll / e) * 100) for hh, ll in zip(dentro_h, dentro_l)]
    return {"mov1h": mov(12), "mov4h": mov(48), "mov24h": mov(287), "dist": dist, "vol": vr, "mae": mae, "mfe": mfe,
            "camino": camino, "roi": float(p.get("roi") or 0) * 100, "lev": float(p.get("leverage") or 1), "lado": lado,
            "t": ab, "simbolo": p["symbol"]}


def copiar(ops, f=0.10, stop=None):
    E, pico, cm = 40000 / COP, 40000 / COP, 0.0
    for o in sorted(ops, key=lambda x: x["t"]):
        m = f * E
        roi = o["roi"]
        if stop is not None and any(x >= stop for x in o["camino"]):
            roi = -stop * o["lev"] - 0.1 * o["lev"]  # salida en el stop, con su apalancamiento
        g = max(m * roi / 100 - m * o["lev"] * 0.0015, -m)
        E += g
        pico = max(pico, E)
        cm = max(cm, 1 - E / pico)
    return E * COP, cm


def main():
    pos = json.load(open(os.path.join(DATOS, f"historial-{PID}.json"), encoding="utf-8"))
    pos = [p for p in pos if p.get("closed") and p.get("opened")]
    print(f"C3 · 迪亚马特: {len(pos)} posiciones. Midiendo el mercado antes y durante cada una (velas de 5 m de Binance)…")
    ops = [m for m in (medir(p) for p in pos) if m]
    print(f"   con velas completas: {len(ops)} de {len(pos)}\n")
    per = [o for o in ops if o["roi"] < 0]
    gan = [o for o in ops if o["roi"] > 0]
    print(f"PERDEDORAS: {len(per)} · GANADORAS: {len(gan)} · lado de las perdedoras: "
          f"{sum(1 for o in per if o['lado'] < 0)} cortos, {sum(1 for o in per if o['lado'] > 0)} largos")
    for o in sorted(per, key=lambda x: x["roi"])[:10]:
        print(f"   {o['simbolo']:12s} {'corto' if o['lado'] < 0 else 'largo'} {o['lev']:.0f}× · resultado {o['roi']:+.0f} % del margen · "
              f"antes: 1 h {o['mov1h']:+.1f} %, 4 h {o['mov4h']:+.1f} %, 24 h {o['mov24h']:+.1f} % · en contra máx {o['mae']:.1f} %")
    print("\nQUÉ LAS SEPARA (mediana perdedoras frente a ganadoras):")
    claves = ["mov1h", "mov4h", "mov24h", "dist", "vol", "mae", "mfe", "lev"]
    for k in claves:
        a, b = np.median([o[k] for o in per]), np.median([o[k] for o in gan])
        print(f"   {k:7s} perdedoras {a:+8.2f} · ganadoras {b:+8.2f}")
    # preventivas elegidas en la primera mitad, comprobadas en la segunda
    ops.sort(key=lambda x: x["t"])
    mitad = len(ops) // 2
    A, B = ops[:mitad], ops[mitad:]
    print(f"\nPREVENTIVAS (elegidas en las primeras {len(A)} operaciones, comprobadas en las últimas {len(B)}):")
    mejor = None
    for k in ("mov1h", "mov4h", "mov24h", "dist", "vol"):
        for q in (60, 70, 80, 90):
            u = np.percentile([o[k] for o in A], q)
            for signo in (1, -1):
                ok = [o for o in A if (o[k] <= u if signo > 0 else o[k] >= u)]
                if len(ok) < 0.6 * len(A):
                    continue
                E, _ = copiar(ok)
                if mejor is None or E > mejor[0]:
                    mejor = (E, k, q, signo, u)
    E_a, k, q, signo, u = mejor
    regla = f"no entrar si {k} {'>' if signo > 0 else '<'} {u:.2f}"
    filtro = lambda o: (o[k] <= u if signo > 0 else o[k] >= u)  # noqa: E731
    for nombre, grupo in (("primera mitad", A), ("segunda mitad", B)):
        sin, cm0 = copiar(grupo)
        con, cm1 = copiar([o for o in grupo if filtro(o)])
        print(f"   filtro «{regla}» · {nombre}: sin preventiva {sin:,.0f} COP (caída {cm0 * 100:.0f} %) · con preventiva {con:,.0f} COP (caída {cm1 * 100:.0f} %)")
    mejor_stop = max((copiar(A, stop=s)[0], s) for s in (5, 10, 15, 20, 30, 50))[1]
    for nombre, grupo in (("primera mitad", A), ("segunda mitad", B)):
        sin, cm0 = copiar(grupo)
        con, cm1 = copiar(grupo, stop=mejor_stop)
        print(f"   stop a {mejor_stop} % en contra · {nombre}: sin stop {sin:,.0f} COP (caída {cm0 * 100:.0f} %) · con stop {con:,.0f} COP (caída {cm1 * 100:.0f} %)")
    todo, cm = copiar(ops)
    todo_p, cmp_ = copiar([o for o in ops if filtro(o)], stop=mejor_stop)
    print(f"\nTODO SU HISTORIAL (10 % de margen por copia): sin preventivas {todo:,.0f} COP (caída {cm * 100:.0f} %) · "
          f"con filtro y stop {todo_p:,.0f} COP (caída {cmp_ * 100:.0f} %)")


if __name__ == "__main__":
    main()
