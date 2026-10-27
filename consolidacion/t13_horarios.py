"""Tarea 13: horario de cada libro. Resultado de cada estrategia según la hora UTC de entrada, en ajuste y en prueba.
Sesiones: Asia 00-07, Londres 07-13, Nueva York 13-21, cierre 21-24 (UTC; Colombia = UTC-5)."""
import numpy as np, pandas as pd
import t8_confirmacion as T
from t12b_nuevas import tablas as nuevas
from lib import CORTE
from sim import p05b, a_tabla, netos
V = T.V
reg = a_tabla(p05b(V)); reg["ok"] = [T.filtros["tend_d"](T.t_senal(r, "P05b"), r["lado"]) for _, r in reg.iterrows()]
conf = a_tabla(T.bases["P05b solo largo (futuros)"][0]); conf["ok"] = [T.filtros["vela3_1h"](T.t_senal(r, "P05b"), 1) and T.filtros["tend_d"](T.t_senal(r, "P05b"), 1) for _, r in conf.iterrows()]
c1 = a_tabla(p05b(V, k=1.0, lados=(1,))); c1["ok"] = [T.filtros["tend_d"](T.t_senal(r, "P05b"), 1) for _, r in c1.iterrows()]
est = {"PRINCIPAL P05b por régimen": reg[reg.ok], "PRINCIPAL P05c largo (contexto)": c1[c1.ok],
       "PRUEBA N9 Asia-Londres": nuevas["N9 rango de Asia en Londres"], "PRUEBA P05b largo + vela 1h": conf[conf.ok]}
def ses(h): return "1 Asia 00-07" if h < 7 else "2 Londres 07-13" if h < 13 else "3 NY 13-21" if h < 21 else "4 cierre 21-24"
for n, t in est.items():
    t = t.copy(); t["n"] = netos(t, 0.05, 0.02); t["ses"] = t.entrada.dt.hour.map(ses); t["tr"] = np.where(t.entrada < CORTE, "aj", "pr")
    g = t.pivot_table(index="ses", columns="tr", values="n", aggfunc=["count", "sum", "mean"]).round(2)
    print(f"\n{n} (total {len(t)} ops)\n" + g.to_string())
