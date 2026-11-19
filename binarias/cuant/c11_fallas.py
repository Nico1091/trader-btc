"""C11 (04/11/2026): P20, por qué falla el núcleo a 15 min y si las caídas se pueden filtrar.

Regla y criterio escritos antes de medir en PLAN-TOTAL.md, sección 7b (P20), el 04/11/2026 a las 19:02.
Solo numpy y biblioteca estándar. Uso: python -I c11_fallas.py
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

SALIDA = os.path.join(AQUI, "resultados", "c11_BTCUSDT.txt")
EQ = 0.5202
SORTEOS = 2000
RNG = np.random.default_rng(4112027)
L = []


def say(x=""):
    print(x)
    L.append(x)


def ts(a, m):
    return int(dt.datetime(a, m, 1, tzinfo=dt.timezone.utc).timestamp())


t1, o1, h1, l1, c1, v1, tb1 = B.cargar("BTCUSDT")
t1 = t1.astype(np.int64)
g = t1 // 300
ini = np.r_[0, np.flatnonzero(np.diff(g)) + 1]
fin = np.r_[ini[1:], len(g)]
H = np.maximum.reduceat(h1, ini)
Lo = np.minimum.reduceat(l1, ini)
ok = fin - ini == 5
ini, fin, H, Lo = ini[ok], fin[ok], H[ok], Lo[ok]
T5 = g[ini].astype(np.int64) * 300
O5, C5 = o1[ini], c1[fin - 1]
n = len(T5)
prev = np.r_[C5[0], C5[:-1]]
tr = np.maximum(H - Lo, np.maximum(np.abs(H - prev), np.abs(Lo - prev)))
atr = np.convolve(tr, np.ones(14) / 14, "full")[: n]
sen = np.zeros(n, dtype=np.int64)
for j in range(20, n):
    if T5[j] - T5[j - 20] != 6000:
        continue
    if C5[j] > H[j - 20:j].max():
        sen[j] = -1
    elif C5[j] < Lo[j - 20:j].min():
        sen[j] = 1
cierre = {int(a) + 60: float(b) for a, b in zip(t1, c1)}
idx = np.flatnonzero((sen != 0) & ((T5 + 300) % 900 == 0))
filas = []
ult_sen = {1: -10 ** 12, -1: -10 ** 12}
todas = np.flatnonzero(sen != 0)
pos = 0
for j in idx:
    t = int(T5[j]) + 300
    a, b = cierre.get(t + 60), cierre.get(t + 900)
    if a is None or b is None:
        continue
    d = int(sen[j])
    while pos < len(todas) and todas[pos] < j:
        ult_sen[int(sen[todas[pos]])] = int(T5[todas[pos]]) + 300
        pos += 1
    m = (b - a) * d
    res = 1.0 if m > 0 else (0.5 if m == 0 else 0.0)
    rup = -d  # sentido de la ruptura: la apuesta va al revés
    cadena = t - ult_sen[d] <= 1800
    largo = (H[j] - Lo[j]) > 2 * atr[j - 1]
    p60 = cierre.get(t - 3600)
    hora = p60 is not None and (C5[j] / p60 - 1) * rup > 0.01
    tres = j >= 2 and all((C5[k] - O5[k]) * rup > 0 for k in (j, j - 1, j - 2))
    filas.append((t, d, res, cadena, largo, hora, tres))
F = np.array(filas, dtype=np.float64)
t, d, r = F[:, 0], F[:, 1], F[:, 2]
TR = {"2021-2023": (ts(2021, 1), ts(2024, 1)), "2024-sep 2026": (ts(2024, 1), ts(2026, 10)), "octubre de 2026": (ts(2026, 10), ts(2026, 11))}
MAS = {k: (t >= a) & (t < b) for k, (a, b) in TR.items()}


def pc(x):
    return f"{100 * x:.2f} %".replace(".", ",")


say("P20 · por qué falla el núcleo a 15 min (M15, entrada 60 s tarde, equilibrio 52,02 %)")
say("\nDónde están las fallas, sin filtrar:")
for k, m in MAS.items():
    say(f"  {k}: {pc(r[m].mean())} en {int(m.sum())}; SUBE {pc(r[m & (d == 1)].mean())}, BAJA {pc(r[m & (d == -1)].mean())}")
NOMBRES = {"A cadena": 3, "B desplome": 4, "C hora >1 %": 5, "D tres velas": 6}
say("\nAcierto cuando aparece cada rasgo, frente a cuando no (2024-sep 2026):")
m0 = MAS["2024-sep 2026"]
for nom, c in NOMBRES.items():
    x = F[:, c] == 1
    say(f"  {nom:13s} con: {pc(r[m0 & x].mean())} ({int((m0 & x).sum())}) · sin: {pc(r[m0 & ~x].mean())} · SUBE con: {pc(r[m0 & x & (d == 1)].mean())} · BAJA con: {pc(r[m0 & x & (d == -1)].mean())}")
say("\nFiltros (se quita la señal con el rasgo):")
pv = {}
for nom, c in NOMBRES.items():
    q = F[:, c] == 0
    base = r[m0].mean()
    nuevo = r[m0 & q].mean()
    k = int((m0 & q).sum())
    az = np.array([RNG.choice(r[m0], k, replace=False).mean() for _ in range(SORTEOS)])
    pv[nom] = float((np.sum(az >= nuevo) + 1) / (SORTEOS + 1))
    dias = (TR["2024-sep 2026"][1] - TR["2024-sep 2026"][0]) / 86400
    say(f"  {nom:13s} 2021-23 {100 * (r[MAS['2021-2023'] & q].mean() - r[MAS['2021-2023']].mean()):+.2f} pts · 2024-26 {100 * (nuevo - base):+.2f} pts ({pc(nuevo)}, {k / dias:.1f}/día, p={pv[nom]:.3f}) · oct {100 * (r[MAS['octubre de 2026'] & q].mean() - r[MAS['octubre de 2026']].mean()):+.2f} pts")
orden = sorted(pv, key=pv.get)
m_ = len(orden)
pasa_bh = {nom: pv[nom] <= 0.05 * (i + 1) / m_ for i, nom in enumerate(orden)}
elegida = max(NOMBRES, key=lambda v: r[MAS["2021-2023"] & (F[:, NOMBRES[v]] == 0)].mean())
say(f"\nElegida en 2021-2023: {elegida}.")
q = F[:, NOMBRES[elegida]] == 0
dias = (TR["2024-sep 2026"][1] - TR["2024-sep 2026"][0]) / 86400
sube = 100 * (r[m0 & q].mean() - r[m0].mean())
c1_ = sube >= 0.5 and pasa_bh[elegida]
c2_ = (m0 & q).sum() / dias >= 3
c3_ = r[MAS["2021-2023"] & q].mean() - r[MAS["2021-2023"]].mean() > -0.01 and r[MAS["octubre de 2026"] & q].mean() - r[MAS["octubre de 2026"]].mean() > -0.01
say(f"Criterio: sube {sube:+.2f} pts con BH {pasa_bh[elegida]}; señales al día {c2_}; sin perder en los otros tramos {c3_}. {'ENTRA' if c1_ and c2_ and c3_ else 'NO ENTRA'}.")
with open(SALIDA, "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")
