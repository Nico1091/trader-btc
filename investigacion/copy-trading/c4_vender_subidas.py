"""C4 (28/10/2026): el método de 迪亚马特 aplicado por nosotros a TODAS las altcoins de futuros de Binance.

De la ingeniería inversa (c3_perdidas_diamat.txt y su historial: 287 posiciones del 27/09 al 28/10/2026, 74 monedas):
- entra en corto en altcoins que ya subieron muchísimo (mediana +35,6 % en 24 h) y que ya empezaron a girar (sus ganadoras
  entran 3,5 % por debajo del máximo de 24 h; las perdedoras, 1,2 %);
- casi siempre a 5×, en margen cruzado (por eso pierde más del 100 % del margen cuando la moneda sigue subiendo);
- sale cuando el precio cae ~5 % (mediana de sus ganadoras 5,01 %, p25 4,91 %): objetivo fijo y sin stop; la mitad de sus
  posiciones dura menos de 1,4 h y la más larga, 82 h.
Él esconde sus posiciones, así que la única forma de usar su método es aplicarlo nosotros. Esta prueba dice si funciona en
TODAS las monedas y no solo en las que él eligió (las suyas están filtradas por su propio éxito de un solo mes).

Reglas fijadas ANTES de la primera corrida (la v1 de este archivo nunca se corrió; la v2 toma la salida medida en su historial):
- Universo: perpetuos USDT de Binance con subyacente COIN, salvo BTC y ETH; velas de 1 h y financiación de la API pública
  desde 2024-01-01 (solo las monedas que siguen en la lista de Binance: las retiradas no entran).
- Señal, al cierre de una hora: el cierre subió ≥ U frente al de 24 h antes (U = 20, 30 o 50 %); «con giro» exige además que el
  cierre esté ≥ 3 % por debajo del máximo de las últimas 24 h. Una sola posición por moneda.
- Entrada: corto a la apertura de la hora siguiente, 5×; tomador 0,05 % + deslizamiento 0,05 %.
- Salida: objetivo −5 % (creador 0,02 %); si no llega en 96 h, cierre a mercado (tomador + deslizamiento).
  Margen cruzado (el suyo): sin liquidación por posición; la cuenta entera se liquida si las pérdidas abiertas alcanzan el saldo.
  Margen aislado: liquidación si el máximo sube +17,5 % (se pierde el margen); en una vela que toca las dos cosas, cuenta lo peor.
- Financiación: se suma o se resta cada cobro entre la entrada y la salida.
- Universos «donde él gana»: (U0) todas; (U1) las monedas que él operó en su mes; (U2) solo monedas donde la regla ya ganó
  antes (suma de sus operaciones anteriores en esa moneda > 0; causal).
- Copia en papel: 40.000 COP, 10 % del saldo como margen por operación, hasta 5 posiciones a la vez, revisada hora a hora.
- Especificación principal: U = 30 %, con giro, margen cruzado, universo U0. Lo demás es sensibilidad.
Uso: python -I c4_vender_subidas.py > c4_vender_subidas.txt"""
import concurrent.futures as cf
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(os.environ.get("TRADER_DATOS") or os.path.join(AQUI, "..", "..", "datos"), "copy")
VELAS, FIN = os.path.join(BASE, "velas1h"), os.path.join(BASE, "financiacion")
PID = "5240448882690502145"
H = {"User-Agent": "Mozilla/5.0"}
HORA = 3600000
INICIO = 1704067200000  # 2024-01-01
COP = 3177.85
LEV, OBJ, LIQ, MAXH = 5, 0.05, 0.175, 96
COM_IN, COM_TP, COM_MK = 0.0010, 0.0002, 0.0010  # entrada (tomador + deslizamiento), objetivo (creador), cierre a mercado
PARADA = threading.Event()


class Ritmo:
    """Espaciado mínimo entre peticiones, compartido por los hilos (velas: ≤ 300/min de peso 5; financiación: ≤ 86/min)."""

    def __init__(self, seg):
        self.seg, self.t, self.lock = seg, 0.0, threading.Lock()

    def esperar(self):
        with self.lock:
            ahora = time.monotonic()
            if self.t > ahora:
                time.sleep(self.t - ahora)
            self.t = max(ahora, self.t) + self.seg


