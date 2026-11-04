"""T16 (29/10/2026): todas las mezclas que se pueden probar, con 16 apuestas al día.

Pedido de Nicolás: «mezcle las que le hacen ganar y las que le hacen perder… desde dos hasta todas completas… más las E…
16 operaciones cada una». Binarias por tiempo, pago 0,85, apuesta 16 % del saldo, máximo 16 al día, una abierta a la vez, sin stop.
Las 36 de T7 con su configuración guardada, más las E con regla aplicable a BTC (E01, E03, E04, E05, E09, E12, E16, E18, E19),
ajustadas como T7: solo con 2024-26. Las mezclas se eligen con 2024-26 y se miran en el mes 29/09-28/10, que no se usó para elegir.
Con 45 estrategias hay 3,5·10^13 mezclas: se prueban todas las parejas y tríos, un crecimiento de 3 caminos hasta las 45 y
60 mezclas al azar de cada tamaño.
Uso: python -I t16_mezclas_todas.py > t16_mezclas_todas.txt"""
import importlib.util
import itertools
import json
import math
import os
import random
import sys
import time

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
_e = importlib.util.spec_from_file_location("t8", os.path.join(AQUI, "t8_prueba_directa.py"))
t8 = importlib.util.module_from_spec(_e)
_e.loader.exec_module(t8)
t7 = t8.t7
R = json.load(open(os.path.join(os.path.dirname(AQUI), "t7_resultados.json"), encoding="utf-8"))
PAGO, AP, TOPE, MIN_AP = 0.85, 0.16, 16, 100
LG, LP = math.log(1 + AP * PAGO), math.log(1 - AP)
LG2, LP2 = math.log(1 + 0.02 * PAGO), math.log(1 - 0.02)
random.seed(29102026)


# ---------------------------------------------------------------- indicadores
def ema(x, n=None, alfa=None):
    a = alfa if alfa else 2 / (n + 1)
    y = np.empty(len(x))
    y[0] = x[0]
    for i in range(1, len(x)):
        y[i] = a * x[i] + (1 - a) * y[i - 1]
    return y


def sma(x, n):
    cs = np.concatenate([[0.0], np.cumsum(x)])
    s = np.full(len(x), np.nan)
    if len(x) >= n:
        s[n - 1:] = (cs[n:] - cs[:-n]) / n
    return s


def rodante(x, n, f):
    s = np.full(len(x), np.nan)
    if len(x) >= n:
        s[n - 1:] = f(sliding_window_view(x, n), axis=1)
    return s


def cruces(a, b):
    with np.errstate(invalid="ignore"):
        arriba = (a > b) & np.r_[False, a[:-1] <= b[:-1]]
        abajo = (a < b) & np.r_[False, a[:-1] >= b[:-1]]
    return arriba, abajo


def rsi(x, n=14):
    d = np.diff(x, prepend=x[0])
    g, p = ema(np.where(d > 0, d, 0.0), alfa=1 / n), ema(np.where(d < 0, -d, 0.0), alfa=1 / n)
    return 100 - 100 / (1 + g / np.maximum(p, 1e-12))


def par(T, seg, up, dn):
    return np.r_[T[up], T[dn]] + seg, np.r_[np.ones(int(up.sum())), -np.ones(int(dn.sum()))]


