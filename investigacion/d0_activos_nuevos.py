"""D0: validación fuera de muestra en activos nunca mirados (criterio fijado en PREREGISTRO.md, punto 2).

Una estrategia «generaliza» si su media neta con comisión DOBLE es positiva en al menos 4 de los 5 activos nuevos y la
media de todas sus operaciones juntas es positiva con un IC 90 % (bootstrap por bloques de meses, los 5 activos juntos en
cada mes porque se mueven a la vez) que no incluye el cero. Uso: python3 -I d0_activos_nuevos.py > d0_activos_nuevos.txt"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from metricas import cargar, neto, ic_bloques, CORTE_PRUEBA  # noqa: E402

NUEVOS = ["SOL", "BNB", "XRP", "DOGE", "ADA"]
ORDEN = ["P05b", "P11", "P05c", "N9", "N8"]
todo = []
for a in NUEVOS + ["BTC", "ETH"]:
    t = cargar(a)
    t["activo"] = a
    t["n1"] = neto(t, "futuros base")
    t["n2"] = neto(t, "futuros doble")
    todo.append(t)
T = pd.concat(todo, ignore_index=True)
N = T[T.activo.isin(NUEVOS)]

print("MEDIA NETA POR OPERACIÓN con comisión DOBLE (%), y número de operaciones")
m = T.pivot_table(index="estrategia", columns="activo", values="n2", aggfunc="mean").reindex(ORDEN)[NUEVOS + ["BTC", "ETH"]]
c = T.pivot_table(index="estrategia", columns="activo", values="n2", aggfunc="count").reindex(ORDEN)[NUEVOS + ["BTC", "ETH"]]
print(m.to_string(float_format=lambda v: f"{v:+.3f}"))
print(c.to_string())
print("\nSUMA NETA con comisión base (%), 2020-2023 | 2024-2026")
for tr, sel in (("2020-2023", T.entrada < CORTE_PRUEBA), ("2024-2026", T.entrada >= CORTE_PRUEBA)):
    s = T[sel].pivot_table(index="estrategia", columns="activo", values="n1", aggfunc="sum").reindex(ORDEN)[NUEVOS + ["BTC", "ETH"]]
    print(f"  {tr}")
    print(s.to_string(float_format=lambda v: f"{v:+.1f}"))

print("\nVEREDICTO PREREGISTRADO (solo los 5 activos nuevos, comisión doble)")
filas = []
for nb in ORDEN:
    x = N[N.estrategia == nb].sort_values("entrada")
    pos = int((m.loc[nb, NUEVOS] > 0).sum())
    lo, hi = ic_bloques(x, x.n2.to_numpy(), sims=3000, semilla=5)
    # sin las 5 mejores operaciones de cada activo
    sin_top = np.concatenate([np.sort(g.n2.to_numpy())[:-5] for _, g in x.groupby("activo")])
    ok = pos >= 4 and lo > 0
    filas.append(dict(estrategia=nb, ops=len(x), activos_positivos=f"{pos}/5", media_doble=x.n2.mean(), ic90=f"[{lo:+.3f}, {hi:+.3f}]",
                      media_sin_top5_por_activo=sin_top.mean(), media_2020_23=x[x.entrada < CORTE_PRUEBA].n2.mean(),
                      media_2024_26=x[x.entrada >= CORTE_PRUEBA].n2.mean(), generaliza="SÍ" if ok else "NO"))
print(pd.DataFrame(filas).to_string(index=False, float_format=lambda v: f"{v:+.3f}"))

print("\nCOMPROBACIÓN DE LO QUE SOLO SE MIRÓ EN BTC (descriptivo, no preregistrado como criterio):")
x = N[N.estrategia == "P05b"].copy()
x["tarde"] = x.senal.dt.hour >= 17
print("  P05b, señales de 17:00-21:00 frente al resto (media doble, ops):",
      x.groupby("tarde").n2.agg(["mean", "count"]).to_dict("index"))
x = N[N.estrategia == "P05c"]
print("  P05c, media doble por lado del contexto: solo largos (por construcción)", f"{x.n2.mean():+.3f}")
