"""Motor de las estrategias con velas de 1 minuto (futuros USDⓈ-M BTCUSDT).

Cada estrategia devuelve una lista de operaciones: entrada y salida (minuto), lado y retorno bruto %.
La comisión se aplica después, según el tipo de entrada (creador o tomador)."""
import numpy as np
import pandas as pd
from lib import remuestrear, patrones

MIN = pd.Timedelta(minutes=1)


class Velas:
    def __init__(self, m1):
        self.df = m1
        self.t = m1.index
        self.o, self.h, self.l, self.c = (m1[k].to_numpy() for k in "ohlc")

    def i(self, ts, lado="left"):
        return int(self.t.searchsorted(ts, side=lado))


def salida(V, i0, lado, precio, stop=None, tp=None, be=None, i_fin=None):
    """Recorre minutos desde i0 (incluido) hasta i_fin (incluido). Devuelve (índice, precio, motivo).
    stop/tp en precio; be = precio que, al tocarse, sube el stop a la entrada. Si en un minuto tocan stop y
    objetivo, se asume el stop (lo peor)."""
    sl = slice(i0, i_fin + 1)
    h, l = V.h[sl], V.l[sl]
    n = len(h)
    if n == 0:
        return i_fin, V.c[i_fin], "tiempo"
    def primero(mask):
        k = np.flatnonzero(mask)
        return k[0] if len(k) else n
    if lado > 0:
        k_sl = primero(l <= stop) if stop is not None else n
        k_tp = primero(h >= tp) if tp is not None else n
        k_be = primero(h >= be) if be is not None else n
    else:
        k_sl = primero(h >= stop) if stop is not None else n
        k_tp = primero(l <= tp) if tp is not None else n
        k_be = primero(l <= be) if be is not None else n
    if be is not None and k_be < min(k_sl, k_tp):
        # desde el minuto siguiente al toque, el stop pasa a la entrada
        resto_sl = (l[k_be + 1:] <= precio) if lado > 0 else (h[k_be + 1:] >= precio)
        k2 = np.flatnonzero(resto_sl)
        k_be_sl = k_be + 1 + k2[0] if len(k2) else n
        if k_be_sl < k_tp:
            return i0 + k_be_sl, precio, "equilibrio"
    if k_sl <= k_tp and k_sl < n:
        return i0 + k_sl, stop, "stop"
    if k_tp < n:
        return i0 + k_tp, tp, "objetivo"
    return i_fin, V.c[i_fin], "tiempo"


def op(V, ie, ix, lado, pe, px, motivo, creador=False, **kw):
    d = dict(entrada=V.t[ie], salida=V.t[ix], lado=lado, pe=pe, px=px,
             bruto=lado * (px / pe - 1) * 100, motivo=motivo, creador=creador)
    d.update(kw)
    return d


def dias(V):
    return pd.date_range(V.t[0].normalize() + pd.Timedelta(days=15), V.t[-1].normalize(), freq="D")


# ---------- P11: largo del lunes UTC ----------

def p11(V, stop_pct=3.0, dias_semana=(0,)):
    ops = []
    for d in dias(V):
        if d.weekday() not in dias_semana:
            continue
        ie, ifin = V.i(d), V.i(d + pd.Timedelta(hours=23, minutes=59))
        if ifin >= len(V.t) or V.t[ifin] != d + pd.Timedelta(hours=23, minutes=59):
            continue
        pe = V.o[ie]
        ix, px, mot = salida(V, ie, 1, pe, stop=pe * (1 - stop_pct / 100), i_fin=ifin)
        ops.append(op(V, ie, ix, 1, pe, px, mot))
    return ops


# ---------- P05b: banda ATR de E09 con entrada de creador ----------

def atr_diario(m1):
    d = remuestrear(m1, 1440)
    tr = np.maximum(d["h"] - d["l"], np.maximum((d["h"] - d["c"].shift()).abs(), (d["l"] - d["c"].shift()).abs()))
    return d, tr.rolling(14).mean().shift(1)  # ATR de los 14 días previos


