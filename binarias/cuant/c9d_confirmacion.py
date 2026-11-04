"""C9d (04/11/2026): P3b (volumen alto sobre el SÍ) y P16 (vela de confirmación), con las reglas escritas antes en
PLAN-TOTAL.md, sección 7b. Núcleo en BTCUSDT, entrada 60 s tarde salvo P16b (120 s), empate = fallo, pago 0,85.
El SÍ es P15: papel del día sumando (con todas las señales del núcleo a 60 s), ningún SÍ perdido ese día e interés abierto
que no sube (P14b, margen de 600 s en el archivo). Uso: python -I c9d_confirmacion.py CARPETA_DEL_INTERES_ABIERTO
"""
import csv
import datetime as dt
import io
import math
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

RNG = np.random.default_rng(4112028)
L = []


def say(x=""):
    print(x)
    L.append(x)


def pct(x):
    return f"{100 * x:.1f} %".replace(".", ",")


def dec(x, k=2):
    return f"{x:.{k}f}".replace(".", ",")


d = datos("BTCUSDT")
td_all = d["t"].astype(np.int64)
r = d["F"]["ruptura"]
s_all = np.where(r == 0, -1, np.where(r == 1, 1, 0)).astype(np.int64)
t1, o1, h1, l1, c1, v1, tb1 = B.cargar("BTCUSDT")
t1 = t1.astype(np.int64)
i0 = np.searchsorted(t1, td_all)  # vela de 1 min que empieza en la decisión (cierra en td + 60)
i0 = np.minimum(i0, len(t1) - 13)
ok = (t1[i0] == td_all) & (t1[i0 + 12] == td_all + 720)
g60 = (np.sign(c1[i0 + 10] - c1[i0]) == s_all).astype(np.int64)        # entra al cierre de la vela 1, sale 10 min después
g120 = (np.sign(c1[i0 + 11] - c1[i0 + 1]) == s_all).astype(np.int64)   # entra al cierre de la vela 2
conf1 = np.sign(c1[i0] - o1[i0]) == s_all
conf2 = conf1 & (np.sign(c1[i0 + 1] - o1[i0 + 1]) == s_all)
vol_alto = d["F"]["volumen"] == 2

# interés abierto (P14b)
C = sys.argv[1]
filas = []
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

m = (s_all != 0) & ok & (d["tramo"] >= 0)
td, s, tramo = td_all[m], s_all[m], d["tramo"][m]
G60, G120, CF1, CF2, VA, DOI = g60[m], g120[m], conf1[m], conf2[m], vol_alto[m], doi[m]
desde_oi = int(dt.datetime(2021, 12, 1, tzinfo=dt.timezone.utc).timestamp())
thr = np.nanpercentile(DOI[(tramo == 0) & (td >= desde_oi)], 50)
filtro_oi = np.nan_to_num(DOI, nan=1.0) <= thr
dia = (td - 18000) // 86400
dias = {k: len(np.unique(dia[tramo == k])) for k in (0, 1, 2)}

# su regla (D1) con el papel del núcleo entero a 60 s
v = np.where(G60 == 1, 0.85, -1.0)
cum = np.r_[0.0, np.cumsum(v)]
kc = np.searchsorted(td + 660, td, side="right")
a0 = np.searchsorted(td, dia * 86400 + 18000, side="left")
D = (cum[np.maximum(kc, a0)] - cum[a0]) > 0


def parada(real, gana, cierre):
    out = real.copy()
    apag, dact = None, None
    for i in range(len(td)):
        if dia[i] != dact:
            dact, apag = dia[i], None
        if apag is not None and td[i] >= apag:
            out[i] = False
            continue
        if out[i] and gana[i] == 0 and apag is None:
            apag = td[i] + cierre
    return out


SI = parada(D & filtro_oi, G60, 660)                      # P15
SI_VOL = parada(D & filtro_oi & ~VA, G60, 660)           # P15 + P3b
SI_C1 = parada(D & filtro_oi & CF1, G60, 660)            # P15 + P16
SI_C2 = parada(D & filtro_oi & CF2, G120, 720)           # P15 + P16b (entra 120 s tarde)
NOM = {0: "2021-2023", 1: "2024-sep 2026", 2: "oct 2026"}
base_n = {k: G60[tramo == k].mean() for k in NOM}