R_VELAS, R_FIN = Ritmo(0.2), Ritmo(0.7)


def get(u, ritmo):
    for i in range(6):
        if PARADA.is_set():
            return None
        ritmo.esperar()
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=30)
            if int(r.headers.get("X-MBX-USED-WEIGHT-1M") or 0) > 1800:
                time.sleep(20)
            return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 418:  # IP vetada: se para todo en vez de insistir
                PARADA.set()
                return None
            time.sleep(int(e.headers.get("Retry-After") or 30) if e.code == 429 else 2 + i)
        except Exception:
            time.sleep(2 + i)
    return None


def simbolos():
    x = get("https://fapi.binance.com/fapi/v1/exchangeInfo", R_VELAS)
    return sorted(s["symbol"] for s in x["symbols"]
                  if s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT"
                  and s.get("underlyingType", "COIN") == "COIN" and s["symbol"] not in ("BTCUSDT", "ETHUSDT"))


def serie(ruta, url, campos, ritmo, paso):
    """Descarga incremental con caché .npz; nunca guarda una descarga a medias."""
    t0, v0 = np.zeros(0, np.int64), np.zeros((0, len(campos) - 1), np.float64)
    if os.path.exists(ruta):
        z = np.load(ruta)
        t0, v0 = z["t"], z["v"]
        if time.time() - os.path.getmtime(ruta) < 12 * 3600:
            return t0, v0
    ahora = int(time.time() * 1000)
    t, nt, nv = (int(t0[-1]) + 1 if len(t0) else INICIO), [], []
    while t < ahora:
        x = get(url + f"&startTime={t}&limit=1000", ritmo)
        if x is None:
            return None
        if not x:
            break
        for k in x:
            tt, fila = campos[0](k), [f(k) for f in campos[1:]]
            if not nt or tt > nt[-1]:
                nt.append(tt)
                nv.append(fila)
        if len(x) < 1000:
            break
        t = nt[-1] + 1
    if nt:
        t0 = np.concatenate([t0, np.array(nt, np.int64)])
        v0 = np.concatenate([v0, np.array(nv, np.float64).reshape(len(nv), -1)])
    if paso:  # se quita la vela que sigue abierta
        cerradas = t0 + paso <= ahora
        t0, v0 = t0[cerradas], v0[cerradas]
    np.savez(ruta, t=t0, v=v0)
    return t0, v0


def bajar(sim):
    if PARADA.is_set():
        return sim, None, None
    v = serie(os.path.join(VELAS, f"{sim}.npz"), f"https://fapi.binance.com/fapi/v1/klines?symbol={sim}&interval=1h",
              [lambda k: int(k[0])] + [lambda k, j=j: float(k[j]) for j in (1, 2, 3, 4)], R_VELAS, HORA)
    f = serie(os.path.join(FIN, f"{sim}.npz"), f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={sim}",
              [lambda k: int(k["fundingTime"]), lambda k: float(k["fundingRate"])], R_FIN, 0)
    return sim, v, f