# ---------------------------------------------------------------- las E con regla aplicable
def senales_E(t, o, h, l, c):
    S = {}
    T60, O60, H60, L60, C60 = t7.velas(t, o, h, l, c, 3600)
    TD, OD, HD, LD, CD = t7.velas(t, o, h, l, c, 86400)
    # E01: reglas de la MEZCLA sin clasificador (sim.py): largo si pendiente de 60 h > 0 y posición en el rango 0,35-0,65; corto si ≥ 0,90
    W = 60
    lo, hi = rodante(L60, W, np.min), rodante(H60, W, np.max)
    x = np.arange(W) - (W - 1) / 2
    pend = np.full(len(C60), np.nan)
    pend[W - 1:] = np.convolve(C60, x[::-1], "valid") / np.dot(x, x)
    with np.errstate(invalid="ignore", divide="ignore"):
        rp = (C60 - lo) / (hi - lo)
        lar = (pend > 0) & (rp >= 0.35) & (rp <= 0.65)
        cor = rp >= 0.9
    S["E01 retroceso alcista y techo extremo (1 h)"] = ("E",) + par(T60, 3600, lar, cor)
    # E03: banda de ruido: apertura 00 UTC ± media de 14 días del movimiento absoluto a la misma hora, revisada cada 30 min
    T30, O30, H30, L30, C30 = t7.velas(t, o, h, l, c, 1800)
    dia, slot = T30 // 86400, (T30 % 86400) // 1800
    d0, nd = int(dia.min()), int(dia.max() - dia.min() + 1)
    Om, Cm = np.full((nd, 48), np.nan), np.full((nd, 48), np.nan)
    Om[dia - d0, slot], Cm[dia - d0, slot] = O30, C30
    ap = Om[:, 0]
    with np.errstate(invalid="ignore", divide="ignore"):
        mov = np.abs(Cm / ap[:, None] - 1)
        sig = np.full_like(mov, np.nan)
        for i in range(14, nd):
            v = mov[i - 14:i]
            sig[i] = np.nansum(v, 0) / np.maximum(np.sum(~np.isnan(v), 0), 1)
        up, dn = Cm > ap[:, None] * (1 + sig), Cm < ap[:, None] * (1 - sig)
    upf = up & ~np.c_[np.zeros((nd, 1), bool), up[:, :-1]]
    dnf = dn & ~np.c_[np.zeros((nd, 1), bool), dn[:, :-1]]
    iu, su = np.nonzero(upf)
    idn, sdn = np.nonzero(dnf)
    S["E03 banda de ruido de Concretum (30 min)"] = ("E", np.r_[(iu + d0) * 86400 + su * 1800, (idn + d0) * 86400 + sdn * 1800] + 1800,
                                                    np.r_[np.ones(len(iu)), -np.ones(len(idn))])
    # E04: estacionalidad 21-23 UTC: sube a las 21:00 UTC
    dias = np.unique(t // 86400)
    S["E04 estacionalidad 21-23 UTC"] = ("E", dias * 86400 + 21 * 3600, np.ones(len(dias)))
    # E05: momentum de la primera media hora (00:00-00:30 UTC) apostado en la última (23:30)
    i0, i30 = np.searchsorted(t, dias * 86400), np.searchsorted(t, dias * 86400 + 1800)
    ok = (i30 < len(t)) & (i0 < len(t))
    ok[ok] &= t[i0[ok]] == dias[ok] * 86400
    S["E05 momentum de la primera media hora"] = ("E", dias[ok] * 86400 + 23 * 3600 + 1800, np.sign(c[i30[ok] - 1] - o[i0[ok]]))
    # E09: primer cierre de 15 min fuera de la apertura 00 UTC ± 0,5 ATR de 14 días
    tr = np.maximum(HD - LD, np.maximum(np.abs(HD - np.r_[np.nan, CD[:-1]]), np.abs(LD - np.r_[np.nan, CD[:-1]])))
    atr = np.r_[np.nan, sma(np.nan_to_num(tr, nan=0.0), 14)[:-1]]
    atr[:15] = np.nan
    dmap = {int(d): (float(OD[i]), float(atr[i])) for i, d in enumerate(TD // 86400)}
    T15, O15, H15, L15, C15 = t7.velas(t, o, h, l, c, 900)
    ts9, ds9, hecho = [], [], set()
    for Ti, Ci in zip(T15.tolist(), C15.tolist()):
        d = Ti // 86400
        if d in hecho or d not in dmap or Ti % 86400 >= 85500:
            continue
        a0, a1 = dmap[d]
        if a1 != a1:
            continue
        if Ci > a0 + 0.5 * a1:
            ts9.append(Ti + 900); ds9.append(1); hecho.add(d)
        elif Ci < a0 - 0.5 * a1:
            ts9.append(Ti + 900); ds9.append(-1); hecho.add(d)
    S["E09 rompimiento ATR de Concretum (15 min)"] = ("E", np.array(ts9, dtype=np.int64), np.array(ds9))
    # E12: MACD horario a favor del MACD diario del día anterior
    mh = ema(C60, 12) - ema(C60, 26)
    sh = ema(mh, 9)
    md = ema(CD, 12) - ema(CD, 26)
    hd = md - ema(md, 9)
    prev = {int(d): float(hd[i - 1]) for i, d in enumerate(TD // 86400) if i > 0}
    hdh = np.array([prev.get(int(x) // 86400, np.nan) for x in T60])
    a_, b_ = cruces(mh, sh)
    with np.errstate(invalid="ignore"):
        S["E12 MACD diario y horario"] = ("E",) + par(T60, 3600, a_ & (hdh > 0), b_ & (hdh < 0))
    # E16: cruce de EMAs en 1 h (el artículo optimiza los largos; aquí 20/50)
    S["E16 cruce de EMA 20/50 (1 h)"] = ("E",) + par(T60, 3600, *cruces(ema(C60, 20), ema(C60, 50)))
    # E18: SMA 10/200 en 4 h
    T4, O4, H4, L4, C4 = t7.velas(t, o, h, l, c, 14400)
    S["E18 SMA 10/200 (4 h)"] = ("E",) + par(T4, 14400, *cruces(sma(C4, 10), sma(C4, 200)))
    # E19: EMA 12/26 con RSI 14 en 1 h
    r14 = rsi(C60)
    a_, b_ = cruces(ema(C60, 12), ema(C60, 26))
    S["E19 EMA 12/26 con RSI 14 (1 h)"] = ("E",) + par(T60, 3600, a_ & (r14 > 50), b_ & (r14 < 50))
    return S


# ---------------------------------------------------------------- mezclas
def simular(P, sel):
    m = sel[P["k"]]
    w = lo = e = 0
    ocupado, dia, n = 0, None, 0
    dias = set()
    for a, b, r, d in zip(P["ts"][m].tolist(), P["en"][m].tolist(), P["rs"][m].tolist(), P["dy"][m].tolist()):
        if d != dia:
            dia, n = d, 0
        if n >= TOPE or a < ocupado:
            continue
        n += 1
        ocupado = b
        dias.add(d)
        if r > 0:
            w += 1
        elif r < 0:
            lo += 1
        else:
            e += 1
    return w, lo, e, len(dias)


def puntaje(x):
    w, lo = x[0], x[1]
    return w * LG + lo * LP if w + lo >= MIN_AP else -1e18


def cop(logf):
    v = 100000 * math.exp(max(min(logf, 600), -600))
    return "0" if v < 1 else f"{v:,.0f}".replace(",", ".") if v < 1e12 else f"{v:.1e}"


def main():
    t_ini = time.time()
    t, o, h, l, c, ext = t7.cargar()
    S, T5, vol5 = t7.senales(t, o, h, l, c, ext)
    ctxd = t7.contexto(t, c)
    S.update(senales_E(t, o, h, l, c))
    CONF = {e["nombre"]: e["conf"] for e in R["estrategias"]}
    t7.APUESTA, t7.CAP = 0.02, 150000.0
    nombres, filas = [], []
    for n, (g, ts, ds) in S.items():
        s = t7.preparar(np.asarray(ts, dtype=np.int64), np.asarray(ds), t, o, c, ctxd, T5, vol5)
        if not len(s["t"]):
            print(f"sin señales desde 2024: {n}")
            continue
        if n not in CONF:
            CONF[n] = t7.optimizar(n, s)[0]
        ev = t7.eventos(n, s, CONF[n])
        if not ev:
            continue
        k = len(nombres)
        nombres.append(n)
        filas += [(a, a + pl * 60, r, k) for a, _, _, r, pl, _, _ in ev]
    filas.sort()
    A = np.array(filas, dtype=np.int64)
    K = len(nombres)
    PER = {}
    for nom, (a, b) in (("2024-26", (t7.INI, t7.MES0)), ("mes", (t7.MES0, t7.MES1))):
        m = (A[:, 0] >= a) & (A[:, 0] < b)
        PER[nom] = {"ts": A[m, 0], "en": A[m, 1], "rs": A[m, 2], "k": A[m, 3], "dy": (A[m, 0] - t7.HCOL) // 86400,
                    "dias": (b - a) / 86400}
    print(f"T16 · {K} estrategias · {len(A)} señales desde 2024 · binarias por tiempo, pago {PAGO}, apuesta {AP * 100:.0f} %, "
          f"máximo {TOPE} al día, una abierta a la vez · {time.time() - t_ini:.0f} s de carga\n")
    print("== LAS E AGREGADAS (configuración elegida solo con 2024-26) ==")
    for k, n in enumerate(nombres):
        if n.startswith("E"):
            print(f"   {n}: {CONF[n]}")
    print()

    visto = {}

    def probar(mezcla):
        mezcla = tuple(sorted(mezcla))
        if mezcla not in visto:
            sel = np.zeros(K, bool)
            sel[list(mezcla)] = True
            visto[mezcla] = simular(PER["2024-26"], sel)
        return visto[mezcla]

    for k in range(K):
        probar((k,))
    for m in itertools.combinations(range(K), 2):
        probar(m)
    print(f"parejas listas: {len(visto)} mezclas · {time.time() - t_ini:.0f} s", file=sys.stderr)
    for m in itertools.combinations(range(K), 3):
        probar(m)
    print(f"tríos listos: {len(visto)} mezclas · {time.time() - t_ini:.0f} s", file=sys.stderr)
    # crecimiento: 3 caminos desde los 3 mejores tríos, agregando la que más suma hasta tenerlas todas
    caminos = [m for m, _ in sorted(((m, v) for m, v in visto.items() if len(m) == 3), key=lambda x: -puntaje(x[1]))[:3]]
    for tam in range(4, K + 1):
        nuevos = []
        for m in caminos:
            for k in range(K):
                if k not in m:
                    mm = tuple(sorted(m + (k,)))
                    nuevos.append((puntaje(probar(mm)), mm))
        nuevos.sort(reverse=True)
        caminos = []
        for _, mm in nuevos:
            if mm not in caminos:
                caminos.append(mm)
            if len(caminos) == 3:
                break
        for _ in range(60):
            probar(random.sample(range(K), tam))
    print(f"crecimiento y azar listos: {len(visto)} mezclas · {time.time() - t_ini:.0f} s", file=sys.stderr)

    mes = {}

    def en_mes(m):
        if m not in mes:
            sel = np.zeros(K, bool)
            sel[list(m)] = True
            mes[m] = simular(PER["mes"], sel)
        return mes[m]

    for m in visto:
        en_mes(m)

    def linea(m):
        a, b = visto[m], mes[m]
        def txt(x, nd):
            n = x[0] + x[1]
            ac = x[0] / n * 100 if n else float("nan")
            return (f"{x[0] + x[1] + x[2]:5d} ap ({(x[0] + x[1] + x[2]) / nd:4.1f}/día) {x[0]}-{x[1]} {ac:4.1f} % · "
                    f"16 %: {cop(x[0] * LG + x[1] * LP):>9s} · 2 %: {cop(x[0] * LG2 + x[1] * LP2):>9s}")
        return f"   2024-26: {txt(a, PER['2024-26']['dias'])}\n   mes:     {txt(b, PER['mes']['dias'])}"

    def nombres_de(m):
        return " + ".join(nombres[k][:30] for k in m)

    print(f"Mezclas probadas: {len(visto)} (todas las de 1, 2 y 3; 3 caminos de crecimiento hasta {K}; 60 al azar por tamaño)\n")
    print(f"== LAS 15 MEJORES ELEGIDAS CON 2024-26 (mínimo {MIN_AP} apuestas), Y CÓMO LES FUE EN EL MES ==")
    orden = sorted(visto, key=lambda m: -puntaje(visto[m]))
    for i, m in enumerate(orden[:15], 1):
        print(f"{i:2d}. [{len(m)}] {nombres_de(m)}\n{linea(m)}")
    print("\n== LA MEJOR DE CADA TAMAÑO (elegida con 2024-26) ==")
    for tam in sorted({len(m) for m in visto}):
        cand = [m for m in visto if len(m) == tam]
        m = max(cand, key=lambda m: puntaje(visto[m]))
        if tam <= 6 or tam % 5 == 0 or tam == K:
            print(f"[{tam}] {nombres_de(m) if tam <= 6 else '(' + str(tam) + ' estrategias)'}\n{linea(m)}")
    print("\n== LAS 10 MEJORES DEL MES (elegidas mirando el mes: así se ve el engaño de elegir después) ==")
    orden_mes = sorted(mes, key=lambda m: -(mes[m][0] * LG + mes[m][1] * LP if mes[m][0] + mes[m][1] >= 20 else -1e18))
    for i, m in enumerate(orden_mes[:10], 1):
        print(f"{i:2d}. [{len(m)}] {nombres_de(m)[:200]}\n{linea(m)}")
    todas = tuple(range(K))
    print(f"\n== LAS {K} JUNTAS ==\n{linea(todas)}")
    json.dump({"estrategias": nombres, "conf": {n: CONF[n] for n in nombres},
               "mejores": [{"mezcla": [nombres[k] for k in m], "ent": visto[m], "mes": mes[m]} for m in orden[:30]]},
              open(os.path.join(AQUI, "t16_resultados.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n{time.time() - t_ini:.0f} s en total", file=sys.stderr)


if __name__ == "__main__":
    main()
