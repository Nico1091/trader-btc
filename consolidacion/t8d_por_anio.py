"""Estabilidad año por año de las versiones confirmadas frente a su base (neto, futuros 0,05/0,02 %)."""
import pandas as pd
import t8_confirmacion as T
from sim import a_tabla, netos
for base, fn in (("P05b solo largo (futuros)", "vela3_1h"), ("P11 (futuros)", "tend_d")):
    ops, _ = T.bases[base]; f = T.filtros[fn]
    t = a_tabla(ops); t["n"] = netos(t, 0.05, 0.02); t["k"] = [f(T.t_senal(o, base), o["lado"]) for o in ops]
    t["anio"] = t.entrada.dt.year
    g = t.groupby("anio").apply(lambda s: pd.Series({"ops_base": len(s), "neto_base": s.n.sum(),
        "ops_filtro": int(s.k.sum()), "neto_filtro": s.n[s.k].sum(), "media_filtro": s.n[s.k].mean() if s.k.any() else 0}))
    print(f"\n{base} + {fn}\n" + g.round(2).to_string())
