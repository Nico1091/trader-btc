"""C12 · P21 (06/11/2026): estudio operativo de su pedido por Telegram. Regla escrita antes en PLAN-TOTAL.md, sección 7b.
Mide las tres estrategias de Gemini (G1, G2, G3), su ruptura con parámetros limitados (N1), los vectores de sus líneas (N2)
y los tres toques en el máximo exacto (N3). Solo lee datos: no toca la caja, el teléfono, la Mesa ni el SÍ.
Entrada 60 s tarde, sin solapar plazos, empate = fallo. Uso: python -X utf8 c12_estudio_06nov.py
"""
import datetime as dt
import math
import os
import sys
import time

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "dispositivos"))
import base as B  # noqa: E402
import graficas as G  # noqa: E402

EQ_MESA, EQ_EVENTO = 0.51 / 0.98, 1 / 1.85
PLAZOS = (10, 15, 30)
TR = {k: (B._ts(a), B._ts(b)) for k, (a, b) in B.TRAMOS.items()}
L = []


def say(x=""):
    print(x, flush=True)
    L.append(x)


def pct(x):
    return "–" if x != x else f"{100 * x:.1f} %".replace(".", ",")


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan")
    p = k / n
    den = 1 + z * z / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / den


def p_mayor_50(k, n):
    """Probabilidad de ver k o más aciertos con moneda justa (aproximación normal, suficiente para n de cientos)."""
    if n == 0:
        return 1.0
    return 0.5 * math.erfc((k - 0.5 - n / 2) / math.sqrt(n / 4) / math.sqrt(2))


t1, o1, h1, l1, c1, v1, _ = B.cargar("BTCUSDT")
t1 = t1.astype(np.int64)
m = t1 >= B._ts(dt.datetime(2020, 11, 1))
t1, o1, h1, l1, c1, v1 = t1[m], o1[m], h1[m], l1[m], c1[m], v1[m]
say(f"Datos: {len(t1)} velas de 1 min, hasta {dt.datetime.fromtimestamp(int(t1[-1]), dt.timezone.utc):%Y-%m-%d %H:%M} UTC.")


def agrupar(seg):
    """Velas completas de `seg` segundos, alineadas al reloj. Devuelve también T, el momento en que cierran."""
    k = t1 // seg
    ini = np.r_[0, np.flatnonzero(np.diff(k)) + 1]
    fin = np.r_[ini[1:], len(t1)] - 1
    H, Lo, V = np.maximum.reduceat(h1, ini), np.minimum.reduceat(l1, ini), np.add.reduceat(v1, ini)
    ok = (fin - ini) == seg // 60 - 1
    return (t1[ini][ok] + seg).astype(np.int64), o1[ini][ok], H[ok], Lo[ok], c1[fin][ok], V[ok]


def media(x, n):
    c = np.cumsum(np.insert(x, 0, 0.0))
    out = np.full(len(x), np.nan)
    out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def ema(x, n):
    a, out = 2 / (n + 1), np.empty(len(x))
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def rsi(c, n=14):
    d = np.diff(c, prepend=c[0])
    su, ba = np.maximum(d, 0), np.maximum(-d, 0)
    a, b, out = su[1:n + 1].mean(), ba[1:n + 1].mean(), np.full(len(c), 50.0)
    for i in range(n + 1, len(c)):
        a, b = (a * (n - 1) + su[i]) / n, (b * (n - 1) + ba[i]) / n
        out[i] = 100.0 if b == 0 else 100 - 100 / (1 + a / b)
    return out


def sin_solape(td, s, H):
    """Una apuesta a la vez: la siguiente solo después de cerrar la anterior."""
    orden = np.argsort(td, kind="stable")
    td, s = td[orden], s[orden]
    ks, fin = [], -1
    for i, x in enumerate(td.tolist()):
        if x >= fin:
            ks.append(i)
            fin = x + 60 + H * 60
    return td[ks], s[ks]


def gana_tarde(td, s, H):
    """Entrada = cierre del minuto que empieza en td (60 s tarde); salida H minutos después. Empate = fallo."""
    i = np.searchsorted(t1, td)
    ok = i + H < len(t1)
    i2 = np.minimum(i, len(t1) - H - 1)
    ok &= (t1[i2] == td) & (t1[i2 + H] == td + H * 60)
    return (np.sign(c1[i2 + H] - c1[i2]) == s).astype(int), ok


