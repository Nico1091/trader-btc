"""Tarea 2: cada patrón de vela del curso en 15 m, 1 h y 4 h, con lo que pasa 1, 4 y 24 horas después.

Entrada al cierre de la vela del patrón, en el lado que indica el patrón. Bruto y neto con 0,05 %/lado
(0,10 % ida y vuelta) y con el doble (0,20 %). El azar: la media de n velas sorteadas del mismo marco,
en el mismo lado. Ajuste 2020-2023 y prueba 2024-01 a 2026-10, por separado.
Patrones de indecisión (lado 0): se mide el retorno largo y el tamaño del movimiento |r| frente al azar."""
import sys
import numpy as np
import pandas as pd
from lib import cargar, remuestrear, patrones, retorno_adelante, percentil_azar, CORTE

m1 = cargar()
print("velas 1m:", len(m1), m1.index[0], "->", m1.index[-1])
filas = []
for tf in (15, 60, 240):
    df = remuestrear(m1, tf)
    pat, lado = patrones(df)
    t_cierre = df.index + pd.Timedelta(minutes=tf) - pd.Timedelta(minutes=1)  # cierre del último minuto
    rets = {H: retorno_adelante(m1["c"], t_cierre, H) for H in (1, 4, 24)}
    prueba = df.index >= CORTE
    for nombre in pat.columns:
        m = pat[nombre].to_numpy()
        s = lado[nombre]
        for H in (1, 4, 24):
            r = rets[H]
            for tramo, sel in (("ajuste", ~prueba), ("prueba", prueba)):
                pob = r[sel]
                x = r[sel & m]
                x = x[~np.isnan(x)]
                n = len(x)
                if s != 0:
                    g = s * x
                    pobs = s * pob
                    fila = dict(tf=tf, patron=nombre, lado=s, H=H, tramo=tramo, n=n,
                                bruto=g.mean() if n else np.nan,
                                neto=(g - 0.10).mean() if n else np.nan,
                                doble=(g - 0.20).mean() if n else np.nan,
                                acierto=(g - 0.10 > 0).mean() * 100 if n else np.nan,
                                azar_bruto=np.nanmean(pobs),
                                pct=percentil_azar(g.mean(), pobs, n) if n else np.nan)
                else:
                    fila = dict(tf=tf, patron=nombre, lado=0, H=H, tramo=tramo, n=n,
                                bruto=x.mean() if n else np.nan,
                                neto=np.nan, doble=np.nan, acierto=np.nan,
                                azar_bruto=np.nanmean(pob),
                                pct=percentil_azar(x.mean(), pob, n) if n else np.nan,
                                mov=np.abs(x).mean() if n else np.nan,
                                azar_mov=np.nanmean(np.abs(pob)),
                                pct_mov=percentil_azar(np.abs(x).mean(), np.abs(pob), n) if n else np.nan)
                filas.append(fila)
    print("listo tf", tf, flush=True)

t = pd.DataFrame(filas)
t.to_csv(sys.argv[1] if len(sys.argv) > 1 else "t2_velas.csv", index=False)
print(t.to_string(max_rows=2000, float_format=lambda v: f"{v:.3f}"))
