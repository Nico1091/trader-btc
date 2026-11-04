"""C9 (04/11/2026): su regla «el real solo cuando el papel esté sumando» y cuatro métodos reconocidos para la devolución.

Reglas y criterios escritos antes de ver resultados en PLAN-TOTAL.md, sección 7b (P8 a P12), el 03/11/2026 a las 23:59.
Base: el núcleo (ruptura de 20 velas de 5 min al revés en BTCUSDT), decisión cada 10 min, binaria de 10 min, entrada 60 s
tarde, empate = fallo, pago 0,85. Solo cuentan apuestas de papel ya cerradas antes de cada señal (cierran 660 s después).
Se elige en 2021-2023 (tramo 0), se juzga en 2024-sep 2026 (tramo 1) y en octubre de 2026 (tramo 2).
Solo numpy y biblioteca estándar. Uso: python -I c9_mejoras.py
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
from c1_cruces import datos  # noqa: E402
from c8_regimen_estrategia import resultado_tarde  # noqa: E402

SALIDA = os.path.join(AQUI, "resultados")
PAGO, MONTO = 0.85, 15900.0
CIERRA = 660
COL_S = -5 * 3600
SORTEOS = 2000
RNG = np.random.default_rng(4112026)
L = []


def say(x=""):
    print(x)
    L.append(x)


def pct(x):
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.1f} %".replace(".", ",")


def miles(n):
    return f"{int(n):,}".replace(",", ".")


def dec(x, k=2):
    return f"{x:.{k}f}".replace(".", ",")


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan")
    p = k / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - r) / (1 + z * z / n)


def neto_cop(g):
    return float(np.sum(np.where(g == 1, MONTO * PAGO, -MONTO)))


def caida_cop(g):
    s = np.cumsum(np.where(g == 1, MONTO * PAGO, -MONTO))
    return float(np.max(np.maximum.accumulate(np.r_[0.0, s]) - np.r_[0.0, s]))


# ---------------------------------------------------------------- datos y núcleo
d = datos("BTCUSDT")
F, X = d["F"], d["extra"]
td_all = d["t"].astype(np.int64)
r = F["ruptura"]
s_all = np.where(r == 0, -1, np.where(r == 1, 1, 0)).astype(np.int64)
t1, o1, h1, l1, c1, v1, tb1 = B.cargar("BTCUSDT")
t1 = t1.astype(np.int64)
g_all, ok_all = resultado_tarde(t1, c1, td_all, s_all)

# autocorrelación de los tramos de 10 min (P10), con todas las decisiones, sin mirar adelante
lp = np.log(X["precio"].astype(np.float64))
r10 = np.r_[np.nan, np.diff(lp)]
r10[np.r_[False, np.diff(td_all) != 600]] = np.nan
r10 = np.nan_to_num(r10)


def autocorr(x, w):
    a, b = x[1:], x[:-1]
    def roll(z):
        c = np.cumsum(np.r_[0.0, z])
        out = np.full(len(z), np.nan)
        out[w - 1:] = (c[w:] - c[:-w]) / w
        return out
    ma, mb, mab, maa, mbb = roll(a), roll(b), roll(a * b), roll(a * a), roll(b * b)
    cov = mab - ma * mb
    den = np.sqrt(np.maximum(maa - ma * ma, 1e-30) * np.maximum(mbb - mb * mb, 1e-30))
    return np.r_[np.nan, cov / den]


ac24, ac72 = autocorr(r10, 144), autocorr(r10, 432)

# tamaño de la ruptura sobre el ATR de 5 min (P12)
T5, O5, H5, L5, C5, V5, TB5, fin5 = B.velas5(t1, o1, h1, l1, c1, v1, tb1)
i_dec = np.searchsorted(t1, td_all - 60)
j5 = np.searchsorted(fin5, i_dec, side="right") - 1
prev = np.r_[C5[0], C5[:-1]]
tr = np.maximum(H5 - L5, np.maximum(np.abs(H5 - prev), np.abs(L5 - prev)))
atr = B._rolling_mean(tr, 14)
hi20 = np.r_[np.nan, B._rolling_max(H5, 20)[:-1]]
lo20 = np.r_[np.nan, B._rolling_min(L5, 20)[:-1]]
with np.errstate(divide="ignore", invalid="ignore"):
    exceso_all = np.where(s_all == -1, (C5[j5] - hi20[j5]) / atr[j5], (lo20[j5] - C5[j5]) / atr[j5])

m = (s_all != 0) & ok_all & (d["tramo"] >= 0)
td = td_all[m]
gana = g_all[m].astype(np.int64)
s = s_all[m]
tramo = d["tramo"][m]
dia = (td + COL_S) // 86400  # día de Colombia
hora = (td % 86400) // 3600  # hora UTC
NOM = {0: "2021-2023 (elegir)", 1: "2024-sep 2026 (juzgar)", 2: "oct 2026 (adelante)"}
dias_tramo = {k: len(np.unique(dia[tramo == k])) for k in NOM}

say("C9 · BTCUSDT · su regla «el papel sumando» y métodos para la devolución (entrada 60 s tarde, pago 0,85, empate = fallo)")
say(f"Núcleo: {miles(len(td))} señales de {dt.datetime.utcfromtimestamp(int(td[0])):%Y-%m-%d} a {dt.datetime.utcfromtimestamp(int(td[-1])):%Y-%m-%d}")
for k, nom in NOM.items():
    sel = tramo == k
    say(f"  {nom}: {miles(sel.sum())} señales, {dec(sel.sum() / dias_tramo[k], 1)} al día, acierto {pct(gana[sel].mean())} (Wilson {pct(wilson(gana[sel].sum(), sel.sum()))})")
base_acc = {k: gana[tramo == k].mean() for k in NOM}
say()

# ---------------------------------------------------------------- P8: su regla
v = np.where(gana == 1, PAGO, -1.0)
cum = np.r_[0.0, np.cumsum(v)]
k_cerradas = np.searchsorted(td + CIERRA, td, side="right")  # señales j con td_j + 660 <= td_i
ini_dia = dia * 86400 - COL_S


def neto_desde(t_desde):
    a = np.searchsorted(td, t_desde, side="left")
    b = np.maximum(k_cerradas, a)
    return cum[b] - cum[a]


def con_parada(real):
    """Apaga el real hasta el día siguiente cuando cierra la primera pérdida real (se sabe 660 s después)."""
    out = real.copy()
    apagado_desde = None
    dia_act = None
    for i in range(len(td)):
        if dia[i] != dia_act:
            dia_act, apagado_desde = dia[i], None
        if apagado_desde is not None and td[i] >= apagado_desde:
            out[i] = False
            continue
        if out[i] and gana[i] == 0 and apagado_desde is None:
            apagado_desde = td[i] + CIERRA
    return out


def ultimos_aciertos(k):
    res = k_cerradas >= k
    for q in range(1, k + 1):
        res = res & (gana[np.maximum(k_cerradas - q, 0)] == 1)
    return res


def semaforo_s2():
    real = np.zeros(len(td), bool)
    for dd in np.unique(dia):
        sel = np.flatnonzero(dia == dd)
        a = np.searchsorted(td + CIERRA, dd * 86400 - COL_S, side="right")
        if a >= 100 and gana[a - 100:a].mean() >= 0.58:
            real[sel] = True
    return real


VAR = {
    "D (día sumando)": neto_desde(ini_dia) > 0,
    "H2 (2 h sumando)": neto_desde(td - 2 * 3600) > 0,
    "H3 (3 h sumando)": neto_desde(td - 3 * 3600) > 0,
    "H6 (6 h sumando)": neto_desde(td - 6 * 3600) > 0,
    "R2 (2 aciertos seguidos)": ultimos_aciertos(2),
    "R3 (3 aciertos seguidos)": ultimos_aciertos(3),
}
VAR["D1 (día sumando y parada)"] = con_parada(VAR["D (día sumando)"])
VAR["S2+P1 (semáforo VERDE actual)"] = con_parada(semaforo_s2())


def azar_mismos_dias(real, k):
    sel = tramo == k
    wins = np.zeros(SORTEOS)
    n_tot = 0
    for dd in np.unique(dia[sel]):
        q = sel & (dia == dd)
        n_d = int((q & real).sum())
        if n_d == 0:
            continue
        m_d, w_d = int(q.sum()), int(gana[q].sum())
        wins += RNG.hypergeometric(w_d, m_d - w_d, n_d, size=SORTEOS)
        n_tot += n_d
    return wins / max(n_tot, 1)


def binomial_p(k, n, p0):
    """P(X >= k) con X ~ Binomial(n, p0), aproximación normal con corrección de continuidad."""
    zz = (k - 0.5 - n * p0) / math.sqrt(n * p0 * (1 - p0))
    return 0.5 * math.erfc(zz / math.sqrt(2))


say("P8 · su regla: el real solo cuando el papel esté sumando (entre corchetes, el acierto del núcleo en ese tramo y la p binomial)")
fila_p8 = {}
for nom, real in VAR.items():
    partes = []
    for k in NOM:
        q = (tramo == k) & real
        n = int(q.sum())
        acc = gana[q].mean() if n else float("nan")
        # 04/11 00:20: el sorteo «del mismo día» incluía las apuestas que volvieron positivo el día y lo inflaba; se
        # reemplaza por la prueba binomial contra el acierto del núcleo en el mismo tramo (no cambia el criterio del punto).
        az = np.array([base_acc[k]])
        p = binomial_p(int(gana[q].sum()), n, base_acc[k]) if n else float("nan")
        fila_p8[(nom, k)] = (n, acc, p, n / dias_tramo[k], neto_cop(gana[q]) if n else 0.0, caida_cop(gana[q]) if n else 0.0)
        partes.append(f"{NOM[k].split(' ')[0]}: {miles(n)} ({dec(n / dias_tramo[k], 1)}/día) {pct(acc)} [núcleo {pct(float(np.nanmean(az)))}, p {dec(p, 3)}]")
    say(f"  {nom:<31} " + " · ".join(partes))
cand = [(fila_p8[(nom, 0)][1], nom) for nom in VAR if not nom.startswith("S2") and fila_p8[(nom, 0)][3] >= 1.0]
elegida = max(cand)[1] if cand else None
say(f"  Elegida en 2021-2023: {elegida}")
if elegida:
    n1, a1, p1, dia1, neto1, caida1 = fila_p8[(elegida, 1)]
    n2, a2, p2, dia2, neto2, caida2 = fila_p8[(elegida, 2)]
    entra = (a1 >= base_acc[1] + 0.01) and (p1 < 0.05)
    say(f"  Juicio 2024-sep 2026: {pct(a1)} frente a {pct(base_acc[1])} del núcleo sin filtro; p {dec(p1, 3)} → {'ENTRA' if entra else 'NO ENTRA'}")
    say(f"  Con 5 USDT por apuesta: 2024-sep 2026 {miles(n1)} apuestas reales, neto {dec(neto1 / 1e6)} M COP, caída máxima {dec(caida1 / 1e6)} M COP; oct 2026: {n2} apuestas, {pct(a2)}, neto {dec(neto2 / 1e3, 0)} mil COP")
n_s, a_s = fila_p8[("S2+P1 (semáforo VERDE actual)", 1)][:2]
say(f"  Núcleo sin filtro, neto 2024-sep 2026: {dec(neto_cop(gana[tramo == 1]) / 1e6)} M COP; caída máxima {dec(caida_cop(gana[tramo == 1]) / 1e6)} M COP")
# ¿el signo del papel de hoy anticipa el de mañana?
neto_dia = {}
for dd in np.unique(dia):
    neto_dia[dd] = float(v[dia == dd].sum())
dd_ord = sorted(neto_dia)
x = np.array([neto_dia[a] > 0 for a, b in zip(dd_ord[:-1], dd_ord[1:]) if b == a + 1])
y = np.array([neto_dia[b] > 0 for a, b in zip(dd_ord[:-1], dd_ord[1:]) if b == a + 1])
say(f"  Días en que el papel termina sumando: {pct(np.mean([neto_dia[a] > 0 for a in dd_ord]))}. Mañana suma tras un día que sumó: {pct(y[x].mean())}; tras uno que restó: {pct(y[~x].mean())}")
say()

# ---------------------------------------------------------------- P9 a P12: filtros
pv = []  # (nombre, p, delta, apuestas por día, acc oct, n oct, pasa_umbral)


def juzgar(nombre, keep, umbral_puntos=0.005):
    res = {}
    for k in NOM:
        sel = tramo == k
        q = sel & keep
        n, N = int(q.sum()), int(sel.sum())
        acc = gana[q].mean() if n else float("nan")
        W = int(gana[sel].sum())
        az = RNG.hypergeometric(W, N - W, n, size=SORTEOS) / n if n else np.array([np.nan])
        p = float(np.mean(az >= acc)) if n else float("nan")
        res[k] = (n, acc, p, n / dias_tramo[k])
    n1, a1, p1, pd1 = res[1]
    dif = a1 - base_acc[1]
    pv.append((nombre, p1, dif, pd1, res[2][1], res[2][0], dif >= umbral_puntos and pd1 >= 6))
    say(f"  {nombre:<36} elegir {pct(res[0][1])} ({dec(res[0][3], 1)}/día) · juzgar {pct(a1)} ({dec(pd1, 1)}/día, {dec(dif * 100)} pts, p {dec(p1, 3)}) · oct {pct(res[2][1])} ({res[2][0]})")


sel0 = tramo == 0
say("P9 · flujo informado: no apostar si el desequilibrio de 15 min a favor de la ruptura supera el percentil de 2021-2023")
q_flujo = X["delta"][m] * (-s)
for pc in (50, 70, 80, 90):
    thr = np.nanpercentile(q_flujo[sel0], pc)
    juzgar(f"P9 percentil {pc}", q_flujo <= thr)
say("P10 · régimen de devolución: solo si la autocorrelación de 10 min es menor que el umbral")
for nom_ac, ac in (("24 h", ac24[m]), ("72 h", ac72[m])):
    for u in (0.0, -0.05, -0.10):
        juzgar(f"P10 {nom_ac} < {u:+.2f}", np.nan_to_num(ac, nan=1.0) < u)
say("P11 · horas")
acc_h = np.array([gana[sel0 & (hora == h)].mean() for h in range(24)])
top12 = np.argsort(acc_h)[::-1][:12]
say(f"  Las 12 horas UTC elegidas en 2021-2023: {sorted(int(h) for h in top12)} (hora de Colombia: {sorted(int((h - 5) % 24) for h in top12)})")
juzgar("P11 H12 (12 mejores horas)", np.isin(hora, top12))
# azar de horas: 12 horas al azar en el tramo de juicio
sel1 = tramo == 1
acc_rand = []
for _ in range(SORTEOS):
    hh = RNG.choice(24, 12, replace=False)
    q = sel1 & np.isin(hora, hh)
    acc_rand.append(gana[q].mean())
a_h12 = gana[sel1 & np.isin(hora, top12)].mean()
p_h12 = float(np.mean(np.array(acc_rand) >= a_h12))
say(f"    frente a 12 horas al azar en 2024-sep 2026: p {dec(p_h12, 3)}")
pv[-1] = (pv[-1][0], max(pv[-1][1], p_h12), *pv[-1][2:])
# HV: la hora cuyo papel de los últimos 30 días suma
hv = np.zeros(len(td), bool)
for h in range(24):
    idx = np.flatnonzero(hora == h)
    if not len(idx):
        continue
    cumh = np.r_[0.0, np.cumsum(v[idx])]
    a = np.searchsorted(td[idx], td[idx] - 30 * 86400, side="left")
    b = np.searchsorted(td[idx] + CIERRA, td[idx], side="right")
    b = np.maximum(b, a)
    hv[idx] = (cumh[b] - cumh[a]) > 0
juzgar("P11 HV (hora sumando en 30 días)", hv)

say("P12 · metaetiquetado: regresión logística propia sobre las señales del núcleo")
sd1 = X["sd1"][m]
def z(a, k):
    return a[m] * s / (sd1 * math.sqrt(k) + 1e-12)
ses = F["sesion"][m]
bol = F["bollinger"][m]
rasgos = np.column_stack([
    X["z15"][m] * s, X["delta"][m] * s, np.log(np.maximum(X["rv"][m], 1e-6)), np.log(np.maximum(X["razon_atr"][m], 1e-6)),
    z(X["a60"], 60), z(X["a240"], 240), z(X["a1d"], 1440), (bol == 0), (bol == 2), (ses == 1), (ses == 2), (ses == 3),
    F["finde"][m], np.nan_to_num(ac24[m]), np.clip(np.nan_to_num(exceso_all[m]), -5, 5),
    np.sin(2 * np.pi * hora / 24), np.cos(2 * np.pi * hora / 24),
]).astype(np.float64)
rasgos[~np.isfinite(rasgos)] = 0.0
anio = np.array([dt.datetime.utcfromtimestamp(int(x)).year for x in td])
ent, val = (anio >= 2021) & (anio <= 2022), anio == 2023
mu, sg = rasgos[ent].mean(0), rasgos[ent].std(0) + 1e-9
Z = np.column_stack([np.ones(len(td)), (rasgos - mu) / sg])


def logistica(A, y, lam=1.0, iters=30):
    w = np.zeros(A.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-A @ w))
        g = A.T @ (p - y) + lam * np.r_[0, w[1:]]
        Hm = (A * (p * (1 - p))[:, None]).T @ A + lam * np.diag(np.r_[0, np.ones(len(w) - 1)])
        w -= np.linalg.solve(Hm, g)
    return w


w = logistica(Z[ent], gana[ent].astype(float))
prob = 1 / (1 + np.exp(-Z @ w))
nombres_r = ["impulso 15 min", "flujo", "volumen", "ATR", "1 h", "4 h", "1 día", "Bollinger estrecho", "Bollinger ancho",
             "Europa", "EE. UU.", "cierre", "fin de semana", "autocorrelación 24 h", "tamaño de la ruptura", "hora seno", "hora coseno"]
orden = np.argsort(-np.abs(w[1:]))[:6]
say("  Pesos más fuertes (positivo = acierta más): " + "; ".join(f"{nombres_r[i]} {dec(w[1 + i], 3)}" for i in orden))
mejor = None
for frac in (0.3, 0.5, 0.7):
    cut = np.quantile(prob[val], 1 - frac)
    a_val = gana[val & (prob >= cut)].mean()
    say(f"  2023, el {int(frac * 100)} % de mayor probabilidad: {pct(a_val)} (umbral {dec(cut, 4)})")
    if mejor is None or a_val > mejor[0]:
        mejor = (a_val, frac, cut)
say(f"  Elegido en 2023: el {int(mejor[1] * 100)} % de mayor probabilidad (umbral {dec(mejor[2], 4)})")
juzgar(f"P12 metaetiquetado {int(mejor[1] * 100)} %", prob >= mejor[2], umbral_puntos=0.01)
say()

# ---------------------------------------------------------------- Benjamini-Hochberg
say("Benjamini-Hochberg (q = 0,05) entre las variantes de P9 a P12, en 2024-sep 2026:")
orden = sorted(range(len(pv)), key=lambda i: pv[i][1])
mmax = len(pv)
pasa_bh = set()
k_max = 0
for rnk, i in enumerate(orden, 1):
    if pv[i][1] <= 0.05 * rnk / mmax:
        k_max = rnk
for rnk, i in enumerate(orden, 1):
    if rnk <= k_max:
        pasa_bh.add(i)
for i in orden:
    nom, p, dif, pdia, a_oct, n_oct, umbral = pv[i]
    estado = "ENTRA" if (i in pasa_bh and umbral) else "no entra"
    say(f"  {nom:<36} p {dec(p, 3)} · {dec(dif * 100)} pts · {dec(pdia, 1)}/día · oct {pct(a_oct)} ({n_oct}) → {estado}")
os.makedirs(SALIDA, exist_ok=True)
with open(os.path.join(SALIDA, "c9_BTCUSDT.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")
print("\nGuardado en resultados/c9_BTCUSDT.txt")