def por_tramo(td, s, H):
    td, s = sin_solape(np.asarray(td, np.int64), np.asarray(s, np.int64), H)
    g, ok = gana_tarde(td, s, H)
    td, g = td[ok], g[ok]
    out = {}
    for nombre, (a, b) in TR.items():
        w = (td >= a) & (td < b)
        n, k = int(w.sum()), int(g[w].sum())
        out[nombre] = (k, n, (k / n if n else float("nan")), wilson(k, n), n / max((b - a) / 86400, 1))
    out["_g"], out["_t"] = g, td
    return out


TODAS = []


def fila(nombre, td, s, plazos=PLAZOS):
    for H in plazos:
        r = por_tramo(td, s, H)
        e, p, a = r["entrenamiento"], r["prueba"], r["adelante"]
        say(f"{nombre:<26} {H:>2} min | 2021-23 {pct(e[2]):>7} ({e[1]:>6}) | 2024-sep26 {pct(p[2]):>7} ({p[1]:>6}), Wilson {pct(p[3]):>7}, {p[4]:4.1f}/día | oct-26 {pct(a[2]):>7} ({a[1]:>4})".replace(".", ","))
        TODAS.append({"nombre": nombre, "H": H, "e": e, "p": p, "a": a, "g": r["_g"], "t": r["_t"]})


# ---------------------------------------------------------------- velas de 15 min y estrategias de Gemini
T15, O, H, Lw, C, V = agrupar(900)
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
cuerpo = np.abs(C - O)
fuerte = cuerpo / rango >= 0.6
volok = V >= media(V, 96)

g1u = compresion & (C > up) & (C > O) & fuerte & (R >= 55)
g1d = compresion & (C < lo) & (C < O) & fuerte & (R <= 45)


def niveles(H4, L4, T4):
    """Pivotes de 4 h ya confirmados: arrays de nivel y del momento desde el que se pueden usar."""
    def piv(x, signo):
        w = sliding_window_view(x * signo, 7).max(axis=1)
        i = np.flatnonzero(x[3:-3] * signo == w) + 3
        return x[i], T4[i + 3]
    return piv(H4, 1), piv(L4, -1)


T4, _, H4, L4, _, _ = agrupar(14400)
(RES, TRES), (SOP, TSOP) = niveles(H4, L4, T4)
env_u = np.r_[False, (C[1:] > O[1:]) & (C[:-1] < O[:-1]) & (C[1:] >= O[:-1]) & (O[1:] <= C[:-1])]
env_d = np.r_[False, (C[1:] < O[1:]) & (C[:-1] > O[:-1]) & (C[1:] <= O[:-1]) & (O[1:] >= C[:-1])]
mecha_ab, mecha_ar = np.minimum(O, C) - Lw, H - np.maximum(O, C)
pin_u = (cuerpo > 0) & (mecha_ab >= 2 * cuerpo) & (mecha_ar <= cuerpo)
pin_d = (cuerpo > 0) & (mecha_ar >= 2 * cuerpo) & (mecha_ab <= cuerpo)


def toca_nivel(i, niv, tniv, es_soporte):
    a, b = np.searchsorted(tniv, T15[i] - 30 * 86400), np.searchsorted(tniv, T15[i], side="right")
    x = niv[a:b]
    if len(x) < 2:
        return False
    if es_soporte:
        cand = x[(Lw[i] <= x * 1.001) & (Lw[i] >= x * 0.997) & (C[i] > x)]
    else:
        cand = x[(H[i] >= x * 0.999) & (H[i] <= x * 1.003) & (C[i] < x)]
    return any((np.abs(x / y - 1) <= 0.002).sum() >= 2 for y in cand)


g2u, g2d = np.zeros(len(C), bool), np.zeros(len(C), bool)
for i in np.flatnonzero(env_u | pin_u).tolist():
    g2u[i] = toca_nivel(i, SOP, TSOP, True)
for i in np.flatnonzero(env_d | pin_d).tolist():
    g2d[i] = toca_nivel(i, RES, TRES, False)

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

say()
say("ESTRATEGIAS DE GEMINI (entrada 60 s tarde; equilibrios: Mesa 52,04 %, Evento 54,05 %)")
for nombre, u, d in (("G1 compresión+ruptura", g1u, g1d), ("G2 zona 4h+rechazo", g2u, g2d), ("G3 EMA50+MACD", g3u, g3d)):
    w = u | d
    fila(nombre, T15[w], np.where(u[w], 1, -1))
    wv = w & volok
    fila(nombre[:2] + "v con volumen", T15[wv], np.where(u[wv], 1, -1))

