"""D6 (D5 del preregistro): cartera y riesgo agregado.

1) Libro completo de BTC (las 5 estrategias a la vez, 1x nocional cada una): posiciones simultáneas, peor día, días en
   que pierden 3 o más a la vez, y el P&L diario conjunto frente a cada una por separado.
2) N8 y N9 en BTC y ETH como cartera: correlación BTC-ETH, exposición conjunta y si la suma mejora el riesgo.
Futuros base. Uso: python3 -I d6_cartera.py > d6_cartera.txt"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from metricas import cargar, neto, diario  # noqa: E402

ORDEN = ["P05b", "P11", "P05c", "N9", "N8"]
B = cargar("BTC")
B["n"] = neto(B)
E = cargar("ETH")
E["n"] = neto(E)
ini = min(B.entrada.min(), E.entrada.min()).normalize()
fin = min(B.salida.max(), E.salida.max()).normalize()


def serie(t):
    return diario(t, t.n.to_numpy(), ini, fin)


def res(d, nombre):
    eq = d.cumsum()
    dd = (eq.cummax() - eq).max()
    sh = d.mean() / d.std() * np.sqrt(365)
    return f"{nombre:<34} suma {d.sum():+7.1f} pts · peor día {d.min():+6.2f} · caída máx {dd:5.1f} pts · Sharpe {sh:+.2f}"


print("1) LIBRO COMPLETO DE BTC (cada estrategia con 1x nocional; suma simple, sin componer)")
D = pd.DataFrame({nb: serie(B[B.estrategia == nb]) for nb in ORDEN})
for nb in ORDEN:
    print("  " + res(D[nb], nb))
print("  " + res(D.sum(axis=1), "LAS 5 JUNTAS"))
print("  " + res(D[["P05b", "P11", "P05c"]].sum(axis=1), "PRINCIPAL (P05b+P11+P05c)"))
# posiciones abiertas a la vez, minuto a minuto (muestreo cada 15 min)
grid = pd.date_range(ini, fin, freq="15min", tz="UTC")
abiertas = np.zeros(len(grid), int)
largos = np.zeros(len(grid), int)
for r in B.itertuples():
    a, b = grid.searchsorted(r.entrada), grid.searchsorted(r.salida)
    abiertas[a:b] += 1
    largos[a:b] += r.lado
print(f"  posiciones abiertas a la vez: máximo {abiertas.max()}; % del tiempo con 2 o más: {(abiertas >= 2).mean() * 100:.1f} %, "
      f"con 3 o más: {(abiertas >= 3).mean() * 100:.2f} %; exposición neta máxima {np.abs(largos).max()} posiciones en el mismo lado")
perd = (D < 0).sum(axis=1)
print(f"  días con 2+ estrategias perdiendo a la vez: {(perd >= 2).sum()}; con 3+: {(perd >= 3).sum()}; con 4+: {(perd >= 4).sum()}")
peores = D.sum(axis=1).nsmallest(5)
print("  los 5 peores días del libro: " + "; ".join(f"{d:%Y-%m-%d} {v:+.2f} ({int(perd[d])} pierden)" for d, v in peores.items()))

print("\n2) N8 Y N9 EN BTC Y ETH COMO CARTERA")
S = {}
for nb in ("N9", "N8"):
    S[f"{nb} BTC"] = serie(B[B.estrategia == nb])
    S[f"{nb} ETH"] = serie(E[E.estrategia == nb])
S = pd.DataFrame(S)
for c in S:
    print("  " + res(S[c], c))
print("  " + res(S.sum(axis=1), "N8+N9 en BTC y ETH (4 piezas)"))
print("  " + res(S[["N9 BTC", "N8 BTC"]].sum(axis=1), "N8+N9 solo BTC"))
print("  correlación del P&L diario:")
print(S.corr().to_string(float_format=lambda v: f"{v:+.2f}"))
for nb in ("N9", "N8"):
    b = set(B[B.estrategia == nb].dia.astype(str) + B[B.estrategia == nb].lado.astype(str))
    e = set(E[E.estrategia == nb].dia.astype(str) + E[E.estrategia == nb].lado.astype(str))
    print(f"  {nb}: días con BTC y ETH operando en el mismo lado: {len(b & e)} de {len(b)} en BTC ({len(b & e) / len(b) * 100:.0f} %)")
