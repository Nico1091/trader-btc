"""C9c · P14 (04/11/2026): ¿la devolución acierta más cuando el estirón vino con cierres forzados (interés abierto que cae)?

Regla escrita antes de bajar los datos en PLAN-TOTAL.md, sección 7b (P14). Interés abierto de futuros de BTCUSDT cada
5 min, de data.binance.vision (conexión normal a Binance). En cada señal del núcleo: cambio del interés abierto en los
15 min previos, con 5 min de margen (instantánea con hora <= decisión - 300 s, frente a la de <= decisión - 1.200 s).
Variantes: apostar solo si el cambio está por debajo del percentil 50 o 30 de dic 2021-2023. Juicio en 2024-sep 2026 y
octubre de 2026: +0,5 puntos o más, p < 0,05 frente a filtros al azar y Benjamini-Hochberg entre las dos, 6+ apuestas al día.
Uso: python -I c9c_interes.py CARPETA_DE_DESCARGA
"""
import csv
import datetime as dt
import io
import math
import os
import sys
import time
import urllib.request
import zipfile

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import base as B  # noqa: E402
from c1_cruces import datos  # noqa: E402
from c8_regimen_estrategia import resultado_tarde  # noqa: E402

URL = "https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-{}.zip"
CARPETA = sys.argv[1]
MARGEN = int(sys.argv[2]) if len(sys.argv) > 2 else 300  # P14: 300 s; P14b (04/11 00:31): 600 s por el desfase de 5 min del archivo
os.makedirs(CARPETA, exist_ok=True)
RNG = np.random.default_rng(4112027)


def pct(x):
    return f"{100 * x:.1f} %".replace(".", ",")


def dec(x, k=2):
    return f"{x:.{k}f}".replace(".", ",")


dia = dt.date(2021, 12, 1)
fin = dt.date(2026, 10, 31)
filas, faltan = [], []
while dia <= fin:
    ruta = os.path.join(CARPETA, f"BTCUSDT-metrics-{dia:%Y-%m-%d}.zip")
    if not os.path.exists(ruta):
        for intento in range(3):
            try:
                req = urllib.request.Request(URL.format(f"{dia:%Y-%m-%d}"), headers={"User-Agent": "binarias-c9c"})
                contenido = urllib.request.urlopen(req, timeout=40).read()
                with open(ruta + ".tmp", "wb") as f:
                    f.write(contenido)
                os.replace(ruta + ".tmp", ruta)
                break
            except Exception:
                time.sleep(2 * (intento + 1))
    if os.path.exists(ruta):
        with zipfile.ZipFile(ruta) as z:
            for fila in csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8")):
                if len(fila) < 3 or not fila[0][:1].isdigit():
                    continue
                try:
                    t = int(dt.datetime.strptime(fila[0][:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc).timestamp())
                    filas.append((t, float(fila[2])))
                except ValueError:
                    continue
    else:
        faltan.append(f"{dia:%Y-%m-%d}")
    dia += dt.timedelta(days=1)
filas.sort()
to = np.array([f[0] for f in filas], dtype=np.int64)
oi = np.array([f[1] for f in filas], dtype=np.float64)
to, u = np.unique(to, return_index=True)
oi = oi[u]
print(f"interés abierto: {len(to):,} instantáneas de 5 min; días que faltan: {len(faltan)}".replace(",", "."))

d = datos("BTCUSDT")
r = d["F"]["ruptura"]
s_all = np.where(r == 0, -1, np.where(r == 1, 1, 0)).astype(np.int64)
td_all = d["t"].astype(np.int64)
t1, _, _, _, c1, _, _ = B.cargar("BTCUSDT")
g_all, ok_all = resultado_tarde(t1.astype(np.int64), c1, td_all, s_all)
ia = np.searchsorted(to, td_all - MARGEN, side="right") - 1
ib = np.searchsorted(to, td_all - MARGEN - 900, side="right") - 1
valido = (ia >= 0) & (ib >= 0) & ((td_all - MARGEN - to[np.maximum(ia, 0)]) <= 600) & ((td_all - MARGEN - 900 - to[np.maximum(ib, 0)]) <= 600)
print(f"margen {MARGEN} s")
with np.errstate(divide="ignore", invalid="ignore"):
    doi = np.where(valido, oi[np.maximum(ia, 0)] / oi[np.maximum(ib, 0)] - 1, np.nan)
m = (s_all != 0) & ok_all & valido & (td_all >= int(dt.datetime(2021, 12, 1, tzinfo=dt.timezone.utc).timestamp()))
tramo, gana, x = d["tramo"][m], g_all[m].astype(np.int64), doi[m]
dias = {k: len(np.unique((td_all[m][tramo == k] - 18000) // 86400)) for k in (0, 1, 2)}
base = {k: gana[tramo == k].mean() for k in (0, 1, 2)}
print(f"señales con interés abierto: dic 2021-2023 {(tramo == 0).sum():,} ({pct(base[0])}); 2024-sep 2026 {(tramo == 1).sum():,} ({pct(base[1])}); oct 2026 {(tramo == 2).sum():,} ({pct(base[2])})".replace(",", "§").replace("§", ".", 3).replace("§", ","))
pvs = []
for pc in (50, 30):
    thr = np.nanpercentile(x[tramo == 0], pc)
    keep = x <= thr
    linea = [f"P14 percentil {pc} (cambio <= {dec(100 * thr, 3)} %)"]
    for k in (0, 1, 2):
        sel = tramo == k
        q = sel & keep
        n, N, W = int(q.sum()), int(sel.sum()), int(gana[sel].sum())
        acc = gana[q].mean()
        az = RNG.hypergeometric(W, N - W, n, size=2000) / n
        p = float(np.mean(az >= acc))
        linea.append(f"{['elegir', 'juzgar', 'oct'][k]} {pct(acc)} ({dec(n / dias[k], 1)}/día, {dec(100 * (acc - base[k]))} pts, p {dec(p, 3)})")
        if k == 1:
            pvs.append((pc, p, acc - base[1], n / dias[1]))
    print(" · ".join(linea))
# contraste: el lado contrario (interés abierto que sube), solo informativo
thr = np.nanpercentile(x[tramo == 0], 50)
for k in (0, 1, 2):
    q = (tramo == k) & (x > thr)
    print(f"  informativo, interés abierto que sube (sobre el percentil 50), {['elegir', 'juzgar', 'oct'][k]}: {pct(gana[q].mean())} en {int(q.sum())}")
pvs.sort(key=lambda z: z[1])
k_max = max([i + 1 for i, z in enumerate(pvs) if z[1] <= 0.05 * (i + 1) / len(pvs)] or [0])
for i, (pc, p, dif, pdia) in enumerate(pvs):
    entra = i < k_max and dif >= 0.005 and pdia >= 6
    print(f"Veredicto P14 percentil {pc}: {dec(100 * dif)} pts, p {dec(p, 3)}, {dec(pdia, 1)}/día → {'ENTRA' if entra else 'no entra'}")
