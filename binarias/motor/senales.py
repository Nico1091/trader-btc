"""Señales de las binarias: una sola fuente para las pruebas (t18 en adelante) y para el centinela en vivo.

Copia fiel de t7_mes_operado.py (grupos A y C) y de t16_mezclas_todas.py (grupo E), sin el grupo B, que depende del
motor de la T95H. La paridad con t7 y t16 se comprueba con pruebas/t18_paridad.py.
Convención: cada señal es (tiempo de entrada en s UTC, dirección +1 sube / −1 baja). El tiempo de entrada es el cierre de la
vela que la produce; la apuesta entra al abrir ese minuto."""
import bisect

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from . import patrones_std


# ---------------------------------------------------------------- indicadores
def media_previa(x, n):
    cs = np.concatenate([[0.0], np.cumsum(x)])
    m = np.full(len(x), np.nan)
    m[n:] = (cs[n:-1] - cs[:-n - 1]) / n
    return m


def sma(x, n):
    cs = np.concatenate([[0.0], np.cumsum(x)])
    s = np.full(len(x), np.nan)
    if len(x) >= n:
        s[n - 1:] = (cs[n:] - cs[:-n]) / n
    return s


def ema(x, n=None, alfa=None):
    a = alfa if alfa else 2 / (n + 1)
    y = np.empty(len(x))
    if not len(x):
        return y
    y[0] = x[0]
    for i in range(1, len(x)):
        y[i] = a * x[i] + (1 - a) * y[i - 1]
    return y


def extremo_previo(x, n, f):
    out = np.full(len(x), np.nan)
    if len(x) > n:
        out[n:] = f(sliding_window_view(x[:-1], n), axis=1)
    return out


def rodante(x, n, f):
    s = np.full(len(x), np.nan)
    if len(x) >= n:
        s[n - 1:] = f(sliding_window_view(x, n), axis=1)
    return s


def transicion(m):
    return m & ~np.r_[False, m[:-1]]


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


def velas(t, o, h, l, c, seg):
    """Agrupa velas de 1 min en velas de `seg` segundos alineadas a UTC; descarta la última si está incompleta."""
    k = seg // 60
    i0 = int(np.argmax(t % seg == 0))
    n = (len(t) - i0) // k * k
    return (t[i0:i0 + n].reshape(-1, k)[:, 0], o[i0:i0 + n].reshape(-1, k)[:, 0], h[i0:i0 + n].reshape(-1, k).max(1),
            l[i0:i0 + n].reshape(-1, k).min(1), c[i0:i0 + n].reshape(-1, k)[:, -1])


# ---------------------------------------------------------------- tres resistencias (a7, copiado tal cual)
VENTANA, TOL, K = 60, 0.25, 2


def pivotes(x, alto):
    out = []
    for i in range(K, len(x) - K):
        w = x[i - K:i + K + 1]
        if (alto and x[i] == w.max() and x[i] > x[i - 1]) or (not alto and x[i] == w.min() and x[i] < x[i - 1]):
            out.append(i)
    return out


def tres_resistencias(Hh, L, C):
    tr = np.maximum(Hh - L, np.maximum(np.abs(Hh - np.r_[C[0], C[:-1]]), np.abs(L - np.r_[C[0], C[:-1]])))
    atr = np.concatenate([[tr[0]], np.convolve(tr, np.ones(14) / 14, mode="full")[:len(tr) - 1]])
    ph, pl = pivotes(Hh, True), pivotes(L, False)
    out, libre = [], 0
    for i in range(VENTANA + 5, len(C) - 9):
        if i < libre:
            continue
        tol = TOL * atr[i]
        if tol <= 0:
            continue
        for alto, piv, ext in ((True, ph, Hh), (False, pl, L)):
            a = bisect.bisect_left(piv, i - VENTANA)
            b = bisect.bisect_right(piv, i - K - 1)
            rec = piv[a:b]
            if len(rec) < 2:
                continue
            j1 = rec[-1]
            grupo = [j for j in rec if abs(ext[j] - ext[j1]) <= tol]
            if len(grupo) < 2:
                continue
            if alto:
                zona = max(ext[j] for j in grupo)
                ok = C[min(grupo):i].max() <= zona + tol and zona - tol <= Hh[i] <= zona + tol and C[i] < zona - tol
            else:
                zona = min(ext[j] for j in grupo)
                ok = C[min(grupo):i].min() >= zona - tol and zona - tol <= L[i] <= zona + tol and C[i] > zona + tol
            if ok:
                out.append((i, -1 if alto else 1))
                libre = i + 8
                break
    return out


