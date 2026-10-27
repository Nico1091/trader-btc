"""Tarea 12, segunda tanda: 3 candidatas más, todas en el lado del contexto (cierre diario de ayer frente a su SMA 50).

N7 Rompimiento del máximo / mínimo de ayer (curso: soportes y resistencias): contexto alcista -> tras un cierre de 15 m
   sobre el máximo de ayer, límite de compra en ese nivel válido 60 min; stop con un cierre de 15 m que vuelve bajo la
   apertura del día; salida 23:59 UTC. Contexto bajista: espejo con el mínimo de ayer. Creador 0,02 % + tomador 0,05 %.
N8 Miércoles UTC con contexto alcista: largo a las 00:00, stop 3 %, salida 23:59 (tomador 0,05 %/lado).
N9 Rango de Asia (00:00-07:00 UTC) roto en la sesión de Londres (07:00-16:00): contexto alcista -> tras un cierre de 15 m
   sobre el máximo de Asia, límite en el nivel 60 min; stop: cierre de 15 m bajo el punto medio del rango; salida 23:59.
   Espejo en contexto bajista.
Ajuste 2020-2023, prueba 2024-2026; azar con las mismas operaciones en momentos sorteados."""
import numpy as np
import pandas as pd
from lib import cargar, remuestrear, CORTE
from sim import Velas, p11, salida, op, dias, a_tabla, netos, azar

V = Velas(cargar())
d1 = remuestrear(V.df, 1440)
ctx = np.sign(d1.c - d1.c.rolling(50).mean())  # contexto al cierre de cada día
c15 = remuestrear(V.df, 15)


def banda(V, nivel_fn, desde_h, hasta_h, stop_fn):
    ops = []
    for d in dias(V):
        ayer = d - pd.Timedelta(days=1)
        if ayer not in ctx.index or ctx.loc[ayer] == 0 or np.isnan(ctx.loc[ayer]):
            continue
        lado = int(ctx.loc[ayer])
        nv = nivel_fn(d, lado)
        if nv is None:
            continue
        b = c15.loc[d + pd.Timedelta(hours=desde_h): d + pd.Timedelta(hours=hasta_h) - pd.Timedelta(minutes=15)]
        cl = b.c.to_numpy()
        j = next((i for i, x in enumerate(cl) if lado * (x - nv) > 0), None)
        if j is None:
            continue
        ts = b.index[j] + pd.Timedelta(minutes=15)
        a0 = V.i(ts)
        a1 = min(V.i(ts + pd.Timedelta(minutes=60)) - 1, len(V.t) - 1)
        seg = V.l[a0:a1 + 1] < nv if lado > 0 else V.h[a0:a1 + 1] > nv
        kk = np.flatnonzero(seg)
        if not len(kk):
            continue
        ie = a0 + kk[0]
        fin = d + pd.Timedelta(hours=23, minutes=59)
        ifin = V.i(fin)
        if ifin >= len(V.t) or V.t[ifin] != fin:
            continue
        ref = stop_fn(d, lado)
        cierres = c15.loc[V.t[ie].floor("15min"): d + pd.Timedelta(hours=23, minutes=30)]
        ix, px, mot = ifin, V.c[ifin], "tiempo"
        for tb, row in cierres.iterrows():
            if lado * (row.c - ref) <= 0:
                ix, px, mot = V.i(tb + pd.Timedelta(minutes=14)), row.c, "stop"; break
        ops.append(op(V, ie, ix, lado, nv, px, mot, creador=True))
    return ops


def ap(d):
    i = V.i(d)
    return V.o[i] if i < len(V.t) and V.t[i] == d else None


def n7_nivel(d, lado):
    ayer = d - pd.Timedelta(days=1)
    if ayer not in d1.index:
        return None
    return d1.loc[ayer].h if lado > 0 else d1.loc[ayer].l


def asia(d):
    a = V.df.loc[d: d + pd.Timedelta(hours=6, minutes=59)]
    return (a.h.max(), a.l.min()) if len(a) > 400 else (None, None)


def n9_nivel(d, lado):
    h, l = asia(d)
    return None if h is None else (h if lado > 0 else l)


def n9_stop(d, lado):
    h, l = asia(d)
    return (h + l) / 2


tablas = {
    "N7 rompe máx/mín de ayer": a_tabla(banda(V, n7_nivel, 0, 24, lambda d, lado: ap(d))),
    "N9 rango de Asia en Londres": a_tabla(banda(V, n9_nivel, 7, 16, n9_stop)),
}
mier = a_tabla(p11(V, dias_semana=(2,)))
mier["ok"] = [ctx.get(e.normalize() - pd.Timedelta(days=1), 0) > 0 for e in mier.entrada]
tablas["N8 miércoles con contexto"] = mier[mier.ok].drop(columns="ok")


def caida(x):
    eq = np.concatenate([[0], np.cumsum(x)])
    return float(np.max(np.maximum.accumulate(eq) - eq))


filas = []
for nombre, t in tablas.items():
    for tramo in ("ajuste", "prueba"):
        s = t[t.entrada < CORTE] if tramo == "ajuste" else t[t.entrada >= CORTE]
        for lado_txt, ss in (("ambos", s), ("largos", s[s.lado > 0]), ("cortos", s[s.lado < 0])):
            if lado_txt != "ambos" and nombre.startswith("N8"):
                continue
            n1, n2 = netos(ss), netos(ss, 0.10, 0.04)
            az = azar(V, ss, sims=300) if len(ss) else np.array([0.0])
            filas.append(dict(estrategia=nombre, tramo=tramo, lado=lado_txt, ops=len(ss),
                              acierto=float((n1 > 0).mean() * 100) if len(ss) else np.nan, neto=float(n1.sum()),
                              doble=float(n2.sum()), media=float(n1.mean()) if len(ss) else np.nan,
                              caida=caida(n1), pct_azar=float((az < n1.sum()).mean() * 100)))
    print(nombre, "listo", flush=True)
r = pd.DataFrame(filas)
r.to_csv("t12b_nuevas.csv", index=False)
pd.set_option("display.width", 220)
print(r.to_string(float_format=lambda v: f"{v:.2f}"))