# ---------------------------------------------------------------- N1, su ruptura con parámetros limitados
say()
say("N1 · SU RUPTURA (vela de 5 min que cierra más allá del máximo o mínimo de N velas)")
T5, O5, H5, L5, C5, V5 = agrupar(300)
for N in (20, 50, 100):
    mx = np.r_[np.full(N, np.nan), sliding_window_view(H5, N).max(axis=1)[:-1]]
    mn = np.r_[np.full(N, np.nan), sliding_window_view(L5, N).min(axis=1)[:-1]]
    ru, rd = C5 > mx, C5 < mn
    vmed = np.r_[np.nan, media(V5, 20)[:-1]]
    for con_vol in (False, True):
        filtro = V5 >= 1.5 * vmed if con_vol else np.ones(len(C5), bool)
        w = (ru | rd) & filtro
        s = np.where(ru[w], 1, -1)
        et = f"{N} velas{' +vol' if con_vol else ''}"
        fila("a favor " + et, T5[w], s, (10, 15))
        fila("al revés " + et, T5[w], -s, (10, 15))

# ---------------------------------------------------------------- N3, tres toques en el máximo exacto
say()
say("N3 · TRES TOQUES EN EL MÁXIMO O MÍNIMO EXACTO (1 min, ventana de 150 min)")
pico = np.zeros(len(h1), bool)
valle = np.zeros(len(l1), bool)
pico[3:-3] = h1[3:-3] == sliding_window_view(h1, 7).max(axis=1)
valle[3:-3] = l1[3:-3] == sliding_window_view(l1, 7).min(axis=1)


def tres_toques(idx, y, signo, tol):
    """idx: índices de los picos en orden. signo=1 para máximos. Devuelve las decisiones (momento) al confirmarse el tercero."""
    sal, ventana, ultimo = [], [], -10 ** 9
    for i, v in zip(idx.tolist(), y[idx].tolist()):
        ventana = [(a, b) for a, b in ventana if i - a <= 150]
        cerca = [(a, b) for a, b in ventana if abs(b / v - 1) <= tol]
        toques, prev = [], None
        for a, b in cerca + [(i, v)]:
            if prev is None or a - prev >= 5:
                toques.append(a)
                prev = a
        if len(toques) >= 3 and i - ultimo > 150:
            a = toques[0]
            tope = v * (1 + signo * tol)
            sano = c1[a:i + 4].max() <= tope if signo == 1 else c1[a:i + 4].min() >= tope
            if sano:
                sal.append(int(t1[i + 3]) + 60)
                ultimo = i
        ventana.append((i, v))
    return np.array(sal, np.int64)


ip, iv = np.flatnonzero(pico), np.flatnonzero(valle)
for tol in (0.0001, 0.0002, 0.0005):
    tp, tv = tres_toques(ip, h1, 1, tol), tres_toques(iv, l1, -1, tol)
    et = f"{100 * tol:.2f} %".replace(".", ",")
    fila(f"máximo a {et}: BAJA", tp, -np.ones(len(tp), np.int64))
    fila(f"mínimo a {et}: SUBE", tv, np.ones(len(tv), np.int64))
    tt, ss = np.r_[tp, tv], np.r_[-np.ones(len(tp), np.int64), np.ones(len(tv), np.int64)]
    fila(f"los dos a {et}", tt, ss)

# ---------------------------------------------------------------- N2, vectores de sus líneas
say()
say("N2 · VECTORES DE SUS LÍNEAS: probabilidad de SUBIR tras cada hecho, 60 s tarde (2024-sep 2026; a su lado, 2021-2023)")
inicio = time.time()
HOR = (5, 10, 15, 30)
ev = {k: [] for k in ("rompe techo", "rompe piso", "rechazo en techo", "rechazo en piso", "rompe techo corto", "rompe piso corto",
                      "rechazo techo corto", "rechazo piso corto", "cruza mitad arriba", "cruza mitad abajo")}