def p05b(V, k=0.5, W=60, lados=(1, -1), veto=None, solo_creador=True):
    """veto: función (instante_señal, lado) -> True si se veta."""
    d1, atr = atr_diario(V.df)
    c15 = remuestrear(V.df, 15)
    ops = []
    for d in dias(V):
        if d not in atr.index or np.isnan(atr.loc[d]):
            continue
        i0 = V.i(d)
        if i0 >= len(V.t) or V.t[i0] != d:
            continue
        ap = V.o[i0]
        a = atr.loc[d]
        up, dn = ap + k * a, ap - k * a
        barras = c15.loc[d: d + pd.Timedelta(hours=23, minutes=30)]  # cierres hasta 23:45
        if len(barras) < 90:
            continue
        cl = barras["c"].to_numpy()
        lado, j = 0, None
        for jj, x in enumerate(cl):
            if x > up:
                lado, j = 1, jj; break
            if x < dn:
                lado, j = -1, jj; break
        if lado == 0 or lado not in lados:
            continue
        t_senal = barras.index[j] + pd.Timedelta(minutes=15)  # instante del cierre
        if veto is not None and veto(t_senal, lado):
            continue
        nivel = up if lado > 0 else dn
        a0 = V.i(t_senal)
        a1 = min(V.i(t_senal + pd.Timedelta(minutes=W)) - 1, len(V.t) - 1)
        seg = V.l[a0:a1 + 1] < nivel if lado > 0 else V.h[a0:a1 + 1] > nivel
        kk = np.flatnonzero(seg)
        if not len(kk):
            continue
        ie = a0 + kk[0]
        ifin = V.i(d + pd.Timedelta(hours=23, minutes=59))
        if ifin >= len(V.t):
            continue
        # stop: primer cierre de 15 m posterior al llenado que vuelve a la apertura
        cierres = c15.loc[V.t[ie].floor("15min") + pd.Timedelta(minutes=15): d + pd.Timedelta(hours=23, minutes=30)]
        ix, px, mot = ifin, V.c[ifin], "tiempo"
        for tb, row in cierres.iterrows():
            if (lado > 0 and row["c"] <= ap) or (lado < 0 and row["c"] >= ap):
                ix = V.i(tb + pd.Timedelta(minutes=14)); px = row["c"]; mot = "stop"; break
        ops.append(op(V, ie, ix, lado, nivel, px, mot, creador=True))
    return ops


# ---------- N3: retroceso de creador en tendencia diaria (tarea 4) ----------

def n3(V, x=0.5, dos_dias=False, hasta_h=20):
    d1, atr = atr_diario(V.df)
    sma = d1["c"].rolling(50).mean()
    ops = []
    for d in dias(V):
        prev = d - pd.Timedelta(days=1)
        if prev not in d1.index or d not in atr.index or np.isnan(atr.loc[d]) or np.isnan(sma.get(prev, np.nan)):
            continue
        if not (d1["c"].loc[prev] > sma.loc[prev] and sma.loc[prev] > sma.loc[prev - pd.Timedelta(days=5)]):
            continue
        i0 = V.i(d)
        if i0 >= len(V.t) or V.t[i0] != d:
            continue
        a = atr.loc[d]
        nivel = V.o[i0] - x * a
        i_lim = V.i(d + pd.Timedelta(hours=hasta_h)) - 1
        kk = np.flatnonzero(V.l[i0:i_lim + 1] < nivel)
        if not len(kk):
            continue
        ie = i0 + kk[0]
        fin = d + pd.Timedelta(days=2 if dos_dias else 1) - pd.Timedelta(minutes=1)
        ifin = V.i(fin)
        if ifin >= len(V.t) or V.t[ifin] != fin:
            continue
        ix, px, mot = salida(V, ie + 1, 1, nivel, stop=nivel - a, i_fin=ifin)
        ops.append(op(V, ie, ix, 1, nivel, px, mot, creador=True))
    return ops


# ---------- E01 / MEZCLA (reglas sin clasificador) ----------

def indicadores_1h(m1, W=60):
    h1 = remuestrear(m1, 60)
    lo = h1["l"].rolling(W).min()
    hi = h1["h"].rolling(W).max()
    rp = (h1["c"] - lo) / (hi - lo)
    x = np.arange(W) - (W - 1) / 2
    pend = h1["c"].rolling(W).apply(lambda y: np.dot(x, y) / np.dot(x, x), raw=True)
    pend_pct = pend / h1["c"] * 100  # % por hora
    sma50d = None
    return h1, rp, pend_pct