# ---------------------------------------------------------------- grupos A y C (t7)
def senales_AC(t, o, h, l, c):
    """Devuelve S {nombre: (grupo, tiempos, direcciones)}, T5 y vol5 (rango de 20 velas de 5 min sobre el de 500)."""
    S = {}
    T5, O5, H5, L5, C5 = velas(t, o, h, l, c, 300)
    T15, O15, H15, L15, C15 = velas(t, o, h, l, c, 900)
    P = patrones_std.patrones(O5.tolist(), H5.tolist(), L5.tolist(), C5.tolist())
    for nom, m in P.items():
        m = np.array(m)
        S[f"patrón {nom.replace('_', ' ')}"] = ("A", T5[m] + 300, np.full(int(m.sum()), patrones_std.LADO[nom]))
    for nom, (T, Hh, L, C, seg) in (("tres resistencias 5 min", (T5, H5, L5, C5, 300)), ("tres resistencias 15 min", (T15, H15, L15, C15, 900))):
        r = tres_resistencias(Hh, L, C)
        S[nom] = ("A", np.array([T[i] + seg for i, d in r], dtype=np.int64), np.array([d for i, d in r]))
    s50 = sma(C5, 50)
    with np.errstate(invalid="ignore"):
        up, dn = transicion(C5 > s50), transicion(C5 < s50)
    S["50 SMA + precio"] = ("A", np.r_[T5[up], T5[dn]] + 300, np.r_[np.ones(up.sum()), -np.ones(dn.sum())])
    m48 = sma(C5, 48)
    with np.errstate(invalid="ignore"):
        pu = transicion((m48 > np.r_[np.nan, m48[:-1]]) & (C5 > m48 * 0.995))
        pd_ = transicion((m48 < np.r_[np.nan, m48[:-1]]) & (C5 < m48 * 1.005))
    S["pendiente de la media 48 (Quantdemy)"] = ("A", np.r_[T5[pu], T5[pd_]] + 300, np.r_[np.ones(pu.sum()), -np.ones(pd_.sum())])
    e9, e21, e50 = ema(C5, 9), ema(C5, 21), ema(C5, 50)
    au, ad = transicion((e9 > e21) & (e21 > e50)), transicion((e9 < e21) & (e21 < e50))
    S["alineación de medias 9/21/50"] = ("A", np.r_[T5[au], T5[ad]] + 300, np.r_[np.ones(au.sum()), -np.ones(ad.sum())])
    s200 = sma(C5, 200)
    hi48, lo48 = extremo_previo(H5, 48, np.max), extremo_previo(L5, 48, np.min)
    with np.errstate(invalid="ignore", divide="ignore"):
        pos = (C5 - lo48) / (hi48 - lo48)
        pos1 = np.r_[np.nan, pos[:-1]]
        tend_up = (C5 > s200) & (s50 > np.r_[np.full(12, np.nan), s50[:-12]])
        tend_dn = (C5 < s200) & (s50 < np.r_[np.full(12, np.nan), s50[:-12]])
        pbu = tend_up & (pos >= 0.35) & (pos <= 0.65) & (pos1 > 0.65)
        pbd = tend_dn & (pos >= 0.35) & (pos <= 0.65) & (pos1 < 0.35)
        hi288, lo288 = extremo_previo(H5, 288, np.max), extremo_previo(L5, 288, np.min)
        p288 = (C5 - lo288) / (hi288 - lo288)
        techo, piso = transicion(p288 >= 0.9), transicion(p288 <= 0.1)
        hi20, lo20 = extremo_previo(H5, 20, np.max), extremo_previo(L5, 20, np.min)
        ru, rd = transicion(C5 > hi20), transicion(C5 < lo20)
    S["pullback en tendencia"] = ("A", np.r_[T5[pbu], T5[pbd]] + 300, np.r_[np.ones(pbu.sum()), -np.ones(pbd.sum())])
    S["techo y piso de 24 h"] = ("A", np.r_[T5[techo], T5[piso]] + 300, np.r_[-np.ones(techo.sum()), np.ones(piso.sum())])
    S["rompimiento de 20 velas"] = ("A", np.r_[T5[ru], T5[rd]] + 300, np.r_[np.ones(ru.sum()), -np.ones(rd.sum())])
    for nom, (T, O, C, seg) in (("REV5", (T5, O5, C5, 300)), ("REV15", (T15, O15, C15, 900))):
        cu = np.abs(C - O)
        with np.errstate(invalid="ignore"):
            f = cu >= 2 * media_previa(cu, 100)
        S[nom] = ("C", T[f] + seg, -np.sign(C[f] - O[f]))
    S["tres cuervos AL REVÉS"] = ("C", T5[np.array(P["tres_cuervos"])] + 300, np.ones(int(np.sum(P["tres_cuervos"]))))
    S["tres soldados AL REVÉS"] = ("C", T5[np.array(P["tres_soldados"])] + 300, -np.ones(int(np.sum(P["tres_soldados"]))))
    rng5 = H5 - L5
    with np.errstate(invalid="ignore"):
        vol5 = media_previa(rng5, 20) > media_previa(rng5, 500)
    return S, T5, vol5


