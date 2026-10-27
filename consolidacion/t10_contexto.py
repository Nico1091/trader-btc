"""Tarea 10 (pedido de Nicolás del 26/10): operar cada lado solo en su contexto.
Cortos solo con contexto bajista y largos solo con contexto alcista. Contexto = cierre diario de ayer frente a su
SMA 50 (tend_d), y de refuerzo un patrón de vela de 1 h del mismo lado en las 3 últimas velas cerradas (vela3_1h).

Bases: P05b k = 0,5 y P05c k = 1,0 en cada lado, y el lunes (P11) en largo y en corto (espejo: corto a las 00:00 UTC,
stop 3 % arriba, cierre 23:59). Futuros: tomador 0,05 %/lado, creador 0,02 %; el doble: 0,10 % y 0,04 %.
Ajuste 2020-2023, prueba 2024-2026, percentil frente a subconjuntos al azar de la misma base."""
import numpy as np
import pandas as pd
import t8_confirmacion as T
from lib import CORTE
from sim import p05b, salida, op, dias, a_tabla, netos

V = T.V
rng = np.random.default_rng(2610)


def lunes_corto(V, stop_pct=3.0):
    ops = []
    for d in dias(V):
        if d.weekday() != 0:
            continue
        ie, ifin = V.i(d), V.i(d + pd.Timedelta(hours=23, minutes=59))
        if ifin >= len(V.t) or V.t[ifin] != d + pd.Timedelta(hours=23, minutes=59):
            continue
        pe = V.o[ie]
        ix, px, mot = salida(V, ie, -1, pe, stop=pe * (1 + stop_pct / 100), i_fin=ifin)
        ops.append(op(V, ie, ix, -1, pe, px, mot))
    return ops


bases = {
    "P05b corto": (p05b(V, lados=(-1,)), "P05b"),
    "P05c corto": (p05b(V, k=1.0, lados=(-1,)), "P05b"),
    "Lunes corto": (lunes_corto(V), "P11"),
    "P05b largo": (T.bases["P05b solo largo (futuros)"][0], "P05b"),
    "P05c largo": (p05b(V, k=1.0, lados=(1,)), "P05b"),
    "Lunes largo (P11)": (T.bases["P11 (futuros)"][0], "P11"),
}
filtros = {"(ninguno)": None, "tend_d": T.filtros["tend_d"], "vela3_1h": T.filtros["vela3_1h"],
           "tend_d + vela3_1h": lambda t, l: T.filtros["tend_d"](t, l) and T.filtros["vela3_1h"](t, l)}

filas = []
for nb, (ops, tipo) in bases.items():
    t = a_tabla(ops)
    t["n"] = netos(t, 0.05, 0.02)
    t["d"] = netos(t, 0.10, 0.04)
    nombre_t = "P11" if tipo == "P11" else "P05b"
    for fn, f in filtros.items():
        if f is None:
            k = np.ones(len(t), bool)
        elif tipo == "P11" and "vela" in fn:
            k = np.array([f(o["entrada"], o["lado"]) for o in ops])  # a las 00:00, velas de 1 h del domingo
        else:
            k = np.array([f(T.t_senal(o, nombre_t), o["lado"]) for o in ops])
        fila = dict(base=nb, filtro=fn)
        for tr in ("ajuste", "prueba"):
            sel = (t.entrada < CORTE).to_numpy() if tr == "ajuste" else (t.entrada >= CORTE).to_numpy()
            x, kk = t.n.to_numpy()[sel], k[sel]
            nk = int(kk.sum())
            pct = np.nan
            if 0 < nk < len(x):
                sims = np.array([x[rng.choice(len(x), nk, replace=False)].mean() for _ in range(3000)])
                pct = (sims < x[kk].mean()).mean() * 100
            fila.update({f"ops_{tr}": nk, f"neto_{tr}": x[kk].sum(), f"doble_{tr}": t.d.to_numpy()[sel][kk].sum(),
                         f"media_{tr}": x[kk].mean() if nk else np.nan, f"pct_{tr}": pct})
        filas.append(fila)
    print(nb, "listo", flush=True)

r = pd.DataFrame(filas)
r.to_csv("t10_contexto.csv", index=False)
pd.set_option("display.width", 250)
print(r.to_string(float_format=lambda v: f"{v:.2f}"))
