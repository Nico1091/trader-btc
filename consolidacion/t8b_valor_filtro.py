"""¿El filtro aporta, o solo hereda la ventaja de la base? Percentil de las operaciones filtradas frente a
5.000 subconjuntos al azar del mismo tamaño sacados de las operaciones de la base, por tramo."""
import numpy as np, pandas as pd
import t8_confirmacion as T
from lib import CORTE
from sim import a_tabla, netos
rng = np.random.default_rng(2610)
casos = [("P05b solo largo (futuros)", "vela3_1h"), ("P05b solo largo (contado)", "vela3_1h"),
         ("P05b + veto 1h (futuros)", "vela3_1h"), ("P05b + veto 1h (futuros)", "tend_d"),
         ("P11 (futuros)", "tend_d"), ("P11 (contado)", "tend_d"), ("P05c solo largo (contado)", "volumen")]
for base, fn in casos:
    ops, merc = T.bases[base]
    f = T.filtros[fn]
    t = a_tabla(ops)
    t["keep"] = [f(T.t_senal(o, base), o["lado"]) for o in ops]
    t["neto"] = netos(t, 0.05, 0.02) if merc == "fut" else netos(t, 0.10, 0.10)
    linea = []
    for tramo in ("ajuste", "prueba"):
        s = t[t.entrada < CORTE] if tramo == "ajuste" else t[t.entrada >= CORTE]
        k = s.keep.to_numpy(); x = s.neto.to_numpy(); n = int(k.sum())
        sims = np.array([x[rng.choice(len(x), n, replace=False)].mean() for _ in range(5000)])
        linea.append(f"{tramo}: {n} de {len(x)} ops, media filtrada {x[k].mean():+.3f} % vs base {x.mean():+.3f} %, "
                     f"percentil frente a subconjuntos al azar {(sims < x[k].mean()).mean()*100:.1f}")
    print(f"{base} + {fn}\n   " + "\n   ".join(linea))
