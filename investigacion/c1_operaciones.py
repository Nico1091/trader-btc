"""C1: vuelca las operaciones del sistema consolidado, con la versión final de cada estrategia, a un CSV.

Usa el motor de la base sin cambiarlo (importa consolidacion/consolidado.py). La versión final es la de BTC
(P05c con «todos 3 de 3»; el resto, base), aplicada igual a cualquier activo, como hizo la consolidación con ETH.
Uso: python3 -I c1_operaciones.py RUTA_VELAS.npy ETIQUETA  ->  ops_ETIQUETA.csv"""
import os
import sys

RUTA, ETQ = sys.argv[1], sys.argv[2]
sys.argv = [sys.argv[0], RUTA, ETQ]  # consolidado lee su ruta de aquí
sys.path.insert(0, "/home/user/trader-btc-investigacion/consolidacion")
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import consolidado as C  # noqa: E402

FINAL = {
    "P05b": (C.BASES["PRINCIPAL P05b por régimen"][0], None),
    "P11": (C.BASES["PRINCIPAL P11 con contexto"][0], None),
    "P05c": (C.BASES["PRINCIPAL P05c largo con contexto"][0], C.CONF15["todos 3 de 3"]),
    "N9": (C.BASES["PRUEBA N9 Asia-Londres"][0], None),
    "N8": (C.BASES["PRUEBA N8 miércoles con contexto"][0], None),
}
filas = []
for nb, (ops, conf) in FINAL.items():
    for o in ops:
        if conf is not None and not conf(o["senal"], o["lado"]):
            continue
        r = dict(o)
        r["estrategia"] = nb
        r["pat1h"] = bool(C.H1.patron(o["senal"], o["lado"]))
        r["e1h"], r["e4h"], r["e1d"] = (bool(m.a_favor(o["senal"], o["lado"])) for m in (C.H1, C.H4, C.D1))
        filas.append(r)
t = pd.DataFrame(filas)
# referencia del stop (lo que sabe la operación al entrar): P05b/P05c la apertura; N9 el punto medio; P11/N8 el 3 %
d = C.dd
t["dia"] = t.entrada.dt.normalize()
from sim import atr_diario  # noqa: E402
t["atr14"] = atr_diario(C.m1)[1].reindex(t.dia).to_numpy()
t["precio_dia"] = d.o.reindex(t.dia).to_numpy()
t["ctx_dist"] = [(d.c.loc[x - pd.Timedelta(days=1)] / C.sma50.loc[x - pd.Timedelta(days=1)] - 1) * 100 for x in t.dia]
t = t.sort_values(["entrada", "estrategia"]).reset_index(drop=True)
t.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "operaciones", f"ops_{ETQ}.csv"), index=False)
print(ETQ, len(t), "operaciones:", t.estrategia.value_counts().to_dict())
