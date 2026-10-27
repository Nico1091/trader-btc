"""D5b: referencia clásica que el diagnóstico volvió obligatoria (no estaba en el preregistro; se declara como tal).

El testigo de d4 («todo el día del lado del contexto») gana casi lo mismo que P05b. Si el «contexto» (cierre diario
frente a su SMA 50) es la fuente de la ventaja, la regla de tendencia sola debería igualar o superar a las estrategias.
No es una regla sacada de estos datos: es el filtro de tendencia de manual, por eso se prueba igual en los 7 activos.

Reglas, con velas diarias UTC (posición decidida con el cierre de AYER, aplicada al retorno de HOY):
  T-LC  largo/corto: largo si cierre de ayer > SMA 50 de ayer, corto si está por debajo (futuros).
  T-L   largo/fuera: largo si está por encima; si no, en efectivo (CONTADO: se puede con 40.000 pesos).
  B&H   comprar y mantener.
Costes por cambio de posición: futuros 0,05 %/lado; contado 0,10 %/lado (doble: 0,10 y 0,20).
Uso: python3 -I d5_contexto_puro.py > d5_contexto_puro.txt"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metricas import ruta_velas  # noqa: E402

ACT = {"BTC": "datos-btc", "ETH": "datos-btc", "SOL": "datos-otros", "BNB": "datos-otros", "XRP": "datos-otros",
       "DOGE": "datos-otros", "ADA": "datos-otros"}


def diarias(etq):
    a = np.load(ruta_velas(f"{etq}USDT"))
    df = pd.DataFrame(a[:, 1:5], columns=["o", "h", "l", "c"], index=pd.to_datetime(a[:, 0].astype("int64"), unit="ms"))
    d = df.resample("1D").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    return d


def correr(d, regla, coste_lado):
    ret = d.c.pct_change().fillna(0.0)  # retorno de cierre a cierre (00:00 a 23:59 UTC)
    sma = d.c.rolling(50).mean()
    arriba = (d.c > sma).shift(1)       # decidido con el cierre de ayer
    if regla == "T-LC":
        pos = np.where(arriba.isna(), 0, np.where(arriba == True, 1, -1))  # noqa: E712
    elif regla == "T-L":
        pos = np.where(arriba == True, 1, 0)  # noqa: E712
    else:
        pos = np.ones(len(d))
    pos = pd.Series(pos, index=d.index, dtype=float)
    pos[sma.shift(1).isna()] = 0.0
    cambios = pos.diff().abs().fillna(pos.abs())
    neto = pos * ret - cambios * coste_lado / 100
    return neto, cambios


def resumen(neto, cambios):
    eq = (1 + neto).cumprod()
    dd = (1 - eq / eq.cummax()).max() * 100
    anos = len(neto) / 365.25
    cagr = (eq.iloc[-1] ** (1 / anos) - 1) * 100
    sh = neto.mean() / neto.std() * np.sqrt(365) if neto.std() > 0 else np.nan
    return dict(anual=cagr, caida=dd, sharpe=sh, cambios_mes=cambios.sum() / (len(neto) / 30.44))


filas = []
for etq in ACT:
    d = diarias(etq)
    for regla, costes in (("T-LC", (0.05, 0.10)), ("T-L", (0.10, 0.20)), ("B&H", (0.10, 0.20))):
        for c in costes:
            neto, camb = correr(d, regla, c)
            for tr, sel in (("2020-2023", neto.index < "2024-01-01"), ("2024-2026", neto.index >= "2024-01-01")):
                r = resumen(neto[sel], camb[sel])
                r.update(activo=etq, regla=regla, coste_lado=c, tramo=tr)
                filas.append(r)
R = pd.DataFrame(filas)
pd.set_option("display.width", 250)
for tr in ("2020-2023", "2024-2026"):
    print(f"\n=== {tr}: rentabilidad anual compuesta % | caída máxima % | Sharpe (diario, 365) | cambios de posición por mes ===")
    x = R[R.tramo == tr]
    for met in ("anual", "caida", "sharpe", "cambios_mes"):
        print(f"  {met}")
        print(x.pivot_table(index=["regla", "coste_lado"], columns="activo", values=met)[list(ACT)].to_string(
            float_format=lambda v: f"{v:+.1f}" if met != "sharpe" else f"{v:+.2f}"))
R.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "d5_contexto_puro.csv"), index=False)
