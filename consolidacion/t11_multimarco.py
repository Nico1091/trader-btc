"""Tarea 11 (pedido de Nicolás del 26/10): leer el estado del mercado en varios marcos antes de operar.
En el instante de la señal, con velas ya cerradas, se mira la dirección del precio en:
  5 min (la última vela de 5 m), 3 h, 16 h, 1 día (24 h) y 3 meses (90 días).
Un marco «acompaña» si el precio se movió en el lado de la operación en ese tramo.
Variantes: todos los marcos largos (3 h, 16 h, 1 d, 3 meses) a favor; al menos 3 de 4; los dos lentos (1 d y 3 meses)
a favor; y cada una con la vela de 5 m también a favor. Se elige en el ajuste (2020-2023) y se mira la prueba
(2024-2026) una vez; se compara con subconjuntos al azar de la misma estrategia."""
import numpy as np
import pandas as pd
import t8_confirmacion as T
from t10_contexto import bases
from lib import CORTE
from sim import a_tabla, netos

V = T.V
rng = np.random.default_rng(2611)
MARCOS = {"3h": 180, "16h": 960, "1d": 1440, "3m": 90 * 1440}


def estado(t, lado):
    """Devuelve dict marco -> True si acompaña al lado. Solo usa minutos anteriores a t."""
    i = V.i(t) - 1  # último minuto cerrado
    out = {}
    for k, m in MARCOS.items():
        j = i - m
        out[k] = j >= 0 and lado * (V.c[i] / V.c[j] - 1) > 0
    i5 = i - (i % 5) - 1 if False else i  # la vela de 5 m que acaba de cerrar: minutos i-4..i
    out["5m"] = lado * (V.c[i] - V.o[i - 4]) > 0
    return out


variantes = {
    "(ninguno)": lambda e: True,
    "4 de 4": lambda e: all(e[k] for k in MARCOS),
    "3 de 4": lambda e: sum(e[k] for k in MARCOS) >= 3,
    "1d y 3m": lambda e: e["1d"] and e["3m"],
    "3m": lambda e: e["3m"],
    "4 de 4 + 5m": lambda e: all(e[k] for k in MARCOS) and e["5m"],
    "3 de 4 + 5m": lambda e: sum(e[k] for k in MARCOS) >= 3 and e["5m"],
    "1d y 3m + 5m": lambda e: e["1d"] and e["3m"] and e["5m"],
    "SMA50 (tarea 10)": None,
}

filas = []
for nb in ("P05b largo", "P05b corto", "P05c largo", "Lunes largo (P11)"):
    ops, tipo = bases[nb]
    t = a_tabla(ops)
    t["n"] = netos(t, 0.05, 0.02)
    t["d"] = netos(t, 0.10, 0.04)
    nombre_t = "P11" if tipo == "P11" else "P05b"
    ts = [T.t_senal(o, nombre_t) for o in ops]
    est = [estado(x, o["lado"]) for x, o in zip(ts, ops)]
    for vn, f in variantes.items():
        if f is None:
            k = np.array([T.filtros["tend_d"](x, o["lado"]) for x, o in zip(ts, ops)])
        else:
            k = np.array([f(e) for e in est])
        fila = dict(base=nb, variante=vn)
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
r.to_csv("t11_multimarco.csv", index=False)
pd.set_option("display.width", 250)
print(r.to_string(float_format=lambda v: f"{v:.2f}"))
print("\nELEGIDA EN EL AJUSTE (mejor media neta con mínimo 40 ops en el ajuste, sin contar la base):")
for nb in r.base.unique():
    s = r[(r.base == nb) & (r.variante != "(ninguno)") & (r.ops_ajuste >= 40)].sort_values("media_ajuste", ascending=False)
    b = s.iloc[0]; z = r[(r.base == nb) & (r.variante == "(ninguno)")].iloc[0]
    print(f"{nb}: «{b.variante}» ajuste {int(b.ops_ajuste)} ops media {b.media_ajuste:+.3f} | PRUEBA {int(b.ops_prueba)} ops neto "
          f"{b.neto_prueba:+.1f} % doble {b.doble_prueba:+.1f} % media {b.media_prueba:+.3f} pct {b.pct_prueba:.0f} || base prueba media {z.media_prueba:+.3f}")
