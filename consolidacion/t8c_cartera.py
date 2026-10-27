"""Cartera «solo cuando debe» en contado con 40.000 pesos: P11 con tendencia diaria + P05b largo con vela alcista
de 1 h + P05c largo. Una posición a la vez (la primera que llega), riesgo 1,5 %, topes 3 % día y 6 % semana."""
import numpy as np, pandas as pd
import t8_confirmacion as T
from lib import CORTE
from sim import a_tabla
COP = 3177.85
def con_filtro(base, fn):
    ops, _ = T.bases[base]; f = T.filtros[fn]
    t = a_tabla([o for o in ops if f(T.t_senal(o, base), o["lado"])]); t["estr"] = base + "+" + fn; return t
t = pd.concat([con_filtro("P11 (contado)", "tend_d"), con_filtro("P05b solo largo (contado)", "vela3_1h"),
               a_tabla(T.bases["P05c solo largo (contado)"][0]).assign(estr="P05c")]).sort_values("entrada")
for com in (0.10, 0.20):
  for tramo, s in (("2020-2023", t[t.entrada < CORTE]), ("2024-2026", t[t.entrada >= CORTE])):
    saldo = ini = 40000 / COP; libre = None; dia = sem = None; pd_ = ps = 0.0; n = 0; minimo = saldo; netos = []
    for _, r in s.iterrows():
        if libre is not None and r.entrada < libre: continue
        d = r.entrada.normalize(); w = r.entrada.isocalendar()[:2]
        if d != dia: dia, pd_ = d, 0.0
        if w != sem: sem, ps = w, 0.0
        if pd_ <= -0.03 * ini or ps <= -0.06 * ini: continue
        if r.estr.startswith("P11"):
            dist = 0.03
        else:  # distancia conocida al entrar: de la banda a la apertura de las 00:00 UTC (el stop es volver a ella)
            ap = T.V.o[T.V.i(r.entrada.normalize())]
            dist = abs(r.pe - ap) / r.pe
        noc = min(saldo, 0.015 * saldo / dist)
        if noc < 5: continue
        g = noc * (r.bruto - 2 * com) / 100; saldo += g; pd_ += g; ps += g; n += 1; minimo = min(minimo, saldo)
        netos.append(r.bruto - 2 * com); libre = r.salida
    anos = (s.entrada.max() - s.entrada.min()).days / 365.25
    print(f"com {com:.2f}/lado {tramo}: {n} ops ({n / anos / 52:.2f}/semana), aciertos {np.mean(np.array(netos) > 0) * 100:.0f} %, "
          f"saldo {saldo * COP:,.0f} COP ({(saldo / ini - 1) * 100:+.1f} %, {((saldo / ini) ** (1 / anos) - 1) * 100:+.1f} %/año), mínimo {minimo * COP:,.0f}")