hl, ll, cl = h1.tolist(), l1.tolist(), c1.tolist()
fin5 = np.searchsorted(t1, T5 - 60)
fin5 = fin5[(t1[fin5] == T5 - 60) & (fin5 >= 149)]
for i in fin5.tolist():
    a = i - 149
    v = [(0, 0, x, y) for x, y in zip(hl[a:i + 1], ll[a:i + 1])]  # graficas.cinco_lineas lee x[2] = máximo y x[3] = mínimo
    r = G.cinco_lineas(v)
    if not r:
        continue
    k, k1 = 149, 148
    c0, c9 = cl[i], cl[i - 1]
    h0, l0 = hl[i], ll[i]
    td = int(t1[i]) + 60

    def marca(nombre_rompe, nombre_rechazo, recta, techo):
        ya, antes = recta.en(k), recta.en(k1)
        if techo:
            if c0 > ya and c9 <= antes:
                ev[nombre_rompe].append(td)
            elif h0 >= ya and c0 < ya:
                ev[nombre_rechazo].append(td)
        else:
            if c0 < ya and c9 >= antes:
                ev[nombre_rompe].append(td)
            elif l0 <= ya and c0 > ya:
                ev[nombre_rechazo].append(td)

    marca("rompe techo", "rechazo en techo", r["techo"], True)
    marca("rompe piso", "rechazo en piso", r["piso"], False)
    marca("rompe techo corto", "rechazo techo corto", r["techo_c"], True)
    marca("rompe piso corto", "rechazo piso corto", r["piso_c"], False)
    ya, antes = r["mitad"].en(k), r["mitad"].en(k1)
    if c0 > ya and c9 <= antes:
        ev["cruza mitad arriba"].append(td)
    elif c0 < ya and c9 >= antes:
        ev["cruza mitad abajo"].append(td)
say(f"(líneas calculadas en {time.time() - inicio:.0f} s sobre {len(fin5)} cierres de 5 min)")
say(f"{'hecho':<22}{'casos':>7}" + "".join(f"{h:>6} min" for h in HOR) + "   |" + "".join(f"{h:>6} min" for h in HOR))
for nombre, lista in ev.items():
    td = np.array(lista, np.int64)
    col, col2 = [], []
    casos = 0
    for h in HOR:
        g, ok = gana_tarde(td, np.ones(len(td), np.int64), h)
        for tramo, destino in (("prueba", col), ("entrenamiento", col2)):
            a, b = TR[tramo]
            w = ok & (td >= a) & (td < b)
            destino.append(g[w].mean() if w.any() else float("nan"))
            if tramo == "prueba":
                casos = int(w.sum())
    say(f"{nombre:<22}{casos:>7}" + "".join(f"{pct(x):>10}" for x in col) + "   |" + "".join(f"{pct(x):>10}" for x in col2))
    es_sube = any(p in nombre for p in ("rompe techo", "rechazo en piso", "rechazo piso", "mitad arriba"))
    sentido = np.full(len(td), 1 if es_sube else -1, np.int64)
    fila("  apuesta: " + nombre, td, sentido, (10, 15))

# ---------------------------------------------------------------- P22, Gemini al revés (idea posterior a ver P21)
say()
say("P22 · GEMINI AL REVÉS (idea surgida al ver P21: no es una prueba a ciegas)")


def por_ventana(T, s):
    """Como la Mesa: gana si el cierre de la ventana de 15 min que abre en T queda del lado apostado frente a la apertura."""
    i = np.searchsorted(t1, T)
    ok = i + 14 < len(t1)
    i2 = np.minimum(i, len(t1) - 15)
    ok &= (t1[i2] == T) & (t1[i2 + 14] == T + 840)
    g = (np.sign(c1[i2 + 14] - o1[i2]) == s).astype(int)
    out = []
    for nombre in ("entrenamiento", "prueba", "adelante"):
        a, b = TR[nombre]
        w = ok & (T >= a) & (T < b)
        out.append((int(g[w].sum()), int(w.sum())))
    return out


for nombre, u, d in (("G1 al revés", g1u, g1d), ("G2 al revés", g2u, g2d), ("G3 al revés", g3u, g3d)):
    w = u | d
    fila(nombre, T15[w], np.where(u[w], -1, 1), (10, 15))
    r = por_ventana(T15[w], np.where(u[w], -1, 1))
    say(f"   ventana de la Mesa (sin retraso): 2021-23 {pct(r[0][0] / max(r[0][1], 1))} ({r[0][1]}), 2024-sep26 {pct(r[1][0] / max(r[1][1], 1))} ({r[1][1]}), oct-26 {pct(r[2][0] / max(r[2][1], 1))} ({r[2][1]})")
wn = (T5 % 900 == 0)
mx20 = np.r_[np.full(20, np.nan), sliding_window_view(H5, 20).max(axis=1)[:-1]]
mn20 = np.r_[np.full(20, np.nan), sliding_window_view(L5, 20).min(axis=1)[:-1]]
wa = wn & ((C5 > mx20) | (C5 < mn20))
r = por_ventana(T5[wa], np.where(C5[wa] > mx20[wa], -1, 1))
say(f"Referencia, núcleo en cierres de 15 min, ventana de la Mesa (sin retraso): 2021-23 {pct(r[0][0] / r[0][1])} ({r[0][1]}), 2024-sep26 {pct(r[1][0] / r[1][1])} ({r[1][1]}), oct-26 {pct(r[2][0] / r[2][1])} ({r[2][1]})")

