"""P05b por régimen: largo solo con cierre diario sobre la SMA 50, corto solo bajo ella. Año por año, frente a la base."""
import pandas as pd
import t8_confirmacion as T
from sim import p05b, a_tabla, netos
V = T.V
t = a_tabla(p05b(V)); t["n"] = netos(t, 0.05, 0.02); t["d"] = netos(t, 0.10, 0.04)
t["ok"] = [T.filtros["tend_d"](T.t_senal(r, "P05b"), r["lado"]) for _, r in t.iterrows()]
t["anio"] = t.entrada.dt.year; t["lado_txt"] = t.lado.map({1: "largo", -1: "corto"})
f = t[t.ok]
g = pd.DataFrame({"base_ops": t.groupby("anio").size(), "base_neto": t.groupby("anio").n.sum(),
                  "reg_ops": f.groupby("anio").size(), "reg_neto": f.groupby("anio").n.sum(), "reg_doble": f.groupby("anio").d.sum(),
                  "reg_cortos_neto": f[f.lado < 0].groupby("anio").n.sum(), "reg_largos_neto": f[f.lado > 0].groupby("anio").n.sum()}).fillna(0)
print(g.round(2).to_string()); print("TOTAL", g.sum().round(2).to_dict())
