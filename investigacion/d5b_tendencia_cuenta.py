"""D5c: la regla de tendencia T-L (largo si el cierre diario de ayer > SMA 50; si no, efectivo) en la cuenta real de
40.000 pesos, con las mismas restricciones que b2 (paso de cantidad, mínimo 5 USDT, comisión) y la parada total del −20 %.

Con 12,59 USDT el mínimo de 5 USDT obliga a poner al menos ~40 % del saldo; se prueban asignaciones de 40, 60 y 100 %.
Compra y venta a la apertura del día (00:00 UTC, primer minuto). Uso: python3 -I d5b_tendencia_cuenta.py"""
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metricas import ruta_velas  # noqa: E402

COP = 3177.85
CAP0 = 40000 / COP
ACT = {"BTC": ("datos-btc", 0.00001), "ETH": ("datos-btc", 0.0001)}


def diarias(etq):
    a = np.load(ruta_velas(f"{etq}USDT"))
    df = pd.DataFrame(a[:, 1:5], columns=["o", "h", "l", "c"], index=pd.to_datetime(a[:, 0].astype("int64"), unit="ms"))
    return df.resample("1D").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()


def cuenta(d, asig, com, bnb, paso, tope_total=0.20):
    sma = d.c.rolling(50).mean()
    quiere = ((d.c > sma) & sma.notna()).shift(1, fill_value=False)
    efectivo, q, polvo = CAP0, 0.0, 0.0
    pico, caida, n_ops, parada = CAP0, 0.0, 0, None
    serie = []
    for f, row, want in zip(d.index, d.itertuples(), quiere):
        if parada is None:
            if want and q == 0:
                noc = asig * (efectivo + polvo * row.o)
                noc = min(noc, efectivo)
                qq = math.floor(noc / row.o / paso + 1e-9) * paso
                if qq * row.o >= 5:
                    efectivo -= qq * row.o * (1 + (com / 100 if bnb else 0))
                    q = qq if bnb else qq * (1 - com / 100)
                    n_ops += 1
            elif not want and q > 0:
                qv = math.floor((q + polvo) / paso + 1e-9) * paso
                polvo = q + polvo - qv
                efectivo += qv * row.o * (1 - com / 100)
                q = 0.0
                n_ops += 1
        valor = efectivo + (q + polvo) * row.c
        pico = max(pico, valor)
        caida = max(caida, (1 - valor / pico) * 100)
        if parada is None and (1 - valor / pico) >= tope_total:
            parada = f  # parada total: se vende al día siguiente y se vuelve a papel
            if q > 0:
                qv = math.floor((q + polvo) / paso + 1e-9) * paso
                polvo = q + polvo - qv
                efectivo += qv * row.c * (1 - com / 100)
                q = 0.0
        serie.append(valor)
    final = serie[-1]
    anos = len(d) / 365.25
    return dict(anual=((final / CAP0) ** (1 / anos) - 1) * 100, final_cop=final * COP, caida=caida, ops_mes=n_ops / (len(d) / 30.44),
                parada=str(parada.date()) if parada is not None else "-")


filas = []
for etq in ACT:
    d = diarias(etq)
    for asig in (0.4, 0.6, 1.0):
        for nombre, com, bnb in (("BNB 0,075", 0.075, True), ("doble 0,15 en BTC", 0.15, False)):
            for tr, sel in (("2020-2023", d.index < "2024-01-01"), ("2024-2026", d.index >= "2024-01-01")):
                # la SMA necesita historia: se calcula con todo y se recorta después (sin mirar el futuro: es una media pasada)
                x = d.copy()
                r = cuenta(x[sel] if tr == "2020-2023" else x[x.index >= x.index[x.index >= "2024-01-01"][0] - pd.Timedelta(days=60)],
                           asig, com, bnb, ACT[etq][1])
                r.update(activo=etq, asignacion=f"{asig * 100:.0f} %", comision=nombre, tramo=tr)
                filas.append(r)
R = pd.DataFrame(filas)[["activo", "asignacion", "comision", "tramo", "anual", "final_cop", "caida", "ops_mes", "parada"]]
pd.set_option("display.width", 200)
print("T-L en la cuenta de 40.000 pesos (2024-2026 arranca 60 días antes para tener SMA 50; la parada del −20 % detiene la cuenta)")
print(R.to_string(index=False, float_format=lambda v: f"{v:,.1f}"))
R.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "d5b_tendencia_cuenta.csv"), index=False)
