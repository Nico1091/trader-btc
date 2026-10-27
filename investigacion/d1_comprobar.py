"""Comprueba que la variante «actual» de d1_variantes.py reproduce EXACTAMENTE las operaciones de la base.
Uso: python3 -I d1_comprobar.py RUTA.npy ETIQUETA"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import d1_variantes as D  # noqa: E402
from metricas import cargar  # noqa: E402

base = cargar(sys.argv[2])


def igual(nombre, t, b):
    t = t.sort_values("entrada").reset_index(drop=True)
    b = b.sort_values("entrada").reset_index(drop=True)
    ok = len(t) == len(b) and (t.entrada.values == b.entrada.values).all() and (t.salida.values == b.salida.values).all() \
        and np.allclose(t.px.to_numpy(float), b.px.to_numpy(float)) and np.allclose(t.pe.to_numpy(float), b.pe.to_numpy(float))
    print(f"{nombre}: variante {len(t)} ops, base {len(b)} ops -> {'IDÉNTICAS' if ok else 'DISTINTAS'}")
    return ok


t = pd.DataFrame(D.banda(0.5, 60, (1, -1)))
t = t[(t.salida_var == "actual") & ((t.senal.dt.hour < 21) | ((t.senal.dt.hour == 21) & (t.senal.dt.minute == 0)))]
r = [igual("P05b", t, base[base.estrategia == "P05b"])]
t = pd.DataFrame(D.banda(1.0, 60, (1,), solo_largo_ctx=True))
t = t[(t.salida_var == "actual") & ((t.senal.dt.hour < 21) | ((t.senal.dt.hour == 21) & (t.senal.dt.minute == 0)))]
t = t[np.array([D.C.CONF15["todos 3 de 3"](x.senal, x.lado) for x in t.itertuples()])]
r.append(igual("P05c", t, base[base.estrategia == "P05c"]))
t = pd.DataFrame(D.n9_var(7, 13))
r.append(igual("N9", t[t.salida_var == "actual"], base[base.estrategia == "N9"]))
r.append(igual("P11", pd.DataFrame(D.dia_largo(0, 3.0)), base[base.estrategia == "P11"]))
r.append(igual("N8", pd.DataFrame(D.dia_largo(2, 3.0)), base[base.estrategia == "N8"]))
print("RESULTADO:", "LA VARIANTE ACTUAL REPRODUCE LA BASE" if all(r) else "HAY DIFERENCIAS")
