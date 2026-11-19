"""Elección mensual a ciegas y operación de las binarias (PLAN.md v2, sección 5). La usan t18 y el centinela.

Cada estrategia se ajusta solo con su ventana de entrenamiento: sentido y plazo; luego zona, sesión y volatilidad si suben el
límite inferior de Wilson al 95 % con al menos 100 apuestas, contadas sin solapes. Se eligen las 3 de mayor límite que superen
el punto de equilibrio del pago. El empate cuenta como fallo."""
import math

import numpy as np

PLAZOS = (10, 30, 60)
SESIONES = {"Asia": (0, 7), "Europa": (7, 13), "América": (13, 21)}  # horas UTC
Z95 = 1.959964
MIN_AP = 100
HCOL = 5 * 3600
TOPE = 16


def wilson_lb(w, n, z):
    if n <= 0:
        return 0.0
    p = w / n
    den = 1 + z * z / n
    centro = p + z * z / (2 * n)
    margen = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centro - margen) / den


def preparar(S, T5, vol5, ctxd, t, o, c, plazos=PLAZOS):
    """Por estrategia: tiempos, direcciones y resultados (+1 acierto, 0 empate, −1 fallo) a cada plazo, entrando al abrir el
    minuto de la señal (`res`) o 60 s después (`res60`), y lo que daría apostar siempre arriba (`up`). Solo señales con resultado."""
    t0, N = int(t[0]), len(c)
    mx = max(plazos)
    P = {}
    for nom, (g, ts, ds) in S.items():
        ts = np.asarray(ts, dtype=np.int64)
        ds = np.asarray(ds, dtype=float)
        k = (ts - t0) // 60
        ok = (k >= 0) & (k + mx + 1 < N) & (ds != 0)
        ts, ds, k = ts[ok], ds[ok], k[ok]
        orden = np.argsort(ts, kind="stable")
        ts, ds, k = ts[orden], ds[orden], k[orden]
        if not len(ts):
            continue
        j5 = np.clip(np.searchsorted(T5, ts - 300, side="right") - 1, 0, len(T5) - 1)
        P[nom] = {"g": g, "t": ts, "d": ds,
                  "res": {pl: np.sign(ds * (c[k + pl - 1] - o[k])).astype(np.int8) for pl in plazos},
                  "res60": {pl: np.sign(ds * (c[k + pl] - o[k + 1])).astype(np.int8) for pl in plazos},
                  "up": {pl: np.sign(c[k + pl - 1] - o[k]).astype(np.int8) for pl in plazos},
                  "ctx": np.array([ctxd.get(int(x) // 86400, 0.0) for x in ts]),
                  "hora": (ts % 86400) // 3600, "valta": np.asarray(vol5)[j5].astype(bool)}
    return P


def mascara(p, conf, i0, i1):
    m = np.ones(i1 - i0, bool)
    if conf.get("zona"):
        m &= conf["sentido"] * p["d"][i0:i1] == p["ctx"][i0:i1]
    if conf.get("sesion"):
        lo, hi = SESIONES[conf["sesion"]]
        hh = p["hora"][i0:i1]
        m &= (hh >= lo) & (hh < hi)
    if conf.get("vol"):
        v = p["valta"][i0:i1]
        m &= v if conf["vol"] == "alta" else ~v
    return m


def puntuar(p, conf, i0, i1):
    """Aciertos, apuestas y límite de Wilson en [i0, i1), sin solapes: se descarta la señal que llega antes de que venza la anterior."""
    m = mascara(p, conf, i0, i1)
    tw = p["t"][i0:i1][m]
    if not len(tw):
        return 0, 0, 0.0
    keep = np.r_[True, np.diff(tw) >= conf["plazo"] * 60]
    r = p["res"][conf["plazo"]][i0:i1][m][keep] * conf["sentido"]
    n = len(r)
    w = int((r > 0).sum())
    return w, n, wilson_lb(w, n, Z95)


def ajustar(p, a, b, min_ap=MIN_AP):
    i0, i1 = (int(x) for x in np.searchsorted(p["t"], [a, b]))
    mejor = None
    for sentido in (1, -1):
        for pl in PLAZOS:
            conf = {"sentido": sentido, "plazo": pl}
            w, n, lb = puntuar(p, conf, i0, i1)
            if n >= min_ap and (mejor is None or lb > mejor[1]):
                mejor = (conf, lb, w, n)
    if mejor is None:
        return None
    for clave, opciones in (("zona", (True,)), ("sesion", tuple(SESIONES)), ("vol", ("alta", "baja"))):
        mejor_op = None
        for op in opciones:
            conf = dict(mejor[0], **{clave: op})
            w, n, lb = puntuar(p, conf, i0, i1)
            if n >= min_ap and lb > mejor[1] and (mejor_op is None or lb > mejor_op[1]):
                mejor_op = (conf, lb, w, n)
        if mejor_op:
            mejor = mejor_op
    return mejor


def elegir(P, a, b, k=3, umbral=1 / 1.85, min_ap=MIN_AP):
    """Las k estrategias de mayor límite inferior en la ventana [a, b) que superan el umbral (equilibrio con pago 0,85)."""
    cands = []
    for nom, p in P.items():
        r = ajustar(p, a, b, min_ap)
        if r and r[1] > umbral:
            cands.append((r[1], nom, r[0], r[2], r[3]))
    cands.sort(key=lambda x: (-x[0], x[1]))
    return [{"nombre": nom, "conf": conf, "lb": lb, "aciertos": w, "apuestas": n} for lb, nom, conf, w, n in cands[:k]]


def eventos(P, elegidos, a, b):
    """Señales de los elegidos en [a, b): (tiempo, estrategia, dirección, plazo, resultado, resultado 60 s tarde, siempre arriba)."""
    ev = []
    for e in elegidos:
        p, conf = P[e["nombre"]], e["conf"]
        pl, s = conf["plazo"], conf["sentido"]
        i0, i1 = (int(x) for x in np.searchsorted(p["t"], [a, b]))
        for i in (np.arange(i0, i1)[mascara(p, conf, i0, i1)]).tolist():
            ev.append((int(p["t"][i]), e["nombre"], int(s * p["d"][i]), pl, int(s * p["res"][pl][i]),
                       int(s * p["res60"][pl][i]), int(p["up"][pl][i])))
    ev.sort()
    return ev


def operar(ev, tope=TOPE):
    """Una apuesta abierta a la vez y como máximo `tope` por día de Colombia."""
    tomadas, ocupado, dia, n = [], 0, None, 0
    for e in ev:
        ts, pl = e[0], e[3]
        d = (ts - HCOL) // 86400
        if d != dia:
            dia, n = d, 0
        if ts < ocupado or n >= tope:
            continue
        tomadas.append(e)
        ocupado = ts + pl * 60
        n += 1
    return tomadas


def saldo(resultados, pago, cap=100000.0, ap=0.16, minimo=15900.0):
    """Saldo tras apostar el mayor entre `ap` del saldo y el mínimo de Binance; 0 si la cuenta quiebra. Empate = fallo."""
    s = cap
    for r in resultados:
        if s < minimo:
            return 0.0
        m = max(ap * s, minimo)
        s += m * pago if r > 0 else -m
    return s
