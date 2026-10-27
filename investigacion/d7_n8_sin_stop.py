"""D7: la única variante que pasa la regla de adopción con una mejora clara (N8 sin stop, elegida en BTC 2020-22 y
confirmada en 2023) se lleva a los 7 activos: media, cola de pérdidas y el criterio del preregistro en los 5 nuevos.
Uso: python3 -I d7_n8_sin_stop.py ETIQUETA RUTA.npy  (un activo; escribe d7_n8_ETIQUETA.csv)"""
import os
import sys

ETQ, RUTA = sys.argv[1], sys.argv[2]
sys.argv = [sys.argv[0], RUTA, ETQ]
sys.path.insert(0, "/home/user/trader-btc-investigacion/consolidacion")
import pandas as pd  # noqa: E402
import consolidado as C  # noqa: E402

filas = []
for var, st in (("stop 3 %", 3.0), ("sin stop", 1000.0)):
    for o in C.p11(C.V, stop_pct=st, dias_semana=(2,)):
        if C.contexto(o["entrada"]) > 0:
            filas.append(dict(activo=ETQ, variante=var, entrada=o["entrada"], salida=o["salida"], bruto=o["bruto"]))
pd.DataFrame(filas).to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "variantes", f"d7_n8_{ETQ}.csv"), index=False)
print(ETQ, len(filas))
