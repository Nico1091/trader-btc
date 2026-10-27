"""Paquete de velas de un ciclo, para que Claude analice CADA vela cerrada él mismo (sesión larga local, 27/10/2026).

Solo biblioteca estándar. Fuente por defecto: futuros USDⓈ-M de Binance (la misma del backtest; desde el PC de
Nicolás la API responde, desde la nube da 451). Si Binance falla, Coinbase BTC-USD, y lo dice.

Por cada marco (1 m, 5 m, 15 m, 1 h, 4 h, 1 d) imprime las últimas velas CERRADAS con, en cada una:
hora, apertura, máximo, mínimo, cierre, cambio %, cuerpo y mechas en % del rango, rango frente al ATR14 del marco,
volumen frente a su media de 20, cierre frente a la EMA 20 del marco y los patrones del curso que terminan en ella.
No decide nada: es la materia prima para la lectura vela por vela.

Uso:
  python -I consolidacion/velas_ciclo.py                       -> paquete ahora
  python -I consolidacion/velas_ciclo.py --esperar             -> espera al próximo cierre de 15 m (como mucho
                                                                  --max-espera s, 540 por defecto) y luego imprime
  python -I consolidacion/velas_ciclo.py --fuente coinbase     -> fuerza Coinbase
  python -I consolidacion/velas_ciclo.py --marcos 15m,1h --n 30"""
import argparse
import datetime as dt
import json
import math
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patrones_std  # noqa: E402

UTC = dt.timezone.utc
COL = dt.timezone(dt.timedelta(hours=-5))
SEG = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}
N_POR_DEFECTO = {"1m": 15, "5m": 12, "15m": 16, "1h": 24, "4h": 12, "1d": 10}