# ---------------------------------------------------------------- veredicto
say()
say("VEREDICTO (la variante se elige en 2021-2023, con 200 apuestas o más; se juzga en 2024-sep 2026)")
grupos = [("G1", ("G1 compresión", "G1v")), ("G2", ("G2 zona", "G2v")), ("G3", ("G3 EMA", "G3v")), ("Gemini al revés (P22, posterior)", ("G1 al revés", "G2 al revés", "G3 al revés")), ("a favor (N1)", "a favor"), ("al revés (N1)", "al revés"), ("tres toques (N3)", ("máximo", "mínimo", "los dos")),
          ("apuestas por líneas (N2)", "  apuesta")]
for et, pref in grupos:
    pref = pref if isinstance(pref, tuple) else (pref,)
    cand = [x for x in TODAS if x["nombre"].startswith(pref) and x["e"][1] >= 200]
    if not cand:
        say(f"{et}: sin 200 apuestas en 2021-2023.")
        continue
    x = max(cand, key=lambda z: z["e"][2])
    e, p, a = x["e"], x["p"], x["a"]
    pasa = p[1] >= 200 and p[3] > EQ_MESA and e[2] > EQ_MESA and (a[2] != a[2] or a[2] >= EQ_MESA)
    say(f"{et}: «{x['nombre'].strip()}» a {x['H']} min. 2021-23 {pct(e[2])}, 2024-sep26 {pct(p[2])} ({p[1]}, Wilson {pct(p[3])}), oct-26 {pct(a[2])} ({a[1]}). {'PASA' if pasa else 'NO PASA'}.")

ps = sorted((p_mayor_50(x["p"][0], x["p"][1]), x) for x in [y for y in TODAS if y["p"][1] >= 200] for _ in [0]) if False else None
validas = [y for y in TODAS if y["p"][1] >= 200]
orden = sorted(validas, key=lambda y: p_mayor_50(y["p"][0], y["p"][1]))
M = len(orden)
limite = 0
for j, y in enumerate(orden, 1):
    if p_mayor_50(y["p"][0], y["p"][1]) <= 0.05 * j / M:
        limite = j
say()
say(f"Benjamini-Hochberg frente al 50 % en 2024-sep 2026: {limite} de {M} variantes sobreviven.")
for y in orden[:limite][:15]:
    say(f"  {y['nombre'].strip()} a {y['H']} min: {pct(y['p'][2])} en {y['p'][1]}, Wilson {pct(y['p'][3])}, oct-26 {pct(y['a'][2])}")
mejor = max(validas, key=lambda y: y["p"][2])
say(f"Acierto más alto de TODAS las variantes con 200 apuestas o más en 2024-sep 2026: {pct(mejor['p'][2])} ({mejor['nombre'].strip()}, {mejor['H']} min, {mejor['p'][1]} apuestas).")
say(f"Variantes que llegan a 82 %: {sum(y['p'][2] >= 0.82 for y in validas)}. Que llegan a 85 %: {sum(y['p'][2] >= 0.85 for y in validas)}.")

# ---------------------------------------------------------------- por qué 85 % aparece en rachas cortas
say()
say("POR QUÉ UN 85 % SE VE EN VIVO Y NO SE SOSTIENE (85,7 % son 6 de 7)")
for p in (0.50, 0.55):
    q = sum(math.comb(7, k) * p ** k * (1 - p) ** (7 - k) for k in (6, 7))
    say(f"Con {pct(p)} de acierto real, la probabilidad de sacar 6 o 7 de 7 es {pct(q)}: 1 de cada {1 / q:.0f} tandas de 7.")
g = mejor["g"]
if len(g) >= 25:
    s7 = sliding_window_view(g, 7).sum(axis=1)
    s25 = sliding_window_view(g, 25).sum(axis=1)
    say(f"En la variante más alta, {pct((s7 >= 6).mean())} de las tandas de 7 dieron 6 o más, y su mejor tanda de 25 dio {int(s25.max())} de 25 ({pct(s25.max() / 25)}), con {pct(g.mean())} en total.")

with open(os.path.join(AQUI, "resultados", "c12_BTCUSDT.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")
print("guardado en resultados/c12_BTCUSDT.txt")
