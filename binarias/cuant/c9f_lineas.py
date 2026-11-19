"""C9f · P18 (04/11/2026): las cinco líneas como filtro del SÍ. Regla escrita antes en PLAN-TOTAL.md, sección 7b (P18),
a las 13:04. Núcleo en BTCUSDT, entrada 60 s tarde, empate = fallo, pago 0,85. Las líneas salen de
graficas.cinco_lineas, el mismo código de la caja y de Pulso, sobre las 150 velas de 1 min de futuros cerradas antes de
cada decisión. El filtro se aplica antes de la parada en la primera pérdida del día.
Uso: python -I c9f_lineas.py CARPETA_DEL_INTERES_ABIERTO
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
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "dispositivos"))
import base as B  # noqa: E402
import graficas as G  # noqa: E402
from c1_cruces import datos  # noqa: E402
from c8_regimen_estrategia import resultado_tarde  # noqa: E402

L = []


def say(x=""):
    print(x, flush=True)
    L.append(x)


def pct(x):
    return "–" if x != x else f"{100 * x:.1f} %".replace(".", ",")


def pts(x):
    return f"{100 * x:+.2f}".replace(".", ",")


d = datos("BTCUSDT")
td_all = d["t"].astype(np.int64)
r = d["F"]["ruptura"]
s_all = np.where(r == 0, -1, np.where(r == 1, 1, 0)).astype(np.int64)
t1, o1, h1, l1, c1, _, _ = B.cargar("BTCUSDT")
t1 = t1.astype(np.int64)
g_all, ok_all = resultado_tarde(t1, c1, td_all, s_all)
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
td, gana, tramo, DOI, sen = td_all[m], g_all[m].astype(np.int64), d["tramo"][m], doi[m], s_all[m]
desde_oi = int(dt.datetime(2021, 12, 1, tzinfo=dt.timezone.utc).timestamp())
thr = np.nanpercentile(DOI[(tramo == 0) & (td >= desde_oi)], 50)
filtro_oi = np.nan_to_num(DOI, nan=1.0) <= thr
dia = (td - 18000) // 86400
v = np.where(gana == 1, 0.85, -1.0)
cum = np.r_[0.0, np.cumsum(v)]
kc = np.searchsorted(td + 660, td, side="right")          # cuántas cerradas hay antes de cada señal
a0 = np.searchsorted(td, dia * 86400 + 18000, side="left")
D = (cum[np.maximum(kc, a0)] - cum[a0]) > 0

# ---------------------------------------------------------------- las cinco líneas en cada señal
FA = np.zeros(len(td), bool)
FB = np.zeros(len(td), bool)
con_lineas = np.zeros(len(td), bool)
for i in range(len(td)):
    j = int(np.searchsorted(t1, td[i] - 60, side="right"))   # velas que cierran a la hora de la decisión o antes
    if j < 150 or t1[j - 1] != td[i] - 60 or t1[j - 1] - t1[j - 150] != 149 * 60:
        continue                                              # hueco en los datos: la señal queda sin líneas
    v5 = [(int(t1[k]), float(o1[k]), float(h1[k]), float(l1[k]), float(c1[k])) for k in range(j - 150, j)]
    s5 = G.cinco_lineas(v5)
    c, n = v5[-1][4], len(v5)
    tch, ps, md = s5["techo"].en(n - 1), s5["piso"].en(n - 1), s5["mitad"].en(n - 1)
    con_lineas[i] = True
    if sen[i] < 0:   # BAJA: el precio se estiró hacia arriba
        FA[i] = c > tch
        FB[i] = c > md + 0.5 * (tch - md)
    else:            # SUBE: se estiró hacia abajo
        FA[i] = c < ps
        FB[i] = c < md - 0.5 * (md - ps)
    if i % 5000 == 0:
        print(f"  … {i} de {len(td)} señales con sus líneas", flush=True)


def parada(mascara):
    """El SÍ con la parada en su primera pérdida del día (la siguiente decisión aún entra, como en vivo)."""
    out = np.zeros(len(td), bool)
    apag, dact = None, None
    for i in np.flatnonzero(mascara):
        if dia[i] != dact:
            dact, apag = dia[i], None
        if apag is not None and td[i] >= apag:
            continue
        out[i] = True
        if gana[i] == 0 and apag is None:
            apag = td[i] + 660
    return out


NOM = {0: "2021-2023", 1: "2024-sep 2026", 2: "oct 2026"}
dias = {k: len(np.unique(dia[tramo == k])) for k in NOM}


def tasa(mascara, k):
    q = (tramo == k) & mascara
    n = int(q.sum())
    return (gana[q].mean() if n else float("nan")), n


cand = D & filtro_oi
SI = parada(cand)
say("C9f · P18, las cinco líneas como filtro del SÍ · BTCUSDT · entrada 60 s tarde · pago 0,85 · empate = fallo")
say(f"  señales del núcleo: {len(td)} · con sus 150 velas completas: {int(con_lineas.sum())} (las demás no pasan el filtro)")
partes = []
for k in NOM:
    a, n = tasa(SI, k)
    partes.append(f"{NOM[k]}: {n} ({n / dias[k]:.1f}/día) {pct(a)}")
say("  SÍ actual (P15):                " + " · ".join(partes))
for nombre, F in (("A, fuera del canal", FA), ("B, mitad lejana", FB)):
    partes = []
    for k in NOM:
        a, n = tasa(F, k)
        partes.append(f"{NOM[k]}: {n} {pct(a)}")
    base_n = [pct(tasa(np.ones(len(td), bool), k)[0]) for k in NOM]
    say(f"  núcleo con {nombre:<18} " + " · ".join(partes) + f"   (núcleo sin filtro: {', '.join(base_n)})")

rng = np.random.default_rng(18)
idx_c = np.flatnonzero(cand)
pv, filas_r = {}, {}
for nombre, F in (("A", FA), ("B", FB)):
    SIf = parada(cand & F)
    acc = {k: tasa(SIf, k) for k in NOM}
    acc0 = {k: tasa(SI, k) for k in NOM}
    k_keep = int((cand & F).sum())
    azar = np.empty(2000)
    for b in range(2000):
        msk = np.zeros(len(td), bool)
        msk[rng.choice(idx_c, size=k_keep, replace=False)] = True
        azar[b] = tasa(parada(msk), 1)[0]
    pv[nombre] = float(np.mean(azar >= acc[1][0]))
    filas_r[nombre] = (acc, acc0)
    say(f"  SÍ con {nombre}: " + " · ".join(f"{NOM[k]}: {acc[k][1]} ({acc[k][1] / dias[k]:.2f}/día) {pct(acc[k][0])} [{pts(acc[k][0] - acc0[k][0])} pts]" for k in NOM)
        + f" · p frente a 2.000 sorteos: {pv[nombre]:.3f}")
orden = sorted(pv, key=pv.get)
bh = {orden[0]: pv[orden[0]] * 2, orden[1]: max(pv[orden[1]], pv[orden[0]] * 2)}
say("Veredicto según la regla escrita (P18):")
alguna = False
for nombre in ("A", "B"):
    acc, acc0 = filas_r[nombre]
    sube = acc[1][0] - acc0[1][0]
    por_dia = acc[1][1] / dias[1]
    c1_ = sube >= 0.005
    c2_ = bh[nombre] < 0.05
    c3_ = por_dia >= 1.0
    c4_ = (acc[0][0] - acc0[0][0]) > -0.01 and (acc[2][0] - acc0[2][0]) > -0.01
    entra = c1_ and c2_ and c3_ and c4_
    alguna |= entra
    say(f"  {nombre}: sube {pts(sube)} pts ({'sí' if c1_ else 'no'} llega a +0,50) · p con Benjamini-Hochberg {bh[nombre]:.3f} "
        f"({'sí' if c2_ else 'no'} < 0,05) · {por_dia:.2f} SÍ al día ({'sí' if c3_ else 'no'} ≥ 1) · otros tramos "
        f"({'sin' if c4_ else 'con'} caída de 1 punto) → {'ENTRA' if entra else 'NO ENTRA'}")
say("  Resultado: " + ("entra al SÍ (semáforo v3.4)." if alguna else "ninguna entra; las cinco líneas quedan solo para mirar."))
os.makedirs(os.path.join(AQUI, "resultados"), exist_ok=True)
open(os.path.join(AQUI, "resultados", "c9f_BTCUSDT.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