def contexto(t, c):
    """Por día UTC: +1 si el cierre de ayer quedó sobre la media de los 50 cierres anteriores, −1 si quedó bajo, 0 sin datos."""
    dia = t // 86400
    ult = np.r_[np.flatnonzero(np.diff(dia)), len(dia) - 1]
    d, cd = dia[ult], c[ult]
    s = np.full(len(cd), np.nan)
    cs = np.concatenate([[0.0], np.cumsum(cd)])
    s[50:] = (cs[50:-1] - cs[:-51]) / 50
    x = np.zeros(len(cd))
    with np.errstate(invalid="ignore"):
        x[1:] = np.sign(cd[:-1] - s[1:])
    return dict(zip(d.tolist(), np.nan_to_num(x).tolist()))


# ---------------------------------------------------------------- grupo E (t16)
def senales_E(t, o, h, l, c):
    S = {}
    T60, O60, H60, L60, C60 = velas(t, o, h, l, c, 3600)
    TD, OD, HD, LD, CD = velas(t, o, h, l, c, 86400)
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
    T30, O30, H30, L30, C30 = velas(t, o, h, l, c, 1800)
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
    dias = np.unique(t // 86400)
    S["E04 estacionalidad 21-23 UTC"] = ("E", dias * 86400 + 21 * 3600, np.ones(len(dias)))
    i0, i30 = np.searchsorted(t, dias * 86400), np.searchsorted(t, dias * 86400 + 1800)
    ok = (i30 < len(t)) & (i0 < len(t))
    ok[ok] &= t[i0[ok]] == dias[ok] * 86400
    S["E05 momentum de la primera media hora"] = ("E", dias[ok] * 86400 + 23 * 3600 + 1800, np.sign(c[i30[ok] - 1] - o[i0[ok]]))
    tr = np.maximum(HD - LD, np.maximum(np.abs(HD - np.r_[np.nan, CD[:-1]]), np.abs(LD - np.r_[np.nan, CD[:-1]])))
    atr = np.r_[np.nan, sma(np.nan_to_num(tr, nan=0.0), 14)[:-1]]
    atr[:15] = np.nan
    dmap = {int(d): (float(OD[i]), float(atr[i])) for i, d in enumerate(TD // 86400)}
    T15, O15, H15, L15, C15 = velas(t, o, h, l, c, 900)
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
    mh = ema(C60, 12) - ema(C60, 26)
    sh = ema(mh, 9)
    md = ema(CD, 12) - ema(CD, 26)
    hd = md - ema(md, 9)
    prev = {int(d): float(hd[i - 1]) for i, d in enumerate(TD // 86400) if i > 0}
    hdh = np.array([prev.get(int(x) // 86400, np.nan) for x in T60])
    a_, b_ = cruces(mh, sh)
    with np.errstate(invalid="ignore"):
        S["E12 MACD diario y horario"] = ("E",) + par(T60, 3600, a_ & (hdh > 0), b_ & (hdh < 0))
    S["E16 cruce de EMA 20/50 (1 h)"] = ("E",) + par(T60, 3600, *cruces(ema(C60, 20), ema(C60, 50)))
    T4, O4, H4, L4, C4 = velas(t, o, h, l, c, 14400)
    S["E18 SMA 10/200 (4 h)"] = ("E",) + par(T4, 14400, *cruces(sma(C4, 10), sma(C4, 200)))
    r14 = rsi(C60)
    a_, b_ = cruces(ema(C60, 12), ema(C60, 26))
    S["E19 EMA 12/26 con RSI 14 (1 h)"] = ("E",) + par(T60, 3600, a_ & (r14 > 50), b_ & (r14 < 50))
    return S


def todas(t, o, h, l, c):
    """Grupos A, C y E juntos, con el contexto diario y la volatilidad de 5 min."""
    S, T5, vol5 = senales_AC(t, o, h, l, c)
    S.update(senales_E(t, o, h, l, c))
    return S, T5, vol5, contexto(t, c)
