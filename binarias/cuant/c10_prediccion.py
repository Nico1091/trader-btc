"""C10 (04/11/2026): P19, el núcleo en los mercados «BTC Up or Down» de 5 y 15 min (Binance Wallet con Predict.fun).

Regla y criterio escritos antes de medir en PLAN-TOTAL.md, sección 7b (P19), el 04/11/2026 a las 18:10.
Solo numpy y biblioteca estándar. Uso: python -I c10_prediccion.py
"""
import datetime as dt
import math
import os
import sys

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import base as B  # noqa: E402

SALIDA = os.path.join(AQUI, "resultados", "c10_BTCUSDT.txt")
COMPRA, COMISION = 0.51, 0.02
EQ = (1 + COMISION) * COMPRA  # 52,02 %
TRAMOS = (("2021-2023", (2021, 1), (2024, 1)), ("2024-sep 2026", (2024, 1), (2026, 10)),
          ("oct 2025-sep 2026", (2025, 10), (2026, 10)), ("octubre de 2026", (2026, 10), (2026, 11)))
L = []


def say(x=""):
    print(x)
    L.append(x)


def ts(a, m):
    return int(dt.datetime(a, m, 1, tzinfo=dt.timezone.utc).timestamp())


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan")
    p, c = k / n, z * z / n
    return (p + c / 2 - z * math.sqrt(p * (1 - p) / n + c / (4 * n))) / (1 + c)


def neto(p, compra=COMPRA, comision=COMISION):
    """Ganancia media por unidad apostada, con aciertos p."""
    return p / compra - (1 + comision)


t1, o1, h1, l1, c1, v1, tb1 = B.cargar("BTCUSDT")
t1 = t1.astype(np.int64)
assert np.all(np.diff(t1) > 0)
# velas de 5 min completas, alineadas a múltiplos de 300 s (bucle de numpy por grupos)
g = t1 // 300
ini = np.r_[0, np.flatnonzero(np.diff(g)) + 1]
fin = np.r_[ini[1:], len(g)]
completa = fin - ini == 5
ini, fin = ini[completa], fin[completa]
T5 = g[ini].astype(np.int64) * 300
H5 = np.maximum.reduceat(h1, np.r_[0, np.flatnonzero(np.diff(g)) + 1])[completa]
L5 = np.minimum.reduceat(l1, np.r_[0, np.flatnonzero(np.diff(g)) + 1])[completa]
C5 = c1[fin - 1]
n = len(T5)
sen = np.zeros(n, dtype=np.int64)
for j in range(20, n):
    if T5[j] - T5[j - 20] != 6000:  # hueco en los datos: sin señal
        continue
    if C5[j] > H5[j - 20:j].max():
        sen[j] = -1
    elif C5[j] < L5[j - 20:j].min():
        sen[j] = 1
print("señales", int((sen != 0).sum()), "de", n)
cierre = {int(a): float(b) for a, b in zip(t1 + 60, c1)}  # hora de fin de vela de 1 min -> cierre


def resultado(j, plazo, tarde):
    """1 acierto, 0,5 empate, 0 fallo; None si faltan datos."""
    t0 = int(T5[j]) + 300
    a, b = cierre.get(t0 + tarde), cierre.get(t0 + plazo)
    if a is None or b is None:
        return None
    m = (b - a) * int(sen[j])
    return 1.0 if m > 0 else (0.5 if m == 0 else 0.0)


def medir(mascara, plazo):
    idx = np.flatnonzero(mascara & (sen != 0))
    return {tarde: [(int(T5[j]) + 300, resultado(j, plazo, tarde)) for j in idx] for tarde in (0, 60)}


VARIANTES = (("M5", np.ones(n, bool), 300),
             ("M5d", (T5 + 300) % 600 == 0, 300),
             ("M15", (T5 + 300) % 900 == 0, 900))
say("P19 · el núcleo en los mercados de predicción (regla escrita a las 18:10 del 04/11/2026)")
say(f"Equilibrio supuesto: compra a {COMPRA} y comisión de {COMISION:.0%} = {EQ:.2%}; a 0,52 = {1.02 * 0.52:.2%}.")
res = {}
for nombre, masc, plazo in VARIANTES:
    m = medir(masc, plazo)
    for tarde in (0, 60):
        for tramo, a, b in TRAMOS:
            d0, d1 = ts(*a), ts(*b)
            x = [r for tt, r in m[tarde] if d0 <= tt < d1 and r is not None]
            k, c = sum(x), len(x)
            dias = (d1 - d0) / 86400
            res[nombre, tarde, tramo] = (k, c)
            say(f"{nombre:4s} entrada +{tarde:2d}s {tramo:18s} n={c:6d} ({c / dias:4.1f}/día) acierto={k / max(c, 1):.2%} "
                f"Wilson={wilson(k, c):.2%} neto a 0,51={neto(k / max(c, 1)):+.4f} a 0,52={neto(k / max(c, 1), 0.52):+.4f}")
elegida = max((v[0] for v in VARIANTES), key=lambda v: res[v, 60, "2021-2023"][0] / max(res[v, 60, "2021-2023"][1], 1))
k, c = res[elegida, 60, "2024-sep 2026"]
k12, c12 = res[elegida, 60, "oct 2025-sep 2026"]
pasa = wilson(k, c) > EQ and k12 / max(c12, 1) >= EQ + 0.01
say(f"Elegida en 2021-2023 con 60 s tarde: {elegida}. Wilson 2024-sep 2026 {wilson(k, c):.2%} frente a {EQ:.2%}; "
    f"últimos 12 meses {k12 / max(c12, 1):.2%} frente a {EQ + 0.01:.2%}. Criterio: {'PASA a papel en vivo' if pasa else 'NO PASA'}.")
with open(SALIDA, "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")