def _json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "velas-ciclo"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def binance(marco, n):
    """Velas [t_apertura_s, o, h, l, c, v] de futuros BTCUSDT, ordenadas (incluye la vela en curso)."""
    x = _json(f"https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval={marco}&limit={min(n, 1500)}")
    return [[int(k[0]) // 1000, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])] for k in x]


def coinbase(marco, n):
    """Coinbase BTC-USD. No tiene 4 h: se arma con velas de 1 h alineadas a 00, 04, 08… UTC."""
    if marco == "4h":
        h = coinbase("1h", n * 4 + 8)
        g = {}
        for v in h:
            g.setdefault(v[0] - v[0] % 14400, []).append(v)
        out = [[k, b[0][1], max(x[2] for x in b), min(x[3] for x in b), b[-1][4], sum(x[5] for x in b)]
               for k, b in sorted(g.items())]
        return out[-n:]
    gran = SEG[marco]
    fin = int(time.time()) // gran * gran + gran
    ini = fin - gran * min(n, 300)
    u = (f"https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity={gran}"
         f"&start={dt.datetime.fromtimestamp(ini, UTC):%Y-%m-%dT%H:%M:%SZ}&end={dt.datetime.fromtimestamp(fin, UTC):%Y-%m-%dT%H:%M:%SZ}")
    x = _json(u)  # [t, low, high, open, close, vol], de la más nueva a la más vieja
    return sorted([[int(k[0]), float(k[3]), float(k[2]), float(k[1]), float(k[4]), float(k[5])] for k in x])


def rango(marco, ini, fin, fuente="auto"):
    """Velas [t, o, h, l, c, v] con ini <= t < fin (segundos UTC), paginando. Para el entrenamiento a ciegas."""
    gran, out = SEG[marco], {}
    usar_binance = fuente in ("auto", "binance")
    t = ini
    while t < fin:
        if usar_binance:
            try:
                x = _json(f"https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval={marco}"
                          f"&startTime={t * 1000}&endTime={(fin - 1) * 1000}&limit=1500")
                filas = [[int(k[0]) // 1000, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])] for k in x]
            except Exception:  # noqa: BLE001
                if fuente == "binance":
                    raise
                usar_binance = False
                continue
            paso = gran * 1500
        else:
            if marco == "4h":
                raise ValueError("Coinbase no tiene 4 h")
            t1 = min(fin, t + gran * 300)
            x = _json(f"https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity={gran}"
                      f"&start={dt.datetime.fromtimestamp(t, UTC):%Y-%m-%dT%H:%M:%SZ}"
                      f"&end={dt.datetime.fromtimestamp(t1 - 1, UTC):%Y-%m-%dT%H:%M:%SZ}")
            filas = [[int(k[0]), float(k[3]), float(k[2]), float(k[1]), float(k[4]), float(k[5])] for k in x]
            paso = gran * 300
        for f in filas:
            if ini <= f[0] < fin:
                out[f[0]] = f
        t += paso
    return [out[k] for k in sorted(out)], ("Binance futuros BTCUSDT" if usar_binance else "Coinbase BTC-USD")


def velas(marco, n, fuente="auto"):
    """(velas cerradas, nombre de la fuente). Pide de más para tener EMA 20, ATR 14 y media de volumen."""
    pedir = n + 60
    if fuente in ("auto", "binance"):
        try:
            v = binance(marco, pedir)
            src = "Binance futuros BTCUSDT"
        except Exception as e:  # noqa: BLE001
            if fuente == "binance":
                raise
            v, src = coinbase(marco, pedir), f"Coinbase BTC-USD (Binance falló: {type(e).__name__})"
    else:
        v, src = coinbase(marco, pedir), "Coinbase BTC-USD"
    ahora = time.time()
    return [x for x in v if x[0] + SEG[marco] <= ahora], src


def ema(xs, n=20):
    a, e, out = 2 / (n + 1), None, []
    for x in xs:
        e = x if e is None else e + a * (x - e)
        out.append(e)
    return out


def tabla(marco, v, n):
    o, h, l, c, vol = ([x[k] for x in v] for k in range(1, 6))
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, len(v))]
    atr = [sum(tr[max(0, i - 14):i]) / max(1, len(tr[max(0, i - 14):i])) for i in range(len(v))]  # ATR de las 14 previas
    mvol = [sum(vol[max(0, i - 20):i]) / max(1, len(vol[max(0, i - 20):i])) for i in range(len(v))]
    e20 = ema(c)
    pat = patrones_std.patrones(o, h, l, c)
    zona = UTC if marco in ("4h", "1d") else COL
    L = [f"--- {marco}: últimas {min(n, len(v))} velas cerradas (hora {'UTC' if zona is UTC else 'Colombia'}) ---",
         "  hora              apertura     máximo     mínimo     cierre   camb%  cuerpo mech↑ mech↓ rango/ATR vol/x̄ vsEMA20%  patrones"]
    for i in range(max(0, len(v) - n), len(v)):
        rango = h[i] - l[i]
        cuerpo = abs(c[i] - o[i])
        sup = h[i] - max(o[i], c[i])
        inf = min(o[i], c[i]) - l[i]
        p = lambda x: f"{x / rango * 100:5.0f}" if rango > 0 else "    -"  # noqa: E731
        nombres = [k + ("↑" if patrones_std.LADO[k] > 0 else "↓" if patrones_std.LADO[k] < 0 else "·")
                   for k in patrones_std.LADO if pat[k][i]]
        hora = dt.datetime.fromtimestamp(v[i][0], zona).strftime("%m-%d %H:%M")
        L.append(f"  {hora}  {o[i]:>10,.1f} {h[i]:>10,.1f} {l[i]:>10,.1f} {c[i]:>10,.1f} "
                 f"{(c[i] / o[i] - 1) * 100:+6.2f}  {p(cuerpo)} {p(sup)} {p(inf)} "
                 f"{(rango / atr[i]) if atr[i] > 0 else float('nan'):9.2f} {(vol[i] / mvol[i]) if mvol[i] > 0 else float('nan'):5.2f} "
                 f"{(c[i] / e20[i] - 1) * 100:+8.2f}  {' '.join(nombres) or '-'}")
    return L


def esperar(max_espera):
    """Espera al próximo cierre de vela de 15 m (+5 s). Devuelve True si llegó; False si se acabó max_espera."""
    falta = 900 - time.time() % 900 + 5
    if falta > max_espera:
        time.sleep(max(0, max_espera))
        print(f"Todavía faltan {falta - max_espera:.0f} s para el cierre de 15 m: vuelve a llamar con --esperar.")
        return False
    time.sleep(falta)
    return True


def main():
    if hasattr(sys.stdout, "reconfigure"):  # Windows: con la salida por tubería usa cp1252, sin «−», «≥» ni flechas
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Paquete de velas cerradas para la lectura vela por vela.")
    ap.add_argument("--fuente", choices=("auto", "binance", "coinbase"), default="auto")
    ap.add_argument("--marcos", default="1m,5m,15m,1h,4h,1d")
    ap.add_argument("--n", type=int, default=0, help="velas por marco (0 = las de siempre)")
    ap.add_argument("--esperar", action="store_true")
    ap.add_argument("--max-espera", type=int, default=540)
    a = ap.parse_args()
    if a.esperar and not esperar(a.max_espera):
        return 2
    ahora = dt.datetime.now(UTC)
    salida, fuentes = [], set()
    for marco in a.marcos.split(","):
        n = a.n or N_POR_DEFECTO[marco]
        v, src = velas(marco, n, a.fuente)
        fuentes.add(src)
        salida += tabla(marco, v, n)
    d, _ = velas("1d", 60, a.fuente)
    cierres = [x[4] for x in d]
    sma50 = sum(cierres[-50:]) / 50
    print(f"PAQUETE DE VELAS · {ahora:%Y-%m-%d %H:%M:%S} UTC ({ahora.astimezone(COL):%H:%M} Colombia) · fuente: {' / '.join(sorted(fuentes))}")
    print(f"Contexto: cierre diario de ayer {cierres[-1]:,.2f} frente a SMA 50 {sma50:,.2f} ({(cierres[-1] / sma50 - 1) * 100:+.2f} %) -> "
          f"{'ALCISTA' if cierres[-1] > sma50 else 'BAJISTA'}")
    print("Columnas: cuerpo y mechas en % del rango de la vela; rango/ATR = rango frente al ATR14 de ese marco; vol/x̄ = volumen "
          "frente a la media de las 20 anteriores; ↑ patrón alcista, ↓ bajista, · indecisión.")
    print("\n".join(salida))
    return 0


if __name__ == "__main__":
    sys.exit(main())