def fila(nombre, sel, gana):
    partes = []
    for k in NOM:
        q = (tramo == k) & sel
        n = int(q.sum())
        partes.append(f"{NOM[k]} {pct(gana[q].mean()) if n else '–'} ({dec(n / dias[k], 1)}/día)")
    say(f"  {nombre:<40} " + " · ".join(partes))


def p_azar(sel_base, sel_filtro, gana, k=1):
    """p de que quitar al azar la misma proporción de las apuestas de sel_base iguale o supere el acierto de sel_filtro."""
    q0 = (tramo == k) & sel_base
    q1 = (tramo == k) & sel_filtro
    N, W, n = int(q0.sum()), int(gana[q0].sum()), int(q1.sum())
    if not n:
        return float("nan")
    az = RNG.hypergeometric(W, N - W, n, size=2000) / n
    return float(np.mean(az >= gana[q1].mean()))


say("C9d · P3b (volumen alto sobre el SÍ) y P16 (vela de confirmación) · BTCUSDT · pago 0,85 · empate = fallo")
say(f"Umbral del interés abierto (P14b): {dec(thr * 100, 3)} %")
say("Sobre el núcleo:")
fila("núcleo (entrada 60 s)", np.ones(len(td), bool), G60)
fila("P16: 1 vela de confirmación (60 s)", CF1, G60)
fila("P16b: 2 velas de confirmación (120 s)", CF2, G120)
fila("núcleo entrando 120 s tarde (referencia)", np.ones(len(td), bool), G120)
pv = []
for nombre, sel, gana in (("P16", CF1, G60), ("P16b", CF2, G120)):
    q = (tramo == 1) & sel
    dif = gana[q].mean() - base_n[1]
    p = p_azar(np.ones(len(td), bool), sel, gana) if nombre == "P16" else float("nan")
    if nombre == "P16b":  # contra el núcleo entrando igual de tarde, quitando al azar la misma proporción
        p = p_azar(np.ones(len(td), bool), sel, G120)
        dif = gana[q].mean() - G120[tramo == 1].mean()
    pv.append((nombre, p, dif, q.sum() / dias[1]))
pv.sort(key=lambda z: z[1])
kmax = max([i + 1 for i, z in enumerate(pv) if z[1] <= 0.05 * (i + 1) / len(pv)] or [0])
for i, (nombre, p, dif, pd) in enumerate(pv):
    entra = i < kmax and dif >= 0.005 and pd >= 6
    say(f"  Veredicto {nombre} sobre el núcleo: {dec(dif * 100)} pts, p {dec(p, 3)}, {dec(pd, 1)}/día → {'ENTRA' if entra else 'no entra'}")
say("Sobre el SÍ (P15):")
fila("SÍ actual (P15)", SI, G60)
fila("SÍ sin volumen alto (P3b)", SI_VOL, G60)
fila("SÍ con 1 vela de confirmación (P16)", SI_C1, G60)
fila("SÍ con 2 velas de confirmación (P16b)", SI_C2, G120)
a15 = G60[(tramo == 1) & SI].mean()
for nombre, sel, gana, crit in (("P3b", SI_VOL, G60, "filtro"), ("P16", SI_C1, G60, "sí"), ("P16b", SI_C2, G120, "sí")):
    q = (tramo == 1) & sel
    acc, pd = gana[q].mean(), q.sum() / dias[1]
    if crit == "filtro":
        p = p_azar(SI, sel, G60)
        entra = acc - a15 >= 0.005 and p < 0.05 and pd >= 1
        say(f"  Veredicto {nombre} sobre el SÍ: {dec((acc - a15) * 100)} pts, p {dec(p, 3)}, {dec(pd, 1)}/día → {'ENTRA' if entra else 'no entra'}")
    else:
        entra = acc >= a15 and pd >= 1
        say(f"  Veredicto {nombre} sobre el SÍ: {pct(acc)} frente a {pct(a15)}, {dec(pd, 1)}/día → {'ENTRA' if entra else 'no entra'}")
os.makedirs(os.path.join(AQUI, "resultados"), exist_ok=True)
open(os.path.join(AQUI, "resultados", "c9d_BTCUSDT.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
