"""Tarea 3: revalidar la MEZCLA con el rigor de octubre y mejorar P05b, P11 y la MEZCLA,
probando los patrones de vela como veto. Ajuste 2020-2023, prueba 2024-01 a 2026-10-24.
Comisión: tomador 0,05 %/lado, creador 0,02 %; con el doble: 0,10 % y 0,04 %."""
import sys
import numpy as np
import pandas as pd
from lib import cargar, CORTE
from sim import Velas, p11, p05b, mezcla, indicadores_1h, VetoVelas, a_tabla, netos, azar

V = Velas(cargar())
h1, rp, pend = indicadores_1h(V.df)
vetos = {f"veto{tf}m_n{n}": VetoVelas(V.df, tf, n) for tf in (15, 60, 240) for n in (1, 3)}

def caida(x):
    eq = np.concatenate([[0], np.cumsum(x)])
    return float(np.max(np.maximum.accumulate(eq) - eq))

filas = []
def evaluar(nombre, ops):
    t = a_tabla(ops)
    for tramo in ("ajuste", "prueba", "total"):
        if len(t):
            s = t[t.entrada < CORTE] if tramo == "ajuste" else t[t.entrada >= CORTE] if tramo == "prueba" else t
        else:
            s = t
        n1, n2 = netos(s), netos(s, 0.10, 0.04)
        az = azar(V, s) if len(s) else np.array([0.0])
        filas.append(dict(estrategia=nombre, tramo=tramo, ops=len(s),
                          acierto=float((n1 > 0).mean() * 100) if len(s) else np.nan,
                          bruto=float(s["bruto"].sum()) if len(s) else 0.0,
                          neto=float(n1.sum()), doble=float(n2.sum()),
                          media=float(n1.mean()) if len(s) else np.nan, caida=caida(n1),
                          azar_med=float(np.median(az)), pct_azar=float((az < n1.sum()).mean() * 100)))
    print(nombre, "listo", flush=True)
    return t

# MEZCLA tal como la definió junio (reglas, sin clasificador)
evaluar("MEZCLA reglas (largo+corto)", mezcla(V, h1, rp, pend))
evaluar("MEZCLA solo largo", mezcla(V, h1, rp, pend, lados=(1,)))
evaluar("MEZCLA solo corto", mezcla(V, h1, rp, pend, lados=(-1,)))
evaluar("MEZCLA corto solo con pendiente<0", mezcla(V, h1, rp, pend, corto_si_bajista=True))
evaluar("MEZCLA sin equilibrio", mezcla(V, h1, rp, pend, be=False))
for k, v in vetos.items():
    evaluar(f"MEZCLA + {k}", mezcla(V, h1, rp, pend, veto=v))
    evaluar(f"MEZCLA solo largo + {k}", mezcla(V, h1, rp, pend, lados=(1,), veto=v))

# P05b y variantes
evaluar("P05b k0,5 (base)", p05b(V))
evaluar("P05b solo largo", p05b(V, lados=(1,)))
evaluar("P05b solo corto", p05b(V, lados=(-1,)))
evaluar("P05c k1,0", p05b(V, k=1.0))
for k, v in vetos.items():
    evaluar(f"P05b + {k}", p05b(V, veto=v))

# P11 y variantes
evaluar("P11 lunes stop 3 % (base)", p11(V))
evaluar("P11 sin stop", p11(V, stop_pct=99))
evaluar("P11 stop 2 %", p11(V, stop_pct=2.0))
evaluar("P11 stop 5 %", p11(V, stop_pct=5.0))
evaluar("P11 lunes+miércoles", p11(V, dias_semana=(0, 2)))
for k in ("veto60m_n3", "veto240m_n1", "veto240m_n3"):
    v = vetos[k]
    ops = [o for o in p11(V) if not v(o["entrada"], 1)]
    evaluar(f"P11 + {k}", ops)

t = pd.DataFrame(filas)
t.to_csv(sys.argv[1] if len(sys.argv) > 1 else "t3_estrategias.csv", index=False)
pd.set_option("display.width", 250)
print(t.to_string(float_format=lambda v: f"{v:.2f}"))
