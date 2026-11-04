"""Procedimiento del mes por historial y tamaño de la apuesta (medio Kelly): una sola fuente para t21 y el centinela.

Insumo: las apuestas a ciegas del banco (t18: reglas en BTC y ETH; t19: modelo a 10, 30 y 60 min en BTC y ETH).
- Procedimiento del mes M: el de mayor límite de Wilson (95 %) de su acierto a ciegas en los 12 meses anteriores, con al menos
  100 apuestas y por encima del equilibrio con pago 0,85.
- Fracción: medio Kelly con el acierto a ciegas de los 6 meses anteriores del procedimiento; 0 si no supera el equilibrio
  (ese mes no se apuesta). La apuesta nunca baja de 5 USDT."""
import datetime as dt
import math
import os

PAGO = 0.85
EQ = 1 / (1 + PAGO)
PRUEBAS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pruebas")


def wilson(w, n, z=1.959964):
    if n <= 0:
        return 0.0
    p = w / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def cargar(carpeta=PRUEBAS):
    """{procedimiento: [(día ordinal de Colombia, "AAAA-MM", acierto)]} ordenado por hora."""
    P = {}
    for s in ("BTCUSDT", "ETHUSDT"):
        lin = open(os.path.join(carpeta, f"t18_{s}_apuestas.csv"), encoding="utf-8-sig").read().splitlines()[1:]
        P[f"reglas {s[:3]}"] = [(x.split(";")[0], x.split(";")[5] == "acierta") for x in lin]
        lin = open(os.path.join(carpeta, f"t19_{s}_apuestas.csv"), encoding="utf-8-sig").read().splitlines()[1:]
        for pl in ("10", "30", "60"):
            P[f"modelo {pl} min {s[:3]}"] = [(x.split(";")[0], x.split(";")[3] == "acierta") for x in lin if x.split(";")[1] == pl]
    out = {}
    for k, v in P.items():
        v.sort()
        out[k] = [(dt.datetime.strptime(f[:10], "%Y-%m-%d").toordinal(), f[:7], r) for f, r in v]
    return out


def stats_mes(P):
    S = {}
    for k, v in P.items():
        d = {}
        for _, mes, r in v:
            w, n = d.get(mes, (0, 0))
            d[mes] = (w + r, n + 1)
        S[k] = d
    return S


def atras(mes, k):
    y, m = int(mes[:4]), int(mes[5:])
    i = y * 12 + m - 1 - k
    return f"{i // 12}-{i % 12 + 1:02d}"


def ventana(S, proc, mes, k):
    w = n = 0
    for i in range(1, k + 1):
        a, b = S[proc].get(atras(mes, i), (0, 0))
        w, n = w + a, n + b
    return w, n


def elegir(S, mes, procs=None):
    """(procedimiento, límite de Wilson, aciertos, apuestas) del mes, o None si ninguno supera el equilibrio."""
    mejor = None
    for pr in procs or list(S):
        w, n = ventana(S, pr, mes, 12)
        lb = wilson(w, n)
        if n >= 100 and lb > EQ and (mejor is None or lb > mejor[1]):
            mejor = (pr, lb, w, n)
    return mejor


def fraccion(S, proc, mes, kelly=0.5):
    w, n = ventana(S, proc, mes, 6)
    if n < 100:
        return 0.0
    p = w / n
    return max(0.0, (p * PAGO - (1 - p)) / PAGO) * kelly


def describir(proc):
    """«modelo 10 min ETH» -> ("modelo", "ETHUSDT", 10); «reglas BTC» -> ("reglas", "BTCUSDT", None)."""
    x = proc.split()
    sim = x[-1] + "USDT"
    return (x[0], sim, int(x[1]) if x[0] == "modelo" else None)
