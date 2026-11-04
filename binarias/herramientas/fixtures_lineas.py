"""Ventanas fijas de 150 velas de 1 min para la paridad de las cinco líneas (04/11/2026).

Saca 10 ventanas de las velas de futuros de BTCUSDT (datos/BTCUSDT_um_1m_tb.npy), cada una elegida por una forma distinta,
y 2 ventanas en vivo (futuros y contado) de Binance. Las deja como CSV (t,apertura,máximo,mínimo,cierre) en
herramientas/fixtures_lineas/, con los decimales en su forma exacta (repr), para que Rust y Python lean los mismos números.
Uso: python -I fixtures_lineas.py
"""
import json
import os
import sys
import time
import urllib.request

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "fixtures_lineas")
DATOS = os.path.join(os.path.dirname(AQUI), "datos", "BTCUSDT_um_1m_tb.npy")
N = 150
os.makedirs(SALIDA, exist_ok=True)


def guardar(nombre, filas):
    with open(os.path.join(SALIDA, nombre + ".csv"), "w", encoding="utf-8", newline="\n") as f:
        f.write("t,o,h,l,c\n")
        for t, o, h, l, c in filas:
            f.write(f"{int(t)},{float(o)!r},{float(h)!r},{float(l)!r},{float(c)!r}\n")
    print("guardada", nombre, len(filas), "velas")


a = np.load(DATOS, mmap_mode="r")
# una muestra fija: el arranque de cada ventana cada 997 velas desde 2022 (determinista, sin azar)
t = (a[:, 0] // 1000).astype(np.int64)
ini = int(np.searchsorted(t, 1640995200))  # 01/01/2022
idx = np.arange(ini, len(a) - N, 997)
H, L, C = a[:, 2], a[:, 3], a[:, 4]
ventanas = np.stack([np.arange(i, i + N) for i in idx])
ret = C[ventanas[:, -1]] - C[ventanas[:, 0]]
rango = H[ventanas].max(axis=1) - L[ventanas].min(axis=1)
pos_max = H[ventanas].argmax(axis=1)
pos_min = L[ventanas].argmin(axis=1)
medio = np.abs(pos_min - N // 2)
elegidas = {
    "01-subida-fuerte": int(np.argmax(ret / rango)),
    "02-caida-fuerte": int(np.argmin(ret / rango)),
    "03-maximo-en-la-ultima": int(np.flatnonzero(pos_max == N - 1)[0]),
    "04-minimo-en-la-ultima": int(np.flatnonzero(pos_min == N - 1)[0]),
    "05-maximo-en-la-147": int(np.flatnonzero(pos_max == N - 3)[0]),
    "06-plano": int(np.argmin(rango)),
    "07-v": int(np.argmin(medio + 1000 * (np.abs(ret) > rango * 0.3))),
    "08-v-invertida": int(np.argmin(np.abs(pos_max - N // 2) + 1000 * (np.abs(ret) > rango * 0.3))),
    "09-rango-grande": int(np.argmax(rango)),
    "10-cualquiera": len(idx) // 2,
}
for nombre, k in elegidas.items():
    i = int(idx[k])
    guardar(nombre, [(t[j], a[j, 1], a[j, 2], a[j, 3], a[j, 4]) for j in range(i, i + N)])

for nombre, url in (("11-vivo-futuros", "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=170"),
                    ("12-vivo-contado", "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=170")):
    x = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "binarias-paridad"}), timeout=20).read())
    ahora = int(time.time())
    v = [(int(k[0]) // 1000, float(k[1]), float(k[2]), float(k[3]), float(k[4])) for k in x if int(k[0]) // 1000 + 60 <= ahora]
    guardar(nombre, v[-N:])
