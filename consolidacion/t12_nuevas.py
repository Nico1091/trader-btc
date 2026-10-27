"""Tarea 12 (pedido de Nicolás del 26/10): 3 estrategias nuevas para el libro PRUEBA, con indicadores de medias,
RSI y patrones de vela del curso, siempre en el lado del contexto (cierre diario de ayer frente a su SMA 50).
Velas de 1 h armadas con las de 1 minuto de futuros; gestión con 1 minuto; una posición a la vez por estrategia.
Entrada a mercado en la apertura del minuto siguiente al cierre de la vela de señal (tomador 0,05 %/lado; el doble 0,10 %).

N4 Retroceso a la EMA 20 (curso, «seguir la tendencia»): precio sobre la EMA 50 de 1 h (corto: bajo), la vela anterior
   tocó la EMA 20 y la actual cierra a favor, fuera de ella, con cuerpo >= 50 % del rango. Stop 1,5·ATR14 de 1 h,
   objetivo 2R, equilibrio en 1R, máximo 24 h.
N5 RSI que sale del extremo + patrón: el RSI14 de 1 h vuelve a cruzar 30 hacia arriba (corto: 70 hacia abajo) y en las
   2 últimas velas hay un patrón del curso a favor. Stop 1,5·ATR, objetivo 2R, equilibrio en 1R, máximo 24 h.
N6 50 SMA + precio (curso): la vela de 1 h cierra al otro lado de la SMA 50 sin tocarla con el cuerpo (la anterior
   cerraba del otro lado). Stop al otro lado de la media menos 0,5·ATR, objetivo 2R, equilibrio en 1R, máximo 48 h.
Ajuste 2020-2023, prueba 2024-2026 (mirada una vez), azar con las mismas operaciones en momentos sorteados."""
import numpy as np
import pandas as pd
from lib import cargar, remuestrear, patrones, CORTE
from sim import Velas, salida, op, a_tabla, netos, azar

V = Velas(cargar())
h = remuestrear(V.df, 60)
c, o, hi, lo = h.c, h.o, h.h, h.l
ema20 = c.ewm(span=20, adjust=False).mean()
ema50 = c.ewm(span=50, adjust=False).mean()
sma50h = c.rolling(50).mean()
tr = pd.concat([hi - lo, (hi - c.shift()).abs(), (lo - c.shift()).abs()], axis=1).max(axis=1)
atr = tr.rolling(14).mean()
d = c.diff()
rs = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean() / (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
rsi = 100 - 100 / (1 + rs)
pat, lado_p = patrones(h)
alc = pat[[k for k, s in lado_p.items() if s > 0]].any(axis=1)
baj = pat[[k for k, s in lado_p.items() if s < 0]].any(axis=1)
alc2, baj2 = alc | alc.shift(1, fill_value=False), baj | baj.shift(1, fill_value=False)
# contexto: cierre diario de ayer frente a su SMA 50
dd = remuestrear(V.df, 1440)
ctx_d = np.sign(dd.c - dd.c.rolling(50).mean())
ctx = ctx_d.shift(1).reindex(h.index.normalize()).to_numpy()  # el de ayer, para cada hora de hoy
cuerpo = (c - o).abs()
rango = hi - lo

sen = {}
toca20 = (lo.shift() <= ema20.shift()) & (hi.shift() >= ema20.shift())
sen["N4 retroceso EMA20"] = np.where((ctx > 0) & (c > ema50) & toca20 & (c > o) & (c > ema20) & (cuerpo >= 0.5 * rango), 1,
                             np.where((ctx < 0) & (c < ema50) & toca20 & (c < o) & (c < ema20) & (cuerpo >= 0.5 * rango), -1, 0))
sen["N5 RSI + patrón"] = np.where((ctx > 0) & (rsi.shift() < 30) & (rsi >= 30) & alc2, 1,
                          np.where((ctx < 0) & (rsi.shift() > 70) & (rsi <= 70) & baj2, -1, 0))
sen["N6 50 SMA + precio"] = np.where((ctx > 0) & (c.shift() < sma50h.shift()) & (np.minimum(o, c) > sma50h), 1,
                             np.where((ctx < 0) & (c.shift() > sma50h.shift()) & (np.maximum(o, c) < sma50h), -1, 0))
H = {"N4 retroceso EMA20": 24, "N5 RSI + patrón": 24, "N6 50 SMA + precio": 48}


def correr(nombre):
    s = sen[nombre]
    ops, libre = [], V.t[0]
    cierre = h.index + pd.Timedelta(hours=1)
    for j in np.flatnonzero(s != 0):
        t = cierre[j]
        if t < libre or np.isnan(atr.iloc[j]):
            continue
        lado = int(s[j])
        ie = V.i(t)
        if ie >= len(V.t) - H[nombre] * 60:
            break
        pe = V.o[ie]
        if nombre.startswith("N6"):
            st = sma50h.iloc[j] - lado * 0.5 * atr.iloc[j]
        else:
            st = pe - lado * 1.5 * atr.iloc[j]
        R = abs(pe - st)
        if R <= 0 or lado * (pe - st) <= 0:
            continue
        tp, be = pe + lado * 2 * R, pe + lado * R
        ifin = min(V.i(t + pd.Timedelta(hours=H[nombre])) - 1, len(V.t) - 1)
        ix, px, mot = salida(V, ie, lado, pe, stop=st, tp=tp, be=be, i_fin=ifin)
        ops.append(op(V, ie, ix, lado, pe, px, mot))
        libre = V.t[ix] + pd.Timedelta(minutes=1)
    return a_tabla(ops)


def caida(x):
    eq = np.concatenate([[0], np.cumsum(x)])
    return float(np.max(np.maximum.accumulate(eq) - eq))


filas = []
for nombre in sen:
    t = correr(nombre)
    for tramo in ("ajuste", "prueba"):
        s = t[t.entrada < CORTE] if tramo == "ajuste" else t[t.entrada >= CORTE]
        for lado_txt, ss in (("ambos", s), ("largos", s[s.lado > 0]), ("cortos", s[s.lado < 0])):
            n1, n2 = netos(ss), netos(ss, 0.10)
            az = azar(V, ss, sims=300) if len(ss) else np.array([0.0])
            filas.append(dict(estrategia=nombre, tramo=tramo, lado=lado_txt, ops=len(ss),
                              acierto=float((n1 > 0).mean() * 100) if len(ss) else np.nan, neto=float(n1.sum()),
                              doble=float(n2.sum()), media=float(n1.mean()) if len(ss) else np.nan,
                              caida=caida(n1), pct_azar=float((az < n1.sum()).mean() * 100)))
    print(nombre, "listo", flush=True)

r = pd.DataFrame(filas)
r.to_csv("t12_nuevas.csv", index=False)
pd.set_option("display.width", 220)
print(r.to_string(float_format=lambda v: f"{v:.2f}"))