def preparar(v):
    """Rejilla horaria continua (los huecos quedan en NaN) y medidas que no dependen de la variante."""
    t, x = v
    n = int((t[-1] - t[0]) // HORA) + 1
    g = np.full((n, 4), np.nan)
    g[(t - t[0]) // HORA] = x
    o, h, l, c = g[:, 0], g[:, 1], g[:, 2], g[:, 3]
    cambio = np.full(n, np.nan)
    cambio[24:] = c[24:] / c[:-24] - 1
    hm = np.full(n, np.nan)
    if n >= 24:
        hm[23:] = np.lib.stride_tricks.sliding_window_view(np.where(np.isnan(h), -np.inf, h), 24).max(axis=1)
    return {"t0": int(t[0]), "o": o, "h": h, "l": l, "c": c, "cambio": cambio, "hm": hm, "n": n}


def senales(d, umbral, giro):
    with np.errstate(invalid="ignore"):
        m = d["cambio"] >= umbral
        if giro:
            m &= d["c"] <= d["hm"] * 0.97
    m[-1] = False
    m &= ~np.isnan(np.roll(d["o"], -1))
    return np.flatnonzero(m)


def operar(sim, d, f, umbral, giro, aislado):
    o, h, l, c, n, t0 = d["o"], d["h"], d["l"], d["c"], d["n"], d["t0"]
    ft, fv = (f[0], f[1][:, 0]) if f is not None and len(f[0]) else (np.zeros(0, np.int64), np.zeros(0))
    res, desde = [], 0
    for i in senales(d, umbral, giro):
        if i < desde:
            continue
        e = float(o[i + 1])
        fin = min(i + MAXH, n - 1)
        sh, sl = h[i + 1:fin + 1], l[i + 1:fin + 1]
        hueco = np.flatnonzero(np.isnan(sh))
        k_fin = int(hueco[0]) - 1 if len(hueco) else len(sh) - 1  # último índice con datos
        k_tp = np.flatnonzero(sl[:k_fin + 1] <= e * (1 - OBJ))
        k_tp = int(k_tp[0]) if len(k_tp) else None
        k_lq = np.flatnonzero(sh[:k_fin + 1] >= e * (1 + LIQ)) if aislado else []
        k_lq = int(k_lq[0]) if len(k_lq) else None
        if k_lq is not None and (k_tp is None or k_lq <= k_tp):
            k, r = k_lq, -100.0
        elif k_tp is not None:
            k, r = k_tp, (OBJ - COM_IN - COM_TP) * 100 * LEV
        else:
            k = k_fin
            r = ((1 - c[i + 1 + k] / e) - COM_IN - COM_MK) * 100 * LEV
        a, b = t0 + (i + 1) * HORA, t0 + (i + 1 + k) * HORA
        if r > -100 or not aislado:
            m = (ft > a) & (ft <= b)
            r += float(fv[m].sum()) * 100 * LEV
        res.append({"s": sim, "a": a, "b": b, "r": r, "contra": np.maximum(0.0, (sh[:k + 1] / e - 1) * 100 * LEV)})
        desde = i + 1 + k + 1
    return res


def copia(ops, aislado, f=0.10, max_ab=5):
    """Saldo en COP, caída máxima y peor operación (fracción del saldo), revisando la cuenta hora a hora."""
    E = pico = 40000 / COP
    cm, peor, ab, T = 0.0, 0.0, [], 0

    def avanzar(hasta):
        nonlocal E, pico, cm, peor, T
        while ab and T < hasta:
            if not aislado and sum(m * o["contra"][min((T - o["a"]) // HORA, len(o["contra"]) - 1)] / 100 for o, m in ab) >= E:
                return False  # margen cruzado: la cuenta entera se liquida
            quedan = []
            for o, m in ab:
                if o["b"] <= T:
                    g = m * o["r"] / 100
                    peor = min(peor, g / E)
                    E += g
                    pico, cm = max(pico, E), max(cm, 1 - E / pico)
                else:
                    quedan.append((o, m))
            ab[:] = quedan
            if E <= 0:
                return False
            T += HORA
        return True

    for o in sorted(ops, key=lambda x: x["a"]):
        if ab and not avanzar(o["a"]):
            return 0.0, 1.0, -1.0
        T = o["a"]
        if len(ab) < max_ab:
            ab.append((o, f * E))
    if not avanzar(float("inf")):
        return 0.0, 1.0, -1.0
    return E * COP, cm, peor


def causal(ops):
    """U2: solo operaciones en monedas donde la regla ya ganó antes (suma de las anteriores > 0)."""
    out, por = [], {}
    for o in sorted(ops, key=lambda x: x["a"]):
        prev = por.get(o["s"], [])
        if prev and sum(p["r"] for p in prev if p["b"] < o["a"]) > 0:
            out.append(o)
        prev.append(o)
        por[o["s"]] = prev
    return out


def linea(ops, aislado, dias):
    if not ops:
        return "sin operaciones"
    r = np.array([o["r"] for o in ops])
    anos = {}
    for o in ops:
        anos.setdefault(time.gmtime(o["a"] / 1000).tm_year, []).append(o["r"])
    E, cm, peor = copia(ops, aislado)
    g = (E / 40000) ** (1 / dias) - 1 if E > 0 else -1.0
    return (f"{len(ops):,} op · acierto {(r > 0).mean() * 100:.1f} % · media {r.mean():+.1f} % del margen · peor {r.min():+.0f} % · por año: "
            + ", ".join(f"{y} {np.mean(x):+.1f} % ({(np.array(x) > 0).mean() * 100:.0f} % ac., n={len(x)})" for y, x in sorted(anos.items()))
            + f"\n        copia (10 % de margen, hasta 5 a la vez): 40.000 → {E:,.0f} COP · {g * 100:+.3f} % al día · "
            f"caída máx {cm * 100:.0f} % · peor operación {peor * 100:+.1f} % del saldo")


def main():
    os.makedirs(VELAS, exist_ok=True)
    os.makedirs(FIN, exist_ok=True)
    sims = simbolos()
    print(f"C4 · vender en corto las subidas de altcoins (método de 迪亚马特) · {len(sims)} perpetuos USDT de Binance · "
          "velas de 1 h y financiación desde 2024-01-01", flush=True)
    datos, fallos = {}, []
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for k, (s, v, f) in enumerate(ex.map(bajar, sims), 1):
            if v is None or f is None or len(v[0]) < 48:
                fallos.append(s)
            else:
                datos[s] = (preparar(v), f)
            if k % 50 == 0:
                print(f"   … {k} de {len(sims)} monedas", file=sys.stderr, flush=True)
    if PARADA.is_set():
        print("PARADA: Binance vetó la IP por exceso de peticiones; no hay resultados.")
        return
    print(f"   monedas con datos: {len(datos)} · sin datos o con menos de 48 h: {len(fallos)}")
    ultimo = max(d["t0"] + (d["n"] - 1) * HORA for d, f in datos.values())
    dias = (ultimo - INICIO) / 86400000
    suyo = [p for p in json.load(open(os.path.join(BASE, f"historial-{PID}.json"), encoding="utf-8")) if p.get("opened")]
    sus_monedas = {p["symbol"] for p in suyo}
    for umbral, giro, aislado in [(0.30, True, False)] + [(u, g, a) for u in (0.20, 0.30, 0.50) for g in (False, True)
                                                          for a in (False, True) if (u, g, a) != (0.30, True, False)]:
        ops = [x for s, (d, f) in datos.items() for x in operar(s, d, f, umbral, giro, aislado)]
        titulo = f"subida ≥ {umbral * 100:.0f} % en 24 h, {'con' if giro else 'sin'} giro, margen {'aislado' if aislado else 'cruzado'}"
        print(f"\n== {'ESPECIFICACIÓN PRINCIPAL · ' if (umbral, giro, aislado) == (0.30, True, False) else ''}{titulo} ==")
        print(f"   U0 todas las monedas: {linea(ops, aislado, dias)}")
        print(f"   U1 sus monedas ({len(sus_monedas)}): {linea([o for o in ops if o['s'] in sus_monedas], aislado, dias)}")
        print(f"   U2 donde la regla ya ganó: {linea(causal(ops), aislado, dias)}")
        if (umbral, giro, aislado) == (0.30, True, False):
            ini = min(int(p["opened"]) for p in suyo)
            mes = [o for o in ops if o["a"] >= ini]
            print(f"   en su mismo mes (desde {time.strftime('%Y-%m-%d', time.gmtime(ini / 1000))}): {linea(mes, aislado, max(1.0, (ultimo - ini) / 86400000))}")
            cortos = [p for p in suyo if p["side"] == "Short"]
            marcas = {s: d["t0"] + (senales(d, umbral, giro) + 1) * HORA for s, (d, f) in datos.items()}
            hits = sum(1 for p in cortos if p["symbol"] in marcas
                       and np.any(np.abs(marcas[p["symbol"]] - int(p["opened"])) <= 3 * HORA))
            print(f"   de sus {len(cortos)} cortos, {hits} ({hits / len(cortos) * 100:.0f} %) coinciden con una señal nuestra (misma moneda, ±3 h)")


if __name__ == "__main__":
    main()