def mezcla(V, h1, rp, pend, lados=(1, -1), stop=3.0, R=2.0, be=True, H=24, veto=None,
           corto_si_bajista=False, rp_largo=(0.35, 0.65), rp_corto=0.9):
    ops = []
    libre_desde = V.t[0]
    tiempos = h1.index + pd.Timedelta(hours=1)  # instante del cierre de la vela
    rpv, pv = rp.to_numpy(), pend.to_numpy()
    for j in range(len(h1)):
        t = tiempos[j]
        if t < libre_desde or np.isnan(rpv[j]) or np.isnan(pv[j]):
            continue
        lado = 0
        if 1 in lados and pv[j] > 0 and rp_largo[0] <= rpv[j] <= rp_largo[1]:
            lado = 1
        elif -1 in lados and rpv[j] >= rp_corto and (not corto_si_bajista or pv[j] < 0):
            lado = -1
        if lado == 0:
            continue
        if veto is not None and veto(t, lado):
            continue
        ie = V.i(t)
        if ie >= len(V.t) - H * 60:
            break
        pe = V.o[ie]
        st = pe * (1 - lado * stop / 100)
        tp = pe * (1 + lado * stop * R / 100)
        bep = pe * (1 + lado * stop / 100) if be else None
        ifin = min(V.i(t + pd.Timedelta(hours=H)) - 1, len(V.t) - 1)
        ix, px, mot = salida(V, ie, lado, pe, stop=st, tp=tp, be=bep, i_fin=ifin)
        ops.append(op(V, ie, ix, lado, pe, px, mot))
        libre_desde = V.t[ix] + MIN
    return ops


# ---------- veto por patrones de vela ----------

class VetoVelas:
    """Veta una operación si en las últimas `n` velas cerradas del marco `tf` aparece un patrón
    de lado contrario. Solo patrones con lado (las de indecisión no vetan)."""
    def __init__(self, m1, tf, n=1, nombres=None):
        df = remuestrear(m1, tf)
        pat, lado = patrones(df)
        nombres = nombres or [k for k, s in lado.items() if s != 0]
        alc = pat[[k for k in nombres if lado[k] > 0]].any(axis=1).to_numpy()
        baj = pat[[k for k in nombres if lado[k] < 0]].any(axis=1).to_numpy()
        self.cierre = df.index + pd.Timedelta(minutes=tf)
        self.alc = pd.Series(alc).rolling(n, min_periods=1).max().to_numpy() > 0
        self.baj = pd.Series(baj).rolling(n, min_periods=1).max().to_numpy() > 0

    def __call__(self, t, lado):
        j = self.cierre.searchsorted(t, side="right") - 1  # última vela cerrada en t
        if j < 0:
            return False
        return bool(self.baj[j]) if lado > 0 else bool(self.alc[j])


# ---------- evaluación ----------

def a_tabla(ops):
    return pd.DataFrame(ops) if ops else pd.DataFrame(columns=["entrada", "salida", "lado", "bruto", "creador"])


def netos(t, com=0.05, com_creador=0.02):
    if len(t) == 0:
        return np.array([])
    entrada = np.where(t["creador"].to_numpy(bool), com_creador, com)
    return t["bruto"].to_numpy() - entrada - com


def azar(V, t, sims=500, semilla=11, com=0.05):
    """Mismas operaciones (lado y duración) en momentos sorteados, sin stop. Devuelve sumas netas."""
    if len(t) == 0:
        return np.array([0.0])
    rng = np.random.default_rng(semilla)
    dur = ((t["salida"] - t["entrada"]) / MIN).to_numpy().astype(int)
    lado = t["lado"].to_numpy()
    n = len(V.t)
    sumas = []
    for _ in range(sims):
        i0 = rng.integers(0, n - 1500, len(t))
        i1 = np.minimum(i0 + np.maximum(dur, 1), n - 1)
        r = lado * (V.c[i1] / V.o[i0] - 1) * 100 - 2 * com
        sumas.append(r.sum())
    return np.array(sumas)
