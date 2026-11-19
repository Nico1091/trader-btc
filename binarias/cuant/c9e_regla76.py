"""C9e · P17 (04/11/2026): su regla del 76 %. El SÍ (P15) pasa a real solo si el papel reciente del núcleo acierta el 76 % o
más. Regla escrita antes en PLAN-TOTAL.md, sección 7b. Núcleo en BTCUSDT, entrada 60 s tarde, empate = fallo, pago 0,85.
Uso: python -I c9e_regla76.py CARPETA_DEL_INTERES_ABIERTO
"""
import csv
import datetime as dt
import io
import os
import sys
import zipfile

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import base as B  # noqa: E402
from c1_cruces import datos  # noqa: E402
from c8_regimen_estrategia import resultado_tarde  # noqa: E402

L = []


def say(x=""):
    print(x)
    L.append(x)


def pct(x):
    return "–" if x != x else f"{100 * x:.1f} %".replace(".", ",")


def dec(x, k=2):
    return f"{x:.{k}f}".replace(".", ",")


d = datos("BTCUSDT")
td_all = d["t"].astype(np.int64)
r = d["F"]["ruptura"]
s_all = np.where(r == 0, -1, np.where(r == 1, 1, 0)).astype(np.int64)
t1, _, _, _, c1, _, _ = B.cargar("BTCUSDT")
g_all, ok_all = resultado_tarde(t1.astype(np.int64), c1, td_all, s_all)
filas = []
C = sys.argv[1]
for f in sorted(os.listdir(C)):
    with zipfile.ZipFile(os.path.join(C, f)) as z:
        for row in csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8")):
            if len(row) > 2 and row[0][:1].isdigit():
                filas.append((int(dt.datetime.strptime(row[0][:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc).timestamp()), float(row[2])))
filas.sort()
to = np.array([a for a, _ in filas], np.int64)
oi = np.array([b for _, b in filas])
to, u = np.unique(to, return_index=True)
oi = oi[u]
ia = np.searchsorted(to, td_all - 600, side="right") - 1
ib = np.searchsorted(to, td_all - 1500, side="right") - 1
val = (ia >= 0) & (ib >= 0) & ((td_all - 600 - to[np.maximum(ia, 0)]) <= 600) & ((td_all - 1500 - to[np.maximum(ib, 0)]) <= 600)
with np.errstate(divide="ignore", invalid="ignore"):
    doi = np.where(val, oi[np.maximum(ia, 0)] / oi[np.maximum(ib, 0)] - 1, np.nan)
m = (s_all != 0) & ok_all & (d["tramo"] >= 0)
td, gana, tramo, DOI = td_all[m], g_all[m].astype(np.int64), d["tramo"][m], doi[m]
desde_oi = int(dt.datetime(2021, 12, 1, tzinfo=dt.timezone.utc).timestamp())
thr = np.nanpercentile(DOI[(tramo == 0) & (td >= desde_oi)], 50)
filtro_oi = np.nan_to_num(DOI, nan=1.0) <= thr
dia = (td - 18000) // 86400
v = np.where(gana == 1, 0.85, -1.0)
cum = np.r_[0.0, np.cumsum(v)]
kc = np.searchsorted(td + 660, td, side="right")          # cuántas cerradas hay antes de cada señal
a0 = np.searchsorted(td, dia * 86400 + 18000, side="left")
D = (cum[np.maximum(kc, a0)] - cum[a0]) > 0
cg = np.r_[0, np.cumsum(gana)]


def ultimas(n, minimo):
    ok = kc >= n
    aciertos = cg[kc] - cg[np.maximum(kc - n, 0)]
    return ok & (aciertos >= minimo)


hits_hoy = cg[np.maximum(kc, a0)] - cg[a0]
cerr_hoy = np.maximum(kc, a0) - a0
with np.errstate(divide="ignore", invalid="ignore"):
    G_hoy = (cerr_hoy >= 5) & (hits_hoy / np.maximum(cerr_hoy, 1) >= 0.76)


def parada(real):
    out = real.copy()
    apag, dact = None, None
    for i in range(len(td)):
        if dia[i] != dact:
            dact, apag = dia[i], None
        if apag is not None and td[i] >= apag:
            out[i] = False
            continue
        if out[i] and gana[i] == 0 and apag is None:
            apag = td[i] + 660
    return out


SI = parada(D & filtro_oi)
NOM = {0: "2021-2023", 1: "2024-sep 2026", 2: "oct 2026"}
dias = {k: len(np.unique(dia[tramo == k])) for k in NOM}
say("C9e · P17, su regla del 76 % sobre el SÍ · BTCUSDT · entrada 60 s tarde · pago 0,85 · empate = fallo")
for nombre, gate in (("SÍ actual (sin la regla del 76 %)", np.ones(len(td), bool)),
                     ("SÍ y últimas 25 con 19 o más (76 %, por defecto)", ultimas(25, 19)),
                     ("SÍ y últimas 10 con 8 o más", ultimas(10, 8)),
                     ("SÍ y últimas 50 con 38 o más", ultimas(50, 38)),
                     ("SÍ y papel de hoy con 76 % (5 cerradas o más)", G_hoy)):
    real = SI & gate
    partes = []
    for k in NOM:
        q = (tramo == k) & real
        n = int(q.sum())
        dias_on = len(np.unique(dia[q]))
        partes.append(f"{NOM[k]}: {n} apuestas en {dias_on} de {dias[k]} días, {pct(gana[q].mean() if n else float('nan'))}")
    say(f"  {nombre:<48} " + " · ".join(partes))
# la racha del papel reciente, ¿anticipa la siguiente apuesta?
for n_v, mn in ((25, 19), (10, 8)):
    g = ultimas(n_v, mn)
    q1 = (tramo == 1) & g
    say(f"  Núcleo tras {mn} de {n_v} o más: {pct(gana[q1].mean())} en {int(q1.sum())} señales de 2024-sep 2026 (sin la condición: {pct(gana[tramo == 1].mean())})")
os.makedirs(os.path.join(AQUI, "resultados"), exist_ok=True)
open(os.path.join(AQUI, "resultados", "c9e_BTCUSDT.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
