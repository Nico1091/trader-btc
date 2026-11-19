"""C9b · P13 (04/11/2026): ¿cambia el resultado del núcleo si se liquida con el índice de precio de Binance?

Los Contratos de Evento se liquidan con el índice de precio (página de Binance, actualizada el 28/10/2026), no con el
último precio de futuros que usa el centinela. Regla escrita antes en PLAN-TOTAL.md, sección 7b (P13): se mide en
2024-sep 2026 cuántas señales cambian de resultado; si el acierto cambia 0,3 puntos o más, el papel pasa a medirse con
el índice. Las velas del índice salen de data.binance.vision (conexión normal a Binance, permitida por su regla).
Uso: python -I c9b_indice.py CARPETA_DE_DESCARGA
"""
import csv
import io
import os
import sys
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

URL = "https://data.binance.vision/data/futures/um/monthly/indexPriceKlines/BTCUSDT/1m/BTCUSDT-1m-{:04d}-{:02d}.zip"
CARPETA = sys.argv[1]
os.makedirs(CARPETA, exist_ok=True)
meses = [(a, m) for a in (2024, 2025, 2026) for m in range(1, 13) if (a, m) <= (2026, 10)]
filas = []
for a, m in meses:
    ruta = os.path.join(CARPETA, f"BTCUSDT-indice-1m-{a:04d}-{m:02d}.zip")
    if not os.path.exists(ruta):
        req = urllib.request.Request(URL.format(a, m), headers={"User-Agent": "binarias-c9b"})
        datos_zip = urllib.request.urlopen(req, timeout=60).read()
        with open(ruta + ".tmp", "wb") as f:
            f.write(datos_zip)
        os.replace(ruta + ".tmp", ruta)
    with zipfile.ZipFile(ruta) as z:
        nombre = z.namelist()[0]
        texto = io.TextIOWrapper(z.open(nombre), encoding="utf-8")
        for fila in csv.reader(texto):
            if not fila or not fila[0].isdigit():
                continue  # cabecera
            filas.append((int(fila[0]) // 1000, float(fila[4])))
filas.sort()
ti = np.array([f[0] for f in filas], dtype=np.int64)
ci = np.array([f[1] for f in filas], dtype=np.float64)
ti, u = np.unique(ti, return_index=True)
ci = ci[u]
print(f"índice: {len(ti):,} velas de 1 min".replace(",", "."))

d = datos("BTCUSDT")
r = d["F"]["ruptura"]
s_all = np.where(r == 0, -1, np.where(r == 1, 1, 0)).astype(np.int64)
td_all = d["t"].astype(np.int64)
t1, _, _, _, c1, _, _ = B.cargar("BTCUSDT")
g_ult, ok_ult = resultado_tarde(t1.astype(np.int64), c1, td_all, s_all)
g_idx, ok_idx = resultado_tarde(ti, ci, td_all, s_all)
i_ent = np.clip(np.searchsorted(ti, td_all), 0, len(ti) - 11)
empate_idx = (ci[i_ent + 10] == ci[i_ent])
i_e1 = np.clip(np.searchsorted(t1, td_all), 0, len(t1) - 11)
empate_ult = (c1[i_e1 + 10] == c1[i_e1])
for k, nom in ((1, "2024-sep 2026"), (2, "oct 2026")):
    m = (s_all != 0) & ok_ult & ok_idx & (d["tramo"] == k)
    n = int(m.sum())
    a_u, a_i = g_ult[m].mean(), g_idx[m].mean()
    cambia = float(np.mean(g_ult[m] != g_idx[m]))
    print(f"{nom}: {n:,} señales · último precio de futuros {100 * a_u:.2f} % · índice {100 * a_i:.2f} % · diferencia {100 * (a_i - a_u):+.2f} pts · "
          f"cambian de resultado {100 * cambia:.1f} % · empates con el último precio {int(empate_ult[m].sum())}, con el índice {int(empate_idx[m].sum())}"
          .replace(",", "§").replace(".", ",").replace("§", "."))
