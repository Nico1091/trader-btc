"""Paridad del Centro de estrategias con cuant/c12_estudio_06nov.py, sin red. Uso: python -I prueba_centro.py

Toma 40 días de velas guardadas de 1 min, calcula las cinco con centro.py (Python puro) y con el código de c12 copiado en numpy,
y compara señal por señal. Luego corre el papel del centro y lo compara con sin_solape + gana_tarde de c12."""
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "dispositivos"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np  # noqa: E402
from numpy.lib.stride_tricks import sliding_window_view  # noqa: E402

import centro as CE  # noqa: E402
import graficas as G  # noqa: E402

fallos = 0


def ver(nombre, cond):
    global fallos
    print(("bien " if cond else "FALLA") + " · " + nombre)
    fallos += 0 if cond else 1


a = np.load(os.path.join(os.path.dirname(AQUI), "datos", "BTCUSDT_um_1m_tb.npy"), mmap_mode="r")[-40 * 1440:]
t1 = (a[:, 0] // 1000).astype(np.int64)
o1, h1, l1, c1 = (np.ascontiguousarray(a[:, k]) for k in (1, 2, 3, 4))
v1 = [(int(t), float(o), float(h), float(lo), float(c)) for t, o, h, lo, c in zip(t1, o1, h1, l1, c1)]


# ---------------------------------------------------------------- c12, copiado tal cual
def agrupar(seg):
    k = t1 // seg
    ini = np.r_[0, np.flatnonzero(np.diff(k)) + 1]
    fin = np.r_[ini[1:], len(t1)] - 1
    H, Lo = np.maximum.reduceat(h1, ini), np.minimum.reduceat(l1, ini)
    ok = (fin - ini) == seg // 60 - 1
    return (t1[ini][ok] + seg).astype(np.int64), o1[ini][ok], H[ok], Lo[ok], c1[fin][ok]


def media(x, n):
    c = np.cumsum(np.insert(x, 0, 0.0))
    out = np.full(len(x), np.nan)
    out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def ema(x, n):
    al, out = 2 / (n + 1), np.empty(len(x))
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = al * x[i] + (1 - al) * out[i - 1]
    return out


def rsi(c, n=14):
    d = np.diff(c, prepend=c[0])
    su, ba = np.maximum(d, 0), np.maximum(-d, 0)
    x, y, out = su[1:n + 1].mean(), ba[1:n + 1].mean(), np.full(len(c), 50.0)
    for i in range(n + 1, len(c)):
        x, y = (x * (n - 1) + su[i]) / n, (y * (n - 1) + ba[i]) / n
        out[i] = 100.0 if y == 0 else 100 - 100 / (1 + x / y)
    return out


def sin_solape(td, s, H):
    orden = np.argsort(td, kind="stable")
    td, s = td[orden], s[orden]
    ks, fin = [], -1
    for i, x in enumerate(td.tolist()):
        if x >= fin:
            ks.append(i)
            fin = x + 60 + H * 60
    return td[ks], s[ks]


def gana_tarde(td, s, H):
    i = np.searchsorted(t1, td)
    ok = i + H < len(t1)
    i2 = np.minimum(i, len(t1) - H - 1)
    ok &= (t1[i2] == td) & (t1[i2 + H] == td + H * 60)
    return (np.sign(c1[i2 + H] - c1[i2]) == s).astype(int), ok


T15, O, H, Lw, C = agrupar(900)
sma, dev = media(C, 20), np.full(len(C), np.nan)
dev[19:] = sliding_window_view(C, 20).std(axis=1)
up, lo = sma + 2 * dev, sma - 2 * dev
ancho = (up - lo) / sma
q20 = np.full(len(C), np.nan)
q20[95 + 19:] = np.quantile(sliding_window_view(ancho[19:], 96), 0.20, axis=1)
minimo5 = np.full(len(C), np.nan)
minimo5[5 + 19:] = sliding_window_view(ancho[19:], 5).min(axis=1)[:-1]
compresion = minimo5 <= np.roll(q20, 1)
R = rsi(C)
rango = np.where(H > Lw, H - Lw, np.nan)
with np.errstate(invalid="ignore"):
    fuerte = np.abs(C - O) / rango >= 0.6
g1u = compresion & (C > up) & (C > O) & fuerte & (R >= 55)
g1d = compresion & (C < lo) & (C < O) & fuerte & (R <= 45)
e50 = ema(C, 50)
macd = ema(C, 12) - ema(C, 26)
sen = ema(macd, 9)
sobre = media((C > e50).astype(float), 20)
bajo3 = np.r_[np.full(2, np.nan), sliding_window_view(Lw, 3).min(axis=1)]
alto3 = np.r_[np.full(2, np.nan), sliding_window_view(H, 3).max(axis=1)]
cruce_u = np.r_[False, (macd[1:] > sen[1:]) & (macd[:-1] <= sen[:-1])]
cruce_d = np.r_[False, (macd[1:] < sen[1:]) & (macd[:-1] >= sen[:-1])]
sube_e = np.r_[np.zeros(5, bool), e50[5:] > e50[:-5]]
g3u = (sobre >= 0.8) & sube_e & (bajo3 <= e50 * 1.001) & cruce_u & (C > e50)
g3d = (sobre <= 0.2) & ~sube_e & (alto3 >= e50 * 0.999) & cruce_d & (C < e50)
T5, O5, H5, L5, C5 = agrupar(300)
ref = {}
for N, k in ((20, "E1"), (50, "E2")):
    mx = np.r_[np.full(N, np.nan), sliding_window_view(H5, N).max(axis=1)[:-1]]
    mn = np.r_[np.full(N, np.nan), sliding_window_view(L5, N).min(axis=1)[:-1]]
    ru, rd = C5 > mx, C5 < mn
    w = ru | rd
    ref[k] = {(int(t), -1 if u else 1) for t, u in zip(T5[w], ru[w])}
ref["E3"] = {(int(t), -1 if u else 1) for t, u in zip(T15[g1u | g1d], g1u[g1u | g1d])}
ref["E4"] = {(int(t), -1 if u else 1) for t, u in zip(T15[g3u | g3d], g3u[g3u | g3d])}

# E5 como N2 de c12, en los últimos 3 días
hl, ll, cl = h1.tolist(), l1.tolist(), c1.tolist()
fin5 = np.searchsorted(t1, T5 - 60)
fin5 = fin5[(t1[fin5] == T5 - 60) & (fin5 >= 149)]
fin5 = fin5[t1[fin5] >= t1[-1] - 3 * 86400]
techo_rech, piso_rech = set(), set()
for i in fin5.tolist():
    r = G.cinco_lineas([(0, 0, x, y) for x, y in zip(hl[i - 149:i + 1], ll[i - 149:i + 1])])
    if not r:
        continue
    c0, c9, h0, l0, td = cl[i], cl[i - 1], hl[i], ll[i], int(t1[i]) + 60
    ya, antes = r["techo"].en(149), r["techo"].en(148)
    if c0 > ya and c9 <= antes:
        pass
    elif h0 >= ya and c0 < ya:
        techo_rech.add(td)
    ya, antes = r["piso"].en(149), r["piso"].en(148)
    if c0 < ya and c9 >= antes:
        pass
    elif l0 <= ya and c0 > ya:
        piso_rech.add(td)
ref["E5"] = {(t, -1) for t in techo_rech - piso_rech} | {(t, 1) for t in piso_rech - techo_rech}

# ---------------------------------------------------------------- centro.py
inicio = time.time()
v5 = CE.agrupar(v1, 300)
v15 = CE.agrupar(v1, 900)
ver(f"velas de 5 min iguales a c12 ({len(v5)})", [x[0] for x in v5] == T5.tolist() and np.allclose([x[2] for x in v5], H5))
ver(f"velas de 15 min iguales a c12 ({len(v15)})", [x[0] for x in v15] == T15.tolist() and np.allclose([x[4] for x in v15], C))
ind = CE.indicadores15(v15)
ver("bandas de Bollinger iguales (1e-6)", np.allclose(np.array(ind["up"], float), up, equal_nan=True, rtol=1e-9, atol=1e-6))
ver("cuantil 20 % del ancho igual", np.allclose(np.array(ind["q20"], float), q20, equal_nan=True, rtol=1e-9, atol=1e-12))
ver("RSI igual", np.allclose(ind["rsi"], R, rtol=1e-9, atol=1e-9))
ver("EMA 50, MACD y señal iguales", np.allclose(ind["e50"], e50) and np.allclose(ind["macd"], macd) and np.allclose(ind["sen"], sen))
mio = {k: set() for k in CE.IDS}
for j, x in enumerate(v5):
    for k, n in (("E1", 20), ("E2", 50)):
        s = CE.ruptura(v5, j, n)
        if s:
            mio[k].add((x[0], s))
for i, x in enumerate(v15):
    s3, s4 = CE.e3_e4(ind, i)
    if s3:
        mio["E3"].add((x[0], s3))
    if s4:
        mio["E4"].add((x[0], s4))
idx = {x[0]: i for i, x in enumerate(v1)}
for x in v5:
    i = idx.get(x[0] - 60)
    if i is not None and x[0] - 60 >= v1[-1][0] - 3 * 86400:
        s, _ = CE.e5(v1, i)
        if s:
            mio["E5"].add((x[0], s))
for k in CE.IDS:
    dif = mio[k] ^ ref[k]
    ver(f"{k}: {len(ref[k])} señales de c12, {len(mio[k])} del centro, {len(dif)} distintas", not dif)
print(f"(señales del centro en {time.time() - inicio:.1f} s)")


# ---------------------------------------------------------------- el papel del centro contra sin_solape + gana_tarde
class Falsa:
    @staticmethod
    def historial(dias):
        return v1

    @staticmethod
    def cambio_interes(t):
        return 0.0


ce = CE.Centro(Falsa)
CE.ARCHIVO = os.path.join(os.environ.get("TEMP", AQUI), "centro_prueba.json")
ce.ops, ce.ultimo5 = {k: [] for k in CE.IDS}, 0
ahora_real = time.time
time.time = lambda: v1[-1][0] + 120.0
try:
    ce.sembrar()
finally:
    time.time = ahora_real
for k in ("E1", "E2", "E3", "E4"):
    td = np.array(sorted(t for t, _ in ref[k]), np.int64)
    s = np.array([dict(ref[k])[t] for t in td], np.int64)
    td, s = sin_solape(td, s, 15)
    g, ok = gana_tarde(td, s, 15)
    cerradas = [o for o in ce.ops[k] if o["res"] is not None]
    ver(f"papel {k}: c12 {int(g[ok].sum())} de {int(ok.sum())}, centro {sum(1 for o in cerradas if o['res'] == 1)} de {len(cerradas)}",
        int(ok.sum()) == len(cerradas) and int(g[ok].sum()) == sum(1 for o in cerradas if o["res"] == 1))
r = ce._resumen("E1", v1[-1][0] + 120)
ver("resumen: 25 en la ventana y puntos de 0 y 1", r["n25"] == 25 and set(r["puntos"]) <= {0, 1} and len(r["puntos"]) == 25)
ver("21 de 25 con 57,7 % de fondo sale por azar menos de 1 de cada 100", CE.cola(21, 25, 0.577) < 0.01)
ver("Wilson de 55 de 100 entre 45 y 55", 45 < CE.wilson(55, 100) < 55)
foto = ce._foto(None, v1[-1][0] + 120)
ver("la foto trae las cinco con indicadores y qué hace", foto["listo"] and len(foto["estrategias"]) == 5 and all(e["que_hace"] for e in foto["estrategias"]))
ver("la gráfica trae 97 velas, canales, bandas y líneas", len(foto["grafica"]["velas"]) >= 96 and foto["grafica"]["boll"] and foto["grafica"]["lineas"])
sint = []
for i in range(150):
    alto = 100.5 if i in (20, 60, 100) else 99.9
    bajo = 99.0 if i in (30, 70, 110) else 99.6
    sint.append((1794000000 + 60 * i, 99.8, alto, bajo, 99.8))
vd = CE.verdes(sint)
ver("verde de tres toques arriba en 100,5 con 3 toques", vd.get("verde_techo", [0, 0, 0, 0, 0])[1] == 100.5 and vd["verde_techo"][4] == 3)
ver("verde de tres toques abajo en 99 y la mitad en 99,75", vd.get("verde_piso", [0, 0])[1] == 99.0 and vd.get("verde_mitad", [0, 0])[1] == 99.75)
sint[105] = (sint[105][0], 99.8, 100.9, 99.6, 100.8)  # un cierre por encima rompe el nivel: ya no es techo
ver("con un cierre por encima, 100,5 deja de ser el techo verde", CE.verdes(sint).get("verde_techo", [0, 0])[1] != 100.5)
print("FALLOS:", fallos)
sys.exit(1 if fallos else 0)
